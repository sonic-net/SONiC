# SmartSwitch DPU Graceful Shutdown

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 12/05/2025 | Ramesh Raghupathy | Initial version|


## Definitions / Abbreviations

| Term | Meaning |
| --- | ---- |
| PMON | Platform Monitor |
| DLM | Device Lifecycle Manager |
| NPU | Network Processing Unit |
| DPU | Data Processing Unit |
| PDK | Platform Development Kit |
| SAI | Switch Abstraction Interface |
| GPIO | General Purpose Input Output |
| PSU | Power Supply Unit |
| I2C | Inter-integrated Circuit communication protocol |
| SysFS | Virtual File System provided by the Linux Kernel |
| CP | Control Plane |
| DP | Data Plane |

## Introduction
SmartSwitch supports graceful reboot of the DPUs. Given this, it is quiet natural that we provide support for graceful shutdown of the DPUs. Though it may sound like that the graceful shutdown is the first half of graceful reboot, it is not so because the way it is invoked, the code path for the shutdown are different making the implementation little complex. Besides this, the limitation of the absence of docker, the container separation, and the platform agnostic implementation adds to the challenge of invoking the gnoi call from this code path. Graceful shutdown on each DPU happens in parallel.

## DPU Graceful Shutdown Sequence

The following sequence diagram illustrates the detailed steps involved in the graceful shutdown of a DPU:

<p align="center"><img src="./images/dpu-graceful-shutdown.svg"></p>

## Sequence of Operations

1. CLI Command Execution:
   * The user issues the command config chassis module shutdown DPUx.

2. Chassis Daemon Invocation:

   * chassisd receives the command and calls set_admin_state(down) on module.py to initiate the shutdown process for DPUx.

3. Module Shutdown Request:

   * module.py delegates the shutdown request to module_base.py, which handles lower-level operations.

4. IPC via Redis STATE_DB:

   * module_base.py writes an entry to the GNOI_REBOOT_REQUEST table in Redis STATE_DB, signaling the intent to reboot DPUx.

5. Daemon Subscribes to Redis Table:

   * gnoi_reboot_daemon.py subscribes to the GNOI_REBOOT_REQUEST table to monitor for new reboot requests.

6. Daemon Receives Notification:

   * Upon detecting a new entry, the daemon is notified and proceeds to process the reboot request.

7. gNOI Reboot RPC Execution:

   * The daemon sends a gNOI Reboot RPC with the method HALT to the sysmgr in DPUx.
   * The sysmgr, in turn, issues a DBUS request reboot -p to initiate the reboot process on DPUx.

8. Reboot Status Verification:

   * Since the initial RPC returns an immediate acknowledgment without confirming the reboot status, the daemon executes gnoi_client -rpc RebootStatus to query the current reboot status of DPUx.

9. Status Response Handling:

   * DPUx responds with its current reboot status.
   
   * The daemon writes the reboot result to the GNOI_REBOOT_RESULT table in Redis STATE_DB

10. Module Base Subscribes to Result Table:

   * module_base.py subscribes to the GNOI_REBOOT_RESULT table to monitor for the reboot result.

11. Module Base Receives Notification:

   * Upon detecting a new entry, module_base.py is notified and retrieves the reboot result.

12. Final Shutdown Procedure:

   * Based on the reboot result, module.py proceeds to shut down DPUx via the platform API.

## Objective

This design enables the `chassisd` process running in the PMON container to invoke a **gNOI-based reboot** when it triggers the "set_admin_state(down)" API of a DPU module, without relying on `docker`, `bash`, or `hostexec` within the container.

## Constraints

- The PMON container is highly restricted: no `docker`, `hostexec`, or `bash`.
- gNOI reboot requires executing a command using `docker exec` on the host.
- Communication must be initiated from PMON and executed by the host.

---

## Design Overview

In the Redis STATE_DB IPC approach, SONiC leverages Redis's publish-subscribe mechanism to facilitate inter-process communication between components. This event-driven design ensures decoupled and reliable communication between components.

### GNOI_REBOOT_REQUEST Table
   **Database:** STATE_DB
   
   **Purpose:** Signals a reboot request for a specific DPU.

   **Key Format:** GNOI_REBOOT_REQUEST|<DPU_ID>

   **Fields:**

   | Field       | Type   | Description                                   |
   | ----------- | ------ | --------------------------------------------- |
   | `method`    | string | Reboot method (e.g., `HALT`, `COLD`, `WARM`). |
   | `timestamp` | string | ISO 8601 formatted timestamp of the request.  |
   | `reason`    | string | Optional reason for the reboot.               |

**Example:**
```
  {
    "method": "HALT",
    "timestamp": "2025-05-19T18:57:06Z",
    "reason": "Scheduled maintenance"
  }
```

### GNOI_REBOOT_RESULT Table
   **Database:** STATE_DB
   
   **Purpose:** Stores the result of the reboot operation for a specific DPU.

   **Key Format:** GNOI_REBOOT_RESULT|<DPU_ID>

   **Fields:**

   | Field       | Type   | Description                                       |
   | ----------- | ------ | ------------------------------------------------- |
   | `status`    | string | Result status (e.g., `SUCCESS`, `FAILURE`).       |
   | `timestamp` | string | ISO 8601 formatted timestamp of the result entry. |
   | `message`   | string | Detailed message or error description.            |

**Example:**
```
  {
    "status": "SUCCESS",
    "timestamp": "2025-05-19T19:00:00Z",
    "message": "Reboot completed successfully."
  }
```
## Parallel Execution

The following sequence diagram illustrates the parallel execution of graceful shutdown of multiple DPUs:

<p align="center"><img src="./images/parallel-execution.svg"></p>

---

## IPC Method Comparison: Redis STATE_DB vs. Named Pipe

| Aspect                          | Redis `STATE_DB` IPC                                                                                            | Named Pipe IPC                                                                               |  
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Mechanism**                   | Utilizes Redis Pub/Sub model with subscription handlers for event-driven communication.                         | Employs file-based FIFO (First-In-First-Out) special files for direct process communication. |
| **Event Handling**              | Subscription handlers wait for events; suitable for frequent events.                                            | Processes block until the other end is ready; efficient for infrequent events.               |
| **Overhead**                    | Introduces additional load on Redis, especially with multiple tables; impact in large-scale systems is unknown. | Minimal overhead; relies on the operating system's file system mechanisms.                   |
| **Message Persistence**         | Messages are transient; if no subscriber is listening, messages are lost.                                       | Data remains in the pipe until read; ensures delivery if the reader is available.            |
| **Suitability for Rare Events** | May be overkill for rare events like DPU shutdowns; the persistent subscription may not be justified.           | Well-suited for rare events; resources are utilized only during the event occurrence.        |

## Summary

**Redis STATE_DB IPC:** Offers an event-driven model suitable for frequent and scalable inter-process communications. However, it introduces additional overhead and complexity, which might not be justified for rare events like DPU shutdowns.

**Named Pipe IPC:** Provides a straightforward and efficient mechanism for IPC, especially apt for infrequent events. Its simplicity and low overhead make it a practical choice for scenarios where events are rare.

---

