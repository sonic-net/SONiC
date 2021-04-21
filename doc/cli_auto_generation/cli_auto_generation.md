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
  * CONFIG DB tables with abbility to add/delete/update entries

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

For instanse let's take a fature called __FEATURE-A__, so a basic rules are: 

__1. For auto-generated CLI (sub-commands, arguments) will be used - hyphen separated style:__

###### config command
```
admin@sonic:~$ config feature-a sub-command-1 add <KEY>
```

__2. To provide not-positional arguments the next style MUST be used:__

###### config command
```
admin@sonic:~$ config feature-a sub-command-1 add <KEY> --mtu 4096 --ip-address 10.10.10.10
```

__3. The *show* command produce a named columns. Each column name is a uppercase of *leaf* name from YANG model:__

###### YANG model
```
//...
	list INTF_LIST {
		key "interface_name";

		leaf interface_name{
			type string;
		}

		leaf port {
			type uint16;
		}

		leaf mtu {
			type uint32;
		}
	}
//...
```
###### show command output
```
INTERFACE_NAME  PORT  MTU
--------------  ----  ---
Ethernet0       1     1024
Ethernet4       2     2048
```

__4. For every container, that goes after *top-level container*, (top-level container goes after *module*) will be generated dedicated sub-command for "show" and "config" command groups AND in case of *container* without *list*, for every *leaf* will be generated dedicated sub-command:__

###### YANG model
```yang
module sonic-feature-a {
	// ...
	container sonic-feature-a {
		// ...
		container FEATURE_A_TABLE {
			container container_1 {
				leaf mtu {
					type uint16;
				}
				leaf action {
					type string;
				}
			}
			container container_2 {
				leaf ip_address {
					type inet:ip-address;
				}
			}
		}
	}
}
```

###### config command
```
admin@sonic:~$ config feature-a-table container-1 mtu 35
admin@sonic:~$ config feature-a-table container-1 action trap

admin@sonic:~$ config feature-a-table container-2 ip-address 10.10.10.10
```

###### show command
```
admin@sonic:~$ show feature-a-table container-1

MTU  ACTION
---  ------
25   drop

=========================================

admin@sonic:~$ show feature-a-table container-2

IP_ADDRESS
----------
10.10.10.10
```

###### Config DB schema
```
{
	"FEATURE_A_TABLE": {
		"container_1": {
			"mtu": 35,
			"action": trap
		},
		"container_2": {
			"ip_address": "10.10.10.10"
		}
	}
}
```

__5. For every *list* element will be generated *add/del* commands. Also it is possible to generate *update* command, if the *list* NOT marked as *create-only*:__
###### YANG model
```yang
module sonic-feature-a {
	// ...
	container sonic-feature-a {
		// ...
		container FEATURE_A {
			list FEATURE_A_LIST {
				key "interface_name";
				leaf interface_name {
					type string;
				}
				leaf port {
					type uint16 {
						range 1..4094;
					}
				}
				leaf mtu {
					type uint16 {
						range 1..4094;
					}
				}
			}
		}
	}
}
```
###### config command
```
admin@sonic:~$ config feature-a add Ethernet0 --mtu 22 --port 33
admin@sonic:~$ config feature-a add Ethernet4 --mtu 4096 --port 16
admin@sonic:~$ config feature-a del Ethernet0
admin@sonic:~$ config feature-a update Ethernet0 --mtu 222 --port 32
```
###### show command
```
admin@sonic:~$ show feature-a

INTERFACE_NAME  PORT  MTU
--------------  ----  ---
Ethernet0       32    222
Ethetnet4       16    4096
```
###### Config DB schema
```json
{
	"FEATURE_A": {
		"Ethernet0": {
			"port": 32,
			"mtu": 222
		},
		"Ethernet4": {
			"port": 16,
			"mtu": 4096
		}
	}
}
```

