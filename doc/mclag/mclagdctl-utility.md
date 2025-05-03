## MCLAGDCTL

`mclagdctl` is utility helps debug mclag setup and track it's state.

Usage: `mclagdctl -i X COMMAND`.

X is maclag domain id.

Available commands:
   * dump state
   * dump arp
   * dump portlist local
   * dump portlist peer
   * dump debug counters
   * dump nd
   * dump mac
   * dump unique_ip
   * config loglevel

Example: `mclagdctl -i 1 dump state`

### Command reference:

#### dump state
Show state of the whole mclag setup

Example:
```mclagdctl -i 1 dump state
The MCLAG's keepalive is: OK         # OK in case connection between iccpds state is ICCP_OPERATIONAL.
MCLAG info sync is: completed        # Completed if mlacp state is MLACP_STATE_EXCHANGE else incomplete.
Domain id: 1                         # Id of mclag domain, currently only one domain is supported.
Local Ip: 192.168.3.1                # Local (source) ip, used for iccpd keepalive messages.
Peer Ip: 192.168.3.2                 # Remote (target) ip, used for iccpd keepalive messages,
                                     # in L3 scenario can be used for traffic
                                     # routing instead of peerlink interface.
Peer Link Interface: Unknown         # Interface used to redirect traffic in case one link is down,
                                     # in L3 scenario can use Unknown (unset), instead use peer ip.
Keepalive time: 1                    # Interval between keepalive messages.
sesssion Timeout : 15                # Max interval of absence keep alive message.
Peer Link Mac: 00:00:00:00:00:00     # Mac of peer link interface,
                                     # in L3 scenario can be blank in case peer ip is used instead.
Role: Active                         # Active in case current iccpd connects to peers,
                                     # Standby in case current iccpd wait for other's connection.
MCLAG Interface: PortChannel0001     # Portchannel grouped with other portchannel in mclag
Loglevel: NOTICE                     # Loglevel of iccpd.
```

#### dump arp

ARP table of MCLAG.
Contains records related only to MCLAG interfaces, in case host connected though non MCLAG interface it will not be mentioned in command output.

Example:
```
mclagdctl -i 1 dump arp
No.   IP                  MAC                 DEV                 Flag
1     192.168.1.1         fe:54:00:a0:d0:df   PortChannel0001     L
```

#### dump portlist local

Show extened info about local MCLAG portchannel with its members.

Example:
```
root@sonic:/home/admin# mclagdctl -i 1 dump portlist local
------------------------------------------------------------
Ifindex: 20
Type: Ethernet
PortName: Ethernet0
State: Up
VlanList:
------------------------------------------------------------

------------------------------------------------------------
Ifindex: 24
Type: PortChannel
PortName: PortChannel0001
MAC: 52:52:00:11:11:11
IPv4Address: 192.168.1.2
Prefixlen: 24
State: Up
IsL3Interface: Yes
MemberPorts: Ethernet0
PortchannelIsUp: 1
IsIsolateWithPeerlink: No
IsTrafficDisable: No
VlanList:
------------------------------------------------------------
```

#### dump portlist peer

Show brief info about remote portchannel interface.
Peer MAC must be the same as local portchannel MAC, because both those physical interfaces must look like one logical interface with same MAC and IP. All other values may differ.

Example:
```
mclagdctl -i 1 dump portlist peer
------------------------------------------------------------
Ifindex: 1
Type: PortChannel
PortName: PortChannel0001
MAC: 52:52:00:11:11:11
State: Up
------------------------------------------------------------
```

#### dump debug counters

Show info on iccpd's connection, including errors and reconnects.

Example:
```
mclagdctl -i 1 dump debug counters
ICCP session down:  0
Peer link down:     0
Rx invalid msg:     0
Rx sock error(hdr): 0
Rx zero len(hdr):   0
Rx sock error(tlv): 0
Rx zero len(tlv):   0
Rx retry max:       0
Rx retry total:     0
Rx retry fail:      0
Socket close err:   0
Socket cleanup:     0

Warmboot:           0

ICCP to MclagSyncd  TX_OK               TX_ERROR
------------------  -----               --------
PortIsolation       0                   0
MacLearnMode        0                   0
FlushFdb            0                   0
SetIfMac            0                   0
SetFdb              0                   0
TrafficDistEnable   1                   0
TrafficDistDisable  1                   0
SetIccpState        1                   0
SetIccpRole         1                   0
SetSystemId         0                   0
DelIccpInfo         0                   0
SetRemoteIntfSts    6                   0
DelRemoteIntf       0                   0
PeerLinkIsolation   0                   0
SetPeerSystemId     0                   0

MclagSyncd to ICCP  RX_OK               RX_ERROR
------------------  -----               --------
FdbChange           0                   0
CfgMclag            1                   0
CfgMclagIface       1                   0
CfgMclagUniqueIp    0                   0
vlanMbrshipChange   0                   0

ICCP to Peer        TX_OK               RX_OK               TX_ERROR            RX_ERROR
------------        -----               -----               --------            --------
SysConfig           1                   1                   0                   0
AggrConfig          1                   1                   0                   0
AggrState           2                   2                   0                   0
MacInfo             0                   0                   0                   0
ArpInfo             2                   1                   0                   0
Unknown             0                   0                   0                   0
PoInfo              1                   1                   0                   0
PeerLinkInfo        0                   0                   0                   0
Heartbeat           7055                7054                0                   0
Nak                 0                   0                   0                   0
SyncData            2                   2                   0                   0
SyncReq             1                   0                   0                   0
Warmboot            0                   0                   0                   0
IfUpAck             1                   1                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0
Unknown             0                   0                   0                   0


Netlink Counters
-----------------
Link add/del: 7/0
  Unknown if_name: 17
Neighbor(ARP) add/del: 20/2
  MAC entry add/del: 0/0
Address add/del: 11/0
Unexpected message type: 0
Receive error: 0
```
#### config loglevel

Set iccpd's loglevel.

Available levels:
    * critical
    * err
    * warn
    * notice
    * info
    * debug

NOTES:
    * keep on mind, that mclagsyncd is a part of swss, so its loglevel must be set using swssloglevel.
    * it is mandatory to specify `-l` before target loglevel, see example.

Example:
```mclagdctl -i 1 config loglevel -l debug
Config loglevel success!
```

### TODO: describe next commands
#### dump nd
#### dump mac
#### dump unique_ip
