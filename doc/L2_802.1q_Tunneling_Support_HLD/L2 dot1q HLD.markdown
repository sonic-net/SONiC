# IEEE 802.1Q Tunneling Support
>
>
>
## Revision History

[© xFlow Research Inc](https://xflowresearch.com/)  

|  Revision No| Description | Author  | Contributors |Date |  
| :-------------: |:-------------:| :-----:|:----------:|:-----:|
|0.1| IEEE 802.1Q Tunneling Support| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 14 Dec 2021|
|0.2| Architectural Changes & CLI Commands addition| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86) , [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad) & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 30 Sep 2022|
  
## Table of Contents

- Scope  
- Definitions/Abbreviations  
- Overview  
- Introduction  
- Features Description  
  - Functional Features  
  - Functional Feature Description  
    - L2 VLAN Tunneling Support  
    - Integration of SONiC with other open-source Implementation  
    - Enabling VLAN pruning  
- Feature Design  
  - Sample Topology  
  - Flow Chart  
    - Flow Chart Explanation  
  - Architecture Design  
- High-level Design  
  - Part 1  
  - Part 2  
  - DB & Schema Changes  
  - Warm Reboot Requirements  
  - Fast reboot Requirements  
- SAI API  
  - Configuration and Management  
  - VLAN DOT1Q Configuration Commands  
  - VLAN DOT1Q Show Commands  
- Warm Boot and Fastboot Design Impact  
- Restrictions/Limitations  
  - Testing Requirements/Design  
    - Unit Test cases  

## Scope

This high-level design document describes the integration of VLAN tunneling encapsulation protocol IEEE 802.1Q in SONiC.  

## Definitions/Abbreviations

| **Sr No** |  **Term**   |  **Definition**                      |
| :------------- |:-------------| :-----|
|  1       |  VLAN_ID      |  Unique identifier for each VLAN     |  
|  2       |  Dot1q        |  IEEE 802.1Q Protocol                |  
|  3       |  Trunk Link   |  The link between different switches that carries the traffic from different VLANs  |  
|  4       | Encapsulation |  Addition of dot.1q tag in the normal ethernet frame.|  
|  5       |  Egress Port  |  Outbound port                       |  
|  6       |  Ingress Port |  Inbound port                        |  
|  7       |  BGP          |  Border gateway protocol             |  
|  8       |  DHCP         |  Dynamic Host Configuration Protocol |  
|  9       |  LAG          |  Link Aggregation                    |  
|  10      |  VID          |  VLAN Identifier                     |  
|  11      |  TPID         |  Tag Protocol Identifier             |  

## Overview

L2 DOT1Q (802.1Q) is an IEEE standard for tunnel encapsulation to support transport of different VLAN frames on the tunnel link. 802.1Q tunneling support is very fundamental for the forwarding of different VLANs frames on the trunk links. This HLD provides implementation details of L2 Dot1Q tunneling support in SONiC.

## Introduction

IEEE 802.1Q is a networking standard that defines the VLANs tagging on an ethernet network. The Ethernet frame contains a TAG with fields that specify VLAN membership and user priority. As seen in the below Ethernet frame, the TAG is inserted between the Source MAC address and Type/Length. The TAG is of 16-bit length. The 802.1Q tags are inserted into the frames before  transmitting out of the interface and similarly, the tags are removed from frames received from the interface. The frames are transmitted and received from the interfaces that are configured with VLAN and they are tagged with VID.  

Original Ethernet Frame  
|  Preamble |  Dest MAC |  Source MAC |  Type/Length |  Data |  CRC |

802.1Q Frame from Customer  
| Preamble |  Dest MAC |  Source MAC |  TAG |  Type/ Length |  Data |  CRC |

802.1Q Frame on Trunks between Service Provider Switches  
| Preamble |  Dest MAC |  Source MAC |  TAG |  TAG | Type/ Length |  Data |  CRC |  
IEEE 802.1 TAG:  
|  TPID (16 bit) | User Priority (PCP) (3 bits) | CFI (1 bit) |  VID (12 bits) |  

- TPID  
A 16-bit field was set to a value of 0x8100 in order to identify the frame as an IEEE 802.1Q-tagged frame. This field is located at the same position as the EtherType field in untagged frames, and is thus used to distinguish the frame from untagged frames.  

- User Priority (PCP)  
A 3-bit field which refers to the IEEE 802.1p class of service and maps to the frame priority level. Different PCP values can be used to prioritize different classes of traffic.

