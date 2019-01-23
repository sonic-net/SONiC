MC-LAG high level design for SONiC

# Document History

| Version | Date       | Author                 | Description                                      |
|---------|------------|------------------------|--------------------------------------------------|
| v.01    | 07/30/2018 |jian                    | Initial version from nephos                      |
| v.02    | 10/19/2018 |jian/shine/jeffrey      | Revised per review meeting with SONIC community  |
| v.03    | 09/18/2018 |jeffrey                 | Minor update to clarify the behavior.            |

# Abbreviations

|**Term** |**Definition**                                    |
|---------|--------------------------------------------------|
|MCLAG	  |Multi-Chassis Link Aggregation Group              |
|ICCP	  |Inter-Chassis Communication Protocol                |

# 3	Terminologies
![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_terminology.png)
 

# 4	Design considerations

- 	MCLAG domain consists of only two systems.
- 	Each system only join one MC-LAG domain
- 	Supports only Unicast
- 	L3 interface on MLAG ports will have vMAC generated from VRRP algorithm using the same IP address assigned to the L3 LIF (logical interface)；(Not supported currently) 
- 	ARP resolution and ARP response packet sync-up between MC-LAG peers
- 	No FDB sync-up between MC-LAG peers [TBD: to be done if required and when SONiC software FDB table sync up with Hardware is available]
- 	Support MC-LAG routed port or MC-LAG L2 port joining L3 vlan interface  

> [caveat: vlan interface does not go down when the last port in the
> vlan goes down, need further discussion in the community with
> regarding the 1Q or 1D model]

# 5	Brief introduction of ICCPd

ICCP(Inter-Chassis Communication Protocol) is defined in RFC7275，our MLAG control plane implements the light version of ICCP. RFC7275 has very complicated state machines, information to be synced up between peers are very heavy, sanity checks are accordingly too many. So-called Lite Version is that MLAG ICCPd only implements a subset of the state machines defined in RFC7275 without compromising the usefulness and integrity.

ICCP protocol using TCP port 8888 to make connection between peers, ICCP lite will do configuration consistence check, sync up ARP table and MAC address of related interfaces.

## 5.1	Use-cases supported by ICCP lite

RFC7275 describes 4 use-cases, this ICCPd or ICCP lite only support “Co-located Dedicated Interconnect”、“Geo-redundant Dedicated Interconnect”:

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_5.1.1.png)

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_5.1.2.png)
 

RFC7275 says that information sync and heartbeat checking and data traffic can take by individual link. Lite version is not supported currently, the peer-link plays all the roles.

In supported two cases above, the requirement is the direct-connected L3 peer link connecting the two peer devices. The peer link interface can be either Ethernet or PortChannel interface. The peer-link (TCP) is used to establish connection, information sync and heartbeat checking from control plane view. But the peer link can be also used to carry data traffic when one of the MC-LAG member link is down and re-routing is needed. Peer-link has active vs standby status, the status is selected by numeric value of peer-link IP address: bigger one is active peer, smaller one is standby peer. Client initiate the connection request to server. 

Will MC-LAG work if there is no physical connection between the peers? In theory, if the peer IP address is reachable, there is no requirement to have physical connection between the peers. But in the lite version, if one of the MC-LAG member link is down, a static route via peer-link will be generated to re-route the data traffic. If the peer-link is not directly connected, the nexthop of that static route is unknown, the route installation will fail. So in the current lite version, if the peer-link is not directly connected via a physical interface, MC-LAG is not supported. It will be supported in later version.

## 5.2	ICCPd State machines

Lite version support complete “ICCP Connection State Machine”，shown as followings:
The ICCP Connection state machine is defined to have six states, as below. Please note although LDP is mentioned in the below section, it’s not used for ICCPd.

- NONEXISTENT: This state is the starting point for the state machine. It indicates that no ICCP connection exists and that there’s no LDP session established between the PEs.

- INITIALIZED: This state indicates that an LDP session exists between the PEs but LDP ICCP capability information has not yet been exchanged between them.

