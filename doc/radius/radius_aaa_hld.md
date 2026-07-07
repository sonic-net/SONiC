# High-Level Design: `auditlogd` — RADIUS Accounting for Command Auditing

## 1. Overview

`auditlogd` is a new daemon in `sonic-host-services` that watches every command executed on a SONiC switch and reports each one to configured RADIUS servers as an **Accounting-Request** (per RFC 2866). It gives operators a central, tamper-resistant audit trail of privileged actions on the box.

The daemon is a pure consumer: it does not authenticate users, does not modify how SONiC does RADIUS auth today, and has no dependency on 802.1x/PAC. It reads:

- Linux kernel audit events (via a netlink socket).
- Existing RADIUS server configuration from `CONFIG_DB`.

---

## 2. What Ships

| Path                                                     | Purpose                                                             |
|----------------------------------------------------------|---------------------------------------------------------------------|
| `scripts/auditlogd`                                      | The daemon itself.                                                  |
| `data/debian/sonic-host-services-data.auditlogd.service` | Systemd unit for the daemon.                                        |
| `data/debian/rules`                                      | Registers the systemd unit at package build time.                   |
| `setup.py`                                               | Installs the daemon as `/usr/local/bin/auditlogd`.                  |
| `tests/auditlogd/`                                       | Unit-test suite (packet formatting, netlink, mgmt-IP, filtering).   |

---

## 3. Architecture

`auditlogd` is a single process with two long-running threads:

- **Main thread** — connects to CONFIG_DB, subscribes to the tables it cares about, and processes configuration changes as they arrive.
- **Monitor thread** — receives audit events from the kernel, assembles them into complete records, and hands each one off to be sent as a RADIUS Accounting-Request.

Internally the code is organized around four roles:

| Role                       | Responsibility                                                                                                                              |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| **Daemon controller**      | Process bootstrap. Owns the CONFIG_DB subscription and spawns the monitor thread.                                                            |
| **Audit-event monitor**    | Owns the kernel audit socket. Buffers and reassembles multi-record events, applies filters, and hands each command up.                       |
| **Audit logger**           | Loads configuration, installs kernel audit rules, and fans a command out to every configured RADIUS server.                                  |
| **RADIUS accounting client** | Builds and sends one Accounting-Request per server, tracks per-server health, and verifies responses.                                     |

RADIUS delivery for a given event runs in short-lived worker threads (one per server) so a slow server can never block audit-event consumption.

```
   kernel audit         audit-event monitor            audit logger          RADIUS accounting client        RADIUS server(s)
   (execve rules)  --netlink-->  reassemble  --command-->   fan-out  --thread-per-server-->  UDP  ------->

                                        ^
                                        | reload / update
                                        |
                           daemon controller (main thread)
                                        ^
                                        |
                                     CONFIG_DB
                                (RADIUS_SERVER, MGMT_INTERFACE, DEVICE_METADATA)
```

---

## 4. Configuration

The daemon does **not** introduce new CONFIG_DB tables or fields. It reads three existing tables:

- **`RADIUS_SERVER`** — one entry per server. From each entry the daemon uses:
  - the server IP (the table key),
  - the accounting port (falls back to the auth port, then to 1813),
  - the shared secret (`passkey`),
  - an optional explicit source IP (`src_ip`),
  - the request `timeout` in seconds (defaults to 5),
  - the number of `retransmit` retries (defaults to 0 — send once, no retry).
- **`MGMT_INTERFACE`** — used to discover the management IP of `eth0`. This becomes the default source IP for any RADIUS server that does not have an explicit `src_ip`.
- **`DEVICE_METADATA`** — the hostname of the switch (`localhost.hostname`) is used as the RADIUS `NAS-Identifier` in every accounting packet.

### Reacting to configuration changes

| Change                          | What the daemon does                                                                            |
|---------------------------------|-------------------------------------------------------------------------------------------------|
| Any `RADIUS_SERVER` change      | Closes all existing RADIUS clients and re-reads the full server list.                           |
| `eth0` management IP change     | Rebuilds only those RADIUS clients whose current source IP was the old management IP. The rebuilt client inherits the server's existing `timeout` and `retransmit` settings so behavior is unchanged across the mgmt-IP swap. |

No manual restart is required for either change.

---

## 5. RADIUS Accounting

For every audited command the daemon sends an Accounting-Request (packet code 4, per RFC 2866) that carries the following information:

- **User-Name** — the resolved username, or `uid:<n>` if the user cannot be resolved.
- **Acct-Status-Type** — `Start`. `Stop` / `Interim-Update` / `Accounting-On` / `Accounting-Off` are implemented for future use.
- **Acct-Session-ID** — a unique per-command ID of the form `sonic-<epoch>-<counter>`.
- **Called-Station-Id** — the command line itself, truncated to 250 bytes (RADIUS attribute limit is 253).
- **Event-Timestamp** — seconds since epoch.
- **NAS-Identifier** — the switch hostname from `DEVICE_METADATA`.

The Request Authenticator is computed per RFC 2866 using the shared secret; the Response Authenticator on the reply is verified before the send is considered successful.

### Timeout and retransmit

Each server's `timeout` (default 5 s) is applied as the UDP socket receive timeout, and its `retransmit` (default 0) is the number of retries the daemon will attempt after the initial send. So `retransmit=2` yields up to 3 total transmissions per audit event; `retransmit=0` sends once.

Retransmits follow RFC 2865 / 2866:

- The **same** packet is sent on every attempt — the RADIUS Identifier, the attribute payload, and the Request Authenticator are all computed once and preserved across retries. This lets the RADIUS server correctly recognize retries as duplicates rather than distinct accounting events.
- The daemon waits up to `timeout` seconds for a valid Accounting-Response between each attempt. A response received at any attempt short-circuits the loop and is treated as success.
- Failures during socket setup (for example a VRF-bind error) fall through to the outer retry loop; a brief 100 ms sleep is inserted between exception retries to avoid tight loops.
- Only if *all* attempts fail is the send counted as a failure for the per-server health state described in §7. A successful retry logs one INFO line noting how many attempts it took.

---

## 6. Consuming Kernel Audit Events

`auditlogd` receives audit events directly from the Linux kernel over a `NETLINK_AUDIT` multicast socket, rather than reading `auditd` log files. This gives it real-time delivery, back-pressure signals, and lets it operate even if `auditd` is briefly restarted.

At startup the daemon installs two audit rules that key every `execve` syscall (on both 32-bit and 64-bit ABIs) as `sonic_commands`, and excludes its own PID to avoid self-audit. A few audit-tool executables (`auditctl`, `ausearch`, `auditd`) are keyed separately so they can be filtered out.

The kernel produces multiple records per command (system-call record, exec arguments, working directory, path, process title, end-of-event marker). The monitor:

1. Starts tracking an event when it sees the `sonic_commands` key on any of its records.
2. Merges subsequent records for the same event.
3. Flushes the reassembled event as soon as an end-of-event marker arrives (the process-title record, an explicit end-of-event record, or any record type that the kernel emits as a single-record event).
4. Also flushes any event that has been sitting in the buffer for more than two seconds without a marker, so the buffer never leaks.

When flushed, the event is filtered and normalized:

- The username is resolved from the UID.
- The command is derived preferentially from the process-title / exec-args record, joining up to the first ten arguments.
- Empty, single-character, all-digit, hex-address-only, and audit-tool commands are discarded.
- The daemon's own PID is filtered a second time as a safety net.

Whatever survives is handed to the audit logger.

---

## 7. RADIUS Server Health & Back-Pressure

Because the daemon feeds off a kernel socket, it must consume events promptly or the kernel will start dropping (or, worse, will surface `ENOBUFS` errors). RADIUS servers are remote and can fail, so the daemon actively pauses instead of blocking:

**Per-server state (tracked by the accounting client):**

- A "failed send" here means all configured retransmit attempts have been exhausted for one audit event (see §5). Marked disconnected after **3 consecutive failed sends**.
- Once disconnected, reconnect is retried at most every **30 seconds**.
- A single log line reports each "disconnected" and "reconnected" transition; single, transient failures are only visible in DEBUG.

**Global back-pressure loop (run by the monitor):**

- Every **10 seconds** the monitor asks the logger whether *any* RADIUS server is currently connected or eligible for reconnect.
- If **no** server is available, the monitor closes the netlink socket and enters a paused state. This stops userspace consumption; the kernel-side subscription is dropped, so no further events queue in the daemon's memory.
- When at least one server is reachable again, the monitor reopens the netlink socket and resumes.
- If the kernel ever returns `ENOBUFS` on a read, the monitor pauses immediately regardless of the 10-second cadence.

The result: RADIUS outages degrade cleanly. The switch continues to operate normally; audit records that fell into the gap are dropped rather than causing memory pressure or blocking user commands.

---

## 8. Preventing Feedback Loops

Auditing the daemon that talks about auditing would blow up quickly. Three defenses:

1. **Audit rules exclude the daemon's own PID at the kernel level**, so its own `execve`s are never tagged `sonic_commands`.
2. **Any command whose executable is `auditlogd`, `auditctl`, `ausearch`, or `auditd`** is dropped in user-space filtering, including compound invocations such as `sudo auditctl ...` or `python3 auditlogd`.
3. **`Wants=auditd.service` (not `Requires=`)**, so a restart of `auditd` does not restart `auditlogd`.

---

## 9. Systemd Integration

The daemon is installed as a normal SONiC host service:

```
[Unit]
Description=Audit Logging daemon for command tracking and RADIUS accounting
Wants=auditd.service
Requires=config-setup.service
After=auditd.service config-setup.service hostcfgd.service
BindsTo=sonic.target
After=sonic.target

[Service]
Type=simple
ExecStart=/usr/local/bin/auditlogd
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=600
TimeoutStopSec=5
# Environment="AUDITLOGD_LOG_LEVEL=DEBUG"    # opt-in verbose logging

[Install]
WantedBy=sonic.target
```

Notes for operators:

- Ordered after `config-setup.service` and `hostcfgd.service` so CONFIG_DB is populated before the daemon starts.
- Bound to `sonic.target`, so it starts and stops with SONiC.
- Restart is capped at 5 restarts per 10 minutes to prevent crash-loops.
- Default log level is `WARNING`; set `AUDITLOGD_LOG_LEVEL=DEBUG` in the service environment to enable verbose logs without touching the code.

---

## 10. Operational Notes

- The daemon must run as root; it manipulates kernel audit rules and reads from `NETLINK_AUDIT`.
- Accounting is best-effort. RADIUS uses UDP; timeouts are treated as failures and drive the health state described in §7. There is no local persistence of unsent events by design — sustained RADIUS outages result in a paused daemon, not unbounded memory growth.
- To increase visibility during troubleshooting, set `AUDITLOGD_LOG_LEVEL=DEBUG` in the service environment and restart the unit.
- Health of each RADIUS server (connected / disconnected / consecutive failures) is available in memory and can be surfaced through future CLI/telemetry work; this document does not define a CLI schema for it.

