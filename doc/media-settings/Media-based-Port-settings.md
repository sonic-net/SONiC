Media based port settings in SONIC

# 1 Document History

| Version | Date       | Author                 | Description                                      |
|---------|------------|------------------------|--------------------------------------------------|
| v.01    | 01/30/2019 |Sudharsan               | Initial version from Dell                        |

Overview:
=========

              Networking devices such as switches or routers use different kind of optics as well as DAC cables to connect with peer devices such as servers, storage or other networking devices. There are different types of networking cables available and based on the cable type the networking ASIC might require additional settings for a cable to work properly on a port. As an example, a 40G-QSFP-CR4 2M DAC might require a different pre-emphasis setting on a device based on Broadcom ASIC than 40G-QSFP-CR4 1M DAC on a port. If the pre-emphasis is not set properly the traffic flowing through the port might encounter CRC errors and even in some cases the port might not even become operationally up.

              To solve the above problem, few SAI attributes required for serdes programming are listed in section below. These SAI attributes will be programmed during media insert event.

Media settings file:
====================

              Each vendor need to define the media settings file under device/<vendor-name>/ <ONIE_PLATFORM_STRING>/ <HARDWARE_SKU>/media_settings.json. This file contains the list of optics and DAC media-based settings for each port in the device. Each media setting for a media type comprises of key-value pairs per lane that is expected to be programmed when an optics or DAC is used. Examples of key value pairs include pre-emphasis, idriver and ipredriver.

              Below example shows the media-based settings for a device on a Broadcom based platform.  For each port the list of supported optics and DAC types are defined (uniquely identified by media type key). For each media type the list of supported vendors (uniquely identified by vendor key) is defined. Each vendor key which will in turn contain the key value pairs per lane that needs to be programmed.

              The media type key defined in the file will be comprised of compliance code and length string or simply compliance code if length does not apply (e.g. 40GBASE-CR4-3M or 40GBASE-SR4).

              The file comprises of two blocks. The first block is for global level settings, where all or multiple ports can be presented as keys. The multiple ports can be represented as a range (Ethernet0-Ethern120) or a list(Ethernet0,Ethernet4,Ethernet8) or a list of ranges(Ethernet0-Ethernet20,Ethernet40-Ethernet60) of logical ports. The second block is port level settings where the key comprises of a single logical port.

              When a media is detected, the logical port is identified. First the global level is looked up and if there is a range or list that the port false within is found, then the media key (compliance + length) is constructed and looked up at the next level. If there is an exact match then those values are fetched and returned. Unlike individual port level block below where a default value is specified, there will be no default value specified for the media-key. A  no-match will make the search fall back to individual port based block from global block.

              In the port based settings block, the port on which it is detected is identified at the first level. At the second level, the media type key is constructed based on compliance code and length. If compliance code -- length key is not found in the media types listed for the port, then the key is reduced to include only compliance code. For instance, if the initial media type key constructed from the EEPROM fields is '40GBASE-CR4-2M' and the specific port does not list such an entry then key is reduced to '40GBASE-CR4' and the port entry is searched if the reduced key exists. If there is still no match, then the 'Default' value listed under the port is selected.

              At the third level, the Vendor key is derived by concatenating vendor name and vendor part number (e.g. DELL-00-11-22).  If there is no exact match for vendor name -- vendor part number key, then the vendor key is reduced to vendor name alone (e.g. DELL) and the media type entry is looked up for such a key. If there is no match, then the default value listed under the media type is chosen. Below is an example for json file for a specific port. For the port Ethernet20 two specific media types (40GBASE-SR4 and 40GBASE-CR4-3M) and a 'Default' media type is defined. For 40GBASE-SR4 a DELL vendor name- vendor PN specific setting is listed along with a 'Default' value which is chosen for all other 40GBASE-SR4 optics apart from the listed key (DELL-00-11-22). For 40GBASE-CR4-3M media key a DELL vendor name alone key word is listed along with a 'Default' key word. This would imply that any 40GBASE-CR4-3M DAC manufactured by DELL will pick the values listed in the vendor name key whereas everything else will pick the default values.

