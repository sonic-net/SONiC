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
This document provides comprehensive functional and design information about the certificate management feature implementation in SONiC.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| PKI                      | Public Key Infrastructure           |
| CSR                      | Certificate Signing Request         |
| gNMI                     | gRPC Network Management Interface   |
| gNOI                     | gRPC Network Operations Interface   |
| CA                       | Certificate Authority               |
| PEM                      | Privacy Enhanced Mail               |
| CRL                      | Certificate Revocation List         |
# 1 Feature Overview

X.509 Public Key Certificates are used by REST and gNMI services currently and will be used by other services in the future. Configuring these certificates requires manually generating and placing the certificate and key files on the filesystem manually. Then you must configure the redis keys manually as well and restart the services. There is also the issue of upgrades where the location of the certificates are placed is not preserved causing these services to break until the files locations are restored. Finally, when certificates expire or are about to expire, there is no warning or alarm for this event or any other issue with the certificates such as invalid hostnames, weak encryption, revocation etc.

The certificate management feature will introduce a new YANG model and CLI to address the above issues. It will handle certificate generation and file management along with association of these certificates with a given service via a security profile. It will also ensure that the certificates are available after upgrade/downgrade and handle certificate rotation and alarms to alert on certificate issues. RPCs will be defined in the YANG model and exposed via REST and gNOI RPC interfaces to trigger certificate related actions.

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

### Overview
  - Certificate Management is a set of YANG models, CLIs and scripts to generate, install, configure and monitor PKI certificates and the services that use them. Security profiles will be used to associate a service with a certificate and key pair.

### Functionality
  - Establish a directory in the filesystem that all certificates and keys will be installed in to and that will be preserved through upgrades and downgrades.
  - Create YANG model for managing certificate and security profile information.
  - Create scripts to generate, download and verify certificates as well as configure services.
  - Integrate with sysmonitor.py to periodically validate certificates/configurations and raise alarms if needed.
  - Create CLI to generate/download certificates & signing requests and configure services.
  - Integrate with gNOI Certificate RPCs.

### Interfaces
 - The configuration of the certificate management YANG model will be available via the CLI, but also the REST and gNMI/gNOI interfaces on the management interface.

### Configurability
  - Install CA certificate from local file, remote location or copy and past into CLI
  - Generate self-signed certificate 
  - Generate certificate signing request (CSR)
  - Install certificate or private key from local file, remote location
  - Delete CA certificate
  - Delete certificate
  - Display certificate
  - Display trusted CAs
  - Display raw PEM Format certificate
  - Configure certificate revocation check behavior
  - Refresh CRL
  - Configure CRL download location(s)
  - Configure CRL Override
  - Display CRL
  - Create new security profile4.15. - Delete security profile
  - Associate a certificate and private key file with a security-profile
  - Apply security profile to service
  - Remove association of security profile with service

### User Interfaces  
  - The feature is managed through the SONiC Management Framework, including full support for Klish, REST and gNMI  

### Serviceability  
  - UI show commands are provided to show session states  
  - All session events are logged 
  - Alarms are raised for certificate issues
  - RPCs will return error codes and messages

### Scaling
  - No known issues with scaling

### Warm Boot/ISSU
  - Warm boot will causes services to restart. On restart services will continue to use their configured certificates.

### Platforms  
  - Certificate management is supported on all SONiC platforms  

### Feature Interactions/Exclusions  
  - HTTP server certificate and CA will be configured with this feature
  - gNMI server certificate and CA will be configured with this feature
  - Other services will be integrated in the future

### Limitations  
  - Services must be restarted in for new certificates to take effect
  - If an invalid certificate is configured, services including REST and gNMI/gNOI may become inaccessible. However the CLI will continue to work.

## 1.3 Design Overview
### 1.3.1 Basic Approach

The certificate management functionality will be implemented using a new YANG model and accompanying KLISH CLI. THe functionality of generating new certificate and key pairs, signing request, downloading and installing will be implemented in a python script that the CLI will call. The script will use the already installed openssl tools on the system for the certificate generation, signing etc. THe downloading of the certificates from remote locations will be handled with calls to curl.

To monitor the certificates validity and the correct configuration of the services, new periodically called functions will be added to SONiC sysmonitor.py script. These functions will be responsible for creating alarms and events.

