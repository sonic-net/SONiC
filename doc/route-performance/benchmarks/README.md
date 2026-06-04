# Route Performance — Benchmarks

This folder is a place for the community to share benchmark data and methodology for route performance testing.

## Recommended Benchmark Methodology

When contributing benchmark results, please include:

### Test Environment

| Item | Details |
|------|---------|
| **SONiC image** | Image name, branch, build date |
| **Platform** | CPU family, core count, clock speed, RAM |
| **ASIC** | Vendor family (e.g., Broadcom DNX, Broadcom XGS) — no need for specific chip model |
| **Topology** | Single-neighbor, multi-neighbor ECMP, single/multi-ASIC |

### Test Parameters

| Parameter | Details |
|-----------|---------|
| **Route count** | Number of routes advertised (e.g., 250K IPv4) |
| **Route type** | IPv4, IPv6, or mixed |
| **Batch size** | `-b` and `-k` parameters if tuned |
| **FIB suppression** | ON or OFF |
| **Traffic generator** | Snappi/IXIA, ExaBGP, or other |

### Measurement

- **Metric**: Routes per second (measured as total routes / total time from first route to last ASIC programming confirmation)
- **Measurement point**: Specify where timing starts and ends (e.g., BGP RIB-IN complete → all routes in ASIC_DB, or FRR received → offload flag set)
- **Repetitions**: Number of test runs, whether results are averaged or best-of

### Optimization Knobs

For each test, clearly state which optimization knobs are enabled:

| Knob | State |
|------|-------|
| ZMQ Northbound | ON/OFF |
| ZMQ Southbound | ON/OFF |
| Multi-DB | ON/OFF |
| Ring Buffer | ON/OFF |
| NHG | ON/OFF |
| Batch tuning | Default / custom (specify) |
| FIB suppression | ON/OFF |
| APPL_STATE_DB | ON/OFF |
| Async mode | ON/OFF |

## Community Test Framework

The sonic-mgmt PR [#22727](https://github.com/sonic-net/sonic-mgmt/pull/22727) provides a Snappi/IXIA-based BGP route convergence test that supports driving different optimization profiles via `fine-tuning.yml`. This can serve as a common test framework for producing comparable results across platforms.
