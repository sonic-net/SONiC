# GNMI/GNOI Splitter for Smart Switch #

## Table of Contents

### 1. Revision History

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 02/18/2025 | Dawei Huang | Initial version    |

### 2. Overview

This document describes the GNMI/GNOI Splitter for Smart Switch. The splitter is a software component that separates GNMI and GNOI traffic and forwards them to the appropriate handlers.

#### 2.1 Background

The gNMI/gNOI Splitter arises from the following two architectural background in the smartswitch:
- `Offloaded gNMI/gNOI Server`
  Due to the limited resources on the DPU, the gNMI server is offloaded onto the NPU. The gNMI server on the NPU is responsible for handling gNMI requests and responses.
  The server is running on a separate `gnmi` container on the NPU, named `gnmidpu[x]`, where `x` is the DPU number. The DPU itself still retains a `gnmi` container used for the gNOI traffic. The splitter is used to separate the gNMI and gNOI traffic and forward them to the appropriate servers.
- `DPU Isolation`
  Due to security requirement, the DPU is isolated from external network, i.e. the DPU's management interface is not accessible from external network and only accessible via the NPU. Hence we need a proxy on NPU to forward the gNOI traffic to the DPU.

#### 2.2 Scope
The scope of this document includes the design and implementation of the gNMI/gNOI Splitter, as well as its integration with the existing gNMI and gNOI servers. More specifically, this document covers the following aspects:

- Architecture
  - gNMI/gNOI Splitter, offloaded gNMI server, and gNOI server
- Configuration
  - gRPC server configuration

#### 2.3 Dependencies###
- gNMI/gNOI Servers
  The splitter relies on the GNMI and GNOI servers to handle incoming requests. The servers must be properly configured and running for the splitter to function correctly.
- Network Configuration
  The splitter requires a network configuration that allows it to receive and forward traffic to the appropriate servers, whether on NPU or DPU.

### 3. Definitions/Abbreviations

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| DPU   | Data Processing Unit                      |
| gNMI  | gRPC Network Management Interface         |
| gNOI  | gRPC Network Operations Interface         |
| NPU   | Network Processing Unit                   |
| ASIC  | Application Specific Integrated Circuit   |

### 4. Architecture

#### 4.1 Offloaded gNMI vs gNMI

The offloaded gNMI server is running on the NPU and is responsible for the following requests:

- All `gNMI` requests。
- Part of `gNOI` requests that can only be served by the NPU, such as `System.Reboot`.

The original/local `gNMI` container on the DPU is responsible for the remaining of `gNOI` requests.

![Architecture Diagram](https://www.mermaidchart.com/raw/3e126a79-0049-4051-ba30-a18251829504?theme=light&version=v0.1&format=svg){ width=40% }

#### 4.2 gNMI/gNOI Splitter

The gNMI/gNOI Splitter is a gRPC server that listens on the NPU and forwards the requests to the appropriate servers. The splitter is responsible for the following tasks:
- Receiving incoming gRPC requests.
- Determines whether the request is a gNMI or gNOI request.
  - If it is a gNOI request, whether it is a request that can only be served by the NPU.
- Forwards the request to the appropriate server.

#### 4.3 Containers and Ports
The splitter is running as a seperate gRPC server on the offloaded gNMI container on the NPU (`gnmidpu[x]`), and listens on a different port than the offloaded gNMI server.

### 5. SAI API
The gNMI/gNOI Splitter does not use any SAI APIs.

### 6. Configuration
The gNMI/gNOI Splitter is configured using the following parameters:
- `gRPC server port` (new)
  The port on which the splitter listens for incoming requests.
- per-DPU configuration
  The splitter is configured per DPU, and each DPU has its own configuration. The configuration includes the following parameters:
  - `Offloaded server port`
    The port on which the offloaded gNMI server listens for incoming requests. Requests that are bounded for the offloaded gNMI server will be forwarded to this port on the NPU (locally).
  - `DPU server address`
    The address to which the splitter forwards the gNOI requests that are not handled by the DPU gNOI server. This is typically the management IP address of the DPU.
  - `DPU server port`
    The port on which the DPU gNOI server listens for incoming requests.

### 7. Testing

#### 7.1 Unit test
The splitter is tested using unit tests to ensure that it correctly forwards requests to the appropriate servers.

#### 7.2 Integration test
The splitter is tested in an integrated environment to ensure that it works correctly with the offloaded gNMI and local gNOI servers.
