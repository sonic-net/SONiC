SONiC VRF support design spec draft

Table of Contents

Document History
================

| Version | Date       | Author       | Description                                      |
|---------|------------|--------------|--------------------------------------------------|
| v.01    | 06/07/2018 | Shine/Andrew | Initial version                                  |
| v.02    | 06/08/2018 | Shine        | Revised per Guohan/prince(MSFT) opinion |
|         |            |              |                                                  |

Abbreviations
=============

| **Term** | **Definition**                                                                                                                                  |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| VRF      | Virtual routing forwarding                                                                                                                      |
| FRR      | FRRouting is an IP routing protocol suite for Linux and Unix platforms which includes protocol daemons for BGP, IS-IS, LDP, OSPF, PIM, and RIP. |
| Quagga   | Open IP routing protocol suite                                                                                                                  |
| RIB      | Routing Information Base                                                                                                                        |

1.  References

2.  VRF feature Requirement

>   SONiC VRF will support the followings:

1.  Add or Delete VRF instance

2.  Bind VRF to a L3 interface.

3.  Static IP route with VRF

4.  Enable eBGP/OSPF VRF aware in SONiC

5.  Support fall through lookup

6.  TBD: VRF route leaking between VRFs.

Note: linux kernel use VRF master device to support VRF and it support admin
up/down on VRF maser dev. But we don't plan to support it on SONIC.

Dependencies
============

>   VRF feature needs the following software package/upgrade

1.  Linux kernel 4.9

>   Linux Kernel 4.9 support generic IP VRF with L3 master net device. Every L3
>   master net device has its own FIB. The name of the master device is the
>   VRF’s name. Real network interface can join the VRF by becoming the slave of
>   the master net device.

>   Application can get creation of deletion of VRF master device via RTNETLINK,
>   as well as information about slave net device joining a VRF.

>   Linux kernel supports VRF forwarding using PBR scheme. It will fall to main
>   routing table to check IP lookup. VRF also can have its own default network
>   instruction in case VRF lookup fails.

1.  FRRouting is needed to support BGP/OSPF VRF aware routing.

2.  IProute2 version should be ss161212 or later to support iproute2 CLIs to
    configure the switch.

>   Example of using iprout2:

>   VRF name: vrf-blue，fib-table-id: 10

>   \$ ip link add name vrf-blue type vrf table 10

>   //enable VRF

>   \$ ip link set dev vrf-blue up

>   // disable global VRF lookup

>   \$ ip [-6] route add table 10 unreachable default

>   //binding sw1p3 device to vrf-blue

>   \$ ip link set dev sw1p3 master vrf-blue

>   // descend local table pref

>   ip [-6] rule add pref 32765 table local && ip [-6] rule del pref 0

1.  SAI VRF support

>   SAI right now does not seem having VRF concept, it does have VR.

>   We propose to implement VR as “virtual router” and VRF as “virtual router
>   forwarding”

>   VR is defined as an logical routing system. VRF is defined as forwarding
>   domain within a VR.

>   As this stage, we assume one VR per system. Only implement VRFs within this
>   VR.

>   Accordingly, we need to add vrf_id to sai_Route_entry and add vrf attribute
>   to sai_routeInterface object.

>   An alternative method is using VR as VRF. But it is needed to add two
>   attribution to VR object.

>   /\*\*

>   \* \@brief if it is global vrf

>   \*

>   \* \@type bool

>   \* \@flags CREATE_AND_SET

>   \* \@default true

>   \*/

>   SAI_VIRTUAL_ROUTER_ATTR_GLOBAL

>   /\*\*

>   \* \@brief continue to do global fib lookup while current vrf fib lookup
>   missed

>   \*

>   \* \@type bool

>   \* \@flags CREATE_AND_SET

>   \* \@default false

>   \*/

>   SAI_VIRTUAL_ROUTER_ATTR_FALL_THROUGH

SONiC system diagram for VRF
============================

The following is high level diagram of modules with VRF support.

1.  Changes in SONiC

    1.  The schema changes

2.  **Adding VRF related configuration in config_db.json**

"VRF":{

"VRF-blue":{

"fall_through":"1" //enable global fib lookup while vrf fib lookup missed

},

"VRF-red":{

"fall_through": "1"

},

"VRF-yellow":{

"fall_through":"0" //disable global fib lookup while vrf fib lookup missed

}

},

"INTERFACE": {

“Ethernet0”:{

“mtu”:”1500”

“vrf”:”vrf-blue”}

“Ethernet1”:{

“mtu”:”1500”

“vrf”:”vrf-red”}

"Ethernet0\|11.11.11.1/24": {},

"Ethernet1\|12.12.12.1/24": {},

"Ethernet2\|13.13.13.1/24": {},

"Ethernet3\|14.14.14.1/24": {},

},

"VLAN_INTERFACE": {

“Vlan100”:{

“mtu”:”1500”

“vrf”:”vrf-blue”}

"Vlan100\|15.15.15.1/24": {},

}

1.  **Adding a app-VRF-table**

;defines virtual routing forward table

;

;Status: stable

key = VRF_TABLE:VRF_NAME ;

fall_through = “1”/”0”

1.  **Breaking up app-intf-table into app-intf-table and app-intf-prefix-table**

app-intf-table is defined as the following:

;defines logical network interfaces, an attachment to a PORT name

;

;Status: stable

key = INTF_TABLE:ifname

if_mtu = 1\*4DIGIT ; MTU for the interface

VRF_NAME = 1\*64VCHAR ;

app-intf-prefix-table is defined as the following:

;defines logical network interfaces with IP-prefix, an attachment to a PORT and
list of 0 or more ip prefixes;

