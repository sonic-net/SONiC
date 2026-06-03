# SONiC Route Download Performance: Large-Scale Datacenter CLOS Fabric Strategy

| | |
|---|---|
| **Version** | 1.0 (Initial) |
| **Author** | Deepak Singhal |
| **Date** | 2026-05-13 |
| **Related issue** | [SONiC#2238](https://github.com/sonic-net/SONiC/issues/2238) |

---

## 1. Production Context

This analysis targets highly redundant CLOS networks with specific characteristics that shape the optimization strategy:

| Dimension | Production Requirement |
|-----------|----------------------------|
| **Network architecture** | Multi-tier CLOS fabric (1M FIB / 5M+ RIB scale) |
| **FIB suppression** | **Required** (`suppress-fib-pending = enabled`) — BGP must not advertise routes until ASIC-confirmed to prevent traffic black holes |
| **Warm/fast boot** | **Not required** — redundant CLOS topology with ECMP at every layer; traffic reconverges around a restarting device via alternate paths |
| **ECMP profile** | **90%+ routes form ECMP** from eBGP neighbors — 16-32 eBGP peers per device |
| **Topology** | Chassis linecards and pizza-box form factors, multi-ASIC and single-ASIC, multi-vendor ASICs, 4-16 core CPUs |
| **Route scale** | Target: **1M FIB, 5M+ BGP RIB** |
| **Telemetry** | gNMI/telemetry used primarily for data streaming (not SNMP polling) |
| **Programming rate** | Routes installed and withdrawn per second are the primary performance metrics |
| **Tunnel overlay** | **Some topologies** — SRv6 or VxLAN tunnels between pizza-box routing nodes. Coexists with pure L3 eBGP topologies using directly connected next-hops. |
| **Failure convergence** | **Sub-second target** — ECMP member failure (link down, node failure) must converge sub-second at production prefix scale. |

### Why this matters

The community HLD ([SONiC#2154](https://github.com/sonic-net/SONiC/pull/2154)) benchmarks 12+ optimization knobs, achieving 2K → 20K+ routes/sec. However, the highest-performing configurations all rely on async mode and disabling APPL_STATE_DB — both incompatible with FIB suppression.

This document analyzes what works best under these production constraints and identifies the most effective optimization strategy.

---

## 2. Knobs Incompatible with FIB Suppression

The community HLD identifies 12 optimization knobs. With FIB suppression enabled, several are blocked because FIB suppression relies on a confirmation feedback loop:

```
orchagent → SAI program → syncd confirms → orchagent writes APPL_STATE_DB
  → fpmsyncd reads confirmation → FRR/zebra marks route RTM_F_OFFLOAD → route advertised
```

Any knob that bypasses or disables part of this loop breaks the safety guarantee:

| Knob | HLD Impact | Why Blocked with FIB Suppression |
|------|-----------|---------------------|
| **Async mode** | 2K → 2.9K (45% gain) | orchagent doesn't wait for SAI confirmation → writes premature offload status → defeats FIB suppression guarantee (advertises before hardware confirms) |
| **Disable APPL_STATE_DB** | 2K → 4K (100% gain) | FIB suppression IS the APPL_STATE_DB write path. Disabling it breaks the entire feedback loop to fpmsyncd/FRR. |
| **Disable APPL_DB / ASIC_DB** | Not measured separately | Not planned — breaks runtime debugging and operational visibility (redis-cli, routeCheck.py, show commands). |

These knobs appear in the community HLD's highest-performing configurations. With FIB suppression enabled, those configurations are ruled out. The focus shifts to the remaining knobs that are compatible.

---

## 3. Two Main Optimization Paths

The remaining knobs divide into two architectural approaches that address the same bottleneck — **Redis contention on the orchagent main thread** — with different philosophies:

### Path A: ZMQ Northbound + Southbound

**Philosophy**: Bypass Redis on the hot path for route programming using ZeroMQ direct IPC.

```
FRR/zebra ──FPM──► fpmsyncd ──ZMQ──► orchagent ──ZMQ──► syncd/SAI
                   (bypasses APPL_DB and ASIC_DB Redis on hot path;
                    both still written asynchronously via AsyncDBUpdater
                    for debugging/show commands)
```

| Component | Notes |
|-----------|-------|
| ZMQ Northbound (fpmsyncd→orchagent) | Original HLD: [SONiC#1659](https://github.com/sonic-net/SONiC/pull/1659); explanation: [SONiC#2230](https://github.com/sonic-net/SONiC/pull/2230) |
| ZMQ Southbound (orchagent→syncd) | Replaces Redis with ZMQ for the southbound programming path |

### Path B: Multi-DB + Ring Buffer

**Philosophy**: Keep Redis but reduce contention by splitting databases and decoupling I/O from processing.

```
FRR/zebra ──FPM──► fpmsyncd ──Redis(isolated)──► orchagent ──Redis(isolated)──► syncd/SAI
                   (APPL_DB on separate Redis)    (ASIC_DB on separate Redis)
```

| Component | Notes |
|-----------|-------|
| Multi-DB | Build-time flag `ENABLE_MULTIDB=y` (image rebuild required) |
| Ring Buffer | Decouples ConsumerStateTable pop from orch processing. Redundant with ZMQ NB — ZmqConsumer::execute() calls pops()+drain() directly, does not use processAnyTask/ring buffer. Not incompatible, just adds no value when ZMQ NB is enabled. |

### Head-to-Head Benchmark (Community-submitted data: Broadcom DNX, AMD 8C 2.5 GHz, 250K IPv4, FIB suppression OFF)

| Configuration | Default Batch | `-b 10000` (batch size 10K) |
|---------------|:---:|:---:|
| **Baseline** (no optimizations) | **~2,000/s** | **~4,000/s** |
| Multi-DB + Ring Buffer | 8,099/s | 11,160/s |
| **ZMQ NB + ZMQ SB** | **10,588/s** | **12,034/s** |

> At default batch size, ZMQ NB+SB outperforms Multi-DB+RB by ~31%. Both paths benefit significantly from batch tuning.

---

## 4. Why Path A (ZMQ) Is the Recommended Direction

### Performance gap in available benchmarks

Section 3's benchmark data shows ZMQ NB+SB leads by **+31% at default batch** (10,588/s vs 8,099/s) and wins across all 24 test configurations. This gap is structural — ZMQ removes Redis serialization from the hot path. With FIB suppression enabled and async APPL_STATE_DB offload, route performance remains comparable to these numbers.

### Why Redis on the hot path is a concern at scale

Redis is single-threaded per instance — all operations (reads, writes, pub/sub notifications) are serialized through one event loop. At high route scale, this means:

- Each route requires multiple serialized Redis operations (write + publish + read), adding ~500μs-1ms of Redis latency per route
- External consumers (SNMP, telemetry, CLI show commands) share the same Redis event loop, competing for cycles during bulk route programming
- Redis memory overhead grows with route scale — key metadata, expiry tracking, and pub/sub subscriber management all consume CPU time proportional to key count

With Path B (Multi-DB+RB), Redis remains on the forward path even when isolated — the single-thread-per-DB ceiling applies. Path A (ZMQ) removes this constraint entirely.

### The FIB suppression feedback loop

Even with NB+SB on ZMQ, every route requires a **feedback confirmation** through Redis so FRR knows it's safe to advertise:

```
orchagent → ResponsePublisher::publish() → Redis PUB/SUB + APPL_STATE_DB write (both synchronous, main thread)
  → fpmsyncd NotificationConsumer → sendOffloadReply() → FPM → zebra RTM_F_OFFLOAD → route advertised
```

This is the remaining Redis bottleneck on orchagent's main thread. `ResponsePublisher` async offload moves APPL_STATE_DB writes, notifications, and recordings to a background thread, controlled by `SYSTEM_DEFAULTS|async_rec:status`.

| What orchagent main thread does | All-Redis Default | ZMQ + Async Offload | End-state |
|---|---|---|---|
| NB read | Redis | ZMQ | ZMQ |
| SB program | Redis | ZMQ | ZMQ |
| Feedback (PUB/SUB + DB write) | Redis (main thread) | Redis (background thread) | **ZMQ + background thread** |
| **Net Redis on main thread** | All I/O | **ZERO** | **ZERO** |

### Path B ceiling

Path B (Multi-DB+RB) retains Redis on the forward path for NB, SB, and feedback — the single-thread-per-DB ceiling cannot be removed by configuration.

### Recommendation

The ZMQ path provides a clear trajectory toward zero Redis on the route programming main thread:

```
All-Redis:  NB=Redis, SB=Redis, Feedback=Redis (main thread)          ← default
ZMQ+Async:  NB=ZMQ,   SB=ZMQ,  Feedback=Redis (background thread)    ← Step 1 deployment
End-state:  NB=ZMQ,   SB=ZMQ,  Feedback=ZMQ + background thread      ← zero Redis on main thread
```

---

## 5. Compatible Optimizations

These optimizations are independent of the core path choice and provide additive improvement:

| Knob | Expected Gain | FIB-Suppression Compatible? | Notes |
|------|--------------|---------------------|-------|
| **Batch/bulk tuning** (empirical — test `-b` and `-k` combos) | Significant over default batch size | ✅ | Default → b=5K is biggest jump; diminishing returns past 10K. Optimal value depends on deployment profile — test different batch/bulk combinations under production-representative conditions and find the balance between throughput and notification starvation for other orchagent subscribers (port state, ACL, etc.). |
| **SAI bulk mode** (`syncd -l`) | 5-10% | ✅ | Enables SAI bulk API for route programming. Target: enable by default on Broadcom platforms (DNX + XGS). |
| **Async logging** | 25-30%+ combined | ✅ | Covers three synchronous I/O items on the main thread: swss.rec logging, sairedis.rec logging, and APPL_STATE_DB writes for the FIB suppression return path. |
| **SNMP KEYS fix** | Eliminates 50-100ms Redis blocks/5s | ✅ | `rfc1213.py::NextHopUpdater` does `KEYS ROUTE_TABLE:*` every 5s — fetches the entire route table key list from Redis (O(N) scan, blocks Redis event loop). Only actually uses `0.0.0.0/0` default route. Fix: replace with direct key lookup. |

---

## 6. Nexthop Group (NHG) + RIB/FIB Support

ZMQ NB+SB addresses transport-layer throughput. For ECMP-heavy CLOS fabrics, nexthop group support addresses a complementary dimension: given a typical profile (90%+ routes, 16-32 eBGP neighbors), NHG improves both **route download performance** (4x payload reduction via dedup) and **failure convergence** (O(1) ECMP member switchover via PIC).

### What NHG delivers

```
Route download:   250K routes × ~200 bytes → ~200 NHG objects + 250K × ~50 bytes (4x smaller)
ECMP failure:     Neighbor down → 1 NHG update → all routes inherit    (O(1) vs O(N))
```

### Two community implementations

| | NTT ([swss#2919](https://github.com/sonic-net/sonic-swss/pull/2919)) | Alibaba RIB/FIB ([SONiC#2060](https://github.com/sonic-net/SONiC/pull/2060)) |
|--|-----------------|-----------------|
| Scope | Dedup only | Full RIB/FIB lifecycle |
| Dedup | ✅ 4x payload reduction | ✅ Same |
| PIC | ❌ No dependency graph | ✅ O(1) via `depends[]`/`dependents[]` backwalk |
| SRv6 | ❌ | ✅ Native VPN route + tunnel NHG handling |
| FRR changes | None | Custom `RTM_NEWNHGFIB` message type |
| Config | `nexthop_group=enabled` | `nhg_fib=enabled` (separate knob) |

These are **parallel code paths, not layers** — each has its own FPM message type, NHG storage, and route lookup logic. Enabling one does not exercise or validate the other.

### Why RIB/FIB for large-scale CLOS

For deployments where ECMP failure convergence and tunnel-based forwarding are requirements — for example, disaggregated chassis topologies with NHG primary/backup switchover (<1s target) and SRv6/VxLAN overlay between routing nodes — the RIB/FIB approach provides the necessary dependency graph for PIC (updating a single NHG object propagates to all dependent routes in SAI) that the simpler dedup-only model does not support.

For deployments requiring PIC and SRv6, the RIB/FIB NHG model is the preferred approach for improving route download performance and churn handling.

HLD: [SONiC#2060](https://github.com/sonic-net/SONiC/pull/2060)

### Transport ordering requirement: ZMQ + NHG

When `ROUTE_TABLE` uses ZMQ northbound but `NEXTHOP_GROUP_TABLE` remains on Redis, routes can arrive at orchagent before their NHG references. Fix: extend NB ZMQ to transport NHG on the same socket.

---

## 7. Risks & Mitigations

### ZMQ-specific risks

| Risk | Impact | Mitigation | Validation |
|------|--------|------------|------------|
| **APPL_DB eventual consistency** with NB ZMQ | Low | By design — ZMQ sends first, APPL_DB written async | routeCheck.py tolerates async delay |
| **ASIC_DB eventual consistency** with SB ZMQ | Low | ASIC_DB written asynchronously via AsyncDBUpdater for diagnostics | routeCheck and show commands return correct data |
| **Warm reboot not supported** | Medium | Not required for target deployment profile (Section 1) | Cold reboot path validated |
| **NB ZMQ: no persistence** | Medium | swss restart cascades to bgp → FRR replays RIB → automatic recovery | swss restart → full route recovery |
| **SB ZMQ: syncd crash recovery** | High | syncd restart must cascade to swss+bgp for full replay | Cascade restart + route recovery validated |
| **Debugging opacity** | Low | Async DB updates keep Redis populated for diagnostics | redis-cli / show commands return current data |

### ZMQ + NHG interaction

| Risk | Impact | Mitigation | Validation |
|------|--------|------------|------------|
| **Mixed transport race** — NB ZMQ covers ROUTE_TABLE but not NEXTHOP_GROUP_TABLE → routes can arrive at orchagent before their NHG references | High | Extend NB ZMQ to transport NEXTHOP_GROUP_TABLE on same socket | Test NHG + ZMQ combined; verify no orphan route references |
| Orch ordering | None | NhgOrch processes before RouteOrch in orchdaemon | Covered by existing orch ordering |
| RouteOrch missing NHG retry | None | Route stays pending for retry if NHG not yet resolved | Covered by existing retry logic |
| NHG persistence on ZMQ | Same as routes | Same async APPL_DB writes mechanism | Covered by async DB validation |

---

## 8. Performance Profiling & Baseline

### Vendor SAI performance counters

SAI-level route programming performance counters ([SAI#2279](https://github.com/opencomputeproject/SAI/pull/2279)) help isolate whether bottlenecks are in the SAI/ASIC layer or the software stack. Enhance sonic-mgmt benchmark test ([sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727)) to collect SAI-level metrics alongside end-to-end route convergence numbers.

### CPU and memory profiling

Extend sonic-mgmt route performance tests to collect CPU and memory profiles during route programming. This enables identifying per-component hotspots (FRR, fpmsyncd, orchagent, syncd) and memory allocation overhead. Key validation: compare current glibc allocator vs tcmalloc performance on FRR for route programming workloads.

---

## 9. Validation Test Plan

### Test infrastructure

- Snappi/IXIA BGP route convergence test ([sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727)) — drives optimization profiles via `fine-tuning.yml`, measures RIB-IN convergence per combination.

### Key validation areas

- **ZMQ NB+SB end-to-end** — route programming with and without FIB suppression, across single-ASIC, multi-ASIC, and chassis platforms
- **Batch/bulk tuning sweep** — vary `-b` and `-k` combinations, measure throughput vs notification starvation for other orchagent subscribers
- **Async offload validation** — ResponsePublisher background thread, async swss.rec/sairedis.rec logging
- **Diagnostic tooling** — routeCheck.py, show commands, redis-cli return correct data under async DB writes
- **Crash recovery** — syncd crash during bulk programming → cascade restart → full route recovery
- **SNMP contention** — validate KEYS scan fix eliminates Redis blocking during bulk programming
- **Route churn** — sustained add/delete/update cycles, validate no ZMQ message loss
- **NHG + PIC convergence** — NHG dedup ratio, ECMP member failure O(1) switchover, combined with ZMQ + FIB suppression
- **Scale** — validate at target route scale (1M FIB, 5M+ RIB)

---

## 10. Deployment Sequence

### Step 1 — ZMQ NB+SB with FIB Suppression + Async Offload

**Goal:** Production deployment of ZMQ northbound + southbound with FIB suppression enabled.

**Configuration knobs:**
- ZMQ (northbound + southbound): `SYSTEM_DEFAULTS|swss_zmq:status = enabled`
- FIB suppression: `suppress-fib-pending = enabled`
- Async recording + APPL_STATE_DB offload: `SYSTEM_DEFAULTS|async_rec:status = enabled`
- Batch/bulk tuning: `-b` and `-k` optimized for deployment profile

**Operational fixes:**
- SAI bulk mode (`syncd -l`) enabled by default on Broadcom platforms
- SNMP KEYS scan fix — eliminate Redis contention during bulk programming
- ASIC_DB and APPL_DB diagnostic visibility confirmed (routeCheck.py, show commands)

**Exit criteria:**
- Route programming benchmark passes on target platforms with ZMQ NB+SB + FIB suppression ON
- Diagnostic tooling (routeCheck.py, show commands, redis-cli) works correctly
- syncd crash recovery validated (restart cascade to swss+bgp)
- No regression vs baseline on standard test suite

### Step 2 — RIB/FIB NHG Integration

**Goal:** Enable NHG deduplication and PIC convergence on top of the ZMQ + FIB suppression stack.

**Capabilities to enable:**
- RIB/FIB NHG lifecycle in fpmsyncd (`nhg_fib = enabled`)
- NHG transport over NB ZMQ (same socket as routes — avoids mixed transport race)
- PIC convergence for ECMP member failure (O(1) NHG update propagates to all dependent routes)

**Exit criteria:**
- NHG dedup reduces programming payload by expected ratio (4x for ECMP-heavy profiles)
- PIC convergence meets sub-second target for ECMP member failure
- Combined stack (ZMQ NB+SB + FIB suppression + NHG) validated at target scale

---

## Appendix: Architectural References

| Area | Document |
|------|----------|
| Route download convergence HLD (master knob analysis) | [SONiC#2154](https://github.com/sonic-net/SONiC/pull/2154) |
| ZMQ Northbound HLD (original) | [SONiC#1659](https://github.com/sonic-net/SONiC/pull/1659) |
| ZMQ Northbound HLD (explanation) | [SONiC#2230](https://github.com/sonic-net/SONiC/pull/2230) |
| RIB/FIB NHG lifecycle + PIC convergence HLD | [SONiC#2060](https://github.com/sonic-net/SONiC/pull/2060) |
| Next Hop Group HLD | [doc/ip/next_hop_group_hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/ip/next_hop_group_hld.md) |
| BGP Loading Optimization HLD (ZMQ, Ring Buffer, async SAI) | [doc/bgp_loading_optimization/bgp-loading-optimization-hld.md](../bgp_loading_optimization/bgp-loading-optimization-hld.md) |
| fpmsyncd NHG Enhancement HLD (NTT) | [doc/pic/hld_fpmsyncd.md](https://github.com/sonic-net/SONiC/blob/master/doc/pic/hld_fpmsyncd.md) |
| BGP PIC Architecture | [doc/pic/bgp_pic_arch_doc.md](https://github.com/sonic-net/SONiC/blob/master/doc/pic/bgp_pic_arch_doc.md) |
| FIB Suppression HLD | [doc/BGP/BGP-supress-fib-pending.md](../BGP/BGP-supress-fib-pending.md) |
| SAI PERFMON header extension | [SAI#2279](https://github.com/opencomputeproject/SAI/pull/2279) |
| Snappi/IXIA BGP route convergence test | [sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) |
