SONiC VRF support design spec draft

Table of Contents

Document History
================

| Version | Date       | Author       | Description                                      |
|---------|------------|--------------|--------------------------------------------------|
| v.01    | 06/07/2018 | Shine/Andrew | Initial version from nephos                      |
| v.02    | 06/08/2018 | Shine        | Revised per Guohan/prince(MSFT) opinion          |
| v.03    | 09/18/2018 | Guohan       | Format document                                  |
| v.04    | 01/17/20189| shine/jeffrey| Update after Sonic community review              |

Abbreviations
=============

| **Term** | **Definition**                                                                                                                                  |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| VRF      | Virtual routing forwarding                                                                                                                      |
| FRR      | FRRouting is an IP routing protocol suite for Linux and Unix platforms which includes protocol daemons for BGP, IS-IS, LDP, OSPF, PIM, and RIP  |
| Quagga   | Open IP routing protocol suite                                                                                                                  |
| RIB      | Routing Information Base                                                                                                                        |
| PBR      | Policy based routing 	                                                                                                                     |


VRF feature Requirement
=============

    - Add or Delete VRF instance
    - Bind VRF to a L3 interface.
          L3 interface includes port interface, vlan interface, LAG interface and  loopback interface.
    - Static IP route with VRF
    - Enable BGP VRF aware in SONiC
    - fallback lookup
          The fallback feature is very useful for specify VRF user access internet through global/main route
          which is defined by RFC4364. Some enterprise user still use this to access internet on vpn environment. 
    - VRF route leaking between VRFs.

    In this release, supporting requirement 5) and 6) are not supported. See next section for details.

Note: linux kernel use VRF master device to support VRF and it supports admin
      up/down on VRF maser dev. But we don't plan to support it on SONIC.

Dependencies
============

VRF feature needs the following software package/upgrade

1.  Linux kernel 4.9

Linux Kernel 4.9 support generic IP VRF with L3 master net device. Every L3
master net device has its own FIB. The name of the master device is the
VRF’s name. Real network interface can join the VRF by becoming the slave of
the master net device.

Application can get creation of deletion of VRF master device via RTNETLINK,
as well as information about slave net device joining a VRF.

Linux kernel supports VRF forwarding using PBR scheme. It will fall to main
routing table to check IP lookup. VRF also can have its own default network
instruction in case VRF lookup fails.

2.  FRRouting is needed to support BGP VRF aware routing.

3.  IProute2 version should be ss161212 or later to support iproute2 CLIs to
    configure the switch.

Example of using iproute2:

```
setup VRF | name: vrf-blue fib-table-id: 10
$ ip link add name vrf-blue type vrf table 10

enable VRF
$ ip link set dev vrf-blue up

disable fallback lookup on vrf-blue
$ ip [-6] route add table 10 unreachable default

bind sw1p3 device to vrf-blue
$ ip link set dev sw1p3 master vrf-blue

descend local table pref
ip [-6] rule add pref 32765 table local && ip [-6] rule del pref 0
```

4.  SAI VRF support

SAI right now does not seem having VRF concept, it does have VR.

We propose to implement VR as “virtual router” and VRF as “virtual router
forwarding”

VR is defined as an logical routing system. VRF is defined as forwarding
domain within a VR.

As this stage, we assume one VR per system. Only implement VRFs within this VR.

Accordingly, we need to add vrf_id to sai_Route_entry and add vrf attribute
to sai_routeInterface object.

An alternative method is using VR as VRF, this requires to add two attribution
to VR object to support Requirement 5) (fallback lookup). SAI community has 
decided that take VR as VRF. So in this implement release we use VR object as VRF.

```
/*
 * \@brief if it is global vrf
 *
 * \@type bool
 * \@flags CREATE_AND_SET
 * \@default true
 */
 SAI_VIRTUAL_ROUTER_ATTR_GLOBAL

/*
 * \@brief continue to do global fib lookup while current vrf fib lookup
 *  missed
 * 
 * \@type bool
 * \@flags CREATE_AND_SET
 * \@default false
 */
 SAI_VIRTUAL_ROUTER_ATTR_FALLBACK
```

SONiC system diagram for VRF
============================

