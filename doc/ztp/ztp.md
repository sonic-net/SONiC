# Zero Touch Provisioning (ZTP)

### Rev 0.1

## Table of Contents
- [1. Revision](#1-revision)
- [2. Requirements](#2-requirements)
- [3. Functional Description](#3-functional-description)
  - [3.1 ZTP JSON](#31-ztp-json)
  - [3.2 ZTP Plugins](#32-ztp-plugins)
  - [3.3 Dynamic Content](#33-dynamic-content)
  - [3.4 DHCP Options](#34-dhcp-options)
  - [3.5 ZTP Service](#35-ztp-service)
- [4. Chronology of Events](#4-chronology-of-events)
- [5. Security Considerations](#5-security-considerations)
- [6. Configuring ZTP](#6-configuring-ztp)
- [7. Code Structure](#7-code-structure)
- [8. Logging](#8-logging)
- [9. Debug](#9-debug)
- [10. Examples](#10-examples)
- [11. Future](#11-future)

## 1. Revision
| Rev | Date     |  Author       | Change Description                |
|:---:|:------------:|:------------------:|-----------------------------------|
| v0.1 |   03/06/2019   |   Rajendra Dendukuri   | Initial version                   |


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

## 3. Functional Description

Zero Touch Provisioning (ZTP) service can be used by users to configure a fleet of switches using common configuration templates. Switches booting from factory default state should be able to communicate with remote provisioning server and download  relevant configuration files and scripts to kickstart more complex configuration steps. ZTP service takes user input in JSON format.

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
  - DISABLED - ZTP service will not apply provided configuration in this section
  
  Default value assumed to be BOOT if the object is not present. ZTP service adds this object to the ZTP JSON file if not found.

- **ignore-result** :
  - false  - ZTP service marks status as FAILED if an error is encountered while processing this individual section
  - true   - ZTP service marks status as SUCCESS even if an error is encountered while processing this individual section

  Default value is assumed to be *false* if the object is not present.

- **timestamp** : Specifies the time and date when the *status* variable of a section is modified.

  ZTP service adds this object to the ZTP JSON file and it need not be added by user.

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

Both predefined and user-defined plugins are executed as a sub process by the ZTP service. The exit code of the executed plugin is used by ZTP service to determine next steps.

|Exit Code |  Description         | Action                                       |
|:-----------:|:-------------------|:-------------------------------------------------|
|   0      | SUCCESS     | Plugin completed intended operation successfully. *status* of the configuration section is set to value SUCCESS.  |
|   -1      | SUSPEND     | Plugin exited after partial execution. *status* of the configuration section continues to be IN-PROGRESS.  |
|   > 0      | FAILED     | An error was encountered while executing the plugin. *status* of the configuration section is set to value FAILED.  |

When using -1 SUSPEND exit code, the corresponding plugin should ensure that when ZTP service comes back to execute the plugin again, appropriate logic is implemented within the plugin to resume from where it had left earlier.

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

*plugin.url* takes precedence over *plugin.name* if both are defined.

#### configdb-json

The *configdb-json* plugin is used to download ConfigDB JSON file and apply the configuration.

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
      "url": {
        "source": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin"
      },
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
      "url": {
        "source": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin"
      },
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

Following is the  list of objects supported by the *snmp* plugin. Also provided is brief description of their usage, values that can be assigned and the default value assumed when the object is not used.

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
      "url": {
        "source": "http://192.168.1.1:8080/minigraph.xml"
      }
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
          "url": {
            "source": "http://192.168.1.1:8080/config_filename_eval.sh"
          }
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
| source.identifier  | Runtime generated string that can uniquely identify a switch  |hostname<br>hostname-fqdn<br>serial-number<br>product-name<br>[url](#url-object) |N/A|
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

The ZTP service is defined as a systemd service running on native SONiC O/S. It does not run inside a container. ZTP service starts after networking service has started. If ZTP is not enabled, the service exits and does not run again until next boot or if user intervenes.

When management interface obtains IP address via DHCP, URL pointing to ZTP JSON file is provided as value of DHCP option 67. When ZTP service starts, it first checks if there already exists a ZTP JSON file locally and if found loads it. If *ztp.status* field of local file is either SUCCESS, FAILED or DISABLED, ZTP service exits. If *ztp.status* field of local ZTP JSON file is  IN-PROGRESS, local file is used for further processing. If no local ZTP JSON file is found or if the *ztp.status* field of local ZTP JSON file is BOOT, ZTP service downloads the ZTP JSON file using the URL provided by DHCP Option 67 are starts processing it.

If user defines DHCP option 239, ZTP service downloads the provisioning script indicated in the URL and executes it. The exit code returned by the provisioning script is used to indicate whether ZTP has succeeded or failed. Exit code 0 indicates successful execution and any other value is treated as failure. ZTP service exits and does not run again unless user enables it again manually.

It is to be noted that DHCP option 67 takes precedence over DHCP option 239. 

ZTP service parses the ZTP JSON file and processes individual configuration sections in lexical order of their names. If *status* or *timestamp* fields are missing they are added to it. A local copy of ZTP JSON file is maintained as the file */var/lib/ztp/data/ztp.json*. Individual configuration sections are identified and split into individual files as */var/lib/ztp/data/sections/section-name*. The ztp.json file continues to hold all sections as defined by the user.

This ztp.json file is constantly updated with any changes made during the processing of loaded ZTP data. To begin with *ztp.status* is set to IN-PROGRESS and individual sections are processed in order of their names. The  *status* object of the configuration section being processed is set to 1 In-Progress and corresponding plugin is executed. 

Each section whose *status* value is BOOT or IN-PROGRESS  is processed in order. Corresponding plugin is called with */var/lib/ztp/data/sections/section-name* as argument to it. Exit code of plugin is used to determine the configuration sections *status* as explained in the [*Plugin Exit Code*](#322-plugin-exit-code) section of this document.

When all the sections have been processed, *ztp.status* field is updated taking into consideration the result of all individual sections. Sections with disabled *status* and *ignore-status: true* are not considered. *ztp.status* is marked as SUCCESS only if *status* field of all rest of the sections is SUCCESS. ZTP service exits and does not run again unless user enables it again.

If user does not provide both DHCP option 67 or DHCP option 239, ZTP service continues to run and wait for one of these values to be provided to it.

 ### 3.6 ZTP State Transition Diagram

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
   - If plugin exits with resume (-1) , the configuration section is marked IN-PROGRESS and executed again in next cycle.
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

Following are the supported ZTP configuration commands.

### ztp status

*ztp status* command displays current state of ZTP service and the date/time since it was in the current state. It also displays current status of each configuration section of user provided ZTP JSON and date/time it was last processed.

### ztp enable
*ztp enable* command is used to restart ZTP of SONiC switch and initiate intended configuration tasks. When ZTP feature is included as a build option, ZTP service is configured to be enabled by default. Also ZTP service is started if it is not already running. This command is useful to restart ZTP after it has failed or disabled by user.

### ztp disable
*ztp disable* command is used to stop ZTP service. If ZTP service is in progress, it is aborted and ZTP status is set to disable in ZTP JSON file.  SIGTERM is sent to ZTP service and its sub processes currently under execution. *systemd* defined default time of 90 seconds is provided for them to handle the SIGTERM and take appropriate action and gracefully exit. It is the responsibility of plugins to handle SIGTERM to perform any necessary cleanup or save actions. If the process is still running after 90s the process is killed.

ZTP service does not run if it is disabled even after reboot. User will have to use *ztp enable* for it to be operational again.

##  7. Code Structure

Code related to ZTP framework shall be included in azure/sonic-ztp github repository. The package will be named as sonic_ztp_*version*_all.deb.

More information will be added to this section after implementation of SONiC-ZTP is complete.

## 8. Logging
All output generated by ZTP service are logged to local syslog and stdout of the service. The *stdout* and *stderr* of executed plugins are are also redirected to syslog and stdout of ZTP service.

## 9. Debug
ZTP service can be started in optional debug mode providing more verbose information on steps being performed by the service.

## 10. Examples

### Example -1

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
        "url": {
          "source": "http://192.168.1.1:8080/broadcom-sonic-v1.0.bin"
        },
        "pre-check": {
          "url": {
            "source": "http://192.168.1.1:8080/firmware_check.sh"
          }
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
        "url": {
          "source": "http://192.168.1.1:8080/post_install.sh"
        },
        "reboot-on-success": true
      }
    },
    "04-connectivity-tests": {
      "plugin": {
        "url": {
          "source": "http://192.168.1.1:8080/ping_test.sh"
        }
      }
    }
  }
}```

## 11. Future

More predefined plugins can be added as deemed appropriate by wider audience.