{

    "PORT_MEDIA_SETTINGS": {

        "Ethernet20": {

            "Default": {

                "Default": {

                    "preemphasis": {

                         "Lane0": "0x1201",

                          "Lane1": "0x1234"

                    },

                    "idriver": {

                        "Lane0": "0x1",

                        "Lane1": "0x1"

                     },

                     "ipredriver": {

                        "Lane0": "0x1",

                        "Lane1": "0x1"

                     }

                },

                "DELL": {

                    "preemphasis": {

                        "Lane0": "0x1205",

                        "Lane1": "0x5055"

                    },

                    "idriver": {

                        "0x2",

                        "0x2"

                    },

                    "ipredriver": {

                        "Lane0": "0x2",

                        "Lane1": "0x2"

                    }

                }

            },

            "40GBASE-SR4": {

                "Default": {

                    "preemphasis": {

                        "Lane0": "0x4321",

                        "Lane1": "0x4321"

                    },

                    "idriver": {

                        "Lane0": "0x2",

                        "Lane1": "0x3"

                    },

                    "ipredriver": {

                         "Lane0": "0x3",

                         "Lane1": "0x1"

                    }

                },

                "DELL-00-11-22": {

                    "preemphasis": {

                        "Lane0": "0x1311",

                        "Lane1": "0x321c",

                    },

                    "idriver": {

                        "Lane0": "0x1",

                        "Lane1": "0x2",

                    },

                    "ipredriver": {

                        "Lane0": "0x2",

                        "Lane1": "0x1",

                    }

                }

            },

            "40GBASE-CR4-3M": {

                "Default": {

                    "preemphasis": {

                        "Lane0": "0x1021",

                        "Lane1": "0x3021",

                    },

                    "idriver": {

                        "Lane0": "0x4",

                        "Lane1": "0x4"

                    },

                    "ipredriver": {

                        "Lane0": "0x4",

                        "Lane1": "0x4"

                    }

                },

                "DELL": {

                    "preemphasis": {

                        "Lane0": "0x1311",

                        "Lane1": "0x1312

                    },

                    "idriver": {

                        "Lane0": "0x2",

                        "Lane1": "0x2"

                    },

                    "ipredriver": {

                        "Lane0": "0x2",

                        "Lane1": "0x2"

                    }

                }

            }

        }

    }

    "GLOBAL_MEDIA_SETTINGS": {

        "Ethernet0-Ethernet120": {

            "40GBASE-CR4-1M": {

                "Default": {

                    "preemphasis": {

                         "Lane0": "0x1111",

                         "Lane1": "0x1274"

                    },

                    "idriver": {

                         "Lane0": "0x1",

                         "Lane1": "0x1"

                     },

                     "ipredriver": {

                         "Lane0": "0x1",

                         "Lane1": "0x1"

                     }

                }

            }

        }

    }

}

![](https://github.com/dgsudharsan/SONiC/blob/hld_media/doc/media-settings/event_flow.png)

Flow:
=====

              When a media is detected in xcvrd daemon, it constructs the media key identifier string as discussed above and searches the media_settings.json file. On finding a matching media key entry the vendor key is constructed and if found the key value pairs are fetched. The xcvrd daemon notifies these key value pairs along with the alias port to portsorch. The portsorch task will convert the alias to SAI object Id and notifies the syncd by doing port attribute set of corresponding settings. Syncd invokes the SAI port set those attribute with specified values. The SAI implementation then programs the attribute into the hardware.

              The notification of hardware profile from xcvrd to portsorch task will be done during initialization and during media detect event. This is not required during media removal event. Since the media settings are required only for the proper functioning of the optics or DAC, the handling can be restricted to media insert event alone and no action needs to be taken during media removal.

              This mechanism is also very helpful in supporting new media types without upgrading the Operating system. If a new media type need to be supported the only change that needs to be done is modify media_settings.json to add the new media type.
              
![](https://github.com/dgsudharsan/SONiC/blob/hld_media/doc/media-settings/key_selection_flow.png)

Breakout Scenario:
==================

              The media_settings.json file is defined based on logical ports and for each logical ports, the settings are defined per lane. When a port is breakout, it is split into multiple logical ports. For example let us assume the port before breakout is Ethernet0 and has four lanes, after breakout the logical ports would be Ethernet0, Ethernet1, Ethernet2, Ethernet3 with each one lane. When a media is detected, the xcvrd daemon will read media_settings.json file for the first logical port (Ethernet0) and will fetch the values for all four lanes and notify portsorch. Portsorch on receiving the message with four lanes will figure out that Ethernet0 is now in one lane mode and thus invoke the SAI API for the first port (Ethernet0) and additional three ports(Ethernet1,Ethernet2,Ethernet3) each with one lane. The data from xcvrd will be cached in a new table as below so that when breakout command is executed dynamically, the settings can be reapplied without any re-notification from xcvrd.

PHY_MEDIA:LOGICAL_PORT_NAME:LANE_NUM:

1)PRE-EMPHASIS:

2)I_DRIVER:

3)IPRE-DRIVER


SAI Attributes:
===============

              To define attributes for SAI pre-emphasis attribute as below. Some attributes like IDRIVER and IPREDRIVER are specific to Broadcom but required to be programmed for different cables similar to pre-emphasis. If an asic vendor does not support these attributes, then SAI implementation can return SAI_STATUS_NOT_SUPPORTED during set attribute call

/**

     * @brief Port serdes control pre-emphasis

     *

     * List of port serdes pre-emphasis values. The values are of type sai_u32_list_t

     * where the count is number lanes in a port and the list specifies list of values

     * to be applied to each lane.

     *

     * @type sai_u32_list_t

     * @flags CREATE_AND_SET

     * @default internal

     */

    SAI_PORT_ATTR_SERDES_PREEMPHASIS,

    /**

     * @brief Port serdes control idriver

     *

     * List of port serdes idriver values. The values are of type sai_u32_list_t

     * where the count is number lanes in a port and the list specifies list of values

     * to be applied to each lane.

     *

     * @type sai_u32_list_t

     * @flags CREATE_AND_SET

     * @default internal

     */

    SAI_PORT_ATTR_SERDES_IDRIVER,

    /**

     * @brief Port serdes control ipredriver

     *

     * List of port serdes ipredriver values. The values are of type sai_u32_list_t

     * where the count is number lanes in a port and the list specifies list of values

     * to be applied to each lane.

     *

     * @type sai_u32_list_t

     * @flags CREATE_AND_SET

     * @default internal

     */

    SAI_PORT_ATTR_SERDES_IPREDRIVER,

Below is the pull request

<https://github.com/opencomputeproject/SAI/pull/907>
