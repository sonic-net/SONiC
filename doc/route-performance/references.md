# Route Performance — References

A consolidated list of HLDs, implementation PRs, known issues, and reference documents related to SONiC route performance optimization.

## HLD / Design Documents

| PR | Repo | Title | Author | Status |
|----|------|-------|--------|--------|
| [#2154](https://github.com/sonic-net/SONiC/pull/2154) | SONiC | Route download convergence HLD (master) | pbrisset (Cisco) | Open |
| [#1659](https://github.com/sonic-net/SONiC/pull/1659) | SONiC | Improve Route Performance HLD (original ZMQ NB) | liuh-80 | Open |
| [#2230](https://github.com/sonic-net/SONiC/pull/2230) | SONiC | Northbound ZMQ HLD (explanation) | inder-nexthop (Nexthop) | Open |
| [#2060](https://github.com/sonic-net/SONiC/pull/2060) | SONiC | RIB/FIB HLD — NHG lifecycle + PIC convergence | eddieruan-alibaba (Alibaba) | Open |

## Implementation PRs

| PR | Repo | Title | Author | Status |
|----|------|-------|--------|--------|
| [#2919](https://github.com/sonic-net/sonic-swss/pull/2919) | sonic-swss | fpmsyncd NHG Enhancement | ntt-omw (NTT) | ✅ Merged Feb 2025 |
| [#3066](https://github.com/sonic-net/sonic-swss/pull/3066) | sonic-swss | P4Orch background thread for ResponsePublisher | — | ✅ Merged May 2024 |
| [#3605](https://github.com/sonic-net/sonic-swss/pull/3605) | sonic-swss | SRv6 PIC Context in fpmsyncd | GaladrielZhao (Alibaba) | ✅ Merged Nov 2025 |
| [#4333](https://github.com/sonic-net/sonic-swss/pull/4333) | sonic-swss | Skip APPL_STATE_DB when FIB suppression OFF | mike-dubrovsky (Cisco) | Open |
| [#26151](https://github.com/sonic-net/sonic-buildimage/pull/26151) | sonic-buildimage | Pass FIB suppression flag to orchagent | mike-dubrovsky (Cisco) | Open |
| [#4361](https://github.com/sonic-net/sonic-utilities/pull/4361) | sonic-utilities | route_check FIB suppression from STATE_DB | mike-dubrovsky (Cisco) | Open |
| [#1801](https://github.com/sonic-net/sonic-sairedis/pull/1801) | sonic-sairedis | SB ZMQ async ASIC_DB persistence | vganesan-nokia (Nokia) | Open |
| [#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) | sonic-mgmt | Snappi BGP route perf test | amitpawar12 | Open |
| [#22916](https://github.com/sonic-net/sonic-mgmt/pull/22916) | sonic-mgmt | config_reload after suppress-fib changes | mike-dubrovsky (Cisco) | Open |

## Known Issues

| Issue | Repo | Title | Status |
|-------|------|-------|--------|
| [#2238](https://github.com/sonic-net/SONiC/issues/2238) | SONiC | Route scaling/convergence for Disaggregated Chassis | Open |
| [#25397](https://github.com/sonic-net/sonic-buildimage/issues/25397) | sonic-buildimage | Regression: route update time in 202511 | Open |
| [#23459](https://github.com/sonic-net/sonic-buildimage/pull/23459) | sonic-buildimage | NHG disabled (stability concern) | Merged 2024 — not reproducible |

## Reference HLDs (already in repo)

| Document | Location |
|----------|----------|
| Next Hop Group HLD | [doc/ip/next_hop_group_hld.md](../ip/next_hop_group_hld.md) |
| BGP Loading Optimization HLD | [doc/bgp_loading_optimization/bgp-loading-optimization-hld.md](../bgp_loading_optimization/bgp-loading-optimization-hld.md) |
| fpmsyncd NHG Enhancement HLD (NTT) | [doc/pic/hld_fpmsyncd.md](../pic/hld_fpmsyncd.md) |
| BGP PIC Architecture | [doc/pic/bgp_pic_arch_doc.md](../pic/bgp_pic_arch_doc.md) |
| Fine Grained ECMP HLD | [doc/ecmp/fine_grained_next_hop_hld.md](../ecmp/fine_grained_next_hop_hld.md) |
| FIB Suppression HLD | [doc/BGP/BGP-supress-fib-pending.md](../BGP/BGP-supress-fib-pending.md) |
