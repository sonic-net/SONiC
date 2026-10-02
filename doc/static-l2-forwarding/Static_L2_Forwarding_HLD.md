# Static L2 Forwarding for SONiC — High Level Design

## Revision

| Rev | Date       | Author            | Change          |
|-----|------------|-------------------|-----------------|
| 0.1 | 2026-07-21 | Anant Kishor Sharma | Initial draft |

## Table of Contents
1. Scope
2. Definitions / Abbreviations
3. Overview
4. Requirements
5. SAI dependency
6. Architecture
7. High-Level Design
   - 7.1 Per-VLAN MAC-learning disable
   - 7.2 Per-VLAN BUM flood disable
   - 7.3 Static FDB via config
8. Configuration examples
9. Warm/Fast reboot
10. Test plan
11. Backward compatibility
12. Open questions

## 1. Scope

This HLD covers config-driven **static L2 forwarding**, made of three independent,
per-VLAN, SAI-backed features:

1. Per-VLAN MAC-learning disable
2. Per-VLAN BUM (Broadcast, Unknown-unicast, Unknown-multicast) flood disable
3. Static FDB entries via CONFIG_DB

Each is usable on its own and defaults to today's behavior (no functional change
unless explicitly configured).

## 2. Definitions / Abbreviations

| Term | Meaning |
|------|---------|
| BUM  | Broadcast, Unknown-unicast, Multicast traffic |
| FDB  | Forwarding Database (MAC address table) |
| GCU  | Generic Config Updater (`config apply-patch`) |
| RIF  | Router interface |

## 3. Overview

Some deployments provision Layer-2 forwarding **entirely statically**: dynamic
MAC learning is off, BUM flooding is
off, and forwarding is driven by static FDB entries, with the **VLAN as the
traffic-isolation domain**. A controller/agent pushes this intent (via gNMI).

Static L2 forwarding is used, for example, in SONiC-based AI scale-up (GPU) fabrics,
where forwarding is statically provisioned and dynamic learning + BUM flooding are
unnecessary. The capability itself is generic and applies to any statically provisioned
L2 domain.

SONiC today cannot express any of these three behaviors per VLAN via configuration:

- MAC-learning control in swss today is only at the bridge-port level: the `learn_mode`
  field is handled for `PORT` (`porthlpr`/`portsorch`) and `PORTCHANNEL` (`teammgr`) and
  mapped to `SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE`. There is no per-VLAN learning control.
- Per-VLAN flood control is set today only by internal features (never by user
  config): `proxy_arp` sets broadcast/unknown-multicast flood to `NONE`
  (`IntfsOrch::setIntfVlanFloodType`), and VXLAN/EVPN sets unknown-unicast/broadcast
  flood via an L2MC group (`COMBINED`, `PortsOrch::addVlanFloodGroups`).
- Static FDB can only be injected into APPL_DB `FDB_TABLE`; the CONFIG_DB `FDB` table
  constant is reserved (`CFG_FDB_TABLE_NAME`) but has **no consumer**, and there is no
  CLI/YANG, so it is not persistable or gNMI-settable.

This HLD adds CONFIG_DB schema + YANG + orchagent wiring for all three.

## 4. Requirements

1. Disable MAC learning per VLAN via configuration.
2. Disable BUM flooding per VLAN via configuration.
3. Program static FDB entries via CONFIG_DB.
4. All settable via `config apply-patch` / GCU / gNMI (i.e. YANG-modeled).
5. Persist across `config reload` and warm/fast reboot.
6. Defaults preserve current behavior (learning on, flooding on, no static FDB).

## 5. SAI dependency

All three are already defined by SAI (`saivlan.h`, `saifdb.h`); no SAI change:

| Feature | SAI attribute / value |
|---------|-----------------------|
| VLAN MAC-learning disable | `SAI_VLAN_ATTR_LEARN_DISABLE` (bool) |
| VLAN BUM flood disable | `SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE`, `..._UNKNOWN_MULTICAST_...`, `..._BROADCAST_...` = `SAI_VLAN_FLOOD_CONTROL_TYPE_NONE` |
| Static FDB | `SAI_FDB_ENTRY_TYPE_STATIC` (already programmed by `fdborch`) |

## 6. Architecture

Two independent, config-driven paths, both landing on existing SAI objects
(`PortsOrch` owns the SAI VLAN; `FdbOrch` is unchanged):

