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

X.509 Public Key Certificates are used by REST and gNMI services currently and will be used by other services in the future. Configuring these certificates requires manually generating and placing the certificate and key files on the filesystem manually. Then you must configure the redis keys manually as well and restart the services. There is also the issue of upgrades where the location of the certificates are placed is not preserved causing these services to break until the files locations are restored. Moreover the process of generating certificates, especially CA certificates and signing and distributing them is complex and error prone. Finally, when certificates expire or are about to expire, there is no warning or alarm for this event or any other issue with the certificates such as invalid hostnames, weak encryption, revocation etc.

The certificate management feature will introduce a new YANG model and CLI to address the above issues. It will handle certificate generation, signing, distribution and file management along with association of these certificates with a given service via a security profile. It will also ensure that the certificates are available after upgrade/downgrade and handle certificate rotation and alarms to alert on certificate issues. RPCs will be defined in the YANG model and exposed via REST and gNOI RPC interfaces to trigger certificate related actions.

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
  - The certificate management feature should allow for host and CA certificates to be installed, generated and removed as well as applied to specific applications. Certificates should also be validated and monitored for issues such as expiration and revocation.


### Functionality
  - Establish a directory in the filesystem that all certificates and keys will be installed in to and that will be preserved through upgrades and downgrades.
  - Add ability to install host and CA certificates
  - Add ability to remove host and CA certificates
  - Add ability to configure CRL
  - Add ability to generate self-signed certificates as well as certificate signing requests
  - Add ability to sign CSR's by running in a CA mode
  - Add ability to associate host and CA certs with application
  - Add CLIs to configure and manage certificates
  - Add validation and monitoring of certificates

### Interfaces
 - The configuration of the certificate management YANG model will be available via the CLI, but also the REST and gNMI/gNOI interfaces on the management interface.

### Configurability
  - Install CA certificate from local file (alias location), remote location or copy and past into CLI
  - Generate self-signed certificate 
  - Generate certificate signing request (CSR)
  - Install certificate or private key from local file (alias location), remote location
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
  - Create new security profile
  - Delete security profile
  - Associate a certificate and private key file with a security-profile
  - Apply security profile to service
  - Remove association of security profile with service
  - Have "CA mode" where switch generates CA certificate and can then sign certificates for other switches
  - Have option to specify CA server to have your CSR signed by it

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

The security-profile YANG model will describe the following structure(s) and field(s):

  - security-profile
    - profile-name
    - certificate-filename
    - CA Store (System or app specific)
    - revocation-check
    - peer-name-check
    - key-usage-check

This model will be for the CA server mode:

  - ca-mode
    - ca-mode (true|false)
    - csr-list
      - csr-hostname
      - csr-source

This model will define a CA certificate trust-store:

  - trust-store
    - name
    - ca-list
      - name

