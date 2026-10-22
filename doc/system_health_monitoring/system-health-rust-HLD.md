# healthd in Rust — 2-pager (brief HLD)

| | |
|---|---|
| Target version | SONiC 202705 |
| Status | Draft for review, 2026-11-13 |
| Python baseline | sonic-buildimage `src/system-health` at https://github.com/sonic-net/sonic-buildimage/tree/def99013c17eee6cc51f759fa24f5979ba2b6659/src/system-health · sonic-utilities `show/system_health.py` at https://github.com/sonic-net/sonic-utilities/blob/0dee3fbed13ce69c9766c8e4b931910210f31f82/show/system_health.py |
| Baseline HLDs | https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-health-HLD.md · https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-ready-HLD.md (outdated; the Python code is the reference) |

## 1. Motivation

Every SONiC system, switch, DPU or BMC, runs one healthd on its host at all times, in a fixed amount of RAM. The
saving is per system, not per ASIC. Measured on one image root with both daemons installed (SN5600 configuration, 60s
polling, simulated STATE_DB data), in steady state:

| Daemon | RSS | PSS | Anonymous PSS |
|---|---|---|---|
| Python | 78.1MB | 72.0MB | 51.8MB |
| Rust | 40.5MB | 38.3MB | 19.6MB |

About 27MB of the Rust daemon is the Python interpreter and the vendor's `sonic_platform`, loaded for the LED (D4).
Few pages are shared in that setup, so PSS is close to RSS; on a device, pages shared with other processes (libpython
among them) lower the PSS of both. On devices the Rust daemon holds 42-43MB RSS on switches, 48MB on a BMC and 50MB on
DPUs; PSS on the same devices, before and after, is still to be measured.

## 2. Decisions

- **D1.** The daemon is rewritten in Rust for every platform. The Python daemon and its `health_checker` package are
  removed from the image. No runtime switch, no Python fallback in the image.
- **D2.** One deb, `sonic-system-health`, holds the daemon `healthd` and the CLI utility `healthcheck`. Both run on
  the host, not in a container. `show system-health` stays in sonic-utilities; it runs `healthcheck --json` and
  renders its output. The two share one Rust library, so the checks are written once. The other Rust debs end in `-rs`
  because their Python packages (the `sonic_ctrmgrd`, `sonic_supervisord_utilities` and `sonic_host_services` wheels)
  are still built beside them; this change removes the Python system health package, so the deb takes the plain name
  (its build rules are `rules/sonic-system-health-rs.mk`).
- **D3.** External interfaces stay the same: STATE_DB tables and fields, the config files
  `system_health_monitoring_config.json` and `/etc/monit/monitrc` (R5), CLI output, the `system-health.service` unit
  (`ExecStart` changes, and the cache directory goes, D6), syslog identifiers and events.
- **D4.** Every check reads the system the way the Python daemon does: the Docker API, `supervisorctl`, `systemctl`,
  `monit`, and for the LED the vendor's `sonic_platform`, called in process through the platform API of
  sonic-platform-common and its PyO3 bridge. Vendors change nothing.
- **D5.** Python bugs that cause a real fault are fixed, not ported. §5 lists every behavior that differs from Python.
- **D6.** No critical-process cache. Python saves each container's critical-process list in
  `/var/cache/sonic/system-health/critical_process_cache` and loads it at start, and the CLI uses the list the daemon
  saved. healthd keeps the lists in memory and reads each container's `critical_processes` once per run, so after a
  restart it reads the current files; `healthcheck` reads them on each run (one `docker inspect` and one file read per
  container, plus one `supervisorctl status` for each container with `group:` lines). The cache file, `CacheDirectory=`
  in the unit and the directory in the image go.

## 3. Requirements

