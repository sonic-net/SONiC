## Command Reference

### SSH Login
Default credential: admin/YourPaSsWoRd

Example:
```
user@debug:~$ ssh admin@sonic
```

### Hardware Platform
* Command `decode-syseeprom` is used to decode the EEPROM that stores the system information.

Example:
```
admin@sonic:~$ decode-syseeprom
lsTLV Name             Len Value
-------------------- --- -----
PPID                  20 XX-XXXXXX-00000-000-0000
DPN Rev                3 XXX
Service Tag            7 XXXXXXX
Part Number           10 XXXXXX
Part Number Rev        3 XXX
Mfg Test Results       2 FF
Card ID                2 0x0000
Module ID              2 0
Base MAC Address      12 FE:EC:BA:AB:CD:EF
(checksum valid)

```
* Command `sfputils` is the utility to decode the SFP EEPROM that stores the SFP information.

Example:
```
admin@sonic:~$ sfputils --port Ethernet0 --dom
Ethernet0: SFP detected
        Connector : No separable connector
        Encoding : Unspecified
        Extended Identifier : Unknown
        Extended RateSelect Compliance : QSFP+ Rate Select Version 1
        Identifier : QSFP+
        Length Cable Assembly(m) : 1
        Specification compliance :
                10/40G Ethernet Compliance Code : 40GBASE-CR4
                Fibre Channel Speed : 1200 Mbytes/Sec
                Fibre Channel link length/Transmitter Technology : Electrical inter-enclosure (EL)
                Fibre Channel transmission media : Twin Axial Pair (TW)
        Vendor Date Code(YYYY-MM-DD Lot) : 2015-10-31
        Vendor Name : XXXXX
        Vendor OUI : XX-XX-XX
        Vendor PN : 1111111111
        Vendor Rev :
        Vendor SN : 111111111
        ChannelMonitorValues :
                RX1Power : -infdBm
                RX2Power : -infdBm
                RX3Power : -infdBm
                RX4Power : -infdBm
                TX1Bias : 0.0000mA
                TX2Bias : 0.0000mA
                TX3Bias : 0.0000mA
                TX4Bias : 0.0000mA
        ModuleMonitorValues :
                Temperature : 1.1111C
                Vcc : 0.0000Volts
```
* Command `sensors` is the utility installed via lm_sensors (Linux monitoring sensors) that provides tools and drivers for monitoring temperatures, voltage, and fans. (Ref: https://wiki.archlinux.org/index.php/lm_sensors)

### Switch Platform
* Command `portstat` is the utility that calculate the RX/TX packets rate on each physical port.
Use `portstat -c` to clear the counters and use `portstat` to get the packets number/rate after the counter is cleared.

Example:
```
admin@sonic:~$ portstat -c
Cleared counters
admin@sonic:~$ portstat
Last cached time was 2017-03-05 08:22:22.22222
      Iface      RX_OK      RX_RATE    RX_UTIL    RX_ERR    RX_DRP    RX_OVR    TX_OK      TX_RATE    TX_UTIL    TX_ERR    TX_DRP    TX_OVR
-----------  ---------  -----------  ---------  --------  --------  --------  -------  -----------  ---------  --------  --------  --------
  Ethernet0    372,049  202.42 MB/s      3.95%         0         0         0  272,687  143.67 MB/s      2.81%         0         0         0
  Ethernet4    894,510  540.25 MB/s     10.55%         0         0         0  450,325  258.69 MB/s      5.05%         0         0         0
  Ethernet8    530,283  308.82 MB/s      6.03%         0         0         0  563,247  323.75 MB/s      6.32%         0         0         0
 Ethernet12          1    52.70 B/s      0.00%         0         1         0        0     0.00 B/s      0.00%         0         0         0
```

### Layer 2
* Command `brctl` is the utility for Ethernet bridge administration. (Ref: http://linuxcommand.org/man_pages/brctl8.html)

Example:
```
admin@sonic:~$ brctl
bridge name     bridge id               STP enabled     interfaces
Vlan1000                8000.ecf4bbfe880a       no              Ethernet12
                                                        Ethernet16
                                                        Ethernet20
                                                        Ethernet24
                                                        Ethernet28
                                                        Ethernet32
                                                        Ethernet36
                                                        Ethernet4
                                                        Ethernet40
                                                        Ethernet44
                                                        Ethernet48
                                                        Ethernet52
                                                        Ethernet56
                                                        Ethernet60
                                                        Ethernet64
                                                        Ethernet68
                                                        Ethernet72
                                                        Ethernet76
                                                        Ethernet8
                                                        Ethernet80
                                                        Ethernet84
                                                        Ethernet88
                                                        Ethernet92
                                                        Ethernet96

```
* Command `teamdctl` is the utility for querying a unning instance of teamd for statistics or configuration information, or to make changes. (Ref: https://www.systutorials.com/docs/linux/man/8-teamdctl/)

Example:
```
admin@sonic:~$ teamdctl PortChannel0 state
setup:
  runner: lacp
ports:
  Ethernet4
    link watches:
      link summary: up
      instance[link_watch_0]:
        name: ethtool
        link: up
        down count: 0
    runner:
      aggregator ID: 1317, Selected
      selected: yes
      state: current
  Ethernet0
    link watches:
      link summary: up
      instance[link_watch_0]:
        name: ethtool
        link: up
        down count: 0
    runner:
      aggregator ID: 1317, Selected
      selected: yes
      state: current
runner:
  active: yes
  fast rate: no
```

* Command `teamshow` is the utility that displays all teamd instances in a one-shot command.

Example:
```
admin@sonic:~$ teamshow
Flags: A - active, I - inactive, N/A - Not Available, S - selected, D - deselected
  No.  Team Dev       Protocol    Ports
-----  -------------  ----------  ---------------------------
   24  PortChannel24  LACP(A)     Ethernet28(S) Ethernet24(S)
   48  PortChannel48  LACP(A)     Ethernet52(S) Ethernet48(S)
   16  PortChannel16  LACP(A)     Ethernet20(S) Ethernet16(S)
   32  PortChannel32  LACP(A)     Ethernet32(S) Ethernet36(S)
   56  PortChannel56  LACP(A)     Ethernet60(S) Ethernet56(S)
   40  PortChannel40  LACP(A)     Ethernet44(S) Ethernet40(S)
    0  PortChannel0   LACP(A)     Ethernet0(S) Ethernet4(S)
    8  PortChannel8   LACP(A)     Ethernet8(S) Ethernet12(S)

```
* Command `lldpctl` is the utility that controls the LLDP daemon. (Ref: https://manpages.debian.org/testing/lldpd/lldpctl.8.en.html)
* Command `lldpshow` is the utility that displays all LLDP neighbors in a pretty one-shot command.

Example:
```
admin@sonic:~$ lldpshow
Capability codes: (R) Router, (B) Bridge, (O) Other
LocalPort    RemoteDevice            RemotePortID    Capability    RemotePortDescr
-----------  ----------------------  --------------  ------------  ----------------------------------------
Ethernet0    SONIC01MS               Ethernet1       BR            Ethernet0
Ethernet4    SONIC02MS               Ethernet1       BR            Ethernet4
Ethernet8    SONIC03MS               Ethernet1       BR            Ethernet8
Ethernet12   SONIC04MS               Ethernet1       BR            Ethernet12
--------------------------------------------------
Total entries displayed:  4
```

### Layer 3
* Command `ifconfig` is the utility that configures the network interfaces. (Ref: http://linuxcommand.org/man_pages/ifconfig8.html)
* Command `ip address` is the utility that shows/manipulate addresses. (Ref:https://linux.die.net/man/8/ip)

Example:
```
admin@sonic:~$ ip route show Ethernet112
1315: Ethernet112: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether ec:f4:bb:fe:80:a1 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.56/31 brd 255.255.255.255 scope global Ethernet112
       valid_lft forever preferred_lft forever
    inet6 fc00::71/126 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::eef4:bbff:fefe:80a1/64 scope link
       valid_lft forever preferred_lft forever
```
* Command `ip route` is the utility that shows/manipulate routing. (Ref:https://linux.die.net/man/8/ip)
Note: Because Quagga is used as the routing software suite in SONiC, it will automatically sync routes to the kernel. That is the reason `ip route` command is able to list all the routes in Quagga.

Example:
```
admin@sonic:~$ ip route show
default  proto zebra  src 10.1.0.32
        nexthop via 10.0.0.1  dev PortChannel0 weight 1
        nexthop via 10.0.0.5  dev PortChannel8 weight 1
        nexthop via 10.0.0.9  dev PortChannel16 weight 1
        nexthop via 10.0.0.13  dev PortChannel24 weight 1
        nexthop via 10.0.0.17  dev PortChannel32 weight 1
        nexthop via 10.0.0.21  dev PortChannel40 weight 1
        nexthop via 10.0.0.25  dev PortChannel48 weight 1
        nexthop via 10.0.0.29  dev PortChannel56 weight 1
10.0.0.0/31 dev PortChannel0  proto kernel  scope link  src 10.0.0.0
10.0.0.4/31 dev PortChannel8  proto kernel  scope link  src 10.0.0.4
10.0.0.8/31 dev PortChannel16  proto kernel  scope link  src 10.0.0.8
10.0.0.12/31 dev PortChannel24  proto kernel  scope link  src 10.0.0.12
10.0.0.16/31 dev PortChannel32  proto kernel  scope link  src 10.0.0.16
10.0.0.20/31 dev PortChannel40  proto kernel  scope link  src 10.0.0.20
10.0.0.24/31 dev PortChannel48  proto kernel  scope link  src 10.0.0.24
10.0.0.28/31 dev PortChannel56  proto kernel  scope link  src 10.0.0.28

```

### BGP
* Command `vtysh` is the integrated shell for Quagga routing software. (Ref: http://man.cx/vtysh(1))

Example:
```
admin@sonic:~$ vtysh -c "show ip bgp summary"
BGP router identifier 10.1.0.32, local AS number 65100
RIB entries 13009, using 1423 KiB of memory
Peers 48, using 214 KiB of memory

Neighbor        V         AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.1        4 65200   27621   15925        0    0    0 5d08h25m     6402
10.0.0.5        4 65200   30806   32466        0    0    0 5d08h25m     6402
10.0.0.9        4 65200   34014   31315        0    0    0 5d08h25m     6402
10.0.0.13       4 65200   27603   27655        0    0    0 5d08h25m     6402

Total number of neighbors 4
```
