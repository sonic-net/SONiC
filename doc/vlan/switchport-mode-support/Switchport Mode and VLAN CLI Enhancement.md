# Switch Port Modes and Vlan CLI Enhancement


## Revision History

[© xFlow Research Inc](https://xflowresearch.com/)  


|  Revision No| Description | Author  | Contributors |Date |  
| :-------------: |:-------------:| :-----:|:----------:|:-----:|
|0.1| IEEE 802.1Q Tunneling Support| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 14 Dec 2021|
|0.2| Architectural Changes & CLI Commands addition| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 30 Sep 2022|
|0.3| Revision in Title,Switchport modes and CLI enhancements| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 24 Oct 2022|
|0.4| Addition of Use Cases, Db Migrator and Config-Db Enchanements| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Rida Hanif](https://github.com/ridahanif96) , [Umar Asad](https://github.com/MuhammadUmarAsad), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 06 Mar 2023|

  
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
- CLI & YANG Model Configuration 
  - CLI Configuration Commands 
  - YANG Model Configurations 
     - Yang New Type for Port and PortChannel
     - Yang Leaf for Port and PortChannel
- Config DB Enhancement
- Db Migrator Enhancement 
- Example/Usage of Commands
   - Examples of Switchport mode Command
      - Switching Ports & PortChannels mode from Routed to Access/Trunk 
      - Displaying Switchport modes on Port & Port Channel
      - Switching Ports & PortChannels mode from Access to Routed/Trunk
      - Switching Ports & PortChannels mode from Trunk to Routed/Access
   - Examples of VLAN CLI Enchanement Command
      -  Add multiple Vlan(s) using a single command
      -  Add range of Vlan(s) using a single command
      -  Add all Vlan(s) as Vlan Member(s) using a single command
      - Add all Vlan(s) as Vlan Member(s) excluding a range of vlans using a single command
      - Multiple Vlan command Truncate Examples
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

## CLI & YANG Model Configuration Commands & Usage 

### CLI Configuration Commands

**1.** config switchport mode <routed|access|trunk> <member_portname>/<member_portchannel>
 
**2.** config vlan add/del -m <comma separated list, range> <vlan_ids>

**3.** config vlan  member add/del -m <all,except, comma separated list, range> <vlan_ids> <member_portname>/<member_portchannel>


### YANG Model Configuration 

For Mode attribute, a new type is defined in YANG Model for adding support of "mode" in PORT_TABLE & PORTCHANNEL_TABLE.

#### YANG New type for PORT_TABLE & PORTCHANNEL_TABLE

    typedef switchport_mode {
        type string {
            pattern "routed|access|trunk";
                    }
        description
            "SwitchPort Modes for Port & PortChannel";
                         }

#### YANG Leaf for PORT_TABLE & PORTCHANNEL_TABLE

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
As there is a change in schema for PORT & PORT CHANNEL Table in config DB . We have added support to migrate the entries to the new schema in db_migrator.py. A new “mode” field is added whose default value is “trunk” to map it with the old configurations for backward compatibility.

Exisitng Before Migration PORT TABLE Schema in Config_DB

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

After migration PORT TABLE Schema in Config_DB

If a VLAN is configured in old configurations its mode will be set as “trunk” for existing configurations.

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

Exisitng Before Migration PORTCHANNEL TABLE Schema in Config_DB

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

After migration PORTCHANNEL TABLE Schema in Config_DB

If a VLAN is configured in old configurations its mode will be set as “trunk” for existing configurations.

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


###  Examples/Usage of SwitchPort mode Command

####  Switching Port & PortChannel mode from routed to access/trunk 

Following example shows usage of switchport modes “access” and “trunk” and switching of port mode from routed to access/trunk. Before switching mode from routed to access/trunk, the user must remove IP first. After the mode has been switched to access/trunk there will be no untagged/tagged vlan member(s) assigned (Community calls this situation a blackhole). 

```
  admin@sonic:~$ sudo config switchport mode access Ethernet0
 
  Usage:  This command will change Ethernet0 mode from routed to access

 ```
 ![Access-mode](https://user-images.githubusercontent.com/61490193/223187133-584d28cd-e662-40a5-9621-a4a86e473544.png)
 
```
  admin@sonic:~$ sudo config switchport mode trunk Ethernet4
 
  Usage:  This command will change Ethernet4 mode from routed to trunk

 ```
   
   ![trunk](https://user-images.githubusercontent.com/61490193/223190390-dcc75cde-6dae-40eb-8c42-1981ed0b3575.png)

 ```
  admin@sonic:~$ sudo config switchport mode access PortChannel0001
 
  Usage:  This command will change PortChannel0001 mode from routed to access 
  
 ```
 ![PortChannel-access](https://user-images.githubusercontent.com/61490193/223190449-b0b7eab3-ba0b-4c82-baa3-988ae22a787d.png)



 ```
  admin@sonic:~$ sudo config switchport mode trunk PortChannel0002
 
  Usage:  This command will change PortChannel0002 mode from routed to trunk
  
 ```
 ![PortChannel-trunk](https://user-images.githubusercontent.com/61490193/223190536-16ad5af8-ebf8-481a-932a-8879cecba133.png)


After configuring port and port channel to “access” and “trunk”. We have added untagged and tagged members on the ports and portchannel using the same commands as has been used before. 


![Vlan-Brief](https://user-images.githubusercontent.com/61490193/223190727-b478448a-806f-4020-bd8f-71dc3eddedd7.png)


####  Displaying switchport modes on Port & Port Channel

Show interface status output is modified, the column header named “Vlan” is renamed as “Mode” to depict “access” and “trunk” modes.

Existing Output:

![Show-Int-Stat-old](https://user-images.githubusercontent.com/61490193/223190797-d47cf8fb-e6c6-406a-bb73-b0af8721e3b4.png)


Modified Output:


![New-Int-Stat](https://user-images.githubusercontent.com/61490193/223196559-e4666118-d022-4a23-85f0-f0ee96d61654.png)


#### Switching Ports & PortChannels mode from Access to Routed/Trunk

We are giving examples for physical ports, these commands work in the same way for PortChannels as they do for physical ports.

#### Switch from access to routed
In Switching from access to routed, user need to remove the untagged member first otherwise, the command will give an error:

![Switch-Access-Route](https://user-images.githubusercontent.com/61490193/223190966-7498a860-98d0-456f-8acb-241612a51790.png)


#### Switch from access to trunk
Switching from access to trunk will work without any error and untagged member added in the access mode is retained:

![Switch-Access-Trunk](https://user-images.githubusercontent.com/61490193/223190991-aeef8fd6-e71a-4bbf-9862-42ea4613002a.png)

To verify the port mode user can make of “show interfaces status” command


#### Switching Ports & PortChannels mode from Trunk to Routed/Access

#### Switch from trunk to routed
Switch from trunk to routed user need to remove the untagged/tagged member(s) first otherwise, the command will give an error:

![Switch-Trunk-Routed](https://user-images.githubusercontent.com/61490193/223191099-c037754d-c221-43b6-874e-6dbcd4eae639.png)


#### Switch from trunk to access
Switch from trunk to access, user need to remove the tagged members firstotherwise, the command will give an error:

![Switch-Trunk-Access](https://user-images.githubusercontent.com/61490193/223191151-cea02ab6-7755-4c7c-994c-72bbbaeccc56.png)



###  Examples/Usage of VLAN CLI Enchancemnts Command

 #### Add multiple Vlan(s) using a single command:

```
  admin@sonic:~$ sudo config vlan add -m 100,200,300

  Usage:  This command will add multiple comma separated vlan in a list
 
 Example : The command will create the VLAN "Vlan 100, Vlan 200, Vlan 300" if these do not already exist.

  ```
  ![Vlan-Comma Separted](https://user-images.githubusercontent.com/61490193/223199523-c6e7ddb4-023a-4c9d-8a49-ec7d637bcd31.png)


 ####  Add range of Vlan(s) using a single command:

```
  admin@sonic:~$ sudo config vlan add -m 10-20

  Usage:  This command will add range of vlan in a list
 
  Example : The command will create the VLAN "Vlan10 Vlan11, Vlan12, Vlan13, Vlan14, Vlan15, Vlan16, Vlan17, Vlan18, Vlan19, Vlan20" if these do not already exist.

  ```
![1](https://user-images.githubusercontent.com/61490193/223469654-38c17b89-cc07-4b5d-92b2-4e1dd19370de.png)

  
 The “-m” flag works the same way for deleting multiple VLANs as it does for adding vlans.


 ####  Add all Vlan(s) as Vlan Member(s) using a single command:

```
  admin@sonic:~$ sudo config vlan member add all Ethernet20

  Usage:  This command will add all existing vlan(s) as vlan member(s) 
 
 Example : Suppose Vlan2, Vlan3, Vlan4, Vlan5, Vlan6, Vlan7, Vlan8, Vlan9 are existing Vlans. This command will add Ethernet20 as a tagged member of Vlan2, Vlan3, Vlan4, Vlan5, Vlan6, Vlan7, Vlan8, Vlan9
 
   ***This command only work for trunk ports***

  ```
  
![Vlan-MultipleAdd](https://user-images.githubusercontent.com/61490193/223199652-01b5ed35-15c0-480c-ad78-c78566db62df.png)


 ####  Add all Vlan(s) as Vlan Member(s) excluding a range of vlans using a single command:

  ```

  admin@sonic:~$ sudo config vlan member add -m -e 12-17 PortChannel0003

  Usage:  This command will add all existing vlan(s) execpt some specific as vlan member(s) 
 
 Example : Suppose if Vlan10, Vlan11, Vlan12, Vlan13, Vlan14, Vlan15, Vlan16, Vlan17, Vlan18, Vlan19, Vlan20 are existing Vlans. This command will add PortChannel0003 as member of Vlan10, Vlan11, Vlan18, Vlan19, Vlan20

    ***This command only work for trunk ports***

  ```
  
  ![Portchannel-except](https://user-images.githubusercontent.com/61490193/223192175-396b487b-fe75-43f6-8598-d9e74773dd58.png)


#### Multiple VLans command truncate:

Multiple Vlan commands for adding Vlans (comma separated or in range) will truncate as soon as it finds any Vlan already exists even at the start or in the middle.  Deletion of Vlans works the same way and the command will truncate as soon as it finds a Vlan doesn’t exist. So, a user has to take care that a vlan should not already exist in the given range if he/she is trying to add multiple vlans.  Similarly, a user has to take care that all the vlans should exist in the given range if he/she is trying to delete multiple vlans. Following examples will make a more clear understanding of this fact.


Example: Suppose Vlan 2 already exists then multiple range vlan command will truncate at the start and no vlan will be added as a result.

![Vlan-Add-Error](https://user-images.githubusercontent.com/61490193/223192280-86424b5a-9cb5-4bea-94ea-c951522fb3a6.png)


Example: Suppose Vlan 28 already exists then multiple range vlan command will truncate in the middle. Such that Vlan26 and Vla27 will be added and then the command will truncate with an error.

![Vlan-Add-Middle](https://user-images.githubusercontent.com/61490193/223192341-7085c38d-421e-440c-8152-474b30a88d82.png)


Example: Suppose Vlan 25 already exists then multiple range vlan command will truncate at the end.  Such that Vlan20 to Vlan24 will be added and then the command will truncate with an error.


![Vlan-Add-Last](https://user-images.githubusercontent.com/61490193/223192431-d1a603a9-dcaf-42fb-bfad-23dde5e22437.png)

We have given examples only for addition of vlans, commands for deletion of vlans will show similar behavior. 

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

