# Interface Range Specification support
Implement support for Interface range Specification via KLISH CLI in SONiC management framework.

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [About This Manual](#about-this-manual)
* [Scope](#scope)
* [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
# Revision
| Rev | Date | Author | Change Description |
|:---:|:----------:|:-----------------------:|----------------------------------------------|
| 0.1 | 05/17/2020 | Tejaswi Goel | Initial version |

# Scope
* Implementation details, syntax, and unit test cases regarding interface range command support via KLISH CLI.
* Interface range specification will not be supported via REST/gNMI.
* Breakout command will not be supported in interface range configuration mode.

# Definition/Abbreviation
NA

# 1 Feature Overview

Interface Range Specification feature support via Klish CLI will allow specification of range of interfaces to which the subsequent commands will be applied. Configuring a range of interfaces will help reduce the time and effort in configuring interfaces.

## 1.1 Requirements

### 1.1.1 Functional Requirements

* Provide ability to create/configure/show/delete range of interfaces via SONiC KLISH CLI.

### 1.1.2 Configuration and Management Requirements
* Support for *interface range* command to configure the range of interfaces in both native and alias mode.
* Extend show and delete interface commands to support range of interfaces.

### 1.1.3 Scalability Requirements
NA
### 1.1.4 Warm Boot Requirements
NA
## 1.2 Design Overview
### 1.2.1 Basic Approach

- KLISH XML changes for adding new CLI view for interface range command.
- Use of VAR tag in KLISH XML to cache existing interfaces list.
- Changes in KLISH actioner script to invoke APIs for range of interfaces.
- Use **interface range <range>** command to configure existing interfaces in the range.
- Use **interface range create <range>** command to create non-existing interfaces in the range and configure all interfaces in the range. Separate "create" cmd is for cases where user wants to configure only existing interfaces in the system but the numbers are not contiguous, so then user will no have to create a complicated cli range. 

### 1.2.2 Container
This feature is implemented within the Management Framework container.

### 1.2.3 SAI Overview
# 2 Functionality
## 2.1 Target Deployment Use Cases
## 2.2 Functional Description
# 3 Design
## 3.1 Overview
* Creation and configuration of interfaces to be done as a single transaction (for the PATCH request a payload is generated including all interfaces in range and the required config). During transaction if error occurs for any interface then none of interfaces in range will be configured and an error with the interface name will be returned.
* Transaction for show and delete of interfaces will be per interface. Since the transaction is per interface, error will be returned for all the interfaces the transaction fails and processing will continue for other interfaces in range.
* Modifying XML file to use correct PTYPE to support number, range, or comma-delimited list of numbers and ranges.
Example: `ETHER_INTERFACE_RANGE` for physical interfaces<br>
```
<PARAM
    name="iface_range_num"
    help="Physical interface range"
    ptype="ETHER_INTERFACE_RANGE"
/>
```
* Using of VAR tag (klish gloal variable) to store existing interfaces.
E.g. Storing existing Ethernet interfaces in VAR tag.
```
<VAR name="ethiflist" dynamic="true">
    <ACTION>python $SONIC_CLI_ROOT/sonic_cli_if_range.py get_available_iflist_in_range ${iface_range_num}</ACTION>
</VAR>
```

## 3.2 DB Changes
### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
## 3.4 SyncD
## 3.5 SAI
## 3.6 User Interface
### 3.6.1 Data Models
NA
### 3.6.2 CLI
#### 3.6.2.1 Interface range commands in native mode

####  3.6.2.1.1 Ethernet interface range:
##### Configure physical interfaces in given range
Syntax: `interface range Ethernet port - port[,port - port...]`
```
sonic(config)# interface range ?
Ethernet         Physical interface range
Vlan             Vlan interface range
PortChannel      PortChannel interface range
create           Create interfaces in range

sonic(config)# interface range Ethernet 1-4,5
<br> `(or)` <br>
sonic(config)# interface range Ethernet1-4,5
<br> `(or)` <br>
sonic(config)# interface range e1-4,5

**Note:** Here is the list of config commands planned for feature's initial release, more subcommands to be added in future.
sonic(conf-if-range-eth**)# ?
channel-group   Configure PortChannel parameters
end             Exit to the exec Mode
exit            Exit from current mode
ip vrf          Bind interface to specified VRF domain
ipv6 enable     Enable IPv6
mtu             Configure MTU
no mtu          Configure interface link MTU
no ip address   Delete IPv4 address(es) on the interface
no ip vrf       Unbind interface from specified VRF domain
no ipv6 enable  Disable IPv6
no shutdown     Enable the interface
no channel-group  Remove from PortChannel group
shutdown        Disable the interface
switchport      Configure switchport parameters
no switchport   Remove switchport paramaters
speed           Configure speed

sonic(conf-if-range-eth**)# mtu 9000
sonic(conf-if-range-eth**)#
```
####  3.6.2.1.2 Vlan interface range:
###### Configure Vlan interfaces existing in given range
Syntax: `interface range Vlan Vlan-id - Vlan-id[,Vlan-id - Vlan-id...]`
```
sonic(config)# interface range Vlan 1-20
sonic(conf-if-range-vl**)# ?
end             Exit to the exec Mode
exit            Exit from current mode
mtu             Configure MTU
ip vrf          Bind interface to specified VRF domain
ipv6 enable     Enable IPv6
no mtu          Configure interface link MTU
no ip address   Delete IPv4 address(es) on the interface
no ip vrf       Unbind interface from specified VRF domain
no ipv6 enable  Disable IPv6

sonic(conf-if-range-vl**)# mtu 9000
sonic(conf-if-range-vl**)#
```
###### Create Vlan interfaces in given range
Syntax: `interface range create Vlan Vlan-id - Vlan-id[,Vlan-id - Vlan-id...]`
```
sonic(config)# interface range create ?
Vlan             Vlan interface range
PortChannel      PortChannel interface range

sonic(config)# interface range create Vlan 3-4,10,11
sonic(conf-if-range-vl**)#
```
###### Delete Vlan interfaces existing in given range
Syntax: `no interface Vlan Vlan-id - Vlan-id[,Vlan-id - Vlan-id...]`
```
sonic(config)# no interface Vlan 1-20
sonic(config)#
```
#### 3.6.2.1.3 PortChannel interface range:
###### Configure PortChannel interfaces existing in given range
Syntax: `interface range PortChannel Po-id - Po-id[,Po-id - Po-id...]`
```
sonic(config)# interface range PortChannel 1-40
sonic(conf-if-range-po**)# ?
end             Exit to the exec Mode
exit            Exit from current mode
mtu             Configure MTU
ip              Interface Internet Protocol config commands
ipv6            Interface Internet Protocol v6 config commands
no mtu          Configure interface link MTU
no ip address   Delete IPv4 address(es) on the interface
no ip vrf       Unbind interface from specified VRF domain
no ipv6 enable  Disable IPv6
no shutdown     Enable the interface
shutdown        Disable the interface
switchport      Configure switchport parameters
no switchport   Remove switchport paramaters

sonic(conf-if-range-po**)# mtu 9000
sonic(conf-if-range-po**)#
```
###### Create PortChannel interfaces in given range
Syntax: `interface range create PortChannel Po-id -Po-id[,Po-id - Po-id...]`
```
sonic(config)# interface range create ?
Vlan             Vlan interface range
PortChannel      PortChannel interface range

sonic(config)# interface range create PortChannel 3-4,10,11
sonic(conf-if-range-po**)#
```
###### Delete PortChannel interfaces existing in given range
Syntax: `no interface PortChannel Po-id - Po-id[,Po-id - Po-id...]`
```
sonic(config)# no interface Portchannel 1-30
sonic(config)#
```
####  3.6.2.1.4 Show interfaces existing in given range
```
sonic# show interface Ethernet 0-20
sonic# show interface Vlan 1-20,40
sonic# show interface PortChannel 1-20
```
#### 3.6.2.2 Interface range Commands in alias mode
##### Configuring a Range of Interfaces
```
sonic(config)# interface range Eth 1/1-1/20
sonic(conf-if-range-eth**)# mtu 9000
```
#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
### 3.6.3 REST API Support
Not supported
#### 3.6.3.1 GET

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug
# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test
The following test cases will be tested using CLI interface only:
- Testing the creation of range of Vlan or PortChannel interfaces.
- Testing all commands supported in interface range configuration mode for Ethernet/VLan/PortChannel.
- Testing all delete & show commands with range of interfaces as input. 
#### Configuration via CLI

##### Range input pattern in native mode
| Test Name | Test Description |
| :------ | :----- |
| Verify number, range, or comma-delimited list of numbers and ranges is accepted | e.g. `show interface Ethernet 0-10,20,44` |
| Verify range in reverse works | e.g. Ethernet 10-0 | 
| Veriry different patterns during range specification | e.g. e1-4,8 or Ethernet1-4,8 or Ethernet 0-20 |
| Verify dupicates in range works and show ouput has no duplicate entries | e.g. `show interface Ethernet 8,8,8` | 

##### Range input pattern in alias mode
| Test Name | Test Description |
| :------ | :----- |
| Verify number, range, or comma-delimited list of numbers and ranges is accepted | e.g. `show interface Eth 1/1-1/10,1/5/1` |
| Verify range in reverse works | cmd e.g. `sonic(config)# interface range Eth 1/10-1/1` | 
| Veriry different patterns during range specification | e.g. e1/1/1-1/10 or Eth 1/1-1/10 or Eth1/1-1/10 |
| Verify dupicates in range works and show ouput has no duplicate entries | e.g. `show interface Ethernet 8,8,8` | 

##### VLAN, PortChannel 
| Test Name | Test Description |
| :------ | :----- |
| Create of range of interfaces | cmd e.g. `interface range create vlan 1-20` | 
| Config MTU/shutdown/no shutdown working for all patterns in range | Verify config using show cmd, e.g. `show interface Vlan/PortChannel <range>` |
| Delete range of Vlan interfaces | cmd e.g `no interface Vlan 1-30` |

##### Ethernet 
| Test Name | Test Description |
| :------ | :----- |
| Config MTU/shutdown/no shutdown working for all subsets in range | Verify config using show cmd, e.g. `show interface Ethernet <range>` |
| Remove IP/IPv6 address for given range of interfaces | Verify using show cmd |

#### Show range of interfaces via Klish CLI
| Test Name | Test Description |
| :------ | :----- |
| show range of Ethernet interfaces | Verify EEPROM information in State DB |
| show range of Vlan interfaces | Verify for duplicat |
| show range of PortChannel interfaces | Verify all interfaces in range displayed |


#### Automation
Spytest cases will be implemented for new CLI.
