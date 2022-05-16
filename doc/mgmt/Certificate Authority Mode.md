# Certificate Authority (CA) Mode

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
| 0.1 | <04/20/2022>|   Eric Seifert     | Initial version                   |

# About this Manual
This document provides comprehensive functional and design information about the certificate authority mode feature implementation in SONiC.

# Definition/Abbreviation

### Abbreviations
| **Term**                 | **Meaning**                             |
|--------------------------|-----------------------------------------|
| PKI                      | Public Key Infrastructure               |
| CSR                      | Certificate Signing Request             |
| gNMI                     | gRPC Network Management Interface       |
| gNOI                     | gRPC Network Operations Interface       |
| CA                       | Certificate Authority                   |
| PEM                      | Privacy Enhanced Mail                   |
| CRL                      | Certificate Revocation List             |
| FIPS                     | Federal Information Processing Standard |
| OCSP                     | Online Certificate Status Protocol      |

# 1 Feature Overview

Managing x.509 certificates can be a complicated task that many are not familiar with. Also, certificates expire or can be revoked require maintanence that is often overlooked. To make these tasks easier, automated certificate management services have been developed by other vendors and in open source. These services, once configured on each node handle creation, signing and distribution of certificates for servers and services. The goaal of the CA mode on SONiC would be to make certificate mangament easier while still maintinaing security.

## 1.1 Target Deployment Use Cases

The use case for certificates is any service that wants secure communication to the outside. This includes but is not limited to:

  - HTTPS Web Server (REST, Swagger UI etc.)
  - gNMI Telemetry/Configuration
  - Dialout Telemetry
  - Syslog
  - RADIUS
  - SSH

## 1.2 Requirements

### Overview
  - The certificate authority feature should allow for host and CA certificates to be generated, signed, installed rotated and revoked.


### Functionality
  - Generate CA certificate and can then sign certificates for other switches
  - Install CA certificate on remote switch using certificate management API
  - Add ability to sign CSR's

### Interfaces
 - The configuration of the certificate authority YANG model will be available via the CLI, but also the REST and gNMI/gNOI interfaces on the management interface.

### Configurability
  - Enable/Disable CA mode
  - Generate self-signed CA certificate, or use user installed one
  - Designate which hosts are allowed to get CSR's signed

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
  - Certificate authority server feature is supported on all SONiC platforms  

## 1.3 Design Overview
### 1.3.1 Basic Approach

The certificate authority server functionality will be implemented using a new YANG model and accompanying KLISH CLI. The functionality of generating new certificate and key pairs, signing request, downloading and installing will be implemented in a python script that the CLI will call. The script will use the already installed openssl tools on the system for the certificate generation, signing etc. The downloading of the certificates from remote locations will be handled with calls to curl.

### 1.3.2 YANG Model

The sonic-crypto YANG model will describe the following structure(s) and field(s):

  - ca-mode
    - ca-mode (true|false)
    - ca-host
    - csr-list
      - name
      - source
      - type

This model will also be proposed to the openconfig community. The model is discussed in more detail below.

### 1.3.3 KLISH CLI

A new CLI will be added with the following commands:

**CLI Commands**

| **Command** | **Description** |
| ----------- | --------------- |
| crypto ca-server mode | Enable CA server/client or disabled |
| crypto ca-server host | The CA server hostname/ip if in client mode |
| crypto ca-server list-csr | Show list of CSRs sent to us to be signed |
| crypto ca-server show-csr | Show details of CSR |
| crypto ca-server sign-csr | Sign CSR sent to us |
| crypto ca-server delete-csr | Reject and delete CSR sent to us |

The CA server mode will automatically generate a CA certificate to be used to sign other certificates. This CA certificate will be rotated automatically.

# 2 Functionality

The Certificate Authoirty Server Feature will extend the YANG model sonic-crypto with the section: ca-mode. 

# 3 Design
## 3.1 Overview

The model will be implemented in sonic-mgmt-common and will be used by the mgmt-framework and telemetry containers. 

The YANG model will store the configuration in the configdb and will add new table for ca-mode.

### 3.1.1 Service and Docker Management

No new containers will be added. The model will be configured via mgmt-framework and gNMI. 

## 3.2 DB Changes

### 3.2.1 CONFIG DB

The config DB will contain the new model's information.

## 3.3 User Interface

### 3.3.1 Data Models

#### sonic-crypto YANG model:


    +--rw ca-mode
       +--rw ca-mode                bool
       +--rw ca-host                string
       +--rw csr-list* [name]
           +--rw name               string
           +--rw source             string
           +--rw type               enum
   
### 3.3.2 CLI

#### 3.3.2.1 Configuration Commands



### 3.3.3 REST API Support

**URLs:**

    /sonic-crypto:ca-mode
    /sonic-crypto:ca-mode/ca-mode
    /sonic-crypto:ca-mode/ca-host
    /sonic-crypto:ca-mode/csr-list
    /sonic-crypto:ca-mode/csr-list/name
    /sonic-crypto:ca-mode/csr-list/source
    /sonic-crypto:ca-mode/csr-list/type

### 3.3.4 gNMI Support

The YANG model defined above will be available to read/write from gNMI as well as REST.

## 3.4 Upgrade and Downgrade Considerations
The certificate directory /etc/sonic/cert must be preserved during upgrades and downgrades. This is achieved using upgrade hook scripts that will copy from the directory to the new partition.

When upgrading from a sonic version before certificate management feature exists, per-application upgrade hook scripts will be used to migrate the old certificates and configuration into the new model.

In the case of migrating a config from one switch to another, there will be no automated way of migrating certificates. The user will have to manually re-install/generate the certificates as needed.

# 4 Error Handling


# 5 Platform

All sonic platforms will be supported.

# 6 Limitations

  - Currently no way to ensure that the time/date is the same between multiple switches which is important when generating certificates since they have start/end times. Either the API should require the client send what it thinks is current time or we should require NTP be configured.


# 7 Unit Test




