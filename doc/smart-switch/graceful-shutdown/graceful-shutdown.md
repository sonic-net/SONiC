# SmartSwitch DPU Graceful Shutdown

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 12/05/2025 | Ramesh Raghupathy | Initial version|


## Definitions / Abbreviations

| Term | Meaning |
| --- | ---- |
| PMON | Platform Monitor |
| DPU | Data Processing Unit |
| gRPC | Generic Remote Procedure Calls |
| gNOI | gRPC Network Operations Interface |
| gNMI  | gRPC Network Management Interface |

## Introduction
SmartSwitch supports graceful reboot of the DPUs. Given this, it is quiet natural that we provide support for graceful shutdown of the DPUs. Though it may sound like that the graceful shutdown is the first half of graceful reboot, it is not so because the way it is invoked, the code path for the shutdown are different making the implementation little complex. Besides this, the limitation of the absence of docker, the container separation, and the platform agnostic implementation adds to the challenge of invoking the gNOI call from this code path. Graceful shutdown on each DPU happens in parallel.

## DPU Graceful Shutdown Sequence

The following sequence diagram illustrates the detailed steps involved in the graceful shutdown of a DPU:

<p align="center"><img src="./images/dpu-graceful-shutdown.svg"></p>

## Sequence of Operations

1. **Daemon Initialization:**

   * Upon startup, `gnoi_reboot_daemon.py` subscribes to the `CHASSIS_MODULE_INFO_TABLE` to monitor incoming shutdown/reboot requests. The state transition will be no-op for startup requests.

2. **CLI Command Execution:**

   * The user executes the command `config chassis module shutdown DPUx` via the CLI or a config load.

3. **Chassis Daemon Processing:**

   * `chassisd` receives the shutdown command and invokes set_admin_state(down) on `module_base.py`.

   * Within `module_base.py`, the system checks if the device `subtype` is `"SmartSwitch"` and  `switch_type` is not `dpu`.

   * If both conditions are met, it proceeds with the graceful shutdown process, else calls `module.py` `set_admin_state(down)`

4. **Graceful Shutdown Handler Invocation:**

   * `module_base.py` calls the `graceful_shutdown_handler()` method to initiate the graceful shutdown sequence.

5. **Reboot Request Creation:**

   * Within the `graceful_shutdown_handler()`, `state_transition_in_progress` `True`is written to the `CHASSIS_MODULE_INFO_TABLE` in Redis STATE_DB for DPUx along with `transition_type`.

6. **Daemon Notification and Processing:**

   * `gnoi_reboot_daemon.py` detects the `state_transition_in_progress` turning `True` in `CHASSIS_MODULE_INFO_TABLE` and sends a gNOI Reboot RPC with the method `HALT` to the sysmgr in DPUx, which in turn issues a DBUS request to execute `reboot -p` on DPUx.

7. **Reboot Request**:

   * The daemon forwards the reboot request.

8. **Reboot Status Monitoring:**

   * The daemon sends  `gnoi_client -rpc RebootStatus` to monitor the reboot status of DPUx.
   
9. **DPUx Returns Status:**

   * DPUx returns the reboot status response to the daemon.

10. **Reboot Result Update in DB:**

      * The daemon writes the reboot result to the `CHASSIS_MODULE_INFO_TABLE` in Redis STATE_DB by turning `state_transition_in_progress` to `False` when after the platform API completes the power down operation of the modules as shown in step 13.

      * In case of a reboot result failure the result gets updated after the timeout.

11. **Read the Result:**

      * `module_base.py` in a loop reads the `state_transition_in_progress` turning `False` in `CHASSIS_MODULE_INFO_TABLE` every 5 secs.

12. **Log the Result:**

      * `module_base.py` logs the reboot result accordingly.

13. **Final State Transition:**

      * `module_base.py` invokes `set_admin_state(down)` on `module.py`.

      * `module.py` calls the platform API to power down the module when the DPUx completes kernel shutdown.

## Objective

This design enables the `chassisd` process running in the PMON container to invoke a **gNOI-based reboot** when it triggers the "set_admin_state(down)" API of a DPU module, without relying on `docker`, `bash`, or `hostexec` within the container.

## Constraints

- The PMON container is highly restricted: no `docker`, `hostexec`, or `bash`.
- gNOI reboot requires executing a command using `docker exec` on the host.
- Communication must be initiated from PMON and executed by the host.

---

## Design Overview

In the Redis STATE_DB IPC approach, SONiC leverages Redis's publish-subscribe mechanism to facilitate inter-process communication between components. This event-driven design ensures decoupled and reliable communication between components.

### CHASSIS_MODULE_INFO_TABLE Schema (STATE_DB)

KEY: `CHASSIS_MODULE_INFO_TABLE|<MODULE_NAME>`.

