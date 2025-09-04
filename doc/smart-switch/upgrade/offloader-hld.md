# DPU Offloader #

## Table of Content

### 1. Revision

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 04/03/2025 | Dawei Huang | Initial version    |

### 2. Scope

This document describes the high-level design of the DPU Offloader, a service that manages offloaded containers on the NPU in a SmartSwitch environment. The offloader aims to provide reliable and automated management of DPU offloaded services through GNOI APIs.

#### 2.1 Dependencies
The DPU Offloader relies on the following components:
* **GNOI API:** Interface to communicate with the NPU for container management.
* **Healthy NPU and DPU State:** The offloader requires that the DPU and NPU are operational.
* **SONiC Offloaded Services:** GNMI, Database, and HA services offloaded from the DPU to the NPU.

### 3. Definitions/Abbreviations

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| DPU   | Data Processing Unit                      |
| NPU   | Network Processing Unit                   |
| GNMI  | gRPC Network Management Interface         |
| GNOI  | gRPC Network Operations Interface         |
| CLI   | Command Line Interface                    |

### 4. Overview

The DPU Offloader provides local management access to containers offloaded from the DPU to the NPU. In the SmartSwitch architecture, resource constraints on the DPU lead to offloading key SONiC services to the NPU. The offloader automates tasks such as starting, stopping, and monitoring these offloaded services while maintaining compatibility with the SmartSwitch upgrade process.

### 5. Goals and Requirements

The primary goals of the DPU Offloader are:
1. **Automated Container Management:** Automatically start, stop, and upgrade offloaded containers.
2. **Health Monitoring:** Continuously check the status of offloaded containers and take appropriate action when needed.
3. **Seamless Integration:** Provide an intuitive CLI for manual management and status monitoring.

Non-goals:
1. **Managing Non-Offloaded Services:** The offloader is exclusively for managing offloaded containers.
2. **Direct DPU OS Management:** Managing the base SONiC OS on the DPU is out of scope.

### 6. Architecture

#### 6.1 Key Components

* **Offloader Daemon:** Runs as a service on the DPU and interacts with the GNOI API for container management.
* **GNOI Client:** Interfaces with the NPU to manage offloaded containers.
* **Health Monitor:** Monitors the status of containers and triggers automatic recovery.
* **CLI Interface:** Allows manual interaction and status checks.

**Component Diagram:**
[DPU] ----> [Offloader Daemon] ----> [GNOI Client] ----> [NPU] | | [Health Monitor] [CLI Interface]


#### 6.2 Offloader Workflow

1. **Startup:**
   * Health Monitor checks the status of offloaded containers.
   * Automatically starts any container that is not running.

2. **Container Management:**
   * Start, stop, list, and deploy offloaded containers through CLI or automatic actions.
   * Monitor containers for crashes or version mismatches and take corrective actions.

3. **Version Check:**
   * Ensure that offloaded container versions match the DPU SONiC version. If not, trigger an update.

4. **Automatic Recovery:**
   * Restart containers if they crash.
   * Attempt version synchronization when a version mismatch is detected.

### 7. High-Level Design

#### 7.1. Initialization Sequence

1. Start the Offloader Daemon.
2. Query the NPU for the list of running offloaded containers.
3. Validate container versions.
4. Start containers if they are not running.
5. Log the current state.

#### 7.2. Management Operations

| Operation       | Command                          | Description                                   |
| -------------- | -------------------------------- | --------------------------------------------- |
| Start Container | `offloadctl start <container>`    | Starts an offloaded container on the NPU.       |
| Stop Container  | `offloadctl stop <container>`     | Stops an offloaded container on the NPU.        |
| List Containers | `offloadctl list`                 | Lists all offloaded containers and their status.|
| Deploy Image    | `offloadctl deploy <image>`       | Deploys a new container image to the NPU.       |
| Monitor Status  | `offloadctl status <container>`   | Shows the health status of a specific container.|

### 8. GNOI Specific Features

#### 8.1. `Containerz` RPC Enhancements

The following GNOI RPCs will be leveraged for container management:
* `Containerz.StartContainer`: Starts an offloaded container.
* `Containerz.StopContainer`: Stops a running container.
* `Containerz.ListContainer`: Lists all containers.
* `Containerz.ListImage`: Lists available container images.
* `Containerz.Deploy`: Deploys a new container image.

### 9. Configuration

No new configuration parameters are needed. The offloader will use the existing GNOI configuration of the DPU and NPU.

### 10. CLI

The Offloader provides a command line interface for manual operations:

* **Starting a Container:**
``` offloadctl start <container> ```
* **Stopping a Container:**
``` offloadctl stop <container> ```
* **Listing Containers:**
``` offloadctl list ```
* **Deploying a New Image:**
``` offloadctl deploy <image> ```
* **Checking Status:**
``` offloadctl status <container> ```


### 11. Implementation Roadmap

1. **Phase 1: Basic Daemon and CLI**
 * Implement the daemon to start and stop containers.
 * Develop the CLI for basic management operations.

2. **Phase 2: Health Monitoring**
 * Integrate automatic container health checks.
 * Implement automated recovery and version synchronization.

3. **Phase 3: Advanced Features**
 * Support for automatic container upgrade during DPU upgrades.
 * Enhanced logging and monitoring integration.

### 12. Testing Requirements/Design

#### 12.1. Unit Tests
* Test the Offloader CLI commands.
* Test the health monitoring and automatic recovery.

#### 12.2. Integration Tests
* Simulate DPU upgrades and verify that the offloader synchronizes container versions.
* Stress test the daemon by causing container crashes and verifying recovery.

#### 12.3. Full Integration Tests
* Test the offloader in a complete SmartSwitch setup, including upgrade scenarios and failure injection.

### 13. Open Items

1. **Automatic Rollback:** Handling scenarios where the upgraded container fails to start.
2. **Logging Enhancements:** More detailed logs for troubleshooting and auditing.
