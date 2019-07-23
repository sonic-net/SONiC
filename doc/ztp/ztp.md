# Zero Touch Provisioning (ZTP)

### Rev 0.2

## Table of Contents
- [1. Revision](#1-revision)
- [2. Requirements](#2-requirements)
- [3. Functional Description](#3-functional-description)
  - [3.1 ZTP JSON](#31-ztp-json)
  - [3.2 ZTP Plugins](#32-ztp-plugins)
  - [3.3 Dynamic Content](#33-dynamic-content)
  - [3.4 DHCP Options](#34-dhcp-options)
  - [3.5 ZTP Service](#35-ztp-service)
  - [3.6 Provisioning over in-band network](#36-provisioning-over-in-band-network)
  - [3.7 Component Interactions](#37-components-interactions)
- [4. Chronology of Events](#4-chronology-of-events)
- [5. Security Considerations](#5-security-considerations)
- [6. Configuring ZTP](#6-configuring-ztp)
- [7. Code Structure](#7-code-structure)
- [8. Logging](#8-logging)
- [9. Debug](#9-debug)
- [10. Examples](#10-examples)
- [11. Future](#11-future)
- [12. ZTP Test Suite](#12-ztp-feature-test-suite)

## 1. Revision
| Rev | Date     |  Author       | Change Description                |
|:---:|:------------:|:------------------:|-----------------------------------|
| v0.1 |   03/06/2019   |   Rajendra Dendukuri   | Initial version                   |
| v0.2 | 04/17/2019 | Rajendra Dendukuri | Added: suspend-exit-code, in-band provisioning, interaction with updategraph, Test plan |


## 2. Requirements
- When a newly deployed SONiC switch boots for the first time, it should allow automatic setup of the switch without any user intervention. This framework is called  as Zero Touch Provisioning or in short ZTP.
- DHCP offer sent to a SONiC switch will kickstart ZTP.
- ZTP should allow users to perform one or more configuration tasks. Data and logic used for these configuration task can be defined by the user. It should also allow ordering of these configuration tasks as defined by the user.
- ZTP should allow users to suspend a configuration task and move on to the next one. ZTP resumes the incomplete task later after finishing rest of the tasks in the order of execution.
- Switch reboots during ZTP should be supported. ZTP should resume from where it had left prior to reboot.
- Configuration tasks should be completely user defined. Few predefined tasks shall be provided as part of default switch image. However, user should be able to override the logic of predefined tasks with user supplied logic (script).
- Include switch information while requesting for files from a remote provisioning server. This allows remote server to provide switch specific files at runtime.
- ZTP output and result should be logged through syslog.
- ZTP is expected to run to completion only after all the configuration tasks are completed. Result is either SUCCESS/FAILED. At this point ZTP exits and does not run again. It requires user intervention to re-enable ZTP.
- Manual interruption of ZTP service should be allowed. It should result in ZTP to be disabled and user intervention is needed to re-enable it.
- User should be able to view completion status of each configuration task and ZTP completion status as a whole.
- ZTP feature should be a build time selection option. By default it is not included in the image.
- Provide optional security features to allow encryption and authentication while exchanging sensitive information between the switch and remote provisioning server.
- Example template to demonstrate download, validate and install of a SONiC image file can be provided.
- ZTP should be able to provisioning the switch over in-band network in addition to out-of-band management network. The first interface to provide provisioning data will be used and any provisioning data provided by other interfaces is ignored.
- Both IPv4 and IPv6 DHCP discovery and ZTP provisioning should be supported.

## 3. Functional Description

Zero Touch Provisioning (ZTP) service can be used by users to configure a fleet of switches using common configuration templates. Switches booting from factory default state should be able to communicate with remote provisioning server and download  relevant configuration files and scripts to kick start more complex configuration steps. ZTP service takes user input in JSON format.

## 3.1 ZTP JSON

SONiC consists of many pre-installed software modules that are part of default image. Some of these modules are network protocol applications (e.g FRR) and some provide support services (e.g syslog, DNS). Data and logic to configure various SONiC modules is encoded in a user defined input file in JSON format. This data file is referred to as ZTP JSON.

When SONiC switch boots for first time, ZTP service checks if there is an existing ZTP JSON file. If no such file exists, DHCP Option 67 value is used to obtain the URL of ZTP JSON file. ZTP service then downloads the ZTP JSON file and processes the file. If DHCP Option 67 value is not available, ZTP service waits till it is provided by the DHCP server.

If a ZTP JSON file is already present on the switch,  ZTP service uses it to perform next steps.

Typically in a ZTP JSON file multiple configuration sections are defined by user. They are all enclosed within ztp object. Below example has four configuration sections *snmp*, *firmware*, *provisioning-script* and *configdb-json* which are included as value of *ztp* object. The overarching ztp object also has *status* and *timestamp* objects which specify the progress of whole ZTP service. It is mandatory to have *ztp* object defined as the first object and rest of the objects are nested under it. ZTP service will not parse the JSON data if *ztp* object is not found.

```json
{
  "ztp": {
    "snmp": {
	
	},
    "firmware": {
	
	},
    "provisioning-script": {
	
	},
    "configdb-json": {
	
	}
  }
}
```

Below is an example configuration section  used for configuring SNMP community string on the switch.

```json
  "snmp": {
    "ignore-result": false,
    "community-ro": [
      "public",
      "local"
    ],
    "community-rw": [
      "private"
    ]
  }
```

Each section has a unique name, *snmp* in above example. It provides sufficient data to configure a single or a set of modules on the switch. In the *snmp* example, a list of read only and read write SNMP community strings are provided as values of the  *community-rw* and *community-ro* objects. ZTP service invokes the logic which takes these values and adds them to "/etc/sonic/snmp.yml" file and restarts SNMP daemon.

Also each configuration section of ZTP JSON includes some common objects that are used to influence its execution. They also help track progress of individual section and the entire ZTP activity.

- **status** : Describes the state of configuration of the section.

  - BOOT   - Provided configuration is not yet applied
  - IN-PROGRESS  - Provided configuration is currently being applied by the ZTP service
  - SUCCESS - Provided configuration is successfully applied by the ZTP service
  - FAILED - ZTP service encountered an error and failed to apply provided configuration
  - SUSPEND - Provided configuration is currently suspended and will retried by the ZTP service later
  - DISABLED - ZTP service will not apply provided configuration in this section

  Default value assumed to be BOOT if the object is not present. ZTP service adds this object to the ZTP JSON file if not found.

- **ignore-result** :
  - false  - ZTP service marks status as FAILED if an error is encountered while processing this individual section
  - true   - ZTP service marks status as SUCCESS even if an error is encountered while processing this individual section

  Default value is assumed to be *false* if the object is not present.

- **timestamp** : Specifies the time and date when the *status* variable of a section is modified.

  ZTP service adds this object to the ZTP JSON file and it need not be added by user.

- **suspend-exit-code**: Specifies the program exit code value to indicate that configuration section can be placed in suspended mode and retried later. See [*Plugin Exit Code*](#322-plugin-exit-code) for additional information

  This object is optional for a configuration section. Possible values are non-zero positive integers. If any other values specified are treated as the case where object is not specified.

- **reboot-on-success** :

  - true  - If configuration section result is  SUCCESS, ZTP service reboots the switch
  - false - ZTP services moves on to next configuration section

  Default value is assumed to be *false* if the object is not present.

- **reboot-on-failure** :
  - true  - If configuration section result is FAILURE, ZTP service reboots the switch
  - false - ZTP services moves on to next configuration section

  Default value is assumed to be *false* if the object is not present.

- **halt-on-failure** :
  - true  - If configuration section result is FAILED, ZTP service stops and exits immediately marking *ztp.status* as FAILED. No other configuration sections are processed. User intervention is needed to restart ZTP.
  - false - ZTP services moves on to next configuration section

  Default value is assumed to be *false* if the object is not present.

- **ztp-json-source** : This object defines the source from which the ZTP JSON file was downloaded from. This object is applicable only for the overarching ztp object and not individual configuration sections. Default value is assumed to be *DHCP* if the object is not present.

  - DHCP  - ZTP service downloaded the ZTP JSON file using the URL specified in the DHCP option 67 received by the switch when it obtained an IP address. 

  - local_fs - This value should be used if the ZTP JSON file has been included in the  SONiC image as part of build. When this value is set, ZTP service ignores the URL provided in DHCP Option 67 and processes only the file on disk. This option can be used in scenarios where some DHCP server is not present or cannot be possible and some initial configuration steps need to be performed on the switch on boot.


Configuration sections in ZTP JSON are processed by ZTP service in lexical order of section names. In order to force execution order, names in xxx-name format (e.g 001-firmware) can be used. For predefined plugins leading sequence number is stripped off to find appropriate plugin. So 001-firmware configuration section will be processed internally using firmware plugin. More on plugins in the [*ZTP plugins*](#32-ztp-plugins) section.

ZTP service exits and marks the status as FAILED if any errors are encountered while parsing the ZTP JSON file. It is encouraged to check for any JSON format correctness before rolling out the ZTP JSON file for use. When processing a configuration section, If provided data is found to be insufficient, it is marked as failed and ZTP moves on to next section.

## 3.2 ZTP Plugins

Each section of ZTP JSON data is processed by corresponding handler which can understand the objects/values of that section using a predefined logic. This handler is referred to as a plugin. Plugins are executable files, mostly scripts, which take  objects/values described in corresponding configuration section as input. For e.g the "snmp" section is processed by the snmp plugin provided by SONiC-ZTP package. For plugins provided by SONiC-ZTP package, it is mandatory that the name of the configuration section matches the plugin file name. Predefined plugins can be found in the directory "/var/lib/ztp/plugins".

### 3.2.1 User Defined Plugins

SONiC ZTP allows users to specify custom configuration sections and provide corresponding plugin executable. ZTP service downloads the plugin and uses it to process objects/values specified in the configuration section. This allows users to extend ZTP functionality in ways that suit their environment and deployment needs. For better compatibility with input data, users are encouraged to use executables which can process JSON formatted data.

Below is an example section of ZTP JSON data which is used to configure SNMP communities on a switch. The *plugin* object defines the usage of user defined plugin. In this example, user provided *my-snmp.py* file is downloaded using the url indicated by the *plugin.url.source* field. The plugin is copied locally as the file "/var/run/ztp/plugins/my-snmp" on SONiC switch and executed by ZTP service.

```json
  "snmp": {
    "ignore-result": false,
    "plugin": {
      "url": {
        "source": "http://192.168.1.1:8080/my-snmp.py",
        "destination": "/var/run/ztp/plugins/my-snmp"
      }
    },
    "community-ro": [
      "public",
      "local"
    ],
    "community-rw": [
      "private"
    ]
  }
```
User defined plugins downloaded by ZTP service are deleted after the configuration section processing is complete.

### 3.2.2 Plugin Exit Code

Both predefined and user-defined plugins are executed as a sub process by the ZTP service. The exit code of the executed plugin is used by ZTP service to determine next steps. The value of *suspend-exit-code* is specified in configuration section's data. 

|Exit Code |  Description         | Action                                       |
|:------------|:-------------------|:-------------------------------------------------|
|   0      | SUCCESS     | Plugin completed intended operation successfully. *status* of the configuration section is set to value SUCCESS.  |
|   *suspend-exit-code*   | SUSPEND     | Plugin exited after partial execution. *status* of the configuration section is set as SUSPEND |
|   > 0 and !=*suspend-exit-code*   | FAILED     | An error was encountered while executing the plugin. *status* of the configuration section is set to value FAILED.  |

When using *suspend-exit-code*, the corresponding plugin should ensure that when ZTP service comes back to execute the plugin again, appropriate logic is implemented within the plugin to resume from where it had left earlier. If *suspend-exit-code* is not specified, suspend and resume feature for the plugin is not supported.

### 3.2.3 Available Plugins and Configuration Sections

More information on supported configuration sections of ZTP JSON file and plugins used to process it can be obtained in this section.

#### url object

This object is used to describe a file that can be downloaded from a remote location. The source URL is provided by the *url.source* object value. Full path of file name on the switch where it is intended to be copied to is specified in *url.destination* object value. When *url.destination* is specified, all directories in the file path are also created. *url.source* field is mandatory and rest of them are optional.

```json
  "url": {
    "source": "http://192.168.1.1:8080/spine01_config_db.json",
    "destination": "/etc/sonic/config_db.json",
    "secure": false
  }
```

When *url.destination* is not specified, the destination location and filename are determined by the plugin which is processing the url object.

Curl application is used to download the file. Please refer to [curl manual](https://curl.haxx.se/docs/manual.html "curl manual") for supported protocols.

It is to be noted that the *source* string defined in the url object is a static string. When this object is processed, the same file is downloaded for all switches using the same ZTP JSON data. It may not be ideal for files which are intended to be unique for a particular switch, e.g config_db.json. Please refer to section [3.3 Dynamic Content](#33-dynamic-content)  for more information on how this problem is solved.

Following is the list of objects supported by url object. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used.

|  Object |Usage   |Supported Values| Default Value|
| ------------ | ------------ | ------------ | ------------ |
| source  | Define the URL string from where file has to be downloaded  |Syntactically valid URL|N/A|
|  destination | Destination file on switch  | Unix file name | Resolved by plugin|
| secure  | Use insecure mode. This can be used to skip security checks when using HTTPS transport.  | false <br> true| true|
|  curl-arguments | Arguments to curl command used to download the url  | Refer to [curl manual](https://curl.haxx.se/docs/manual.html "curl manual"). | Null string |
|  encrypted | Indicates the file being downloaded in encrypted format.  | Refer to [Encryption](#511-encryption-and-authentication). | No encryption |
|  include-http-headers | To enable/disable sending of switch information as part of [HTTP Headers](#331-http-headers).   | true<br>false | true |

In case there are no additional fields to be defined in *url* object and only *source* is being defined, *url* can be specified in short hand notation.

  "url": {
    "source": "http://192.168.1.1:8080/spine01_config_db.json"
  }

can also be specified as

 "url": "http://192.168.1.1:8080/spine01_config_db.json"

In general url object is used with other objects and not as an individual configuration section.

#### plugin object

The plugin object is used to describe a user-defined plugin that needs to be used to process a configuration section.

In below example, SONiC ZTP package provided *config-db-json* plugin is being used by the *initial-config* section to download and apply initial configuration.

```json
  "initial-config": {
    "plugin": {
      "name": "config-db-json"
    },
    "url": {
      "source": "http://192.168.1.1:8080/spine01_first_boot_config.json",
      "destination": "/etc/sonic/config_db.json",
      "secure": false
    }
  }
```

Following is the list of objects supported by plugin object. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used.

|  Object |Usage   |Supported Values| Default Value|
| ------------ | ------------ | ------------ | ------------ |
| url  | Define the URL string from where plugin has to be downloaded in the form of url object  |Refer to [url object](#url-object)  |Name of enclosing object |
| dynamic-url  | Define the URL string from where plugin has to be downloaded in the form of url object  |Refer to [dynamic-url object](#332-dynamic-url-object)  |Name of enclosing object |
|  name | Use a predefined plugin available as part of SONiC ZTP package  | Predefined plugins | Name of enclosing object|

*plugin.dyrnamic-url* takes precedence over *plugin.url* over *plugin.name* if multiple definitions are defined.

A short hand notation is possible using 'plugin': 'name' which is equivalent of defining *name* objected nested inside *plugin* object.

```json
    "plugin": {
      "name": "config-db-json"
    }
```
can be written in short hand notation as

```json
    "plugin": "config-db-json"
```

#### configdb-json

The *configdb-json* plugin is used to download ConfigDB JSON file and apply the configuration. A *config reload* is performed during which various SWSS services may restart.

```json
  "configdb-json": {
    "url": {
      "source": "http://192.168.1.1:8080/spine01_config_db.json",
      "destination": "/etc/sonic/config_db.json"
    }
  }
```

#### firmware

The *firmware* plugin is used for image management on a switch. It can be used to install, remove and boot selection of images. sonic_installer utility is used by this plugin to perform the supported functions.

Example to install a new image and boot into it.

```json
  "firmware": {
    "install": {
      "url": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin",
      "set-default": true
    },
    "reboot-on-success": true
  }
```

Example to uninstall a SONiC image from the switch.

```json
  "firmware": {
    "remove": {
      "image": "SONiC-OS-brcm_xlr_gts.0-dirty-20190304.154831"
    }
  }
```

Example to install a new image only if it satisfies the pre-install verify check script provided by user.

```json
  "firmware": {
    "install": {
      "url": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin",
      "pre-check": {
        "url": {
          "source": "http://192.168.1.1:8080/firmware_check.sh",
          "destination": "/tmp/firmware_check.sh"
        }
      },
      "set-default": true
    },
    "reboot-on-success": true
  }
```

Following is the  list of objects supported by the *firmware* plugin. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used.

|  Object |Usage   |Supported Values| Default Value|
| ------------ | ------------ | ------------ | ------------ |
|  install | Used to install an image using URL | [url](#url-object) <br> [dynamic-url](#332-dynamic-url) <br> pre-check <br> set_default <br>set_next_boot |N/A|
|  remove | Used to uninstall an existing image  | version <br> pre-check  |N/A|
|  upgrade_docker | Used install a docker image on the SONiC switch | [url](#url-object)<br> [dynamic-url](#332-dynamic-url)   | N/A   |

The *pre-check* object is used to specify a user provided script to be executed. If the result of the script is successful, the action (install/remove) is performed. Its value is a *url object*.

*firmware.remove* is first processed followed by *firmware.install* if both are defined.

#### snmp

The *snmp* plugin is used to configure SNMP community string on SONiC switch. This plugin is provided as an alternative for soon to be deprecated privately used DHCP options 224 used by SONiC.

```json
  "snmp": {
    "community-ro": [
      "public",
      "local"
    ],
    "community-rw": [
      "private"
    ]
  }
```

Following is the  list of objects supported by the *snmp* plugin. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used. The snmp plugin also restarts snmp agent daemon.

|  Object |Usage   |Supported Values| Default Value|
| ------------ | ------------ | ------------ | ------------ |
|  community-ro | Comma separated list of SNMP read only community strings | Syntactically valid SNMP community string  |Null string|
|  community-rw | Comma separated list of SNMP read write community strings |  Syntactically valid SNMP community string  | Null string|
|  restart_agent |  | true <br> false | true  |

#### graphservice

The *graphservice* plugin is used to provide minigraph xml and ACL json file to be used by the SONiC switch. This plugin is provided as an alternative for soon to be deprecated privately used DHCP options 225 and 226 used by SONiC.

Example usage.

```json
  "graphservice": {
    "minigraph_url": {
      "url": "http://192.168.1.1:8080/minigraph.xml"
    },
    "acl_url": {
      "dynamic-url": {
        "source": {
          "prefix": "http://192.168.1.1:8080/acl_",
          "identifier": "hostname-fqdn",
          "sufix": ".json"
        }
      }
    }
  }
```
### 3.3 Dynamic Content

When a switch requests for a file specified by a url, it is expected that the server which is handling the request knows which file to be returned. For e.g when a switch requests for configuration file, the server needs to be able to give out configuration file for the requesting switch. This selection of the file can be done in two ways:

1. Server side - [HTTP Headers](#331-http-headers)
2. Client side - [dynamic-url](#332-dynamic-url)

#### 3.3.1 HTTP Headers

For a server to make the decision on which file to serve out, it requires uniquely identifiable information about the requesting switch.  Then, appropriate logic can be implemented at the server side to porcess the provided information, identify and give out the requested file.

All HTTP/HTTPS requests made during ZTP contain switch identification information as part of HTTP headers. Below is the information that is included.

| Header | Value          | Example                                        |
|:-----------:|:-------------------|:-------------------------------------------------|
|   User-Agent      |  SONiC-ZTP/0.1   | |
|    PRODUCT-NAME      |  *String specifying the switch model*    | E1031|
|    SERIAL-NUMBER      |   *String specifying the manufacture provided serial number*    | E1031B2F035A17GD020|
|    BASE-MAC-ADDRESS      | *Ethernet MAC Address assigned to the switch by the manufacturer*     | 00&#58;E0&#58;EC&#58;38&#58;50&#58;FB|
| SONiC-VERSION | *Version string as seen in 'show version' command* | SONiC.201811.0-20190315.181511 |

#### 3.3.2 dynamic-url

*dynamic-url* object is used in ZTP JSON to allow the url path to be constructed at runtime. This allows switch to request appropriate file instead of relying the server to interpret HTTP headers. Also since other protocol's like scp/TFTP/FTP are also supported, use of HTTP headers may not be valid.

*dynamic-url.source* field consists of three subj-obects whose values are used to construct a url string at runtime. The *identifier*  subobject is mandatory. The prefix and suffix subobjects are optional.

 - prefix  - Specifies a static string which forms the leading part of the url. This typically specifies the transfer protcol and server address. e.g http://192.168.1.1:8080/
 - identifier - Specifies the runtime logic to be used to generate the filename of the resource to be downloaded.
 - suffix - Specifies any filename extension that needs to be added for convenience.

The *prefix*, *identifier* and *suffix* are concatenated to form the url which is specific to the requesting switch.

##### identifier subobject
This subobject is used to specify the logic that is executed on the switch to determine the variable portion of the url. Some pre-defined generally used logic are provided. There is also a possibility to provide user-defined logic.

"identifier:": "hostname"
"identifier:": "hostname-fqdn"

Hostname of the switch is used to the identifier. Switches are assigned unique hostnames by the DHCP server. It can be used while naming files corresponding to a particular switch.

In below example all the switch configuration files are stored at the remote server using long hostname of each switch as part of filename. The long hostname of the switch where ZTP is underway is  *tor-05-pod-10.azure.us.microsoft.com*. When this object is processed by ZTP, the url string is evaluated as http://192.168.1.1:8080/configs/tor-05-pod-10.azure.us.microsoft.com_config_db.json"

```json
    "dynamic-url": {
      "source": {
        "prefix": "http://192.168.1.1:8080/configs/",
        "identifier": "hostname-fqdn",
        "suffix": "_config_db.json"
      },
      "destination": "/etc/sonic/config_db.json"
    }
```
"identifier:": "serial-number"

```json
    "dynamic-url": {
      "source": {
        "prefix": "http://192.168.1.1:8080/configs/",
        "identifier": "serial-number",
        "suffix": "_config_db.json"
      },
      "destination": "/etc/sonic/config_db.json"
    }
```
"identifier:": "product-name"

In below example switch model string is used to identify the image that needs to be downloaded.

```json
    "dynamic-url": {
      "source": {
        "prefix": "http://192.168.1.1:8080/images/sonic-",
        "identifier": "product-name",
        "suffix": ".bin"
      },
    }
```

"identifier:": "url"
It is not possible to pre-determine the file naming convention using at the server. So a provision for running user-defined logic can be supplied as a url object. In below example user provides a script *config_filename_eval.sh* which is downloaded and executed. The output string returned by the user provided script is used as the switch's configuration file name.

```json
    "dynamic-url": {
      "source": {
        "prefix": "http://192.168.1.1:8080/configs/",
        "identifier": {
          "url": "http://192.168.1.1:8080/config_filename_eval.sh"
        },
        "suffix": ".json"
      },
      "destination": "/etc/sonic/config_db.json"
    }
```
Following is the list of objects supported by the *dynamic-url* object. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used.

|  Object |Usage   |Supported Values| Default Value|
| ------------ | ------------ | ------------ | ------------ |
| source.prefix  |Leading part of url string |Syntactically valid URL|Null string|
| source.suffix  |Trailing part of url string |Acceptable characters in a syntactically valid URL|Null string|
| source.identifier  | Runtime generated string that can uniquely identify a switch  |hostname<br>hostname-fqdn<br>serial-number<br>product-name<br>sonic-version<br>[url](#url-object) |N/A|
|  destination | Destination file on switch  | Unix file name | Resolved by plugin|
| secure  | Use insecure mode. This can be used to skip security checks when using HTTPS transport.  | false <br> true| true|
|  curl-arguments | Arguments to curl command used to download the url  | Refer to [curl manual](https://curl.haxx.se/docs/manual.html "curl manual"). | Null string |
|  encrypted | Indicates the file being downloaded in encrypted format.  | Refer to [Encryption](#511-encryption-and-authentication). | No encryption |
|  include-http-headers | To enable/disable sending of switch information as part of [HTTP Headers](#331-http-headers).   | true<br>false | true |

### 3.4 DHCP Options
The following are the private DHCP options used by SONiC switch to receive input data for ZTP service and graphservice.

| DHCP Option | Name         | Description                                       |
|:-----------:|:-------------------|:-------------------------------------------------|
|    224      | snmp_community     | snmpcommunity DHCP hook updates /etc/sonic/snmp.yml file with  provided value |
|    225      | minigraph_url     | graphserviceurl DHCP hook updates the file /tmp/dhcp_graph_url with the provided url. updategraph service processes uses it for further processing. |
|    226      | acl_url           | graphserviceurl DHCP hook updates the file /tmp/dhcp_acl_url with the provided url. updategraph service processes uses it for further processing. |
|    67      | ztp_json_url    | URL for ZTP input data:  All user configurable data that can be input to  ZTP process. This information can be used to access more advanced configuration information.|
|    239      | ztp_provisioning_script_url    | URL for a script which needs to be downloaded and executed by ZTP service on the switch. |

The use of following DHCP options will be deprecated in future releases of SONiC as its values can be included in the ZTP JSON file whose URL can be obtained via DHCP option 67.

| Deprecated <br />  DHCP Options | Name         |
|:-----------:|:-------------------|
|    224      | snmp_community     |
|    225      | minigraph_url     |
|    226      | acl_url           |

It is recommended to use either ztp_provisioning_script_url or ztp_json_url but not both. Provisioning script can be defined with in ZTP JSON file as a user defined plugin thus not requiring the need for ztp_provisioning_script_url to be used. Similarly, user can opt not to use ztp_json file and use custom scripts to perform all configuration activities. If  both options are part of DHCP offer message, ztp_json_url file shall be used and ztp_provisioning_script_url is ignored.

DHCP hook script */etc/dhcp/dhclient-exit-hooks.d/ztp*  is used to process DHCP option 67 and 239. This script is provided as part of SONiC-ZTP package.

## 3.5 ZTP Service



![ZTP_Block_Diagram.png](images/ZTP_Block_Diagram.png)





The ZTP service is defined as a systemd service running on native SONiC O/S. It does not run inside a container.  ZTP service starts after *networking.service*, *rc-local.service* and *database.service*. If ZTP is not administratively enabled, the service exits and does not run again until next boot or if user intervenes. Only updategraph.service wants ztp.service. No other services are not blocked for ztp.service to start or exit.

When management interface obtains IP address via DHCP, URL pointing to ZTP JSON file is provided as value of DHCP option 67. When ZTP service starts, it first checks if there already exists a ZTP JSON file locally and if found loads it. If *ztp.status* field of local file is either SUCCESS, FAILED or DISABLED, ZTP service exits. If *ztp.status* field of local ZTP JSON file is  IN-PROGRESS, local file is used for further processing. If no local ZTP JSON file is found or if the *ztp.status* field of local ZTP JSON file is BOOT, ZTP service downloads the ZTP JSON file using the URL provided by DHCP Option 67 are starts processing it.

If user defines DHCP option 239, ZTP service downloads the provisioning script indicated in the URL and executes it. The exit code returned by the provisioning script is used to indicate whether ZTP has succeeded or failed. Exit code 0 indicates successful execution and any other value is treated as failure. ZTP service exits and does not run again unless user enables it again manually.

It is to be noted that DHCP option 67 takes precedence over DHCP option 239. 

ZTP service parses the ZTP JSON file and processes individual configuration sections in lexical order of their names. If *status* or *timestamp* fields are missing they are added to it. A local copy of ZTP JSON file is maintained as the file */var/lib/ztp/data/ztp.json*. Individual configuration sections are identified and split into individual files as */var/lib/ztp/data/sections/section-name*. The ztp.json file continues to hold all sections as defined by the user.

This ztp.json file is constantly updated with any changes made during the processing of loaded ZTP data. To begin with *ztp.status* is set to IN-PROGRESS and individual sections are processed in order of their names. The  *status* object of the configuration section being processed is set to 1 In-Progress and corresponding plugin is executed. 

Each section whose *status* value is BOOT or IN-PROGRESS  is processed in order. Corresponding plugin is called with */var/lib/ztp/data/sections/section-name* as argument to it. Exit code of plugin is used to determine the configuration sections *status* as explained in the [*Plugin Exit Code*](#322-plugin-exit-code) section of this document.

When all the sections have been processed, *ztp.status* field is updated taking into consideration the result of all individual sections. Sections with disabled *status* and *ignore-status: true* are not considered. *ztp.status* is marked as SUCCESS only if *status* field of all rest of the sections is SUCCESS. ZTP service exits and does not run again unless user enables it again.

If user does not provide both DHCP option 67 or DHCP option 239, ZTP service continues to run and wait for one of these values to be provided to it.



### 3.6 Provisioning over in-band network

If there is no */etc/sonic/config_db.json* and */tmp/pending_config_initialization* is set, ZTP service creates a configuration using ztp preset. The *ztp* preset defines a configuration with PORT table and DEVICE_METADATA table. In addition to creating the default configuration, ztp also creates interface files with name *ztp-Ethernetxxx* for all the ports in PORT table. These are added in */var/run/ztp/dhcp/interfaces.d* and *networking.service*  is restarted. This starts DHCP discovery on all in-band interfaces. A dhcp-exit-hook is installed which is used to set the offered IP address in Config DB using the *"config interface interface-name ip  add"* command. At this point, the switch receives DHCP option 67 ZTP JSON and is ready to communicate with remote devices. ZTP JSON file is downloaded and ZTP service start performing configuration tasks described in the ZTP JSON. 

Since DHCP discovery is performed on all in-band interfaces, there can be a condition where multiple interfaces can get an IP address. Only the first port receiving the DHCP offer along with DHCP Option 67 or/and DHCP Option 239 will be processed. So, care should be taken by the administrator to ensure that only one and also the same DHCP server responds to the DHCP discovery initiated by ZTP.

If ZTP is in completed state or in administratively disabled state, it will not create ZTP preset configuration. Instead, switch will continue to boot with empty configuration. To re-run ZTP user will have to login via console and issue 'ztp enable' and/or 'ztp run' command. There are some other scenarios that are possible when a new SONiC image is installed. They are discussed in the section [*Component Interactions*](#37-component-interactions).

SONiC ZTP supports reboot and resume while a ZTP session is in progress. To handle these scenarios appropriately, it is recommended that the plugins used for configuration tasks, use sufficient checks to determine that switch is communicating to external devices before executing provisioning steps. Since SONiC ZTP is a framework and does not have knowledge on making a decision on reachability, connectivity checks or sufficient retries need to be included in the plugins scripts as part of the defined workflow. This may not be applicable in the case of first run of ZTP since the ZTP JSON URL is obtained only after establishing connectivity. ZTP service can safely assume connectivity and proceed without any issues. To summarize, when there is a reboot step involved, the configuration section plugins should take care that there may be instances where there can be connectivity loss. Same is the case when a config_db.json file is downloaded and applied to the switch.

A configuration option is provided in the ZTP configuration file *ztp_cfg.json* to enable or disable in-band provisioning feature. Provisioning over in-band network is enabled by default when ZTP package is included.



### 3.7 Component Interactions

##### updategraph

ZTP and updategraph can co-exist in the same SONiC image. However, updategraph depends on ZTP to provide the values of *graph_url* and *acl_url.* ZTP service processes the DHCP response and updates *src* and *acl_src* values in */etc/sonic/updategraph.conf* file and restarts updategraph service. In the updategraph.service definition file, updategraph.service wants ztp.service. When ZTP feature is available in the build, updategraph does not creates default *''/etc/sonic/config_db.json'* from preset config templates.

If */tmp/config_migration* is set, ZTP will not create switch default configuration but wait for config_migration to be completed.

**Image Upgrade**

When a new SONiC image is installed, contents of */etc/sonic* directory are migrated to the newly installed directory. ZTP JSON and ZTP configuration files are also migrated as part of this configuration migration step. If the image upgrade happened as part of a ZTP session in progress, after booting the new image, ZTP resumes from the point where it left of prior to image switchover. ZTP service waits for configuration migration to complete before taking any action. If after configuration migration, if */etc/sonic/config_db.json* file is not found, ZTP service creates a ZTP preset configuration that enables all in-band interfaces and performs DHCP discovery on them. This establishes connectivity to external devices for provisioning to be completed. 

There can also be a scenario where on a switch a ZTP is in completed (SUCCESS/FAILED) state. A new SONiC image is installed and user reboots the switch to boot into new image. Even this scenario, contents of */etc/sonic* and ZTP JSON, ZTP configuration files are migrated to the newly installed image. A new session of ZTP is started using the ZTP JSON file that was migrated. If */etc/sonic/config_db.json* file does not exist, ZTP service creates a ZTP preset configuration that enables all in-band interfaces and performs DHCP discovery on them. This establishes connectivity to external devices for provisioning to be completed. It is to be noted that no new ZTP JSON file is downloaded as it is assumed that in a typical scenarios, a successful ZTP would have generated a *config_db.json* file which is migrated to the new image. By not  performing DHCP discovery again, we are trying to minimize the affect on the network where in connectivity is provided by the migrated switch configuration and ZTP is re-executed to perform all tasks that are needed for the new switch image.



 ### 3.8 ZTP State Transition Diagram

Below figure explains the events and its effect on ZTP state.

![ztp-states.png](images/ztp-states.png)

## 4. Chronology of Events

User is expected to use supported installation methods by SONiC to install image. One such tool is ONIE on supported switches. Installation of SONiC on to the switch for the first time is out of scope of SONiC ZTP framework.

Below is sequence of events that happen in a simple workflow.

1.  SONiC switch boots and ZTP service starts
2.  DHCP server provides IP connectivity to management interface along with DHCP Option 67 which provides URL to ZTP JSON file
3. ZTP service downloads ZTP JSON file and processes individual configuration sections in the lexical sorted order of their names, one at a time.
4. Plugin scripts for each configuration section are executed. If it is user-defined, the plugin is downloaded and then executed.
   - If plugin exits with success (= 0), the configuration section is marked SUCCESS and not executed again.
   - If plugin exits with failure (> 0), the configuration section is marked FAILED and not executed again.
   - If plugin exits with *suspend-exit-code* , the configuration section is marked SUSPEND and executed again in next cycle.
5. ZTP service cycles through all configuration sections multiple times until each and every configuration section is either in SUCCESS or FAILED state. This is to address sections that have returned with (-1) return code.
6. ZTP result is evaluation based on the result of each configuration section and ZTP service exits and does not run again.

All possible scenarios are not described here as they have been explained in the [ZTP Service](#34-ztp-service) section.

## 5. Security Considerations

### 5.1 Secure Communication

SONiC ZTP framework requires some data exchanged between the remote provisioning server and SONiC switch. Some of this data can be viewed by a hacker by snooping the contents of packets in the network. For example, the ZTP JSON data can be obtained by looking into DHCP packets on the network. A hacker can then use the ZTP JSON contents to determine the configuration deployed on the switch. Similarly, a hacker can spoof the data exchanged between switch and the server.

To solve this problem, couple of options are provided by the SONiC ZTP framework.
- File encryption and authentication
- Use Secure communication protocol

#### 5.1.1 Encryption and Authentication

The data that is exposed to network during ZTP process is following:

- ZTP JSON file
- Plugin files downloaded
- Any other files downloaded during ZTP in unencrypted mode (HTTP, FTP, TFTP)

SONiC ZTP provides basic elementary framework to establish encrypted communication which can also be authenticated at the switch. AES encryption is used to encrypt files stored on the provisioning server. Then RSA key pair with SHA-512 hash algorithm is used to generate a digital signature to authenticate the decrypted content after it has been downloaded. All URL's used in ZTP JSON are encoded as URL objects. An additional object "encrypted" is added to URL object to indicate that the contents of the file downloaded needs to be decrypted and authenticated on the switch.

In below example configuration section, Config DB JSON file is being pushed to the switch. It is stored as an encrypted file using an AES key.

```json
  "configdb-json": {
    "url": {
      "source": "http://192.168.1.1:8080/spine01_config_db_encrypted.json",
      "destination": "/etc/sonic/config_db.json",
      "encrypted": {
        "fingerprint": "xxxxxxxxxxxxxxxxxxx",
        "fingerprint-hash-algorithm": "SHA-512"
      }
    }
  }
```

When ZTP service is processing the *url*  object, it checks if *url.encrypted* object is present. It then downloads the file and uses the same AES key stored in the SONiC switch to decrypt the downloaded file. If decryption procedure succeeds, the contents of the file are used to generate a fingerprint and matched against the value defined *url.encrypted.fingerprint*. Only if fingerprint matches, the file is placed in intended destination. Any errors encountered during this process are thus identified by the plugin processing the *url* object and corrective actions are taken.

Similarly, ZTP JSON can also be supplied in encrypted format. Below is the initial ZTP JSON file which is first downloaded as pointed by the URL in DHCP Option 67. ZTP service then downloads, decrypts and authenticates the encrypted version of ZTP JSON. The final ZTP JSON is then processed.

```json
{
  "ztp": {
    "url": {
      "source": "http://192.168.1.1:8080/ztp_encrypted.json",
      "destination": "/var/lib/dhcp/ztp.json",
      "encrypted": {
        "fingerprint": "xxxxYYYYxxxZZZZxxxx",
        "fingerprint-hash-algorithm": "SHA-512"
      }
    }
  }
}
```

Files downloaded inside of user defined plugins need to use their own security methods. They will not be automatically handled by the ZTP service.

#####  Installing Keys
User is required to generate one symmetric key (AES) and an asymmetric key pair (RSA). The symmetric key is used for encryption and decryption of files. The private key of the RSA key pair is used to generate a fingerprint hash. The public key of the RSA key pair is used to verify the fingerprint hash.

The RSA public key and AES key need to be included in SONiC switch image at build time as */usr/lib/ztp/keys/fingerprint_key.pub* and */usr/lib/ztp/keys/decryption_key*. The inclusion of the keys in the build image can be done using organizational extensions or by placing them in the appropriate place in the SONiC ZTP package source directory.

#### 5.1.2 Secure Medium
The security concerns can be solved by using a secure protocol like HTTPS for downloading the contents. Users use https URLs and ZTP service verifies the server certificate against known trusted CA certificates on the switch. Thus a trusted and secure communication is established.

#####  Installing Certificates
In case of HTTPS URL's, the certificate issuing authority's certificate which issued the server's SSL certificate needs to be installed on the switch as part of default image at build time. */etc/ssl/certs* is the directory to install these certificates. This can be done using organizational extensions or by placing them in the *usr/lib/ztp/certs*  directory inside SONiC ZTP package source code directory.

### 5.2 File Permissions

Only *root* user is allowed to read and modify the files created by ZTP service. This includes all downloaded files and generated temporary files during ZTP activity.

## 6. Configuring ZTP

Following are the supported ZTP configuration commands. All configurable parameters are found in *ztp_cfg.json*. ZTP service reads the configuration file during initialization.

### ztp status

*ztp status* command displays current state of ZTP service and the date/time since it was in the current state. It also displays current status of each configuration section of user provided ZTP JSON and date/time it was last processed.

### ztp enable
*ztp enable* command is used to administratively enable ZTP. When ZTP feature is included as a build option, ZTP service is configured to be enabled by default. This command is used to re-enable ZTP after it has been disabled by user. It is to be noted that this command will only modify the ZTP configuration file and does not perform any other actions.

### ztp run

*ztp run* command is used to restart ZTP of a SONiC switch and initiate intended configuration tasks. Also ZTP service is started if it is not already running. This command is useful to restart ZTP after it has failed or is disabled by user.

### ztp disable
*ztp disable* command is used to stop and disable ZTP service. If ZTP service is in progress, it is aborted and ZTP status is set to disable in configuration file.  SIGTERM is sent to ZTP service and its sub processes currently under execution. *systemd* defined default time of 90 seconds is provided for them to handle the SIGTERM and take appropriate action and gracefully exit. It is the responsibility of plugins to handle SIGTERM to perform any necessary cleanup or save actions. If the process is still running after 90s the process is killed.

ZTP service does not run if it is disabled even after reboot. User will have to use *ztp enable* for it to enable it administratively again.

##  7. Code Structure

Code related to ZTP framework shall be included in azure/sonic-ztp github repository. The package will be named as sonic_ztp_*version*_all.deb.

More information will be added to this section after implementation of SONiC-ZTP is complete.

## 8. Logging
All output generated by ZTP service are logged to local syslog and stdout of the service. The *stdout* and *stderr* of executed plugins are are also redirected to syslog and stdout of ZTP service. In addition to this, logs are are also sent to */var/log/ztp.log* file. User can modify */usr/lib/ztp/ztp_cfg.json* to increase or decrease logging priority level. User can also disable logging to file */var/log/ztp.log* or change to which file logs can be written to. Default logging level is assumed to be of level INFO. All messages with severity of INFO or greater are logged.

## 9. Debug
ZTP service can be started in optional debug mode providing more verbose information on steps being performed by the service. Set logging level in */usr/lib/ztp/ztp_cfg.json* to 'DEBUG'.

## 10. Examples

### Example #1

Use this ZTP JSON file which performs following steps on first boot
1. Install firmware
2. Push configuration
3. Run post-provisioning scripts and reboot on success
4. Run connectivity check scripts


```json
{
  "ztp": {
    "01-firmware": {
      "install": {
        "url": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin",
        "pre-check": {
          "url": "http://192.168.1.1:8080/firmware_check.sh"
        },
        "set-default": true
      },
      "reboot-on-success": true
    },
    "02-configdb-json": {
      "dynamic-url": {
        "source": {
          "prefix": "http://192.168.1.1:8080/",
          "identifier": "hostname",
          "suffix": "_config_db.json"
        },
        "destination": "/etc/sonic/config_db.json"
      }
    },
    "03-provisioning-script": {
      "plugin": {
        "url":"http://192.168.1.1:8080/post_install.sh"
      },
      "reboot-on-success": true
    },
    "04-connectivity-tests": {
      "plugin": {
        "url": "http://192.168.1.1:8080/ping_test.sh"
      }
    }
  }
}
```

## 11. Future

More predefined plugins can be added as deemed appropriate by wider audience.



## 12. ZTP Feature Test Suite

### 12.1 Overview

This test plan describes tests to exercise various capabilities of Zero Touch Provisioning (ZTP). The scope of these tests is limited to testing ZTP and not SONiC protocol applications functionality. Certain central features like loading a switch configuration and applying them on the switch, installing new switch image are also part of this test plan.

### 12.2 Test setup

- Out-of-band Provisioning
  - DHCP server to assign IP address to management interface (eth0)
  - Web server to host scripts and other relevant files needed for provisioning
- In-band Provisioning
  - DHCP server to assign IP address to front-panel ports. Ensure that the DHCP server is one hop away and there is a DHCP relay agent to ensure DHCP requests/response are forwarded to next hop.
    - DHCP server <-----> [DHCP Relay agent] <-------------> [DUT] 
  - Web server to host scripts and other relevant files needed for provisioning reachable over front panel interfaces. 
- Test ZTP JSON files as per test case
- Plugin scripts for processing ZTP JSON
- Switch configuration files (config_db.json, minigraph.xml, acl.json)
- Few different versions of switch firmware images

## 12.3 Test Cases Summary

1. Verify that ZTP can be initiated using ZTP JSON URL provided as part of DHCP Option 67 using out-of-band management network.

2. Verify that ZTP can be initiated using ZTP JSON URL provided as part of DHCP Option 67 using front panel ports

3. Use IPv6 transport for provisioning

4. Define and perform multiple configuration tasks as part of ZTP. 

5. Verify support for reboot and resume in the middle of execution of a configuration section in the middle of ZTP process.

6. Verify ZTP feature to reboot the switch when a configuration section was executed with/with out any errors.

7. Verify ZTP feature to ignore the failed result of executing an individual configuration section and determine ZTP result as success

8. Verify that a configuration section can be suspended and retried by exiting with a specific program exit code.

9. Verify processing of configuration sections with user-defined plugins using URL object

10. Verify processing of configuration sections with user-defined plugins using dynamic URL object

11. Verify installation of new SONiC firmware image using pre-defined firmware plugin

12. Verify uninstalling an installed SONiC firmware from a switch using pre-defined firmware plugin

13. Verify installation of a docker package using pre-defined firmware plugin

14. Verify deployment of a config_db.json file using pre-defined config-db-json plugin

15. Verify deployment of minigraph.xml and acl.json using pre-defined graphservice plugin

16. Verify configuration of SNMP community string using pre-defined snmp plugin

17. Verify use of a simple executable script using DHCP option 239 as an alternative to ZTP JSON

18. Verify that ZTP is executed to completion (success/failed) only once. After completion, even a reboots should cause ZTP to execute again

19. Verify that ZTP can be disabled by using 'ztp disable' and 'ztp run' command

20. Verify that 'systemctl stop ztp' command stops an in-progress ZTP session and 'systemctl start ztp' resumes the service from where it has left off

21. Verify that 'ztp status' command displays information about an in-progress ZTP session or last completed session

22. Verify that DHCP Option 67 is given precedence over DHCP Option 239 when both of them are provided by the DHCP response. DHCP Option 239 is ignored

23. Verify that ZTP service exits with a failure when ZTP configuration file*/usr/lib/ztp/ztp_cfg.json* is not present or contains incorrect data

24. Verify behavior when a ZTP session is in progress and as part of ZTP, install a new SONiC switch image and reboot to newly installed image

25. Verify behavior when a ZTP session has completed (FAILED/SUCCESS) and a new SONiC image is installed, switch reboots into the newly installed image

26. Verify behavior of ZTP when */etc/sonic/config_db.json* file is not found during switch bootup

27. Verify that ZTP service can be re-enabled and restarted using 'ztp enable' and 'ztp run' command

28. Verify that all files downloaded and created by ztp service in */var/lib/ztp* directory cannot be read by regular users. Only root privileged users can read them

29. Verify behavior of ZTP service when DHCP Options 225-minigraph_url, 226-acl_url and 67 - ZTP JSON file are all sent by the DHCP server

30. Verify logging of ZTP service

    

### 12.4 Test Cases

### Test Case #1

**Objective:** Verify that ZTP can be initiated using ZTP JSON URL provided as part of DHCP Option 67 using out-of-band management network.

**Test Steps:**

- Define a simple ztp_data.json file and place it on a reachable web server over eth0
- Configure DHCP server to assign IP address to the eth0 and also send DHCP Option 67 with value = <web url to ztp_data.json>
- Install SONiC switch image from ONIE prompt

**Expected Result:**

- When SONiC switch boots and eth0 gets ip address, ztp service identifies the ztp json url from DHCP Option 67
- ZTP service successfully downloads the ztp json file and processes it.

**Additional Tests:**

- File without JSON content or  with JSON content but incorrect format
  - ZTP service exits and logs an error.
- Syntactically valid URL string but not working
  - ZTP service keeps retrying to download the URL
- Syntactically invalid URL string
  - ZTP service exits and logs an error
- DHCP Option 67 is not specified
  - ZTP service remains active and continues to wait till a DHCP offer with Option 67 value set is provided

### Test Case #2

**Objective:** Verify that ZTP can be initiated using ZTP JSON URL provided as part of DHCP Option 67 using front panel ports

**Test Steps:**

- Define a simple ztp_data.json file and place it on a reachable web server over front panel interface
- Configure DHCP server to assign IP address and also send DHCP Option 67 with value = <web url to ztp_data.json>
- Install SONiC switch image from ONIE prompt using a USB media or over out-of-band management network

**Expected Result:**

- When SONiC switch boots, ZTP service enables all front panel ports and starts DHCP on every single port including eth0
- One of the interface where the working DHCP server is connected to, receives IP address.
- ztp service identifies the ztp json url from DHCP Option 67
- ZTP service successfully downloads the ztp json file and processes it.

**Additional Tests:**

- More than one DHCP servers are connected	
  - DHCP information received from first interface with DHCP Option 67 is processed 
- No DHCP server is connected to in-band network for a very long time
  - Switch continues to try DHCP on in-band interfaces until a DHCP response is received
- After a long wait time a DHCP server is connected to Out of band network instead of in-band-network
  - ZTP continues using DHCP assignment received from out-of-band network 

### Test Case #3

**Objective:** Use IPv6 transport for provisioning

**Test Steps:**

- Use DHCPv6 server and repeat TestCase #1 and TestCase #2

### Test Case #4

**Objective:** Define and perform multiple configuration tasks as part of ZTP. 

**Test Steps:**

- Define ZTP JSON with 4 configuration sections each performing different tasks
- Define sections using names '03-conf-task', '01-conf-task-1',  '04-end-step', '02-conf-task'
- Define user-defined plugin's for each configuration section using URL object 
- Use steps defined in *Test Case #1* to initiate ZTP

**Expected Result:**

- Tasks are performed in sorted order of their names even though they are defined out of order in the ZTP JSON file -  '01-conf-task-1',  '02-conf-task', '03-conf-task', '04-end-step'
- Result of ZTP is success only if all configuration task's results are success

**Additional Tests:**

- Define just one configuration section
  - The defined configuration section is executed
- Do not define any configuration sections but have only top level ztp section
  - ZTP is marked as complete and successful as there are not configuration sections to be processed
- Define ZTP JSON file without top level ztp section
  - ZTP service exits and logs an error

### Test Case #5

**Objective:** Verify support for reboot and resume in the middle of execution of a configuration section in the middle of ZTP process.

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks
- Inside the plugin script of 3rd task, ''03-conf-task', issue a reboot command and let switch restart

**Expected Result:**

- After reboot ZTP **will not** execute 01-config-task-1 and 02-conf-task2.
- ZTP executes *03-conf-task* and *03-end-step* in order
- Result of ZTP is success only if all configuration task's results are success

### Test Case #6

**Objective:** Verify ZTP feature to reboot the switch when a configuration section was executed with/with out any errors.

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks
- In ZTP JSON, for configuration section '03-conf-task', include "reboot-on-success: true"

**Expected Result:**

- ZTP  executes '01-config-task-1', '02-conf-task2' and '03-conf-task' to completion.
- ZTP reboots the switch
- After reboot ZTP continues to execute '04-end-step' after which marks ZTP as completed

**Additional Tests:**

- Modify  '03-conf-task' plugin script to return failure
  - ZTP does not reboot the switch and continues to execute '04-end-step' after which ZTP is marked as completed.
- reboot-on-success: false
  - ZTP does not reboot the switch and continues to execute '04-end-step' after which ZTP is marked as completed.
- An invalid value is specified for reboot-on-success field. e.g 'reboot-on-success: "foo"' instead of true/false
  - reboot-on-success field is ignored and, ZTP does not reboot the switch and continues to execute '04-end-step' after which ZTP is marked as completed.
- Include 'reboot-on-failure: true' and modify  '03-conf-task' plugin script to return failure
  - switch reboots after executing '03-conf-task'.
- Include 'halt-on-failure' : 'true' for '03-conf-task' and modify plugin script to return failure
  - '01-config-task-1', '02-conf-task2' and '03-conf-task' are executed and ZTP stops.  '04-end-step' is not executed.

### Test Case #7

**Objective:** Verify ZTP feature to ignore the failed result of executing an individual configuration section and determine ZTP result as success.

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks

- In ZTP JSON, for configuration section '03-conf-task', include "ignore-result: true"

- Modify  '03-conf-task' plugin script to return failure

  

**Expected Result:**

- ZTP  executes all tasks to completion.
- Even though '03-conf-task' status is FAILED, since ignore-result is set, overall ZTP result is considered as SUCCESS

**Additional Tests:**

- An invalid value is specified for ignore-result field. e.g 'ignore-result: "foo"' instead of true/false
  - ignore-result field is ignored and, ZTP considers failure of '03-conf-task' as reason for marking ZTP result as FAILED.
- ignore-result: false
  - ZTP considers failure of '03-conf-task' as reason for marking ZTP result as FAILED.

### Test Case #8

**Objective:** Verify that a configuration section can be suspended and retried by exiting with a specific program exit code.

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks

- In ZTP JSON, for configuration section  '02-conf-task2' , '03-conf-task', include "suspend-exit-code: 2"

- Modify  '02-conf-task2' plugin script to return exit code 2 for three successive executions after which return exit code 0. Implement logic in the plugin script to keep track how many times the plugin script is executed.

- Modify  '02-conf-task2' plugin script to return exit code 2 for five successive executions after which return exit code 0. Implement logic in the plugin script to keep track how many times the plugin script is executed.

  

**Expected Result:**

- ZTP starts executing all tasks in the order  '01-conf-task-1',  '02-conf-task', '03-conf-task', '04-end-step'
- After first cycle, since  '02-conf-task' and '03-conf-task' have returned with error code equal to suspend-exit-code, they are executed again
- Execution sequence looks like this
  - Cycle 1 - '01-conf-task-1',  '02-conf-task', '03-conf-task', '04-end-step'
  - Cycle 2 - '02-conf-task', '03-conf-task'
  - Cycle 3 -'02-conf-task', '03-conf-task'
  - Cycle 4 -'03-conf-task'
  - Cycle 5 -'03-conf-task'
- ZTP result is marked as success

**Additional Tests:**

- An invalid value is specified for suspend-exit-code. e.g 'suspend-exit-code: "foo"' or suspend-exit-code: 0 instead of a valid integer > 0
  - suspend-exit-code field is ignored and ZTP does not execute the configuration section again
- Use value of suspend-exit-code: 1 while the script returns exit code 2
  - ZTP considers  02-conf-task and 03-conf-task result as failed and does not execute them again

### Test Case #9

**Objective:** Verify processing of configuration sections with user-defined plugins using URL object

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks
- url object is used to define user-defined plugins for the configuration tasks in ZTP JSON

**Expected Result:**

- Plugins for each configuration task are downloaded and executed
- All configuration sections are executed in order and ZTP is marked as complete
- File download requests include http headers. Check using wireshark or at http server end
  - User-Agent
  - PRODUCT-NAME
  - SERIAL-NUMBER
  - BASE-MAC-ADDRESS
  - SONiC-VERSION

**Additional Tests:**

- *destination* is not defined as part of URL object

  - Destination file name is resolved using the filename extracted from the URL source

- *source*  is not defined as part of URL object

  - Configuration section is marked as FAILED and not executed again

- Invalid data type value is assigned to URL object (e.g url : true)

  - Configuration section is marked as FAILED and not executed again

- Incorrectly formatted URL string is used as source

  - Configuration section is marked as FAILED and not executed again

- For an HTTPS URL that requires certificate checking use secure: false

  - Download operation fails
  - Configuration section is marked as FAILED and not executed again

- include-http-headers:false

  - Observe that http headers are not included in the http request sent by the switch

- "url": "source-string"

  - Using shorthand notation of url object uses its value as source string and does not look for sub objects

  

### Test Case #10

**Objective:** Verify processing of configuration sections with user-defined plugins using dynamic URL object

**Test Steps:**

- Use steps defined in *Test Case #4* to initiate ZTP and perform configuration tasks
- Also set the hostname of switch as host777 as part of DHCP response
- dynamic-url object is used to define user-defined plugins for the configuration tasks in ZTP JSON
- Store the plugin script as *file_host777_setup.sh*
- Inside dynamic-url, define:
  - prefix: 'http://192.168.1.1:8080/plugins/file_'
  - identifier: 'hostname'
  - suffix: '_setup.sh'

**Expected Result:**

- Plugins URL's for each configuration task are constructed at runtime, downloaded and executed. 
- The source.identifier field is used to construct the url source as prefix + hostname + suffx =  'http://192.168.1.1:8080/plugins/file_host777_setup.sh'
- All configuration sections are executed in order and ZTP is marked as complete
- File download requests include http headers. Check using wireshark or at http server end
  - User-Agent
  - PRODUCT-NAME
  - SERIAL-NUMBER
  - BASE-MAC-ADDRESS

**Additional Tests:**

- Use different values for source.identifier and filename on the server

  - hostname-fqdn
  - serial-number
  - product-name
  - sonic-version

- *destination* is not defined as part of URL object

  - Destination file name is resolved using the filename extracted from the URL source or assigned a unique file by ZTP

- User provided script to evaluate the identifier string.  'identifier: url'

  - The script specified is downloaded and executed. Output of the script is used for constructing the url source string

- User provided script to evaluate the identifier string.  'identifier: url' with script which fails during execution

  - Configuration section is marked as FAILED and not executed again

- User provided script to evaluate the identifier string.  'identifier: url' which is incorrectly formatted or not working

  - Download operation fails
  - Configuration section is marked as FAILED and not executed again

- *source*  is not defined as part of dynamic-url object

  - Configuration section is marked as FAILED and not executed again

- source.prefix is not defined, source.identifier and source.suffix are defined

  - url string is constructed as value of identifier + suffix

- source.prefix is defined or source.identifier and source.suffix is not defined

  - url string is constructed as prefix + value of identifier

- source.identifier is not defined

  - url string is constructed as value of identifier

- source.identifier is not defined

  - Configuration section is marked as FAILED and not executed again

- For an HTTPS url that requires certificate checking use secure: false

  - Download operation fails
  - Configuration section is marked as FAILED and not executed again

- include-http-headers:false

  - Observe that http headers are not included in the http request sent by the switch

- Invalid data type value is assigned to dynamic-url object (e.g 'dynamic-url' : 'foo')

  - Configuration section is marked as FAILED and not executed again

  

### Test Case #11

**Objective:** Verify installation of new SONiC firmware image using pre-defined firmware plugin

**Test Steps:**

- Define a ZTP JSON file with configuration section 'firmware'
- Define install section within firmware using url object to specify the link to download a SONiC image

**Expected Result:**

- SONiC image is download and installed
- Use 'sonic_installer list' command to view if the new image has been installed

**Additional Tests:**

- Use dynamic-url to specify the link to download source code of the switch from
  - SONiC image is download and installed
- Invalid image file is provided
  - Download of file succeeds but sonic_install of the downloaded file fails
  - Configuration section is marked as failed and ZTP is marked as failed
- Invalid url/dynamic-url data is provided
  - Configuration section is marked as failed and ZTP is marked as failed
- url/dynamic-url objects are not defined
  - Configuration section is marked as failed and ZTP is marked as failed
- set_default: true
  - After downloading and installing the firmware image, the image is set as the image switch is going to boot on next reboot and every reboot after that unless modified
  - Verify using 'sonic_installer list' command
- set_next_boot: true 
  - After downloading and installing the firmware image, the image is set as the image switch is going to boot on next reboot. This is only for next reboot.
  - Verify using 'sonic_installer list' command
- pre-check script is used 
  - The pre-check script is downloaded and executed. If the program exit code is 0, download and install of firmware is performed. If the exit code is non-zero, download/install of firmware image is not performed
  - Configuration section result is marked as SUCCESS.
- url provided by pre-check cannot be downloaded or invalid data is provided
  - The pre-check step is determined as failed and download/install of the image is not performed.
  - Configuration section result is marked as FAILED

### Test Case #12

**Objective:** Verify uninstalling an installed SONiC firmware from a switch using pre-defined firmware plugin

**Test Steps:**

- Define a ZTP JSON file with configuration section 'firmware'
- Define remove section within firmware
- Specify version of the installed image you wish to remove

**Expected Result:**

- SONiC image with specified version is removed
- Use 'sonic_installer list' command to view if the new image version has been removed

**Additional Tests:**

- A non-existent version is specified
  - Configuration section is marked as failed and ZTP is marked as failed
- Version object is not specified
  - Configuration section is marked as failed and ZTP is marked as failed
- pre-check script is used 
  - The pre-check script is downloaded and executed. If the program exit code is 0, removal of specified version is performed. If the exit code is non-zero, removal of the image is not performed.
  - Configuration section result is marked as SUCCESS.
- url provided by pre-check cannot be downloaded or invalid data is provided
  - The pre-check step is determined as failed and image removal is not performed
  - Configuration section result is marked as FAILED
- Both install and remove sections are defined in firmware
  - remove section is processed first, then install section is processed.



### Test Case #13

**Objective:** Verify installation of a docker package using pre-defined firmware plugin

**Test Steps:**

- Define a ZTP JSON file with configuration section 'firmware'
- Define upgrade_docker section within firmware using url object to specify the link to download the docker image

**Expected Result:**

- Docker package is download and installed
- Use 'docker images' command to view if the new image has been installed

**Additional Tests:**

- Use dynamic-url to specify the link to download source code of the switch from

  - Docker image is download and installed

- Invalid image file is provided

  - Download of file succeeds but sonic_install of the downloaded file fails
  - Configuration section is marked as failed and ZTP is marked as failed

- Invalid url/dynamic-url data is provided

  - Configuration section is marked as failed and ZTP is marked as failed

- url/dynamic-url objects are not defined

  - Configuration section is marked as failed and ZTP is marked as failed

- pre-check script is used 

  - The pre-check script is downloaded and executed. If the program exit code is 0, download and install of docker image is performed. If the exit code is non-zero, download/install of docker image is not performed
  - Configuration section result is marked as SUCCESS.

- url provided by pre-check cannot be downloaded or invalid data is provided

  - The pre-check step is determined as failed and download/install of the docker image is not performed.
  - Configuration section result is marked as FAILED

  

### Test Case #14

**Objective:** Verify deployment of a config_db.json file using pre-defined config-db-json plugin

**Test Steps:**

- Define a ZTP JSON file with configuration section 'config-db-json'
- Include url object to specify the link to download config_db.json for the file
- destination field is not specified in url

**Expected Result:**

- Config JSON file is downloaded and placed in location ''/etc/sonic/config_db.json'
- Configuration is applied to the switch

**Additional Tests:**

- dynamic-url object is used instead of url object
  - Configuration is downloaded and applied to the switch
- Invalid or no url/dynamic-url object is specified
  - Configuration section is marked as failed and ZTP is marked as failed
- Both dynamic-url and url objects are defined
  - dynamic-url is used
- destination is specified in url/dynamic-url
  - Configuration file is download as specified in destination file
  - Downloaded configuration file is applied to the switch
- Invalid config json file is used
  - Configuration section is marked as failed and ZTP is marked as failed

### Test Case #15

**Objective:** Verify deployment of minigraph.xml and acl.json using pre-defined graphservice plugin

**Test Steps:**.

- Define a ZTP JSON file with configuration section 'graphservice'
- Include minigraph_url to specify the url object for the link to download minigraph.xml file
- Include acl_url to specify the url object for the link to download acl.json file

**Expected Result:**

- minigraph.xml is downloaded and updategraph service uses its value to process and load it into config db
- acl.json file is downloaded and updategraph service processes it

**Additional Tests:**

- Use dynamic-url instead of url object
  - minigraph.xml and acl.json are downloaded and processed
- Invalid or unreachable url/dynamic-url object is specified
  - Configuration section is marked as FAILED and ZTP is marked as FAILED
- Only acl_url / minigraph_url is specified
  - Appropriate file is downloaded and processed
- No acl_url or minigraph_url is specified
  - Configuration section is marked as FAILED and ZTP is marked as FAILED
- In acl_url /minigraph_url both url and dynamic-url are mentioned
  - URL string specified by dynamic-url is used and url object is ignored

### Test Case #16

**Objective:** Verify configuration of SNMP community string using pre-defined snmp plugin

**Test Steps:**

- Define a ZTP JSON file with configuration section 'snmp'
- Include "community-ro" and "community-rw" with appropriate values specifying the community string

**Expected Result:**

- SNMP agent is configured with user provided community string
- SNMP agent is restarted after setting the community string

**Additional Tests:**

- Set restart_agent : false
  - SNMP agent is configured with user provided community string
  - SNMP agent is not restarted after setting the community string
- Invalid value is provided as values for  "community-ro" 
  - Configuration section is marked as FAILED and ZTP is marked as failed
- Invalid value is provided as values for  "community-rw" 
  - Configuration section is marked as FAILED and ZTP is marked as failed
- Only "community-ro" or "community-rw" values are specified
  - Appropriate community string is configured with SNMP agent
- Invalid value is specified for restart_agent
  - Presence of the field is ignored and SNMP agent is restarted when a valid community string is set
- Both "community-ro" and "community-rw" are not specified
  - Configuration section is marked as FAILED and ZTP is marked as failed
- A list of community strings is configured
  - SNMP agent should be configured with the full list of community strings provided



### Test Case #17

**Objective:** Verify use of a simple executable script using DHCP option 239 as an alternative to ZTP JSON

**Test Steps:**

- Configure DHCP server to send url of an executable script as part of DHCP Option 239 
- Install SONiC image from ONIE prompt
- Boot SONiC switch boots for the first time and let it obtain IP address via DHCP

**Expected Result:**

- ZTP service downloads the script from the url link provided by DHCP option239
- Downloaded script is executed
- ZTP is marked as SUCCESS if the script returns exit code 0
- ZTP is marked as FAILED if the script returns exit code > 0

**Additional Tests:**

- Invalid or not working URL is provided
  - ZTP continues to try to download the file every 30 seconds
- Include a REBOOT inside the provisioning script
  - When switch boots, ZTP downloads the provisioning script again and starts execution again from the begining

### Test Case #18

**Objective:** Verify that ZTP is executed to completion (success/failed) only once. After completion, even a reboots should cause ZTP to execute again.

**Test Steps:**

- Follow steps defined Test case #1 and complete a ZTP session with SUCCESS status
- Reboot the switch manually after ZTP service exits

**Expected Result:**

- ZTP process is not executed once again even if DHCP server provides Option 67 / Option 239

**Additional Tests:**

- ZTP completed with FAILED status and switch is rebooted
  - ZTP process is not executed once again even if DHCP server provides Option 67 / Option 239
- ZTP completed with FAILED/SUCCESS status and ztp service is restarted using 'systemctl start ztp'
  - ZTP process is not executed once again. It exits without throwing any error.

### Test Case #19

**Objective:** Verify that ZTP can be disabled by using 'ztp disable' command.

**Test Steps:**

- Initiate a ZTP session using test steps described in Test Case #1
- Make sure that the scripts executed take sufficiently long time to execute. Use sleep or loop statements
- While the ZTP session is in progress issue 'ztp disable' command

**Expected Result:**

- ZTP session is aborted and all the processes spawned by ZTP are also killed and there are no zombie processes performing provisioning steps 

**Additional Tests:**

- Restart ZTP service using 'systemctl start ztp'
  - ZTP is administratively disabled and thus even when ztp service is restarted systemctl command or switch reboots, it simply exits without performing any provisioning tasks	
- Reboot the switch after performing 'ztp disable'
  - ZTP session does not start
- Issue 'ztp disable' after ZTP session has completed
  - ZTP is administratively disabled in ztp_cfg.json
  - User has to issue 'ztp enable' for ZTP to be enabled again.

### Test Case #20

**Objective:** Verify that 'systemctl stop ztp' command stops an in-progress ZTP session and 'systemctl start ztp' resumes the service from where it has left off.

**Test Steps:**

- Initiate a ZTP session using test steps described in Test Case #1
- Make sure that the scripts executed take sufficiently long time to execute. Use sleep or loop statements
- While the ZTP session is in progress issue 'systemctl stop ztp' command
- Restart ZTP service using 'systemctl start ztp'

**Expected Result:**

- Observe that completed configuration tasks are not executed again
- ZTP session resumes from the configuration task which was interrupted
- All processes spawned during the previous interrupted ZTP session are not executing

**Additional Tests:**

- Issue 'systemctl restart ztp'
  - Same as expected results

### Test Case #21

**Objective:** Verify that 'ztp status' command displays information about an in-progress ZTP session or last completed session

- Overall ZTP status (FAILED / SUCCESS / IN-PROGRESS)
- Date/time of ZTP status
- Individual configuration task  status (FAILED / SUCCESS / IN-PROGRESS / SUSPEND)
- Date/time of individual configuration task status

**Test Steps:**

- Initiate a ZTP session using test steps described in Test Case #8
- Just before ZTP session starts issue 'ztp status' command
- While ZTP session in progress issue 'ztp status' command
- After ZTP session has finished issue 'ztp status' command

**Expected Result:**

- ZTP status and individual configuration section results are displayed along with their date/time stamps

### Test Case #22

**Objective:** Verify that DHCP Option 67 is given precedence over DHCP Option 239 when both of them are provided by the DHCP response. DHCP Option 239 is ignored.

**Test Steps:**

- Configure DHCP server to send url of an executable script as part of DHCP Option 239  and link to ZTP JSON file using DHCP Option 67
- Install SONiC image from ONIE prompt
- Boot SONiC switch boots for the first time and let it obtain IP address via DHCP

**Expected Result:**

- ZTP service starts and ignores DHCP option 239 and uses ZTP JSON file using the URL provided in Option 67

**Additional Tests:**

- Include a non-working URL for DHCP Option 67
  - ZTP service will still try to download the ZTP JSON url instead of using DHCP Option 239 URL
- Reboot the switch after ZTP session is complete
  - ZTP service will not use DHCP Option 239 as it has been marked as complete
- Use just DHCP Option 239 and complete a ZTP session followed by reboot. This time DHCP Option 67 is sent unlike in previous case
  - ZTP service will not start processing ZTP JSON as ZTP is already in completed state by processing the DHCP Option 239

### Test Case #23

**Objective:** Verify that ZTP service exits with a failure when ZTP configuration file */usr/lib/ztp/ztp_cfg.json* is not present or contains incorrect data

**Test Steps:**

- Modfy contents with invalid values, incorrect JSON format or delete the file /usr/lib/ztp/ztp_cfg.json
- Start ztp service

**Expected Results:**

- ZTP service exits with a failure and log message indicating error reading the ZTP configuration file

### Test Case #24

**Objective:** Verify behavior when a ZTP session is in progress and as part of ZTP, install a new SONiC switch image and reboot to newly installed image

**Test Steps:**

- Define a ZTP JSON file with multiple configuration sections
- Include a firmware configuration task which installs a new SONiC image version and also set_default : true
- Include reboot-on-success flag for the firmware task so that switch reboots after successful installation of the image

**Expected Results:**

- When sonic_installer installs the new firmware on the switch,  it creates a backup copy of existing configuration files on the switch intended to be migrated when it boots into new image on reboot
- ZTP JSON file is also backed up along with these files
- Switch boots into new image and ZTP resumes provisioning from the configuration task after firmware installation.
- ZTP runs to completion
- It is expected that a valid /etc/sonic/config_db.json file is created prior to installing firmware image and this provides connectivity to external entities for provisioning to proceed

**Additional Tests:**

- When the newly installed image is booted, there is no */etc/sonic/config_db.json*.

  - ZTP creates a preset config and enables all in-band interfaces and performs DHCP discovery
  - After that ZTP proceeds to resume processing of the ZTP JSON file which has been migrated

  

### Test Case #25

**Objective:** Verify behavior when a ZTP session has completed (FAILED/SUCCESS) and a new SONiC image is installed, switch reboots into the newly installed image

**Test Steps:**

- Initiate a ZTP session and run to completion
- Install a new firmware image using 'sonic_installer' command line utility and set the switch to boot into this newly installed image on reboot
- Reboot the switch

**Expected Results:**

- When sonic_installer installs the new firmware on the switch,  it creates a backup copy of existing configuration files on the switch intended to be migrated when it boots into new image on reboot
- ZTP JSON file is also backed up along with these files and migrated to new image.
- Switch boots into new image and restarts ZTP using the ZTP JSON file that has been migrated.
- It is expected that a valid /etc/sonic/config_db.json file is created prior to installing firmware image and this provides connectivity to external entities for provisioning to proceed

**Additional Tests:**

- When the newly installed image is booted, there is no */etc/sonic/config_db.json*.
  - ZTP creates a preset config and enables all in-band interfaces and performs DHCP discovery
  - After that ZTP proceeds to resume processing of the ZTP JSON file which has been migrated



### Test Case #26

**Objective:** Verify behavior of ZTP when */etc/sonic/config_db.json* file is not found during switch bootup

**Test Steps:**

- Initiate a ZTP session and let it complete
- Delete /etc/sonic/config_db.json file 
- Reboot the switch

**Expected Results:**

- ZTP does not start. It stays in completed state.

**Additional Tests:**

- Issue 'ztp run' command

  - A new ZTP session is started

    

### Test Case #27

**Objective:** Verify that ZTP service can be re-enabled and restarted using 'ztp enable' and 'ztp run' command

**Test Steps:**

- Follow test steps described in test case #19
- Issue 'ztp enable' command

**Expected Results:**

- ZTP is now re-enabled administratively but is not executed again.

**Additional Tests:**

- Issue 'ztp run' command 

  - All in-band interfaces are but in ztp preset config mode and  DHCP discovery is performed on all interfaces, a new ZTP JSON URL is obtained and ZTP is performed

    

### Test Case #28

**Objective:** Verify that all files downloaded and created by ztp service in */var/lib/ztp* directory cannot be read by regular users. Only root privileged users can read them.

**Test Steps:**

- Initiate a ZTP session and let it complete
- Login as user 'admin' and try to read files created in */var/lib/ztp* directory

**Expected Results:**

- Observe that all files created by ZTP service cannot be read

**Additional Tests:**

- Use sudo command to read the contents of /var/lib/ztp directory

  - User should be able to read the contents of the files created

    

### Test Case #29

**Objective:** Verify behavior of ZTP service when DHCP Options 225-minigraph_url, 226-acl_url and 67 - ZTP JSON file are all sent by the DHCP server

**Test Steps:**

- Configure DHCP server to send  DHCP Options 225-minigraph_url, 226-acl_url and 67 - ZTP JSON file URL options as part of IP address assignment
- Install a new SONiC image from ONIE prompt
- Boot into SONiC for the first time

**Expected Results:**

- ZTP service processes the values of minigraph_url and acl_url provided by DHCP server
- ZTP service provides these values as input to updategraph service and allows it to process them
- ZTP service then proceeds to process ZTP JSON file

**Additional Tests:**

- DHCP option 239 is also included in the provisioning data sent by DHCP server

  - DHCP option 239 is ignored as DHCP Option 67 takes priority over it
- graphservice configuration task is defined in ZTP JSON
  - ZTP service assigns the values provided by graphservice JSON data and allows updategraph service to process it

  - This is in addition to providing updategraph service the information learnt from DHCP Option 225, 226

    

### Test Case #30

**Objective:** Verify logging of ZTP service

**Test Steps:**

- Initiate a ZTP session and let it run to completion

**Expected Results:**

- Check file ''/var/log/ztp.log' and /var/log/syslog. Observe that all messages with INFO or higher severity are seen in the log files
- All output generated by configuration tasks and written to stdout is also sent to /var/log/syslog and /var/log/ztp.log

**Additional Tests:**

- Use various levels of severity to log-level-stdout field in /usr/lib/ztp/ztp_cfg.json file
  - Messages with severity level equal to or higher than set level show up in /var/log/syslog
- Use various levels of severity to log-level-file field in /usr/lib/ztp/ztp_cfg.json file
  - Messages with severity level equal to or higher than set level show up in /var/log/ztp.log
- Use different logging priority level values for log-level-stdout  and  log-level-file
  - Observe that log contents are different based on their set values
- User invalid logging level string
  - Observe that logging is performed assuming default level as INFO and ignoring the invalid value provided by user
- Remove "log-level-file" field from /usr/lib/ztp/ztp_cfg.json
  - Observe that no logs are generated to file ''/var/log/ztp.log'
- Remove "log-level-stdout" or "log-level-file" fields from /usr/lib/ztp/ztp_cfg.json
  - Observe that logging is performed assuming default level as INFO
- Issue 'systemctl status -l' command
  - Contents of output are same as the ZTP logs sent to syslog
- Create a configuration task which generates a huge volume of output continuously and does not exit for a very long time, may be days
  - Ensure that all the volumes of data is logged to /var/log/ztp.log and /var/log/syslog without any interruption to ztp process
  - Run these tests continuously and use logrotate to truncate the log files so that switch does not run out of disk space
