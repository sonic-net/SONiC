# SONiC Component Statistics — Framework HLD

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

| Rev | Date       | Author        | Change Description                                   |
|-----|------------|---------------|------------------------------------------------------|
| 0.1 | 2026-04-28 | Yutong Zhang  | Initial revision                                     |
| 0.2 | 2026-05-12 | Yutong Zhang  | Split out the reporting pipeline into a separate HLD |
| 0.3 | 2026-05-27 | Yutong Zhang  | Trim inline code, focus on metric design tables      |
| 0.4 | 2026-05-27 | Yutong Zhang  | Clarify Metric / Label terminology in §3             |
| 0.5 | 2026-05-27 | Yutong Zhang  | Clarify §7.8 facade LoC vs SwssStats LoC discrepancy |

### 2. Scope

This HLD specifies a reusable producer-side mechanism for **service-level (control-plane software) counters** in SONiC containers. It introduces:

1. A new shared library `swss::ComponentStats` in `sonic-swss-common`.
2. A SWSS-specific facade `SwssStats` in `sonic-swss` built on top of that library, which is the first consumer.

The library publishes counters into `COUNTERS_DB` so that:

- on-box diagnostic tooling (`redis-cli`, `show ... stats`) keeps working with no new transport, and
- off-box telemetry consumers can pick the counters up via the reporting pipeline described in the companion HLD.

**This HLD owns the producer side only**: the library, the facade pattern, the hot-path / threading / memory-ordering design, and warmboot / memory / testing concerns for the library itself. The reporting pipeline (how counters travel from `COUNTERS_DB` to Geneva or other off-box telemetry systems) is specified in the companion HLD:

- [Component Statistics — Reporting HLD](./component-stats-reporting-hld.md)

### 3. Definitions/Abbreviations

