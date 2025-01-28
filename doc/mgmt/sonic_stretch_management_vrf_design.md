# SONiC Management VRF Design Document - 201911 Release

## Introduction
Management VRF is a subset of Virtual Routing and Forwarding, and provides a separation between the management network traffic and the data plane network traffic. For all VRFs the main routing table is the default table for all data plane ports. With management VRF a second routing table, mgmt, is used for routing through the management ethernet ports of the switch. 
This design document is applicable for 201911 release of SONiC where it uses the debian stretch kernel.
A new design document will be written for 202006 release of SONiC that uses the debian Buster kernel.

The following design for Management VRF uses the l3mdev (with CGROUPS) approach for implementing management VRF on SONiC; refer to [design comparison](#design_comparison) for trade-offs of that approach vs. namespace-based design.  
 
## Requirements
| Req. No | Description                                                                                                | Priority | Comments |
|---:     |---                                                                                                         |---       |---       |
| 1       | Develop and implement a separate Management VRF that provide management plane and Data Plane Isolation
| 2       | Management VRF should be associated with a separate L3 Routing table and the management interface
| 3       | Management VRF and Default VRF should support IP services like `ping` and `traceroute` in its context
| 4       | Management VRF should provide the ability to be polled via SNMP both via Default VRF and Management VRF
| 5       | Management VRF will provide the ability to send SNMP traps both via the Management VRF and Data Network
| 7       | Dhcp Relay  - Required on Default VRF support
| 8       | Dhcp Client - Required on both default VRF and management VRF
| 9       | Enable SSH services to run in the Management VRF context and Default VRF context
| 10      | Enable TFTP services to run in the Management VRF context and Default VRF context
| 11      | Management VRF should support NTP services in its context
| 12      | Management VRF and Default VRF should support `wget`, `cURL` and HTTPS services
| 13      | Management VRF should support `apt-get` package managers in the Management VRF context
| 14      | Management VRF will provide TACACS+ support

The Scope of this design document is only limited to management VRF. 

## Traffic Flow 
### Terminating On The Switch
IP packets arriving on the switch will be associated to a VRF, based on the incoming port association. All packets coming via mgmt port (`eth0`) are associated to management VRF, and all packets coming to Front Panel Ports (FPP) are associated with default VRF and treated as data traffic. Packet forwarding is based on the corresponding routing table lookup as follows.

1. Packet processing for management traffic coming via mgmt port(s) will be based on management VRF routing table.
   1. If the destination IP matches the management port's IP address, packet is accepted and handed over to application. All IP application services are supported as listed in Table 1.
   2. If the destination IP does not match the management port's IP,  packet is dropped.
2. Packet processing for data traffic coming via front-panel ports will be based on default routing table.
   1. If the destination IP matches system's IP (any IP address that is configured for any of the front-panel ports or for any L3 Vlan interfaces), packet is accepted and handed over to application. All IP application services are supported as listed in Table 1.
   2. If the destination IP does not match any of the system's IP addresses, packet will be routed via the front-panel ports using the default routing table. 

Note: Transit traffic will never be forwarded between default and management VRF and vice-versa.

### Originating On The Switch
All switch-originated traffic will be based on the VRF on which the applications are running. By default all application will use the default routing table unless explictly mentioned to use management VRF. Applications like ping, traceroute has option to specify which interface (VRF) to use while sending packets out and hence they work on both default VRF & management VRF. The design approach for each application is explained in later sections.

## Design
L3 Master Device (l3mdev) is based on L3 domains that correlate to a specific FIB table. Network interfaces are enslaved to an l3mdev device uniquely associating those interfaces with an L3 domain. Packets going through devices enslaved to an l3mdev device use the FIB table configured for the device for routing, forwarding and addressing decisions. The key here is the enslavement only affects L3 decisions. 

With l3mdev on 4.9 kernel, VRFs are created and enslaved to an L3 Interface and services like ssh can be shared across VRFs thereby avoiding overhead of running multiple instances of IP services. i.e. entire network stack is not replicated using l3mdev.

Applications like Ping, Traceroute & DHCP client already operate on a per-interface (that maps to VRF) basis. E.g., Ping accepts `-I` to specify the interface in which the ping should happen; DHCP client is enabled on a per-interface basis; hence, no enhancement is required in those application packages to run them on the required VRF. 

## Implementation

Implementation of l3mdev (with CGROUPS) based solution involves the following key design points.
1. Management VRF Creation
2. Applications/services to work on both management network and data network.

### Management VRF Creation
#### Initialization Sequence & Default Behavior
This section describes the default behavior and configuration of management VRF for static IP and dhcp scenarios. After upgrading to this management VRF supported SONiC image, the binary boots in normal mode with no management VRF created. Customers can either continue to operate in normal mode without any management VRF, or, they can run a command to configure/enable management VRF. 


Users can either use the config command "config vrf add mgmt", OR, users can add the MGMT_VRF_CONFIG tag with mgmtVrfEnabled as true in config_db.json (as given below) and load the same.


```
"MGMT_INTERFACE": {
    "eth0|10.11.150.19/24": {
        "gwaddr": "10.11.150.1"
        "vrfname": "mgmt"
     }
}
    "MGMT_VRF_CONFIG": {
        "vrf_global": {
            "mgmtVrfEnabled": "true"
        }
    },

```

When the config CLI command is used, configuration is loaded into the running config_db and then two services, viz, "interfaces-config", "ntp", are restarted.
When config is directly loaded using "config load" without using CLI command, users should manually restart these services as follows.

```
service ntp stop  - Stop the NTP running in default VRF context.
systemctl restart interfaces-config - This will do the required backend work to create management VRF and attach eth0 to management VRF.
service ntp start - Start the NTP service, which will internally execute the ntp daemon inside management VRF.
```


#### Configuration Sequence

##### Management VRF create configuration sequence
When the "config vrf add mgmt" CLI command is executed, following sequence of things happen in the backend.

1. set the mgmtVrfEnabled to true inside MGMT_VRF_CONFIG in running configuration.

2. Restart the "interfaces-config" service.
   (a) This service first does "ifdown --force eth0" where it will execute all the commands specified in the already existing "/etc/network/interfaces" file. 
       For example, it will execute the command "down ip route delete default via <def_gw_ip> dev eth0 table default", which will delete the existing default route from the routing table "default". 
       Similarly, it deletes the route related to directly connected network that corresponds to the management IP address. Note that these rules are already existing even without management vrf implementation.
   (b) It then regenerates the management VRF specific /etc/network/interfaces file as per the requriement 
   (c) It then restarts the "networking" service (explained in next point) which will bring up the management VRF. 

   As part of management vrf implementation, "interfaces.j2" file has been modified to create the management vrf specific "/etc/network/interfaces" file. The generated file is given below for reference.

```  
auto mgmt
iface mgmt
    vrf-table 5000

auto lo
iface lo inet loopback

# The loopback network interface for mgmt VRF that is required for applications  
like NTP
    up ip link add lo-m type dummy
    up ip addr add 127.0.0.1/8 dev lo-m
    up ip link set lo-m up
    up ip link set dev lo-m master mgmt

# The management network interface
auto eth0
iface eth0 inet static
    address 100.104.47.74
    netmask 255.255.255.0
    vrf mgmt
    up ip -4 route add default via 100.104.47.254 dev eth0 table 5000 metric 201
    up cgcreate -g l3mdev:mgmt
    up cgset -r l3mdev.master-device=mgmt mgmt

```  

3. As part of the "networking" service restart sequence, this modified /etc/network/interfaces will be run using "ifdown2" internally by linux where each of the new interfaces ("mgmt" and "lo-m") are created.
   A new CGROUP "l3mdev:mgmt" is created and set as master device and made UP.
   An interface by name "mgmt" is created (equivalent to `ip link add dev mgmt type vrf table 5000` and  `ip link set dev mgmt up`) and a dummy loopback interface lo-m is also created.
   The management interface "eth0" is also enslaved to the VRF device "mgmt" (equivalent to `ip link set dev eth0 master mgmt`).
   vrf-table ID 5000 is used for management VRF routing table.
   If a default route was already present in default VRF, it is added to the new vrf table 5000. This is done when the eth0 interface comes up. 
   A dummy loopback interface "lo-m" is also created and enslaved to the "mgmt" master device. This is required for NTP commands like "ntpq" that expects a loopback interface for internal communication. Since the "lo" interface cannot be moved to management VRF ("lo" interface is required in default VRF for all internal communications), this new lo-m is created.


##### Management VRF delete configuration sequence
When the "config vrf del mgmt" CLI command is executed, following sequence of things happen in the backend.

1. set the mgmtVrfEnabled to "false" inside MGMT_VRF_CONFIG in running configuration.

2. Restart the "interfaces-config" service.
   (a) This service first does "ifdown --force eth0" where it will execute all the commands specified in the already existing management VRF specific "/etc/network/interfaces" file. 
       For example, it will execute the command "down ip route delete default via <def_gw_ip> dev eth0 table 5000", which will delete the existing default route from the routing table "5000" that corresponds to management VRF. 
       Similarly, it deletes the route related to directly connected network that corresponds to the management IP address. Note that these rules are same as the rules that were already existing even without management VRF implementation; the only difference is the routing table name/ID.
       It also deletes the CGROUP "l3mdev:mgmt" using the command "cgdelete -g l3mdev:mgmt".
   (b) It then regenerates the management VRF specific /etc/network/interfaces file as per the requriement 
   (c) It then restarts the "networking" service (explained in next point) which will bring up the the system without management VRF. 

   As part of management vrf implementation, "interfaces.j2" file has been modified to delete the management vrf specific interfaces using the "/etc/network/interfaces" file. The default "/etc/network/interfaces" file is given below for reference.

```  
auto lo
iface lo inet loopback

# The management network interface
auto eth0
iface eth0 inet static
    address 100.104.47.74
    netmask 255.255.255.0
    up ip -4 route add default via 100.104.47.254 dev eth0 table default metric 201
```  

3. As part of the "networking" service restart sequence, this reverted back /etc/network/interfaces will be run using "ifdown2" internally by linux where each of the new interfaces ("lo" and "eth0") are created.
   The loopback interface "lo" and management interface "eth0" are created.
   If a default route was already present in management VRF, it is added to the "default" routing table which is part of default VRF. This is done when the eth0 interface comes up. 
   When networking service is restarted, it will first bring down all existing interfaces. As part of "lo" down, previously created interface "lo-m" that was used as part of management VRF will be deleted.

These management VRF changes are implemented in the pull request [PR2585](https://github.com/sonic-net/sonic-buildimage/pull/2585) 

#### Config Commands

mVRF can be enabled using config vrf add mgmt and deleted using config vrf del mgmt. One more none management VRF commands are also added to add and remove IP address for management interface(eth0). 
```
config vrf add mgmt - This command is to create management VRF and move eth0 to mvrf.
config vrf del mgmt - This command is to delete the management VRF and move back eth0 to default VRF.
config interface eth0 ip add ip/mask gatewayIP - This command is to add IP address for management interface. 
config interface eth0 ip remove ip/mask - This command is to remove the IP address for management interface.
```

#### Show Commands

Show commands for management VRF are added which displays the Linux command output, will update show command display after concluding what would be the
output for the show commands.
```
show mgmt-vrf - This command displays the management VRF enabled status and the interfaces that are bound to mvrf.
show mgmt-vrf route - This command displays the routes present in management VRF routing table.
show management_interface address - This command displays the IP addresses configured for the management interface eth0.
```

Following are the example output from these show commands.

```
root@sonic:/etc/init.d# show mgmt-vrf 

ManagementVRF : Enabled

Management VRF interfaces in Linux:
348: mgmt: <NOARP,MASTER,UP,LOWER_UP> mtu 65536 qdisc noqueue state UP mode DEFAULT group default qlen 1000
    link/ether f2:2a:d9:bc:e8:f0 brd ff:ff:ff:ff:ff:ff
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master mgmt state UP mode DEFAULT group default qlen 1000
    link/ether 4c:76:25:f4:f9:f3 brd ff:ff:ff:ff:ff:ff
350: lo-m: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue master mgmt state UNKNOWN mode DEFAULT group default qlen 1000
    link/ether b2:4c:c6:f3:e9:92 brd ff:ff:ff:ff:ff:ff
root@sonic:/etc/init.d#
```


```
root@sonic:/etc/init.d# show mgmt-vrf routes

Routes in Management VRF Routing Table:
default via 10.16.210.254 dev eth0 metric 201 
broadcast 10.16.210.0 dev eth0 proto kernel scope link src 10.16.210.75 
10.16.210.0/24 dev eth0 proto kernel scope link src 10.16.210.75 
local 10.16.210.75 dev eth0 proto kernel scope host src 10.16.210.75 
broadcast 10.16.210.255 dev eth0 proto kernel scope link src 10.16.210.75 
broadcast 127.0.0.0 dev lo-m proto kernel scope link src 127.0.0.1 
127.0.0.0/8 dev lo-m proto kernel scope link src 127.0.0.1 
local 127.0.0.1 dev lo-m proto kernel scope host src 127.0.0.1 
broadcast 127.255.255.255 dev lo-m proto kernel scope link src 127.0.0.1 
root@sonic:/etc/init.d#
```


```
root@sonic:/etc/init.d# show management_interface address 
Management IP address = 10.16.210.75/24
Management NetWork Default Gateway = 10.16.210.254
root@sonic:/etc/init.d#
```

These CLI commands are implemented as part of the pull request [PR463](https://github.com/sonic-net/sonic-utilities/pull/463)

### IP Application Design
This section explains the behavior of each application on the default VRF and management VRF. Application functionality differs based on whether the application is used to connect to the application daemons running in the device or the application is triggered from the device.

#### Application Daemons In The Device  
##### TCP Application Daemons  
Linux kernel has got the flag tcp_l3mdev_accept which is required for enabling the TCP applications to receive and process packets from both data VRF and management VRF. By default, this flag is already enabled. With this flag enabled, TCP is capable of accepting the incoming connections that internally binds the incoming interface to the connection. i.e. When connection request arrives via the front-panel ports, TCP accepts the connection via the front-panel port; when connect request arrives via the management port (eth0), it accepts via the management port. Example: sshd, ftpd, etc., No changes are required in these deamons to make them work on both management VRF and default VRF.

##### UDP Application Daemons
Linux 4.9 does not support `udp_l3mdev_accept`; corresponding patch is back ported to SONiC Linux 4.9. With this patch, UDP applications will be able to receive and process packets from both data VRF and management VRF. UDP being a connectionless protocol, these is no concept of accepting the connection through the same incoming port (VRF) and hence UDP applications will not be able to specify the interface through which the reply has to be sent. i.e. When UDP applications send a reply reply packet, there is no reference to the port in which the request packet had arrived. Hence the Linux stack will try to route this packet via default routing table, even if request packet had arrived via management port. Such UDP application daemon code needs to be modified to use the incoming port reference and use it for sending replies via the same VRF through which the request had arrived.

##### IP Application Daemons
Most IP applications (like PING) always have the incoming port/VRF association with the reply packet and hence they will continue to work without any modification. 

#### Applications Originating From the Device
Applications originating from the device need to know the VRF in which it has to run.  
They should use "cgexec -g l3mdev:mgmt" as prefix before each command to run the application in management VRF.


##### SSH
1. SSH to the device - Works with both management and default VRF setting the tcp_l3mdev_accept=1 and no changes are required to sshd.
2. SSH from the device - Need to use "cgexec -g l3mdev:mgmt" as prefix before the SSH command. 
Example for SSH: 
cgexec -g l3mdev:mgmt ssh 10.1.2.3  

##### Ping
1. Ping to device -  Works with both management and default VRF without any change.
2. Ping from the device - Works for default VRF as usual. For pings via management interface, use "cgexec -g l3mdev:mgmt" as prefix.

  Example ping command:
```
   // default VRF ping command
   ping x.x.x.x

   // management VRF ping command
   cgexec -g l3mdev:mgmt x.x.x.x
```

##### Traceroute
1. traceroute to device - Works for default VRF and management VRF without any change.
2. traceRoute from the device - Works for default VRF as usual. For traceroute via management interface, use "cgexec -g l3mdev:mgmt" as prefix.

  Example Traceroute commands
```
   // default VRF traceroute command
   traceroute x.x.x.x

   // management VRF traceroute command
   cgexec -g l3mdev:mgmt x.x.x.x
```   

##### TACACS
TACACS is a library function that is used by applications like SSHD to authenticate the users. When users connect to the device using SSH and if the "aaa" authentication is configured to use the tacacs+, it is expected that device shall connect to the tacacs+ server via management port and authenticate the user. TACACS implementation contains two sub-modules, viz, NSS and PAM. These module codes is enhanced to support an additional parameter "--use-mgmt-vrf" while configuring the tacacs+ server IP address. When user specifies the --use-mgmt-vrf as part of "config tacacs add --use-mgmt-vrf <tacacs_server_ip>" command, this is passed as an additional parameter to the config_db's TACPLUS_SERVER tag. This additional parameter is read using the files/image_config/hostcfgd/common-auth-sonic.j2 & files/image_config/hostcfgd/tacplus_nss.conf.j2 and the information is added to the tacplus configuration files /etc/tacplus_nss.conf and /etc/pam.d/common-auth-sonic. When SSHD uses the tacacs+ authentication using the API "pam_authenticate", enhanced tacacs+ code shall read the additional configuration related to vrfname "mgmt" associated with the tacac+ server and then it uses SO_BINDTODEVICE to attach the socket to the "mgmt" interface. Once if the socket is attached to "mgmt" interface, all tacacs+ traffic shall be routed via the management interface.

Code changes required in PAM & NSS are completed. [PR2217](https://github.com/sonic-net/sonic-buildimage/pull/2217) & [PR346](https://github.com/sonic-net/sonic-utilities/pull/346) address the same.
As explained in the PR, tacacs PAM & NSS module had been enhanced to parse and process the "vrfname" and to setsockopt using SO_BINDTODEVICE for "mgmt" interface.
Added an optional parameter "-m" (or --use-mgmt-vrf) for the "tacacs" command. The optional parameter "-m" used while configuring tacacs server results in configuring the DB with vrfname as "mgmt". Files "files/image_config/hostcfgd/common-auth-sonic.j2" and "files/image_config/hostcfgd/tacplus_nss_conf.j2" are modified to read this optional parameter and update the PAM & NSS configuration files "/etc/pam.d/common-auth" and "/etc/tacplus_nss.conf" respectively with the vrfname.
After enhancing the code for NSS in the file nss_tacplus.c for parsing the vrfname and passing it to the connect library function "tac_connect_single", git patch "0003-management-vrf-support.patch" was generated and checked in.
Similarly PAM code is also enhanced to parse and pass vrfname to the connect library function. PAM library code (libtac2) is also enhanced to do the actual SO_BINDTODEVICE in libtac/lib/connect.c for the "mgmt" vrfname. Git patch "0004-management-vrf-support.patch" was generated with all these PAM changes.
src/tacacs/Makefile is enhanced to use these enhanced patches for PAM & NSS.

```
root@sonic-z9264f-03:~# config tacacs add --use-mgmt-vrf 10.11.55.40
root@sonic-z9264f-03:~# config tacacs add -m 10.11.55.41
root@sonic-z9264f-03:~# show tacacs 
TACPLUS global auth_type pap (default)
TACPLUS global timeout 5 (default)
TACPLUS global passkey <EMPTY_STRING> (default)

TACPLUS_SERVER address 10.11.55.40
               priority 1
               tcp_port 49
               vrf mgmt

TACPLUS_SERVER address 10.11.55.41
               priority 1
               tcp_port 49
               vrf mgmt

```


##### cURL
1. cURL to device: cURL uses TCP and hence it is expected to work without any change.
2. cURL from device: Works for default VRF as usual. For cURL via management interface, use "cgexec -g l3mdev:mgmt" as prefix.

#### SNMP
1. snmp to the device: SNMP being an UDP application, Linux netsmp 5.7.3 patch for VRF support is patched with SONiC sources. [PR2608](https://github.com/sonic-net/sonic-buildimage/pull/2608) and [PR472](https://github.com/sonic-net/sonic-utilities/pull/472) contains the changes done for SNMP.
2. snmp traps from device: netsnmp 5.7.3 Linux patch has VRF support for traps. Conifuguration file needs to specify VRF name. Above mentioned PRs handle the required changes.

#### NTP  
When managmenet VRF is enabled, NTP application is restarted in the mvrf context by doing the following changes.
Debian contains the NTP package that has got the NTP initialization script file /etc/init.d/ntp that calls "start-stop-daemon" command which in turn starts the "ntpd" daemon as follows.
```
start-stop-daemon --start --quiet --oknodo --pidfile $PIDFILE --startas $DAEMON -- -p $PIDFILE $NTPD_OPTS
```
When management VRF is enabled, this "ntpd" daemon should be started using "cgexec" as follows.
```
cgexec -g l3mdev:mgmt start-stop-daemon --start --quiet --oknodo --pidfile $PIDFILE --startas $DAEMON -- -p $PIDFILE $NTPD_OPTS
```
Since this file "/etc/init.d/ntp" is part of the default NTP package from debian, this file is manually copied into sonic-buildimage (at files/image_config/ntp/ntp) and modified to handle the mvrf enable status. It is then copied into /etc/init.d/ntp along with this mvrf changes. Whenever a new version of NTP is added to SONiC, care must be taken to repeat this change as required.

In addtion to this change, NTP has got linux commands like "ntpq" which communicates with "ntpd" using the loopback IP address 127.0.0.1.
Hence, a dummy interface "lo-m" is created and enslaved into "mgmt" and configured with the IP address 127.0.0.1

These NTP changes are done as part of the pull request [PR3204](https://github.com/sonic-net/sonic-buildimage/pull/3204) 

Similarly, the "show ntp" command is also enhanced to use "cgexec -g l3mdev:mgmt" as explained in the [PR627](https://github.com/sonic-net/sonic-utilities/pull/627)
 
#### DHCP Client 
DHCP client gets the IP address for the management ports from the DHCP server, since it is enabled on a per interface the IP address is received automatically. 
DHCP Client had already been enhanced to execute a "vrf" script as part of exit-hook. 
This script does "no-op" when management VRF is not enabled (i.e. when eth0 is not in management vrf).
With the script, eth0 is placed in a vrf and on startup it will get an IP address via dhcp. 
IP address changes or gateway changes are correctly reflected.
[PR2348](https://github.com/sonic-net/sonic-buildimage/pull/2348) handles these changes.

#### DHCP Relay 
DHCP relay is expected to work via the default VRF. 
DHCP Relay shall receive the DHCP requests from servers via the front-panel ports and it will send it to DHCP server through front-panel ports. No code changes are reqiured.


#### DNS
DNS is expected to work in default VRF and management VRF without any change.
In general, applications like ping, traceroute are getting executed using "cgexec -g l3mdev:mgmt" prefix. 
When such processes run in mvrf context, all the internal library calls and the resultant sockets are also opened in mvrf context.
When such processes call DNS POSIX API like getaddrinfo, the sockets opened by the API are opened in mvrf context which means that the SO_BINDTODEVICE is internally taken care.
Hence, no other code change is required to make the internal DNS calls to work.

#### Other Applications
Applications like "apt-get", "ntp", "scp", "sftp", "tftp", "wget" are expected to work via both default VRF & management VRF when users connect from external device to the respective deamons running in the device.
When these applications are triggered from the device, they work through default VRF by default without any change.
To make them work through management VRF, use "cgexec -g l3mdev:mgmt" as prefix before the actual command. 

## Appendix

### <a name="design_comparison"></a>Design Approach Comparison
| Features         | Namespace                    | L3MDev
|---               |---                           |---
| Kernel Support   | Yes                          | Yes
| Scalability      | Limited                      | Better
| Protocol support | IP services replicated       | IP services enslaved to a L3 interface
| Performance      | Service replication overhead | Shared services


### Namespace Based Design
This solution is based on creating a complete instance of network stack for each VRF using the namespace solution available in Linux. 
Linux's Network Namespaces were designed to provide a complete isolation of the entire network stack - devices, network addresses, neighbor and routing tables, protocol ports and sockets. 
VRF On the other hand is a network layer 3 feature and as such should really only impact FIB lookups. 
While the isolation provided by a namespace includes the route tables, a network namespace will have a significant overhead as we will end up having two network stacks.
Using network name space as VRF's will involve having services replicated across all VRF's. 
For example, we will have to run two instances of lldp/ssh, one for Management and other for Default VRF's.Also in terms of extensibility, using namespaces for Multi VRF means N-VRFâ€™s which will have N-application instances and also the additional complexity of aggregating all the data across these instances.

### Conclusion: Use l3mdev instead of namespace  

The Linux kernel has brought in the l3mdev primarily to provide the VRF solution in the L3 layer. 
Linux kernel upgrades are also targetted towards using the L3mdev solution for VRF. 
Industry also uses l3mdev as the solution for VRF. 
Hence, it is decided to use l3mdev solution for supporting the VRF requirements. 
The alternate solution that is based on "Namespace" (given above) has been ignored due to the reasons stated above.