- CFIA  
1-bit field. May be used separately or in conjunction with PCP to indicate frames eligible to be dropped in the presence of congestion.  

- VIDA  
A 12-bit field specifying the VLAN to which the frame belongs. The values of 0 and 4095 (0x000 and 0xFFF in hexadecimal) are reserved. All other values may be used as VLAN identifiers, allowing up to 4,094 VLANs. The reserved value 0x000 indicates that the frame does not carry a VLAN ID; in this case, the 802.1Q tag specifies only a priority (in PCP and DEI fields) and is referred to as a priority tag. On bridges, VID 0x001 (the default VLAN ID) is often reserved for a network management VLAN; this is vendor-specific. The VID value 0xFFF is reserved for implementation use; it must not be configured or transmitted. 0xFFF can be used to indicate a wildcard match in management operations or filtering database entries.  

## Feature Design

### Sample Topology

![Topology](https://user-images.githubusercontent.com/92853499/193266802-21c3dc9a-50db-44ae-be51-dc823ebbe3b2.png)


This sample topology shows the primary VLANs and the dot1q trunking protocol working. The figure shows that 3 different VLANs are configured with 6 other hosts. Ethernet switches can forward the frames from the same VLANs if the host is connected to the same switch. On the contrary, if the hosts are in the same VLANs are connected via different switches then frames can only be forwarded if any one of the following is available:

1\. A link between switches with the same VLAN ID.  
2\. A tunnel link with 802.1Q encapsulation.

Practically option 1 is not feasible as it requires a separate link between switches for each VLAN. Option 2 is accepted and more practical where only one link known as the trunk link between switches with 802.1Q encapsulation is sufficient for carrying any possible number of VLANs.

## Architecture Design

The overall SONiC architecture will remain the same and no new sub-modules will be introduced.

## High-level Design

In this document we have defined switch port modes i.e. access, trunk, and routed. We have added cli commands for vlan management on trunk ports.

### Access Mode

In access mode a port possesses the following properties
* Receives untagged/tagged traffic for a particular Vlan
* Forwards untagged/tagged traffic for a particular Vlan

### Trunk Mode

In trunk mode a port possesses the following properties
* Receives untagged traffic for a single Vlan
* Forwards untagged traffic for a single Vlan
* Receives tagged traffic for one or more Vlan(s)
* Forwards tagged traffic for one or more Vlan(s)

### Switch Port Mode

![Sequence 1](media/1.png)  

__*Figure 2: Sequence Diagram Switch Port mode*__

**1.** Check if a port name with an alias exists.

**2.** Check if the port is already configured as a mirror destination port and port is a member of vlan.

**3.** Check port assigned is a valid port on a valid port channel.

**4.** Check if the port is the router interface and if the interface is a part of the port channel.

**5.** Check if the interface is an untagged member then the switch port mode will be Access.

**6.** Check if the interface is a tagged member then the switchport mode will be Trunk.

**7.** Check if the interface is  neither tagged or untagged then switchport mode will be routed which is a default switchport mode.


### Add Multiple VLANs
 
![Sequence 2](media/2.png)

__*Figure 3: Sequence Diagram for adding Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list and return.

**2.** Check for the default Vlan. If default vlan is assigned then switchport mode commands will be used.

**3.** Check if the VLAN is in the range (2-4094) and whether the vid already exists or not.

**4.** Check if vlan id exist

**5.** After checking if it’s in the range, CLI will call for the VLAN_id function.

**6.** Finally, CLI will add the VLAN from the list in the VLAN table.

### Delete Multiple VLANs

![Sequence 3](media/3.png)

__*Figure 4: Sequence Diagram for deleting Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list and return.

**2.** Check if the VLAN is in the range .

**3.** Read the existing vlan table and delete vlans(s).

### Add VLANs Range

![Sequence 4](media/4.png)

__*Figure 5: Sequence Diagram for adding VLANs range*__

**1.** CLI will call for the vlan_range list function in the cli_common.

**2.** CLI will check if the range is in between (2-4094) in the cli_common.

**3.** SONiC CLI will verify the vid by checking in the CONFIG_DB if it already exists or not.

**4.** If the vid doesn’t exist CLI will add the vlan in range in cli_common.

**5.** CLI will also add the vlan from the list in the vlan table in the CONFIG_DB.


### Delete VLANs Range

![Sequence 5](media/5.png)

__*Figure 6: Sequence Diagram for deleting VLANs range*__

**1.** CLI will call for the vlan_range list function in the cli_common.

**2.** CLI will check if the range is in between (2-4094) in the cli_common.

**3.** SONiC CLI will read the vlan table from CONFIG_DB.

**4.** If the vlan exists CLI will call the del_vid function.

**5.** CLI will delete the vlan from the list in the vlan table in the CONFIG_DB.

### Add VLAN member on Trunk Port

![Sequence 6](media/6.png)

__*Figure 7: Sequence Diagram for Adding VLAN member on Trunk Port*__

**1.** Check if the vlan flag is all then add all the existing VLANs from the vlan list as members to the port.

**2.** Check if the vlan flag is except then add all the existing VLANs from the vlan list as vlan members except the vlan id specifically mentioned.

**3.** Check if the vlan flag is multiple then check multiple vlan parsers.

**4.** Check default vlan and vlan_range and return if they already exist.

**5.** Add the vlan(s) from the list to the vlan member in the vlan member table. 

### Delete VLAN member on Trunk Port

![Sequence 7](media/7.png)

__*Figure 8: Sequence Diagram for deleting VLAN member on Trunk Port*__

**1.** Check if the vlan flag is all then delete all the existing VLANs from the vlan list as members to port.

**2.** Check if the vlan flag is except then delete all the existing VLANs from the vlan list as vlan members except the vlan id specifically mentioned.

**3.** Check if the vlan flag is multiple then check multiple vlan parsers.

**4.** Check default vlan and vlan_range and return if they already exist.

**5.** Check if the port exists for that particular VLAN.

**6.** Check if the interface_is an untagged member of the port.

**7.** Delete the vlan(s) from the list to vlan members in the vlan member table.

### Add VLAN member range on Trunk Port

![Sequence 8](media/8.png)

__*Figure 9: Sequence Diagram for Adding VLAN member range on Trunk Port*__

**1.** CLI will call for the vlan_range list function in the cli_common.

**2.** CLI will check if the range is in between (2-4094) in the cli_common.

**3.** If the vid doesn’t exist CLI will add the vlan in range in cli_common.

**4.** Add vlan members in range in the vlan member table.

### Delete VLAN member range on Trunk Port

![Sequence 9](media/9.png)

__*Figure 10: Sequence Diagram for deleting VLAN member range on Trunk Port*__

**1.** CLI will call for the vlan_range list function in the cli_common.

**2.** CLI will check if the range is in between (2-4094) in the cli_common.

**3.** If the vid doesn’t exist CLI will add the vlan in range in cli_common.

**4.** Delete vlan members in range in the vlan member table.

#### CLI & sonic-cfggen Modules

We will be adding a few commands to the SONiC CLI for the configuration and management of L2 Dot1Q trunking. The details of the commands are given in the configuration and management section below. CLI and sonic-cfggen modules are two interrelated modules that are implemented outside all of the sonic containers, these modules are used for configuration and management of sonic. 

### Warm Boot and Fastboot Design Impact

The existing warm boot/fast boot feature is not affected due to this design.

#### Warm Reboot Requirements

N/A

#### Fast reboot Requirements

N/A

## SAI API

No SAI API change or addition is needed for this HLD. We will be using the existing SAI API.

## Configuration and Management

### VLAN DOT1Q Configuration Commands

**1.** config switchport mode <port_type (access or trunk or routed)> <physical port>
 
**2.** config vlan add/del -m <vlan_id>

**3.** config vlan add/del range  <vlan_id> 

**4.** config vlan  member add/del  -m <all,except, comma separated list><physical port>

**5.** config vlan member range add/del <vlan_id> <physical port>

## Restrictions/Limitations

This HLD did not consider hybrid switch port mode. We will be adding a separate HLD for hybrid mode. 

### Testing Requirements/Design

#### Unit Test cases

Unit testing will be done at two levels CLI level and Functional Level

CLI Level Tests
* Verify CLI to set the mode of an interface to access or trunk
* Verify CLI to add a comma separated list of vlan(s)
* Verify CLI to add range of vlan(s) 
* Verify CLI to add all vlan(s) except given vlan to member port
* Verify CLI to delete list of vlan(s)
* Verify CLI to delete all vlans except given comma separated list of vlan(s)

Functional Level Tests
* Verify that port modes are set .
* Verify that multiple vlan(s) or range of vlan(s) can be added.
* Verify that multiple vlan member(s) can be added on a trunk port.
* Verify intra-vlan communication between hosts on a single switch
* Verify intra-vlan communication between hosts on two different switches
* Repeat above step for different vlans
* Verify interoperability of SONiC with other OS by creating a trunk between SONiC switch and any other switch running a different OS other than SONiC.

