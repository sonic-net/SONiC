# healthd in Rust — 2-pager (brief HLD)

| | |
|---|---|
| Target version | SONiC 202705 |
| Status | Draft for review, 2026-10-26 |
| Baseline HLDs | https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-health-HLD.md · https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-ready-HLD.md (outdated; the Python code is the reference) |

## 1. Motivation

SONiC on multi-ASIC switches must fit in a fixed amount of RAM, and healthd is an always-running daemon. Measured on one
image root with both daemons installed (SN5600 configuration, 60s polling, simulated STATE_DB data), the Python daemon
holds 78MB RSS and the Rust one 40.5MB, of which about 27MB is the Python interpreter and the vendor's `sonic_platform`,
loaded for the LED (D4).

## 2. Decisions

- **D1.** The daemon is rewritten in Rust for every platform. The Python daemon and its `health_checker` package are
  removed from the image. No runtime switch, no Python fallback in the image.
- **D2.** One deb, `sonic-system-health`, holds the daemon `healthd` and the CLI utility `healthcheck`. Both run on
  the host, not in a container. `show system-health` stays in sonic-utilities; it runs `healthcheck --json` and
  renders its output. The two share one Rust library, so the checks are written once.
- **D3.** External interfaces stay the same: STATE_DB tables and fields, the config files
  `system_health_monitoring_config.json` and `/etc/monit/monitrc` (R5), CLI output, the `system-health.service` unit
  (`ExecStart` changes; the unused cache directory goes), syslog identifiers and events.
- **D4.** Every check reads the system the way the Python daemon does: the Docker API, `supervisorctl`, `systemctl`,
  `monit`, and for the LED the vendor's `sonic_platform`, called in process through the platform API of
  sonic-platform-common and its PyO3 bridge. Vendors change nothing.
- **D5.** Python bugs that cause a real fault are fixed, not ported (§5).

## 3. Requirements

| ID | Requirement | Pri |
|---|---|---|
| R1 | Same results as Python for the Services, Hardware and user-defined checks: object names, messages, `summary`. | P1 |
| R2 | Same system-ready as Python: `ALL_SERVICE_STATUS`, one global `SYSTEM_READY\|SYSTEM_STATE`, console message. | P1 |
| R3 | LED as in Python: normal color when OK; when Not OK, booting color during monit's start delay, then fault color. Set every daemon cycle and every CLI run. | P1 |
| R4 | `show system-health summary\|detail\|monitor-list` output is unchanged. | P1 |
| R5 | The same configuration files as Python, read the same way. `/usr/share/sonic/device/<platform>/system_health_monitoring_config.json`: `polling_interval`, `services_to_ignore`, `devices_to_ignore`, `include_devices`, `user_defined_checkers`, `led_color` and `optional_containers`; checked at the start of every check cycle and every sysmonitor service scan, and re-read when it changes; an invalid file means the defaults; without the file healthd exits at start with status 0, and `Restart=always` restarts it until the unit's start limit, as with Python. `/etc/monit/monitrc`: its `with start delay` sets how long a Not OK system shows the booting LED color (300s without it). No new files or settings. | P1 |
| R6 | Every command, Docker API call and platform API call after start has a 15s timeout; user-defined checks get the polling interval (60s by default). Building the vendor's chassis at start and Redis calls wait, as in Python. A timeout counts as that check failing, except that a container whose merged directory cannot be read in time is read again next cycle, as when `docker inspect` answers nothing; a platform API call that times out is abandoned, and the LED is left alone until it returns. A timed-out systemd call in sysmonitor keeps the unit's last status. | P1 |
| R7 | `cargo test` runs in the package build. | P2 |

R1 and R2 exclude the fixes in §5.

## 4. Design

