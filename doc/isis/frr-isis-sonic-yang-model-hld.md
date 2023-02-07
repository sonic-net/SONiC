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
|  0.1  | Jan-11-2022  | C Choate | Initial version    |

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
  "net"                         :{{net-address}} (OPTIONAL)
  "level-capability"            :{{"level-1"/"level-2"/"level-1-2"}} (OPTIONAL)
  "dynamic-hostname"            :{{boolean}} (OPTIONAL)
  "attach-send"                 :{{boolean}} (OPTIONAL)
  "attach-receive-ignore"       :{{boolean}} (OPTIONAL)
  "set-overload-bit"            :{{boolean}} (OPTIONAL)             
  "lsp-mtu-size"                :{{UINT16}}  (OPTIONAL)
  "spf-init-delay"              :{{UINT16}}  (OPTIONAL*)
  "spf-short-delay"             :{{UINT16}}  (OPTIONAL*)
  "spf-long-delay"              :{{UINT16}}  (OPTIONAL*)
  "spf-hold-delay"              :{{UINT16}}  (OPTIONAL*)
  "spf-time-to-learn"           :{{UINT16}}  (OPTIONAL*)
  "log-adjacency-changes"       :{{boolean}} (OPTIONAL)

* If an SPF value is specified, all other global SPF values must also be specified

ISIS_GLOBAL|{{instance}}
; Defines schema for global ISIS configuration attributes
key                         = ISIS_GLOBAL:instance ; Instance name/area tag
; field                     = value
net                         = net-address          ; OSI NET address. Format: xx.xxxx.xxxx.xxxx.xx
level-capability            = "level-1"/"level-2"/"level-1-2" ; ISIS level capability
dynamic-hostname            = boolean              ; Dynamic-hostname support. Default "true"
attach-send                 = boolean              ; Send attached bits in LSP for inter-area traffic. Default "true"
attach-receive-ignore       = boolean              ; Attached bits recieved in LSP cause default route add. Default "false"
set-overload-bit            = boolean              ; Administratively enable the overload bit
lsp-mtu-size                = UINT16               ; MTU of an LSP. Range 128..4352. Default 1487
spf-init-delay              = UINT16               ; Delay used while in QUIET state. Range 0..60000 in msec.
spf-short-delay             = UINT16               ; Delay used while in SHORT_WAIT state. Range 0..60000 in msec.
spf-long-delay              = UINT16               ; Delay used while in LONG_WAIT state. Range 0..60000 in msec.
spf-hold-delay              = UINT16               ; Time with no received IGP events before considering IGP stable. 
                                                     Range 0..60000 in msec.
spf-time-to-learn           = UINT16               ; Maximum duration needed to learn all the events related to a single failure. 
                                                     Range 0..60000 in msec.
log-adjacency-changes       = boolean              ; Log changes to the IS-IS adjacencies in this instance. Default "false"

Tree view
     +--rw ISIS_GLOBAL
     |  +--rw ISIS_GLOBAL_LIST* [instance]
     |     +--rw instance                       string
     |     +--rw net?                           net-address
     |     +--rw level-capability?              level-capability
     |     +--rw dynamic-hostname?              boolean
     |     +--rw attach-send?                   boolean
     |     +--rw attach-receive-ignore?         boolean
     |     +--rw set-overload-bit?              boolean
     |     +--rw lsp-mtu-size?                  UINT16
     |     +--rw spf-init-delay                 uint16
     |     +--rw spf-short-delay                uint16
     |     +--rw spf-long-delay                 uint16
     |     +--rw spf-hold-down                  uint16
     |     +--rw spf-time-to-learn              uint16
     |     +--rw log-adjacency-changes?         boolean
```

##### Level Config
Level specific ISIS config options.

```
"ISIS_LEVEL"
  "instance"                         :{{string}} 
  "level-number"                     :{{UINT8}} 
  "lsp-refresh-interval"             :{{UINT16}} (OPTIONAL)
  "lsp-maximum-lifetime"             :{{UINT16}} (OPTIONAL)
  "lsp-generation-interval"          :{{UINT16}} (OPTIONAL)
  "spf-minimum-interval"             :{{UINT16}} (OPTIONAL)

