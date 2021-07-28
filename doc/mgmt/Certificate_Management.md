# Certificate Mangement

# High Level Design Document
# Table of Contents
- [1 Feature Overview](#1-Feature-Overview)
    - [1.1 Target Deployment Use Cases](#11-Target-Deployment-Use-Cases)
    - [1.2 Requirements](#12-Requirements)
    - [1.3 Design Overview](#13-Design-Overview)
        - [1.3.1 Basic Approach](#131-Basic-Approach)
        - [1.3.2 Container](#132-Container)
        - [1.3.3 SAI Overview](#133-SAI-Overview)
- [2 Functionality](#2-Functionality)
- [3 Design](#3-Design)
    - [3.1 Overview](#31-Overview)
        - [3.1.1 Service and Docker Management](#311-Service-and-Docker-Management)
        - [3.1.2 Packet Handling](#312-Packet-Handling)
    - [3.2 DB Changes](#32-DB-Changes)
        - [3.2.1 CONFIG DB](#321-CONFIG-DB)
        - [3.2.2 APP DB](#322-APP-DB)
        - [3.2.3 STATE DB](#323-STATE-DB)
        - [3.2.4 ASIC DB](#324-ASIC-DB)
        - [3.2.5 COUNTER DB](#325-COUNTER-DB)
        - [3.2.6 ERROR DB](#326-ERROR-DB)
    - [3.3 Switch State Service Design](#33-Switch-State-Service-Design)
        - [3.3.1 Orchestration Agent](#331-Orchestration-Agent)
        - [3.3.2 Other Processes](#332-Other-Processes)
    - [3.4 SyncD](#34-SyncD)
    - [3.5 SAI](#35-SAI)
    - [3.6 User Interface](#36-User-Interface)
        - [3.6.1 Data Models](#361-Data-Models)
        - [3.6.2 CLI](#362-CLI)
        - [3.6.2.1 Configuration Commands](#3621-Configuration-Commands)
        - [3.6.2.2 Show Commands](#3622-Show-Commands)
        - [3.6.2.3 Exec Commands](#3623-Exec-Commands)
        - [3.6.3 REST API Support](#363-REST-API-Support)
        - [3.6.4 gNMI Support](#364-gNMI-Support)
     - [3.7 Warm Boot Support](#37-Warm-Boot-Support)
     - [3.8 Upgrade and Downgrade Considerations](#38-Upgrade-and-Downgrade-Considerations)
     - [3.9 Resource Needs](#39-Resource-Needs)
- [4 Flow Diagrams](#4-Flow-Diagrams)
- [5 Error Handling](#5-Error-Handling)
- [6 Serviceability and Debug](#6-Serviceability-and-Debug)
- [7 Scalability](#7-Scalability)
- [8 Platform](#8-Platform)
- [9 Limitations](#9-Limitations)
- [10 Unit Test](#10-Unit-Test)
- [11 Internal Design Information](#11-Internal-Design-Information)
    - [11.1 IS-CLI Compliance](#111-IS-CLI-Compliance)
    - [11.2 Broadcom Packaging](#112-Broadcom-SONiC-Packaging)
    - [11.3 Broadcom Silicon Considerations](#113-Broadcom-Silicon-Considerations)    
    - [11.4 Design Alternatives](#114-Design-Alternatives)
    - [11.5 Broadcom Release Matrix](#115-Broadcom-Release-Matrix)

# List of Tables
[Table 1: Abbreviations](#table-1-Abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | <07/20/2020>|   Eric Seifert     | Initial version                   |

# About this Manual
This document provides comprehensive functional and design information about the certificate mangement feature implementation in SONiC.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| PKI                      | Public Key Infrastructure           |
| CSR                      | Certificate Signing Request         |
| gNMI                     | gRPC Network Management Interface   |
| CA                       | Certificate Authority               |
| PEM                      | Privacy Enhanced Mail               |
| CRL                      | Certificate Revocation List         |
# 1 Feature Overview

X.509 Public Key Certificates are used by REST and gNMI services currently and will be used by other services in the future. Configuring these certificates requires manually generating and placing the certificate and key files on the filesystem manually. Then you must configure the redis keys manually as well and restart the services. There is also the issue of upgrades where the location of the certificates are placed is not preserved causing these services to break until the files locations are restored. Finally, when certificates expire or are about to expire, there is no warning or alarm for this event or any other issue with the certificates such as invalid hostnames, weak encryption, revocation etc.

The certificate management feature will introduce a new YANG model and CLI to address the above issues. It will handle certificate generation and file management along with association of these certificates with a given service via a security profile. It will also ensure that the certificates are available after upgrade/downgrade and handle certificate rotation and alarms to alert on certificate issues.

## 1.1 Target Deployment Use Cases

The use case for certificates is any service that wants secure communication to the outside. This includes but is not limited to:

    - HTTPS Web Server (REST, Swagger UI etc.)
    - gNMI Telemetry/Configuration
    - Dialout Telemetry
    - Syslog
    - RADIUS
    - SSH

Although only REST and gNMI are to be targeted initially for use with certificate management, the other services can be integrated eventually as well. 

## 1.2 Requirements

*Fill out with detailed, immutably numbered requirements from which test cases can be generated. A structured numbering scheme is used using the following sections. Some sections may be omitted according to the needs of the feature: -*

1. *Overview - Overview of the feature and its purpose and usage*
2. *Functionality - This is the main body of the detailed requirements, and contains most of the functionality statements. This section may be further sub-divided into sub-categories as makes sense, each covering a different aspect of the functionality. Numbering like this allows requirements to be later inserted into their natural position without renumbering*
3. *Interfaces - Which interfaces does the feature run on? Cover physical ports (incl. dynamic port breakout), port channels/MCLAGs, routing interfaces (port, VLAN, loopback), tunnel interfaces (VXLAN), routing sub-interfaces (future), Management port etc.*
4. *Configurability - What configuration operations will the feature have? Describe these at a general level.*
5. *User Interfaces - Which UIs will be available for managing the feature (Klish, REST, gNMI, Click, vtysh, Linux shell etc). On these: -*
    - *SONiC Management Framework UIs (YANG, REST/gNMI, Klish) is basically mandatory for all new features (full coverage)*
        - *Please also state where the underlying Northbound YANG model will come from (standards, standard augmentations/deviations, proprietary)*
    - *Click - generally only added when extending an existing Click feature*
    - *vtysh - only when adding or extending an FRR feature*
6. *Serviceability - Which serviceability features are provided to allow the feature to be debugged in development, QA, and the field (e.g. debug commands, logs, counters, state dumps etc)?*
7. *Scaling - Key scaling factors (e.g. instances, interfaces, neighbors, table entries etc)*
8. *Warm Boot/ISSU - How should the feature behave through a Warm Boot or Upgrade?* 
   - *Forwarding plane features are required to maintain consistent forwarding through and after the restart, and for the system to arrive at a fully consistent state (SW, HW) afterwards.* 
   - *For Control Plane features, what provisions (if any) are required to manage our relationships with other devices in the network to avoid forwarding plane disruption?*
9. *Platforms - In general, all SONiC features should be available on all SONiC hardware platforms. However in some cases there may be some limitations, and these can be documented here.*
10. *Feature Interactions/Exclusions - requirements associated with other/adjacent features (e.g. "should not be used with feature x", "depends upon feature y") 
11. *Limitations - Any limitations relative to what might be expected of the feature? This can include future enhancements.*

*Some general guidance for the detailed requirements: -*
- *These requirements should be written in sufficient detail to allow: -*
   - *The reviewers to confirm that the feature will meet customer and product needs*
   - *The test case developer to start writing a test plan (tracing back to these requirements)*
   - *The developer (and their manager) to come up with an accurate sizing of the work effort and schedule*

1 Overview
1.0 - Certificate Management is a set of YANG models, CLIs and scripts to generate, install, configure and monitor PKI certificates and the services that use them. Security profiles will be used to associate a service with a certificate and key pair.

2 Functionality
2.0 Overview
2.0.1 - Establish a directory in the filesystem that all certificates and keys will be installed in to and that will be preserved through upgrades and downgrades.
2.0.2 - Create YANG model for managing certificate and security profile information.
2.0.3 - Create scripts to generate, download and verify certificates as well as configure services.
2.0.4 - Integrate with sysmonitor.py to periodically validate certificates/configurations and raise alarms if needed.
2.0.5 - Create CLI to generate/download certificates & signing requests and configure services.

3 Interfaces
3.0 The configuration of the certificate management YANG model will be available via the CLI, but also the REST and gNMI interfaces on the management interface.

4 Configuration
4.0 - Install CA certificate from local file, remote location or copy and past into CLI
4.1 - Generate self-signed certificate 
4.2 - Generate certificate signing request (CSR)
4.3 - Install certificate or private key from local file, remote location
4.4 - Delete CA certificate
4.5 - Delete certificate
4.6 - Display certificate
4.7 - Display trusted CAs
4.8 - Display raw PEM Format certificate
4.9 - Configure certificate revocation check behavior
4.10 - Refresh CRL
4.11 - Configure CRL download location(s)
4.12 - Configure CRL Override
4.13 - Display CRL
4.14 - Create new security profile
4.15 - Delete security profile
4.16 - Associate a certificate and private key file with a security-profile
4.17 - Apply security profile to service
4.18 - Remove association of security profile with service

5 User Interfaces  
5.0 The feature is managed through the SONiC Management Framework, including full support for Klish, REST and gNMI  

6 Serviceability  
6.0 - UI show commands are provided to show session states  
6.1 - All session events are logged 
6.2 - Alarms are raised for certificate issues

7 Scaling
7.0 No known issues with scaling

8 Warm Boot/ISSU
8.0 Warm boot will causes services to restart. On restart services will continue to use their configured certificates.

9 Platforms  
9.0 - Certificate management is supported on all SONiC platforms  

10 Feature Interactions/Exclusions  
10.1 HTTP server certificate and CA will be configured with this feature
10.2 gNMI server certificate and CA will be configured with this feature
10.3 Other services will be integrated in the future

11 Limitations  
11.1 Services must be restarted in for new certificates to take effect

*Below is an example for the BFD feature - these are hypothetical, and only relate loosely to the existing SONiC BFD feature!*

1 Overview  
1.0 - BFD (Bidirectional Forwarding Detection) is an OAM protocol used to detect the health (or otherwise) of a forwarding path. It is used as a detection mechanism by other protocols, typically because it can detect failures faster than the protocol-native detection mechanisms.  
1.1 - BFD is widely used in Routing environments, and is broadly supported in OEM products.  
1.2 - It is standardized through RFC 5880 and a set of related RFCs (RFC 5881 to RFC 5885).  


2 Functionality

*In this example, sub-categories (with additional numbering) are used to get natural grouping and ordering, and to allow requirement insertion without re-numbering.*

2.0 Overview  
2.0.1 - Compliant with RFC 5880 (BFD) and RFC 5881 (BFD for IPv4 and IPv6 (Single Hop)) unless otherwise stated  
2.1 Protocol Functions  
2.1.1 - Support Asynchronous mode  
2.1.2 - Support Demand mode  
2.1.3 - Support Echo function  
2.2 Security Functions  
2.2.1 - Support MD5 Authentication (incl. meticulous)  
2.2.2 - Support SHA1 Authentication (incl. meticulous)  
2.3 Encapsulation Functions  
2.3.1 - IPv4 encapsulation  
2.3.1 - IPv6 encapsulation  
2.4 Timer interval range  
2.4.1 - Support >= 100ms Tx interval  
2.5 Client Protocols  
2.5.1 - Operate with BGP. BGP uses BFD to inform on the state of the forwarding path to a neighbor  
2.5.2 - When BGP Graceful Restart is enabled, helper mode is triggered when a BFD session with a neighbor goes down  

3 Interfaces  
3.0 - Supported on loopback interfaces  
3.1 - Supported on Port-based routing interfaces  
3.2 - Supported on VLAN-based routing interfaces  
3.3 - In the case of a VLAN-based interface, physical path selection is consistent with VLAN forwarding - no special measures are taken to steer to a given physical path  
3.4 - In the case of a LAG on the physical path, BFD runs at the LAG-level and not at the member port level  
3.5 - BFD can be used on routing interfaces in any VRF except for the Management VRF  

4 Configuration  
4.0 - BFD is enabled on a per-interface basis  
4.1 - BFD session parameters are managed per session  
4.2 - Session Tx intervals are configurable  
4.3 - Configure operational mode (Async, Demand, Echo)  
4.4 - A session may be administratively set to down  
4.5 - Detect Multiplier is configurable  
4.6 - Associate a BFD session to a BGP neighbor relationship  

5 User Interfaces  
5.0 The feature is managed through the SONiC Management Framework, including full support for Klish, REST and gNMI  
5.1 Base data model is OpenConfig BFD with extensions - https://github.com/openconfig/public/blob/master/release/models/bfd/openconfig-bfd.yang  

6 Serviceability  
6.0 - UI show commands are provided to show session states  
6.1 - Per-session statistics are provided on packet Tx, Rx and stats change events  
6.2 - All session events are logged  

7 Scaling  
7.0 Support up to 64 BFD sessions at an interval of 100 milliseconds (total 6400 pps)   
7.1 Number of sessions can scale up or down according to the packet (pps) limit (e.g. 128 sessions at 200 ms)  

8 Warm Boot/ISSU  
8.0 BFD allows Warm Boot to be supported in conjunction with client protocol Graceful Restart methods (e.g. BGP GR)  
8.1 During a Warm Boot, BFD packet processing stops. This would normally cause the session neighbors to detect the path as down and route around the Warm Booting switch. However, when used in conjunction with BGP GR, BFD sets a flag to state that the forwarding plane does not share fate with the control plane, enabling the neighbors to continue using the Warm Boot data path.  
8.2 After Warm Boot is completed, BGP will re-establish all the sessions and trigger BFD to re-establish corresponding BFD sessions.  

9 Platforms  
9.0 - BFD is supported on all SONiC platforms  

10 Feature Interactions/Exclusions  
10.0 - A BFD session is typically associated with a BGP session.

11 Limitations  
11.0 - BFD is not supported on the out-of-band management port  
11.1 - BFD is not supported on VXLAN tunnels  
11.2 - Multi-hop BFD is not required  
11.3 - Password session Authentication is not supported  

## 1.3 Design Overview
### 1.3.1 Basic Approach

The certificate management functionality will be implemented using a new YANG model and accompanying KLISH CLI. THe functionality of generating new certificate and key pairs, signing request, downloading and installing will be implemented in a python script that the CLI will call. The script will use the already installed openssl tools on the system for the certificate generation, signing etc. THe downloading of the certificates from remote locations will be handled with calls to curl.

To monitor the certificates validity and the correct configuration of the services, new periodically called functions will be added to SONiC sysmonitor.py script. These functions will be responsible for creating alarms and events.

### 1.3.2 Container

No new containers are introduced for this feature. Existing Mgmt container will be updated.

### 1.3.3 SAI Overview

No new or existing SAI services are required

Note that the SAI specification includes a BFD capability for SAI acceleration of BFD - this is not used in this feature

*---------------------------------- Stop here for the first stage review -----------------------------------------*

# 2 Functionality

*Feature specific. Much of the overview and usage should already be covered in section 1. This section is for more detailed functional descriptions as required.*

# 3 Design
## 3.1 Overview
*Big picture view of the actors involved - containers, processes, DBs, kernel etc. What's being added, what's being changed, how will they interact etc. A diagram is strongly encouraged.*

### 3.1.1 Service and Docker Management

*Discuss the dockers affected by the feature. If a new service and/or a new docker is introduced, please follow the guidelines below:*

- *Identify the dependencies on other services. This includes the starting order, restart dependencies on other services, etc. Please take the multiple images (Cloud Base, Enterprise Advanced) into consideration - where is this feature included/excluded?*
- *Identify the processes in the docker and their starting order (if applicable); specify process restartability needs and dependencies*

### 3.1.2 Packet Handling
*e.g. Discuss CoPP queue/priority and limits here*

## 3.2 DB Changes
*Describe changes to existing DB tables or any new tables being added. Cover schema and defaults.*

*Note that changes to existing DB contents (keys, fields) should be avoided where possible, and handled very carefully where necessary. Need to consider forward/backward migration etc.*

### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB
### 3.2.6 ERROR DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
*List/describe all the orchagents that are added/changed - sub-section for each.*

### 3.3.2 Other Processes 
*Describe adds/changes to other processes within SwSS (if applicable) - e.g. \*mgrd, \*syncd*

## 3.4 SyncD
*Describe changes to syncd (if applicable).*

## 3.5 SAI
*Describe SAI APIs used by this feature. State whether they are new or existing.*

## 3.6 User Interface
*Please follow the SONiC Management Framework Developer Guide - https://drive.google.com/drive/folders/1J5_VVuwoJBa69UZ2BoXLYW8PZCFIi76K*

### 3.6.1 Data Models
*Include at least the short tree form here (as least for standard extensions/deviations, or proprietary content). The full YANG model can be a reference another file as desired.*

### 3.6.2 CLI
*Describe the type (Klish, Click etc) and content of the CLI. Klish is the preferred choice in almost all cases, and we are aiming for 100% coverage. Generally other choices would only be used where you are extending an existing feature with other prior command support.*

- *Klish commands must be added in the appropriate manner, including:*
   - *full command syntax, with descriptions*
   - *command modes*
   - *Follow IS-CLI syntax (incl "no" form)*
- *Klish command specs also ideally include:*
   - *Usage / Help string*
   - *Command line completion options*
   - *Error messages*
   - *show output formats*
   - *show running-config outputs*

*Where there are command interactions (e.g. dependencies, ordering) that are not obvious, then please state some "best practices" for the configuration sequence(s).*
*Also cover backward compatibility (if applicable). For instance, if existing commands are being changed, how is compatibility maintained? Any command deprecation?*

*This content should go into the following sub-sections.*

#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 Show Commands
#### 3.6.2.3 Exec Commands
*e.g. "Clear" commands*

### 3.6.3 REST API Support
*URL-based view*

### 3.6.4 gNMI Support
*Generally this is covered by the YANG specification. This section should also cover objects where on-change and interval based telemetry subscriptions can be configured.*

## 3.7 Warm Boot Support
*Describe expected behavior and any limitations. Also describe any design artefacts in support of this.*

## 3.8 Upgrade and Downgrade Considerations
*If any - cover things like DB changes/versioning, config migration etc*

## 3.9 Resource Needs
*Describe any significant resource needs for the feature (esp. at scale) - memory, CPU, disk, I/O etc. Only cover for significant needs (designed decision) - not required for small/medium resource usages.*

# 4 Flow Diagrams
*Provide flow diagrams for inter-container and intra-container interactions.*

# 5 Error Handling
*Provide details about incorporating error handling feature into the design and functionality of this feature.*

# 6 Serviceability and Debug
***This section is important and due attention should be given to it**. Topics include:*

- *Commands: Debug commands are those that are not targeted for the end user, but are more for Dev, Support and QA engineers. They are not a replacement for user show commands, and don't necessarily need to comply with all command style rules. Many features will not have these.*
- *Logging: Please state specific, known events that will be logged (and at what severity level)*
- *Counters: Ensure that you add counters/statistics for all interesting events (e.g. packets rx/tx/drop/discard)*
- *Trace: Please make sure you have incorporated the debugging framework feature (or similar) as appropriate. e.g. ensure your code registers with the debugging framework and add your dump routines for any debug info you want to be collected.*

# 7 Scalability
*Describe key scaling factors and considerations.*

# 8 Platform
*Describe any platform support considerations (e.g. supported/not, scaling, deviations etc)*

# 9 Limitations
*More detail on the limitations stated in requirements*

# 10 Unit Test
*List unit test cases added for this feature (one-liners). These should ultimately align to tests (e.g SPytest, Pytest) that can be shared with the Community.*

# 11 Internal Design Information
*Internal BRCM information to be removed before sharing with the community.*

## 11.1 IS-CLI Compliance
*This is here because we don't want to be too externally obvious about a "follow the leader" strategy. However it must be filled in for all Klish commands.*

*The following table maps SONIC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:*

- ***IS-CLI drop-in replace**  – meaning that it follows exactly the format of a pre-existing IS-CLI command.*
- ***IS-CLI-like**  – meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).*
- ***SONIC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONIC.*

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---:|:-----------:|:------------------:|-----------------------------------|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

***Deviations from IS-CLI:** If there is a deviation from IS-CLI, Please state the reason(s).*

## 11.2 Broadcom SONiC Packaging
*Cloud base vs. Enterprise etc*

## 11.3 Broadcom Silicon Considerations
*Where this feature is/not supported, silicon-specific scaling factors and behaviors*

## 11.4 Design Alternatives
*Please state any significant design alternatives considered (if any), and why these were not chosen*

## 11.5 Broadcom Release Matrix
*Please state the Broadcom release in which a feature is planned to be introduced. Where a feature spans multiple releases, then please state which enhancements/sub-features go into which Broadcom release*
|Release|Change(s)|
|:-------:|:-------------------------------------------------------------------------|
| | |
