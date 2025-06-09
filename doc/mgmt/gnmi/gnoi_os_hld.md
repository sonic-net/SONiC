# gNOI HLD for OS APIs #

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
| v0.1 | 01/07/2025 | Neha Das (Google)   | Initial version |

## Scope

This document describes the high level design of adding the capability to support gNOI APIs for OS services in the gNMI server. 
It provides the definition as well as the front end and back end implementation for the gNOI services needed in the SONIC framework. The details of the underlying gNMI server design are captured [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md) and the host service DBUS communication is captured in a separate [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md).

The gNOI OS RPCs covered in this doc include: Activate, Install, Verify

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

This feature does not change the SONiC Architecture but leverages the existing gNMI server interface design. gNOI requests made by clients are verified and serviced by the gNMI UMF server after which they are sent to the corresponding Backend entity to process through DBUS communication to the host service. The details of the Docker to Host communication through DBUS are added [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md)

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

Step 1: OS Install on the primary and secondary controller cards.

	Install and activate a new software version on primary supervisor.
 
	a) Issue gnoi.os.Install RPC to the chassis with InstallRequest.TransferRequest message. The message should set the version to the desired new version image, and standby_supervisor to FALSE.
		* Wait for the switch to respond with InstallResponse. Expect it to return TransferReady.

	b) Transfer the content by issuing gnoi.os.Install rpc with InstallRequest.transfer_content message. 
  		* Expect it to return InstallResponse with a TransferProgress status asynchronously at certain intervals.

	c) End the transfer of software by issuing gnoi.os.Install rpc with InstallRequest.TransferEnd message. 
 		* Expect the switch to return InstallResponse with a Validated message. The version in the message should be set to the one which was transferred above.

	d) Activate the software by issuing gnoi.os.Activate rpc. 
 		* Set the version field of the ActivateRequest message to be the same as the version specified in the TransferRequest message above.
  		* Set the no_reboot flag to true.
  		* Set the standby_supervisor to FALSE.

Step 2: Install and activate the same new software version on standby supervisor:

	a) Repeat the above process of TransferRequest. This time set the standby_supervisor to TRUE.
		* Expect the switch to return a InstallResponse with a SyncProgress message. The switch should sync the software image from primary SUP to standby.
		* Expect the sync to return a value of 100 for percentage_transferred field.
		* At the end, expect the switch to return InstallResponse with a Validated message. The version in the message should be set to the one which was transferred above.

Step 3: Activate the software by issuing gnoi.os.Activate rpc as in the case of primary supervisor.

	a) Set the version field of the ActivateRequest message to be the same as the version specified in the TransferRequest message above.
 
	b) Set the no_reboot flag to true. This is done to first set the standby_supervisor to TRUE and then rebooting the switch through gNOI System Reboot.
 
	c) Set the standby_supervisor to TRUE this time.

Step 4: Reboot the switch.

	a) Issue gnoi.system.Reboot

Step 5: Verify that the supervisor image has moved to the new image.

	a) Verify that the supervisor has a valid image by issuing gnoi.os.Verify rpc.
		* Expect a VerifyResponse with the version field set to the version specified in messages above eventually.
		* Verify the standby supervisor version.
		* Expect that the VerifyResponse.verify_standby has the same version in messages above.

##### Configuration push verification post OS update.

Push a test configuration  using gNMI.Set() RPC with Set Replace operation.

- If the configuration push is successful, make a gNMI.Get() RPC call and compare the configuration received with the originally pushed configuration and check if the configuration is a match. 

- Test is a failure if either the gNMI.Get() operation fails or the configuration do not match with the one that was pushed.

#### DBUS Endpoints

There is an existing interface to sonic-installer https://github.com/sonic-net/sonic-host-services/blob/master/host_modules/image_service.py which can be used to consolidate all OS operations in one place. The front end implementation can call the host service via the module `image_service` to remove the file on the target. HostQuery calls the corresponding D-Bus endpoint on the host and returns any error and the response body.
```
// ActivateOS initiates the operations for activating the OS (via DBUS).
func ActivateOS(reqStr string) (string, error) {
	...
	r := HostQuery("image_service.activate", reqStr)
}

// VerifyOS initiates the operations for verifying the OS (via DBUS).
func VerifyOS(reqStr string) (string, error) {
	...
	r := HostQuery("image_service.verify", reqStr)
}

// InstallOS initiates the operations for transferring the image (via DBUS).
func InstallOS(reqStr string) (string, error) {
	...
	r := HostQuery("image_service.install", reqStr)
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

- CLI
    - The gNMI server has a [gnoi_client](https://github.com/sonic-net/sonic-gnmi/tree/master/gnoi_client) CLI tool which can be used to invoke service RPCs on the switch. This would include adding support for both JSON and proto formats of requests.

#### Automated Tests

- Unit Tests
For gNOI logic implementation in UMF, we will use the existing unit test and component test infrastructure for testing by adding unit tests for individual API per supported gNOI service.
    - TestOSInstallSucceeds
    - TestOSInstallFailsIfTransferRequestIsMissingVersion
    - TestOSInstallFailsForConcurrentOperations
    - TestOSInstallFailsIfWrongMessageIsSent
    - TestOSInstallAbortedImmediately
    - TestOSInstallFailsIfImageExistsWhenTransferBegins
    - TestOSInstallFailsIfStreamClosesInTheMiddleOfTransfer
    - TestOSInstallFailsIfWrongMsgIsSentInTheMiddleOfTransfer
    - TestOSActivateSucceeds
    - TestOSActivateFailsWrongVersion
    - TestOSVerifySucceeds
    - TestOSVerifyFailsWrongVersion

- End-to-End Tests
These tests would invoke gNOI requests from the client to verify expected behaviour for gNOI services and are implemented on the Ondatra and Thinkit testing infrastructure.
    - Run an end-to-end workflow with the OS Sequence flow as detailed above with
    	1) Calling gNOI OS Install,
  	2) Activating the image by running gNOI OS Activate, and
  	3) Verifying the image by calling gNOI OS Verify.

### Open/Action items - if any