ISIS_LEVEL|{{instance|level-number}}
; Defines schema for ISIS level configuration attributes
key                                = ISIS_LEVEL:instance ; Instance name/area tag
key                                = ISIS_LEVEL:level-number     ; Level number. ("level-1"/"level-2")
; field                            = value
lsp-refresh-interval               = UINT16               ; LSP refresh interval. Default 900 in seconds
lsp-maximum-lifetime               = UINT16               ; Maximum LSP lifetime. Range 350..65535. Default 1200 in seconds. Must be at least 300 seconds more than lsp-refresh-interval 
lsp-generation-interval            = UINT16               ; Minimum time allowed before LSP retransmissions. Range 1..120. Default 30 in seconds. Must be lower than lsp-refresh-interval
spf-minimum-interval               = UINT16               ; Minimum time between consecutive SPFs. Range 1..120. Default 1 in seconds

Tree view
     +--rw ISIS_LEVEL
     |  +--rw ISIS_LEVEL_LIST* [instance level]
     |     +--rw instance                         string
     |     +--rw level-number                     level-number
     |     +--rw lsp-refresh-interval?            uint16
     |     +--rw lsp-maximum-lifetime?            uint16
     |     +--rw lsp-generation-interval?         uint16
     |     +--rw spf-minimum-interval?            uint16
```

##### Interface Config
Interface specific ISIS config options.

```
"ISIS_INTERFACE"
  "instance"                         :{{string}} 
  "ifname"                           :{{string}} 
  "ipv4-routing"                     :{{{boolean}}} (OPTIONAL)
  "ipv6-routing"                     :{{{boolean}}} (OPTIONAL)
  "passive"                          :{{boolean}} (OPTIONAL)
  "hello-padding"                    :{{{boolean}}} (OPTIONAL)
  "network-type"                     :{{"UNKNOWN_NETWORK"/"BROADCAST_NETWORK"/"POINT_TO_POINT_NETWOR"/"LOOPBACK"}} (OPTIONAL)
  "enable-bfd"                       :{{{boolean}}} (OPTIONAL)
  "bfd-profile"                      :{{string}} (OPTIONAL)    
  "metric"                           :{{UINT32}} (OPTIONAL)
  "csnp-interval"                    :{{{UINT16}}} (OPTIONAL)
  "psnp-interval"                    :{{{UINT16}}} (OPTIONAL)
  "hello-interval"                   :{{{UINT32}}} (OPTIONAL)
  "hello-multiplier"                 :{{UINT16}} (OPTIONAL)
  "authentication-key"               :{{string}}
  "authentication-type"              :{{"TEXT"/"MD5HMAC"}} (OPTIONAL)

ISIS_INTERFACE|{{instance|ifname}}
; Defines schema for ISIS interface configuration attributes
key                                = ISIS_INTERFACE:instance ; Instance name/area tag
key                                = ISIS_INTERFACE:ifname ; Interface name
; field                            = value
ipv4-routing                       = boolean               ; Enable routing IPv4 traffic over this circuit
ipv6-routing                       = bolean                ; Enable routing IPv6 traffic over this circuit
passive                            = bolean                ; Advertise the interface in the ISIS topology, but don't allow it to form adjacencies. Default "false"
hello-padding                      = boolean               ; Add padding to IS-IS hello PDUs
network-type                       = "UNKNOWN_NETWORK"/"BROADCAST_NETWORK"/"POINT_TO_POINT_NETWOR"/"LOOPBACK"
; ISIS circuit type
enable-bfd                         = boolean               ; Monitor IS-IS peers on this circuit
bfd-profile                        = string                ; Let BFD use a pre-configured profile
metric                             = UINT32                ; Metric value on a circuit for a given level. Range 0..16777215. Default 0
csnp-interval                      = boolean               ; Complete Sequence Number PDU (CSNP) generation interval. Range 1..600. Default 10 in seconds
psnp-interval                      = boolean               ; Partial Sequence Number PDU (PSNP) generation interval. Range 1..120. Default 2 in seconds
hello-interval                     = UINT32                ; Hello interval between consecutive hello messages. Range 1..600. Default 3 in seconds
hello-multiplier                   = UINT16                ; Multiplier for the hello holding time. Range 2..100. Default 10
authentication-key                 = string                ; Authentication password
authentication-type                = "TEXT"/"MD5HMAC"      ; Authentication keychain type


