# SONiC Port Auto Negotiation Design #

## Table of Content 

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

### Scope
This document is the design document for port auto negotiation feature on SONiC. This includes the requirements, CLI change, DB schema change, swss change.

### Definitions/Abbreviations 
N/A
 
### Overview

The IEEE 802.3 standard defines a set of Ethernet protocols that are comprised of speed rate and interface type. It allows for configuring multiple values at the same time for port provisioning and advertising to the remote side. However, on SONiC, user can configure the speed of port, and user can configure auto negotiation mode via config DB. Port attributes such as interface type, advertised speeds, advertised interface types are not supported.

The feature in this document is to address the above issues.

### Requirements

The main goal of this document is to discuss the design of following requirement:

- Allow user to configure auto negotiation via CLI
- Allow user to configure advertised speeds
- Allow user to configure interface type
- Allow user to configure advertised interface types

### Architecture Design

This feature does not change the existing SONiC architecture.

This feature introduces a few new CLI commands which will fit in sonic-utilities. And this feature also requires to change the configuration flow for port auto negotiation attributes which will be covered in orchagent.

### High-Level Design

- SAI API requirements is covered in section [SAI API](#sai-api).
- 4 new CLI commands will be added to sonic-utilities sub module. These CLI commands support user to configure auto negotiation mode, advertised speeds, interface type and advertised interface types for a given interface. See detail description in section [CLI Enhancements](#cli-enhancements).
- Port speed setting flow will be changed in orchagent of sonic-swss. See detail description in section [SWSS Enhancements](#swss-enhancements).
- A few new fields will be added to existing table in APP_DB and CONFIG_DB to support auto negotiation attributes. See detail description in section [Config DB Enhancements](#config-db-enhancements) and [Application DB Enhancements](#application-db-enhancements).

### SAI API

Currently, SAI already defines a few port attributes to support port auto negotiation. Please note that `SAI_PORT_ATTR_ADVERTISED_INTERFACE_TYPE` is a new attribute introduced in SAI 1.7.1. As SAI 1.7.1 is not merged to master branch at this time, vendors need to implement this attribute in their SAI implementation. Vendor specified SAI implementation is not in the scope of this document. The related port attributes are listed below:
```cpp
    /**
     * @brief Auto Negotiation configuration
     *
     * @type bool
     * @flags CREATE_AND_SET
     * @default false
     */
    SAI_PORT_ATTR_AUTO_NEG_MODE,
    /**
     * @brief Speed in Mbps
     *
     * On get, returns the configured port speed.
     *
     * @type sai_uint32_t
     * @flags MANDATORY_ON_CREATE | CREATE_AND_SET
     */
    SAI_PORT_ATTR_SPEED,
    /**
     * @brief Query/Configure list of Advertised port speed (Full-Duplex) in Mbps
     *
     * Used when auto negotiation is on. Empty list means all supported values are enabled.
     *
     * @type sai_u32_list_t
     * @flags CREATE_AND_SET
     * @default empty
     */
    SAI_PORT_ATTR_ADVERTISED_SPEED,
    /**
     * @brief Configure Interface type
     *
     * @type sai_port_interface_type_t
     * @flags CREATE_AND_SET
     * @default SAI_PORT_INTERFACE_TYPE_NONE
     */
    SAI_PORT_ATTR_INTERFACE_TYPE,

    /**
     * @brief Configure advertised interface type list
     *
     * Used when auto negotiation is on. Empty list means all supported values are enabled.
     *
     * @type sai_s32_list_t sai_port_interface_type_t
     * @flags CREATE_AND_SET
     * @default empty
     */
    SAI_PORT_ATTR_ADVERTISED_INTERFACE_TYPE,
```

SAI API must return error if any of the given attributes is not supported.

### Configuration and management 

#### CLI Enhancements 

A few new CLI commands are designed to support port auto negotiation.

##### Config auto negotiation mode

```
Format:
  config interface autoneg <interface_name> <mode>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  mode: auto negotiation mode, can be either "enabled" or "disabled"

Example:
  config interface autoneg Ethernet0 enabled
  config interface autoneg Ethernet0 disabled

Return:
  error message if interface_name or mode is invalid otherwise empty
```

##### Config advertised speeds

Configuring advertised speeds takes effect only if auto negotiation is enabled. If auto negotiation is disabled, this command still saves advertised speeds value to CONFIG_DB, orchagent will not pass the value to SAI until auto negotiation is enabled.

```
Format:
  config interface advertised-speeds <interface_name> <speed_list>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  speed_list: a list of speeds to be advertised or "all". e.g: 40000,100000.

Example:
  config interface advertised-speeds Ethernet0 40000,100000
  config interface advertised-speeds Ethernet0 all

Return:
  error message if interface_name or speed_list is invalid otherwise empty

Note:
  speed_list value "all" means all supported speeds 
```

This command always replace the advertised speeds instead of append. For example, say the current advertised speeds value are "10000,25000", if user configure it with `config interface advertised-speeds Ethernet0 40000,100000`, the advertised speeds value will be changed to "40000,100000".

##### Config interface type

Configuring interface type takes effect only if auto negotiation is disabled. If auto negotiation is enabled, this command still saves interface type value to CONFIG_DB, orchagent will not pass the value to SAI until auto negotiation is disabled.

```
Format:
  config interface interface-type <interface_name> <interface_type>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  interface_type: interface type, valid value include: KR4, SR4 and so on. A list of valid interface type could be found at saiport.h.

Example:
  config interface interface-type Ethernet0 KR4

Return:
  error message if interface_name or interface_type is invalid otherwise empty
```

##### Config advertised interface types

Configuring advertised interface types takes effect only if auto negotiation is enabled. If auto negotiation is disabled, this command still saves advertised interface types value to CONFIG_DB, orchagent will not pass the value to SAI until auto negotiation is enabled.

```
Format:
  config interface advertised-interface-types <interface_name> <interface_type_list>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  media_type_list: a list of interface types to be advertised or "all". e.g: KR4,SR4.

Example:
  config interface advertised-interface-types Ethernet0 KR4,SR4
  config interface advertised-interface-types all

Return:
  error message if interface_name or interface_type_list is invalid otherwise empty

Note:
  media_type_list value "all" means all supported interface type 
```

This command always replace the advertised interface types instead of append. For example, say the current advertised interface types value are "KR4,SR4", if user configure it with `config interface advertised-interface-types Ethernet0 CR4`, the advertised interface types value will be changed to "CR4".

#### Config DB Enhancements  

SONiC already defined two fields related to port speed setting: **speed**, **autoneg**. 3 new fields **adv_speeds**, **interface_type**, **adv_interface_types** will be added to **PORT** table:

	; Defines information for port configuration
	key                     = PORT|port_name                 ; configuration of the port
	; field                 = value
    ...
	adv_speeds              = STRING                         ; advertised speed list
	interface_type          = STRING                         ; interface type
	adv_interface_types     = STRING                         ; advertised interface types

Valid value of the new fields are described below:

- adv_speeds: string value "all" or a list of speed value separated by commas. For example: "50000,100000", "all".
- interface_type: valid interface type value defined in IEEE 802.3. For example: "CR4", "SR4" and so on.
- adv_interface_types: string value "all" or a list of interface type values defined in IEEE 802.3. For example: "CR4,KR4,SR4", "all".

#### Application DB Enhancements

The change in APP_DB is similar to CONFIG_DB. 3 new fields **adv_speeds**, **interface_type**, **adv_interface_types** will be added to **PORT_TABLE** table:

	; Defines information for port configuration
	key                     = PORT_TABLE:port_name           ; configuration of the port
	; field                 = value
    ...
	adv_speeds              = STRING                         ; advertised speed list
	interface_type          = STRING                         ; interface type
	adv_interface_types     = STRING                         ; advertised interface types

Valid value of the new fields are the same as **PORT** table in CONFIG_DB.

Here is the table to map the fields and SAI attributes:
| **Parameter**       | **sai_port_attr_t**
|---------------------|------------------------------------------------|
| adv_interface_types | SAI_PORT_ATTR_ADVERTISED_INTERFACE_TYPE        |
| adv_speeds          | SAI_PORT_ATTR_ADVERTISED_SPEED                 |
| autoneg             | SAI_PORT_ATTR_AUTO_NEG_MODE                    |
| interface_type      | SAI_PORT_ATTR_INTERFACE_TYPE                   |
| speed               | SAI_PORT_ATTR_SPEED                            |

#### SWSS Enhancements

The current SONiC speed setting flow in PortsOrch can be described in following pseudo code:

```
port = getPort(alias)
if autoneg changed:
    setPortAutoNeg(port, autoneg)

if autoneg == true and speed is set:
    setPortAdvSpeed(port, speed)
else if autoneg == false and speed is set:
    setPortSpeed(port, speed)
```

The new SONiC speed setting flow can be described in following pseudo code:

```
port = getPort(alias)
if autoneg changed:
    setPortAutoNeg(port, autoneg)

if autoneg == true:
    speed_list = vector()
    if adv_speeds is set:
        speed_list = adv_speeds
    else if speed is set: // for backward compatible
        speed_list.push_back(speed)
    else:
        speed_list = all_supported_speeds
    setPortAdvSpeed(port, speed_list)

    interface_type_list = vector()
    if adv_interface_types is set:
        interface_type_list = adv_interface_types
    else:
        interface_type_list = all_supported_interface_types
    setPortAdvInterfaceType(port, interface_type_list)
else:
    if speed is set:
        setPortSpeed(port, speed)
    if interface_type is set:
        setInterfaceType(port, interface_type)
```

#### portsyncd and portmgrd Consideration

No changes for portsyncd and portmgrd.

Due to historical reason, portsyncd and portmgrd both handle **PORT** table changes in **CONFIG_DB** and write **APPL_DB** according to configuration change. portmgrd handles fields including "mtu", "admin_status" and "learn_mode"; portsyncd handles the rest fields. 

#### Port Breakout Consideration

No changes for port breakout.

Currently, when user change port breakout mode, SONiC removes the old ports and create new ports in CONFIG_DB according to platform.json. For example, say Ethernet0 supports breakout mode 1x100G and 2x50G. The platform.json looks like:

```json
"interfaces": {
	"Ethernet0": {
	    "index": "1,1,1,1",
	    "lanes": "0,1,2,3",
	    "alias_at_lanes": "Eth1/1, Eth1/2, Eth1/3, Eth1/4",
	    "breakout_modes": "1x100G,2x50G"
	 },
 	 ...
 }
```

**Without port auto negotiation feature**,  the current configuration of Ethernet0 is:

```json
"Ethernet0": {
    "alias": "Eth1/1",
    "lanes": "0,1,2,3",
    "speed": "100000",
    "index": "1"
}
```

User change the port breakout mode via command `config interface breakout Ethernet0 2x50G`. According to platform.json, the configuration of Ethernet0 will change to:

```json
"Ethernet0": {
    "alias": "Eth1/1",
    "lanes": "0,1",
    "speed": "50000",
    "index": "1"
},
"Ethernet2": {
    "alias": "Eth1/3",
    "lanes": "2,3",
    "speed": "50000",
    "index": "1"
}
```

However, **with port auto negotiation feature**, the original configuration of Ethernet0 could be:

```json
"Ethernet0": {
    "alias": "Eth1/1",
    "lanes": "0,1,2,3",
    "speed": "100000",
    "index": "1",
    "autoneg": "true",
    "adv_speeds": "10000,25000,40000,50000,100000",
    "adv_interface_types": "CR4,KR4,SR4"
}
```

So if user breakout the port to 2x50G mode and we simply copy the old configuration to new ports, there are a few issues:

1. For field adv_speeds, value "10000,25000,40000,100000" are not suitable for 2x50G mode. The same issue also may apply to field adv_interface_types.
2. Since autoneg is true and port speed could be auto negotiated to value which is not 50G, it would confuse user: we breakout to 2x50G mode but the actual port speed is not 50G.

So I would suggest to not set the value of autoneg, adv_speeds and adv_interface_types in such situation. Then the configuration after port breakout is still:

```json
"Ethernet0": {
    "alias": "Eth1/1",
    "lanes": "0,1",
    "speed": "50000",
    "index": "1"
},
"Ethernet2": {
    "alias": "Eth1/3",
    "lanes": "2,3",
    "speed": "50000",
    "index": "1"
}
```

I choose this solution because:

1. It's simple. No code changes are required to existing port breakout implementation.
2. It's clear. User gets two new ports with expected speed.
3. It's backward compatible.
4. User can still set auto negotiation parameter after port breakout.

However, there is still one problem. As port breakout mode is saved in CONFIG_DB like:

```json
"BREAKOUT_CFG":
{
    "Ethernet0": {
        "brkout_mode": "1x100G"
    },
    ...
}
```

If auto negotiation is enabled on Ethernet0 and its speed is negotiated to a value which is not 100G, what will happen if user change the breakout mode? Since this problem exists even if without port auto negotiation feature, I suppose port breakout implementation should properly handle it (or it has been already handled).

### Warmboot and Fastboot Design Impact

N/A

### Restrictions/Limitations

N/A

### Testing Requirements/Design

#### Unit Test cases

For sonic-utilities, we will leverage the existing unit test framework to test. A few new test cases will be added:

1. Test command `config interface autoneg <interface_name> <mode>`. Verify the command return error if given invalid interface_name or mode.
2. Test command `config interface advertised-speeds <interface_name> <speed_list>`. Verify the command return error if given invalid interface name or speed list.
3. Test command `config interface interface-type <interface_name> <interface_type>`. Verify the command return error if given invalid interface name or interface type.
4. Test command `config interface advertised-interface-types <interface_name> <interface_type_list>`. Verify the command return error if given invalid interface name or interface type list.

For sonic-swss, there is an existing test case [test_port_an](https://github.com/Azure/sonic-swss/blob/master/tests/test_port_an.py). The existing test case covers autoneg and speed attributes on both direct and warm-reboot scenario. So new unit test cases need cover the newly supported attributes:

1. Test attribute adv_speeds on both direct and warm-reboot scenario. Verify SAI_PORT_ATTR_ADVERTISED_SPEED is in ASIC_DB and has correct value.
2. Test attribute interface_type on both direct and warm-reboot scenario. Verify SAI_PORT_ATTR_INTERFACE_TYPE is in ASIC_DB and has correct value.
3. Test attribute adv_interface_types on both direct and warm-reboot scenario. Verify SAI_PORT_ATTR_ADVERTISED_INTERFACE_TYPE is in ASIC_DB and has correct value.

#### System Test cases

Will leverage sonic-mgmt to test this feature.

TBD

### Open/Action items - if any

- CLI commands cannot validate the supported speeds and supported interface types for now
