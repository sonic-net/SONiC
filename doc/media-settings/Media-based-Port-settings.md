# Media based port settings in SONIC

## 1 Document History

| Version | Date       | Author                 | Description                                      |
|---------|------------|------------------------|--------------------------------------------------|
| v.01    | 01/30/2019 |Sudharsan               | Initial version from Dell                        |

## Overview:


              Networking devices such as switches or routers use different kind of optics as well as DAC cables to connect with peer devices such as servers, storage or other networking devices. There are different types of networking cables available and based on the cable type the networking ASIC might require additional settings for a cable to work properly on a port. As an example, a 40G-QSFP-CR4 2M DAC might require a different pre-emphasis setting on a device based on Broadcom ASIC than 40G-QSFP-CR4 1M DAC on a port. If the pre-emphasis is not set properly the traffic flowing through the port might encounter CRC errors and even in some cases the port might not even become operationally up.

              To solve the above problem, few SAI attributes required for serdes programming are listed in section below. These SAI attributes will be programmed during media insert event.

## Media settings file:

	Each vendor need to define the media settings file under device/<vendor-name>/ <ONIE_PLATFORM_STRING>/ <HARDWARE_SKU>/media_settings.json. This file contains the list of optics and DAC media-based settings for each port in the device. Each media setting for a media type comprises of key-value pairs per lane that is expected to be programmed when an optics or DAC is used. Examples of key value pairs include pre-emphasis, idriver and ipredriver.

	Below example shows the media-based settings for a device on a Broadcom based platform.  For each port the list of supported optics and DAC types are defined (uniquely identified by media type key). For each media type the list of supported vendors (uniquely identified by vendor key) is defined. Each vendor key which will in turn contain the key value pairs per lane that needs to be programmed.

	The media type key defined in the file will be comprised of compliance code and length string or simply compliance code if length does not apply (e.g. 40GBASE-CR4-3M or 40GBASE-SR4).

	The file comprises of two blocks. The first block is for global level settings, where all or multiple ports can be presented as keys. The multiple ports can be represented as a range (Ethernet0-Ethern120) or a list(Ethernet0,Ethernet4,Ethernet8) or a list of ranges(Ethernet0-Ethernet20,Ethernet40-Ethernet60) of logical ports. The second block is port level settings where the key comprises of a single logical port.
	
	When a media is detected, the logical port is identified. First the global level is looked up and if there is a range or list that the port false within is found, then the vendor key (vendor name + vendor PN) as well as media_key (media type + specification compliance + length) is constructed and looked up at the next level. First Vendor key (eg. AMPHENOL-1234) is looked and If there is an exact match then those values are fetched and returned. If vendor key doesn't match, then media key (eg. QSFP28-40GBASE-CR4-1M) is looked and if there is a match then those values are fetched and returned.  The purpose of having a media key is to have default values for a media type across vendors.  A no-match on vendor and media keys will make the search fall back to individual port based block from global block.

              In the port based settings block, the port on which it is detected is identified at the first level. At second level, the Vendor key is and media key are derived as earlier (e.g. DELL-0123, QSFP28-40GBASE-SR4).  If there is no exact match for vendor key or media key, then the default value listed is chosen. Below is an example for json file for a specific port. For the port Ethernet0 a Vendor specific media type and a 'Default' media type is defined apart from global section containing vendor key as well as media key

```
{
    "GLOBAL_MEDIA_SETTINGS": {
        "Ethernet0-Ethernet124": {
            "AMPHENOL-1234": {
                "preemphasis": {
                    "lane0":"0x001234",
                    "lane1":"0x001234",
                    "lane2":"0x001234",
                    "lane3":"0x001234"
                },
                "idriver": {
                    "lane0":"0x2",
                    "lane1":"0x2",
                    "lane2":"0x2",
                    "lane3":"0x2"
                }
            },
            "MOLEX-5678": {
                "preemphasis": {
                    "lane0":"0x005678",
                    "lane1":"0x005678",
                    "lane2":"0x005678",
                    "lane3":"0x005678"
                },
                "idriver": {
                    "lane0":"0x1",
                    "lane1":"0x1",
                    "lane2":"0x1",
                    "lane3":"0x1"
                }
            },
            "QSFP28-40GBASE-CR4-1M":{
                "preemphasis": {
                    "lane0":"0x005678",
                    "lane1":"0x005678"
                },
                "idriver": {
                    "lane0":"0x1",
                    "lane1":"0x1"
                }
            }
        }
    },
    "PORT_MEDIA_SETTINGS": {
        "Ethernet0": {
            "Default": {
                "preemphasis": {
                    "lane0":"0x112233",
                    "lane1":"0x112233",
                    "lane2":"0x112244",
                    "lane3":"0x443322"
                },
                "idriver": {
                    "lane0":"0xb",
                    "lane1":"0xc",
                    "lane2":"0xd",
                    "lane3":"0xa"
                }
            },
            "DELL-5678": {
                "preemphasis": {
                    "lane0":"0x102233",
                    "lane1":"0x132233",
                    "lane2":"0x152244",
                    "lane3":"0x413322"
                },
                "idriver": {
                   "lane0":"0xc",
                   "lane1":"0xc",
                   "lane2":"0xd",
                   "lane3":"0xb"
               }
            }
        }
    }
}
```
![](https://github.com/dgsudharsan/SONiC/blob/hld_media/doc/media-settings/event_flow.png)

## Flow:


              When a media is detected in xcvrd daemon, it constructs the key identifier string as discussed above and searches the media_settings.json file. If found the key value pairs are fetched. The xcvrd daemon notifies these key value pairs along with the alias port to portsorch. The portsorch task will convert the alias to SAI object Id and notifies the syncd by doing port attribute set of corresponding settings. Syncd invokes the SAI port set those attribute with specified values. The SAI implementation then programs the attribute into the hardware.

              The notification of hardware profile from xcvrd to portsorch task will be done during initialization and during media detect event. This is not required during media removal event. Since the media settings are required only for the proper functioning of the optics or DAC, the handling can be restricted to media insert event alone and no action needs to be taken during media removal.

              This mechanism is also very helpful in supporting new media types without upgrading the Operating system. If a new media type need to be supported the only change that needs to be done is modify media_settings.json to add the new media type.
              
![](https://github.com/dgsudharsan/SONiC/blob/hld_media/doc/media-settings/key_selection_flow.png)

## Breakout Scenario:


              For breakout the particular media, if it has a global value is listed in the media_settings.json with appropriate lane values. If the values are specific to a port, then the entry is listed under the port. If the logical port is going to be created after breakout (E.g Ethernet0 is modified to Ethernet0,Ethernet1,Ethernet2,Ethernet3) those corresponding ports are listed in the ports section in media_settings.json. In the current breakout scenario, when port_config.ini is modified and a config reload is done, the flow will be similar to bootup sequence and thus all the media settings will be pushed from xcvrd to portsorch on restart during config apply.


## SAI Attributes:


              To define attributes for SAI pre-emphasis attribute as below. Some attributes like IDRIVER and IPREDRIVER are specific to Broadcom but required to be programmed for different cables similar to pre-emphasis. If an asic vendor does not support these attributes, then SAI implementation can return SAI_STATUS_NOT_SUPPORTED during set attribute call

```
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
```
Below is the pull request

<https://github.com/opencomputeproject/SAI/pull/907>
