# SONiC Component Statistics — Reporting HLD

## Table of Content

- [Revision](#1-revision)
- [Scope](#2-scope)
- [Definitions/Abbreviations](#3-definitionsabbreviations)
- [Overview](#4-overview)
- [Requirements](#5-requirements)
- [Architecture Design](#6-architecture-design)
- [High-Level Design](#7-high-level-design)
- [SAI API](#8-sai-api)
- [Configuration and management](#9-configuration-and-management)
- [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [Memory Consumption](#11-memory-consumption)
- [Restrictions/Limitations](#12-restrictionslimitations)
- [Testing Requirements/Design](#13-testing-requirementsdesign)
- [Open/Action items](#14-openaction-items)

### 1. Revision

| Rev | Date       | Author        | Change Description                                       |
|-----|------------|---------------|----------------------------------------------------------|
| 0.1 | 2026-05-12 | Yutong Zhang  | Initial revision (split from component-stats Framework HLD) |
| 0.2 | 2026-05-27 | Yutong Zhang  | Reframe §7.2 as a Metric Name / Label List / Description table |
| 0.3 | 2026-05-27 | Yutong Zhang  | Align §7.5 and §13.2 with the §7.2 metric naming         |

### 2. Scope

This HLD specifies how the service-level component counters produced by `swss::ComponentStats` (see the [Framework HLD](./component-stats-framework-hld.md)) are **reported** from a SONiC switch to off-box telemetry systems.

For the initial revision the reporting path is exactly one:

```
component (swss/gnmi/...)
  -> ComponentStats library
       -> COUNTERS_DB (Redis)
            -> telegraf (Geneva mdm pipeline)
                 -> Geneva
```

This HLD owns the **schema contract** between the producer (`ComponentStats`) and the consumer (telegraf). The deployment, configuration, and operation of the telegraf and mdm containers themselves are owned by the NDM "Geneva integration with SONiC" HLD; this document references them but does not duplicate them.

Direct application-side OTLP export (e.g. the `OpenTelemetry SDK -> mdm` path described in the NDM HLD §4) is **not** part of this revision; it is listed as future work in §14.

### 3. Definitions/Abbreviations

| Term            | Definition                                                                                  |
|-----------------|---------------------------------------------------------------------------------------------|
| Component       | A SONiC container that produces service-level counters (e.g. `swss`, `gnmi`, `bmp`).        |
| Entity          | A logical grouping of metrics inside a component (e.g. an orchagent table, a gNMI path).    |
| Metric          | A named `uint64` counter or gauge inside an entity.                                         |
| ComponentStats  | The reusable producer library specified in the Framework HLD.                               |
| `COUNTERS_DB`   | The existing SONiC Redis database (logical DB 2) holding counter rows.                      |
| telegraf        | The off-box-friendly metric agent running on the switch; configured and operated by NDM.    |
| mdm             | Geneva metric agent that consumes telegraf output and forwards it to Geneva.                |
| NDM HLD         | "Geneva integration with SONiC" HLD, owned by the NDM team.                                 |

### 4. Overview

The Framework HLD specifies a producer that writes each component's service-level counters into `COUNTERS_DB` under a uniform key layout. To make those counters useful off-box, we need a stable contract between that producer and whatever agent harvests Redis on the switch and forwards data to Geneva.

NDM has already designed and is rolling out a telegraf-based pipeline for harvesting `COUNTERS_DB` and forwarding to Geneva (see NDM HLD §5 "Existing stats collecting from Database via mdm"). This HLD therefore does **not** introduce a new transport. Instead it:

1. **Defines the Redis schema** that the producer writes and that telegraf consumes (key layout, hash fields, types, dirty-tracking semantics).
2. **Specifies the SWSS-specific vocabulary** (`SWSS_STATS:<table>` with `SET` / `DEL` / `COMPLETE` / `ERROR`).
3. **States the conventions** that future components must follow so that telegraf can pick them up by pattern match without a per-component configuration change.

The result is a thin, declarative contract between two teams: SONiC owns what is written; NDM owns how it is harvested and forwarded.

### 5. Requirements

**Functional**

- R1. Every SONiC container that integrates `ComponentStats` shall expose its counters in `COUNTERS_DB` under the uniform key layout defined in §7.1.
- R2. The schema shall be discoverable by pattern match (`<COMPONENT>_STATS:*`) so that a single telegraf input definition can pick up all current and future components without code or configuration changes.
- R3. The SWSS facade (`SwssStats`) shall publish counters under `SWSS_STATS:<table>` with hash fields `SET`, `DEL`, `COMPLETE`, `ERROR` (decimal `uint64`).
- R4. The schema shall include a per-entity *update marker* (the version-bump in the producer; observable to telegraf as the row's hash value changing) so that idle rows are not re-emitted to Geneva every cycle.

**Non-functional**

- R5. The reporting path shall not require changes to the SONiC dataplane, syncd, SAI, or the existing Flex-Counter pipeline.
- R6. The reporting path shall not impose any on-the-wire dependency between SONiC and a specific off-box telemetry system. SONiC writes Redis; whatever consumes Redis is replaceable.
- R7. A failure of telegraf, mdm, or Geneva shall not affect the producer or any other SONiC service.

**Out of scope**

- Telegraf container packaging, lifecycle, and configuration. See NDM HLD §5.2 ("telegraf design").
- mdm container deployment, KubeSonic rollout. See NDM HLD §3 and §6.
- Geneva endpoint, authentication, dashboards, alerting.
- Direct OTLP export from the application (see future work, §14).

### 6. Architecture Design

```
+-------------------------- SONiC switch ---------------------------+
|                                                                   |
|  +-- container (e.g. swss) -----------------------------------+   |
|  | application -> ComponentStats library                      |   |
|  +------------------------+-----------------------------------+   |
|                           | HSET                                  |
|                           v                                       |
|              +-------------------------+                          |
|              | COUNTERS_DB (Redis DB 2)|                          |
|              |  SWSS_STATS:PORT_TABLE  |                          |
|              |  GNMI_STATS:/iface/...  |                          |
|              |  BMP_STATS:...          |                          |
|              +-----------+-------------+                          |
|                          | HSCAN / HGETALL                        |
|                          v                                        |
|              +-------------------------+                          |
|              | telegraf                |  (owned by NDM HLD §5.2) |
|              +-----------+-------------+                          |
|                          |                                        |
|                          v                                        |
|              +-------------------------+                          |
|              | mdm                     |  (owned by NDM HLD §4)   |
|              +-----------+-------------+                          |
|                          |                                        |
+--------------------------|----------------------------------------+
                           v
                       +--------+
                       | Geneva |
                       +--------+
```

The boundary owned by this HLD is the box labelled `COUNTERS_DB`. Everything above it (the producer) is specified in the Framework HLD; everything below it (telegraf, mdm, Geneva) is specified in the NDM HLD. This HLD owns the **interface between the two**.

### 7. High-Level Design

#### 7.1 `COUNTERS_DB` key layout (the contract)

For a component named `C` (case-insensitive at the API; rendered uppercase on the wire) and an entity `E`:

```
db:        COUNTERS_DB             (logical DB 2)
key:       "<UPPER(C)>_STATS:<E>"
type:      Redis hash
fields:    each metric name -> decimal uint64 string
```

Properties guaranteed by the producer:

- **Stable suffix `_STATS`.** Every component writes under `<COMPONENT>_STATS:*` and only there, so telegraf can match `*_STATS:*` (or a per-component pattern such as `SWSS_STATS:*`) to discover all rows for that component without an allow-list.
- **Hash, never string.** Field names are metric names; values are decimal `uint64`. Telegraf can call `HGETALL` and produce one measurement per (key, field) pair.
- **Idle suppression.** A row is `HSET` only when at least one of its metrics changed during the producer's 1 s cycle. Rows that did not change are not rewritten. Therefore an idle SONiC produces zero extra Redis traffic and telegraf, when configured to detect "no change since last poll", produces no upstream traffic either.
- **No TTL.** Keys are not expired; their lifetime is the producer process. On container restart they are recreated by the next 1 s flush.
- **No deletion in v1.** Entities that disappear at the application layer leave their last `HSET` in Redis until the container restarts. Garbage collection is left to the application; the framework does not delete keys (this keeps the contract simple).

Example for `componentName="SWSS"`, entity `PORT_TABLE`:

```
redis-cli -n 2 HGETALL "SWSS_STATS:PORT_TABLE"
1) "SET"
2) "1283"
3) "DEL"
4) "17"
5) "COMPLETE"
6) "1300"
7) "ERROR"
8) "0"
```

The shape mirrors the existing `COUNTERS:*` keys produced by the Flex-Counter pipeline so that on-box tooling (`redis-cli`, `show ... stats`) needs no changes.

#### 7.2 SWSS metric design

When telegraf reads a `SWSS_STATS:<table>` hash from `COUNTERS_DB` and
forwards it via mdm, each `(key, field)` pair surfaces downstream as a
single metric with one label carrying the orchagent table name. The
SWSS facade emits the following four metrics:

| Metric Name           | Label List    | Description                                                                       |
|-----------------------|---------------|-----------------------------------------------------------------------------------|
| `SWSS_STATS_SET`      | `swss.table`  | Count of `SET` operations enqueued on the orchagent table named by the label.     |
| `SWSS_STATS_DEL`      | `swss.table`  | Count of `DEL` operations enqueued on the orchagent table named by the label.    |
| `SWSS_STATS_COMPLETE` | `swss.table`  | Count of operations that finished successfully on the table.                      |
| `SWSS_STATS_ERROR`    | `swss.table`  | Count of operations that finished with error on the table.                        |

Notes:

- All values are monotonically increasing `uint64` counters. Consumers
  compute rate-of-change; absolute values reset on container restart
  (see §10).
- The label value (`swss.table`) is the orchagent table identifier
  verbatim — e.g. `PORT_TABLE`, `VLAN_TABLE`, `ROUTE_TABLE` — so
  dashboards can filter on a specific table without parsing the Redis
  key.
- Mapping back to `COUNTERS_DB`: the metric `SWSS_STATS_<X>`
  corresponds to Redis key `SWSS_STATS:<entity>` with hash field
  `<X>`; the label value is the `<entity>` part of the key. See §7.1
  for the key layout and §7.4 for the dirty-tracking semantics that
  guarantee idle entities do not produce reporting traffic.

#### 7.3 Conventions for future components

When onboarding a new component (`gnmi`, `bmp`, `telemetry`, …) using
the framework:

1. Pick a stable, uppercase component name `C`. Counters land under
   `C_STATS:*` automatically and surface downstream as metrics named
   `C_STATS_<VERB>`.
2. Define a short, finite vocabulary of `<VERB>` names that describe
   the event classes the component cares about (e.g. `SUBSCRIBE`,
   `GET`, `SET`, `ERROR`). Avoid putting cardinality-heavy values
   (interface name, neighbour IP, gNMI path) inside the metric name;
   put them in the entity (`E`) so they become the label value
   downstream. Telegraf reads the entity from the Redis key and the
   metric from the hash field, so dashboards can pivot freely without
   metric-name explosion.
3. Document the vocabulary in the component's own HLD as a Metric
   Name | Label List | Description table, identical in shape to §7.2.
   A typical label name is `c.entity` for a generic component, or a
   domain-specific synonym such as `gnmi.path` / `bmp.peer` /
   `swss.table` when that reads better on dashboards.

No telegraf configuration change is required to onboard a new
component, provided telegraf is configured to scan `*_STATS:*` patterns
(NDM HLD §5.2.1).

#### 7.4 Interaction with the producer

The producer (specified in the Framework HLD) maintains a per-entity *version* counter that is bumped on every `increment()` / `setValue()`. The 1 s writer thread snapshots only entities whose version changed since the last cycle and issues one `HSET` per dirty entity. As a result:

- A row that has not changed since the previous cycle is **not** rewritten — telegraf and Redis monitoring both see this as no activity.
- A row that has changed even once is rewritten with the latest cumulative values, so the next `HGETALL` always returns the latest snapshot.
- There is no risk of telegraf reading a half-written row: each `HSET` is atomic on the Redis side, and a single `HSET` writes all fields of the entity together.

#### 7.5 Telegraf interface (consumed, not specified here)

Telegraf is expected to:

- Run on the switch alongside the SONiC containers (NDM HLD §5.2.2 "telegraf container").
- Scan `COUNTERS_DB` for keys matching `*_STATS:*`.
- Convert each `(key, field)` pair into a metric in the schema defined
  by §7.2 / §7.3 of this HLD: the metric name is
  `<UPPER(component)>_STATS_<field>`, the entity part of the Redis key
  becomes the label value, and the label name is component-specific
  (e.g. `swss.table` for SWSS — see §7.2). The hostname is attached as
  an additional label by telegraf itself.
- Forward to mdm.

The exact telegraf configuration (input plugin, polling interval, output to mdm) is owned by the NDM HLD §5.2.1. This HLD only commits to the schema described in §7.1 / §7.2 / §7.3.

### 8. SAI API

No SAI API changes are required. This HLD covers a Redis schema and an interface to a consumer agent; SAI is not involved.

### 9. Configuration and management

Not applicable. This HLD introduces no new CLI commands, YANG models, manifests, or `CONFIG_DB` schema. Operator-facing configuration of telegraf / mdm is documented in the NDM HLD.

### 10. Warmboot and Fastboot Design Impact

The Redis schema is process-local: keys live in `COUNTERS_DB` for the duration of the producer container. On warmboot / fastboot the producer container restarts, the keys are recreated at the next 1 s flush, and counters start again from zero (see Framework HLD §10). Telegraf treats the appearance of fresh keys as new measurements; consumers compute rate-of-change and tolerate the reset.

No boot-critical-chain dependency is added.

### 11. Memory Consumption

The reporting path adds no new in-container state beyond what the Framework HLD already describes for the DB sink (one Redis client per producer instance). Redis-side memory is bounded by the number of `(component, entity)` rows × the number of fields × the size of a `uint64` ASCII string; for the SWSS facade this is on the order of tens of rows × four fields.

Telegraf and mdm memory are owned by the NDM HLD.

### 12. Restrictions/Limitations

- The schema is hash-only. Field values are decimal `uint64` strings; non-numeric fields are not supported. Components that need richer types must use a different reporting path (out of scope).
- The schema does not encode metric units. Units are implicit in the metric name (events) for v1; if a future component needs to report bytes / seconds / etc. it should put the unit in the metric name (e.g. `BYTES_RX`) until a more elaborate schema is introduced.
- Entity names are opaque strings. They must be safe for use as a Redis key suffix and for use as an attribute value downstream; in practice all SONiC table names already satisfy this.
- No deletion in v1 (see §7.1). Stale rows accumulate until container restart.

### 13. Testing Requirements/Design

#### 13.1 Unit / library tests

The library-level invariants (`HSET` on dirty entities, idle suppression, field naming) are covered by the Framework HLD unit-test suite (`componentstats_ut.cpp`). No additional unit tests are introduced by this HLD.

#### 13.2 System tests

- Boot a `sonic-vs` image that includes the Framework HLD's two companion PRs.
- Exercise orchagent so that the SWSS facade increments counters (e.g. `config vlan add`, `config interface ip add`).
- Verify the schema directly in Redis:
  ```
  redis-cli -n 2 KEYS    "SWSS_STATS:*"
  redis-cli -n 2 HGETALL "SWSS_STATS:PORT_TABLE"
  ```
  Confirm that:
  - The key shape matches §7.1.
  - All four SWSS fields (`SET`, `DEL`, `COMPLETE`, `ERROR`) are present and are decimal integers.
  - After a quiescent dwell, no `HSET` traffic is observed (idle suppression).
- End-to-end with telegraf (on a testbed configured per the NDM HLD):
  exercise orchagent and confirm the four metrics defined in §7.2
  (`SWSS_STATS_SET` / `SWSS_STATS_DEL` / `SWSS_STATS_COMPLETE` /
  `SWSS_STATS_ERROR`) arrive in Geneva carrying the `swss.table` label
  for the exercised orchagent tables.

### 14. Open/Action items

- The single reporting path in this revision is `COUNTERS_DB -> telegraf -> mdm -> Geneva`. Direct OTLP export from the application (the `OpenTelemetry SDK -> mdm` path described in NDM HLD §4) is a possible future addition; it would be specified in a future revision of this document if and when SONiC components need lower reporting latency than 1 s polling can provide.
- Garbage collection of stale `*_STATS:<entity>` keys on long-lived containers is left for a future revision. The current behaviour (cleared on container restart) is sufficient for the planned consumers.
- When additional components (`gnmi`, `bmp`, `telemetry`, …) adopt the framework, each one should add its vocabulary table to §7.3 by a small follow-up PR on this HLD.

