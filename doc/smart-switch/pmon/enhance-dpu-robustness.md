# Smart Switch: PMON: Enhance DPU Robustness #

## Table of Content ##

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Terminology](#terminology)
- [Critical Processes for DPU Management](#critical-processes-for-dpu-management)
- [Timers and Thresholds](#timers-and-thresholds)
- [DPU Status DB Info](#dpu-status-db-info)
- [DPU Recovery State Machine](#dpu-recovery-state-machine)
- [DPU Software Failures](#dpu-software-failures)
  - [Critical Process Restart on DPU](#critical-process-restart-on-dpu)
  - [Critical Process Persistently Down on DPU](#critical-process-persistently-down-on-dpu)
  - [pmon Crash on NPU](#pmon-crash-on-npu)
  - [databasedpu Crash on NPU](#databasedpu-crash-on-npu)
- [DPU Hardware Failures](#dpu-hardware-failures)
  - [DPU Hardware Failure (Complete DPU Down)](#dpu-hardware-failure-complete-dpu-down)
  - [DPU Power Failure / Unexpected Shutdown](#dpu-power-failure--unexpected-shutdown)
  - [PCIe Failure](#pcie-failure)
- [NPU / Switch Level Failures](#npu--switch-level-failures)
  - [NPU Kernel Crash / Memory Exhaustion](#npu-kernel-crash--memory-exhaustion)
- [Planned Operations](#planned-operations)
  - [DPU Graceful Shutdown](#dpu-graceful-shutdown)
  - [DPU Cold Reboot](#dpu-cold-reboot)
  - [Full SmartSwitch Reboot](#full-smartswitch-reboot)
- [Scenario DB State Summary](#scenario-db-state-summary)
- [Repository Change Summary](#repository-change-summary)
- [References](#references)

---

## Revision ##

|  Rev  |        Author       | Change Description                     |
| :---: |  :----------------: | -------------------------------------- |
|  0.1  |  Vasundhara Volam   | Initial Version                        |

---

## Scope ##

This document covers the High Level Design for DPU failure scenarios on a SmartSwitch from the PMON (Platform Monitor) perspective — specifically focused on detection, DB state management, and recovery actions performed by `chassisd` and other PMON sub-daemons.

The scope includes:

- DPU software failures (critical process crashes and restarts on DPU; pmon and databasedpu crashes on NPU)
- DPU hardware failures (complete DPU down, power failure / unexpected shutdown, PCIe failure)
- NPU/switch-level failures (kernel crash, memory exhaustion)
- DB state tracking for DPU failure detection and recovery (new and existing DB entries)
- DB state tracking for planned operations
- PMON critical process definitions and criticality levels
- Timers and thresholds used by PMON for failure detection and recovery

---

## Definitions/Abbreviations ##

| Term | Meaning                                                 |
| ---- | ------------------------------------------------------- |
| API  | Application Programming Interface                       |
| ASIC | Application-Specific Integrated Circuit                 |
| CLI  | Command-Line Interface                                  |
| DB   | Redis Database                                          |
| DPU  | Data Processing Unit                                    |
| gNOI | gRPC Network Operations Interface                       |
| gRPC | Google Remote Procedure Call                             |
| NPU  | Network Processing Unit                                 |
| PCIe | PCI Express (Peripheral Component Interconnect Express) |
| PMON | Platform Monitor                                        |
| RPC  | Remote Procedure Call                                   |
| SAI  | Switch Abstraction Interface                            |

---

## Overview ##

SmartSwitch consists of one NPU (switch ASIC) and multiple DPUs. All front panel ports are connected to the NPU. DPUs are connected to the NPU via PCIe and back-panel ports.

The PMON (Platform Monitor) daemon on the NPU is responsible for monitoring DPU health and managing DPU lifecycle operations. Its primary sub-daemon, `chassisd`, continuously polls DPU states (midplane, control plane, data plane), detects failures, performs recovery actions (power-cycle, PCIe rescan), and updates database entries to reflect DPU readiness.

This document enumerates all failure scenarios that can occur on a DPU or its supporting infrastructure from the PMON perspective, describes detection mechanisms driven by `chassisd`, recovery paths, and the corresponding database state changes. It also covers planned operations (graceful shutdown, cold reboot, full SmartSwitch reboot) and the DB state changes introduced to support them.

---

## Terminology ##

| Term | Explanation |
| ---- | ----------- |
| chassisd | Chassis daemon running inside `pmon` on the NPU; monitors DPU health states, manages DPU power-cycle and reset operations |
| pmon | Platform Monitor daemon on NPU; hosts `chassisd` and other hardware monitoring sub-daemons |
| syncd | Sync daemon; manages SAI API calls to DPU ASIC |
| control plane state | DPU SONiC is booted up, all containers are up, interfaces are up, and DPU is ready to accept configuration. Derived from SYSTEM_READY in STATE_DB. Values: `"up"`, `"down"`. |
| midplane link state | The PCIe link between the NPU and DPU is operational. Monitored and updated by NPU pmon `chassisd` via the `is_midplane_reachable` platform API. Values: `"up"`, `"down"`. |
| dataplane state | Configuration is downloaded, pipeline stages are up, and DPU hardware (port/ASIC) is ready to take traffic. Values: `"up"`, `"down"`. |

---

## Critical Processes for DPU Management ##

The following processes are critical for SmartSwitch DPU lifecycle management. A failure in any of these impacts the ability to monitor, recover, or manage DPUs.

**PMON-managed processes (on NPU):**

| Process |  Role | Failure Impact |
| ------- |  ---- | -------------- |
| `chassisd` | Monitors DPU health (midplane, control plane, data plane); manages power-cycle, reset, and DB state updates | All DPU failure detection and recovery stops; no DB updates |
| `pcied` | Monitors PCIe link state between NPU and DPUs; updates `PCIE_DETACH_INFO` in STATE_DB | PCIe failures go undetected; `PCIE_DETACH_INFO` not updated |

**Other critical NPU processes:**

| Process | Container | Role | Failure Impact |
| ------- | --------- | ---- | -------------- |
| `gnoi_reboot_daemon.py` | `gnmi` | Sends gNOI Reboot RPCs to DPUs for graceful shutdown / reboot | Graceful shutdown and planned reboot operations fail; DPU cannot be halted cleanly before power-cycle |
| `sysmgr` | Host | Routes DPU planned shutdown and reboot requests to host services for execution | Planned DPU reset operations cannot be carried out |


---

## Timers and Thresholds ##

All timers and thresholds used by PMON for DPU failure detection and recovery are listed below. Values shown are defaults; some are configurable via `platform.json`.

| Timer / Threshold | Default Value | Configurable | Used By | Description |
| ----------------- | :-----------: | :----------: | ------- | ----------- |
| `chassisd` health poll interval | 10 seconds | No | `chassisd` | Interval at which `chassisd` polls `dpu_control_plane_state`, `dpu_data_plane_state`, and `dpu_midplane_link_state` |
| DPU auto-recovery timeout | 60 seconds | Yes (`platform.json`) | `chassisd` | Time allowed for a DPU to recover from a critical process restart before escalating. If `dpu_control_plane_state` or `dpu_midplane_state` remains `down` beyond this timeout, `chassisd` initiates a DPU reset, if DPU is still up and running. |
| DPU power-cycle timeout | 180 seconds | Yes | `chassisd` | Time `chassisd` waits for `dpu_control_plane_state` to return to `up` before issuing a power-cycle |
| `pcied` PCIe poll interval | 60 seconds | No | `pcied` | Interval at which `pcied` checks PCIe link status for all DPUs. A PCIe failure may go undetected for up to 60 seconds. |
| `dpu_halt_services_timeout` | 60 seconds | Yes (`platform.json`) | `gnoi_reboot_daemon.py` | Maximum time to wait for DPU services to halt gracefully during reboot/shutdown |
| `reset_limit` | 5 | Yes (`platform.json`) | `chassisd` | Maximum number of consecutive unplanned power-cycle attempts before marking DPU as unrecoverable |

> **Note:** `chassisd` polls `dpu_data_plane_state` alongside `dpu_control_plane_state` and `dpu_midplane_link_state`, but `dpu_data_plane_state` alone does not trigger recovery actions. A data-plane-down with control-plane-up scenario indicates that the DPU SONiC stack is running but the data plane pipeline has not converged — this is expected during initial programming or after a configuration change. Recovery is triggered only when `dpu_control_plane_state` or `dpu_midplane_link_state` transitions to `down`. The `dpu_data_plane_state` is used by `chassisd` solely to determine full DPU readiness for setting `ready_status` to `true`.

---

## DPU Status DB Info ##

### Existing DB entries ###

The following DB entries track the DPU lifecycle state and are referenced during failure detection and recovery.

**DPU State in CHASSIS_STATE_DB:**

```
DPU_STATE|DPU<dpu_index>:
{
  "dpu_control_plane_state": "up" | "down",
  "dpu_control_plane_time":  "<UTC timestamp>",
  "dpu_data_plane_state":    "up" | "down",
  "dpu_data_plane_time":     "<UTC timestamp>",
  "dpu_midplane_link_state": "up" | "down",
  "dpu_midplane_link_time":  "<UTC timestamp>"
}
```

**PCIe Detach Info in STATE_DB:**

```
PCIE_DETACH_INFO|DPU<dpu_index>:
{
  "dpu_id":    "<index>",
  "dpu_state": "detaching" | "detached" | "reattached",
  "bus_info":  "[DDDD:]BB:SS.F"
}
```

**Graceful Shutdown / Reboot Tracking in STATE_DB:**

```
CHASSIS_MODULE_TABLE|DPU<dpu_index>:
{
  "oper_status":                  "Online" | "Offline",
  "state_transition_in_progress": "True" | "False",
  "transition_start_time":        "<UTC timestamp>",
  "transition_type":              "shutdown" | "reboot" | "none"
}
```

> **Note:** The `state_transition_in_progress`, `transition_start_time`, and `transition_type` fields are managed by the graceful-shutdown implementation in [sonic-gnmi](https://github.com/sonic-net/sonic-gnmi) and [sonic-utilities](https://github.com/sonic-net/sonic-utilities). These fields are not managed by sonic-platform-daemons.

### New DB entries ###

The following DB entries will now be newly created to track DPU failure states.

**DPU additional Info in CHASSIS_STATE_DB on NPU**

```
DPU_STATE|DPU<dpu_index>:
{
  "ready_status":                      "true" | "false",
  "recovery_status":                   "recoverable" | "unrecoverable",
  "reset_count":                       "<integer>",
  "last_down_time":                    "<UTC timestamp>",
  "last_ready_time":                   "<UTC timestamp>"
}
```

| Field | Description | Set by | Cleared by |
| ----- | ----------- | ------ | ---------- |
| `ready_status` | Set to `"true"` when the DPU is fully up and ready (midplane, control plane, data plane all up). Set to `"false"` when the DPU goes down or undergoes a reset. | `chassisd` | `chassisd` (set to `"false"` on failure/reset) |
| `recovery_status` | Set to `"recoverable"` on initialization. Set to `"unrecoverable"` when `reset_count` reaches `reset_limit`. | `chassisd` | `chassisd` (reset to `"recoverable"` on planned restart) |
| `reset_count` | Number of unplanned DPU resets. Reset to 0 on `chassisd` reset on NPU (e.g., NPU reboot, `pmon` restart). | `chassisd` | `chassisd` |
| `last_down_time` | UTC timestamp of the last time the DPU went down | `chassisd` | — |
| `last_ready_time` | UTC timestamp of the last time the DPU became ready | `chassisd` | — |

**DPU Auto-Recovery Feature in CONFIG_DB on NPU**

```
FEATURE|dpu-auto-recovery:
{
  "state":        "enabled" | "disabled" | "always_disabled",
  "auto_restart": "enabled" | "disabled",
  "high_mem_alert": "disabled"
}
```

| Field | Default | Description |
| ----- | ------- | ----------- |
| `state` | `enabled` | Enable or disable the DPU auto-recovery feature. When `disabled` or `always_disabled`, `chassisd` will not automatically power-cycle DPUs on failure. |
| `auto_restart` | `enabled` | Standard SONiC FEATURE table field — enables `systemd` to restart the feature's associated service if it crashes. |
| `high_mem_alert` | `disabled` | Standard SONiC FEATURE table field — high memory usage alert threshold. |

> **Note:** `dpu-auto-recovery` is **not** a separate service or container. It is a feature flag entry in CONFIG_DB's `FEATURE` table, read by `chassisd` (running inside the `pmon` container) to determine whether automatic DPU power-cycle recovery is enabled. The `auto_restart` and `high_mem_alert` fields are standard SONiC FEATURE table fields required by the feature infrastructure; they do not govern `chassisd` itself. When `state` is `disabled`, `chassisd` still monitors and updates DPU states in CHASSIS_STATE_DB, but will not initiate automatic power-cycle recovery. Manual intervention is required to recover failed DPUs.

---

## DPU Recovery State Machine ##

The following diagram shows the state transitions managed by `chassisd` for a single DPU. Each box represents a `chassisd`-observed DPU state; edges show the triggers and actions.

```mermaid
stateDiagram-v2
    [*] --> Booting : DPU power on

    Booting --> Ready : All states up

    Ready --> SWFailure : Control plane down
    SWFailure --> Ready : Self recovers within 60s
    SWFailure --> PowerCycle : 180s timeout expires

    Ready --> PowerCycle : HW failure detected

    PowerCycle --> Booting : Power cycle issued
    PowerCycle --> Unrecoverable : reset count >= reset limit

    Ready --> PlannedShutdown : CLI module shutdown
    Ready --> PlannedReboot : CLI reboot DPU

    PlannedShutdown --> Offline : gNOI HALT then power down
    PlannedReboot --> Booting : gNOI HALT then power cycle

    Offline --> Booting : CLI module startup

    Unrecoverable --> Booting : chassisd reset on NPU
```

| State | `ready_status` | `recovery_status` | Key DB Indicators |
| ----- | :------------: | :----------------: | ----------------- |
| **Booting** | `false` | `recoverable` | `dpu_control_plane_state: down` |
| **Ready** | `true` | `recoverable` | All three states `up` |
| **SWFailure** | `false` | `recoverable` | `dpu_control_plane_state: down`, `dpu_midplane_link_state: up` |
| **PowerCycle** | `false` | `recoverable` | `chassisd` issuing power-cycle; `reset_count` incremented |
| **Offline** | `false` | `recoverable` | `oper_status: Offline` |
| **Unrecoverable** | `false` | `unrecoverable` | `reset_count` ≥ `reset_limit` |

---

## DPU Software Failures ##

### Critical process restart on DPU ###

**Description:**
When any process in the `syncd` or `swss` dockers crashes on the DPU, but the container supervisor successfully restarts the process and the DPU recovers on its own within the auto-recovery timeout (default: 60 seconds). No power-cycle is needed.

**Detection (by PMON):**
- `chassisd` on the NPU polls `dpu_control_plane_state` every 10 seconds and observes it as `down`.

**PMON Action:**
- `chassisd` sets `ready_status` to `false` and updates `last_down_time` for the corresponding DPU.
- `chassisd` waits up to 60 seconds for the DPU to self-recover.
- Once `dpu_control_plane_state` transitions back to `up`, `chassisd` verifies all DPU states (midplane, control plane, data plane), sets `ready_status` back to `true`, and updates `last_ready_time`.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `dpu_control_plane_state` | `up` | `down` | `up` |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |

---

### Critical process persistently down on DPU ###

**Description:**
When any critical process in `syncd`, `swss`, `pmon`, or `database` crashes on the DPU and **remains down beyond the auto-recovery timeout** (i.e., the container supervisor cannot successfully restart it, or the process keeps crash-looping). Unlike a transient restart, this scenario indicates a persistent failure that requires a DPU power-cycle to recover.

**Detection (by PMON):**
- `chassisd` on the NPU polls `dpu_control_plane_state` every 10 seconds and observes it as `down`.
- State remains `down` beyond the 60-second auto-recovery timeout.

**PMON Action:**
- `chassisd` sets `ready_status` to `false` and updates `last_down_time` for the corresponding DPU.
- After the power-cycle timeout (default: 180 seconds, measured from the time failure is first detected — i.e., total wait is 180 seconds, which includes the initial 60-second auto-recovery window) elapses without recovery, `chassisd` issues a power-cycle of the DPU and increments `reset_count`.
- Once `dpu_control_plane_state` transitions back to `up`, `chassisd` verifies all DPU states (midplane, control plane, data plane), sets `ready_status` back to `true`, and updates `last_ready_time`.
- If `reset_count` reaches `reset_limit`, `chassisd` sets `recovery_status` to `"unrecoverable"` and stops further automatic power-cycle attempts.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `dpu_control_plane_state` | `up` | `down` | `up` |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |
| `reset_count` | N | N | N+1 |
| `recovery_status` | `recoverable` | `recoverable` | `recoverable` (or `unrecoverable` if N+1 ≥ `reset_limit`) |

---

### pmon crash on NPU ###

**Description:**
The `pmon` (Platform Monitor) daemon on the NPU crashes. This is a **critical** PMON failure — `chassisd` and all other PMON sub-daemons stop, halting all DPU health monitoring.

**Detection (by PMON):**
- Not self-detectable. `systemd` detects the `pmon` container is down and restarts it.
- DPU health state updates to `CHASSIS_STATE_DB` stop during the outage.

**PMON Action:**
- On `chassisd` bringup sequence after restart, `chassisd` sets `ready_status` to `false` and updates `last_down_time` for **all** DPUs.
- `chassisd` re-polls all DPU states and updates `CHASSIS_STATE_DB` with current values.
- For each DPU found healthy, `chassisd` sets `ready_status` back to `true` and updates `last_ready_time`.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `ready_status` (all DPUs) | `true` | stale | `false` → `true` (per DPU) |
| `last_down_time` (all DPUs) | — | — | `<UTC timestamp>` |
| `last_ready_time` (all DPUs) | — | — | `<UTC timestamp>` (per DPU) |

> **Note:** If only `chassisd` crashes within the `pmon` container (while `pmon` itself stays running), `supervisord` inside `pmon` restarts `chassisd` automatically. The recovery behavior is identical to the full `pmon` crash case described above — `chassisd` re-initializes all DPU states on startup.

---

### databasedpu crash on NPU ###

**Description:**
The `databasedpu<dpu-index>` (per-DPU Redis database instance) on the NPU crashes. Each DPU has a dedicated Redis instance on the NPU (port 6381 + DPU ID, bound to midplane bridge IP 169.254.200.254).

**Detection (by PMON):**
- `chassisd` cannot read DPU state from the corresponding Redis instance.

**PMON Action:**
- `chassisd` detects loss of DPU state, sets `ready_status` to `false`, and updates `last_down_time`.
- After `systemd` restarts the Redis instance and DPU reconnects, `chassisd` polls DPU state, sets `ready_status` back to `true`, and updates `last_ready_time` once all states are verified.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |

---

## DPU Hardware Failures ##

### DPU Hardware Failure (Complete DPU Down) ###

**Description:**
A DPU completely fails due to hardware fault, thermal event, or unrecoverable error. The DPU is no longer responsive on the midplane or back-panel ports.

**Detection (by PMON):**
- NPU: Oper state of the DPU `CHASSIS_MODULE_TABLE|DPU<dpu_index>|oper_status` is set to `offline`.

**PMON Action:**
- `chassisd` sets `ready_status` to `false` and updates `last_down_time` for the corresponding DPU.
- `chassisd` power-cycles the DPU **immediately** (no 180-second timeout — the DPU is already confirmed non-functional via `oper_status: Offline`) and increments `reset_count`.
- After power-cycle, DPU goes through full boot sequence: midplane attach → PCIe rescan → SONiC boot → container startup.
- `chassisd` verifies all DPU states (midplane, control plane, data plane), sets `ready_status` back to `true`, and updates `last_ready_time`.
- If `reset_count` reaches `reset_limit`, `chassisd` sets `recovery_status` to `"unrecoverable"` and stops further automatic power-cycle attempts.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `oper_status` | `Online` | `Offline` | `Online` |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |
| `reset_count` | N | N | N+1 |
| `recovery_status` | `recoverable` | `recoverable` | `recoverable` (or `unrecoverable` if N+1 ≥ `reset_limit`) |

---

### DPU Power Failure / Unexpected Shutdown ###

**Description:**
The DPU loses power unexpectedly or shuts down without graceful notification (e.g., voltage regulator failure, firmware crash).

**Detection (by PMON):**
- NPU `pmon` detects midplane ping failure → `dpu_midplane_link_state` set to `down`.
- `dpu_control_plane_state` transitions to `down`.

**PMON Action:**
- `chassisd` sets `ready_status` to `false` and updates `last_down_time`.
- `chassisd` power-cycles the DPU **immediately** (no 180-second timeout — midplane and control plane are already confirmed down) and increments `reset_count`.
- After power-cycle, `chassisd` verifies all DPU states, sets `ready_status` back to `true`, and updates `last_ready_time`.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `dpu_midplane_link_state` | `up` | `down` | `up` |
| `dpu_control_plane_state` | `up` | `down` | `up` |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |
| `reset_count` | N | N | N+1 |

---

### PCIe Failure ###

**Description:**
The PCIe bus between the NPU and a local DPU fails, making the DPU unreachable from the NPU. The DPU may still be running internally but is disconnected from the NPU.

**Detection (by PMON):**
- `pcied` detects PCIe link down and updates `PCIE_DETACH_INFO|DPU<dpu_index>` in STATE_DB with `dpu_state: detached`.
- Independently, `chassisd` detects midplane loss via `is_midplane_reachable()` polling and updates `dpu_midplane_link_state` → `down` in CHASSIS_STATE_DB.

**PMON Action:**
- `chassisd` sets `ready_status` to `false` and updates `last_down_time`.
- `chassisd` power-cycles the DPU **immediately** (no 180-second timeout — midplane link loss and PCIe detach confirm the DPU is unreachable) and increments `reset_count`.
- After power-cycle, PCIe rescan is performed:
  - Platform vendor API: `pci_reattach()` (provided by `sonic_platform`).
- `chassisd` verifies all DPU states (midplane, control plane, data plane), sets `ready_status` back to `true`, and updates `last_ready_time`.

**DB State Transition:**

| DB Field | Before | During Failure | After Recovery |
| -------- | :----: | :------------: | :------------: |
| `dpu_midplane_link_state` | `up` | `down` | `up` |
| `PCIE_DETACH_INFO` `dpu_state` | `reattached` | `detached` | `reattached` |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |
| `reset_count` | N | N | N+1 |

---

## NPU / Switch Level Failures ##

### NPU Kernel Crash / Memory Exhaustion ###

**Description:**
The entire switch (NPU + all DPUs) goes down due to kernel panic or memory exhaustion. All DPUs on the switch are impacted simultaneously.

**Detection (by PMON):**
- On NPU recovery, `chassisd` reads the reboot cause from `/host/reboot-cause/reboot-cause.txt`. If the reboot cause indicates a kernel crash or memory exhaustion (e.g., `Kernel Panic`), `chassisd` treats all DPU states as potentially stale and triggers re-initialization.

**PMON Action:**
- On recovery, `chassisd` initializes all DPU states as `down`, sets `ready_status` to `false`, and updates `last_down_time` for all DPUs.
- `chassisd` re-establishes midplane connectivity and polls each DPU's state.
- If a DPU is still running and healthy (midplane, control plane, data plane all `up`), `chassisd` sets `ready_status` back to `true` and updates `last_ready_time`.
- If a DPU is unresponsive or in a bad state, `chassisd` sends gNOI Reboot RPC to reset it. Each such DPU then goes through: midplane attach → PCIe rescan → SONiC boot → container startup.

**DB State Transition:**

| DB Field | Before Crash | On NPU Recovery | After DPU Recovery |
| -------- | :----------: | :-------------: | :----------------: |
| `ready_status` (all DPUs) | `true` | `false` | `true` (per DPU) |
| `last_down_time` (all DPUs) | — | `<UTC timestamp>` | — |
| `last_ready_time` (all DPUs) | — | — | `<UTC timestamp>` (per DPU) |

---

## Planned Operations ##

### DPU Graceful Shutdown ###

**Description:**
Orderly shutdown of a DPU via CLI command: `config chassis module shutdown DPU<x>`.

**PMON Sequence:**
1. `chassisd` calls `set_admin_state(down)` → `module_base.py` triggers `graceful_shutdown_handler()`.
2. `CHASSIS_MODULE_TABLE` in STATE_DB updated:
   - `state_transition_in_progress`: `True`
   - `transition_start_time`: `<UTC timestamp>`
   - `transition_type`: `shutdown`
3. `chassisd` updates CHASSIS_STATE_DB:
   - `DPU_STATE|DPU<dpu_index>`: `ready_status`: `false`, `last_down_time`: `<UTC timestamp>`
4. `gnoi_reboot_daemon.py` detects the transition and sends gNOI Reboot RPC (Method: `HALT`) to DPU.
5. DPU gracefully shuts down all services via `reboot -p`.
6. NPU polls `gnoi_client -rpc RebootStatus` until `active=false` (services terminated).
7. `state_transition_in_progress` set to `False`.
8. `module_base.py` calls platform API `power_down()` to power off DPU.
9. PCIe detach: platform vendor API `pci_detach()`.
10. Sensor ignore configs added, sensord restarted.

**DB State Transition:**

| DB Field | Before | After Shutdown |
| -------- | :----: | :------------: |
| `ready_status` | `true` | `false` |
| `last_down_time` | — | `<UTC timestamp>` |
| `oper_status` | `Online` | `Offline` |
| `state_transition_in_progress` | `False` | `True` → `False` |

**Race Condition Handling:**
- If module shutdown is requested during a DPU reboot: operation fails; retry after reboot completes.
- If switch reboot is requested during module shutdown: graceful shutdown completes; switch reboot proceeds.
- Concurrent startup/shutdown on the same module: fails; user retries later.
- If `config chassis module shutdown` is issued while `chassisd` is in the middle of an auto-recovery power-cycle for the same DPU: `chassisd` detects the admin-down request, aborts the auto-recovery loop, and proceeds with the graceful shutdown sequence.
- If `pcied` detects a PCIe failure and updates `PCIE_DETACH_INFO` at the same time `chassisd` initiates a power-cycle due to midplane loss: `chassisd` holds a per-DPU lock during the power-cycle sequence. `pcied` updates `PCIE_DETACH_INFO` independently (no lock contention). `chassisd` reads `PCIE_DETACH_INFO` during its power-cycle flow and performs PCIe rescan if `dpu_state` is `detached`. No conflicting actions occur because `pcied` is read-only from `chassisd`'s perspective — it only updates state, while `chassisd` acts on it.

---

### DPU Cold Reboot ###

**Description:**
Reboot a DPU with full power-cycle via CLI: `reboot -d <DPU_ID>`.

**PMON Sequence:**
1. NPU sends gNOI Reboot RPC (Method: `HALT`) to DPU.
2. NPU polls gNOI `RebootStatus` until `active=false` and `Status=STATUS_SUCCESS`.
3. Timeout: `dpu_halt_services_timeout` (Read from `platform.json`, default 60 seconds).
4. PCIe detach: platform vendor API `pci_detach()`.
5. Platform vendor reboot API invoked (DPU cold boot / power-cycle).
6. PCIe reattach: platform vendor API `pci_reattach()`.
7. DPU boots, services start, reports `dpu_control_plane_state=up`.
8. `chassisd` verifies all DPU states and sets `ready_status` to `true`.

**DB State Transition:**

| DB Field | Before | During Reboot | After Recovery |
| -------- | :----: | :-----------: | :------------: |
| `ready_status` | `true` | `false` | `true` |
| `last_down_time` | — | `<UTC timestamp>` | — |
| `last_ready_time` | — | — | `<UTC timestamp>` |
| `PCIE_DETACH_INFO` `dpu_state` | `reattached` | `detaching` → `detached` | `reattached` |

**Error handling:**
- If gNOI service is unreachable: detach PCIe and proceed after timeout.
- If PCIe reattach fails: error handling + restoration mechanism triggered.
- If DPU stuck: hardware watchdog triggers reset (vendor-specific).

---

### Full SmartSwitch Reboot ###

**Description:**
Planned reboot of the entire SmartSwitch (NPU + all DPUs) via CLI: `reboot`. All DPUs are gracefully shut down in parallel before the NPU reboots.

**PMON Sequence:**
1. NPU sends gNOI Reboot RPC (Method: `HALT`) to **all** DPUs in parallel (multiple threads).
2. NPU polls gNOI `RebootStatus` for each DPU until `active=false` and `Status=STATUS_SUCCESS`.
3. Timeout per DPU: `dpu_halt_services_timeout` (default from `platform.json`, typically 60 seconds).
4. For each DPU: PCIe detach via platform vendor API `pci_detach()`.
5. NPU proceeds with its own reboot sequence.
6. On NPU boot, PCIe enumeration discovers all DPUs.
7. `chassisd` power-cycles each DPU and performs PCIe reattach.
8. Each DPU boots: midplane attach → SONiC boot → container startup → reports `dpu_control_plane_state=up`.

**DB State Transition:**

| DB Field | Before | During Reboot | After Recovery |
| -------- | :----: | :-----------: | :------------: |
| `ready_status` (all DPUs) | `true` | `false` | `true` (per DPU) |
| `last_down_time` (all DPUs) | — | `<UTC timestamp>` | — |
| `last_ready_time` (all DPUs) | — | — | `<UTC timestamp>` (per DPU) |
| `PCIE_DETACH_INFO` `dpu_state` (per DPU) | `reattached` | `detaching` → `detached` | `reattached` |

**Error handling:**
- If a DPU does not respond to gNOI Reboot RPC within the timeout: NPU proceeds with PCIe detach and continues the reboot. The unresponsive DPU is cold-booted on NPU recovery.
- If a DPU fails to come back after the full switch reboot: `chassisd` retries power-cycle up to `reset_limit` (tracked via `reset_count`). If still unresponsive, `chassisd` sets `recovery_status` to `"unrecoverable"`.
- If the NPU reboot is initiated while a DPU graceful shutdown is in progress: the graceful shutdown completes first, then the NPU reboot proceeds.

---

## Scenario DB State Summary ##

| DPU Scenario | `dpu_control_plane_state` | `dpu_midplane_link_state` | `ready_status` | PMON Action |
| ------------ | :-----------------------: | :-----------------------: | :-----------: | ----------- |
| DPU booting – initial state | down | down | false | `chassisd` polls; waiting for DPU to come up |
| DPU healthy and running – first boot | up | up | true | Set `ready_status=true` after verifying all states |
| DPU crash / unplanned reboot | down | down | false | Power-cycle DPU; increment `reset_count` |
| DPU up after crash | up | up | true | Set `ready_status=true` after verifying all states |
| DPU stuck (lost connectivity) | down | down | false | Power-cycle DPU; increment `reset_count` |
| DPU up after losing connectivity / reboot | up | up | true | Set `ready_status=true` after verifying all states |
| DPU control plane restart – critical services | down → up | up | false → true | Wait for auto-recovery; set `ready_status=true` on recovery |
| NPU/DPU OS upgrade | down → up | up | false → true | Re-poll DPU states on NPU recovery |
| DPU dead – power cycle | down | down | false | Power-cycle DPU; increment `reset_count` |
| DPU dead – unrecoverable | down | down | false | `reset_count` reached `reset_limit`; `recovery_status` set to `"unrecoverable"`; raise alert |
| Full SmartSwitch reboot (planned) | down → up | down → up | false → true | gNOI halt; power-cycle; re-verify |

---

## Repository Change Summary ##

| Repository | Component | Changes |
| ---------- | --------- | ------- |
| [sonic-platform-daemons](https://github.com/sonic-net/sonic-platform-daemons) | `chassisd` | DPU failure detection, automated power-cycle recovery, new CHASSIS_STATE_DB fields (`ready_status`, `recovery_status`, `reset_count`, `last_down_time`, `last_ready_time`) |
| [sonic-buildimage](https://github.com/sonic-net/sonic-buildimage) | PMON container | Configuration updates for new `chassisd` failure recovery features |

---

## References ##

- [Smart Switch PMON](../pmon/smartswitch-pmon.md)
- [Smart Switch Graceful Shutdown](../graceful-shutdown/graceful-shutdown.md)
- [Smart Switch Reboot HLD](../reboot/reboot-hld.md)
- [Smart Switch Database Architecture](../smart-switch-database-architecture/smart-switch-database-design.md)
- [Smart Switch IP Address Assignment](../ip-address-assigment/smart-switch-ip-address-assignment.md)
- [Smart Switch DPU Upgrade HLD](../upgrade/dpu-upgrade-hld.md)
