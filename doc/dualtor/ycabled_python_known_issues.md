# ycabled in Rust, appendix B: known issues of Python ycabled

This appendix to [ycabled in Rust](ycabled_to_rust_hld.md) is its Sections 3.7 and 3.8: the issues found in Python ycabled, and improvements to its design.

## Content

- [ycabled in Rust, appendix B: known issues of Python ycabled](#ycabled-in-rust-appendix-b-known-issues-of-python-ycabled)
  - [Content](#content)
  - [3.7 Known issues](#37-known-issues)
    - [3.7.1 Found by reading the code](#371-found-by-reading-the-code)
    - [3.7.2 Found by the black-box tests](#372-found-by-the-black-box-tests)
    - [3.7.3 State the threads share](#373-state-the-threads-share)
    - [3.7.4 Found by reviewing the unit tests](#374-found-by-reviewing-the-unit-tests)
    - [3.7.5 Cable insertion and removal after startup](#375-cable-insertion-and-removal-after-startup)
    - [3.7.6 Tests that reproduce the issues](#376-tests-that-reproduce-the-issues)
  - [3.8 Current design improvements](#38-current-design-improvements)

## 3.7 Known issues

Issues keep their numbers in the tables below, which group them by how they were found ([Sections 3.7.1](#371-found-by-reading-the-code) to [3.7.4](#374-found-by-reviewing-the-unit-tests)) or, for cable changes after startup, by trigger ([Section 3.7.5](#375-cable-insertion-and-removal-after-startup)). ycabled-rs has the fixes ([Section 4.5](ycabled_to_rust_hld.md#45-deliberate-behavior-differences)); whether Python gets them is open question 4 ([Section 9](ycabled_to_rust_hld.md#9-open-questions)).

Each table lists its issues by priority:

- **P0:** ycabled stops serving every port (it exits, restarts in a loop or deadlocks) after a trigger that occurs in normal operation: a cable error, a state orchagent writes, or a missing TLS file. Issues 17, 18, 20 and 24.
- **P1:** a port gets a wrong state or is not served; or every port is, but only after an uncommon trigger (a misconfiguration, an unusual CLI command, a cable or `MUX_CABLE` change after startup); or the logs that tests rely on are wrong. Issues 2, 3, 5, 15, 16, 19, 21, 26 to 28 and 30 to 32.
- **P2:** no effect on toggles, probes or the state of a working port. The other 15 issues.

### 3.7.1 Found by reading the code

| # | Priority | Issue | Where | Impact | Proposal |
| :---: | :---: | --- | --- | --- | --- |
| 2 | P1 | The syslog identity changes with import order. `openlog` is process-wide, and any module that creates a `Logger` later replaces `ycable`; for example `sonic_platform_base/bmc_base.py`. | `sonic_py_common` logger | ycabled messages appear as `pmon#bmc_base`, and sonic-mgmt's `pmon#ycable` ignore rules do not match them | Rust uses a fixed identity. Raise the problem separately for the Python daemons. |
| 3 | P1 | `logical_port_name` undefined in an error path | `get_muxcable_info_for_active_active` | `NameError` ends the telemetry thread, and the process is killed within 60 s, after every restart while the port has no SoC address | Fix in Python |
| 1 | P2 | SIGTERM never completes. `run()` joins worker threads whose stop events are never set. | `ycable.py` `run()` | Every stop waits until supervisord or the container kills the process. `deinit()` never runs. | Rust exits in ≤ 2 s and keeps the tables (C7). A Python fix must keep them too, so it cannot simply let `deinit()` run. |
| 4 | P2 | `peer_eye_height_lane2` is written from lane 1 | `post_port_mux_info_to_db` | Wrong telemetry value | Fix in Python |
| 6 | P2 | `break` instead of `continue` for a port that is not active-active | `YCableTableUpdateTask` | None observed. The entries after that port stay in the subscriber's buffer, and are handled one more pass of the loop later: swsscommon's `Select` keeps a subscriber with more than one entry pending in its ready set, so the next `select()` returns it at once. | Fix in Python |
| 7 | P2 | `auth_level` values differ: `server` or `client` in YANG, `server` or `mutual` in the code | `get_grpc_credentials`, `sonic-grpcclient.yang` | Mutual TLS needs a value YANG rejects | Align the two ([Section 9](ycabled_to_rust_hld.md#9-open-questions)) |
| 8 | P2 | `XCVRD_LOG\|Y_CABLE.disable_telemetry` is missing from YANG | `sonic-xcvrd-log.yang` | YANG validation rejects what `config muxcable telemetry` writes | Add it to the YANG model |
| 9 | P2 | The global `GRPC_CLIENT_OPTIONS` list gets another target-name override for every secure channel, and insecure channels are created with it too | `create_channel` | The option list grows with the number of channels. No other effect is observable, because every secure channel has the same target name and insecure channels ignore it. | Fix in Python |
| 10 | P2 | `XCVRD_DOWN_FW_STATUS_CMD` is in the select set but never popped, and nothing writes it | `YcableCliUpdateTableHelper`, `YCableCliUpdateTask` | Dead. A write would make select return it on every call. | Remove |
| 11 | P2 | Dead code: `setup_grpc_channels` has no caller, and `hook_grpc_nic_simulated` uses undefined names | `y_cable_helper.py` | | Remove |
| 12 | P2 | 27 tests never run because of duplicate names | `tests/` | Lost coverage | Rename |
| 13 | P2 | 124 Redis connections on a 24-port KVM DUT; 166 with 16 active-active ports in the black-box tests | measured | The count grows with the number of active-active ports | Rust: bounded (N5). Attribute the Python count on a physical testbed. |
| 14 | P2 | `nice -n -20` fails: "cannot set niceness: Permission denied" | supervisord log, KVM | The intended high priority is not applied, at least on KVM | Check on hardware |

### 3.7.2 Found by the black-box tests

Issues 18 and 24 also occur when a cable is inserted after startup.

| # | Priority | Issue | Where | Impact | Proposal |
| :---: | :---: | --- | --- | --- | --- |
| 17 | P0 | An active-standby toggle request with a state other than `active` or `standby` | `y_cable_helper.py` `toggle_mux_direction` | orchagent writes `init` after a failed first switch; `TypeError` ends the toggle thread | Ignore other states, as for active-active |
| 18 | P0 | An exception from a vendor driver's constructor is not caught | `check_identifier_presence_and_update_mux_table_entry` | ycabled exits at startup; at insertion the thread dies | Fix in Python |
| 20 | P0 | A secure `GRPCCLIENT` config that yields no channel (missing file, target name or client key) gives the GracefulRestart task a `None` channel | `YCableAsyncNotificationTask` | The task dies and the process is killed within 60 s, after every restart | Fix in Python |
| 24 | P0 | After a `get_vendor()` exception, the port lock is taken again while it is held | `check_identifier_presence_and_update_mux_table_entry` → `read_y_cable_and_update_statedb_port_tbl` | Startup deadlocks: no port is published or served, while supervisord sees a running process. A transient EEPROM error at boot is enough. At insertion, the insertion thread deadlocks instead, and no later insertion or removal of any port is handled. | Fix in Python |
| 19 | P1 | `config muxcable firmware rollback` for a port without a driver takes a lock that does not exist | `handle_config_firmware_roll_cmd_arg_tbl_notification` | After answering, `KeyError` ends the CLI thread | Fix in Python |
| 23 | P2 | Multi-ASIC: namespace connections are opened before `SonicDBConfig.initializeGlobalConfig()`, and the default namespace `''` is resolved to an ASIC index | `ycable.py` `DaemonYcable.__init__`; `apply_grpc_secrets_configuration`, `wait_for_state_change`, `process_loopback_interface_and_get_read_side` and `delete_ports_status_for_y_cable` | ycabled cannot start on a multi-ASIC platform | Rust keeps the namespaces; fix Python only if multi-ASIC dual ToR is planned |
| 25 | P2 | `XCVRD_LOG` changes are handled as key `Y_CABLE`, whatever their key | `YCableCliUpdateTask` | The fields of any `XCVRD_LOG` key set the log level and the telemetry flag | Fix in Python |

### 3.7.3 State the threads share

Found by a review of the state ycabled's threads share. Issues 27 to 29, found by the same review, are in [Section 3.7.5](#375-cable-insertion-and-removal-after-startup).

| # | Priority | Issue | Where | Impact | Proposal |
| :---: | :---: | --- | --- | --- | --- |
| 26 | P1 | Active-standby toggles and probes call the cable without the port lock, which insertion, telemetry and the CLI take | `y_cable_toggle_mux_torA`, `y_cable_toggle_mux_torB` and `toggle_mux_tor_direction_and_update_read_side` (toggle), `update_appdb_port_mux_cable_response_table` (probe) | A toggle or probe interleaves its cable access with another thread's call to the same cable, unless the vendor driver serializes them itself | Rust: the port actor ([Section 4.3.3](ycabled_to_rust_hld.md#433-router-and-port-actors)). Python: take the port lock in toggles and probes. |

### 3.7.4 Found by reviewing the unit tests

Found by a review of the unit tests against the code.

| # | Priority | Issue | Where | Impact | Proposal |
| :---: | :---: | --- | --- | --- | --- |
| 30 | P1 | Without a usable Loopback3 address, read_side is -1, and active-active toggles still go to the SoC: `portid=[-1]` for this ToR, `[2]` for the peer | `handle_hw_mux_cable_table_grpc_notification` | The SoC gets port ids that name neither side. A SoC that indexes its port list with them toggles the wrong side, or fails. | Do not call the SoC; answer `unknown` |
| 31 | P1 | An active-standby cable read from the NIC side (read side 0) is published and probed as `standby`, but a toggle treats the read side as invalid and writes `unknown`. A probe also answers `standby` when the read side could not be read (-1). | `read_y_cable_and_update_statedb_port_tbl`, `update_appdb_port_mux_cable_response_table` | Neither read side tells which ToR this is, so the state answered is a guess, and the paths disagree | `unknown` on every path |
| 32 | P1 | A `MUX_CABLE` state outside the YANG enum (auto, manual, detach, active, standby) makes `check_mux_cable_port_type` return `None` instead of a tuple | `check_mux_cable_port_type` and its callers | Every caller dies unpacking it: at startup ycabled exits, and supervisord restarts it into the same failure. YANG validation keeps such values out, except for writes that bypass it. | Skip the port with a warning |

### 3.7.5 Cable insertion and removal after startup

These issues only occur when a cable is inserted or removed, or a `MUX_CABLE` entry changes, after ycabled has started; issues 18 and 24 ([Section 3.7.2](#372-found-by-the-black-box-tests)) occur then too. Without such changes they are rare: xcvrd deletes `TRANSCEIVER_INFO` only when the platform reports the transceiver removed, when the port is removed from CONFIG_DB, or when it starts and finds the transceiver absent, and it keeps the table when it restarts. Whether Python must handle these changes is open question 10 ([Section 9](ycabled_to_rust_hld.md#9-open-questions)). Issue 5 was found by reading the code, 15, 16, 21 and 22 by the black-box tests, and 27 to 29 by the review of the state the threads share.

| # | Priority | Issue | Where | Impact | Proposal |
| :---: | :---: | --- | --- | --- | --- |
| 5 | P1 | STATE_DB `HW_MUX_CABLE_TABLE` keys are read once when the toggle thread starts | `YCableTableUpdateTask` | Toggles and probes for ports that get an entry later are dropped until restart. Initialization writes an entry for every mux port it initializes, but it skips a port whose `MUX_CABLE` entry has no `state`, which YANG defaults to `auto`. If the state is set later, the next insertion of that cable initializes the port, and its requests are then dropped. | Fix in Python |
| 15 | P1 | The first `TRANSCEIVER_INFO` event without fields (a DEL, or a SET whose row is already gone) uses `fvp_dict` before it is assigned | `ycable.py` `YcableStateUpdateTask.task_worker` | `UnboundLocalError` ends the thread, and the process is killed within 60 s. A later event without fields reuses the previous event's `fvp_dict`; that has no effect, because the handler does not use it. | Fix in Python |
| 16 | P1 | The toggle, probe and CLI threads start only if a cable initialized at startup | `ycable.py` `run()` | Cables inserted later are initialized but never toggled, probed or served until restart | Fix in Python |
| 21 | P1 | A re-inserted active-active cable keeps its channel and returns early | `check_identifier_presence_and_setup_channel` | `HW_MUX_CABLE_TABLE` stays `unknown` until the next toggle | Query the SoC again |
| 27 | P1 | The toggle thread and the insertion and removal thread write a port's `HW_MUX_CABLE_TABLE` entry in no defined order; each calls the cable, then writes | `YCableTableUpdateTask` (toggle), `read_y_cable_and_update_statedb_port_tbl` (insertion), `check_identifier_presence_and_delete_mux_table_entry` (removal) | A toggle that finishes after a removal leaves `active` or `standby` for a cable that is gone. An insertion that read the direction before a toggle overwrites the toggle's result, so the entry disagrees with the cable. Most likely when a cable is pulled, which can bring a removal and a toggle at once. | Rust: the port actor. Python: hold the port lock from the cable call to the write, removal included. |
| 28 | P1 | Insertion publishes the driver before `get_vendor()` verifies it and before it creates the port lock, and replaces the lock of a port that had one | `check_identifier_presence_and_update_mux_table_entry` | Toggles can go through a driver that is then rejected. A thread that still holds the old lock overlaps the insertion's calls. For a port without a lock, telemetry or the CLI would hit `KeyError` between the two steps, which ends the thread and gets the process killed within 60 s; no test reproduces this, as no call holds that moment open. | Rust: the port actor. Python: create each port's lock once, and publish the driver after the check. Removal already leaves the lock in place: its check for a driver runs after the driver has been dropped. |
| 22 | P2 | Removing a port that has no `HW_MUX_CABLE_TABLE` entry (active-active without a SoC address) | `check_identifier_presence_and_delete_mux_table_entry` | Creates the entry with `read_side` `None` | Fix in Python |
| 29 | P2 | Telemetry and the CLI fetch the driver once, then keep calling it after the cable's removal has been handled | `get_muxcable_info`, CLI handlers | Calls go to a cable that is gone, and telemetry can write `MUX_CABLE_INFO` for it | Rust: the port actor. Python: look the driver up for each call, under the port lock. |

### 3.7.6 Tests that reproduce the issues

The black-box tests ([Section 6.3](ycabled_to_rust_hld.md#63-black-box-component-tests)) that reproduce these issues, by test file in `sonic-ycabled/blackbox/tests`. Each test describes its issue in its `known_issue` reason and docstring, without referring to this document.

| Test file | Issue: test |
| --- | --- |
| `test_lifecycle.py` | 1 `test_sigterm_exits_promptly`, 2 `test_syslog_identity`, 32 `test_mux_cable_state_outside_yang_enum` |
| `test_active_standby.py` | 17 `test_toggle_to_other_state_is_ignored`, 18 `test_driver_constructor_failure`, 24 `test_get_vendor_failure`, 31 `test_read_side_nic` |
| `test_active_active.py` | 7 `test_tls_auth_level_client`, 20 `test_tls_misconfiguration_keeps_running`, 30 `test_no_toggle_without_read_side`; requirements N1 `test_slow_soc_does_not_delay_other_ports`, N3 `test_parallel_startup_with_unreachable_socs` |
| `test_insert_remove.py` | 5 `test_port_initialized_after_startup_is_served`, 15 `test_first_transceiver_event_without_fields`, 16 `test_first_cable_inserted_after_startup`, 21 `test_reinsert_active_active_refreshes_state`, 22 `test_remove_port_without_state` |
| `test_telemetry.py` | 3 `test_active_active_port_without_soc_address`, 4 `test_peer_eye_height_lane2` |
| `test_cli.py` | 19 `test_rollback_firmware_without_driver` |
| `test_config.py` | 13 `test_redis_connections_bounded`, 25 `test_log_verbosity_other_key_is_ignored` |
| `test_multi_asic.py` | 23 `test_multi_asic` |
| `test_concurrency.py` | 26 `test_toggle_waits_for_call_in_progress`; 27 `test_removal_during_toggle_leaves_unknown`, `test_toggle_during_insertion_keeps_cable_direction`; 28 `test_no_toggle_through_unverified_driver`, `test_insertion_waits_for_call_in_progress`; 29 `test_no_cable_calls_after_removal` |

## 3.8 Current design improvements

These are improvement candidates for the current Python daemon, independent of the Rust port. They complement the concrete bugs in [Section 3.7](#37-known-issues); implementing all of them in Python is not a prerequisite for the port.

| Improvement | Proposed change | Safeguard |
| --- | --- | --- |
| Ready-table dispatch instead of table scans | Register each subscription with its ASIC and handler, then dispatch only the ready table. Use one registry for registration and dispatch rather than separate lists of subscriptions and `pop()` blocks ([Section 4.3.2](ycabled_to_rust_hld.md#432-db-access)). | Preserve startup replay, pending events, namespace isolation and fairness between ready tables. |
| Use the main thread for coordination | Replace the mostly idle liveness loop with lightweight event dispatch, timer scheduling and supervision. Consolidate redundant listener threads where practical. | Isolate blocking work first. Do not run a full telemetry sweep or firmware operation inline; preserve signal handling, worker-failure detection and the active-active asyncio notification loop. |
| Isolate slow work by port | Use asynchronous RPCs or a bounded worker pool instead of serial operations across all ports or a new thread for each firmware request. Schedule telemetry separately from latency-sensitive toggles and probes. | Preserve per-port ordering and driver locks. Test slow-port isolation and pool saturation; adding a pool alone does not guarantee either. |
| Reuse DB access infrastructure | Consolidate table helpers and reuse read/write connectors per DB and namespace where safe, rather than duplicating them for every task. | Keep subscriber-owned connections required by swsscommon. Do not share a connector across threads without a defined ownership or serialization model; measure the actual connection reduction. |
| Structured shutdown and supervision | Stop accepting work, signal every worker, cancel asynchronous streams and use bounded waits with explicit failure reporting. Surface worker failures promptly instead of waiting for the 60 s health check. | Keep DB tables on exit (C7). A vendor call cannot be forcibly cancelled inside a Python thread; retain supervisor/watchdog handling for stuck calls. |
| Explicit per-port state ownership | Encapsulate driver instances, locks, gRPC channels, connectivity and probe counters in a port context instead of unrelated module-global dictionaries. Serialize updates and take consistent telemetry snapshots. | Preserve externally visible DB fields and counter semantics; this is an ownership cleanup, not a schema change. |

Start with ready-table dispatch as a focused cleanup. Treat thread consolidation and concurrency changes separately, with parity and black-box tests. Compare empty-table checks, CPU/RSS, thread and Redis connection counts, and healthy-port toggle/probe latency before and after each change; fewer dispatch blocks alone do not establish resource savings.