| ID | Requirement | Pri |
|---|---|---|
| R1 | Same results as Python at the baseline for the Services, Hardware and user-defined checks: object names, messages, `summary`. | P1 |
| R2 | Same system-ready as Python at the baseline: `ALL_SERVICE_STATUS`, one global `SYSTEM_READY\|SYSTEM_STATE`, console message. | P1 |
| R3 | LED as in Python: normal color when OK; when Not OK, booting color during monit's start delay, then fault color. Set every daemon cycle and every CLI run. | P1 |
| R4 | `show system-health summary\|detail\|monitor-list` output is unchanged. | P1 |
| R5 | The same configuration files as Python, with the same keys and defaults. `/usr/share/sonic/device/<platform>/system_health_monitoring_config.json`: `polling_interval`, `services_to_ignore`, `devices_to_ignore`, `include_devices`, `user_defined_checkers`, `led_color` and `optional_containers`; checked at the start of every check cycle and every sysmonitor service scan, and re-read when it changes; an invalid file means the defaults; without the file healthd exits at start with status 0, and `Restart=always` restarts it, as with Python. `/etc/monit/monitrc`: its `with start delay` sets how long a Not OK system shows the booting LED color (300s without it; §5 has two cases where Python's value differs). No new files or settings. | P1 |
| R6 | Every command, Docker API call and platform API call after start has a 15s timeout; user-defined checks get the polling interval, but at least 60s. Building the vendor's chassis at start and Redis calls wait, as in Python. A timeout counts as that check failing, except that a container whose merged directory or `group:` members cannot be read in time is read again next cycle, as when `docker inspect` answers nothing; a platform API call that times out is abandoned, and the LED is left alone until it returns. A timed-out systemd call in sysmonitor keeps the unit's last status. The result of each timeout is in §4. | P1 |
| R7 | `cargo test` runs in the package build. | P2 |

R1, R2 and R4 exclude the differences in §5. Until the image change merges, every change to the Python baseline is
ported into it, and the baseline moves with it.

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
  directory (`docker inspect`) once per run (D6), and their states come from `docker exec <container> bash -c
  "supervisorctl status"`. A `group:<name>` line stands for the members of that supervisord group, taken from one
  `supervisorctl status` when the file is read. If that gives no member (supervisord still starting, or an empty group,
  such as dhcp_relay's `dhcp-relay` with no DHCP relay VLANs), the list is not kept and is read again next cycle, as in
  Python, so members added later are checked; its "no processes" warning is logged once per container while that lasts,
  not every cycle (§5). A timed-out call fails all of the container's critical processes, each with a
  `process-not-running` event; otherwise only the processes it lists are judged. When the Docker container list fails or
  times out, no container is known to run or to be stopped: the cycle reports one Not OK object, `docker`, and no result
  per container, only the `critical_processes` syntax errors already known (§5).
- **User-defined checks:** the vendor commands in `user_defined_checkers`, from the platform's root-owned configuration
  file only, run through the shell each cycle, and their output (a category line, then `object:message` lines) is parsed
  as in Python. Used by BlueField (CPU and DDR throttling), Pensando and Super Micro.
- **LED:** through the platform API of sonic-platform-common, whose PyO3 bridge calls the vendor's `sonic_platform`
  inside the process. As the Python daemon does, `healthd` builds the chassis once at start (and exits without
  `sonic_platform`) and sets the LED every cycle; `healthcheck` sets, initializes and reads it, as the Python CLI
  does. The calls run on a thread of their own with the 15s timeout. A failed or abandoned call shows the LED as N/A;
  a call that never returns is logged once, the checks go on, and the LED is left as it is; `healthcheck` still
  answers, with the LED as N/A, after two timeouts (30s): the stuck call's, then the wait for it at exit, where the
  vendor's exit handlers are skipped, as when a process is killed.
- **Platform load failure:** without `sonic_platform`, healthd logs Python's warning and exits, as Python does. When
  `sonic_platform` is there but the vendor's chassis fails to load, healthd and `healthcheck` log the error and run the
  checks without the LED, which reads as N/A: only the LED needs the platform (§5).
- **Embedded Python:** the deb builds against `python3-dev` and links the image's libpython (3.13 today), so a Python
  version change in the image needs the deb rebuilt; the build container is in the deb's cache key, so a new one
  rebuilds it. healthd builds the chassis on its main thread, as Python does, because vendor code can install signal
  handlers then (the Mellanox `Chassis` does). Stopped on a signal, healthd runs the vendor's SIGTERM handler, then
  the interpreter's exit (`atexit`) handlers; on an error exit only the exit handlers. When a stuck call holds the
  platform thread past the stop's 15s limit, they are skipped.
- **Events:** `process-not-running` and `liquid-cooling-leak` from `sonic-events-host`. As in Python, a publisher is
  opened for each batch and closed after it. No YANG model defines `liquid-cooling-leak` (`sonic-events-host.yang` has
  `process-not-running` only); the gap predates this change (§9).
- **Publisher:** `SYSTEM_HEALTH_INFO` is deleted and written anew every cycle (a reader can find it empty in between,
  as with Python), and deleted when healthd stops.
- **Redis errors:** healthd's connections are opened once and its CONFIG_DB reads do not reconnect, and a restarted
  Redis has lost what healthd wrote, `SYSTEM_READY` among it. So when a Redis call fails and the same call does not
  fail on a new connection too (the connection was lost, or Redis is down), healthd does not act on that cycle or scan
  (no LED, no `SYSTEM_HEALTH_INFO`, no system state or console message), exits with status 1, and systemd
  (`Restart=always`) starts it again, waiting for Redis; the new process writes `SYSTEM_HEALTH_INFO` anew, and
  `SYSTEM_READY` once the system is up, as at boot. An error that a new connection gets too comes from the data (a key
  of the wrong type, for instance): it is reported in the results, and healthd goes on, as Python did. `healthcheck`
  reports any Redis error in its results, as the Python CLI did.
- **sysmonitor:** unit properties from `systemctl show`, unit changes from systemd's `JobRemoved` signal over D-Bus
  (zbus), and a full rescan every 15s, as in Python. `FEATURE.state` templates are rendered with minijinja and match
  jinja2.
- **Boot gate:** waits up to 180s for a warm or fast boot to finish, as swss `RestartWaiter`, using the swss-common
  crate (§10).
- **Syslog:** `healthd` for the checkers and sysmonitor, `healthd#utils` (facility DAEMON) for the helpers.
- **sonic-rs-common:** gains the boot gate, a `multi_asic` module and more `device_info` helpers.

**Timeouts (R6).** What each one gives:

| Call (limit) | Result |
|---|---|
| `systemctl is-active monit.service` (15s) | Service `monit` Not OK: "monit service is not running". |
| `monit summary -B` (15s) | Service `monit` Not OK: "monit service is not ready". |
| Docker container list (15s) | Service `docker` Not OK: "Failed to retrieve the running container list"; no result per container that cycle. |
| Docker image check of an optional container (15s) | The container is not expected that cycle. |
| `docker inspect` for the merged directory (15s) | The container's processes are not judged that cycle; read again next cycle. |
| `supervisorctl status` in a container (15s) | Each critical process Not OK: "Process '<process>' in container '<container>' is not running", with a `process-not-running` event each. |
| `supervisorctl status` for a `group:` line (15s) | The container's processes are not judged that cycle; read again next cycle. |
| User-defined command (polling interval, at least 60s) | `UserDefine` object `UserDefinedChecker - <command>` Not OK: "Failed to get output of command "<command>"". |
| Platform API call (15s) | The CLI shows the LED as N/A; healthd leaves the LED until the call returns. |
| `systemctl show` in sysmonitor (15s) | The unit keeps its last status. |
| D-Bus connection and subscription of sysmonitor (15s) | Retried after 5s; the 15s rescans go on. |

**CLI contract.** `healthcheck --json` runs one check cycle and prints:

```json
{"led": "red",
 "stat": {"Hardware": {"PSU 1": {"type": "PSU", "message": "PSU 1 is out of power", "status": "Not OK"}}},
 "ignore": {"services": [], "devices": []}}
```

Exit codes: 0 the cycle ran, 1 no `system_health_monitoring_config.json` for the platform, 2 not run as root, or an
internal error; like `show system-health`, `healthcheck` needs root. What the checks print (an LED set failure, the
vendor's own prints) goes to stderr. The order of the keys is part of the output: categories and their objects keep the
order in which the checks add them, as in Python, because `display_system_health_summary()` prints the reasons in
reverse insertion order and `display_monitor_list()` sorts by status only, with a stable sort. Containers that are not
running come in name order (Python's came in the order of a set, which changes from one process to the next). The
`ignore` lists keep the configuration file's order, without duplicates (Python's sets give an order that changes from
one process to the next). There is no version field: `healthcheck` and `show system-health` ship in the same image. In
sonic-utilities only how `get_system_health_status()` gets its data changes: it runs the binary with no overall time
limit, as the in-process checks had none (each call inside has its own, R6); it prints that stderr first, as the
in-process checks printed it, and the display code stays as is; on exit 1 it prints the binary's message and exits 1, as
the in-process check did. `show system-health` needs root, as today. On an older image without the binary it logs a
notice and runs the Python `health_checker` in process, as today; without either it reports the error.

## 5. Differences from Python

| Case | Python (baseline) | Rust |
|---|---|---|
| `show system-health` while a sensor leaks, or while `supervisorctl status` times out in a container | Every run re-sends the leak and process-not-running events. | The CLI sends no events. |
| The sysmonitor subscriptions are not up 60s after start | sysmonitor exits, and `SYSTEM_READY` is never written. | Retried every 5s; sysmonitor keeps running. |
| A sysmonitor subscription fails later (systemd D-Bus or STATE_DB FEATURE) | That monitor thread logs the error and ends; its events are not seen again. | Resubscribed after 5s (the error is logged at most every 10 minutes). |
| healthd stops while a sysmonitor scan is in progress | The stop waits for the scan. | The scan is dropped; the stop goes on. |
| A command other than `supervisorctl status` hangs | No timeout; the loop stalls. | Timeouts everywhere (R6). |
| The Docker container list fails or times out | An HTTP error gives every expected container "not running". A timeout (docker-py's 60s) raises outside the checker's `APIError` handler: one `Internal` entry and no Services results. | One Service object, `docker`: "Failed to retrieve the running container list", within 15s; no result per container. |
| The Docker image check of an optional container times out | The timeout raises outside the checker's handler: one `Internal` entry and no Services results. | The container is not expected that cycle. |
| A `group:` line gives no process, every cycle (an empty group) | The "no processes" warning every cycle. | That warning once per container, until the group has members or the container is no longer running. Both read the group again every cycle. |
| A Redis connection is lost, for example when Redis restarts | The checks fail; the next STATE_DB write raises in the daemon's main loop, which ends, but sysmonitor's thread keeps the process up: no health check runs any more, and systemd does not restart it. | healthd exits at once, without acting on that cycle, and systemd restarts it with new connections. |
| `sonic_platform` is installed, but the chassis fails to load | The daemon stops with the exception; systemd restarts it, and it fails again. The CLI fails with a traceback. | healthd and `healthcheck` log the error and run the checks without the LED (N/A). |
| A user-defined command takes long | No limit; the loop waits for it. | The polling interval, but at least 60s; then "Failed to get output of command ...". |
| A sysmonitor read fails for a systemd event | The unit counts as masked: its entry is deleted, and the system can be reported ready. | The unit keeps its last status. |
| `monitrc` has `with start delay 120` with no comment after it | `line[:pos]` with `pos = -1` drops the last digit: 12s. | 120s. |
| `monitrc` has no `with start delay` | `uptime < None` raises `TypeError`, so the LED is not set while the system is Not OK. | 300s. |
| `polling_interval` is not a number | The main loop ends with `TypeError` after its first cycle; as in the Redis row, sysmonitor's thread keeps the process up, so no health check runs any more and systemd does not restart it. | The default, 60s. |
| `polling_interval` is too large to wait for | The wait raises `OverflowError`; the main loop ends, and the process stays up as in the Redis row. | The longest wait there is. |
| The LED cannot be set (the vendor's method raises) | "Failed to set system led due to - " and the exception's `repr()`, for example `OSError('...')`. | The same text with the exception's message only: the platform API passes no exception type. |
| A checker fails (an `Internal` entry) | "Failed to perform health check for <checker> due to exception - " and the exception's `repr()`. | The same text with the error's message. |
| When sysmonitor first scans | After its systemd and FEATURE subscriptions are up (it waits up to 60s). | At once; a unit job that ends before the subscriptions are up is found by the next 15s rescan. |
| How the CLI builds the chassis | `sonic_platform.chassis.Chassis()` | `Platform().get_chassis()`, as the daemon does; on Mellanox, `Platform()` builds `SmartSwitchChassis` or `ModularChassis` where they apply. |
| The CLI's `get_status_led()` raises | A traceback. | The LED shows as N/A. |
| The critical-process list | Saved in a cache file; the CLI uses the daemon's list. | Read once per healthd run, and on each CLI run (D6). |
| The fan message | "target speed date" | "target speed data" |

## 6. Changes by repository

| Repository | Change |
|---|---|
| sonic-buildimage: https://github.com/sonic-net/sonic-buildimage/pull/30514 | Add `src/sonic-system-health-rs` and its rules: one deb, `sonic-system-health`, with `healthd` and `healthcheck`, installed in every image; `system-health.service` starts `/usr/bin/healthd` and has no cache directory (D6). Remove `src/system-health` (the Python daemon and `health_checker`) and its wheel; the telemetry sidecar stops shipping its copy of `service_checker.py`. `src/sonic-rs-common`: boot gate, `multi_asic`, `device_info`. |
| sonic-utilities: https://github.com/sonic-net/sonic-utilities/pull/5015 | `show/system_health.py` runs `healthcheck --json`; without the binary, the Python package as today. |

**Merge first.** The sonic-buildimage change depends on these:

1. The platform API facade and its PyO3 bridge, sonic-platform-common:
   https://github.com/sonic-net/sonic-platform-common/pull/768. Merged on 2026-10-30; the sonic-buildimage master pin
   of `src/sonic-platform-common` has it.
2. The sonic-utilities change: https://github.com/sonic-net/sonic-utilities/pull/5015. It keeps the Python path where
   the binary is missing, so it can merge first; the image change merges once the `src/sonic-utilities` pin includes
   it.

Out of scope: new checks, per-ASIC system-ready, YANG or CONFIG_DB changes.

## 7. Test

- **Unit:** `cargo test` with mocks, covering what the Python tests at the baseline cover (`src/system-health/tests`),
  plus a test for each difference in §5 that the library makes.
- **Vendor data, against Python's results:** every vendor's `system_health_monitoring_config.json` (read as
  Python's `Config` reads it, LED colors included); each kind of vendor LED method (answers, None, False,
  `NotImplementedError`, other exceptions, slow calls) and every vendor LED color through the real PyO3 bridge and
  facade; the vendor check scripts' output (BlueField, Pensando, Super Micro).
- **Parity:** CLI output and STATE_DB on the same DUT, with the image before and after the change: healthy; PSU, fan and
  ASIC-temperature faults; process killed; container stopped; failing user-defined check; ignore lists;
  `system_health_monitoring_config.json` changed while running.
- **sonic-mgmt:** system health, sysready, PSU-threshold and liquid-leak tests, on a multi-ASIC and a single-ASIC
  platform.
- **Other vendors:** the vendor data tests run in every build. During the review period (§8), vendors are asked to check
  on their own hardware `show system-health detail`, the LED, `SYSTEM_HEALTH_INFO` and a stopped critical process.
  Upstream PR CI builds the deb and runs its tests on amd64, arm64 and armhf. Its KVM tests skip system health, because
  the virtual platforms have no configuration file.

## 8. Risks → mitigations

- **No fallback, so a parity bug hits every platform** → the vendor data tests in every build, parity runs and
  sonic-mgmt before merge. The authors announce the change in the Platform WG once the image change is approved;
  vendors get at least four weeks to check it on their hardware before it merges, and before the 202705 branch. A
  revert of the image change, on master and on the release branch, undoes it only until the first follow-up change to
  the Rust code.
- **The platform API bridge runs vendor code in an embedded interpreter, a first in production, on every platform at
  once** → the bridge test calls each kind of vendor LED method through the real bridge and facade; a vendor platform
  that fails to load costs only the LED (§4); the vendors' review period above.

## 9. Restrictions and limitations

- `liquid-cooling-leak` has no YANG model, as before this change.
- `SYSTEM_HEALTH_INFO` is deleted and rewritten every cycle, as in Python, so a reader can find it empty or partial in
  between. Writing it in one `MULTI`/`EXEC` transaction would close that window; it is not part of this change.

## 10. Warm and fast boot impact

`system-health.service` starts where it did. healthd waits for a warm or fast boot to finish (boot gate, up to 180s),
as the Python daemon does, before it checks or writes anything, and then writes the same tables. Nothing in the warm or
fast boot path waits for healthd, so their timing does not change.
