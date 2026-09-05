<!-- omit in toc -->
# fpmsyncd → orchagent ZMQ Route Delivery (Producer Side) — High Level Design

<!-- omit in toc -->
## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions / Abbreviations](#3-definitions--abbreviations)
- [4. Overview](#4-overview)
  - [4.1 Problem A — silent route drop under burst (#28369)](#41-problem-a--silent-route-drop-under-burst-28369)
  - [4.2 Problem B — heap RSS ratchet (#28245)](#42-problem-b--heap-rss-ratchet-28245)
  - [4.3 Goals / Motivation](#43-goals--motivation)
- [5. Requirements](#5-requirements)
  - [5.1 Functional](#51-functional)
  - [5.2 Non-functional](#52-non-functional)
  - [5.3 Non-goals](#53-non-goals)
  - [5.4 Scale targets](#54-scale-targets)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Design overview](#71-design-overview)
  - [7.2 Coalescing from the async send thread](#72-coalescing-from-the-async-send-thread)
  - [7.3 Retention — retain-and-retry from the map](#73-retention--retain-and-retry-from-the-map)
  - [7.4 Chunked drain from the live map](#74-chunked-drain-from-the-live-map)
  - [7.5 Batch sizing — wire efficiency vs. coalescing yield](#75-batch-sizing--wire-efficiency-vs-coalescing-yield)
  - [7.6 Failure, retry and liveness](#76-failure-retry-and-liveness)
  - [7.7 Send-thread state machine](#77-send-thread-state-machine)
  - [7.8 Heap reclaim — allocator-managed (#28245)](#78-heap-reclaim--allocator-managed-28245)
  - [7.9 Relationship to the consumer-side design](#79-relationship-to-the-consumer-side-design)
  - [7.10 Telemetry and observability](#710-telemetry-and-observability)
  - [7.11 Repository / component change map](#711-repository--component-change-map)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI / YANG](#92-cli--yang)
  - [9.3 Config DB and tuning knobs](#93-config-db-and-tuning-knobs)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions / Limitations](#12-restrictions--limitations)
- [13. Testing Requirements / Design](#13-testing-requirements--design)
  - [13.1 Unit test cases](#131-unit-test-cases)
  - [13.2 Component A/B benchmark design](#132-component-ab-benchmark-design)
  - [13.3 System test cases](#133-system-test-cases)
- [14. Open / Action Items](#14-open--action-items)
- [15. References](#15-references)
- [Appendix A — Measured benchmark results](#appendix-a--measured-benchmark-results)
  - [A.1 Route delivery](#a1-route-delivery)
  - [A.2 Heap reclaim — allocator A/B](#a2-heap-reclaim--allocator-ab)

---

## 1. Revision

| Rev | Date        | Author          | Change Description                                              |
|:---:|:-----------:|:---------------:|:---------------------------------------------------------------|
| 0.1 | Jul 27 2026 | Deepak Singhal  | Initial HLD — producer-side route delivery, chunked drain, event-driven heap release, STATE_DB telemetry; component A/B results. |
| 0.2 | Aug 31 2026 | Deepak Singhal  | Heap reclaim moved from an fpmsyncd-managed idle-edge release (tcmalloc) to allocator-managed background reclaim (jemalloc `background_thread`), per the A/B in Appendix A.2; heap telemetry dropped in favour of a startup check. Review feedback: ZMQ-path applicability and Redis-path invariant, coalescing stated as Redis parity with an explicit `(table, key)` key and cross-table drain fairness, FPM offload-reply placement, zebra's unconditional RIB re-drive as the recovery basis, and the consumer-side design noted as landed upstream. |

---

## 2. Scope

This HLD covers the **producer side** of the fpmsyncd → orchagent route-delivery path in SONiC:
how fpmsyncd hands FRR/zebra route updates to `orchagent` over ZMQ. fpmsyncd consumes FRR/zebra's
FPM netlink stream (north) and produces route updates to orchagent over ZMQ (south); "producer"
refers to that ZMQ egress channel, the subject of this document. It specifies:

- **(a)** a non-blocking, coalescing, chunked send path that removes a class of **silent route drops**
  under burst ([sonic-buildimage #28369](https://github.com/sonic-net/sonic-buildimage/issues/28369));
- **(b)** an **allocator change** that returns burst-inflated memory to the OS with no
  application-managed release code
  ([sonic-buildimage #28245](https://github.com/sonic-net/sonic-buildimage/issues/28245)); and
- **(c)** the **STATE_DB telemetry** that makes route delivery observable.

**Applicability — the ZMQ route path only.** This design is active only where the ZMQ route path is
enabled (`SYSTEM_DEFAULTS|swss_zmq`, field `status` = `enabled`; an **absent key means disabled**).
With it disabled fpmsyncd uses the plain `ProducerStateTable`/Redis path, which this design leaves
**unchanged** (§7.1). Within fpmsyncd it governs the **route and label-route tables** — the tables
carried over ZMQ; tables on the plain producer keep their existing behavior. The scoping is
deliberate: #28369 is a failure of the ZMQ send path under socket back-pressure, while the Redis
path absorbs the same burst through a shared pipeline with server-side dedup (§7.2), so the thread
and map belong where the problem lives.

**Out of scope:** the *consumer* side (orchagent route ingestion), designed separately in
[sonic-net/SONiC #2328](https://github.com/sonic-net/SONiC/pull/2328) and implemented upstream in
[sonic-swss-common #1187](https://github.com/sonic-net/sonic-swss-common/pull/1187) and
[sonic-swss #4564](https://github.com/sonic-net/sonic-swss/pull/4564). The two designs are
architecturally independent: this producer-side design composes with the consumer-side one (§7.9)
but does not require it. No change to ZMQ HWM configuration or the single-message transport
ceiling.

---

## 3. Definitions / Abbreviations

| Term | Definition |
|------|------------|
| **fpmsyncd** | SONiC daemon that receives FRR route updates via the FPM (Forwarding Plane Manager) netlink channel and delivers them to orchagent over ZMQ (`APPL_DB` is written for debug only in the ZMQ path). |
| **FPM** | Forwarding Plane Manager — FRR's interface that streams zebra's forwarding-plane route updates (the selected/installed best paths, as netlink messages) to an external agent. |
| **RIB / FIB** | Routing Information Base (control-plane routes) / Forwarding Information Base (programmed ASIC routes). |
| **ZMQ** | ZeroMQ, the message transport between fpmsyncd (producer) and orchagent (consumer). |
| **SNDHWM / RCVHWM** | ZMQ send / receive High-Water-Mark — the per-socket queue depth (in messages) before back-pressure/`EAGAIN`. |
| **EAGAIN** | ZMQ "would block" — the socket send buffer is full; the write did not complete. |
| **Back-pressure** | Used in this document in the **transport** sense: the socket signalling `EAGAIN` so the *producer* stops writing. It does **not** mean flow control reaching zebra — the producer absorbs into the coalescing map instead of blocking ingest (R3), so this design does not throttle the RIB. Producer-side holding of unsent work is called **retention** (§7.3). |
| **Coalescing** | Collapsing multiple updates for the **same key** into one, keeping only the latest (last-writer-wins). |
| **LWW** | Last-Writer-Wins — the map-merge policy: a later op for a key overwrites the earlier one. |
| **HWM** | High-Water-Mark (see SNDHWM/RCVHWM). |
| **RIB replay** | fpmsyncd's route replay after a restart — on FPM reconnect zebra re-drives the **entire** RIB unconditionally (not only routes it believes are unacknowledged) and fpmsyncd re-produces the routes. |
| **RSS** | Resident Set Size — physical memory a process holds, as seen by the OS. |
| **glibc arena / auto-trim** | The heap region glibc allocates from, and its automatic reclaim: the arena contracts **only from the top**, and only once the free region at the top crosses a threshold, so free pages below a live allocation stay resident. |
| **jemalloc** | The allocator fpmsyncd links. Returns freed pages to the OS on a **decay** schedule and, with `background_thread` enabled, does that work on its own thread rather than on whichever application thread happened to call `free()`. |
| **`background_thread`** | jemalloc runtime option (`MALLOC_CONF`); when true, jemalloc runs page reclaim off the application's critical path, and reports whether it is active. |

---

## 4. Overview

fpmsyncd is the sole conduit from the FRR control plane to the SONiC data plane for routes. Its
producer-side send path has two independent defects that surface under **burst** (tens of
thousands of route updates in a short window) — a scale point SONiC routinely hits on session
flap, peer bounce, or a full-table refresh.

### 4.1 Problem A — silent route drop under burst (#28369)

In the baseline (pre-fix) implementation, fpmsyncd sends **one prefix per ZMQ message**, **inline
on its single main thread**. When a
burst fills the ZMQ send buffer, the send returns a would-block (`EAGAIN`); the code spins a **bounded**
inline retry ladder and, once the ladder exhausts, **silently drops** the route — nothing is
retained, nothing is logged or counted, and the process keeps running. The route never reaches
orchagent and is never retried, so
the ASIC FIB diverges from the RIB **with no signal**. Figure 1 traces the failure.

<p align="center">
  <img alt="Figure 1. The #28369 silent-drop chain: inline per-prefix send, EAGAIN ladder, silent drop, permanent FIB divergence." src="images/fpmsyncd_zmq_route_delivery/06_bug_droppath.png" width="620">
</p>
<p align="center"><b>Figure 1.</b> The #28369 silent-drop chain. The inline send blocks the main
thread; on sustained <code>EAGAIN</code> the bounded ladder exhausts and the route is
<b>dropped with nothing retained, no telemetry, and no crash</b> — the ASIC FIB diverges from the
RIB permanently. The same inline structure also makes <b>coalescing structurally impossible</b>:
two updates for one prefix are never co-resident (dashed edge).</p>

Two distinct gaps hide in that one path:

1. **No retention (the correctness bug).** When ZMQ is not writable the producer has nowhere to
   *hold* the update: it spins the ladder, then discards. The spin does stall FPM ingest, so the
   baseline pushes back on zebra *incidentally* — but only until the ladder's bound, after which the
   route is silently discarded. What is missing is retain-and-retry, and a signal when the producer
   gives up.
2. **No coalescing; per-prefix framing (the efficiency gap).** Every update is its own ZMQ
   message, so a burst of *N* updates costs *N* messages and nothing collapses redundant same-key
   churn (e.g. ECMP next-hop flap rewriting the same prefix repeatedly).

### 4.2 Problem B — heap RSS ratchet (#28245)

fpmsyncd's RSS climbs after each burst and never comes back down. glibc's main arena keeps freed
pages as **free-but-not-returned**; its automatic reclaim shrinks the arena **only from the top**
(and only once the top free region crosses the trim threshold) and never proactively returns freed
*interior* pages to the OS. A single long-lived allocation near the top **pins every free
page below it**, so a transient burst permanently inflates steady-state RSS → eventual
OOM-restart. Figure 2 shows the mechanism.

<p align="center">
  <img alt="Figure 2. glibc heap ratchet: a pinned top allocation blocks arena-top contraction, leaving interior free pages resident across bursts." src="images/fpmsyncd_zmq_route_delivery/07_heap_ratchet.png" width="720">
</p>
<p align="center"><b>Figure 2.</b> The #28245 RSS ratchet. glibc auto-trim contracts only the arena
top; a long-lived top allocation pins the interior free pages, so each burst leaves more
free-but-held memory and RSS climbs monotonically toward an eventual OOM-restart.</p>

### 4.3 Goals / Motivation

Both defects share a root cause: the producer does its work **inline on the FPM read path**, so a
slow socket becomes fpmsyncd's problem to absorb and a burst's memory becomes permanent. The design
therefore aims to:

- **Move the cost off the critical path.** Ingest should never wait on the wire, so a congested
  consumer slows delivery instead of destroying it.
- **Reduce work at the earliest point.** Collapsing same-key churn at the producer saves
  serialize-CPU, wire bytes, and consumer memory that no downstream fix can recover.
- **Make failure loud.** Where delivery genuinely cannot proceed, fail observably and recover —
  silent divergence is the defect being removed, so it must have no successor.
- **Leave memory where it started.** A burst should cost memory while it runs, not afterwards.
- **Keep the shared library generic.** Route-specific policy belongs in fpmsyncd, so other producers
  inherit the mechanism without inheriting route semantics.

These become the testable requirements in §5.

---

## 5. Requirements

RFC-2119 keywords. A requirement states an **outcome**; the mechanism that achieves it is a design
choice (§7) guarded by a test (§13).

### 5.1 Functional

- **R1.** fpmsyncd **shall not** silently drop a route update in any recoverable regime — the number
  of route updates lost **shall** be zero in all regimes. A deliberate assert-and-restart (R6)
  interrupts in-flight delivery, but zebra's full RIB re-drive on reconnect re-delivers those
  routes.
- **R2.** The producer **shall** retain un-sent route updates and retry them when the socket is
  not writable, rather than dropping them.
- **R3.** Route ingest (the FPM netlink read path) **shall not** block on the ZMQ socket.
- **R4.** Redundant same-key updates pending at send time **shall** be coalesced last-writer-wins
  before crossing the wire.
- **R5.** *(Design-induced, not a baseline problem: the pre-fix one-prefix-per-message path could
  never approach the ceiling.)* Because this design sends route updates in bulk messages, no
  individual wire message **shall** exceed the transport's single-message ceiling, and delivery of
  the full backlog **shall** still complete.
- **R6.** A prolonged unrecoverable stall **shall** produce an **observable** failure that survives
  the ensuing restart, never silent divergence.
- **R7.** fpmsyncd's steady-state RSS **shall not** ratchet across bursts: free heap left behind by a
  burst **shall** be returned to the OS.
- **R8.** The producer **shall** publish STATE_DB telemetry sufficient to answer, at a glance,
  "is the no-drop guarantee holding?" and "is there congestion?".

### 5.2 Non-functional

- **R9.** Telemetry publication **shall not** prevent fpmsyncd from starting, or crash it, if
  STATE_DB is unreachable at startup; publication **shall** degrade gracefully and resume once
  STATE_DB is reachable.
- **R10.** The `swss-common` change **shall** remain route-agnostic, so other producers using that
  library are unaffected.
- **R11.** Heap reclaim **shall not** measurably reduce route-delivery throughput, including while
  reclaim runs concurrently with a burst.
- **R12.** The design **shall** be backward compatible: no new CONFIG_DB schema, no CLI change, and
  it **shall** compose with the consumer-side design (§7.9) without requiring it.

### 5.3 Non-goals

1. **Bounding a flood of *distinct* prefixes** is out of scope — coalescing collapses nothing when
   every key differs; only retention + the assert bound protect that regime.
2. **Consumer-side changes** are out of scope — designed in
   [#2328](https://github.com/sonic-net/SONiC/pull/2328) (§7.9).
3. **Changing the Redis/`ProducerStateTable` route path** is out of scope — the design engages
   only where the ZMQ path is enabled (§2), and the Redis path already coalesces server-side (§7.2).
4. **Changing ZMQ HWM or the single-message transport ceiling** is out of scope — the design lives
   within the existing transport limits (R5, §7.5).
5. **A user-facing config surface** is a non-goal — the knobs (§9.3) are internal defaults tuned by
   benchmark, not CONFIG_DB. Adding a CLI/YANG surface is deferred to §14 if a need emerges.

### 5.4 Scale targets

- **R13.** The design **shall** sustain the full BGP table (order **10⁶** routes) and absorb a burst
  drain of **≥ 40,000** route updates without silent drop, staying within the transport's existing
  single-message ceiling (§7.5) and the map memory bound (§7.4).

---

## 6. Architecture Design

fpmsyncd is the FRR→orchagent route conduit — it consumes zebra's FPM netlink stream and produces
route updates to orchagent over ZMQ. This design keeps that daemon topology unchanged: all new code
lives inside fpmsyncd (`sonic-swss`), plus a small generic send-path guard in `sonic-swss-common`.
What changes is the **internal shape** of fpmsyncd's producer path — a coalescing map + a dedicated
send thread + a chunked drain replace the inline per-prefix send. Figure 3 shows where each piece
plugs in and the end-to-end dataflow.

<p align="center">
  <img alt="Figure 3. Producer→wire→consumer dataflow: coalescing map, dedicated send thread, chunked bulk drain under the generic swss-common guard, feeding the (separate) #2328 consumer." src="images/fpmsyncd_zmq_route_delivery/01_dataflow.png" width="880">
</p>
<p align="center"><b>Figure 3.</b> End-to-end dataflow. The FPM netlink thread only does a
non-blocking hand-off (last-writer-wins) into the coalescing map; a
<b>dedicated send thread</b> drains it in bounded chunks through the generic
<code>ZmqProducerStateTable</code> guard (swss-common slice). Green = coalescing points, yellow =
the generic send-path guard. The orchagent consumer (right) is a separate design, covered in §7.9.</p>

**Four load-bearing pieces, in priority order:**

| # | Piece | Role | Regime it matters most |
|---|---|---|---|
| 1 | **Retention** (retain-and-retry from the map) | the *bound* — never drop | consumer unavailable / socket not draining |
| 2 | **Assert + process exit + restart RIB replay** | bounded, observable failure | prolonged unrecoverable stall |
| 3 | **Coalescing map** (LWW) | earliest-possible work reduction | same-key churn |
| 4 | **Chunked bulk framing** | throughput + removes the 16 MiB cliff | every large drain |

---

## 7. High-Level Design

### 7.1 Design overview

The producer path is redesigned around a single principle: **decouple FPM ingest from ZMQ delivery,
and never let the delivery side drop a route.** Concretely, the inline "serialize-and-send each
prefix on the FPM thread" path is replaced by the following set of mechanisms, listed here in
dataflow order; each is detailed in the subsection noted.

1. **Asynchronous send thread** — the FPM thread hands each update off in microseconds and returns
   to reading netlink; a dedicated thread owns all ZMQ I/O, so ingest never blocks on the socket
   (§7.2).
2. **Coalescing map as the retain buffer** — updates land in a keyed, last-writer-wins (LWW) map
   (not a FIFO queue), so redundant same-key updates that are co-resident collapse to the latest
   before they ever cross the wire (§7.2).
3. **Retention by retain-and-retry** — when the socket is not writable the unsent work stays in
   the map and is retried, rather than being dropped; the map is the buffer and the bound (§7.3).
4. **Chunked bulk drain** — the send thread drains the map in bounded chunks (by entry count and by
   bytes), each chunk becoming one multipart wire message that stays under the transport's
   single-message ceiling (§7.4, §7.5).
5. **Bounded, observable failure** — a prolonged unrecoverable stall (or a map that exceeds its
   memory bound) produces a sticky STATE_DB assert record and a process exit for restart RIB-replay
   recovery, never silent divergence (§7.6, §7.7).
6. **Allocator-managed heap reclaim** — fpmsyncd links jemalloc with background reclaim enabled, so
   burst-inflated free heap is returned to the OS off the critical path, with no release code in
   fpmsyncd itself (§7.8).
7. **STATE_DB telemetry** — the producer publishes a read-only route-health record so the no-drop
   guarantee and congestion are observable at a glance (§7.10).

Coalescing, retention, and chunking are all properties of one structure — the async send thread
plus the coalescing map. §7.9 places this producer design alongside the separate consumer-side
design, and §7.11 maps each mechanism to the repository/component it lands in.

**Invariant — the ZMQ path gates the whole change.** A **single predicate** enforces the
applicability condition (§2): one "is there a ZMQ client?" test decides *both* whether the route
tables are `ZmqProducerStateTable` or plain `ProducerStateTable` *and* whether the coalescer and its
send thread are constructed. Because one test drives both, the coalescer is active exactly where the
ZMQ tables are; with the path disabled fpmsyncd runs as it does today — no map, no send thread, no
extra STATE_DB connector. Every route and label-route write site is reached through the same pair of
funnels, whose non-ZMQ branch is the original producer call.

Warm restart is a second, independent gate: reconciliation keeps its existing direct-write path and
the map stays empty until it completes, so the send thread is the **sole ZMQ writer at any
instant**. Tests cover both properties (§13.1).

### 7.2 Coalescing from the async send thread

> **In short:** coalescing restores **parity with the Redis path this design replaces**, and it
> falls out of the async send thread itself. While one send is on the wire, same-key updates pile
> into the live map and collapse to the latest; the effect grows with congestion.

**The Redis path already coalesces; the ZMQ path lost it.** On the plain `ProducerStateTable` path,
a write is applied server-side as a key added to the table's pending-key set plus a state hash
overwritten with the new field values. A key written twice before the consumer drains is therefore
delivered **once, with the latest value** — last-writer-wins, scoped per table. ZMQ carries messages
without server-side dedup, so moving routes onto it left that property behind: *N* updates to one
prefix became *N* wire messages. The coalescing map restores the semantics the route path
already had.

**The coalescing key is `(table, key)`.** The database is not part of the key — both route tables
live in `APPL_DB` — which mirrors Redis, whose dedup namespace is likewise per table. One wire
message never mixes tables, because the transport frames a single `(db, table)` per message, so
chunks are table-pure by construction.

**The drain is fair across tables.** The Redis path submits every table into one shared pipeline
that is flushed wholesale, so no table can starve another. The coalescer preserves that: each drain
cycle is a **single ordered pass covering both route tables**, rather than draining one to empty
before looking at the other. Fairness comes from the drain order itself: the liveness bound (§7.6)
observes only that *some* send is succeeding, a condition sustained churn on the larger table would
keep satisfying on its own while the other table starved.

Coalescing requires **dwell**: two updates for the same key must be resident in the map at the
same instant for the second to overwrite the first.

- **Inline (the bug):** the main thread serializes+sends route P, blocks on ZMQ, *then* reads the
  next FPM message. A and B for the same prefix are never co-resident, so the structure permits
  **no coalescing at all** (Figure 1, dashed edge).
- **Async send thread:** the main thread hands the update off (microseconds, non-blocking) and
  immediately returns to reading FPM. The send thread is off doing one send, which takes real
  wall-clock time. **During that send, the map is live and every FPM update that arrives
  coalesces.** The natural dwell window equals **one send's duration** and **self-scales with
  congestion**: the slower the wire, the longer each send, the more arrives during that send, and
  the more coalescing — so the mechanism strengthens precisely when the wire is under pressure.

**FPM offload reply.** The reply to zebra is sent **after** the update has been handed to the
producer, so it corresponds to work fpmsyncd has taken custody of. (With `suppress-fib-pending`
enabled the reply is instead driven by the programming response from orchagent, unchanged by this
design.)

**Design choice — no explicit flush timer.** A Nagle-style "hold the map N ms" timer would add
coalescing only in the light-load gap between sends, where wire load is already low, and it would
spend **convergence latency** to do so. Under real congestion the send-duration window already
dominates. Dwell therefore comes purely from send duration: a route waits only as long as the send
thread was already busy — latency the system was paying anyway — so coalescing adds no delay of its
own. The retain-and-retry buffer being a **map** (keyed, LWW) rather than a FIFO queue is what
carries this: coalescing arrives as a property of the async send thread and chunked drain.

### 7.3 Retention — retain-and-retry from the map

The coalescing map *is* the retain buffer. When a chunk's send fails past the inner absorber
(§7.6), the whole chunk is **re-merged into the live map** (newer-wins) and the drain aborts into an
outer backoff; the next drain picks it up again. Work is therefore **held, not dropped** (R1/R2).
The map is bounded by `mMax`; exceeding it is a memory-safety assert (observable, §7.6), never a
silent drop. (Named knobs throughout §7 are internal defaults; their values are tabulated in §9.3.)

### 7.4 Chunked drain from the live map

The send thread drains the map in **bounded chunks** (≤ `maxBatchEntries` keys **and**
≤ `maxBatchBytes`), each chunk becoming exactly one wire message. Each chunk is pulled **from the
live map, which stays open** — between chunk pulls the main thread keeps upserting, so a large drain
keeps coalescing and leaves ingest running. Figure 4 is the numbered sequence.

<p align="center">
  <img alt="Figure 4. Chunked drain sequence: pull bounded chunk under lock, send outside lock, on failure re-merge the whole chunk newer-wins and abort." src="images/fpmsyncd_zmq_route_delivery/02_chunked_drain.png" width="820">
</p>
<p align="center"><b>Figure 4.</b> Chunked drain from the live map. Each iteration pulls a bounded
chunk under the map lock, releases the lock, and sends <b>outside</b> the lock, so ingest never waits
on the wire and new same-key upserts arriving during a send coalesce into the remainder. The map is
therefore drained without ever being frozen.</p>

**Design choice — chunk from the live map rather than freezing it.** Snapshotting or locking the
entire map for a drain would stall ingest for the duration of that drain, and would stop coalescing
at the moment it pays most (a big backlog). Bounded chunks from the live map keep both ingest and
coalescing running throughout.

### 7.5 Batch sizing — wire efficiency vs. coalescing yield

> **In short:** chunk size trades wire efficiency against coalescing yield. The benchmarked knee is
> 256 keys per chunk; an 8 MiB byte cap independently guards the wide-route case so no message
> crosses the 16 MiB transport limit.

Given that the drain is chunked (§7.4), how large should each chunk be? The bound is a deliberate
balance between two opposing pressures.

- **Larger chunks amortize fixed per-message cost.** Each chunk is one multipart ZMQ message — one
  serialization/framing pass, one send syscall, one HWM check, one consumer-side receive/dispatch.
  Packing more keys into a message spreads those fixed costs over more routes, cutting CPU and
  syscall overhead per route and raising wire throughput. This is the whole point of batching over
  the original per-prefix send.
- **Smaller chunks preserve coalescing (and latency).** Keys extracted into a chunk have left the
  map; a late same-key update that arrives while that chunk is in flight can no longer collapse into
  it — it becomes a fresh map entry that must be sent again. Draining in smaller chunks leaves more
  of the working set resident in the map for longer (§7.2 dwell), so more same-key duplicates
  coalesce before extraction. Very large chunks also delay the first route's delivery and raise
  per-message memory.

The right chunk size is therefore the **knee** where wire efficiency has essentially saturated but
coalescing yield has not yet begun to erode. Benchmarking (Appendix A) puts that knee at
`maxBatchEntries` = **256** keys per chunk (**128** as a conservative backup): at 256 the fixed-cost
amortization is effectively fully captured, while the map still retains enough residency to coalesce
same-key churn. Larger chunks buy no further throughput but start trading away coalescing; smaller
chunks lose throughput without a matching coalescing gain.

Independently of that tuning, a hard correctness bound also applies (R5): a single multipart message
must stay under the transport's **16 MiB** per-message limit. `maxBatchBytes` (**8 MiB**) enforces
this and specifically guards the pathological wide-route case (few keys but very large field-value
lists), where the entry-count bound alone would not. A chunk is thus capped by whichever of
`maxBatchEntries` or `maxBatchBytes` it reaches first.

### 7.6 Failure, retry and liveness

The retry design separates a **benign HWM blip** from **real congestion**, so a transient hiccup
never escalates while a genuine stall is always bounded:

- **Inner blip absorber:** on a transient "would block", the send path retries a small number of
  times with a short backoff (a few milliseconds total). A momentary HWM blip clears here and
  **never escalates**; absorbed blips are counted separately from real congestion (§7.10).
- **Outer retry:** if the blip absorber is exhausted, the whole chunk is **re-merged into the live
  map** (§7.3) and the drain aborts to a backoff; the next drain retries. A congestion **episode**
  opens under hysteresis, so isolated blips do not inflate the episode count.
- **Liveness bound:** if the time since the last successful send exceeds `tFailMs`, or the map depth
  exceeds `mMax`, the producer writes a **sticky STATE_DB assert record** (which survives the
  process exit) and exits for recovery.

**How the restart recovers routes that were only in the map.** Recovery rests on zebra's
**unconditional full re-drive** on FPM reconnect: re-establishing the connection resets the
per-destination "already sent to FPM" marker across the entire RIB and re-enqueues every destination
as a fresh route-install. Its unconditional scope is what matters here. Routes parked in the map are
ones zebra already considers delivered (they went down FPM and were replied to), so a selective
resend would pass over them; a full re-drive carries them along with everything else, and the
failure path converges without silent loss (R6).

### 7.7 Send-thread state machine

Figure 5 is the send thread's lifecycle — the single place all of §7.3–7.6 comes together.

<p align="center">
  <img alt="Figure 5. Send-thread state machine: Idle → Waiting → Draining (pull bounded chunk, send outside lock, on success advance else re-merge and back off), with Assert on a prolonged stall. Green = success, red = congestion/failure path." src="images/fpmsyncd_zmq_route_delivery/03_sendthread_state.png" width="620">
</p>
<p align="center"><b>Figure 5.</b> Send-thread state machine — where every outcome of a drain leads.
A successful chunk advances to the next one, or returns to <code>Waiting</code> when the map empties;
a failed chunk backs off and is retried from the map; and a stall beyond <code>tFailMs</code> or a
depth over <code>mMax</code> leaves the loop for the assert path (sticky record → process exit →
RIB re-drive). The wait is timed rather than signal-only, so telemetry and the liveness clock
advance even when no routes are arriving. <b>Colour legend:</b> green = normal delivery, red =
congestion / failure path; cream = steady states.</p>

### 7.8 Heap reclaim — allocator-managed (#28245)

The RSS ratchet (Figure 2) is a property of the **allocator**, so it is fixed by changing the
allocator rather than by adding reclaim logic to fpmsyncd: fpmsyncd links **jemalloc** with
`background_thread:true`, which returns free pages to the OS on a decay schedule, on jemalloc's own
thread. Unlike glibc's top-only trim, decay reclaims interior free pages, so a pinned top allocation
no longer holds a burst's worth of memory resident. fpmsyncd contains no release code, no release
policy, and no reclaim thread of its own.

#### 7.8.1 Alternatives considered

Two alternatives were carried far enough to measure (Appendix A.2). Throughput did not decide
between them — measured drain rates are comparable across all of them — so the choice rests on where
the reclaim work lives.

**An fpmsyncd-managed release on the send thread's idle edge** — the original proposal. It does
bound RSS, and two considerations moved the design away from it.

The first is the trigger's premise. An idle FPM socket was taken to imply a quiescent heap, but that
window is precisely when the producer's deferred APPL_DB write-back drains on its own low-priority
thread, so the release would run against concurrent allocator activity. An allocator-owned
background thread makes no such assumption.

The second is code volume: a slicing policy, an abort predicate, idle detection, and their tests
reduce to one allocator configuration string. The concern that motivated the idle trigger — that
reclaiming *during* churn would cost delivery rate — did not materialize; background reclaim
returned memory continuously while holding full rate. Its measurable cost is more minor page faults,
which is bounded (§12).

**tcmalloc** — the allocator originally paired with that release. It reaches the same drain ceiling
as jemalloc, the two being statistically indistinguishable on rate. jemalloc is preferred because it
owns the release loop itself, whereas a tcmalloc background release still has to be driven by the
application, which would retain the machinery this design set out to remove.

#### 7.8.2 Configuration

Only `background_thread:true` is set; jemalloc's default decay intervals are kept. Tuning them
lowers the transient RSS *peak* but reaches the same resting RSS, so it buys nothing for the ratchet
this design targets and is left as optional future work (§14).

#### 7.8.3 Operational notes

**Startup check.** Background reclaim can silently fail to take effect, returning the daemon to the
ratcheting behavior this design removes. fpmsyncd therefore verifies at startup that reclaim is
active and logs an error if it is not, so the regression is reported rather than showing up only as
slow RSS growth.

**Coexistence.** Each process links exactly one allocator at build time and owns its own address
space, so this selects *which* allocator fpmsyncd uses. Per-process allocator choice is already
established practice in `docker-fpm-frr`, where daemons in the container use different allocators.
The cost is one additional library in the image.

### 7.9 Relationship to the consumer-side design

The end-to-end route path (Figure 3, §6) has two halves that ship independently: this **producer**
fix and the separate **consumer-side** design
([#2328](https://github.com/sonic-net/SONiC/pull/2328)), implemented upstream in
[sonic-swss-common #1187](https://github.com/sonic-net/sonic-swss-common/pull/1187) and
[sonic-swss #4564](https://github.com/sonic-net/sonic-swss/pull/4564). They are complementary, and
compose without ordering constraints:

- **This producer fix requires no consumer change.** It reduces the wire-message count at the source
  and never silently drops, so it delivers its full benefit against either consumer.
- **The two reduce different things.** This design coalesces route *updates*, so fewer tuples and
  fewer messages cross the wire. The consumer-side change coalesces *wakeups* — it drains the socket
  until empty and signals its main loop once per burst instead of once per message, so the receive
  side batches its work. Each addresses a different cost, so either can ship first.

Deployed together they reduce message volume at the producer and wakeup/flush overhead at the
consumer, at opposite ends of the same pipe.

### 7.10 Telemetry and observability

The producer publishes one STATE_DB table (read-only, debug-first) plus a sticky assert record.
Full schema, ABNF, and examples are in §9 (Configuration and Management, DB section) so vendors and
operators have one home for the contract. The **on-call one-liner**: read `health` first, then
`routes_lost_total` (must be `0`) for the no-drop guarantee.

Heap behavior is covered by the startup check (§7.8) instead of a telemetry table. With reclaim
owned by the allocator there is no fpmsyncd-side release activity to report, and the symptom the
design targets — steady-state RSS — is already visible to existing process and container monitoring.
The one failure mode that would otherwise be silent, reclaim not being active, is what the startup
check reports.

### 7.11 Repository / component change map

| Repo | Component | Change |
|---|---|---|
| `sonic-swss-common` | ZMQ producer client | Generic send-path overflow guard + a clamped retry-config setter (max attempts and backoff ceiling) + send-path counters (raw blips, blips absorbed, max backoff). **No route-specific logic.** Landed in [sonic-swss-common #1233](https://github.com/sonic-net/sonic-swss-common/pull/1233). |
| `sonic-swss` | `fpmsyncd` — new coalescing send component | Coalescing map + dedicated send thread + chunked, table-fair drain + inner blip-absorber wiring + outer retry + episode hysteresis + assert/liveness + route STATE_DB telemetry. |
| `sonic-swss` | `fpmsyncd` — route sync path | Funnels the steady-state route/label-route write path through the coalescer when the ZMQ path is enabled; sends the FPM offload reply after the producer hand-off. |
| `sonic-swss` | fpmsyncd build + `docker-fpm-frr` | Link jemalloc and enable background reclaim; startup check that it is active. |

Components are named by the role they play, so the map stays accurate as implementation names settle
in code review.

---

## 8. SAI API

**No new SAI API or SAI behavior changes are required.** This design is entirely upstream of
orchagent's route-programming path — it changes how fpmsyncd *delivers* routes to orchagent over
ZMQ, not how routes are programmed into the ASIC. The orchagent → syncd → SAI path is unchanged.

---

## 9. Configuration and Management

### 9.1 Manifest

Not applicable. fpmsyncd is a **built-in** SONiC daemon, not an Application Extension; no package
manifest changes are required.

### 9.2 CLI / YANG

**No new CLI commands and no YANG model changes.** The design adds no CONFIG_DB schema (§9.3), so
there is nothing to model in YANG and no `config`/`show` surface to add. The telemetry is exposed in
STATE_DB and read with standard tooling:

```
admin@sonic:~$ sonic-db-cli STATE_DB HGETALL "FPMSYNCD_ROUTE_STAT_TABLE|global"
```

A dedicated `show` wrapper is a possible future enhancement (§14); it is intentionally not part of
this change to keep the surface minimal and backward compatible.

### 9.3 Config DB and tuning knobs

**No CONFIG_DB tables are added or changed** — hence the design is trivially **backward
compatible**: upgrading to (or downgrading from) an image with this change does not alter any
operator-visible configuration or default behavior. The correctness fix is **always on**: it ships
without a disable switch, since the behavior such a switch would restore is the silent drop this
design removes.

The behavior is governed by internal coalescer defaults, tuned by benchmark
(Appendix A), not by CONFIG_DB:

| Knob | Default | Purpose |
|---|---|---|
| `maxBatchEntries` | 256 (backup 128) | keys per chunk = one wire message; the coalescing/throughput knee (§7.4) |
| `maxBatchBytes` | 8 MiB | safety cap under the 16 MiB ceiling (§7.5); guards pathological wide routes |
| `idleTickMs` | 1000 | timed-wait period, so telemetry and the liveness clock advance even with no ingest |
| `sendInnerMaxRetries` | 1–2 | inner **blip-absorber** attempts (§7.6) — not a retry ladder |
| `sendInnerMaxBackoffMs` | ~5 | inner per-attempt backoff cap (~10 ms total) |
| `outerBackoffMs` | 50 | pause after a failed flush before re-draining — the real retry cadence |
| `tFailMs` | 60000 | assert if the time since the last successful send exceeds this |
| `mMax` | 1000000 | assert if total map depth exceeds this (memory bound) |
| `telemetryMinIntervalMs` | 10000 | throttle STATE_DB publish |

The allocator is configured out-of-band rather than through this table: fpmsyncd is built against
jemalloc with `background_thread` enabled (§7.8).

#### 9.3.1 STATE_DB schema — route send stats

Key separator `|` (STATE_DB). Producer: fpmsyncd send thread. Consumer: operators / DRI tooling.

```
; Route send statistics — one global record, published by fpmsyncd
key                        = FPMSYNCD_ROUTE_STAT_TABLE|global   ; single global row
health                     = "OK" / "CONGESTED" / "STALLED" / "RECOVERED" ; health state machine (see below)
map_depth                  = 1*DIGIT      ; current backlog (live gauge)
map_depth_hwm              = 1*DIGIT      ; peak backlog ever (sizing signal for mMax)
last_success_age_sec       = 1*DIGIT      ; seconds since last successful send (liveness leading indicator)
routes_sent_total          = 1*DIGIT      ; routes that crossed the wire (monotonic)
routes_coalesced_total     = 1*DIGIT      ; inputs collapsed before the wire (efficiency win)
chunks_sent_total          = 1*DIGIT      ; wire messages sent (feeds avg_chunk_fill)
congestion_episodes_total  = 1*DIGIT      ; real episodes (hysteresis-gated; blips excluded)
routes_lost_total          = 1*DIGIT      ; THE no-drop guarantee — 0 always
assert_total               = 1*DIGIT      ; lifetime asserts (restarts)
ep_duration_ms             = 1*DIGIT      ; last episode duration
ep_peak_depth              = 1*DIGIT      ; worst backlog during last episode
ep_coalesced_in            = 1*DIGIT      ; inputs folded during last episode
ep_coalesced_out           = 1*DIGIT      ; sets emitted during last episode
zmq_eagain_total           = 1*DIGIT      ; raw EAGAIN count (all blips)
zmq_blip_absorbed_total    = 1*DIGIT      ; EAGAIN cleared inside the inner absorber
retry_from_map_total       = 1*DIGIT      ; outer re-merges (real congestion past hysteresis)
zmq_backoff_max_ms         = 1*DIGIT      ; max backoff on the retry path
```

*Example STATE_DB record (excerpt — the complete field set is the ABNF above; §13.1 #11 governs the full published record):*

```json
{
  "FPMSYNCD_ROUTE_STAT_TABLE": {
    "global": {
      "health": "OK",
      "map_depth": "0",
      "map_depth_hwm": "1841",
      "last_success_age_sec": "0",
      "routes_sent_total": "5823941",
      "routes_coalesced_total": "214877",
      "chunks_sent_total": "23142",
      "congestion_episodes_total": "0",
      "routes_lost_total": "0",
      "assert_total": "0"
    }
  }
}
```

```
admin@sonic:~$ sonic-db-cli STATE_DB HGETALL "FPMSYNCD_ROUTE_STAT_TABLE|global"
health                     OK
map_depth                  0
map_depth_hwm              1841
routes_sent_total          5823941
routes_coalesced_total     214877     # ~3.6% collapsed before the wire
chunks_sent_total          23142      # avg_chunk_fill = 5823941/23142 ≈ 251 (256 well-utilized)
routes_lost_total          0          # ← no-drop guarantee holding
assert_total               0
```

**`health` state machine:** `OK` (draining freely, no open episode) → `CONGESTED` (an episode is
open — failure persisted past the inner absorber + first outer backoff) → `STALLED`
(`last_success_age_sec` approaching `tFailMs` — heading to assert) → `RECOVERED` (episode just
closed; sticky for one publish, then `OK`).

#### 9.3.2 Sticky assert record

Written once at death into the route-stat table so post-restart triage sees **why** it died (STATE_DB
survives an fpmsyncd container bounce): `assert_last_ts`, `assert_last_reason`
(`STUCK_TIMEOUT` / `DEPTH_OVERFLOW`), `assert_last_depth`, `assert_last_stuck_ms`.

**Timestamp convention.** Absolute wall-clock stamps (`assert_last_ts`) are human-readable UTC
strings (`YYYY-MM-DD HH:MM:SS`), **not epoch integers**, so a raw `HGETALL` is fleet-unambiguous;
elapsed values (`*_age_sec`, `*_ms`) stay numeric for alert math.

**Backward compatibility:** STATE_DB *outputs* only — like the schema above, they add no existing
table or configuration change (§9.3), and consumers that ignore them are unaffected.

---

## 10. Warmboot and Fastboot Design Impact

Warmboot/fastboot behavior is **out of scope** for this design and unchanged from the baseline —
this change touches only fpmsyncd's steady-state producer path, not the boot/reboot sequence, and
adds nothing to the boot critical chain.

The only restart-relevant property: the coalescing map is process memory and is intentionally *not*
persisted. On restart the route state is relearned end-to-end across the bgp→swss→syncd pipeline
(FRR re-drives the RIB), so any routes pending in the map at exit are re-delivered by that replay.
The sticky assert record (§7.6) persists in STATE_DB; other telemetry gauges reset on restart.

---

## 11. Memory Consumption

- **When idle:** the coalescing map is empty, so it adds no steady-state footprint; the STATE_DB
  telemetry record is small and fixed-size.
- **When enabled under load:** the map grows with the number of **distinct pending route keys** and
  is hard-capped at `mMax` before an observable assert. This is a **transient** high-water bound
  that the send thread drains continuously — not a persistent allocation.
- **Reclaim:** the allocator returns free pages to the OS on its own background thread (§7.8), so
  the burst high-water mark decays back rather than accumulating; steady-state RSS does **not**
  ratchet across bursts (Appendix A.2).
- **When the ZMQ path is disabled:** no map, no send thread, no added footprint at all (§7.1).

Net effect: a **bounded, transient** working set plus **continuous reclaim** replaces the baseline's
unbounded RSS ratchet.

---

## 12. Restrictions / Limitations

- **Distinct-prefix floods are bounded by assert, not coalescing.** When every key differs,
  coalescing collapses nothing; a sustained flood past `mMax` becomes an observable assert + restart
  (recovered by zebra's full re-drive, §7.6), not a silent drop. This is a deliberate design boundary
  (§5.3 non-goal 1): a bounded, observable, self-healing failure is preferred over the silent
  divergence it replaces.
- **Reclaim is decay-based, not immediate.** Free pages are returned on the allocator's schedule
  rather than at the instant of `free()`, so RSS trails the working set by a bounded interval — the
  high-water mark of a burst persists briefly after it clears. Reclaim also cannot return free memory
  interleaved with genuinely-live objects, so residual fragmentation keeps RSS somewhat above live
  bytes. Both are properties of any decaying allocator, not fixable defects.
- **Reclaim costs page faults.** Returning pages during churn means re-faulting them on the next
  burst. Under sustained congestion this was measured at 2.4–2.6× the minor-fault rate of the
  idle-triggered alternative, in exchange for the lower resting RSS (Appendix A.2). Throughput was
  unaffected.
- **The Redis path is unchanged.** The no-drop guarantee and the telemetry apply where the ZMQ path
  is enabled (§2). Redis-path deployments keep their existing behavior, which already coalesces and
  is free of the defect this design fixes.
- **No user config surface.** Retuning the knobs (§9.3) requires a build; there is no runtime
  control. Deliberate — §5.3 non-goal 5.

---

## 13. Testing Requirements / Design

### 13.1 Unit test cases

The code changes ship with unit tests that verify the following behaviors:

| # | Behavior verified | Covers |
|---|---|---|
| 1 | A backlog larger than one batch drains as multiple bounded wire messages, each within the size ceiling. | R5, §7.4–7.5 |
| 2 | Repeated updates to the same key collapse to a single wire update, keeping the latest. | R4, §7.2 |
| 3 | Sustained churn on one route table does not starve delivery of the other. | §7.2 |
| 4 | A failed batch is re-merged into the map without overwriting a newer update that arrived for the same key. | R2, §7.3/§7.6 |
| 5 | A transient send blip is absorbed and does **not** open a congestion episode. | §7.6 |
| 6 | A field-less update (indistinguishable from a delete on the wire) is rejected rather than sent. | §7.6 |
| 7 | With the ZMQ path disabled, no coalescer and no send thread are created and writes take the original producer path. | R12, §7.1 |
| 8 | While warm-restart reconciliation is in progress the coalescer is bypassed, so the send thread is never a concurrent ZMQ writer. | §7.1 |
| 9 | Routes accepted into the map but not yet dispatched are still resident, and undispatched, when the coalescer is destroyed. | R1, §7.6 |
| 10 | The lifetime assert count survives a restart via the sticky STATE_DB record. | R6, §9.3.2 |
| 11 | The published route-stat record contains exactly the documented fields. | R8, §9.3.1 |
| 12 | Absolute timestamps are published as human-readable UTC strings, not epoch integers. | R8, §9.3.2 |
| 13 | With STATE_DB unreachable at startup, fpmsyncd starts and delivers routes; telemetry publication resumes once STATE_DB is reachable. | R9, §9.3 |

R7 and R11 (heap) are proved by the allocator A/B in §13.2; R10 is carried by the `swss-common`
change's own tests, since the guard it adds is route-agnostic by construction (§7.11).

### 13.2 Component A/B benchmark design

Each requirement is validated by a **same-rig A/B** comparison: Baseline **A** = the pre-fix inline
path; Fix **B** = the coalescer. An in-process harness drives controllable workloads through a fake
send sink (no real ZMQ socket), so the comparison isolates coalescer behavior from send-duration.
The scenarios and the requirement each one proves:

| Scenario | What it demonstrates | Proves |
|---|---|---|
| Same-key churn | repeated same-key updates collapse to a single wire update, latest wins | R4, §7.2 |
| Distinct-prefix flood | a large backlog drains as bounded, well-filled chunks | R5, §7.4 |
| Congestion stall | under an identical stall the inline path drops routes while the coalescer holds, retries, and converges with zero loss | R1, R2, R3 |
| Throughput | sustained ingest/drain rate over a large prefix set | R13 |

Results in **Appendix A.1**.

**Allocator A/B.** The heap requirement is validated separately, because the variable is the
allocator and its release mechanism rather than fpmsyncd logic. Each arm is a **separate binary**
(no `LD_PRELOAD`), gated by link- and map-level checks that exactly one allocator is present, run
against an identical consumer with arms interleaved so host drift is common-mode:

| Arm | Allocator | Release mechanism | Role |
|---|---|---|---|
| application-managed | tcmalloc | idle-triggered release on the send thread | the rejected candidate |
| **allocator-managed** | **jemalloc** | **`background_thread`, stock decay** | **the design** |
| allocator-managed, tuned | jemalloc | `background_thread` + shortened decay | tuning sensitivity |
| control (per allocator) | each | none | isolates mechanism from allocator |

Three regimes are exercised — burst-then-drain, saturation, and sustained congestion with reclaim
overlapping live route delivery — measuring resting RSS, drain ceiling, CPU per route, and minor
faults. The controls are what make the result attributable: with release disabled in both, any
remaining difference is the allocator rather than the mechanism. Results in **Appendix A.2**;
they prove R7 and R11.

### 13.3 System test cases

Integration coverage lands in `sonic-mgmt` (data-plane proof on a fixed image). Strongest form —
legacy vs expected:

| # | Scenario | Legacy behavior | Expected behavior |
|---|---|---|---|
| 1 | Burst past SNDHWM (tens of thousands of routes) | silent drop; ASIC route count < RIB, no signal | no drop; ASIC route count reconciles to RIB; `routes_lost_total == 0` |
| 2 | Same-key churn (ECMP next-hop flap) | N per-prefix messages | coalesced; `routes_coalesced_total` > 0; convergence unchanged |
| 3 | Sustained consumer stall (> `tFailMs`) | silent divergence | sticky assert record written; container bounce; zebra's re-drive repairs |
| 4 | **Recovery of undispatched routes:** stall delivery so routes are parked in the map, confirm they are resident and not yet dispatched, then kill fpmsyncd | routes acknowledged to zebra but never sent are lost | after restart the routes are present in the ASIC; `routes_lost_total == 0` |
| 5 | Sustained route churn concurrent with label-route updates | — | label-route delivery latency stays bounded (no cross-table starvation) |
| 6 | Steady-state churn over hours (RSS watch) | RSS ratchets up → OOM-restart | RSS plateaus across bursts |
| 7 | Image upgrade old→new, restart | N/A | no crash; routes relearned via zebra's re-drive; no route loss |
| 8 | ZMQ route path disabled | — | behavior identical to the pre-change image |

Scenario 4 is the load-bearing one for the no-drop guarantee, and it needs a real control plane:
routes parked in the map have already been acknowledged to zebra, so recovery depends on zebra's
unconditional full re-drive (§7.6) rather than on any resend by fpmsyncd. A unit test cannot
demonstrate that without assuming it.

On-box verification: `sonic-db-cli STATE_DB HGETALL "FPMSYNCD_ROUTE_STAT_TABLE|global"`; compare
`show ip route` count vs the ASIC route count. These scenarios are implemented as `sonic-mgmt` test
cases accompanying the change.

---

## 14. Open / Action Items

Future **design** increments (not a fix backlog):

1. **Operator `show`/`config` surface.** If a fleet need emerges to retune `maxBatchEntries` or the
   liveness bounds at runtime, add a `show fpmsyncd route-stats` wrapper and a CONFIG_DB-backed
   knob table + YANG model (deliberately deferred, §5.3 non-goal 5).
2. **Allocator decay tuning.** Shortening jemalloc's decay intervals lowers the transient RSS peak
   without changing resting RSS (Appendix A.2). If peak RSS becomes a constraint on a
   memory-tight platform, tune decay then — it needs no code change.
3. **KVM/hardware data-plane A/B.** Corroborate the component results (Appendix A) end-to-end on a T2
   testbed (burst-past-HWM no-drop + RSS behavior under real FRR flap). The component evidence is
   load-bearing; this is confirming.

---

## 15. References

- [sonic-buildimage #28369 — fpmsyncd drops route updates under burst](https://github.com/sonic-net/sonic-buildimage/issues/28369)
- [sonic-buildimage #28245 — fpmsyncd heap RSS ratchet](https://github.com/sonic-net/sonic-buildimage/issues/28245)
- [sonic-swss-common #1233 — generic ZMQ send-path overflow guard and retry config](https://github.com/sonic-net/sonic-swss-common/pull/1233) (§7.11)
- [sonic-net/SONiC #2328 — consumer-side (orchagent) route ingestion design](https://github.com/sonic-net/SONiC/pull/2328), implemented in
  [sonic-swss-common #1187](https://github.com/sonic-net/sonic-swss-common/pull/1187) and
  [sonic-swss #4564](https://github.com/sonic-net/sonic-swss/pull/4564) (complementary; §7.9)
- FRR FPM / zebra route streaming — [FRRouting documentation](https://docs.frrouting.org/)
- [jemalloc tuning reference](http://jemalloc.net/jemalloc.3.html) — `background_thread`, decay options (§7.8)

---

## Appendix A — Measured benchmark results

> Two different rigs are used, and each is labelled at its section. Absolute rates are
> rig-specific; the ratios are what carry. Test design is in §13.2.

### A.1 Route delivery

> **Rig:** `sonic-slave` container, `-O2`. An in-process fake sink replaces the real ZMQ socket, so
> these measure the fix's own overhead rather than wire time. **Before** = the existing inline path,
> **After** = the fix.

| Test | Measure | Before | After |
|---|---|---|---|
| **Same-key churn** — 1000 prefixes rewritten 20× | Messages sent | 20,000 | **4** |
| | Duplicates collapsed | 0 | **19,000** |
| | Routes converged | 1000 | 1000 ✓ |
| **Prefix flood** — 5000 unique prefixes | Messages sent (avg fill) | 5000 *(by construction)* | **20** (250/chunk) |
| **Congestion** — send stalls 40× | Routes dropped | **40** | **0** |
| | Routes converged | 2960 | **3000** |
| **Throughput** — drain 100k prefixes | Accept into map / drain to wire | — | **1.6M / 3.4M routes/s** |

**What it shows:** two independent levers. Coalescing collapses a 20,000-message same-key burst to
4 messages, with every route still converged. Bulking carries the case coalescing cannot help: a
flood of 5000 *distinct* prefixes has nothing to collapse, yet still leaves as 20 chunked messages
rather than 5000 individual ones (R5). Under the same stall the inline path silently drops 40 routes
while the fix holds and delivers all 3000 (R1, R2). The map keeps up at millions of routes/s each way
— far above real churn — so it adds no throughput bottleneck (R13).

The *Before* column is the pre-fix one-prefix-per-message path; its flood value follows from that
structure rather than from a separate run.

### A.2 Heap reclaim — allocator A/B

> **Rig:** bare-metal, CPU-pinned container, one allocator per binary (no `LD_PRELOAD`), identical
> consumer across arms, arms interleaved within each repetition. KVM was abandoned for this
> comparison because steal time is noise at the same scale as the effects measured. n=5/arm unless
> noted. Arm names are those of §13.2; the shipped design is **allocator-managed (stock decay)**.

**Burst, then drain.** Congestion drives the map to a fixed depth cap, then clears.

| Arm | RSS peak | RSS resting | minor faults (k/M routes) |
|---|---|---|---|
| application-managed (tcmalloc + idle release) | **117.7 MB** | 47.4 MB | **6.9** |
| allocator-managed, tuned (jemalloc) | 184.5 MB | **28.0 MB** | 36.2 |
| *control:* tcmalloc, no release | 143.4 MB | 143.4 MB | 3.6 |
| *control:* jemalloc, no decay | 1506.3 MB | 1506.3 MB | 50.1 |

Both mechanisms bound RSS; they trade differently. The application-managed release holds a lower
peak and takes fewer page faults, while background reclaim settles lower at rest — the axis #28245
is about. The controls confirm each mechanism is doing the work: with release disabled, tcmalloc
rests at its peak and jemalloc grows to 1.5 GB. The jemalloc arm in this regime is the *tuned*
configuration; stock decay was measured under sustained congestion below, where it matches the
tuned arm.

**Saturation.** Operating point located by sweep; the consumer is unthrottled so any cost on the send
thread becomes visible.

| Arm | drain ceiling (k routes/s) | CPU µs/route |
|---|---|---|
| *control:* tcmalloc, no release | **689.0 ± 20.9** | 2.141 |
| allocator-managed, tuned (jemalloc) | **685.7 ± 22.1** | 2.139 |
| application-managed (tcmalloc + idle release) | 661.6 ± 9.3 | 2.251 |
| *control:* jemalloc, no decay | 653.3 ± 15.9 | 2.301 |

Two results:

1. **The workload sets the ceiling, not the allocator.** Pooled across arms, tcmalloc reaches 675.3
   and jemalloc 669.5 k routes/s — +0.9 %, t = +0.56, indistinguishable.
2. **Reclaiming does not cost throughput.** Decay measures +5.0 % over no-decay (t = +2.66): a
   compact working set outperforms an unbounded one.

The two release mechanisms do separate slightly, which is recorded here for completeness rather than
as a design input. Against the same allocator with release disabled, application-managed release
measures 4.0 % lower (661.6 vs 689.0, t = −2.68; CPU per route 2.251 vs 2.141), while
allocator-managed release measures −0.5 % (n.s.) despite purging far more often. At this ceiling
4.0 % is about 60 ms of drain time on a full 10⁶-route table (R13).

**Sustained congestion.** The map is held at its cap for 60 s — the regime where an allocator
background thread purges *while routes are still flowing*, which is what the idle trigger existed to
avoid. Terminal RSS is shown per repetition.

| Arm | delivery/s | minor faults /1k | RSS peak | terminal RSS | reclaims *during* burst |
|---|---|---|---|---|---|
| application-managed (tcmalloc + idle release) | 51,038 | 27.4 | 379.8 MB | 51.5 / 49.2 / 47.8 MB | **0** |
| allocator-managed, tuned (jemalloc) | 56,268 | 65.9 | 433.2 MB | **32.5 / 32.6 / 32.5 MB** | 126 / 134 / 135 |
| **allocator-managed, stock decay (the design)** | **66,783** | 72.6 | 566.8 MB | **33.0 / 33.3 / 32.8 MB** | 82 / 104 / 146 |

The preemption asymmetry was measured in both directions: the allocator purged ~130
times mid-burst, reclaiming on the order of a gigabyte, while the idle trigger released nothing until
delivery stopped — in every arm and every repetition. The allocator-managed arms delivered the
higher route rate while purging mid-burst, at 2.4–2.6× the minor faults. That page-fault increase is
the genuine cost of this design, and it is bounded (§12).

**Stock decay is sufficient.** The shipped configuration reaches the same terminal RSS (~33 MB) as the
tuned arm. Tuning decay buys a lower transient peak (433 vs 567 MB) and nothing else, which is why it
is deferred rather than adopted (§14).
