# `auditlogd` — Audit Logging Daemon for Command Tracking and RADIUS Accounting

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Repositories and modules changed](#71-repositories-and-modules-changed)
  - [7.2 Threading model and internal roles](#72-threading-model-and-internal-roles)
  - [7.3 RADIUS Accounting packet contents](#73-radius-accounting-packet-contents)
  - [7.4 Retransmit behavior](#74-retransmit-behavior)
  - [7.5 Kernel audit consumption and reassembly](#75-kernel-audit-consumption-and-reassembly)
  - [7.6 Per-server health and global back-pressure](#76-per-server-health-and-global-back-pressure)
  - [7.7 Feedback-loop prevention](#77-feedback-loop-prevention)
  - [7.8 Systemd integration](#78-systemd-integration)
  - [7.9 Linux dependencies and interfaces](#79-linux-dependencies-and-interfaces)
  - [7.10 Scalability and performance](#710-scalability-and-performance)
  - [7.11 Docker and build dependencies](#711-docker-and-build-dependencies)
  - [7.12 Serviceability and debug](#712-serviceability-and-debug)
  - [7.13 Platform dependency](#713-platform-dependency)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test cases](#131-unit-test-cases)
  - [13.2 System Test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items)

---

## 1. Revision

| Rev | Change Description                                        |
|-----|-----------------------------------------------------------|
| 0.1 | Initial HLD for `auditlogd` in `sonic-host-services`.     |

---

## 2. Scope

This document describes the high-level design of `auditlogd`, a new host-level daemon in `sonic-host-services` that streams every command executed on a SONiC switch to configured RADIUS servers as an RFC 2866 **Accounting-Request**, providing operators with a central, tamper-resistant audit trail of privileged actions.

**In scope**

- Daemon architecture and internal roles.
- Consumption of the existing `RADIUS_SERVER`, `MGMT_INTERFACE`, and `DEVICE_METADATA` tables in `CONFIG_DB`, including per-server `timeout` and `retransmit`.
- RFC 2865 / 2866 conformant RADIUS Accounting-Request construction and retransmit behavior (same packet reused across retries).
- Kernel audit consumption over `NETLINK_AUDIT`, multi-record event reassembly, and command normalization.
- Per-server health tracking and a global back-pressure loop that pauses consumption when no RADIUS server is reachable.
- Feedback-loop prevention against self-auditing.
- Systemd integration under `sonic.target`.

**Out of scope**

- Authentication (`Access-Request`) flows — this daemon does not change how SONiC does RADIUS authentication today.
- 802.1x / port-based authentication (PAC).
- New CONFIG_DB tables or fields (the design deliberately reuses what exists).
- New CLI or YANG models (a future doc will define operator-facing surfaces such as per-server health).
- Persisting unsent events across RADIUS outages.

---

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| AAA | Authentication, Authorization, and Accounting |
| RADIUS | Remote Authentication Dial In User Service (RFC 2865 / 2866) |
| Accounting-Request | RADIUS packet code 4 used to convey session accounting information |
| NAS | Network Access Server — the switch itself in this context |
| NAS-Identifier | RADIUS attribute (32) identifying the NAS; set to the switch hostname |
| Netlink audit | Kernel-to-userspace interface (`NETLINK_AUDIT`) that streams audit records |
| `execve` | Linux syscall used to execute a program; the trigger for audit records |
| VRF | Virtual Routing and Forwarding instance (e.g., `mgmt` VRF) |
| CONFIG_DB | Redis DB #4 in SONiC that holds configuration state |

---

## 4. Overview

`auditlogd` is a new daemon in `sonic-host-services` that watches every command executed on a SONiC switch and reports each one to configured RADIUS servers as an **Accounting-Request** (per RFC 2866). It gives operators a central, tamper-resistant audit trail of privileged actions on the box.

The daemon is a pure consumer:

- It does **not** authenticate users.
- It does **not** modify how SONiC does RADIUS auth today.
- It has **no** dependency on 802.1x / PAC.

It reads only:

- Linux kernel audit events (via a netlink socket).
- Existing RADIUS server configuration from `CONFIG_DB`.

---

## 5. Requirements

**Functional**

1. Emit one RFC 2866 Accounting-Request per audited command to every configured RADIUS server.
2. Reuse the existing SONiC RADIUS configuration (`RADIUS_SERVER`, `MGMT_INTERFACE`, `DEVICE_METADATA`) without introducing new tables.
3. Honor per-server `timeout` (default 5 s) and `retransmit` (default 0) semantics as defined by RFC 2865 / 2866; the same packet must be reused across retries so servers can dedupe.
4. Verify the Response Authenticator on every Accounting-Response before treating a send as successful.
5. Track per-server health and expose transitions via logs (`disconnected` after 3 consecutive fully-failed sends; reconnect probe at most every 30 s).
6. Pause audit consumption cleanly when no RADIUS server is reachable, so that sustained outages do not cause memory growth or block user commands.
7. React to `RADIUS_SERVER` and management-IP changes without a manual restart.
8. Prevent self-auditing feedback loops.

**Non-functional**

1. Must consume kernel audit events promptly to avoid `ENOBUFS` from the kernel.
2. A slow or unresponsive RADIUS server must not block delivery to other servers or audit-event consumption.
3. The daemon must run as root (required for netlink audit and audit-rule management).
4. Restart must be capped by systemd to prevent crash-loops.

**Exemptions / non-goals**

- No new CLI/YANG in this phase.
- No local persistence of unsent events (accounting is best-effort by design).
- No changes to how SONiC currently authenticates users via RADIUS.

---

## 6. Architecture Design

`auditlogd` slots in as a **new host-level service** in the existing `sonic-host-services` package. It does not change the SONiC control-plane architecture: no changes to SWSS, syncd, orchagent, or SAI. It is a passive consumer of kernel state and existing CONFIG_DB tables, and a producer of RADIUS UDP traffic.

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

This is not a SONiC Application Extension; it is a first-party host service delivered as part of `sonic-host-services`, and does not require Application Extension infrastructure changes.

---

## 7. High-Level Design

### 7.1 Repositories and modules changed

Only `sonic-host-services` is modified — a new daemon script, its systemd unit, packaging hooks, and a unit-test folder. No changes required in `sonic-swss`, `sonic-utilities`, or `sonic-buildimage`.

### 7.2 Threading model and internal roles

Single process with two long-running threads: a **main thread** that owns the CONFIG_DB subscription and reacts to configuration changes, and a **monitor thread** that reads and reassembles kernel audit events. Internally the code is split into four roles — *daemon controller*, *audit-event monitor*, *audit logger*, and *RADIUS accounting client* — with per-server RADIUS delivery done on short-lived worker threads so a slow server never blocks audit-event consumption.

### 7.3 RADIUS Accounting packet contents

For each audited command the daemon sends one RFC 2866 Accounting-Request carrying the resolved username, `Acct-Status-Type=Start`, a unique `Acct-Session-ID`, the command line as `Called-Station-Id` (truncated to 250 bytes), the event timestamp, and the switch hostname as `NAS-Identifier`. Request and Response Authenticators are computed and verified per RFC 2866 using the shared secret.

### 7.4 Retransmit behavior

The per-server `timeout` (default 5 s) and `retransmit` (default 0) drive an RFC 2865 / 2866-compliant retry loop: the **same** packet — Identifier, attributes, and Request Authenticator — is reused across every attempt so servers can dedupe rather than double-count. A valid response short-circuits the loop; only fully exhausted attempts count as a failure for the per-server health state (§7.6).

### 7.5 Kernel audit consumption and reassembly

Events are consumed live from `NETLINK_AUDIT` (not by tailing `auditd` files), giving real-time delivery and native back-pressure signals from the kernel. At startup the daemon installs `execve` audit rules keyed `sonic_commands` and excludes its own PID; the monitor reassembles multi-record events, flushes on end-of-event markers or after a 2 s deadline, resolves the username, filters noise (audit tools and empty/degenerate commands), and hands the result to the audit logger.

### 7.6 Per-server health and global back-pressure

- **Per-server** — a server is marked `disconnected` after 3 consecutive fully-failed sends; reconnect is attempted at most every 30 s. Only transitions are logged at INFO.
- **Global** — every 10 s the monitor checks whether any server is reachable. If none is, it closes the netlink socket so the kernel stops queueing events; consumption resumes when at least one server recovers. An `ENOBUFS` from the kernel forces an immediate pause.

Net effect: RADIUS outages degrade cleanly with no memory growth and no impact on user commands.

### 7.7 Feedback-loop prevention

Three layered defenses stop the daemon from auditing itself: kernel-level PID exclusion in the audit rules, user-space filtering of `auditlogd` / `auditctl` / `ausearch` / `auditd` (including `sudo` / `python3` wrappers), and `Wants=auditd.service` (not `Requires=`) so `auditd` restarts do not cascade into `auditlogd`.

### 7.8 Systemd integration

Delivered as a standard `sonic-host-services` unit: ordered after `config-setup.service` and `hostcfgd.service`, bound to `sonic.target`, with a crash-loop cap of 5 restarts per 10 minutes and an `AUDITLOGD_LOG_LEVEL` environment override for verbose logging. Full unit file lives with the daemon source.

### 7.9 Linux dependencies and interfaces

Uses `NETLINK_AUDIT` for event ingestion, `auditctl` (once, at startup) to install audit rules, and `libaudit` / `python-audit` for record decoding. Runs in the host namespace (not a container) because it owns audit rules; the RADIUS UDP socket can optionally be bound to a VRF such as `mgmt`.

### 7.10 Scalability and performance

Command rates are low and per-event work is bounded by the number of configured RADIUS servers (usually a handful). The reassembly buffer is bounded by the 2 s flush deadline, and the back-pressure loop (§7.6) prevents unbounded queueing during outages.

### 7.11 Docker and build dependencies

No new docker container. Ships in the existing `sonic-host-services` Debian package with no additional first-party dependencies.

### 7.12 Serviceability and debug

Syslog logging (default `WARNING`, runtime override to `DEBUG` via the systemd environment). One INFO line per per-server disconnect/reconnect transition and per retry-recovered send. Per-server health is in-memory today and can be exposed by a future CLI/telemetry work item. Delivery is best-effort — timeouts count as failures and drive health; there is no local persistence of unsent events.

### 7.13 Platform dependency

Host-level Python daemon with no ASIC / SAI interaction. Runs on all supported SONiC platforms; no vendor-specific enablement is required.

---

## 8. SAI API

Not applicable. `auditlogd` is a host-level daemon with no ASIC interaction; **no SAI APIs are used, added, or modified**.

---

## 9. Configuration and Management

### 9.1 Manifest

Not applicable — `auditlogd` is delivered as part of the built-in `sonic-host-services` package, **not** as a SONiC Application Extension. No AE manifest is required.

### 9.2 CLI/YANG model Enhancements

No new CLI or YANG model is introduced by this HLD.

### 9.3 Config DB Enhancements

**No new CONFIG_DB tables or fields are added.** The daemon reads three existing tables:

- **`RADIUS_SERVER`** — one entry per server. From each entry the daemon uses:
  - the server IP (the table key),
  - the accounting port (falls back to the auth port, then to 1813),
  - the shared secret (`passkey`),
  - an optional explicit source IP (`src_ip`),
  - the request `timeout` in seconds (defaults to 5),
  - the number of `retransmit` retries (defaults to 0 — send once, no retry).
- **`MGMT_INTERFACE`** — used to discover the management IP of `eth0`. This becomes the default source IP for any RADIUS server that does not have an explicit `src_ip`.
- **`DEVICE_METADATA`** — the hostname of the switch (`localhost.hostname`) is used as the RADIUS `NAS-Identifier` in every accounting packet.

**Reacting to configuration changes:**

| Change | What the daemon does |
|--------|----------------------|
| Any `RADIUS_SERVER` change | Closes all existing RADIUS clients and re-reads the full server list. |
| `eth0` management IP change | Rebuilds only those RADIUS clients whose current source IP was the old management IP. The rebuilt client inherits the server's existing `timeout` and `retransmit` settings so behavior is unchanged across the mgmt-IP swap. |

No manual restart is required for either change. Downward compatibility is preserved because no schema keys are added, removed, or repurposed.

---

## 10. Warmboot and Fastboot Design Impact

`auditlogd` is not in the data-plane path. It has **no** warmboot or fastboot handoff requirements.
Existing warmboot/fastboot performance targets (control-plane and data-plane downtime) are not affected.

---

## 11. Memory Consumption

- When the package is not installed / the unit is masked: **zero** memory consumption.
- When installed but disabled by configuration (no `RADIUS_SERVER` entries): the daemon runs but its monitor thread stays paused; memory is bounded by the Python interpreter footprint plus the fixed-size reassembly buffer.
- When enabled with active traffic: memory is bounded by the reassembly buffer (per-event, flushed on end-of-event marker or after 2 s — see §7.5) plus a fixed number of short-lived worker threads (one per RADIUS server per event). No unbounded queues.
- During sustained RADIUS outages: the global back-pressure loop (§7.6) closes the netlink socket, so incoming events do not queue in userspace memory.

---

## 12. Restrictions/Limitations

1. **Best-effort accounting.** RADIUS uses UDP; timeouts count as failures. During a full outage of all configured servers the monitor pauses and events in that window are dropped rather than queued. No local persistence.
2. **Requires root privilege.** The daemon manipulates kernel audit rules and reads from `NETLINK_AUDIT`.
3. **Command truncation.** `Called-Station-Id` (the command line) is truncated to **250 bytes** to fit under the RADIUS attribute limit of 253.
4. **UID resolution failures** fall back to `uid:<n>` in `User-Name`.
5. **Audit-tool commands are intentionally filtered** (`auditlogd`, `auditctl`, `ausearch`, `auditd`) to prevent feedback loops, including `sudo`/`python3` wrappers of those binaries.
6. **No CLI/YANG surface yet.** Per-server health is in-memory only; troubleshooting today relies on `AUDITLOGD_LOG_LEVEL=DEBUG` and syslog.
7. **No SAI or platform enablement**, and therefore no vendor-specific dependencies.

---

## 13. Testing Requirements/Design

### 13.1 Unit Test cases

Delivered under `tests/auditlogd/`:

- **Packet formatting** — Accounting-Request attributes and Request Authenticator match RFC 2866 for a given shared secret.
- **Retransmit determinism** — the same packet is reused across retries and a valid response short-circuits the loop.
- **Response validation** — a tampered Response Authenticator is rejected.
- **Event reassembly** — multi-record kernel events are merged into one command; stale buffers flush after 2 s.
- **Command filtering** — audit-tool commands and empty/degenerate commands are dropped.
- **Mgmt-IP handling** — the mgmt IP of `eth0` is used as default `src_ip`, and mgmt-IP changes rebuild only affected clients while preserving `timeout` / `retransmit`.
- **Config reactivity** — `RADIUS_SERVER` changes trigger a client rebuild without process restart.
- **Per-server health** — a server flips to disconnected after 3 consecutive fully-failed sends and back on recovery, with one INFO log per transition.
- **Back-pressure** — the netlink socket is closed when no server is reachable and reopened on recovery; `ENOBUFS` forces an immediate pause.
- **Feedback-loop safety** — executing `auditctl` or `auditlogd` under audit produces no outbound Accounting-Request.

### 13.2 System Test cases

Regression: existing SONiC RADIUS authentication tests must continue to pass, since `auditlogd` does not modify that path.

---

## 14. Open/Action items