### 1.3.2 YANG Model

The YANG model will describe the following structure(s) and field(s):

  - security-profile
    - profile-name
    - certificate-filename
    - revocation-check
    - peer-name-check
    - key-usage-check

To align with the gNOI [cert.proto](https://github.com/openconfig/gnoi/blob/master/cert/cert.proto), the following RPCs will be defined, but initially only available in gNOI due to limitations with REST RPCs:

**Table 1: gNOI RPCs**

| **RPC Name**                   | **Description** |
| ------------------------------ | --------------- |
| Rotate                         | Rotate will replace an existing Certificate on the target by creating a new CSR request and placing the new Certificate based on the CSR on the target. If the stream is broken or any steps in the process fail the target must rollback to the original Certificate. |
| Install                        | Install will put a new Certificate on the target by creating a new CSR request and placing the new Certificate based on the CSR on the target.The new Certificate will be associated with a new Certificate Id on the target. If the target has a pre existing Certificate with the given Certificate Id, the operation should fail. If the stream is broken or any steps in the process fail the target must revert any changes in state. |
| GenerateCSR                    | When credentials are generated on the device, generates a keypair and returns the Certificate Signing Request (CSR). The CSR has the public key, which when signed by the CA, becomes the Certificate  |
| LoadCertificate                | Loads a certificate signed by a Certificate Authority (CA). |
| LoadCertificateAuthorityBundle | Loads a bundle of CA certificates. |
| GetCertificates                | An RPC to get the certificates on the target. |
| RevokeCertificates             | An RPC to revoke specific certificates. If a certificate is not present on the target, the request should silently succeed. Revoking a certificate should render the existing certificate unusable by any endpoints. |
| CanGenerateCSR                 | An RPC to ask a target if it can generate a Certificate. |

In addition, to facilitate local generation of self-signed certificates and easier KLISH implementation these RPCs will also be defined for both REST and gNOI:

**Table 2: Custom RPCs**

| **RPC Name**                   | **Description** |
| ------------------------------ | --------------- |
| crypto-ca-cert-install | This procedure is used to install an X.509 CA certificate |
| crypto-ca-cert-delete | This procedure is used to delete an X.509 CA certificate |
| crypto-host-cert-install | This procedure is used to install the X.509 host certificate |
| crypto-host-cert-delete | This procedure is used to delete the X.509 host certificate |
| crypto-cdp-delete | This procedure is used to install an X.509 certificate revocation list |
| crypto-cdp-add | This procedure is used to install an X.509 certificate revocation list |
| crypto-crl-install | This procedure is used to install an X.509 certificate revocation list |
| crypto-crl-delete | This procedure is used to delete an X.509 certificate revocation list |
| crypto-cert-generate | This procedure is used to create X.509 CSRs and self-signed certificates |


### 1.3.3 KLISH CLI

A new CLI will be added with the following commands:



### 1.3.4 Monitoring

The sysmonitor.py script will be enhanced to detect the following conditions:

**Table 3: Alarms**

| **Alarm Name** | **Severity** | **Description** |
| -------------- | ------------ | --------------- |
| Certificate Expiration | Warning | The host certificate is within 7 days of expiring |
| Certificate Expired | Alarm | The host certificate has expired |
| CA Certificate Expiration | Warning | The CA certificate is within 7 days of expiring |
| CA Certificate Expired | Alarm | The CA certificate has expired |
| Revoked Certificate | Alarm | The host certificate has been revoked |
| Revoked CA Certificate | Alarm | The CA certificate has been revoked |
| Certificate Misconfigured | Warning | An application that is configured to use a certificate has been manually changed to another certificate |
| CA Certificate Misconfigured | Warning | An application that is configured to use a CA certificate has been manually changed to another CA certificate |

### 1.3.5 Directory Structure

THe directory `/etc/sonic/cert` will be used to store certificates and will be mounted on the containers by default. The directory will be preserved during upgrade/downgrade through the use of upgrade hook scripts.

### 1.3.6 Application Associations

Applications associations with certificates will be done the same way as they currently are via per-application redis DB keys for certificate location and CA certificate location. This will preserve backwards compatibility and does not require chaning the applications.

### 1.3.7 Container

No new containers are introduced for this feature. Existing Mgmt container will be updated.

### 1.3.8 SAI Overview

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