```
                  system_health_monitoring_config.json, /etc/monit/monitrc
                                        │
 ┌────────────── healthd (Rust, on the host, one process, tokio) ──────────────┐
 │ checker loop (polling_interval, default 60s)                                │
 │   Hardware     ← STATE_DB TEMPERATURE/FAN/PSU/LIQUID_COOLING_INFO           │──► STATE_DB SYSTEM_HEALTH_INFO
 │   Services     ← monit, Docker API, supervisorctl, CONFIG_DB FEATURE        │──► status LED (platform API, PyO3)
 │   User-defined ← configured commands                                        │──► events
 │ sysmonitor                                                                  │──► STATE_DB ALL_SERVICE_STATUS|*,
 │   systemctl, systemd D-Bus job events, 15s rescan; STATE_DB FEATURE         │            SYSTEM_READY|SYSTEM_STATE
 └─────────────────────────────────────────────────────────────────────────────┘──► /dev/console "System is ready"

 show system-health ──exec──► healthcheck --json   (on the host; same checks; sets and reads the LED; no DB writes,
                                                    no events)
```

One cargo workspace, built into the one deb: the `system-health` library (config, checkers, LED, STATE_DB
publisher, sysmonitor), `healthd` (runs the checker loop and sysmonitor after the boot gate) and `healthcheck`. Both
binaries run on the host, not in a container. The checks and sysmonitor reach the system through traits, so their
logic is unit-tested with mocks. Crates come from crates.io, pinned by the committed `Cargo.lock`, as for the other
Rust packages of sonic-buildimage.

- **Hardware:** ASIC, fan, PSU and liquid-cooling rows from STATE_DB, with Python's thresholds and messages.
- **Services:** monit through `systemctl is-active monit.service` and `monit summary -B`. Expected containers come from
  CONFIG_DB FEATURE (`state` as written), running ones from the Docker API (bollard). For each running container, the
  critical processes are listed in its `/etc/supervisor/critical_processes`, read through the container's merged
  directory (`docker inspect`) on each start, with no cache file, and their states come from `docker exec <container>
  bash -c "supervisorctl status"`. A timed-out call fails all of the container's critical processes, each with a
  `process-not-running` event; otherwise only the processes it lists are judged.
- **User-defined checks:** the vendor commands in `user_defined_checkers`, from the platform's root-owned configuration
  file only, run through the shell each cycle, and their output (a category line, then `object:message` lines) is parsed
  as in Python. Used by BlueField (CPU and DDR throttling), Pensando and Supermicro.
- **LED:** through the platform API of sonic-platform-common, whose PyO3 bridge calls the vendor's `sonic_platform`
  inside the process. As the Python daemon does, `healthd` builds the chassis once at start (and exits without
  `sonic_platform`) and sets the LED every cycle; `healthcheck` sets, initializes and reads it, as the Python CLI
  does. The calls run on a thread of their own with the 15s timeout. A failed or abandoned call shows the LED as N/A;
  a call that never returns is logged once, the checks go on, and the LED is left as it is; `healthcheck` still
  answers, with the LED as N/A, after two timeouts (30s): the stuck call's, then the wait for it at exit, where the
  vendor's exit handlers are skipped, as when a process is killed.
- **Events:** `process-not-running` and `liquid-cooling-leak` from `sonic-events-host`. As in Python, a publisher is
  opened for each batch and closed after it.
- **Publisher:** `SYSTEM_HEALTH_INFO` is deleted and written anew every cycle (a reader can find it empty in between,
  as with Python), and deleted when healthd stops.
- **sysmonitor:** unit properties from `systemctl show`, unit changes from systemd's `JobRemoved` signal over D-Bus
  (zbus), and a full rescan every 15s, as in Python. `FEATURE.state` templates are rendered with minijinja and match
  jinja2.
- **Boot gate:** waits up to 180s for a warm or fast boot to finish, as swss `RestartWaiter`, using the swss-common
  crate. Warm and fast boot are otherwise unaffected: the unit starts where it did, and writes the same tables.
- **Syslog:** `healthd` for the checkers and sysmonitor, `healthd#utils` (facility DAEMON) for the helpers.
- **sonic-rs-common:** gains the boot gate, a `multi_asic` module and more `device_info` helpers.

**CLI contract.** `healthcheck --json` runs one check cycle and prints:

```json
{"led": "red",
 "stat": {"Hardware": {"PSU 1": {"type": "PSU", "status": "Not OK", "message": "PSU 1 is out of power"}}},
 "ignore": {"services": [], "devices": []}}
```

