# Switch Port Modes and Vlan CLI Enhancement


## Revision History

[© xFlow Research Inc](https://xflowresearch.com/)  

|  Revision No| Description | Author  | Contributors |Date |  
| :-------------: |:-------------:| :-----:|:----------:|:-----:|
|0.1| IEEE 802.1Q Tunneling Support| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 14 Dec 2021|
|0.2| Architectural Changes & CLI Commands addition| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86) , [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad) & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 30 Sep 2022|
|0.3| Revision in Title,Switchport modes and CLI enhancements| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86) , [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad) & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 24 Oct 2022|
  
## Table of Contents

- Scope  
- Definitions/Abbreviations  
- Overview  
- Introduction
- Topology Design 
- Architecture Design  
- High-level Design  
  - Switchport Mode  
  - Add Multiple Vlan(s) 
  - Delete Multiple Vlan(s) 
  - Add Multiple Vlan(s) on Trunk Ports  
  - Delete Multiple Vlan(s) on Trunk Ports   
- CLI & YANG Model Configuration Commands & Usage  
  - CLI Configuration Commands 
  - YANG Model Configurations 
  - Example/Usage of Commands 
- SAI API 
- Warm Boot and Fastboot Design Impact  
- Restrictions/Limitations 
- Testing Requirements/Design  
    - Unit Test cases  
- Future Work

## Scope

This high-level design document describes the implementation of switchport modes and CLI enhancements in SONiC.

## Definitions/Abbreviations

| **Sr No** |  **Term**   |  **Definition**                      |
| :------------- |:-------------| :-----|
|  1       |  VLAN_ID      |  Unique identifier for each VLAN     |  
|  2       |  Dot1q        |  IEEE 802.1Q Protocol                |  
|  3       |  Trunk  |  The port is untagged member to one VLAN and tagged member to one or more VLANs  |  
|  4       | Access |  The port is untagged member to only one VLAN|  
|  5       |  Routed | The port is in L3 interface mode                       |  
|  6       |  Hybrid|   The port is multiple untagged and multiple tagged vlan members to  more VLANs         |  


## Overview

This HLD will provide implementation details of switch port modes access and trunk on a Port or on a PortChannel. In this HLD vlan configuration commands are also improved for efficient configuration and management of VLANs.

## Introduction

Switch ports are Layer 2-only interfaces associated with a physical port. A switch port can have three modes: access port, a trunk port, or a hybrid port. We can manually configure a port as an access port, trunk port or hybrid port depending on requirement . Switch ports are used for managing the physical interface and associated Layer 2 protocols and do not handle routing.

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

### Hybrid Mode

In hybrid mode a port possesses the following properties
* Receives  multiple tagged & untagged traffic for  one or more Vlan(s)
* Forwards multiple tagged & untagged traffic for  one or more Vlan(s)

### Sample Topology

