# gNOI HLD for System APIs #

# High Level Design Document

#### Rev 0.1

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
- [Overview](#overview)
- [Requirements](#2-requirements)
- [Architecture Design](#3-architecture-design)
- [High Level Design](#4-high-level-design)
- [SAI API](#sai-api)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
- [Open/Action items - if any](#openaction-items---if-any)

### Revision

| Rev  | Rev Date   | Author(s)          | Change Description |
|------|------------|--------------------|--------------------|
| v0.2 | 01/07/2025 | Neha Das (Google)   | Removed non-Reboot gNOI APIs |
| v0.1 | 07/22/2024 | Neha Das (Google)   | Initial version |

## Scope

This document describes the high level design of adding the capability to support gNOI APIs for Reboot services in the telemetry server. 
It provides the definition as well as the front end and back end implementation for the gNOI services needed in the SONIC framework. The details of the underlying gNMI server design are captured [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md) and the host service DBUS communication is captured in a separate [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md).

The System RPCs covered in this doc include: Reboot, RebootStatus, CancelReboot

## Definitions/Abbreviations

- [gNOI](https://github.com/openconfig/gnoi) : gRPC Network Operations Interface
- API : Application Programming Interface
- SONiC: Software for Open Networking in the Cloud
- UMF : Unified Management Framework
- SAI: Switch Abstraction Interface
- FE: Frontend
- BE: Backend

## Overview

gNOI defines a set of gRPC-based microservices for executing operational commands on network devices as an alternative to using CLI commands for the same. 
These RPC services are supported through OpenConfig and are defined through protobuf in [OpenConfig](https://github.com/openconfig/gnoi)
The target device will listen on a specific TCP port(s) to expose the collection of gNOI services. The standard port for gNOI is 9339, which is the same as the gNMI server.

## Requirements

Any client should be able to connect to these gNOI services at the IP of the target device and the port of the service, provided they have the necessary authentication and authorization privileges. 

## Architecture Design

This feature does not change the SONiC Architecture but leverages the existing gNMI/telemetry server interface design. gNOI requests made by clients are verified and serviced by the gNMI UMF server after which they are sent to the corresponding Backend entity to process through DBUS communication to the host service. The details of the Docker to Host communication through DBUS are added [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md)

![gnoi_dbus](https://github.com/user-attachments/assets/2b33a978-36b7-439f-810f-65339d0355f7)

In the above picture “SONiC Host Service” and “DBUS” are entities executing directly on the host (as opposed to within a container). DBUS is a system daemon facilitating IPC between processes and is used for communication between containers and the SONiC Host Service. SONiC Host Service is a host process fulfilling container requests that require host access. The host service is python based and has a module plugin style architecture. The Redis database is used as an IPC mechanism between containers.

## High-Level Design


### gNOI System

The details of the System Reboot API design is captured in a separate [HLD](https://github.com/sonic-net/SONiC/pull/1489/). The OpenConfig [system.proto](https://github.com/openconfig/gnoi/blob/main/system/system.proto) defines Reboot, CancelReboot and RebootStatus RPCs within the system service. These RPCs can be used to start, cancel and check the status of reboot on a target.

```
service System {
  // Reboot causes the target to reboot, possibly at some point in the future.
  // If the method of reboot is not supported then the Reboot RPC will fail.
  // If the reboot is immediate the command will block until the subcomponents
  // have restarted.
  // If a reboot on the active control processor is pending the service must
  // reject all other reboot requests.
  // If a reboot request for active control processor is initiated with other
  // pending reboot requests it must be rejected.
  rpc Reboot(RebootRequest) returns (RebootResponse) {}

  // RebootStatus returns the status of reboot for the target.
  rpc RebootStatus(RebootStatusRequest) returns (RebootStatusResponse) {}

  // CancelReboot cancels any pending reboot request.
  rpc CancelReboot(CancelRebootRequest) returns (CancelRebootResponse) {}

  // Time returns the current time on the target.  Time is typically used to
  // test if a target is actually responding.
  rpc Time(TimeRequest) returns (TimeResponse) {}
}

// A RebootRequest requests the specified target be rebooted using the specified
// method after the specified delay.  Only the COLD method with a delay of 0
// is guaranteed to be accepted for all target types.
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

// A RebootMethod determines what should be done with a target when a Reboot is
// requested.  Only the COLD method is required to be supported by all
// targets.  A target should return 'INVALID_ARGUMENT` if UNKNOWN or any other
// unsupported method is called.
//
// It is vendor defined if a WARM reboot is the same as an NSF reboot.
enum RebootMethod {
  UNKNOWN = 0;     // Invalid default method.
  COLD = 1;        // Shutdown and restart OS and all hardware.
  POWERDOWN = 2;   // Halt and power down, if possible.
  HALT = 3;        // Halt, if possible.
  WARM = 4;        // Reload configuration but not underlying hardware.
  NSF = 5;         // Non-stop-forwarding reboot, if possible.
  // RESET method is deprecated in favor of the gNOI FactoryReset.Start().
  reserved 6;
  POWERUP = 7;     // Apply power, no-op if power is already on.
}

// A CancelRebootRequest requests the cancelation of any outstanding reboot
// request.
message CancelRebootRequest {
  string message = 1;      // informational reason for the cancel
  repeated types.Path subcomponents = 2; // optional sub-components.
}

message CancelRebootResponse {
}

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

// A TimeRequest requests the current time accodring to the target.
message TimeRequest {
}

message TimeResponse {
  uint64 time = 1;           // Current time in nanoseconds since epoch.
}

```

The gNOI server performs sanity checks after receiving the requests, and rejects if it fails (and `force` is not set). For example, we should reject requests if:
- the supplied reboot method is not supported in the platform,
- parameters are out range (e.g., reboot after 1year), etc.

The Reboot Request Succeeds when:
- The gNOI server validates the request,
- checks that no requests are pending/ active, and
- writes the data successfully to the DB.
- Once notified, the back end will act on the operation independently.

![reboot](https://github.com/user-attachments/assets/2979e81e-ab88-4cd6-8ff6-6e651c9600e0)

The design for warmboot through the gNOI System.Reboot service is covered in the [Warmboot Manager HLD](https://github.com/akarshgupta25/SONiC-NSF-Mgr-HLD/blob/9dd1ade0b48ce96d513468a54bf794efa43a9f54/doc/warm-reboot/Warmboot_Manager_HLD.md)


### SAI API

No change in SAI API.


### Warmboot and Fastboot Design Impact

No effect on warm/fast boot

### Restrictions/Limitations

### Testing Requirements/Design

In this section, we discuss both manual and automated testing strategies.

#### Manual Tests
CLI
UMF has a gnoi_client CLI tool which can be used to invoke service RPCs on the switch. This would include adding support for both JSON and proto formats of requests.

#### Automated Tests
Component Tests
For gNOI logic implementation in UMF, we will use the existing component test infrastructure for testing by adding UTs for individual API per supported gNOI service.

End-to-End Tests
These tests would invoke gNOI requests from the client to verify expected behaviour for gNOI services and are implemented on the Thinkit testing infrastructure.

### Open/Action items - if any
