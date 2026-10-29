# sFlow Support on T2 Chassis in Packet Mode

## Table of Contents

1. [Revision History](#1-revision-history)
2. [Scope](#2-scope)
3. [Definitions and Abbreviations](#3-definitions-and-abbreviations)
4. [Overview and Use Case](#4-overview-and-use-case)
5. [Requirements](#5-requirements)
6. [Architecture](#6-architecture)
7. [High-Level Design](#7-high-level-design)
8. [SAI API and SDK Changes](#8-sai-api-and-sdk-changes)
9. [Configuration and Management](#9-configuration-and-management)
10. [Warmboot and Fastboot Impact](#10-warmboot-and-fastboot-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions, Limitations, and Non-Requirements](#12-restrictions-limitations-and-non-requirements)
13. [Testing Requirements](#13-testing-requirements)
14. [Open Questions and Action Items](#14-open-questions-and-action-items)
15. [References](#15-references)

## 1. Revision History

| Version | Date | Author | Description |
| --- | --- | --- | --- |
| 0.1 | 2026-10-20 | Sridhar Talari Rajagopal, Cisco | Initial draft for sFlow support on T2 chassis in packet mode. |
| 0.2 | 2026-10-23 | Sridhar Talari Rajagopal, Cisco | Cleaned up document structure and terminology; added revision history and unit and system test tables. |
| 0.3 | 2026-10-27 | Sridhar Talari Rajagopal, Cisco | Editorial cleanup: fixed typos and wording, restructured the high-level design, feature enablement, and design choices sections, and populated open questions. |
| 0.4 | 2026-10-29 | Sridhar Talari Rajagopal, Cisco | Aligned the design with a single global sFlow configuration applied to all ASIC namespaces and an interface-derived namespace for `config sflow interface`; excluded fabric interfaces and fabric-card ASICs; reworked CLI, design choices, and test cases accordingly. |

## 2. Scope

This document describes the high-level design changes required to support sFlow on a T2 chassis operating in packet mode (`DEVICE_METADATA.localhost.switch_type = chassis-packet`).
The scope includes support for ingress sampling on designated line-card front-panel interfaces and delivery of sFlow datagrams to IPv4 and IPv6 collectors through front-panel ports.
It builds on the existing single-node sFlow HLD and does **not** replace that design for fixed or VOQ systems.

## 3. Definitions and Abbreviations

| Term | Definition |
| --- | --- |
| APPL_DB | SONiC application database. |
| ASIC | Application-specific integrated circuit. |
| ASIC namespace | The Linux network namespace associated with an ASIC instance. |
| CONFIG_DB | SONiC configuration database. |
| hsflowd | Host sFlow daemon that builds and exports sFlow datagrams. |
| KNET | Kernel network driver used to deliver packets from the ASIC to the CPU. |
| LC | Line card. |
| psample | Linux kernel packet-sampling framework that exposes samples over a generic netlink (genetlink) group. |
| SAI | Switch Abstraction Interface. |
| SDK | Software development kit. |
| sFlow | A standards-based technology for monitoring network traffic using sampling. |
| T2 chassis | The modular chassis platform (supervisor and line cards) targeted by this design. |
| VOQ | Virtual output queue. |

## 4. Overview and Use Case

sFlow provides traffic visibility on switches and routers by sampling packets and exporting the samples to a collector.
The existing SONiC sFlow design is described in the [SONiC sFlow HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sflow/sflow_hld.md).

A T2 chassis in packet mode runs a SONiC stack per ASIC instance.
See the [SONiC Multi-ASIC HLD](https://github.com/sonic-net/SONiC/blob/master/doc/multi_asic/SONiC_multi_asic_hld.md) for the underlying architecture.

The target use case is to monitor ingress traffic on selected line-card front-panel interfaces and export the resulting sFlow datagrams through a front-panel port.

## 5. Requirements

| ID | Requirement |
| --- | --- |
| R1 | Support ingress sFlow on designated line-card front-panel interfaces. |
| R2 | No sFlow support on fabric interfaces of line-card ASICs. |
| R3 | No sFlow support on ASICs of fabric cards. |
| R4 | Support sampling configuration (rate) at the port level. |
| R5 | Inject and forward sFlow datagrams through a front-panel port to the collector. |
| R6 | Support both IPv4 and IPv6 collectors. |
| R7 | Provide a single global sFlow configuration (enable/disable, collectors, polling interval, agent-id) that is applied to all ASIC namespaces of the line card. |
| R8 | Resolve the ASIC namespace of a per-interface sFlow configuration from the interface name. |
| R9 | Provide a show CLI that displays sFlow state per ASIC namespace. |

## 6. Architecture

![sFlow fixed system high-level design](./fixed-system-sflow.png)

The diagram above shows the existing SONiC sFlow architecture on a fixed system. This design extends it to the T2 chassis packet-mode deployment, shown below.

The design consists of the following changes:

- Instantiate a separate `sflow` container per namespace.
- Instantiate a psample genetlink socket per namespace.
- Demultiplex sample packets received in the KNET driver to the corresponding genetlink socket, based on the incoming interface.
- Apply global `config sflow` settings to the CONFIG_DB of every ASIC namespace, and derive the namespace of `config sflow interface` settings from the interface name.
- Enhance the show CLI to take the namespace into consideration.

![sFlow high-level design](./sflow.png)

## 7. High-Level Design

The logical data path for each ASIC namespace is:

1. An ASIC samples ingress traffic on an enabled line-card front-panel interface.
2. The sample is demultiplexed to the corresponding ASIC namespace.
3. The sFlow processing path in that namespace forms a datagram for the configured collector.
4. The datagram is injected and forwarded through a front-panel port toward the collector.

### 7.1. Per-ASIC Components

The following components are instantiated once per line-card ASIC:

| Component | Function |
| --- | --- |
| `sflowmgrd` | Translates CONFIG_DB to the APPL_DB `SFLOW_SESSION_TABLE` and starts/stops `hsflowd`. |
| `sfloworch` | Creates SAI samplepacket objects and sets `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE`. |
| ASIC / psample | The ASIC posts samples on the genetlink psample `packets` group. |
| `hsflowd` | Builds sFlow v5 datagrams and sends them over UDP to the collector. |

### 7.2. Sampling and Namespace Handling

Sampling is limited to designated ingress front-panel interfaces. Fabric, backplane, and internal interfaces of line-card ASICs, and all ASICs on fabric cards, are outside the scope of this design; `config sflow interface` must reject such interfaces and no `sflow` container is instantiated for fabric-card ASICs.

Sample processing must preserve the association between the sample, its source interface, and its ASIC namespace. Namespace demultiplexing must prevent samples from being attributed to a different ASIC or interface.

### 7.3. Collector Delivery

The export path must support IPv4 and IPv6 collector addresses and use front-panel connectivity. The management-port collector path is outside the scope of this design.

### 7.4. Implementation Dependencies

| Area | Design Status |
| --- | --- |
| Feature integration | Extend existing SONiC sFlow support; Application Extension manifest is not applicable. |
| Modules and repositories | sonic-buildimage, sonic-utilities. |
| SWSS and syncd | No changes anticipated |
| Database schemas | No changes anticipated. Existing `SFLOW`, `SFLOW_SESSION` and `SFLOW_COLLECTOR` CONFIG_DB tables are used in each ASIC namespace. |
| Linux interfaces and dependencies | psample genetlink socket per namespace. |
| Containers and build dependencies | No changes anticipated. |
| Platform dependencies | T2 packet-mode sample delivery and front-panel injection support must be confirmed. |
| Serviceability | No changes. |
| Scale and performance | Supported port count, collector count, sample throughput, and CPU limits are TBD. |

### 7.5. Feature Enablement

The sFlow feature is disabled by default in `init_cfg.json.j2`. The `FEATURE` table entry is what starts the `sflow@N` units, so the units are controlled by the feature state and not by `config sflow enable`.

- `config feature state sflow enabled|disabled` performs multi-ASIC writes. It loops over every namespace's CONFIG_DB (`db.cfgdb_clients`), first checks that the feature exists and has the same state in all of them, and then writes the state to all of them.
- `config sflow enable` sets `admin_state=up` in the host namespace's CONFIG_DB only. On a packet-mode chassis it instead writes `admin_state` to the CONFIG_DB of every ASIC namespace, as described in [Section 9.2](#92-cli-and-yang-models).

### 7.6. Design Choices

| Choice | Selected approach |
| --- | --- |
| sFlow instances | One `hsflowd` instance per ASIC namespace rather than a single instance per line card. A single instance does not help, because the collector is reachable only through front-panel interfaces that belong to individual ASIC namespaces. |
| Configuration CLI scope | `config sflow` is global: it is applied to every ASIC namespace of the line card, so the user does not pass `-n`. `config sflow interface` resolves the namespace from the interface name. Per-namespace configuration commands are not introduced. |
| Show CLI scope | `show sflow` accepts an optional `-n <asicN>` to display a single namespace, and displays all namespaces by default. |

## 8. SAI API and SDK Changes

No SAI API changes are currently expected. Sample demultiplexing per ASIC namespace is required.

## 9. Configuration and Management

### 9.1. Application Extension Manifest

Not applicable.

### 9.2. CLI and YANG Models

The design requires port-level sampling configuration and IPv4 and IPv6 collector configuration.

**`config sflow ...`**

On a T2 packet-mode chassis the command syntax is unchanged and `-n` is not required. Global settings are written to the CONFIG_DB of **every** ASIC namespace of the line card, so the configuration is identical across namespaces (R7).

| Command | Behavior on a packet-mode chassis |
|---|---|
| `config sflow enable \| disable` | Writes `admin_state` to all ASIC namespaces. The host `sflow` unit is not touched. |
| `config sflow polling-interval <0\|5-300>` | Applied to all ASIC namespaces. |
| `config sflow sample-direction <rx\|tx\|both>` | Applied to all ASIC namespaces; see open question 3. |
| `config sflow drop-monitor-limit <pps>` | Applied to all ASIC namespaces. |
| `config sflow collector add <name> <ip> [--port 6343] [--vrf default\|mgmt]` | Added in all ASIC namespaces; see open questions 1 and 3. |
| `config sflow collector del <name>` | Removed from all ASIC namespaces. |
| `config sflow agent-id add <ifname>` \| `del` | Applied to all ASIC namespaces; see open question 10. |

A global write that cannot be completed on every namespace must not leave namespaces in different states: the command validates all namespaces first and reports an error naming the failing namespace without writing (see open question 11).

**`config sflow interface ...`**

The namespace is derived from the interface name: the command is applied to the ASIC namespace that owns the interface and fails if the interface is not a designated front-panel interface of any ASIC on the line card (for example, a fabric, backplane, or internal interface).

| Command | Behavior on a packet-mode chassis |
|---|---|
| `config sflow interface enable \| disable <ifname>` | Applied in the owning ASIC namespace. |
| `config sflow interface sample-rate <ifname> <rate>` | Applied in the owning ASIC namespace. |
| `config sflow interface sample-direction <ifname> <rx\|tx\|both>` | Applied in the owning ASIC namespace; see open question 3. |
| `config sflow interface enable \| disable \| sample-rate \| sample-direction all ...` | Applied to the front-panel interfaces of every ASIC namespace, each in its own namespace. |

**`show sflow [-n <asicN>]`**

- `show sflow` shows the global settings. On a packet-mode chassis without `-n`, it prints every ASIC under an `=== asicN ===` banner.
- `show sflow interface` shows per-interface settings and also accepts `-n`.
- `-n` can be given on the group or on `interface`. An invalid namespace is rejected, as is `-n` on a single-ASIC system. Because the global settings are identical on all namespaces, any difference shown between banners indicates a failed or partial configuration write.
- On other platforms, `show sflow` behaves as before.

**Unchanged:**

- `config feature state sflow enabled|disabled` is unchanged. It already writes to all namespaces.
- `config sflow ...` is guarded by the same `ADHOC_VALIDATION` and YANG-validation behavior as before. Validated writes are issued against each target namespace's CONFIG_DB.

Any changes must preserve compatibility with existing saved configurations. If CLI changes are required, update the [SONiC Command Reference](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md).

### 9.3. CONFIG_DB

Any schema changes, namespace ownership rules, and validation rules are TBD. The sampling rate is configured per port; configuration handling must define the default rate for ports that have none and how rates that differ between ports or namespaces are handled.

### 9.4. Other Management Interfaces

Requirements for SNMP, REST, and gNMI exposure are TBD.

## 10. Warmboot and Fastboot Impact

Warmboot and fastboot behavior must be validated with sFlow enabled and disabled. The expected configuration restoration sequence, sampling recovery behavior, and collector export recovery time are TBD.

### 10.1. Performance Impact

Measure control-plane and data-plane downtime against the existing platform baseline. The feature must meet the platform's established reboot requirements; specific acceptance thresholds are TBD.

The implementation review must identify any new CPU processing, I/O, dependency initialization, or blocking operations in the boot path. Whether sFlow startup can be deferred and whether any additional boot-time cost requires optimization are TBD.

## 11. Memory Consumption

Quantitative memory estimates are TBD. Measure memory usage with the feature disabled, enabled without traffic, and enabled under sustained sampling load.

No additional runtime memory usage is expected when the feature is excluded from the build. When disabled by configuration, the feature must not exhibit unbounded memory growth. Sample processing and export must remain bounded during collector or injection failures.

## 12. Restrictions, Limitations, and Non-Requirements

### 12.1. Limitations

This design targets T2 chassis operating in packet mode. Supported scale, performance limits, and platform-specific constraints are TBD.

### 12.2. Non-Requirements

The following are outside the scope of this design:

- Sampling on fabric, backplane, or internal interfaces, and on ASICs of fabric cards.
- Per-namespace (`-n`) configuration commands.
- Egress traffic sampling.
- Collector delivery through the management port.
- Hardware-based sFlow.

## 13. Testing Requirements

The following tables define proposed test coverage, not execution results. Test framework ownership, fixtures, statistical tolerances, and performance thresholds are TBD.

### 13.1. Unit Test Cases

Use mocks or fixtures for configuration, namespace metadata, sample delivery, and export interfaces where appropriate.

| Test ID | Area | Test Case | Expected Result |
| --- | --- | --- | --- |
| UT-01 | Port configuration | Enable and disable ingress sampling on a designated front-panel port. | Sampling state is applied to the intended port and removed when disabled. |
| UT-02 | Interface eligibility | Attempt to enable sampling on fabric, backplane, or internal interfaces of a line-card ASIC. | The command is rejected and the interface is not programmed for sampling. |
| UT-03 | Sampling rate | Configure different sampling rates on multiple designated ports, including ports of different ASIC namespaces. | Each enabled port receives its own configured rate in its owning namespace. |
| UT-04 | Configuration validation | Supply invalid rates, invalid collector addresses, and an unknown interface name. | Invalid values are rejected and nothing is written to any namespace. |
| UT-05 | Namespace demultiplexing | Deliver samples with valid metadata for multiple ASIC namespaces. | Each sample is assigned to the correct namespace and source interface. |
| UT-06 | Invalid sample metadata | Deliver malformed samples or samples with unknown namespace or interface metadata. | Samples are handled safely without incorrect attribution or process failure; diagnostics follow the finalized design. |
| UT-07 | IPv4 export | Process a sample with an IPv4 collector configured. | The export path forms a datagram for the configured IPv4 destination. |
| UT-08 | IPv6 export | Process a sample with an IPv6 collector configured. | The export path forms a datagram for the configured IPv6 destination. |
| UT-09 | Front-panel injection | Exercise export with a mocked front-panel injection interface. | The datagram is submitted to the intended front-panel export path. |
| UT-10 | Export failure | Simulate injection errors or an unavailable export interface. | Failures do not crash sample processing or cause unbounded buffering. |
| UT-11 | Configuration lifecycle | Add, update, and remove port and collector configuration. | Processing reflects the latest configuration and releases stale state. |
| UT-12 | Global configuration propagation | Run `config sflow enable`, `polling-interval`, `sample-direction`, `collector add`, and `agent-id add` without `-n` on a packet-mode chassis. | The setting is written to the CONFIG_DB of every ASIC namespace and the host `sflow` unit is not modified. |
| UT-13 | Global configuration removal | Run `config sflow disable`, `collector del`, and `agent-id del` without `-n`. | The setting is removed or disabled in every ASIC namespace. |
| UT-14 | Global write atomicity | Make one namespace's CONFIG_DB unavailable or fail validation, then run a global `config sflow` command. | The command fails with an error naming the namespace and no namespace is modified. |
| UT-15 | Interface-to-namespace resolution | Run `config sflow interface enable`, `disable`, `sample-rate`, and `sample-direction` for interfaces that belong to different ASIC namespaces. | Each setting is written only to the CONFIG_DB of the namespace that owns the interface. |
| UT-16 | Interface `all` expansion | Run `config sflow interface enable all` and `sample-rate all <rate>`. | Every eligible front-panel interface is configured in its own namespace; fabric, backplane, and internal interfaces are skipped. |
| UT-17 | Namespace option handling | Pass `-n` to `config sflow`; pass an invalid namespace to `show sflow -n`; pass `-n` on a single-ASIC system. | Behavior follows Section 9.2: `show` rejects invalid namespaces and `-n` on single-ASIC systems; `-n` is not required by any `config sflow` command. |
| UT-18 | Show CLI | Run `show sflow` and `show sflow interface` with and without `-n asicN`. | Without `-n`, every ASIC is printed under an `=== asicN ===` banner; with `-n`, only that namespace is shown. |
| UT-19 | Non-chassis behavior | Run the `config sflow` and `show sflow` commands on single-ASIC and non-packet-mode multi-ASIC systems. | Behavior is unchanged from the existing sFlow design. |

### 13.2. System Test Cases

Run on a supported T2 chassis in packet mode with traffic generation and collector capture available. Record topology, ASIC namespaces, software version, port configuration, and collector addresses for each run.

| Test ID | Area | Test Case | Expected Result |
| --- | --- | --- | --- |
| ST-01 | Ingress sampling | Send traffic into an enabled designated front-panel interface. | The collector receives samples attributed to the correct ingress interface. |
| ST-02 | Port isolation | Send traffic into enabled and disabled front-panel interfaces. | Samples are exported only for enabled interfaces. |
| ST-03 | Excluded traffic | Exercise fabric/backplane/internal traffic and traffic that only egresses a designated interface. | Excluded interfaces and egress-only traffic do not generate samples. |
| ST-04 | Sampling rate | On ports with different configured rates, send a sufficiently large packet population per port, including 1 in 10,000 if adopted. | The observed sampling ratio on each port falls within the agreed statistical tolerance of that port's configured rate. |
| ST-05 | Multiple ASICs | Sample traffic concurrently on ports belonging to different ASIC namespaces. | Samples retain correct namespace and interface attribution without cross-namespace leakage. |
| ST-06 | IPv4 collector | Export samples to a reachable IPv4 collector. | Valid sFlow datagrams arrive at the configured IPv4 collector. |
| ST-07 | IPv6 collector | Export samples to a reachable IPv6 collector. | Valid sFlow datagrams arrive at the configured IPv6 collector. |
| ST-08 | Export path | Capture exported datagrams on the front-panel and management paths. | Datagrams use the intended front-panel path; no sFlow export uses the management port. |
| ST-09 | Configuration persistence | Save and reload port and collector configuration. | Supported settings are restored and sampling resumes with correct attribution and delivery. |
| ST-10 | Collector failure | Remove collector reachability, sustain sampling, and restore reachability. | Forwarding remains stable, resource usage remains bounded, and export recovers after reachability returns. |
| ST-11 | Service recovery | Restart affected sFlow services or containers while sampling is active. | Sampling and export recover with the configured port, namespace, and collector state. |
| ST-12 | Warmboot | Perform warmboot with sFlow enabled and repeat with it disabled. | Configuration and export recover; forwarding disruption meets existing platform requirements. |
| ST-13 | Fastboot | Perform fastboot with sFlow enabled and repeat with it disabled. | Configuration and export recover; boot time and forwarding disruption meet existing platform requirements. |
| ST-14 | Scale and soak | Exercise the agreed maximum port and collector scale under sustained sampling load. | CPU, memory, sample loss, and export throughput remain within agreed limits without unbounded growth. |
| ST-15 | Regression | Exercise existing sFlow configurations and normal forwarding with the feature enabled and disabled. | Existing supported behavior and forwarding meet the platform baseline. |
| ST-16 | Global configuration | Configure the collector, polling interval, and `enable` once with `config sflow` (no `-n`), then enable interfaces on at least two ASIC namespaces. | `show sflow` shows identical global settings under every ASIC banner, and samples from ports on every ASIC reach the collector. |
| ST-17 | Global disable | Run `config sflow disable` while sampling on multiple ASICs, then re-enable. | Sample export stops on every ASIC and resumes on every ASIC after re-enable. |
| ST-18 | Interface namespace resolution | Enable sFlow on one port in each of two ASIC namespaces with different rates using `config sflow interface`. | Each port is configured only in its owning namespace (`show sflow interface -n asicN`) and samples carry the correct ingress interface and rate. |
| ST-19 | Fabric exclusion | Attempt `config sflow interface enable` on a line-card fabric interface; verify no `sflow` container is running on fabric-card ASICs. | The command is rejected, no samples are generated from fabric traffic, and fabric-card ASICs run no sFlow instance. |
| ST-20 | Feature state | Run `config feature state sflow enabled` and `disabled`. | The `sflow@N` unit starts or stops on every ASIC namespace and the feature state is identical across all CONFIG_DBs. |

## 14. Open Questions and Action Items

| # | Item | Owner |
| --- | --- | --- |
| 1 | Define collector configuration ownership, route selection, source address selection, and injection behavior across namespaces. | TBD |
| 2 | Define the default sampling rate for ports without an explicit rate and how rates that differ between ports or namespaces are handled (see UT-03, ST-04). | TBD |
| 3 | Reconcile the CLI with the stated non-requirements: `sample-direction` accepts `tx` and `both`, and `collector add` accepts `--vrf mgmt`, while egress sampling and management-port collector delivery are out of scope (Section 12.2). Decide whether to restrict these options on packet-mode chassis. | TBD |
| 4 | Confirm repositories and modules to be changed, and ownership of each change. | TBD |
| 5 | Define CONFIG_DB schema changes, if any, and namespace validation rules. | TBD |
| 6 | Confirm platform support for T2 packet-mode sample delivery and front-panel injection. | TBD |
| 7 | Define serviceability (logging, counters, diagnostics) for namespace attribution and export failures. | TBD |
| 8 | Define scale and performance targets, warmboot/fastboot acceptance thresholds, and quantitative memory estimates. | TBD |
| 9 | Define SNMP, REST, and gNMI exposure requirements. | TBD |
| 10 | Define how a global `agent-id` interface is resolved in each ASIC namespace, since the interface (for example a loopback) may not exist in every namespace. | TBD |
| 11 | Define the failure semantics of global `config sflow` writes (pre-validate all namespaces, as assumed in Section 9.2 and UT-14, versus best-effort with rollback). | TBD |

## 15. References

- [SONiC sFlow HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sflow/sflow_hld.md)
- [SONiC Multi-ASIC HLD](https://github.com/sonic-net/SONiC/blob/master/doc/multi_asic/SONiC_multi_asic_hld.md)
- Implementation: [cisco-wb-bsp PR 2752](https://wwwin-github.cisco.com/whitebox/cisco-wb-bsp/pull/2752), [sonic-buildimage PR 4747](https://wwwin-github.cisco.com/whitebox/sonic-buildimage/pull/4747)

