# Introduction
## Overview

The LACP Fallback Feature allows an active LACP interface to establish a Link Aggregation (LAG) before it receives LACP PDUs from its peer.

This feature is useful in environments where customers have Preboot Execution Environment (PXE) Servers connected with a LACP Port Channel to the switch.  Since PXE images are very small, many operating systems are unable to leverage LACP during the preboot process.  The server’s NICs do not have the capability to run LACP without the assistance of a fully functional OS; during the PXE process, they are unaware of the other NIC and don’t have a method to form a LACP connection. Both the NIC’s on the server will be active and are sourcing frames from their respective MAC addresses during the initial boot process.  Simply keeping both ports in the LAG active will not solve the problem because packets sourced from the MAC address of NIC-1 can be returned to the port on which NIC-2 is attached, which will cause NIC-2 to drop the packets (due to MAC mismatch).

![lag.png](https://github.com/Azure/SONiC/blob/gh-pages/images/lacp_fallback_hld/lag.png)

With the LACP fallback feature, the switch allows the server to bring up the LAG (before receiving any LACP PDUs from the server) and keeps a single port active until it receive the LACP PDUs from the server. This allows the PXE boot server to establish a connection over one Ethernet port, download its boot image and then continue the booting process. When the server boot process is complete, the server fully forms an LACP port-channel.

## Requirements

a)	LACP fallback feature can be enabled / disabled per LAG.
b)	Only one member port will be selected as active per LAG during fallback mode
c)	The member port will be moved out of the fallback state if it receives any LACP PDU from its peer.
d)	Interoperability with other devices running standard 802.3ad LACP protocol.
e)	The LACP runner behavior is not changed if fallback feature is disabled

## Assumptions

a)	The LACP fallback feature is implemented on top of the open source libteam (https://github.com/jpirko/libteam) adopted by SONiC
b)	The server is supposed to use only the member port in fallback mode to communicate with switch during the fallback mode.
c)	The changes are limited to the libteam library only, the APP DB/SAI DB is not aware of the fallback state.

## Limitations

LACP fallback mode may also kick in during the normal LACP negotiation process due to the timing, which might cause some unexpected traffic loss. For example, if the LACP PDUs sent by peer are dropped completely, local member port with fallback enabled may still enter fallback mode, which might end up with data traffic loss.
 
# Background

LACP fallback feature is implemented on the receiver side to establish a LAG before it receives LACP PDUs from its peer. So this section presents a formal description of the standard LACP Receive Machine.

## Receive Machine States and Timer
The receive machine has four states:
• Rxm_current
• Rxm_expired
• Rxm_defaulted
• Rxm_disabled

One timer:
Current while timer that is started in the Rxm_current and Rxm_expired states with two timeout: Short timeout (3s) and Long timeout (180s) depending on the value of the Actor’s Operational Status LACP_Timeout, as transmitted in LACPDUs.

![Current_LACP_State_Machine.png](https://github.com/Azure/SONiC/blob/gh-pages/images/lacp_fallback_hld/Current_LACP_State_Machine.png)

## Receive Machine Events
The following events can occur:
• Participant created or reinitialized
• Received LACP PDU
• Physical MAC enabled
• Physical MAC disabled
• Current while timer expiry
The physical MAC disabled event indicates that either or both of the physical MAC transmission or reception for the physical port associated with the actor have become non-operational. The received LACPDU event only occurs if both physical transmission and reception are operational, so far as the actor is aware.

![rxm.png](https://github.com/Azure/SONiC/blob/gh-pages/images/lacp_fallback_hld/rxm.png)

# LACP Fallback Design

With the standard rx state machine described above, the member port will be put into defaulted state if the member port never receives LACP PDUs from remote end. And the member port is not selectable in defaulted state, thus the member port cannot be aggregated to the LAG.

In order to support LACP fallback feature, we need to make the port selectable in defaulted state if fallback is enabled. Hence we'd like to introduce the fallback mode in defaulted state.

![LACP_Defaulted.png](https://github.com/Azure/SONiC/blob/gh-pages/images/lacp_fallback_hld/LACP_Defaulted.png)

Fallback Mode:
In this mode, the port selected bit is being set, which means the port is selectable and can be aggregated into the LAG. If any LACP PDU is being received over the LAG during this mode, the port will move to expired state, and restart the LACP negotiation with peer.

Fallback Eligible:
This checks whether LACP fallback feature is configured on this LAG. One and only one member port can be put into fallback mode per LAG. And the server is supposed to use only the member port in fallback mode to communicate with switch.

To summarize, in the defaulted state, we have
```
If member port is configured with fallback enable
	Selectable = 1
Else
	Selectable = 0
```

# LACP Fallback Config
## JSON Config
teamd is configured using JSON config string. This can be passed to teamd either on the command line or in a file. JSON format was chosen because it's easy to specify (and parse) hierarchic configurations using it.

Example teamd config (teamd1.conf):
```
{
        "device":"team0",
        "runner":
        {
                "name":"lacp",
                "active": true,
                "fast_rate": true,
				"fallback": true,
                "tx_hash": ["eth", "ipv4"]
        },
        "link_watch":{"name":"ethtool"},
        "ports":
        {
                "Ethernet30":{},
	            "Ethernet31":{},
	            "Ethernet32":{}
        }
}
```
## Minigraph Config
```
<PortChannelInterfaces>
  <PortChannel>
    <Name>PortChannel01</Name>
    <AttachTo>Ethernet0</AttachTo>
    <Fallback>true</Fallback>
    <SubInterface/>
  </PortChannel>
</PortChannelInterfaces>
```
The following set of Show commands relevant for LACP will be supported:
```
	Teamshow
	Teamdctl teamdevname state
```

# References

a)	SONiC Configuration Management
b)	Open Source libteam https://github.com/jpirko/libteam
c)	IEEE 802.3ad Standard for LACP http://www.ieee802.org/3/ad/public/mar99/seaman_1_0399.pdf
 
