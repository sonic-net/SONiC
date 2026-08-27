# Resolve-via-default Control for Nexthop Tracking

## Table of Content 

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions/Abbreviations](#3-definitionsabbreviations)
4. [Overview](#4-overview)
   - 4.1 [Background](#41-background)
   - 4.2 [Problem](#42-problem)
   - 4.3 [Solution](#43-solution)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
   - 6.1 [Component Flow](#61-component-flow)
   - 6.2 [Boot Template Selection](#62-boot-template-selection)
   - 6.3 [Changed Components](#63-changed-components)
7. [High-Level Design](#7-high-level-design)
   - 7.1 [Boot-Time Rendering](#71-boot-time-rendering)
   - 7.2 [Runtime Apply in Traditional Mode](#72-runtime-apply-in-traditional-mode)
   - 7.3 [Runtime Apply in FRR Management Mode](#73-runtime-apply-in-frr-management-mode)
   - 7.4 [Absent Field and Row Delete](#74-absent-field-and-row-delete)
8. [SAI API](#8-sai-api)
9. [Configuration and management](#9-configuration-and-management)
   - 9.1 [Manifest](#91-manifest-if-the-feature-is-an-application-extension)
   - 9.2 [CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
   - 9.3 [Config DB Enhancements](#93-config-db-enhancements)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
    - 10.1 [Warmboot and Fastboot Performance Impact](#101-warmboot-and-fastboot-performance-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions/Limitations](#12-restrictionslimitations)
13. [Testing Requirements/Design](#13-testing-requirementsdesign)
    - 13.1 [Unit Test cases](#131-unit-test-cases)
    - 13.2 [System Test cases](#132-system-test-cases)
14. [Open/Action items](#14-openaction-items---if-any)

### 1. Revision  

| Rev | Date       | Author             | Description     |
|-----|------------|--------------------|-----------------|
| 0.1 | 2026-08-17 | Maheeppartap Singh | Initial version |

### 2. Scope  

This document describes a CONFIG_DB control for nexthop resolution through the default route in SONiC.

Zebra can resolve a tracked nexthop through the default route. The default route is `0.0.0.0/0` for IPv4 and `::/0` for IPv6. The zebra commands `ip nht resolve-via-default` and `ipv6 nht resolve-via-default` control this behavior. Before this design, SONiC wrote these two commands into a boot template as fixed text. An operator could not change them from CONFIG_DB.

### 3. Definitions/Abbreviations 

| Term | Definition |
|------|------------|
| FRR | FRRouting. SONiC uses this software suite for the routing control plane. |
| zebra | The FRR daemon that manages routes and programs the kernel routing table. |
| `vtysh` | The FRR command-line shell. An operator uses it to send commands to the FRR daemons. |
| `bgpcfgd` | The legacy SONiC daemon that translates CONFIG_DB rows into FRR configuration. |
| `frrcfgd` | The newer SONiC daemon that translates CONFIG_DB rows into FRR commands. |
| `frr_mgmt_framework_config` | A field in the `DEVICE_METADATA` table. It selects `frrcfgd` when the value is `true`. It selects `bgpcfgd` when the value is `false`. |
| Traditional mode | The mode in which `bgpcfgd` configures FRR. |
| FRR Management mode | The mode in which `frrcfgd` configures FRR. |
| BGP monitor | A BGP peer that receives routes for monitoring. This peer is not directly connected to the switch. |
| Nexthop | The next hop that the switch uses to reach a destination. A nexthop is an IP address, an interface, or both. |
| Nexthop tracking (NHT) | The zebra function that monitors the reachability of a nexthop. Zebra informs its clients when the reachability changes. |
| Default route | The route that matches all destinations. It is `0.0.0.0/0` for IPv4 and `::/0` for IPv6. |
| Resolve-via-default | The zebra behavior that permits a tracked nexthop to resolve through the default route. |
| VRF | Virtual Routing and Forwarding instance. |
| AFI | Address Family Identifier. It is `ipv4` or `ipv6`. |
| CONFIG_DB | The SONiC configuration database. SONiC applications read their configuration from this database. |
| `sonic-cfggen` | The SONiC tool that renders configuration files from CONFIG_DB. |
| `NEXTHOP_TRACKING` | The CONFIG_DB table that holds the nexthop tracking settings. |
| YANG | The data modeling language that SONiC uses to validate the content of CONFIG_DB. |

### 4. Overview 

#### 4.1. Background

Zebra tracks the reachability of each nexthop. A BGP session starts only after zebra resolves the address of the peer. A BGP monitor peer is not directly connected, so zebra cannot resolve it from a connected route. The session then stays in the "waiting for NHT" state. An operator can add a static route for each such peer, or an operator can permit resolution through the default route.

SONiC added the commands `ip nht resolve-via-default` and `ipv6 nht resolve-via-default` to the zebra boot template for this reason.

#### 4.2. Problem

SONiC wrote the two commands into the boot template as fixed text. The commands applied to every nexthop in the default VRF. CONFIG_DB held no field for them. An operator could change the commands with `vtysh`, but the change did not stay in place. SONiC renders the zebra configuration files again at each configuration reload, and the new files replace the change.

Resolution through the default route is not correct for every network. A nexthop that has no specific route still resolves through the default route. Zebra keeps this nexthop in the route, and the switch sends the traffic through the default route. The traffic does not move to the other nexthops of the same route.

#### 4.3. Solution

This design adds a `resolve_via_default` field to the `NEXTHOP_TRACKING` table. Each row of the table holds one VRF and one address family. An operator therefore controls each VRF and each address family separately.

The default value of the field is `true`. This value keeps the behavior of the earlier releases. An operator sets the field to `false` to stop resolution through the default route for that VRF and that address family.

SONiC applies the field in two places:

- At boot, `sonic-cfggen` renders the zebra configuration files from CONFIG_DB.
- At runtime, `bgpcfgd` or `frrcfgd` sends the equivalent command to FRR when the row changes.

### 5. Requirements

1. CONFIG_DB shall hold a field that controls resolution through the default route.
2. The field shall apply to one VRF and one address family. An operator shall control each VRF and each address family separately.
3. The YANG model shall reject a value that is not a boolean.
4. The switch shall keep the behavior of the earlier releases when the field is absent.
5. SONiC shall render the correct zebra command at boot from the value in CONFIG_DB.
6. SONiC shall send the correct command to FRR when an operator changes the value on a running switch.
7. A change shall take effect without a restart of FRR.
8. The design shall work in traditional mode and in FRR Management mode.
9. The design shall not change the `neighbor_tracking` field of the `NEXTHOP_TRACKING` table.
10. The design shall not change the resolution logic in zebra. The design sets only the FRR commands that FRR already has.

### 6. Architecture Design 

This design does not change the SONiC architecture. It is a built-in SONiC feature, and it is not a SONiC Application Extension. The `NEXTHOP_TRACKING` table, the user-VRF boot template, and the two runtime translators are already present for the `neighbor_tracking` field. This design adds one field to that table and extends each of those components. It also makes the default-VRF boot template read the table for the first time.

#### 6.1. Component Flow

```
                    ┌──────────────────────────────────────────────┐
                    │                  CONFIG_DB                   │
                    │                                              │
                    │  NEXTHOP_TRACKING|<vrf>|<afi>                │
                    │      resolve_via_default = true | false      │
                    └───────┬──────────────────────────┬───────────┘
                            │                          │
                boot        │                          │  row change
                            ▼                          ▼
            ┌───────────────────────────┐  ┌───────────────────────────┐
            │ boot path: sonic-cfggen   │  │ runtime path              │
            │                           │  │                           │
            │ default VRF:              │  │ traditional mode:         │
            │   zebra.interfaces.conf.j2│  │   bgpcfgd.NhtMgr          │
            │                           │  │   zebra.nht.db.conf.j2    │
            │ user VRFs:                │  │                           │
            │   zebra.nht.conf.j2       │  │ FRR Management mode:      │
            │   (FRR Management mode)   │  │   frrcfgd.nht_handler     │
            └───────────────┬───────────┘  └───────────┬───────────────┘
                            │                          │
              rendered file │                          │ vtysh
              read at start │                          │
                            ▼                          ▼
                    ┌──────────────────────────────────────────────┐
                    │                     FRR                      │
                    │   ┌──────────────────────────────────────┐   │
                    │   │                zebra                 │   │
                    │   │                                      │   │
                    │   │   [no] ip   nht resolve-via-default  │   │
                    │   │   [no] ipv6 nht resolve-via-default  │   │
                    │   └──────────────────────────────────────┘   │
                    └──────────────────────────────────────────────┘
```

#### 6.2. Boot Template Selection

`docker_init.sh` renders `gen_frr.conf.j2`. That template selects the file set from the value of `frr_mgmt_framework_config`. This design supports two combinations of `frr_mgmt_framework_config` and `docker_routing_config_mode`. The table below shows the file that holds the nexthop tracking configuration for each combination.

| Mode | `frr_mgmt_framework_config` | `docker_routing_config_mode` | Rendered file | Default VRF | User VRF |
|---|---|---|---|---|---|
| FRR Management mode | `true` | `unified` | `frr.conf` from the `frrcfgd` template set | Yes | Yes |
| Traditional mode | `false` | `separated` | `zebra.conf` | Yes | No |

#### 6.3. Changed Components

| Component | File | Change |
|---|---|---|
| YANG model | `sonic-yang-models/yang-models/sonic-nexthop-tracking.yang` | Add the `resolve_via_default` leaf. |
| Boot template, default VRF | `dockers/docker-fpm-frr/frr/zebra/zebra.interfaces.conf.j2` | Read the field and render the command for the default VRF. |
| Boot template, user VRFs | `dockers/docker-fpm-frr/frr/zebra/zebra.nht.conf.j2` | Read the field and render the command inside each `vrf` block. |
| Runtime translator, traditional mode | `sonic-bgpcfgd/bgpcfgd/managers_nht.py` | Extend `NhtMgr` to read the field. |
| Runtime template, traditional mode | `dockers/docker-fpm-frr/frr/zebra/zebra.nht.db.conf.j2` | Render the command for the default VRF. |
| Runtime translator, FRR Management mode | `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | Extend `nht_handler` to read the field. |

This design adds no new file. Each change extends a component that already exists. `zebra.interfaces.conf.j2` is the only component that reads the `NEXTHOP_TRACKING` table for the first time.

### 7. High-Level Design 

#### 7.1. Boot-Time Rendering

`sonic-cfggen` reads the `NEXTHOP_TRACKING` table and renders the zebra configuration files. The table key is a composite key of a VRF name and an AFI. `sonic-cfggen` converts such a key into a tuple, so both templates accept a key as a string or as a tuple.

Two templates render the field, and each template holds a different structure.

`zebra.interfaces.conf.j2` renders the default VRF. The template reads the rows `default|ipv4` and `default|ipv6`, and it emits one line for each AFI.

`zebra.nht.conf.j2` renders the user VRFs. The template collects the rows for each VRF, and it then emits one `vrf` block for each VRF. Each block holds the lines for both AFIs of that VRF.

Both templates use the same rule for the value. The start value is `true`. A value of `false` emits the negative form. Any other state emits the affirmative form, which keeps the behavior of the earlier releases.

For example, on a switch with `resolve_via_default` set to `false` on `default|ipv4`, and with no row for `default|ipv6`, `zebra.interfaces.conf.j2` renders these lines:

```
no ip nht resolve-via-default
ipv6 nht resolve-via-default
```

On a switch with `resolve_via_default` set to `false` on `Vrf_blue|ipv4`, and with `neighbor_tracking` set to `true` on `Vrf_red|ipv4`, `zebra.nht.conf.j2` renders these lines:

```
vrf Vrf_blue
 no ip nht resolve-via-default
exit-vrf
!
vrf Vrf_red
 ip nht arp-tracking
 ip nht resolve-via-default
exit-vrf
```

The `Vrf_red` block shows the start value. That row sets `neighbor_tracking` only, but the block still holds the affirmative resolve line.

#### 7.2. Runtime Apply in Traditional Mode

`NhtMgr` in `bgpcfgd` subscribes to the `NEXTHOP_TRACKING` table. It runs these steps for each row change:

1. Split the key into a VRF name and an AFI. Reject a key that does not hold two parts, that holds an empty VRF name, or that holds an AFI other than `ipv4` or `ipv6`. A rejected key produces a log message, and the manager makes no other change.
2. Read `neighbor_tracking` and `resolve_via_default` from the row.
3. Render `zebra.nht.db.conf.j2` from these values.
4. Add the rendered text to the pending changes for FRR.
5. Record the row in the internal table that the manager keeps. The manager does this step after step 4, so a failed render leaves no record of a change that FRR did not receive.
6. Write one log message for each field that the manager applied.

`bgpcfgd` collects the pending changes from all of its managers. A later commit step writes the collected text to FRR with `vtysh`.

The manager reads each value into one of three states. The state `unset` means that the manager emits no line for that field, and the state of FRR does not change.

| Condition | State of `resolve_via_default` |
|---|---|
| The row holds `true` or `false` | The value from the row |
| The row holds no `resolve_via_default` field | `unset` |
| The row holds a value that is not a boolean | `unset`, and the manager writes a warning |
| The VRF is not the default VRF | `unset` |

The examples below show the rendered command lines for two row changes. 

```
default|ipv4, neighbor_tracking=false, resolve_via_default=false
    no ip nht arp-tracking
    no ip nht resolve-via-default

default|ipv4, neighbor_tracking=true, resolve_via_default absent
    ip nht arp-tracking
```

The second example shows the value of the `unset` state. The operator changed `neighbor_tracking` only, so the manager emits no resolve line. The resolve state that the boot files established stays in place.

#### 7.3. Runtime Apply in FRR Management Mode

`nht_handler` in `frrcfgd` subscribes to the `NEXTHOP_TRACKING` table. It runs these steps for each row change:

1. Split the key into a VRF name and an AFI. Reject a key that does not hold two parts, that holds an empty VRF name, or that holds an AFI other than `ipv4` or `ipv6`. A rejected key produces a log message, and the handler makes no other change.
2. Read `neighbor_tracking` and `resolve_via_default` from the row.
3. Build a `vtysh` command list from these values.
4. Run the command list.
5. Write one log message for each field that the handler configured.

The handler reads `resolve_via_default` into the same three states that traditional mode uses. The start value of the state depends on the VRF.

| Condition | State of `resolve_via_default` |
|---|---|
| The row holds `true` or `false` | The value from the row |
| The row holds no field, and the VRF is the default VRF | `unset` |
| The row holds no field, and the VRF is a user VRF | `true` |
| The row holds a value that is not a boolean | `unset`, and the handler writes a warning |

The second and third rows hold the difference between the two VRF scopes. The boot file of the default VRF always holds a resolve line, so the handler leaves that line in place when a row carries no field. A user VRF has no such guarantee, so the handler sends the affirmative line.

The handler puts the commands of a user VRF inside a `vrf` block. The examples below show the command list for two row changes.

```
default|ipv4, neighbor_tracking=false, resolve_via_default=false
    no ip nht arp-tracking
    no ip nht resolve-via-default

Vrf_blue|ipv4, neighbor_tracking=true, resolve_via_default=false
    vrf Vrf_blue
    ip nht arp-tracking
    no ip nht resolve-via-default
    exit-vrf
```

#### 7.4. Absent Field and Row Delete

A row change can carry no `resolve_via_default` field, and an operator can delete a row. The table below shows what the runtime path sends to FRR for each of these two events. The user VRF column applies to FRR Management mode only.

| Event | Default VRF | User VRF |
|---|---|---|
| The change carries no `resolve_via_default` field | No command | `ip nht resolve-via-default` |
| The operator deletes the row | `ip nht resolve-via-default` | `ip nht resolve-via-default` |

IPv6 uses `ipv6 nht resolve-via-default`, and the behavior is equivalent. 

The default VRF always holds a resolve line from the boot files. A change that carries only `neighbor_tracking` must not remove that line, so the runtime path sends no command for the default VRF. A user VRF has no such boot line, so the runtime path sends the command.

A row delete returns the row to the default value of the YANG model, which is `true`. A row that an operator creates and then deletes therefore ends in the same state as a row that never existed.

CONFIG_DB holds no empty table, so a change that removes the last row of `NEXTHOP_TRACKING` is not valid. An operator removes the table itself to delete the last row. Each row of the table receives the delete, so the effect on FRR is the same.

### 8. SAI API 

This design needs no change in the SAI API.

### 9. Configuration and management 

This design has no breaking change. An operator configures the field through CONFIG_DB.

#### 9.1. Manifest (if the feature is an Application Extension)

This design is not a SONiC Application Extension, so it has no manifest.

#### 9.2. CLI/YANG model Enhancements 

This design adds no CLI command.

The design adds one leaf to the `sonic-nexthop-tracking` YANG model:

```
leaf resolve_via_default {
    type boolean;
    default true;
    description
        "Allow nexthop to resolve via the default route.";
}
```

The leaf belongs to `NEXTHOP_TRACKING_LIST`. That list uses `vrf_name` and `afi` as its key. The model holds these constraints:

| Item | Constraint |
|---|---|
| `vrf_name` | The string `default`, or a name from the `VRF` table |
| `afi` | The value `ipv4` or the value `ipv6` |
| `resolve_via_default` | A boolean |

The leaf is optional, and its default value is `true`. A configuration file from an earlier release holds no such leaf, so it validates without a change and it keeps the behavior of that earlier release.

#### 9.3. Config DB Enhancements  

The design adds the `resolve_via_default` field to the `NEXTHOP_TRACKING` table. It adds no table, and it changes no other field.

```
{
    "NEXTHOP_TRACKING": {
        "default|ipv4": {
            "resolve_via_default": "false"
        },
        "default|ipv6": {
            "resolve_via_default": "true"
        }
    }
}
```

| Field | Type | Description |
|---|---|---|
| `resolve_via_default` | boolean | Optional. A value of `true` permits a tracked nexthop of this VRF and this AFI to resolve through the default route. A value of `false` stops that resolution. The default value is `true`. |

An operator that upgrades a switch keeps the behavior of the earlier release, because the configuration file of that release holds no `resolve_via_default` field.

### 10. Warmboot and Fastboot Design Impact  

The design keeps the setting in CONFIG_DB. There is no change in behavior for Warmboot or Fastboot.

#### 10.1. Warmboot and Fastboot Performance Impact

Two boot templates now read the `NEXTHOP_TRACKING` table. Each template walks the rows of that table one time. The table holds two rows for each VRF, and the performance impact is negligible. `sonic-cfggen` rendered both templates before this feature, so the design adds no new render step. The work is the same when an operator does not use the feature.

### 11. Memory Consumption

There is no impact to memory consumption.

### 12. Restrictions/Limitations  

1. Traditional mode applies the field for the default VRF only. That mode does not support user VRFs for routing, so an operator that needs the control for a user VRF must use FRR Management mode. This is a limitation of the traditional mode.
2. A value of `false` can stop a BGP session. A peer that zebra resolves only through the default route becomes unresolved, and the session for that peer then stays in the "waiting for NHT" state.
3. The control applies to every tracked nexthop of one VRF and one address family. The design holds no smaller scope.


### 13. Testing Requirements/Design  

The unit tests cover the four components that read the field: the YANG model, the two boot templates, and the two runtime translators. The system tests cover the behavior of a switch.

#### 13.1. Unit Test cases  

The tests check these conditions:

- The YANG model accepts a boolean value. It rejects a value that is not a boolean, and the runtime translators ignore such a value.
- A value of `true` gives the affirmative form, and a value of `false` gives the negative form.
- An absent field keeps the behavior of the earlier releases.
- A row delete returns the configuration to the affirmative form.
- The tests cover the default VRF and a user VRF.
- Each boot template renders a file that matches a golden file.

#### 13.2. System Test cases

The system tests are in `sonic-mgmt`, in `tests/neigh_tracking/test_resolve_via_default.py`. Each case runs in traditional mode and in FRR Management mode. The user VRF case runs in FRR Management mode only, because traditional mode does not support user VRFs.

Each case asserts two things at each step. The first is the state that zebra holds, read from the `resolveViaDefault` field of `show ip[v6] nht json`. The second is the effect on a route, read from the FIB nexthops of a route whose nexthop only the default route can resolve. The state alone does not show that forwarding changed, and the route alone does not show that CONFIG_DB caused the change.

| Case | Purpose |
|---|---|
| `test_resolve_toggle_default_vrf_ipv4` | Set the field to `false` for the default VRF and IPv4, then set it back to `true`. Check the state and the route after each step. |
| `test_resolve_toggle_default_vrf_ipv6` | The same steps for IPv6, and a check that IPv4 does not change with it. |
| `test_resolve_user_vrf` | The same steps for a user VRF, and a check that the default VRF does not change. |
| `test_tracking_change_leaves_resolve` | Change `neighbor_tracking` on a row that holds `resolve_via_default`. Check that the state of zebra does not change. |
| `test_delete_row_restores_resolve` | Delete a row that holds the value `false`. Check that zebra returns to the affirmative form, and that the other row does not change. |
| `test_resolve_survives_config_reload` | Set the field to `false`, then reload the configuration. Check that the rendered configuration file holds the negative form, and that zebra holds that form after the reload. |

The last two cases need one note each.

A test cannot delete the last row of the table. The configuration tool rejects a change that would leave a table with no rows, so `test_delete_row_restores_resolve` creates a row for each AFI and deletes one of them. The remaining row keeps the table valid, and it also shows that the delete applied to one row only.

`test_resolve_survives_config_reload` reads the rendered configuration file, and not only the state of zebra. A reload starts the runtime translators again, so the state of zebra alone does not show which path applied the value. The rendered file is the output of `sonic-cfggen`, and no daemon has started when that file is written.

### 14. Open/Action items - if any 

None.
