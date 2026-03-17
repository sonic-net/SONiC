# SONiC Packet Capture (sonic-pcap) HLD

## Table of Contents

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Abbreviations](#3-abbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
  - [5.1 Functional Requirements](#51-functional-requirements)
  - [5.2 Configuration and Management Requirements](#52-configuration-and-management-requirements)
  - [5.3 Scalability Requirements](#53-scalability-requirements)
- [6. Architecture Design](#6-architecture-design)
  - [6.1 Capture Modes](#61-capture-modes)
  - [6.2 Data Flow](#62-data-flow)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Mirror Manager](#71-mirror-manager)
  - [7.2 Platform Capabilities](#72-platform-capabilities)
  - [7.3 tcpdump Backend](#73-tcpdump-backend)
  - [7.4 Cleanup and Safety](#74-cleanup-and-safety)
  - [7.5 Inline Explanations](#75-inline-explanations)
- [8. DB Changes](#8-db-changes)
  - [8.1 CONFIG_DB](#81-config_db)
  - [8.2 STATE_DB](#82-state_db)
- [9. SAI Requirements](#9-sai-requirements)
  - [9.1 Current State](#91-current-state)
  - [9.2 Required SAI Behavior](#92-required-sai-behavior)
  - [9.3 Vendor Implementation Notes](#93-vendor-implementation-notes)
- [10. SWSS Changes](#10-swss-changes)
  - [10.1 mirrororch Changes](#101-mirrororch-changes)
  - [10.2 CoPP Configuration](#102-copp-configuration)
- [11. CLI Design](#11-cli-design)
  - [11.1 sonic-pcap Command](#111-sonic-pcap-command)
  - [11.2 Subcommands](#112-subcommands)
  - [11.3 Usage Examples](#113-usage-examples)
- [12. YANG Model](#12-yang-model)
- [13. Warmboot and Fastboot Design Impact](#13-warmboot-and-fastboot-design-impact)
- [14. Testing Requirements](#14-testing-requirements)
  - [14.1 Unit Tests](#141-unit-tests)
  - [14.2 System Tests](#142-system-tests)
- [15. Open Questions](#15-open-questions)

## 1. Revision

| Rev | Date       | Author | Change Description |
|:---:|:----------:|:------:|--------------------|
| 0.1 | 2026-03-17 | Jaime  | Initial version    |

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

## 5. Requirements

### 5.1 Functional Requirements

1. One-command packet capture on any interface with automatic mirror session management
2. Three capture modes:
   - **mirror-to-cpu**: SPAN mirror to CPU port, capture via tcpdump on mirror netdev (requires vendor SAI support)
   - **mirror-to-port**: SPAN mirror to a physical port, capture via tcpdump on that port
   - **cpu-only**: Plain tcpdump on the kernel interface (control-plane traffic only, no mirror)
3. Automatic cleanup of mirror sessions on exit, Ctrl+C, SIGTERM, or crash
4. Detection and cleanup of stale sessions from previous interrupted captures
5. Live stats display (packets, bytes, rate, drops) in the terminal
6. BPF filter support (passed through to tcpdump)
7. PCAP file output, including stdout pipe mode (`-w -`) for streaming to Wireshark
8. Graceful degradation when mirror-to-CPU is not supported by the platform

### 5.2 Configuration and Management Requirements

1. No persistent configuration changes — sonic-pcap creates ephemeral mirror sessions and cleans them up
2. All sonic-pcap mirror sessions use a `SONIC_PCAP_` prefix for identification
3. Platform capabilities queryable via `sonic-pcap capabilities`
4. Stale sessions removable via `sonic-pcap cleanup`

### 5.3 Scalability Requirements

1. One capture session at a time (sonic-pcap is a debugging tool, not a monitoring pipeline)
2. CoPP rate-limiting for mirror-to-CPU mode to protect the CPU (default: 1000 pps)
3. Configurable timeout (default: 300 seconds) as a safety net

## 6. Architecture Design

### 6.1 Capture Modes

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

### 6.2 Data Flow

```
sonic-pcap CLI
    |
    |-- 1. Query STATE_DB SWITCH_CAPABILITY for mirror support
    |-- 2. Write MIRROR_SESSION to CONFIG_DB (SONIC_PCAP_<uuid>)
    |-- 3. Poll STATE_DB MIRROR_SESSION_TABLE for status=active
    |-- 4. Detect mirror netdev (mirror0) or use destination port
    |-- 5. Launch tcpdump subprocess on the capture interface
    |-- 6. Display live stats + inline explanations on stderr
    |-- 7. On exit: stop tcpdump, delete MIRROR_SESSION from CONFIG_DB
    |
    v
CONFIG_DB MIRROR_SESSION
    |
    v
mirrororch (sonic-swss)
    |-- validateDstPort() -- accepts Port::CPU (NEW)
    |-- activateSession() -- sets SAI_MIRROR_SESSION_ATTR_MONITOR_PORT = CPU OID
    |
    v
Vendor SAI
    |-- create_mirror_session() with MONITOR_PORT = CPU port OID
    |-- Programs ASIC to mirror traffic to CPU
    |-- Creates kernel netdev for packet delivery (vendor-specific)
    |
    v
Linux kernel netdev ("mirror0")
    |
    v
tcpdump captures packets
```

## 7. High-Level Design

### 7.1 Mirror Manager

Creates and deletes SPAN mirror sessions in CONFIG_DB using `ConfigDBConnector.set_entry()`. Replicates the pattern from `sonic-utilities/config/main.py:3311-3439`.

- Session names: `SONIC_PCAP_<uuid8>` for easy identification
- Entry format: `{"type": "SPAN", "src_port": "<interface>", "dst_port": "CPU", "direction": "BOTH"}`
- Polls STATE_DB `MIRROR_SESSION_TABLE|<name>` for `status: "active"` (30s timeout)
- Multi-ASIC: iterates front-end namespaces via `multi_asic.get_all_namespaces()`

### 7.2 Platform Capabilities

Queries STATE_DB `SWITCH_CAPABILITY|switch` for:
- `PORT_INGRESS_MIRROR_CAPABLE`
- `PORT_EGRESS_MIRROR_CAPABLE`
- `MIRROR`

Absent keys are treated as supported (backward compatibility per existing `config/main.py:1198` pattern).

Detects CPU mirror netdev by checking for known interface names (`mirror0`) and falling back to `/etc/sonic/sonic-pcap.conf` for operator override.

### 7.3 tcpdump Backend

Launches tcpdump as a subprocess with `--immediate-mode` for real-time output. Supports:
- Text mode (packet lines to stdout)
- Binary mode (`-w -` for PCAP stream to stdout, enabling `sonic-pcap -i Eth0 -w - | wireshark -k -i -`)
- BPF filter passthrough
- Configurable snap length and packet count

### 7.4 Cleanup and Safety

- Registers `atexit`, `SIGINT`, and `SIGTERM` handlers to delete mirror sessions
- Thread-locked cleanup prevents double-deletion
- On startup, scans CONFIG_DB for `SONIC_PCAP_*` sessions without a running process and cleans them up
- Default 5-minute timeout prevents forgotten sessions

### 7.5 Inline Explanations

The key differentiator. sonic-pcap prints educational ASCII-boxed explanations that teach users:
- What capture mode is active and how it works
- What traffic they will and won't see
- Why no packets are appearing (after 10 seconds of silence)
- When CoPP rate limiting may be dropping mirrored packets
- Capture summary with stats on completion

Example:

```
+--[ Capture Mode: Data-Plane Mirror-to-CPU ]--------------------------+
|                                                                      |
| HOW IT WORKS:                                                        |
|   ASIC --> hardware mirror (SPAN) --> copy to CPU --> tcpdump        |
|                                                                      |
| WHAT YOU SEE:                                                        |
|   All traffic on Ethernet0 (ingress + egress), but rate-limited      |
|   by CoPP to ~1000 packets/sec.                                     |
|                                                                      |
| WHAT YOU DON'T SEE:                                                  |
|   Packets dropped by ASIC before mirroring (ACL denies, etc.)        |
|                                                                      |
+----------------------------------------------------------------------+
```

## 8. DB Changes

### 8.1 CONFIG_DB

No schema changes. Uses existing `MIRROR_SESSION` table:

```
MIRROR_SESSION|SONIC_PCAP_a1b2c3d4
    "type": "SPAN"
    "src_port": "Ethernet0"
    "dst_port": "CPU"
    "direction": "BOTH"
```

### 8.2 STATE_DB

No schema changes. Reads existing tables:
- `MIRROR_SESSION_TABLE|<name>` — polls for `status: "active"`
- `SWITCH_CAPABILITY|switch` — reads mirror capability flags

## 9. SAI Requirements

### 9.1 Current State

- `SAI_SWITCH_ATTR_CPU_PORT` returns a valid CPU port OID on all platforms
- `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` accepts physical port OIDs
- No vendor SAI currently accepts the CPU port OID as a MONITOR_PORT value
- The SAI specification does not prohibit this — it is an implementation gap

### 9.2 Required SAI Behavior

When `sai_mirror_api->create_mirror_session()` is called with:
- `SAI_MIRROR_SESSION_ATTR_TYPE = SAI_MIRROR_SESSION_TYPE_LOCAL`
- `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT = <CPU port OID>`

The vendor SAI should:

1. Return `SAI_STATUS_SUCCESS`
2. Program the ASIC to copy mirrored packets to the CPU RX path
3. Deliver those packets to a Linux netdev (e.g., `mirror0`)
4. On session removal, tear down the netdev

If the vendor SAI does not support this, it should return `SAI_STATUS_NOT_SUPPORTED`. sonic-pcap handles this gracefully with a fallback message.

### 9.3 Vendor Implementation Notes

The packet delivery mechanism is vendor-specific:

**Cisco Silicon One**: The NPU already supports mirror-to-CPU (IOS-XR EPC uses this path). The Silicon One SAI adapter needs to expose it via `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT`.

**Broadcom**: The KNET driver (`ngknet_extra.c`) already has mirror packet delivery infrastructure (`mirror_type`, `mirror_id`, `mirror_ndev`). The SAI needs to create a KNET virtual netdev and filter when MONITOR_PORT is the CPU port.

**Mellanox/NVIDIA**: The `psample` kernel subsystem handles ASIC-to-CPU packet delivery for sFlow. A similar mechanism could be used for mirrored packets.

**Precedent**: sFlow already delivers ASIC-sampled packets to CPU on all platforms via `SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET`. Mirror-to-CPU uses the same data path — the trigger differs (mirror session vs statistical sampling).

## 10. SWSS Changes

### 10.1 mirrororch Changes

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

### 10.2 CoPP Configuration

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

## 11. CLI Design

### 11.1 sonic-pcap Command

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
  -v, --verbose             Increase tcpdump verbosity (repeatable)
  -q, --quiet               Suppress explanations and stats
```

### 11.2 Subcommands

```
sonic-pcap capabilities    Show platform capture capabilities
sonic-pcap cleanup         Remove stale capture sessions
```

### 11.3 Usage Examples

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

## 12. YANG Model

No YANG model changes required. The existing `sonic-mirror-session.yang` already allows `dst_port: "CPU"` for SPAN sessions (lines 145-157).

## 13. Warmboot and Fastboot Design Impact

No impact. sonic-pcap creates ephemeral mirror sessions for debugging. Sessions are cleaned up before any reboot. If a session persists through a crash, the stale session cleanup runs on next `sonic-pcap` invocation.

## 14. Testing Requirements

### 14.1 Unit Tests

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

### 14.2 System Tests

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

## 15. Open Questions

1. **SAI vendor support timeline**: Which vendors will implement `MONITOR_PORT=CPU` first? Cisco Silicon One is the most likely candidate (IOS-XR EPC on same hardware proves NPU capability).

2. **Netdev naming convention**: Should the CPU mirror netdev be standardized as `mirror0` across all vendors, or should sonic-pcap discover it dynamically? Current design supports both (checks known names, falls back to config file).

3. **CoPP trap type**: Should mirrored-to-CPU packets reuse `SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET` or use a vendor-specific custom range trap? Reusing `SAMPLEPACKET` is simpler but may conflict with sFlow if both are active simultaneously.

4. **Multi-interface capture**: Phase 1 supports single interface. Should phase 2 support `-i Ethernet0,Ethernet4` or wildcard `-i any`?
