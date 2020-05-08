# Feature Name
Domain Name System (DNS) support

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
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 05/05 |   Venkatesan Mahalingam         | Initial version                   |


# About this Manual

This document introduces the support of DNS in SONiC.

# Scope

This document covers the following,
1) Click commands to configure DNS server & Source IP
2) Click command to show DNS hosts
3) New tables in config DB to handle DNS configs
4) DNS table configuration and show based on OpenConfig YANG model
5) KLISH commands to configure DNS server & Source IP
6) KLISH commands to show DNS hosts
7) Backend support to add DNS configs in "/etc/resolv.conf" file & iptable rules to change the source-IP of the DNS query packets
8) Unit Testcases

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          DNS             |  Domain Name System             |



# 1 Feature Overview

DNS stands for Domain Name System. It is used to translate human readable domain names into machine readable IP addresses.

With this feature, users will be able to configure DNS servers and source IP using SONiC Click commands and north bound interface (KLISH/REST/gNMI) provided by management framework module using OpenConfig models.

Also, backend support to handle new config DB table events to populate nameservers in "/etc/resolv.conf" and add iptable rules to change the source IP of the DNS query that is being sent to the DNS server.

## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities

#### 1.1.1.1 add/delete DNS server      
This requirement is to add/delete DNS name server information in the Redis ConfigDB (DNS_SERVER) using Click and mgmt-framework.
The DNS server can be IPv4/IPv6 ipaddress and multiple DNS name servers can be configured.

#### 1.1.1.2 add/delete DNS source IP
This requirement is to add/delete the global DNS source IP information in the Redis ConfigDB (DNS) using Click and mgmt-framework.

Only one DNS source IP can be configured in the global DNS table. A new source IP will override the existing DNS source IP.   

#### 1.1.1.4 add/delete VRF name
No special handling is required in "/etc/resolv.conf" file to work on the management VRF (for this release).

#### 1.1.1.5 Get DNS hosts
This displays the output of the DNS source IP and nameservers.

### 1.1.2 Backend mechanisms to support configuration and get

#### 1.1.2.1 add/delete DNS server
The creates or deletes a DNS server entry in the Redis ConfigDB.

```
  "DNS_SERVER|10.11.0.1": {
    "type": "hash",
    "value": {
      "NULL": "NULL"
    }
  },
  "DNS_SERVER|2001:aa:aa::a": {
    "type": "hash",
    "value": {
      "NULL": "NULL"
    }
  },
  }
```

A change in the DNS_SERVER entry triggers hostcfgd to start the DNS configuration script, which in turn writes each DNS server to the resolv.conf and then restart the dns-config service.   

#### 1.1.2.2 add/delete DNS source IP

This creates or deletes a global DNS source IP entry in the Redis ConfigDB.

```
  "DNS|global": {
    "type": "hash",
    "value": {
      "src_ip": "1.1.1.1"
    }
  }
```

A change in this entry triggers hostcfgd to add iptables SNAT rule incase of IPv4 address and ip6tables SNAT rule in IPv6 source address.

Only one global DNS source IP is allowed.

#### 1.1.2.4 get DNS hosts

Transformer function issues get on DNS tables, parses the response and maps the outputs to the OpenConfig DNS states incase of mgmt-framework interface.

Incase of Click commands, show commands directly fetches the information from DNS & DNS_SERVER tables and display to the user.

### 1.1.3 Functional Requirements

Provide management framework support to    
- configure DNS name server   
- configure DNS source IP   

### 1.1.4 Configuration and Management Requirements
- Click configuration and show commands
- CLI style configuration and show commands   
- REST API support   
- gNMI Support   

Details described in Section 3.

### 1.1.6 Scalability Requirements

### 1.1.7 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach
- Implement Click commands using SONiC utilities.
- Implement DNS support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
The front end code change will be done in management-framework container including:   
- XML file for the CLI   
- Python script to handle CLI request (actioner)   
- Jinja template to render CLI output (renderer)   
- OpenConfig YANG model for DNS openconfig-system.yang   
- SONiC DNS model for DNS based on Redis DB schema   
- transformer functions to    
   * convert OpenConfig YANG model to SONiC YANG model for DNS related configurations   

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure Management VRF via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide CLI, gNMI and REST supports for Management VRF handling

## 2.3 Backend change to support new configurations
Provide change in hostcfgd, dns config script, dns service script.

# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for DNS.

## 3.2 DB Changes

### 3.2.1 CONFIG DB
```
; DNS configuration attributes global to the system. Only one instance of the table exists in the system.
; Key
global_key           = “global”  ;  TACACS+ global configuration
; Attributes
src_ip               = IPAddress  ;  source IP address for the outgoing DNS packets

```

```
; DNS name server configuration in the system.
; Key
server_key           = IPAddress  ;  DNS server’s address
; Attributes
No attributes are introduced as part of this design.
```

### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models

YANG models needed for DNS handling in the management framework:
1. **openconfig-system.yang**  

2. **sonic-system-dns.yang**