;Status: stable

key = INTF_TABLE:ifname:IPprefix ; an instance of this key will be repeated for
each prefix

IPprefix = IPv4prefix / IPv6prefix ; an instance of this key/value pair will be
repeated for each prefix

scope = "global" / "local" ; local is an interface visible on this localhost
only

if_mtu = 1\*4DIGIT ; MTU for the interface （move to INTF_TABLE:ifname table）

family = "IPv4" / "IPv6" ; address family

1.  **Adding VRF key to app-route-table key list**

;Stores a list of routes

;Status: Mandatory

key = ROUTE_TABLE:VRF_NAME:prefix ;

nexthop = \*prefix, ;IP addresses separated “,” (empty indicates no gateway)

intf = ifindex? PORT_TABLE.key ; zero or more separated by “,” (zero indicates
no interface)

blackhole = BIT ; Set to 1 if this route is a blackhole (or null0)

Since global vrf name is null, global vrf key will becomes ROUTE_TABLE:prefix.

 VrfMgrd 
---------

>   Listening VRF related configuration in config_db such as VRF
>   creation/deletion, VRF binding to any interface. Once detected, update
>   kernel using iproute2 CLIs and write VRF information to app-VRF-table and
>   app-intf-table.

>   VrfMgrd process will be placed in swss docker. In case of “swss restart”,
>   VRF device will be still retained in kernel. When VrfMgrd starts up it
>   querys all master device from kernel and clean up all vrf related device and
>   restore vrf device per configdb.

>   VRFOrch has three member routerCnt , neighCnt and rifCnt which record VRF
>   related route number , neigh number and rif number.VRFOrch is added to
>   RouteOrch , NeighOrch and intfsOrch member to update routeCnt , neighCnt and
>   rifCnt.

>   When  VRFOrch receives vrf-delete event VRF object won’t  be deleted until
>   routerCnt  ,neighCnt and rifCnt  is decreased to zero.

>   When device binds to specified VRF, the ip address of slave device will be
>   removed and kernel will delete all neigh associated slave device.

 fpmsyncd changes
-----------------

with added VRF ID, fpmsyncd can use rtnl_route_get_table to acquire tableid.
Hence can send VRF routes further down. The messages from FRR has nh(next hop)
information which contain further information about (nexthop_ipaddress and
interface index)，tableid can be derived from the interface index.

Fpmsyncd can build \<tableid, vrf_name\> pairs using rtnetlink api.

 adding vrforch 
----------------

>   Monitorying app-VRF-table，Using sai_create_virtual_router_fn or

>   sai_remove_virtual_router_fn defined in saivirtualrouter.h to track
>   (VR，VRF) creation/deletion.and save (vrf_name, vrf-vid) pairs.

intfsorch changes
-----------------

>   Adding following logics:

-   adding vrforch as one member to intfsorch

-   intfsorch monitors both app-intf-table和app-intf-prefix-table，when
    app-intf-table has changes，handle updating vrf attribute on
    routerintf，request vrforch for tableid/vrf-id .

    1.  routeorch changes

Adding the following logics:

-   Adding vrforch member to routesorch

-   Once app-route-table has new udpate，get tableid from vrforch for route
    add/delete.

>   When query nexthop，keys now are (tableid, ipaddress)，tableid of nexthop
>   can be acquired using nexthop interface.

neighorch changes
-----------------

Adding the following logic:

-   the Key of NextHop now is changed from only ipaddress to a pair of
    (ipaddress, interface_name)

    1.  TODO

-   (Mirror， tunnel，PBR) to be designed in future.

CLI
===

>   VRF configureation can be done via SONiC build-in CLIs (to implement)

>   sonic CLIs are proposed as followings：

>   Config vrf \<add \| del\> \<VRF-name\>

>   Config vrf \<VRF-name\> member \<add \| del\> interface \<interface-name\>

>   Config vrf \<VRF-name\> global-lookup \<enable \| disable\>

>   Config route add [vrf \<vrf-name\>] prefix \<route_prefix/mask\> nexthop
>   [vrf \<vrf-name\>] \<nh\>

>   Config route del [vrf \<vrf-name\>] prefix \<route_prefix/mask\> nexthop
>   [vrf \<vrf-name\>] \<nh\>

Impact to other service after import VRF feature
================================================

>   For apps that don't care VRF they don't need to modify after sonic import
>   VRF.

>   Linux supports “VRF-global” socket from kernel 4.5.  The socket listened by
>   service are VRF-global by default unless the VRF instance is specified. It
>   means the service can accept connection over all VRFs. Connected sockets are
>   bound to the VRF domain in which the connection originates.

>   Take teamd as an example. Teamd is layer2 apps and it doesn't care VRF
>   attribute. Teamd code is as followed with removing some exceptional code. It
>   uses VRF-global socket for every port-channel member port.

>   {

>                   sock = socket(PF_PACKET, type, 0);

>                   err = attach_filter(sock, fprog, alt_fprog);

>                   memset(&ll_my, 0, sizeof(ll_my));

>                   ll_my.sll_family = AF_PACKET;

>                   ll_my.sll_ifindex = ifindex;

>                   ll_my.sll_protocol = family;

>                   ret = bind(sock, (struct sockaddr \*) &ll_my,
>   sizeof(ll_my));

>   }

>   Put port-channel in different VRF instance doesn't affect vrf-global socket
>   to receive lacp protocol packet from member port. So  teamd doesn't  need to
>   be modified or restarted for VRF binding event.

>   For layer 3 apps such as snmpd or ntpd they are using vrf-global socket too.
>   So  they are vrf-transparent too.
