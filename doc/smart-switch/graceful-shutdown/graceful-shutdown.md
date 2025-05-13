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
SmartSwitch supports graceful reboot of the DPUs. Given this, it is quiet natural that we provide support for graceful shutdown of the DPUs. Though it may sound like that the graceful shutdown is half of graceful reboot, it is not so because the way it is invoked, the code path for the shutdown are different making the implementation little complex. Besides this the limitation of the absence of docker, the container separation, and the platform agnostic implementation adds to the challenge of invoking the gnoi call from this code path.

## DPU Graceful Shutdown Sequence

The following sequence diagram illustrates the detailed steps involved in the graceful shutdown of a DPU:

<p align="center"><img src="./images/dpu-graceful-shutdown.svg"></p>

## Explanation of the Flow
   * chassisd: Initiates the shutdown process by invoking set_admin_state(down) in module.py.

   * module.py: Requests dpu_base.py to issue a gNOI reboot request for DPUx.

   * dpu_base.py: Writes a JSON message to the host's named pipe at /host/gnoi_reboot.pipe.

   * Host OS: Forwards the JSON message to gnoi_reboot_daemon.py via /var/run/gnoi_reboot.pipe.

   * gnoi_reboot_daemon.py: Executes the gnoi_client with the provided parameters.

   * gnmi container: Sends the gNOI Reboot RPC to DPUx.

   * DPUx: Acknowledges the reboot request.

   * Alternative Paths:

      * Success: gnmi returns success to gnoi_reboot_daemon.py, which logs the success.

      * Failure: gnmi returns failure to gnoi_reboot_daemon.py, which logs the failure.

   * gnoi_reboot_daemon.py: Writes the reboot result to /var/run/gnoi_reboot_response.pipe.

   * Host OS: Provides the reboot result to dpu_base.py via /host/gnoi_reboot_response.pipe.

   * dpu_base.py: Returns the reboot result to module.py.

   * module.py: Proceeds to shut down DPUx via the platform API, regardless of the reboot outcome.

## Objective

This design enables the `chassisd` process running in the PMON container to invoke a **gNOI-based reboot** when it triggers the "set_admin_state(down)" API of a DPU module, without relying on `docker`, `bash`, or `hostexec` within the container.

## Constraints

- The PMON container is highly restricted: no `docker`, `hostexec`, or `bash`.
- gNOI reboot requires executing a command using `docker exec` on the host.
- Communication must be initiated from PMON and executed by the host.

---

## Design Overview

The solution uses a **named pipe (FIFO)** created on the host and bind-mounted into the PMON container. PMON writes structured reboot requests (as JSON) into the pipe. A lightweight daemon running on the host listens for messages on this pipe, and executes the appropriate `docker exec` command using `gnoi_client`.

---

## Components

### 1. Host-side Named Pipe

A named pipe (e.g., `/var/run/gnoi_reboot.pipe`) is created on the host. It acts as a one-way communication channel from PMON to the host.

### 2. Host-side Reboot Daemon

A long-running Python script monitors the pipe for new lines of input. Each line is expected to be a JSON string with fields like DPU name, IP, and port.

Upon receiving a valid request, the daemon runs a `docker exec` command that invokes `gnoi_client` with parameters to perform a gNOI reboot of the DPU module.

### 3. PMON-side Hook (in `module_base.py`)

Within the PMON container, the `pre_shutdown_hook()` function opens the mounted pipe and writes a JSON-formatted reboot request, including the DPU name and midplane IP.

If writing fails (e.g., pipe is unavailable), the error is logged, and shutdown continues without halting DPU services.

### 4. File Mounting

The named pipe on the host is mounted into PMON 

---

## Workflow Summary

1. **Initialization**
   - Host creates the pipe and starts the reboot listener daemon.
   - The pipe is mounted into the PMON container

2. **Trigger**
   - PMON’s `pre_shutdown_hook()` fetches the DPU’s midplane IP and writes a JSON message to the pipe.

3. **Execution**
   - The host daemon reads the message and performs `docker exec` to invoke `gnoi_client` for rebooting the DPU.

4. **Result**
   - Logs indicate success or failure on both PMON and host sides.
   - The host can remove processed requests or keep logs as needed.

---

## Benefits

- **No PMON dependencies:** No reliance on `docker`, `bash`, or host tools inside PMON.
- **Minimal mount:** Only a single pipe file is mounted from host to container.
- **Clear separation of responsibilities:** PMON requests; host executes.

---

