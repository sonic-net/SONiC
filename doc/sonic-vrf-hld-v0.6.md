# SONiC VRF support design spec draft

Table of Contents
<!-- TOC -->

- [SONiC VRF support design spec draft](#sonic-vrf-support-design-spec-draft)
  - [Document History](#document-history)
  - [Abbreviations](#abbreviations)
  - [VRF feature Requirement](#vrf-feature-requirement)
  - [Dependencies](#dependencies)
  - [SONiC system diagram for VRF](#sonic-system-diagram-for-vrf)
  - [The schema changes](#the-schema-changes)
  - [Agent changes](#agent-changes)
    - [vrfmgrd changes](#vrfmgrd-changes)
    - [intfsmgrd changes](#intfsmgrd-changes)
    - [fpmsyncd changes](#fpmsyncd-changes)
    - [vrforch changes](#vrforch-changes)
    - [intfsorch changes](#intfsorch-changes)
    - [routeorch changes](#routeorch-changes)
    - [neighorch changes](#neighorch-changes)
    - [TODO](#todo)
  - [CLI](#cli)
  - [user scenarios](#user-scenarios)
    - [Configure ip address without vrf feature](#configure-ip-address-without-vrf-feature)
    - [Add VRF and bind/unbind interfaces to this VRF](#add-vrf-and-bindunbind-interfaces-to-this-vrf)
    - [Delete vrf](#delete-vrf)
    - [Another CLI implementation proposal](#another-cli-implementation-proposal)
  - [Impact to other service after import VRF feature](#impact-to-other-service-after-import-vrf-feature)
  - [Progress](#progress)

<!-- /TOC -->

## Document History

| Version | Date       | Author       | Description                                      |
|---------|------------|--------------|--------------------------------------------------|
| v.01    | 06/07/2018 | Shine/Andrew | Initial version from nephos                      |
| v.02    | 06/08/2018 | Shine        | Revised per Guohan/prince(MSFT) opinion          |
| v.03    | 09/18/2018 | Guohan       | Format document                                  |
| v.04    | 01/17/2019 | shine/jeffrey| Update after Sonic community review              |
| v.05    | 04/17/2019 | Xin/Prince   | Update the status                                |
| v.06    | 05/09/2019 | Shine/Tyler/Jeffrey  | Some description correction and format adjustment                  |

## Abbreviations

| **Term** | **Definition**                                                                                                                                  |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| VRF      | Virtual routing forwarding                                                                                                                      |
| FRR      | FRRouting is an IP routing protocol suite for Linux and Unix platforms which includes protocol daemons for BGP, IS-IS, LDP, OSPF, PIM, and RIP  |
| Quagga   | Open IP routing protocol suite                                                                                                                  |
| RIB      | Routing Information Base                                                                                                                        |
| PBR      | Policy based routing         |

## VRF feature Requirement

1. Add or Delete VRF instance
2. Bind L3 interface to a VRF.

    L3 interface includes port interface, vlan interface, LAG interface and loopback interface.
3. Static IP route with VRF
4. Enable BGP VRF aware in SONiC
5. Fallback lookup.

   The fallback feature is very useful for specify VRF user to access internet through global/main route which is defined by RFC4364. Some enterprise user still use this to access internet on vpn environment.
6. VRF route leaking between VRFs.

    In this release, supporting requirement 5) and 6) are not supported. See next section for details.

Note: linux kernel use VRF master device to support VRF and it supports admin
      up/down on VRF master device. But we don't plan to support VRF level up/down state on SONIC.

## Dependencies

VRF feature needs the following software package/upgrade

1. Linux kernel 4.9

Linux Kernel 4.9 support generic IP VRF with L3 master net device. Every L3
master net device has its own FIB. The name of the master device is the
VRF's name. Real network interface can join the VRF by becoming the slave of
the master net device.

Application can get creation or deletion event of VRF master device via RTNETLINK,
as well as information about slave net device joining a VRF.

Linux kernel supports VRF forwarding using PBR scheme. It will fall to main
routing table to check do IP lookup. VRF also can have its own default network
instruction in case VRF lookup fails.

2. FRRouting is needed to support BGP VRF aware routing.

3. IProute2 version should be ss161212 or later to support iproute2 CLIs to
    configure the switch.

Example of using iproute2:

```bash
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

4. SAI VRF support

SAI right now does not seem to have VRF concept, it does have VR.

We propose to implement VR as "virtual router" and VRF as "virtual router
forwarding"

VR is defined as a logical routing system. VRF is defined as forwarding
domain within a VR.

As this stage, we assume one VR per system. Only implement VRFs within this VR.

Accordingly, we need to add vrf_id to sai_Route_entry and add vrf attribute
to sai_routeInterface object.

An alternative method is using VR as VRF, this requires to add two attribution
to VR object to support Requirement 5) (fallback lookup). SAI community has 
decided that take VR as VRF. So in this implement release we use VR object as VRF.
Here are the new flags we propose to add in the SAI interface:

```jason
/*
 * @brief if it is global vrf
 *
 * @type bool
 * @flags CREATE_AND_SET
 * @default true
 */
 SAI_VIRTUAL_ROUTER_ATTR_GLOBAL

/*
 * @brief continue to do global fib lookup while current vrf fib lookup
 *  missed
 *
 * @type bool
 * @flags CREATE_AND_SET
 * @default false
 */
 SAI_VIRTUAL_ROUTER_ATTR_FALLBACK
```

## SONiC system diagram for VRF

The following is high level diagram of modules with VRF support.
![](https://github.com/Azure/SONiC/blob/f2ebba476b4ef364b13b7980c2fe01e8929c71e6/images/vrf_hld/VRF_HIGH_LEVEL_DIAGRAM.png)

## The schema changes

1. Adding VRF related configuration in config_db.json.
Note "fallback" keyword is not supported in this release.

```jason
"VRF": {
    "Vrf-blue": {
        "fallback":"true" //enable global fib lookup while vrf fib lookup missed
    },
    "Vrf-red":{
        "fallback": "true"
    },
    "Vrf-yellow":{
        "fallback":"false" //disable global fib lookup while vrf fib lookup missed
    }
},

"INTERFACE":{
    "Ethernet0":{
        "vrf_name":"Vrf-blue"  // vrf_name must start with "Vrf" prefix
    },
    "Ethernet1":{
        "vrf_name":"Vrf-red"
    },
    "Ethernet2":{}, // it means this interface belongs to global vrf
    "Ethernet0|11.11.11.1/24": {},
    "Ethernet0|12.12.12.1/24": {},
    "Ethernet1|12.12.12.1/24": {},
    "Ethernet2|13.13.13.1/24": {}
},

"LOOPBACK_INTERFACE":{
    "Loopback0":{
        "vrf_name":"Vrf-yellow"
    },
    "Loopback0|14.14.14.1/32":{}
},

"VLAN_INTERFACE": {
    "Vlan100":{
        "vrf_name":"Vrf-blue"
    },
    "Vlan100|15.15.15.1/24": {}
},

"PORTCHANNEL_INTERFACE":{
    "Portchannel0":{
        "vrf_name":"Vrf-yellow"
    },
    "Portchannel0|16.16.16.1/24":{}
}

```

Logically IP address configuration must be processed after interface binding to vrf is processed. In intfmgrd/intfOrch process intf-bind-vrf event must be handled before IP address event.
So interface-name entry in config_db.json is necessary even user doesn't use VRF feature. e.g. `"Ethernet2":{}` in the above example configuration. For version upgrade compatibility we plan to add a script, this script will convert old config_db.json to new config_db.json at bootup, and the new config_db.json contains the interface-name entry for interfaces associated in the global VRF table.

Another way to solve the above dependency is to provide this syntax in the config_db.json:

```jason
"INTERFACE":{
    "Ethernet2":{
        "vrf_name":"Vrf-blue"  // vrf_name must start with "Vrf" prefix
    },
    "Ethernet2|Vrf-blue|13.13.13.1/24": {}
},
```

Here "Vrf-blue" is part of the IP address configuration of the interface. It can remove intf-bind-vrf event and ip-address event sequence dependency. But it will cause vrf info verbose and incompatibility with the existing SONiC parser, so this approach will not be implemented.

2. **Adding a VRF_TABLE** in APP_DB

```jason
;defines virtual routing forward table
;
;Status: stable

key = VRF_TABLE:vrf_name ;
fallback = "true"/"false"
```

3. **Add 2-segment key entry** support in APP-intf-table

There are two reasons why adding 2-segment key entry in interface table.

1. Multiple ip addresses can be configured on one interface. So we put common attribute of interface
   into app-intf-table and keep ip-prefix specific attribute on app-intf-prefix-table.
2. Interface can be put to specific VRF before ip address is configured on it.

app-intf-table is defined as the following:

```json
;defines logical network interfaces, an attachment to a PORT name
;
;Status: stable

key = INTF_TABLE:ifname
mtu = 1\*4DIGIT ; MTU for the interface
VRF_NAME = 1\*64VCHAR ;
```

app-intf-prefix-table is defined as the following:

```json
;defines logical network interfaces with IP-prefix, an attachment to a PORT and
list of 0 or more ip prefixes;

;Status: stable
key = INTF_TABLE:ifname:IPprefix ; an instance of this key will be repeated for each prefix
IPprefix = IPv4prefix / IPv6prefix ; an instance of this key/value pair will be repeated for each prefix
scope = "global" / "local" ; local is an interface visible on this localhost only
mtu = 1\*4DIGIT ; MTU for the interface  (move to INTF_TABLE:ifname table)
family = "IPv4" / "IPv6" ; address family
```

4. **Adding VRF key to app-route-table key list**

```jason
;Stores a list of routes
;Status: Mandatory

key = ROUTE_TABLE:vrf_name:prefix ;
nexthop = \*prefix, ;IP addresses separated "," (empty indicates no gateway)
intf = ifindex? PORT_TABLE.key ; zero or more separated by "," (zero indicates no interface)
blackhole = BIT ; Set to 1 if this route is a blackhole (or null0)
```

Since global vrf name is null, global vrf key will becomes ROUTE_TABLE:prefix.
The non-global vrf_name must start with "Vrf" prefix. So it can differ from ipv6 address.

## Agent changes

### vrfmgrd changes

- Listening to VRF creation/deletion configuration in config_db. Once detected,
update kernel using iproute2 CLIs and write VRF information to app-VRF-table.

- When vrfmgrd receives VRF delete event it wont process the event till all the devices belonging to this VRF are unbound from the VRF.

- vrfmgrd process will be placed in swss docker. In case of swss docker warm reboot, since VRF device is still retained in kernel, when vrfmgrd starts up it will follow the required steps for warm reboot and take proper actions to recover the VRF system
state. If it's cold reboot, vrfmgrd will query kernel to obtain all the VRF
interfaces and flush those interfaces.

### intfsmgrd changes

- Listening to interface binding to specific VRF configuration in config_db. Once
detected, update kernel using iproute2 CLIs and write VRF information to app-intf-table.

- Listening to interface ip address configuration in config_db. Once detected , update kernel and write ip address information to app-intf-prefix-table.

Note: if ip address event arrives before vrf-binding event intfmgrd need to postpone ip-address handling until vrf-binding event processing is done. Since vrf-binding event is triggered by the entries of cfg-intf-table cfg-intf-table is necessary even user doesn't use VRF feature.

An alternative approach is to handle the two events similar to what Linux kernel is doing. e.g. if the IP address is configured in an interface first, it will be accepted. Later on when the interface is enslaved to a VRF, the IP address from the master FIB will be removed, and reprogrammed to the VRF table. But this approach is not currently supported in the SONiC infrastructure, and may have potential issues in BGP daemons and syncd/SAI if we implement it. So Now this approach is not supported.

### fpmsyncd changes

- fpmsyncd will add VRF support, it can use rtnl_route_get_table to get VRF table ID.
But with the current FRR implementation, this API returns the master devices' ifIndex for
this VRF. The VRF name of Prefix can be derived from ifindex.
- The key of app-route-table is "vrf_name:prefix".
- The route from FRR has nexthop information which contain nexthop_ipaddress and interface index. Nexthop interface contain vrf information. It is available for route-leak scenarios.

### vrforch changes

- Monitoring app-VRF-table, using sai_create_virtual_router_fn or
sai_remove_virtual_router_fn defined in saivirtualrouter.h to track (VR, VRF) creation/deletion and save (vrf_name, vrf-vid) pairs.
- When vrforch receives vrf-delete event for a given VRF, this VRF object will be deleted after routes,neighbors and rif interfaces related this VRF are removed.

### intfsorch changes

- add vrforch as a member of intfsorch
- intfsorch monitors interface tables.
  - When app-intf-table change, create/delete router interface with vrf attribute , retrieving VRF object ID from vrforch? updating the refcnt of vrforch.
  - When app-intf-prefix-table change, set/unset ip address on existing router interface.
  - seting ip address on rif should be done after router interface is created. Deleting router interface should be executed until all ip address on rif have been deleted.

### routeorch changes

- Adding vrforch as a member of routeorch
- Once app-route-table has new udpate, get VRF object ID from vrforch by vrf_name.
- Nexthop key is changed to ``(ipaddress, intf_name)`` pair from ``ipaddress``.
- The key of Nexthop group is the set of nexthop key.
- The value of routetable is changed to the set of ``(ipaddress, intf_name)`` pair from ``ipaddresses``
- Expanding single routetable to mutiple routetables with vrf-key

### neighorch changes

- the Key of Nexthop now is changed from only ipaddress to a pair of
    ``(ipaddress, intf_name)``.

### TODO

- (Mirror,tunnel,PBR) to be designed in future.

## CLI

VRF configuration can be done via SONiC Click CLIs framework In this release, new CLIs are proposed as following:

```bash
//create a VRF:
$ config vrf add [OPTIONS] <vrf_name>

//remove a VRF
$ config vrf del <vrf_name>

//create a router interface, optional
$ config interface <interface_name> router-interface add

//remove a router interface, optional
$ config interface <interface_name> router-interface del

//bind an interface to a VRF
$ config interface <interface_name> vrf bind <vrf_name>

//unbind an interface from a VRF
$ config interface <interface_name> vrf unbind

// show attributes for a given vrf
$ show vrf [<vrf_name>]

// show the list of router interfaces
$ show router-interface

//add IP address to an interface.  The command already exists in SONiC, but will be enhanced
$ config interface <interface_name> ip add <ip_addr/mask>

//remove an IP address from an interface. The command already exists in SONiC, but will be enhanced.
$ config interface <interface_name> ip remove <ip_addr/mask>

//add a prefix to a VRF
$ config route add [vrf <vrf_name>] prefix <route_prefix/mask> nexthop <[vrf <vrf_name>] <ip> | dev <dev_name>>

//remove a prefix from a VRF
$ config route del [vrf <vrf_name>] prefix <route_prefix/mask> nexthop <[vrf <vrf_name>] <ip> | dev <dev_name>>

//show prefixes in a given VRF. The existing command is enhanced to take VRF as the key
$ show ip route [vrf < all | vrf_name>]

```

## user scenarios

Here are some of the use cases and configuration steps.

### Configure ip address without vrf feature

If a user does not care about VRF configuration, it can simply use this command to configure the IP address of an interface. This IP address is attached to the main FIB table.

Lets use Ethernet0 as an example in this document.

```bash

$ config interface Ethernet0 ip add 1.1.1.1/24

```

This command is enhanced to do the following:

- Read info from config_db
- Check if interface Ethernet0 exists in the db.
  - If not, create Ethernet0 router interface, and attach to global VRF. Then, add the corresponding IP address to config_db.
  - If yes, add the corresponding IP address to config_db.

To remove IP address from an interface:

```bash

$ config interface Ethernet0 ip remove 1.1.1.1/24

```

This command is enhanced to do the following:

- Read info from config_db
- Remove IP address from config_db.
- Check other IP address(es) on Ethernet0.
  - If other IP addresses exist in db, no further action is taken.
  - If no other IP address exists, remove Ethernet0 router interface.

### Add VRF and bind/unbind interfaces to this VRF

In this case, user wants to configure a VRF “Vrf-blue”, with interfaces attached to this VRF. Following are the steps:

```bash

$ config vrf add Vrf-blue
$ config interface Ethernet0 vrf bind Vrf-blue

```

bind command will do the following:

- Read info from config_db
- Check if IP address exists for Ethernet0. If yes, delete the IP from interface
- Bind the interface to Vrf-blue (it will eventually create Ethernet0 router interface)

```bash

$ config interface Ethernet0 ip add 1.1.1.1/24

```

This command will do the following:

- Read config_db
- check if interface Ethernet0 exists in db.
  - If no, create Ethernet0 router interface, attach to the VRF. Then, add IP address to config_db.
  - If yes, just add IP address to config_db

To unbind an interface from VRF:

```

$ config interface Ethernet0 vrf unbind

```

This command will do the following:

- Read config_db
- check if IP address exists. If yes, delete all IP addresses from interface
- Delete all attributes, delete router interface(Ethernet0)

### Delete vrf

User wants to delete a VRF (Vrf-blue), here are the steps:

Current proposal:

```bash

$ show vrf Vrf-blue
This will to get interface list belonging to Vrf-blue from app_db
$ config interface Ethernet0 ip remove 1.1.1.1/24
This will remove all IP addresses from the interfaces belonging to the VRF.
$ config interface Ethernet0 vrf unbind
This will unbind all interfaces from this VRF
$ config vrf del Vrf-blue
This command will delete the VRF.

```

To simplify the user experience, we can combine the above commands to create one single command, similar to the iprotue2 command:`# ip link del Vrf-blue`

```bash

$ config vrf del Vrf-blue

```

- get interface list belonging to Vrf-blue from app_db
- delete interface(s) IP addresses
- unbind interfaces(s) from Vrf-blue
- del Vrf-blue

### Another CLI implementation proposal

For the VRF configuration steps, another proposal is discussed as well. That is for each operational step, user must execute a CLI to trigger the operation, there is no implicit extra operation taken inside each CLI command.

For example, to configure an IP address in an interface, it takes those steps:

```bash

//create a router interface. This will create a router interface object, indicating a global VRF used for this interface
$ config interface Ethernet36 router-interface add
// add IP address to the interface
$ config interface Ethernet36 ip add 1.1.1.1/24
Now this command will only add IP address to the config_db, it will not implicitly create a router interface object.

```

With this proposal, here is the map between the CLI command and the corresponding function:

CLIs | corresponding table entry on config-db
---------|----------
 config vrf | "VRF\|Vrf-blue"
 config interface router-interface | "INTERFACE\|Ethernet0"
 config interface vrf | "INTERFACE\|Ethernet0" attribute "vrf_name"
 config interface ip | "INTERFACE\|Ethernet0\|1.1.1.1/24"

## Impact to other service after import VRF feature

For apps that don't care VRF they don't need to modify after sonic import VRF.

Linux supports "VRF-global" socket from kernel 4.5.  The socket listened by
service are VRF-global by default unless the VRF instance is specified. It
means the service can accept connection over all VRFs. Connected sockets are
bound to the VRF domain in which the connection originates.

Take teamd as an example. Teamd is layer2 apps and it doesn't care VRF
attribute. Sample Teamd code is shown below. It
uses VRF-global socket for every port-channel member port.

```c
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

## Progress

In the diagram, fpmsyncd, vrfmgrd, intfsmgrd, intfsorch are checked into the master branch. All the other components are open.
