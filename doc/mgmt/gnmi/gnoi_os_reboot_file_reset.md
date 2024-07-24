# gNOI HLD for OS, Reboot, File, Factory Reset APIs #

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
| v0.1 | 07/22/2024 | Neha Das (Google)   | Initial version |

## Scope

This document describes the high level design of adding the capability to support gNOI APIs for OS, Reboot, File, Factory Reset services in the telemetry server. 
It provides the definition as well as the front end and back end implementation for the gNOI services needed in the SONIC framework. The details of the underlying gNMI server design are captured [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md) and the host service DBUS communication is captured in a separate [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md).

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

### gNOI OS

The [OS](https://github.com/openconfig/gnoi/blob/main/os/os.proto) proto is designed for switch software installation and defines APIs for OS services and provides an interface for OS installation on a Target.

```
// The OS service provides an interface for OS installation on a Target. The
// Client progresses through 3 RPCs:
//   1) Installation - provide the Target with the OS package.
//   2) Activation - activate an installed OS package.
//   3) Verification - verify that the Activation was successful.
//
...
service OS {
  // Install transfers an OS package into the Target. No concurrent Install RPCs
  // MUST be allowed to the same Target.
  ...
  rpc Install(stream InstallRequest) returns (stream InstallResponse);

  // Activate sets the requested OS version as the version which is used at the
  // next reboot, and reboots the Target if the 'no_reboot' flag is not set.
  // When booting the requested OS version fails, the Target recovers by
  // booting the previously running OS package.
  rpc Activate(ActivateRequest) returns (ActivateResponse);

  // Verify checks the running OS version. During reboot, gRPC client returns
  // the gRPC status code UNAVAILABLE while the Target is unreachable, which
  // should be retried by the client until successful. After the Target becomes
  // reachable, it should report all ready or error states normally through
  // VerifyResponse.
  //
  // On a dual Supervisor system, if the Standby Supervisor is rebooting, it
  // should be reported in the VerifyResponse via verify_standby as
  // StandbyState UNAVAILABLE.
  rpc Verify(VerifyRequest) returns (VerifyResponse);
}
```

#### gNOI OS Sequence Flow

![gnoi_install](https://github.com/user-attachments/assets/6f3c40b1-c0bc-4ea9-a991-8d0deea05a53)

Step 1. OS Install on the primary and secondary controller cards.

Install and activate a new software version on primary supervisor.

a. Issue gnoi.os.Install RPC to the chassis with InstallRequest.TransferRequest message. The message should set the version to the desired new version image, and standby_supervisor to FALSE.

Wait for the switch to respond with InstallResponse. Expect it to return TransferReady.

b. Transfer the content by issuing gnoi.os.Install rpc with InstallRequest.transfer_content message. 
  * Expect it to return InstallResponse with a TransferProgress status asynchronously at certain intervals.

c. End the transfer of software by issuing gnoi.os.Install rpc with InstallRequest.TransferEnd message. 
  * Expect the switch to return InstallResponse with a Validated message. The version in the message should be set to the one which was transferred above.

d. Activate the software by issuing gnoi.os.Activate rpc. 
  * Set the version field of the ActivateRequest message to be the same as the version specified in the TransferRequest message above.
  * Set the no_reboot flag to true.
  * Set the standby_supervisor to FALSE.

2. Install and activate the same new software version on standby supervisor:

a. Repeat the above process of TransferRequest. This time set the standby_supervisor to TRUE.

* Expect the switch to return a InstallResponse with a SyncProgress message. The switch should sync the software image from primary SUP to standby.
* Expect the sync to return a value of 100 for percentage_transferred field.
* At the end, expect the switch to return InstallResponse with a Validated message. The version in the message should be set to the one which was transferred above.

3. Activate the software by issuing gnoi.os.Activate rpc as in the case of primary supervisor.

a. Set the version field of the ActivateRequest message to be the same as the version specified in the TransferRequest message above.

b. Set the no_reboot flag to true.

c. Set the standby_supervisor to TRUE this time.

4. Reboot the switch:

a. Issue gnoi.system.Reboot

5. Verify that the supervisor image has moved to the new image:

a. Verify that the supervisor has a valid image by issuing gnoi.os.Verify rpc.

* Expect a VerifyResponse with the version field set to the version specified in messages above eventually.
* Verify the standby supervisor version.
* Expect that the VerifyResponse.verify_standby has the same version in messages above.

Configuration push verification post OS update.

Push a test configuration  using gNMI.Set() RPC with "replace operation".
If the configuration push is successful, make a gNMI.Get() RPC call and compare the configuration received with the originally pushed configuration and check if the configuration is a match. Test is a failure if either the gNMI.Get() operation fails or the configuration do not match with the one that was pushed.

The front end implementation calls the host service via the module `gnoi_os_mgmt` to remove the file on the target. HostQuery calls the corresponding D-Bus endpoint on the host and returns any error and the response body.
```
// ActivateOS initiates the operations for activating the OS (via DBUS).
// Input is the request message in JSON format.
// Back end is expected to return the response message in JSON format.
func ActivateOS(reqStr string) (string, error) {
	osMu.Lock()
	defer osMu.Unlock()
	r := HostQuery("gnoi_os_mgmt.activate", reqStr)
	return checkQueryOutput(r)
}

// VerifyOS initiates the operations for verifying the OS (via DBUS).
// Input is the request message in JSON format.
// Back end is expected to return the response message in JSON format.
func VerifyOS(reqStr string) (string, error) {
	osMu.Lock()
	defer osMu.Unlock()
	r := HostQuery("gnoi_os_mgmt.verify", reqStr)
	return checkQueryOutput(r)
}

// InstallOS initiates the operations for transferring the image (via DBUS).
// Input is the request message in JSON format.
// Back end is expected to return the response message in JSON format.
func InstallOS(reqStr string) (string, error) {
	osMu.Lock()
	defer osMu.Unlock()
	r := HostQuery("gnoi_os_mgmt.install", reqStr)
	return checkQueryOutput(r)
}
```


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


### gNOI File

The [file](https://github.com/openconfig/gnoi/blob/main/file/file.proto) proto defines a gNOI API used for file specific services on the target. The following is described for the Remove API which is supported.

```
service File {
  // Remove removes the specified file from the target. An error is
  // returned if the file does not exist, is a directory, or the remove
  // operation encounters an error (e.g., permission denied).
  rpc Remove(RemoveRequest) returns (RemoveResponse) {}
}

// A RemoveRequest specifies a file to be removed from the target.
message RemoveRequest {
  string remote_file = 1;
}

message RemoveResponse {
}
```

The front end implementation calls the host service via the module `infra_host` to remove the file on the target.

```
// Remove implements the corresponding RPC.
func (srv *GNOIFileServer) Remove(ctx context.Context, req *file.RemoveRequest) (*file.RemoveResponse, error) {
  ...
  if _, err := transformer.FileRemove(req.GetRemoteFile()); err != nil {
		return nil, status.Errorf(codes.Internal, err.Error())
	}
	return &file.RemoveResponse{}, nil
}

// FileRemove removes the specified file from the target.
func FileRemove(remoteFile string) (string, error) {
	fileMu.Lock()
	defer fileMu.Unlock()

	return checkQueryOutput(HostQuery("infra_host.exec_cmd", "rm "+remoteFile))
}
```

### gNOI Factory Reset

The [factory_reset](https://github.com/openconfig/gnoi/blob/main/factory_reset/factory_reset.proto) proto defines a gNOI API used for factory resetting a Target.

```
// The FactoryReset service exported by Targets.
service FactoryReset {
  // The Start RPC allows the Client to instruct the Target to immediately
  // clean all existing state and boot the Target in the same condition as it is
  // shipped from factory. State includes storage, configuration, logs,
  // certificates and licenses.
  //
  // Optionally allows rolling back the OS to the same version shipped from
  // factory.
  //
  // Optionally allows for the Target to zero-fill permanent storage where state
  // data is stored.
  //
  // If any of the optional flags is set but not supported, a gRPC Status with
  // code INVALID_ARGUMENT must be returned with the details value set to a
  // properly populated ResetError message.
  rpc Start(StartRequest) returns (StartResponse);
}

message StartRequest {
  // Instructs the Target to rollback the OS to the same version as it shipped
  // from factory.
  bool factory_os = 1;
  // Instructs the Target to zero fill persistent storage state data.
  bool zero_fill = 2;
  // Instructs the Target to retain certificates
  bool retain_certs = 3;
}

message StartResponse {
  oneof response {
    // Reset will be executed.
    ResetSuccess reset_success = 1;
    // Reset will not be executed.
    ResetError reset_error = 2;
  }
}
```
The front end implementation marshals the request, and sends it to the sonic-host-service via the host module `gnoi_reset`. The back end is expected to return the response in JSON format.

```
reqStr, err := json.Marshal(req)
...
respStr, err := resetXfmr.factoryReset(string(reqStr))
...
func (t resetXfmrImpl) factoryReset(req string) (string, error) {
	return transformer.FactoryReset(req)
}
...
// FactoryReset initiates the operations for Target to immediately clean all
// existing state and boot the Target in the same condition as it is shipped
// from factory (via DBUS).
// Input is the request message in JSON format.
// Back end is expected to return the response message in JSON format.
func FactoryReset(reqStr string) (string, error) {
	resetMu.Lock()
	defer resetMu.Unlock()

	return checkQueryOutput(HostQuery("gnoi_reset.issue_reset", reqStr))
}
```


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
