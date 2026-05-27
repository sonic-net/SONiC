# Platform capability file enhancement #

### Rev 0.1

## Table of Content

## Revision

 | Rev |     Date    |            Author            | Change Description   |
 |:---:|:-----------:|:----------------------------:|----------------------|
 | 0.1 |             | Arun Saravanan Balachandran  | Initial version      |

## Scope

This document provides information on the enhancements for platform capability file `platform.json`.

## Definitions/Abbreviations

| Definitions/Abbreviation | Description |
|--------------------------|-------------|
| BMC | Baseband Management Controller |
| NOS | Network Operating System |
| PSU | Power Supply Unit |

## Overview

Each networking switch has a set of platform components (e.g: Fans, PSUs, LEDs, etc.) and these components in each platform can have different characteristics (like supported colors for a LED). In a given platform, the components could be controlled by a dedicated platform controller (like BMC) or the NOS running on the CPU is required to control it and in the former the control of the components from the NOS could be limited.

In SONiC the platform components' supported attributes are made available via Platform API, but certain platform specific capabilties for the components are not available for the applications.

This document provides the enhancement for `platform.json` to address the above issue.

## Design

Currently, `platform.json` is used for providing the expected structure of the platform components and interface details for supporting dynamic port breakout.

### Platform capabilities field

A new set of `capabilities` fields are introduced in platform.json, for providing platform specific capablities on control and characteristics of the components.

For each component's attribute, the defined `capabilities` fields are as follows:

- "controllable" : A boolean, 'true' if the given attribute can be controlled from the NOS, 'false' otherwise. Defaults to 'true'.
- Attribute specific fields:
    - status led - "color" - A list of the supported colors.
    - speed
        - "minimum" - Minimum recommended fan speed that can be set.
        - "maximum" - Maximum recommended fan speed that can be set.

Sample `capabilities` fields:

```
{
    "chassis": {
        "name": "PLATFORM",
        "status_led": {
            "controllable": true,
            "colors": ["off", "amber", "green"]
        },
        "fan_drawers":[
            {
                "name": "FanTray1",
                "status_led": {
                    "controllable": true,
                    "colors": ["red", "green"]
                }
                "fans": [
                    {
                        "name": "FanTray1-Fan",
                        "speed": {
                            "controllable": true,
                            "minimum": 40,
                            "maximum": 100
                        }
                    }
                ]
            },
            {
                "name": "FanTray2",
                "status_led": {
                    "controllable": true,
                    "colors": ["red", "green"]
                }
                "fans": [
                    {
                        "name": "FanTray2-Fan",
                        "speed": {
                            "controllable": true,
                            "minimum": 40,
                            "maximum": 100
                        }
                    }
                ]
            }
        ],
        "psus": [
            {
                "name": "PSU1",
                "status_led": {
                    "controllable": false
                }
                "fans": [
                    {
                        "name": "PSU1 Fan",
                        "speed": {
                            "controllable": false
                        }
                    }
                ],
            }
        ],
        "thermals": [
            {
                "name": "Thermal 1",
                "controllable": false
            },
            {
                "name": "Thermal 2",
                "controllable": false
            },
        ],

    ...
}
```
