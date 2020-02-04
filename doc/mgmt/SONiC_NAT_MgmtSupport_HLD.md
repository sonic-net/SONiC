# NAT
Management Support for NAT Feature

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
| 0.1 | 10/30/2019  |   Ravi Vasantham, Arthi Sivanantham      | Initial version                   |

# About this Manual

This document provides north bound interface details for NAT feature.

# Scope

This document covers the management interfaces supported for NAT feature and Unit test cases. It does not include the protocol design or protocol implementation details.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| NAT                      | Network Address Translation  |

# 1 Feature Overview

Provide CLI, GNMI and REST management framework capabilities for CONFIG and GET support for NAT feature.


## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide CLI, REST and gNMI support for configuring and displaying NAT attributes.


### 1.1.2 Configuration and Management Requirements

Supported Commands via:
- CLI style commands
- REST API support
- gNMI Support

### 1.1.3 Scalability Requirements
N/A

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach
Will be enhancing the management framework backend and transformer methods to add support for NAT configuration and display.


### 1.2.2 Container
All code changes will be done in management-framework container.

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
N/A
## 2.2 Functional Description
N/A


# 3 Design
## 3.1 Overview
N/A
## 3.2 DB Changes
No changes to existing DBs and no new DB being added.
### 3.2.1 CONFIG DB
### 3.2.2 APP DB

### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
N/A
### 3.3.1 Orchestration Agent
N/A
### 3.3.2 Other Process
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models

IETF NAT Yang (RFC 8512) is used for the north bound management interface support.
https://tools.ietf.org/html/rfc8512#page-24
https://github.com/project-arlo/sonic-mgmt-framework/blob/nat-impl/models/yang/ietf-nat.yang
https://github.com/project-arlo/sonic-mgmt-framework/blob/nat-impl/models/yang/ietf-nat-ext.yang

```
Supported yang attributes:
module: ietf-nat
    +--rw nat
       +--rw instances
          +--rw instance* [id]
             +--rw id                              uint32
             +--rw name?                           string
             +--rw enable?                         boolean
             +--rw mapping-table
             |  +--rw mapping-entry* [index]
             |     +--rw index                        uint32
             |     +--rw type?                        enumeration
             |     +--rw transport-protocol?          uint8
             |     +--rw internal-src-address?        inet:ip-prefix
             |     +--rw internal-src-port
             |     |  +--rw start-port-number?   inet:port-number
             |     |  +--rw end-port-number?     inet:port-number
             |     +--rw external-src-address?        inet:ip-prefix
             |     +--rw external-src-port
             |     |  +--rw start-port-number?   inet:port-number
             |     |  +--rw end-port-number?     inet:port-number
             |     +--rw internal-dst-address?        inet:ip-prefix
             |     +--rw internal-dst-port
             |     |  +--rw start-port-number?   inet:port-number
             |     |  +--rw end-port-number?     inet:port-number
             |     +--rw external-dst-address?        inet:ip-prefix
             |     +--rw external-dst-port
             |     |  +--rw start-port-number?   inet:port-number
             |     |  +--rw end-port-number?     inet:port-number
             |     +--rw lifetime?                    uint32
             |     +--rw ietf-nat-ext:twice_nat_id?   uint16
             |     +--ro ietf-nat-ext:statistics
             |        +--ro ietf-nat-ext:dnat-translations-pkts?    yang:zero-based-counter64
             |        +--ro ietf-nat-ext:dnat-translations-bytes?   yang:zero-based-counter64
             |        +--ro ietf-nat-ext:snat-translations-pkts?    yang:zero-based-counter64
             |        +--ro ietf-nat-ext:snat-translations-bytes?   yang:zero-based-counter64
             +--rw ietf-nat-ext:nat_timeout?       uint32
             +--rw ietf-nat-ext:nat_tcp_timeout?   uint32
             +--rw ietf-nat-ext:nat_udp_timeout?   uint16
             +--rw ietf-nat-ext:zone-counters
             |  +--rw ietf-nat-ext:zone-counter-entry* [zone-id]
             |     +--rw ietf-nat-ext:zone-id                        uint8
             |     +--rw ietf-nat-ext:nat-dnat-discards?             yang:zero-based-counter64
             |     +--rw ietf-nat-ext:nat-snat-discards?             yang:zero-based-counter64
             |     +--rw ietf-nat-ext:nat-dnat-translation-needed?   yang:zero-based-counter64
             |     +--rw ietf-nat-ext:nat-snat-translation-needed?   yang:zero-based-counter64
             |     +--rw ietf-nat-ext:nat-dnat-translations?         yang:zero-based-counter64
             |     +--rw ietf-nat-ext:nat-snat-translations?         yang:zero-based-counter64
             +--rw ietf-nat-ext:nat-pool
             |  +--rw ietf-nat-ext:nat-pool-entry* [pool-name]
             |     +--rw ietf-nat-ext:pool-name           string
             |     +--rw (ietf-nat-ext:nat-ip)?
             |     |  +--:(ietf-nat-ext:ip-address)
             |     |  |  +--rw ietf-nat-ext:IP-ADDRESS?         inet:ipv4-address
             |     |  +--:(ietf-nat-ext:ip-address-range)
             |     |     +--rw ietf-nat-ext:IP-ADDRESS-RANGE?   string
             |     +--rw ietf-nat-ext:nat-port?           string
             +--rw ietf-nat-ext:nat-bindings
                +--rw ietf-nat-ext:nat-binding-entry* [binding-name]
                   +--rw ietf-nat-ext:binding-name    string
                   +--rw ietf-nat-ext:nat-pool        string
                   +--rw ietf-nat-ext:access-list?    string
                   +--rw ietf-nat-ext:nat-type?       enumeration
                   +--rw ietf-nat-ext:twice-nat-id?   uint16

```

