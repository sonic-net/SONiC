# SmartSwitch ENI Based Forwarding

## Table of Content ##

- [SmartSwitch ENI Based Forwarding](#smartswitch-eni-based-forwarding)
  - [Table of Content](#table-of-content)
  - [Revision](#revision)
  - [Scope](#scope)
  - [Definitions/Abbreviations](#definitionsabbreviations)
  - [Overview](#overview)
    - [Packet Flow](#packet-flow)
  - [Requirements](#requirements)
    - [Phase 1](#phase-1)
    - [Phase 2](#phase-2)
  - [Architecture Design](#architecture-design)
    - [ACL Table Configuration](#acl-table-configuration)
    - [ACL Rules](#acl-rules)
    - [Handling path loops after Tunnel decap](#handling-path-loops-after-tunnel-decap)
    - [Nexthop resolution](#nexthop-resolution)
    - [Dash ENI Forward Orch](#dash-eni-forward-orch)
      - [Schema Change in ACL_RULE](#schema-change-in-acl-rule)
  - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
  - [Restrictions/Limitations](#restrictionslimitations)
  - [Testing Requirements/Design](#testing-requirementsdesign)
    - [System Test cases](#system-test-cases)
  - [Open/Action items - if any](#openaction-items---if-any)

## Revision ##

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 10/05/2024 | Vivek Reddy Karri | Initial version |

## Scope ##

This document provides a high-level design for Smart Switch ENI based Packet Forwarding using ACL rules

## Definitions/Abbreviations ##

| Term | Meaning                                                 |
| ---- | ------------------------------------------------------- |
| NPU  | Network Processing Unit                                 |
| DPU  | Data Processing Unit                                    |
| VIP  | Virtual IP                                    |
| PA  | Physical Address                                   |
| NH  | Next Hop                                   |
| NHG  | Next Hop Group                                |
| HA  | High Availability                                |

## Overview ##

There are two possible NPU-DPU Traffic forwarding models.

1) VIP based model
    * Controller allocates VIP per DPU, which is advertised and visible from anywhere in the cloud infrastructure.
    * The host has the DPU VIP as the gateway address for its traffic.
    * Simple, decouples a DPU from switch.
    * Costly, since you need VIP per DPU.

2) ENI Based Forwarding
    * The host has the switch VIP as the gateway address for its traffic.
    * Cheaper, since only VIP per switch is needed (or even per a row of switches). ENI placement can be directed even across smart switches.

ENI Based Forwarding is the preferred approach because of cost constraints. 

Packet Forwarding from NPU to local and remote DPU's are clearly explained in the HA HLD https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/high-availability/smart-switch-ha-hld.md#42-data-path-ha

### Packet Flow ###

**Case 1: Packet lands directly on NPU which has the currrent Active ENI**

![Active ENI case](./images/active_eni.png)

**Case 2: Packet lands NPU which has the currrent Standby ENI**

![Active Standby ENI case](./images/active_standby_eni.png)


## Requirements ##

ENI based forwarding requires the switch to understand the relationship between the packet and ENI, and ENI and DPU.

* Each DPU is represented as a PA (public address). Unlike VIP, PA does't have to be visible from the entire cloud infrastructure
* Each ENI belongs to a certain DPU (local or remote)
* Each packet can be identified as belonging to that switch using VIP and VNI
* Forwarding can be to local DPU PA or remote DPU PA over L3 VxLAN
* Scale: 
    - One VIP per HA pair: [# of DPUs] * [# of ENIs per DPU] * 2 (inbound and outbound) * 2 (One with/without Tunnel Termination)

### Phase 1 ###

- Only HaMgrd will make decision on where to route the packet and write to ENI_DASH_TUNNEL_TABLE table
- Orchagent will only process the primary endpoint and translate the requirement into ACL Rules
- Orchagent should also program ACL Rules with Tunnel termination entries
- No BFD sessions are created to local DPU or the remote DPU.

### Phase 2 ###

- BFD sessions are created to local DPU or the remote DPU for faster reactivity to card level failures
- Orchagent will switch between primary and secondary endpoint based on BFD status

## Architecture Design ##

### ACL Table Configuration ### 
```
{
    "ACL_TABLE_TYPE": {
        "ENI_REDIRECT": {
            "MATCHES": [
                "TUNNEL_VNI",
                "DST_IP",
                "DST_IPV6",
                "INNER_SRC_MAC",
                "INNER_DST_MAC",
                "TUNNEL_TERM"
            ],
            "ACTIONS": [
                "REDIRECT_ACTION",
            ],
            "BIND_POINTS": [
                "PORT"
            ]
        }
    },
    "ACL_TABLE": {
        "ENI": {
            "STAGE": "INGRESS",
            "TYPE": "ENI_REDIRECT",
            "PORTS": [
                "<Ingress front panel ports>"
            ]
        }
    }
}
```
### ACL Rules ### 

Assume the following ENI attributes
```
MAC: aa:bb:cc:dd:ee:ff
TUNNEL_VNI: 4000
VIP: 1.1.1.1/32
```

**ACL Rule for outbound traffic**

```
{  
    "ACL_RULE": {
        "ENI:aa:bb:cc:ff:fe:dd:ee:ff:OUT0": {
            "PRIORITY": "999",
            "TUNNEL_VNI": "4000",
            "DST_IP": "1.1.1.1/32",
            "INNER_SRC_MAC": "aa:bb:cc:dd:ee:ff"
            "REDIRECT": "<local/remote nexthop oid>"
        }
    }
}
```

**ACL Rule for inbound traffic**

```
{  
    "ACL_RULE": {
        "ENI:aa:bb:cc:ff:fe:dd:ee:ff:IN0": {
            "PRIORITY": "999",
            "TUNNEL_VNI": "4000",
            "DST_IP": "1.1.1.1/32",
            "INNER_DST_MAC": "aa:bb:cc:dd:ee:ff"
            "REDIRECT": "<local/remote nexthop oid>"
        }
    }
}
```

### Handling path loops after Tunnel decap ### 

During HA failover, the HA pair will end up in a transitional state that makes it ambiguous to the switch if it is active or backup.

When the HA failover happens, the used-to-be active becomes standby, but the used-to-be standby is still unchanged.

This state, although brief in time, may lead to congestion, and packet drops on a switch.

![Tunnel Termination Problem](./images/tunn_term_problem.png)

To solve this, ACL rules with high priority are added and the redirect should always be to local nexthop

![Tunnel Termination Solution](./images/tunn_term_solution.png)

**ACL Rule for outbound traffic with Tunnel Termination**

```
{  
    "ACL_RULE": {
        "ENI:aa:bb:cc:ff:fe:dd:ee:ff:OUT1": {
            "PRIORITY": "9999",
            "TUNNEL_VNI": "4000",
            "DST_IP": "1.1.1.1/32",
            "INNER_SRC_MAC": "aa:bb:cc:dd:ee:ff",
            "TUNN_TERM": "true",
            "REDIRECT": "<local nexthop oid>"
        }
    }
}
```

**ACL Rule for inbound traffic with Tunnel Termination**

```
{
    "ACL_RULE": {
        "ENI:aa:bb:cc:ff:fe:dd:ee:ff:IN1": {
            "PRIORITY": "9999",
            "TUNNEL_VNI": "4000",
            "DST_IP": "1.1.1.1/32",
            "INNER_DST_MAC": "aa:bb:cc:dd:ee:ff",
            "TUNN_TERM": "true",
            "REDIRECT": "<local nexthop oid>"
        }
    }
}
```

### Nexthop resolution ###

Nexthop can be to a local DPU or a remote DPU. Orchagent must figure out if the endpoint is either local or remote and handle it accordingly

### Dash ENI Forward Orch ### 

A new orchagent DashEniFwdOrch is added which runs on NPU to translate the requirements into ACL Rules. 

DashEniFwdOrch should infer the type of endpoint (local or remote) by parsing the DPU/vDPU table and saving the local DPU PA's in a set.

```mermaid
flowchart LR
    ENI_TABLE[ENI_DASH_TUNNEL_TABLE]

    HaMgrD --> ENI_TABLE
    ENI_TABLE --> DashEniFwdOrch

    DashEniFwdOrch --> Ques1{Remote Endpoint}
    DashEniFwdOrch --> |Observe| RouteOrch

    Ques1 --> CREATE_TUNNEL_NH
    CREATE_TUNNEL_NH --> |oid| DashEniFwdOrch
    RouteOrch --> |Notify NH for Local Endpoint| DashEniFwdOrch
    DashEniFwdOrch --> AclOrch
    DPU/vDPU --> DashEniFwdOrch
```

#### Schema Change in ACL_RULE ####

Current Schema for REDIRECT field in ACL_RULE_TABLE

```
    key: ACL_RULE_TABLE:table_name:rule_name

    redirect_action = 1*255CHAR                ; redirect parameter
                                               ; This parameter defines a destination for redirected packets
                                               ; it could be:
                                               : name of physical port.          Example: "Ethernet10"
                                               : name of LAG port                Example: "PortChannel5"
                                               : next-hop ip address (in global) Example: "10.0.0.1"
                                               : next-hop ip address and vrf     Example: "10.0.0.2@Vrf2"
                                               : next-hop ip address and ifname  Example: "10.0.0.3@Ethernet1"
                                               : next-hop group set of next-hop  Example: "10.0.0.1,10.0.0.3@Ethernet1"
```

This is enhanced to accept an object oid. AclOrch will verify if the object is of type SAI_OBJECT_TYPE_NEXT_HOP and only then permit the rule

```
   redirect_action = 1*255CHAR                  : oid of type SAI_OBJECT_NEXT_HOP Example: oid:0x400000000064d
```

## Warmboot and Fastboot Design Impact ##

No impact here

## Restrictions/Limitations ##

## Testing Requirements/Design ##

- Migrate existing Private Link tests to use ENI Forwarding Approach. Until HaMgrd is available, test should write to the ENI_DASH_TUNNEL_TABLE
- Add individual test cases which verify forwarding to remote endpoint and also Tunnel Termination. This should not require HA availability
- HA test cases should work by just writing the expected configuration to ENI_DASH_TUNNEL_TABLE

## Open/Action items - if any ##

- Will there be a packet coming to T1 which doesn't host its ENI? Theoretically possible if all the T1's in a cluster share the same VIP
- Will the endpoint for local DPU is PA of the interface address of the DPU
- ENI_DASH_TUNNEL_TABLE schema
