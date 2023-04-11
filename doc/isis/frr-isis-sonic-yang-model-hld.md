# ISIS Yang Model for SONiC High Level Design Document #

## Table of Contents
- [ISIS Yang Model for SONiC High Level Design Document](#isis-yang-model-for-sonic-high-level-design-document)
  - [Table of Content](#table-of-content)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
    - [High-Level Design](#high-level-design)
      - [CONFIG DB](#config-db)
        - [Global Config](#global-config)
        - [Level Config](#level-config)
        - [Interface Config](#interface-config)
      - [YANG Model Enhancements](#yang-model-enhancements)
        - [SONiC ISIS Global](#sonic-isis-global)
        - [SONiC ISIS Level](#sonic-isis-level)
        - [SONiC ISIS Interface](#sonic-isis-interface)
        - [SONiC ISIS Authentication Groupings](#sonic-isis-authentication-groupings)
        - [SONiC ISIS Defined Types](#sonic-isis-defined-types)
    - [Testing Requirements/Design](#testing-requirementsdesign)
    - [Open/Action items - if any](#openaction-items---if-any)

### Revision
|  Rev  |  Date        |  Author  | Change Description |
| :---  | :---------   | :------  | :----------------  |
|  0.1  | April-11-2023  | C Choate | Initial version    |

### Scope

This document provides general information about the initial design for the ISIS YANG model in the SONiC infrastructure.  The focus of this initial support is to expand existing SONiC infrastructure for IPv4/IPv6 routing to include equivalent FRR-ISIS functionality.

### Definitions/Abbreviations
| Abbreviation | Description                                |
| :----------  | :-----------------------------------       |
| BFD          | Bidirectional Forwarding Detection         |
| CSNP         | Complete Sequence Number PDU               |
| ISIS         | Intermediate System to Intermediate System |
| LSP          | Label-Switched Path                        |
| MPLS         | Multiprotocol Label Switching              |
| MTU          | Maximum Transmission Unit                  |
| PSNP         | Partial Sequence Number PDU                |
| SPF          | Sender Policy Framework                    |
| SR           | Segment Routing                            |

### Overview
This document provides general information about the initial design for the ISIS YANG model in the SONiC infrastructure.

### High-Level Design

#### CONFIG DB

##### Global Config
Global ISIS config options.

```
"ISIS_GLOBAL"
  "instance"                    :{{string}} 
  "net"                         :{{stypes:net-address}} (OPTIONAL)
  "level_capability"            :{{"level-1"/"level-2"/"level-1-2"}} (OPTIONAL)
  "dynamic_hostname"            :{{boolean}} (OPTIONAL)
  "attach_send"                 :{{boolean}} (OPTIONAL)
  "attach_receive_ignore"       :{{boolean}} (OPTIONAL)
  "set_overload_bit"            :{{boolean}} (OPTIONAL)             
  "lsp_mtu_size"                :{{UINT16}}  (OPTIONAL)
  "spf_init_delay"              :{{UINT16}}  (OPTIONAL*)
  "spf_short_delay"             :{{UINT16}}  (OPTIONAL*)
  "spf_long_delay"              :{{UINT16}}  (OPTIONAL*)
  "spf_hold_delay"              :{{UINT16}}  (OPTIONAL*)
  "spf_time_to_learn"           :{{UINT16}}  (OPTIONAL*)
  "log_adjacency_changes"       :{{boolean}} (OPTIONAL)

* If an SPF value is specified, all other global SPF values must also be specified

ISIS_GLOBAL|{{instance}}
; Defines schema for global ISIS configuration attributes
key                         = ISIS_GLOBAL:instance ; Instance name/area tag
; field                     = value
net                         = stypes:net-address   ; OSI NET address. Format: xx.xxxx.xxxx.xxxx.xx
level_capability            = "level-1"/"level-2"/"level-1-2" ; ISIS level capability
dynamic_hostname            = boolean              ; Dynamic-hostname support. Default "true"
attach_send                 = boolean              ; Send attached bits in LSP for inter-area traffic. Default "true"
attach_receive_ignore       = boolean              ; Attached bits recieved in LSP cause default route add. Default "false"
set_overload_bit            = boolean              ; Administratively enable the overload bit
lsp_mtu_size                = UINT16               ; MTU of an LSP. Range 128..4352. Default 1487
spf_init_delay              = UINT16               ; Delay used while in QUIET state. Range 0..60000 in msec.
spf_short_delay             = UINT16               ; Delay used while in SHORT_WAIT state. Range 0..60000 in msec.
spf_long_delay              = UINT16               ; Delay used while in LONG_WAIT state. Range 0..60000 in msec.
spf_hold_delay              = UINT16               ; Time with no received IGP events before considering IGP stable. Range 0..60000 in msec.
spf_time_to_learn           = UINT16               ; Maximum time needed to learn all of the events related to a failure. Range 0..60000 in msec.
log_adjacency_changes       = boolean              ; Log changes to this instance's IS-IS adjacencies. Default "false"

Tree view
     +--rw ISIS_GLOBAL
     |  +--rw ISIS_GLOBAL_LIST* [instance]
     |     +--rw instance                       string
     |     +--rw net?                           stypes:net-address
     |     +--rw level_capability?              stypes:level-capability
     |     +--rw dynamic_hostname?              boolean
     |     +--rw attach_send?                   boolean
     |     +--rw attach_receive_ignore?         boolean
     |     +--rw set_overload_bit?              boolean
     |     +--rw lsp_mtu_size?                  UINT16
     |     +--rw spf_init_delay                 uint16
     |     +--rw spf_short_delay                uint16
     |     +--rw spf_long_delay                 uint16
     |     +--rw spf_hold_down                  uint16
     |     +--rw spf_time_to_learn              uint16
     |     +--rw log_adjacency_changes?         boolean
```

##### Level Config
Level specific ISIS config options.

```
"ISIS_LEVEL"
  "instance"                         :{{string}} 
  "level_number"                     :{{"level-1"/"level-2"}} 
  "lsp_refresh_interval"             :{{UINT16}} (OPTIONAL)
  "lsp_maximum_lifetime"             :{{UINT16}} (OPTIONAL)
  "lsp_generation_interval"          :{{UINT16}} (OPTIONAL)
  "spf_minimum_interval"             :{{UINT16}} (OPTIONAL)

ISIS_LEVEL|{{instance|level_number}}
; Defines schema for ISIS level configuration attributes
key                                = ISIS_LEVEL:instance ; Instance name/area tag
key                                = ISIS_LEVEL:level_number     ; Level number. ("level-1"/"level-2")
; field                            = value
lsp_refresh_interval               = UINT16               ; LSP refresh interval. Default 900 in seconds
lsp_maximum_lifetime               = UINT16               ; Maximum LSP lifetime. Range 350..65535. Default 1200 in seconds. Must be at least 300 seconds more than lsp_refresh_interval 
lsp_generation_interval            = UINT16               ; Minimum time allowed before LSP retransmissions. Range 1..120. Default 30 in seconds. Must be lower than lsp_refresh_interval
spf_minimum_interval               = UINT16               ; Minimum time between consecutive SPFs. Range 1..120. Default 1 in seconds

Tree view
     +--rw ISIS_LEVEL
     |  +--rw ISIS_LEVEL_LIST* [instance level_number]
     |     +--rw instance                         string
     |     +--rw level_number                     stypes:level-number
     |     +--rw lsp_refresh_interval?            uint16
     |     +--rw lsp_maximum_lifetime?            uint16
     |     +--rw lsp_generation_interval?         uint16
     |     +--rw spf_minimum_interval?            uint16
```

##### Interface Config
Interface specific ISIS config options.

```
"ISIS_INTERFACE"
  "instance"                         :{{string}} 
  "ifname"                           :{{string}} 
  "ipv4_routing_instance"            :{{{string}}} (OPTIONAL)
  "ipv6_routing_instance"            :{{{string}}} (OPTIONAL)
  "passive"                          :{{boolean}} (OPTIONAL)
  "hello_padding"                    :{{{boolean}}} (OPTIONAL)
  "network_type"                     :{{"point-to-point"}} (OPTIONAL)
  "enable_bfd"                       :{{{boolean}}} (OPTIONAL)
  "bfd_profile"                      :{{string}} (OPTIONAL)    
  "metric"                           :{{UINT32}} (OPTIONAL)
  "csnp_interval"                    :{{{UINT16}}} (OPTIONAL)
  "psnp_interval"                    :{{{UINT16}}} (OPTIONAL)
  "hello_interval"                   :{{{UINT32}}} (OPTIONAL)
  "hello_multiplier"                 :{{UINT16}} (OPTIONAL)
  "authentication_key"               :{{string}}
  "authentication_type"              :{{"clear"/"md5"}} (OPTIONAL)

ISIS_INTERFACE|{{instance|ifname}}
; Defines schema for ISIS interface configuration attributes
key                                = ISIS_INTERFACE:instance ; Instance name/area tag
key                                = ISIS_INTERFACE:ifname ; Interface name
; field                            = value
ipv4_routing                       = string                ; Enable routing IPv4 traffic over this interface for the given instance
ipv6_routing                       = string                ; Enable routing IPv6 traffic over this interface for the given instance
passive                            = bolean                ; Advertise the interface in the ISIS topology, but don't allow it to form adjacencies. Default "false"
hello_padding                      = boolean               ; Add padding to ISIS hello PDUs
network_type                       = "point-to-point"      ; ISIS interface type
enable_bfd                         = boolean               ; Monitor ISIS peers on this interface
bfd_profile                        = string                ; Let BFD use a pre-configured profile
metric                             = UINT32                ; Metric value. Range 0..16777215. Default 0
csnp_interval                      = boolean               ; Complete Sequence Number PDU (CSNP) generation interval. Range 1..600. Default 10 in seconds
psnp_interval                      = boolean               ; Partial Sequence Number PDU (PSNP) generation interval. Range 1..120. Default 2 in seconds
hello_interval                     = UINT32                ; Hello interval between consecutive hello messages. Range 1..600. Default 3 in seconds
hello_multiplier                   = UINT16                ; Multiplier for the hello holding time. Range 2..100. Default 10
authentication_key                 = string                ; Authentication password
authentication_type                = "clear"/"md5"         ; Authentication keychain type


Tree view
     +--rw ISIS_INTERFACE
     |  +--rw ISIS_INTERFACE_LIST* [instance ifname]
     |     +--rw instance                         string
     |     +--rw ifname                           string
     |     +--rw ipv4_routing_instance?           string
     |     +--rw ipv6_routing_instance?           string
     |     +--rw passive?                         boolean
     |     +--rw hello_padding?                   boolean
     |     +--rw network_type?                    stypes:network-type
     |     +--rw enable_bfd?                      boolean
     |     +--rw bfd_profile?                     string
     |     +--rw metric?                          uint32
     |     +--rw csnp_interval?                   uint16
     |     +--rw psnp_interval?                   uint16
     |     +--rw hello_interval?                  uint32
     |     +--rw hello_multiplier?                uint16
     |     +--rw authentication_key?              string
     |     +--rw authentication_type?             stypes:authentication-type
```

#### YANG Model Enhancements

##### SONiC ISIS Global
Global ISIS Yang container is sonic-isis.yang.

```
        container ISIS_GLOBAL {

            list ISIS_GLOBAL_LIST {

                max-elements "1";

                key "instance";

                leaf instance {
                    type string;
                    description
                        "The identifier for this instance of IS-IS. Area-tag";
                }

                leaf net { 
                    type stypes:net-address; 
                    description
                        "IS-IS OSI network entity title (NET) address.";
                }

                leaf level_capability {
                    type stypes:level-capability;
                    default "level-1-2";
                    description
                        "IS-IS level capability (level-1, level-2, level-1-2).";
                  }

                leaf dynamic_hostname {
                    type boolean;
                    default "true";
                    description
                        "Dynamic hostname support for IS-IS.";
                }

                leaf attach_send {
                    type boolean;
                    default "true";
                    description
                        "For an L1 or L2 router, attached bits are sent in an LSP when set to true.";
                }

                leaf attach_receive_ignore {
                    type boolean;
                    default "false";
                    description
                        "For an L1 router, attached bits received in an LSP create a default route when set to false";
                }

                leaf set_overload_bit {
                    type boolean;
                    default "false";
                    description
                        "Administratively enable the overload bit.";
                }

                leaf lsp_mtu_size {
                    type uint16 {
                        range "128..4352";
                    }
                    default "1497";
                    description
                        "LSP MTU.";
                }

                leaf spf_init_delay {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "../spf_short_delay and ../spf_long_delay and ../spf_hold_down and ../spf_time_to_learn or not(../spf_init_delay)" {
                        error-message
                            "SPF init delay must only be specified if all other SPF parameters are specified";
                    }
                    description
                        "Delay used during QUIET state";
                }

                leaf spf_short_delay {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "../spf_init_delay and ../spf_long_delay and ../spf_hold_down and ../spf_time_to_learn or not(../spf_short_delay)" {
                        error-message
                            "SPF short delay must only be specified if all other SPF parameters are specified";
                    }
                    description
                        "Delay used during SHORT_WAIT state";
                }

                leaf spf_long_delay {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "../spf_init_delay and ../spf_short_delay and ../spf_hold_down and ../spf_time_to_learn or not(../spf_long_delay)" {
                        error-message
                            "SPF long delay must only be specified if all other SPF parameters are specified";
                    }
                    description
                        "Delay used during LONG_WAIT state";
                }

                leaf spf_hold_down {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "../spf_init_delay and ../spf_short_delay and ../spf_long_delay and ../spf_time_to_learn or not(../spf_hold_down)" {
                        error-message
                            "SPF hold down must only be specified if all other SPF parameters are specified";
                    }
                    description
                        "Period of time without IGP events before considering IGP stable";
                }

                leaf spf_time_to_learn {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "../spf_init_delay and ../spf_short_delay and ../spf_long_delay and ../spf_hold_down or not(../spf_time_to_learn)" {
                        error-message
                            "SPF time_to_learn must only be specified if all other SPF parameters are specified";
                    }
                    description
                        "Maximum time needed to learn all of the events related to a failure";
                }

                leaf log_adjacency_changes {
                    type boolean;
                    default "false";
                    description
                        "Log changes to this instance's IS-IS adjacencies.";
                }

            } // list ISIS_GLOBAL_LIST

        } // container ISIS_GLOBAL
```

##### SONiC ISIS Level
ISIS Level Yang container is sonic-isis.yang.

```
        container ISIS_LEVEL {

            list ISIS_LEVEL_LIST {

                description
                    "Configuration parameters related to a particular level within the
                    IS-IS protocol instance";

                key "instance level_number";

                leaf instance {
                    type string;
                    description
                        "The identifier for this instance of IS-IS. Area-tag";
                }

                leaf level_number {
                    type stypes:level-number;
                    description
                        "IS-IS level number.";
                }

                leaf lsp_refresh_interval {
                    type uint16;
                    units "seconds";
                    default "900";
                    description
                        "LSP refresh interval.";
                }

                leaf lsp_maximum_lifetime {
                    type uint16 {
                        range "350..65535";
                    }
                    units "seconds";
                    must "(. >= ../lsp_refresh_interval + 300)" {
                        error-message
                            "lsp_maximum_lifetime must be at least 300 seconds greater than lsp_refresh_interval";
                    }
                    default "1200";
                    description
                        "Maximum LSP lifetime.";
                }

                leaf lsp_generation_interval {
                    type uint16 {
                        range "1..120";
                    }
                    units "seconds";
                    must "(. < ../lsp_refresh_interval)" {
                        error-message
                            "lsp_generation_interval must be greater than lsp_refresh_interval";
                    }
                    default "30";
                    description
                        "Minimum time before an LSP retransmissions.";
                }

                leaf spf_minimum_interval {
                    type uint16 {
                        range "1..120";
                    }
                    units "seconds";
                    default "1";
                    description
                        "Minimum time between consecutive SPFs.";
                }

            } // list ISIS_LEVEL_LIST

        } // container ISIS_LEVEL
```

##### SONiC ISIS Interface
ISIS Interface Yang container is sonic-isis.yang.

```
        container ISIS_INTERFACE {

            list ISIS_INTERFACE_LIST {

                description
                    "Configuration parameters related to a particular interface within the
                    IS-IS protocol instance";

                key "instance ifname";

                leaf instance {
                    type string;
                    description
                        "The identifier for this instance of IS-IS. Area-tag";
                }

                leaf ifname {
                    type string;
                    description
                        "Interface for which IS-IS configuration is to be applied.";
                }

                leaf ipv4_routing_instance {
                    type string;
                    description
                        "Routing IS-IS IPv4 traffic over this interface for the given instance.";
                }
                leaf ipv6_routing_instance {
                    type string;
                    description
                        "Routing IS-IS IPv6 traffic over this interface for the given instance.";
                }

                leaf passive {
                    type boolean;
                    default "false";
                    description
                        "When set to true, the referenced interface is a passive interface
                        such that it is not eligible to establish adjacencies with other
                        systems, but is advertised into the IS-IS topology.";
                }

                leaf hello_padding {
                    type boolean; 
                    default "true";
                    description
                        "When true, padding is added to IS-IS hello PDUs.";
                }

                leaf network_type {
                    type stypes:network-type;
                    description
                        "IS-IS interface type (point-to-point).";
                }

                leaf enable_bfd {
                    type boolean;
                    default "false";
                    description
                        "Monitor IS-IS peers on this interface.";
                }

                leaf bfd_profile {
                    type string;
                    description
                        "Set BFD to use a pre-configured profile.";
                }

                leaf metric {
                    type uint32 {
                        range "0..16777215";
                    }
                    default "0";
                    description
                        "The metric value of this interface.";
                }

                leaf csnp_interval {
                    type uint16 {
                        range "1..600";
                    }
                    units "seconds";
                    default "10";
                    description
                        "Complete Sequence Number PDU (CSNP) generation interval.";
                }

                leaf psnp_interval {
                    type uint16 {
                        range "1..120";
                    }
                    units "seconds";
                    default "2";
                    description
                        "Partial Sequence Number PDU (PSNP) generation interval.";
                }

                leaf hello_interval {
                    type uint32 {
                        range "1..600";
                    }
                    units "seconds";
                    default "3";
                    description
                        "Hello interval between consecutive hello messages. Interval will depend on multiplier.";
                }

                leaf hello_multiplier {
                    type uint16 {
                        range "2..100";
                    }
                    default "10";
                    description
                        "Multiplier for the hello holding time.";
                }

                uses isis-authentication; 

            }  // list ISIS_INTERFACE

        } // container ISIS_INTERFACE
```

#### SONiC ISIS Authentication Groupings
Authentication leafs used to define isis authentication options. 
 
 
``` 
    grouping isis-authentication {
        leaf authentication_key {
            type string {
                length "1..254";
            }
            must "(../authentication_type or not(../authentication_key))" {
                error-message
                    "If authentication_key is specified, then authentication_type must also be specified.";
            }
            description
                "Authentication password.";
        }

        leaf authentication_type {
            type stypes:authentication-type;
            must "(../authentication_key or not(../authentication_type))" {
                error-message
                    "If authentication_type is specified, then authentication_key must also be specified.";
            }
            description
                "This grouping defines keychain configuration type.";
        }
    }
```

##### SONiC ISIS Defined Types
Types defined in sonic-types.yang.j2.

```
    typedef net-address {
        type string {
            pattern "[a-fA-F0-9]{2}(\\.[a-fA-F0-9]{4}){3,9}\\.[a-fA-F0-9]{2}";
        }
        description
            "An IS-IS OSI NET address.
             An example NET address looks something like 49.0001.0143.0438.00.";
    }

    typedef level-number {
        type enumeration {
            enum "level-1";
            enum "level-2";
        }
        description
            "This type defines IS-IS level options for level specific configurations.";
    }

    typedef level-capability {
        type union {
            type level-number;
            type enumeration {
                enum "level-1-2";
            }
        }
        description
            "This type defines all IS-IS level options capable of being configured.";
    }

    typedef network-type {
        type enumeration {
            enum "point-to-point";
        }
        description
            "Configure a circuit to operate as point-to-point
             else the circuit defaults to broadcast.";
    }

    typedef authentication-type {
        type enumeration { 
            enum "clear";
            enum "md5";
        }
        description 
            "IS-IS authentication key encrypt type";
    } 
```

### Testing Requirements/Design

Extended unit test cases to cover FRR-ISIS YANG features
- Test new ISIS YANG model Validation
   - /src/sonic-yang-models/tests/test_sonic_yang_models.py
   - /src/sonic-yang-models/tests/yang_model_tests/test_yang_model.py
Extensive system test cases to cover FRR-ISIS YANG features
- Verify configs are properly stored in Redis DB

### Open/Action items - if any

