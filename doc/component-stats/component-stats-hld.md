# SONiC Component Statistics HLD

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

| Rev | Date       | Author        | Change Description       |
|-----|------------|---------------|--------------------------|
| 0.1 | 2026-04-28 | Yutong Zhang  | Initial draft            |

### 2. Scope

This HLD specifies a reusable mechanism for exposing **service-level (control-plane software) counters** from SONiC containers. It introduces a new shared library `swss::ComponentStats` in `sonic-swss-common` and refactors the existing `SwssStats` class in `sonic-swss` (introduced by [sonic-swss#4434](https://github.com/sonic-net/sonic-swss/pull/4434)) into a thin façade over the new library. The library publishes counters to:

1. `COUNTERS_DB`, for parity with the existing Flex-Counter pipeline and for on-box diagnostic tooling (`redis-cli`, `show ... stats`).
2. A local OpenTelemetry (OTLP) Collector sidecar, so the same counters can be forwarded to off-box telemetry systems (e.g. Geneva mdm) that consume OTLP.

Configuration of the OTel Collector itself, off-box telemetry endpoints, dashboards, and alerts are explicitly **out of scope** for this HLD.

### 3. Definitions/Abbreviations

| Term            | Definition                                                                                  |
|-----------------|---------------------------------------------------------------------------------------------|
| Component       | A SONiC container that produces service-level counters (e.g. `swss`, `gnmi`, `bmp`).        |
| Entity          | A logical grouping of metrics inside a component (e.g. an orchagent table, a gNMI path).    |
| Metric          | A named uint64 counter or gauge inside an entity (e.g. `SET`, `DEL`, `COMPLETE`, `ERROR`).  |
| ComponentStats  | The new shared library in `sonic-swss-common` providing the producer mechanism.             |
| SwssStats       | A SWSS-specific façade over `ComponentStats` (lives in `sonic-swss`).                       |
| DB sink         | The output path that mirrors counters into `COUNTERS_DB`.                                   |
| OTLP sink       | The output path that exports counters via OpenTelemetry Protocol to a local OTel Collector. |
| OTel Collector  | A locally-running OpenTelemetry Collector sidecar; not delivered by this HLD.               |

### 4. Overview

SONiC already publishes **dataplane** counters via the Flex-Counter framework (`CONFIG_DB / FLEX_COUNTER_TABLE` → `syncd` → `COUNTERS_DB`). What is missing is **service-level** counters — software-side events such as orchagent task throughput, gNMI request rate, BMP message error counts. Without these we cannot answer questions like *"is orchagent draining tasks?"*, *"is gNMI seeing subscribe failures?"*, *"is one container dropping more events than its peers?"*.

A first attempt ([sonic-swss#4434](https://github.com/sonic-net/sonic-swss/pull/4434)) added a class `SwssStats` directly inside `orchagent`. The same plumbing — atomic counters, dirty tracking, a 1-second writer thread, a Redis-side schema — will be needed by every other SONiC container, and we additionally want to expose these counters via OTLP for off-box collection. Copy-pasting the implementation into each container is unacceptable: every container needs its own concurrency review, bug-fixes drift, and the on-the-wire schemas diverge.

This HLD specifies a single, reusable producer that:

1. accumulates counters in process-local atomic state with negligible hot-path cost,
2. mirrors them to `COUNTERS_DB` so `redis-cli`, `show ... stats` CLIs, and any other on-box tooling continue to work,
3. emits them as OTLP metrics to a local OTel Collector for forwarding to off-box telemetry systems,
4. exposes a stable public API so each container only needs to write a thin (~100 LoC) façade.

### 5. Requirements

**Functional**

- R1. A reusable C++ library shall accumulate per-component, per-entity, per-metric `uint64` counters.
- R2. The library shall publish counters to `COUNTERS_DB` under a uniform key layout `<COMPONENT>_STATS:<entity>` (Redis hash, fields = metric names, values = decimal `uint64`).
- R3. The library shall publish the same counters as OpenTelemetry OTLP records to a configurable endpoint (default `localhost:4317`).
- R4. The library shall be usable by any SONiC container by writing a thin façade that owns only the container-specific metric vocabulary.
- R5. The existing `SwssStats` public surface (`gSwssStatsRecord`, `SwssStats::getInstance()`, `recordTask/Complete/Error`) shall remain byte-identical to that introduced in #4434.
- R6. The `COUNTERS_DB` schema introduced by #4434 (`SWSS_STATS:<table>` hash with SET/DEL/COMPLETE/ERROR fields) shall remain unchanged.

**Non-functional**

- R7. The hot path (`increment` / `setValue`) shall be lock-free and constant-time after the first use of a given (entity, metric) pair.
- R8. Construction of a `ComponentStats` instance shall not crash the host process if Redis or the OTel Collector is not yet reachable; both sinks shall connect lazily and retry independently.
- R9. A failure in one sink (Redis down, OTel Collector restarting) shall not affect the other sink and shall not affect the hot path. After recovery, no monotonic data point shall be lost beyond intermediate samples (the next successful flush carries the latest cumulative value).
- R10. Idle systems shall produce zero outbound traffic on either sink (driven by per-entity dirty tracking).

**Out of scope**

- The OTel Collector itself, including its image, configuration, exporter pipeline to off-box telemetry systems, authentication, and operator onboarding.
- Replacing existing FlexCounter / SAI counter pipelines (those measure dataplane state via SAI; this design measures control-plane software events).
- Defining the metric vocabulary for non-swss containers — that is the job of each container's own façade.

### 6. Architecture Design

The architecture is unchanged at the SONiC system level. A single new library is introduced in `sonic-swss-common`; an existing class in `sonic-swss` is refactored to delegate to it; future containers may add their own façades using the same library.

```
┌────────────────────────────── SONiC switch ──────────────────────────────┐
│                                                                          │
│  orchagent (sonic-swss)            gnmi / bmp / telemetry / …            │
│   ┌──────────────────────┐          ┌──────────────────────┐             │
│   │ orch.cpp + SwssStats │   …      │ gnmistats / bmpstats │             │
│   └──────────┬───────────┘          └──────────┬───────────┘             │
│              │ instrument                      │                         │
│              ▼                                 ▼                         │
│   ┌────────────────────────────────────────────────────────────┐         │
│   │      swss::ComponentStats   (in libswsscommon)             │         │
│   │   ┌─────────────────────────────────────────────────────┐  │         │
│   │   │ atomic counters + dirty tracking + writer thread    │  │         │
│   │   └──────────────┬──────────────────────────┬───────────┘  │         │
│   │                  │                          │              │         │
│   │             DB sink                  OTLP sink             │         │
│   │     (Redis HSET via swss::Table)   (OTLP/gRPC, localhost)  │         │
│   └──────────┬──────────────────────────────────┬──────────────┘         │
│              │                                  │                        │
│              ▼                                  ▼                        │
│  ┌──────────────────────────┐      ┌────────────────────────────┐        │
│  │ COUNTERS_DB              │      │ Local OTel Collector       │        │
│  │  SWSS_STATS:PORT_TABLE   │      │  (sidecar container)       │        │
│  │  GNMI_STATS:/iface/…     │      │                            │        │
│  │  BMP_STATS:…             │      │   batches, retries, adds   │        │
│  │                          │      │   resource attrs, exports  │        │
│  │  used by: redis-cli,     │      │   to off-box telemetry     │        │
│  │  show stats CLI, local   │      └─────────────┬──────────────┘        │
│  │  diagnostic tools        │                    │                       │
│  └──────────────────────────┘                    │                       │
│                                                  │ OTLP                  │
└──────────────────────────────────────────────────┼───────────────────────┘
                                                   │
                                                   ▼
                                       ┌────────────────────┐
                                       │ Off-box telemetry  │
                                       │ (e.g. Geneva mdm)  │
                                       └────────────────────┘
```

**Layering rule.** `swss-common` knows nothing of orchagent or any specific container; each container knows only its own façade plus `swss::ComponentStats`. New containers get both sinks for free by writing a ~100-line wrapper.

**Dual-sink design properties.**

- *One source of truth.* Both sinks consume the same atomic-counter snapshot inside `ComponentStats`. They cannot diverge: if the OTel pipeline is briefly down, `COUNTERS_DB` still reflects current state, and vice versa.
- *No new transport for local debugging.* The `COUNTERS_DB` layout is unchanged, so `redis-cli`, `show ... stats` CLIs, and any existing in-band tooling keep working.
- *No off-box-system-specific code in containers.* Containers know only `ComponentStats`; the OTLP sink talks to a local OTel Collector at `localhost:4317`, and the Collector handles everything beyond that hop.
- *Independent failure domains.* Failures in one sink (DB unreachable, OTel agent restarting) do not affect the other or the hot path.

### 7. High-Level Design

#### 7.1 Repositories changed

| Repository                     | What changes                                                                |
|--------------------------------|-----------------------------------------------------------------------------|
| `sonic-net/sonic-swss-common`  | New library `swss::ComponentStats` + unit tests ([PR #1180](https://github.com/sonic-net/sonic-swss-common/pull/1180)). |
| `sonic-net/sonic-swss`         | `SwssStats` is reduced to a thin façade over `ComponentStats` ([PR #4516](https://github.com/sonic-net/sonic-swss/pull/4516)). |
| `sonic-net/sonic-buildimage`   | Submodule pointer bumps for the two repos above ([PR #26924](https://github.com/sonic-net/sonic-buildimage/pull/26924)). |

No platform-specific code is added. No SAI changes. No syncd changes.

#### 7.2 `swss::ComponentStats` — public API

```cpp
namespace swss {

class ComponentStats {
public:
  using CounterSnapshot = std::map<std::string, uint64_t>;

  // Sink configuration. Both sinks default to "on".
  struct SinkConfig {
    bool        enableDb     = true;             // mirror to COUNTERS_DB
    bool        enableOtlp   = true;             // export to local OTel Collector
    std::string otlpEndpoint = "localhost:4317"; // OTLP/gRPC endpoint
    std::string serviceName;                     // OTel resource attr (default: componentName)
    std::string serviceInstanceId;               // OTel resource attr (default: hostname)
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

```cpp
void ComponentStats::increment(const string& entity, const string& metric, uint64_t n) {
  if (!isEnabled() || n == 0) return;

  auto& e = getOrCreateEntity(entity);              // mutex on first use only
  auto& c = getOrCreateCounter(e, metric);          // mutex on first use only

  c.value  .fetch_add(n, memory_order_relaxed);     // ① counter
  e.version.fetch_add(1, memory_order_release);     // ② dirty-bump (release)
}
```

Cost after warm-up: two atomic RMWs. No mutex acquisition, no allocation, no syscall.

#### 7.5 Writer thread

Runs at `intervalSec` (default 1 s) and fans the snapshot out to both sinks:

```
┌───────────────────────────────────────────────────────────────┐
│ Phase A — connect each enabled sink (run once, with retry)    │
│   loop until m_running == false:                              │
│     if enableDb   and !dbConnected:   try connect Redis       │
│     if enableOtlp and !otlpConnected: try open OTLP exporter  │
│     if all enabled sinks connected: break                     │
│     else cv.wait_for(intervalSec, predicate=!m_running)       │
└───────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────┐
│ Phase B — flush loop                                          │
│   loop:                                                       │
│     cv.wait_for(intervalSec, predicate=!m_running)            │
│     if !m_running: break                                      │
│                                                               │
│     # SNAPSHOT (under lock) — single snapshot, two sinks      │
│     for each entity e in m_entities:                          │
│       v = e.version.load(acquire)                  ← pairs ② │
│       if lastVersion[e.name] == v: continue       (skip clean)│
│       lastVersion[e.name] = v                                 │
│       row = [(metric, c.value.load(relaxed)) for c in e]      │
│       enqueue(name, row)                                      │
│                                                               │
│     # FAN-OUT (lock released, sinks fail independently)       │
│     if enableDb:                                              │
│       for (name, row) in queue:                               │
│         try: m_table->set(name, stringify(row))               │
│         catch: log warn, continue                             │
│                                                               │
│     if enableOtlp:                                            │
│       build OTLP ResourceMetrics{ … } from queue              │
│       try: m_otlp->Export(batch)                              │
│       catch: log warn, continue                               │
└───────────────────────────────────────────────────────────────┘
```

Three properties:

1. *Lock released before any I/O.* Round-trips under the structural lock would briefly stall every concurrent `increment()`.
2. *Idle systems generate zero outbound traffic on either sink.* When no entity has changed, the queue is empty and neither sink is touched.
3. *Sink isolation.* A failure in one sink is logged and skipped; the other sink still publishes the same cycle's snapshot.

#### 7.6 Memory ordering correctness

The release/acquire pair (`②` in 7.4 ↔ acquire-load in 7.5) guarantees:

> If the writer reads `version == N`, then every counter mutation that contributed to bumping the version up to `N` has already happened-before the reader and is visible.

Without it, on weakly ordered architectures (ARM, POWER) the writer could see the new version but read an old counter value, recording a stale snapshot.

#### 7.7 OTLP sink details

- **Wire format.** OTLP/gRPC over plaintext `localhost:4317`. No TLS or authentication on the local hop — the loopback link is inside the switch, and any off-box credentials live in the OTel Collector. OTLP/HTTP is supported as a build option but not the default.
- **Metric model.** Counters set via `increment()` are exported as OTLP `Sum` with `aggregation_temporality = CUMULATIVE` and `is_monotonic = true`. Counters set via `setValue()` (gauges) are exported as OTLP `Gauge`.
- **Resource attributes** attached to every batch: `service.name=<component>`, `service.instance.id=<hostname>`, `sonic.component=<component>`.
- **Metric attributes** attached to every data point: `entity` — the table name / gNMI path / etc. The entity is a *label*, not part of the metric name, so dashboards can pivot freely.
- **Metric name** convention: `sonic.<component>.<metric>` (e.g. `sonic.swss.SET`, `sonic.gnmi.SUBSCRIBE`).
- **Batching / retry.** The producer does not batch beyond one `intervalSec` snapshot and does not retry. Batching, queuing, retrying, and back-pressure are the local OTel Collector's responsibility.
- **Container restart.** `start_time_unix_nano` is captured once in the constructor and advances on every container restart. This is the OTel-defined signal for counter reset; consumers handle it natively.

#### 7.8 `COUNTERS_DB` sink details

For component name `C` and entity `E`:

```
COUNTERS_DB key:    "<UPPER(C)>_STATS:<E>"
hash fields:        each metric name → uint64_t string
```

Example: `redis-cli -n 2 HGETALL "SWSS_STATS:PORT_TABLE"` →

```
1) "SET"
2) "1283"
3) "DEL"
4) "17"
5) "COMPLETE"
6) "1300"
7) "ERROR"
8) "0"
```

The shape mirrors the existing `COUNTERS:*` keys produced by the Flex-Counter pipeline.

#### 7.9 `SwssStats` thin façade

`SwssStats` (in `sonic-swss/orchagent/`) is reduced to a translation layer that owns only the SWSS-specific vocabulary and the global enable flag consumed by `orch.cpp`:

```cpp
SwssStats::SwssStats() : m_impl(swss::ComponentStats::create("SWSS")) {}

void SwssStats::recordTask(const std::string& t, const std::string& op) {
  if      (op == "SET") m_impl->increment(t, "SET");
  else if (op == "DEL") m_impl->increment(t, "DEL");
}
void SwssStats::recordComplete(const std::string& t, uint64_t n) { m_impl->increment(t, "COMPLETE", n); }
void SwssStats::recordError   (const std::string& t, uint64_t n) { m_impl->increment(t, "ERROR",    n); }
```

The whole file is ~130 lines of straightforward translation. **The public surface (`gSwssStatsRecord`, `SwssStats::getInstance()`, `recordTask`/`recordComplete`/`recordError`) and the on-the-wire `SWSS_STATS:<table>` Redis layout are byte-identical to those introduced in #4434.** Existing consumers keep working without changes.

#### 7.10 Adopting the library in a new container

To add equivalent metrics to e.g. `gnmi`, write a façade analogous to §7.9:

```cpp
class GnmiStats {
public:
  static GnmiStats* getInstance();
  void recordSubscribe(const std::string& path) { m_impl->increment(path, "SUBSCRIBE"); }
  void recordError    (const std::string& path) { m_impl->increment(path, "ERROR");     }
private:
  GnmiStats() : m_impl(swss::ComponentStats::create("GNMI")) {}
  std::shared_ptr<swss::ComponentStats> m_impl;
};
```

Result: counters land in `COUNTERS_DB` under keys `GNMI_STATS:<path>` **and** are exported as OTLP metrics `sonic.gnmi.SUBSCRIBE` / `sonic.gnmi.ERROR` (with attribute `entity=<path>`). No new threads, no new Redis or gRPC client management, no new test harness needed.

### 8. SAI API

No SAI API changes are required for this feature. This design measures control-plane software events inside SONiC containers; it does not query or modify any SAI state.

### 9. Configuration and management

#### 9.1 Manifest

Not applicable. This is a built-in SONiC library, not an Application Extension.

#### 9.2 CLI/YANG model Enhancements

No new CLI commands or YANG models are introduced by this HLD. Existing CLIs that already read `COUNTERS_DB` (e.g. `redis-cli -n 2 HGETALL`, `show ... stats` style commands) continue to work and gain visibility into the new `<COMPONENT>_STATS:<entity>` keys for free.

#### 9.3 Config DB Enhancements

A future enhancement may add a `COMPONENT_STATS` table in `CONFIG_DB`, keyed by component name, to allow operators to flip individual sinks on/off and to override the OTLP endpoint without rebuilding:

```
CONFIG_DB key:    COMPONENT_STATS|<component>
fields:           enable_db          : "true" | "false"
                  enable_otlp        : "true" | "false"
                  otlp_endpoint      : <host:port>
                  interval_sec       : <uint32>
```

The library reads the table once at construction time. Runtime re-configuration is not in scope for the first cut.

### 10. Warmboot and Fastboot Design Impact

Counters are kept in process memory and are reset on container restart, including warmboot and fastboot. This matches the existing behaviour of the `SwssStats` introduced in #4434, and is acceptable because consumers (dashboards, alerts) compute rate-of-change rather than absolute values. The OTLP `start_time_unix_nano` attribute advances on every restart, which is the OTel-standard signal for counter reset and is handled natively by OTel-aware consumers.

#### Warmboot and Fastboot Performance Impact

- The library does **not** add any stalls, sleeps, or I/O operations to the boot critical chain. Construction is non-blocking; the writer thread connects to Redis and to the OTel Collector lazily and retries in the background, so a not-yet-ready dependency cannot delay container start.
- No CPU-heavy processing (Jinja templates, etc.) is added in the boot path.
- No third-party dependency is updated by this HLD beyond linking against the OpenTelemetry C++ SDK gRPC exporter, which is loaded only when the OTLP sink is enabled.
- The library does not delay any service or Docker container.

No measurable boot-time degradation is expected.

### 11. Memory Consumption

- Per-instance footprint: O(entities × metrics) `uint64` slots plus their `std::map` keys. Bounded by the number of orchagent tables (≈ tens) for the SWSS façade.
- The OTLP exporter adds a small fixed overhead (one gRPC channel, one per-cycle batch buffer).
- When the feature is disabled at runtime via `setEnabled(false)`, the hot path becomes inert and the writer thread's queue stays empty; memory remains bounded.
- When the feature is disabled at compile time (the OTLP sink can be compiled out via build option), there is no residual memory cost beyond the symbols of `swss::ComponentStats` itself (the DB sink remains unconditional, matching #4434 behaviour).

### 12. Restrictions/Limitations

- Counters reset to zero on container restart by design. Consumers must compute rate-of-change rather than rely on absolute values across restarts.
- The library does not retain history; it relies on downstream consumers (`COUNTERS_DB` readers, OTel Collector) for retention.
- The OTLP sink depends on a local OTel Collector reachable at the configured endpoint. If absent, the OTLP sink retries silently in the background; the DB sink and the hot path are unaffected.
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

The existing `swssstats_ut.cpp` (9 cases) in `sonic-swss` is kept verbatim and continues to pass against the thin façade, proving the public API has not regressed.

Run:

```
cd sonic-swss-common && ./autogen.sh && ./configure && make check
./tests/tests --gtest_filter='ComponentStats*'
```

#### 13.2 System Test cases

- Boot a `sonic-vs` image built with the three companion PRs.
- Exercise orchagent (e.g. `config vlan add`, `config interface ip add`).
- Verify on-box DB sink:
  ```
  redis-cli -n 2 KEYS    "SWSS_STATS:*"
  redis-cli -n 2 HGETALL "SWSS_STATS:PORT_TABLE"
  ```
  Counters increment in proportion to operations; idle dwell shows zero further writes (dirty tracking working).
- Verify OTLP sink (Phase 2): point a local OTel Collector at `localhost:4317` with a debug exporter and confirm `sonic.swss.*` metrics arrive with correct resource and metric attributes.
- Confirm warmboot and fastboot are unaffected (no boot-time regression, no service startup ordering change).

### 14. Open/Action items

- Phase 1 (this HLD's three PRs) lands the `ComponentStats` library and `SwssStats` refactor with the DB sink fully active and the OTLP sink stubbed (`enableOtlp=false` by default).
- Phase 2 implements the OTLP sink against the OpenTelemetry C++ SDK and is gated on the local OTel Collector sidecar being available in `sonic-buildimage`. Coordination with whichever team owns the local OTel Collector image is required before Phase 2 can be enabled by default.
- Phase 3 onboards additional SONiC containers (`gnmi`, `bmp`, `telemetry`, …) by adding their own façades. Each is a self-contained PR in the relevant repository.
