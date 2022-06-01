# SONiC Port Auto FEC Design #

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [High-Level Design](#high-level-design)
- [SAI API Requirements](#sai-api-requirements)
- [SWSS Enhancements](#swss-enhancements)
- [Configuration and management ](#configuration-and-management)
    - [Config command](#config-command)
    - [Show command](#show-command)
- [YANG Model changes](#yang-model-changes)
- [Warmboot and Fastboot Considerations](#warmboot-and-fastboot-considerations)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Design](#testing-design)
    - [VS Test cases](#vs-test-cases)


### Revision

 | Rev |     Date    |       Author        | Change Description                         |
 |:---:|:-----------:|:-------------------:|--------------------------------------------|
 | 0.1 |             |      Sudharsan      | Initial version                            |

### Scope
This document is the design document for port auto fec mode on SONiC. This includes the requirements, CLI change, yang model change and swss change.

### Definitions/Abbreviations
 FEC - Forward Error Correction

### Overview
SONiC supports the following FEC settings:

**None**: FEC is disabled.

**Reed Solomon (RS)**: IEEE 802.3 Clause 108 (CL108) on individual 25G channels and Clause 91 on 100G (4channels). This is the highest FEC algorithm, providing the best bit-error correction.

**Fire Code (FC)**: IEEE 802.3 Clause 74 (CL74). Base-R provides less protection from bit errors than RS FEC but adds less latency.

The behavior of FEC when autoneg is configured is currently not defined. By introducing a new FEC mode called 'auto' this document brings a deterministic approach in  behavior of FEC when autoneg is configured


### Requirements

Primary requirements for configuring FEC are
- Honor the backward compatibility.
- Allow user to enable FEC to be auto negotiated
- Allow user to force set FEC


### High-Level Design
In order to facilitate the behavior of FEC when autoneg is enabled, the SAI attribute SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE was introduced. Before this attribute the behavior is not clearly defined and it is dependent on vendor SAI implementation. 

A new FEC mode called 'auto' is introduced. 
- When FEC mode is set to any of the legacy modes (none, rs, FC) SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will be set to true. User FEC will take precedence
- When FEC mode is seto 'auto' SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will be set to false. Auto negotiated FEC will take precedence.
- To maintain backward compatibility, the SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will be queried and will be used only when it is supported.

### SAI API Requirements

The following is an existing attribute which was recently added to support the FEC override functionality.
```
    /**
     * @brief FEC mode auto-negotiation override status
     *
     * If set to true, any auto-negotiated FEC mode will be
     * overridden by the value configured in SAI_PORT_ATTR_FEC_MODE
     *
     * @type bool
     * @flags CREATE_AND_SET
     * @default false
     */
    SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE,
```
Any SAI vendors who want to make use of this deterministic behavior should implement the above attribute.

In order to get operation FEC the following attributes will be introduced
```
    /**
     * @brief Operational FEC mode
     *
     * If port is down, the returned value should be zero.
     * If auto negotiation is on, the returned value should be the negotiated fec.
     *
     * @type sai_port_fec_mode_t
     * @flags READ_ONLY
     */
    SAI_PORT_ATTR_OPER_FEC,
```

### SWSS Enhancements

As specified in the high level design, the SAI attribute SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will be queried in portsorch. If it is not supported the existing behavior will continue to be in effect. If it is supported and FEC is configured, SAI_PORT_ATTR_FEC_MODE will be set to the configured FEC value followed by SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE set to true.
If FEC is configured as 'auto' by the user SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will be set to false. If AN is set to false, SAI_PORT_ATTR_FEC_MODE will be set to SAI_PORT_FEC_MODE_NONE.
If AN is set to true and FEC is not set, no FEC related attributes will be programmed and existing behavior will continue.
The below table covers different scenarios of what will be programmed in SAI when override is supported and not supported for various combinations of FEC and autoneg

 | Idx | Override supported | Autoneg    |    FEC     | SAI Attributes set by orchagent                                                 |
 |:---:|:------------------:|:----------:|:----------:|---------------------------------------------------------------------------------|
 |  1  |       False        | True/False | none/rs/fc | SAI_PORT_ATTR_FEC_MODE=none/rs/fc                                               |
 |  2  |       False        | True/False | auto       | No FEC attributes will be set                                                   |
 |  3  |       False        | True/False | N/A        | No FEC attributes will be set                                                   |
 |  4  |       True         | True       | none/rs/fc | SAI_PORT_ATTR_FEC_MODE=none/rs/fc SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE=True |
 |  5  |       True         | True       | auto       | SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE=False                                  |
 |  6  |       True         | True       | N/A        | SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE will not be set                        |
 |  7  |       True         | False      | None/rs/fc | SAI_PORT_ATTR_FEC_MODE=none/rs/fc                                               |
 |  8  |       True         | False      | auto       | No FEC attributes will be set                                                   |
 |  9  |       True         | False      | N/A        | No FEC attributes will be set                                                   |
 
 The portsorch will also be responsible to update  operational FEC. This operational mode is applicable only when the mode is 'auto'. When the FEC mode is auto and oper up is detected, SAI_PORT_ATTR_OPER_FEC will be queried and updated in the STATE_DB PORT_TABLE field 'fec'. 

### Configuration and management

#### Config command

No new CLI commands are introduced to support auto FEC. The existing 'config interface fec' is extended to have additional option called 'auto'. If this option is set without autoneg enabled, it will default to 'none'

```
Format:
  config interface fec <interface_name> <mode>

Arguments:
  interface_name: name of the interface to be configured. e.g: Ethernet0
  mode: none/rs/fc/auto

Example:
  config interface fec Ethernet0 auto

Return:
  error message if interface_name or mode is invalid otherwise empty
```

#### Show command

Currently the configured FEC mode is displayed in "show interfaces status" command. With the introduction of mode 'auto' it becomes necessary to display operational FEC. For modes other than auto, the config will match the operational FEC. In case of mode 'auto' the operational FEC will be queried from SAI during oper up sequence using SAI_PORT_ATTR_OPER_FEC. This will be updated to state_db PORT_TABLE field "fec". The value will contain the operational FEC and have the config auto in paranthesis as shown below.
The show command will query the state DB and if there is FEC field, it would be displayed.
If the field is not present, the config will be displayed, similar to the legacy behavior.

````
show interfaces  status
   Interface            Lanes    Speed    MTU    FEC       Alias          Vlan    Oper    Admin             Type    Asym PFC
------------  ---------------  -------  -----  ---------   -------  ------------  ------  -------  ---------------  ----------
   Ethernet0          0,1,2,3     100G   9100    N/A       etp1        routed      up       up   QSFP+ or later         N/A
   Ethernet4          4,5,6,7     100G   9100     rs       etp2  PortChannel1      up       up   QSFP+ or later         N/A
   Ethernet8        8,9,10,11     100G   9100   rs(auto)   etp3        routed      up       up   QSFP+ or later         N/A
````

### YANG model changes

The yang model will be modified to accept additional value 'auto' for FEC

```
leaf fec {
	type string {
		pattern "rs|fc|none|auto";
	}
}
```

### Warmboot and Fastboot Considerations

No impact to warm or fastboot

### Restrictions/Limitations

Since previously the behavior of FEC with autoneg is undefined, if a vendor always gives precedence for auto negotiated FEC over user configured FEC, implementing the new attribute may lead to backward incompatibility issues when SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE is implemented. Since orchagent will always set SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE to true when FEC is explicitly configured, there will be difference in behavior before and after upgrade.

In order to mitigate for those platforms, a db migrator plugin can be introduced which will be executed based on platform check. This plugin will change change 'fec' to 'auto' if the attribute exists in port table and 'autoneg' is enabled. This will make sure that previously when autoneg was given precedence over user configuration, it will continue to happen even after the upgrade.

### Testing Design

#### VS Test cases

1. Add SWSS VS test to query SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE and if supported expect SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE to be set to true when FEC is configured.
2. If SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE is not suppored it should not be set when configuring FEC
3. Set FEC mode to auto and AN=true verify SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE is set to false
4. Set FEC mode to auto and AN=false verify no FEC mode is programmed
