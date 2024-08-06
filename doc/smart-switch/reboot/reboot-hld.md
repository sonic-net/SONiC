#  Smart Switch Reboot High Level Design

## Table of Contents ##

- [Smart Switch Reboot Design](#smart-switch-reboot-design)
  - [Table of Contents](#table-of-contents)
  - [Revision](#revision)
  - [Glossary](#glossary)
  - [Overview](#overview)
  - [Assumptions](#assumptions)
  - [Requirements](#requirements)
  - [Methods of Switch and DPU Reboot](#methods-of-switch-and-dpu-reboot)
  - [DPU reboot sequence](#dpu-reboot-sequence)
  - [Switch reboot sequence](#switch-reboot-sequence)
  - [High Level Design](#high-level-design)
    - [ModuleBase Class API](#modulebase-class-api)
    - [ModuleBase Class new APIs](#modulebase-class-new-apis)
    - [NPU platform.json](#npu-platformjson)
    - [GNOI API implementation](#gnoi-api-implementation)
    - [reboot CLI modifications](#reboot-cli-modifications)
    - [reboot script modifications](#reboot-script-modifications)
    - [PCIe daemon modifications](#pcie-daemon-modifications)
    - [Error handling and exception scenarios](#error-handling-and-exception-scenarios)
  - [Test plan](#test-plan)
  - [References](#references)

## Revision ##

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 05/16/2024 | Vasundhara Volam | Initial version    |
| 0.2 | 05/29/2024 | Vasundhara Volam | Update images and APIs |
| 0.3 | 06/10/2024 | Vasundhara Volam | Minor changes based on discussion with the community |
| 0.4 | 07/29/2024 | Vasundhara Volam | Add PCIe daemon changes |

## Glossory ##

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| ASIC  | Application-Specific Integrated Circuit   |
| DPU   | Data Processing Unit                      |
| gNMI  | gRPC Network Management Interface         |
| gNOI  | gRPC Network Operations Interface         |
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

1. NPU host is running gNOI client to communicate with DPU.
2. DPU host is running gNOI server to listen to gNOI client requests.
3. Each DPU is assigned an IP address to communicate from NPU.

## Methods of Switch and DPU Reboot ##

The switch or DPU can be rebooted using either the CLI or during an image upgrade. The reboot can be initiated in two ways.

1. Performing a complete SmartSwitch reboot, which restarts the NPU and all DPUs.
2. Rebooting a specific DPU by specifying its ID.

In addition to the previously mentioned causes of graceful reboots, a switch or DPU may also reboot due to events such as power failures during DPU power-up, kernel panics, and other similar incidents.

## DPU reboot sequence ##

<p align="center"><img src="./images/dpu-reboot-seq.svg"></p>

DPUs are internally connected to the NPU via PCI-E bridge. Below is the reboot sequence for rebooting a specific DPU:

* Upon receiving a reboot CLI command to restart a particular DPU, the NPU transmits a gNOI Reboot API signal with reboot method set to ‘HALT’, instructing
the DPU to terminate all services.

* Upon dispatching the Reboot API, the NPU issues the RebootStatus API to monitor whether the DPU has terminated all services except gNOI and database
service, continuing until the timeout is reached. Once the DPU successfully terminates all services, it responds to the RebootStatus API with STATUS_SUCCESS.
Until the services are terminated gracefully, DPU response RebootStatusResponse with STATUS_RETRIABLE_FAILURE status.

* Subsequently, the NPU detaches the DPU PCI with a vendor defined API. If a vendor specific API is not defined, detachment is done via sysfs
(echo 1 > /sys/bus/pci/devices/XXXX:XX:XX.X/remove).

* Next, the NPU triggers a platform vendor reboot API to initiate the reboot process for the DPU.

* The NPU either immediately rescans the PCI upon return or after a timeout period. Rescan of the PCI is achieved by vendor defined API. If vendor specific API
is not defined, then rescan is done via sysfs (echo 1 > /sys/bus/pci/rescan).

## Switch reboot sequence ##

<p align="center"><img src="./images/smartswitch-reboot-seq.svg"></p>

The following outlines the reboot procedure for the entire Smart Switch:

* When the NPU receives a reboot command via the CLI to restart the SmartSwitch, it initiates the reboot sequence.

* The NPU sends a gNOI Reboot API signal to all connected DPUs in parallel using multiple threads. This signal instructs the DPUs to gracefully terminate all
services, excluding the gNOI server and also database, in preparation for the reboot.

* Upon dispatching the Reboot API, the NPU issues the RebootStatus API to monitor whether the DPU has terminated all services except GNMI and database
service, continuing until the timeout is reached. Once the DPU successfully terminates all services, it responds to the RebootStatus API with STATUS_SUCCESS.
Until the services are terminated gracefully, DPU response RebootStatusResponse with STATUS_RETRIABLE_FAILURE status.

* Following the confirmation from the DPUs, the NPU proceeds to detach the PCI devices associated with the DPUs. This detachment is achieved either by calling
vendor specific API or by issuing a command through the sysfs interface, specifically by echoing '1' to the /sys/bus/pci/devices/XXXX:XX:XX.X/remove file
for each DPU.

* With the DPUs prepared for reboot, the NPU triggers a platform vendor API to initiate the reboot process for the DPUs. Vendor API reboots a single DPU, but the NPU spawns multiple threads to reboot DPUs in parallel.

* DPUs will send an acknowledgment to the NPU and then undergo a reboot. After receiving the acknowledgment from the DPUs, the NPU will proceed to reboot itself to complete the overall reboot procedure. The vendor-specific reboot API should include an error handling mechanism to manage DPU reboot failures. Additionally log all the failures. DPUs will be in DPU_READY state, if the reboot happened successfully.

* Upon successful reboot, the NPU resumes operation. As part of the post-reboot process, the NPU may choose to rescan the PCI devices. This rescan operation,
performed either by invoking vendor API or by echoing '1' to the /sys/bus/pci/rescan file, ensures that all PCI devices are properly
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

get_dpu_bus_info(self, dpu_module_name):
```
For a given DPU module name, retrieve the PCI bus information. In the case of non-smart-switch chassis, no action is taken.

Returns:
    Returns the PCI bus information in BDF format like "[DDDD:]:BB:SS.F"
```

### NPU platform.json ###

Introduce a new parameter, <span style="color:blue">'dpu_halt_services_timeout'</span>, to specify the duration(in secs) for waiting for the DPU to terminate all services,
as defined by the platform vendor. If the DPU fails to respond within this timeout, the NPU will proceed with the reboot sequence. If no timeout is explicitly defined,
a default timeout will be used.

```json
{
    .
    .
    "dpu_halt_services_timeout" : "TBD"

    "DPUS" : [
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

According to the RebootRequest protocol outlined below, we will utilize the 'HALT' in the RebootMethod to terminate services on the DPU. When the NPU sends the RebootRequest
with the HALT RebootMethod to the DPU, it will invoke the /usr/local/bin/reboot script to stop all the services except GNMI server and database services. Refer to the
[gNOI reboot HLD](#https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/Warmboot_Manager_HLD.md) for design information of gNOI reboot flow to invoke the
reboot script in SONiC host services.

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

After receiving the acknowledgement for RebootRequest RPC from the DPU, the NPU starts polling with RebootStatusRequest. If the DPU has effectively terminated
the services, it responds with STATUS_SUCCESS set in the RebootStatusResponse. Otherise, it will send the response with STATUS_RETRIABLE_FAILURE status.

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

Introduce a new parameter <span style="color:blue">'-d'</span> to the reboot command for specifying the DPU module name requiring a reboot. If the chassis is
not a smart switch, this action will have no effect. If the reboot command is executed without specifying any '-d' option, the entire switch will
be rebooted.

```
Usage /usr/local/bin/reboot [options]
    Request rebooting the device. Invoke platform-specific tool when available.
    This script will shutdown syncd before rebooting.

    Available options:
        -h, -? : getting this help
        -f     : execute reboot force
        -d     : DPU module name
        -p     : pre-shutdown
```

### reboot script modifications ###

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

* NPU invokes the reboot script with "-p" option on the DPU via GNOI API to reboot the DPU. When reboot script is invoked with "-p" option,
execute all the steps except the actual reboot at the end of the script.

* When a DPU module is requested for a reboot, the reboot script will update StateDB with the reboot information according to the schema defined
below. Define a new function named update_dpu_pcie_info() for this purpose. Additionally, if the entire smart switch is undergoing a reboot,
update the same information for all the DPUs. Once the DPU is rebooted and the PCIe device is reattached, the StateDB entry will be updated accordingly.

#### PCIE_DETACH_INFO schema in StateDB

```
"PCIE_DETACH_INFO|DPU_0": {
  "value": {
    "id": "1",
    "dpu_state": "detaching",
    "bus_info" : "[DDDD:]BB:SS.F"
  }
}
```

### PCIe daemon modifications ###
The PCIe daemon will be updated to avoid logging "PCIe Device: <Device name> Not Found" messages when DPUs are undergoing a reboot, as this is a
user-initiated action.

In the [check_pci_devices()](#https://github.com/sonic-net/sonic-platform-daemons/blob/bf865c6b711833347d3c57e9d84cd366bcd1b776/sonic-pcied/scripts/pcied#L155) function,
read the State DB for the PCIE_DETACH_INFO and suppress the "device not found" warning logs during a DPU reboot when the device is intentionally detached.

### Error handling and exception scenarios ###

The following are specific error scenarios where the DPU state will not be DPU_READY.

* If the gNOI service is not operational on the DPU or DPU is unreachable for any reason, detach the PCI, and proceed with the reboot after a timeout
upon receiving an acknowledgment.

* After the DPU reboots, if the DPU PCI fails to reconnect for any reason, an error-handling mechanism should be in place to restore the DPU.

* If a DPU fails to reboot during a switch reboot, the NPU should attempt to recover the DPU and log any errors that occur.

* In the event of power failure, a power-cycle due to a kernel panic, or any other unknown reason, both the DPU and NPU will undergo an ungraceful reboot.

* In the event of a DPU reboot failure, a hardware watchdog is needed to monitor and reset the DPU. This implementation is vendor-specific.

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

## References

- [Openconfig system.proto](#https://github.com/openconfig/gnoi/blob/main/system/system.proto)
- [Warmboot Manager HLD](#https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/Warmboot_Manager_HLD.md)
- [gNOI reboot HLD](#https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/Warmboot_Manager_HLD.md)
- [PCIe daemon](#https://github.com/sonic-net/sonic-platform-daemons/blob/master/sonic-pcied/scripts/pcied)