__6. For every *leaf-list* element will be generated dedicated add/del commands, also the user can use comma-separed list when creating new list element to fill *leaf-list*. Also will be added dedicated command *clear* to delete all the elements from *leaf-list*:__
###### YANG model
```yang
module sonic-feature-a {
	// ...
	container sonic-feature-a {
		// ...
		container FEATURE_A {
			list FEATURE_A_LIST {
				key "interface_name";
				leaf interface_name {
					type string;
				}
				leaf-list dhcp_servers {
					type inet:ip-address;
				}
				leaf mtu {
					type uint16;
				}
			}
		}
	}
}
```
###### config command
```
admin@sonic:~$ config feature-a add Ethernet0 --dhcp-servers "192.168.0.20,10.10.10.10" --mtu 256
admin@sonic:~$ config feature-a dhcp-servers add Ethernet0 192.168.0.20
admin@sonic:~$ config feature-a dhcp-servers del Ethernet0 192.168.0.20
admin@sonic:~$ config feature-a dhcp-servers clear Ethernet0
```
###### show command
```
admin@sonic:~$ show feature-a

INTERFACE_NAME  DHCP_SERVERS  MTU
--------------  ------------  ---
Ethernet0       192.168.0.20  256
                10.10.10.10
```
###### Config DB schema
```
{
	"FEATURE_A": {
		"Ethernet0": {
			"dhcp_servers: [
				"192.168.0.20",
				"10.10.10.10"
			],
			"mtu": "256"
		}
	}
}
```

__7. In case if YANG model contains "grouping" syntax:__

###### YANG model
```yang
module sonic-feature-a {
	// ...
	container sonic-feature-a {
		// ...
		container FEATURE_A {
			list FEATURE_A_LIST {
				key "host_name";
				leaf host_name {
					type string;
				}
				grouping target {
					leaf address {
						type inet:ip-address;
					}
					leaf port {
						type inet:port-number;
					}
				}
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

__8. In case if YANG model contains "description", it will be used for CLI --help:__
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
  update  Update configuration.

===============================================================

admin@sonic:~$ config feature-a add --help
Usage: config feature-a add [OPTIONS] <key> 

   Add configuration

Options:
  --help     Show this message and exit.
  --adrress  IP address.
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

__2. In case if need to extend existing YANG model - [RFC7950 - augment](https://tools.ietf.org/html/rfc7950#section-4.2.8):__

Let's take as an example - *DHCP relay* feature. For now in SONiC *DHCP relay* feature is part of SONiC *VLAN* ([sonic-vlan.yang](https://github.com/vadymhlushko-mlnx/sonic-buildimage/blob/9580b0407f333fd9fcf32bedf47b741c797f4d86/src/sonic-yang-models/yang-models/sonic-vlan.yang#L145)), the user can configure *DHCP relay* feature by using the next CLI:

###### config command
```
admin@sonic:~$ config vlan dhcp_relay add [OPTIONS] <vid> <dhcp_relay_destination_ip>
```

In case if the *DHCP relay* will be application extension, we need a specific YANG models for it, then the auto-generated CLI will be created.

###### sonic-dhcp-relay.yang
``` yang
module sonic-dhcp-relay {
	// ...
	container sonic-dhcp-relay {
		// ...
		augment /vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:vlan_name {
			leaf-list dhcp-servers {
				type inet:ip-address;
			}
		}
	}
}
```
The *augment* statement means that *sonic-dhcp-relay.yang* will extend a current [sonic-vlan.yang](https://github.com/vadymhlushko-mlnx/sonic-buildimage/blob/9580b0407f333fd9fcf32bedf47b741c797f4d86/src/sonic-yang-models/yang-models/sonic-vlan.yang#L145).

So, the main questions are:
- how does it affect existing *config* CLI for *DHCP relay*?
- how does it affect existing *show* CLI for *DHCP relay*?

## Development plan

#### Phase 1 requirements
* Should support:
  * CONFIG DB tables with abbility to add/delete/update entries

#### Phase 2 requirements
* Should support:
  * All SONiC DB tables with abbility to add/delete/update entries
  * Auto-generation of *sonic-clear* CLI