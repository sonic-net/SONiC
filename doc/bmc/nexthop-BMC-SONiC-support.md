# BMC Support in SONiC

## Table of Content
## Table of Content
- [BMC Support in SONiC](#bmc-support-in-sonic)
  - [Table of Content](#table-of-content)
  - [1. Revision](#1-revision)
  - [2. Scope](#2-scope)
  - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
  - [4. Overview](#4-overview)
  - [5. High-Level Requirements](#5-high-level-requirements)
    - [5.1. Functional Requirements](#51-functional-requirements)
      - [5.1.1 Baseboard Management Controller (BMC)](#511-baseboard-management-controller-bmc)
      - [5.1.2 BMC Hardware](#512-bmc-hardware)
      - [5.1.3 Operating System (OS)](#513-operating-system-os)
      - [5.1.4 Out-of-Band Management (OOB Management)](#514-out-of-band-management-oob-management)
      - [5.1.5 Serial Console](#515-serial-console)
      - [5.1.6 OBMC Console](#516-obmc-console)
      - [5.1.7 OBMC Web](#517-obmc-web)
    - [5.2 BMC Components Deployment](#52-bmc-components-deployment)
  - [6. Boot Loader Components](#6-boot-loader-components)
  - [7. eMMC Writes](#7-emmc-writes)
  - [8. Restrictions/Limitations](#8-restrictionslimitations)


### 1. Revision

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 0.1 | 2025-07-16 | ctikku-nexthop  | Initial Draft |
| 0.2 | 2025-08-28 | ctikku-nexthop  | Revised Draft |
| 0.3 | 2025-09-25 | chander-nexthop | Revised Draft |
| 0.4 | 2025-11-11 | chinmoy-nexthop | Revised Draft |
| 0.5 | 2026-02-02 | chander-nexthop | Revised Draft |

### 2. Scope
This document describes the addition of BMC support in SONiC and the execution of SONiC on a BMC controller for out-of-band management of network devices. This design supports Aspeed AST2720 platform, and can be extended to other BMC chipsets.

### 3. Definitions/Abbreviations

| Term | Definition |
| :---- | :---- |
| BMC | Baseboard Management Controller |
| NOS | Network Operating System |
| PSU | Power Supply Unit |
| CLI | Command Line Interface |
| SEL | System Event Log |

### 4. Overview

The purpose of this HLD is to enable a SONiC image with BMC functionality to run on a BMC controller within a network switch, providing out-of-band monitoring and management of the device. This enhancement improves reliability, manageability, and automation by enabling interaction with the switch through the BMC controller.
Initial capabilities include power control of the main CPU and redirection of its serial console over the network.

Future enhancements may include advanced hardware health monitoring, telemetry data collection, proactive fault management, and BMC-driven operations for provisioning and diagnostics.

### 5. High-Level Requirements

#### 5.1. Functional Requirements

##### 5.1.1 Baseboard Management Controller (BMC)
- The BMC will be a dedicated hardware component, independent of the main switch CPU.
- It will operate on its own OS, separate from the main switch CPU’s OS.
- It will include a dedicated management network port for out-of-band management.
- It will have an independent serial port, separate from the main switch system.
- The BMC uses eMMC storage; therefore, write operations must be minimized.
- The BMC will provide staged boot control, manage main system power on/off, and handle leak detection and management.
- The BMC will support a network device over USB to connect to the x86 CPU for a secure private network between the x86 and the BMC.

##### 5.1.2 BMC Hardware
- The BMC controller will include its own CPU, memory, storage, and network port.
- SOC: Aspeed 2720 (arm64), Memory: 4GB, Storage: 32GB eMMC.
- The main switch CPU can operate independently of the BMC controller.
- The BMC controller can also operate independently of the main switch CPU.

##### 5.1.3 Operating System (OS)
- The operating system running on the BMC will be referred to as **BMC-SONiC-OS**.
- **BMC-SONiC-OS** will be built from the SONiC-OS [sonic-buildimage]( https://github.com/sonic-net/sonic-buildimage.git) codebase.
- All BMC-related enhancements will be committed to the same repository.
- The image will use SONiC build tools and workflows but with BMC-specific build flags.
- The SONiC-OS image build process and functionality will remain unchanged.
- **BMC-SONiC-OS** will include BMC-specific services packaged as Docker containers.
- Switching-related components and associated containers will be excluded from the BMC image.
- A multi-port ethernet switch may connect the BMC and main CPU. The switch will be managed by the BMC, for example, to configure VLANs for traffic separation.
- Support will be added to enable a USB-based network interface for connectivity between the x86 and the BMC.

##### 5.1.4 Out-of-Band Management (OOB Management)
- **BMC-SONiC-OS** will provide a dedicated management network port and IP address.
- It will support standard network access protocols (e.g., SSH).
- It will allow management of the main switch CPU (e.g., reboot or power cycle) from the BMC controller.
- Rebooting or power cycling the main switch CPU will not impact the BMC.
- Rebooting or power cycling the BMC will not affect the main switch CPU.

##### 5.1.5 Serial Console
- The BMC will have its own UART-based serial port, separate from the main switch.
- The front-panel serial port can be dynamically switched between the BMC and main CPU.
- Predefined hotkeys will be used to toggle between the two UART interfaces.

##### 5.1.6 OBMC Console
- **BMC-SONiC-OS** will use [obmc-console](https://github.com/openbmc/obmc-console) for console management.
- A clone of this project will be created and added as a submodule in the sonic-buildimage repository.
- The switch CPU console will be accessible by invoking the obmc-console-client inside the obmc-console docker.
- The switch CPU console will also be accessible over the network via ssh to a specific port on the BMC.
- It will capture and log the main switch CPU’s serial console output for later review.
- Log rotation, compression and export to an external server will be supported

##### 5.1.7 OBMC Web
- **BMC-SONiC-OS** will use [OpenBMC Web (bmcweb)](https://github.com/openbmc/bmcweb) as the RESTful (Redfish) API server.
- A clone of this project will be created and added as a submodule in the sonic-buildimage repository.
- A new module SONiC-Dbus-Bridge will be created to populate necessary state from REDIS and other data sources into DBus. This way bmcweb can continue to read dbus paths.
- **bmcweb** will provide a web-based interface to the switch CPU console.
- The **staged boot process** will be managed through the Redfish API.
- **Redfish API** for Power On/Off control of the main system.
- **Redfish API** for leak detection and management.
    - The leak detection mechanism within the switch.

#### 5.2 BMC Components Deployment
- **BMC-SONiC-OS** will deploy BMC functionalities as Docker containers.
- **Kubernetes** will be used for container orchestration.

### 6. Boot Loader Components
- **BMC-SONiC-OS** will use **U-Boot** as the boot loader.
- The image will be installed on an **eMMC partition**.
- The **OpenBMC image** will continue to serve as the **golden firmware** in the SPI boot flash
- **Initial Load Process**:
  - Boot the SONiC kernel with a minimal initramfs from U-Boot to launch a shell, and use the included script to download the image via TFTP and flash it to the eMMC.
- **Subsequent Boots**:
  - Once the image is installed, the system can boot directly from the eMMC, eliminating the need to download or reinstall the image over TFTP.
  - The image will support the sonic-installer utility for image management, including adding a new image, removing an existing image, and selecting the default image for boot.
  - There will be only one partition in the eMMC and multiple images can be installed in that partition, conforming to the standard SONiC behaviour (Ex: /host/image-1, /host/image-2, etc.).
- The boot process may be refined in future revisions to improve efficiency and usability.

### 7. eMMC Writes
  - eMMC writes are minimized to protect the device from wear.

### 8. Restrictions/Limitations
- This functionality is under development. The final implementation details and affected areas may differ from this design.
