# SONiC Packet Capture (sonic-pcap) HLD

## Table of Contents

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Abbreviations](#3-abbreviations)
- [4. Overview](#4-overview)
- [5. What Works Today vs. What Needs Vendor SAI Support](#5-what-works-today-vs-what-needs-vendor-sai-support)
- [6. Requirements](#6-requirements)
  - [6.1 Functional Requirements](#61-functional-requirements)
  - [6.2 Configuration and Management Requirements](#62-configuration-and-management-requirements)
  - [6.3 Scalability Requirements](#63-scalability-requirements)
- [7. Architecture Design](#7-architecture-design)
  - [7.1 Capture Modes](#71-capture-modes)
  - [7.2 Data Flow](#72-data-flow)
- [8. High-Level Design](#8-high-level-design)
  - [8.1 Mirror Manager](#81-mirror-manager)
  - [8.2 Platform Capabilities](#82-platform-capabilities)
  - [8.3 tcpdump Backend](#83-tcpdump-backend)
  - [8.4 Cleanup and Safety](#84-cleanup-and-safety)
  - [8.5 Inline Explanations](#85-inline-explanations)
- [9. CPU Protection](#9-cpu-protection)
  - [9.1 ASIC Policer](#91-asic-policer)
  - [9.2 CoPP Backstop](#92-copp-backstop)
  - [9.3 Kernel BPF Filter](#93-kernel-bpf-filter)
  - [9.4 Auto-Timeout](#94-auto-timeout)
- [10. Operational Impact](#10-operational-impact)
- [11. DB Changes](#11-db-changes)
  - [11.1 CONFIG_DB](#111-config_db)
  - [11.2 STATE_DB](#112-state_db)
- [12. SAI Requirements](#12-sai-requirements)
  - [12.1 Current State](#121-current-state)
  - [12.2 Required SAI Behavior](#122-required-sai-behavior)
  - [12.3 Vendor Implementation Notes](#123-vendor-implementation-notes)
- [13. SWSS Changes](#13-swss-changes)
  - [13.1 mirrororch Changes](#131-mirrororch-changes)
  - [13.2 CoPP Configuration](#132-copp-configuration)
- [14. CLI Design](#14-cli-design)
  - [14.1 sonic-pcap Command](#141-sonic-pcap-command)
  - [14.2 Subcommands](#142-subcommands)
  - [14.3 Usage Examples](#143-usage-examples)
- [15. YANG Model](#15-yang-model)
- [16. Warmboot and Fastboot Design Impact](#16-warmboot-and-fastboot-design-impact)
- [17. Testing Requirements](#17-testing-requirements)
  - [17.1 Unit Tests](#171-unit-tests)
  - [17.2 System Tests](#172-system-tests)
- [18. Open Questions](#18-open-questions)

## 1. Revision

| Rev | Date       | Author | Change Description |
|:---:|:----------:|:------:|--------------------|
| 0.1 | 2026-03-17 | Jaime  | Initial version    |
| 0.2 | 2026-03-17 | Jaime  | Add ASIC policer design, CPU protection, operational impact, what works today vs. vendor SAI |

## 2. Scope

This document presents the high-level design for `sonic-pcap`, a unified packet capture CLI tool for SONiC. It covers:

- A new CLI tool that automates mirror session management and tcpdump execution
- A one-line change to `mirrororch` to accept CPU as a SPAN mirror destination
- The SAI behavior required from vendor implementations to enable mirror-to-CPU
- CoPP configuration for rate-limiting mirrored traffic to the CPU

This document does NOT propose changes to the SAI specification. It proposes that vendor SAI implementations accept an existing port OID (the CPU port) as a value for an existing attribute (`SAI_MIRROR_SESSION_ATTR_MONITOR_PORT`).

## 3. Abbreviations

| Abbreviation | Description |
|:------------:|-------------|
| SPAN | Switched Port Analyzer (local port mirroring) |
| ERSPAN | Encapsulated Remote SPAN (tunneled mirroring) |
| CoPP | Control Plane Policing |
| SAI | Switch Abstraction Interface |
| KNET | Memory Memory Memory Memory Kernel Network (Broadcom kernel driver) |
| NPU | Network Processing Unit |
| EPC | Embedded Packet Capture (Cisco IOS-XR feature) |
| BPF | Berkeley Packet Filter |

## 4. Overview

SONiC currently has no integrated packet capture command. Capturing data-plane traffic requires multiple manual steps:

1. Create a SPAN mirror session to a physical destination port
2. Connect an external packet analyzer to that port
3. Run tcpdump on the destination port's kernel interface
4. Manually delete the mirror session when done

Every major NOS solves this in one command:

| NOS | Command |
|-----|---------|
| Cisco IOS-XR | `monitor capture` (EPC) |
| Cisco NX-OS | `ethanalyzer` / SPAN-to-CPU |
| Arista EOS | `monitor session ... destination Cpu` + `bash tcpdump` |
| Juniper JunOS | `monitor traffic interface` |
| **SONiC** | **3+ manual steps (no unified command)** |

`sonic-pcap` closes this gap. It automates mirror session lifecycle, wraps tcpdump, and provides inline educational explanations that teach users what they're seeing and why.

## 5. What Works Today vs. What Needs Vendor SAI Support

sonic-pcap has three capture modes. Two work on all platforms today with no changes. The third — mirror-to-CPU — needs vendor SAI support to enable data-plane capture directly to the CPU.

```
+------------------+-------------------+-------------------------------------------+
| Mode             | Works Today?      | What It Captures                          |
+------------------+-------------------+-------------------------------------------+
| CPU-only         | YES, all platforms| Control-plane traffic only (ARP, BGP,     |
|                  |                   | LLDP, SSH). 99.9% of ASIC-forwarded       |
|                  |                   | traffic is invisible. No mirror session.   |
+------------------+-------------------+-------------------------------------------+
| Mirror-to-port   | YES, all platforms| Data-plane traffic mirrored to a physical  |
|                  |                   | port via standard SPAN. Requires a spare   |
|                  |                   | port and an external capture device.       |
+------------------+-------------------+-------------------------------------------+
| Mirror-to-CPU    | NO — needs vendor | Data-plane traffic mirrored to the CPU.    |
|                  | SAI support       | No spare port, no external device. One     |
|                  |                   | command. This is the transformative mode.  |
+------------------+-------------------+-------------------------------------------+
```

The SAI work required: vendor SAI implementations must accept the CPU port OID as a mirror destination and deliver mirrored packets to a Linux netdev. Every vendor already has ASIC-to-CPU infrastructure (sFlow, traps, etc.) — the gap is wiring mirror sessions to use that same path.

## 6. Requirements

### 6.1 Functional Requirements

1. One-command packet capture on any interface with automatic mirror session management
2. Three capture modes:
   - **mirror-to-cpu**: SPAN mirror to CPU port, capture via tcpdump on mirror netdev (requires vendor SAI support)
   - **mirror-to-port**: SPAN mirror to a physical port, capture via tcpdump on that port (works today)
   - **cpu-only**: Plain tcpdump on the kernel interface (control-plane traffic only, no mirror) (works today)
3. Automatic cleanup of mirror sessions on exit, Ctrl+C, SIGTERM, or crash
4. Detection and cleanup of stale sessions from previous interrupted captures
5. Live stats display (packets, bytes, rate, drops) in the terminal
6. BPF filter support (passed through to tcpdump)
7. PCAP file output, including stdout pipe mode (`-w -`) for streaming to Wireshark
8. Graceful degradation when mirror-to-CPU is not supported by the platform
9. ASIC-level CPU protection via hardware policer on mirror sessions (default: 1000 pps)
10. Configurable packet sampling (`--sample-rate N`) for high-traffic interfaces

### 6.2 Configuration and Management Requirements

1. No persistent configuration changes — sonic-pcap creates ephemeral mirror sessions and policers, cleans them up on exit
2. All sonic-pcap mirror sessions use a `SONIC_PCAP_` prefix for identification
3. Platform capabilities queryable via `sonic-pcap capabilities`
4. Stale sessions removable via `sonic-pcap cleanup`

### 6.3 Scalability Requirements

1. One capture session at a time (sonic-pcap is a debugging tool, not a monitoring pipeline)
2. ASIC policer rate-limiting for mirror-to-CPU mode (default: 1000 pps, configurable via `--rate-limit`)
3. CoPP as a backstop rate limit on the CPU RX path
4. Configurable timeout (default: 300 seconds) as a safety net

## 7. Architecture Design

### 7.1 Capture Modes

```
+-------------------+---------------------+------------------------------+
| Mode              | Data Path           | What You See                 |
+-------------------+---------------------+------------------------------+
| mirror-to-cpu     | ASIC mirror -> CPU  | All traffic on interface,    |
| (default)         | -> mirror netdev    | rate-limited by CoPP         |
|                   | -> tcpdump          |                              |
+-------------------+---------------------+------------------------------+
| mirror-to-port    | ASIC mirror -> phys | All traffic on interface,    |
| (--to-port X)     | port -> tcpdump     | no rate limit (full rate)    |
+-------------------+---------------------+------------------------------+
| cpu-only          | kernel interface    | Only control-plane traffic   |
| (--cpu-only)      | -> tcpdump          | (ARP, BGP, LLDP, SSH, etc.) |
+-------------------+---------------------+------------------------------+
```

### 7.2 Data Flow

```
sonic-pcap CLI
    |
    |-- 1. Clean stale SONIC_PCAP_* sessions from CONFIG_DB
    |-- 2. Query STATE_DB SWITCH_CAPABILITY for mirror support
    |-- 3. Create POLICER entry in CONFIG_DB (ASIC-level rate limit)
    |-- 4. Write MIRROR_SESSION to CONFIG_DB (SONIC_PCAP_<uuid>)
    |-- 5. Poll STATE_DB MIRROR_SESSION_TABLE for status=active
    |-- 6. Detect mirror netdev (mirror0) or use destination port
    |-- 7. Launch tcpdump subprocess on the capture interface
    |-- 8. Display live stats + inline explanations on stderr
    |-- 9. On exit: stop tcpdump, delete MIRROR_SESSION + POLICER from CONFIG_DB
    |
    v
CONFIG_DB
    |-- MIRROR_SESSION (SONIC_PCAP_<uuid>)
    |-- POLICER (SONIC_PCAP_policer)
    |
    v
mirrororch + policerorch (sonic-swss)
    |-- validateDstPort() -- accepts Port::CPU (NEW)
    |-- activateSession() -- sets SAI_MIRROR_SESSION_ATTR_MONITOR_PORT = CPU OID
    |-- attaches SAI_MIRROR_SESSION_ATTR_POLICER for ASIC-level rate limit
    |
    v
Vendor SAI
    |-- create_mirror_session() with MONITOR_PORT = CPU port OID + policer
    |-- ASIC mirrors packets --> policer drops excess in hardware
    |-- Remaining packets delivered to CPU RX path
    |-- CoPP provides backstop rate limiting
    |-- Creates kernel netdev for packet delivery (vendor-specific)
    |
    v
Linux kernel netdev ("mirror0")
    |
    v
tcpdump captures packets (BPF filter runs in kernel)
```

## 8. High-Level Design

### 8.1 Mirror Manager

Creates and deletes SPAN mirror sessions in CONFIG_DB using `ConfigDBConnector.set_entry()`. Replicates the pattern from `sonic-utilities/config/main.py:3311-3439`.

- Session names: `SONIC_PCAP_<uuid8>` for easy identification
- Entry format: `{"type": "SPAN", "src_port": "<interface>", "dst_port": "CPU", "direction": "BOTH", "policer": "SONIC_PCAP_policer"}`
- Automatically creates a companion POLICER entry for ASIC-level CPU protection (see section 9)
- Polls STATE_DB `MIRROR_SESSION_TABLE|<name>` for `status: "active"` (30s timeout)
- On deletion, removes the POLICER entry if no other sonic-pcap sessions remain
- Multi-ASIC: iterates front-end namespaces via `multi_asic.get_all_namespaces()`

### 8.2 Platform Capabilities

Queries STATE_DB `SWITCH_CAPABILITY|switch` for:
- `PORT_INGRESS_MIRROR_CAPABLE`
- `PORT_EGRESS_MIRROR_CAPABLE`
- `MIRROR`

Absent keys are treated as supported (backward compatibility per existing `config/main.py:1198` pattern).

Detects CPU mirror netdev by checking for known interface names (`mirror0`) and falling back to `/etc/sonic/sonic-pcap.conf` for operator override.

### 8.3 tcpdump Backend

Launches tcpdump as a subprocess with `--immediate-mode` for real-time output. Supports:
- Text mode (packet lines to stdout)
- Binary mode (`-w -` for PCAP stream to stdout, enabling `sonic-pcap -i Eth0 -w - | wireshark -k -i -`)
- BPF filter passthrough
- Configurable snap length and packet count

### 8.4 Cleanup and Safety

- Registers `atexit`, `SIGINT`, and `SIGTERM` handlers to delete mirror sessions
- Thread-locked cleanup prevents double-deletion
- On startup, scans CONFIG_DB for `SONIC_PCAP_*` sessions without a running process and cleans them up
- Default 5-minute timeout prevents forgotten sessions

### 8.5 Inline Explanations

The key differentiator. sonic-pcap prints educational ASCII-boxed explanations that teach users:
- What capture mode is active and how it works
- What traffic they will and won't see
- What CPU protection is active and how to adjust it
- Why no packets are appearing (after 10 seconds of silence)
- When CoPP rate limiting may be dropping mirrored packets
- Capture summary with stats on completion

Example:

```
+--[ Capture Mode: Data-Plane Mirror-to-CPU ]--------------------------+
|                                                                      |
| HOW IT WORKS:                                                        |
|   ASIC --> hardware mirror (SPAN) --> policer --> copy to CPU -->     |
|   tcpdump                                                            |
|                                                                      |
| WHAT YOU SEE:                                                        |
|   All traffic on Ethernet0 (ingress + egress), rate-limited to       |
|   ~1000 packets/sec by the ASIC policer. Excess packets are          |
|   dropped in hardware before reaching the CPU.                       |
|                                                                      |
| CPU PROTECTION:                                                      |
|   ASIC policer: 1000 pps (change with --rate-limit N)               |
|   Sampling: every packet (change with --sample-rate N)               |
|   CoPP: backstop rate limit on the CPU RX path                      |
|                                                                      |
| WHAT YOU DON'T SEE:                                                  |
|   Packets dropped by ASIC before mirroring (ACL denies, etc.)        |
|   Packets dropped by the policer (use --rate-limit 0 to disable)     |
|                                                                      |
+----------------------------------------------------------------------+
```

## 9. CPU Protection

Mirror-to-CPU captures are protected by four layers that prevent the capture from impacting switch operation.

### 9.1 ASIC Policer (hardware, default on)

sonic-pcap automatically creates a SAI policer (`SAI_MIRROR_SESSION_ATTR_POLICER`) that rate-limits mirrored packets in hardware before they reach the CPU. Excess packets are dropped by the ASIC — they never consume CPU cycles or memory.

The policer uses SR_TCM (Single Rate Three Color Marker, RFC 2697):
- CIR (Committed Information Rate): configurable, default 1000 pps
- CBS (Committed Burst Size): matches CIR to allow short bursts
- Red packet action: drop (packets exceeding the rate are discarded in hardware)

```
POLICER|SONIC_PCAP_policer
    "meter_type": "packets"
    "mode": "sr_tcm"
    "cir": "1000"
    "cbs": "1000"
    "red_packet_action": "drop"
```

The policer is created in CONFIG_DB alongside the mirror session and removed on cleanup. Users control it via `--rate-limit`:

```bash
sonic-pcap -i Ethernet0                    # Default: 1000 pps policer
sonic-pcap -i Ethernet0 --rate-limit 500   # Conservative: 500 pps
sonic-pcap -i Ethernet0 --rate-limit 0     # Disable policer (not recommended)
```

For high-traffic interfaces, `--sample-rate N` mirrors 1-in-N packets (via `SAI_MIRROR_SESSION_ATTR_SAMPLE_RATE`), reducing load before the policer:

```bash
sonic-pcap -i Ethernet0 --sample-rate 100  # Mirror 1-in-100 packets
```

### 9.2 CoPP Backstop

SONiC's CoPP configuration provides per-queue rate limiting on the CPU RX path. The sFlow/sample_packet trap group defaults to 1000 pps. Mirror-to-CPU traffic benefits from this existing backstop. CoPP enforces per-queue isolation, so mirror traffic cannot starve control-plane protocols (BGP gets 6000 pps on its own queue, LACP likewise).

### 9.3 Kernel BPF Filter

tcpdump's `-f` filter compiles to BPF bytecode that runs in the kernel. Non-matching packets are discarded before being copied to userspace, reducing CPU load:

```bash
sonic-pcap -i Ethernet0 -f "tcp port 179"   # Only BGP packets
sonic-pcap -i Ethernet0 -f "icmp"            # Only ICMP packets
```

### 9.4 Auto-Timeout

Default 5-minute timeout (`--timeout 300`) ensures forgotten captures don't run indefinitely. Configurable with `--timeout 0` for unlimited.

At 1000 pps with the ASIC policer, tcpdump uses approximately 1-5% of one CPU core. The ASIC handles all packet selection and rate limiting — the CPU only processes what the policer allows through.

## 10. Operational Impact

sonic-pcap is designed to run on production switches without disrupting normal operation.

**Data plane forwarding: zero impact.** Mirroring is performed in ASIC hardware. The ASIC copies packets to the mirror destination after the normal forwarding decision. Original traffic is never delayed, dropped, or modified.

**Control plane protocols: unaffected.** BGP, LLDP, LACP, and other protocols have dedicated CoPP queues with separate rate limits. The ASIC policer on the mirror session drops excess mirrored packets in hardware before they reach the CPU.

**Mirror session slots: one slot consumed.** Most ASICs support 4 mirror sessions. sonic-pcap uses one for the duration of the capture. `sonic-pcap capabilities` reports the maximum. The slot is released when the capture ends.

**Mirror-to-port: destination port is dedicated.** When using `--to-port`, that port carries only mirrored traffic during capture. The explanation box warns about this. Mirror-to-CPU and CPU-only modes do not consume any physical port.

**CPU-only mode: truly zero impact.** No mirror session, no ASIC resources, no policer. tcpdump reads packets the CPU was already receiving.

**Cleanup safety.** If the SSH session drops, the switch loses power, or sonic-pcap crashes: atexit and signal handlers attempt cleanup; on next invocation, stale session scan removes orphans automatically.

```
+------------------+----------------+------------+---------------+-----------------+
| Mode             | Data Plane     | CPU Load   | Ports Used    | ASIC Resources  |
+------------------+----------------+------------+---------------+-----------------+
| Mirror-to-CPU    | No impact      | ~1-5% core | None          | 1 mirror slot   |
|                  |                | (policer   |               | 1 policer       |
|                  |                | bounded)   |               |                 |
+------------------+----------------+------------+---------------+-----------------+
| Mirror-to-port   | No impact      | ~1-5% core | 1 port        | 1 mirror slot   |
|                  |                |            | dedicated     |                 |
+------------------+----------------+------------+---------------+-----------------+
| CPU-only         | No impact      | <1% core   | None          | None            |
+------------------+----------------+------------+---------------+-----------------+
```

## 11. DB Changes

### 11.1 CONFIG_DB

No schema changes. Uses existing `MIRROR_SESSION` and `POLICER` tables:

```
MIRROR_SESSION|SONIC_PCAP_a1b2c3d4
    "type": "SPAN"
    "src_port": "Ethernet0"
    "dst_port": "CPU"
    "direction": "BOTH"
    "policer": "SONIC_PCAP_policer"

POLICER|SONIC_PCAP_policer
    "meter_type": "packets"
    "mode": "sr_tcm"
    "cir": "1000"
    "cbs": "1000"
    "red_packet_action": "drop"
```

Both entries are ephemeral — created on capture start and removed on capture end.

### 11.2 STATE_DB

No schema changes. Reads existing tables:
- `MIRROR_SESSION_TABLE|<name>` — polls for `status: "active"`
- `SWITCH_CAPABILITY|switch` — reads mirror capability flags

## 12. SAI Requirements

### 12.1 Current State

- `SAI_SWITCH_ATTR_CPU_PORT` returns a valid CPU port OID on all platforms
- `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` accepts physical port OIDs
- No vendor SAI currently accepts the CPU port OID as a MONITOR_PORT value
- The SAI specification does not prohibit this — it is an implementation gap

### 12.2 Required SAI Behavior

When `sai_mirror_api->create_mirror_session()` is called with:
- `SAI_MIRROR_SESSION_ATTR_TYPE = SAI_MIRROR_SESSION_TYPE_LOCAL`
- `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT = <CPU port OID>`

The vendor SAI should:

1. Return `SAI_STATUS_SUCCESS`
2. Program the ASIC to copy mirrored packets to the CPU RX path
3. Deliver those packets to a Linux netdev (e.g., `mirror0`)
4. On session removal, tear down the netdev

If the vendor SAI does not support this, it should return `SAI_STATUS_NOT_SUPPORTED`. sonic-pcap handles this gracefully with a fallback message.

### 12.3 Vendor Implementation Notes

The packet delivery mechanism is vendor-specific:

**Cisco Silicon One**: The NPU already supports mirror-to-CPU (IOS-XR EPC uses this path). The Silicon One SAI adapter needs to expose it via `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT`.

**Broadcom**: The KNET driver (`ngknet_extra.c`) already has mirror packet delivery infrastructure (`mirror_type`, `mirror_id`, `mirror_ndev`). The SAI needs to create a KNET virtual netdev and filter when MONITOR_PORT is the CPU port.

**Mellanox/NVIDIA**: The `psample` kernel subsystem handles ASIC-to-CPU packet delivery for sFlow. A similar mechanism could be used for mirrored packets.

**Precedent**: sFlow already delivers ASIC-sampled packets to CPU on all platforms via `SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET`. Mirror-to-CPU uses the same data path — the trigger differs (mirror session vs statistical sampling).

## 13. SWSS Changes

### 13.1 mirrororch Changes

**File**: `sonic-swss/orchagent/mirrororch.cpp`

**Change 1** — `validateDstPort()` (line 284): Accept `Port::CPU`

Current:
```cpp
if (port.m_type != Port::PHY)
```

Proposed:
```cpp
if (port.m_type != Port::PHY && port.m_type != Port::CPU)
```

**Change 2** — `setSessionState()` (line 589-603): Fix SPAN monitor port reporting

Add SPAN-specific path to resolve `session.dst_port` (string) instead of `session.neighborInfo.portId` (which is only populated for ERSPAN).

### 13.2 CoPP Configuration

Add a CoPP trap group for mirror traffic in `copp_cfg.j2`:

```json
"trap.group.mirror": {
    "trap_ids": "sample_packet",
    "cir": "1000",
    "cbs": "1000",
    "queue": "1",
    "trap_action": "copy"
}
```

This reuses `SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET` which is already supported on all platforms.

## 14. CLI Design

### 14.1 sonic-pcap Command

```
sonic-pcap [OPTIONS]

Options:
  -i, --interface TEXT      Interface to capture on (required)
  -f, --filter TEXT         BPF filter expression
  -w, --write FILE          Write PCAP to file ("-" for stdout)
  -c, --count INT           Stop after N packets
  -t, --timeout INT         Stop after N seconds (default: 300, 0=unlimited)
  -s, --snap-len INT        Bytes per packet (0=full)
  -d, --direction [rx|tx|both]  Capture direction (default: both)
  --mirror                  Force mirror mode
  --cpu-only                CPU traffic only (no mirror)
  --to-port TEXT            Mirror to physical port
  --rate-limit INT          ASIC policer rate limit in pps (default: 1000, 0=disable)
  --sample-rate INT         Mirror 1-in-N packets (default: 1 = all)
  -v, --verbose             Increase tcpdump verbosity (repeatable)
  -q, --quiet               Suppress explanations and stats
```

### 14.2 Subcommands

```
sonic-pcap capabilities    Show platform capture capabilities
sonic-pcap cleanup         Remove stale capture sessions
```

### 14.3 Usage Examples

```bash
# Basic capture with auto-mirror
sonic-pcap -i Ethernet0

# CPU-only (control plane traffic)
sonic-pcap -i Ethernet0 --cpu-only

# Mirror to physical port (full rate, no CoPP limit)
sonic-pcap -i Ethernet0 --to-port Ethernet48

# With BPF filter
sonic-pcap -i Ethernet0 -f "tcp port 179"

# Save to file
sonic-pcap -i Ethernet0 -w /tmp/capture.pcap

# Pipe to remote Wireshark
sonic-pcap -i Ethernet0 -w - | ssh user@laptop "wireshark -k -i -"

# Show what the platform supports
sonic-pcap capabilities
```

## 15. YANG Model

No YANG model changes required. The existing `sonic-mirror-session.yang` already allows `dst_port: "CPU"` for SPAN sessions (lines 145-157).

## 16. Warmboot and Fastboot Design Impact

No impact. sonic-pcap creates ephemeral mirror sessions for debugging. Sessions are cleaned up before any reboot. If a session persists through a crash, the stale session cleanup runs on next `sonic-pcap` invocation.

## 17. Testing Requirements

### 17.1 Unit Tests

122 unit tests implemented covering all modules. Tests run without a switch using mocked Redis and mocked subprocess.

| Module | Key Test Cases |
|--------|---------------|
| `test_main.py` | CLI flag parsing, missing -i error, mutual exclusion, subcommands |
| `test_mirror_manager.py` | CONFIG_DB create/delete, STATE_DB polling, stale cleanup |
| `test_platform_capabilities.py` | Capability parsing, absent key backward compat, CoPP rate |
| `test_tcpdump_backend.py` | Command construction, BPF filter, stats parsing, stop/kill |
| `test_explanation_system.py` | All box formats, word wrapping, all capture mode variants |
| `test_stats_display.py` | Counter formatting, TTY vs non-TTY, rate calculation |
| `test_cleanup.py` | SIGINT cleanup, atexit, double-cleanup safety, stale detection |
| `test_capture_engine.py` | Full orchestration flow, error paths |

### 17.2 System Tests

| Test Case | Description |
|-----------|-------------|
| CPU-only capture | `sonic-pcap -i Ethernet0 --cpu-only` — verify control-plane packets captured |
| Mirror-to-port | `sonic-pcap -i Ethernet0 --to-port Ethernet48` — verify data-plane traffic mirrored |
| Mirror-to-CPU | `sonic-pcap -i Ethernet0` — verify capture works (on platforms with SAI support) |
| BPF filter | `sonic-pcap -i Ethernet0 -f "icmp"` — verify only ICMP captured |
| PCAP output | `sonic-pcap -i Ethernet0 -w /tmp/test.pcap` — verify valid PCAP file |
| Cleanup on Ctrl+C | Interrupt capture, verify mirror session removed from CONFIG_DB |
| Stale cleanup | Kill sonic-pcap with SIGKILL, re-run, verify orphaned session cleaned |
| Capabilities | `sonic-pcap capabilities` — verify accurate platform reporting |
| Timeout | `sonic-pcap -i Ethernet0 -t 10` — verify auto-stop after 10 seconds |

## 18. Open Questions

1. **SAI vendor support timeline**: Which vendors will implement `MONITOR_PORT=CPU` first? Each vendor already has ASIC-to-CPU infrastructure that could be extended.

2. **Netdev naming convention**: Should the CPU mirror netdev be standardized as `mirror0` across all vendors, or should sonic-pcap discover it dynamically? Current design supports both (checks known names, falls back to config file).

3. **CoPP trap type**: Should mirrored-to-CPU packets reuse `SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET` or use a vendor-specific custom range trap? Reusing `SAMPLEPACKET` is simpler but may conflict with sFlow if both are active simultaneously.

4. **Multi-interface capture**: Phase 1 supports single interface. Should phase 2 support `-i Ethernet0,Ethernet4` or wildcard `-i any`?
