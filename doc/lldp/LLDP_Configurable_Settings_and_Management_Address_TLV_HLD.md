# LLDP Configurable Settings and Management Address TLV <!-- omit in toc -->

## Table of Contents <!-- omit in toc -->

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1. sonic-lldp YANG model](#71-sonic-lldp-yang-model)
  - [7.2. lldpmgrd](#72-lldpmgrd)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
  - [9.1. CLI/YANG Model Enhancements](#91-cliyang-model-enhancements)
        - [9.1.1. Config CLI additions](#911-config-cli-additions)
        - [9.1.2. Show CLI additions](#912-show-cli-additions)
  - [9.2. Config DB Enhancements](#92-config-db-enhancements)
  - [9.3. Configuration Examples](#93-configuration-examples)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1. Unit Test cases](#131-unit-test-cases)
  - [13.2. System Test cases](#132-system-test-cases)
- [14. Open/Action Items](#14-openaction-items)

## 1. Revision

| Rev | Date       | Author      | Change Description                                                      |
| --- | ---------- | ----------- | ----------------------------------------------------------------------- |
| 0.1 | 09/22/2026 | Yash Pandit | Configurable LLDP global/per-port settings and Management Address TLV   |

## 2. Scope

This HLD introduces LLDP configuration and management enhancements across YANG model, LLDP control-plane handling, and CLI surfaces. The scope covers runtime application of global and per-port LLDP configuration from CONFIG_DB and introduces a new management-address source selector (`mgmt_addr_interface`).

## 3. Definitions/Abbreviations

| Term      | Definition                                                       |
| --------- | ---------------------------------------------------------------- |
| TLV       | Type-Length-Value element carried in an LLDP PDU                 |
| lldpcli   | CLI client used to configure a running `lldpd` instance          |
| lldpmgrd  | SONiC daemon that translates CONFIG_DB changes into `lldpcli` commands |

## 4. Overview

This HLD adds operator-facing LLDP configuration control for global and per-port behavior, with live effect on advertised LLDP information. It also adds `mgmt_addr_interface`, which lets operators select the interface used as the Management Address TLV source.

## 5. Requirements

- Configurable global LLDP timers (`hello_time`, `multiplier`); advertised TTL follows those timers.
- Global and per-port admin status (`enabled`, `mode`); per-port always overrides global.
- Configurable `system_name` and `system_description`.
- Configurable Management Address TLV source via `mgmt_addr_interface` (Loopback, Ethernet, VLAN, PortChannel, management port).
- At most one IPv4 and one IPv6 address from the selected interface.

## 6. Architecture Design

No SONiC macro-architecture change is introduced. This update is confined to existing `lldpmgrd` control-plane handling for `LLDP|GLOBAL`, `LLDP_PORT|<ifname>`, and `mgmt_addr_interface`, applying configured values to `lldpd` runtime.

## 7. High-Level Design

### 7.1. sonic-lldp YANG model

**One new leaf** is added to `LLDP|GLOBAL`:

```yang
leaf mgmt_addr_interface {
    must "not(../supp_mgmt_address_tlv = 'true')" {
        error-message "mgmt_addr_interface cannot be set when supp_mgmt_address_tlv is true";
    }
    type union {
        type leafref { path "/lointf:sonic-loopback-interface/.../LOOPBACK_INTERFACE_LIST/name"; }
        type leafref { path "/prt:sonic-port/.../PORT_LIST/name"; }
        type leafref { path "/vlan:sonic-vlan/.../VLAN_LIST/name"; }
        type leafref { path "/lag:sonic-portchannel/.../PORTCHANNEL_LIST/name"; }
        type leafref { path "/mgmtprt:sonic-mgmt_port/.../MGMT_PORT_LIST/name"; }
    }
    description "Interface whose IP is advertised in the LLDP Management Address TLV.";
}
```

The union of interface-family leafrefs keeps source-interface validation explicit across supported namespaces at commit time.

### 7.2. lldpmgrd

`lldpmgrd` subscribes to LLDP configuration tables and related interface/hostname tables, then reconciles runtime `lldpd` state through `lldpcli`.

#### Runtime behavior

- `LLDP|GLOBAL` updates are applied live, including timers (`hello_time`, `multiplier`) and TLV suppression controls.
- Advertised TTL follows `hello_time × multiplier`.
- Effective lldpd status is derived from `enabled` + `mode`: `enabled=false` → `disabled`, `mode=RECEIVE` → `rx-only`, `mode=TRANSMIT` → `tx-only`, omitted `mode` → `rx-and-tx`. Per-port `LLDP_PORT|<ifname>` overrides global settings.
- When an `LLDP_PORT|<ifname>` entry is removed, that interface falls back to current global status.
- `supp_mgmt_address_tlv` and `supp_system_capabilities_tlv` toggle Management Address and System Capabilities TLV advertisement, respectively.
- `mgmt_addr_interface` is valid only when `supp_mgmt_address_tlv=false`; when set, its interface IP is advertised, and if no IP exists, `!*` is applied so no management address is advertised.
- At most one IPv4 and one IPv6 address from that interface are advertised. The IPv4 is the first one configured; the IPv6 is a non-link-local address in preference to a link-local one.
- `system_name` override takes precedence over DEVICE_METADATA hostname and reverts to current hostname when removed.

## 8. SAI API

No SAI API changes. LLDP is a control-plane protocol handled entirely by `lldpd`/`lldpmgrd`; there is no ASIC programming involved.

## 9. Configuration and Management

### 9.1. CLI/YANG Model Enhancements

The YANG change is the new `mgmt_addr_interface` leaf described in §7.1.

In addition, this feature introduces LLDP config and show CLI coverage in sonic-utilities, backed by YANG validation before writing CONFIG_DB.

#### 9.1.1. Config CLI additions

Global LLDP configuration commands under `config lldp global`:

- `config lldp global hello-time <value>`
- `config lldp global multiplier <value>`
- `config lldp global system-name <value>`
- `config lldp global system-description <value>`
- `config lldp global enabled <true|false>`
- `config lldp global mode <RECEIVE|TRANSMIT>`
- `config lldp global supp-mgmt-address-tlv <true|false>`
- `config lldp global supp-system-capabilities-tlv <true|false>`
- `config lldp global mgmt-addr-interface <ifname>`

Per-port LLDP configuration commands under `config lldp-port`:

- `config lldp-port add <ifname> [--enabled <true|false>] [--mode <RECEIVE|TRANSMIT>]`
- `config lldp-port update <ifname> [--enabled <true|false>] [--mode <RECEIVE|TRANSMIT>]`
- `config lldp-port delete <ifname>`

#### 9.1.2. Show CLI additions

LLDP show commands include two config-oriented views:

- `show lldp global` (renders `LLDP|GLOBAL` fields)
- `show lldp port [<ifname>]` (renders `LLDP_PORT` entries)

Expected output:

```text
$ show lldp global
Field                             Value
-------------------------------  ---------
Hello Time (seconds)              5
Multiplier                        4
System Name                       N/A
System Description                N/A
Mgmt Address Interface            Loopback0
Suppress Mgmt Address TLV         N/A
Suppress System Capabilities TLV  N/A
Enabled                           N/A
Mode                              N/A
```

```text
$ show lldp port Ethernet8
Interface    Enabled    Mode
-----------  ---------  ------
Ethernet8    false      N/A
```

N/A means the leaf is unset in CONFIG_DB.

### 9.2. Config DB Enhancements

This HLD introduces one schema addition in CONFIG_DB:

- `LLDP|GLOBAL|mgmt_addr_interface`
    - Type: union of interface-family leafrefs (Loopback, Ethernet, VLAN, PortChannel, management port)
    - Constraint: cannot be set when `supp_mgmt_address_tlv=true`
    - Effect: selected interface IP is used for Management Address TLV advertisement

### 9.3. Configuration Examples

```json
{
    "LLDP": {
        "GLOBAL": {
            "hello_time": "5",
            "multiplier": "3",
            "system_name": "my-switch",
            "system_description": "Rack-4 ToR",
            "mgmt_addr_interface": "Loopback0"
        }
    },
    "LLDP_PORT": {
        "Ethernet8": { "enabled": "false" },
        "Ethernet0": { "mode": "RECEIVE" }
    }
}
```

- TTL advertised = 5 × 3 = 15 seconds.
- `Ethernet8` is `disabled`; `Ethernet0` is `rx-only` — both override the global `rx-and-tx` (no `mode` key).
- `mgmt_addr_interface=Loopback0` advertises Loopback0's IPv4/IPv6 in the Management Address TLV. If Loopback0 has no IP, lldpmgrd applies management IP pattern `!*`, so no Management Address TLV address is advertised until an IP is added.

## 10. Warmboot and Fastboot Design Impact

No impact on warmboot or fastboot.

### Warmboot and Fastboot Performance Impact

No additional CPU/IO cost in the boot-critical chain.

## 11. Memory Consumption

No material memory impact is introduced by this HLD.

## 12. Restrictions/Limitations

None.

## 13. Testing Requirements/Design

### 13.1. Unit Test cases

- Validate `mgmt_addr_interface` leafref and the `must` constraint with `supp_mgmt_address_tlv`.
- Reject out-of-range hello_time, multiplier, and invalid mode; CONFIG_DB unchanged.
- Apply enabled/mode, per-port override, TTL, management-address selection, and system_name vs hostname.

### 13.2. System Test cases

- Per-port disable ages out only that peer; re-enable restores it.
- Global disable ages out all peers; re-enable restores them.
- Per-port enabled false then true: interface admin status goes from rx-and-tx to disabled and back to rx-and-tx.
- Global TRANSMIT and RECEIVE set admin status on all ports that have no per-port override.
- Per-port TRANSMIT and RECEIVE affect only that port.
- Per-port enabled beats global disabled; per-port disabled beats global enabled.
- Delete per-port config when global is default; the port returns to rx-and-tx.
- Delete per-port config when global is disabled; the port stays disabled.
- Peer receives chassis ID, port ID, port description, system name, and system description; system name matches DUT hostname.
- system_name override survives hostname change.
- `mgmt_addr_interface` set to a loopback advertises that loopback's addresses.
- `mgmt_addr_interface` set to the management port advertises the management-port IP.
- A loopback with only IPv6 is advertised when selected as `mgmt_addr_interface`.
- Interface with no IP does not advertise a management address.
- PortChannel, VLAN SVI, and routed Ethernet each advertise that interface's IPv4 and IPv6.
- Non-link-local IPv6 is preferred over link-local when both are present.
- Link-local IPv6 is advertised when it is the only IPv6.
- Several addresses per family yield exactly one IPv4 and one IPv6 on the wire.
- IPv4-mapped IPv6 occupies the IPv6 slot; the real IPv4 is still advertised.
- IPv4-mapped IPv6 alone is advertised as IPv6.
- Unknown interface for `mgmt_addr_interface` is rejected.
- Advertised TTL equals hello_time × multiplier.
- LLDPDU send interval equals `hello_time`.
- With a reduced hello_time and multiplier, peer age-out is within advertised TTL and re-learn is within two hello intervals.
- After `docker restart lldp`, running state still has configured hello_time, multiplier, system_name, system_description, mgmt_addr_interface, and a per-port override (not defaults).
- The same configured profile survives `config save` and `config reload`.
- The same configured profile survives cold reboot.
- Suppress and restore the System Capabilities TLV on the wire.
- Suppress and restore the Management Address TLV on the wire.

## 14. Open/Action Items

None.

