# Route Performance

This folder provides a collaborative space for the SONiC community to share route performance analysis, optimization strategies, and benchmark data across different network operators and deployment profiles.

## Scope

Route performance spans the full lifecycle:

- **Route download** — BGP RIB → fpmsyncd → orchagent → SAI/ASIC programming
- **Route advertisement** — ASIC offload confirmation → FIB suppression feedback → BGP advertisement
- **Convergence** — ECMP member failure handling, prefix-independent convergence (PIC), reconvergence time

These areas are tightly coupled — for example, FIB suppression ties download completion to advertisement, and NHG/PIC affects both installation speed and failure convergence.

## The Problem

Route performance optimization in SONiC is a **constrained system design problem**. The platform offers 12+ tuning knobs — ZMQ transport, Multi-DB, Ring Buffer, Nexthop Groups, batch tuning, async mode, and more — documented in the community HLD ([SONiC#2154](https://github.com/sonic-net/SONiC/pull/2154)). But these knobs interact: some are complementary, some are mutually exclusive, and production requirements rule out certain combinations entirely.

Each operator brings a unique set of constraints:

- **FIB suppression** — required by some, optional for others — blocks async mode and APPL_STATE_DB disable
- **Warm/fast boot** — changes which optimizations are safe to deploy
- **ECMP profile** — determines whether Nexthop Group deduplication is a 4x win or negligible
- **Topology** — chassis vs pizza-box, single vs multi-ASIC, CPU/memory budget
- **Route scale** — 250K FIB vs 2M FIB changes where bottlenecks appear

The result: **there is no single optimal configuration**. The same knob that delivers 2x improvement for one operator may be incompatible with another's production requirements. Finding the right combination requires understanding how these knobs interact under your specific constraints — a system architecture exercise, not a parameter sweep.

This folder provides a space for operators to share that analysis. By publishing constraint-aware strategies alongside benchmark data, the community can collectively map the optimization landscape and identify which architectural paths lead to the best outcomes for different deployment models.

## Tracking

- Feature request: [SONiC#2238](https://github.com/sonic-net/SONiC/issues/2238) — Route scaling/convergence for Disaggregated Chassis

## Structure

```
route-performance/
├── README.md                          ← This file
├── references.md                      ← Links to HLDs, PRs, and existing community resources
├── strategies/
│   └── large-scale-datacenter-clos-fabric.md  ← Analysis & strategy for large-scale datacenter CLOS fabrics
│   └── (your-org-strategy.md)         ← Contributions welcome
└── benchmarks/
    └── README.md                      ← Benchmark methodology and guidelines
```

## Contributing a Strategy

We encourage network operators to contribute their own route performance analysis. A strategy document typically covers:

1. **Production context** — What constraints shape your optimization choices (FIB suppression, warm boot, topology, scale)
2. **Knob analysis** — Which optimization knobs work for your deployment, which don't, and why
3. **Benchmark data** — Performance measurements with your hardware/topology
4. **Optimization path** — Your phased plan for improving route performance

To contribute:
1. Create a file in `strategies/` named `<your-org>-strategy.md`
2. Open a PR against this repo

There is no required template — each operator's constraints and priorities are different. The goal is shared learning, not uniformity.

## Related Community Resources

| Resource | Description |
|----------|-------------|
| [SONiC#2154](https://github.com/sonic-net/SONiC/pull/2154) | Community HLD — Route download convergence (master knob analysis) |
| [bgp_loading_optimization HLD](../bgp_loading_optimization/bgp-loading-optimization-hld.md) | ZMQ, Ring Buffer, async SAI design HLD |
| [l3-performance-scaling HLD](../l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md) | Broadcom — L3 performance and scaling enhancements (2019) |
| [next_hop_group_hld](../ip/next_hop_group_hld.md) | NHG HLD — Nexthop Group design |
| [BGP FIB suppression HLD](../BGP/BGP-supress-fib-pending.md) | FIB suppression — ties route download to advertisement |
| [PIC architecture](../pic/bgp_pic_arch_doc.md) | Prefix-Independent Convergence — O(1) ECMP failure handling |
| [sonic-mgmt#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) | Snappi/IXIA BGP route convergence test framework |