- CAPSENT: This state indicates that an LDP session exists between the PEs and that the local PE has advertised LDP ICCP capability to its peer.

- CAPREC: This state indicates that an LDP session exists between the PEs and that the local PE has both received and advertised LDP ICCP capability from/to its peer.

- CONNECTING: This state indicates that the local PE has initiated an ICCP connection to its peer and is awaiting its response.

- OPERATIONAL: This state indicates that the ICCP connection is operational.

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_5.2.png)

RFC7275 also describes so called “Application Connection State Machine”, which are designed for application exclusively, and each application maintains its own state machines. 

In this version, when ICCP state machine becomes OPERATIONAL, application state machine will be OPERATIONAL immediately.

In RFC7275 original requirements, ICCP will sync up many information with LACP protocol etc. This lite version does not implement the connection between ICCP and teamd to avoid the modification in teamd, there is no information exchange between ICCPd and teamd neither. ICCP work with teamd indirectly, for example, when ICCPd detects the change of MAC address for any MLAG member portchannel, ICCPd will inform Linux kernel and teamd will be hence notified by kernel.  In this way, teamd can notify LACP so that LACP in the server will form teamd interface.

## 5.3	Role election

ICCP peer must be in active mode or standby mode. The ipv4 address is used to determine which role the peer has Local ip and remote ip is configured manually, system compares these two ip addresses to determine its role, the one with large IP address is the standby, and the other one is active. Active is the client, standby is the server. The client connect to the server actively. 

The role of active or standby is the concept of control plane. In the data plane, each peer determine the data forward path individually, no matter the role it is.

Another way to specify the active/standby role is via static configuration from config db. Currently static configuration from config db is not supported, may support it in the future.

## 5.4	Information sync up with ICCP

Following information are sync’ed up between ICCP lite peers.

1	system configuration：Sync up system MAC address. This is to serve LACP to derive the correct system ID. When the standby receives a system MAC from active, it will change local system ID to the peer system MAC.

2	Aggregator configuration: Sync up AGG_ID (portchannel ID, name, MAC etc), this is to record portchannel information of each peer. This info is used for sanity check as well as enabling packet forwarding in the peer link when a member link of MC-LAG goes down.

3	Aggregator State: mainly exchanges portchannel state (up/down) with AGG_ID. Generally, if the same named portchannels in each peer are both up, the data forwarding in the peer-link for that portchannel is disabled to prevent the data stream pass-through. When a portchannel of one peer is down, the peer-link is enabled for that portchannel to let the data stream pass-through.

4	ARP information: ARP entries learned from kernel will be synced up with peer. The peer will update kernel as dynamically learned ARP once the ARP is synced via ICCP. 

ICCP lite does not support port-configuration/state sync up. We don’t sync the static IP address, it’s to update the nexthop info of the prefix.
## 5.5	ICCP Heartbeat sanity check

RFC7275 does not specify how to do the heartbeat check, but just suggest to use BFD or IP reachability monitoring to check if peer is reachable. This ICCP lite version defines a proprietary heartbeat message sent every 1s. If no such message is received within 3 consecutive intervals, then peer is declared as lost.
## 5.6	ICCP consistence check

This lite version does consistence check for the following contents:
1	Peer IP, local IP will be checked against with message contents.
2	Enable MC-LAG portchannel interface check: if it is L3 interface, then the IP address assigned must be the same. If they join a vlan, then the vlan must be the same etc.

# 6	Typical configurations

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_6.1.png)

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_6.2.png)

Combination of both cases in one system are supported.

# 7	Typical Data diagram for MCLAG

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_7.1.png)                           
In the above diagram, PortChannel0001 and PortChannel0002 are mclag enabled interfaces, PortChannel0003 is peer-link. Peer-link forwarding is disabled for mclag enabled interfaces, and MAC learning of peer-link is disabled. Generally, all portchannels in each PE are in up state, and the data flow path is presented by the red line.
                        
![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_7.2.png)
In the above diagram, if PortChannel0001 in PE1 is down, the data flow from CE2 to CE1 through PE1 is changed to the path presented by the blue line. A shorter prefix is installed in PE1 with nexthop points to the peer link. the data flow from CE1 to CE2 is unchanged. When PE2 is notified that PortChannel0001 in PE1 is down, it remove the isolation from peer-link to PortChannel0001.

