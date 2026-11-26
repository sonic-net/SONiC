# LACP Activity Mode (Active / Passive) for PortChannels — HLD

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions and Abbreviations](#3-definitions-and-abbreviations)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [Architecture](#6-architecture)
7. [High-Level Design](#7-high-level-design)
8. [Configuration and Management](#8-configuration-and-management)
9. [Error Handling](#9-error-handling)
10. [Serviceability and Debug](#10-serviceability-and-debug)
11. [Warm Boot / Upgrade](#11-warm-boot--upgrade)
12. [Restrictions and Limitations](#12-restrictions-and-limitations)
13. [Dependencies](#13-dependencies)
14. [Testing](#14-testing)

## 1. Revision

| Rev | Date       | Author                  | Change Description |
|-----|------------|-------------------------|--------------------|
| 0.1 | 2026-11-25 | Varuna Mayya (Nokia)    | Initial version    |

## 2. Scope

This document describes support for configuring the LACP activity mode
(active or passive) of a PortChannel in SONiC.

In scope:

| Repository | Component | Change |
|------------|-----------|--------|
| sonic-buildimage | `src/sonic-yang-models` | New `active` leaf in `PORTCHANNEL` (`sonic-portchannel.yang`), YANG tests, `Configuration.md` |
| sonic-swss | `cfgmgr/teammgr.cpp`, `cfgmgr/teammgr.h` | teammgrd reads `active` and passes it to the teamd lacp runner; unit and VS tests |
| sonic-utilities | `config/main.py` | `--lacp-mode active\|passive` option on `config portchannel add`; unit tests, `Command-Reference.md` |

Out of scope:

- OpenConfig `/lacp/interfaces/interface/config/lacp-mode` support in
  sonic-mgmt-common. This is covered by the OpenConfig LACP HLD and
  implementation, which map this leaf to the `active` field defined here.

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| LACP | Link Aggregation Control Protocol (IEEE 802.1AX) |
| LACPDU | LACP Protocol Data Unit |
| LAG / PortChannel | Link Aggregation Group |
| Activity | 802.1AX `LACP_Activity` bit of the actor/partner port state. 1 = active, 0 = passive |
| Active mode | The port transmits LACPDUs periodically, regardless of the partner |
| Passive mode | The port transmits LACPDUs only after it receives LACPDUs from the partner |
| teamd | The libteam daemon that runs the LACP state machines for each PortChannel |
| teammgrd | SWSS daemon that creates and configures teamd instances from CONFIG_DB |

## 4. Overview

IEEE 802.1AX allows each LACP port to operate in active or passive mode. A link
aggregates if at least one end is active; if both ends are passive, no LACPDUs
are exchanged and the LAG does not come up.

Passive mode is commonly used on devices that should never initiate LACP, for
example on ports facing servers or third-party switches that are configured as
active, or to avoid sending LACPDUs on ports that are not yet cabled to an LACP
partner.

The teamd lacp runner already supports both modes through the runner option
`"active": true|false`, and SONiC already exports the running value to
STATE_DB (`LAG_TABLE|<lag>` field `runner.active`), which
`show interfaces portchannel` displays as `LACP(A)` or `LACP(I)`. However,
teammgrd always starts teamd with `"active": true`, and there is no CONFIG_DB
field, YANG leaf or CLI option to select passive mode.

This feature adds the missing configuration path.

## 5. Requirements

### 5.1 Functional

1. The LACP activity mode can be configured per PortChannel as active or passive.
2. The default mode is active. PortChannels configured without the new field
   behave exactly as today.
3. The mode is applied when the PortChannel (teamd instance) is created.
4. The mode is configurable through CONFIG_DB and the `config portchannel add`
   CLI.
5. The running mode is visible in STATE_DB and in existing show commands.

### 5.2 Non-functional

1. No change to SAI, orchagent or syncd.
2. No change to libteam / teamd.
3. Backward compatible with existing `config_db.json` files.

## 6. Architecture

No new components are added. The existing PortChannel configuration flow is
extended with one field.

```
 config portchannel add          config_db.json / GCU / mgmt-framework
          |                                   |
          v                                   v
 +---------------------------------------------------------+
 | CONFIG_DB  PORTCHANNEL|PortChannelN  active: true|false  |
 +---------------------------------------------------------+
          |
          v
 teammgrd (sonic-swss)  -- builds teamd JSON config -->  teamd -t PortChannelN
          "runner": { "name": "lacp", "active": <true|false>, ... }
                                                              |
                                                              v
 tlm_teamd  <-- teamdctl state dump (runner.active) ----------+
          |
          v
 STATE_DB  LAG_TABLE|PortChannelN  runner.active: true|false
          |
          v
 show interfaces portchannel   ->   LACP(A) / LACP(I)
```

## 7. High-Level Design

### 7.1 CONFIG_DB schema

New optional field in the `PORTCHANNEL` table:

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `active` | `true` / `false` | `true` (when absent) | LACP activity mode. `true` = active, `false` = passive |

Example:

```json
"PORTCHANNEL": {
    "PortChannel0001": {
        "admin_status": "up",
        "mtu": "9100",
        "lacp_key": "auto",
        "fast_rate": "false",
        "active": "false"
    }
}
```

The field name `active` was chosen to match the teamd runner option and the
existing STATE_DB field `runner.active`.

### 7.2 YANG model (`sonic-portchannel.yang`)

A new revision and leaf are added to `PORTCHANNEL_LIST`:

```yang
revision 2026-11-25 {
    description "Add LACP activity mode (active/passive)";
}

leaf active {
    description
        "LACP activity mode. When true, the PortChannel runs LACP in
         active mode and always transmits LACPDUs. When false, it runs
         in passive mode and transmits LACPDUs only after receiving
         them from the partner. When unset, active mode is used.";
    type stypes:boolean_type;
}
```

### 7.3 teammgrd (sonic-swss)

In `TeamMgr::doLagTask()`, the `active` field is parsed in the same way as
`fast_rate`:

```cpp
bool active = true;
...
else if (fvField(i) == "active")
{
    active = fvValue(i) == "true";
}
```

The value is passed to `TeamMgr::addLag()`, which uses it in the teamd
configuration instead of the hard-coded `true`:

```cpp
conf << "'{\"device\":\"" << alias << "\","
     << "\"hwaddr\":\"" << mac_boot.to_string() << "\","
     << "\"runner\":{"
     << "\"active\":" << (active ? "true" : "false") << ","
     << "\"name\":\"lacp\"";
```

Like `min_links`, `fallback` and `fast_rate`, `active` is applied when the
teamd instance is created.

### 7.4 STATE_DB and telemetry

No change. `tlm_teamd` already reads `runner.active` from the teamd state dump
and writes it to `STATE_DB LAG_TABLE|<lag>`.

### 7.5 CLI (sonic-utilities)

A new option is added to `config portchannel add`. The CLI always writes the
`active` field, so CONFIG_DB shows the configured mode explicitly.

| CLI option | CONFIG_DB `active` |
|------------|--------------------|
| *(not given)* | `true` |
| `--lacp-mode active` | `true` |
| `--lacp-mode passive` | `false` |

The option value is case-insensitive.

## 8. Configuration and Management

### 8.1 CLI

```
config portchannel add <portchannel_name> [--min-links <num_min_links>]
                       [--fallback (true | false)] [--fast-rate (true | false)]
                       [--lacp-mode (active | passive)]
```

Example:

```
admin@sonic:~$ sudo config portchannel add PortChannel0012 --lacp-mode passive
admin@sonic:~$ sudo config portchannel member add PortChannel0012 Ethernet0
```

Existing show command (no change):

```
admin@sonic:~$ show interfaces portchannel
Flags: A - active, I - inactive, Up - up, Dw - down, N/A - Not Available,
       S - selected, D - deselected, * - not synced
  No.  Team Dev         Protocol     Ports
-----  ---------------  -----------  -------------
   12  PortChannel0012  LACP(I)(Up)  Ethernet0(S)
```

### 8.2 config_db.json

The `active` field can be set directly in `config_db.json` (see
[7.1](#71-config_db-schema)) and applied with `config reload` or at boot.

### 8.3 Management framework (REST / gNMI)

The OpenConfig leaf
`/lacp/interfaces/interface/config/lacp-mode` (`ACTIVE` / `PASSIVE`) will map to
`PORTCHANNEL|<lag>` field `active` (`true` / `false`). The read-only state leaf
`/lacp/interfaces/interface/state/lacp-mode` maps to `runner.active` in STATE_DB.

## 9. Error Handling

| Condition | Behavior |
|-----------|----------|
| Invalid value written through the CLI | Rejected by Click (`Invalid value for '--lacp-mode'`) |
| Invalid value written through a YANG-validated path (GCU, mgmt-framework) | Rejected by YANG validation (`boolean_type` pattern) |
| Field absent | Active mode (existing behavior) |
| Any value other than lowercase `true` written directly to CONFIG_DB | Treated as passive, same as `fast_rate` parsing. The CLI and the management framework always write lowercase `true` / `false`. |
| Both ends configured passive | No LACPDUs exchanged; members stay deselected and the LAG stays down. This is expected 802.1AX behavior. |

## 10. Serviceability and Debug

- teammgrd logs the parsed value at INFO level: ``Get active `true|false` ``, and
  the full teamd configuration: `Port channel <lag> teamd configuration: ...`.
- `teamdctl <lag> state dump` shows `"runner": { "active": true|false, ... }`.
- `redis-cli -n 6 HGET "LAG_TABLE|<lag>" runner.active` shows the running mode.
- `show interfaces portchannel` shows `LACP(A)` or `LACP(I)`.

## 11. Warm Boot / Upgrade

- Warm boot: teammgrd builds the same teamd configuration (including `active`)
  from CONFIG_DB and starts teamd with `-w -o`. No change in behavior.
- Upgrade from an image without this feature: existing PortChannels have no
  `active` field and continue in active mode. No db_migrator change is needed.
- Downgrade: older images ignore the `active` field and run in active mode.

## 12. Restrictions and Limitations

1. As with the other LACP parameters, the mode is applied when the PortChannel
   is created.
2. If both link partners are passive, the LAG does not come up.
3. The mode is per PortChannel; all members of a PortChannel use the same mode.

## 13. Dependencies

- teamd lacp runner support for the `active` option (already present in
  libteam).
- `runner.active` export in `tlm_teamd` (already present in sonic-swss).

Related work:

| Item | Link |
|------|------|
| OpenConfig LACP HLD | [SONiC#2664](https://github.com/sonic-net/SONiC/pull/2664) |
| OpenConfig LACP implementation | [sonic-mgmt-common#298](https://github.com/sonic-net/sonic-mgmt-common/pull/298) |

## 14. Testing

### 14.1 Unit tests

| Repository | Test | Coverage |
|------------|------|----------|
| sonic-buildimage | `PORT_CHANNEL_VALID_ACTIVE_PASSIVE` | `active: "false"` is accepted |
| sonic-buildimage | `PORT_CHANNEL_INVALID_ACTIVE` | Invalid value is rejected by the `boolean_type` pattern |
| sonic-buildimage | `sample_config_db.json` | Full config validation with `active` set |
| sonic-swss | `teammgr_ut`: `testAddLagLacpModePassive` | `active: false` produces `"active":false` in the teamd command |
| sonic-swss | `teammgr_ut`: `testAddLagLacpModeActive` | `active: true` produces `"active":true` |
| sonic-swss | `teammgr_ut`: `testAddLagLacpModeDefaultsToActive` | Field absent produces `"active":true` |
| sonic-utilities | `test_add_portchannel_with_lacp_mode_adhoc_validation` | `active` / `passive` in any case writes `true` / `false` |
| sonic-utilities | `test_portchannel_lacp_mode_default_active` | No option writes `active: true` |
| sonic-utilities | `test_add_portchannel_with_invalid_lacp_mode` | Invalid values are rejected |

### 14.2 VS tests (sonic-swss)

`test_portchannel.py::test_Portchannel_lacp_mode`, parametrized for field
absent, `false` and `true`: creates a PortChannel with a member and verifies
`runner.active` in `teamdctl <lag> state dump`.

### 14.3 System tests

| # | Setup | Expected result |
|---|-------|-----------------|
| 1 | DUT active, peer active | LAG up, `LACP(A)` on DUT |
| 2 | DUT passive, peer active | LAG up, `LACP(I)` on DUT |
| 3 | DUT active, peer passive | LAG up |
| 4 | DUT passive, peer passive | LAG down; no LACPDUs transmitted by DUT (packet capture) |
| 5 | DUT passive, no LACPDU from peer | DUT does not transmit LACPDUs |
| 6 | `config_db.json` without `active`, `config reload` | LAG in active mode |
| 7 | Warm reboot with a passive LAG | LAG stays up, mode preserved |