SONiC NAT Yang will be used for Config Validation purposes and has RPC for clear commands.

https://github.com/project-arlo/sonic-mgmt-framework/blob/nat-impl/models/yang/sonic/sonic-nat.yang

### 3.6.2 CLI
SONiC NAT Click CLI based Configuration and Show Commands will be supported by management framework.
Refer Section 3.8 from https://github.com/Azure/SONiC/blob/dc5d3a894618bcb07a3c5d2dd488caf3beb7479a/doc/nat/nat_design_spec.md

#### 3.6.2.1 Configuration Commands

###### Add static NAT entry

`static basic <global-ip> <local-ip> [snat | dnat] [ twice_nat_id <value> ]`

```
sonic# config t
sonic(config)# nat
sonic(config-nat)# static basic 20.0.0.2 65.55.45.8 snat twice_nat_id 1
```
###### Remove static NAT entry

`
sonic# config t
sonic(config)# nat
sonic(config-nat) # no static basic {global-ip} {local-ip}`

```
sonic# config t
sonic(config)# nat
sonic(config-nat)# no static basic 20.0.0.2 65.55.45.8
```

###### Add static NAPT entry

`static {tcp | udp} <global-ip> <global-port> <local-ip> <local-port> [snat | dnat ] [ twice_nat_id <value> ]`

```
sonic# config t
sonic(config)# nat
sonic(config-nat)# static tcp 65.55.45.7 4000 20.0.0.1 4500 dnat twice_nat_id 1
```

###### Remove static NAPT entry

`no static {tcp | udp} <global-ip> <global-port> <local-ip> <local-port>`

```
sonic# config t
sonic(config)# nat
sonic(config-nat)# no static tcp 65.55.45.7 4000 20.0.0.1 4500
```

###### Remove all static NAT/NAPT configuration

`no static all`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) # no static all
```

###### Create NAT pool

`pool <pool-name> <global-ip-range> [ <global-port-range> ] `

```
sonic# config t
sonic(config)# nat
sonic(config-nat) pool Pool1 65.55.45.10-65.55.45.15 1024-65535
```

###### Remove NAT pool

`no pool <pool-name>`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) no pool Pool1
```

###### Remove all NAT pool configuration

`no pools`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) no pools
```

###### Create binding between an ACL and a NAT pool

`binding <binding-name> <pool-name> <acl-name> [ snat | dnat ] [ twice_nat_id <value> ]`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) binding Bind1 Pool1 Acl1 snat twice_nat_id 1
```

###### Remove binding between an ACL and a NAT pool

