# SONiC-VPP Packet Trimming HLD

## Table of Contents

1. [Revisions](#1-revisions)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [Background](#4-background)
5. [Requirements](#5-requirements)
6. [Architecture](#6-architecture)
7. [High-Level Design](#7-high-level-design)
8. [SAI API Mapping](#8-sai-api-mapping)
9. [Configuration and Management](#9-configuration-and-management)
10. [Warmboot and Fastboot](#10-warmboot-and-fastboot)
11. [Memory and Performance](#11-memory-and-performance)
12. [Error Handling](#12-error-handling)
13. [Limitations and Future Work](#13-limitations-and-future-work)
14. [Testing](#14-testing)
15. [Open Items](#15-open-items)
16. [References](#16-references)

## 1. Revisions

| Rev | Date | Author(s) | Changes |
|---|---|---|---|
| v1.0 | 2026-07-31 | Aaron Bernardino | Initial SONiC-VPP packet-trimming design |

## 2. Scope

This document describes how SONiC-VPP relates to the existing
[SONiC Packet Trimming](../packet_trimming/packet-trimming-design.md) design,
and defines the dataplane architecture implementing it on VPP.

**Increment scope (this change).** A Gate 0 feasibility spike on the live VPP
KVM testbed (see [4. Background](#4-background)) established that the VPP
dataplane has no native egress QoS / queue-admission model, so a blocking SONiC
scheduler cannot by itself produce the admission failure that packet trimming
hangs off. Rather than defer the datapath, this increment **supplies the missing
substrate in software**: the `sonic_ext` VPP plugin gains a generic
per-`{egress port, queue}` token-bucket admission shim on the
`interface-output` feature arc, plus a trim action node that truncates the
rejected packet, rewrites its DSCP, and retries it on the configured static trim
queue. The binary API accepts generic rate and capacity values, while the
delivered SAI-VPP translation intentionally programs only the two states needed
by the supported topology: an unlimited bucket for a queue with no effective
rate limit and an empty, non-refilling bucket for a queue with any nonzero
scheduler `PIR`. Buffer profiles determine trim eligibility; their size is not
used as bucket depth in this increment. For the symmetric core that is complete
and validated end to end, SAI-VPP advertises the capability truthfully as
**supported**
(`SWITCH_TRIMMING_CAPABLE=true`), at which point the `sonic-mgmt` symmetric suite
runs.

The capability stays honest by narrowing *what* is advertised rather than gating
the switch capability off: SAI-VPP advertises only the enum values the datapath
honors (`DSCP_VALUE` DSCP resolution, `STATIC` queue resolution), so orchagent
never programs the asymmetric `FROM_TC` or `DYNAMIC` modes VPP does not implement.
Cases that exercise unimplemented behavior are deferred in `sonic-mgmt` through
conditional_mark skips keyed on `asic_type == vpp`. The shared `sonic-sairedis`
virtual-switch base over-advertises every trim enum today; that enum
over-advertisement is corrected on VPP (see
[7.12](#712-capability-advertisement)).

The delivered increment covers:

- Translating the symmetric packet-trimming switch attributes into VPP state.
- Selecting eligibility from the buffer profile attached to the original queue.
- Classifying the original queue through a switch-wide DSCP-to-queue table.
- Producing a recoverable admission failure from the scheduler's binary
  blocked/unlimited state.
- Truncating eligible IPv4 and IPv6 packets and writing the configured symmetric
  DSCP value.
- Sending the shortened packet through a configured static trim queue on the
  selected physical egress member.

The full target design additionally includes asymmetric `FROM_TC`, dynamic
trim-queue resolution, ACL `DISABLE_TRIM`, SAI switch/port/queue counter
sourcing, and validated replay/persistence behavior. Those items are deferred
as listed in [13.1](#131-integration-status).

This document is a VPP platform adaptation. It does not redefine the existing
SONiC CLI, Config DB schema, YANG model, orchestration, or SAI contract.

The design does not support dynamic trim-queue resolution. That mode requires the
complete DSCP-to-TC-to-queue pipeline to select the trim queue after DSCP
remapping and is left for future work. The shared `sonic-sairedis` virtual-switch
base currently advertises the dynamic mode as supported; VPP advertises only the
`STATIC` mode it honors and omits `DYNAMIC` from the enum (see
[7.12](#712-capability-advertisement)).

## 3. Definitions

| Term | Meaning |
|---|---|
| Admission failure | The selected egress queue's admission provider rejects the packet. In the delivered VPP mapping this means the queue is trim-eligible and has a nonzero scheduler `PIR`, which is represented by an empty, non-refilling bucket |
| Original queue | The egress queue selected for the unmodified packet |
| Trim queue | The egress queue selected for the shortened packet |
| Trim attempt | An eligible original packet reaches the packet-trimming path after original-queue admission fails |
| Trimmed packet | A packet processed by the trim path, whether or not its original length exceeded the configured trim size |
| Admission provider | The VPP feature node that evaluates the programmed per-queue token-bucket state and diverts rejected buffers to packet-trimming policy |
| DSCP | Differentiated Services Code Point |
| TC | Traffic Class |
| LAG | Link Aggregation Group, represented by a VPP BondEthernet interface |
| SAI-VPP | The `sonic-sairedis` virtual switch implementation that translates SAI objects to VPP |
| VPP plugin | The SONiC-local VPP packet-trimming plugin and binary API |

## 4. Background

Packet trimming lets a receiver learn about congestion sooner than it would
after a complete packet drop and retransmission timeout. When admission to a
trim-eligible lossy queue fails, the switch:

1. Keeps at most the configured number of bytes.
2. Assigns a configured DSCP, or resolves DSCP from a configured trim TC.
3. Tries to transmit the shortened packet through a high-priority trim queue.

SONiC already provides the platform-independent control-plane implementation:

```text
CLI / Config DB
    |
    v
switchorch + bufferorch + qosorch + aclorch
    |
    v
SAI switch / buffer profile / QoS / ACL objects
    |
    v
syncd
    |
    v
platform SAI
```

The **pre-change SAI-VPP baseline** is important to state precisely, because the
control-plane capability already existed before this increment:

- The shared `sonic-sairedis` virtual-switch base already advertises full
  packet-trimming capability. It reports the switch, buffer-profile, and stats
  enum capabilities (DSCP `DSCP_VALUE`/`FROM_TC`, queue `STATIC`/`DYNAMIC`,
  buffer action `DROP`/`DROP_AND_TRIM`, and the switch/port/queue trim stats),
  and `SwitchVpp::queryAttributeCapability` reports every attribute as
  create/set/get implemented.
- As a result, `sonic-swss` already computed
  `isSwitchTrimmingSupported() == true` and published
  `SWITCH_CAPABILITY|switch:SWITCH_TRIMMING_CAPABLE=true` on VPP. The
  configuration path was functional at the virtual-object layer: switch,
  buffer-profile, QoS, and ACL objects were accepted and stored.
- What was missing was entirely below SAI: VPP performed no trimming, and the
  trim statistics read back as zero because the base returned no values for
  them.

VPP also has no native equivalent of
`SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM`.

Because capability was already advertised while the datapath did nothing, the
pre-change platform reported support it did not provide. A Gate 0 feasibility
spike on the live `vms-kvm-vpp-t1-lag` testbed confirmed *why* and established
the implementation direction:

- **Forwarding path (measured).** Front-panel transit egresses through
  `BondEthernetXXX` (mode `xor`, load-balance `l34-inner`) onto member
  interfaces that are **DPDK virtio** ports (`Red Hat Virtio`, one TX queue,
  4096 descriptors). SONiC `EthernetX` ports are VPP **Linux Control Plane
  (LCP) TAP** interfaces paired to those members. (An AF_PACKET
  `host-interface` backend exists in `vpp_init.sh` only for veth-based ports;
  this testbed presents virtio PCI, so it takes the DPDK path.)
- **No QoS / admission substrate (measured).** The running VPP graph has no
  policer (the CLI is not even compiled in), no scheduler, shaper, HQoS, or
  per-queue admission node, no per-queue buffer accounting, and no
  congestion/tail-drop counter in the transit path. There is no native
  equivalent of `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM`.
- **The SONiC scheduler is a dataplane no-op.** SAI-VPP stores the
  `SAI_SCHEDULER_GROUP` / `SAI_QUEUE` object model so orchagent is satisfied,
  but programs no VPP rate/shaper. The packet-trimming test creates congestion
  by binding a `PIR=1` blocking scheduler to a queue; on VPP that scheduler
  changes no dataplane state, so the "blocked" queue keeps forwarding at line
  rate. Without congestion there is no admission failure, so a trim action
  would never fire.

Consequently, real trimming on VPP first requires an egress per-queue admission
model that reacts to the SONiC scheduler state, so that a blocked queue can
produce a *cannot-admit* result. Rather than treat that as a separate
prerequisite, this design **provides it in software**: a generic
per-`{port, queue}` token-bucket admission shim on the `interface-output` arc
(see [7.1](#71-admission-provider)). The delivered SAI-VPP mapping represents
the test's nonzero `PIR` blocking scheduler with a zero-rate, zero-capacity
bucket, yielding a real, recoverable admission failure; a queue without a rate
limit receives an always-admitting bucket. The trim action node
([7.4](#74-truncation-and-header-handling)–[7.6](#76-static-trim-queue-and-retry))
hangs off that failure. Because the shim is generic — it carries no
packet-trimming SAI policy or test constants — it is the minimal substrate
needed and keeps the SONiC-specific logic in SAI-VPP and the plugin control path.

The SAI-VPP translation that drives this datapath is completed and validated for
the symmetric core, so the platform advertises packet trimming as *supported*
(`SWITCH_TRIMMING_CAPABLE=true`). To keep the advertisement honest, VPP corrects
the base's enum over-advertisement — narrowing the advertised trim enum values to
the modes the datapath honors (`DSCP_VALUE`, `STATIC`) so orchagent never
programs an unimplemented mode — rather than gating the switch capability off
(see [7.12](#712-capability-advertisement)).

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Increment status |
|---|---|---|
| REQ-1 | VPP must trim only after admission to the original queue fails | Delivered |
| REQ-2 | Trimming eligibility must follow the buffer profile attached to the original queue | Delivered |
| REQ-3 | `DROP` must retain normal drop behavior; `DROP_AND_TRIM` must invoke trim policy | Delivered |
| REQ-4 | The trim size must be runtime configurable | Delivered |
| REQ-5 | Symmetric mode must write the configured DSCP value | Delivered |
| REQ-6 | Asymmetric mode must resolve DSCP from the configured trim TC and the selected egress port's TC-to-DSCP map | Deferred |
| REQ-7 | The initial implementation must transmit through the configured static trim queue | Delivered |
| REQ-8 | ACL `DISABLE_TRIM` must suppress trimming for matching packets | Deferred |
| REQ-9 | A packet must enter the trim path no more than once | Delivered |
| REQ-10 | Trim attempts, successful trim transmissions, and trim-queue drops must be counted at the required SAI scopes | Plugin summary counters delivered; SAI scope attribution deferred |
| REQ-11 | LAG traffic must remain associated with the physical member selected before original-queue admission | Delivered |
| REQ-12 | A failed runtime VPP update must be surfaced so orchagent can retry the idempotent full policy and converge SAI and VPP state | Delivered for set; create refresh is best effort |

### 5.2 Non-Functional Requirements

- No per-packet heap allocation is allowed in the dataplane path.
- Packet trimming must be inactive when no eligible buffer profile is bound.
- Existing forwarding behavior must remain unchanged while the feature is
  disabled.
- The admission integration point must be generic and must not contain SONiC
  SAI policy.
- The design must not depend on scheduler names, a particular configured rate,
  or constants from the packet-trimming test suite.
- Capability advertisement must reflect only functionality that is initialized
  and usable at runtime.

### 5.3 Non-Goals

- Changes to the generic packet-trimming Config DB schema or CLI.
- A new SONiC application extension.
- Full hardware-MMU emulation in VPP.
- Dynamic trim-queue resolution in the initial implementation.
- Recalculation of IP or transport length and checksum fields after truncation.
- Replacing VPP's existing forwarding, LAG hashing, QoS, or ACL architecture.

## 6. Architecture

> **Scope note.** Sections [6](#6-architecture)–[9](#9-configuration-and-management)
> describe both the full target architecture and the delivered symmetric core.
> Status labels in the detailed sections are authoritative. The delivered path
> is the software admission shim, symmetric DSCP rewrite, static trim queue,
> binary API/CLI, and SAI-VPP programming validated end to end. Deferred behavior
> is summarized in [13](#13-limitations-and-future-work).

### 6.1 Control-Plane Flow

```mermaid
flowchart TD
    A[Config DB packet-trimming configuration] --> B[SONiC orchagent]
    B --> C[SAI switch, buffer, QoS, ACL objects]
    C --> D[syncd]
    D --> E[SAI-VPP]
    E --> F[VPP packet-trim binary API]
    F --> G[Packet-trim plugin policy]
    E --> H[Egress admission provider configuration]
    E --> I[Capability mapping; SAI counter sourcing deferred]
```

SAI-VPP owns object relationships and translates the platform-independent SAI
contract into compact VPP policy:

- Global trim size, symmetric DSCP value, and static trim queue. The DSCP mode
  and TC value are stored, but `FROM_TC` is not honored in this increment.
- Effective eligibility for each `{egress port, original queue}` pair.
- A switch-wide DSCP-to-queue table composed from the first front-panel port
  that has both `DSCP_TO_TC` and `TC_TO_QUEUE` maps.
- Binary blocked/unlimited admission state derived from the effective scheduler.

ACL trim-disable programming, per-port TC-to-DSCP resolution, and SAI trim
counter sourcing are deferred.

### 6.2 Dataplane Flow

```mermaid
flowchart TD
    A[Packet reaches final egress classification] --> B[Resolve physical egress and original queue]
    B --> C{Original queue admits packet?}
    C -->|Yes| D[Transmit original packet]
    C -->|No| E{Eligible and not ACL disabled?}
    E -->|No| F[Normal original-packet drop]
    E -->|Yes| G[Increment trim-attempt counters on original queue and port]
    G --> H[Truncate to configured size when needed]
    H --> I[Apply symmetric or asymmetric DSCP]
    I --> J[Select configured static trim queue on same physical egress]
    J --> K{Trim queue admits packet?}
    K -->|Yes| L[Transmit and increment trim-sent counters]
    K -->|No| M[Drop and increment trim-drop counters]
```

This flowchart is the full conceptual design. In the delivered increment the
"ACL disabled" branch and the asymmetric-DSCP step are deferred: the datapath
applies symmetric `DSCP_VALUE` only and does not yet honor an ACL trim-disable
flag ([7.5](#75-dscp-resolution), [7.9](#79-acl-disable-trim),
[13.1](#131-integration-status)). The delivered counters are switch-global
plugin summaries; the port/queue increments shown are target SAI attribution
([7.11](#711-counters)).

### 6.3 Component Responsibilities

| Component | Responsibility |
|---|---|
| VPP admission integration | Software per-`{port, queue}` token-bucket admission shim on the `interface-output` arc that turns a rate-limited (blocked) queue into a recoverable admission failure; generic, carrying no packet-trimming SAI policy |
| VPP packet-trim plugin | Eligibility lookup, truncation, DSCP rewrite, static trim-queue retry with one-shot `interface-output-arc-end` re-injection, counters, binary API, and debug CLI |
| SAI-VPP | Translate the delivered symmetric policy onto the plugin: global size/DSCP/static queue, per-queue eligibility from the buffer profile, binary blocked/unlimited state from the scheduler, and a switch-wide DSCP-to-queue table. Advertise only `DSCP_VALUE` and `STATIC`, while leaving SAI trim-counter sourcing and the asymmetric/ACL modes deferred |
| sonic-swss | No VPP-specific change expected; the generic packet-trimming orchestration and capability publication already function on VPP |
| sonic-mgmt | Make the test setup self-sufficient on the minimal VPP config, clean up test-created buffer bindings/profiles, exempt VPP from the hardware-SKU gate, and skip deferred files/cases on `asic_type == vpp` ([14.2](#142-system-tests), [14.3](#143-enablement-gating)) |

## 7. High-Level Design

### 7.1 Admission Provider

Packet trimming needs a point where an egress packet can be *recoverably*
rejected — rejected while VPP still owns the buffer, so the trim action can run
instead of the packet being freed. VPP has no such point natively, so the plugin
provides one as a software admission shim.

**`sonic-ext-trim-admission`** is a feature node on the `interface-output` arc,
enabled per egress `sw_if_index` whenever that port has at least one
trim-eligible queue. For each packet it resolves the egress `{port, queue}` — the
queue from the packet DSCP via the SAI-pushed DSCP-to-queue table — and runs that
queue's software token bucket:

| Result | Meaning | Action |
|---|---|---|
| Non-eligible / unconfigured queue | not policed | pass straight through the arc (normal traffic is never perturbed) |
| Eligible queue, bucket admits | within rate | continue the arc (normal egress) |
| Eligible queue, bucket rejects | recoverable admission failure | divert to the trim action node ([7.4](#74-truncation-and-header-handling)) |

The plugin API and token-bucket implementation accept generic rate/capacity
inputs. The delivered SAI-VPP translation deliberately binarizes them: a queue
with no effective rate limit receives `UINT64_MAX` rate and capacity (always
admit), while any nonzero scheduler `PIR` — including the
`SCHEDULER_BLOCK_DATA_PLANE` profile's `PIR=1` — receives zero rate and capacity
(always reject). The attached buffer profile controls only whether the queue is
trim-eligible; its size does not set the bucket depth in this increment. The
plugin recognizes no scheduler names or test constants, and non-eligible queues
are never policed.

Because the shim is a normal feature-arc node, no VPP core change is required for
the KVM DPDK-virtio backend. Backends that cannot be policed on the
`interface-output` arc (for example the AF_PACKET `host-interface` path) would
reuse the same generic node at their own pre-transmit point.

### 7.2 Packet-Trim Policy State

The VPP plugin maintains:

- One global packet-trimming configuration.
- One eligibility record per effective egress-port/original-queue binding.
- One switch-wide DSCP-to-queue table used for original-queue classification.
- Three switch-global summary counters: admission failures, trimmed packets
  sent, and trimmed packets dropped.

Per-port TC-to-DSCP state for `FROM_TC` and per-port/per-queue counter
attribution are target behavior, not delivered state.

The global configuration contains:

| Field | Meaning |
|---|---|
| `trim_size` | Maximum number of bytes retained |
| `dscp_mode` | Stored DSCP mode; only direct `DSCP_VALUE` is honored |
| `dscp_value` | Symmetric DSCP value |
| `trim_tc` | Stored TC for the deferred asymmetric egress-map lookup |
| `trim_queue` | Queue index used for the shortened packet |

An eligibility record is active only when the queue's effective buffer profile
uses `DROP_AND_TRIM`.

### 7.3 Original-Queue Admission Failure

On a recoverable admission failure, the admission node has resolved:

- The buffer index.
- The final physical egress `sw_if_index` (`VLIB_TX`).
- The original queue index (stamped into the buffer for the trim node).
- That the queue is trim-eligible.

The plugin diverts the packet to the trim action node only when the global
configuration is valid and the original queue is trim-eligible; otherwise the
packet stays on the normal arc (admitted) or follows the existing drop path.
Re-entry is prevented **structurally** rather than with a per-buffer flag: the
trimmed packet is re-injected at `interface-output-arc-end`, past the admission
feature, so it can never re-enter admission and be trimmed twice (see
[7.6](#76-static-trim-queue-and-retry)). This avoids depending on `opaque2` being
cleared on buffer recycle, which VPP does not guarantee.

The target ACL-driven trim-suppression path would add a per-buffer flag to this
decision. It is not present in the delivered node
([7.9](#79-acl-disable-trim)).

### 7.4 Truncation and Header Handling

When a packet is longer than `trim_size`, VPP shortens the buffer chain to at
most `trim_size` bytes, freeing any tail buffers in a chained packet. When a
packet is shorter than or equal to `trim_size`, it is sent at its original
length. In both cases the packet is processed by the trim path and receives the
configured DSCP behavior.

**Multi-segment (jumbo) buffers.** On the KVM/DPDK backend, jumbo frames arrive
scatter-gathered into a chain of VLIB buffers, each backed by a DPDK `rte_mbuf`
(the `interface-output` arc runs with `VLIB_BUFFER_EXT_HDR_VALID` set on RX
buffers). Truncating the chain clears the VLIB `VLIB_BUFFER_NEXT_PRESENT` flag
and frees the tail buffers, but that alone does **not** update the backing
`rte_mbuf`: it still carries the RX-time `nb_segs` and a `->next` pointer to the
now-freed tail segment. `dpdk_validate_rte_mbuf()` only rebuilds the mbuf header
(via `rte_pktmbuf_reset()`, which sets `next = NULL` and `nb_segs = 1`) when
`EXT_HDR_VALID` is clear, and the virtio PMD TX path walks `mb->next` until NULL
rather than trusting `nb_segs`. Without intervention the freed tail therefore
rides onto the wire — a 5000-byte frame trimmed to 256 was observed egressing as
256 + 952 = 1208 bytes. The trim path fixes this by clearing
`VLIB_BUFFER_EXT_HDR_VALID` on the severed segment, forcing the mbuf header to be
rebuilt cleanly so only the retained bytes are transmitted. This case is covered
end to end by `test_packet_size_after_trimming` (jumbo 5000 → 4084 and a second
multi-segment case, 3000 → 256).

The trim path deliberately preserves the original L3/L4 length fields as the
congestion signal — it does **not** recalculate:

- IPv4 total length (the header still reports the pre-trim length).
- IPv6 payload length.
- TCP or UDP length and checksum fields.

The one field that *is* updated is the **IPv4 header checksum**, and only because
the DSCP rewrite ([7.5](#75-dscp-resolution)) changes the ToS byte: the checksum
is recomputed over the 20-byte header so the header stays valid after the DSCP
change, while the (deliberately unmodified) total-length field is unaffected. The
IPv4 header checksum covers only the header, so leaving the truncated payload out
does not invalidate it; IPv6 carries no header checksum. This matches the
existing SONiC packet-trimming validation contract, which inspects the preserved
length fields together with the rewritten DSCP.

### 7.5 DSCP Resolution

For IPv4, VPP rewrites the six DSCP bits in the Type of Service field while
preserving ECN bits. For IPv6, VPP rewrites the DSCP portion of Traffic Class
while preserving ECN bits.

| Mode | Resolution |
|---|---|
| `DSCP_VALUE` | Use the global configured `dscp_value` |
| `FROM_TC` (deferred) | Use `trim_tc` to look up DSCP in the TC-to-DSCP map attached to the selected egress port |

The delivered datapath implements **only** the symmetric `DSCP_VALUE` mode and
always rewrites with the global `dscp_value`; asymmetric `FROM_TC` is deferred
and omitted from the advertised DSCP-resolution enum
([7.12](#712-capability-advertisement), [13.1](#131-integration-status)), so
orchagent never programs it. The `FROM_TC` behavior below is the target design
for a future increment: if asymmetric mode has no usable egress map entry, the
trim operation fails, the packet is dropped, and a configuration/runtime error
counter is incremented. SAI-VPP should reject configurations that are invalid at
programming time.

### 7.6 Static Trim Queue and Retry

The initial implementation uses
`SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_STATIC`.

The trim action node:

1. Rewrites the packet DSCP ([7.5](#75-dscp-resolution)) and truncates it
   ([7.4](#74-truncation-and-header-handling)).
2. Steers the shortened packet to the configured static `trim_queue` on the **same** physical
   egress interface (`VLIB_TX` is unchanged) and runs that queue's token bucket.
3. If the trim queue admits, transmits the packet by enqueuing it directly to
   `interface-output-arc-end` — the node the `interface-output` feature arc
   terminates at — so it goes straight to the port TX, *past* the admission
   feature. If the trim queue rejects (it is itself congested), the packet is
   dropped.

Enqueuing the transmitted packet to the arc end is what makes the one-shot
guarantee **structural**: a trimmed packet never re-enters the admission feature,
so it can never be trimmed a second time and no per-buffer "already trimmed" flag
is needed. This is deliberately more robust than a buffer flag, because VPP does
not zero `opaque2` on buffer recycle, so a flag could survive into an unrelated
future packet and wrongly suppress its trimming.

### 7.7 Physical Ports and LAGs

For a physical-port egress, the trim retry uses the same physical interface.

For a LAG egress, VPP bond selection occurs before queue admission. The
admission provider records the selected physical member. The trim retry uses
that member directly instead of re-entering bond hashing, which:

- Keeps the original and trimmed packet on one physical port; future
  per-port/per-queue counter sourcing can therefore use that member.
- Avoids moving a congestion notification to a different LAG member.
- Prevents a second flow-hash decision from changing packet ordering.

The delivered plugin records the selected physical `VLIB_TX` member. SAI
port/queue trim counters are not sourced yet; the target attribution is the
physical member and its queues.

### 7.8 Buffer Profile and Queue Relationships

SAI-VPP tracks the object chain from a queue to its attached buffer profile.
Whenever the queue binding or
`SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` changes, SAI-VPP
recomputes and programs effective eligibility.

Because sonic-vpp creates front-panel ports dynamically as orchagent brings the
switch up — not at switch-create time — SAI-VPP enumerates the ports to program
from the live SAI port-object store on each recompute, rather than from a port
list captured at initialization. A recompute therefore always covers every
front-panel port that currently exists, including ports created after the first
trim-relevant attribute was observed, and a late buffer-profile binding is picked
up by the next recompute rather than being missed.

On a trim-relevant set, SAI-VPP first commits the virtual object attribute, then
rebuilds and pushes the complete eligibility state. A push failure is returned
to orchagent for retry; the committed attribute is retained. On create, the
object is committed and the trim refresh is best effort. Normal orchagent remove
sequencing first unbinds a profile or scheduler through a set (which refreshes
eligibility), then removes the now-unreferenced object; direct object removal
does not itself trigger a trim refresh ([7.13](#713-update-and-remove-ordering)).

### 7.9 ACL Disable Trim

> **Status: deferred (target design).** The ACL trim-disable path is not
> implemented in this increment; SAI-VPP accepts and stores the ACL objects as
> virtual state but does not yet program a per-buffer trim-disable flag into the
> VPP datapath. The `sonic-mgmt` `test_acl_action_with_trimming` case is skipped
> on `vpp` ([14.3](#143-enablement-gating)). The design below is the target for a
> future increment ([13.1](#131-integration-status)).

SAI-VPP extends the existing VPP ACL translation for
`SAI_ACL_ENTRY_ATTR_ACTION_PACKET_TRIM_DISABLE`.

A matching ACL rule sets a per-buffer `trim_disabled` flag. The flag is metadata
only and does not change the packet action by itself. If original-queue admission
later fails, trim policy observes the flag and follows normal drop behavior.

The target implementation must use the same explicit failure propagation and
retry/convergence model as other trim-relevant updates.

### 7.10 Scheduler and Capacity Inputs

The plugin admission API supports a byte rate and byte capacity, but the
delivered SAI-VPP translation does not model proportional scheduling or derive a
capacity from the buffer profile. It resolves the queue's effective scheduler
(direct queue binding first, then the parent leaf scheduler group used by
QosOrch) and programs one of two states:

| Effective scheduler | Programmed rate | Programmed capacity | Behavior |
|---|---:|---:|---|
| No scheduler or `MAX_BANDWIDTH_RATE=0` | `UINT64_MAX` | `UINT64_MAX` | Always admit |
| Any nonzero `MAX_BANDWIDTH_RATE` | `0` | `0` | Always reject when trim-eligible |

The buffer profile contributes only
`PACKET_ADMISSION_FAIL_ACTION=DROP_AND_TRIM` eligibility. Modeling a
proportional sub-line-rate `PIR`, actual queue occupancy, or buffer-profile
capacity as token-bucket depth is future work.

Full SAI scheduler hierarchy, shared-buffer accounting across ports, headroom,
and hardware-specific threshold behavior remain outside this design.

### 7.11 Counters

The VPP plugin currently maintains three switch-global summary counters and
exposes them through `sonic_ext_trim_counters_get` and `show sonic-ext trim`:

- `trim_admit_fail` — eligible original-queue admission failures.
- `trim_sent` — shortened packets transmitted.
- `trim_drop` — shortened packets rejected by the trim queue.

The **target** design adds the per-port/per-queue accounting needed to map these
events onto the existing SAI statistics and serve them from `getStatsExt`:

| Event | Counter attribution |
|---|---|
| Eligible original-queue admission failure | `TRIM_PACKETS` on the original queue and physical egress port |
| Trim packet transmitted | `TX_TRIM_PACKETS` on the switch, physical egress port, and trim queue |
| Trim-queue admission failure | `DROPPED_TRIM_PACKETS` on the switch, physical egress port, and trim queue |

Counter reads must be monotonic and safe while workers update them, and a clear
operation resets only the requested scope and statistics.

The target queue-index attribution must match the `sonic-mgmt` counter
assertions: the suite verifies that the switch-level trim-sent counter equals the
sum of the per-port counters and that each port's counter is consistent with its
per-queue counters, and the feature-toggle test reads the queue-level
`trimpacket` counter on the *trim* queue index (`UC` + configured trim queue).

**Delivered scope (initial enablement).** The global plugin summaries are
available through the binary API/CLI, but SAI-VPP does **not** source them
through `getStatsExt`, and the plugin does not yet maintain the per-port and
per-queue breakdown required by the SAI contract. `SwitchVpp::getStatsExt`
delegates trim stat IDs to the shared virtual-switch base, which returns zero.
SAI stat sourcing and scoped accounting are deferred, and the `sonic-mgmt`
trim-counter cases are skipped on `vpp`.

### 7.12 Capability Advertisement

Packet-trimming capability on VPP must track the datapath: `sonic-swss` must be
told which trim modes VPP can actually satisfy so orchagent never programs one it
cannot. The shared virtual-switch base advertises packet trimming on VPP:

- `SwitchStateBase::queryAttrEnumValuesCapability` returns the DSCP modes
  (`DSCP_VALUE`, `FROM_TC`), the queue modes (`STATIC`, `DYNAMIC`), and the
  buffer-profile action modes (`DROP`, `DROP_AND_TRIM`).
- `SwitchStateBase::queryStatsCapability` lists the switch, port, and queue trim
  stats as supported.
- `SwitchVpp::queryAttributeCapability` reports every switch trim attribute as
  create/set/get implemented.

Together these make `sonic-swss` publish `SWITCH_TRIMMING_CAPABLE=true`. The
initial enablement **keeps** trimming advertised as supported — the symmetric
datapath is wired and validated ([13.1](#131-integration-status)) — but narrows
the advertised *enum values* to exactly what the software admission shim honors:

| Seam | Delivered behavior |
|---|---|
| `SwitchVpp::queryAttributeCapability` | Inherits the base: the six `SAI_SWITCH_ATTR_PACKET_TRIM_*` attributes (size, DSCP mode, DSCP value, TC value, queue mode, queue index) stay create/set/get implemented, so `sonic-swss`'s `isSwitchTrimmingSupported()` follows the `set` capability and `SWITCH_TRIMMING_CAPABLE` is `true` |
| `SwitchVpp::queryAttrEnumValuesCapability` | Overrides the base to advertise a single value per trim enum — `DSCP_VALUE` for `SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_RESOLUTION_MODE` and `STATIC` for `SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_RESOLUTION_MODE` — so orchagent never programs the asymmetric `FROM_TC` or `DYNAMIC` modes VPP does not implement. `DROP`/`DROP_AND_TRIM` buffer-profile actions are left to the base metadata |

Because the capability stays `true`, the symmetric `packet_trimming` PTF suite
runs on sonic-vpp. Cases that exercise unimplemented behavior — asymmetric
per-port DSCP (`FROM_TC`), `DYNAMIC` queue resolution, ACL disable-trim, trim
counters, GCU config validation, feature/port toggles, port mirroring, SRv6, and
reload/reboot persistence — are deferred in `sonic-mgmt` through
conditional_mark skips keyed on `asic_type == vpp`
([14.3](#143-enablement-gating)), rather than by gating the switch capability to
`false`. This keeps the supported symmetric core enabled while excluding the
out-of-scope cases from the run.

The enum-advertisement decision is factored into a small pure predicate
(`SwitchVpp::getTrimEnumValuesCapability`) that the override calls, so it is
covered directly by a SAI-VPP unit test ([14.1](#141-unit-and-component-tests)).

### 7.13 Update and Remove Ordering

For set operations on a trim-relevant object, SAI-VPP:

1. Receives the metadata-validated SAI attribute and resolves available object
   references.
2. Commits the SAI virtual object state.
3. Rebuilds the affected VPP policy from the committed state (the global policy,
   or the full per-`{port, queue}` admission/eligibility set) and pushes it.
4. If the VPP push fails, returns the failure so orchagent retries the set. The
   committed SAI state is intentionally left in place; because each push is a
   full idempotent re-send, the retry re-pushes the same state and converges. The
   switch-global trim attributes program VPP first and then commit, but likewise
   surface a push failure to the caller.

For create operations, the SAI object is created unconditionally and a trim
re-program failure is **not** propagated (the object exists regardless); the
subsequent set path is where a dataplane push failure is reported.

For remove operations, the generic `remove_internal` path removes only the
virtual object state and does not invoke a trim refresh. Normal orchagent
sequencing must first unbind trim-relevant references through a set operation,
which refreshes the VPP policy, and then remove the unreferenced object.

## 8. SAI API Mapping

### 8.1 Switch Attributes

| SAI attribute | VPP mapping |
|---|---|
| `SAI_SWITCH_ATTR_PACKET_TRIM_SIZE` | Global `trim_size` |
| `SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_RESOLUTION_MODE` | Stored globally; only `DSCP_VALUE` is advertised and honored |
| `SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_VALUE` | Symmetric DSCP value |
| `SAI_SWITCH_ATTR_PACKET_TRIM_TC_VALUE` | Stored for the deferred asymmetric path; not used by the delivered trim node |
| `SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_RESOLUTION_MODE` | Accept `STATIC`; `DYNAMIC` is omitted from the advertised enum ([7.12](#712-capability-advertisement)) so orchagent never programs it. A stored `DYNAMIC` value is not honored by the datapath (an explicit set is accepted as a no-op) |
| `SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_INDEX` | Global static trim queue; the plugin stores the low three bits (`queue & 7`). The validated configuration uses queue 6 |

### 8.2 Buffer Profile and ACL

| SAI attribute/action | VPP mapping |
|---|---|
| `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION=DROP` | Disable trim eligibility for queues using the profile |
| `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION=DROP_AND_TRIM` | Enable trim eligibility for queues using the profile |
| `SAI_ACL_ENTRY_ATTR_ACTION_PACKET_TRIM_DISABLE` | **Deferred** — the ACL trim-disable path is not implemented in this increment ([7.9](#79-acl-disable-trim), [13.1](#131-integration-status)); the corresponding `sonic-mgmt` case is skipped on `vpp` |

### 8.3 Statistics

The trim statistics below are listed as supported by the shared virtual-switch
stats capability, so `sonic-swss` reads them. The VPP plugin maintains the
global summary counters in the dataplane and exposes them over its binary API
and debug CLI, but **SAI sourcing through `getStatsExt` is deferred**
([7.11](#711-counters),
[13.1](#131-integration-status)): trim stat IDs currently delegate to the shared
virtual-switch base, which returns zero, and the `sonic-mgmt` trim-counter cases
are skipped on `vpp` until real sourcing lands.

- `SAI_SWITCH_STAT_DROPPED_TRIM_PACKETS`
- `SAI_SWITCH_STAT_TX_TRIM_PACKETS`
- `SAI_PORT_STAT_TRIM_PACKETS`
- `SAI_PORT_STAT_DROPPED_TRIM_PACKETS`
- `SAI_PORT_STAT_TX_TRIM_PACKETS`
- `SAI_QUEUE_STAT_TRIM_PACKETS`
- `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS`
- `SAI_QUEUE_STAT_TX_TRIM_PACKETS`

No SAI API change is required.

## 9. Configuration and Management

This design introduces no new CLI, Config DB, APP DB, State DB, YANG, REST, or
gNMI schema. SONiC-VPP uses the configuration and capability fields defined by
the generic packet-trimming HLD.

The VPP plugin adds `show sonic-ext trim`, which reports:

- The current global trim configuration.
- Configured per-port/per-queue admission buckets, including eligibility,
  binary rate/capacity, and current tokens.
- The three global plugin counters (`sent`, `drop`, and `admit-fail`).

The CLI does not expose per-port TC-to-DSCP resolution or SAI-scoped counters in
this increment.

These commands are for serviceability and do not replace the standard SONiC CLI.

## 10. Warmboot and Fastboot

Reload, warmboot, and fastboot persistence are **not validated in this
increment**; `test_trimming_with_reload_and_reboot` is skipped on `vpp`.

The expected replay behavior is that switch attributes, queue/profile bindings,
scheduler bindings, and QoS maps trigger the same full-state programming used
at runtime. ACL trim-disable state is deferred and therefore is not rebuilt.
Plugin counters and token-bucket state are process-local and reset when VPP
restarts; no SAI counter persistence is provided. A packet in flight during a
restart may be dropped.

The implementation adds no sleeps or file I/O to the boot path. Broader
warmboot/fastboot behavior remains future validation work.

## 11. Memory and Performance

The per-port state is a vector indexed by VPP `sw_if_index`, with eight fixed
queue slots per entry, plus one switch-wide DSCP-to-queue table:

```text
O((maximum programmed sw_if_index + 1) * SONIC_EXT_TRIM_MAX_QUEUES + 64)
```

The per-buffer trim metadata currently stores only the resolved original queue
in existing VPP buffer opaque space. The target ACL trim-disable flag is not
implemented. The one-shot guarantee is structural (arc-end re-injection), not a
stored flag, and the dataplane performs no per-packet heap allocation.

When no eligible profile is bound, the admission feature is disabled on that
port, so there is no per-packet feature-node cost. If eligible queues remain but
the global trim policy is disabled, the node executes one early configuration
check and bypasses. Packets admitted to their original queue do not enter packet
mutation.

The software admission shim does not buffer packets; it only accounts byte
credits and immediately admits or rejects each buffer. Each `{port, queue}` has
one shared bucket with no synchronization. This is safe for the supported
single-worker topology; per-worker buckets or atomic accounting are deferred.

## 12. Error Handling

| Error case | Handling |
|---|---|
| Out-of-range scalar values reaching the vendor layer | The vendor code performs no additional rejection: trim size is narrowed to `u16`, DSCP is masked to six bits by the plugin, and the static trim queue is masked to three bits. The supported control path programs valid values (size 256/4084, DSCP 48, queue 6) |
| Queue is multicast or has an out-of-range unicast index | Multicast queues are skipped by `SAI_QUEUE_ATTR_TYPE` so a colliding multicast index cannot overwrite the corresponding unicast admission slot. Unicast indices at or above `SONIC_EXT_TRIM_MAX_QUEUES` (8) are skipped as SUCCESS. Every eligible lossy queue in the supported configuration is unicast and below the cap ([13.2](#132-design-limitations)) |
| `DYNAMIC` queue-resolution mode | Omitted from the advertised enum so orchagent never programs it; a stored value is not honored by the datapath ([7.12](#712-capability-advertisement)) |
| Queue attributes or bindings are not present during replay | Skip the incomplete queue for that refresh; a later trim-relevant set triggers another full recompute |
| No front-panel port currently has both DSCP-to-TC and TC-to-queue maps | Keep the plugin's last-good switch-wide DSCP-to-queue table rather than replacing it with an all-zero table |
| VPP plugin/API programming is unavailable | Capability advertisement is not dynamically probed. A set reports the VPP API failure for orchagent retry; create refresh remains best effort |
| VPP binary API update fails on a set | Commit the SAI object state and return the failure so orchagent retries; the next retry re-pushes the same full (idempotent) policy ([7.13](#713-update-and-remove-ordering)) |
| Asymmetric DSCP cannot be resolved at runtime (deferred `FROM_TC`) | Target design: drop the trim packet and increment a diagnostic error counter. Not reachable in this increment — only symmetric `DSCP_VALUE` is advertised and honored ([7.5](#75-dscp-resolution)) |
| Egress metadata is missing at admission failure | Use the normal drop path; do not guess an interface or queue |
| Trim queue rejects the packet | Drop once, increment the plugin trim-drop counter, and do not retry |
| SAI trim counter read | Trim stat IDs currently delegate to the shared virtual-switch base and return zero; SAI sourcing through `getStatsExt` is deferred ([7.11](#711-counters)) |

## 13. Limitations and Future Work

### 13.1 Integration status

The datapath in [6](#6-architecture)–[9](#9-configuration-and-management) — the software
admission shim, the trim action node, the binary API, and the debug CLI — is
implemented in the `sonic_ext` plugin and validated on standalone VPP
(happy-path trim plus the recycled-buffer regression that confirms the arc-end
bypass one-shot guarantee).

The SAI-VPP translation that drives it from live SONiC configuration is
implemented and validated at the datapath-programming layer on the `t1-lag`
testbed dev VM, confirmed by reading VPP's own plugin state (`show sonic-ext
trim`) after pushing configuration through CONFIG_DB:

1. **Per-`{port, queue}` eligibility** is programmed from
   `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` and the
   queue↔buffer-profile binding. **Validated:** with `egress_lossy_profile` set
   to `DROP_AND_TRIM`, VPP reports the lossy queues (`0,1,2,5,6`) eligible and
   the lossless queues (`3,4,7`) bypassed on every front-panel port.
2. **Scheduler state** maps onto the admission shim as binary unlimited/blocked;
   the buffer profile controls eligibility but does not provide bucket depth
   ([7.10](#710-scheduler-and-capacity-inputs)). **Validated:** unlimited
   eligible queues report `UINT64_MAX` rate/capacity and always admit; a queue
   with any nonzero scheduler `PIR` reports zero rate/capacity and drives the
   admission-failure branch.
3. **The global trim policy and switch-wide DSCP-to-queue table** are pushed and
   confirmed in VPP. **Validated:** `show sonic-ext trim` reports `size=256,
   dscp=48 (symmetric), queue=6`.

The remaining integration work, tracked by the feature story, is:

4. Source the switch/port/queue trim counters through `getStatsExt`
   ([7.11](#711-counters)) instead of returning the base's zero values, and
   enable the deferred `sonic-mgmt` trim-counter cases.
5. Complete or validate the deferred surfaces — asymmetric per-port DSCP
   (`FROM_TC`), `DYNAMIC` queue resolution, ACL disable-trim, GCU config,
   feature/port toggles, port mirroring, SRv6, and reload/reboot persistence —
   and remove the corresponding conditional_mark skips
   ([14.3](#143-enablement-gating)).

Capability is advertised as supported (`SWITCH_TRIMMING_CAPABLE=true`) and the
symmetric `packet_trimming` suite is enabled now that its end-to-end PTF cases
pass on the `t1-lag` testbed; the out-of-scope cases above remain skipped on
`vpp` until each is implemented and validated.

### 13.2 Design limitations

- Dynamic trim-queue resolution is not supported in the initial implementation;
  only `STATIC` queue resolution is advertised and honored.
- The plugin masks the configured static trim queue to the range 0–7. The
  supported configuration uses queue 6; explicit values above 7 are not rejected
  by the vendor path.
- The admission shim models only the token-bucket behavior needed to produce a
  recoverable admission failure; it is not full hardware-MMU or multi-level HQoS
  emulation.
- SAI-VPP programs only unicast (or `ALL`) queue objects into the admission
  shim. Multicast queues are skipped by type regardless of index so a colliding
  multicast index cannot overwrite the same-indexed unicast admission slot.
  Unicast queue indices at or above the plugin's
  `SONIC_EXT_TRIM_MAX_QUEUES` (8) are also skipped. The configured trim queue
  and every eligible lossy queue in the supported topology are unicast and below
  the cap.
- Eligibility is recomputed on each trim-relevant attribute change rather than
  cached at initialization ([7.8](#78-buffer-profile-and-queue-relationships)),
  so a binding that lands after an earlier recompute (for example while buffer
  configuration is still replaying on a cold boot) is picked up by the next
  trim-relevant update rather than being missed.
- The IPv4 header checksum is updated after the DSCP rewrite, but IP and
  transport **length** fields are deliberately not recalculated after truncation
  (the original length is the congestion signal —
  [7.4](#74-truncation-and-header-handling)).
- The admission shim uses one token bucket per `{port, queue}` updated on the
  egress worker; multi-worker per-queue bucket sharding is future work and is not
  required by the single-worker KVM topology.
- The global trim policy and the DSCP-to-queue table are switch-wide; per-port
  QoS-map variation is not modeled in the initial implementation, which matches
  the uniform testbed configuration.
- The first implementation targets the DPDK virtio egress backend used by the
  supported VPP KVM topology. Additional backends (for example the AF_PACKET
  `host-interface` path used for veth ports) may reuse the same generic admission
  node at their own pre-transmit point.
- Advanced interactions such as mirroring and SRv6 are enabled in sonic-mgmt only
  after their focused validation passes.

Future work includes dynamic queue resolution, per-worker bucket sharding,
per-port QoS-map fidelity, broader software QoS scheduling, and upstreaming any
generic VPP admission-failure integration through FD.io.

## 14. Testing

### 14.1 Unit and Component Tests

**Target coverage.** The full trim design is intended to be covered by VPP
framework tests and SAI-VPP unit tests:

- VPP dataplane: IPv4/IPv6 TCP/UDP packets; packets larger than, equal to, and
  smaller than the trim size; symmetric and asymmetric DSCP resolution; ECN
  preservation; ineligible buffer profiles; ACL trim disable; original-queue and
  trim-queue admission failure; one-shot retry behavior; physical and LAG-member
  egress attribution; chained-buffer truncation; counter read and clear behavior.
- SAI-VPP: capability query results; switch attribute handling and update
  ordering; buffer-profile-to-queue relationship changes; QoS map create,
  replace, and remove; ACL action create, update, and remove; VPP failure
  propagation/retry; switch, port, and queue statistic mapping.

**Delivered in this enablement.** The datapath itself was validated on standalone
VPP and on the `t1-lag` dev VM by reading the plugin state directly (`show
sonic-ext trim`, [13.1](#131-integration-status)); no automated VPP framework
tests are added for `sonic_ext` yet. The SAI-VPP unit tests
(`unittest/vslib/TestSwitchVpp.cpp`, built under `USE_VPP`) cover the pure
decision logic that gates the enablement:

- `getTrimEnumValuesCapability` — the trim enum-values advertisement
  ([7.12](#712-capability-advertisement)): `DSCP_VALUE` for the DSCP mode,
  `STATIC` for the queue mode, and no match for unrelated attributes or object
  types.
- `isTrimDataplaneAttr` — the set/create attribute classification that triggers a
  per-queue trim re-resolve, including the port QoS-map bindings and QoS-map
  edits.
- `getLagMemberEgressDisableAction` — pre-existing LAG-member egress logic.

The remaining target coverage (VPP framework tests and
counter/failure-propagation/QoS-map SAI tests) is future work tracked with the
deferred datapath modes
([13.1](#131-integration-status)).

### 14.2 System Tests

The packet-trimming suite is enabled on the VPP `t1-lag` KVM topology in
stages:

1. Runtime configuration and capability tests (not the deferred GCU config
   modules).
2. Symmetric packet size and DSCP tests.
3. Asymmetric `FROM_TC` tests.
4. Feature and port-state toggles.
5. ACL disable trim.
6. Switch, port, and queue counters.
7. Trim-queue congestion.
8. Reload and reboot persistence.
9. Mirror and SRv6 interactions.

Target regression coverage includes normal forwarding, LAG hashing and
failover, QoS mapping, ACL actions, and the existing SONiC-VPP regression
suites.

**Validation status (2026-07-30).** Stages 1–2 are validated end to end on the
live `vms-kvm-vpp-t1-lag` testbed with the delivered `sonic_ext` datapath and the
SAI-VPP capability raised to `true`:

| Test | Result |
|---|---|
| `test_trimming_configuration` | pass |
| `test_packet_size_after_trimming` (single-segment 400→256) | pass |
| `test_packet_size_after_trimming` (jumbo/multi-segment 5000→4084, 3000→256) | pass |
| `test_dscp_remapping_after_trimming` (trimmed and small-untrimmed) | pass |

The jumbo case exercised the multi-segment DPDK mbuf fix in
[7.4](#74-truncation-and-header-handling). The asymmetric module, both GCU
config modules, counters, ACL disable-trim, feature/port toggles, reload/reboot
persistence, mirror, and SRv6 remain out of scope for this increment and are
tracked as future work in
[13.1](#131-integration-status).

**Test-layer self-sufficiency (2026-07-30).** The suite now runs unattended on
VPP with no manual `redis-cli` preparation. Three `sonic-mgmt` gaps surfaced on the
minimal `Force10-S6000` config and were closed in the test helpers:

- The per-block-queue `queue{1,3}_{uplink,downlink}_lossy_profile` BUFFER_PROFILEs
  the suite references ship only in the real Mellanox SN5640 / Arista 7060X6 QoS
  templates. `set_buffer_profile_for_block_queue` now creates the profile when it
  is absent (idempotent no-op on the real SKUs), so the block-queue scheduler
  wiring is available on VPP.
- `config load` of the pre-test backup is a merge, so a test-created
  `BUFFER_QUEUE|<intf>|<trim-queue>` reference is not removed on platforms whose
  base config lacks it (VPP). Teardown now clears those references before
  deleting `trim_queue_test_profile`, so post-test YANG validation stays clean.
- The blocking-queue setup can also create lossy buffer profiles and
  `BUFFER_QUEUE` bindings on VPP. Teardown records those bindings, removes them,
  and deletes only profiles created by the fixture before restoring the backup.

With these fixes the three in-scope cases pass with zero setup/teardown errors.

### 14.3 Enablement Gating

The suite is gated by two mechanisms that act at different granularities:

1. The `sonic-mgmt` `conditional_mark` packet-trimming rule (OR-combined
   conditions). On the VPP testbed `asic_type` is `vpp` (not `vs`) and `hwsku`
   is `Force10-S6000`, so the hardware-SKU allowlist disjunct is the one that
   would otherwise skip the suite; it is amended to exempt VPP (see the
   implemented enablement below). This is the primary gate for **scoping** the
   suite on VPP: it selects exactly the in-scope symmetric cases to run and
   defers every out-of-scope case, keyed on `asic_type == vpp`.
2. The suite's own `skip_if_packet_trimming_not_supported` fixture, which reads
   `STATE_DB SWITCH_CAPABILITY|switch:SWITCH_TRIMMING_CAPABLE` and skips the
   whole suite when it is not `true`.

Mechanism 2 is a coarse on/off switch, and it is **satisfied** on VPP:
`SWITCH_TRIMMING_CAPABLE` is `true` (the shared virtual-switch base reports the
switch trim capability as implemented; VPP narrows only the advertised trim
*enum values* to the modes the datapath honors — see
[7.12](#712-capability-advertisement)), so the fixture does not skip. Case-level
scoping is therefore performed entirely by Mechanism 1: `conditional_mark` runs
the in-scope symmetric cases on VPP and defers the rest. The suite is brought up
in the stages listed in [14.2](#142-system-tests), deferring each
not-yet-validated stage through `conditional_mark` rather than by gating the
switch capability off.

**Implemented enablement (2026-07-30).** The `packet_trimming` `conditional_mark`
rule is updated so exactly the three in-scope symmetric cases run on VPP:

- The hardware-SKU allowlist disjunct becomes
  `hwsku not in [<4 real SKUs>] and asic_type != 'vpp'`, so the SKU gate no
  longer skips the suite on VPP while every non-VPP platform keeps its prior
  behavior.
- The deferred cases are skipped on VPP with per-test / per-file rules keyed on
  `asic_type in ['vpp']`: the whole `test_packet_trimming_asymmetric.py` module,
  both `test_packet_trimming_config_asymmetric.py` and
  `test_packet_trimming_config_symmetric.py`,
  and the symmetric `test_acl_action_with_trimming`, `test_trimming_with_srv6`,
  `test_stability_during_feature_toggles`,
  `test_trimming_during_port_admin_toggle`,
  `test_trimming_with_reload_and_reboot`, `test_trimming_counters`,
  `test_trimming_counters_with_feature_toggle`, and
  `test_port_mirror_with_trimming` cases. Each carries a reason pointing at the
  deferral in [13.1](#131-integration-status) and the tracking issue.

This was validated by driving the plugin's own `find_all_matches` /
`evaluate_conditions` logic against the deployed rule file with the DUT's real
facts: on VPP the three in-scope cases run and all deferred/asymmetric cases
skip; on the real SN5640 SKU every case still runs; on a non-listed SKU and on
the generic `vs` KVM every case still skips. The longest-match-per-mark
semantics keep the VPP disjunct and the general rule mutually exclusive per
platform, so there is no cross-interference.

The local KVM harness cannot exercise a `conditional_mark`-enforcing `pytest`
run because its `dut_basic_facts` ansible module is incompatible with the
harness ansible-core (`No module named ansible.module_utils.parse_utils`), which
is why in-harness runs use `--ignore-conditional-mark` and select cases with
`-k`. The rule is therefore validated at the plugin-decision level and behaves
normally in standard CI, where DUT fact-gathering works.

## 15. Open Items

Gate 0 (feasibility) is **resolved positively**: the VPP egress backend is DPDK
virtio with LCP TAP control-plane interfaces and has no native QoS/admission
substrate, so this design supplies that substrate as a generic software admission
shim in the `sonic_ext` plugin ([7.1](#71-admission-provider)) and builds the
trim action on top of it. The former open question — whether the backend could
supply recoverable admission directly or needed a software shim — is answered:
the shim approach is implemented and validated on standalone VPP.

The remaining integration details and their current status are tracked by the
feature story ([13.1](#131-integration-status)):

1. **Resolved.** SAI-VPP maps the SONiC scheduler onto the shim as open/closed:
   no effective rate limit admits, while any nonzero
   `MAX_BANDWIDTH_RATE` (including `SCHEDULER_BLOCK_DATA_PLANE`) programs a
   zero-rate, zero-capacity bucket and rejects. The buffer profile controls
   eligibility only. A proportional sub-line-rate `PIR` and real buffer capacity
   are not modeled ([7.10](#710-scheduler-and-capacity-inputs)).
2. Add the target per-`{port, queue}` counters and `getStatsExt` sourcing, then
   confirm the queue-index attribution expected by the `sonic-mgmt` counter
   assertions (which read `trimpacket` on the trim-queue index)
   ([7.11](#711-counters)).
3. **Resolved.** The [7.12](#712-capability-advertisement) enum-narrowing
   override is in place: `SWITCH_TRIMMING_CAPABLE` is advertised `true` for the
   symmetric core, with the trim enum values restricted to `DSCP_VALUE` and
   `STATIC` so orchagent never programs the asymmetric modes VPP does not
   implement. Out-of-scope cases are deferred in `sonic-mgmt` via
   `conditional_mark` rather than by gating the capability off
   ([14.3](#143-enablement-gating)).

These items do not change the SONiC configuration or SAI contract, nor the
generic packet-trimming design described above.

## 16. References

- [SONiC Packet Trimming HLD](../packet_trimming/packet-trimming-design.md)
- [SONiC-VPP LAG Member Egress Disable HLD](vpp-lag-member-egress-disable-HLD.md)
- [SONiC HLD Template](../guidelines/hld_template.md)
- [sonic-buildimage issue #25789](https://github.com/sonic-net/sonic-buildimage/issues/25789)
- [SAI repository](https://github.com/opencomputeproject/SAI)
- [FD.io VPP](https://github.com/FDio/vpp)
