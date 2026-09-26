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
        - [AND Logic](#and-logic)
        - [OR Logic](#or-logic)
        - [Specificity Ordering](#specificity-ordering)
    - [DB Changes](#db-changes)
        - [Config DB](#config-db)
            - [Modified Tables](#modified-tables)
            - [New Tables](#new-tables)
            - [Unchanged Tables](#unchanged-tables)
            - [DB Objects](#db-objects)
            - [Yang Model](#yang-model)
        - [State DB](#state-db)
- [CLI](#cli)
    - [Config CLI](#config-cli)
    - [Clear CLI](#clear-cli)
    - [Show CLI](#show-cli)
- [Debuggability](#debuggability)
    - [Existing behaviour](#existing-behaviour)
    - [Changes](#changes)
    - [Operator workflow](#operator-workflow)
- [Test](#test)
    - [Unit Test](#unit-test)
        - [Config CLI](#config-cli-1)
        - [Clear CLI](#clear-cli-1)
        - [Show CLI](#show-cli-1)
    - [Test Plan](#test-plan)

<!-- /TOC -->

# Revision

| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:------------------------------------|
| 0.1 |  2026/08/31 | Nishant Sharma     | Initial version                     |
| 0.2 |  2026/09/15 | Nishant Sharma     | Review Updates                      |

# About this Manual

This document describes the design details of extending the **IPv4 port-based DHCP server** feature to support **match-condition-based IP assignment**. This allows operators to assign different IP addresses to DHCP clients based on configurable match conditions such as port identity (Option 82 Circuit ID) and Vendor Class Identifier (Option 60).

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

* **Mode switching.** When a VLAN's mode is changed from `PORT` to `MATCH`, the `DHCP_SERVER_IPV4_PORT` entries for that VLAN are ignored and the server is reconfigured using `BINDING` entries only. Active leases are not revoked — they expire naturally per their lease time. Operators should configure `BINDING` entries before switching modes to avoid a gap in service.

* **Match conditions are the building blocks.** Each condition tests a single DHCP packet field. Conditions are composed via AND logic in bindings. This includes port identity — `circuit_id` is a match type, not a structural key.

* **Unified design.** Port identification and DHCP option matching use the same `DHCP_SERVER_IPV4_MATCH` table and `DHCP_SERVER_IPV4_BINDING` table. There is no separate port-coupled table for match bindings.

* **Match bindings use AND logic** — when multiple match conditions are specified in a single binding, the client must satisfy ALL conditions.

* **OR logic** is achieved by creating separate binding entries pointing to the same IP pool.

* In the current design, only **exact matching** is supported. Substring/prefix matching may be added in future releases.

* IP assignments remain the same if the device reconnects before the lease expires; after lease expiry, a new IP can be assigned from the available IP range.

* For a client to be matched by an  option60  match condition, the Vendor Class Identifier (Option 60) must be present in the DISCOVER and in every subsequent DHCPREQUEST.  If Option 60 is absent from a REQUEST, the client is re-classified into a different (or no) binding, the requested address no longer falls within a pool reachable by that class, and the server replies with a DHCPNAK, forcing the client back to INIT.

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

**Note:** Operators should avoid creating multiple bindings with the same number of conditions that can both match the same client. If such an overlap exists, the behavior is non-deterministic. This is considered a misconfiguration. This becomes especially applicable when more match conditions are supported in future like MAC address.  Example :

```json
"Vlan100|vendor_a_on_etp1": {
    "matches": ["port_etp1", "vendor_a"],
    "ips": ["100.1.1.20", "100.1.1.21"]
},
"Vlan100|vendor_b_on_etp1": {
    "matches": ["port_etp1", "macaddress_a"],
    "ips": ["100.1.1.20", "100.1.1.21"]
}
```
There is a chance that a device can match both of the above match conditions. The behavior becomes non-deterministic in this case and the bindings should be updated to avoid ambiguity.

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
| value | string | Yes      | Value to match against (exact match). For `circuit_id`, the user configures the **port alias** (e.g., "etp1"); the implementation constructs the full on-wire Circuit ID (`hostname:port_alias`) internally, consistent with existing `PORT` mode behavior. |

**DHCP_SERVER_IPV4_BINDING** — Associates match condition(s) with an IP pool.

Key format: `<vlan>|<binding_name>`

> `<binding_name>` is a user-defined unique label. It has no semantic meaning beyond making the key unique and providing a readable identifier. The actual match logic comes entirely from the `matches` field.

| Field   | Type      | Required | Description |
|---------|-----------|----------|-------------|
| matches | leaf-list | Yes      | One or more references to `DHCP_SERVER_IPV4_MATCH` entries. Combined with AND logic. |
| ips     | leaf-list | No       | Direct IP assignment. Mutually exclusive with `ranges`. At least one of `ips` or `ranges` must be provided (enforced at application level). |
| ranges  | leaf-list | No       | Range references. Mutually exclusive with `ips`. At least one of `ips` or `ranges` must be provided (enforced at application level). |

**DHCP_SERVER_IPV4_GLOBAL** — Server wide dhcp_server settings that are not specific to a dhcp_interface.

Key format: `global`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| log_level | enum | No | Verbosity of the `kea-dhcp4` logger: `info` (default), `debug`, `trace`. The setting is server wide because a Kea logger applies to the whole `kea-dhcp4` process, not to an individual subnet. |

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

A container is also added for the server wide settings:

```yang
container DHCP_SERVER_IPV4_GLOBAL {

    description "DHCP_SERVER_IPV4_GLOBAL part of config_db.json";

    list DHCP_SERVER_IPV4_GLOBAL_LIST {

        description "Server wide dhcp_server settings";

        key "name";

        leaf name {
            description "Fixed key, always 'global'";
            type string {
                pattern "global";
            }
        }

        leaf log_level {
            description "Verbosity of the kea-dhcp4 logger";
            type enumeration {
                enum info;
                enum debug;
                enum trace;
            }
            default info;
        }
    }
}
```

### State DB

No new State DB tables are required. The existing `DHCP_SERVER_IPV4_LEASE` table continues to track leases regardless of whether they were assigned via port-only or match condition rules.

Three fields are added to each `DHCP_SERVER_IPV4_LEASE` entry, so that an operator can determine how an address was assigned and not merely that it was assigned.

| Field | Description |
|:-|:-|
| `mode` | Mode of the dhcp_interface at the time the address was assigned, `PORT` or `MATCH` |
| `binding` | Name of the binding that supplied the address. Empty in `PORT` mode. Comma separated when more than one binding resolves to the same address pool, see the note below |
| `assign_time` | Epoch time at which this client first received this address. Unlike `lease_start`, it is preserved across renewals, and is reset only when the client is assigned a different address |

# CLI

* New config CLI (under existing `config dhcp_server ipv4` group)
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 match add | Add a named match condition |
  | config dhcp_server ipv4 match del | Delete a named match condition |
  | config dhcp_server ipv4 match update | Update a named match condition |
  | config dhcp_server ipv4 binding add | Add a binding (match condition(s) → IP pool) |
  | config dhcp_server ipv4 binding update | Update a binding |
  | config dhcp_server ipv4 binding del | Delete a binding |
  | config dhcp_server ipv4 log-level | Set the verbosity of the kea-dhcp4 logger |

* New Clear CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | sonic-clear dhcp_server ipv4 lease | Delete an existing lease |

* New show CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | show dhcp_server ipv4 match | Show defined match conditions |
  | show dhcp_server ipv4 binding | Show bindings |
  | show dhcp_server ipv4 log-level | Show the configured verbosity of the kea-dhcp4 logger |

* Update existing config CLI to support MATCH mode
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 add --mode PORT\|MATCH | Extended to accept `MATCH` as a valid mode |
  | config dhcp_server ipv4 update --mode PORT\|MATCH | Extended to accept `MATCH` as a valid mode |

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

**config dhcp_server ipv4 binding update**

This command is used to update an existing binding's match condition(s) and/or IP pool. The `--match` option, when given, replaces the entire match list (comma-separated, AND logic when multiple). `ip_list` and `--range` are mutually exclusive, and providing one replaces the other.

- Usage
  ```
  config dhcp_server ipv4 binding update <vlan_interface> <binding_name> [--match <match_list>] [--range <ip_range_list> | <ip_list>]
  ```

- Example
  ```
  # Replace the match list
  config dhcp_server ipv4 binding update Vlan100 vendor_a_on_etp1 --match port_etp1,vendor_b

  # Replace the assigned ips
  config dhcp_server ipv4 binding update Vlan100 vendor_a_on_etp1 100.1.1.30

  # Switch from ip_list to a range
  config dhcp_server ipv4 binding update Vlan100 vendor_a_on_etp1 --range range3
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

**config dhcp_server ipv4 add/update**

This command is used to set the match mode to either PORT or MATCH. This CLI already accepts "PORT", it will be extended to accept "MATCH" as well to support this feature.

- Usage
  ```
  config dhcp_server ipv4 add --mode <mode> [--dup_gw_nm] [--lease_time <lease_time>] [--gateway <gateway>] [--netmask <netmask>] <dhcp_interface>
  config dhcp_server ipv4 update --mode <mode> [--dup_gw_nm] [--lease_time <lease_time>] [--gateway <gateway>] [--netmask <netmask>] <dhcp_interface>

  Options:
     mode: Specify mode of assign IP, support 'PORT' and 'MATCH'. [required]
  ```

- Example
  ```
  # Add a dhcp_server in MATCH mode for Vlan1000
  config dhcp_server ipv4 add --mode MATCH --dup_gw_nm --lease_time 300 Vlan1000

  # Switch an existing dhcp_server from PORT mode to MATCH mode
  config dhcp_server ipv4 update --mode MATCH Vlan1000
  ```

**config dhcp_server ipv4 log-level**

This command is used to set the verbosity of the `kea-dhcp4` logger. The setting is server wide, and is intended to be raised for the duration of an investigation and returned to `info` afterwards. See the Debuggability section for what each level records.

- Usage
  ```
  config dhcp_server ipv4 log-level <info|debug|trace>
  ```

- Example
  ```
  # Record the match conditions that were rejected for each client
  config dhcp_server ipv4 log-level debug

  # Additionally record the option values that were compared
  config dhcp_server ipv4 log-level trace

  # Return to the default
  config dhcp_server ipv4 log-level info
  ```

## Clear CLI

**sonic-clear dhcp_server ipv4 lease**

This command is used to delete an existing lease. This is helpful when a device is being replaced: the operator can remove the existing lease so that the same IP address can be re-assigned to the new device without waiting for the current lease to expire.

`<dhcp_interface>` is mandatory, since leases are scoped per subnet. Exactly one selector must be supplied: `IP_ADDRESS`, `--mac` or `--all`.

- Usage
  ```
  sonic-clear dhcp_server ipv4 lease <dhcp_interface> [IP_ADDRESS] [--mac <MAC>] [--all]
  ```

- Example
  ```
  # Clear the lease for an IP address on the interface
  sonic-clear dhcp_server ipv4 lease Vlan100 192.168.0.10

  # Clear the lease for a MAC address on the interface
  sonic-clear dhcp_server ipv4 lease Vlan100 --mac AA:BB:CC:DD:EE:FF

  # Clear all leases on the interface
  sonic-clear dhcp_server ipv4 lease Vlan100 --all
  ```

The lease is removed both from the DHCP server and from the `DHCP_SERVER_IPV4_LEASE` table in State DB, so that a subsequent `show dhcp_server ipv4 lease` no longer reports the cleared entry. If no lease matches the given selector, the command reports this and exits with a non-zero status.

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

**show dhcp_server ipv4 log-level**

This command displays the configured verbosity of the `kea-dhcp4` logger, together with the Kea severity and debug level it maps to.

- Usage
  ```
  show dhcp_server ipv4 log-level
  ```

- Example
  ```
  admin@sonic:~$ show dhcp_server ipv4 log-level
  +-----------+------------+--------------+
  | Log Level | Severity   |   Debuglevel |
  +===========+============+==============+
  | info      | INFO       |            0 |
  +-----------+------------+--------------+
  ```

# Debuggability

## Existing behaviour

`kea-dhcp4` already reports the result of every match condition evaluation through its `EVAL_RESULT` message, and this is emitted at `INFO` severity, which is the severity configured by default. A successful assignment therefore already leaves a trace in `/var/log/kea/kea-dhcp4.log`:

```
INFO  EVAL_RESULT [hwtype=1 00:11:22:33:44:01], cid=[no info], tid=0x6f2f79d8: Expression sonic_match_1000_20050c49d907bea1 evaluated to true
INFO  DHCP4_LEASE_ALLOC [hwtype=1 00:11:22:33:44:01], cid=[no info], tid=0x6f2f79d8: lease 192.168.0.21 has been allocated for 300 seconds
```

Two properties of this output limit its usefulness for an operator:

* The client class name is derived from a hash of the interface, subnet and address intervals, so it cannot be related back to a configured binding or match condition without reading the generated Kea configuration.
* Only the condition that matched is recorded at the default severity. Conditions that were evaluated and did not match are reported only at `DEBUG` severity with a raised debug level, so the common question of why a client did not match an expected binding cannot be answered from the default log.

## Changes

**Match condition class mapping.** Whenever `dhcpservd` regenerates the Kea configuration, it logs the mapping between each generated client class and the configuration it was generated from. This makes the existing `EVAL_RESULT` output directly interpretable, and covers the merged binding case described in the State DB section, where one class corresponds to more than one binding.

```
DHCP_SERVER_MATCH_CLASS sonic_match_1000_20050c49d907bea1 interface=Vlan1000 binding=bmc_on_etp1 matches=port_etp1,vendor_bmc pool=192.168.0.21-192.168.0.21 pool_id=1
```

**Assignment result.** `dhcpservd` logs the resolved binding when a lease is added or changed, so that the assignment is recorded in the SONiC log as well as in the Kea log.

```
DHCP_SERVER_LEASE_ASSIGNED interface=Vlan1000 mac=00:11:22:33:44:01 ip=192.168.0.21 mode=MATCH binding=bmc_on_etp1
```

**Configurable log severity.** The `severity` and `debuglevel` of the `kea-dhcp4` logger are fixed in `kea-dhcp4.conf.j2` today. They are made configurable, so that an operator can raise the verbosity for an investigation and lower it again afterwards without editing files inside the container:

```
config dhcp_server ipv4 log-level <info|debug|trace>
```

The setting is server wide rather than per dhcp_interface, because a Kea logger applies to the whole `kea-dhcp4` process. It is held in Config DB, so it survives a service restart and an image upgrade, is visible to `show` and to configuration backup, and can be reverted from the CLI. `dhcpservd` re-renders the Kea configuration and reloads `kea-dhcp4` when the value changes, in the same way as for any other DHCP configuration change.

Each level maps to a Kea `severity` and `debuglevel` pair. The mapping follows the detail that Kea actually produces at each level:

| CLI level | Kea severity | Kea debuglevel | What is recorded |
|:-|:-|:-|:-|
| `info` | `INFO` | `0` | Default. The match condition that matched, through `EVAL_RESULT ... evaluated to true`, together with `DHCP4_LEASE_ALLOC` |
| `debug` | `DEBUG` | `50` | Additionally every match condition that was evaluated and did not match, through `EVAL_RESULT ... evaluated to false`. This identifies which bindings were rejected for a given client |
| `trace` | `DEBUG` | `55` | Additionally the evaluation of each individual term, through the `EVAL_DEBUG_*` messages, which record the option values that were compared. This identifies why a condition was rejected |

Kea debug levels below 50 produce additional output without adding any classification detail, so they are not exposed as separate CLI levels.

At `trace`, the comparison that caused a client to miss a binding is visible directly:

```
DEBUG EVAL_DEBUG_EQUAL Popping 0x4D4149412D475055 and 0x4D4149412D424D43 pushing result 'false'
DEBUG EVAL_RESULT Expression sonic_match_1000_44bd8eaab98cbb3b evaluated to false
```

**Warning on non-default severity.** `dhcpservd` emits a warning to syslog each time it renders the Kea configuration at a level other than `info`, so that a debugging session left enabled is visible in the SONiC log and not only in the growth of the Kea log.

```
WARNING dhcpservd: DHCP_SERVER_LOG_SEVERITY kea-dhcp4 logger rendered at log-level=trace (severity=DEBUG debuglevel=55). This is intended for temporary debugging and should be reverted with 'config dhcp_server ipv4 log-level info'.
```

**Log rotation.** `/var/log/kea/kea-dhcp4.log` is added to the existing logrotate configuration, since raising the severity materially increases the volume written.

## Operator workflow

| Question | Where it is answered |
|:-|:-|
| Which address does a client currently hold | `show dhcp_server ipv4 lease` |
| Which binding assigned that address, and when it was first assigned | `binding` and `assign_time` fields of the lease, displayed by `show dhcp_server ipv4 lease` |
| Which match conditions a binding is built from | `show dhcp_server ipv4 binding` and `show dhcp_server ipv4 match` |
| Which class matched for a given client | `EVAL_RESULT` in the Kea log, resolved to a binding through the `DHCP_SERVER_MATCH_CLASS` mapping |
| Why a client did not match the expected binding | `config dhcp_server ipv4 log-level debug`, then the failing `EVAL_RESULT` for that client |
| Whether a client is sending the expected Option 60 or Option 82 | `config dhcp_server ipv4 log-level trace`, whose `EVAL_DEBUG_*` output records the option values that were compared |

# Test

## Unit Test

Unit tests cover the new `match` and `binding` command groups, as well as the
extensions to existing commands (`config dhcp_server ipv4 add|update --mode`).
Existing `PORT` mode test cases remain unchanged
and must continue to pass, to verify backward compatibility.

### Config CLI

- config dhcp_server ipv4 match add \<match_name\> --type \<type\> --value \<value\>

  |Case Description|Expected res|
  |:-|:-|
  |Add with valid name, --type=circuit_id, --value=etp1|Add success|
  |Add with valid name, --type=option60, --value=VendorA|Add success|
  |Add without --type|Add failed because type is missing|
  |Add without --value|Add failed because value is missing|
  |Add with unsupported type, like --type=option61|Add failed because type not supported|
  |Add with invalid type, like --type=CIRCUIT_ID|Add failed because type is case sensitive|
  |Add existed match name|Add failed because match name already exists|
  |Add with empty value|Add failed because value length invalid|
  |Add with value longer than 255 characters|Add failed because value length invalid|
  |Add with match name longer than 255 characters|Add failed because match name length invalid|
  |Add with --type=circuit_id and value not an existing port alias|Add failed because port alias not exist|
  |Add with same type and value as an existing match, different name|Add success with warning of duplicated match condition|

- config dhcp_server ipv4 match del \<match_name\>

  |Case Description|Expected res|
  |:-|:-|
  |Delete valid match that is not referenced by any binding|Delete success|
  |Delete match that is referenced by a binding|Delete failed because match is referenced, referencing bindings are listed|
  |Delete match not exist|Delete failed|

- config dhcp_server ipv4 match update \<match_name\> [--type \<type\>] [--value \<value\>]

  |Case Description|Expected res|
  |:-|:-|
  |Update --value of existing match|Update success|
  |Update --type of existing match|Update success|
  |Update both --type and --value of existing match|Update success|
  |Update match not exist|Update failed|
  |Update with unsupported type|Update failed because type not supported|
  |Update with invalid value|Update failed because value invalid|
  |Update without --type and --value|Update failed because nothing to update|
  |Update match that is referenced by bindings|Update success, affected bindings are listed in warning|

- config dhcp_server ipv4 binding add \<vlan_interface\> \<binding_name\> --match \<match_list\> (--range \<ip_range_list\> | \<ip_list\>)

  |Case Description|Expected res|
  |:-|:-|
  |Add with single match and single ip|Add success|
  |Add with multiple matches and single ip|Add success, matches are combined with AND logic|
  |Add with multiple matches and --range|Add success|
  |Add with multiple ips|Add success|
  |Add with both ip_list and --range|Add failed because 'ips' and 'ranges' cannot both exist|
  |Add without ip_list and --range|Add failed because neither 'ips' nor 'ranges' is given|
  |Add without --match|Add failed because at least one match is required|
  |Add with empty --match list|Add failed because at least one match is required|
  |Add with match not exist|Add failed because match not exist|
  |Add with duplicated match name in --match list|Add failed because match list contains duplication|
  |Add with vlan_interface not exist|Add failed|
  |Add with vlan_interface that has no dhcp_server config|Add failed because dhcp_server is not configured on this interface|
  |Add existed binding name under same vlan_interface|Add failed because binding already exists|
  |Add same binding name under different vlan_interface|Add success|
  |Add with ip_list not in vlan net|Add failed|
  |Add with range not in vlan net|Add failed|
  |Add with range not exist|Add failed because range not exist|
  |Add with binding name longer than 255 characters|Add failed because binding name length invalid|
  |Add to a vlan_interface whose mode is PORT|Add success with warning that binding is not effective under PORT mode|
  |Add a binding that has the same number of matches as an existing binding and can match the same client|Add success, Behavior becomes non-deterministic and this is an operator level misconfiguration|
  |Add a binding whose matches are a strict superset of an existing binding|Add success, more specific binding takes priority|

- config dhcp_server ipv4 binding update \<vlan_interface\> \<binding_name\> [--match \<match_list\>] [--range \<ip_range_list\> | \<ip_list\>]

  |Case Description|Expected res|
  |:-|:-|
  |Update --match of existing binding|Update success|
  |Update ip_list of existing binding|Update success|
  |Update --range of existing binding|Update success|
  |Update binding from ip_list to --range|Update success, 'ips' is replaced by 'ranges'|
  |Update with both ip_list and --range|Update failed because 'ips' and 'ranges' cannot both exist|
  |Update binding not exist|Update failed|
  |Update with vlan_interface not exist|Update failed|
  |Update with match not exist|Update failed because match not exist|
  |Update without any option|Update failed because nothing to update|
  |Update to a binding that becomes ambiguous with an existing binding|Update failed because binding is ambiguous|

- config dhcp_server ipv4 binding del \<vlan_interface\> \<binding_name\>

  |Case Description|Expected res|
  |:-|:-|
  |Delete valid binding|Delete success|
  |Delete binding not exist|Delete failed|
  |Delete with vlan_interface not exist|Delete failed|

- config dhcp_server ipv4 add --mode \<mode\> [--dup_gw_nm] [--lease_time \<lease_time\>] [--gateway \<gateway\>] [--netmask \<netmask\>] \<dhcp_interface\>

  |Case Description|Expected res|
  |:-|:-|
  |Add with --dup_gw_nm, --mode=MATCH|Add success, state is disabled|
  |Add with --mode=PORT|Add success, existing behavior is unchanged|
  |Add with --mode=DYNAMIC|Add failed because mode not supported|
  |Add with --mode=match|Add failed because mode is case sensitive|

- config dhcp_server ipv4 update --mode \<mode\> [--dup_gw_nm] [--lease_time \<lease_time\>] [--gateway \<gateway\>] [--netmask \<netmask\>] \<dhcp_interface\>

  |Case Description|Expected res|
  |:-|:-|
  |Update --mode from PORT to MATCH|Update success|
  |Update --mode from MATCH to PORT|Update success|
  |Update --mode to MATCH while no binding is configured for this interface|Update success with warning that no binding is configured|
  |Update --mode to MATCH while DHCP_SERVER_IPV4_PORT entries exist for this interface|Update success with warning that port entries are ignored under MATCH mode|
  |Update --mode to PORT while DHCP_SERVER_IPV4_BINDING entries exist for this interface|Update success with warning that bindings are ignored under PORT mode|
  |Update --mode=DYNAMIC|Update failed because mode not supported|

### Clear CLI

- sonic-clear dhcp_server ipv4 lease \<dhcp_interface\> [\<ip_address\>] [--mac \<mac\>] [--all]

  |Case Description|Expected res|
  |:-|:-|
  |Clear an existing lease by IP address|Lease is deleted and the corresponding DHCP_SERVER_IPV4_LEASE entry is removed from State DB|
  |Clear an existing lease by MAC address|Lease is deleted and the corresponding DHCP_SERVER_IPV4_LEASE entry is removed from State DB|
  |Clear all leases of specified dhcp_interface with --all|All leases of that interface are deleted, leases of other interfaces are retained|
  |Show lease after clear|Cleared lease is no longer displayed by show dhcp_server ipv4 lease|
  |Clear lease for an IP address that has no lease|Clear failed|
  |Clear lease for a MAC address that has no lease|Clear failed|
  |Clear lease of dhcp_interface not exist|Clear failed|
  |Clear lease without any selector|Clear failed|
  |Clear lease with more than one selector|Clear failed|
  |Clear lease of an IP address that is leased on a different dhcp_interface|Clear failed, lease is retained|
  |Clear lease while dhcp_server feature is disabled|Clear failed|
  |Clear lease while no lease is present on the interface|Clear failed|


### Show CLI

- show dhcp_server ipv4 match [\<match_name\>]

  |Case Description|Expected res|
  |:-|:-|
  |Show all matches while multiple matches are configured|All matches are displayed with Match Name, Type and Value columns|
  |Show specified match|Only the specified match is displayed|
  |Show specified match not exist|Show failed|
  |Show while no match is configured|Empty table is displayed|

- show dhcp_server ipv4 binding [\<dhcp_interface\>]

  |Case Description|Expected res|
  |:-|:-|
  |Show all bindings while multiple bindings are configured|All bindings of all interfaces are displayed|
  |Show bindings of specified dhcp_interface|Only bindings of the specified interface are displayed|
  |Show bindings of dhcp_interface not exist|Show failed|
  |Show binding configured with multiple matches|Matches column displays all match names, comma separated|
  |Show binding configured with ip_list|Bind column displays the ips|
  |Show binding configured with --range|Bind column displays the range names|
  |Show while no binding is configured|Empty table is displayed|

## Test Plan

Detailed test cases will be covered in a separate test plan document in [sonic-mgmt](https://github.com/sonic-net/sonic-mgmt).
