# Feature Name
TACACS+ Support in Management Framework
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author          | Change Description                   |
|:---:|:-----------:|:---------------------:|--------------------------------------|
| 0.1 | 10/29/2019  |   Joyas Joseph        | Initial version                      |
| 0.2 | 12/26/2019  |   Srinadh Penugonda   | Updated with CLI, yang tree          |
| 0.3 | 05/05/2020  | Venkatesan Mahalingam | Updated for source-interface support |

# About this Manual
This document provides general information about Terminal Access Controller Access Control Service Plus (TACACS+) support in SONiC Management Framework
# Scope
The scope of this document is within the bounds of the functionality provided by the new SONiC Management Framework. The underlying TACACS+
support in SONiC is provided by this high-level design document:
[TACACS+ Authentication](https://github.com/Azure/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md)

## Table 1

| Term |     Meaning            |
|:----:|:----------------------:|
|NBI   |	North Bound Interface |


# 1 Feature Overview
This feature allows the user to configure TACACS+ Authentication using NBI (CLI/REST/gNMI) provided by SONiC Management Framework.
Configuration changes from the user are pushed to CONFIG DB. The implementation is contained within the Management Framework container.

## 1.1 Requirements

### 1.1.1 Functional Requirements
1. Support TACACS+ login authentication for SSH and console.
2. Support Source interface to pick source address for TACACS+ packets can be specified.
3. Support multiple TACACS+ server, and the priority of the server can be configured.
4. Support to set the order of local authentication and TACACS+ authentication.
5. Support fail_through mechanism for authentication. If a TACACS+ server authentication fails, the next TACACS+ server authentication will be performed.

### 1.1.2 Configuration and Management Requirements
1. CLI configuration/show support
2. REST API support
3. gNMI support

## 1.2 Design Overview
### 1.2.1 Basic Approach
1. Implement TACACS+ support using transformer in sonic-mgmt-framework by using openconfig-system.yang.

### 1.2.2 Container
The changes are in the sonic-mgmt-framework container. There will be additional files added.
1. XML file for the CLI
2. Python script to handle CLI request (actioner)
3. Jinja template to render CLI output (renderer)
4. YANG models
	a. openconfig-aaa.yang and its dependents
	b. openconfig-tacacs.yang and its dependents

# 2 Functionality
## 2.1 Target Deployment Use Cases
TACACS+ is a security protocol used in AAA framework to provide centralised authentication for users who want to gain access to the network.
TACACS+ provides authorization control by allowing a network administrator to define what commands a user may run.

## 2.2 Functional Description
Since openconfig-system.yang is being used, both radius and tacacs+ configuration would be sharing same configuration parameters. They are
differentiated with the help of server-groups. server-group by name "TACACS" will be used to store tacacs+ specific configuration.

The configuration supports global parameters, namely: timeout, source interface (to pick the source IP) for outgoing packets, type of authentication method to use for messages,
a shared secret for encryption.
The configuration allows configuring tacacs host, identifiable through an IP address. Each host will contain its tcp port, shared secret for encryption,
authentication type for messages, server priority and time value. Properties specified with a particular tacacs host takes precedence over
global tacacs properties.

In addition, this feature also supports configuration for aaa authentication: an authentication method, which is ordered. Currently only local and tacacs+
are supported.
Failthrough mechanism can be enabled or disabled.


# 3 Design
## 3.1 Overview
Tacacs configuration is segregated with the help of server-group. /openconfig-system:system/aaa/server-groups/ supports list of server-groups.
Tacacs configuration is identified with the help of server-group by case sensitive name "TACACS".
Radius (which is covered in another HLD) configuration will be identified with the help of server-group by case sensitive name "RADIUS".

## 3.2 DB Changes
### 3.2.1 CONFIG DB
This feature will allow the user to make/show TACACS+ configuration changes to CONFIG DB

## 3.3 User Interface
### 3.3.1 Data Models
openconfig-system.yang is used by augmenting whereever applicable with openconfig-system-ext.yang.

Sonic version of the yang is as below:

module: sonic-system-aaa
    +--rw sonic-system-aaa
       +--rw AAA
          +--rw AAA_LIST* [type]
             +--rw type           enumeration
             +--rw login*         string
             +--rw failthrough?   boolean

module: sonic-system-tacacs
    +--rw sonic-system-tacacs
       +--rw TACPLUS_SERVER
       |  +--rw TACPLUS_SERVER_LIST* [ipaddress]
       |     +--rw ipaddress    inet:ip-address
       |     +--rw priority?    uint8
       |     +--rw tcp_port?    inet:port-number
       |     +--rw timeout?     uint16
       |     +--rw auth_type?   auth_type_enumeration
       |     +--rw passkey?     string
       +--rw TACPLUS
          +--rw TACPLUS_LIST* [type]
             +--rw type         enumeration
             +--rw auth_type?   auth_type_enumeration
             +--rw timeout?     uint16
             +--rw passkey?     string
             +--rw src_intf?    union


```
```

### 3.3.2 CLI

#### 3.3.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```
#### **AAA configuration**

##### Configure authentication methods and order
`aaa authentication login-method {local | tacacs+}`

The command allows the user to specify the authentication methods (local/tacacs+). Authentication will be attempted based on the order of the methods specified.

Examples:

```
sonic(config)# aaa authentication login-method local
sonic(config)# aaa authentication login-method local tacacs+
sonic(config)# aaa authentication login-method tacacs+
sonic(config)# aaa authentication login-method tacacs+ local

```

##### Set authentication method to default
```
sonic(config)# no aaa authentication login-method
```
Default is local.

##### Enable/disable failthrough

```
sonic(config)# aaa authentication failthrough
  enable|disable  failthrough status (enable/disable)

```

`[no] aaa authentication failthrough`

Default is disable.

#### **TACACS global configuration**
```
sonic(config)# tacacs-server
  auth-type  Configure global authentication type for TACACS
  key        Configure global shared secret for TACACS
  source-interface  Configure source interface to pick the source IP, used for the TACACS+ packets
  timeout    Configure global timeout for TACACS
sonic(config)# tacacs-server auth-type
pap    chap   mschap
sonic(config)# no tacacs-server auth-type
  <cr>

sonic(config)# tacacs-server key
  (Valid Chars: [0-9A-Za-z], Max Len: 32) shared secret

sonic(config)# no tacacs-server key
  <cr>

sonic(config)# tacacs-server source-interface
 Ethernet     Ethernet interface
 Loopback     Loopback interface
 Management   Management interface
 PortChannel  PortChannel interface
 Vlan         Vlan interface

sonic(config)# no tacacs-server source-interface
  <cr>

sonic(config)# tacacs-server timeout
  seconds  timeout (default: 5) (0..60)

sonic(config)# no tacacs-server timeout
  <cr>
Defaults to 0.

```

#### **TACACS server configuration**
##### Add TACACS+ server
`tacacs-server host <address> {port <1-65535> | timeout <0-60> | key <TEXT> | type <pap|chap|mschap> priority <1-65535>}`

```
sonic(config)# tacas-server host 1.1.1.1 key Pass
sonic(config)# tacas-server host 1.1.1.2 port 1234 timeout 5 key Pass

sonic(config)# no tacacs-server host
  A.B.C.D/A::B  server ip address

```

#### 3.3.2.2 Show Commands
##### Show AAA configurations
```
---------------------------------------------------------
AAA Authentication Information
---------------------------------------------------------
failthrough  : True
login-method : local, tacacs+

```
##### Show TACACS+ configurations
```
sonic# show tacacs-server global
---------------------------------------------------------
TACACS Global Configuration
---------------------------------------------------------
source-interface  : Ethernet8
timeout    : 4
auth-type  : mschap
key        : mykey
sonic#

sonic# show tacacs-server host
  A.B.C.D  IP address of the tacacs server
  |        Pipe through a command
  <cr>
sonic# show tacacs-server host 9.9.9.9
------------------------------------------------------------------------------------------------
HOST                AUTH-TYPE      KEY       PORT      PRIORITY  TIMEOUT
------------------------------------------------------------------------------------------------
9.9.9.9             pap            mykey     90        10        10
sonic# show tacacs-server host
------------------------------------------------------------------------------------------------
HOST                AUTH-TYPE      KEY       PORT      PRIORITY  TIMEOUT
------------------------------------------------------------------------------------------------
1.1.1.1             pap            mykey     10        10        10
1.3.5.7             pap            mykey2    20        20        20
9.9.9.9             pap            mykey     90        10        10

```

#### 3.3.2.3 Debug Commands
N/A
#### 3.3.2.4 IS-CLI Compliance
Yes

### 3.3.3 REST API Support
```
GET - Get existing TACACS+ configuration information from CONFIG DB.
POST - Add a new TACACS+  configuration into CONFIG DB.
PATCH - Update existing TACACS+  configuraiton information in CONFIG DB.
PUT - Add a list of TACACS+  configurations into CONFIG DB.
DELETE - Delete a existing TACACS+  configuration from CONFIG DB. This will cause some configurations to return to default value.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug


# 7 Warm Boot Support


# 8 Scalability


# 9 Unit Test
The unit-test for this feature will include:
#### Configuration via CLI
##### AAA
1. Configure one authentication method
2. Change the configured authentication method
3. Configure multiple authentication methods
4. Change the order of the authentication methods


##### TACACS
1. Configure one tacacs host
2. Configure another tacacs host with non-default parameters
3. Update parameters for a host already configured
4. Delete one tacacs host
5. Configure the same tacacs host again


#### Configuration via gNMI

Same test as CLI configuration test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information
