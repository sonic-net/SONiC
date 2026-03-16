# IPv4 Match Condition Based DHCP_SERVER in SONiC
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

This document describes the design details of extending the **ipv4 port based DHCP server** feature to support **match condition based IP assignment**. This allows operators to assign different IP addresses to DHCP clients based on configurable match conditions such as port identity (Option 82 Circuit ID) and Vendor Class Identifier (Option 60).

A key insight of this design is that **port identification is itself a DHCP option match** (via Option 82 Circuit ID). By treating port as a first-class match condition type alongside other DHCP option matches, the design becomes uniform and extensible — all conditions are defined in the same table and composed freely.

This design is an **additive extension** to the existing port-based DHCP server described in the [Port Based DHCP Server HLD](https://github.com/sonic-net/SONiC/blob/master/doc/dhcp_server/port_based_dhcp_server_high_level_design.md). All existing tables, CLI commands, YANG models, and behaviors remain unchanged.

# Scope

This document describes the high level design for adding match condition support to the existing port-based DHCP server. The scope includes:

- New Config DB tables for match conditions and bindings
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
| match condition          | A named rule that tests a DHCP packet field (e.g., Option 82 Circuit ID, Option 60 value) |
| binding                  | A named association of match condition(s) → IP pool within a VLAN |
| circuit_id               | The Circuit ID sub-option of DHCP Option 82 (Relay Agent Information), used to identify the physical port a client is connected to |

# Overview

The existing port-based DHCP server assigns IPs solely based on which physical port a client is connected to. This works well for simple scenarios where each port serves a single device type.

However, in practice, a single port may connect to different device types (e.g., via a downstream switch or hub), and operators need to assign different IPs based on what type of device is requesting. DHCP Option 60 (Vendor Class Identifier) is commonly used by devices to identify their type.

This extension introduces a **generalized match condition system** where all matching criteria — including port identity — are treated uniformly as match conditions. Port identification (via DHCP Option 82 Circuit ID) and DHCP packet option matching (e.g., Option 60) use the same mechanism and can be composed freely.

## Background

In the current design, port identity is determined by matching against the Circuit ID sub-option of DHCP Option 82, which encodes the `hostname:port_alias` of the ingress port. This is fundamentally the same operation as matching any other DHCP option value.

By making `circuit_id` a match condition type alongside `option60`, the design achieves full uniformity:
- A port-only assignment is a binding with a single `circuit_id` match
- A port + vendor class assignment is a binding with `circuit_id` + `option60` matches (AND logic)
- Future match types are added by extending the enumeration — no structural changes required

## Functional Requirements

1. Support IP assignment based on configurable DHCP packet field matching.
2. Support `circuit_id` (port identification via Option 82) as a match condition type.
3. Support DHCP Option 60 (Vendor Class Identifier) as a match condition type.
4. Support combining multiple match conditions per binding (AND logic).
5. Support assigning different IP pools to different conditions within the same VLAN.
6. Introduce a new `MATCH` mode for `DHCP_SERVER_IPV4` to enable match condition based assignment.
7. Maintain backward compatibility — existing `PORT` mode assignments continue to work unchanged.
8. Extensible design for adding new match types in the future.

## Configuration and Management Requirements

Configuration of match condition feature can be done via:
* JSON config input
* SONiC CLI

# Design

## Design Considerations

* This feature is an **additive extension** to the existing port-based DHCP server. All existing CLI commands and YANG models remain backward compatible.

* **New `MATCH` mode.** The `DHCP_SERVER_IPV4` table's `mode` field gains a new enum value `MATCH`. When `mode=MATCH`, the DHCP server reads from `DHCP_SERVER_IPV4_MATCH` and `DHCP_SERVER_IPV4_BINDING` tables. When `mode=PORT`, behavior is unchanged. Different VLANs can use different modes independently.

* **Match conditions are the building blocks.** Each condition tests a single DHCP packet field. Conditions are composed via AND logic in bindings. This includes port identity — `circuit_id` is a match type, not a structural key.

* **Unified design.** Port identification and DHCP option matching use the same `DHCP_SERVER_IPV4_MATCH` table and `DHCP_SERVER_IPV4_BINDING` table. There is no separate port-coupled table for match bindings.

* **Match bindings use AND logic** — when multiple match conditions are specified in a single binding, the client must satisfy ALL conditions.

* **OR logic** is achieved by creating separate binding entries pointing to the same IP pool.

* In the current design, only **exact matching** is supported. Substring/prefix matching may be added in future releases.

## Design Overview

The extension adds a new mode and two new Config DB tables:

1. **`MATCH` mode** — A new value for the `mode` field in `DHCP_SERVER_IPV4`, enabling match condition based IP assignment for the VLAN.
2. **`DHCP_SERVER_IPV4_MATCH`** — Defines named, reusable match conditions (e.g., "match circuit_id equals etp1", "match option60 equals VendorA").
3. **`DHCP_SERVER_IPV4_BINDING`** — Associates a (Vlan, BindingName) tuple with one or more match conditions and an IP pool.

Since port identification is a match condition type, port-based and option-based matching are handled identically. A "port + vendor class" assignment is simply a binding with two match conditions: one `circuit_id` and one `option60`.

Example scenario:
- VendorA devices on etp1 → binding with matches [port_etp1, vendor_a] → Pool A
- VendorB devices on etp1 → binding with matches [port_etp1, vendor_b] → Pool B
- Any device on etp1 (no vendor match) → binding with matches [port_etp1] → default Pool C
- Any device on etp2 → binding with matches [port_etp2] → Pool D

## Match Condition Resolution

### AND Logic

When a binding references multiple match conditions, all conditions must be satisfied:

```json
"Vlan100|vendor_a_on_etp1": {
    "matches": ["port_etp1", "vendor_a"],
    "ips": ["100.1.1.20"]
}
```

A client must be on etp1 **and** have Option 60 matching "VendorA" to receive 100.1.1.20.

### OR Logic

OR logic is achieved by creating separate bindings that point to the same IP pool:

```json
"Vlan100|vendor_a_on_etp1": {
    "matches": ["port_etp1", "vendor_a"],
    "ips": ["100.1.1.20", "100.1.1.21"]
},
"Vlan100|vendor_b_on_etp1": {
    "matches": ["port_etp1", "vendor_b"],
    "ips": ["100.1.1.20", "100.1.1.21"]
}
```

Either VendorA or VendorB devices on etp1 will receive addresses from that pool.

### Specificity Ordering

When a VLAN has multiple bindings with overlapping conditions, more-specific bindings (more match conditions) take priority over less-specific ones:

1. Bindings with more match conditions are evaluated first (most specific)
2. Bindings with fewer match conditions are evaluated next

For example, a "VendorA device on etp1" matches both a 2-condition binding [port_etp1, vendor_a] and a 1-condition binding [port_etp1]. The more-specific 2-condition binding takes priority.

## DB Changes

### Config DB

Two new tables are added. One existing table is extended with a new mode value.

#### Modified Tables

**DHCP_SERVER_IPV4** — The `mode` field gains a new enum value `MATCH`.

| Mode    | Description |
|---------|-------------|
| `PORT`  | Existing behavior. IP assignment based on `DHCP_SERVER_IPV4_PORT` table. |
| `MATCH` | New. IP assignment based on `DHCP_SERVER_IPV4_MATCH` + `DHCP_SERVER_IPV4_BINDING` tables. |

#### New Tables

**DHCP_SERVER_IPV4_MATCH** — Defines named match conditions.

| Field | Type   | Required | Description |
|-------|--------|----------|-------------|
| type  | enum   | Yes      | Match type. Currently: `circuit_id`, `option60`. Extensible for future types. |
| value | string | Yes      | Value to match against (exact match). For `circuit_id`, this is the port alias (e.g., "etp1"). |

**DHCP_SERVER_IPV4_BINDING** — Associates match condition(s) with an IP pool.

Key format: `<vlan>|<binding_name>`

> `<binding_name>` is a user-defined unique label. It has no semantic meaning beyond making the key unique and providing a readable identifier. The actual match logic comes entirely from the `matches` field.

| Field   | Type      | Required | Description |
|---------|-----------|----------|-------------|
| matches | leaf-list | Yes      | One or more references to `DHCP_SERVER_IPV4_MATCH` entries. Combined with AND logic. |
| ips     | leaf-list | No       | Direct IP assignment. Mutually exclusive with `ranges`. |
| ranges  | leaf-list | No       | Range references. Mutually exclusive with `ips`. |

#### Unchanged Tables

The following existing tables are **not modified**:
- `DHCP_SERVER_IPV4_PORT` — Port-to-IP bindings (used when `mode=PORT`)
- `DHCP_SERVER_IPV4_RANGE` — Named IP ranges
- `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` — DHCP option definitions

#### DB Objects

```JSON
{
  "DHCP_SERVER_IPV4": {
      "Vlan100": {
          "gateway": "100.1.1.1",
          "lease_time": "3600",
          "mode": "MATCH",
          "netmask": "255.255.255.0",
          "state": "enabled"
      }
  },
  "DHCP_SERVER_IPV4_MATCH": {
      "port_etp1": {
          "type": "circuit_id",
          "value": "etp1"
      },
      "port_etp2": {
          "type": "circuit_id",
          "value": "etp2"
      },
      "vendor_a": {
          "type": "option60",
          "value": "VendorA"
      },
      "vendor_b": {
          "type": "option60",
          "value": "VendorB"
      }
  },
  "DHCP_SERVER_IPV4_BINDING": {
      "Vlan100|vendor_a_on_etp1": {
          "matches": [
              "port_etp1",
              "vendor_a"
          ],
          "ips": [
              "100.1.1.20"
          ]
      },
      "Vlan100|vendor_b_on_etp1": {
          "matches": [
              "port_etp1",
              "vendor_b"
          ],
          "ranges": [
              "range2"
          ]
      },
      "Vlan100|default_etp1": {
          "matches": [
              "port_etp1"
          ],
          "ips": [
              "100.1.1.10"
          ]
      }
  }
}
```

#### Yang Model

The existing `DHCP_SERVER_IPV4` mode enum is extended with `MATCH`. The following new YANG containers are added to the `sonic-dhcp-server-ipv4` module:

```yang
/* Extension to existing DHCP_SERVER_IPV4_LIST mode leaf */
leaf mode {
    description "DHCP server mode";
    type enumeration {
        enum PORT;
        enum MATCH;
    }
}

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
                enum circuit_id;
                enum option60;
            }
        }

        leaf value {
            description "Value to match against (exact match). For circuit_id, this is the port alias.";
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

container DHCP_SERVER_IPV4_BINDING {

    description "DHCP_SERVER_IPV4_BINDING part of config_db.json";

    list DHCP_SERVER_IPV4_BINDING_LIST {

        description "Associates match condition(s) with an IP pool";

        key "name binding";

        leaf name {
            description "Name of DHCP interface (Vlan)";
            type leafref {
                path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4/dhcp-server-ipv4:DHCP_SERVER_IPV4_LIST/dhcp-server-ipv4:name";
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
    /* end of DHCP_SERVER_IPV4_BINDING_LIST */
}
/* end of DHCP_SERVER_IPV4_BINDING container */
```

### State DB

No new State DB tables are required. The existing `DHCP_SERVER_IPV4_LEASE` table continues to track leases regardless of whether they were assigned via port-only or match condition rules.

# CLI

* New config CLI (under existing `config dhcp_server ipv4` group)
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 match add | Add a named match condition |
  | config dhcp_server ipv4 match del | Delete a named match condition |
  | config dhcp_server ipv4 match update | Update a named match condition |
  | config dhcp_server ipv4 binding add | Add a binding (match condition(s) → IP pool) |
  | config dhcp_server ipv4 binding del | Delete a binding |

* New show CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | show dhcp_server ipv4 match | Show defined match conditions |
  | show dhcp_server ipv4 binding | Show bindings |

## Config CLI

**config dhcp_server ipv4 match add**

This command is used to add a named match condition.

- Usage
  ```
  config dhcp_server ipv4 match add <match_name> --type <type> --value <value>

  Options:
     match_name: Unique name for the match condition. [required]
     type: Match type. Currently 'circuit_id' and 'option60' are supported. [required]
     value: Value to match against (exact match). For circuit_id, this is the port alias. [required]
  ```

- Example
  ```
  config dhcp_server ipv4 match add port_etp1 --type circuit_id --value "etp1"
  config dhcp_server ipv4 match add vendor_a --type option60 --value "VendorA"
  ```

**config dhcp_server ipv4 match del**

This command is used to delete a named match condition. Deletion is not allowed if the match is referenced by any binding.

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

**config dhcp_server ipv4 binding add**

This command is used to add a binding that associates match condition(s) with an IP pool. The `--match` option accepts comma-separated match names (AND logic when multiple).

- Usage
  ```
  config dhcp_server ipv4 binding add <vlan_interface> <binding_name> --match <match_list> (--range <ip_range_list> | <ip_list>)
  ```

- Example
  ```
  # Port + vendor class match (AND logic)
  config dhcp_server ipv4 binding add Vlan100 vendor_a_on_etp1 --match port_etp1,vendor_a 100.1.1.20

  # Using ranges
  config dhcp_server ipv4 binding add Vlan100 vendor_b_on_etp1 --match port_etp1,vendor_b --range range2

  # Port-only binding
  config dhcp_server ipv4 binding add Vlan100 default_etp1 --match port_etp1 100.1.1.10
  ```

**config dhcp_server ipv4 binding del**

This command is used to delete a binding.

- Usage
  ```
  config dhcp_server ipv4 binding del <vlan_interface> <binding_name>
  ```

- Example
  ```
  config dhcp_server ipv4 binding del Vlan100 vendor_a_on_etp1
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
  +--------------+------------+---------+
  | Match Name   | Type       | Value   |
  +==============+============+=========+
  | port_etp1    | circuit_id | etp1    |
  +--------------+------------+---------+
  | vendor_a     | option60   | VendorA |
  +--------------+------------+---------+
  | vendor_b     | option60   | VendorB |
  +--------------+------------+---------+

  show dhcp_server ipv4 match vendor_a
  +--------------+----------+---------+
  | Match Name   | Type     | Value   |
  +==============+==========+=========+
  | vendor_a     | option60 | VendorA |
  +--------------+----------+---------+
  ```

**show dhcp_server ipv4 binding**

This command is used to show bindings.

- Usage
  ```
  show dhcp_server ipv4 binding [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 binding Vlan100
  +----------------------------+--------------------+--------------+
  | Binding                    | Matches            | Bind         |
  +============================+====================+==============+
  | Vlan100|vendor_a_on_etp1   | port_etp1,vendor_a | 100.1.1.20   |
  +----------------------------+--------------------+--------------+
  | Vlan100|vendor_b_on_etp1   | port_etp1,vendor_b | range2       |
  +----------------------------+--------------------+--------------+
  | Vlan100|default_etp1       | port_etp1          | 100.1.1.10   |
  +----------------------------+--------------------+--------------+
  ```

# Test

Detailed test cases will be covered in a separate test plan document in [sonic-mgmt](https://github.com/sonic-net/sonic-mgmt).