Supported yang objects and attributes:
```diff

module: openconfig-system
      +--rw system

      +--rw dns
           |  +--rw config
           |  |  +--rw search*                      oc-inet:domain-name
+          |  |  +--rw oc-sys-ext:source-address?   inet:ip-address
           |  +--ro state
           |  |  +--ro search*                      oc-inet:domain-name
+          |  |  +--ro oc-sys-ext:source-address?   inet:ip-address
           |  +--rw servers
           |  |  +--rw server* [address]
           |  |     +--rw address    -> ../config/address
           |  |     +--rw config
+          |  |     |  +--rw address?   oc-inet:ip-address
           |  |     |  +--rw port?      oc-inet:port-number
           |  |     +--ro state
+          |  |        +--ro address?   oc-inet:ip-address
           |  |        +--ro port?      oc-inet:port-number

Above fields with '+' are supported as part of DNS feature.

module: sonic-system-dns
  +--rw sonic-system-dns
     +--rw DNS_SERVER
     |  +--rw DNS_SERVER_LIST* [ipaddress]
     |     +--rw ipaddress    inet:ip-address
     +--rw DNS
        +--rw DNS_LIST* [type]
           +--rw type      enumeration ('global')
           +--rw src_ip?   inet:ip-address

```

### 3.6.2 CLI


#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

##### 3.6.2.1.1 Configure DNS server & source IP
```
sonic(config)# ip name-server
  source-ip     Configure source IP to reach the name server
  A.B.C.D/A::B  Domain name server

sonic(config)# ip name-server 10.11.0.1

sonic(config)# ip name-server 2001:aa:aa::a

sonic(config)# ip name-server source-ip 1.1.1.1

```

##### 3.6.2.1.2 Delete DNS server & source IP

```
sonic(config)# no ip name-server
  source-ip     Configure source IP to reach the name server
  A.B.C.D/A::B  Domain name server

sonic(config)# no ip name-server 10.11.0.1

sonic(config)# no ip name-server 2001:aa:aa::a

sonic(config)# no ip name-server source-ip 1.1.1.1

```
#### 3.6.2.2 Show dns hosts

```
sonic# show hosts
Default domain is not configured
Name/address lookup uses domain service
Source IP  : 1.1.1.1
Name servers are: 10.11.0.1 2001:aa:aa::a
sonic#
```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing DNS configuration information from CONFIG DB.
      Get DNS peer states
POST - Add DNS configuration into CONFIG DB.
PATCH - Update existing DNS Configuration information in CONFIG DB.
DELETE - Delete a existing DNS configuration from CONFIG DB.
```
### 3.6.4 Click command support
#### 3.6.4.1 Configuration support
Below click commands are supported for DNS configurations
root@sonic:~# config dns
Usage: config dns [OPTIONS] COMMAND [ARGS]...

  DNS command line

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  add       Specify a DNS name server
  delete    Delete a DNS name server
  sourceip  Specify DNS server global source ip...
```
root@sonic:~# ping www.yahoo.com
ping: www.yahoo.com: Temporary failure in name resolution

root@sonic:~# config dns add 10.11.0.1

root@sonic:~# ping www.yahoo.com
PING new-fp-shed.wg1.b.yahoo.com (98.137.246.8) 56(84) bytes of data.
64 bytes from media-router-fp2.prod1.media.vip.gq1.yahoo.com (98.137.246.8): icmp_seq=1 ttl=52 time=24.2 ms
64 bytes from media-router-fp2.prod1.media.vip.gq1.yahoo.com (98.137.246.8): icmp_seq=2 ttl=52 time=23.9 ms
64 bytes from media-router-fp2.prod1.media.vip.gq1.yahoo.com (98.137.246.8): icmp_seq=3 ttl=52 time=23.9 ms
^C
--- new-fp-shed.wg1.b.yahoo.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2001ms
rtt min/avg/max/mdev = 23.910/24.033/24.262/0.241 ms
root@sonic:~#
```
#### 3.6.4.2 Show support
Below Click command is used to dump the DNS configurations
```
root@sonic:~# show hosts
DNS global src_ip 1.1.1.1

Name servers are: 10.11.0.1
root@sonic:~#
```
# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### Configuration via CLI

| Test Name | Test Description |
| :-------- | :----- |
| Configure DNS server | Verify DNS servers are present in the DNS_SERVER table (configDB) and the same is reflected in the resolv.conf file |
| Delete DNS server | Verify DNS servers are not present in the DNS_SERVER table (configDB) and the same is reflected in the resolv.conf file  |
| Configure DNS source IP| Verify DNS source IP is present in the DNS table (configDB) and DNS query packets are transmitted with the configured source IP |
| Delete DNS source IP| Verify DNS source IP is not present in the DNS table (configDB) and DNS query packets are not transmitted with the configured source IP |
| Configure mgmt VRF | verify that DNS query packets are transmitted based on nameservers present in resolv.conf file |
| show hosts | Verify source IP and nameservers are displayed correctly |

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request.
Additional tests will be done to set DNS configuration at different levels of Yang models.

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done to get DNS configuration and DNS states at different levels of Yang models.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request
Additional tests will be done to set DNS configuration at different levels of Yang models.


#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done to get DNS configuration and DNS states at different levels of Yang models.


# 10 Internal Design Information