To align with the gNOI [cert.proto](https://github.com/openconfig/gnoi/blob/master/cert/cert.proto), the following RPCs will be defined, but initially only available in gNOI due to limitations with REST RPCs:

**Table 2: gNOI RPCs**

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

**Table 3: Custom RPCs**

| **RPC Name**                   | **Description** |
| ------------------------------ | --------------- |
| crypto-ca-cert-install | This procedure is used to install an X.509 CA certificate |
| crypto-ca-cert-delete | This procedure is used to delete an X.509 CA certificate |
| crypto-host-cert-install | This procedure is used to install the X.509 host certificate |
| crypto-host-cert-delete | This procedure is used to delete the X.509 host certificate |
| crypto-cdp-delete | This procedure is used to install an X.509 certificate revocation list |
| crypto-cdp-add | This procedure is used to install an X.509 certificate revocation list |
| crypto-cert-generate | This procedure is used to create X.509 CSRs and self-signed certificates |
| crypto-cert-ca-sign | Sign CSR that was sent to us |
| crypto-cert-signed-cert-get | Get/Download the signed certificate after the CA has signed it |

### 1.3.3 KLISH CLI

A new CLI will be added with the following commands:

**Table 4: CLI Commands**

| **Command** | **Description** |
| ----------- | --------------- |
| crypto ca-cert install | Install CA cert from local (alias location) or remote location |
| crypto ca-cert delete | Delete CA certificate |
| crypto cert generate | Generate signing request or self-signed host certificate |
| crypto cert install | Install host certificate from local (alias location) or remote location |
| crypto cert delete | Delete host certificate |
| show crypto cert | Show installed certificates |
| show crypto ca-certs | Show installed CA certificates |
| show file cert | Show raw certificate file in PEM format |
| crypto security-profile | Create security-profile |
| crypto security-profile certificate | Associate security-profile with certificate |
| crypto ca-server mode | Enable CA server/client or disabled |
| crypto ca-server host | The CA server hostname/ip if in client mode |
| crypto ca-server list-csr | Show list of CSRs sent to us to be signed |
| crypto ca-server show-csr | Show details of CSR |
| crypto ca-server sign-csr | Sign CSR sent to us |
| crypto ca-server reject-csr | Reject and delete CSR sent to us |
| crypto trust-store <name> | Create new or access existing trust-store |
| crypto trust-store <name> add <ca-name> | Add CA cert to trust-store |


The CA server mode will automatically generate a CA certificate to be used to sign other certificates. This CA certificate will be rotated automatically.

**Note:**
Association of security-profile to application happens in the application specific CLI (i.e. telemetry, rest etc.). The CLIs will follow the format below:

`rest security-profile <profile-name>`

### 1.3.4 Validation

When the security-profile model is configured and the RPC's are called, the data and files passed will be validated and return appropriate errors if invalid configuration is applied. The following validations will be run at configuration time:

**Table 5: Validations**

| **Operation** | **Condition** | **Response** |
| ------------- | ------------- | ------------ |
| Host cert install | Invalid Certificate | Return invalid certificate error |
| Host cert install | Expired Certificate | Return expired certificate error |
| Host cert install | Revoked Certificate | Return revoked certificate error |
| CA cert install | Invalid Certificate | Return invalid certificate error |
| CA cert install | Expired Certificate | Return expired certificate error |
| CA cert install | Revoked Certificate | Return revoked certificate error |
| Delete Host Cert | Certificate in use | Return certificate in use error |
| Delete CA Cert | Certificate in use | Return certificate in use error |
| CSR Create | Invalid CSR | Return invalid CSR error |


In addition, checking if a certificate has been revoked must be enabled on a per-application basis (rest, gNMI etc.) in the options provided to the server tls settings.

### 1.3.5 Monitoring

The sysmonitor.py script will be enhanced to detect the following conditions, and using the event management framework, raise the appropriate alarm:

**Table 6: Alarms**

| **Name** | **Type** | **Severity** | **Description** |
| -------- | -------- | ------------ | --------------- |
| Certificate Expiration | EVENT | WARNING | The host certificate is within 60 days of expiring |
| Certificate Expiration | EVENT | WARNING | The host certificate is within 30 days of expiring |
| Certificate Expiration | EVENT | WARNING | The host certificate is within 14 days of expiring |
| Certificate Expiration | EVENT | WARNING | The host certificate is within 7 days of expiring |
| Certificate Expired | ALARM | CRITICAL | The host certificate has expired |
| CA Certificate Expiration | EVENT | WARNING | The CA certificate is within 60 days of expiring |
| CA Certificate Expiration | EVENT | WARNING | The CA certificate is within 30 days of expiring |
| CA Certificate Expiration | EVENT | WARNING | The CA certificate is within 14 days of expiring |
| CA Certificate Expiration | EVENT | WARNING | The CA certificate is within 7 days of expiring |
| CA Certificate Expired | ALARM | CRITICAL | The CA certificate has expired |
| Revoked Certificate | ALARM | CRITICAL | The host certificate has been revoked |
| Revoked CA Certificate | ALARM | CRITICAL | The CA certificate has been revoked |
| Certificate Misconfigured | ALARM | WARNING | An application that is configured to use a certificate has been manually changed to another certificate |
| CA Certificate Misconfigured | ALARM | WARNING | An application that is configured to use a CA certificate has been manually changed to another CA certificate |


Also, the CA server mode will automatically generate a CA certificate to be used to sign other certificates. This CA certificate will be rotated automatically and so sysmonitor.py will periodically check and rotate the CA certificate as needed.

### 1.3.6 Directory Structure

THe directory `/etc/sonic/cert` will be used to store certificates and will be mounted on the containers by default. The directory will be preserved during upgrade/downgrade through the use of upgrade hook scripts. All certificate copying, generation and associations will only use this directory path as the target.

### 1.3.7 Application Associations

Applications associations with certificates will be done the same way as they currently are via per-application redis DB keys for certificate location and CA certificate location. This will preserve backwards compatibility and does not require changing the applications. The association will be managed by per-application CLI.

### 1.3.8 Container

No new containers are introduced for this feature. Existing Mgmt container will be updated.

### 1.3.9 SAI Overview

No new or existing SAI services are required

Note that the SAI specification includes a BFD capability for SAI acceleration of BFD - this is not used in this feature

# 2 Functionality

The Certificate Management Feature will implement two new YANG models, security-profile and ca-mode. The security-profile model will be for associating certificates with applications as well as providing options for using those certificates. The ca-mode model will be for managing the CA certificates, CSRs and configuring a CA server either locally (server mode) or remotely (client mode). The models will also have RPCs defined for all certificate related actions.

A set of functions will be created in sysmonitor.py that will be used to monitor the certificates and configurations and raise appropriate alarms and events.

# 3 Design
## 3.1 Overview
*Big picture view of the actors involved - containers, processes, DBs, kernel etc. What's being added, what's being changed, how will they interact etc. A diagram is strongly encouraged.*

The models will be implemented in sonic-mgmt-common and will be used by the mgmt-framework and telemetry containers. The sysmonitor.py is in sonic-buildimage and will run on the host. The certificates themselves will be stored on the host in /etc/sonic/cert and will be mounted on all of the containers by default.

The YANG models will store their configuration in the configdb and will add two new tables, for security-profiles and ca-mode.

### 3.1.1 Service and Docker Management

No new containers will be added. The models will be configured via mgmt-framework and gNMI. The monitoring will run on the host as part of sysmonitor.py. No new services will be running either since the monitoring will be periodic and handled by sysmonitor.py.

### 3.1.2 Packet Handling
N/A

## 3.2 DB Changes

### 3.2.1 CONFIG DB

The config DB will contain the new model's information.

## 3.3 Switch State Service Design
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface

### 3.6.1 Data Models

security-profile:

    +--rw security-profile* [profile-name]
       +--rw profile-name            string
       +--rw certificate-name?       leaf-ref
       +--rw trust-store?            leaf-ref
       +--rw revocation-check?       boolean
       +--rw peer-name-check?        boolean
       +--rw key-usage-check?        boolean

ca-mode:

    +--rw ca-mode
       +--rw ca-mode                bool
       +--rw csr-list* [csr-hostname]
           +--rw csr-hostname       string
           +--rw csr-source         string

trust-store:

    +--rw trust-store
       +--rw name                   string
       +--rw ca-list* [name]
           +--rw certificate-name?  leaf-ref


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

*Install host certificate*

    crypto cert install cert-file <URI> key-file <URI> password <password>

*Delete host certificate*

    crypto cert delete <name|all>

*Install CA Certificate*

    crypto ca-cert install <URI> 

*Delete CA certificate*

    crypto ca-cert delete <name|all>

*Configure CRL frequency*

    crypto x509 crl frequency <days>

*Refresh CRL*

    crypto cert refresh crl

*Configure CRL download location*

    [no] revocation crl identifier

#### 3.6.2.2 Show Commands

*Show host certificate(s)*

    show crypto cert <name|all>

*Show CA cert(s)*

    show crypto ca-cert <name|all>

*Raw PEM Format Certificate*

    show file cert <name>

*Create new or access existing trust-store*

    crypto trust-store <name>

*Add/Remove CA to trust-store*

    [no] ca-cert <name>

*Create new or access existing security-profile*

    security-profile <name>

*Associate host certificate to security-profile*

    certificate <name>

*Associate trust-store to security-profile*

    trust-store <name|system|none>




#### 3.6.2.3 Exec Commands
*e.g. "Clear" commands*

### 3.6.3 REST API Support
*URL-based view*

### 3.6.4 gNMI Support
The YANG models defined above will be available to read/wrtie from gNMI as well as REST. In addition to the RPCs defined, gNOI defines a set of certificate management RPCs here: [https://github.com/openconfig/gnoi/blob/master/cert/cert.proto](https://github.com/openconfig/gnoi/blob/master/cert/cert.proto) and are described above.

## 3.7 Warm Boot Support
N/A

## 3.8 Upgrade and Downgrade Considerations
The certificate directory /etc/sonic/cert must be preserved during upgrades and downgrades. This is acheived using upgrade hook scripts that will copy from the directory to the new partition.

## 3.9 Resource Needs
N/A

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
N/A

# 8 Platform
All sonic platforms will be supported.

# 9 Limitations
Currently the REST and gNMI processes need to be restarted in order to use new certificates and this can take a minute or more. For REST server in particular, this can be an issue since the sonic-cli must be exited and re-started when REST server restarts due to invalidation of the jwt token.

# 10 Unit Test

	- Add certificate
	- Add security-profile
	- Apply security-profile to REST & telemetry server and vilidate it is applied correctly
	- Add CA certificate and client certificate and verify REST & telemetry server can be accessed without insecure mode


