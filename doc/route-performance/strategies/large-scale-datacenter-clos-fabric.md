# SONiC Route Download Performance: Large-Scale Datacenter CLOS Fabric Strategy

| | |
|---|---|
| **Version** | 1.0 (Initial) |
| **Author** | Deepak Singhal |
| **Date** | 2026-04-02 |
| **Tracking** | [SONiC#2238](https://github.com/sonic-net/SONiC/issues/2238) |

---

## 1. Production Context

This analysis targets highly redundant Clos networks with specific characteristics that shape the optimization strategy:

| Dimension | Production Requirement |
|-----------|----------------------------|
| **Network layers** | **T2 and above** — pizza-box and disaggregated chassis-based devices in Clos fabric |
| **FIB suppression** | **Required** (`suppress-fib-pending = enabled`) — BGP must not advertise routes until ASIC-confirmed to prevent traffic black holes |
| **Warm/fast boot** | **Not required** — redundant Clos topology with ECMP at every layer; traffic reconverges around a restarting device via alternate paths |
| **ECMP profile** | **90%+ routes form ECMP** from eBGP neighbors — 16-32 eBGP peers per device |
| **Topology** | Chassis linecards and pizza-box form factors, multi-ASIC and single-ASIC, multi-vendor ASICs, 4-16 core CPUs |
| **Route scale** | Target: **1M FIB, 10M BGP RIB** |
| **Telemetry** | gNMI/telemetry used primarily for data streaming (not SNMP polling) |
| **Programming rate** | Routes installed and withdrawn per second are the primary performance metrics |
| **Tunnel overlay** | **Some topologies** — SRv6 or VxLAN tunnels between pizza-box routing nodes. Coexists with pure L3 eBGP topologies using directly connected next-hops. |
| **Failure convergence** | **Sub-second target** — ECMP member failure (link down, node failure) must converge sub-second at production prefix scale. |

### Why this matters

The community HLD ([SONiC#2154](https://github.com/sonic-net/SONiC/pull/2154)) benchmarks 12+ optimization knobs, achieving 2K → 20K+ routes/sec. However, async mode and disable APPL_STATE_DB are incompatible with FIB suppression. Every HLD configuration from T7 onwards (12K+) uses both.

This document analyzes what works best under these production constraints and charts a phased path forward.

---

## 2. Knobs Incompatible with FIB Suppression

The community HLD identifies 12 optimization knobs. With FIB suppression enabled, several are blocked:

| Knob | HLD Impact | Why Blocked with FIB Suppression |
|------|-----------|---------------------|
| **Async mode** | 2K → 2.9K (45% gain) | orchagent doesn't wait for SAI confirmation → writes premature offload status → defeats FIB suppression guarantee (advertises before hardware confirms) |
| **Disable APPL_STATE_DB** | 2K → 4K (100% gain) | FIB suppression IS the APPL_STATE_DB write path. Disabling it breaks the entire feedback loop to fpmsyncd/FRR. |
| **Disable APPL_DB / ASIC_DB** | Not measured separately | Not planned — breaks runtime debugging and operational visibility (redis-cli, routeCheck.py, show commands). |

These knobs are used in HLD configurations T7-T12. With FIB suppression enabled, these configurations are ruled out. The focus shifts to the remaining knobs that are compatible.

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

| Component | Status | Notes |
|-----------|--------|-------|
| ZMQ Northbound (fpmsyncd→orchagent) | In 202511 | Original HLD: [SONiC#1659](https://github.com/sonic-net/SONiC/pull/1659) (liuh-80); Nexthop explanation: [SONiC#2230](https://github.com/sonic-net/SONiC/pull/2230) |
| ZMQ Southbound (orchagent→syncd) | In 202511 | Originally contributed; Nokia PR [sairedis#1801](https://github.com/sonic-net/sonic-sairedis/pull/1801) adds async Redis persistence |

### Path B: Multi-DB + Ring Buffer

**Philosophy**: Keep Redis but reduce contention by splitting databases and decoupling I/O from processing.

```
FRR/zebra ──FPM──► fpmsyncd ──Redis(isolated)──► orchagent ──Redis(isolated)──► syncd/SAI
                   (APPL_DB on separate Redis)    (ASIC_DB on separate Redis)
```

| Component | Status | Notes |
|-----------|--------|-------|
| Multi-DB | In master | Build-time flag `ENABLE_MULTIDB=y` (image rebuild required) |
| Ring Buffer | In master | Decouples ConsumerStateTable pop from orch processing. Redundant with ZMQ NB — ZmqConsumer::execute() calls pops()+drain() directly, does not use processAnyTask/ring buffer. Not incompatible, just adds no value when ZMQ NB is enabled. |

### Head-to-Head Benchmark (Nokia data, Broadcom DNX — AMD 8C 2.5 GHz, 250K IPv4, FIB suppression OFF)

| Configuration | Default Batch | batch=10K |
|---------------|:---:|:---:|
| Multi-DB + Ring Buffer | 8,099/s | 11,160/s |
| **ZMQ NB + ZMQ SB** | **10,588/s** | **12,034/s** |

> ZMQ NB+SB wins across **all 24 test configurations** (2 platforms × 2 protocols × 2 log modes × 3 batch sizes). At default batch size (most production-relevant), ZMQ NB+SB leads by **+31%**. Notably, ZMQ at default batch (10,588/s) matches Multi-DB+RB at batch=10K (11,160/s) — delivering batch-tuned performance without any batch tuning.

---

## 4. Shared Add-On Knobs

These optimizations are independent of the core path choice and provide additive improvement:

| Knob | Expected Gain | Status | FIB-Suppression Compatible? | Notes |
|------|--------------|--------|---------------------|-------|
| **Batch/bulk tuning** (empirical — test `-b` and `-k` combos) | Significant over default batch size | Available | ✅ | Default → b=5K is biggest jump; diminishing returns past 10K. Optimal value depends on deployment profile — test different batch/bulk combinations under production-representative conditions and find the balance between throughput and notification starvation for other orchagent subscribers (port state, ACL, etc.). |
| **Async logging** (syslog to ramdisk) | ~10% (estimated from NO_SWSS_REC proxy) | Needs validation | ⚠️ | Nokia's ~10% gain came from disabling swss.rec/sairedis.rec entirely (NO_SWSS_REC). These .rec files are critical for production debugging (full timestamped timeline of every orchagent op and SAI call). Current `RecWriter::record()` does synchronous `ofstream << val << std::endl` — forces disk flush per route. **Fix: make RecWriter async** (background thread + buffered writes) instead of disabling. Keeps debugging, removes I/O stall. |
| **Sort SAI route bulk** | ~4% | Available | ✅ | Improves SAI batch efficiency |
| **Bypass saimeta::Meta** | Small | Available | ✅ | Reduces CPU in SAI path |
| **SNMP KEYS fix** | Eliminates 50-100ms Redis blocks/5s | Trivial PR needed | ✅ | `rfc1213.py::NextHopUpdater` does `KEYS ROUTE_TABLE:*` every 5s — fetches the entire route table key list from Redis (O(N) scan, blocks Redis event loop). Only actually uses `0.0.0.0/0` default route. Fix: replace with direct key lookup. |

---

## 5. Mid-Term: Nexthop Group (NHG) + RIB/FIB Support

Given a typical ECMP-heavy profile (90%+ routes, 16-32 eBGP neighbors), nexthop group support addresses two dimensions: **route download performance** (4x payload reduction via dedup) and **failure convergence** (O(1) ECMP member switchover via PIC).

### What NHG delivers

```
Route download:   250K routes × ~200 bytes → ~200 NHG objects + 250K × ~50 bytes (4x smaller)
ECMP failure:     Neighbor down → 1 NHG update → all routes inherit    (O(1) vs O(N))
```

### Two community implementations

| | NTT ([swss#2919](https://github.com/sonic-net/sonic-swss/pull/2919)) | Alibaba RIB/FIB ([SONiC#2060](https://github.com/sonic-net/SONiC/pull/2060)) |
|--|-----------------|-----------------|
| Status | ✅ Merged | 🟡 Open (12 PRs across 4 repos) |
| Dedup | ✅ 4x payload reduction | ✅ Same |
| PIC | ❌ No dependency graph | ✅ O(1) via `depends[]`/`dependents[]` backwalk |
| SRv6 | ❌ | ✅ Native VPN route + tunnel NHG handling |
| FRR changes | None | Custom `RTM_NEWNHGFIB` message type |
| New deps | None | `libnexthopgroup` shared library ([buildimage#26423](https://github.com/sonic-net/sonic-buildimage/pull/26423)) |
| Config | `nexthop_group=enabled` | `nhg_fib=enabled` (separate knob) |

These are **parallel code paths, not layers** — each has its own FPM message type, NHG storage, and route lookup logic. Enabling one does not exercise or validate the other.

### Why RIB/FIB for large-scale Clos

For deployments where ECMP failure convergence and tunnel-based forwarding are requirements — for example, disaggregated chassis topologies with NHG primary/backup switchover (<1s target) and SRv6/VxLAN overlay between routing nodes — the RIB/FIB approach provides the necessary dependency graph for PIC (updating a single NHG object propagates to all dependent routes in SAI) that the simpler dedup-only model does not support.

### Current state and adoption path

```
FRR upstream (frr#21415, #21125, #21104)      ← enrich dplane NHG context (needed by SONiC plugin)
  → sonic-frr submodule update                ← picks up upstream changes
sonic-fib library (buildimage#26423)          ← shared NHG serialization
  → FRR dplane plugin (buildimage#26486)      ← dplane_fpm_sonic.c encodes NHG via sonic-fib
  → fpmsyncd core (swss#4419)                 ← NHGMgr processes NHG lifecycle
    → SRv6 support (swss#4420)
    → APPL_STATE_DB feedback (swss#4421)
```

HLD: [SONiC#2060](https://github.com/sonic-net/SONiC/pull/2060) | LLD: [SONiC#2275](https://github.com/sonic-net/SONiC/pull/2275), [SONiC#2274](https://github.com/sonic-net/SONiC/pull/2274)

### Known gap: ZMQ + NHG transport race

fpmsyncd currently sends `NEXTHOP_GROUP_TABLE` via Redis while `ROUTE_TABLE` goes via ZMQ — routes can arrive at orchagent before their NHG references. Fix: extend NB ZMQ to transport NHG on the same socket.

---

## 6. Long-Term: Why Path A (ZMQ) Is the Recommended Direction

### Performance gap today

Section 3's Nokia benchmarks show ZMQ NB+SB leads by **+31% at default batch** (10,588/s vs 8,099/s) and wins across all 24 test configurations. This gap is structural — ZMQ removes Redis serialization from the hot path — and widens under production conditions (FIB suppression, external consumers competing for Redis cycles).

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

This is the remaining Redis bottleneck on orchagent's main thread. `ResponsePublisher` already supports both `db_write_thread` (offload DB writes to background pthread, [swss#3066](https://github.com/sonic-net/sonic-swss/pull/3066), production-validated in P4Orch) and `ZmqServer*` (send responses via ZMQ instead of Redis PUB/SUB). Neither is wired to RouteOrch today — both need code changes + CONFIG_DB knobs for runtime rollback.

| What orchagent main thread does | Today | Target |
|---|---|---|
| NB read | ZMQ | ZMQ |
| SB program | ZMQ | ZMQ |
| Feedback (PUB/SUB + DB write) | Redis (main thread) | **ZMQ + background thread** |
| **Net Redis on main thread** | Feedback I/O | **ZERO** |

### Path B ceiling

Path B (Multi-DB+RB) retains Redis on the forward path for NB, SB, and feedback — the single-thread-per-DB ceiling cannot be removed by configuration.

### Recommendation

The ZMQ path provides a clear trajectory toward zero Redis on the route programming main thread:

```
Today:     NB=ZMQ, SB=ZMQ, Feedback=Redis (main thread)     ← current state
Target:    NB=ZMQ, SB=ZMQ, Feedback=ZMQ+bg thread           ← zero Redis on main thread
```

---

## 7. Known Issues & Challenges

### ZMQ-specific risks

| Issue | Severity | Status | Mitigation |
|-------|----------|--------|------------|
| **del+set regression** ([buildimage#25397](https://github.com/sonic-net/sonic-buildimage/issues/25397)) | High | 🟢 Fixed | [swss#3979](https://github.com/sonic-net/sonic-swss/pull/3979) merged Nov 2025 |
| **APPL_DB async** with NB ZMQ | Low | 🟢 By design | ZMQ sends first, APPL_DB written async. Eventually consistent for routeCheck/show commands. |
| **ASIC_DB not populated** with SB ZMQ | High | 🟡 Open PR | [sairedis#1801](https://github.com/sonic-net/sonic-sairedis/pull/1801) adds async ASIC_DB writes. Needed for routeCheck. |
| **Warm reboot** | Medium | 🟡 Pending | Not a blocker — warm reboot not required for target deployment (Section 1) |
| **Debugging opacity** | Low | 🟢 Manageable | Async DB updates keep Redis populated for diagnostics |
| **NB ZMQ: no persistence** | Medium | 🟡 Inherent | swss restart cascades to bgp → FRR replays RIB → automatic recovery |
| **SB ZMQ: syncd crash recovery** | High | 🔴 Not addressed | syncd restart doesn't cascade to swss (asymmetric with `swss.sh`). Async ASIC_DB can be stale on crash. **Fix:** make syncd restart cascade to swss+bgp (symmetric with `swss.sh`). |

### ZMQ + NHG interaction

| Issue | Severity | Status | Fix |
|-------|----------|--------|-----|
| **Mixed transport race** — NB ZMQ covers ROUTE_TABLE but not NEXTHOP_GROUP_TABLE → routes arrive before their NHG references | High | 🔴 Needs work | Extend NB ZMQ to transport NEXTHOP_GROUP_TABLE on same socket |
| Orch ordering | None | 🟢 Already correct | NhgOrch before RouteOrch in orchdaemon |
| RouteOrch missing NHG retry | None | 🟢 Already handled | Route stays pending for retry |
| NHG persistence on ZMQ | Same as routes | 🟢 Already handled | Same async APPL_DB writes mechanism |

---

## 8. Phased Implementation Plan

### Phase 0 — Target: 202605 release

**FIB suppression: OFF** — Phase 0 qualifies ZMQ NB+SB for production deployment without FIB suppression.

**ZMQ NB + SB enablement and hardening**

- Enable `orch_northbond_route_zmq_enabled = true`
- Add CONFIG_DB knob for SB ZMQ (today SB ZMQ is only enabled via `context_config.json` / syncd CLI flag `-z zmq_sync`, not runtime-toggleable like NB ZMQ)
- Enable SB ZMQ + merge [sairedis#1801](https://github.com/sonic-net/sonic-sairedis/pull/1801) for async ASIC_DB persistence
- Fix syncd crash recovery for SB ZMQ (Section 7: make syncd restart cascade to swss+bgp)
- Harden sonic-mgmt route performance tests (Section 9) — validate with ZMQ NB+SB across platforms

**Batch/Bulk tuning**

- Test different batch size (`-b`) and bulk size (`-k`) combinations under production-representative conditions
- Find the optimal balance between route programming throughput and notification starvation for other orchagent subscribers (port state, ACL, etc.)

**SNMP mitigation**

- Fix `rfc1213.py` KEYS scan contention during bulk route programming

**SAI Performance Monitoring**

- Integrate SAI PERFMON support in SONiC ([SAI#2265](https://github.com/opencomputeproject/SAI/pull/2265) — SAI header open, Broadcom has SAI support)
- Expose SAI-level performance counters in SONiC (design TBD)
- Enhance sonic-mgmt route performance test to report SAI-level results as an additional column alongside end-to-end metrics
- For vendors that do not yet support SAI PERFMON: recommend adding support; SONiC integration will be ready

### Phase 1 — Target: 202611 release

**FIB suppression: ON** — Phase 1 enables FIB suppression alongside ResponsePublisher offload, ensuring the feedback loop doesn't regress performance.

**NHG (RIB/FIB) enablement and hardening**

- All Alibaba RIB/FIB PRs (12 across 4 repos) are in flight; target merge and stabilization
- Feature controlled by CONFIG_DB knob (`nhg_fib=enabled`) — safe to iterate
- Harden via sonic-mgmt tests: NHG + ECMP + FIB suppression combined validation
- Extend NB ZMQ to transport NEXTHOP_GROUP_TABLE on same socket (fix mixed transport race)

**ResponsePublisher offload — remove Redis from orchagent main thread**

- Wire `db_write_thread=true` to RouteOrch's `m_publisher` (Phase 1a: DB writes off main thread)
- Wire ZmqServer to RouteOrch's `m_publisher` + add ZMQ response consumer in fpmsyncd (Phase 1b: PUB/SUB off main thread)
- Expose both as CONFIG_DB knobs for runtime rollback
- Target: **zero Redis I/O on orchagent main thread** for route programming path

---

## 9. Hardening with sonic-mgmt Tests

### Test infrastructure

- [sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) (amitpawar12): Snappi/IXIA BGP route convergence test — drives optimization profiles via `fine-tuning.yml`, measures RIB-IN convergence per combination. 250K routes. PR still open.

### Phase 0 tests (202605) — FIB suppression OFF

These tests validate ZMQ NB+SB, batch/bulk tuning, and baseline stability:

| Test | Purpose | Priority |
|------|---------|----------|
| **ZMQ NB+SB, FIB suppression OFF** | End-to-end ZMQ path validation (no Redis on hot path except feedback) | **Critical** |
| **Batch/Bulk sweep** (vary `-b` and `-k`: 1K/5K/10K/20K combos) | Find optimal batch/bulk balance — measure throughput vs notification starvation (port state, ACL latency) | **Critical** |
| **SNMP impact measurement** | Route download with SNMP running (rfc1213 KEYS scan) vs stopped — validate fix | High |
| **Multi-neighbor ECMP** (10+ neighbors, 250K routes across ECMP groups) | Match production Clos topology, stress ZMQ under ECMP fan-out | High |
| **Stress: rapid route churn** | ZMQ behavior under sustained add/delete/update cycles — validate no message loss | Medium |
| **routeCheck.py validation** | Verify routeCheck does not fire false-positive mismatches with async APPL_DB/ASIC_DB writes under ZMQ NB+SB | High |
| **syncd crash recovery** | Kill syncd during bulk programming → verify swss+bgp cascade restart → full recovery | High |
| **Multi-ASIC / chassis** | Run tests on both single-ASIC/multi-ASIC pizzabox and chassis | High |

### Phase 1 tests (202611) — FIB suppression ON + NHG + ResponsePublisher offload

These tests validate the full production profile with FIB suppression enabled:

| Test | Purpose | Priority |
|------|---------|----------|
| **ZMQ NB+SB + FIB suppression ON** | End-to-end with feedback — compare to Phase 0 numbers | **Critical** |
| **ZMQ NB+SB + FIB suppression ON + ResponsePublisher bg thread** | Validate offload removes feedback penalty | **Critical** |
| **NHG enabled + ZMQ NB+SB + FIB suppression ON** | Full feature stack combined | High |
| **Failover: ECMP member down with NHG** | Measure PIC convergence O(1) vs O(N) | Medium |
| **5M RIB + 500K FIB** | Scale beyond current 250K test baseline | Medium |
| **ZMQ feedback path** (Phase 1b — if ready) | Validate ZMQ replaces Redis PUB/SUB for response channel | Medium |

### Vendor SAI performance baseline

Integrate SAI-level route programming performance counters ([SAI#2265](https://github.com/opencomputeproject/SAI/pull/2265)) into SONiC (design TBD). This helps isolate whether bottlenecks are in the SAI/ASIC layer or the software stack. Enhance sonic-mgmt benchmark test ([sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727)) to collect SAI-level metrics alongside end-to-end route convergence numbers.

---

## Appendix A: Related PRs

### HLD / Design Documents

| PR | Repo | Title | Author | Status |
|----|------|-------|--------|--------|
| [#2267](https://github.com/sonic-net/SONiC/pull/2267) | SONiC | Route Performance Optimization HLD (this PR) | — | Open |
| [#2154](https://github.com/sonic-net/SONiC/pull/2154) | SONiC | Route download convergence HLD (master) | pbrisset (Cisco) | Open |
| [#1659](https://github.com/sonic-net/SONiC/pull/1659) | SONiC | Improve Route Performance HLD (original ZMQ NB) | liuh-80 | Open |
| [#2230](https://github.com/sonic-net/SONiC/pull/2230) | SONiC | Northbound ZMQ HLD (explanation) | inder-nexthop (Nexthop) | Open |
| [#2060](https://github.com/sonic-net/SONiC/pull/2060) | SONiC | RIB/FIB HLD — NHG lifecycle + PIC convergence | eddieruan-alibaba (Alibaba) | Open |

### ZMQ Implementation PRs

| PR | Repo | Title | Author | Status | Phase |
|----|------|-------|--------|--------|-------|
| [#3632](https://github.com/sonic-net/sonic-swss/pull/3632) | sonic-swss | Enable ZMQ for route orch (core NB ZMQ) | liuh-80 | ✅ Merged | 0 |
| [#3620](https://github.com/sonic-net/sonic-swss/pull/3620) | sonic-swss | ZMQ support for swssconfig | liuh-80 | ✅ Merged | 0 |
| [#3619](https://github.com/sonic-net/sonic-swss/pull/3619) | sonic-swss | Dash ZMQ feature flag | liuh-80 | ✅ Merged | 0 |
| [#3837](https://github.com/sonic-net/sonic-swss/pull/3837) | sonic-swss | Fix DPU restart message drop (ZMQ lazy bind) | liuh-80 | ✅ Merged | 0 |
| [#3979](https://github.com/sonic-net/sonic-swss/pull/3979) | sonic-swss | ZMQ del+set DROP fix | — | ✅ Merged Nov 2025 | 0 |
| [#1801](https://github.com/sonic-net/sonic-sairedis/pull/1801) | sonic-sairedis | SB ZMQ async ASIC_DB persistence | vganesan-nokia (Nokia) | Open | 0 |

### NHG / RIB-FIB Implementation PRs

| PR | Repo | Title | Author | Status | Phase |
|----|------|-------|--------|--------|-------|
| [#2919](https://github.com/sonic-net/sonic-swss/pull/2919) | sonic-swss | fpmsyncd NHG Enhancement | ntt-omw (NTT) | ✅ Merged Feb 2025 | 1 |
| [#3742](https://github.com/sonic-net/sonic-swss/pull/3742) | sonic-swss | NHG table unordered_map (20% perf) | liuh-80 | ✅ Merged | 1 |
| [#3605](https://github.com/sonic-net/sonic-swss/pull/3605) | sonic-swss | SRv6 PIC Context in fpmsyncd | GaladrielZhao (Alibaba) | ✅ Merged Nov 2025 | 1 |
| [#4419](https://github.com/sonic-net/sonic-swss/pull/4419) | sonic-swss | fpmsyncd RIB/FIB processing support | GaladrielZhao (Alibaba) | Open | 1 |
| [#4420](https://github.com/sonic-net/sonic-swss/pull/4420) | sonic-swss | SRv6 RIB/FIB in fpmsyncd | GaladrielZhao (Alibaba) | Open | 1 |
| [#4421](https://github.com/sonic-net/sonic-swss/pull/4421) | sonic-swss | fpmsyncd APP_STATE DB support | GaladrielZhao (Alibaba) | Open | 1 |
| [#26486](https://github.com/sonic-net/sonic-buildimage/pull/26486) | sonic-buildimage | FRR NHG encoding for RIB/FIB | GaladrielZhao (Alibaba) | Open | 1 |
| [#26423](https://github.com/sonic-net/sonic-buildimage/pull/26423) | sonic-buildimage | sonic-fib library (libnexthopgroup) | GaladrielZhao (Alibaba) | Open | 1 |

### FIB Suppression / ResponsePublisher PRs

| PR | Repo | Title | Author | Status | Phase |
|----|------|-------|--------|--------|-------|
| [#3066](https://github.com/sonic-net/sonic-swss/pull/3066) | sonic-swss | P4Orch background thread for ResponsePublisher | — | ✅ Merged May 2024 | 1 |
| [#4333](https://github.com/sonic-net/sonic-swss/pull/4333) | sonic-swss | Skip APPL_STATE_DB when FIB suppression OFF | mike-dubrovsky (Cisco) | Open | 0 |
| [#26151](https://github.com/sonic-net/sonic-buildimage/pull/26151) | sonic-buildimage | Pass FIB suppression flag to orchagent | mike-dubrovsky (Cisco) | Open | 0 |
| [#4361](https://github.com/sonic-net/sonic-utilities/pull/4361) | sonic-utilities | route_check FIB suppression from STATE_DB | mike-dubrovsky (Cisco) | Open | 0 |

### SAI Performance Monitoring

| PR | Repo | Title | Author | Status | Phase |
|----|------|-------|--------|--------|-------|
| [#2265](https://github.com/opencomputeproject/SAI/pull/2265) | SAI | SAI PERFMON header extension | — | Open | 0 |

### Test / sonic-mgmt PRs

| PR | Repo | Title | Author | Status | Phase |
|----|------|-------|--------|--------|-------|
| [#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) | sonic-mgmt | Snappi BGP route perf test | amitpawar12 | Open | 0 |
| [#22916](https://github.com/sonic-net/sonic-mgmt/pull/22916) | sonic-mgmt | config_reload after suppress-fib changes | mike-dubrovsky (Cisco) | Open | 0 |

### Reference HLDs

| Document | Location |
|----------|----------|
| Next Hop Group HLD | [sonic-net/SONiC/doc/ip/next_hop_group_hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/ip/next_hop_group_hld.md) |
| fpmsyncd NHG Enhancement HLD (NTT) | [sonic-net/SONiC/doc/pic/hld_fpmsyncd.md](https://github.com/sonic-net/SONiC/blob/master/doc/pic/hld_fpmsyncd.md) |
| BGP PIC Architecture | [sonic-net/SONiC/doc/pic/bgp_pic_arch_doc.md](https://github.com/sonic-net/SONiC/blob/master/doc/pic/bgp_pic_arch_doc.md) |

## Appendix B: Benchmark Data Summary

TBD