![](https://github.com/Azure/SONiC/blob/a3ee33a73c4f58f0ad32c9df893ed477843335a4/images/mclag_hld/MCLAG_HLD_7.3.png)
When peer link is down, as shown above, no action is taken. Data forwarding continues as usual, but eventually the system will become instable since information cannot be exchanged between the two peers.

# 8	SONiC system diagram for MCLAG


The MC-LAG code will run in a separate container. The following chart is with added ICCPd container. The blocks below are just illustrating the concept flow. 

![](https://github.com/Azure/SONiC/blob/6577edb5dba96d9d25c988b7aafe565063966af6/images/mclag_hld/MCLAG_HLD_8.png)

Flow 1: ICCPd reads MCLAG related configuration from CONFIG_DB

Flow 2: Updating kernel with ARP learned. Syncing up kernel with changed MAC to update LACP with system ID for the portchannel  also, in this stage, the static route using peer link is also updated.

Flow 3: ICCPd learns events such as L2 interface creation, L3 interface creation, MAC of local interfaces and its modification, IP address and its modification, ARP learning, VLAN creation and its member’s association/de-association, interface admin/link state.

Flow 4: ICCPd update teamd with system ID to help LACP to form the portchannel for the MLAG ports. Please note teamds in the two peers are independent.

Flow 5: mclagctld receives CLIs, pass it on to ICCPd, so that MCLAG information can be displayed.

Flow 6: ICCPd exchange information with APP_DB via mclagsyncd，for example, the information cover the stop L2 learning of MAC on peer-link,  flush software FDB table of MC-LAG vlans、isolate peer-link from port-channel in the flood domain,  associate MAC to its L3 interface.

Flow 7: same as 6

Flow 8: After configure/update APP_DB, OrchAgent monitory and process the related information, then update ASIC_DB.

# 9	Design changes


## 9.1	The schema changes
1.	Adding MCLAG configuration
```
  "MC_LAG": {
        "1": {
            "local_ip": "2.2.2.1",
            "bind_lacp": "PortChannel0001,PortChannel0002",
            "peer_link": "PortChannel0022",
            "peer_ip": "2.2.2.2"
        }
    },
```
2.	Adding a new mclagsyncd process
Mclagsyncd will work with APP_DB to take care of following actions:
Disable L2 learning for peer-link port for those VLANs that there is no need of flooding. Flash FDB table contents for MCLAG vlans. Isolate peer-link from portchannel、updating MAC association with its L3 interface.

3.	Adding mclagctld process
Mclagctld supports some new defined CLIs so that some ICCPd related information can be displayed. 
The new CLIs are:
```
1.	mclagdctl -i <mclag-id> dump arp
This command to display the local ARP entries learned from the port-channels that mclag is enabled.
2.	mclagdctl -i <mclag-id> dump mac
This command to display the local MAC entries learned from the port-channels that mclag is enabled.
3.	mclagdctl -i <mclag-id> dump portlist local
This command to display the local portlist, include the port-channels and their member ports.
4.	mclagdctl -i <mclag-id> dump portlist peer
This command to display the peer portlist, include the port-channels and their member ports.
5.mclagdctl -i <mclag-id> dump state
This command to display the local configuration and state.
```
## 9.2	portsorch changes
Adding the following logic:
Listening new APP_DB events，isolating peer-link ports,  learn interface MACs.

## 9.3	intfsorch changes
Adding the following logics:
Listening MAC modification of L3 interfaces,  updating it to ASIC
Removing adding/delete direct connected network FIB update triggered by creation of L3 interface in orchAgent. (Such direct connected network FIB does not respond to the state change which is wrong, it only responds to the ip address addition or deletion）

## 9.4	routeorch changes
From this version, the direct connect network is not created by intfsorch. Like other types of route, the direct connect network is informed by Zebra. This is a common issue, not only for MC-LAG support.
rocess

