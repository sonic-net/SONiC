
# Switch Port Modes and Vlan CLI Enhancement


## Revision History

[© xFlow Research Inc](https://xflowresearch.com/)  


|  Revision No| Description | Author  | Contributors |Date |  
| :-------------: |:-------------:| :-----:|:----------:|:-----:|
|0.1| IEEE 802.1Q Tunneling Support| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 14 Dec 2021|
|0.2| Architectural Changes & CLI Commands addition| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 30 Sep 2022|
|0.3| Revision in Title,Switchport modes and CLI enhancements| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 24 Oct 2022|
|0.4| Addition of Use Cases, Db Migrator and Config-Db Enchanements| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 06 Mar 2023|
|0.5| Detailed Examples Section | [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 05 May 2023|




  
  
## Table of Contents

- Scope  
- Definitions/Abbreviations  
- Overview  
- Introduction
  - Access Mode
  - Trunk Mode
- Topology Design 
- Use cases for Switchport modes
  - Access Mode
  - Trunk Mode
- Architecture Design  
- High-level Design  
  - State Transition Diagram of Switchport Mode for Port & PortChannel 
  - Sequence Diagram for Adding Multiple Vlan(s) 
  - Sequence Diagram for Deleting Multiple Vlan(s) 
  - Sequence Diagram for Adding Multiple Vlan(s) on Trunk Ports  
  - Sequence Diagram for Deleting Multiple Vlan(s) on Trunk Ports   
- CLI Configuration 
  - VLAN CLI Enchanement Commands
  - Switchport Modes Command
- YANG Model Configuration 
  - Yang New Type for Port and PortChannel
  - Yang Leaf for Port and PortChannel
- Config DB Enhancement
- Db Migrator Enhancement 
- Example/Usage of Commands
  - Examples of VLAN CLI Enchanement Command
    -  Add Multiple Vlans in Range or Comma Separated List
    -  Add Multiple VLAN Members on Port/PortChannel 
    -  Multiple Vlan command Truncate Examples
   - Examples of Switchport mode Command
      - Configuring Port & PortChannel from Routed to Access 
      - Configuring Port & PortChannel from Routed to Trunk
        - Physical Port Configuration
        - PortChannel Configuration
- SAI API 
- Warm Boot and Fastboot Design Impact  
- Restrictions/Limitations 
- Testing Requirements/Design  
    - Unit Test cases
    - Functional Test cases
- Future Work

## Scope

This high-level design document describes the implementation of Switchport modes and VLAN CLI enhancements in SONiC.

## Definitions/Abbreviations

| **Sr No** |  **Term**   |  **Definition**                      |
| :------------- |:-------------| :-----|
|  1       |  VLAN_ID      |  Unique identifier for each VLAN     |  
|  2       |  Trunk  |  The port is untagged member to one VLAN and tagged member to one or more VLANs  |  
|  3       | Access |  The port is untagged member to only one VLAN|  
|  4       |  Routed | The port is in L3 interface mode                       |  



## Overview

This HLD will provide implementation details of switch port modes access and trunk on a Port or on a PortChannel. In this HLD vlan configuration commands are also improved for efficient configuration and management of VLANs.

## Introduction

Switch ports are Layer 2-only interfaces associated with a physical port. A switch port can have three modes: access port, a trunk port, or a hybrid port. We can manually configure a port as an access port, trunk port or hybrid port depending on requirement . Switch ports are used for managing the physical interface and associated Layer 2 protocols and do not handle routing.

### Access Mode

In access mode a port possesses the following properties
* Receives untagged traffic for a particular Vlan
* Forwards untagged traffic for a particular Vlan

### Trunk Mode

In trunk mode a port possesses the following properties
* Receives untagged traffic for a single Vlan
* Forwards untagged traffic for a single Vlan
* Receives tagged traffic for one or more Vlan(s)
* Forwards tagged traffic for one or more Vlan(s)

### Sample Topology

![Topology](https://user-images.githubusercontent.com/61490193/208155234-3a04ca08-5ca3-42b3-b679-c1efcacddff2.png)


__*Figure 1: Sample Topology*__

The figure shows that 3 different VLANs are configured with 6 other hosts. The switch ports connected to hosts would be configured as access ports. The ports that connect switches together would be configured as trunk ports.

## Use Caess for Switchport modes
### Access Mode
Here are some common use cases for switch port mode access:

**1.** Connecting devices to a network: When users need to connect devices to a switch, such as computers, printers, or IP phones, you can configure the switch ports to operate in access mode. This allows the devices to communicate with other devices on the network.

**2.** Restricting VLANs: Users can use switch port mode access to restrict the VLANs that a device can access. This can help control access to network resources and improve network security.

**3.** Improving network performance: By using switch port mode access, users can reduce the amount of unnecessary broadcast traffic on the network. When a switch port is in access mode, it forwards traffic for the configured VLAN only, thus reducing/restricting the broadcast domain.

**4.** Implementing Quality of Service (QoS): QoS allows users to prioritize traffic on the network based on the type of traffic and the needs of users. By configuring switch ports to operate in access mode in conjunction with QoS parameters available in SONiC, users can ensure that traffic from specific devices is prioritized over other traffic on the network.

Overall, switch port mode access is a useful feature for controlling access to your network, improving network performance and segmenting a network into multiple broadcast domains.

### Trunk Mode
Here are some common use cases for switch port mode trunk:

**1.** Connecting switches: When users need to connect two or more switches together, they can configure the switch ports to operate in trunk mode. This allows multiple VLANs to be transmitted over a single link, which can help to reduce the number of ports required and simplify network topology.

**2.** Connecting to a router: Users can use switch port mode trunk to connect a switch to a router or other network device that supports VLANs. This allows the user to create multiple VLANs on the switch and route traffic between them using the router.

**3.** Reducing congestion: By enabling trunking, you can reduce the number of ports required to connect switches together. This can help to reduce congestion and improve network performance by allowing more bandwidth to be dedicated to data traffic.

**4.** Improving network scalability: Trunking also improves network scalability. By allowing multiple VLANs to be transmitted over a single port, you can increase the number of devices that can be connected to the network without needing additional switches.

Overall, the switch port mode trunk is a useful feature for connecting switches and other network devices together, improving network performance, and providing redundancy. By enabling trunking, users can simplify network topology, reduce congestion, and increase network scalability.

## Architecture Design

The overall SONiC architecture will remain the same and no new sub-modules will be introduced. Changes are made only in the CLI container and Config_DB.

![Architecture](https://user-images.githubusercontent.com/61490193/217232727-811b98a8-ce9c-4227-a94a-1c83a4825a62.png)


## High-level Design

In this section we will explain sequence diagrams for the implemented features.

### State Transition Diagram of Switchport modes for PORT or PORT CHANNEL

The following state transition depicts the behavior of Switchport  modes access and trunk for adding port modes on a Port or PortChannel. Switching between these modes is also depicted here. Default port mode is “routed”.

![State-Transition-Diagram](https://user-images.githubusercontent.com/61490193/223195784-05cc4e98-8883-4911-bca3-fded6a87d202.png)

__*Figure 2: State Transition Diagram SwitchPort mode*__


### Sequence Diagram for Adding Multiple VLANs
 

![Add-Vlan](https://user-images.githubusercontent.com/61490193/223186173-b1eecf22-eef0-4ba1-86d1-8675a7b00f31.png)

__*Figure 3: Sequence Diagram for adding Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list and return.

**2.** Check if the VLAN is in the range (2-4094) and whether the vid already exists or not.

**3.** Check if vlan id already exist it will show an error message and truncate. Examples for such cases have been mentioned in the examples section below.

**4.** After checking the vlan list in the range and vlan doesn’t already exist.

**5.** CLI will add the VLAN from the list in the VLAN table.

__*NOTE: This works same for Adding Multiple VLANs on a PortChannel*__


### Seqence Diagram for Deleting Multiple VLANs


![Delete-Vlan](https://user-images.githubusercontent.com/61490193/223189728-8545972f-c726-4d6a-a66c-984617e825c2.png)


__*Figure 4: Sequence Diagram for deleting Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list.

**2.** Check if the VLAN is in the range .

**3.** Check if vlan exists or not. If vlan does not exist it will show an error message and truncate. Examples for such cases have been mentioned in the examples section as well.

**4.** Read the existing vlan table and delete vlans(s).


__*NOTE: This works same for Deleting Multiple VLANs from a PortChannel*__


### Sequence Diagram for Adding Multiple VLAN member on Trunk Port


![Add-Vlan-Member](https://user-images.githubusercontent.com/61490193/223186389-94bb1c7f-0966-40a2-b569-38c0a56a5899.png)


__*Figure 5: Sequence Diagram for Adding VLAN member on Trunk Port*__


**1.**  The SONiC CLI will Call vlan_member_input_parser to add multiple vlan member(s).

**2.**  Check for vlan_range.

**3.**  Check port mode (access or trunk) for adding vlan members (untagged or tagged) on a port from the PORT table and return.

**4.**  Add member vlan(s) in multiple commas or range list, all flag & except flag can be used as well.

**5.**  Add the vlan member(s) in the vlan member table. 


__*NOTE: This works same for Adding Multiple VLANs members on a PortChannel*__


### Delete Multiple VLAN member on Trunk Port

![Delete-Vlan-Member](https://user-images.githubusercontent.com/61490193/223199172-0ae75308-6e93-4176-9db6-3bcfbd02b948.png)


__*Figure 6: Sequence Diagram for deleting VLAN member on Trunk Port*__

**1.** The SONiC CLI will call the vlan_member_input_parser which will parse multiple vlan(s) in a list.

**2.** Check if the members exist in the range .

**3.** Read the existing vlan table and delete vlans(s).


__*NOTE: This works same for Delete Multiple VLANs members from a PortChannel*__

## CLI Configuration Commands 

### VLAN CLI  Enhancement Commands


**1.** config vlan add/del -m <vlan_ids>

**2.** config vlan  member add/del  -m  <vlan_id> <member_portname>/<member_portchannel>

**3.** config vlan  member add/del  -e  <vlan_id> <member_portname>/<member_portchannel>

**4.** config vlan  member add/del  -e  -m  <vlan_id> <member_portname>/<member_portchannel>

**5.** config vlan member add/del all <member_portname>/<member_portchannel>


### Switchport Mode Commands:

**1.** config switchport mode < access | trunk | routed> <member_portname>/<member_portchannel>

**2.** show interfaces switchport config

**3.** show interfaces switchport status


## YANG Model Configuration 

For Mode attribute, a new type is defined in YANG Model for adding support of "mode" in PORT_TABLE & PORTCHANNEL_TABLE.

### YANG New type for PORT_TABLE & PORTCHANNEL_TABLE

    typedef switchport_mode {
        type string {
            pattern "routed|access|trunk";
                    }
        description
            "SwitchPort Modes for Port & PortChannel";
                         }

### YANG Leaf for PORT_TABLE & PORTCHANNEL_TABLE

         leaf mode {
		description "SwitchPort Modes possible values are routed|access|trunk. Default val is routed. "; 
		type stypes:switchport_mode; 
		default "routed";
				}
## Config DB Enhancements
We have added a new “mode” field in PORT & PORT CHANNEL Table .

    "PORT":
      {
        "Ethernet0": {
            "admin_status": "up",
            "alias": "fortyGigE0/0",
            "index": "0",
            "lanes": "25,26,27,28",
            "mode": "access",
            "mtu": "9100",
            "speed": "40000"
        }
      }
  **Assumption: Etherent0 has been configured as access by user

     "PORTCHANNEL": {
        "PortChannel0001": {
            "admin_status": "up",
            "fast_rate": "false",
            "lacp_key": "auto",
            "min_links": "1",
            "mode": "trunk",
            "mtu": "9100"
        }
      }
 **Assumption: PortChannel0001 has been configured as trunk by user


## DB Migrator Enhancements
As there is a change in the schema for PORT & PORT CHANNEL Table in config DB. We have added a  new "mode" field in db_migrator.py in order to support backward compatibility. 

#### Existing Before Migration PORT TABLE Schema in Config_DB

     "PORT": 
    {
        "Ethernet0": {
            "admin_status": "up",
            "alias": "fortyGigE0/0",
            "index": "0",
            "lanes": "25,26,27,28",
            "mtu": "9100",
            "speed": "40000"
        }
    }

 If there is IP or IPV6 configured, no "mode" field will be added which means "routed" for the old configurations. If there is a VLAN membership, then the mode field will be "trunk". 

After Migration PORT TABLE if there is VLAN Membership in Config_DB


    "PORT":
    {
        "Ethernet0": {
            "admin_status": "up",
            "alias": "fortyGigE0/0",
            "index": "0",
            "lanes": "25,26,27,28",
            "mode": "trunk",
            "mtu": "9100",
            "speed": "40000"
        }
    }


#### Existing Before Migration PORTCHANNEL TABLE Schema in Config_DB

    "PORTCHANNEL": 
     {
        "PortChannel0001": {
            "admin_status": "up",
            "fast_rate": "false",
            "lacp_key": "auto",
            "min_links": "1",
            "mtu": "9100"
        }
     }


If there is IP or IPV6 configured, no "mode" field will be added which means "routed" for the old configurations. If there is a VLAN membership, then the mode field will be "trunk". 


 After Migration PORTCHANNEL TABLE if there is VLAN Membership in Config_DB

     "PORTCHANNEL": 
     {
        "PortChannel0001": {
            "admin_status": "up",
            "fast_rate": "false",
            "lacp_key": "auto",
            "min_links": "1",
            "mode": "trunk",
            "mtu": "9100"
        }
      }


##  Examples/Usage of Commands

This section provides examples/usage of new commands that have been added for switchport modes and VLAN CLI enhancements. These commands work similarly for both Physical Ports and Port Channels. 


###  Examples/Usage of VLAN CLI Enhancement Commands


* Add Multiple Vlans in Range or Comma Separated List

```
admin@sonic:~$ sudo config vlan add -m 2-7 
 
Usage:  The command will add/del multiple Vlan using a single command by providing a range. 

Example: Suppose User wants to create multiple range of Vlans. The command will create the VLANs "Vlan2, Vlan3, Vlan4, Vlan5, Vlan6, Vlan7" if these do not already exist.

```

```
admin@sonic:~$ sudo config vlan add -m 8,9,10,11,12
 
Usage:  The command will add/del multiple Vlan using a single command by providing a comma separated list. 

Example: Suppose User wants to create multiple comma sepaated Vlans. The command will create the VLANs "Vlan8, Vlan9, Vlan10, Vlan11, Vlan12" if these do not already exist.

```

** Above two examples can be verified using "show vlan brief" command as shown below **

<img src="https://user-images.githubusercontent.com/61490193/236170623-234e6458-2516-4425-b8c9-2ce7af53ec78.png"  width="65%" height="30%">

* Add Multiple VLAN Members on Port/PortChannel 

```
admin@sonic:~$ sudo config vlan add -m 3-5 Ethernet0

Usage:  The command will add/del multiple Vlan Member(s) using a single command by providing a range.

Example : Suppose Vlan2 to Vlan12 are exisitng Vlan. The command will add Ethernet0 which is configured as trunk as member of VLANs "Vlan3, Vlan4, Vlan5"
```
<img src="https://user-images.githubusercontent.com/61490193/236294589-11909ecd-4b35-4deb-95c2-1632b38d6819.png" width="65%" height="40%">

```
admin@sonic:~$ sudo config vlan member add -e -m 2,3,5 Ethernet4

Usage:  The command will add/del all exisitng Vlan excluding some specific Vlan(s) as member to a Port/PortChannel 

Example: Suppose Vlan2 to Vlan12 are existing Vlans. Users wanted to add all existing VLANs excluding Vlan2, Vlan3, Vlan5. This command will add Ethernet4 which is configured as trunk port as member of Vlan4, Vlan6 , Vlan7 ,Vlan8 ,Vlan9 ,Vlan10 ,Vlan11 ,Vlan12 
```

<img src="https://user-images.githubusercontent.com/61490193/236534613-007ca01c-a0ce-428b-ba2a-f1c16b9c9a21.png" width="65%" height="30%">


```
admin@sonic:~$ sudo config vlan add -e 10 Ethernet8
 
Usage:  The command will add/del all exisitng Vlan excluding some specific Vlan(s) as member to a Port/PortChannel 

Example: Suppose Vlan2 to Vlan12 are existing Vlans. Users wanted to add all existing VLANs excluding Vlan10. This command will add Ethernet8 which is configured as trunk port as member of Vlan2, Vlan3 , Vlan4 , Vlan5, Vlan6, Vlan7 ,Vlan8 ,Vlan11, Vlan12
```

<img src="https://user-images.githubusercontent.com/61490193/236533226-6f815971-6ccf-49eb-8e00-46aa721dc02b.png" width="65%" height="30%">

```
admin@sonic:~$ sudo config vlan member add all Ethernet12

Usage:  The command will add/del all exisitng Vlan as Member to a Port/PortChannel

Example: Suppose Vlan2 to Vlan12 are existing Vlans. Users wanted to add all existing VLANs to a Trunk Port. This command will add Ethernet12 which is configured as a trunk port as member of Vlan2 to Vlan12
```

<img src="https://user-images.githubusercontent.com/61490193/236533155-05efdba3-4df4-416d-ab98-b51ac5fc0cc2.png" width="65%" height="30%">

*  Add/Del Multiple VLAN & Vlan Members Command Truncate Examples

Multiple Vlan commands for adding Vlans (comma separated or in range) will truncate as soon as it finds any Vlan already exists. This is the existing behavior of SONiC, where command is aborted if any Vlan already exists in case of Vlan addition. Deletion of Vlans works the same way and the command will truncate as soon as it finds a Vlan doesn’t exist. 

Users has to take care that a vlan should not already exist in the given range if he/she is trying to add multiple vlans.  Similarly, a user has to take care that all the vlans should exist in the given range if he/she is trying to delete multiple vlans. Following examples will make a more clear understanding of this fact.

* Example 01: Suppose Vlan 2 already exists then multiple range vlan command will truncate at the start, so no vlan will be added as a result.

```
admin@sonic:~$ sudo config vlan add -m 2-11 
```
<img src="https://user-images.githubusercontent.com/61490193/236564441-df20e795-0f35-443f-9c3f-6ebb71554071.png" width="65%" height="30%">

* Example 02: Suppose Vlan 18 already exists then multiple range vlan command will truncate in the middle. So, Vlan16 and Vlan17 will be added and then the command will truncate with an error.

```
admin@sonic:~$ sudo config vlan add -m 16,17,18,19
```

<img src="https://user-images.githubusercontent.com/61490193/236563679-40bd03ef-91b6-4db2-aeb4-7767abd47c5d.png" width="65%" height="30%">

*  Example 03:  Suppose Vlan 25 already exists then multiple range vlan command will truncate at the end.  So, Vlan20 to Vlan24 will be added and then the command will truncate with an error.

```
admin@sonic:~$ sudo config vlan add -m 20-25
```
<img src="https://user-images.githubusercontent.com/61490193/236563569-ace341d3-48e8-49f0-ad8e-0b94f4a280b0.png" width="65%" height="30%">


We have given examples only for addition of vlans, commands for deletion of vlans will show similar behavior.  


###  Examples/Usage of Switchport Modes Command

Following example shows usage of switchport modes “access” and “trunk” and switching of port mode from routed to access/trunk. Before switching mode from routed to access/trunk, the user must remove IP first. 

#### Configuring Port & PortChannel from Routed to Access 

In these examples, Ethernet0 will be configured as “Access” from “Routed”. We will be using some of exisitng Vlans (Vlan2 to Vlan12 created in the above section) for vlan member configuration on Port. 

By default, all ports have IP assigned. For Switchport configuration we have to remove IP assignment otherwise CLI will show following Error:

**For Ethernet0**

<img src="https://user-images.githubusercontent.com/61490193/236294097-1c79ee78-0b83-4daf-ae48-39de60804683.png" width="65%" height="30%">


Following Steps will be taken to configure “Access”  mode  on Ethernet0 from “Routed”.

**1.** Remove IP assigned on Ethernet0

```
admin@sonic:~$ sudo config interface ip remove Ethernet0 10.0.0.0/31
```

**2.** Configure Ethernet0 as Access

```
admin@sonic:~$ sudo config switchport mode access Ethernet0        
```
**3.** View current configuration by using “show interfaces switchport status” command

```
admin@sonic:~$ show int switchport status
```
<img src="https://user-images.githubusercontent.com/61490193/236170364-27cc8f1e-a6f3-401a-90e5-8ed035b0e65e.png" width="65%" height="30%">


**4.** Untagged Vlan Member Assignment on Access Port

a) One Untagged Vlan member can be added on access port by using following command:
 
```
admin@sonic:~$ sudo config vlan member add 2 -u Ethernet0
```

<img src="https://user-images.githubusercontent.com/61490193/236294143-3df37252-dcf4-46d2-bb0d-b8ad104dbb66.png" width="65%" height="30%"> 

b) Adding a Tagged Vlan Member on Access Port

 If a VLAN member is initially added as an untagged member and then later added as a tagged member, this action is not permitted and will result in the following error being displayed:
 
```
admin@sonic:~$ sudo config vlan member add 2 Ethernet0          
```

<img src="https://github.com/ham-xa/SONiC/assets/61490193/b291497d-345b-4fdb-adf9-b1b55cc8751e" width="65%" height="30%">

**Note: This is exisiting VLAN funcationality, This HLD has not proposed any changes/modifications on exisiting behavior of VLAN.**

**5.** Multiple Untagged Vlan Member Assignment on Access Port

Ethernet0 is in Access mode, it can have only 1 untagged member. Configuring More than 1 untagged member on Access Port will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236170322-030f56ac-b829-4273-95c1-193ddd33807a.png" width="65%" height="30%"> 

**6.** Tagged Vlan Member Assignment on Access Port

Ethernet0 is in Access mode, it cannot have tagged members. Configuring tagged member on Access Port will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236170445-2d086077-1c78-45c6-9e23-f03b1b280a14.png" width="65%" height="30%"> 

**7.** IP Assignment on Access Port

Ethernet0 is in Access mode, IP assignment on the access port is not allowed. Configuring IP Assignment on Access Port will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236170194-2423f230-483a-42b7-936c-5939bf0e84ae.png" width="65%" height="30%"> 

**8.** Change Mode from Access to Routed

a) Ethernet0 is in Access mode, switching an access port to routed is not possible until it has an untagged member. Changing  mode from access to routed will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236168568-40e2c53b-d674-49b5-8885-faefac2283e5.png" width="65%" height="30%"> 

b) Ethernet0 is in Access mode, in order to change mode from access to routed, user first has to remove untagged member assigned to it. 
After removal of vlan membership, mode can be changed by using switchport mode command as show below.
Here, in example Interface Ethernet0 is in  "routed" mode which means it has no VLAN membership. It may not have ip address configured either and still qualify as mode "routed". This can be verified by config_db as well after changing mode to "routed" as show below:

<img src="https://github.com/ham-xa/SONiC/assets/61490193/8143f4eb-f36e-4d39-a6b7-19afd252675b" width="65%" height="30%"> 

<img src="https://github.com/ham-xa/SONiC/assets/61490193/77e4dbdf-330c-4750-9978-f5775d7480aa" width="35%" height="20%"> 


**Note: This works in the same way for PortChannels as they do for physical ports.**

**9.**  Change Mode from Access to Trunk

Ethernet0 is in Access mode, switching an access to trunk mode is possible and its untagged member will be retained.  After changing mode from access to trunk, all functionalities of a trunk mode can be used/configred on Port

<img src="https://user-images.githubusercontent.com/61490193/236169645-6911ab37-8384-4c4e-b9d1-5e6af634497d.png" width="65%" height="30%">

We have given examples/usage for switchport mode configuration from routed to access on physical port. This works in the same way for PortChannels as they do for physical ports.

#### Configuring Port & PortChannel from Routed to Trunk 

* Physical Port Configuration

In these examples, Ethernet4 will be configured as “Trunk” from “Routed” on Port.

By default, all ports are in routed mode and have IP assigned. For Switchport configuration we have to remove IP assignment otherwise CLI will show following Error:

**For Ethernet4**

<img src="https://user-images.githubusercontent.com/61490193/236170350-be5d23a1-ba77-4a1e-8cfb-5b9b795c48a9.png" width="65%" height="30%">


Following Steps will be taken to configure “Trunk” from “Routed” on a Port

**1.** IP Removal on  Ethernet4

```
admin@sonic:~$ sudo config interface ip remove Ethernet4 10.0.0.2/31
```

**2.** Configure Ethernet4 as Trunk

```
admin@sonic:~$ sudo config switchport mode Trunk Ethernet4       
```
<img src="https://user-images.githubusercontent.com/61490193/236542261-682ebb20-07bd-4a34-ab9b-dc92bfc95bf0.png" width="65%" height="30%">

**3.** Untagged Vlan Member Assignment on Trunk Port

a) Adding one Untagged Member on Trunk port is allowed. This can be done by follwing command:

```
admin@sonic:~$ sudo config vlan member add 3 -u Ethernet4          
```

<img src="https://user-images.githubusercontent.com/61490193/236294289-44cbceff-a3be-4460-a5c0-a8f219720466.png" width="65%" height="30%">

b) Adding a Tagged Vlan Member on Trunk Port

If a VLAN member is initially added as an untagged member and then later added as a tagged member, this action is not permitted and will result in the following error being displayed:

```
admin@sonic:~$ sudo config vlan member add 3 Ethernet4          
```
<img src="https://github.com/ham-xa/SONiC/assets/61490193/0049f286-c8b4-4533-809f-322e7a5ffd2e" width="65%" height="30%">

**Note: This is existing VLAN functionality, This HLD has not proposed any changes/modifications on exisiting behavior of VLAN.**

**4.** Multiple Untagged Vlan Member Assignment on Trunk Port

Ethernet4 is in Trunk mode, it can have only 1 untagged member. Configuring More than 1 untagged member on trunk Port will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236170542-587403ed-3cf0-465a-9e58-fff7c8130508.png" width="65%" height="30%">


**5.**  Single Tagged Vlan Member Assignment on Trunk Port

Ethernet4 is in trunk mode, it can have single tagged member. Configuring tagged member on trunk Port will show following:


<img src="https://github.com/ham-xa/SONiC/assets/61490193/f2bee94b-b9ae-45a3-b68b-82b0c6686a2f" width="65%" height="30%">

**6.** Tagged Vlan Member Assignment on Trunk Port

Ethernet4 is in trunk mode, it can have multiple tagged members. Configuring tagged member on trunk Port will show following:


<img src="https://user-images.githubusercontent.com/61490193/236294274-61705636-4f9f-4756-9062-58d55334b836.png" width="65%" height="30%">

**7.** IP Assignment on Trunk Port


Ethernet4 is in Trunk mode, IP assignment on the Trunk port is not allowed. Configuring IP Assignment on Trunk Port will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236170307-9c58b1c3-4ad8-4061-9908-4163a833a315.png" width="65%" height="40%">
 
**8.** Change Mode from Trunk to Routed 

a) Ethernet4 is in Trunk mode, Changing Trunk port to routed is not possible until it has an untagged and tagged members. Changing Trunk to routed will show following error:


<img src="https://user-images.githubusercontent.com/61490193/236533178-bba78b3f-f429-4042-8de9-0decbe938f36.png" width="65%" height="40%">

b) Ethernet4 is in trunk mode, in order to change mode from trunk to rounted, user first has to remove untagged and tagged member assigned to it. After removal of vlan membership, mode can be changed by using switchport mode command as show below.
Here, in example Interface Ethernet4 is in  "routed" mode which means it has no VLAN membership. It may not have ip address configured either and still qualify as mode "routed". This can be verified by config_db as well after changing mode "routed" as show below:

 <img src="https://github.com/ham-xa/SONiC/assets/61490193/43a63bc5-bc1c-4001-8197-f0eed4f49246" width="65%" height="40%">

 <img src="https://github.com/ham-xa/SONiC/assets/61490193/00ea0599-0a13-434f-bf41-4a9241c961a6" width="35%" height="20%">

**Note: This works in the same way for PortChannels as they do for physical ports.**

**9.** Change Mode from Trunk to Access

Ethernet4 is in Trunk mode, Changing Trunk port to access is possible and  its  untagged members wll retain. Changing Trunk to access will show following:

<img src="https://user-images.githubusercontent.com/61490193/236170489-5534af51-ce5d-4a39-b2cc-59b3c1660a23.png" width="45%" height="20%">


* PortChannel Configurations

In these examples, PortChannel will be configured as “Trunk” from “Routed”. We will be using some of exisitng Vlans (Vlan2 to Vlan12 created in the above section) for vlan member configuration on Portchannel.

Following Steps will be taken to configure “Trunk” from "Routed" on PortChannel

**1.**  PortChannel Creation 

To configure a PortChannel as Trunk, we first need to create a new PortChannel "PortChannel1010" 

```
admin@sonic:~$ sudo config portchannel add PortChannel1010       
```

**2.** PortChannel Member Addition and PortChannel Trunk Configuration

Ethernet8, Ethernet12 will be added as Portchannel member but first we have to remove IP assigned to Ethernet8 & Ethernet12. After IP address can be removed , we will add Ethernet8 & Ethernet12 as portchannel member on PortChannel1010

<img src="https://user-images.githubusercontent.com/61490193/236294465-ec73c97c-8531-4a59-943c-8aed4e773d45.png" width="65%" height="30%"> 


**3.** Untagged Vlan Member Assignment on Trunk PortChannel

```
admin@sonic:~$ sudo config vlan member add 3 -u PortChannel1010            

Ethernet8 & Ethernet12 has be configured as Portchannel1010 member, they are excluded from interface list.

Those Interfaces which are members of PortChannel will be reomved from interface list in show interfaces switchport
```

<img src="https://user-images.githubusercontent.com/61490193/236294399-38b70aa3-b90d-4e57-8d13-0860375e738b.png" width="65%" height="20%"> 

**4.** Multiple Untagged Member Assignment on Trunk PortChannel

PortChannel1010 is in Trunk mode, it can have only 1 untagged member. Configuring More than 1 untagged member on Trunk Portchannel will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236238520-6fb49e9b-9607-4e5e-b3a2-09b762580e7d.png" width="65%" height="20%"> 

**5.** Tagged Vlan Member Assignment on Trunk PortChannel

PortChannel1010 is in Trunk mode, it can have tagged members. Configuring tagged member on Trunk Port will show following:

```
admin@sonic:~$ sudo config vlan member add -m 4,5,6 PortChannel1010           
```

<img src="https://user-images.githubusercontent.com/61490193/236294479-887748f2-7772-403a-b241-375c767fb172.png" width="65%" height="20%"> 

**6.** IP Assignment on Trunk PortChannel

PortChannel1010 is in Trunk mode, IP assignment on the trunk portchannel is not allowed. Configuring IP Assignment on Trunk PortChannel will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236238492-f5cf68a4-78e9-4981-8377-c825dc49f3b1.png" width="65%" height="20%">


**7.** Change Trunk PortChannel to Routed

PortChannel1010 is in Trunk mode, switching an trunk portchannel to routed is not allowed until it has an untagged member. Switching Trunk PortChannel to routed will show following error:

```
admin@sonic:~$ sudo config switchport mode routed PortChannel1010          
```
<img src="https://user-images.githubusercontent.com/61490193/236238571-ec324daf-53bb-4b6f-9a9e-ea17595d81e6.png" width="65%" height="20%">

**8.** Change Trunk PortChannel to Access
PortChannel1010 is in Trunk mode, switching trunk portchannel to access is not possible and its has tagged members.Switching Trunk PortChannel to access will show following error:

<img src="https://user-images.githubusercontent.com/61490193/236238520-6fb49e9b-9607-4e5e-b3a2-09b762580e7d.png" width="65%" height="40%">

### Warm Boot and Fastboot Design Impact

The existing warm boot/fast boot feature is not affected due to this design.

## SAI API

No SAI API change or addition is needed for this HLD. We will be using the existing SAI API.

## Restrictions/Limitations

This HLD did not consider hybrid switch port mode. We will be adding a separate HLD for hybrid mode. 

### Testing Requirements/Design

#### Unit Test cases

Unit testing will be done at two levels CLI level and Functional Level

CLI Level Tests

* Verify CLI to add a multiple comma separated list of vlan(s)
* Verify CLI to add multiple range of vlan(s)
* Verify CLI to add multiple range of vlan(s) & comma separted vlan(s)
* Verify CLI to add multiple range of vlan(s) with default vlan and show error
* Verify CLI to add multiple range of vlan(s) with invlaid digit and show error
* Verify CLI to add multiple vlan(s) with default vlan and show error
* Verify CLI to add a vlan that already exist and show error
* Verify CLI to delete vlan(s) that doesn't exist and show error 
* Verify CLI to add multiple range of vlan member(s) 
* Verify CLI to delete multiple range of vlan member(s)
* Verify CLI to add vlan(s) with except vlan check
* Verify CLI to delete vlan(s) with except vlan check
* Verify CLI to add vlan member(s) with except vlan member(s) check
* Verify CLI to delete vlan member(s) with except vlan member(s) check
* Verify CLI to add all vlan member(s)
* Verify CLI to delete all vlan member(s)
* Verify CLI to remove vlan assigned to port to switch to routed mode.
* Verify CLI to show error to remove IP assigned on a port to switch from routed to access
* Verify CLI to show error to remove IP assigned on a port to switch from routed to trunk
* Verify CLI to add untagged member on access port 
* Verify CLI to show error on adding tagged members on access port
* Verify CLI to show error on adding  multiple untagged members on access port
* Verify CLI to add tagged members on trunk port
* Verify CLI to  show error on switching from access to routed  port when it has untagged member
* Verify CLI to show error on switching from trunk to routed port when it has tagged members
* Verify CLI to switch from access to trunk port and untagged member retained
* Verify CLI to switch from trunk to access port if no members are  configured to that port
* Verify CLI to show error when switching from trunk to access when the port has tagged members
* Verify CLI to switch from trunk to routed when port has no tagged members


#### Functional Tests cases
* Verify that port modes are set .
* Verify that multiple vlan(s) or range of vlan(s) can be added.
* Verify that multiple vlan member(s) can be added on a trunk port or on trunk portchannel.
* Verify intra-vlan communication between hosts on a single switch
* Verify intra-vlan communication between hosts on two different switches
* Repeat above step for different vlans

### Future Work
 The scope of this HLD is limited to Switchport  Mode “Access” and “Trunk”. In future, support for “Hybrid” will also be provided.