The following is high level diagram of modules with VRF support.
![](https://github.com/Azure/SONiC/blob/f2ebba476b4ef364b13b7980c2fe01e8929c71e6/images/vrf_hld/VRF_HIGH_LEVEL_DIAGRAM.png)


## The schema changes

1. Adding VRF related configuration in config_db.json.
Note "fallback" keyword is not supported in this release.

```
"VRF": {
    "VRF-blue": {
        "fallback":"true" //enable global fib lookup while vrf fib lookup missed
    },
    "VRF-red":{
        "fallback": "true"
    },
    "VRF-yellow":{
        "fallback":"false" //disable global fib lookup while vrf fib lookup missed
    }
},

"INTERFACE":{
    "Ethernet0":{
        "vrf":"vrf-blue"
    },
    "Ethernet1":{
        "vrf":"vrf-red"
    },
    "Ethernet0|vrf-blue|11.11.11.1/24": {},
    "Ethernet0|vrf-blue|12.12.12.1/24": {},
    "Ethernet1|vrf-red |12.12.12.1/24": {},
    "Ethernet2|13.13.13.1/24": {} //In global vrf the key will keep unchanged
},

"VLAN_INTERFACE": {
    "Vlan100":{
        "vrf":"vrf-blue"
    },
    "Vlan100|vrf-blue|15.15.15.1/24": {}
}
```
Ip address configuration has tight event order dependency with interface bind vrf configuration.
But currently sonic can Not guarantee that. So we add vrf-name prefix before ip address. 
It can remove vrf-bind and ip address setting order dependency.

2. **Adding a VRF_TABLE** in APP_DB

```
;defines virtual routing forward table
;
;Status: stable

key = VRF_TABLE:VRF_NAME ;
fallback = "true"/"false"
```

3. **Add 2-segment key entry** support in APP-intf-table

There is two reason why add 2-segment key entry in interface table.
1. Multiple ip addresses can be configured on one interface. So we put interface common attribute 
   into app-intf-table and keep ip-prefix specific attribute on app-intf-prefix-table.
2. Interface can be put to specific VRF before ip address is configured on it.

For same reason describled on configdb.json paragraph we add vrf-name-prefix before ip-prefix on app-intf-prefix table.

app-intf-table is defined as the following:

```
;defines logical network interfaces, an attachment to a PORT name
;
;Status: stable

key = INTF_TABLE:ifname
mtu = 1\*4DIGIT ; MTU for the interface
VRF_NAME = 1\*64VCHAR ;
```

app-intf-prefix-table is defined as the following:

```
;defines logical network interfaces with IP-prefix, an attachment to a PORT and
list of 0 or more ip prefixes;

;Status: stable
key = INTF_TABLE:ifname:VRF_NAME|IPprefix ; an instance of this key will be repeated for each prefix
IPprefix = IPv4prefix / IPv6prefix ; an instance of this key/value pair will be repeated for each prefix
scope = "global" / "local" ; local is an interface visible on this localhost only
mtu = 1\*4DIGIT ; MTU for the interface （move to INTF_TABLE:ifname table）
family = "IPv4" / "IPv6" ; address family
```

4. **Adding VRF key to app-route-table key list**

```
;Stores a list of routes
;Status: Mandatory

key = ROUTE_TABLE:VRF_NAME:prefix ;
nexthop = \*prefix, ;IP addresses separated “,” (empty indicates no gateway)
intf = ifindex? PORT_TABLE.key ; zero or more separated by “,” (zero indicates no interface)
blackhole = BIT ; Set to 1 if this route is a blackhole (or null0)
```

Since global vrf name is null, global vrf key will becomes ROUTE_TABLE:prefix.
Here between "VRF_NAME" and "prefix" we must change delimiter ":" to "|" since for IPv6 
there is no way to figure out if the prefix contains "VRF_NAME" or not.

## Agent changes

### VrfMgrd changes
Listening to VRF creation/deletion configuration in config_db. Once detected, 
update kernel using iproute2 CLIs and write VRF information to app-VRF-table.

When VRFMgrd receives VRF delete event it wont do it until all device binding 
to the VRF unbind from this VRF. It implicitly requires that user must first 
unbind all interfaces belong to the vrf then issue vrf-delete command.

VrfMgrd process will be placed in swss docker. In case of "swss restart", since 
VRF device is still retained in kernel, when VrfMgrd starts up it will follow the 
required steps for warm reboot and take proper actions to recover the VRF system 
state. If it's cold reboot, VrfMgrd will query kernel to obtain all the VRF 
intefaces and flush those intefaces.

### IntfsMgrd changes
Listening to interface binding to specific VRF configuration in config_db. Once 
detected, update kernel using iproute2 CLIs and write VRF information to app-INTF-table.
When a device binds to specified VRF, implicitly intfsMgrd will first remove the IP 
address of the device in last vrf domain, then add the ip address in specified VRF.

### fpmsyncd changes
fpmsyncd will add VRF support, it can use rtnl_route_get_table to get VRF table ID.
But with the current FRR implementation, this API returns the master devices' ifIndex for 
this VRF. The messages from FRR has nexthop) information which contain further information
 about nexthop_ipaddress and interface index. VRF name can be derived from the interface index.

