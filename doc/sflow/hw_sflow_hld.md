# Hardware Accelerated sFlow High Level Design

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 SAI object flow](#71-sai-object-flow)
  - [7.2 Collector resolution](#72-collector-resolution)
  - [7.3 Serviceability and debug](#73-serviceability-and-debug)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI and YANG model enhancements](#92-cli-and-yang-model-enhancements)
  - [9.3 Config DB enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit test cases](#131-unit-test-cases)
  - [13.2 System test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items---if-any)

### 1. Revision

| Revision | Date | Author | Change Description |
| ----- | ----- | ----- | ----- |
| 0.1 | 2026-08-15 | darius-nexthop | Initial Proposal |

### 2. Scope

This document describes an optional sFlow datapath for SONiC: hardware
accelerated sFlow. On ASICs that support it, the switch builds sFlow v5
datagrams in silicon and sends them straight to the collector rather than
punting every sampled packet to the CPU.

Hardware acceleration applies to **flow samples only**. Counter samples, the
hsflowd agent, and every other part of the sFlow subsystem continue to operate
unchanged on the CPU path regardless of the selected mode.

### 3. Definitions/Abbreviations

| Term | Definition |
| :---- | :---- |
| sFlow | Sampled flow, sFlow v5 (sflow.org) |
| HW sFlow | Hardware accelerated sFlow: the ASIC builds and sends the datagram |
| CPU sFlow | The existing sample-and-punt datapath described in [`sflow_hld.md`](https://github.com/sonic-net/SONiC/blob/master/doc/sflow/sflow_hld.md) |
| SAI | Switch Abstraction Interface |
| hsflowd | [InMon host-sflow](https://github.com/sflow/host-sflow) agent, SONiC's userspace sFlow agent |

### 4. Overview

This document proposes an alternative flow-sampling datapath for SONiC:
hardware accelerated sFlow. When it is selected, `SflowOrch` creates a SAI
mirror session of type sFlow and binds it to sampled ports; the ASIC then
samples, aggregates, and emits sFlow v5 datagrams without CPU involvement.
Because the datagram is built in silicon, its encapsulation must be supplied
up front, so `SflowOrch` takes a dependency on `NeighOrch` and `RouteOrch` to
resolve the path to the collector and to refresh it on change. The path is
gated on platform capability.

### 5. Requirements

Supported:

- Opt-in through a new `mode` field via CLI, reflected in `CONFIG_DB:SFLOW|global`.
- Gated on platform capability, published in `STATE_DB:SWITCH_CAPABILITY`.
- Ingress sampling on physical ports and PortChannels.
- IPv4 and IPv6 collectors.
- Per-port sample rate and header truncation size.
- Encapsulation (destination MAC, source MAC, source IP, egress port) resolved
  automatically from routing and neighbor state, refreshed on change.
- Selected mode and per-collector resolution visible in `show sflow`.

Not supported:

- Egress sampling (`tx`, `both`).
- Hardware counter samples (still egress via CPU path).

### 6. Architecture Design

This design does not change the SONiC architecture. `SflowOrch` gains a
`HwSflow` class that owns the sFlow mirror session and the per-port sample
bindings for the hardware datapath. The existing CPU path is untouched and
remains the default. Other sFlow features, such as counter samples and MOD,
will remain unimpacted on the CPU path regardless of `mode` configuration.

### 7. High-Level Design

#### 7.1 SAI object flow

For each collector, `HwSflow` creates one mirror session of type sFlow and
binds it to every sampled port.

Throughout this document, the **collector-facing port** is the port sFlow
datagrams egress towards the collector on. It is programmed as
`SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` and is unrelated to egress sampling,
which the hardware path does not support.

```mermaid
flowchart TB
    CFG["CONFIG_DB<br/>SFLOW · SFLOW_COLLECTOR · SFLOW_SESSION"] --> ORCH
    NR["NeighOrch / RouteOrch"] -->|"collector-facing port,<br/>next-hop MAC, src MAC"| ORCH
    ORCH["HwSflow (SflowOrch, sonic-swss)"] ==>|creates| MS
    subgraph MS["MIRROR_SESSION — TYPE = sFlow"]
        direction LR
        SMP["<b>Sampling</b><br/>rate = 1-in-N<br/>truncate size"]
        ENC["<b>Encapsulation</b><br/>src/dst IP<br/>src/dst MAC<br/>UDP src/dst port"]
        DLV["<b>Delivery</b><br/>collector-facing port<br/>(MONITOR_PORT)"]
    end
    ORCH ==>|"binds session"| PORT["Sampled port<br/>SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION"]
    PORT ==> WIRE(["Silicon emits sFlow v5 UDP<br/>datagrams to the collector"])
```

Creation order:

1. Resolve the collector against `NeighOrch` and `RouteOrch` to
   obtain the collector-facing port, next-hop MAC and source MAC.
2. `create_mirror_session()`: `TYPE = SAI_MIRROR_SESSION_TYPE_SFLOW`, the
   collector-facing port as `MONITOR_PORT`, source and destination IP and MAC,
   UDP source and destination port (6343 by default, from `SFLOW_COLLECTOR`),
   the configured 1-in-N `SAMPLE_RATE` and `TRUNCATE_SIZE`.
3. `set_port_attribute(port, SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION,
   [session])` for every port whose `SFLOW_SESSION` row is enabled. Passing an
   empty list unbinds the port.

Teardown reverses that order: unbind every port, then remove the session. Two
consequences for `SflowOrch` bookkeeping:

- SAI puts the sample rate on the session, but SONiC configures it per port.
  Ports that share a collector and a rate share one session; a port with a
  different rate needs its own session.
- SAI binds sessions to physical ports only. Enabling sFlow on a PortChannel
  binds every member port, and a membership change rebinds.

Optionally, `MONITOR_PORT` can be set to a recirc port instead of a
front-panel port. The datagram then takes a second pass through the pipeline
and the FIB forwards it to the collector, so delivery follows route changes.

#### 7.2 Collector resolution

`HwSflow` resolves each collector address against `NeighOrch` and `RouteOrch`
and re-resolves on any route or neighbor change. The result — collector-facing
port, next-hop MAC, source MAC — is applied to the live session with
`set_mirror_session_attribute()`; nothing is recreated. The encapsulation
source IP is the address of the interface named by `SFLOW|global:agent_id`,
which is also the Agent Address carried in every emitted datagram.

A sample-rate change is also an attribute set, but a vendor SAI may implement
it with a brief sampling pause and a datagram sequence-number reset, so
`HwSflow` coalesces bursts of changes (about 100 ms) into one reprogram.

#### 7.3 Serviceability and debug

- `STATE_DB:SFLOW_COLLECTOR_STATE|<name>`: resolved encapsulation, last error
  and last update time.
- `show sflow` reports the selected mode and the above. Syslog records mode
  transitions at INFO, and a rejected mode selection or a resolution failure at
  WARN.

### 8. SAI API

No new SAI API is required. Every object and attribute used here exists in
SAI today: `SAI_MIRROR_SESSION_TYPE_SFLOW` and the sFlow-conditional
`UDP_SRC_PORT`/`UDP_DST_PORT` attributes are defined in
[`inc/saimirror.h`](https://github.com/opencomputeproject/SAI/blob/master/inc/saimirror.h),
and the per-port binding attribute
`SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION` in
[`inc/saiport.h`](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h).

### 9. Configuration and management

#### 9.1 Manifest

Not applicable. This is a built-in feature, not an Application Extension.

#### 9.2 CLI and YANG model enhancements

One new command selects the datapath; every existing sFlow command is unchanged.

```text
config sflow mode <cpu-path|hw-accelerated>
```

`show sflow` gains the selected mode, and per collector the resolved
encapsulation. Existing fields and layout are unchanged:

```text
sFlow Global Information:
  sFlow Admin State:          up
  sFlow Sample Direction:     rx
  sFlow Polling Interval:     default
  sFlow AgentID:              Loopback0
  sFlow Sampling Mode:        hw-accelerated
  sFlow Sampling Status:      operational

  1 Collectors configured:
    Name: collector0          IP addr: 10.0.0.1       UDP port: 6343   VRF: default
      Programmed: true        Dst MAC: 0c:42:a1:5e:3b:07   Src IP: 10.1.0.32   Egress: Ethernet48
```

On a platform that cannot support the configured mode:

```text
  sFlow Sampling Mode:        hw-accelerated
  sFlow Sampling Status:      non-operational (platform not capable)
```

`sonic-sflow.yang`:

```yang
leaf mode {
    type enumeration {
        enum cpu-path;
        enum hw-accelerated;
    }
    default "cpu-path";
    description "Where sFlow datagrams are built. 'cpu-path' builds them
                 in hsflowd in userspace; 'hw-accelerated' builds them
                 in the ASIC.";
}
```

#### 9.3 Config DB enhancements

`CONFIG_DB:SFLOW` gains `mode`:

```json
"SFLOW": {
    "global": {
        "admin_state": "up",
        "agent_id": "Loopback0",
        "sample_direction": "rx",
        "mode": "hw-accelerated"
    }
}
```

`STATE_DB:SWITCH_CAPABILITY` gains one bit, sourced from
`sai_query_attribute_enum_values_capability()` on
`SAI_MIRROR_SESSION_ATTR_TYPE` (the platform is capable when the returned list
contains `SAI_MIRROR_SESSION_TYPE_SFLOW`):

```json
"SWITCH_CAPABILITY|switch": {
    "HW_SFLOW_CAPABLE": "true"
}
```

Two new STATE_DB tables, written by `SflowOrch`:

```text
key           = SFLOW_COLLECTOR_STATE|<collector_name>
programmed    = "true" / "false"
resolved_dst_mac, resolved_src_mac, resolved_src_ip, egress_port
last_error    = string
last_updated  = timestamp
```

```text
key          = SFLOW_STATE|global
operational  = "true" / "false"
reason       = string (empty when operational)
```

Configuration without `mode` behaves as `cpu-path`, so nothing is migrated and
an upgrade does not change an existing deployment's datapath.
`SFLOW_COLLECTOR_STATE` exists only while the hardware path is active.

### 10. Warmboot and Fastboot Design Impact

HW sFlow packet sampling should not be affected after a warm reboot.

### 11. Memory Consumption

One mirror session per (collector, sample rate) pair, plus port-to-session
bookkeeping in `SflowOrch` and one STATE_DB row per collector. Nothing is
allocated while `mode` is `cpu-path`.

### 12. Restrictions/Limitations

1. A sample-rate change may pause sampling briefly and reset the datagram
   sequence number, depending on the vendor SAI, so collectors must tolerate
   resets. Bursts coalesce into one reprogram.
2. PortChannel support binds each member port, since
   `SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION` is a port attribute with no
   LAG-level equivalent.
3. Ports configured `sample_direction tx` or `both` are not programmed on the
   hardware path and are logged at WARN.

### 13. Testing Requirements/Design

#### 13.1 Unit test cases

| # | Test |
| :---- | :---- |
| 1 | `HW_SFLOW_CAPABLE` is published from the SAI capability query |
| 2 | Default `mode=cpu-path` uses the CPU path and creates no mirror session |
| 3 | `mode=hw-accelerated` on a capable platform creates the mirror session with expected attributes and binds it to enabled ports |
| 4 | `mode=hw-accelerated` on an incapable platform: config is retained, flow sampling stops (no CPU fallback), `SFLOW_STATE|global` reports non-operational with a reason, and a WARN is logged |
| 5 | A neighbor or route change re-resolves and updates the session in place; a burst collapses into one reprogram |
| 6 | Two ports at the same sample rate share one session; different rates get distinct sessions |
| 7 | Bindings are removed on session delete; a mode change tears down one path before standing up the other |

#### 13.2 System test cases

`test_sflow.py` already exists in sonic-mgmt and we will modify that test-case to
also evaluate HW sFlow on supported platforms.

We will evaluate:
- End to end: with `mode=hw-accelerated`, a collector receives and decodes sFlow v5 datagrams
- IPv4/6 collectors function properly
- Nexthop-flap reprograms the encapsulation and sampling resumes
- PortChannel ingress is sampled across LAG members
- Counter samples arrive while hardware path is active
- Warmboot continues sampling on unchanged

### 14. Open/Action items - if any

- SAI has no LAG-level equivalent of
  `SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION`, so PortChannel support binds
  each member port. A SAI enhancement request to add one is worth
  raising.
