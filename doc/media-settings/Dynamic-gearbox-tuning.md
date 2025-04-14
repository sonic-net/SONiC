# SONiC Dynamic Gearbox Tuning Design Plan

## Revision

  | Version |     Date    |       Author           | Description                |
  |:-------:|:-----------:|:----------------------:|----------------------------|
  | 0.1     | 19/12/2024  | Jan Mazurek            | Initial version            |

## Summary

This document describes the design plan to implement dynamic gearbox (external phy) tuning for SONiC-supported switches.

## Definitions / Abbreviations

 | Term       |  Definition / Abbreviation                                            |
 |------------|-----------------------------------------------------------------------|
 | Tuning     | Process by which specific pre-emphasis is applied to a transmitted signal to cancel out noise.
 | Gearbox    | An external phy connected to some phsyical ports on the switch, designed to either change serdes speeds or retransmit signals.
 | line-side  | The side of a gearbox facing the physical ports on a switch.
 | system-side| The side of a gearbox facing the internal switch ASIC.
 | APPL_DB    | Application Database
 | pmon       | Platform daemon controller
 | xcvrd      | daemon in charge of updating APPL_DB with transceiver information
 | orchagent  | process which monitors APPL_DB and makes SAI calls when certain events are triggered
 | SAI        | API library for programming switch hardware

## Context

When ethernet traffic travels over a medium like copper or fiber, noise propagates over time in the signal, reducing its clarity and increasing the risk of CRC errors or link issues. To this end, we introduce pre-emphasis noise to the signal when it is transmitted over a given medium in an effort to cancel out the natural noise which accumulates as the signal travels. We determine the amount of pre-emphasis noise to apply to each signal based on medium type and serdes rate of the transceiver. The pre-emphasis noise applied is represented by “tuning values”, which are used to program the hardware at each port to allow for the tunings to be applied. In switches where gearboxes are present, tuning values must be applied at each point of signal transmission, so tuning support must be available for the switch ASIC internal phys as well as the system-side and line-side ports of the gearboxes.  
Currently gearbox tuning values are set manually by reading a hard-coded xml file and programming the hardware at system start. This means we need to manually set the tuning values any time that a customer wishes to change transceiver type/medium/speed.

For further background on Media tuning:

* [Media-based Port Settings](https://github.com/sonic-net/SONiC/blob/master/doc/media-settings/Media-based-Port-settings.md)  
* [Medium + Lane Speed based tuning](https://github.com/sonic-net/sonic-platform-daemons/pull/538)

## Theory

The aim of this feature is to create a larger media settings file which includes all configurations of transceivers and media types for a specific SKU and to implement a system which will dynamically set tuning values for all ASIC-port, ASIC-gearbox, and gearbox-port connections based on the detected type of transceivers/media present. This will eliminate the need for engineers to manually change these values in the future by allowing the platform daemon controller to automatically set these values based on detected media attributes.

## Current Design

### Orchagent

The orchagent process within sonic-swss currently configures gearbox tunings based on a hard-coded blackhawk.xml file when gearbox ports are initialized. This means that any time a customer wants to change transceiver types or serdes lane speeds, a change to this file must be upstreamed to configure the new tuning values properly.

### Media Settings

The media settings file currently supports lookups for a variety of media tuning keys based on transceiver type for ASIC-port tunings. We intend to expand on the current design to include a section for gearbox media settings and update the parser file accordingly.

## Design Proposal

### 1\. sonic-buildimage \- Add GEARBOX\_MEDIA\_SETTINGS Section in Media Settings File

The first proposed change is to add support for a new section to the media settings file of gearbox-enabled SKUs specifically for gearbox tunings. Support is added for GEARBOX\_GLOBAL\_MEDIA\_SETTINGS and GEARBOX\_PORT\_MEDIA\_SETTINGS as top-level keys, representing global gearbox settings over a range of ports and individual logical port configurations, respectively. These new keys will should include sub-sections for line-side and system-side tunings for logical ports which have gearbox connections.

#### Example media_settings.json

```
{
    "GEARBOX_PORT_MEDIA_SETTINGS": {
        "1": {
            "line": {
                "COPPER10000": {
                    "main": {
                        "lane0": "0x75",
                        "lane1": "0x75",
                        "lane2": "0x75",
                        "lane3": "0x75",
                        "lane4": "0x75",
                        "lane5": "0x75",
                        "lane6": "0x75",
                        "lane7": "0x75"
                    },
			  ...
			  ...
                }
            },
            "system": {
                "COPPER10000": {
                    "main": {
                        "lane0": "0x75",
                        "lane1": "0x75",
                        "lane2": "0x75",
                        "lane3": "0x75",
                        "lane4": "0x75",
                        "lane5": "0x75",
                        "lane6": "0x75",
                        "lane7": "0x75"
                    },
			  ...
			  ...
                }
            }
        }
    },
    "PORT_MEDIA_SETTINGS": {
        "3": {
            "COPPER10000": {
                "main": {
                    "lane0": "0x6d",
                    "lane1": "0x6d",
                    "lane2": "0x6d",
                    "lane3": "0x6d",
                    "lane4": "0x6d",
                    "lane5": "0x6d",
                    "lane6": "0x6d",
                    "lane7": "0x6d"
                },
		    ...
            }
        }
    }
}
```

### 2\. sonic-platform-daemons \- Update Media Settings Parser / xcvrd

The second proposed change is to expand the media settings parser to parse the new gearbox settings section(s) in the media settings file. Currently xcvrd uses the parser file to parse tuning values for ASIC-port connections and sets these values in APPL\_DB. The aim here is to expand this functionality to include the new gearbox tunings. To facilitate this, we will simply add new gearbox media settings keys to the lookup function within the parser and make additional calls to parse the gearbox values. Updating APPL\_DB with gearbox tuning values will follow the same design as ASIC tunings while simply adding a unique prefix to the key-value pair to distinguish between line-side and system-side values. Parsing gearbox tunings will follow the same lookup logic as current ASIC tunings, and will support global gearbox settings over a range of ports (GEARBOX\_GLOBAL\_MEDIA\_SETTINGS) or individual logical port configurations (GEARBOX\_PORT\_MEDIA\_SETTINGS). This change will not disrupt vendors and SKUs which do not implement gearboxes or rely on specific vendor/media keys to perform tuning value lookups.

#### Example gearbox port APPL\_DB:

```
| Keys              | field-value pairs                                                                                                 | |
+===================+===================================================================================================================+ |
| PORT_TABLE:Ethernet0 | +------------------+-----------------------------------------------------------------------------------------+ | |
|                   | | field               | value                                                                                   | | |
|                   | |---------------------+-----------------------------------------------------------------------------------------| | |
|                   | | admin_status        | up                                                                                      | | |
|                   | | alias               | Ethernet1/1                                                                             | | |
|                   | | description         | Ethernet0-connected-to-bkd596@eth20/1                                                   | | |
|                   | | fec                 | rs                                                                                      | | |
|                   | | flap_count          | 3                                                                                       | | |
|                   | | index               | 1                                                                                       | | |
|                   | | lanes               | 17,18,19,20,21,22,23,24                                                                 | | |
|                   | | last_down_time      | Tue Nov 19 18:23:42 2024                                                                | | |
|                   | | last_up_time        | Tue Nov 19 18:23:44 2024                                                                | | |
|                   | | line_tx_fir_main    | 0x6f,0x6f,0x6f,0x6f,0x6f,0x6f,0x6f,0x6f                                                 | | |
|                   | | line_tx_fir_post1   | 0xfffffff6,0xfffffff6,0xfffffff6,0xfffffff6,0xfffffff6,0xfffffff6,0xfffffff6,0xfffffff6 | | |
|                   | | line_tx_fir_post2   | 0xffffffff,0xffffffff,0xffffffff,0xffffffff,0xffffffff,0xffffffff,0xffffffff,0xffffffff | | |
|                   | | line_tx_fir_post3   | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | line_tx_fir_pre1    | 0xfffffffb,0xfffffffb,0xfffffffb,0xfffffffb,0xfffffffb,0xfffffffb,0xfffffffb,0xfffffffb | | |
|                   | | line_tx_fir_pre2    | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | line_tx_fir_pre3    | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | mtu                 | 9100                                                                                    | | |
|                   | | oper_status         | up                                                                                      | | |
|                   | | pfc_asym            | off                                                                                     | | |
|                   | | speed               | 400000                                                                                  | | |
|                   | | subport             | 0                                                                                       | | |
|                   | | system_tx_fir_main  | 0x50,0x50,0x50,0x50,0x50,0x50,0x50,0x50                                                 | | |
|                   | | system_tx_fir_post1 | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | system_tx_fir_post2 | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | system_tx_fir_post3 | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | system_tx_fir_pre1  | 0xfffffff4,0xfffffff4,0xfffffff4,0xfffffff4,0xfffffff4,0xfffffff4,0xfffffff4,0xfffffff4 | | |
|                   | | system_tx_fir_pre2  | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | system_tx_fir_pre3  | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                   | | tpid                | 0x8100                                                                                  | | |
|                     | +-----------------------+--------------------------------------------------------------------------------------------------+ | |
+---------------------+------------------------------------------------------------------------------------------------------------------------------+ |
```

#### Example non-gearbox port APPL\_DB:

```
| Keys                  | field-value pairs                                                                                            | |
+=======================+==============================================================================================================+ |
| PORT_TABLE:Ethernet16 | +----------------+-----------------------------------------------------------------------------------------+ | |
|                       | | field          | value                                                                                   | | |
|                       | |----------------+-----------------------------------------------------------------------------------------| | |
|                       | | admin_status   | up                                                                                      | | |
|                       | | alias          | Ethernet3/1                                                                             | | |
|                       | | description    | Ethernet16-connected-to-bkd596@eth3/1                                                   | | |
|                       | | fec            | rs                                                                                      | | |
|                       | | flap_count     | 3                                                                                       | | |
|                       | | index          | 3                                                                                       | | |
|                       | | lanes          | 49,50,51,52,53,54,55,56                                                                 | | |
|                       | | last_down_time | Tue Nov 19 18:23:41 2024                                                                | | |
|                       | | last_up_time   | Tue Nov 19 18:23:47 2024                                                                | | |
|                       | | main           | 0x8a,0x8b,0x8b,0x8a,0x8a,0x8b,0x8a,0x8b                                                 | | |
|                       | | mtu            | 9100                                                                                    | | |
|                       | | oper_status    | up                                                                                      | | |
|                       | | pfc_asym       | off                                                                                     | | |
|                       | | post1          | 0xfffffff6,0xfffffff5,0xfffffff5,0xfffffff6,0xfffffff6,0xfffffff5,0xfffffff6,0xfffffff5 | | |
|                       | | post2          | 0xfffffffe,0xffffffff,0xffffffff,0xfffffffe,0xfffffffe,0xffffffff,0xfffffffe,0xffffffff | | |
|                       | | post3          | 0xfffffffd,0xfffffffd,0xfffffffd,0xfffffffd,0xfffffffd,0xfffffffd,0xfffffffd,0xfffffffd | | |
|                       | | pre1           | 0xfffffff1,0xfffffff1,0xfffffff1,0xfffffff1,0xfffffff1,0xfffffff1,0xfffffff1,0xfffffff1 | | |
|                       | | pre2           | 0x2,0x1,0x1,0x2,0x2,0x1,0x2,0x1                                                         | | |
|                       | | pre3           | 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0                                                         | | |
|                       | | speed          | 400000                                                                                  | | |
|                       | | subport        | 0                                                                                       | | |
|                       | | tpid           | 0x8100                                                                                  | | |
|                       | +----------------+-----------------------------------------------------------------------------------------+ | |
+-----------------------+--------------------------------------------------------------------------------------------------------------+ |
```

### 3\. sonic-swss \- Update Orchagent to Dynamically Program Gearbox Tunings

The third proposed change is to alter the way the orchagent process sets gearbox tunings. Upon detecting a change within APPL\_DB for a particular port, orchagent will be triggered to run doPortTask() with SET\_COMMAND on the logical port. Since the media settings parser change from above will use the same mechanism as before to update APPL\_DB with gearbox tunings, similarly the same flow and system can be used within orchagent as before to set the gearbox tuning values. This will involve creating new serdes attributes for line-side and system-side tunings. These new serdes attributes will then be used to make SAI calls and program the relevant gearbox ports in a manner similar to how ASIC tunings are currently applied. In the current iteration of this feature, only tunings with serdes attributes of the form ('main', 'post1', 'pre1', etc.) will be parsed and applied to gearbox ports. This change will allow orchagent to dynamically set the appropriate tunings to gearboxes if customers ever wish to change the configuration of their ports or transceivers and will eliminate the need for Arista engineers to spend time doing so manually.

## Overview \- Big Picture

The following diagram depicts an overview of the new proposed dynamic gearbox tuning flow. Intentionally, this is identical to the current flow of ASIC-port dynamic tuning with media settings as shown in [SONiC/Media-based-Port-settings.md at master](https://github.com/sonic-net/SONiC/blob/master/doc/media-settings/Media-based-Port-settings.md).

![](gearbox_flow.png)


## Testing

- Tested on dut  
- media\_settings\_parser.py  
  - Verified that the script correctly parses ASIC and gearbox values and updates them in APPL\_DB  
- orchagent  
  - Verified through gdb that correct values were being read from APPL\_DB and that SAI calls to program hardware were running successfully  
  - Verified hardware programming by first passing in a media settings file with all tuning values at 0  
    - Used credo shell to verify that tuning values for all gearboxes had been set to 0  
    - Updated media\_settings.json to use real tuning values
    - Verified once again through credo shell that all gearboxes had been updated with the real tuning values.  
- Tested against existing unit tests and added test cases covering new changes.

## Unit Tests

- Ensured existing unit tests passed 
- Added unit tests in test_xcvrd.py for pmon changes

## Future Considerations

- Any SKU for which we want to support dynamic gearbox tuning for will require an update to its media_settings.json file as shown in change 1
- Currently only supporting gearbox serdes attributes of the form (‘main’, ‘post1’, ‘pre1’, etc.)  
  - Will need to add additional serdes attributes if we wish to support attributes like preemphasis, idriver, etc.