`no binding <binding-name>`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) no binding Bind1
```

###### Remove all NAT binding configuration

`no bindings`

```
sonic# config t
sonic(config)# nat
sonic(config-nat) no bindings
```

###### Configure NAT zone value on an interface

`nat-zone <zone-value>`

```
sonic# config t
sonic (config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# nat-zone 1
```

###### Remove NAT configuration on interface

`no nat-zone`

```
sonic# config t
sonic (config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# no nat-zone
```

###### Remove NAT configuration on all L3 interfaces

`no nat interfaces`

```
sonic# config t
sonic (config)# no nat interfaces
```

###### Configure NAT entry aging timeout in seconds

`timeout <secs>`

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# timeout 1200
```

###### Reset NAT entry aging timeout to default value

`no timeout`

Default value: 600 secs

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# no timeout
```

###### Enable or disable NAT feature

`nat { enable | disable } `

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# enable
```

###### Configure UDP NAT entry aging timeout in seconds

`udp-timeout <secs>`

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# udp-timeout 600
```

###### Reset UDP NAT entry aging timeout to default value

`no udp-timeout`

Default value: 300 secs

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# no udp-timeout
```

######  Configure TCP NAT entry aging timeout in seconds

`tcp-timeout <secs>`

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# tcp-timeout 86460
```

###### Reset TCP NAT entry aging timeout to default value

`no tcp-timeout`

Default Value: 86400 secs

```
sonic# config t
sonic (config)# nat
sonic (config-nat)# no tcp-timeout
```

#### 3.6.2.2 Clear Commands

###### Clear dynamic NAT translations

`clear nat translations`

```
sonic# clear nat translations

```

###### Clear NAT statistics

`clear nat statistics`

```
sonic# clear nat statistics

```


#### 3.6.2.3 Show Commands

###### Show NAT translations table

`show nat translations`

```
sonic# show nat translations

Protocol Source           Destination       Translated Source  Translated Destination
-------- ---------        --------------    -----------------  ----------------------
all      10.0.0.1         ---               65.55.42.2         ---
all      ---              65.55.42.2        ---                10.0.0.1
all      10.0.0.2         ---               65.55.42.3         ---
all      ---              65.55.42.3        ---                10.0.0.2
tcp      20.0.0.1:4500    ---               65.55.42.1:2000    ---
tcp      ---              65.55.42.1:2000   ---                20.0.0.1:4500
udp      20.0.0.1:4000    ---               65.55.42.1:1030    ---
udp      ---              65.55.42.1:1030   ---                20.0.0.1:4000
tcp      20.0.0.1:6000    ---               65.55.42.1:1024    ---
tcp      ---              65.55.42.1:1024   ---                20.0.0.1:6000
tcp      20.0.0.1:5000    65.55.42.1:2000   65.55.42.1:1025    20.0.0.1:4500
tcp      20.0.0.1:4500    65.55.42.1:1025   65.55.42.1:2000    20.0.0.1:5000

```

###### Display NAT translation statistics

`show nat statistics`

```
sonic# show nat statistics

Protocol Source           Destination          Packets          Bytes
-------- ---------        --------------       -------------    -------------
all      10.0.0.1         ---                            802          1009280
all      10.0.0.2         ---                             23             5590
tcp      20.0.0.1:4500    ---                            110            12460
udp      20.0.0.1:4000    ---                           1156           789028
tcp      20.0.0.1:6000    ---                             30            34800
tcp      20.0.0.1:5000    65.55.42.1:2000                128           110204
tcp      20.0.0.1:5500    65.55.42.1:2000                  8             3806

```

###### Display Static NAT/NAPT configuration

`show nat config static`

```
sonic# show nat config static

Nat Type  IP Protocol Global IP      Global L4 Port  Local IP       Local L4 Port  Twice-Nat Id
--------  ----------- ------------   --------------  -------------  -------------  ------------
dnat      all         65.55.45.5     ---             10.0.0.1       ---            ---
dnat      all         65.55.45.6     ---             10.0.0.2       ---            ---
dnat      tcp         65.55.45.7     2000            20.0.0.1       4500           1
snat      tcp         20.0.0.2       4000            65.55.45.8     1030           1

```

###### Display NAT pools configuration

`show nat config pool`

```
sonic# show nat config pool

Pool Name      Global IP Range             Global L4 Port Range
------------   -------------------------   --------------------
Pool1          65.55.45.5                  1024-65535
Pool2          65.55.45.6-65.55.45.8       ---
Pool3          65.55.45.10-65.55.45.15     500-1000

```

###### Display NAT bindings configuration

`show nat config bindings`

```
sonic# show nat config bindings

Binding Name   Pool Name      Access-List    Nat Type  Twice-Nat Id
------------   ------------   ------------   --------  ------------
Bind1          Pool1          ---            snat      ---
Bind2          Pool2          1              snat      1
Bind3          Pool3          2              snat      --

```

###### Display global NAT configuration

`show nat config globalvalues	`

```
sonic# show nat config globalvalues

Admin Mode     : enabled
Global Timeout : 600 secs
TCP Timeout    : 86400 secs
UDP Timeout    : 300 secs

```

###### Display L3 interface zone values

`show nat config zones`

```
sonic# show nat config zones
Port                Zone
-------------------------------------------------
Ethernet0           1
Vlan2               3
Loopback1           0
PortChannel1        2
sonic#

```


###### Display NAT entries count

`show nat translations count`

```
sonic# show nat translations count

Static NAT Entries        ................. 4
Static NAPT Entries       ................. 2
Dynamic NAT Entries       ................. 0
Dynamic NAPT Entries      ................. 4
Static Twice NAT Entries  ................. 0
Static Twice NAPT Entries ................. 4
Dynamic Twice NAT Entries  ................ 0
Dynamic Twice NAPT Entries ................ 0
Total SNAT/SNAPT Entries   ................ 9
Total DNAT/DNAPT Entries   ................ 9
Total Entries              ................ 14

```

###### Display all NAT configuration

`show nat config`

```
sonic# show nat config
Global Values

Admin Mode     : enabled
Global Timeout : 650 secs
TCP Timeout    : 86450 secs
UDP Timeout    : 325 secs

Static Entries

----------------------------------------------------------------------------------------------------------------------------
Nat Type       IP Protocol         Global IP                     Global L4 Port      Local IP                      Local L4 Port       Twice-Nat Id
----------------------------------------------------------------------------------------------------------------------------
snat           all                 100.100.100.100               ----                15.15.15.15                   ----                5
dnat           all                 138.76.28.1                   ----                12.12.12.14                   ----                ----
dnat           all                 200.200.200.5                 ----                17.17.17.17                   ----                5
snat           tcp                 100.100.101.101               251                 15.15.16.16                   1201                5
dnat           tcp                 138.76.29.2                   250                 12.12.15.15                   1200                ----
dnat           tcp                 200.200.201.6                 276                 17.17.18.18                   1251                5

Pool Entries

Pool Name           Global IP Range               Global L4 Port Range
----------------------------------------------------------------------------------------------------------------------------
Pool1               19.19.19.19                   ----
Pool2               20.0.0.7                      1024-65535
--more--
Pool3               65.55.45.10-65.55.45.15       500-1000
Pool4               65.55.43.5-65.55.43.15        300-1024

NAT Bindings

Binding Name        Pool Name                     Access-List         Nat Type       Twice-Nat Id
----------------------------------------------------------------------------------------------------------------------------
Bind1               Pool1                         10_ACL_IPV4         ----           ----
Bind2               Pool2                         12_ACL_IPV4         snat           25
Bind3               Pool3                         15_ACL_IPV4         dnat           25
Bind4               Pool4                         ----                ----           ----

NAT Zones

Port                Zone
-------------------------------------------------
Ethernet0           1
Vlan2               3
Loopback1           0
PortChannel1        2
sonic#

```


#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
N/A

**Deviations from IS-CLI:**

### 3.6.3 REST API Support

# 4 Flow Diagrams
N/A

# 5 Error Handling


# 6 Serviceability and Debug


# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
The following lists the unit test cases added for the north bound interfaces for NAT
1. Configure (Add/Remove) NAT entries and verify using it's appropriate show command.
2. Configure (Add/Remove) NAPT entries and verify the same.
3. Remove all static configurations and verify the same.
4. Create/Remove NAT pools and verify the same.
5. Create/Remove bindings between ACL and NAT pools and verify the same.
6. Configure/Remove NAT Zone value on an interface and verify the same.
7. Configure/Remove Basic NAT entry aging timeout in seconds and verify the same.
8. Enable/Disable NAT feature and verify the same.
9. Configure/Reset UDP NAT entry aging timeout in seconds and verify the same.
10. Configure/Reset TCP NAT entry aging timeout in seconds and verify the same.
11. Clear NAT dynamic translations and verify the same in DB.
12. Clear NAT statistics and verify the same in DB.


# 10 Internal Design Information
N/A