Tree view
     +--rw ISIS_INTERFACE
     |  +--rw ISIS_INTERFACE_LIST* [instance ifname]
     |     +--rw instance                         string
     |     +--rw ifname                           string
     |     +--rw ipv4-routing?                    string
     |     +--rw ipv6-routing?                    string
     |     +--rw passive?                         boolean
     |     +--rw hello-padding?                   boolean
     |     +--rw network-type?                    network-type
     |     +--rw enable-bfd?                      boolean
     |     +--rw bfd-profile?                     string
     |     +--rw metric?                          uint32
     |     +--rw csnp-interval?                   uint16
     |     +--rw psnp-interval?                   uint16
     |     +--rw hello-interval?                  uint32
     |     +--rw hello-multiplier?                uint16
     |     +--rw authentication-key?              string
     |     +--rw authentication-type?             "TEXT"/"MD5HMAC"
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
                        "The identifier for this instance of ISIS. Area-tag";
                }

                leaf net { 
                    type net-address; 
                    description
                        "ISIS network entity title (NET). The first 8 bits are usually
                        49 (private AFI), next 16 bits represent area, next 48 bits represent
                        system id and final 8 bits are set to 0.";
                    reference
                        "International Organization for Standardization, Information
                        technology - Open Systems Interconnection-Network service
                        Definition - ISO/ IEC 8348:2002.";
                }

                leaf level-capability {
                    type level-capability;
                    default "level-1-2";
                    description
                        "ISIS level capability (level-1, level-2, level-1-2).";
                  }

                leaf dynamic-hostname {
                    type boolean;
                    default "true";
                    description
                        "Dynamic hostname support for IS-IS.";
                }

                leaf attach-send {
                    type boolean;
                    default "true";
                    description
                        "For an L1 or L2 router, attached bits are sent in an LSP when set to true.";
                }

                leaf attach-receive-ignore {
                    type boolean;
                    default "false";
                    description
                        "For an L1 router, attached bits received in an LSP createa default route when set to false";
                }

                leaf set-overload-bit {
                    type boolean;
                    default "false";
                    description
                        "Administratively enable the overload bit.";
                }

                leaf lsp-mtu-size {
                    type uint16 {
                        range "128..4352";
                    }
                    default "1497";
                    description
                        "LSP MTU.";
                }

                leaf spf-init-delay { 
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "(not((not(../spf-init-delay)) and ../spf-short-delay and ../spf-long-delay and ../spf-hold-down and ../spf-time-to-learn))" {
                        error-message "SPF init delay must only be specified if all other spf parameters are specified";
                    }
                    description
                        "Delay used during QUIET state";
                }

                leaf spf-short-delay {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "(not((not(../spf-short-delay)) and ../spf-init-delay and ../spf-long-delay and ../spf-hold-down and ../spf-time-to-learn))" {
                        error-message "SPF short delay must only be specified if all other spf parameters are specified";
                    }
                    description
                        "Delay used during SHORT_WAIT state";
                }

                leaf spf-long-delay {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "(not((not(../spf-long-delay)) and ../spf-init-delay and ../spf-short-delay and ../spf-hold-down and ../spf-time-to-learn))" {
                        error-message "SPF long delay must only be specified if all other spf parameters are specified";
                    }
                    description
                        "Delay used during LONG_WAIT state";
                }

                leaf spf-hold-down {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "(not((not(../spf-hold-down)) and ../spf-short-delay and ../spf-long-delay and ../spf-init-delay and ../spf-time-to-learn))" {
                        error-message "SPF hold down must only be specified if all other spf parameters are specified";
                    }
                    description
                        "Period of time without IGP events before considering IGP stable";
                }

                leaf spf-time-to-learn {
                    type uint16 {
                        range "0..60000";
                    }
                    units "msec";
                    must "(not((not(../spf-time-to-learn)) and ../spf-short-delay and ../spf-long-delay and ../spf-hold-down and ../spf-init-delay))" {
                        error-message "SPF time-to-learn must only be specified if all other spf parameters are specified";
                    }
                    description
                        "Maximum time needed to learn all of the events related to a
                        failure";
                }

                leaf log-adjacency-changes {
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

                key "instance level-number";

                leaf instance {
                    type string;
                    description
                        "The identifier for this instance of ISIS. Area-tag";
                }

                leaf level-number {
                    type level-number;
                    description
                        "ISIS level-number.";
                }

                leaf lsp-refresh-interval {
                    type uint16;
                    units "seconds";
                    default "900";
                    description
                        "LSP refresh interval.";
                }

                leaf lsp-maximum-lifetime {
                    type uint16 {
                        range "350..65535";
                    }
                    units "seconds";
                    must ". >= ../lsp-refresh-interval + 300";
                    default "1200";
                    description
                        "Maximum LSP lifetime.";
                }

                leaf lsp-generation-interval {
                    type uint16 {
                        range "1..120";
                    }
                    units "seconds";
                    must ". < ../lsp-refresh-interval";
                    default "30";
                    description
                        "Minimum time before an LSP retransmissions.";
                }

                leaf spf-minimum-interval {
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
                        "The identifier for this instance of ISIS. Area-tag";
                }

                leaf ifname {
                    type string;
                    description
                        "Interface for which ISIS configuration is to be applied.";
                }

                leaf ipv4-routing-instance {
                    type string;
                    description
                        "Routing IS-IS IPv4 traffic over this interface for the given instance.";
                }
                leaf ipv6-routing-instance {
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

                leaf hello-padding {
                    type boolean; 
                    default "true";
                    description
                        "When true, padding is added to IS-IS hello PDUs.";
                }

                leaf network-type {
                    type network-type;
                    default "BROADCAST_NETWORK";
                    description
                        "ISIS interface type (p2p, broadcast, loopback, unknown).";
                }

                leaf enable-bfd {
                    type boolean;
                    default "false";
                    description
                        "Monitor IS-IS peers on this interface.";
                }

                leaf bfd-profile {
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

                leaf csnp-interval {
                    type uint16 {
                        range "1..600";
                    }
                    units "seconds";
                    default "10";
                    description
                        "Complete Sequence Number PDU (CSNP) generation interval.";
                }

                leaf psnp-interval {
                    type uint16 {
                        range "1..120";
                    }
                    units "seconds";
                    default "2";
                    description
                        "Partial Sequence Number PDU (PSNP) generation interval.";
                }

                leaf hello-interval {
                    type uint32 {
                        range "1..600";
                    }
                    units "seconds";
                    default "3";
                    description
                        "Hello interval between consecutive hello messages. Interval will depend on multiplier.";
                }

                leaf hello-multiplier {
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
 
        leaf authentication-key { 
            type string { 
                length "1..254"; 
            }
            must "(not((not(../authentication-key)) and ../authentication-type))" {
                error-message "ISIS authentication-key must only be specified if authentication-type is specified";
            }
            description 
                "Authentication password."; 
        } 
 
        leaf authentication-type { 
            type enumeration { 
                enum "TEXT" { 
                    value 1; 
                description 
                    "Clear text authentication type."; 
                } 
                enum "MD5HMAC" { 
                    value 2; 
                description 
                    "MD5 authentication type."; 
                } 
            }
            must "(not((not(../authentication-type)) and ../authentication-key))" {
                error-message "ISIS authentication-type must only be specified if authentication-key is specified";
            }
            description 
                "This grouping defines keychain configuration type."; 
            } 
    } 
```

##### SONiC ISIS Defined Types
Types defined in sonic-isis.yang.

```
    typedef net-address {
        type string {
            pattern "[a-fA-F0-9]{2}(\\.[a-fA-F0-9]{4}){3,9}\\.[a-fA-F0-9]{2}";
      }
        description
            "This type defines an OSI NET address,
            Example: 49.0123.4567.8910.00";
    }

    typedef level-number {
        type enumeration {
            enum "level-1" {
                value 1;
                description
                    "L1-only capability.";
            }
            enum "level-2" {
                value 2;
                description
                    "L2-only capability.";
            }
        }
        description
            "This type defines IS-IS level options for level specific configurations.";
    }

    typedef level-capability {
        type union {
            type level-number;
            type enumeration {
                enum "level-1-2" {
                    value 3;
                    description
                        "L1 and L2 capability.";
                }
            }
        }
        description
            "This type defines all IS-IS level options capable of being configured.";
    }

    typedef network-type {
        type enumeration {
            enum "UNKNOWN_NETWORK" {
                value 0;
                description
                    "Unknown network type.";
            }
            enum "BROADCAST_NETWORK" {
                value 1;
                description
                    "Broadcast interface network type.";
            }
            enum "POINT_TO_POINT_NETWORK" {
                value 2;
                description
                    "Point-to-point interface network type.";
            }
            enum "LOOPBACK" {
                value 3;
                description
                    "Loopback interface network type.";
            }
        }
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
Is there a way to better align the custom yang models designed for SONiC FRR-ISIS with Open Config ISIS models ? Not all FRR-ISIS features are compatible with Open Configs' models.