with added VRF ID, fpmsyncd can use rtnl_route_get_table to acquire table id.
Hence can send VRF routes further down. The messages from FRR has nh (next hop)
information which contain further information about (nexthop_ipaddress and
interface index)，tableid can be derived from the interface index.

Fpmsyncd can build ```<vrf id, vrf_name>``` pairs using rtnetlink api.

### vrforch changes
Monitoring app-VRF-table, using sai_create_virtual_router_fn or
sai_remove_virtual_router_fn defined in saivirtualrouter.h to track (VR, VRF) creation/deletion and
save (vrf_name, vrf-vid) pairs.
When VRFOrch receives vrf-delete event for a given VRF, this VRF object will be deleted after routes, 
neighbors and rif interfaces related this VRF are removed.

### intfsorch changes
-   add vrforch as one member of intfsorch
-   intfsorch monitors interface tables. When interface table contents change, handle updating 
    vrf attribute on routerintf, retrieving VRF object ID from VRFOrch.

### routeorch changes
-   Adding vrforch as one member of routesorch
-   Once app-route-table has new udpate£¬get VRF object ID from vrforch for route add/delete.
    When query nexthop£¬keys now are (VRF ID, ipaddress), VRF ID of nexthop can be acquired from nexthop interface.

### neighorch changes
-   the Key of NextHop now is changed from only ipaddress to a pair of
    ``(ipaddress, interface_name)``. VRF ID can be acquired from neighbor interface.

### TODO
-   (Mirror，tunnel，PBR) to be designed in future.

## CLI

VRF configureation can be done via SONiC Click CLIs framework

sonic CLIs are proposed as followings：

```
Config vrf <add | del> <VRF-name>
Config vrf <VRF-name> fallback <enable | disable>
Config interface <interface-name> <bind | unbind> vrf <vrf-name>
Config route add [vrf <vrf-name>] prefix <route_prefix/mask> nexthop <[vrf <vrf-name>] <ip> | dev <DEV-name>>
Config route del [vrf <vrf-name>] prefix <route_prefix/mask> nexthop [vrf <vrf-name>]  <ip> | dev <DEV-name>>
Show vrf [<interface-name>]
Show ip route //add VRF support
```

Impact to other service after import VRF feature
================================================

For apps that don't care VRF they don't need to modify after sonic import VRF.

Linux supports “VRF-global” socket from kernel 4.5.  The socket listened by
service are VRF-global by default unless the VRF instance is specified. It
means the service can accept connection over all VRFs. Connected sockets are
bound to the VRF domain in which the connection originates.

Take teamd as an example. Teamd is layer2 apps and it doesn't care VRF
attribute. Teamd code is as followed with removing some exceptional code. It
uses VRF-global socket for every port-channel member port.

```
{
    sock = socket(PF_PACKET, type, 0);
    err = attach_filter(sock, fprog, alt_fprog);
    memset(&ll_my, 0, sizeof(ll_my));
    ll_my.sll_family = AF_PACKET;
    ll_my.sll_ifindex = ifindex;
    ll_my.sll_protocol = family;
    ret = bind(sock, (struct sockaddr \*) &ll_my, sizeof(ll_my));
}
```

Put port-channel in different VRF instance doesn't affect vrf-global socket
to receive lacp protocol packet from member port. So teamd doesn't  need to
be modified or restarted for VRF binding event.

For layer 3 apps such as snmpd or ntpd they are using vrf-global socket too.
So they are vrf-transparent too.

