# SONiC CLI Auto-generation tool

## Table of Content 

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Feature overview](#feature-overview)
- [Motivation](#motivation)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-level design](#high-level-design)
- [Configuration and management](#configuration-and-management)
- [SAI API](#sai-api)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions Limitations](#restrictions-limitations)
- [Testing Requirements Design](#testing-requirements-design)
- [Open questions](#open-questions)
- [Development plan](#development-plan)

### Revision

|  Rev  |  Date   |      Author      | Change Description |
| :---: | :-----: | :--------------: | ------------------ |
|  1.0  | 04/2021 | Vadym Hlushko    | Phase 1 Design     |

### Scope  

This document describes the high-level design details of SONiC CLI Auto-generation tool for SONiC Application extensions infrastructure.

### Definitions/Abbreviations 

| Abbreviation | Definition                            |
|--------------|---------------------------------------|
| SONiC        | Software for Open Networking in Cloud |
| SAE          | SONiC Application Extension           |
| DB           | Database                              |
| API          | Application Programming Interface     |
| SAI          | Switch Abstraction Interface          |
| YANG         | Yet Another Next Generation           |
| CLI          | Command-line interface                |
| NOS          | Network operating system              |

## Overview 

### Feature overview

The SONiC CLI Auto-generation - is a utility for generating the command-line interface for third-party features, called application extensions, that provide their functionality as separate docker containers. The YANG model will be used to describe the CONFIG DB schema and CLI will be generated according to CONFIG DB schema. YANG model passed as an input parameter for the SONiC Auto-generation utility. The CLI should be a part of SONiC utilities and support - show, config operations.

### Motivation

To make SONiC NOS more flexible for developers [SONiC Application Extension infrastructure](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md) was introduced. 

If someone wants to extend the SONiC NOS functionality - the SAE infrastructure should be used. Some of third-party feature that will be integrated into the SONiC - may require the command line interface. To avoid spending time on the investigation of how to add a new CLI to [sonic-utilities](https://github.com/Azure/sonic-utilities/tree/master) - the CLI Auto-generation utility was introduced. The command line interface that would be generated will be intuitive for people familiar with the SONiC NOS and CONFIG DB.

## Requirements

### Functional requirenments
* Should support:
  * CONFIG DB tables with ability to add/delete/update entries

## Architecture design

A current SONiC NOS architecture does not require changes, because the SONiC CLI Auto-generation feature comes as a component for the SONiC Application extension infrastructure. So, only the [sonic-package-manager](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#cli-enhancements) utility require changes.

## High-level design

### Basic concept

There are three main entities:

*YANG model* - YANG model file which contain description of CONFIG DB schema. Should be writen strictly according to [SONiC Yang Model Guidelines](https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md) 

*SONiC CLI Auto-generation tool* - a unitility that read the YANG model and produce the Auto-generated CLI plugin.

*Auto-generated CLI plugin* - python script, that will be used as a plugin for existing CLI, will be placed in the specific location (described later) and provide user with a CLI for a new feature.

###### Figure 1: Basic Concepts
<p align=center>
<img src="images/auto_generation_flow.svg" alt="Figure 2.1 CLI Auto-generation flow">
</p>

A current SONiC utilities support *show*, *config*, *sonic-clear* operations. A plugin approach is taken when extending those utilities. A common way to introduce a plugin support for a python application is to structure a plugin as a python module that can be discovered by the application in a well known location in the system.

An Auto-generated CLI plugins will be placed to a package directory named *auto-gen-plugins* under each *show*, *config* python package, so that by iterating modules inside those packages utilities can load them. This is implemented in a way defined in [Python Packaging Guide. Creating and discovering plugins.](https://packaging.python.org/guides/creating-and-discovering-plugins/#using-namespace-packages)

A code snipped describing the approach is given:

```python
import show.plugins

def iter_plugins_namespace(ns_pkg):
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")

discovered_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in iter_namespace(show.plugins)
}
```

### Modules/sub-modules changes

The SONiC CLI Auto-generation tool is a part of [sonic-package-manager](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#cli-enhancements) utility. A package [installation](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#package-installation) and [upgrade flow](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#package-upgrade) can trigger CLI auto-generation script, if the YANG model was provided.

The YANG models should be a part of the Appication extension Docker image and placed alongside with [manifest.json](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#manifest) file. The user should be able to access the YANG model by using the docker labels.

```
com.azure.sonic.yang_model
```

###### Figure 2: YANG model location
<p align=center>
<img src="images/yang_model_location.svg" alt="Figure 2.1 Yang model location">
</p>

Also the SONiC CLI Auto-generation tool will be accessible from the switch CLI as independed CLI utility called - __sonic-cli-gen__. A user can provide a YANG model to this script get auto-generated CLI.

The [manifest.json](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#manifest) file should have a specific ON/OFF trigers for CLI auto-generation:

| Path                                 | Type   | Mandatory | Description                                                               |
| ---------------------------------    | ------ | --------- | ------------------------------------------------------------------------- |
| /cli/click-cli-auto-generate-config  | boolean| yes       | ON/OFF triger for auto-generation of CLI command *config*. Default: false | 
| /cli/click-cli-auto-generate-show    | boolean| yes       | ON/OFF triger for auto-generation of CLI command *show*. Default: false   |

Inside the manifest.json there are [others keys](https://github.com/stepanblyschak/SONiC/blob/sonic-app-ext-3/doc/sonic-application-extention/sonic-application-extention-hld.md#manifest-path-7), that describing a path to a *NOT auto-generated CLI plugins*. For example there are:

| Path                   | Type   | Mandatory | Description                                                     |
| ---------------------- | ------ | --------- | --------------------------------------------------------------- |
| /cli/show-cli-plugin   | string | no        | A path to a plugin for sonic-utilities show CLI command.        |
| /cli/config-cli-plugin | string | no        | A path to a plugin for sonic-utilities config CLI command.      |
| /cli/clear-cli-plugin  | string | no        | A path to a plugin for sonic-utilities sonic-clear CLI command. |

For example the user can have part of the *config* CLI auto-generated and the other part NOT auto-generated.

If the Application Extension will be installed and the CLI will be generated - the YANG model for current Application Extension will be placed in a well-known system location on the switch alongside with existing YANG models. This step is done in order to provide data validation - when the user executing generated CLI.
```
/usr/local/yang-models
```

## Configuration and management

### Auto-generation rules

```diff
- Please make sure that you read all of the rules.
- Because you will often have a question that is covered in the next rule.
```

__1. For auto-generated CLI (sub-commands, arguments) will be used - hyphen separated style:__

For instanse let's take a feature called __FEATURE-A__: 

###### config command
```
admin@sonic:~$ config feature-a sub-command-1 add <KEY> ...
```

__2. For every *container*, that goes after *top-level container*, (top-level container goes after *module*) will be generated dedicated sub-command for "show" and "config" command groups AND in case if *container* is without *list*, for every *leaf* will be generated dedicated sub-command:__

For instanse let's take a PART of existing [sonic-device_metadata.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-device_metadata.yang)

###### sonic-device_metadata YANG model
```yang
module sonic-device_metadata {
		//..
    container sonic-device_metadata {
        container DEVICE_METADATA {
            container localhost{
                leaf hwsku {
                    type stypes:hwsku;
                }
                leaf default_bgp_status {
                    type enumeration {
                        enum up;
                        enum down;
                    }
                    default up;
                }
                leaf hostname {
                    type string {
                        length 1..255;
                    }
                }
                leaf platform {
                    type string {
                        length 1..255;
                    }
                }
            }
        }
    }
}
```

###### config command
```
admin@sonic:~$ config device-metadata localhost hwsku "ACS-MSN2100"
admin@sonic:~$ config device-metadata localhost default-bgp-status up
admin@sonic:~$ config device-metadata localhost hostname "r-sonic-switch"
admin@sonic:~$ config device-metadata localhost platform "x86_64-mlnx_msn2100-r0"
```

The *show* command produces named columns. Each column name is an uppercase of *leaf* name from the YANG model:

###### show command
```
admin@sonic:~$ show device-metadata localhost

HWSKU        DEFAULT-BGP-STATUS  HOSTNAME        PLATFORM
-----        ------------------  --------        --------
ACS-MSN2100  UP                  r-sonic-switch  x86_64-mlnx_msn2100-r0
```

###### Config DB schema
```
{
	"DEVICE_METADATA": {
		"locahost": {
			"hwsku": "ACS-MSN2100",
			"default_bgp_status": "up",
			"hostname": "r-sonic-switch",
			"platform": "x86_64-mlnx_msn2100-r0"
		}
	}
}
```
__3. For every *list* element will be generated *add/del* commands:__

For instanse let's take a PART of existing [sonic-vlan.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang)

###### sonic-vlan YANG model
```yang
module sonic-vlan {
	// ...
	container sonic-vlan {
		// ...
		container VLAN {
			list VLAN_LIST {
				key "name";
				leaf name {
					type string {
						pattern 'Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])';
					}
				}
				leaf vlanid {
					type uint16 {
						range 1..4094;
					}
				}
				leaf mtu {
					type uint16 {
						range 1..9216;
					}
				}
				leaf admin_status {
					type stypes:admin_status;
				}
			}
		}
	}
}
```

In the case of bellow, "Vlan11" - is a positional argument and *key* for the *list*.
"vlanid", "mtu", "admin-status" - are not-positional arguments, and to provide them the next style MUST be used(check *config command*)
__This style "--arg" is NOT RELATED to the Linux CLI optional parameter style__

###### config command
```
admin@sonic:~$ config vlan add Vlan11 --vlanid 11 --mtu 128 --admin-status up
admin@sonic:~$ config vlan del Vlan11
```

YANG models support [The leaf's "mandatory" Statement](https://tools.ietf.org/html/rfc7950#section-7.6.5).
If the user wants to distinguish whether a CLI argument is mandatory or not, he can use the --help command (covered in the next rules)

If the user wants to add to the list a new element with KEY that already existed in the list, he will get a warning message

###### config command
```
admin@sonic:~$ config vlan add Vlan11 --vlanid 11 --mtu 128 --admin-status up
Vlan11 already exist! Do you want to replace it? yes/no
```

###### show command
```
admin@sonic:~$ show vlan

NAME    VLANID  MTU  ADMIN-STATUS
----    ------  ---  ------------
Vlan11  11      128  up
```
###### Config DB schema
```
{
	"VLAN": {
		"Vlan11": {
			"vlanid": 11,
			"mtu": 128,
			"admin_status": up
	  }
	}
}
```
__4. For every *leaf-list* element will be generated dedicated *add/del/clear* commands, also the user can use a comma-separated list when creating a new list element to fill *leaf-list*. Also will be added dedicated command *clear* to delete all the elements from *leaf-list*:__

For instanse let's take a PART of existing [sonic-vlan.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang)

###### sonic-vlan YANG model
```yang
module sonic-vlan {
	// ...
	container sonic-vlan {
		// ...
		container VLAN {
			list VLAN_LIST {
				key "name";
				leaf name {
					type string {
						pattern 'Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])';
					}
				}
				leaf vlanid {
					type uint16 {
						range 1..4094;
					}
				}
				leaf mtu {
					type uint16 {
						range 1..9216;
					}
				}
				leaf admin_status {
					type stypes:admin_status;
				}
			  leaf-list dhcp_servers {
					type inet:ip-address;
				}
			}
		}
	}
}
```

The user can create new list object, and provide values to *leaf-list* *dhcp_servers* by using a comma-separated list (example bellow)

###### config command
```
admin@sonic:~$ config vlan add Vlan11 --vlanid 11 --mtu 128 --admin-status up --dhcp-servers "192.168.0.10,11.12.13.14"
```

The user can use dedicated sub-commands *add/del*, a *clear* sub-command will delete all the elements from *leaf-list*.
The *add* subcommand will append new element to the end of the list.

###### config command
```
admin@sonic:~$ config vlan dhcp-servers add Vlan11 10.10.10.10
admin@sonic:~$ config vlan dhcp-servers del Vlan11 10.10.10.10
admin@sonic:~$ config vlan dhcp-servers clear Vlan11
```

###### show command
```
admin@sonic:~$ show vlan

NAME    VLANID  MTU  ADMIN-STATUS  DHCP-SERVERS
----    ------  ---  ------------  ------------
Vlan11  11      128  up            192.168.0.10
                                   11.12.13.14
```
###### Config DB schema
```
{
	"VLAN": {
		"Vlan11": {
			"vlanid": 11,
			"mtu": 128,
			"admin_status": up,
			"dhcp_servers": [
				"192.168.0.10",
				"11.12.13.14"
			]
	  }
	}
}
```

__5. In case if YANG model contains "grouping" syntax:__

###### YANG model
```yang
module sonic-feature-a {
	// ...
				grouping target {
					leaf address {
						type inet:ip-address;
					}
					leaf port {
						type inet:port-number;
					}
				}
	container sonic-feature-a {
		// ...
		container FEATURE_A {
			list FEATURE_A_LIST {
				key "host_name";
				leaf host_name {
					type string;
				}
				uses target;
			}
		}
	}
}
```

###### config command
```
admin@sonic:~$ config feature-a add Linux --address "10.10.10.10" --port 1024
```

###### show command
```
admin@sonic:~$ show feature-a

HOST_NAME  TARGET
---------  ------
Linux      address: "192.168.0.20"
           port:    "1024"
```

###### Config DB schema
```
{
	"FEATURE_A": {
		"Linux": {
			"address: "192.168.0.20",
			"port": 1024
		}
	}
}
```

__6. In case if YANG model contains "description", it will be used for CLI --help:__
###### YANG model
```yang
module sonic-feature-a {
	// ...
	container sonic-feature-a {
		// ...
		container FEATURE_A {
			description "FEATURE_A overview";
			list FEATURE_A_LIST {
				key "host_name";
				leaf host_name {
					type string;
				}
				grouping target {
					leaf address {
						mandatory true;
						type inet:ip-address;
						description "IP address";
					}
					leaf port {
						type inet:port-number;
						description "Port number";
					}
				}
			}
		}
	}
}
```

###### config command
```
admin@sonic:~$ config feature-a --help
Usage: config feature-a [OPTIONS] COMMAND [ARGS]...

  FEATURE_A overview

Options:
  --help  Show this message and exit.

Commands:
  add     Add configuration.
  del     Del configuration.
```

In case if *leaf* contain ["mandatory" statement](https://tools.ietf.org/html/rfc7950#section-7.6.5)

###### config command
```
admin@sonic:~$ config feature-a add --help
Usage: config feature-a add [OPTIONS] <key> 

   Add configuration

Options:
  --help     Show this message and exit.
  --adrress  [mandatory] IP address.
  --port     Port number. 
```

### Generated CLI workflow

###### Figure 3. Config command flow
<p align=center>
<img src="images/config_cmd_flow.svg" alt="Figure 2.1 Yang model location">
</p>

The auto-generated CLI will use the next scenarion:

1. The user execute an auto-generated CLI command.
2. The auto-generated command produce a .json file, which describe configuration to apply.
3. The YANG library validate data provided by user in 1 step, according to the YANG model.
4. After successful validation it write data to Config DB.

## SAI API

No SAI API changes required for this feature.

## Warmboot and Fastboot Design Impact

No impact for warmboot/fastboot flows.

## Restrictions Limitations 

1. The YANG models for Application extension MUST have unique names for constructs - __module__, __container__, that are located on the same nested level in comparison to [existing YANG models](https://github.com/Azure/sonic-buildimage/tree/master/src/sonic-yang-models/yang-models). This needed to avoid an intersection with the existing CLI on the switch. The below [sonic-vlan.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan.yang) has a __module__ name - "sonic-vlan", so the developer can NOT use this "sonic-vlan" name for another module in another YANG mode.

```yang
module sonic-vlan {
	// ...
	container sonic-vlan {

		container VLAN_INTERFACE {
		}
	}
}
```
If there will be some conflicts, CLI auto-generation process will fail with error message.

## Testing Requirements Design  

### Unit Test cases 

The unit tests will be provided during implementation.

## Open questions

__1. In case if the YANG models for Application extension have more than 1 __list__ construct inside __container__:__

```yang
module sonic-vlan {
	// ...
	container sonic-vlan {

		container VLAN_INTERFACE {
			// ...

			list VLAN_INTERFACE_LIST {

			}

			// NOT SUPPORTED
			list VLAN_INTERFACE_IPPREFIX_LIST {
			}
		}
	}
}
```

__PROPOSAL__ - if there is more than 1 __list__ construct inside __container__ then generate dedicated sub-command for every list:

###### config command
```
admin@sonic:~$ config vlan-interface vlan-interface-list add <KEY> ...
admin@sonic:~$ config vlan-interface vlan-interface-ipprefix-list add <KEY> ...
```
If there is only 1 __list__ construct inside __container__ then NOT generate dedicated sub-command.

Is it a general SONiC rule that the table can have different keys inside?

__2.For the YANG model *list* in addition to *add/del* commands, it is possible to generate *update* command:__

In case if YANG model contains a *list* element, besides *add/del* commands it is possible to generate the *update* command, but in the YANG model there is no ability to mark some *list* with the *create only* marker, it means that user can NOT modify the list, he only can 'add' or 'delete' list elements.

## Development plan

#### Phase 1 requirements
* Should support:
  * CONFIG DB tables with abbility to add/delete/update entries

#### Phase 2 requirements
* Should support:
  * All SONiC DB tables with abbility to add/delete/update entries
  * Auto-generation of *sonic-clear* CLI
