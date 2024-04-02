# SONiC GNOI Server Interface Design

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [About this Document](#about-this-document)
- [Definition/Abbreviation](#definitionabbreviation)
- [Background](#background)
- [Scope](#scope)
- [1 Project Goal Summary](#1-project-goal-summary)
- [2 Requirements](#2-requirements)
- [3 Architecture Design](#3-architecture-design)
- [4 High Level Design](#4-high-level-design)
- [5 Sample Scenario](#5-sample-scenario)
- [6 Testing](#6-testing)



# Revision

| Rev | Date        | Author             | Change Description  |
|:---:|:-----------:|:------------------:|---------------------|
| 0.1  | 03/27/2024 | Isabel Li    | Initial version     |

# About this Document
This document provides a detailed description on the strategy to implement the SONiC GNOI Server Interface.

# Definition/Abbreviation
| **Term** | **Meaning**                |
| -------- | -------------------------- |
| API      | Application Programming Interface |
| CLI      | Command Line Interface |
| gRPC     | A modern open-source high performance Remote Procedure Call (RPC) framework that can run in any environment |
| gNMI     | gRPC Network Management Interface, used to retrieve or manipulate the state of a device via telemetry or configuration data |
| gNOI     | gRPC Network Operations Interface |
| NE       | Network Engineers |

# Background
Software for Open Networking in the Cloud (SONiC) is an open source network operating system (NOS) based on Linux that runs on switches from multiple vendors and ASICs. SONiC offers a full suite of network functionality, like BGP and RDMA, that has been production-hardened in the data centers of some of the largest cloud service providers. 

Currently, most SONiC operation and configuration management requires directly using CLI on the device. This document proposes the addition of gNOI API to SONiC to modernize SONiC operation management. 

GNOI (gRPC network operations interface) is supported through OpenConfig. All gNOI services and documentation are available on the [OpenConfig page](https://github.com/openconfig/gnoi). OpenConfig defines and implements a common, vendor-independent software layer for managing network devices.

# Scope
This document describes the high level design of SONiC gNOI Server Interface, as well as the gNOI APIs necessary for SONiC operation management. 

GNOI support comes as a natural extension to preexisting gNMI support. GNOI RPCs are exposed on the same server/port as the gNMI server. For more information regarding gNMI, please refer to the [gNMI HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md).

## 1 Project Goal Summary
Network engineers (NE) currently rely on command line interfaces (CLI) to operate SONiC devices. We plan to replace CLI by GNOI API, which will help minimize network engineers’ manual touches on SONiC devices.

We plan to use GNOI API to replace the most common NE CLI used for SONiC operation management. These APIs can sit behind a website frontend that NEs interact with directly, which enables NEs to execute common tasks with a simple webpage interaction. This saves time and reduces errors.

## 2 Requirements

Support for commonly used SONiC operation management CLI
* `sudo sonic_installer install`
* `sudo reboot`
* `sudo systemctl restart <service>`

Support for commonly used Linux system management CLI
* `mv`
* `cp`
* `rm`

Support for other commonly used SONiC operations
* cert installation
* firmware upgrade

## 3 Architecture Design

All the introduced features are part of the sonic-gnmi package installed in the sonic-gnmi container.

The GNOI/GNMI server uses [DBUS](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md) to communicate with the SONiC host services, which are responsible for executing various commands on the device. Some of these commands are "config reload", "reboot", "sonic-installer install", "cp", "mv", and "rm". 


<img src="images/gnoi_gnmi_arch.svg" viewBox="0 0 width height" alt="gnmi-server" width="1200px"/>

## 4 High Level Design

GNOI is composed of services, each of which is organized into related RPCs. We plan to add support for the following services: 
* File - provides an interface for file operations on the target, including file transfer to and from the target node.
* FactoryReset - provides an interface for factory resetting the target node.
* CertificateManagement - provides an interface to install certificates on the target node.
* System - provides an interface for the management system-related operations on the target node. 
* Containerz - provides an interface to perform container operations on a network device. 

### 4.1. GNOI RPC API
We need to implement these GNOI APIs to support SONiC operations. 


#### File.Get
We can use this API to get a file from a SONiC device.

Arguments: absolute path string to an existing remote file
```
rpc Get(GetRequest) returns (stream GetResponse) {}

message GetRequest {
  string remote_file = 1;
}

message GetResponse {
  oneof response {
    bytes contents = 1;
    gnoi.types.HashType hash = 2; // hash of the file.
  }
}
```

#### File.Put
We can use this API to put a file to SONiC device. Since File API is verify powerful, we will check client role. Only read-write clients can upload files.

Arguments: absolute path string on target where file should be written, file permissions, contents to be written to target 

```
rpc Put(stream PutRequest) returns (PutResponse) {}

message PutRequest {
  message Details {
    string remote_file = 1;
    // Permissions are represented as the octal format of standard UNIX
    // file permissions.
    // ex. 775: user read/write/execute, group read/write/execute,
    // global read/execute.
    uint32 permissions = 2;
  }
  oneof request {
    Details open = 1;
    bytes contents = 2;
    gnoi.types.HashType hash = 3; // hash of the file.
  }
}

message PutResponse {
}
```

#### File.Stat
We can use this API to get metadata about a file including size, permission etc.

Arguments: path string for which we want to retrieve file(s) info
```
rpc Stat(StatRequest) returns (StatResponse) {}

// StatRequest will list files at the provided path.
message StatRequest {
  string path = 1;
}

// StatResponse contains list of stat info of the provided path.
message StatResponse {
  repeated StatInfo stats = 1;
}

// StatInfo provides a file system information about a particular path.
message StatInfo {
  string path = 1;
  uint64 last_modified = 2; // Nanoseconds since epoch.
  // Permissions are represented as the octal format of standard UNIX
  // file permissions.
  // ex. 775: user read/write/execute, group read/write/execute,
  // global read/execute.
  // The value returned in this field should be the octal number. No base
  // conversion should be required to read the value. For example, 0755
  // should result in the permissions field holding the value 755, 4644
  // results in the permissions field being 4644, and so on.
  uint32 permissions = 3;
  uint64 size = 4;
  // Default file creation mask. Represented as the octal format of
  // standard UNIX mask.
  uint32 umask = 5;
}
```

#### File.Remove
We can use this API to remove a file from SONiC device. We will check client role, only read-write clients can remove file.

Arguments: path string of file to be removed from target
```
rpc Remove(RemoveRequest) returns (RemoveResponse) {}

// A RemoveRequest specifies a file to be removed from the target.
message RemoveRequest {
  string remote_file = 1;
}

message RemoveResponse {
}
```

#### FactoryReset.Start
We can use this API to clean up all the configurations and decommission device.

Arguments: Booleans to instruct target to rollback to original OS version, zero fill persistent storage state data, and retain certificates
```
rpc Start(StartRequest) returns (StartResponse);

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

#### CertificateManagement.Install
We can use this API to install bootstrap certificate.

Arguments: parameters to generate and store new certificates
```
rpc Install(stream InstallCertificateRequest)
    returns (stream InstallCertificateResponse);
// Request messages to install new certificates on the target.

message InstallCertificateRequest {
  // Request Messages.
  oneof install_request {
    GenerateCSRRequest generate_csr = 1;
    LoadCertificateRequest load_certificate = 2;
  }
}

// Response Messages from the target for the InstallCertificateRequest.
message InstallCertificateResponse {
  // Response messages.
  oneof install_response {
    GenerateCSRResponse generated_csr = 1;
    LoadCertificateResponse load_certificate = 2;
  }
}
```

#### System.SetPackage
We can use this API to download an image or package from remote (or passed directly in client request) and install this image or package.

Arguments: filename of the package, version of the package, Boolean to indicate whether the package should be made active after receipt on the device, package contents, hash of file contents
```
rpc SetPackage(stream SetPackageRequest) returns (SetPackageResponse) {}

message SetPackageRequest {
  oneof request {
    Package package = 1;
    bytes contents = 2;
    types.HashType hash = 3;    // Verification hash of data.
  }
}

// Package defines a single package file to be placed on the target.
message Package  {
  // filename of the package.
  string filename = 1;
  // Version of the package. (vendor internal name)
  string version = 4;
  // Indicates that the package should be made active after receipt on
  // the device. For system image packages, the new image is expected to
  // be active after a reboot.
  bool activate = 5;
  // Details for the device to download the package from a remote location.
  common.RemoteDownload remote_download = 6;
}

message SetPackageResponse {
}
```

The SetPackage API downloads an image or package from a remote host to the local filesystem. Because multiple targets are possible (SONiC image, cable firmware, etc.), filename in the `SetPackageRequest` is used to identify the target. The below table demonstrates how the target is specified through filename. Additionally, through SetPackage API implementation logic, the filename is then translated to a proposed file location. If filename is not in the expected format, the client's request is rejected. This process ensures that client-requested firmware upgrade files are in the expected path. 

| Filename                | Version    | Activate | Firmware type              | Proposed file location                               |
|-------------------------|------------|----------|----------------------------|-----------------------------------------------------|
| SONiC/localhost/default | 20230531.10| False    | SONiC image                | /tmp/sonic-20230531.10.bin                |
| SONiC/DPU0/default      | 20230531.10| False    | SONiC image to run on DPU0 | /usr/share/sonic/dpu/dpu-sonic-20230531.10.bin     |
| DPU/DPU0/default        | 20230531.10| False    | DPU firmware for DPU0      | /usr/share/sonic/dpu/dpu-20230531.10.bin           |
| CABLE/Ethernet0/default | 1.1        | False    | Cable firmware for Ethernet0| /usr/share/sonic/firmware/cable-1.1.bin            |
| ASIC/ASIC0/default      | 1.0        | False    | ASIC firmware for ASIC0    | /usr/share/sonic/asic/asic-1.0.bin                  |
| CPLD/localhost/default  | 1.0        | False    | CPLD firmware for localhost| /usr/share/sonic/cpld/cpld-1.0.bin                 |
| CPLD/DPU0/default       | 1.0        | False    | CPLD firmware for DPU0     | /usr/share/sonic/dpu/cpld/cpld-1.0.bin             |

GNOI API will use the below rules for Filename in System.SetPackage. Each part of filename is split by slash.
1.	The first part is type. This may be SONIC, DPU, CABLE, CPLD or ASIC.
2.	The second part is device name. This may be DPU0 for DPU, or Ethernet0 for cable. It’s possible to have embedded device name, for example, DPU0/Ethernet0.
3.	The last part is default for now, we will use this part for future extension.

<img src="images/filename_gnoi.svg" alt="filename-gnoi" width="800px"/>


#### System.Reboot
We can use this API to support various reboot methods. 

Arguments: type of reboot (cold, warm, etc.), delay before issuing reboot, string describing reason for reboot, option to force reboot if sanity checks fail
```
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
```
For SONiC cold reboot, we can use COLD method.

For SONiC warm reboot, we can use WARM method.

For SONiC fast reboot, we can use NSF method.

For SONiC config reload, we can use reserved method.

#### System.KillProcess
We can use this API to kill an OS process, and optionally restart.

Arguments: process ID of process to be killed, name of process to be killed, termination signal sent to process (SIGNAL_TERM, SIGNAL_KILL, etc.)
```
rpc KillProcess(KillProcessRequest) returns (KillProcessResponse) {}

message KillProcessRequest {
  // Process ID of the process to be killed.
  uint32 pid = 1;
  // Name of the process to be killed.
  string name = 2;
  // Termination signal sent to the process.
  enum Signal {
    SIGNAL_UNSPECIFIED = 0;  // Invalid default.
    SIGNAL_TERM = 1;         // Terminate the process gracefully.
    SIGNAL_KILL = 2;         // Terminate the process immediately.
    SIGNAL_HUP = 3;          // Reload the process configuration.
    // Terminate the process immediately and dump a core file.
    SIGNAL_ABRT = 4;
  }

  Signal signal = 3;
  // Whether the process should be restarted after termination.
  // This value is ignored when the termination signal is SIGHUP.
  bool restart = 4;
}

message KillProcessResponse {
}
```

#### Containerz.StartContainer
We can use this API to start a SONiC container. Note: a new API needs to be added to support non-containerized service restarts

Arguments: image tag, image name of container to start
```
rpc StartContainer(StartContainerRequest) returns (StartContainerResponse) {}

message StartContainerRequest {
  // The name and tag of the container to start.
  string image_name = 1;
  string tag = 2;
  string cmd = 3;

  // Optional. The name to give the running container. If none is specified,
  // the target should assign one.
  string instance_name = 4;
  message Port {
    uint32 internal = 1;
    uint32 external = 2;
  }

  // List of internal ports to expose outside the container.
  repeated Port ports = 5;

  // Environment to set in the container.
  map<string, string> environment = 6;

  // List of volumes that should be attached to the container.
  repeated Volume volumes = 7;

  // Other container properties will be added as it becomes necessary.
}

message StartContainerResponse {
  oneof response {
    StartOK start_ok = 1;
    StartError start_error = 2;
  }
}

```

#### Containerz.StopContainer
We can use this API to stop or restart a SONiC container.

Arguments: container name, bool force to determine whether the process should be forcibly killed, bool restart to determine if the service should be started immediately after stopping it
```
rpc StopContainer(StopContainerRequest) returns (StopContainerResponse) {}

message StopContainerRequest {
  string instance_name = 1;

  // If force is set, the target should attempt to forcibly kill the container.
  bool force = 2;

  // If restart is set, the target should start the container immediately
  // after stopping it.
  bool restart = 3;
}

message StopContainerResponse {
  enum Code {
    // An unspecified error. The details field should provide more information.
    UNSPECIFIED = 0;

    // Container is busy.
    BUSY = 1;

    // Instance was not found on the target.
    NOT_FOUND = 2;

    // The container was removed.
    SUCCESS = 3;
  }

  Code code = 1;
  string details = 2;
}
```

#### Containerz.Deploy
We can use this API to set a new container image on the target

Arguments: container image name, tag, remote download URL or image file content
```
rpc Deploy(stream DeployRequest) returns (stream DeployResponse) {}

message DeployRequest {
  oneof request {
    ImageTransfer image_transfer = 1;
    bytes content = 2;
    ImageTransferEnd image_transfer_end = 3;
  }
}

message DeployResponse {
  oneof response {
    ImageTransferReady image_transfer_ready = 1;
    ImageTransferProgress image_transfer_progress = 2;
    ImageTransferSuccess image_transfer_success = 3;
    google.rpc.Status image_transfer_error = 4;
  }
}
```

#### Containerz.RemoveContainer
We can use this API to remove an unused container image

Arguments: container image name to be removed, container tag to be removed, force boolean
```
rpc RemoveContainer(RemoveContainerRequest) returns (RemoveContainerResponse) {}

message RemoveContainerRequest {
  // The container image name to be removed.
  string name = 1;

  // The container tag to be removed.
  string tag = 2;

  // If force is set, the target should attempt to forcibly remove the
  // container.
  bool force = 3;
}

message RemoveContainerResponse {
  enum Code {
    // An unspecified error. Must use the detail value to describe the issue.
    UNSPECIFIED = 0;

    // Indicates the image was not found in the remote location.
    NOT_FOUND = 1;

    // Indicates that a container using this image is running.
    RUNNING = 2;

    // The container image was successfully removed.
    SUCCESS = 3;
  }

  Code code = 1;
  string detail = 2;
}
```

Additionally, some [private SONiC APIs](https://github.com/sonic-net/sonic-gnmi/blob/master/proto/gnoi/sonic_gnoi.proto#L11) have been defined: 
```
service SonicService {
  rpc ShowTechsupport (TechsupportRequest) returns (TechsupportResponse) {}
}
```
We plan to add support for ShowTechsupport. We also plan to an additional API not yet included in OpenConfig gNOI:
* #### Start Process
GNOI System.proto defines only KillProcess, which can optionally restart a process. There is no API specific to starting a process.

### 4.2. Authentication

GNOI shares the same authentication methods as GNMI, as described in the [gNMI HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md#1218-authentication).

### 4.3. Parallel Operations
The GNOI/GNMI server accepts concurrent requests. Parallel reads and sequential writes are permitted. 

The GNOI server does not support parallel write operations. GNOI write requests are placed in a queue and served with a single worker.


### 4.4. Docker to Host Communication
As described in the [gNMI HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md#1218-authentication), we utilize dbus to execute some commands designed to run on the host, such as `systemctl restart <service>`, `config apply-patch` and `config reload`.

## 5 Sample Scenario

### Upgrade SONiC image
<img src="images/install_sonic_image_apis_flow.svg" alt="upgrade-dpu-firmware" width="800px"/>
We need the below steps to upgrade DPU firmware:
* GNMI Get
Read current SONiC image version. If it's not golden version, we need to ugprade.

* GNOI System.SetPackage

We will use the SetPackage API to install and activate the new SONiC image.

```
// Package defines a single package file to be placed on the target.
message Package {
  // Destination path and filename of the package.
  string filename = 1;
  // Version of the package. (vendor internal name)
  string version = 4;
  // Indicates that the package should be made active after receipt on
  // the device. For system image packages, the new image is expected to
  // be active after a reboot.
  bool activate = 5;
  // Details for the device to download the package from a remote location.
  common.RemoteDownload remote_download = 6;
}

// SetPackageRequest will place the package onto the target and optionally mark
// it as the next bootable image. The initial message must be a package
// message containing the filename and information about the file. Following the
// initial message the contents are then streamed in maximum 64k chunks. The
// final message must be a hash message contains the hash of the file contents.
message SetPackageRequest {
  oneof request {
    Package package = 1;
    bytes contents = 2;
    types.HashType hash = 3;    // Verification hash of data.
  }
}

message SetPackageResponse {
}
```
Note: The OS.Activate API is not suitable for our use case, because it does not have a field to specify the subcomponent that we want to activate.

* GNOI System.Reboot
We will use System.Reboot API to reboot the device.
```
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
message Path {
  string origin = 2;                              // Label to disambiguate path.
  repeated PathElem elem = 3;                     // Elements of the path.
}
message PathElem {
  string name = 1;                    // The name of the element in the path.
  map<string, string> key = 2;        // Map of key (attribute) name to value.
}
```
* GNMI Get
Read current SONiC image version. If it's equal to target version, then upgrade was successful. 



## 6 Testing
### 6.1. Unit Testing
| Test Case | Description |
| ---- | ---- |
| 1 | UT for OS.Activate |
| 2 | UT for OS.Verify |
| 3 | UT for File.Get |
| 4 | UT for File.Put |
| 5 | UT for File.Stat |
| 6 | UT for File.Remove |
| 7 | UT for FactoryReset.Start |
| 8 | UT for CertificateManagement.Install |
| 9 | UT for System.SetPackage |
| 10 | UT for System.Reboot |
| 11 | UT for Containerz.StartContainer |
| 12 | UT for Containerz.StopContainer |
| 13 | UT for Containerz.Deploy |
| 14 | UT for Containerz.RemoveContainer |
| 15 | UT for System.KillProcess |
| 16 | UT for dbus client initialization |
| 17 | UT for dbus config reload API call |
| 18 | UT for dbus service restart API call |


### 6.2. E2E Testing
E2E tests will be added to [sonic-mgmt](https://github.com/sonic-net/sonic-mgmt.git)
| Test Case | Description |
| ---- | ---- |
| 1 | E2E test for OS.Activate |
| 2 | E2E test for OS.Verify |
| 3 | E2E test for File.Get |
| 4 | E2E test for File.Put |
| 5 | E2E test for File.Stat |
| 6 | E2E test for File.Remove |
| 7 | E2E test for FactoryReset.Start |
| 8 | E2E test for CertificateManagement.Install |
| 9 | E2E test for System.SetPackage |
| 10 | E2E test for System.Reboot |
| 11 | E2E test for Containerz.StartContainer |
| 12 | E2E test for Containerz.StopContainer |
| 13 | E2E test for Containerz.Deploy |
| 14 | E2E test for Containerz.RemoveContainer |
| 15 | E2E test for System.KillProcess |
| 16 | E2E test to verify that required gNOI/gNMI parameters are in ConfigDB (certs, port) |