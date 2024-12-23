# Platform components firmware information #

### Rev 0.1

## Table of Content

## Revision

 | Rev |     Date    |         Author               | Change Description   |
 |:---:|:-----------:|:----------------------------:|----------------------|
 | 0.1 |  2/7/2022   |      Sujin Kang              | Initial version      |

## Scope

This document provides the platform compoent firmware information file `platform_component.json`.

## Definitions/Abbreviations

| Definitions/Abbreviation | Description                       |
|--------------------------|-----------------------------------|
| CPLD                     | Complex Programmable Logic Device |
| SSD                      | Solid State Drive                 |
| FPGA                     | Field-Programmable Gate Array     |
| BIOS                     | Basic Input/Output System         |
| ONIE                     | Open Network Install Environment  |

## Overview

SONiC FW utility uses platform API to interact with the various platform components. SONiC FW utility extends to support for the automatic firmware update based on "platform_components.json" under platform directory and next reboot option which is passed as a option for fwutil update all fw command. SONiC FW utility also extends to support for the automatic firmware update with a custom firmware package that can include any firmware update tool and the firmware update tool will be used for the firmware update if it's specified in the "platform_components.json".

Automatic FW installation requires "platform_components.json" to be created and placed at: sonic-buildimage/device/<platform_name>/<onie_platform>/platform_components.json.

The purpose of the update all commands group is to provide and interface for automatic fw updates of various platform components based on the boot option and the platform firmware update configuration file - "platform_components.json".

 The custom firmware image package should have the platform_components.json which indicates which component's firmware image is available
and the relative location of the image file. Fwutil will search for the platform_components.json first to get the firmware image information - version and the relative location
from the platform_componenets.json.


This document provides the structure and the information of for `platform_components.json` to support the automatic firmware update using `fwutil update all`.

## Design

`platform_components.json` is used for providing the expected structure of the platform components firmware details for supporting the component firmware update.

### Platform components field

A set of fields are introduced in platform_components.json, for providing platform specific capablities on control and characteristics of the components.

- "chassis" : A boolean, 'true' if the given attribute can be controlled from the NOS, 'false' otherwise. Defaults to 'true'.
- "module" : A boolean, 'true' if the given attribute can be controlled from the NOS, 'false' otherwise. Defaults to 'true'.
- "component" : A boolean, 'true' if the given attribute can be controlled from the NOS, 'false' otherwise. Defaults to 'true'.
- Attribute specific fields:
    - firmware - firmware path
    - utility - firmware update utility

Sample `firmware` fields for chassis device:

```
{
    "chassis": {
        "MSN2410": {
            "component": {
                "ONIE": { },
                "SSD": { },
                "BIOS": { },
                "CPLD1": {
                        "firmware": "/lib/firmware/CPLD_older.mpfa"
                },
                "CPLD2": {
                        "firmware": "/lib/firmware/CPLD_older.mpfa"
                },
                "CPLD3": {
                        "firmware": "/lib/firmware/CPLD_older.mpfa"
                }
            }
        }
    }
}
```
Sample `firmware` fields for chassis and module device:

```
{
    "chassis": {
        "S6100-ON": {
            "component": {
                "BIOS": { },
                "CPLD": { },
                "FPGA": { },
                "SSD": {
                    "firmware":"ssd_firmware_upgrade.tar"
                }
            }
        }
    },
    "module": {
        "IOM1: 16x40G QSFP+ Module": {
            "component": {
                "IOM1-CPLD": { }
            }
        },
        "IOM2: 16x40G QSFP+ Module": {
            "component": {
                "IOM2-CPLD": { }
            }
        },
        "IOM3: 16x40G QSFP+ Module": {
            "component": {
                "IOM3-CPLD": { }
            }
        },
        "IOM4: 16x40G QSFP+ Module": {
            "component": {
                "IOM4-CPLD": { }
            }
        }
    }
}
```
Sample `utility` fields for chassis and module device:

```
{
    "chassis": {
        "S6100-ON": {
            "component": {
                "BIOS": { },
                "CPLD": { },
                "FPGA": { },
                "SSD": {
                    "firmware":"ssd_firmware_upgrade.tar",
                    "utility":"ssd_upgrade_schedule"
                }
            }
        }
    },
    "module": {
        "IOM1: 16x40G QSFP+ Module": {
            "component": {
                "IOM1-CPLD": { }
            }
        },
        "IOM2: 16x40G QSFP+ Module": {
            "component": {
                "IOM2-CPLD": { }
            }
        },
        "IOM3: 16x40G QSFP+ Module": {
            "component": {
                "IOM3-CPLD": { }
            }
        },
        "IOM4: 16x40G QSFP+ Module": {
            "component": {
                "IOM4-CPLD": { }
            }
        }
    }
}
```
