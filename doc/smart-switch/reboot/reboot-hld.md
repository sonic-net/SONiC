#  Smart Switch Reboot High Level Design

## Table of Contents ##

- [Smart Switch Reboot Design](#smart-switch-reboot-design)
  - [Table of Contents](#table-of-contents)
  - [Revision](#revision)
  - [Glossory](#glossary)
  - [Overview](#overview)
  - [Assumptions](#assumptions)
  - [Requirements](#requirements)
  - [Methods of Switch and DPU Reboot](#methods-of-switch-and-dpu-reboot)
  - [DPU reboot sequence](#dpu-reboot-sequence)
  - [Switch reboot sequence](#switch-reboot-sequence)
  - [High Level Design](#high-level-design)
    - [ModuleBase Class API enhancement](#modulebase-class-api)
    - [ModuleBase Class new APIs](#modulebase-class-new-apis)
    - [NPU platform.json](#npu-platformjson)
    - [GNOI API implementation](#gnoi-api-implementation)
    - [reboot.py script modifications](#rebootpy-script-modifications)
    - [Error handling and exception scenarios](#error-handling-and-exception-scenarios)
  - [Test plan](#test-plan)

## Revision ##

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 05/16/2024 | Vasundhara Volam | Initial version    |
| 0.2 | 05/29/2024 | Vasundhara Volam | Update images and APIs |

## Glossory ##

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| ASIC  | Application-Specific Integrated Circuit   |
| DPU   | Data Processing Unit                      |
| GNMI  | gRPC Network Management Interface         |
| GNOI  | gRPC Network Operations Interface         |
| NPU   | Network Processing Unit                   |
| PCI-E | Peripheral Component Interconnect Express |

## Overview ##

Smart Switch aims to provide a full suite of network functionality, like traditional network devices, but with the flexibility
and scalability of cloud-based services. It consists of one switch ASIC (NPU) and multiple DPUs. The DPU ASICs are only
connected to the NPU, and all front panel ports are connected to the NPU. The DPU also connects to the SmartSwitch CPU via PCI-E
interfaces, allowing the Switch CPU to control DPUs through these interfaces.

Each DPU will have one internal management IP which is used for internal communications, such as Redis database and zmq. This
internal communication is also used between NPU and DPU, and between DPUs.

This document provides high level design of reboot sequence of a SmartSwitch with multiple DPUs and single DPU reboot sequence
through GNOI API.

## Assumptions ##

Smart Switch supports only cold-reboot and does not support warm-reboot as of today.

## Requirements ##

1. NPU host is running GNMI service to communicate with DPU.
2. DPU host is running GNMI server to listen to GNOI client requests.
3. Each DPU is assigned an IP address to communicate from NPU.

## Methods of Switch and DPU Reboot ##

The switch or DPU can be rebooted using either the CLI or during an image upgrade. The reboot can be initiated in two ways.

1. Performing a complete SmartSwitch reboot, which restarts the NPU and all DPUs.
2. Rebooting a specific DPU by specifying its ID.

In addition to the aforementioned causes of graceful reboots, a switch or DPU could be rebooted due to events such as power failures, kernel panics, etc.

## DPU reboot sequence ##

<p align="center"><img src="./images/dpu-reboot-seq.svg"></p>

DPUs are internally connected to the NPU via PCI-E bridge. Below is the reboot sequence for rebooting a specific DPU:

* Upon receiving a reboot CLI command to restart a particular DPU, the NPU transmits a GNOI Reboot API signal with reboot method set to ‘HALT’, instructing
the DPU to terminate all services.

* Upon dispatching the Reboot API, the NPU issues the RebootStatus API to monitor whether the DPU has terminated all services except GNMI and database
service, continuing until the timeout is reached. Once the DPU successfully terminates all services, it responds to the RebootStatus API with STATUS_SUCCESS.
Until the services are terminated gracefully, DPU response RebootStatusResponse with STATUS_RETRIABLE_FAILURE status.

* Subsequently, the NPU detaches the DPU PCI. Detachment can be achieved either by a vendor specific API or via sysfs
(echo 1 > /sys/bus/pci/devices/XXXX:XX:XX.X/remove).

* Next, the NPU triggers a platform vendor API to initiate the reboot process for the DPU.

* The NPU either immediately rescans the PCI upon return or after a timeout period. Rescan of the PCI could be achieved either by calling vendor specific
API or via sysfs (echo 1 > /sys/bus/pci/devices/XXXX:XX:XX.X/rescan).

## Switch reboot sequence ##

<p align="center"><img src="./images/smartswitch-reboot-seq.svg"></p>

The following outlines the reboot procedure for the entire Smart Switch:

* When the NPU receives a reboot command via the CLI to restart the SmartSwitch, it initiates the reboot sequence.

* The NPU sends a GNOI Reboot API signal to all connected DPUs in parallel using multiple threads. This signal instructs the DPUs to gracefully terminate all
services, excluding the GNMI server, in preparation for the reboot.

* Upon dispatching the Reboot API, the NPU issues the RebootStatus API to monitor whether the DPU has terminated all services except GNMI and database
service, continuing until the timeout is reached. Once the DPU successfully terminates all services, it responds to the RebootStatus API with STATUS_SUCCESS.
Until the services are terminated gracefully, DPU response RebootStatusResponse with STATUS_RETRIABLE_FAILURE status.

* Following the confirmation from the DPUs, the NPU proceeds to detach the PCI devices associated with the DPUs. This detachment is achieved either by calling
vendor specific API or by issuing a command through the sysfs interface, specifically by echoing '1' to the /sys/bus/pci/devices/XXXX:XX:XX.X/remove file
for each DPU.

* With the DPUs prepared for reboot, the NPU triggers a platform vendor API to initiate the reboot process for the DPUs.

* After receiving the response from the DPUs, the NPU proceeds to reboot itself to complete the overall reboot procedure.

* Upon successful reboot, the NPU resumes operation. As part of the post-reboot process, the NPU may choose to rescan the PCI devices. This rescan operation,
performed either by invoking vendor API or by echoing '1' to the /sys/bus/pci/devices/XXXX:XX:XX.X/rescan file, ensures that all PCI devices are properly
recognized and initialized.

## High-Level Design ##

### ModuleBase Class API ###

reboot(self, reboot_type):
```
Define new reboot_type as MODULE_REBOOT_DPU for DPU only reboot and MODULE_REBOOT_SMARTSWITCH for entire switch reboot.
```

This API is defined in [smartswitch-pmon.md](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/pmon/smartswitch-pmon.md#:~:text=reboot(self%2C%20reboot_type)%3A)

### ModuleBase Class new APIs ###

pci_detach_dpu(self):
```
Detaches the DPU PCI device from the NPU. In the case of non-smart-switch chassis, no action is taken.

Returns:
    True
```

pci_reattach_dpu(self):
```
Rescans the PCI bus and attach the DPU back to NPU. In the case of non-smart-switch chassis, no action is taken.

Returns:
    True
```

get_dpu_bus_info(self, dpu_id):
```
For a given DPU id, retrieve the PCI bus information. In the case of non-smart-switch chassis, no action is taken.

Returns:
    Returns the PCI bus information in BDF format like "[DDDD:]:BB:SS.F"
```

### NPU platform.json ###

Introduce a new parameter, <span style="color:blue">'dpu_halt_services_timeout'</span>, to specify the duration(in secs) for waiting for the DPU to terminate all services, as defined by
the platform vendor. If the DPU fails to respond within this timeout, the NPU will proceed with the reboot sequence. If no timeout is explicitly
defined, a default timeout will be used.

```json
{
    .
    .
    "dpu_halt_services_timeout" : "TBD"

    "DPUs" : [
        {
            "dpu0": {
                "bus_info" : "[DDDD:]BB:SS.F"
            }
        },
        {
            "dpu1": {
                "bus_info" : "[DDDD:]BB:SS.F"
            }
        },
        .
        .
        {
            "dpuX": {
                "bus_info" : "[DDDD:]BB:SS.F"
            }
        }
    ]
    .
    .
}
```

### GNOI API implementation ###

According to the RebootRequest protocol outlined below, we will utilize the HALT command in the RebootMethod to terminate services on the DPU.
When the NPU sends the RebootRequest with the HALT RebootMethod to the DPU, it will kill all services except GNMI and database services.

```
*Arguments*: type of reboot (cold, warm, etc.), delay before issuing reboot, string describing reason for reboot, option to force reboot if sanity checks fail.

rpc Reboot(RebootRequest) returns (RebootResponse) {}

message RebootRequest {
  RebootMethod method = 1;
  // Delay in nanoseconds before issuing reboot.
  uint64 delay = 2;
  // Informational reason for the reboot.
  string message = 3;
  // Optional sub-components to reboot.
  repeated types.Path subcomponents = 4;
  // Force reboot if sanity checks fail. (ex. uncommited configuration)
  bool force = 5;
}

message RebootResponse {
}

enum RebootMethod {
  UNKNOWN = 0;     // Invalid default method.
  COLD = 1;        // Shutdown and restart OS and all hardware.
  POWERDOWN = 2;   // Halt and power down, if possible.
  *HALT = 3;*        // Halt, if possible.
  WARM = 4;        // Reload configuration but not underlying hardware.
  NSF = 5;         // Non-stop-forwarding reboot, if possible.
  // RESET method is deprecated in favor of the gNOI FactoryReset.Start().
  reserved 6;
  POWERUP = 7;     // Apply power, no-op if power is already on.
}
```

Upon sending the RebootRequest RPC to the DPU, the NPU will commence polling using RebootStatusRequest. If the DPU has effectively terminated the
services, it responds with STATUS_SUCCESS set in the RebootStatusResponse. Otherise, it will send the response with STATUS_RETRIABLE_FAILURE status.

```
rpc RebootStatus(RebootStatusRequest) returns (RebootStatusResponse) {}

message RebootStatusRequest {
  repeated types.Path subcomponents = 1; // optional sub-component.
}

message RebootStatusResponse {
  bool active = 1;      // If reboot is active.
  uint64 wait = 2;      // Time left until reboot.
  uint64 when = 3;      // Time to reboot in nanoseconds since the epoch.
  string reason = 4;    // Reason for reboot.
  uint32 count = 5;     // Number of reboots since active.
  RebootMethod method = 6; // Type of reboot.
  RebootStatus status = 7; // Applicable only when active = false.
}

message RebootStatus {
  enum Status {
    STATUS_UNKNOWN = 0;
    STATUS_SUCCESS = 1;
    STATUS_RETRIABLE_FAILURE = 2;
    STATUS_FAILURE = 3;
  }
  Status status = 1;
  string message = 2;
}
```

### reboot CLI modifications ###

Introduce a new parameter <span style="color:blue">'-d'</span> to the reboot command for specifying the DPU ID requiring a reboot. If the chassis is
not a smart switch, this action will have no effect. If the reboot command is executed without specifying any '-d' option, the entire switch will
be rebooted.

```
Usage /usr/local/bin/reboot [options]
    Request rebooting the device. Invoke platform-specific tool when available.
    This script will shutdown syncd before rebooting.

    Available options:
        -h, -? : getting this help
        -f     : execute reboot force
        -d     : DPU ID
```

### reboot.py script modifications ###

* Within the reboot() function, incorporate a verification step to invoke is_smartswitch(). Should is_smartswitch() yield false, proceed with the current
implementation. However, if is_smartswitch() returns true, invoke the new reboot_smartswitch() function, passing a parameter to specify whether it's
a complete switch reboot or targeting a specific DPU.

* If the reboot_type is ‘REBOOT_TYPE_WARM’ and is_smartswitch is true, return a warning that this type of reboot is not supported.

* Add a new reboot_smartswitch() function to reboot either the entire switch or a particular DPU, which takes DPU ID as an argument that
needs a reboot.

```
def reboot_smartswitch(duthost, localhost, reboot_type='cold', reboot_dpu='false', dpu_id='0')
    """
    reboots SmartSwitch or a DPU
    :param duthost: DUT host object
    :param localhost:  local host object
    :param reboot_type: reboot type (cold)
    :param reboot_dpu: reboot dpu or switch (true, false)
    :param dpu_id: reboot the dpu with id, valid only if reboot_dpu is true.
```

### Error handling and exception scenarios ###

* If the GNMI service is not operational on the DPU or DPU is unreachable for any reason, detach the PCI, and proceed with the reboot after a timeout
upon receiving an acknowledgment.

* After the DPU reboots, if the DPU PCI fails to reconnect for any reason, an error-handling mechanism should be in place to restore the DPU.

* If a DPU fails to reboot during a switch reboot, the NPU should attempt to recover the DPU and log any errors that occur.

* In the event of power failure, a power-cycle due to a kernel panic, or any other unknown reason, both the DPU and NPU will undergo an ungraceful reboot.

## Test plan ##

Presented below is the test plan within the ```sonic-mgmt``` framework for the smart switch reboot.


| Event                                     | NPU reboot sequence | DPU reboot sequence |
| ----------------------------------------- | ------------------- | ------------------- |
| Power-On                                  | Graceful boot       | Graceful boot       |
| Planned cold reboot of Smart Switch       | Graceful reboot     | Graceful reboot     |
| Planned cold reboot of DPU                | -                   | Graceful reboot     |
| Planned power-cycle of Smart Switch       | Graceful reboot     | Graceful reboot     |
| Planned power-cycle of DPU                | -                   | Graceful reboot     |
| Unplanned DPU power failure               | -                   | Ungraceful reboot   |
| Unplanned Smart Switch power failure      | Ungraceful reboot   | Ungraceful reboot   |
| Unplanned Smart Switch System Crash       | Ungraceful reboot   | Ungraceful reboot   |
| Unplanned DPU System Crash                | -                   | Ungraceful reboot   |

The test scenarios above ensure that both the NPU and all DPUs are fully operational following any type of reboot. Furthermore, the tests verify the
functionality of PCI communication between NPU and DPUs.
