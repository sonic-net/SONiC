# Certificate Mangement

# High Level Design Document
# Table of Contents
- [1 Feature Overview](#1-Feature-Overview)
    - [1.1 Target Deployment Use Cases](#11-Target-Deployment-Use-Cases)
    - [1.2 Requirements](#12-Requirements)
    - [1.3 Design Overview](#13-Design-Overview)
        - [1.3.1 Basic Approach](#131-Basic-Approach)
        - [1.3.2 YANG Model](#132-YANG-Model)
        - [1.3.3 KLISH CLI](#133-KLISH-CLI)
        - [1.3.4 Validation](#134-Validation)
        - [1.3.5 Monitoring](#135-Monitoring)
        - [1.3.6 Directory Structure](#136-Directory-Structure)
        - [1.3.7 Application Associations](#137-Application-Associations)
        - [1.3.8 Container](#138-Container)
        - [1.3.9 SAI Overview](#139-SAI-Overview)
- [2 Functionality](#2-Functionality)
- [3 Design](#3-Design)
    - [3.1 Overview](#31-Overview)
        - [3.1.1 Service and Docker Management](#311-Service-and-Docker-Management)
    - [3.2 DB Changes](#32-DB-Changes)
        - [3.2.1 CONFIG DB](#321-CONFIG-DB)
    - [3.3 User Interface](#33-User-Interface)
        - [3.3.1 Data Models](#331-Data-Models)
        - [3.3.2 CLI](#332-CLI)
        - [3.3.2.1 Configuration Commands](#3321-Configuration-Commands)
        - [3.3.2.2 Show Commands](#3322-Show-Commands)
        - [3.3.2.3 Exec Commands](#3323-Exec-Commands)
        - [3.3.3 REST API Support](#333-REST-API-Support)
        - [3.3.4 gNMI Support](#334-gNMI-Support)
     - [3.4 Upgrade and Downgrade Considerations](#34-Upgrade-and-Downgrade-Considerations)
- [4 Error Handling](#4-Error-Handling)
- [5 Platform](#5-Platform)
- [6 Limitations](#6-Limitations)
- [7 Unit Test](#7-Unit-Test)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | <07/20/2021>|   Eric Seifert     | Initial version                   |
| 0.2 | <08/24/2021>|   Eric Seifert     | Add Functionality Section         |
| 0.3 | <09/17/2021>|   Eric Seifert     | Address Review Comments           |
| 0.4 | <08/18/2022>|   Eric Seifert     | Address comments                  |

# About this Manual
This document provides comprehensive functional and design information about the certificate management feature implementation in SONiC.

# Definition/Abbreviation

### Abbreviations
| **Term**                 | **Meaning**                             |
|--------------------------|-----------------------------------------|
| PKI                      | Public Key Infrastructure               |
| gNMI                     | gRPC Network Management Interface       |
| gNOI                     | gRPC Network Operations Interface       |
| CA                       | Certificate Authority                   |
| PEM                      | Privacy Enhanced Mail                   |
| CRL                      | Certificate Revocation List             |
| FIPS                     | Federal Information Processing Standard |
| OCSP                     | Online Certificate Status Protocol      |

# 1 Feature Overview

X.509 Public Key Certificates are used by REST and gNMI services currently and will be used by other services in the future. Configuring these certificates requires manually generating and placing the certificate and key files on the filesystem. Then you must configure the redis keys and restart the services. There is also the issue of upgrades where the location the certificates are placed is not preserved causing these services to break until the files locations are restored. Moreover the process of generating certificates, especially CA certificates and signing and distributing them is complex and error prone. Finally, when certificates expire or are about to expire, there is no warning or alarm for this event or any other issue with the certificates such as invalid hostnames, weak encryption, revocation etc.

The certificate management feature will introduce a new YANG model and CLIs to address the above issues. It will handle certificate generation, signing, distribution and file management along with association of these certificates with a given service via a security profile. It will also ensure that the certificates are available after upgrade/downgrade and handle certificate rotation and alarms to alert on certificate issues. RPCs will be defined in the YANG model and exposed via REST and gNOI RPC interfaces to trigger certificate related actions.

The feature will be done in two phases. Phase one will supply the CLI and basic certificate management functionality to install, delete, view and assosciate certificates with services to replace the current manual process. Phase two will provide a CA mode to facilitate the creation, signing, distribution and rotation of certificates.

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
  - The certificate management feature should allow for host and CA certificates to be installed and removed as well as applied to specific applications. Certificates should also be validated and monitored for issues such as expiration and revocation.


### Functionality
  - Establish a directory in the filesystem that all certificates and keys will be installed in to and that will be preserved through upgrades and downgrades.
  - Add ability to install host and CA certificates
  - Decrypt password protected certs when installed and store the unencrypted certs
  - Allow install of certificate bundles by breaking bundle apart and saving each cert in its own file with suffix number
  - Support DER format certificates as well as PEM
  - Allow trusted-host certificates (self-signed host certs) to be installed in trust-store as well as CA certs
  - Add ability to remove host and CA certificates
  - Add ability to configure CRL
  - Add ability to configure OCSP
  - Add ability to associate host and CA certs with application
  - Add CLIs to configure and manage certificates
  - Add validation and monitoring of certificates
  - FIPS support: install fips keys and use only in fips mode. Only fips or non-fips certificates will be allowed at once depending on the global setting.
  - Peer Name Checking. Each application using security-profile should check if peer-name-check is set and act accordingly.
  - Key usage check. Each application using security-profile should check if key-usage-check is set and if so verify the key is used appropriately.

### Interfaces
 - The configuration of the certificate management YANG model will be available via the CLI, but also the REST and gNMI/gNOI interfaces on the management interface.

### Configurability
  - Install CA certificate from local file (alias location), remote location or copy and past into CLI
  - Install certificate and private key from local file (alias location), remote location
  - Delete CA certificate
  - Delete certificate
  - Display certificate
  - Display trusted CAs
  - Display raw PEM Format certificate
  - Configure certificate revocation check behavior
  - Configure CRL download location(s)
  - Display CRL
  - Configure OCSP
  - Show OCSP
  - Create new security profile
  - Delete security profile
  - Associate a certificate, private key file and CA trust-store with a security-profile

### User Interfaces  
  - The feature is managed through the SONiC Management Framework, including full support for KLISH, REST and gNMI  

### Serviceability  
  - All session events are logged
  - Alarms are raised for certificate issues
  - RPCs will return error codes and messages
  - All RPC and API calls will be logged
  - YANG model will validate data and return errors as appropriate

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
  - Debian’s pre-installed ca-certificates will only be used by default Debian applications that have not been enabled to use the certificate management infrastructure.

## 1.3 Design Overview
### 1.3.1 Basic Approach

The certificate management functionality will be implemented using a new YANG model and accompanying KLISH CLI. The script will use the already installed openssl tools on the system for the certificate operations. The downloading of the certificates from remote locations will be handled with the existing file managament API.

To monitor the certificates validity and the correct configuration of the services, new periodically called functions will be added to SONiC sysmonitor.py script. These functions will be responsible for creating alarms and events and downloading CRL lists and make OCSP requests.

### 1.3.2 YANG Model

The sonic-crypto YANG model will describe the following structure(s) and field(s):

       +--rw PKI_GLOBALS
       |  +--rw PKI_GLOBALS_LIST* [name]
       |     +--rw name         enumeration
       |     +--rw fips-mode?   boolean
       +--rw SECURITY_PROFILES
       |  +--rw SECURITY_PROFILES_LIST* [profile-name]
       |     +--rw profile-name           string
       |     +--rw certificate-name?      -> /sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST/cert-name
       |     +--rw key-name?              string
       |     +--rw trust-store?           -> /sonic-pki/TRUST_STORES/TRUST_STORES_LIST/name
       |     +--rw revocation-check?      boolean
       |     +--rw peer-name-check?       boolean
       |     +--rw key-usage-check?       boolean
       |     +--rw cdp-list*              string
       |     +--rw ocsp-responder-list*   string
       +--rw TRUST_STORES
       |  +--rw TRUST_STORES_LIST* [name]
       |     +--rw name       string
       |     +--rw ca-name*   -> /sonic-pki/PKI_CA_CERTIFICATES/PKI_CA_CERTIFICATES_LIST/cert-name
       +--rw PKI_HOST_CERTIFICATES
       |  +--rw PKI_HOST_CERTIFICATES_LIST* [cert-name]
       |     +--rw cert-name    string
       |     +--rw key-name?    string
       +--rw PKI_CA_CERTIFICATES
          +--rw PKI_CA_CERTIFICATES_LIST* [cert-name]
             +--rw cert-name    string

This model will also be proposed to the openconfig community. The model is discussed in more detail below.

**Custom RPCs**

| **RPC Name**                   | **Description** |
| ------------------------------ | --------------- |
| crypto-ca-cert-install | This procedure is used to install an X.509 CA certificate |
| crypto-ca-cert-delete | This procedure is used to delete an X.509 CA certificate |
| crypto-host-cert-install | This procedure is used to install the X.509 host certificate |
| crypto-host-cert-delete | This procedure is used to delete the X.509 host certificate |
| crypto-ca-cert-display | This procedure retrieves and returns the x.509 CA cert |
| crypto-host-cert-display | This procedure retrieves and returns the x.509 host cert |
| crypto-cert-verify | This procedure validates the x.509 host cert |


### 1.3.3 KLISH CLI

A new CLI for REST and Telemetry will be added.
A new CLI will be added with the following commands:

**CLI Commands**

| **Command** | **Description** |
| ----------- | --------------- |
| crypto ca-cert install | Install CA cert from local (alias location) or remote location or via pasting raw cert file |
| crypto ca-cert delete | Delete CA certificate |
| crypto ca-cert verify | Verify CA certificate |
| crypto cert install | Install host certificate from local (alias location) or remote location |
| crypto cert delete | Delete host certificate |
| crypt cert verify | Verify host cert |
| show crypto cert | Show installed certificates list or specific cert details |
| show crypto ca-cert | Show installed CA certificates list or specific cert details |
| show crypto cert file | Show raw host certificate file in PEM format |
| show crypto ca-cert file | Show raw CA certificate file in PEM format |
| crypto security-profile <name> | Create security-profile |
| crypto security-profile certificate | Associate security-profile with certificate |
| crypto security-profile trust-store | Associate security-profile with trust-store |
| crypto security-profile ocsp-list | Associate security-profile with ocsp list |
| crypto security-profile cdp-list | Associate security-profile with cdp list |
| crypto trust-store <name> | Create new or access existing trust-store |
| crypto trust-store <name> ca-cert <ca-name> | Add CA cert to trust-store |

**Note:**
Association of security-profile to application happens in the application specific CLI (i.e. telemetry, rest etc.). The CLIs will follow the format below:

`rest security-profile <profile-name>`

### 1.3.4 Validation

When the security-profile model is configured and the RPC's are called, the data and files passed will be validated and return appropriate errors if invalid configuration is applied. The following validations will be run at configuration time:

**Validations**

| **Operation** | **Condition** | **Response** |
| ------------- | ------------- | ------------ |
| Host cert install | Invalid Certificate | Return invalid certificate error with output of openssl verify command indicating specific condition |
| CA cert install | Invalid Certificate | Return invalid certificate error with output of openssl verify command indicating specific condition |
| Delete Host Cert | Certificate in use | Return certificate in use error |
| Delete CA Cert | Certificate in use | Return certificate in use error |
| Delete CA Cert | Certificate is root CA for another cert | Return certificate is root CA for child error |

**Notes:**
  - In addition, checking if a certificate has been revoked must be enabled on a per-application basis (rest, gNMI etc.) in the options provided to the server tls settings.
  - Validation of certificate validity will be done via openssl verify and will be done at install time, association with a security-profile and association with an application.

### 1.3.5 Monitoring

The sysmonitor.py script will be enhanced to detect the following conditions, and using the event management framework, raise the appropriate alarm. A new certificate monitoring thread will be added to sysmonitor.py to periodically check the certificates.

**Alarms**

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
| CDP connection failed | EVENT | WARNING | Failed to connect and download from CDP server |

*Notes:*
  - The certificate expiration alarms will be rechecked when a new certificate is installed and cleared if the condition is resolved by the new certificate.
  - Alarms for invalid certificates will only be raised on certificates that are currently in use by a security-profile. If you attempt to use an expired certificate, it will be rejected during configuration validation instead.

### 1.3.6 Directory Structure

The directory `/etc/sonic/cert` will be used to store certificates and will be mounted on the containers by default. The directory will be preserved during upgrade/downgrade through the use of upgrade hook scripts. All certificate copying, generation and associations will only use this directory path as the target. Under this directory will contain the following sub-directories:

  - ca
  - ca/<trust-store-name>
  - certs
  - keys

The keys directories and all files within will have correct permissions 0700 so that no unauthorized users can read the private key files. The fips directory will store the fips mode keys and certs separately from the non-fips mode keys/certs. The trust-store directory will hold directories named after the trust-stores and symlinks to each certificate in the trust-store. There will be one default system trust-store directory that will be a symlink to the host system's trust-store directory (/etc/ssl/certs). Any certificate added to this trust store will be added to the system trust-store and update-ca-certificates will be ran.

### 1.3.7 Application Associations

Applications associations with certificates will be done the same way as they currently are via per-application redis DB keys for certificate location and CA certificate location. This will preserve backwards compatibility and does not require changing the applications. The association will be managed by per-application CLI.

### 1.3.8 Container

No new containers are introduced for this feature. Existing Mgmt container will be updated.

### 1.3.9 SAI Overview

No new or existing SAI services are required.

# 2 Functionality

The Certificate Management Feature will implement a new YANG model sonic-crypto with these section: security-profile, trust-store and cdp-config. The security-profile will be for associating certificates with applications as well as providing options for using those certificates. The model will also have RPCs defined for all certificate related actions.

A set of functions and a certificate monitor thread will be created in sysmonitor.py that will be used to monitor the certificates and configurations and raise appropriate alarms and events.

# 3 Design
## 3.1 Overview
*Big picture view of the actors involved - containers, processes, DBs, kernel etc. What's being added, what's being changed, how will they interact etc. A diagram is strongly encouraged.*

The model will be implemented in sonic-mgmt-common and will be used by the mgmt-framework and telemetry containers. The sysmonitor.py is in sonic-buildimage and will run on the host. The certificates themselves will be stored on the host in /etc/sonic/cert and will be mounted on all of the containers by default.

The YANG model will store the configuration in the configdb and will add new tables, for security-profiles, trust-store and cdp-config.

### 3.1.1 Service and Docker Management

No new containers will be added. The model will be configured via mgmt-framework and gNMI. The monitoring will run on the host as part of sysmonitor.py. No new services will be running either since the monitoring will be periodic and handled by sysmonitor.py.

## 3.2 DB Changes

### 3.2.1 CONFIG DB

The config DB will contain the new model's information.

## 3.3 User Interface

### 3.3.1 Data Models

#### sonic-pki YANG model:

    module: sonic-pki
        +--rw sonic-pki
          +--rw PKI_GLOBALS
          |  +--rw PKI_GLOBALS_LIST* [name]
          |     +--rw name         enumeration
          |     +--rw fips-mode?   boolean
          +--rw SECURITY_PROFILES
          |  +--rw SECURITY_PROFILES_LIST* [profile-name]
          |     +--rw profile-name           string
          |     +--rw certificate-name?      -> /sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST/cert-name
          |     +--rw key-name?              string
          |     +--rw trust-store?           -> /sonic-pki/TRUST_STORES/TRUST_STORES_LIST/name
          |     +--rw revocation-check?      boolean
          |     +--rw peer-name-check?       boolean
          |     +--rw key-usage-check?       boolean
          |     +--rw cdp-list*              string
          |     +--rw ocsp-responder-list*   string
          +--rw TRUST_STORES
          |  +--rw TRUST_STORES_LIST* [name]
          |     +--rw name       string
          |     +--rw ca-name*   -> /sonic-pki/PKI_CA_CERTIFICATES/PKI_CA_CERTIFICATES_LIST/cert-name
          +--rw PKI_HOST_CERTIFICATES
          |  +--rw PKI_HOST_CERTIFICATES_LIST* [cert-name]
          |     +--rw cert-name    string
          |     +--rw key-name?    string
          +--rw PKI_CA_CERTIFICATES
              +--rw PKI_CA_CERTIFICATES_LIST* [cert-name]
                +--rw cert-name    string

      rpcs:
        +---x crypto-ca-cert-install
        |  +---w input
        |  |  +---w file-path?       string
        |  |  +---w file-contents?   string
        |  |  +---w file-name?       string
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        +---x crypto-ca-cert-delete
        |  +---w input
        |  |  +---w file-name?   string
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        +---x crypto-host-cert-install
        |  +---w input
        |  |  +---w file-path?   string
        |  |  +---w key-path?    string
        |  |  +---w password?    string
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        +---x crypto-host-cert-delete
        |  +---w input
        |  |  +---w file-name?   string
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        +---x crypto-ca-cert-display
        |  +---w input
        |  |  +---w file-name?   string
        |  |  +---w raw-file?    boolean
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        |     +--ro cert-details*    string
        |     +--ro filename*        string
        +---x crypto-host-cert-display
        |  +---w input
        |  |  +---w file-name?   string
        |  +--ro output
        |     +--ro status?          int32
        |     +--ro status-detail?   string
        |     +--ro cert-details*    string
        |     +--ro filename*        string
        +---x crypto-cert-verify
          +---w input
          |  +---w cert-name?   string
          +--ro output
              +--ro status?          int32
              +--ro status-detail?   string
              +--ro verify-output?   string

### 3.3.2 CLI

#### 3.3.2.1 Configuration Commands

#### Create new or access existing trust-store

    crypto trust-store <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of trust-store |

#### Add/Remove CA to trust-store

    [no] crypto trust-store <ts name> ca-cert <cert name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| ts name | Trust Store Name
| ca-cert | name of existing CA cert to add to trust-store |

#### Create new or access existing security-profile

    crypto security-profile <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of security-profile |

#### Associate host certificate to security-profile

    crypto seurity-profile certificate <sp name> <cert>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| sp name | Name os security profile
| cert | name of existing host cert to associate with security-profile |

#### Associate trust-store to security-profile

    [no] crypto security-profile trust-store <sp name> <ts name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| sp name | security profile name |
| ts name | name of existing trust-store to associate with security-profile. If unset, the system trust-store will be used. |

#### Associate OCSP list to security-profile

    [no] crypto security-profile ocsp-list <sp name> <ocsp list>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| sp name | security profile name |
| ocsp list | Comma separated list of urls |

#### Associate CDP list to security-profile

    [no] crypto security-profile cdp-list <sp name> <cdp list>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| sp name | security profile name |
| cdp list | Comma separated list of urls |

#### Configure FIPS mode
    crypto fips <true/false>

#### Configure REST parameters
    [no] ip rest <attr>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| authentication | REST authentication modes |
| jwt-refresh | Time before JWT expiry the token can be refreshed |
| jwt-valid | Seconds that JWT token is valid |
| log-level | Log level |
| port | Port that the REST server listens on |
| read-timeout | Number of seconds the server waits for a valid http request to arrive on a connection |
| request-limit | Maximum number of concurrent requests allowed for REST server |
| security-profile | Security profile |

#### Configure REST parameters
    [no] ip telemetry <attr>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| authentication | Telemetry authentication modes |
| jwt-refresh | Time before JWT expiry the token can be refreshed |
| jwt-valid | Seconds that JWT token is valid |
| log-level | Log level |
| port | Port that the telemetry server listens on |
| security-profile | Security profile |

#### 3.3.2.2 Show Commands

#### Show host certificate(s)

    show crypto cert <name|all>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of certificate or all will show all host certificates |

#### Show CA cert(s)

    show crypto ca-cert <name|all>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of certificate or all will show all CA certificates |

#### Raw PEM Format Certificate

    show crypto cert file <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of certificate |

#### Raw PEM Format CA Certificate

    show crypto ca-cert file <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of certificate |

#### Security Profiles

    show crypto security-profile

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of security-profile |
    
#### Trust Stores

    show crypto trust-store

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | name of trust-store |

#### REST
    show ip rest
    
*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| authentication | Display REST authentication modes |
| jwt-refresh | Display JWT refresh time |
| jwt-valid | Display JWT valid time |
| log-level | Display log level |
| port | Display port that REST server is listening on |
| read-timeout | Display read timeout |
| request-limit | Display concurrent request limit |
| security-profile | Display security profile |



#### Telemetry
    show ip telemetry

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| authentication | Display telemetry authentication modes |
| jwt-refresh | Display JWT refresh time |
| jwt-valid | Display JWT valid time |
| log-level | Display log level |
| port | Display port that telemetry server is listening on |
| security-profile | Display security profile |


#### 3.3.2.3 Exec Commands

#### Install host certificate

    crypto cert install cert-file <URI> key-file <URI> password <password>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| cert-file | The certificate file location URI as defined by the file mgmt feature. URL or location alias i.e. home:// |
| key-file | The private key file location URI |
| password | Optional password if the private key file is password protected |

*Notes:*
  - The cert install rpc will also trigger a rechecking of the cert expiration alarms to clear alarms if the new certificate resolves the condition, instead of waiting for sysmonitor.py to check sometime later

#### Delete host certificate

    crypto cert delete <name|all>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | The certificate name or all which will delete all host certificates and keys |

#### Install CA Certificate

     crypto ca-cert install <URI>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| cert-file | Optional certificate file location URI as defined by the file mgmt feature. URL or location alias i.e. home://. If no URI is provided, the CLI will prompt to paste the CA certificate |

*Examples*

    sonic(config)# crypto ca-cert install <URI> 
    crypto ca-cert install home://GeoTrust_Universal_CA.crt
    Processing certificate ...
    Installed Root CA certificate
     CommonName = GeoTrust Universal CA
     IssuerName = GeoTrust Universal CA

The certificate between the begin and end tags will be extracted to facilitate pasting from a source such as an email containing other text.

    sonic(config)# crypto ca-cert install
    Certificate base file name : Dell_interCA1
    Paste certificate below.
    Include the -----BEGIN CERTIFICATE----- and -----END CERTIFICATE----- headers.
    Enter a blank line to abort this command.
    Certificate:
    -----BEGIN CERTIFICATE-----
    MIIFuzCCA6OgAwIBAgICEAAwDQYJKoZIhvcNAQELBQAwdzELMAkGA1UEBhMCVVMx
    EzARBgNVBAgMCkNhbGlmb3JuaWExFDASBgNVBAcMC1NhbnRhIENsYXJhMREwDwYD
    VQQKDAhEZWxsIEVNQzETMBEGA1UECwwKTmV0d29ya2luZzEVMBMGA1UEAwwMRGVs
    bF9yb290Q0ExMB4XDTE4MDcyNTE4NDkyMloXDTI4MDcyMjE4NDkyMlowYjELMAkG
    A1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExETAPBgNVBAoMCERlbGwgRU1D
    MRMwEQYDVQQLDApOZXR3b3JraW5nMRYwFAYDVQQDDA1EZWxsX2ludGVyQ0ExMIIC
    IjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAuEaThievPvunvcEldv1QhwLe
    mCuVLrBJ5Fx824O55z3jYWPp4elvpOu4Br9Xt7sX0VDufK3RCf7DLOp5v7n6klIi
    DkliC5e4ksJZQy5T4MbU6tXsNXlPwpWCkUPuPj2u46m6N5R5J7MN+VrMG/1tJNYA
    zh09SvqVlMilHGXM8AhKf3nHaE7COrW5IYIcJUX0foT5068oBguN2nLBQRrKwWPe
    1iXv+Oynk4jgoE+TFIGm6JAxerhTTFJE4VxqqpS2DetzuBgh1Zykc6RUFluvsDUN
    Nv/LcgRj0d9IWdPpUeHLKmEg7jElUWgOvpjDIpgp+RMDxC27StLPfQD5TC5GcOOr
    5zyRsMn3SInq599P9PX8Ohfc+IxI5aoDhNcge1Uuc2OFHJehu5aVodOuDHquAjws
    B7abxZdp+oi97IuIs5Dj3KqYFcaRmaTsUnOhF7MxkIh5jynITYOFaPR6Kr+ULvyU
    En/4Nm7YvY7ZynKF37ICknagnFKkr09/VwiIjw+DeaX8Xpbxq8DabaMbYtuNQFN7
    AZ4t/39UCS6FQgumdyh98gpwmDqtTtCeGKs5bUZNW3Uqhq9J70mBPluVyyjF28pi
    CNQlSgXqgIENc440mhPrLVdiHsg9OmkxNAJsN7o4iQrLzaLJRr4mVTBR9L/1up3s
    UJzLNSmRZtkldSF59kcCAwEAAaNmMGQwHQYDVR0OBBYEFKM5y8d2hjsFRDTCb5Bz
    H19kVVx2MB8GA1UdIwQYMBaAFHUiP76Zt/qhWx1oC+leIX2DYqzbMBIGA1UdEwEB
    /wQIMAYBAf8CAQAwDgYDVR0PAQH/BAQDAgGGMA0GCSqGSIb3DQEBCwUAA4ICAQCE
    A5u+roYvaVGTALbo628a3477On5B6kw3NLeDOyzfr5aHa0Z+NNo1UonrQgXWLXJu
    MO3p9+7HG/ShBYUU4aTKWQ+J5aYNqfrA8tc9kOE7yZDvXPOY2wB1zEtiKnmUEEEB
    PXdl8jYCfJRNe9n0KHZ6pTgn5lFRZhagldZCEnWQm7yVRYBaobS+Kjlnwds86/7z
    TNdlBEcrJaQFkfdRwyTa6FSdM3XMxMjNUD7g2wgJXOCRRTsi0U2GHmTGaZQIcARD
    LdUTAgrDUmQUPOX0oS9sdNb0gHxBKpDoaQ30IOe3YIrPuOtE8FnPFDtJp5ajYNwd
    6/uR2NaL76Gnt24P9xR6afixnkghUpO6g8ttv5rC3zhF/P64pjIjI42Kzx8Venxe
    GiPEjcG2x0o8X24+5zv5GSKdGWVtEh9+kKu2sycvNH6p9p1PMWeK/uXZ0ijYknx2
    FpY3nk/dw54Ci14Q/x+sBQQsFiqpHLKKalcLxFgXmamQ/HgahPYamHESljL3d4Dw
    44xIJHVURT2RIRHHBEK8H4uARLL6ouY71gK32IgUVw5D9PtFZPmkKS4Z0m8+VaFO
    86uf2A3B+7/8m7IkySRbi83J1USrEwwuQjQMcag9bTXVia9NOzPz02k29Ev67dSV
    YlJmoZLRJebozS40kikUc4jA2LJMNNaMJPNwihMqkA==
    -----END CERTIFICATE-----
    Processing certificate ...
    Installed CA certificate
     CommonName = Dell_interCA1
     IssuerName = Dell_rootCA1
    sonic(config)#

*Notes:*
  - The CA cert install rpc will also trigger a rechecking of the CA cert expiration alarms to clear alarms if the new certificate resolves the condition, instead of waiting for sysmonitor.py to check sometime later

#### Delete CA certificate

This command will first verify that you cannot delete a root CA that is used to verify other certificates.

    crypto ca-cert delete <name|all>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | The certificate name or all which will delete all CA certificates |

#### Verify Certificate

Verify certificate using openssl verify command.

    crypto cert verify <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | The certificate name which will be verified |

#### Verify CA Certificate

    crypto ca-cert verify <name>

*Parameters*
|**Name**|**Description**|
| ------ | ------------- |
| name | The CA certificate name which will be verified |

### 3.3.3 REST API Support

**URLs:**

    /sonic-pki:sonic-pki/PKI_GLOBALS:
    /sonic-pki:sonic-pki/PKI_GLOBALS/PKI_GLOBALS_LIST={name}:
    /sonic-pki:sonic-pki/PKI_GLOBALS/PKI_GLOBALS_LIST:
    /sonic-pki:sonic-pki/PKI_GLOBALS/PKI_GLOBALS_LIST={name}/name:
    /sonic-pki:sonic-pki/PKI_GLOBALS/PKI_GLOBALS_LIST={name}/fips-mode:

    /sonic-pki:sonic-pki/SECURITY_PROFILES:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/profile-name:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/certificate-name:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/key-name:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/trust-store:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/revocation-check:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/peer-name-check:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/key-usage-check:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/cdp-list:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/cdp-list={cdp-list}:
    /sonic-pki:sonic-pki/SECURITY_PROFILES/SECURITY_PROFILES_LIST={profile-name}/ocsp-responder-list:

    /sonic-pki:sonic-pki/TRUST_STORES:
    /sonic-pki:sonic-pki/TRUST_STORES/TRUST_STORES_LIST={name}:
    /sonic-pki:sonic-pki/TRUST_STORES/TRUST_STORES_LIST:
    /sonic-pki:sonic-pki/TRUST_STORES/TRUST_STORES_LIST={name}/name:
    /sonic-pki:sonic-pki/TRUST_STORES/TRUST_STORES_LIST={name}/ca-name:
    /sonic-pki:sonic-pki/TRUST_STORES/TRUST_STORES_LIST={name}/ca-name={ca-name}:

    /sonic-pki:sonic-pki/PKI_HOST_CERTIFICATES:
    /sonic-pki:sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST={cert-name}:
    /sonic-pki:sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST:
    /sonic-pki:sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST={cert-name}/cert-name:
    /sonic-pki:sonic-pki/PKI_HOST_CERTIFICATES/PKI_HOST_CERTIFICATES_LIST={cert-name}/key-name:
    /sonic-pki:sonic-pki/PKI_CA_CERTIFICATES:
    /sonic-pki:sonic-pki/PKI_CA_CERTIFICATES/PKI_CA_CERTIFICATES_LIST={cert-name}:
    /sonic-pki:sonic-pki/PKI_CA_CERTIFICATES/PKI_CA_CERTIFICATES_LIST:
    /sonic-pki:sonic-pki/PKI_CA_CERTIFICATES/PKI_CA_CERTIFICATES_LIST={cert-name}/cert-name:


### 3.3.4 gNMI Support

The YANG model defined above will be available to read/write from gNMI as well as REST.

## 3.4 Upgrade and Downgrade Considerations
The certificate directory /etc/sonic/cert must be preserved during upgrades and downgrades. This is achieved using upgrade hook scripts that will copy from the directory to the new partition.

When upgrading from a sonic version before certificate management feature exists, per-application upgrade hook scripts will be used to migrate the old certificates and configuration into the new model.

In the case of migrating a config from one switch to another, there will be no automated way of migrating certificates. The user will have to manually re-install/generate the certificates as needed.

# 4 Error Handling

The primary error handling will happen during configuration/RPC call time where data validation will occur to prevent invalid configuration. Secondly, since certificates can expire or be revoked, periodically the sysmonitor.py will check that the host and CA certificates are still valid and raise alarms if not. Also, events will be generated as certificates approach the invalidation time.

# 5 Platform

All sonic platforms will be supported.

# 6 Limitations

  - Currently the REST and gNMI processes need to be restarted in order to use new certificates and this can take a minute or more. For REST server in particular, this can be an issue since the sonic-cli must be exited and re-started when REST server restarts due to invalidation of the jwt token.
  - Currently no way to ensure that the time/date is the same between multiple switches which is important when generating certificates since they have start/end times. Either the API should require the client send what it thinks is current time or we should require NTP be configured.


# 7 Unit Test

  - Add certificate
  - Add security-profile
  - Add trust-store
  - Configure cdp
  - Apply security-profile to REST & telemetry server and validate it is applied correctly
  - Add CA certificate and client certificate and verify REST & telemetry server can be accessed without insecure mode
  - Use invalid client certificate with CA and verify it is rejected
  - Force CDP refresh


