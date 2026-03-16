# IPv4 Port + Match Condition Based DHCP_SERVER in SONiC
# High Level Design Document
**Rev 0.1**

# Table of Contents
<!-- TOC -->

- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
    - [Background](#background)
    - [Functional Requirements](#functional-requirements)
    - [Configuration and Management Requirements](#configuration-and-management-requirements)
- [Design](#design)
    - [Design Considerations](#design-considerations)
    - [Design Overview](#design-overview)
    - [Match Condition Resolution](#match-condition-resolution)
    - [DB Changes](#db-changes)
        - [Config DB](#config-db)
            - [New Tables](#new-tables)
            - [Unchanged Tables](#unchanged-tables)
            - [DB Objects](#db-objects)
            - [Yang Model](#yang-model)
        - [State DB](#state-db)
- [CLI](#cli)
    - [Config CLI](#config-cli)
    - [Show CLI](#show-cli)
- [Test](#test)

<!-- /TOC -->


# Revision

| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:-----------------------------------|
| 0.1 |  2026/03/13 |                    | Initial version                     |

# About this Manual

This document describes the design details of extending the **ipv4 port based DHCP server** feature to support **match condition based IP assignment**. This allows operators to assign different IP addresses to DHCP clients connected to the same port based on DHCP packet options such as Vendor Class Identifier (Option 60).

This design is an **additive extension** to the existing port-based DHCP server described in the [Port Based DHCP Server HLD](https://github.com/sonic-net/SONiC/blob/master/doc/dhcp_server/port_based_dhcp_server_high_level_design.md). All existing tables, CLI commands, YANG models, and behaviors remain unchanged.

# Scope

This document describes the high level design for adding match condition support to the existing port-based DHCP server. The scope includes:

- New Config DB tables for match conditions and port+match bindings
- New CLI commands for managing match conditions and bindings
- YANG model extensions

# Definitions/Abbreviations

###### Table 1: Abbreviations
| Abbreviation             | Full form                        |
|--------------------------|----------------------------------|
| DHCP                     | Dynamic Host Configuration Protocol |
| VCI                      | Vendor Class Identifier (DHCP Option 60) |

###### Table 2: Definitions
| Definitions              | Description                        |
|--------------------------|----------------------------------|
| match condition          | A named rule that tests a DHCP packet field (e.g., option 60 value) |
| binding                  | A named association of (port, match condition(s)) → IP pool |

# Overview

The existing port-based DHCP server assigns IPs solely based on which physical port a client is connected to. This works well for simple scenarios where each port serves a single device type.

However, in practice, a single port may connect to different device types (e.g., via a downstream switch or hub), and operators need to assign different IPs based on what type of device is requesting. DHCP Option 60 (Vendor Class Identifier) is commonly used by devices to identify their type.

This extension adds the ability to match on DHCP packet options in addition to port, enabling **port + match condition** based IP assignment.

## Background

The current design assigns IP pools per port. This extension introduces a **generalized match condition system** where match types are extensible. Initially, `option60` (Vendor Class Identifier) is supported. Future types (e.g., `option61`, `option77`, `option12`) can be added by extending the enumeration — no structural changes required.

## Functional Requirements

1. Support IP assignment based on port + DHCP packet option matching.
2. Support DHCP Option 60 (Vendor Class Identifier) as the initial match type.
3. Support combining multiple match conditions per binding (AND logic).
4. Support assigning different IP pools to different device types on the same port.
5. Maintain backward compatibility — existing port-only assignments continue to work unchanged.
6. Provide a fallback mechanism — when a port has match bindings, clients not matching any condition fall back to the default port pool (if configured).
7. Extensible design for adding new match types in the future.

## Configuration and Management Requirements

Configuration of match condition feature can be done via:
* JSON config input
* SONiC CLI

# Design

## Design Considerations

* This feature is an **additive extension** to the existing port-based DHCP server. All existing Config DB tables, CLI commands, and YANG models remain unchanged.

* Match conditions are **always combined with port**. A match condition alone does not determine the IP pool; it is always port + match. This keeps the security property of port-based assignment (unconfigured ports cannot obtain IPs).

* The existing `DHCP_SERVER_IPV4_PORT` table acts as the **default/fallback** pool for a port. When a port has both `PORT` and `PORT_MATCH` entries, clients that don't match any condition receive IPs from the `PORT` pool.

* **Match bindings use AND logic** — when multiple match conditions are specified in a single binding, the client must satisfy ALL conditions.

* **OR logic** is achieved by creating separate binding entries pointing to the same IP pool.

* In the current design, only **exact matching** is supported. Substring/prefix matching may be added in future releases.

## Design Overview

The extension adds two new Config DB tables:

1. **`DHCP_SERVER_IPV4_MATCH`** — Defines named, reusable match conditions (e.g., "match option 60 equals VendorA").
2. **`DHCP_SERVER_IPV4_PORT_MATCH`** — Binds a (Vlan, Port, BindingName) tuple with one or more match conditions to an IP pool.

When the DHCP server processes a request from a port that has match bindings configured, it evaluates the match conditions against the DHCP packet. If a match is found, the corresponding IP pool is used. If no match is found, the default port pool (from `DHCP_SERVER_IPV4_PORT`) is used as fallback, if configured.

Example scenario:
- VendorA devices on port Ethernet1 → receive IPs from Pool A
- VendorB devices on port Ethernet1 → receive IPs from Pool B
- Other devices on port Ethernet1 → receive IPs from default Pool C
- Devices on port Ethernet2 (no match entries) → receive IPs from Pool D (unchanged behavior)

## Match Condition Resolution

### AND Logic

When a binding references multiple match conditions, all conditions must be satisfied:

```json
"Vlan100|Ethernet1|vendor_a_voip": {
    "matches": ["vendor_a", "voip_class"],
    "ips": ["100.1.1.25"]
}
```

A client must have option 60 matching "VendorA" **and** option 77 matching "VoIP" to receive 100.1.1.25.

### OR Logic

OR logic is achieved by creating separate bindings that point to the same IP pool:

```json
"Vlan100|Ethernet1|vendor_a_phones": {
    "matches": ["vendor_a"],
    "ips": ["100.1.1.20", "100.1.1.21"]
},
"Vlan100|Ethernet1|vendor_c_phones": {
    "matches": ["vendor_c"],
    "ips": ["100.1.1.20", "100.1.1.21"]
}
```

Either VendorA or VendorC devices will receive addresses from that pool.

### Specificity Ordering

When a port has multiple match bindings with overlapping conditions, more-specific bindings (more match conditions) take priority over less-specific ones:

1. Bindings with more match conditions are evaluated first (most specific)
2. Bindings with fewer match conditions are evaluated next
3. The default port pool (from `DHCP_SERVER_IPV4_PORT`) is used last as fallback

This ensures a "VendorA VoIP" device (matching 2 conditions) is assigned from the VoIP-specific pool, not the broader "VendorA" pool.

## DB Changes

### Config DB

Two new tables are added. All existing tables remain unchanged.

#### New Tables

**DHCP_SERVER_IPV4_MATCH** — Defines named match conditions.

| Field | Type   | Required | Description |
|-------|--------|----------|-------------|
| type  | enum   | Yes      | Match type. Currently: `option60`. Extensible for future types. |
| value | string | Yes      | Value to match against (exact match). |

**DHCP_SERVER_IPV4_PORT_MATCH** — Binds port + match condition(s) to IP pool.

Key format: `<vlan>|<port>|<binding_name>`

> `<binding_name>` is a user-defined unique label. It has no semantic meaning beyond making the key unique and providing a readable identifier. The actual match logic comes entirely from the `matches` field.

| Field   | Type      | Required | Description |
|---------|-----------|----------|-------------|
| matches | leaf-list | Yes      | One or more references to `DHCP_SERVER_IPV4_MATCH` entries. Combined with AND logic. |
| ips     | leaf-list | No       | Direct IP assignment. Mutually exclusive with `ranges`. |
| ranges  | leaf-list | No       | Range references. Mutually exclusive with `ips`. |

#### Unchanged Tables

The following existing tables are **not modified**:
- `DHCP_SERVER_IPV4` — DHCP interface configuration
- `DHCP_SERVER_IPV4_PORT` — Port-to-IP bindings (acts as default/fallback)
- `DHCP_SERVER_IPV4_RANGE` — Named IP ranges
- `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` — DHCP option definitions

#### DB Objects

```JSON
{
  "DHCP_SERVER_IPV4_MATCH": {
      "vendor_a": {
          "type": "option60",
          "value": "VendorA"
      },
      "voip_class": {
          "type": "option77",
          "value": "VoIP"
      },
      "vendor_b": {
          "type": "option60",
          "value": "VendorB"
      }
  },
  "DHCP_SERVER_IPV4_PORT_MATCH": {
      "Vlan100|Ethernet1|vendor_a_voip": {
          "matches": [
              "vendor_a",
              "voip_class"
          ],
          "ips": [
              "100.1.1.25"
          ]
      },
      "Vlan100|Ethernet1|vendor_a_devices": {
          "matches": [
              "vendor_a"
          ],
          "ips": [
              "100.1.1.20"
          ]
      },
      "Vlan100|Ethernet1|vendor_b_devices": {
          "matches": [
              "vendor_b"
          ],
          "ranges": [
              "range2"
          ]
      }
  }
}
```

#### Yang Model

The following YANG containers are added to the existing `sonic-dhcp-server-ipv4` module:

```yang
container DHCP_SERVER_IPV4_MATCH {

    description "DHCP_SERVER_IPV4_MATCH part of config_db.json";

    list DHCP_SERVER_IPV4_MATCH_LIST {

        description "Named match conditions for conditional DHCP IP assignment";

        key "name";

        leaf name {
            description "Name of match condition";
            type string {
                length 1..255 {
                    error-message "Invalid length for match condition name";
                }
            }
        }

        leaf type {
            description "Match type, determines which DHCP packet field to match";
            mandatory true;
            type enumeration {
                enum option60;
            }
        }

        leaf value {
            description "Value to match against (exact match)";
            mandatory true;
            type string {
                length 1..255 {
                    error-message "Invalid length for match value";
                }
            }
        }
    }
    /* end of DHCP_SERVER_IPV4_MATCH_LIST */
}
/* end of DHCP_SERVER_IPV4_MATCH container */

container DHCP_SERVER_IPV4_PORT_MATCH {

    description "DHCP_SERVER_IPV4_PORT_MATCH part of config_db.json";

    list DHCP_SERVER_IPV4_PORT_MATCH_LIST {

        description "Binds port + match condition(s) to an IP pool";

        key "name port binding";

        leaf name {
            description "Name of DHCP interface (Vlan)";
            type leafref {
                path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4/dhcp-server-ipv4:DHCP_SERVER_IPV4_LIST/dhcp-server-ipv4:name";
            }
        }

        leaf port {
            description "Interface under DHCP interface";
            type union {
                type leafref {
                    path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                }
                type leafref {
                    path "/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name";
                }
                type leafref {
                    path "/smartswitch:sonic-smart-switch/smartswitch:DPUS/smartswitch:DPUS_LIST/smartswitch:midplane_interface";
                }
            }
        }

        leaf binding {
            description "User-defined binding label for uniqueness";
            type string {
                length 1..255 {
                    error-message "Invalid length for binding name";
                }
            }
        }

        leaf-list matches {
            description "References to match conditions. Multiple entries use AND logic.";
            min-elements 1;
            type leafref {
                path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4_MATCH/dhcp-server-ipv4:DHCP_SERVER_IPV4_MATCH_LIST/dhcp-server-ipv4:name";
            }
            ordered-by user;
        }

        leaf-list ips {
            description "Assigned IPs";
            must "(not(boolean(../ranges)))"{
                error-message "Statement of 'ips' and 'ranges' cannot both exist";
            }
            type inet:ipv4-address;
            ordered-by user;
        }

        leaf-list ranges {
            description "IP ranges";
            must "(not(boolean(../ips)))"{
                error-message "Statement of 'ips' and 'ranges' cannot both exist";
            }
            type leafref {
                path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4_RANGE/dhcp-server-ipv4:DHCP_SERVER_IPV4_RANGE_LIST/dhcp-server-ipv4:name";
            }
            ordered-by user;
        }
    }
    /* end of DHCP_SERVER_IPV4_PORT_MATCH_LIST */
}
/* end of DHCP_SERVER_IPV4_PORT_MATCH container */
```

### State DB

No new State DB tables are required. The existing `DHCP_SERVER_IPV4_LEASE` table continues to track leases regardless of whether they were assigned via port-only or port+match rules.

# CLI

* New config CLI (under existing `config dhcp_server ipv4` group)
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 match add | Add a named match condition |
  | config dhcp_server ipv4 match del | Delete a named match condition |
  | config dhcp_server ipv4 match update | Update a named match condition |
  | config dhcp_server ipv4 match bind | Bind port + match condition(s) to IP pool |
  | config dhcp_server ipv4 match unbind | Unbind port + match condition(s) from IP pool |

* New show CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | show dhcp_server ipv4 match | Show defined match conditions |
  | show dhcp_server ipv4 port_match | Show port + match bindings |

## Config CLI

**config dhcp_server ipv4 match add**

This command is used to add a named match condition.

- Usage
  ```
  config dhcp_server ipv4 match add <match_name> --type <type> --value <value>

  Options:
     match_name: Unique name for the match condition. [required]
     type: Match type. Currently only 'option60' is supported. [required]
     value: Value to match against (exact match). [required]
  ```

- Example
  ```
  config dhcp_server ipv4 match add vendor_a --type option60 --value "VendorA"
  config dhcp_server ipv4 match add voip_class --type option60 --value "VoIP-Device"
  ```

**config dhcp_server ipv4 match del**

This command is used to delete a named match condition. Deletion is not allowed if the match is referenced by any port match binding.

- Usage
  ```
  config dhcp_server ipv4 match del <match_name>
  ```

- Example
  ```
  config dhcp_server ipv4 match del vendor_a
  ```

**config dhcp_server ipv4 match update**

This command is used to update an existing match condition.

- Usage
  ```
  config dhcp_server ipv4 match update <match_name> [--type <type>] [--value <value>]
  ```

- Example
  ```
  config dhcp_server ipv4 match update vendor_a --value "VendorA-v2"
  ```

**config dhcp_server ipv4 match bind**

This command is used to bind port + match condition(s) to an IP pool. The `--match` option accepts comma-separated match names (AND logic when multiple).

- Usage
  ```
  config dhcp_server ipv4 match bind <vlan_interface> <member_interface> <binding_name> --match <match_list> (--range <ip_range_list> | <ip_list>)
  ```

- Example
  ```
  # Single match condition
  config dhcp_server ipv4 match bind Vlan100 Ethernet1 vendor_a_devices --match vendor_a 100.1.1.20

  # Multiple match conditions (AND logic)
  config dhcp_server ipv4 match bind Vlan100 Ethernet1 vendor_a_voip --match vendor_a,voip_class 100.1.1.25

  # Using ranges
  config dhcp_server ipv4 match bind Vlan100 Ethernet1 vendor_b_devices --match vendor_b --range range2
  ```

**config dhcp_server ipv4 match unbind**

This command is used to unbind port + match condition(s) from IP pool.

- Usage
  ```
  config dhcp_server ipv4 match unbind <vlan_interface> <member_interface> <binding_name> (--range <ip_range_list> | <ip_list> | all)
  ```

- Example
  ```
  config dhcp_server ipv4 match unbind Vlan100 Ethernet1 vendor_a_devices all
  config dhcp_server ipv4 match unbind Vlan100 Ethernet1 vendor_a_devices 100.1.1.20
  ```

## Show CLI

**show dhcp_server ipv4 match**

This command is used to show defined match conditions.

- Usage
  ```
  show dhcp_server ipv4 match [<match_name>]
  ```

- Example
  ```
  show dhcp_server ipv4 match
  +--------------+----------+--------------+
  | Match Name   | Type     | Value        |
  +==============+==========+==============+
  | vendor_a     | option60 | VendorA      |
  +--------------+----------+--------------+
  | voip_class   | option60 | VoIP-Device  |
  +--------------+----------+--------------+
  | vendor_b     | option60 | VendorB      |
  +--------------+----------+--------------+

  show dhcp_server ipv4 match vendor_a
  +--------------+----------+---------+
  | Match Name   | Type     | Value   |
  +==============+==========+=========+
  | vendor_a     | option60 | VendorA |
  +--------------+----------+---------+
  ```

**show dhcp_server ipv4 port_match**

This command is used to show port + match bindings.

- Usage
  ```
  show dhcp_server ipv4 port_match [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 port_match Vlan100
  +------------------------------------------+---------------------+--------------+
  | Interface                                | Matches             | Bind         |
  +==========================================+=====================+==============+
  | Vlan100|Ethernet1|vendor_a_voip          | vendor_a,voip_class | 100.1.1.25   |
  +------------------------------------------+---------------------+--------------+
  | Vlan100|Ethernet1|vendor_a_devices       | vendor_a            | 100.1.1.20   |
  +------------------------------------------+---------------------+--------------+
  | Vlan100|Ethernet1|vendor_b_devices       | vendor_b            | range2       |
  +------------------------------------------+---------------------+--------------+
  ```

# Test

Detailed test cases will be covered in a separate test plan document in [sonic-mgmt](https://github.com/sonic-net/sonic-mgmt).