Exit codes: 0 the cycle ran, 1 no `system_health_monitoring_config.json` for the platform, 2 internal error. What the
checks print (an LED set failure, the vendor's own prints) goes to stderr. In sonic-utilities only
`get_system_health_status()` changes: it runs the binary with a 5-minute timeout, prints that stderr first, as the
in-process checks printed it, and the display code stays as is; `show system-health` needs root, as today. On an older
image without the binary it logs a notice and runs the Python `health_checker` in process, as today; without either it
reports the error.

## 5. Python bugs fixed, not ported

| Bug in Python | Rust |
|---|---|
| A leaking liquid-cooling sensor is reported in the first cycle only; then the summary and LED go back to OK while it leaks (sn6600_ld, sn6810_ld). A sensor with an unknown status drops out of the report. | Not OK every cycle while it leaks; one event per change. An ignored or missing sensor keeps its state, so its recovery is still reported. An unexpected status is Not OK. |
| Every `show system-health` run re-sends the leak and process-not-running events. | The CLI sends no events. |
| If the sysmonitor subscriptions are not up 60s after start, sysmonitor exits and `SYSTEM_READY` is never written. | Retried every 5s; sysmonitor keeps running. |
| Only `supervisorctl status` and the Docker API have a timeout; any other hung command stalls the loop. | Timeouts everywhere (R6). |
| The fan message says "target speed date". | "target speed data". |

## 6. Changes by repository

| Repository | Change |
|---|---|
| sonic-buildimage | Add `src/sonic-system-health-rs` and its rules: one deb, `sonic-system-health`, with `healthd` and `healthcheck`, installed in every image; `system-health.service` starts `/usr/bin/healthd`. Remove `src/system-health` (the Python daemon and `health_checker`) and its wheel; the telemetry sidecar stops shipping its copy of `service_checker.py`. `src/sonic-rs-common`: boot gate, `multi_asic`, `device_info`. Pin `src/sonic-platform-common` to a commit with the platform API. |
| sonic-utilities | `show/system_health.py` runs `healthcheck --json`; without the binary, the Python package as today. |

**Merge first.** The sonic-buildimage change depends on these:

1. The platform API facade and its PyO3 bridge, sonic-platform-common:
   https://github.com/sonic-net/sonic-platform-common/pull/768
2. The sonic-utilities change above: `show system-health` through `healthcheck`. It keeps the Python path where the
   binary is missing, so it can merge before the image change.

Out of scope: new checks, per-ASIC system-ready, YANG or CONFIG_DB changes.

## 7. Test

- **Unit:** `cargo test` with mocks, covering what the 65 Python tests cover, plus a test for each fix in §5 that the
  library makes.
- **Vendor data, against Python's results:** every vendor's `system_health_monitoring_config.json` (read as
  Python's `Config` reads it, LED colors included); each kind of vendor LED method (answers, None, False,
  `NotImplementedError`, other exceptions, slow calls) and every vendor LED color through the real PyO3 bridge and
  facade; the vendor check scripts' output (BlueField, Pensando, Supermicro).
- **Parity:** CLI output and STATE_DB on the same DUT, with the image before and after the change: healthy; PSU, fan and
  ASIC-temperature faults; process killed; container stopped; failing user-defined check; ignore lists;
  `system_health_monitoring_config.json` changed while running.
- **sonic-mgmt:** system health, sysready, PSU-threshold and liquid-leak tests, on a multi-ASIC and a single-ASIC
  platform.
- **Other vendors:** the vendor data tests run in every build. On their own hardware, vendors check
  `show system-health detail`, the LED, `SYSTEM_HEALTH_INFO` and a stopped critical process. Upstream PR CI builds
  the deb and runs its tests on amd64, arm64 and armhf. Its KVM tests skip system health, because the virtual
  platforms have no configuration file.

## 8. Risks → mitigations

- **No fallback, so a parity bug hits every platform** → the vendor data tests in every build, parity runs and
  sonic-mgmt before merge; rollback is one revert.
