# HLD: Centralized-Chassis Manageability - Counters via statsd, SNMP, GNMI

## Table of contents

- [1. Introduction](#1-introduction)
- [2. Architecture at a glance](#2-architecture-at-a-glance)
- [3. The `statsd` daemon](#3-the-statsd-daemon)
  - [3.1 What it does, in order](#31-what-it-does-in-order)
    - [3.1.1 How a name actually flows from an LC namemap to a central key](#311-how-a-name-actually-flows-from-an-lc-namemap-to-a-central-key)
    - [3.1.2 Why each prefix exists](#312-why-each-prefix-exists)
  - [3.2 The systemd gate](#32-the-systemd-gate)
  - [3.3 Operational properties](#33-operational-properties)
  - [3.4 Failure modes worth knowing](#34-failure-modes-worth-knowing)
  - [3.5 What this gives the team](#35-what-this-gives-the-team)
  - [3.6 `portstat -c` on Centralized Chassis](#36-portstat--c-on-centralized-chassis)
- [4. `sonic-snmpagent` changes](#4-sonic-snmpagent-changes)
  - [4.1 Before vs after - the existing maps we are replacing](#41-before-vs-after---the-existing-maps-we-are-replacing)
    - [4.1.1 Interface table (An example)](#411-interface-table-an-example)
    - [4.1.2 Counter-table key format](#412-counter-table-key-format)
  - [4.2 Physical-entity sub-OID generator - `mibs/ietf/physical_entity_sub_oid_generator.py`](#42-physical-entity-sub-oid-generator---mibsietfphysical_entity_sub_oid_generatorpy)
  - [4.3 New file - `mibs/ietf/fs_oid_generator.py`](#43-new-file---mibsietffs_oid_generatorpy)
  - [4.4 Sub-OID generation: old vs new (side-by-side)](#44-sub-oid-generation-old-vs-new-side-by-side)
    - [4.4.1 `entPhysicalTable` chassis-thermal sub-OID (RFC2737 / RFC3433)](#441-entphysicaltable-chassis-thermal-sub-oid-rfc2737--rfc3433)
    - [4.4.2 `hrFSTable` / `hrStorageTable` sub-OID (RFC2790)](#442-hrfstable--hrstoragetable-sub-oid-rfc2790)
  - [4.5 `mibs/ietf/rfc2737.py` - ENTITY-MIB](#45-mibsietfrfc2737py---entity-mib)
  - [4.6 `mibs/ietf/rfc3433.py` - ENTITY-SENSOR-MIB](#46-mibsietfrfc3433py---entity-sensor-mib)
  - [4.7 Test coverage](#47-test-coverage)
- [5. `sonic-gnmi` changes](#5-sonic-gnmi-changes)
  - [5.1 The problem](#51-the-problem)
  - [5.2 The fix - two guarded skips in `populateDbtablePath()`](#52-the-fix---two-guarded-skips-in-populatedbtablepath)
  - [5.3 The `isChassisCentralized()` wrapper (`virtual_db.go`)](#53-the-ischassiscentralized-wrapper-virtual_dbgo)
  - [How this all ties together](#how-this-all-ties-together)

---

## 1. Introduction

In an SI centralized chassis there is one supervisor with multiple linecards. Each linecards has mulitple ASICs. All real port, queue, PG, RIF and fabric-port counters live on the line cards, keyed by per-ASIC SAI OIDs of the form `COUNTERS:oid:0x…`. Resolving those to interface names requires reading the per-ASIC `COUNTERS_*_NAME_MAP` tables that only exist on each LC.

That is fine for code running on the LC. But from the supervisor's POV, when a query is made, to figure out which linecard and ASIC combination for a particular entry could be complicated, if possible. The change set described in this document closes that gap in two coordinated moves:
1. A new daemon, **`statsd`**, runs on each line card and also on the supervisor, reads the local per-ASIC OID-keyed counters, and republishes them into the **central** COUNTERS_DB on the chassis Redis using readable, OID-free keys.
2. Every supervisor-side consumer that previously assumed an OID-keyed COUNTERS_DB grew an `is_chassis_centralized()` branch that reads those new readable keys directly, without name maps and without per-ASIC fan-out. Everything is gated on `is_chassis_centralized()`. Distributed chassis and single-ASIC boxes are untouched.

---

## 2. Architecture at a glance

```
                ┌──────────────────────────────────────────────────────────┐
                │                       Supervisor (RP)                    │
                │                                                          │
                │   Central Redis  (redis_chassis.server : 6381)           │
                │   ┌──────────────────────────────────────────────────┐   │
                │   │ COUNTERS_DB                                      │   │
                │   │   COUNTERS:Ethernet1_1            (port)         │   │
                │   │   RATES:Ethernet1_1               (rate)         │   │
                │   │   COUNTERS:QUEUE_Ethernet1_1:0    (queue)        │   │
                │   │   COUNTERS:PG_Ethernet1_1:3       (PG)           │   │
                │   │   COUNTERS:RIF_Ethernet1_1        (RIF)          │   │
                │   │   COUNTERS:FABRIC_PORT_RP0_3_14   (fabric)       │   │
                │   └──────────────────────────────────────────────────┘   │
                │                       ▲                                  │
                │   Readers (named keys only, on is_chassis_centralized):  │
                │     • sonic-snmpagent  (IF-MIB, PFC MIB, QoS queue MIB)  │
                │     • portstat, intfstat, intfutil                       │
                └───────────────────────┼──────────────────────────────────┘
                                        │ HMSET COUNTERS:<name> …
       ┌────────────────────────────────┴────────────────────────────────┐
       │                                                                 │
   ┌───┴────────────────┐                                ┌───────────────┴─┐
   │   Line card 1      │              …                 │   Line card N   │
   │                    │                                │                 │
   │   statsd daemon ───┴──► reads asic0..asicN          │   statsd daemon │
   │                        COUNTERS_DB (per-ASIC),      │                 │
   │                        joins COUNTERS_*_NAME_MAP,   │                 │
   │                        writes named keys to         │                 │
   │                        central COUNTERS_DB.         │                 │
   └────────────────────────────────────────────────────────────────────── ┘
```

Two things matter about this picture. 
First, the contract between LC and RP is *purely* the shape of keys in the central COUNTERS_DB. 
Second, the central data is a periodic snapshot; every key carries a TTL so the picture self-heals when a line card disappears.

---

## 3. The `statsd` daemon
`statsd` lives at `src/sonic-host-services/scripts/statsd` and is shipped by `sonic-host-services`. Its job is small and well-defined: take what the linecards' `syncd` instances already write to per-ASIC COUNTERS_DBs and make it look, from the chassis Redis, like a single chassis-wide view.

### 3.1 What it does, in order

On every cycle (currently every 10 seconds) the daemon walks each ASIC
namespace on the line card (`asic0`, `asic1`, …) and performs three steps.

**Step 1 — build name maps.** 
It pulls "regular" name maps and the queue maps from the local ASIC's COUNTERS_DB:

| Source table on the LC ASIC      | Output prefix in central DB |
| -------------------------------- | --------------------------- |
| `COUNTERS_PORT_NAME_MAP`         | `Ethernet0_0`               |
| `COUNTERS_PG_NAME_MAP`           | `PG_Ethernet0_0:3`          |
| `COUNTERS_QUEUE_NAME_MAP`        | `QUEUE_Ethernet0_0:0`       |
| `COUNTERS_RIF_NAME_MAP`          | `RIF_Ethernet0_0`           |
| `COUNTERS_FABRIC_PORT_NAME_MAP`  | `FABRIC_PORT_RP0_3_14`      |

**Step 2 — aggregate.** 
For every `COUNTERS:oid:*` key on the ASIC the daemon resolves the OID to a readable name, copies the hash verbatim into an in-memory dictionary keyed by `COUNTERS:<name>`, and does the same for the matching `RATES:oid:*` key under `RATES:<name>`. The SI naming convention (`Ethernet<slot>_<port>`) is unique chassis-wide by design: each front-panel port name is owned by exactly one ASIC on exactly one line card, so no two writes can ever target the same central key.

**Step 3 — bulk publish.**
Each `(target_key, hash)` pair built in Step 2 is written to the central COUNTERS_DB with one `HMSET` and a single `EXPIRE` of 60 seconds.

#### 3.1.1 How a name actually flows from an LC namemap to a central key

The translation looks like one step at the call site (`COUNTERS:<name>` lands in central Redis), but underneath it is a three-stage pipeline. It is worth following one entry from end to end, because consumers now depend on this exact pipeline.

Take a single physical port, `Ethernet0_0`, on `asic0` of line card 1.

**Stage A — what `syncd` writes on the line card.** 
Two unrelated rows exist in the LC's per-ASIC COUNTERS_DB:

```
# In COUNTERS_DB on asic0 of LC1:

HGETALL COUNTERS_PORT_NAME_MAP
  1) "Ethernet0_0"
  2) "oid:0x1000000000016"
  3) "Ethernet0_4"
  4) "oid:0x1000000000017"
  ...

HGETALL COUNTERS:oid:0x1000000000016
  1) "SAI_PORT_STAT_IF_IN_OCTETS"
  2) "847219384"
  3) "SAI_PORT_STAT_IF_OUT_OCTETS"
  4) "923847123"
  ...

HGETALL RATES:oid:0x1000000000016
  1) "RX_BPS"
  2) "1200000"
  ...
```

There is no key called `COUNTERS:Ethernet0_0` here. The interface name and the counter values are connected only by the indirection through the namemap.

**Stage B — Step 1 builds the reverse lookup.** When the daemon iterates
`COUNTERS_PORT_NAME_MAP`, the loop body in `_build_name_maps` derives the *output* key name from the *input* map name with a small prefix table:

| Source namemap entry (name → OID)                     | `map_type`    | Output name (`key_name`)            |
| ----------------------------------------------------- | ------------- | ----------------------------------- |
| `Ethernet0_0  → oid:0x1000000000016` (PORT)           | `port`        | `Ethernet0_0`     (verbatim)        |
| `Ethernet0_0:3 → oid:0x2000000000003` (PG)            | `pg`          | `PG_Ethernet0_0:3` (prefix added)   |
| `Ethernet0_0:0 → oid:0x3000000000000` (QUEUE)         | `queue`       | `QUEUE_Ethernet0_0:0`               |
| `Ethernet0_0  → oid:0x60000000005a3` (RIF)            | `rif`         | `RIF_Ethernet0_0` (prefix added)    |
| `PORT_RP0_3_14 → oid:0x4000000000010` (FABRIC_PORT)   | `fabric_port` | `FABRIC_PORT_RP0_3_14` (rewrite)    |

The result of Stage B for our example is two dictionaries kept entirely in the daemon's memory — never written to Redis.

**Stage C — Step 2 resolves the OID and rekeys the hash.** 
Now the daemon walks every `COUNTERS:oid:*` key it can find on `asic0`.

The hash on the right-hand side is copied **verbatim**: same SAI counter field names, same field values, same field count. The translation changes only the *key*.

**Stage D — Step 3 publishes the entry.** 
What finally lands on the chassis central Redis is exactly:

```
# In COUNTERS_DB on redis_chassis.server:6381

HMSET COUNTERS:Ethernet0_0  SAI_PORT_STAT_IF_IN_OCTETS  847219384 \
                            SAI_PORT_STAT_IF_OUT_OCTETS 923847123 \
                            ...
EXPIRE COUNTERS:Ethernet0_0 60

HMSET RATES:Ethernet0_0     RX_BPS 1200000 ...
EXPIRE RATES:Ethernet0_0    60
```

A consumer on the supervisor — `portstat`, `snmpd`, the queue MIB — can now ask for `COUNTERS:Ethernet0_0` directly. It never sees the underlying OID, never has to know which line card or ASIC owns the port, and never has to load a namemap.

#### 3.1.2 Why each prefix exists

The prefix shapes in Stage B's table are not arbitrary. Each one solves a real collision or readability problem that the namemap-on-the-LC schema does not have to solve: 
- **`PORT_` is dropped** from port names because front-panel ports already carry the slot in their SI name (`Ethernet<slot>_<port>`), so the name is unique chassis-wide on its own.
- **`PG_` and `QUEUE_`are added** because PG and queue keys share the `Ethernet<slot>_<port>:<index>` shape with no other distinguishing feature — without a prefix, a PG row and a queue row for the same port and the same index would collide on one key in central Redis.
- **`RIF_` is added** because a router interface and its underlying port  share the same readable name (`Ethernet0_0`) but resolve to entirely  different OIDs. Without `RIF_`, the second one to publish would  overwrite the first.
- **`PORT_ → FABRIC_PORT_` rewrite** is the fabric-port edge case: the LC namemap already starts those names with `PORT_`, so a naïve `f"FABRIC_PORT_{name}"` would produce `FABRIC_PORT_PORT_RP0_3_14`. Stripping the leading `PORT_` first keeps the central key both correct and human-readable.

These rules are baked into both the publisher (Step 1's `key_name` derivation) and every consumer's key-pattern glob (`COUNTERS:QUEUE_*`, `COUNTERS:RIF_*`, …).

### 3.2 The systemd gate

`statsd` is meaningful only on SI centralized chassis. The condition is also **fail-closed**: any exception loading `sonic_py_common` is treated as "not centralized" and the unit refuses to start. This is the safer default for a daemon that writes into shared chassis state.

### 3.3 Operational properties

A few invariants of the design deserve to be called out, because every downstream consumer assumes them:

- **Bounded staleness.** A 10-second cycle plus a 60-second TTL means a fully healthy LC keeps its keys live continuously, while a wedged or rebooting LC's keys disappear within a minute. Readers therefore never see indefinitely-stale data, and they do not need to track LC liveness themselves.
- **Per-ASIC isolation.** Each ASIC's read and translate step is wrapped in its own try/except. A single misbehaving ASIC cannot poison the whole cycle.
- **No arithmetic.** The daemon never sums, scales or rebases counters. Everything in central COUNTERS_DB is a verbatim copy of what `syncd` wrote on the LC — just under a different key.
- **No name maps published.** Only `COUNTERS:<name>` and `RATES:<name>` rows go to the central DB. The supervisor's `COUNTERS_*_NAME_MAP` tables remain empty. Consumers must be written to discover names from the keys directly, not from a map.

### 3.4. Failure modes worth knowing

The design fails gracefully in every interesting direction, but the behaviour is worth making explicit because it shapes what operators.

- **A line card's `statsd` dies.** Its `COUNTERS:*` keys age out via the 60-second TTL, and within a minute the RP's view stops showing those ports — but nothing on the LC itself is disturbed.
- **The central Redis is unreachable.** `statsd` loops with backoff and logs; the LC's local COUNTERS_DB is untouched, so `portstat` *on the LC* keeps working for emergency triage.
- **One ASIC inside an LC misbehaves.** That ASIC's slice of the cycle fails inside its own try/except; the other ASICs publish normally.

### 3.5. What this gives the team

The user-visible result is the simple one: on an SI centralized chassis `snmpwalk`, `show interfaces counters`, `portstat`, `intfstat`, the queu MIB and the PFC MIB all work against the supervisor and return chassis-wide data, with no operator-side awareness of how many line cards or ASICs ar behind them.

The engineering result is more interesting:

- The chassis-wide counter view is a **Redis-only contract** — one publisher, many readers. There is no new RPC, no new bus, no new daemon to misconfigure. Debugging is one `redis-cli` away.
- The split between "publish via `statsd`" and "fan-out on demand" is principled: anything that is a verbatim per-port hash goes through the daemon, anything that requires arithmetic merging stays an LC-local counter that the RP aggregates on demand.
- Every change is guarded by `is_chassis_centralized()` and the daemon itself is fail-closed at the systemd level. Distributed and fixed-box SONiC paths are not perturbed, and rollback is a single feature-flag flip.

### 3.6. `portstat -c` on Centralized Chassis

What this command does NOT do:
- Does not modify the `COUNTERS_DB` entries in `redis_central`.
- Does not touch the ASIC / SAI on any LC. Hardware counters keep incrementing.
- SNMP, GNMI and any other applications that view COUNTERS_DB directly, will not be affected by any of the `portstat -c` calls

#### `portstat -c` on the RP does exactly three things:
1. Reads every entry (ie: `COUNTERS:Ethernet*`) from the chassis-wide `redis_central` instance's `COUNTERS_DB` (DB #2).
2. Dumps that snapshot as JSON to `/tmp/cache/portstat/<uid>/portstat` on the RP's local filesystem.
3. Prints `Cleared counters` and exits.

Nothing else is written or cleared. Hardware / ASIC / SAI counters continue to increment untouched. Line cards are not contacted directly by `portstat` — the counters are read from the central Redis, not pulled from LCs.

#### Next time `show interfaces counters` runs on the RP:

1. `portstat` (no `-c`) reads the same `redis_central` `COUNTERS_DB` the same way (steps above).
2. Loads the JSON snapshot from `/tmp/cache/portstat/<uid>/portstat`.
3. Prints `current - snapshot` per port.
4. Prepends the line `Last cached time was <timestamp from snapshot>`.

That is the entire "clear" illusion: neither `redis_central` nor the hardware is ever cleared — `show` just subtracts the last snapshot before printing.

#### `portstat -c` on the LCs:
The command will be disabled on LCs in a centralied system. The command will only be able to run on the RP. 

---

## 4. `sonic-snmpagent` changes

### 4.1 Before vs after - the existing maps we are replacing

Before diving into the new SI-aware helpers, it is useful to see what the non-centralized code already builds. On those systems every ASIC has its own OIDs that identify each port, LAG, queue, PG, etc. into that ASIC's local `COUNTERS_DB`. The MIB updaters walk those SAI-OID-keyed structures.

#### 4.1.1 Interface table (An example)

`init_sync_d_interface_tables()` builds four maps from `port_util.get_interface_oid_map()` plus `APPL_DB:PORT_TABLE`. All four maps depend on SAI OIDs being present in `COUNTERS_DB`:

```python
# { if_name (SONiC) -> sai_id }
# ex: { "Ethernet76" : "1000000000023" }
if_name_map

# { "<namespace>:<sai_id>" -> if_name }
# ex: { ":1000000000023" : "Ethernet76" }
if_id_map

# { OID -> if_name (SONiC) }             <-- SNMP ifIndex
# ex: { 77 : "Ethernet76" }
oid_name_map

# { if_name -> alias (from PORT_TABLE)   <-- SNMP ifAlias
# ex: { "Ethernet76" : "etp10" }
if_alias_map

return if_name_map, if_alias_map, if_id_map, oid_name_map
```

On a centralized RP there is no local SAI, so none of these OID-keyed structures exist there - which is exactly why the new `init_readable_*` helpers and the `COUNTERS:<name>` key format were needed.
The new `init_readable_interface_tables()` returns **only two** of these - `(if_alias_map, if_id_map)` - because there is no SAI OID map to build on the RP, and no `sai_id_key` cache to consult:

```python
# { OID -> if_name }
# ex: { 1001 : "Ethernet1/1" }
if_id_map

# { if_name -> alias }
# ex: { "Ethernet1/1" : "etp1" }
if_alias_map

return if_alias_map, if_id_map
```

#### 4.1.2 Counter-table key format

The classic `counter_table()` builds a key from a SAI OID:

```python
def counter_table(sai_id):
    return 'COUNTERS:oid:0x' + sai_id     # ex: COUNTERS:oid:0x1000000000023
```

The new `central_counter_table()` builds a key from the human-readable interface name that `statsd` publishes into the central COUNTERS_DB on the RP:

```python
def central_counter_table(interface_name):
    return 'COUNTERS:' + interface_name    # ex: COUNTERS:Ethernet1/1
```

### 4.2 Physical-entity sub-OID generator - `mibs/ietf/physical_entity_sub_oid_generator.py`

A new SI-aware sub-OID scheme was added for chassis thermals so that sensors on FABRIC-CARDs, PSUs and LINE-CARDs are reachable at unique OIDs under `entPhysicalTable` / `entPhySensorTable`:

```99:133:src/sonic-buildimage/src/sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/physical_entity_sub_oid_generator.py
def get_chassis_thermal_sub_id(position, parent="", thermal_name=""):
    """
    Returns sub OID for thermals that belong to chassis. Sub OID is calculated as follows:
    sub OID = CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_CHASSIS_THERMAL + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_TEMP, 
    :param position: thermal position
    :return: sub OID of the thermal
    """
    if is_chassis_centralized():
        rp_lc_slot = 0
        rp_lc_type = 1
        parent_slot = 0
        parent_type = 0

        # Set RP/LC type and slot
        if thermal_name.startswith("LINE-CARD"):
            match = re.search(r"LINE-CARD(\d+)", thermal_name)
            if match:
                rp_lc_slot = int(match.group(1))
                rp_lc_type = 2
        ...
```

The centralized-mode encoding uses:

* `rp_lc_type` (1=RP, 2=LC), `rp_lc_slot`
* `parent_type` (0=chassis, 1=FABRIC-CARD, 2=PSU), `parent_slot`
* `position` on that parent

Non-centralized mode falls back to the classic `CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_CHASSIS_THERMAL + position*100 + SENSOR_TYPE_TEMP` computation, so pizza-box devices are unaffected.

### 4.3 New file - `mibs/ietf/fs_oid_generator.py`

Because HOST-RESOURCES-MIB (`hrFSTable`, `hrStorageTable`) now has to enumerate mount points and memory regions **for every card in the chassis**, a fresh sub-OID scheme was needed.  This lives in a new file, `fs_oid_generator.py`.

The scheme is a 6-digit integer:
```
final_oid = (card_type * 10000) + (card_index * 100) + mount_index
where card_type = 10 for RP, 20 for LC
      card_index = 0-99
      mount_index = 1-99 (per-card, resets per card)
```

Examples: `RP0`/mount 1 -> `100001`; `LC0`/mount 1 -> `200001`; `LC1`/mount 3 -> `200103`.

The RP entries are always emitted **before** LC entries so an `snmpwalk` follows a natural card ordering.

### 4.4 Sub-OID generation: old vs new (side-by-side)

Sections 6.2 and 6.3 introduce two new sub-OID schemes. This subsection putseach one next to the pre-existing (non-centralized) scheme so it is easy tosee what changed and why.

#### 4.4.1 `entPhysicalTable` chassis-thermal sub-OID (RFC2737 / RFC3433)

The classic scheme in `physical_entity_sub_oid_generator.py`  is a 9-digit integer laid out as (from the docstring at the top of the file):

```
Digit 1   : Module Type  (2=Mgmt, 5=Fan Drawer, 6=PSU, 7=Fabric Card)
Digit 2-3 : Module Index
Digit 4-5 : Device Type  (01=PS, 02=Fan, 24=Power Monitor, 99=Chassis Thermal)
Digit 6-7 : Device Index
Digit 8   : Sensor Type  (1=Temp, 2=Fan Tach, 3=Power, 4=Current, 5=Voltage)
Digit 9   : Sensor Index
```

For a chassis thermal specifically, the non-centralized formula collapses to:

```
sub_id = CHASSIS_MGMT_SUB_ID + DEVICE_TYPE_CHASSIS_THERMAL
       + position * DEVICE_INDEX_MULTIPLE + SENSOR_TYPE_TEMP
       = 2_00_00_00_00              # module = Mgmt (2), no index
       + 99 * 10_000                # device type = chassis thermal
       + position * 100             # per-thermal position
       + 10                         # sensor type = temperature
```

This assumes exactly **one** chassis (the Mgmt module) and no way to distinguish "the temperature sensor on FABRIC-CARD 2, position 3" from "the temperature sensor on FABRIC-CARD 5, position 3".  On a centralized chassis with multiple RPs, LCs, fabric cards and PSUs, every thermal would collide onto the same OID.

The centralized formula (also 9 digits, but repartitioned) is:

```
sub_id = rp_lc_type * 100_000_000     # 1=RP, 2=LC
       + rp_lc_slot * 1_000_000       # slot of the RP/LC that owns this thermal
       + parent_type * 100_000        # 0=chassis, 1=FABRIC-CARD, 2=PSU
       + parent_slot * 1_000          # slot of the fabric card / PSU
       + 100                          # fixed marker (was PORT_IFINDEX_MULTIPLE)
       + position                     # thermal position on the parent
```

The non-centralized path is preserved unchanged - `get_chassis_thermal_sub_id()` falls back to the classic formula when `is_chassis_centralized()` returns `False`, so pizza-box devices see identical OIDs to before.

#### 4.4.2 `hrFSTable` / `hrStorageTable` sub-OID (RFC2790)

For HOST-RESOURCES-MIB the pre-existing behavior is not a "scheme" at all - it is a plain sequential counter that ignores card identity because a pizza-box has only one card:

```python
# Non-centralized (existing behavior)
sub_oid = len(self.fs_oid_map) + 1     # 1, 2, 3, 4, ...
```

That is fine when there is one filesystem set to enumerate, but on a centralized chassis the RP has to expose mount points and memory regions for **every card in the chassis**, and the sub-OIDs need to (a) be stable across polls, (b) be groupable per card in an `snmpwalk`, and (c) leave enough room for a chassis with many LCs.

The new centralized scheme (in `fs_oid_generator.py`) is a 6-digit integer:

```
final_oid = card_type   * 10_000    # 10 = RP, 20 = LC
          + card_index  * 100       # 0-99 slot
          + mount_index * 1         # 1-99, per-card (resets per card)
```

Side-by-side:

| Entry                          | Non-centralized | Centralized |
|---|---|---|
| First mount of the "card"      | `1`             | `100001` (RP0, mount 1) |
| Second mount of the "card"     | `2`             | `100002` (RP0, mount 2) |
| First mount of the next card   | `3`             | `200001` (LC0, mount 1) - jumps to new "card block" |
| First mount of LC1             | *(n/a)*         | `200101` (LC0 slot 1, mount 1) |
| Third mount of LC3             | *(n/a)*         | `200303` (LC3, mount 3) |

Key differences:

* **Card identity is encoded in the OID.**  A single `snmpwalk` of `hrStorageTable` shows all RP entries in a contiguous block starting at `100001`, followed by all LC entries starting at `200001`.  With the pre-existing sequential scheme, the operator would have to correlate `hrStorageDescr` strings to figure out which card each entry belonged to.
* **Ordering is stable across polls.**  `init_fs()` explicitly sorts RP cards first, then LC cards, then assigns per-card `mount_index` starting at 1.  A card going away no longer renumbers the other cards' OIDs the way `len(self.fs_oid_map) + 1` would.
* **Room for growth.**  6 digits allow 2 card types x 100 slots x 100 mount points per card, which is more than the current chassis needs.
* **Backward compatible.**  `rfc2790.py` keeps the classic `sub_oid = len(self.fs_oid_map) + 1` code path in the `else` branch, so pizza-boxes and distributed multi-ASIC systems still see the sequential numbers they had before.


### 4.5 `mibs/ietf/rfc2737.py` - ENTITY-MIB

Thermal-sensor discovery was widened so PSU and FABRIC-CARD child thermals are attached to the correct parent via the new SI-aware sub-OID:

```1136:1148:src/sonic-buildimage/src/sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc2737.py
is_fabric_card_0_sub_id = any(chassis_oid == (FABRIC_CARD0_SUB_ID + i, ) for i in range(len(multi_asic.get_asic_presence_list()) * 2))
is_psu_name = thermal_parent_name.startswith("PSU")
if chassis_oid and (is_chassis_sub_id or (is_chassis_centralized() and (is_fabric_card_0_sub_id or is_psu_name))):
    thermal_sub_id = get_chassis_thermal_sub_id(thermal_position, thermal_parent_name, thermal_name)
    ...
```

### 4.6 `mibs/ietf/rfc3433.py` - ENTITY-SENSOR-MIB

Sensor-parent classification was relaxed in centralized mode so thermals whose parent is a FABRIC-CARD are still enumerated (in non-centralized mode we only kept thermals whose parent was `chassis`):

```599:606:src/sonic-buildimage/src/sonic-snmpagent/src/sonic_ax_impl/mibs/ietf/rfc3433.py
if is_null_empty_str(thermal_parent_name):
    continue
if (is_chassis_centralized()):
    if (CHASSIS_NAME_SUB_STRING not in thermal_parent_name.lower() and FABRIC_CARD_SUB_STRING not in thermal_parent_name.lower()):
        continue
else:
    if CHASSIS_NAME_SUB_STRING not in thermal_parent_name.lower():
        continue
```

### 4.7 Test coverage

New / expanded unit tests exercise the centralized-chassis code paths:

* `tests/test_rfc1213.py`
* `tests/test_rfc2737.py`
* `tests/test_rfc2790_fs.py`
* `tests/test_rfc2790_hrstorage.py`
* `tests/test_rfc2790_empty_tables.py` (added in `d23a84f679`)
* `tests/test_rfc2863.py`
* `tests/test_rfc3433.py`
* `tests/test_pfc.py`
* `tests/test_queues_stat.py`
* `tests/test_physical_entity_sub_oid_generator.py`
* `tests/test_lldp.py`
* `tests/namespace/test_lldp.py`

Plus new mock DB fixtures under `tests/mock_tables/`:

* `appl_db.json`, `counters_db.json`, `state_db.json` in the default
  namespace with `MOUNT_POINTS|RP0|...`, `MEMORY_STATS|1|...`,
  `COUNTERS:Ethernet1_1`, LAG members, LLDP remote entries, etc.
* `asic0/appl_db.json`, `global_db/appl_db.json` for the LLDP fanout tests.
---

## 5. `sonic-gnmi` changes

The `is_chassis_centralized = True` work in `sonic-gnmi` teaches the gNMI server that on a centralized RP the COUNTERS_DB keys are already interface names (populated by the `statsd` daemon from section 6).

### 5.1 The problem

On a distributed / pizza-box system, gNMI paths under `COUNTERS_DB/COUNTERS/...` refer to SAI OIDs. A request like `COUNTERS/Ethernet0` is translated:

1. `Ethernet0` is looked up in `COUNTERS_PORT_NAME_MAP` -> `oid:0x1000000000023`.
2. The real Redis key `COUNTERS:oid:0x1000000000023` is fetched.
3. Similar name maps exist for queues (`COUNTERS_QUEUE_NAME_MAP`), PGs, PFCWD, fabric ports, debug switch stats, SIDs, ACL rules.

On a centralized RP none of that applies:

* The RP has no local SAI, so **no `COUNTERS_*_NAME_MAP` tables exist** in its COUNTERS_DB. Attempting to initialise them just errors out.
* Counters are pushed from every LC by `statsd` under the human-readable key format described in section 1 - `COUNTERS:Ethernet0_0`, `COUNTERS:QUEUE_Ethernet0_9:9`, etc. The "name" already **is** the key; there is nothing to translate.


### 5.2 The fix - two guarded skips in `populateDbtablePath()`

The entire behavioural change is two `if !isChassisCentralized()` guards in `sonic_data_client/db_client.go`.

**Guard 1** - skip loading the OID -> name maps that don't exist on the RP:

```go
if targetDbName == "COUNTERS_DB" {
    // In centralized chassis mode the COUNTERS_*_NAME_MAP tables are
    // not populated because counters are keyed by interface name
    // directly rather than by SAI OID, so the OID-lookup maps below
    // are only initialised in distributed mode.
    if !isChassisCentralized() {
        err := initCountersPortNameMap()
        ...
        err = initCountersQueueNameMap()
        err = initCountersPGNameMap()
        err = initAliasMap()
        err = initCountersPfcwdNameMap()
        err = initCountersFabricPortNameMap()
        err = initDebugNameSwitchStatMap()
        err = initCountersSidMap()
        err = initCountersAclRuleMap()
    }
}
```

**Guard 2** - skip the lookup so the path is used verbatim:

```go
// First lookup the Virtual path to Real path mapping tree.
// The path from gNMI might not be a real db path.
//
// In centralized chassis mode the gNMI path elements (e.g.
// "Ethernet0_0", "QUEUE_Ethernet0_9:9") are already the physical
// COUNTERS_DB keys, so the V2R translation must be skipped and the
// path used verbatim. Skipping the lookup here is the intended
// behaviour, not a workaround.
if tblPaths, err := lookupV2R(stringSlice); err == nil && !isChassisCentralized() {
    ...
}
```

With those two guards in place, `gnmi_get COUNTERS/Ethernet0_0` on the RP falls through to the generic table/key resolver in `populateDbtablePath()`, which produces `tablePath{tableName: "COUNTERS", tableKey: "Ethernet0_0"}` and reads the real Redis key `COUNTERS:Ethernet0_0` - exactly what `statsd` populates and what SNMP reads via `central_counter_table()` in section 6.

### 5.3 The `isChassisCentralized()` wrapper (`virtual_db.go`)

A thin package-level wrapper is added so the two guards above (and their unit tests) share one predicate:

```go
// isChassisCentralized is a thin wrapper around the shared
// deviceinfo.IsChassisCentralized() helper. It exists primarily so that
// existing call sites (and unit tests) continue to work without having
// to reach into another package.
//
// The shared implementation lives in sonic-mgmt-common/pkg/deviceinfo
// to keep behaviour aligned with sonic_py_common.device_info and to
// avoid duplicating the platform_env.conf parsing in every repo.
//
// It is exposed as a package-level var (rather than a func) so that unit
// tests can override it with a plain assignment. A direct func definition
// would get inlined by the compiler, which silently breaks gomonkey-style
// patching unless the build is invoked with `-gcflags="all=-N -l"` - a
// flag the standard `make check_gotest` recipe does not pass.
var isChassisCentralized = func() bool {
    return deviceinfo.IsChassisCentralized()
}
```

### How this all ties together

Sections 4 and 5 are the two ends of the same wire:

* Section 4 (`sonic-snmpagent` + `statsd` + `procdockerstatsd`) sets up the central COUNTERS_DB / STATE_DB on the RP with **human-readable keys** (`COUNTERS:Ethernet0_0`, `COUNTERS:QUEUE_...`, `MOUNT_POINTS|RP0|...`).
* Section 5 (`sonic-gnmi`) makes sure `gnmi_get` / `gnmi_subscribe` on the same RP **serve those keys verbatim** instead of trying to translate them through OID name-maps that don't exist in centralized mode.

Net result: `snmpwalk` and `gnmi_get` against the same centralized RP now read the same underlying rows and return consistent chassis-wide counter data.