```
Per-VLAN learning + BUM flood
  CONFIG_DB   VLAN|VlanX            { mac_learning, *_flood }
      │  vlanmgr
      ▼
  APPL_DB     VLAN_TABLE:VlanX      { mac_learning, *_flood }
      │  PortsOrch::addVlan
      ▼
  SAI / ASIC  SAI_VLAN_ATTR_LEARN_DISABLE
              SAI_VLAN_ATTR_*_FLOOD_CONTROL_TYPE

Per-VLAN static FDB
  CONFIG_DB   FDB|VlanX|MAC         { port }
      │  vlanmgr
      ▼
  APPL_DB     FDB_TABLE:VlanX:MAC   { type=static, port }
      │  FdbOrch (existing, unchanged)
      ▼
  SAI / ASIC  SAI_FDB_ENTRY_TYPE_STATIC
```

## 7. High-Level Design

### 7.1 Per-VLAN MAC-learning disable

- **CONFIG_DB** `VLAN` table: new field `mac_learning` — enumeration `"enabled"|"disabled"`, default `"enabled"`.
- **YANG**: `sonic-vlan.yang`, leaf `mac_learning` in `VLAN_LIST`.
- **cfgmgr**: `vlanmgr` propagates `mac_learning` from CONFIG_DB `VLAN` to APPL_DB `VLAN_TABLE`.
- **orchagent**: `PortsOrch` owns SAI VLAN objects (`PortsOrch::addVlan`, which today sets only `SAI_VLAN_ATTR_VLAN_ID`). Set `SAI_VLAN_ATTR_LEARN_DISABLE = (mac_learning == "disabled")` on VLAN create and on change. `SAI_VLAN_ATTR_LEARN_DISABLE` is not set anywhere in swss today, so there is no existing owner to coordinate with.

### 7.2 Per-VLAN BUM flood disable

> **Non-goal:** configuring per-VLAN BUM-flood-disable *together with* `proxy_arp` or
> VXLAN/EVPN on the **same** VLAN is out of scope. This feature is **mutually exclusive**
> with those features on a given VLAN and is a **single-owner (`PortsOrch`)** change that
> does not alter their code paths.

Why this non-goal is safe and non-restrictive:
- **It follows SONiC's existing flood-ownership precedent.** There is no cross-feature
  flood arbitration in swss today: `proxy_arp` (`IntfsOrch`, writes broadcast +
  unknown-multicast) and VXLAN/EVPN (`PortsOrch::addVlanFloodGroups`, writes
  unknown-unicast + broadcast) each set the VLAN flood-control type from their own feature
  state, and neither reads the other's. This feature is one more such writer; it adds
  **no** new arbitration.
- **It does not co-occur with the target use case.** A static-L2 isolation VLAN runs
  neither an anycast/`proxy_arp` L3 service nor a VXLAN/EVPN overlay, so the combination
  does not arise in the deployments this feature targets.
- **Existing behavior is preserved.** If the combination is configured anyway, the config
  flood-disable is not applied on a VLAN that already has a VXLAN/EVPN flood group
  (`m_vlan_info` = `COMBINED`) — rejected/ignored with a warning — so those features'
  behavior is untouched.

Other writers of the three `SAI_VLAN_ATTR_*_FLOOD_CONTROL_TYPE` attributes today:
- `PortsOrch::addVlan` sets the baseline `ALL` (tracked in `Port::m_vlan_info`; `umc`
  is not tracked there yet).
- VXLAN/EVPN sets `COMBINED` via an L2MC flood group (`PortsOrch::addVlanFloodGroups`).
- `proxy_arp` sets `NONE` (`IntfsOrch::setIntfVlanFloodType`) — already **aligned** with
  our intent, not a conflict.

Design:
- **CONFIG_DB** `VLAN` table: new fields `unknown_unicast_flood`,
  `unknown_multicast_flood`, `broadcast_flood` — enumeration `"enabled"|"disabled"`,
  default `"enabled"` (single `bum_flooding` convenience flag: open question).
- **YANG**: `sonic-vlan.yang` leaves in `VLAN_LIST`.
- **Mutual exclusion:** the config flood-disable is honored only on a **pure-L2 VLAN** —
  one with no VXLAN/EVPN flood group and no proxy_arp/RIF. If such a feature is present
  on the VLAN, the config flag is **rejected/ignored with a warning**; we do **not** merge
  semantics or define a runtime precedence between owners.
- **orchagent (`PortsOrch`)**: on a pure-L2 VLAN, set the three
  `*_FLOOD_CONTROL_TYPE = NONE` from config, tracked in `m_vlan_info` (add
  `umc_flood_type` for completeness). No change to `addVlanFloodGroups` or the
  proxy_arp path.

### 7.3 Static FDB via config

