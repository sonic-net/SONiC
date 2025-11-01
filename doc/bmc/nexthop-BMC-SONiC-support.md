# BMC Support in SONiC

## Table of Content
- [BMC Support in SONiC](#bmc-support-in-sonic)
  - [Table of Content](#table-of-content)
    - [1. Revision](#1-revision)
    - [2. Scope](#2-scope)
    - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
    - [4. Overview](#4-overview)
    - [5. High-Level Enchancements](#5-high-level-enhancements)
      - [5.1. Functional-Requirements](#51-functional-requirements)
      - [5.2. sonic-platform-daemons Support](#52-sonic-platform-daemons-support)
      - [5.3. sonic-utilities Support](#53-sonic-utilities-support)
      - [5.4. sonic-swss Support](#54-sonic-swss-support)
    - [6. Restrictions/Limitations](#6-restrictionslimitations)

### 1. Revision

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 0.1 | 2025-07-16 | ctikku-nexthop | Initial Draft |
| 0.2 | 2025-08-28 | ctikku-nexthop | Revisised draft |
| 0.3 | 2025-09-25 | chander-nexthop | Revisised draft |

### 2. Scope
This document outlines adding BMC support in SONiC and executing SONiC on a BMC controller for out-of-band management of the network device.

### 3. Definitions/Abbreviations

| Term | Definition |
| :---- | :---- |
| BMC | Baseboard Management Controller |
| NOS | Network Operating System |
| PSU | Power Supply Unit |
| CLI | Command Line Interface |
| SEL | System Event Log |

### 4. Overview

The purpose of this HLD is to run a BMC-feature enabled SONiC image, on a BMC controller, in the network switch for out-of-band monitoring and management of the switch device. It is to enhance the reliability, manageability, and automation capabilities by allowing interaction to the switch device via the BMC controller. The initial capabilities will include the ability to power cycle the main CPU and redirection of its serial console over the network.

In the future the capabilities can be expanded to include comprehensive hardware health metrics, including telemetry data, proactive fault management, and support BMC-driven operations for device provisioning and other diagnostics actions.

### 5. High-Level Requirements

#### 5.1. Functional Requirements

##### 5.1.1 Baseboard Management Controller (BMC)
- The BMC will be a dedicated hardware component, separate from the main switch CPU.
- It will have its own Operating System, running independently from that of the main switch CPU.
- It will have its own management network port for out-of-band management.
- It will have its own serial port, separate from that of the main switch system.

##### 5.1.2 BMC Hardware
- The BMC controller will have its own CPU, memory, storage, and network port.
- SOC: Aspeed 2720 chip (arm64), Memory: 4GB, Storage: 32GB eMMC, Network: 1Gbps.
- The main switch CPU can operate with or without the presence of the BMC controller.
- The BMC controller can operate with or without the presence of the main switch CPU.

##### 5.1.3 Operating System (OS)
- The operating system running on the BMC will be called BMC-SONiC-OS.
- BMC-SONiC-OS image will be built from the SONiC-OS codebase: https://github.com/sonic-net/sonic-buildimage.git
- All changes related to BMC functionaliy will be committed back into the same git repository.
- The BMC-SONiC-OS image will leverage SONiC-OS build tools and processes, but build with differnent flags.
- There will be no changes to the SONiC-OS image build steps, functionality or the image itself.
- BMC-SONiC-OS will include BMC functionality, similar to SONiC-OS, in the docker container format.
- BMC-SONiC-OS will remove switching functionality and associated docker containers from its image.

##### 5.1.4 Out-of-Band Management (OOB Management)
- BMC-SONiC-OS running on BMC, will contain its own management network port and network IP address.
- BMC-SONiC-OS will allow connection to it using standard network protocols (ex: SSH)
- BMC-SONiC-OS will allow the main switch CPU to be managed (reboot, power cycled) from the BMC controller.
- Rebooting or power cycling of main switch CPU will not affect the BMC controller.
- Rebooting or power cycling of BMC controller will not affect the main switch CPU.

##### 5.1.5 Serial Console
- BMC will have its own serial port (UART), separate from that of the main switch system.
- The physical serial port on the front panel of the device can be "attached" to the BMC or the main switch CPU.
- Fixed hot keys will be used to swap between the two serial UART that connect to the front panel.

##### 5.1.6 OBMC Console
- BMC-SONiC-OS will use obmc-console for console services: https://github.com/openbmc/obmc-console
- BMC-SONiC-OS will log the serial console output from the main switch CPU to a file for later access.
- Log files will be managed using compression and rotation, similar to syslog.
- Access to the switch CPU console will also be available from the BMC when connected to it over the network.

##### 5.1.7 OBMC Web
- BMC-SONiC-OS will use OpenBMC Web - https://github.com/openbmc/bmcweb as the RESTful API (Redfish) server.
- bmcweb will be used to provide a web interface to the switch CPU console.

#### 5.2 BMC Components deployment
- BMC-SONiC-OS will deploy the BMC functionality as docker containers.
- BMC-SONiC-OS will use kubernetes for container orchestration.

#### 5.3. sonic-platform-daemons Support
- sonic-platform-daemons executing on the main NOS CPU will not require any update to support the BMC integration.

#### 5.4. sonic-utilities Support
- show commands executing on the main NOS CPU will not require any update to support the BMC integration.

#### 5.5. sonic-swss Support
- sonic-swss executing on the main NOS CPU will not require any update to support the BMC integration.

### 6. Boot Loader Components
- BMC-SONiC-OS will use uboot as the boot loader.

### 7. Restrictions/Limitations
The functionality does not exist yet. It is possible that the final implementation and areas needed to be changed may differ.
