# ICMP Hardware Offload and FRR Protection Switching
ICMP Hardware Offload and FRR Protection Switching are new features aimed at improving link state failure detection and switchover time in Dual ToR architecture.

## Revision
| Rev |     Date    |         Author        |          Change Description      |
|:---:|:-----------:|:---------------------:|:--------------------------------:|
| 1.0 | 03/27/2025  | Manas Kumar Mandal    | Initial Version                  |

## Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| FRR | Fast Re-Route - protection group feature |
| GUID | Global Unique Identifier - ID to distinguish between different ICMP sessions in hardware |
| ICMP | Internet Control Message Protocol |
| NPU | Network Processing Unit - ASIC used for processing and forwarding packets |
| ToR | Top of Rack Switch that connects to the servers on the rack |
| TLV | Type Length Value - Used in payload of ICMP sessions |

## Scope
This document describes high level design details of SONiC's ICMP Hardware Offload and using FRR Hardware Protection switching for dual ToR architecture.
A separate HLD will be added to cover the high level design of FRR Hardware Protection switching for dual ToR architecture.


## Table of Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Requirement Overview](#requirement-overview)
  - [Overview](#overview)
  - [Requirement](#requirement)
- [High Level Components and Requirement](#high-level-components-and-requirements)
  - [LinkMgrd Requirements](#linkmgrd-requirements)
  - [Orchagent Requirements](#orchagent-requirements)
  - [SaiRedis Requirements](#sairedis-requirements)
- [Detailed Design](#detailed-design)
    - [LinkMgrd](#linkmgrd)
      - [Session cookie](#session-cookie)
      - [Session GUID handling](#session-guid-handling)
      - [Peer session handling](#peer-session-handling)
      - [Timer considerations](#timer-considerations)
      - [Link Prober State transitions](#link-prober-state-transitions)
      - [TLV generation considerations](#tlv-generation-considerations)
    - [Orchagent](#orchagent)
      - [IcmpOrch](#icmporch)
      - [MuxOrch](#muxorch)
      - [MuxCableOrch](#muxcableorch)
      - [MuxNbrHandler](#muxnbrhandler)
- [DB Schema Changes](#db-schema-changes)
  - [Config-DB](#config-db)
  - [App-DB](#app-db)
  - [State-DB](#state-db)
- [Command Line](#command-line)
- [Testing](#testing)

<!-- /code_chunk_output -->


## Requirement Overview
### Overview
SONiC uses ICMP echo request and reply packets to monitor state of links between server blades and the ToR switches in DualTor architecture. When link state change is detected, SONiC switches the traffic by reprogramming the routes. Currently SONiC uses software based generation and reception of ICMP packets that passes over the Host OS network stack. This limits the intervals at which ICMP packets can be transmitted and received and hence the link state detection time. Reprogramming of routes during the switchover also adds further delays to switch the traffic. ICMP hardware offload and FRR protection switching addresses these limitations.

ICMP Hardware offload overcomes this limitation using the NPU hardware in the ToR switches to transmit and receive the ICMP packets and monitor the ICMP sessions for link state. This hardware based monitoring reduces the link state detection time.

Protection switching reduces the switching time by avoiding reprogramming of routes and using Next Hop Protection Group in NPU hardware to toggle the traffic destination.

Following diagram shows the cluster topology of Dual-ToR architecture for reference. Both ToRs use same loopback IP address as source IP in the ICMP echo packets.
<div align="center"> <img src=image/cluster_topology.png width=600 /> </div>

### Requirement
Current link state detection time with software based ICMP sessions is in the order of 200-400 milliseconds. Requirement for ICMP Hardware Offload is to bring this down to < 10 milliseconds.

Currently switching time after link state change is detected, is around 25-50 milliseconds. Note this depends on route scale. Requirement for FRR protection switching using Nexthop Protection Group is to keep it consistent irrespective of the route scale.

### High Level Components and Requirements
#### LinkMgrd Requirements
LinkMgrd is the central component that runs in MUX docker and is responsible for managing ICMP echo sessions and link state. Link prober sub-component in Linkmgrd is responsible for the ICMP echo sessions.
* Requirements
   * Add / Remove Hardware ICMP echo session in App DB based on mux cable and link prober config entries.
   * Consume ICMP echo session state from State DB produced by Orchagent and update mux state.
   * Create two hardware sessions per mux port / interface one for self and another one to monitor the peer replies.
   * Generate and handle ICMP packets with TLVs in software.

Following diagram shows the hardware ICMP echo sessions between the TORs and Server.
<div align="center"> <img src=image/hw_icmp_echo_sessions.png width=600 /> </div>

#### Orchagent Requirements
Currently orchagent creates tunnel at initialization and add / removes routes to forward traffic to peer ToR via a IpinIP tunnel when linkmgrd switches state to standby / active.
* IcmpOrch Requirements
   * Create / Remove hardware ICMP echo sessions by consuming entries in App DB.
   * Consume ICMP echo session notification from SAI and update session state in State DB.
* MuxOrch Requirements
   * Create Protection Next Hop group for FRR switchover based on config.
   * Initiate traffic switchover by toggling members of Protection Next Hop group based on mux state produced by LinkMgrd.

#### SaiRedis Requirements
A new SAI specification was added to support ICMP Echo offload sessions in SAI version 1.12.
* Requirements
  * Support all SAI attributes of sai icmp echo session from saiicmpecho.h.
  * Support SAI switch notification for sai icmp echo sessions.

## Detailed Design
Following diagram describes high level interaction of components in SONiC.
<div align="center"> <img src=image/sonic_component_interaction.png width=700 /> </div>

### LinkMgrd
With introduction of ICMP hardware offload a new config knob **[prober_type]** is added to differentiate between software and hardware based link probing. Hardware based Link Prober is added in LinkMgrd to support hardware based probing that produces the ICMP echo sessions entries in App DB ICMP_ECHO_SESSION_TABLE that gets consumed by orchagent. LinkMgrd will consume icmp echo session entries from State DB ICMP_ECHO_SESSION_TABLE to determine the hardware prober state and trigger events for Link state machines.

#### Session cookie
Session cookie is used by NPU to distinguish between software ICMP packets and ICMP packets that needs to be handled by the offload engine in NPU. LinkMgrd will use separate cookies for software and hardware based sessions.

#### Session GUID handling
Session GUID is used to distinguish between the ICMP sessions. However session GUID is not generated per session in the current implementation, yet it works as the software based probing uses raw Linux packet socket on the interface. This way software does not need to demultiplex icmp echo reply packets for each link's session based on session GUID. However in hardware based approach NPU uses the session GUID to map the icmp packets to a session. So with introduction of hardware probing session GUID will always be a randomly generated unique value for both software and hardware sessions.

To avoid collision of GUIDs between self and peer sessions, last byte of session GUID will be set to a fixed value unique to a ToR. ToR roles like Upper ToR and Lower ToR can be determined based on multiple factors and Linkmgrd can as well use some preset values based on these roles as the last byte of session GUID.

#### Peer session handling
Hardware Link prober needs to know the peer session GUID to set the peer session entry in App DB. For this the hardware link prober in LinkMgrd will listen / receive initially icmp echo reply packets from peer over the Linux packet socket on the interface, reusing the mechanism used in software link prober. It will learn the session GUID from the payload of these icmp echo reply packets from peer and use this learnt session GUID to create the hardware offload session entry for peer in App DB.

#### Timer considerations
* **Minimum timer value:** Minimum allowed timer value for software session will be set to 100 msec and for hardware session will be 3 msec.
* **ICMP echo session tx_interval setting:**
    * tx_interval = probing interval
    * Positive probing timer value = probing interval x positive signal count.
    * LinkMgrd will start positive probing timer after receiving the first UP state notification for a session from State DB and link prober will continue to remain in unknown state until the expiry of this positive timer at which it will transition the Link prober to Active state.
* **ICMP echo session rx_interval setting:**
    * rx_interval = probing interval x negative signal count.
    * LinkMgrd will directly transition the link prober to unknown state avoiding the negative probing timer as opposed to what was done in case of software probing.

#### Link Prober State transitions
Following table shows the link prober state transitions based on event when link_prober mode is set as hardware and icmp echo session is offloaded to NPU.
<div align="center"> <img src=image/link_state_transition.png width=600 /> </div>

#### TLV generation considerations
ICMP packets with TLVs will not be generated by the hardware/NPU and LinkMgrd will generate these packets in software using the software cookie as currently done by software prober. Using the software cookie for TLV generation will make sure peer NPU will not consume these ICMP packets in hardware and LinkMgrd running on peer ToR will be able to receive and handle these TLV packets.

### Orchagent
#### IcmpOrch
IcmpOrch is a new component introduced which consumes icmp echo session entries from App DB ICMP_ECHO_SESSION_TABLE and programs the ICMP hardware offload sessions in NPU. It receives icmp echo session state notifications from SAI / NPU and produces session state in State DB ICMP_ECHO_SESSION_TABLE that is consumed by LinkMgrd.

Following diagram describes the component level flow for icmp session creation and removal.
<div align="center"> <img src=image/icmp_session_create.png width=700 /> </div>

Following diagram describes the component level flow for icmp state change notifications.
<div align="center"> <img src=image/icmp_session_state_notification.png width=600 /> </div>

* **Session Key format:**
Vrf-name : Interface Alias : Session GUID : Session Type
* Examples of session key format:
  * default:default:5000:NORMAL
  * default:default:6000:RX
  * default:Ethernet0:12000:NORMAL
* Session Type:
  * 'NORMAL': Install a normal icmp echo session that will transmit, receive icmp echo session packets and monitor the session.
  * 'RX': Install a monitor only icmp echo session and set the tx_interval to zero which will not send any icmp echo session.
* Interface Alias 'default' will set the SAI atttribute hw_lookup to true and NPU will perform forwarding lookup basd on dst_ip to determine the outgoing interface.

#### MuxOrch
This feature introduces a new config knob **switching_mode** to differentiate between normal software based switching and hardware based protection switching that will use next hop protection group hardware type to switch traffic. MuxOrch will create next hop protection groups for each mux port and maintain a mapping of mux port and next hop protection groups based on this config knob.
MuxOrch creates the IPinIP tunnel based on the peer_switch configuration. Currently IPinIP tunnel destination next hop is created when mux state changes to standby however with hardware based protection switching_mode it will create the IPinIP tunnel destination next hop in advance and add this as the backup member of the next hop protection group.

#### MuxCableOrch
MuxCableOrch in orchagent is the component responsible for consuming mux state from App DB MUX_CABLE_TABLE and switching traffic. Currently this component updates all routes whenever a traffic switchover is needed. When **switching_mode** will be set to **hardware-protection** in MuxOrch, MuxCableOrch will program the routes with the nexthop protection group as destination. With hardware-protection mode traffic switching will be done in hardware and SONiC will no longer need to reprogram all routes manually.

SONiC today allows changing the muxcable state to active or standby using configuration, with hardware-protection mode SAI support needs to be added into protection group type hardware.

When using hardware-protection switching_mode ICMP session state notification would also indicate the switching notification.

Following diagram shows component level flow for traffic switching.
<div align="center"> <img src=image/traffic_switching_flow.png width=700 /> </div>

#### MuxNbrHandler
Currently when FDB changes or neighbor changes, neighbors are updated based on the state of mux. With frr **hardware-protection** swithing_mode when a new neighbor is learnt on mux port following will happen:
  * create a frr protection nexthop group, with the IPinIP tunnel destination nexthop as backup nexthop.
  * add the neighbor without host route using sai attribute SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE.
  * create the neighbor nexthop and add it as primary nexthop of the protection group used by the neighbor.
  * update all routes to this neigbor to point to the protection group nexthop group. 

### DB Schema Changes

#### Config-DB
Two new knobs will be added in MUX_LINKMGR|LINK_PROBER and MUX_CABLE config table to support these features:
  * **prober_type**
    * software : create software based icmp echo session. This is default value.
    * hardware : create hardware based icmp echo session.
  * **switching_mode**
    * normal                   : Use normal software for traffic switching. This is default value.
    * hardware                 : Use hardware FRR protection group for traffic switching.

```
{
    "MUX_CABLE": {
        "Ethernet4": {
	    "cable_type": "active-active",
            "server_ipv4": "192.168.0.2/32",
            "server_ipv6": "fc02:1000::30/128",
            "soc_ipv4": "192.168.0.3/32",
            "state": "auto",
            "prober_type": "software/hardware",
            "switching_mode": "normal/hardware",
        }
    }
}
```

#### App-DB
A new table, named **ICMP_ECHO_SESSION_TABLE**, will be introduced in the App DB to create hardware based icmp echo sessions. Entries in this table will be produced by LinkMgrd and consumed by Orchagent.

```
{
    "ICMP_ECHO_SESSION_TABLE:default:Ethernet0:6000:NORMAL": {
        "value": {
      	    "dst_ip": "192.168.0.3",
            "dst_mac": "42:1a:16:02:d8:db",
            "rx_interval": "15",
            "session_cookie": "0x55aa55aa",
            "session_guid": "6000",
            "src_ip": "10.1.0.36",
            "tx_interval": "3"
        }
    }
}
```

#### State-DB

A new table **ICMP_ECHO_SESSION_TABLE** will be added in the State DB. Entries in this table will be produced by orchagent and consumed by LinkMgrd.

```
{
    "ICMP_ECHO_SESSION_TABLE|default|Ethernet0|6000|NORMAL": {
        "value": {
            "dst_ip": "192.168.0.3",
            "hw_lookup": "false",
            "rx_interval": "15",
            "session_cookie": "0x55aa55aa",
            "session_guid": "6000",
            "src_ip": "10.1.0.36",
            "state": "Up",
            "tx_interval": "3"
        }
    }
}
```

## Command Line



### Show CLI

**Existing CLI to show mux config**

`show mux config` returns the mux configurations:
  * `SWITCH_NAME`: peer switch hostname
  * `PEER_TOR`: peer switch loopback address
  * `PORT`: mux port name
  * `state`: mux mode configuration
    * `auto`: enable failover logics for both self and peer
    * `manual`: disable failover logics for both self and peer
    * `active`: if current mux status is not `active`, toggle the mux to `active`
    * `standby`: if current mux status is not `standby`, toggle the mux `standby`
    * `detach`: enable failover logics only for self
  * `ipv4`: mux server ipv4 address
  * `ipv6`: mux server ipv6 address
  * `cable_type`: mux cable type, `active-active` for active-active dualtor
  * `soc_ipv4`: soc ipv4 address

```
$ show mux config
SWITCH_NAME        PEER_TOR
-----------------  ----------
lab-switch-2  10.1.0.33
port        state    ipv4             ipv6               cable_type     soc_ipv4
----------  -------  ---------------  -----------------  -------------  ---------------
Ethernet4   auto     192.168.0.2/32   fc02:1000::2/128   active-active  192.168.0.3/32
Ethernet8   auto     192.168.0.4/32   fc02:1000::4/128   active-active  192.168.0.5/32
```

**New CLI to show mux config**
```
$ show mux config
SWITCH_NAME        PEER_TOR
-----------------  ----------
lab-switch-2  10.1.0.33
port        state    ipv4             ipv6               cable_type     soc_ipv4         prober_type
----------  -------  ---------------  -----------------  -------------  ---------------  ----------------
Ethernet4   auto     192.168.0.2/32   fc02:1000::2/128   active-active  192.168.0.3/32   hardware
Ethernet8   auto     192.168.0.4/32   fc02:1000::4/128   active-active  192.168.0.5/32   hardware
```

**New CLI to show hardware icmp sessions**
```
$ show icmp sessions
Key                                  Dst IP         Tx Interval    Rx Interval  HW lookup    Cookie      State
-----------------------------------  -----------  -------------  -------------  -----------  ----------  -------
default|Ethernet0|0x12e386aa|NORMAL  192.168.0.3            100            300  false        0x58767e7a  Up
default|Ethernet0|0xa458bfbc|RX      192.168.0.3              0            300  false        0x58767e7a  Up
```

**New CLI to show hardware icmp sessions summary**
```
$ show icmp summary
# show icmp summary
Total Sessions: 2
Up sessions: 2
RX sessions: 1
```

## Testing
- Unit tests for LinkMgrd
- Unit tests for IcmpOrch
- Unit tests for MuxOrch / MuxCableOrch / MuxCfgOrch
- Unit tests for Yang-model and CLIs
- Existing SONiC Management tests for dual-ToR:
- New SONiC Management test for dual-ToR:
    - Add support for hardware based ICMP echo session configurations
    - Add support for FRR Hardware Protection switching configurations
