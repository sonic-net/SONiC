## Troubleshooting Connectivity

### Packet Drops

```
sudo portstat
```

portstat example

```
sonicadmin@sonicswitch:~$ sudo portstat
     Iface    RX_OK    RX_RATE    RX_UTIL    RX_ERR    RX_DRP    RX_OVR    TX_OK    TX_RATE    TX_UTIL    TX_ERR    TX_DRP    TX_OVR
----------  -------  ---------  ---------  --------  --------  --------  -------  ---------  ---------  --------  --------  --------
 Ethernet0   582523        N/A        N/A         0    533446         0    82636        N/A        N/A         0         0         0
 Ethernet4   582523        N/A        N/A         0    533446         0    82635        N/A        N/A         0         0         0
Ethernet12   533446        N/A        N/A         0    540582         0    82635        N/A        N/A         0         0         0
```

### Light Level

```
sudo sfputil
```

sfputil example
```
sonicadmin@sonicswitch:~$ sudo sfputil --dom -p Ethernet0
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


