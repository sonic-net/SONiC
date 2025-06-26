# gNOI HLD for Healthz API #

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
| v0.1 | 06/16/2025 | Neha Das (Google)   | Initial version |

## Scope

This document describes the high level design of adding the capability to support gNOI APIs for the Healthz service in the gNMI server. 
It provides the definition as well as the front end and back end implementation for the gNOI service needed in the SONIC framework. The details of the underlying gNMI server design are captured [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md) and the host service DBUS communication is captured in a separate [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md).
The original OpenConfig Healthz Streaming RPC design and motivation is covered [here](https://github.com/openconfig/gnoi/blob/main/healthz/README.md)

The Healthz RPCs covered in this doc include: Get, Acknowledge, Artifact 

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

The Healthz service provides a means by which a user may initiate health check or a system may report the results of a check that it has initiated of its own accord. Healthz also allows a component inside of a system to report its health.

## Requirements

Any client should be able to connect to gNOI services at the IP of the target device and the port of the service, provided they have the necessary authentication and authorization privileges. 

## Architecture Design

This feature does not change the SONiC Architecture but leverages the existing gNMI/telemetry server interface design. gNOI requests made by clients are verified and serviced by the gNMI UMF server after which they are sent to the corresponding Backend entity to process through DBUS communication to the host service. The details of the Docker to Host communication through DBUS are added [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md)

![gnoi_dbus](https://github.com/user-attachments/assets/2b33a978-36b7-439f-810f-65339d0355f7)

In the above picture “SONiC Host Service” and “DBUS” are entities executing directly on the host (as opposed to within a container). DBUS is a system daemon facilitating IPC between processes and is used for communication between containers and the SONiC Host Service. SONiC Host Service is a host process fulfilling container requests that require host access. The host service is python based and has a module plugin style architecture. The Redis database is used as an IPC mechanism between containers.

## High-Level Design for gNOI Healthz

The [Healthz](https://github.com/openconfig/gnoi/blob/main/healthz/healthz.proto) proto defines gNOI RPCs used for Healthz specific services on the target. Out of the following, Get, Acknowledge and Artifact will be initially supported.

```
// The Healthz service provides access to the status of a path on the
// system. Addtitionally it allows the implementor to provide path specific
// diagnositic data into the status return.
//
// Healthz is expected to work in conjunction with the component OC model.
service Healthz {
  // Get will get the latest health status for a gNMI path.  If no status is
  // available for the requested path an error will be returned.
  rpc Get(GetRequest) returns (GetResponse) {}

  // Acknowledge will set the acknowledged field for the event.
  // This is an idempotent operation.
  rpc Acknowledge(AcknowledgeRequest) returns (AcknowledgeResponse) {}

  // Artifact will stream the artifact contents for the provided artifact id.
  rpc Artifact(ArtifactRequest) returns (stream ArtifactResponse) {}

  // Initially unsupported.
  // Check will invoke the healthz on the provided component path. This RPC
  // can be expensive depending on the vendor implementation.
  rpc Check(CheckRequest) returns (CheckResponse) {}

  // List returns all events for the provided component path.
  rpc List(ListRequest) returns (ListResponse) {}
}
```

Sequence following a health check:
- A caller can use the Get RPC to discover the health "events" (expressed as a ComponentStatus message) that are associated with a component and its corresponding subcomponents. Each event reflects a collection of data that is required to debug or further root cause the fault that occurs with an entity in the system.
- The Artifact RPC is used to retrieve specific artifacts that are listed by the target system in the Get RPC.
- Once retrieved, an event - which corresponds to a series of artifacts - can be 'acknowledged' by the client of the RPC. 
Acknowledged events are no longer returned in the list of events by default. The device may use the acknowledged status as a hint to allow garbage collection of artifacts that are no longer relevant.
- The device itself is responsible for garbage collection any may, if necessary, garbage collect artifacts that are not yet acknowledged. It is expected that events are persisted across restarts of the system or its hardware and software components, and they are removed only for resource management reasons.

Healthz works in conjunction with telemetry streamed via gNMI. OpenConfig paths for a specific component are streamed to indicate when components become unhealthy, allowing the receiving system to determine that further inspection of the component's health is required. 
Wherever a gNMI path (gnoi.types.Path) is used in Healthz, the path specified should be the complete path to a specific component, for example, `/components/component[name=FOO]`.

Example
```
Path: &types.Path{
    Origin: "openconfig",
    Elem: []*types.PathElem{
        {
            Name: "components",
        },
        {
            Name: "component",
            Key: map[string]string{
                "name": "healthz",
            },
        },
    },
}

```

The system can add its debug and health check data to a specified location in any format. Vendors can implement their healthz data as they please since parts of this data might be platform specific.


### Healthz.Get

```
message GetRequest {
  // Path defines the component to try to fetch healthz state for. Get
  // retrieves the latest healthz results for a specific component
  // that have been collected as a result of a call to Check, or by
  // the target itself.
  types.Path path = 1;
}

message GetResponse {
  ComponentStatus component = 1;
}

message ComponentStatus {
  gnoi.types.Path path = 1; // path of subcomponent.
  // Subcomponents that are aggregated by this status.
  repeated ComponentStatus subcomponents = 2;
  // Status of this component.
  Status status = 3;
  // Opaque data for how the healthcheck is implemented.  This can be any proto
  // defined by the vendor.  This could be the equivalent to outputs like
  // "show tech" or core files or any other diagnostic data.
  google.protobuf.Any healthz = 4 [deprecated=true];
  // Artifacts provides links to all artifacts contained in this event.
  // The individual artifacts can be retrieved via the Artifact() RPC.
  repeated ArtifactHeader artifacts = 5;
  // ID is the unique key for this event in the system.
  string id = 6;
  // Acknowledged is set when at least one caller has processed the event.
  bool acknowledged = 7;
  // Created is the timestamp when this event was created.
  google.protobuf.Timestamp created = 8;
  // Expires is the timestamp when the system will clean up the
  // artifact. If unset, the artifact is not scheduled for garbage
  // collection.
  google.protobuf.Timestamp expires = 9;
}
```
![Healthz.Get](https://github.com/user-attachments/assets/199c098d-e191-42c6-9a5a-494b685ad4f3)


Supported Paths for Get:
```
/components/component[name=healthz]/alert-info
/components/component[name=healthz]/critical-info
/components/component[name=healthz]/all-info
```
Get Sequence Flow

1. The Get RPC handler translates the incoming gNMI Path in the Get request to the correct component and derives the related information for the log level indicated. 
2. For the above supoorted paths, a call to HealthzCollect is made through the DBUS client with the component name, log level, and a persistent_storage flag to indicate if the artifacst should be stored in persistent storage. This in turn invokes the DBUS endpoint of the host service via the module `debug_info`.
3. The host service module `debug_info.collect` collects all the artifacts for a given board type. Depending on the log level and board type input, the relevant log files, DB snapshots, counters, record files, and various command outputs are collected for multiple components and aggregated under a specified artifact directory in the host. Once complete, the directory is compressed to a `*.tar.gz` file ready to be streamed.
4. In. the meantime, the frontend keeps polling for the artifact to be ready with a call to HealthzCheck through the DBUS client `debug_info.check`.
5. Once the artifact tar file is ready, the artifact details (filename, size, checksum) with the unique ID string are sent in the Get response back to the client.


### Healthz.Artifact
```
message ArtifactRequest {
  // Artifact ID to be streamed.
  string id = 1;
}

message ArtifactResponse {
  oneof contents {
    // Header is the first message in the stream. It contains
    // the id of the artifact and metadata for the artifact
    // based on the type of the artifact.
    // OC defines FileArtifactType and ProtoArtifactType.
    ArtifactHeader header = 1;
    ArtifactTrailer trailer = 2;
    bytes bytes = 3;
    google.protobuf.Any proto = 4;
  }
}

message ArtifactHeader {
  // ID of the artifact.
  string id = 1;
  // Artifact type describes data contents in the artifact.
  // File artifacts should use the defined FileArtifactType.
  // Proto artifacts should either use the generic ProtoArtifactType
  // which means the artifact is made up a sequence of proto.Any
  // messages which can be deserialized directly into thier message
  // types. Otherwise the implementer can provide a specific artifact type
  // which can add any additional metadata the implementor wants and define
  // a custom format for the message stream.
  oneof artifact_type {
    FileArtifactType file = 101;
    ProtoArtifactType proto = 102;
    google.protobuf.Any custom = 103;
  }
}

message FileArtifactType {
  // Local file name of the artifact.
  string name = 1;
  // Path to file on the local file system. (optional)
  string path = 2;
  // Mimetype of the file.
  string mimetype = 3;
  // Size of the file.
  int64 size = 4;
  // Hash of the file.
  gnoi.types.HashType hash = 5;
}
```

The Artifact RPC initiates the system's debugging artifact collection. The input ID string is the same unique id received from the Get Response. 
The RPC handler packages the artifact header information and streams the file to the caller.

### Healthz.Acknowledge

```
message AcknowledgeRequest {
  types.Path path = 1;
  // Healthz event id.
  string id = 2;
}

message AcknowledgeResponse {
  ComponentStatus status = 1;
}
```
The Acknowledge RPC removes the artifact associated with the path and ID provided in the backend and returns the status of the component.


### SAI API

No change in SAI API.


### Warmboot and Fastboot Design Impact

No effect on warm/fast boot

### Restrictions/Limitations

### Testing Requirements/Design

In this section, we discuss both manual and automated testing strategies.

#### Manual Tests
CLI
- The gNMI server has a gnoi_client CLI tool which can be used to invoke service RPCs on the switch. This would include adding support for both JSON and proto formats of requests.

#### Automated Tests
Unit Tests
- For gNOI logic implementation in UMF, we will use the existing unit test and component test infrastructure for testing by adding unit tests for individual API per supported gNOI service.

- TestHealthzServer
- HealthzGetFailsForInvalidComponent
- HealthzGetForInvalidPaths
- HealthzGetForDebugDataFailsForHostServiceError
- HealthzGetForDebugDataFailsForHostServiceErrorCode
- HealthzGetForDebugDataFailsForNotExistingFile
- HealthzGetForDebugDataFailsForCheckError
- HealthzArtifactForDebugDataFailsForNotExistingFile
- HealthzAcknowledgeForDebugDataForHostServiceError
- HealthzAcknowledgeForDebugDataForHostServiceErrorCode
- HealthzAcknowledgeForDebugDataFailsForNotExistingFile
- HealthzGetForDebugDataSucceeds


### Open/Action items - if any