![Topology](https://user-images.githubusercontent.com/61490193/208155234-3a04ca08-5ca3-42b3-b679-c1efcacddff2.png)


__*Figure 1: Sample Topology*__

The figure shows that 3 different VLANs are configured with 6 other hosts. The switch ports connected to hosts would be configured as access ports. The ports that connect switches together would be configured as trunk ports.

## Architecture Design

The overall SONiC architecture will remain the same and no new sub-modules will be introduced. Changes are made only in the CLI container and Config_DB.

![Architecture](https://user-images.githubusercontent.com/61490193/217232727-811b98a8-ce9c-4227-a94a-1c83a4825a62.png)


## High-level Design

In this section we will explain sequence diagrams for the implemented features.

### Switch Port Mode

![SwitchPortMode-PortPortChannel](https://user-images.githubusercontent.com/61490193/207826139-3ff0c41a-69af-4018-bf19-c083e1307bf7.png)


__*Figure 2: Sequence Diagram Switch Port mode*__


**1.** Check the existing_port_mode.

**2.** Check if existing_port_mode!=routed then set port mode as access and update config_db.

**3.** Check if type==access and existing_mode==trunk then show an error message to remove tagged members first and update config_db. Moreover, switching between modes also works here.

**4.** Check if type==trunk && existing_mode==trunk then update port mode.

**5.** if mode==access or trunk && want to assign IP it will show error to switch mode to routed first for IP assignment.


**5.** Check if type== routed then show an error message to remove tagged && untagged vlan members first from port and then set_mode entry as “routed” .

**6.** Update PORT table.


__*NOTE: This works same for Adding Switchport Mode on a PortChannel*__


### Add Multiple VLANs
 
![MultipleVlans](https://user-images.githubusercontent.com/61490193/208155973-801f99e5-bc79-4e4d-9db4-be13decf6637.png)


__*Figure 3: Sequence Diagram for adding Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list and return.

**2.** Check if the VLAN is in the range (2-4094) and whether the vid already exists or not.

**3.** Check if vlan id exist

**4.** After checking if it’s in the range, CLI will call for the VLAN_id function.

**5.** Finally, CLI will add the VLAN from the list in the VLAN table.

__*NOTE: This works same for Adding Multiple VLANs on a PortChannel*__


### Delete Multiple VLANs

![DeleteVlan](https://user-images.githubusercontent.com/61490193/208156042-88b5ba0a-4ad4-4cc9-b919-6cf0c1dec281.png)

__*Figure 4: Sequence Diagram for deleting Multiple VLANs*__

**1.** The SONiC CLI will call the multiple vlan list parser which will parse multiple vlan(s) in a list and return.

**2.** Check if the VLAN is in the range .

**3.** Read the existing vlan table and delete vlans(s).


__*NOTE: This works same for Deleting Multiple VLANs from a PortChannel*__


### Add Multiple VLAN member on Trunk Port

![AddMember_trunk](https://user-images.githubusercontent.com/61490193/208156160-cefe6ca7-4092-436e-a209-6da8fc238756.png)


__*Figure 5: Sequence Diagram for Adding VLAN member on Trunk Port*__


**1.**  The SONiC CLI will  Call vlan_member_input_parser to add multiple vlan member(s).

**2.**  Check for vlan_range and return.

**3.**  Check port mode for adding vlan members on a port from the PORT table and return.

**4.**  Add member vlan(s) in multiple commas or range list, all flag & except flag can be used as well.

**5.**  Add the vlan member(s) in the vlan member table. 


__*NOTE: This works same for Adding Multiple VLANs members on a PortChannel*__


### Delete Multiple VLAN member on Trunk Port

![DeleteVlanMember](https://user-images.githubusercontent.com/61490193/208156383-f1ba0a89-f7c4-444c-850b-aa96eb95dc08.png)


__*Figure 6: Sequence Diagram for deleting VLAN member on Trunk Port*__

**1.** The SONiC CLI will call the vlan_member_input_parser parser which will parse multiple vlan(s) in a list and return.

**2.** Check if the members exist in the range .

**3.** Read the existing vlan table and delete vlans(s).


__*NOTE: This works same for Delete Multiple VLANs members from a PortChannel*__

## CLI & YANG Model Configuration Commands & Usage 

## CLI Configuration Commands

**1.** config switchport mode <routed|access|trunk> <member_portname>/<member_portchannel>
 
**2.** config vlan add/del -m <comma separated list, range> <vlan_ids>

**3.** config vlan  member add/del -m <all,except, comma separated list, range> <vlan_ids> <member_portname>/<member_portchannel>

##  Examples/Usage of Commands
  
 The following examples will provide the usage for these new commands that have been added for providing switchport modes and VLAN CLI enhancements.

**1.**  Switchport mode command:

```
  admin@sonic:~$ sudo config switchport mode access Ethernet0
 
  Usage:  This command will add Ethernet0 as access port
  
 ```
 ```
  admin@sonic:~$ sudo config switchport mode trunk Ethernet4
 
  Usage:  This command will add Ethernet4 as trunk port
 ```

 ```
  admin@sonic:~$ sudo config switchport mode access PortChannel1001
 
  Usage:  This command will add PortChannel1001 as access 
  
 ```

 ```
  admin@sonic:~$ sudo config switchport mode trunk PortChannel1002
 
  Usage:  This command will add PortChannel1002 as trunk 
  
 ```
 ```
 admin@sonic:~$ sudo config switchport mode routed Ethernet4

 Usage:  This command will add Ethernet4 as routed port. This is for switching from access or trunk mode to routed mode. 

 ```

 ```
 admin@sonic:~$ sudo config switchport mode routed PortChannel1001

 Usage:  This command will add PortChannel1001 as routed port. This is for switching from access or trunk mode to routed mode. 

 ```
  
 **2.**  Add multiple Vlan(s) using a single command:

```
  admin@sonic:~$ sudo config vlan add -m 100,200,300

  Usage:  This command will add multiple comma separated vlan in a list
 
 Example : The command will create the VLAN "Vlan 100, Vlan 200, Vlan 300" if these do not already exist.

  ```
  
 **3.**  Add range of Vlan(s) using a single command:

```
  admin@sonic:~$ sudo config vlan add -m  100-103

  Usage:  This command will add range of vlan in a list
 
  Example : The command will create the VLAN "Vlan 100, Vlan 101, Vlan 102, Vlan 103" if these do not already exist.

   ***This works with deleting multiple VLANs in the same way***
  ```


**4.**  Add all Vlan(s) as Vlan Member(s) using a single command:

```
  admin@sonic:~$ sudo config vlan member add all Ethernet0

  Usage:  This command will add all existing vlan(s) as vlan member(s) 
 
 Example : Suppose Vlan 100, Vlan 101, Vlan 102 are already existing Vlans. This command will add Ethernet0 as a member of Vlan 100, Vlan 101, Vlan 102. 
  
    ***This command only work for trunk ports***

  ```

  ```
  admin@sonic:~$ sudo config vlan member add all PortChannel1001

  Usage:  This command will add all existing vlan(s) as vlan member(s) on PortChannel1001
 
 Example : Suppose Vlan 100, Vlan 101, Vlan 102 are already existing Vlans. This command will add PortChannel1001 as a member of Vlan 100, Vlan 101, Vlan 102. 
  
    ***This command only work for trunk ports***

  ```

**5.** Add multiple Vlan Member(s) except one specific using a single range command:


  ```
  admin@sonic:~$ sudo config vlan member add -m -e 12-17 Ethernet0
  
  Usage:  This command will add all existing vlan(s) execpt as vlan member(s) 
     
Example: Suppose if Vlan10, Vlan11, Vlan12, Vlan13, Vlan14, Vlan15, Vlan16, Vlan17, Vlan18, Vlan19, Vlan20 are existing Vlans. This command will add Ethernet0 as member of Vlan10, Vlan11, Vlan18, Vlan19, Vlan20

***This command only work for trunk ports***

  ```
  
  ```
  admin@sonic:~$ sudo config vlan member add -m -e 12-17 PortChannel1002
  
  Usage:  This command will add all existing vlan(s) execpt as vlan member(s) 
     
Example: Suppose if Vlan10, Vlan11, Vlan12, Vlan13, Vlan14, Vlan15, Vlan16, Vlan17, Vlan18, Vlan19, Vlan20 are existing Vlans. This command will add PortChannel1002 as member of Vlan10, Vlan11, Vlan18, Vlan19, Vlan20

***This command only work for trunk ports***

  ```

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
* Verify CLI to set the mode of an interface or a PortChannel to access or trunk
* Verify CLI to add a comma separated list of vlan(s)
* Verify CLI to add all vlan(s) except given vlan to member port or portchannel
* Verify CLI to delete list of vlan(s)
* Verify CLI to delete all vlans except given comma separated list of vlan(s)

Functional Level Tests
* Verify that port modes are set .
* Verify that multiple vlan(s) or range of vlan(s) can be added.
* Verify that multiple vlan member(s) can be added on a trunk port or on trunk portchannel.
* Verify intra-vlan communication between hosts on a single switch
* Verify intra-vlan communication between hosts on two different switches
* Repeat above step for different vlans

### Future Work
 The scope of this HLD is limited to Switchport  Mode “Access” and “Trunk”. In future, support for “Hybrid” will also be provided.
