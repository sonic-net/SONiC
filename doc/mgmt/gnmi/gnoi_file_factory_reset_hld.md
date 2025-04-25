# gNOI HLD for File and Factory Reset APIs #

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

This document describes the high level design of adding the capability to support gNOI APIs for File and Factory Reset services in the telemetry server. 
It provides the definition as well as the front end and back end implementation for the gNOI services needed in the SONIC framework. The details of the underlying gNMI server design are captured [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md) and the host service DBUS communication is captured in a separate [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md).

The File RPCs covered in this doc include: Remove
The Factory Reset RPCs covered in this doc include: Start

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


### gNOI File

The [file](https://github.com/openconfig/gnoi/blob/main/file/file.proto) proto defines a gNOI API used for file specific services on the target. The following is described for the Remove API which is supported.

Currently we only support removing the config_db.json file. A string match for `rm ..../etc/sonic/config_db.json` validates the request in the host service backend, else it fails.

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
