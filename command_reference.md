## Command Reference

### SSH Login

SONiC has SSH enabled by default.

```
user@debug:~$ ssh sonicadmin@sonicswitch
```

### LLDP

```
sudo llpdctl [interface]
```

Example
```
sonicadmin@sonicswitch:~$ sudo lldpctl
-------------------------------------------------------------------------------
LLDP neighbors:
-------------------------------------------------------------------------------
Interface:    eth0, via: LLDP, RID: 1, Time: 11 days, 15:16:47
  Chassis:
    ChassisID:    mac 54:e0:32:f2:6e:00
    SysName:      ###
    SysDescr:     ###
    Capability:   Bridge, on
    Capability:   Router, on
  Port:
    PortID:       local 539
    PortDescr:    ge-0/0/12.0
    MFS:          1514
    PMD autoneg:  supported: no, enabled: yes
      Adv:          10Base-T, HD: no, FD: yes
      Adv:          100Base-TX, HD: yes, FD: no
      Adv:          1000Base-X, HD: no, FD: yes
      Adv:          1000Base-T, HD: yes, FD: no
      MAU oper type: unknown
  VLAN:         146, pvid: yes ntp
  LLDP-MED:
    Device Type:  Network Connectivity Device
    Capability:   Capabilities
    Capability:   Policy
    Capability:   Location
    Capability:   MDI/PSE
```

### BGP

BGP is implemented via [Quagga](http://www.nongnu.org/quagga/docs/docs-info.html#Show-IP-BGP).

```
sudo vtysh
```

Example
```
sonicadmin@sonicswitch:~$ sudo vtysh -c "show ip bgp summary"
BGP router identifier 100.1.0.32, local AS number 65100
RIB entries 1, using 112 bytes of memory
Peers 3, using 13 KiB of memory

Neighbor        V         AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
100.0.0.1       4 65200       0       0        0    0    0 never    Active
100.0.0.3       4 65200       0       0        0    0    0 never    Active
100.0.0.7       4 65200       0       0        0    0    0 never    Active

Total number of neighbors 3
```
