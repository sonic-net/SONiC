# Command Reference

## Platform information

### System EEPROM

### Transceiver information

Usage:
```
sfputil
```

Example:
```
admin@sonic:~$ sudo sfputil --dom -p Ethernet0
Ethernet12: SFP detected

        Connector : Unknown
        EncodingCodes : Unspecified
        ExtIdentOfTypeOfTransceiver : GBIC def not specified
        LengthOM3(UnitsOf10m) : 144
        RateIdentifier : Unspecified
        ReceivedPowerMeasurementType : Avg power
        TransceiverCodes :
                10GEthernetComplianceCode : 10G Base-SR
                InfinibandComplianceCode : 1X Copper Passive
        TypeOfTransceiver : QSFP
        VendorDataCode(YYYY-MM-DD Lot) : 2013-11-29
        VendorName : MOLEX
        VendorOUI : MOL
        VendorPN : 1064141400
        VendorRev : E th
        VendorSN : G13474P0120
        ChannelMonitorValues :
                RX1Power : -5.7398dBm
                RX2Power : -4.6055dBm
                RX3Power : -5.0252dBm
                RX4Power : -12.5414dBm
                TX1Bias : 19.1600mA
                TX2Bias : 19.1600mA
                TX3Bias : 19.1600mA
                TX4Bias : 19.1600mA
        ChannelStatus :
                Rx1LOS : Off
                Rx2LOS : Off
                Rx3LOS : Off
                Rx4LOS : Off
                Tx1Fault : Off
                Tx1LOS : Off
                Tx2Fault : Off
                Tx2LOS : Off
                Tx3Fault : Off
                Tx3LOS : Off
                Tx4Fault : Off
                Tx4LOS : Off
        ModuleMonitorValues :
                Temperature : 23.7500C
                Vcc : 3.2805Volts
        StatusIndicators :
                DataNotReady : Off
```

### Interface counters

Usage:
```
portstat
```

Example:
```
sonicadmin@sonicswitch:~$ sudo portstat
     Iface    RX_OK    RX_RATE    RX_UTIL    RX_ERR    RX_DRP    RX_OVR    TX_OK    TX_RATE    TX_UTIL    TX_ERR    TX_DRP    TX_OVR
----------  -------  ---------  ---------  --------  --------  --------  -------  ---------  ---------  --------  --------  --------
 Ethernet0   582523        N/A        N/A         0    533446         0    82636        N/A        N/A         0         0         0
 Ethernet4   582523        N/A        N/A         0    533446         0    82635        N/A        N/A         0         0         0
Ethernet12   533446        N/A        N/A         0    540582         0    82635        N/A        N/A         0         0         0
```

## L2 Information

### LLDP Neighbors

Usage:
```
llpdctl [Interface]
```

Example:
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

## IP Information

### IP Addresses

### IP Route

## BGP Information

BGP is implemented via [Quagga](http://www.nongnu.org/quagga/docs/docs-info.html#Show-IP-BGP).

Usage:
```
vtysh
```

Example:
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
