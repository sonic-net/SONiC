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

### 1\. Revision

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 0.1 | 2025-07-16 | ctikku-nexthop | Initial Draft |

### 2\. Scope
This document outlines adding BMC support in SONiC and executing SONiC on a BMC controller for out-of-band management of the network device.

### 3\. Definitions/Abbreviations

| Term | Definition | 
| :---- | :---- |
| BMC | Baseboard Management Controller |
| NOS | Network Operating System |
| PSU | Power Supply Unit |
| CLI | Command Line Interface |
| SEL | System Event Log |

### 4\. Overview

The purpose of this HLD is to run a BMC-feature enabled SONiC image, on a BMC controller, in the network switch for out-of-band monitoring and management of the switch. It is to enhance the reliability, manageability, and automation capabilities by allowing interaction to the switch device via the BMC controller. The initial capabilities will include the ability to power cycle the main CPU and redirection of its serial console over the network. 

In the future the capabilities can be expanded to include comprehensive hardware health metrics, including telemetry data, proactive fault management, and support BMC-driven operations for device provisioning and other diagnostics actions. 

### 5\. High-Level Requirements

#### 5.1. Functional Requirements

- BMC-SONiC-OS: SONiC-OS, will execute on a BMC controller, operating in an isolated and support role to the main switch CPU. It will have its own out-of-band network access and will be independent of any resources on the main swich CPU or the NOS running on it. 

- Console: BMC-SONiC-OS will provide the capablity to redirect serial port console of the main switch CPU over its network.

- Power: BMC-SONiC-OS will provide the capablity to power cycle the main switch CPU and any other components (ex: switch ASIC, PSU, etc.) as needed.

- Events: BMC-SONiC-OS will be able to retrieve and process System Event Log (SEL) entries from main switch CPU.

#### 5.2. sonic-platform-daemons Support
- sonic-platform-daemons executing on the main NOS CPU will not require any update to support the BMC integration.

#### 5.3. sonic-utilities Support
- show commands executing on the main NOS CPU will not require any update to support the BMC integration.

#### 5.4. sonic-swss Support
- sonic-swss executing on the main NOS CPU will not require any update to support the BMC integration.

### 6.0 High Level Design
OpenBMC, a project from the Linux Foundation, provides the necessary software stack, thats widely used in the industry for BMC implementations. The OpenBMC framework will be used as the base for the BMC-SONiC-OS. Its proposed that we pull the necessary components from OpenBMC and integrate them into SONiC, while adding the necessary SONiC components to support the BMC functionality.

### 6.1.1 Boot Loader Components
OpenBMC uses the uboot as its boot loader. Its proposed that we continue to use uboot as the boot loader for BMC-SONiC-OS.

### 6.1.2 SONiC Kernel Components
Sonic Kernel will be used as the base for the BMC-SONiC-OS kernel. Its proposed to adopt the relevant kernel config options and drivers from the OpenBMC kernel and add them to the SONiC kernel.

### 6.1.3 SONiC User Space Components
The user space components from OpenBMC will be integrated into SONiC. To begin with its proposed to add

  - OpenBMC Console - https://github.com/openbmc/obmc-console as the console capture and redirection component.
  - OpenBMC BMC Web - https://github.com/openbmc/bmcweb as the RESTful API (Redfish) server component.

These components will be built as docker containers to conform to the SONiC docker based architecture.

### 7\. Restrictions/Limitations
The functionality does not exist yet. It is possible that the final implementation and areas needed to be changed may differ.