| Field                          | Description                                                                                              |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `state_transition_in_progress` | `"True"` indicates that a transition is ongoing; `"False"` or absence implies no transition.             |
| `transition_start_time`        | Timestamp in human-readable UTC format representing the start of the transition.                         |
| `transition_type`              | Specifies the nature of the transition: `"shutdown"`, `"none"`. `none` is default for reboot and startup |

**Example:**
```
CHASSIS_MODULE_INFO_TABLE|DPU0
{
  "state_transition_in_progress": "True",
  "transition_start_time": "Mon Jun 17 08:32:10 UTC 2025",
  "transition_type": "shutdown"
}
```

| Transition Type       | Who Sets the Field                                              | How It's Cleared                                    |
| --------------------- | --------------------------------------------------------------- | --------------------------------------------------- |
| **Startup**           | CLI or config load       | Once module reaches online state                    |
| **Shutdown**       | CLI or config load  | `gnoi-reboot-daemon` upon completing the platform API (module shutdown)         |
| **Reboot**         | `smartswitch_reboot_helper`                                     |  Cleared by `smartswitch_reboot_helper` upon completing the platform API |

## Parallel Execution

The following sequence diagram illustrates the parallel execution of graceful shutdown of multiple DPUs:

<p align="center"><img src="./images/parallel-execution.svg"></p>

## Interoperability between DPU Graceful Shutdown & gNOI Reboot

<p align="center"><img src="./images/reboot-interoperability.svg"></p>

The diagram above illustrates scenarios where both module_base.py and smartswitch_reboot_helper might attempt to initiate a shutdown, startup and reboot simultaneously. When there is a race condition the one that writes the `CHASSIS_MODULE_INFO_TABLE`  `state_transition_in_progress` field wins. In case if the `state_transition_in_progress` is `True` as a result of DPU startup in progress both reboot and shutdown will fail. It is up to the requesting module to re-issue the transaction if needed. When the module level reboot and switch level reboot happen simultaneously, if the module level reboot has already updated the
`state_transition_in_progress` to `True` the switch level reboot needs to be reissued.  If the switch level reboot happens first it will grab all the module
`state_transition_in_progress` and set them to `True` as a first step and runs to completion.

**Scenario 1:** module_base issues a startup or shutdown when smartswitch_reboot_helper module reboot is in progress for the same module.

 The same scenario applies if "config reload" happens when reboot is in progress.

* smartswitch_reboot_helper writes to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` to `True`.

* If module_base.py attempts to write to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True` during this process, the operation will fail. The user has to retry the shutdown operation later.

* When the reboot is complete the  `CHASSIS_MODULE_INFO_TABLE` `state_transition_in_progress` will be set to `False`. The module_base.py has to retry the shutdown/startup operation as needed when the reboot is complete.

**Scenario 2:** smartswitch_reboot_helper module issues a reboot when module_base graceful shutdown is in progress.

* module_base.py writes to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True` and sets the `"transition_type": "shutdown"`.

* gnoi_reboot_daemon.py is notified of the new entry and proceeds to send a gNOI Reboot RPC with the method HALT to the sysmgr in DPUx.

* The daemon writes the reboot result to the `CHASSIS_MODULE_INFO_TABLE` by toggling `state_transition_in_progress`  to `False`.

* If smartswitch_reboot_helper also attempts to write to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True` during this process, the operation will fail.

* The graceful shutdown completes as planned. So, there is no need for the reboot in this situation.

**Scenario 3:** smartswitch_reboot_helper module issues a reboot when module_base startup is in progress.

* module_base.py writes to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True`.

* If smartswitch_reboot_helper also attempts to write to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True` during this process, the operation will fail.

* The module startup completes as planned. So, the reboot may not be needed in this situation.

**Scenario 4:** module_base issues a graceful shutdown when the module startup is in progress or vice versa.

* If module_base.py writes to `CHASSIS_MODULE_INFO_TABLE`  with `state_transition_in_progress` `True` indicating startup or shutdown is in progress.

* If module_base.py issues another startup or shutdown to the same module that will fail and the user has to issue it again later when the previous operation is complete.

**Scenario 5:** Switch level reboot is issued when module level reboot or startup or shutdown in progress.

* In this situation the switch level reboot logic will check the `state_transition_in_progress` for all the modules first and grab anything that is `False` set them the `True`.  If one or more modules are already undergoing reboot or shutdown or startup it will ignore those modules and complete the remaining.  This will leave the system in the expected state. Until the switch level reboot is complete the  `state_transition_in_progress` for all modules will be maintained `True` irrespective of the type of operation.

**Scenario 6:** Module level reboot or startup or shutdown is issued when switch level reboot is in progress.

* The module level requests will fail as the switch level reboot has already set all the module level `state_transition_in_progress` to `True`.
* The user needs to redo the module level operation after the switch level reboot if needed.

This design ensures that only one reboot process is initiated, regardless of which component triggers it first, thereby preventing race conditions and ensuring system stability.

---

## References

- [PMON HLD](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/pmon/smartswitch-pmon.md)
- [Smart Switch Reboot HLD](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/reboot/reboot-hld.md)

---