> Designed in the merged **Layer 2 Forwarding Enhancements HLD** (#379,
> `doc/layer2-forwarding-enhancements`) but only **partially landed**: the CONFIG_DB
> `FDB` table constant merged (`CFG_FDB_TABLE_NAME = "FDB"`, swss-common #303) and
> `FdbOrch` handles APPL static FDB, but the **config→APPL consumer, the CLI**
> (sonic-utilities #529, **closed**) **and YANG were never completed**. This piece completes it.

- **CONFIG_DB**: use the reserved `FDB` table (`CFG_FDB_TABLE_NAME`), key
  `VlanX|<mac>`, field `port` (entry type is implicitly static).
- **YANG**: new `sonic-fdb.yang` modeling the `FDB` table.
- **cfgmgr**: add a consumer of CONFIG_DB `FDB` in `vlanmgr`, which already owns the
  APPL `FDB_TABLE` producer (`m_appFdbTableProducer`), so it writes APPL_DB `FDB_TABLE`
  with `type=static` + `port`. No new manager is needed.
- **orchagent**: **no change** — `FdbOrch` already programs APPL static FDB as
  `SAI_FDB_ENTRY_TYPE_STATIC`.
- **CLI** (sonic-utilities): follow the approved #379 precedent —
  `config mac add <mac> <vlan> <interface>` / `config mac del <mac> <vlan>` (implemented
  in the closed sonic-utilities #529). That name is available today; `config fdb` is a
  more descriptive alternative.

## 8. Configuration examples

```json
{
  "VLAN": {
    "Vlan100": {
      "vlanid": "100",
      "mac_learning": "disabled",
      "unknown_unicast_flood": "disabled",
      "unknown_multicast_flood": "disabled",
      "broadcast_flood": "disabled"
    }
  },
  "FDB": {
    "Vlan100|00:11:22:33:44:55": { "port": "Ethernet8" }
  }
}
```

## 9. Warm / Fast reboot

All state is config-driven and restored from `config_db.json`; APPL_DB entries are
re-created by the managers on start, and orchagent reprograms SAI. No new warmboot
state required.

## 10. Test plan

- **YANG**: sonic-yang-models positive/negative cases for each new leaf/table.
- **swss**: mock/VS tests asserting orchagent programs `SAI_VLAN_ATTR_LEARN_DISABLE`,
  the flood-control attrs, and static FDB entries.
- **End-to-end attribute (VS + HW)**: `config apply-patch`/gNMI → CONFIG_DB → APPL_DB →
  ASIC_DB, confirming the SAI attributes are programmed (VLAN learn-disable, the three
  `*_FLOOD_CONTROL_TYPE`, and the static FDB entry as `SAI_FDB_ENTRY_TYPE_STATIC`).
- **Dataplane / traffic (VS + HW)**: with the config applied, verify forwarding behavior:
  (a) learning disabled → no new MACs are learned on the VLAN; (b) BUM flood disabled →
  broadcast, unknown-unicast, and unknown-multicast are not flooded to VLAN members;
  (c) static FDB entry → known-unicast is forwarded only to the configured port.

## 11. Backward compatibility

All new fields default to today's behavior. Absent config = learning on, flooding
on, no static FDB. No change to existing deployments.

## 12. Open questions

1. BUM flood granularity: both SAI (three separate `*_FLOOD_CONTROL_TYPE` attributes)
   and SONiC's existing BUM precedent (`sonic-storm-control.yang` keyed by `storm_type`;
   the BUM storm-control HLD configures the types **independently**) model broadcast,
   unknown-unicast, and unknown-multicast per-type — so the schema uses three granular
   fields (`unknown_unicast_flood`, `unknown_multicast_flood`, `broadcast_flood`). Open:
   whether to also offer a single `bum_flooding` convenience flag that fans out to all three.
2. no-BUM mutual-exclusion guard: the VXLAN/EVPN case is the only real divergence and is
   detectable from `PortsOrch` state (`m_vlan_info` flood type = `COMBINED`). Since
   `proxy_arp` writes broadcast/unknown-multicast `NONE` directly via `IntfsOrch` (not
   tracked in `m_vlan_info`) — the same value this feature wants — the open point is
   whether explicit `proxy_arp`/RIF detection is needed at all, or the overlap is harmless.
3. Static FDB CLI name: the approved #379 HLD and its (closed) implementation #529 both
   proposed `config mac add <mac> <vlan> <interface>` / `config mac del <mac> <vlan>`, and
   that name is free today. Leaning to reuse it for precedent;
   `config fdb` is a more descriptive alternative. Key format `Vlan<id>|<mac>` in the
   reserved `FDB` table, per #379.