| Term            | Definition                                                                                  |
|-----------------|---------------------------------------------------------------------------------------------|
| Component       | A SONiC container that produces service-level counters (e.g. `swss`, `gnmi`, `bmp`).        |
| Entity          | A logical grouping of metrics inside a component (e.g. an orchagent table, a gNMI path).    |
| Metric          | A named uint64 counter or gauge inside an entity (e.g. `SET`, `DEL`, `COMPLETE`, `ERROR`). Stored as a Redis hash field on the producer side; surfaces downstream as a wire metric named `<COMPONENT>_STATS_<metric>` — see the [Reporting HLD §7.2](./component-stats-reporting-hld.md#72-swss-metric-design) for the wire schema. |
| Label           | A key/value attribute attached to a wire metric by telegraf. The entity name (the part after the `:` in the Redis key) is surfaced as a component-specific label such as `swss.table`. |
| ComponentStats  | The new shared library in `sonic-swss-common` providing the producer mechanism.             |
| SwssStats       | A SWSS-specific facade over `ComponentStats` (lives in `sonic-swss`).                       |
| DB sink         | The output path that mirrors counters into `COUNTERS_DB`.                                   |

### 4. Overview

SONiC already publishes **dataplane** counters via the Flex-Counter framework (`CONFIG_DB / FLEX_COUNTER_TABLE` -> `syncd` -> `COUNTERS_DB`). What is missing is **service-level** counters — software-side events such as orchagent task throughput, gNMI request rate, BMP message error counts. Without these we cannot answer questions like *"is orchagent draining tasks?"*, *"is gNMI seeing subscribe failures?"*, *"is one container dropping more events than its peers?"*.

A naive implementation would put this plumbing — atomic counters, dirty tracking, a 1-second writer thread, and a Redis-side schema — directly inside each container. That is unacceptable: every container would need its own concurrency review, bug fixes would drift, and the on-the-wire schemas would diverge.

This HLD specifies a single, reusable producer that:

1. accumulates counters in process-local atomic state with negligible hot-path cost,
2. mirrors them to `COUNTERS_DB` so `redis-cli`, `show ... stats` CLIs, and any other on-box tooling continue to work,
3. exposes a stable public API so each container only needs to write a thin (~100 LoC) facade.

How the `COUNTERS_DB` rows then reach Geneva or any other off-box system is the responsibility of the [Reporting HLD](./component-stats-reporting-hld.md).

### 5. Requirements

**Functional**

- R1. A reusable C++ library shall accumulate per-component, per-entity, per-metric `uint64` counters.
- R2. The library shall publish counters to `COUNTERS_DB` under a uniform key layout `<COMPONENT>_STATS:<entity>` (Redis hash, fields = metric names, values = decimal `uint64`). The exact key/field contract is normatively defined in the Reporting HLD.
- R3. The library shall be usable by any SONiC container by writing a thin facade that owns only the container-specific metric vocabulary.
- R4. The first consumer of the library is the SWSS-specific facade `SwssStats` (in `sonic-swss/orchagent/`), which exposes a small SWSS-specific public surface: a global `gSwssStatsRecord` enable flag, `SwssStats::getInstance()`, and `recordTask` / `recordComplete` / `recordError` methods.
- R5. The `SwssStats` facade shall write into `COUNTERS_DB` under keys `SWSS_STATS:<table>` with hash fields `SET` / `DEL` / `COMPLETE` / `ERROR`, following the uniform schema in R2.

**Non-functional**

- R6. The hot path (`increment` / `setValue`) shall be lock-free and constant-time after the first use of a given (entity, metric) pair.
- R7. Construction of a `ComponentStats` instance shall not crash the host process if Redis is not yet reachable; the sink shall connect lazily and retry independently.
- R8. A failure in the sink (Redis down) shall not affect the hot path. After recovery, no monotonic data point shall be lost beyond intermediate samples (the next successful flush carries the latest cumulative value).
- R9. Idle systems shall produce zero outbound traffic on the sink (driven by per-entity dirty tracking).

**Out of scope**

- The reporting pipeline that consumes the `COUNTERS_DB` rows (telegraf, mdm, Geneva, etc.) — see the [Reporting HLD](./component-stats-reporting-hld.md).
- Replacing existing FlexCounter / SAI counter pipelines (those measure dataplane state via SAI; this design measures control-plane software events).
- Defining the metric vocabulary for non-swss containers (`gnmi`, `bmp`, `telemetry`, …); this is left as future work.

### 6. Architecture Design

The architecture is unchanged at the SONiC system level. A new library is introduced in `sonic-swss-common`, and a new SWSS-specific facade (its first consumer) is added in `sonic-swss`; future containers may add their own facades using the same library.

```
+---------------------------- SONiC switch ------------------------------+
|                                                                        |
|  orchagent (sonic-swss)         gnmi / bmp / telemetry / ...           |
|   +----------------------+       +----------------------+              |
|   | orch.cpp + SwssStats |  ...  | gnmistats / bmpstats |              |
|   +----------+-----------+       +----------+-----------+              |
|              | instrument                   |                          |
|              v                               v                          |
|   +----------------------------------------------------------+         |
|   |      swss::ComponentStats   (in libswsscommon)           |         |
|   |   +---------------------------------------------------+  |         |
|   |   | atomic counters + dirty tracking + writer thread  |  |         |
|   |   +-------------------------+-------------------------+  |         |
|   |                             |                            |         |
|   |                          DB sink                         |         |
|   |                  (Redis HSET via swss::Table)            |         |
|   +-----------------------------+----------------------------+         |
|                                 |                                      |
|                                 v                                      |
|                    +-------------------------+                         |
|                    | COUNTERS_DB             |                         |
|                    |  SWSS_STATS:PORT_TABLE  |                         |
|                    |  GNMI_STATS:/iface/...  |                         |
|                    |  BMP_STATS:...          |                         |
|                    |                         |                         |
|                    |  used by:               |                         |
|                    |   - redis-cli           |                         |
|                    |   - show stats CLI      |                         |
|                    |   - reporting pipeline  | --> see Reporting HLD   |
|                    +-------------------------+                         |
+------------------------------------------------------------------------+
```

**Layering rule.** `swss-common` knows nothing of orchagent or any specific container; each container knows only its own facade plus `swss::ComponentStats`. New containers get the sink for free by writing a ~100-line wrapper.

**Sink design properties.**

- *One source of truth.* The sink consumes the atomic-counter snapshot inside `ComponentStats`.
- *No new transport for local debugging.* The `COUNTERS_DB` layout follows the existing convention so `redis-cli`, `show ... stats` CLIs, and any in-band tooling keep working.
- *Sink isolation from hot path.* Failures in the sink (Redis unreachable) do not affect the hot path; they are logged and retried.

### 7. High-Level Design

#### 7.1 Repositories changed

| Repository                     | What changes                                                                |
|--------------------------------|-----------------------------------------------------------------------------|
| `sonic-net/sonic-swss-common`  | New library `swss::ComponentStats` + unit tests ([PR #1180](https://github.com/sonic-net/sonic-swss-common/pull/1180)). |
| `sonic-net/sonic-swss`         | New `SwssStats` thin facade over `ComponentStats` in `orchagent/` ([PR #4516](https://github.com/sonic-net/sonic-swss/pull/4516)). |

No platform-specific code is added. No SAI changes. No syncd changes.

#### 7.2 `swss::ComponentStats` — public API

```cpp
namespace swss {

class ComponentStats {
public:
  using CounterSnapshot = std::map<std::string, uint64_t>;

  // Sink configuration. The DB sink is on by default; additional
  // sinks (e.g. OTLP) may be added by future revisions and are kept
  // off by default.
  struct SinkConfig {
    bool enableDb = true;   // mirror to COUNTERS_DB
  };

  static std::shared_ptr<ComponentStats> create(
      const std::string& componentName,
      const std::string& dbName      = "COUNTERS_DB",
      uint32_t           intervalSec = 1,
      const SinkConfig&  sinks       = SinkConfig{});

  void increment(const std::string& entity, const std::string& metric, uint64_t n = 1);
  void setValue (const std::string& entity, const std::string& metric, uint64_t value);

  uint64_t        get   (const std::string& entity, const std::string& metric);
  CounterSnapshot getAll(const std::string& entity);

  void setEnabled(bool on);
  bool isEnabled() const;
  void stop();
};

} // namespace swss
```

`create()` consults a process-wide registry keyed by `componentName`. A second call with the same name returns the existing instance, ensuring containers cannot accidentally start multiple writer threads against the same Redis prefix.

#### 7.3 Internal state

Per instance:
- `m_entities : std::map<string, EntityStats>` — `std::map` (not `unordered_map`) so references returned by `getOrCreateEntity` remain valid after later inserts.
- `EntityStats` holds `map<string, unique_ptr<Counter>>` (heap-allocated because `std::atomic<uint64_t>` is not movable) plus a per-entity `atomic<uint64_t> version`.
- `m_mutex` guards only the **structure** of the maps (insert/find). Hot-path reads/writes of counter values use `std::atomic` and skip the mutex after the first use.
- `m_running`, `m_enabled` — atomic flags.
- `m_cv` — wakes the writer thread immediately on `stop()` instead of waiting up to `intervalSec`.
- `m_thread` — owns the writer.

Process-wide:
- `registry : std::map<string, weak_ptr<ComponentStats>>` (`weak_ptr` so a fully released instance can be destroyed).

#### 7.4 Hot path

After the first use of a given `(entity, metric)` pair, `increment()` does
exactly two atomic RMWs and nothing else:

1. **Relaxed `fetch_add`** on the counter value — accumulates the event.
2. **Release `fetch_add`** on the per-entity *version* — marks the entity
   dirty and publishes the new counter value to the writer thread.
   Pairs with the writer's acquire-load (see §7.6).

No mutex acquisition, no allocation, no syscall on the hot path. The
structural mutex is taken only the first time a given `(entity, metric)`
pair is seen, to insert it into the per-entity map.

#### 7.5 Writer thread

Runs at `intervalSec` (default 1 s) and flushes the snapshot to the DB sink:

```
+---------------------------------------------------------------+
| Phase A - connect the DB sink (run once, with retry)          |
|   loop until m_running == false:                              |
|     if !dbConnected: try connect Redis                        |
|     if connected: break                                       |
|     else cv.wait_for(intervalSec, predicate=!m_running)       |
+---------------------------------------------------------------+
+---------------------------------------------------------------+
| Phase B - flush loop                                          |
|   loop:                                                       |
|     cv.wait_for(intervalSec, predicate=!m_running)            |
|     if !m_running: break                                      |
|                                                               |
|     # SNAPSHOT (under lock)                                   |
|     for each entity e in m_entities:                          |
|       v = e.version.load(acquire)              <- pairs (2)   |
|       if lastVersion[e.name] == v: continue   (skip clean)    |
|       lastVersion[e.name] = v                                 |
|       row = [(metric, c.value.load(relaxed)) for c in e]      |
|       enqueue(name, row)                                      |
|                                                               |
|     # FAN-OUT (lock released)                                 |
|     for (name, row) in queue:                                 |
|       try: m_table->set(name, stringify(row))                 |
|       catch: log warn, continue                               |
+---------------------------------------------------------------+
```

Three properties:

1. *Lock released before any I/O.* Round-trips under the structural lock would briefly stall every concurrent `increment()`.
2. *Idle systems generate zero outbound traffic.* When no entity has changed, the queue is empty and the sink is not touched.
3. *Hot-path isolation.* A sink failure is logged and skipped; the hot path is never blocked.

#### 7.6 Memory ordering correctness

The release/acquire pair ((2) in 7.4 ↔ acquire-load in 7.5) guarantees:

> If the writer reads `version == N`, then every counter mutation that contributed to bumping the version up to `N` has already happened-before the reader and is visible.

Without it, on weakly ordered architectures (ARM, POWER) the writer could see the new version but read an old counter value, recording a stale snapshot.

#### 7.7 `SwssStats` thin facade

`SwssStats` (in `sonic-swss/orchagent/`) is a ~130-line translation layer
that owns only the SWSS-specific vocabulary and the global
`gSwssStatsRecord` enable flag consumed by `orch.cpp`. Every call
delegates directly to `swss::ComponentStats::increment()`:

| `SwssStats` call            | Delegates to                      | Reports as (see Reporting HLD §7.2) |
|-----------------------------|-----------------------------------|--------------------------------------|
| `recordTask(t, "SET")`      | `increment(t, "SET")`             | `SWSS_STATS_SET{swss.table=t}`       |
| `recordTask(t, "DEL")`      | `increment(t, "DEL")`             | `SWSS_STATS_DEL{swss.table=t}`       |
| `recordComplete(t, n)`      | `increment(t, "COMPLETE", n)`     | `SWSS_STATS_COMPLETE{swss.table=t}`  |
| `recordError(t, n)`         | `increment(t, "ERROR", n)`        | `SWSS_STATS_ERROR{swss.table=t}`     |

The public surface (`gSwssStatsRecord`, `SwssStats::getInstance()`,
`recordTask` / `recordComplete` / `recordError`) and the on-the-wire
`SWSS_STATS:<table>` Redis layout are deliberately kept narrow and
stable so the SWSS vocabulary remains independent of future evolution
of the underlying `ComponentStats` library.

The full SWSS metric design (metric names, labels, descriptions) and
the exact `SWSS_STATS:<table>` Redis schema are owned by the
[Reporting HLD §7.2](./component-stats-reporting-hld.md#72-swss-metric-design),
which is the contract with downstream consumers.

#### 7.8 Adopting the library in a new container

A new component `C` adopts the framework by:

1. Picking an uppercase component name `C`. Counters automatically land in
   `COUNTERS_DB` under `C_STATS:*` and surface downstream as metrics
   named `C_STATS_<VERB>` with one label per entity.
2. **Designing a finite vocabulary** of verb-style metric names for the
   events the component cares about. Anything high-cardinality
   (interface name, neighbour IP, gNMI path, BMP peer) **must** go into
   the entity (the part after the `:` in the Redis key) rather than the
   metric name, so that dashboards can pivot on the label without
   explosion in metric count. See
   [Reporting HLD §7.3](./component-stats-reporting-hld.md#73-conventions-for-future-components)
   for the rationale.
3. Documenting that vocabulary as a Metric Name | Label List |
   Description table in the component's own HLD, identical in shape to
   the SWSS table in Reporting HLD §7.2.
4. Writing a thin facade that calls
   `swss::ComponentStats::increment()` for each event.
   A minimal facade needs only ~30 LoC. The SwssStats facade is larger
   (~130 LoC) because it also integrates a `gSwssStatsRecord` enable flag
   and a singleton into orchagent's existing `orch.cpp` infrastructure;
   new containers that do not need that extra plumbing stay near ~30 LoC.

No new threads, no new Redis client management, no new test harness
needed. Reporting picks the metrics up automatically via the
`*_STATS:*` pattern match.

Illustrative future vocabulary for `gnmi` (to be finalised when the
gNMI facade lands):

| Metric Name             | Label List   | Description                                                  |
|-------------------------|--------------|--------------------------------------------------------------|
| `GNMI_STATS_SUBSCRIBE`  | `gnmi.path`  | Number of `Subscribe` requests received on the path.         |
| `GNMI_STATS_GET`        | `gnmi.path`  | Number of `Get` RPCs handled on the path.                    |
| `GNMI_STATS_SET`        | `gnmi.path`  | Number of `Set` RPCs handled on the path.                    |
| `GNMI_STATS_ERROR`      | `gnmi.path`  | Number of RPCs that returned an error on the path.           |

### 8. SAI API

No SAI API changes are required for this feature. This design measures control-plane software events inside SONiC containers; it does not query or modify any SAI state.

### 9. Configuration and management

Not applicable. This HLD introduces no new CLI commands, YANG models, manifests, or `CONFIG_DB` schema. Existing CLIs that already read `COUNTERS_DB` (e.g. `redis-cli -n 2 HGETALL`, `show ... stats` style commands) continue to work and gain visibility into the new `<COMPONENT>_STATS:<entity>` keys for free.

### 10. Warmboot and Fastboot Design Impact

Counters are kept in process memory and are reset on container restart, including warmboot and fastboot. This is acceptable because consumers (dashboards, alerts) compute rate-of-change rather than absolute values.

#### Warmboot and Fastboot Performance Impact

- The library does **not** add any stalls, sleeps, or I/O operations to the boot critical chain. Construction is non-blocking; the writer thread connects to Redis lazily and retries in the background, so a not-yet-ready dependency cannot delay container start.
- No CPU-heavy processing (Jinja templates, etc.) is added in the boot path.
- No third-party dependency is updated by this HLD.
- The library does not delay any service or Docker container.

No measurable boot-time degradation is expected.

### 11. Memory Consumption

- Per-instance footprint: O(entities × metrics) `uint64` slots plus their `std::map` keys. Bounded by the number of orchagent tables (≈ tens) for the SWSS facade.
- When the feature is disabled at runtime via `setEnabled(false)`, the hot path becomes inert and the writer thread's queue stays empty; memory remains bounded.

### 12. Restrictions/Limitations

- Counters reset to zero on container restart by design. Consumers must compute rate-of-change rather than rely on absolute values across restarts.
- The library does not retain history; it relies on downstream consumers (`COUNTERS_DB` readers, the reporting pipeline) for retention.
- The structural mutex (`m_mutex`) is acquired only on the *first* use of a given (entity, metric) pair. Workloads that constantly mint new entity names will see one mutex acquisition per new name; this is not the expected pattern for SONiC containers.

### 13. Testing Requirements/Design

#### 13.1 Unit Test cases

Library unit tests live in `sonic-swss-common/tests/componentstats_ut.cpp`:

| # | Test                       | What it proves                                                                              |
|---|----------------------------|---------------------------------------------------------------------------------------------|
| 1 | BasicIncrement             | `increment` + `get` round-trip                                                              |
| 2 | MultipleMetrics            | metric isolation within an entity                                                           |
| 3 | MultipleEntities           | entity isolation within a component                                                         |
| 4 | SetValueOverwrites         | gauge semantics                                                                             |
| 5 | DisabledIsNoOp             | `setEnabled(false)` makes hot path inert                                                    |
| 6 | GetAllReturnsSnapshot      | bulk read returns the right shape                                                           |
| 7 | ConcurrentIncrements       | 8 threads × 10 000 increments → exactly 80 000 (no torn writes, no lost updates)            |
| 8 | SingletonSameName          | `create("X")` returns the same instance                                                     |
| 9 | SingletonDifferentNames    | `create("X") ≠ create("Y")`                                                                 |

A facade-level test suite `swssstats_ut.cpp` (9 cases) is added in `sonic-swss` and exercises the SwssStats vocabulary (`recordTask`/`recordComplete`/`recordError`, `gSwssStatsRecord` enable flag, singleton behaviour) end-to-end against the new backend.

Run:

```
cd sonic-swss-common && ./autogen.sh && ./configure && make check
./tests/tests --gtest_filter='ComponentStats*'
```

#### 13.2 System Test cases

- Boot a `sonic-vs` image built with the two companion PRs.
- Exercise orchagent (e.g. `config vlan add`, `config interface ip add`).
- Verify on-box DB sink:
  ```
  redis-cli -n 2 KEYS    "SWSS_STATS:*"
  redis-cli -n 2 HGETALL "SWSS_STATS:PORT_TABLE"
  ```
  Counters increment in proportion to operations; idle dwell shows zero further writes (dirty tracking working).
- Confirm warmboot and fastboot are unaffected (no boot-time regression, no service startup ordering change).

End-to-end validation of the reporting path (telegraf → mdm → Geneva) is covered in the [Reporting HLD](./component-stats-reporting-hld.md).

### 14. Open/Action items

- Phase 1 (this HLD's two PRs) lands the `ComponentStats` library and the `SwssStats` facade with the DB sink fully active.
- Phase 2 onboards additional SONiC containers (`gnmi`, `bmp`, `telemetry`, …) by adding their own facades. Each is a self-contained PR in the relevant repository.
- Phase 3 (future) may add direct OTLP export from the library to a local agent for components that need lower reporting latency than the DB → telegraf path provides. Out of scope for this HLD.



