# Port Mirroring and Everflow on VPP Dataplane — High Level Design

## Revision History

| Date | Author | Description |
|---|---|---|
| 2026-05-20 | yue-fred-gao | Initial version with both SPAN and everflow |
| 2026-08-13 | yue-fred-gao | Updated Everflow mirror semantics to hybrid behavior: MIRROR_INGRESS clones immediately in ACL node; MIRROR_EGRESS sets deferred flag for late clone at egress. Synced section text, node graph summary, test expectations, and file change summary. |

## Table of Contents

- [Revision History](#revision-history)

- **Phase 1: Port Mirroring**
  1. [Overview](#1-overview)
  2. [Switch Capability Advertisement](#2-switch-capability-advertisement)
  3. [Port Mirroring — Feature Description](#3-port-mirroring--feature-description)
  4. [Port Mirroring — SONiC Configuration](#4-port-mirroring--sonic-configuration)
  5. [Port Mirroring — SAI API Calls](#5-port-mirroring--sai-api-calls)
  6. [Port Mirroring — VPP Implementation](#6-port-mirroring--vpp-implementation)
  7. [Port Mirroring — Unit Tests](#7-port-mirroring--unit-tests)
- **Phase 2: Everflow (ACL-Based Mirroring)**
  1. [Everflow — Feature Description](#8-everflow--feature-description)
  2. [Everflow — SONiC Configuration](#9-everflow--sonic-configuration)
      - [9.3 Supported Match Qualifiers](#93-supported-match-qualifiers)
      - [9.4 MIRROR_DSCP Table (Policer)](#94-mirror_dscp-table-policer)
      - [9.5 Per-Interface ACL Binding](#95-per-interface-acl-binding)
  3. [Everflow — SAI API Calls](#10-everflow--sai-api-calls)
  4. [Everflow — VPP Gap Analysis and Proposed Changes](#11-everflow--vpp-gap-analysis-and-proposed-changes)
  5. [Everflow — SAI-VPP Implementation](#12-everflow--sai-vpp-implementation)
  6. [Everflow — VPP Node Graphs](#13-everflow--vpp-node-graphs)
  7. [Everflow — Unit Tests](#14-everflow--unit-tests)
      - [14.2 IPv4 Match Qualifiers](#142-dataplane--ipv4-match-qualifiers)
      - [14.3 IPv6 Match Qualifiers](#143-dataplane--ipv6-match-qualifiers)
      - [14.5 Routing — Mirror Session Destination](#145-routing--mirror-session-destination)
      - [14.6 Advanced Scenarios](#146-advanced-scenarios)
      - [14.7 ACL Stage × Mirror Direction Matrix](#147-acl-stage--mirror-direction-matrix)
- **Cross-Cutting**
  1. [LAG / Port-Channel Support](#15-lag--port-channel-support)
- **Appendices**
  - [Appendix A: File Change Summary](#appendix-a-file-change-summary)
  - [Appendix B: VPP Existing API Reference](#appendix-b-vpp-existing-api-reference)

---

# Phase 1: Port Mirroring

## 1. Overview

This HLD covers mirroring support for the VPP dataplane in SONiC, delivered in two phases:

| Phase | Feature | Description | VPP Change Required |
|---|---|---|---|
| **Phase 1** | Port Mirroring | Mirror ALL traffic on a port to a destination (SPAN or ERSPAN) | None — uses VPP native SPAN module |
| **Phase 2** | Everflow | Mirror SELECTED traffic matching ACL rules | Yes — patch VPP ACL plugin with new mirror action |

Both phases share the same mirror session infrastructure (SPAN and ERSPAN session types), but differ in what triggers the mirroring:

```
 ┌─────────────────────────────────────────────────────────────┐
 │                    Mirror Session (shared)                  │
 │  ┌──────────────┐              ┌──────────────────────────┐ │
 │  │ SPAN (LOCAL)  │             │ ERSPAN (ENHANCED_REMOTE) │ │
 │  │ dst = phy port│             │ dst = GRE-ERSPAN tunnel  │ │
 │  └──────────────┘              └──────────────────────────┘ │
 └──────────────────────┬──────────────────────┬───────────────┘
                        │                      │
          ┌─────────────┴───────┐    ┌─────────┴──────────────┐
          │ Phase 1:            │    │ Phase 2:               │
          │ Port Mirroring      │    │ Everflow               │
          │ (VPP SPAN module)   │    │ (VPP ACL plugin patch) │
          │ ALL port traffic    │    │ ACL-selected traffic   │
          └─────────────────────┘    └────────────────────────┘
```

---

## 2. Switch Capability Advertisement

SONiC queries the SAI switch for mirror capabilities before using mirror features. The VPP SAI must respond correctly.

### 2.1 Capability Discovery Process

SwitchOrch queries mirror capabilities at startup:

```
SwitchOrch::querySwitchPortMirrorCapability()
  │
  ├── sai_query_attribute_capability(switch, SAI_OBJECT_TYPE_PORT,
  │     SAI_PORT_ATTR_INGRESS_MIRROR_SESSION, &capability)
  │     → Must return: { create=true, set=true, get=true }
  │
  ├── sai_query_attribute_capability(switch, SAI_OBJECT_TYPE_PORT,
  │     SAI_PORT_ATTR_EGRESS_MIRROR_SESSION, &capability)
  │     → Must return: { create=true, set=true, get=true }
  │
  └── sai_object_type_get_availability(switch,
        SAI_OBJECT_TYPE_MIRROR_SESSION, ...)
        → Must return available count > 0
```

MirrorOrch also checks availability before creating sessions:

```
MirrorOrch::isHwResourcesAvailable()
  └── sai_object_type_get_availability(switch,
        SAI_OBJECT_TYPE_MIRROR_SESSION, 0, nullptr, &availCount)
        → availCount > 0 required to proceed
```

### 2.2 Required VPP SAI Responses

| Query | SAI API | Required VPP Response |
|---|---|---|
| Port ingress mirror supported? | `sai_query_attribute_capability(PORT, INGRESS_MIRROR_SESSION)` | `set_implemented = true` |
| Port egress mirror supported? | `sai_query_attribute_capability(PORT, EGRESS_MIRROR_SESSION)` | `set_implemented = true` |
| Mirror sessions available? | `sai_object_type_get_availability(MIRROR_SESSION)` | count > 0 (max - used) |
| Max mirror sessions | `SAI_SWITCH_ATTR_MAX_MIRROR_SESSION` | 10 (no hard limit in vpp) |
| MIRROR capability | STATE_DB `SWITCH_CAPABILITY\|switch` `MIRROR` | `"true"` |
| MIRRORV6 capability | STATE_DB `SWITCH_CAPABILITY\|switch` `MIRRORV6` | `"true"` |
| Ingress ACL mirror action | `acl_capabilities["INGRESS"]["action_list"]` | Contains `MIRROR_INGRESS_ACTION`, `MIRROR_EGRESS_ACTION` |
| Egress ACL mirror action | `acl_capabilities["EGRESS"]["action_list"]` | Contains `MIRROR_INGRESS_ACTION`, `MIRROR_EGRESS_ACTION` |
| Port ingress mirror capable | STATE_DB `PORT_INGRESS_MIRROR_CAPABLE` | `"true"` |
| Port egress mirror capable | STATE_DB `PORT_EGRESS_MIRROR_CAPABLE` | `"true"` |

The sonic-mgmt Everflow tests (`tests/everflow/`) query these capabilities at fixture setup time. Tests are **skipped** if any required capability is missing. The VPP SAI must advertise all of these to pass the entire Everflow test suite.

### 2.3 Current VPP SAI State

The VS/VPP SAI interface already returns all capabilities as supported:

```cpp
// VirtualSwitchSaiInterface::queryAttributeCapability()
capability->create_implemented = true;
capability->set_implemented    = true;
capability->get_implemented    = true;
return SAI_STATUS_SUCCESS;
```

**Action required**: Implement `objectTypeGetAvailability()` for `SAI_OBJECT_TYPE_MIRROR_SESSION` to return a non-zero count. Currently returns `SAI_STATUS_NOT_SUPPORTED`.

### 2.4 Implementation

**File**: `src/sonic-sairedis/vslib/vpp/SwitchVpp.cpp`

```cpp
// In objectTypeGetAvailability() or SwitchVpp override:
case SAI_OBJECT_TYPE_MIRROR_SESSION:
    *count = 10 - used;  // We need to track the number of created mirror sessions, similar to nexthop CRM
    return SAI_STATUS_SUCCESS;
```

**File**: `src/sonic-sairedis/vslib/vpp/SwitchVpp.cpp` (switch attributes)

```cpp
// Return MAX_MIRROR_SESSION when queried:
case SAI_SWITCH_ATTR_MAX_MIRROR_SESSION:
    attr.value.u32 = 10;
    break;
```

---

## 3. Port Mirroring — Feature Description

Port mirroring copies ALL traffic on a source port (ingress, egress, or both) to a mirror destination. No packet filtering is applied.

### 3.1 How It Works

```
 ┌───────────────────────────────────────────────────────┐
 │  VPP Dataplane                                        │
 │                                                       │
 │  ┌───────────┐ ALL pkts  ┌─────────────────┐          │
 │  │ Ethernet0 │──────────>│ VPP SPAN module │          │
 │  │ (source)  │           │ (span-input /   │          │
 │  │           │           │  span-output)   │          │
 │  └───────────┘           └────────┬────────┘          │
 │                                   │ clone             │
 │                                   ▼                   │
 │                          ┌─────────────────┐          │
 │                          │ interface-output│          │
 │                          └────────┬────────┘          │
 │                              ┌────┴────┐              │
 │                              ▼         ▼              │
 │                        ┌────────┐ ┌──────────────┐    │
 │                        │ SPAN:  │ │ ERSPAN:      │    │
 │                        │ Eth8-tx│ │ gre-erspan   │    │
 │                        │ (local)│ │ → ip4-rewrite│    │
 │                        │        │ │ → phy-tx     │    │
 │                        └────────┘ └──────────────┘    │
 │                                                       │
 │  Original pkt continues through normal forwarding     │
 └───────────────────────────────────────────────────────┘
```

Key properties:
- **All traffic**: Every packet on the source port is cloned — no filtering
- **Direction control**: RX only, TX only, or both
- **SPAN or ERSPAN**: Mirror destination can be a local port or GRE-ERSPAN tunnel
- **Multiple source ports**: A single mirror session can have multiple source ports
- **VPP native**: Uses VPP's built-in SPAN module — no VPP code changes needed

### 3.2 VPP SPAN Module

VPP has a native port mirroring implementation at `src/vnet/span/`:

| Component | Description |
|---|---|
| `span.api` | `sw_interface_span_enable_disable` API message |
| `span.c` | Core logic — `span_add_delete_entry()` |
| `node.c` | Dataplane — `span_mirror()` with `vlib_buffer_copy()` |
| `span.h` | `span_interface_t`, `span_mirror_t` structs |

**VPP SPAN API:**
```c
autoreply define sw_interface_span_enable_disable {
    vl_api_interface_index_t sw_if_index_from;   /* source port */
    vl_api_interface_index_t sw_if_index_to;     /* mirror destination */
    vl_api_span_state_t state;                   /* 0=disable, 1=RX, 2=TX, 3=both */
    bool is_l2;
};
```

**VPP CLI:**
```
vpp# set interface span Ethernet0 destination Ethernet8 both
vpp# set interface span Ethernet0 destination gre0 rx
vpp# show interface span
```

**Feature arcs:**
- Ingress (RX): `device-input` → `span-input` node
- Egress (TX): `interface-output` → `span-output` node

---

## 4. Port Mirroring — SONiC Configuration

### 4.1 SPAN (Local Mirror)

```json
{
    "MIRROR_SESSION": {
        "port_mirror_span": {
            "type": "SPAN",
            "dst_port": "Ethernet8",
            "src_port": "Ethernet0,Ethernet4",
            "direction": "BOTH"
        }
    }
}
```

### 4.2 ERSPAN (Remote Mirror)

```json
{
    "MIRROR_SESSION": {
        "port_mirror_erspan": {
            "type": "ERSPAN",
            "dst_ip": "10.0.0.2",
            "src_ip": "10.0.0.1",
            "gre_type": "0x88BE",
            "dscp": "8",
            "ttl": "64",
            "src_port": "Ethernet0",
            "direction": "RX"
        }
    }
}
```

### 4.3 Configuration Fields

| Field     | Required | Description |
|-----------|----------|---------------------------------------------|
| type      | Yes      | `"SPAN"` for local mirror, `"ERSPAN"` for remote |
| dst_port  | SPAN     | Local destination port for mirrored packets |
| src_port  | Yes      | Comma-separated list of source ports |
| direction | Yes      | `"RX"`, `"TX"`, or `"BOTH"` |
| src_ip    | ERSPAN   | Outer IP source for ERSPAN encapsulation |
| dst_ip    | ERSPAN   | Collector IP (ERSPAN destination) |
| gre_type  | No       | GRE protocol type (default: 0x88BE) |
| dscp      | No       | DSCP value in outer IP header |
| ttl       | No       | TTL of outer IP header |

---

## 5. Port Mirroring — SAI API Calls

### 5.1 Create Mirror Session

#### SPAN (Local)

```c
sai_attribute_t attrs[] = {
    { SAI_MIRROR_SESSION_ATTR_TYPE,
      .value.s32 = SAI_MIRROR_SESSION_TYPE_LOCAL },
    { SAI_MIRROR_SESSION_ATTR_MONITOR_PORT,
      .value.oid = dst_port_oid },
};
sai_mirror_api->create_mirror_session(&session_oid, switch_id, 2, attrs);
```

#### ERSPAN (Remote)

```c
sai_attribute_t attrs[] = {
    { SAI_MIRROR_SESSION_ATTR_TYPE,
      .value.s32 = SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE },
    { SAI_MIRROR_SESSION_ATTR_ERSPAN_ENCAPSULATION_TYPE,
      .value.s32 = SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL },
    { SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION, .value.u8 = 4 },
    { SAI_MIRROR_SESSION_ATTR_SRC_IP_ADDRESS, .value.ipaddr = src_ip },
    { SAI_MIRROR_SESSION_ATTR_DST_IP_ADDRESS, .value.ipaddr = dst_ip },
    { SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE, .value.u16 = 0x88BE },
    { SAI_MIRROR_SESSION_ATTR_TOS, .value.u8 = (dscp << 2) },
    { SAI_MIRROR_SESSION_ATTR_TTL, .value.u8 = 64 },
    { SAI_MIRROR_SESSION_ATTR_SRC_MAC_ADDRESS, .value.mac = src_mac },
    { SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS, .value.mac = dst_mac },
    { SAI_MIRROR_SESSION_ATTR_MONITOR_PORT, .value.oid = port_oid },
};
sai_mirror_api->create_mirror_session(&session_oid, switch_id, 11, attrs);
```
Note: vpp dateplane doesn't support TOS, TTL, SRC/DST_MAC_ADDRESS
### 5.2 Bind Mirror Session to Port

MirrorOrch uses `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` and `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION` to bind the session to source port(s):

```c
// Bind ingress mirror (direction = RX or BOTH)
sai_attribute_t port_attr;
port_attr.id = SAI_PORT_ATTR_INGRESS_MIRROR_SESSION;
port_attr.value.objlist.count = 1;
port_attr.value.objlist.list = &session_oid;
sai_port_api->set_port_attribute(src_port_oid, &port_attr);

// Bind egress mirror (direction = TX or BOTH)
port_attr.id = SAI_PORT_ATTR_EGRESS_MIRROR_SESSION;
port_attr.value.objlist.count = 1;
port_attr.value.objlist.list = &session_oid;
sai_port_api->set_port_attribute(src_port_oid, &port_attr);
```

Direction mapping:
| CONFIG_DB direction | SAI Attributes Set |
|---|---|
| `"RX"` | `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` |
| `"TX"` | `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION` |
| `"BOTH"` | Both attributes |

### 5.3 Unbind Mirror Session from Port

```c
port_attr.id = SAI_PORT_ATTR_INGRESS_MIRROR_SESSION;
port_attr.value.objlist.count = 0;  // empty list = unbind
sai_port_api->set_port_attribute(src_port_oid, &port_attr);
```

### 5.4 SAI Object Relationships

```
  SAI_OBJECT_TYPE_MIRROR_SESSION (session_oid)
    ├── type = LOCAL or ENHANCED_REMOTE
    ├── monitor_port (SPAN: dst port, ERSPAN: egress port)
    └── [ERSPAN only: src_ip, dst_ip, gre_type, ttl, tos]

  SAI_OBJECT_TYPE_PORT (src_port_oid)
    ├── INGRESS_MIRROR_SESSION → { session_oid }   (if RX/BOTH)
    └── EGRESS_MIRROR_SESSION  → { session_oid }   (if TX/BOTH)
```

---

## 6. Port Mirroring — VPP Implementation

### 6.1 Component Overview

```
  SONiC Orchestration (MirrorOrch)
         │
         ▼
  SAI API (libsai)
         │
         ▼
  ┌──────────────────────────────────────────────┐
  │  src/sonic-sairedis/vslib/vpp/               │
  │                                              │
  │  SwitchVpp.cpp          (create_internal)    │
  │       │                                      │
  │       ├── SwitchVppMirror.cpp    [NEW]       │
  │       │    ├── createMirrorSession()         │
  │       │    │    ├── SPAN: resolve dst_port   │
  │       │    │    │   → sw_if_index            │
  │       │    │    └── ERSPAN: create GRE tunnel│
  │       │    │        → vpp_gre_tunnel_add_del │
  │       │    └── removeMirrorSession()         │
  │       │                                      │
  │       ├── SwitchVppPort.cpp     [MODIFY]     │
  │       │    └── setPort() handles:            │
  │       │         SAI_PORT_ATTR_INGRESS_MIRROR │
  │       │         SAI_PORT_ATTR_EGRESS_MIRROR  │
  │       │         → vpp_span_enable_disable()  │
  │       │                                      │
  │       └── vppxlate/                          │
  │            ├── SaiVppXlate.h     [MODIFY]    │
  │            │    └── vpp_span_enable_disable()│
  │            │    └── vpp_gre_tunnel_add_del() │
  │            └── SaiVppXlate.c     [MODIFY]    │
  │                 └── implement both wrappers  │
  └──────────────────────────────────────────────┘
```

### 6.2 New File: `SwitchVppMirror.cpp`

Handles `SAI_OBJECT_TYPE_MIRROR_SESSION` create/remove.

**Create flow:**

```
createMirrorSession(attrs)
  │
  ├── Extract: session type (LOCAL or ENHANCED_REMOTE)
  │
  ├── If type == LOCAL (SPAN):
  │     ├── Extract: monitor_port OID
  │     ├── Resolve monitor_port OID → VPP sw_if_index
  │     └── Store: session_oid → { sw_if_index, type=SPAN }
  │
  └── If type == ENHANCED_REMOTE (ERSPAN):
        ├── Extract: src_ip, dst_ip, session_id, ttl, tos
        ├── Call vpp_gre_tunnel_add_del(is_add=true):
        │     ├── type = GRE_API_TUNNEL_TYPE_ERSPAN
        │     ├── src = src_ip, dst = dst_ip
        │     ├── session_id = derived from session params
        │     └── Returns: sw_if_index of GRE tunnel
        └── Store: session_oid → { sw_if_index, type=ERSPAN }
```

**Key data:**

```cpp
struct MirrorSessionInfo {
    uint32_t sw_if_index;    // SPAN: phy port, ERSPAN: GRE tunnel
    bool is_erspan;
};

std::map<sai_object_id_t, MirrorSessionInfo> m_mirror_sessions;
```

**Remove flow:**

```
removeMirrorSession(session_oid)
  │
  ├── If is_erspan:
  │     └── vpp_gre_tunnel_add_del(is_add=false)
  │
  └── Erase from m_mirror_sessions
```

### 6.3 Port Attribute Handler: Bind/Unbind SPAN

When MirrorOrch calls `set_port_attribute()` with `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` or `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION`:

**File**: `src/sonic-sairedis/vslib/vpp/SwitchVpp.cpp` (in `setPort()` or `set_internal()`)

```cpp
case SAI_PORT_ATTR_INGRESS_MIRROR_SESSION:
case SAI_PORT_ATTR_EGRESS_MIRROR_SESSION:
{
    bool is_ingress = (attr->id == SAI_PORT_ATTR_INGRESS_MIRROR_SESSION);
    uint32_t src_sw_if_index = portOidToSwIfIndex(port_oid);

    if (attr->value.objlist.count > 0)
    {
        // Bind: enable SPAN
        sai_object_id_t session_oid = attr->value.objlist.list[0];
        uint32_t dst_sw_if_index = m_mirror_sessions[session_oid].sw_if_index;

        uint8_t state = is_ingress ? 1 : 2;  // 1=RX, 2=TX
        vpp_span_enable_disable(src_sw_if_index, dst_sw_if_index, state, false);
    }
    else
    {
        // Unbind: disable SPAN
        vpp_span_enable_disable(src_sw_if_index, 0, 0 /*disable*/, false);
    }
    break;
}
```

### 6.4 New VPP API Wrappers

**File**: `vppxlate/SaiVppXlate.h`

```c
/* SPAN (port mirroring) */
extern int vpp_span_enable_disable(uint32_t sw_if_index_from,
                                   uint32_t sw_if_index_to,
                                   uint8_t state,    /* 0=disable,1=RX,2=TX,3=both */
                                   bool is_l2);

/* GRE tunnel (for ERSPAN) */
typedef struct _vpp_gre_tunnel {
    vpp_ip_addr_t src;
    vpp_ip_addr_t dst;
    uint8_t  type;          /* 0=L3, 1=TEB, 2=ERSPAN */
    uint16_t session_id;    /* ERSPAN session ID (0-1023) */
    uint32_t instance;
    uint32_t outer_table_id;
} vpp_gre_tunnel_t;

extern int vpp_gre_tunnel_add_del(vpp_gre_tunnel_t *tunnel, bool is_add,
                                  uint32_t *sw_if_index);
```

**File**: `vppxlate/SaiVppXlate.c`

```c
int vpp_span_enable_disable(uint32_t sw_if_index_from,
                            uint32_t sw_if_index_to,
                            uint8_t state, bool is_l2)
{
    vl_api_sw_interface_span_enable_disable_t *mp;
    /* Construct message:
       mp->sw_if_index_from = htonl(sw_if_index_from)
       mp->sw_if_index_to   = htonl(sw_if_index_to)
       mp->state             = state
       mp->is_l2             = is_l2
    */
    /* Send message via VPP shared memory API */
    return 0;
}

int vpp_gre_tunnel_add_del(vpp_gre_tunnel_t *tunnel, bool is_add,
                           uint32_t *sw_if_index)
{
    vl_api_gre_tunnel_add_del_t *mp;
    /* Construct message:
       mp->is_add = is_add
       mp->tunnel.type = tunnel->type
       mp->tunnel.session_id = htons(tunnel->session_id)
       mp->tunnel.src = tunnel->src
       mp->tunnel.dst = tunnel->dst
    */
    /* Send message, receive reply with sw_if_index */
    return 0;
}
```

### 6.5 Dispatch in `SwitchVpp::create_internal()`

**File**: `src/sonic-sairedis/vslib/vpp/SwitchVpp.cpp`

```cpp
case SAI_OBJECT_TYPE_MIRROR_SESSION:
    return createMirrorSession(object_id, switch_id, attr_count, attr_list);
```

### 6.6 VPP Node Graph for Port Mirroring

#### Port Mirror with SPAN (Local)

```
 ALL packets on Ethernet0
              │
     ┌────────────────────────────┐
     │ span-input (RX)            │  VPP SPAN feature arc on device-input
     │  or span-output (TX)       │  on interface-output
     │   vlib_buffer_copy()       │
     └─────┬──────────┬───────────┘
        original    clone
           │          │
           ▼          ▼
      [normal      ┌──────────────────────┐
       forwarding] │ interface-output     │  sw_if_index[TX] = Ethernet8
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ Ethernet8-tx         │  physical NIC
                   └──────────────────────┘
```

#### Port Mirror with ERSPAN (Remote)

```
 ALL packets on Ethernet0
              │
     ┌────────────────────────────┐
     │ span-input (RX)            │  VPP SPAN feature arc
     │   vlib_buffer_copy()       │
     └─────┬──────────┬───────────┘
        original    clone
           │          │
           ▼          ▼
      [normal      ┌──────────────────────┐
       forwarding] │ interface-output     │  sw_if_index[TX] = gre0
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ gre-erspan-encap     │  + ERSPAN Type II + GRE
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ adj-l2-midchain      │  + outer IP rewrite
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ ip4-rewrite          │  + L2 header
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ {underlay}-tx        │  physical NIC to collector
                   └──────────────────────┘
```

---

## 7. Port Mirroring — Unit Tests

> **Note**: Port mirroring (SPAN) tests in sonic-mgmt are in `tests/span/test_port_mirroring.py` (4 tests). The Everflow tests (`tests/everflow/`) exercise ERSPAN mirror session creation/deletion implicitly via the `setup_mirror_session` fixture in `BaseEverflowTest`, but do not test local port-binding (SPAN) scenarios directly.

### 7.1 Capability Advertisement

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| CAP-01 | Query `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` capability | Implicit — `everflow_capabilities` fixture in `tests/everflow/conftest.py` | `set_implemented = true` |
| CAP-02 | Query `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION` capability | Implicit — `everflow_capabilities` fixture in `tests/everflow/conftest.py` | `set_implemented = true` |

### 7.2 Mirror Session Lifecycle

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| MS-01 | Create SPAN mirror session | `setup_session` fixture in `tests/span/conftest.py` — `config mirror_session span add` | `sw_if_index` resolved to destination physical port |
| MS-02 | Create ERSPAN mirror session | `setup_mirror_session` fixture in `tests/everflow/everflow_test_utilities.py` — `config mirror_session add` | GRE-ERSPAN tunnel created; `show gre tunnel` shows entry |
| MS-03 | Create ERSPAN session with IPv6 endpoints | `setup_mirror_session` with `erspan_ip_ver=6` in `tests/everflow/` | GRE tunnel with IPv6 src/dst |
| MS-04 | Remove SPAN session | `setup_session` teardown in `tests/span/conftest.py` — `config mirror_session remove` | Map entry cleared; no VPP cleanup needed |
| MS-05 | Remove ERSPAN session | `setup_mirror_session` teardown in `tests/everflow/` | GRE tunnel deleted |
| MS-06 | Verify ERSPAN session (TTL, DSCP) | Implicit — `get_expected_mirror_packet_ipv4` checks TTL/DSCP in `tests/everflow/` and needs to skip | Outer IP fields match config |

### 7.3 Port Mirror Binding

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| PM-01 | Bind SPAN session to port (RX) | `test_mirroring_rx` in `tests/span/test_port_mirroring.py` | `vpp_span_enable_disable(from, to, state=1)` called; `show interface span` shows entry |
| PM-02 | Bind SPAN session to port (TX) | `test_mirroring_tx` in `tests/span/test_port_mirroring.py` | `state=2`; span-output active |
| PM-03 | Bind SPAN session to port (BOTH) | `test_mirroring_both` in `tests/span/test_port_mirroring.py` | `state=3`; both span-input and span-output active |
| PM-04 | Bind ERSPAN session to port (RX) | Implicit — `setup_mirror_session` in `tests/everflow/` creates ERSPAN session | SPAN to GRE tunnel interface; `state=1` |
| PM-05 | Unbind mirror session from port | `setup_session` teardown in `tests/span/conftest.py` | `state=0`; `show interface span` empty |
| PM-06 | Bind session to multiple source ports | `test_mirroring_multiple_source` in `tests/span/test_port_mirroring.py` | Each source port has independent SPAN config |
| PM-07 | Bind to LAG | — (no dedicated sonic-mgmt test) | Applied to all LAG member ports |

### 7.4 Dataplane — Port Mirror

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| DP-01 | SPAN RX: Send packet to mirrored port | `test_mirroring_rx` in `tests/span/test_port_mirroring.py` | Clone arrives on monitor port; original forwarded |
| DP-02 | SPAN TX: Send packet out mirrored port | `test_mirroring_tx` in `tests/span/test_port_mirroring.py` | Clone arrives on monitor port; original forwarded |
| DP-03 | SPAN BOTH: Send packet both directions | `test_mirroring_both` in `tests/span/test_port_mirroring.py` | Both ingress and egress clones on monitor port |
| DP-04 | ERSPAN RX: Send packet to mirrored port | All dataplane tests in `tests/everflow/test_everflow_testbed.py` | Clone encapsulated with ERSPAN headers; sent to collector |
| DP-05 | SPAN clone is raw (no encap) | `test_mirroring_rx` — `verify_packet` checks byte-identical clone | Clone on monitor port is byte-identical to original |
| DP-06 | ERSPAN Type II header verification | `BaseEverflowTest.get_expected_mirror_packet_ipv4` in `tests/everflow/` | GRE proto=0x88BE, session_id matches, seq_num increments |
| DP-07 | ERSPAN outer IP header verification | `BaseEverflowTest.get_expected_mirror_packet_ipv4` in `tests/everflow/` | src_ip, dst_ip, TTL, DSCP match config |

### 7.5 Error Scenarios

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| ERR-01 | Exceed max mirror sessions | — (no dedicated sonic-mgmt test) | Returns `SAI_STATUS_INSUFFICIENT_RESOURCES` |

---

# Phase 2: Everflow (ACL-Based Mirroring)

## 8. Everflow — Feature Description

Everflow extends mirroring by using ACL rules to selectively mirror only packets matching specific criteria (5-tuple: src/dst IP, protocol, src/dst port). Unlike port mirroring which copies all traffic, Everflow only mirrors interesting flows.

### 8.1 How It Works

```
                           SONiC Control Plane
 ┌─────────────────┐   ┌───────────────┐   ┌──────────────┐
 │  CONFIG_DB      │──>│  MirrorOrch   │──>│  SAI API     │
 │  MIRROR_SESSION │   │  AclOrch      │   │  mirror +    │
 │  ACL_TABLE      │   │               │   │  acl calls   │
 │  ACL_RULE       │   └───────────────┘   └──────┬───────┘
 └─────────────────┘                              │
                                                  ▼
                              VPP Dataplane (saivpp)
 ┌──────────────────────────────────────────────────────────┐
 │  Ingress / Egress                                        │
 │  ┌─────────┐    ┌──────────────┐     ┌───────────────┐   │
 │  │ Packet  │───>│  ACL Match   │────>│ Original pkt  │   │
 │  │         │    │  (5-tuple)   │     │ continues     │   │
 │  └─────────┘    └──────┬───────┘     └───────────────┘   │
 │                        │ clone (if match)                │
 │                        ▼                                 │
 │               ┌──────────────────┐                       │
 │               │ interface-output │                       │
 │               │ (mirror_sw_if)   │                       │
 │               └────────┬─────────┘                       │
 │                   ┌────┴────┐                            │
 │                   ▼         ▼                            │
 │             ┌──────────┐ ┌──────────────────┐            │
 │             │ SPAN:    │ │ ERSPAN:          │            │
 │             │ phy-tx   │ │ gre-erspan-encap │            │
 │             │ (local)  │ │ → ip4-rewrite    │            │
 │             │          │ │ → phy-tx         │            │
 │             └──────────┘ └──────────────────┘            │
 └──────────────────────────────────────────────────────────┘
```

Key difference from port mirroring:
- Port mirroring: VPP SPAN module clones ALL port traffic (no VPP change needed)
- Everflow: VPP ACL plugin must clone SELECTED traffic (requires VPP ACL plugin patch)

---

## 9. Everflow — SONiC Configuration

### 9.1 ACL_TABLE (type=MIRROR)

```json
{
    "ACL_TABLE": {
        "EVERFLOW": {
            "type": "MIRROR",
            "policy_desc": "Everflow ingress mirror",
            "ports": ["Ethernet0", "Ethernet4"]
        }
    }
}
```

Table types: `MIRROR` (IPv4), `MIRRORV6` (IPv6)

### 9.2 ACL_RULE with MIRROR_ACTION

```json
{
    "ACL_RULE": {
        "EVERFLOW|rule1": {
            "PRIORITY": "100",
            "SRC_IP": "192.168.1.0/24",
            "DST_IP": "10.10.0.0/16",
            "IP_PROTOCOL": "6",
            "L4_DST_PORT": "443",
            "MIRROR_INGRESS_ACTION": "erspan0"
        }
    }
}
```

| Field | Description |
|---|---|
| MIRROR_INGRESS_ACTION | Mirror session name; clone ingress-matched packets |
| MIRROR_EGRESS_ACTION | Mirror session name; clone egress-matched packets |

The referenced mirror session (`erspan0`) is the same `MIRROR_SESSION` table used for port mirroring (Phase 1). Sessions are shared between port mirroring and Everflow.

### 9.3 Supported Match Qualifiers

The sonic-mgmt Everflow test suite exercises the following match qualifiers. All must be supported:

| Qualifier | CONFIG_DB Field | SAI ACL Field | VPP ACL Rule Field |
|---|---|---|---|
| Source IP (v4) | `SRC_IP` | `SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP` | `src_prefix` |
| Destination IP (v4) | `DST_IP` | `SAI_ACL_ENTRY_ATTR_FIELD_DST_IP` | `dst_prefix` |
| Source IPv6 | `SRC_IPV6` | `SAI_ACL_ENTRY_ATTR_FIELD_SRC_IPV6` | `src_prefix` |
| Destination IPv6 | `DST_IPV6` | `SAI_ACL_ENTRY_ATTR_FIELD_DST_IPV6` | `dst_prefix` |
| IP Protocol / Next Header | `IP_PROTOCOL` | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` | `proto` |
| L4 Source Port | `L4_SRC_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_SRC_PORT` | `srcport_or_icmptype_first/last` |
| L4 Destination Port | `L4_DST_PORT` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT` | `dstport_or_icmpcode_first/last` |
| L4 Source Port Range | `L4_SRC_PORT_RANGE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_RANGE_TYPE` | `srcport_or_icmptype_first/last` |
| L4 Dest Port Range | `L4_DST_PORT_RANGE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_RANGE_TYPE` | `dstport_or_icmpcode_first/last` |
| TCP Flags | `TCP_FLAGS` | `SAI_ACL_ENTRY_ATTR_FIELD_TCP_FLAGS` | `tcp_flags_mask/value` |
| DSCP | `DSCP` | `SAI_ACL_ENTRY_ATTR_FIELD_DSCP` | (IP header match) |
| ICMPv6 Type | `ICMPV6_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMPV6_TYPE` | `srcport_or_icmptype_first/last` |
| ICMPv6 Code | `ICMPV6_CODE` | `SAI_ACL_ENTRY_ATTR_FIELD_ICMPV6_CODE` | `dstport_or_icmpcode_first/last` |
| IP Type | `IP_TYPE` | `SAI_ACL_ENTRY_ATTR_FIELD_ACL_IP_TYPE` | (pre-filter) |

**Note**: The existing saivpp ACL implementation (`SwitchVppAcl.cpp`) already translates all these match qualifiers into VPP ACL rules. No additional match qualifier work is needed for Everflow — only the **mirror action** is missing.

### 9.4 MIRROR_DSCP Table (Policer)

Sonic-mgmt tests a `MIRROR_DSCP` ACL table type with an attached policer for rate-limiting mirror traffic:

```json
{
    "ACL_TABLE": {
        "EVERFLOW_DSCP": {
            "type": "MIRROR_DSCP",
            "policy_desc": "DSCP based everflow",
            "ports": ["Ethernet0"]
        }
    },
    "POLICER": {
        "TEST_POLICER": {
            "meter_type": "packets",
            "mode": "sr_tcm",
            "cir": "100",
            "cbs": "100",
            "red_packet_action": "drop"
        }
    }
}
```

Mirror session is created with `--policer TEST_POLICER`. This rate-limits mirrored traffic to the CIR (committed information rate).

**VPP support**: VPP policer integration with ACL mirror is out of initial scope. The `test_everflow_dscp_with_policer` test may be skipped initially.

### 9.5 Per-Interface ACL Binding

Sonic-mgmt `test_everflow_per_interface` tests that Everflow ACLs can be bound to **specific interfaces** using `input_interface` qualifier. Packets ingress from bound ports are mirrored; packets from unbound ports are not.

This is already supported — AclOrch binds ACL tables to specific ports/LAGs via `SAI_PORT_ATTR_INGRESS_ACL` / `SAI_LAG_ATTR_INGRESS_ACL`.

---

## 10. Everflow — SAI API Calls

### 10.1 Create ACL Table (type=MIRROR)

```c
sai_attribute_t tbl_attrs[] = {
    { SAI_ACL_TABLE_ATTR_ACL_STAGE, .value.s32 = SAI_ACL_STAGE_INGRESS },
    { SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST,
      .value.objlist = { 1, (sai_object_id_t[]){ SAI_ACL_BIND_POINT_TYPE_PORT } } },
    { SAI_ACL_TABLE_ATTR_FIELD_SRC_IP,      .value.booldata = true },
    { SAI_ACL_TABLE_ATTR_FIELD_DST_IP,      .value.booldata = true },
    { SAI_ACL_TABLE_ATTR_FIELD_IP_PROTOCOL, .value.booldata = true },
    { SAI_ACL_TABLE_ATTR_FIELD_L4_SRC_PORT, .value.booldata = true },
    { SAI_ACL_TABLE_ATTR_FIELD_L4_DST_PORT, .value.booldata = true },
};
sai_acl_api->create_acl_table(&table_oid, switch_id, 7, tbl_attrs);
```

### 10.2 Create ACL Entry with Mirror Action

```c
sai_attribute_t entry_attrs[] = {
    { SAI_ACL_ENTRY_ATTR_TABLE_ID, .value.oid = table_oid },
    { SAI_ACL_ENTRY_ATTR_PRIORITY, .value.u32 = 100 },
    { SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP,
      .value.aclfield = { .enable = true, .data.ip4 = src, .mask.ip4 = mask } },
    /* ... other match fields ... */

    /* Mirror action — references the mirror session from Phase 1 */
    { SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS,
      .value.aclaction = {
          .enable = true,
          .parameter.objlist = { 1, &session_oid }
      }
    },
};
sai_acl_api->create_acl_entry(&entry_oid, switch_id, N, entry_attrs);
```

### 10.3 Bind ACL Table to Port

```c
sai_attribute_t port_attr = {
    SAI_PORT_ATTR_INGRESS_ACL, .value.oid = table_oid
};
sai_port_api->set_port_attribute(port_oid, &port_attr);
```

---

## 11. Everflow — VPP Gap Analysis and Proposed Changes

### 11.1 Gap Analysis

The VPP ACL plugin (`src/plugins/acl/`) has full 5-tuple matching with port ranges and per-rule counters, but no deferred Everflow handoff to a post-rewrite mirror stage:

| Gap | Location | Detail |
|---|---|---|
| No ACL mirror action | `acl_types.api` | Only `DENY=0`, `PERMIT=1`, `PERMIT_REFLECT=2` |
| No mirror destination in rule | `types.h` | `acl_rule_t` has no `mirror_sw_if_index` field |
| No deferred mirror metadata handoff | `dataplane_node.c` | Action dispatch lacks a path to stash mirror destination metadata for a later egress node. |
| No mirror action in saivpp ACL | `SwitchVppAcl.cpp` | No handling of `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS/EGRESS` |

**Why the change must start in the ACL plugin**: `match_acl_in_index` and `match_rule_index` are local to `dataplane_node.c`, so the ACL plugin must transfer mirror intent into packet metadata. The clone itself is then performed later by `sonic-ext-egress-mirror` on `interface-output` to obtain post-rewrite wire form.

**Why global arc lifecycle control is needed**: Late clone is only used by deferred egress mirror actions. The `sonic-ext-egress-mirror` node should be added to the `interface-output` arc globally when the first active `MIRROR_EGRESS` ACL action is configured, and removed when the last active `MIRROR_EGRESS` action is deleted or disabled.

### 11.2 Change 1: New Action Value

**File**: `src/plugins/acl/acl_types.api`

```diff
 enum acl_action : u8
 {
   ACL_ACTION_API_DENY = 0,
   ACL_ACTION_API_PERMIT = 1,
   ACL_ACTION_API_PERMIT_REFLECT = 2,
+  ACL_ACTION_API_PERMIT_MIRROR = 3,
 };
```

### 11.3 Change 2: Mirror Destination Field

**File**: `src/plugins/acl/acl_types.api`

```diff
 typedef acl_rule
 {
   vl_api_acl_action_t is_permit;
+  vl_api_interface_index_t mirror_sw_if_index;
   vl_api_prefix_t src_prefix;
   ...
 };
```

**File**: `src/plugins/acl/types.h`

```diff
 typedef struct
 {
   u8 is_permit;
+  acl_mirror_action_t mirror_action;
   u8 is_ipv6;
   ...
 } acl_rule_t;
```

Keep the API payload as a single `u32` for compatibility, but represent it in
`acl_rule_t` with a dedicated mirror-action struct:

```c
typedef struct
{
    u32 raw;
} acl_mirror_action_t;

#define ACL_MIRROR_SW_IF_BITS        28u
#define ACL_MIRROR_FLAGS_BITS         4u
#define ACL_MIRROR_SW_IF_MASK         ((1u << ACL_MIRROR_SW_IF_BITS) - 1u)
#define ACL_MIRROR_FLAGS_SHIFT        ACL_MIRROR_SW_IF_BITS
#define ACL_MIRROR_FLAGS_MASK         (0xfu << ACL_MIRROR_FLAGS_SHIFT)

#define ACL_MIRROR_F_DEFERRED         (1u << 0)

/* encoded value in acl_mirror_action_t::raw */
/* [27:0] mirror destination sw_if_index */
/* [31:28] mirror flags                  */

static_always_inline u32
acl_mirror_action_get_sw_if_index (acl_mirror_action_t m)
{
    return m.raw & ACL_MIRROR_SW_IF_MASK;
}

static_always_inline u8
acl_mirror_action_get_flags (acl_mirror_action_t m)
{
    return (u8) ((m.raw & ACL_MIRROR_FLAGS_MASK) >> ACL_MIRROR_FLAGS_SHIFT);
}
```

`acl_rule_t` uses this struct for mirror action metadata. `SwitchVppAcl.cpp`
sets `ACL_MIRROR_F_DEFERRED` only for `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS`.
`SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` keeps flags clear and clones
immediately in `dataplane_node.c`.

### 11.4 Change 3: Hybrid Clone/Mark Logic in `dataplane_node.c`

Insert after `next[0] = action ? next[0] : 0;` (line ~536):

```c
if (PREDICT_FALSE (action == 3))   /* ACL_ACTION_API_PERMIT_MIRROR */
  {
    pkts_acl_permit++;

    acl_rule_t *mir_rule = &(am->acls[match_acl_in_index].rules[match_rule_index]);
        acl_mirror_action_t mirror_action = mir_rule->mirror_action;
        u32 mirror_sw_if_index = acl_mirror_action_get_sw_if_index(mirror_action);
        u8 flags = acl_mirror_action_get_flags(mirror_action);
        u8 defer_mirror = (flags & ACL_MIRROR_F_DEFERRED) != 0;

    if (mirror_sw_if_index != ~0)
      {
                if (PREDICT_TRUE (defer_mirror))
          {
                        sonic_ext_buffer_opaque_t *seb = sonic_ext_buffer (b[0]);
                        seb->magic = SONIC_EXT_BUFFER_MAGIC;
                        seb->mirror_sw_if_index = mirror_sw_if_index;
                    }
                else
                    {
                        /* Immediate clone path (used by MIRROR_INGRESS action) */
                        vlib_buffer_t *clone = vlib_buffer_copy (vm, b[0]);
                        if (PREDICT_TRUE (clone != NULL))
                            {
                                vnet_buffer (clone)->sw_if_index[VLIB_TX] = mirror_sw_if_index;
                                clone->flags |= VNET_BUFFER_F_SPAN_CLONE;
                                vnet_main_t *vnm = vnet_get_main ();
                                vlib_frame_t *f = vnet_get_frame_to_sw_interface (vnm, mirror_sw_if_index);
                                u32 *to_next = vlib_frame_vector_args (f);
                                to_next += f->n_vectors;
                                to_next[0] = vlib_get_buffer_index (vm, clone);
                                f->n_vectors++;
                            }
          }
      }
  }
```

### 11.5 Change 4: ACL Rule Validation

**File**: `src/plugins/acl/acl.c`

```c
if (r->is_permit == 3 &&
        acl_mirror_action_get_sw_if_index(r->mirror_action) == ~0)
  return VNET_API_ERROR_INVALID_VALUE;
```

### 11.6 saivpp Changes

**File**: `vppxlate/SaiVppXlate.h`

```diff
 typedef enum  {
     VPP_ACL_ACTION_API_DENY = 0,
     VPP_ACL_ACTION_API_PERMIT = 1,
     VPP_ACL_ACTION_API_PERMIT_STFULL = 2,
+    VPP_ACL_ACTION_API_PERMIT_MIRROR = 3,
 } vpp_acl_action_e;

 typedef struct _vpp_acl_rule {
     vpp_acl_action_e action;
+    uint32_t mirror_action; /* 4-bit flags + 28-bit sw_if_index */
     vpp_ip_addr_t src_prefix;
     ...
 } vpp_acl_rule_t;
```

**File**: `SwitchVppAcl.cpp` — handle mirror action:

```cpp
case SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS:
{
    if (value->aclaction.enable)
    {
        rule->action = VPP_ACL_ACTION_API_PERMIT_MIRROR;
        sai_object_id_t session_oid = value->aclaction.parameter.objlist.list[0];
        uint32_t sw_if_index = lookup_mirror_session_sw_if_index(session_oid);
        rule->mirror_action =
            (sw_if_index & ACL_MIRROR_SW_IF_MASK);
    }
    break;
}
case SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS:
{
    if (value->aclaction.enable)
    {
        rule->action = VPP_ACL_ACTION_API_PERMIT_MIRROR;
        sai_object_id_t session_oid = value->aclaction.parameter.objlist.list[0];
        uint32_t sw_if_index = lookup_mirror_session_sw_if_index(session_oid);
        rule->mirror_action =
            (sw_if_index & ACL_MIRROR_SW_IF_MASK) |
            (ACL_MIRROR_F_DEFERRED << ACL_MIRROR_FLAGS_SHIFT);
    }
    break;
}
```

---

## 12. Everflow — SAI-VPP Implementation

### 12.1 Shared Components with Phase 1

Everflow reuses the mirror session infrastructure from Phase 1:
- `SwitchVppMirror.cpp` — same mirror session create/remove (SPAN and ERSPAN)
- `vpp_gre_tunnel_add_del()` — same GRE tunnel management
- `m_mirror_sessions` map — same session_oid → sw_if_index lookup

### 12.2 New Components (Phase 2 only)

| Component | Description |
|---|---|
| VPP ACL plugin patch | `acl_types.api`, `types.h`, `dataplane_node.c`, `acl.c` (defer-flag decode + metadata write) |
| sonic_ext egress node | `sonic-ext-egress-mirror` clones late on `interface-output` from metadata; presence on arc is controlled globally by active MIRROR_EGRESS actions |
| `SwitchVppAcl.cpp` modification | Handle `ACTION_MIRROR_INGRESS/EGRESS` |
| `SaiVppXlate.h/c` modification | `VPP_ACL_ACTION_API_PERMIT_MIRROR`, encoded `mirror_action` (4-bit flags + 28-bit sw_if_index) in rule |

### 12.2.1 `sonic_ext_buffer_opaque_t` Extension

Deferred egress mirroring stores mirror destination metadata in per-buffer
`sonic_ext` opaque storage:

```c
typedef struct
{
    u32 magic;
    u32 orig_rx_sw_if_index;
    u32 orig_vlan_tag;

    /* Added for deferred egress mirror.
     * ~0 means no pending mirror action. */
    u32 mirror_sw_if_index;
} sonic_ext_buffer_opaque_t;
```

Comment: as a future optimization, we can reduce `sonic_ext_buffer_opaque_t`
size by storing a compact mirror session id in the buffer and using a mirror
session table (`session_id -> mirror_sw_if_index`) in `sonic_ext`. The mapped
`mirror_sw_if_index` can point to either a SPAN destination interface or an
ERSPAN GRE tunnel interface.

### 12.3 Statistics

ACL per-rule counters work for all action types including mirror. The stats segment path `/acl/{N}/matches` increments for every matched rule regardless of action. No changes needed.

### 12.4 Global `interface-output` Arc Lifecycle

To avoid unnecessary per-packet overhead when deferred egress mirroring is not in use,
`sonic-ext-egress-mirror` is managed with a global active-action refcount:

1. On ACL entry create/enable for `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS`, increment `active_egress_mirror_actions`.
2. If transition is `0 -> 1`, enable `sonic-ext-egress-mirror` on `interface-output` arc globally.
3. On ACL entry delete/disable for `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS`, decrement the refcount.
4. If transition is `1 -> 0`, disable `sonic-ext-egress-mirror` from `interface-output` arc globally.

`SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` does not affect this refcount because it
clones immediately in ACL node and does not require late-clone execution.

### 12.5 Placement in `interface-output` Arc

`sonic-ext-egress-mirror` must be placed at the tail of the `interface-output`
feature arc for the original packet path:

1. After normal forwarding graph processing, including route/adjacency rewrite.
2. After optional tunnel encapsulation nodes (for example GRE/ERSPAN/VXLAN paths).
3. Before `sonic-ext-aggr-tap-redirect` (which may consume/reset sonic_ext cookie metadata).
4. Before final TX handoff (`device-tx` or tunnel transmit node).

This ordering ensures the mirrored copy reflects the final wire-form packet
(post-rewrite, post-encapsulation), while still allowing the original packet to
continue on the same egress path.

Example node registration placement:

```c
VNET_FEATURE_INIT (sonic_ext_egress_mirror, static) = {
    .arc_name = "interface-output",
    .node_name = "sonic-ext-egress-mirror",

    /* Run after rewrite / encap work is done */
    .runs_after = VNET_FEATURES (
        "ip4-rewrite",
        "ip6-rewrite",
        "mpls-output",
        "gre-erspan-encap"
    ),

    /* Must run before aggr-tap redirect, which can clear seb->magic */
    .runs_before = VNET_FEATURES (
        "sonic-ext-aggr-tap-redirect",
        "interface-output-end"
    ),
};
```

If a platform uses different egress node names, keep the same intent: register
`sonic-ext-egress-mirror` after rewrite/encap features, before any node that
consumes/resets sonic_ext metadata (for example aggr-tap redirect), and then
immediately before final transmit handoff.

### 12.6 Re-cloning Prevention

To prevent clone-of-clone recursion when mirrored packets re-enter
`interface-output`, the egress mirror node resets `mirror_sw_if_index` to `~0`
on **both the original and the clone** immediately after the clone is created.
The fast-path entry check bails out when `mirror_sw_if_index == ~0`, so neither
packet can trigger a second clone.

Reference behavior:

```c
if (seb->magic != SONIC_EXT_BUFFER_MAGIC ||
    seb->mirror_sw_if_index == ~0)
{
    goto passthrough;
}

u32 dst_sw_if_index = seb->mirror_sw_if_index;

/* Clear on original before clone so the clone inherits ~0 already */
seb->mirror_sw_if_index = ~0;

clone = vlib_buffer_copy(vm, b0);
if (clone)
{
    /* clone->mirror_sw_if_index is already ~0 (copied from original above) */
    enqueue_clone_to_mirror_tx(clone, dst_sw_if_index);
}
```

By clearing `mirror_sw_if_index` on the original **before** calling
`vlib_buffer_copy`, the cloned buffer inherits `~0` automatically through
VPP's `opaque2` memcpy, so no separate per-clone fixup is needed.

---

## 13. Everflow — VPP Node Graphs

### 13.1 Ingress ACL + Egress Mirror (deferred)

When at least one `MIRROR_EGRESS` action is active, `sonic-ext-egress-mirror` is
present on `interface-output` arc globally and executes late clone for deferred
traffic.

```
 Packet arrives on Ethernet0
     ┌────────────────────────────┐
     │ acl-plugin-in-ip4-fa       │  ACL match, action=3
 │   writes seb->mirror_sw_if_index  │  no immediate clone
     └──────────────┬────────────────┘
                    ▼
      [ip4-lookup] → [ip4-rewrite / encap]
                    ▼
           interface-output arc
                    ▼
     ┌────────────────────────────┐
     │ sonic-ext-egress-mirror    │  clones post-rewrite packet
     └─────┬──────────┬───────────┘
        original    clone
           │          ▼
           │  interface-output → mirror destination
           ▼
      original forwarded
```

### 13.2 Ingress ERSPAN (deferred)

```
 Packet arrives on Ethernet0
     ┌────────────────────────────┐
     │ acl-plugin-in-ip4-fa       │  ACL match, action=3
 │   writes seb->mirror_sw_if_index  │  no immediate clone
     └──────────────┬────────────────┘
                    ▼
      [ip4-lookup] → [vxlan/gre/ipip encap] → [ip4-rewrite]
                    ▼
           interface-output arc
                    ▼
     ┌────────────────────────────┐
     │ sonic-ext-egress-mirror    │  clone now includes tunnel+rewrite
     └─────┬──────────┬───────────┘
        original    clone→mirror destination
```

### 13.3 Egress SPAN / ERSPAN

`acl-plugin-out-ip4-fa` sets deferred metadata for MIRROR_EGRESS and does not
clone when deferred bit is set. `sonic-ext-egress-mirror` then clones on
`interface-output`.

`acl-plugin-in-ip4-fa` for MIRROR_INGRESS keeps `ACL_MIRROR_F_DEFERRED` clear,
so clone happens immediately in the ACL node.

For **egress ACL + egress mirror**, clone timing is still late egress: the
packet is mirrored after rewrite/encap as observed at `interface-output`.

Re-cloning is blocked in `sonic-ext-egress-mirror` by clearing
`mirror_sw_if_index` to `~0` on the original **before** `vlib_buffer_copy`;
the clone therefore inherits `~0` and cannot trigger a second clone on
re-entry.

### 13.4 Node Graph Summary

| Scenario | Clone Origin | Mirror Dest | Clone Path | Nodes |
|---|---|---|---|---|
| Ingress SPAN (`MIRROR_INGRESS_ACTION`) | `acl-plugin-in-ip4-fa` (clone) | phy port | interface-output → device-tx | 3 |
| Ingress ERSPAN (`MIRROR_INGRESS_ACTION`) | `acl-plugin-in-ip4-fa` (clone) | GRE tunnel | interface-output → gre-erspan-encap → adj-l2-midchain → ip4-rewrite → device-tx | 6 |
| Egress SPAN | `acl-plugin-out-ip4-fa` (mark) | phy port | ...rewrite... → `sonic-ext-egress-mirror` → device-tx | 4+ |
| Egress ERSPAN | `acl-plugin-out-ip4-fa` (mark) | GRE tunnel | ...rewrite/encap... → `sonic-ext-egress-mirror` → tunnel tx | 6+ |

The ACL plugin uses a shared function (`acl_fa_inner_node_fn`) for input and
output; MIRROR_INGRESS clones immediately, while MIRROR_EGRESS records metadata
and relies on `sonic-ext-egress-mirror` for late clone execution.

---

## 14. Everflow — Unit Tests

### 14.1 ACL with Mirror Action (SAI-level)

These are saivpp unit tests with no direct sonic-mgmt equivalents. They validate the SAI-to-VPP translation.

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| ACL-01 | Create ACL rule with `ACTION_MIRROR_INGRESS` | Implicit via `setup_acl_table` fixture | VPP rule has `is_permit=3`; `mirror_action.flags` has deferred bit clear |
| ACL-02 | Create ACL rule with `ACTION_MIRROR_EGRESS` | Implicit via `setup_acl_table` fixture | VPP rule bound to output direction; `mirror_action.flags` has deferred bit set |
| ACL-03 | ACL rule with both mirror + packet action | — | Packet forwarded and cloned |
| ACL-04 | Bind MIRROR ACL table to port | Implicit via `setup_acl_table` fixture | `show acl-plugin interface` shows ACL |
| ACL-05 | Unbind MIRROR ACL from port | Implicit via `setup_acl_table` teardown | ACL removed from interface |
| ACL-06 | Multiple mirror rules, different sessions | — | Each rule references different `sw_if_index` |
| ACL-07 | Delete ACL entry with mirror action | Implicit via `remove_acl_rule_config` | Rule removed; no orphan state |
| ACL-08 | First `ACTION_MIRROR_EGRESS` configured | — | `sonic-ext-egress-mirror` is added to `interface-output` arc globally |
| ACL-09 | Last `ACTION_MIRROR_EGRESS` removed | — | `sonic-ext-egress-mirror` is removed from `interface-output` arc globally |
| ACL-10 | Mirrored clone re-enters `interface-output` | — | `mirror_sw_if_index` is `~0` on clone; node passes through without cloning again |

### 14.2 Dataplane — IPv4 Match Qualifiers

Maps to `_run_everflow_test_scenarios()` in sonic-mgmt `test_everflow_testbed.py`. Called from all 4 IPv4 test classes (see Section 14.7). Each row is a packet sent within `_run_everflow_test_scenarios()`.

| Test Case | Match Qualifier | sonic-mgmt Test | Expected Result |
|---|---|---|---|
| DP-01 | Source IP | `EverflowIPv4Tests._run_everflow_test_scenarios` `(src ip)` | Mirrored; original forwarded |
| DP-02 | Destination IP | `EverflowIPv4Tests._run_everflow_test_scenarios` `(dst ip)` | Mirrored; original forwarded |
| DP-03 | L4 Source Port | `EverflowIPv4Tests._run_everflow_test_scenarios` `(l4 src port)` | Mirrored |
| DP-04 | L4 Destination Port | `EverflowIPv4Tests._run_everflow_test_scenarios` `(l4 dst port)` | Mirrored |
| DP-05 | IP Protocol | `EverflowIPv4Tests._run_everflow_test_scenarios` `(ip protocol)` | Mirrored |
| DP-06 | TCP Flags | `EverflowIPv4Tests._run_everflow_test_scenarios` `(tcp flags)` | Mirrored |
| DP-07 | L4 Source Port Range | `EverflowIPv4Tests._run_everflow_test_scenarios` `(l4 src range)` | Mirrored |
| DP-08 | L4 Dest Port Range | `EverflowIPv4Tests._run_everflow_test_scenarios` `(l4 dst range)` | Mirrored |
| DP-09 | DSCP | `EverflowIPv4Tests._run_everflow_test_scenarios` `(dscp)` | Mirrored |
| DP-10 | Non-matching traffic | `EverflowIPv4Tests._run_everflow_test_scenarios` `expect_recv=False` | Forwarded normally; no clone |

### 14.3 Dataplane — IPv6 Match Qualifiers

Maps to individual test functions in `tests/everflow/test_everflow_ipv6.py`. Run by `TestIngressEverflowIPv6` and `TestEgressEverflowIPv6`.

| Test Case | Match Qualifier | sonic-mgmt Test Function | Expected Result |
|---|---|---|---|
| V6-01 | Source IPv6 | `EverflowIPv6Tests::test_src_ipv6_mirroring` | Mirrored |
| V6-02 | Destination IPv6 | `EverflowIPv6Tests::test_dst_ipv6_mirroring` | Mirrored |
| V6-03 | Next Header (proto) | `EverflowIPv6Tests::test_next_header_mirroring` | Mirrored |
| V6-04 | L4 Source Port | `EverflowIPv6Tests::test_l4_src_port_mirroring` | Mirrored |
| V6-05 | L4 Destination Port | `EverflowIPv6Tests::test_l4_dst_port_mirroring` | Mirrored |
| V6-06 | L4 Src Port Range | `EverflowIPv6Tests::test_l4_src_port_range_mirroring` | Mirrored |
| V6-07 | L4 Dst Port Range | `EverflowIPv6Tests::test_l4_dst_port_range_mirroring` | Mirrored |
| V6-08 | TCP Flags | `EverflowIPv6Tests::test_tcp_flags_mirroring` | Mirrored |
| V6-09 | DSCP | `EverflowIPv6Tests::test_dscp_mirroring` | Mirrored |
| V6-10 | Bidirectional L4 ranges | `EverflowIPv6Tests::test_l4_range_mirroring` | Mirrored |
| V6-11 | TCP SYN→SYN-ACK | `EverflowIPv6Tests::test_tcp_response_mirroring` | Both directions mirrored |
| V6-12 | TCP application (443) | `EverflowIPv6Tests::test_tcp_application_mirroring` | Client+server mirrored |
| V6-13 | UDP application (514) | `EverflowIPv6Tests::test_udp_application_mirroring` | Client+server mirrored |
| V6-14 | Protocol-agnostic | `EverflowIPv6Tests::test_any_protocol` | All protocols mirrored |
| V6-15 | Transport-agnostic port | `EverflowIPv6Tests::test_any_transport_protocol` | TCP+UDP mirrored on same ports |
| V6-16 | Invalid TCP rule | `EverflowIPv6Tests::test_invalid_tcp_rule` | SAI does not crash |
| V6-17 | Source subnet (/20) | `EverflowIPv6Tests::test_source_subnet` | Mirrored |
| V6-18 | Dest subnet (/20) | `EverflowIPv6Tests::test_dest_subnet` | Mirrored |
| V6-19 | Both subnets | `EverflowIPv6Tests::test_both_subnets` | Mirrored |
| V6-20 | Fuzzy subnets (non-standard) | `EverflowIPv6Tests::test_fuzzy_subnets` | Mirrored |
| V6-21 | ICMPv6 Type | `EverflowIPv6Tests::test_icmpv6_type` | Mirrored |
| V6-22 | ICMPv6 Code | `EverflowIPv6Tests::test_icmpv6_code` | Mirrored |
| V6-23 | IP_TYPE=ANY | `EverflowIPv6Tests::test_ip_type_any` | Mirrored |
| V6-24 | IP_TYPE=IP | `EverflowIPv6Tests::test_ip_type_ip` | Mirrored |
| V6-25 | IP_TYPE=IPv6ANY | `EverflowIPv6Tests::test_ip_type_ipv6any` | Mirrored |

### 14.4 Dataplane — ERSPAN Encapsulation

Encapsulation is verified implicitly by all `send_and_check_mirror_packets()` calls in sonic-mgmt via `get_expected_mirror_packet()` which builds an expected GRE-encapsulated packet.

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| ENC-01 | ERSPAN Type II header verify | `BaseEverflowTest.get_expected_mirror_packet_ipv4` — checks `GRE.proto` | GRE proto=0x88BE, session_id, seq_num |
| ENC-02 | IPv4 ERSPAN outer IP header verify | `BaseEverflowTest.get_expected_mirror_packet_ipv4` — checks src/dst/ttl/dscp | src_ip, dst_ip, TTL, DSCP match config |
| ENC-03 | IPv6 ERSPAN outer IP header verify | `BaseEverflowTest.get_expected_mirror_packet_ipv6` — checks src/dst/hlim/tc | src_ipv6, dst_ipv6, hop_limit, TC match config |
| ENC-04 | Mirrored packet no VLAN tag | `test_everflow_packet_format` in `test_everflow_per_interface.py` | no Dot1Q |
| ENC-05 | Mirrored packet no MPLS | `test_everflow_packet_format` in `test_everflow_per_interface.py` | No unexpected MPLS encap |
| ENC-06 | Mirrored packet no VXLAN | `test_everflow_packet_format` in `test_everflow_per_interface.py` | No unexpected VXLAN encap |
Note: ttl/dscp/hlim/tc are not support in vpp
### 14.5 Routing — Mirror Session Destination

Maps to routing-related tests in `tests/everflow/test_everflow_testbed.py`.

| Test Case | Description | sonic-mgmt Test Function | Expected Result |
|---|---|---|---|
| RT-01 | Resolved route to session dst IP | `EverflowIPv4Tests::test_everflow_basic_forwarding` | Mirrored traffic sent to nexthop |
| RT-02 | Unresolved route supersedes but doesn't override | `EverflowIPv4Tests::test_everflow_basic_forwarding` | Traffic still uses resolved route |
| RT-03 | Better (LPM) route added | `EverflowIPv4Tests::test_everflow_basic_forwarding` | Switches to new nexthop |
| RT-04 | Better route removed | `EverflowIPv4Tests::test_everflow_basic_forwarding` | Falls back to original nexthop |
| RT-05 | Neighbor MAC change for nexthop | `EverflowIPv4Tests::test_everflow_neighbor_mac_change` | Session uses updated MAC |
| RT-06 | ECMP: remove unused nexthop | `EverflowIPv4Tests::test_everflow_remove_unused_ecmp_next_hop` | Traffic unaffected |
| RT-07 | ECMP: remove used nexthop | `EverflowIPv4Tests::test_everflow_remove_used_ecmp_next_hop` | Shifts to remaining nexthop(s) |

### 14.6 Advanced Scenarios

| Test Case | Description | sonic-mgmt Test Function | Expected Result |
|---|---|---|---|
| ADV-01 | Mirror with background traffic | `EverflowIPv4Tests::test_everflow_frwd_with_bkg_trf` | Mirror works correctly; no interference |
| ADV-02 | Recircle port queue assignment | `EverflowIPv4Tests::test_everflow_fwd_recircle_port_queue_check` |vpp doesn't support queue. must skip |
| ADV-03 | DSCP with policer (rate-limit) | `EverflowIPv4Tests::test_everflow_dscp_with_policer` | CIR enforced within tolerance (not supported. skip)|
| ADV-04 | Multi-binding ACL (dualtor) | `EverflowIPv4Tests::test_everflow_multi_binding_acl` | Mirror works across bindings |
| ADV-05 | Per-interface ACL binding | `test_everflow_per_interface` in `test_everflow_per_interface.py` | Only bound ports mirrored |
| ADV-06 | Unselected port not mirrored | `test_everflow_per_interface` in `test_everflow_per_interface.py` | No mirror from unbound ports |

### 14.7 ACL Stage × Mirror Direction Matrix

Sonic-mgmt runs the full test suite across 4 class variants (IPv4) and 2 variants (IPv6):

| Test Class | ACL Stage | Mirror Direction | sonic-mgmt Class |
|---|---|---|---|
| IPv4 Ingress/Ingress | Ingress | Ingress | `TestEverflowV4IngressAclIngressMirror` |
| IPv4 Ingress/Egress | Ingress | Egress | `TestEverflowV4IngressAclEgressMirror` |
| IPv4 Egress/Ingress | Egress | Ingress | `TestEverflowV4EgressAclIngressMirror` |
| IPv4 Egress/Egress | Egress | Egress | `TestEverflowV4EgressAclEgressMirror` |
| IPv6 Ingress | Ingress | Ingress | `TestIngressEverflowIPv6` |
| IPv6 Egress | Egress | Egress | `TestEgressEverflowIPv6` |

Each of these classes runs all the dataplane tests above — the VPP ACL plugin patch must handle both ingress and egress ACL stages with both ingress and egress mirror directions.

### 14.8 Counter Verification

| Test Case | Description | sonic-mgmt Coverage | Expected Result |
|---|---|---|---|
| CTR-01 | Per-rule stats after mirror match | Implicit — `validate_acl_rules_in_asic_db` verifies ASIC_DB entries | Packet + byte counters increment |
| CTR-02 | Stats for non-matching rules | — (no dedicated sonic-mgmt test) | Counters zero |

### 14.9 Capability Gate Tests

These must pass for the sonic-mgmt test suite to run. Checked at fixture setup time in `everflow_test_utilities.py::gen_setup_information()` and `conftest.py::everflow_capabilities()`.

| Test Case | Description | sonic-mgmt Check Location | Expected Result |
|---|---|---|---|
| CAP-01 | `switch_capabilities["MIRROR"]` | `gen_setup_information()` → `switch_capabilities_facts()` | `"true"` |
| CAP-02 | `switch_capabilities["MIRRORV6"]` | `gen_setup_information()` → `switch_capabilities_facts()` | `"true"` |
| CAP-03 | `acl_capabilities["INGRESS"]["action_list"]` has `MIRROR_INGRESS_ACTION` | `gen_setup_information()` → `acl_capabilities_facts()` | Present |
| CAP-04 | `acl_capabilities["EGRESS"]["action_list"]` has `MIRROR_EGRESS_ACTION` | `gen_setup_information()` → `acl_capabilities_facts()` | Present |
| CAP-05 | `acl_capabilities["INGRESS"]["action_list"]` has `MIRROR_EGRESS_ACTION` | `gen_setup_information()` → `acl_capabilities_facts()` | Present |
| CAP-06 | `acl_capabilities["EGRESS"]["action_list"]` has `MIRROR_INGRESS_ACTION` | `gen_setup_information()` → `acl_capabilities_facts()` | Present |
| CAP-07 | `PORT_INGRESS_MIRROR_CAPABLE` in STATE_DB | `setup_mirror_session` fixture → `everflow_capabilities()` | `"true"` |
| CAP-08 | `PORT_EGRESS_MIRROR_CAPABLE` in STATE_DB | `setup_mirror_session` fixture → `everflow_capabilities()` | `"true"` |

---

## 15. LAG / Port-Channel Support

Both port mirroring and ACL-based Everflow work with LAG (port-channel) interfaces. The binding mechanisms differ between the two features, but neither requires additional VPP SAI implementation beyond what is already described in Phases 1 and 2.

### 15.1 Port Mirroring on LAGs (Phase 1)

**Binding mechanism**: MirrorOrch decomposes LAG source-port bindings into per-member SAI port attribute calls.

When a mirror session's `src_port` is a LAG:
1. MirrorOrch calls `getLagMember()` to enumerate all members
2. For each member port, calls `sai_port_api->set_port_attribute()` with `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` or `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION`
3. saivpp `setPort()` translates each call to `vpp_span_enable_disable()` on the individual member's `sw_if_index`

When a mirror session's `dst_port` is a LAG:
- MirrorOrch uses the first LAG member's `port_id` as the monitor destination port

Dynamic LAG membership is handled automatically:
- `updateLagMember()` is called when members join/leave the LAG
- Joining members get `SAI_PORT_ATTR_INGRESS/EGRESS_MIRROR_SESSION` applied
- Leaving members get the mirror attribute removed

```
SONiC MirrorOrch (src_port = PortChannel0001)
  │
  ├─ getLagMember() → [Ethernet0, Ethernet4]
  │
  ├─ set_port_attribute(Ethernet0, INGRESS_MIRROR_SESSION, session_oid)
  │   └─ saivpp: vpp_span_enable_disable(sw_if_index=1, dst_sw_if_index, state=RX)
  │
  └─ set_port_attribute(Ethernet4, INGRESS_MIRROR_SESSION, session_oid)
      └─ saivpp: vpp_span_enable_disable(sw_if_index=2, dst_sw_if_index, state=RX)
```

### 15.2 ACL Everflow on LAGs (Phase 2)

**Binding mechanism**: AclOrch binds the ACL table directly to the LAG SAI object (no per-member expansion).

When an Everflow ACL table's `ports` includes a port channel:
1. AclOrch maps `BIND_POINT_TYPE_PORTCHANNEL` → `SAI_ACL_BIND_POINT_TYPE_LAG`
2. Calls `sai_lag_api->set_lag_attribute()` with `SAI_LAG_ATTR_INGRESS_ACL` or `SAI_LAG_ATTR_EGRESS_ACL`
3. saivpp `setLag()` routes to `aclBindUnbindPort(lagId, acl_grp_oid, ...)`
4. `vpp_get_hwif_name(lagId)` resolves LAG OID → `"BondEthernetX"` via `m_lag_bond_map`
5. `vpp_acl_interface_bind("BondEthernetX", acl_swindex, is_input)` binds the VPP ACL to the bond's `sw_if_index`

VPP ACL plugin treats the bond `sw_if_index` identically to any physical interface — packets arriving from the bond carry the bond's `sw_if_index` in the buffer metadata, so ACL lookup and mirror-action processing work without modification.

```
SONiC AclOrch (ACL_TABLE["EVERFLOW"] ports = ["PortChannel0001"])
  │
  └─ set_lag_attribute(lag_oid, SAI_LAG_ATTR_INGRESS_ACL, acl_grp_oid)
      │
      saivpp setLag():
      ├─ aclBindUnbindPort(lag_oid, acl_grp_oid, is_input=true, is_bind=true)
      │   ├─ vpp_get_hwif_name(lag_oid) → "BondEthernet0" (via m_lag_bond_map)
      │   └─ vpp_acl_interface_bind("BondEthernet0", acl_swindex=2, is_input=true)
      │
      VPP ACL plugin:
      └─ acl_interface_add_del_inout_acl(sw_if_index=7, acl_list_index=2)
          └─ Packet from bond (sw_if_index=7) → ACL lookup → mirror action → clone
```

### 15.3 Comparison

| Aspect | Port Mirroring (Phase 1) | ACL Everflow (Phase 2) |
|---|---|---|
| **SONiC orch** | MirrorOrch | AclOrch |
| **Binding granularity** | Per-member port | LAG object |
| **SAI attribute** | `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` per member | `SAI_LAG_ATTR_INGRESS_ACL` on LAG |
| **saivpp handler** | `setPort()` per member | `setLag()` → `aclBindUnbindPort()` |
| **VPP mechanism** | SPAN on each member `sw_if_index` | ACL on bond `sw_if_index` |
| **Dynamic membership** | `updateLagMember()` adds/removes per member | Automatic — new members inherit bond's ACL |
| **Additional code needed** | None | None |

---

## Appendix A: File Change Summary

### Phase 1 Files

| File | Change | Description |
|---|---|---|
| `src/sonic-sairedis/vslib/vpp/SwitchVppMirror.cpp` | **New** | Mirror session create/remove (SPAN + ERSPAN) |
| `src/sonic-sairedis/vslib/vpp/SwitchVpp.cpp` | Modify | Dispatch `SAI_OBJECT_TYPE_MIRROR_SESSION`; handle `SAI_PORT_ATTR_{INGRESS,EGRESS}_MIRROR_SESSION`; report `SAI_SWITCH_ATTR_MAX_MIRROR_SESSION` and mirror availability |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.h` | Modify | Add `vpp_span_enable_disable()`, `vpp_gre_tunnel_t`, `vpp_gre_tunnel_add_del()` |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.c` | Modify | Implement `vpp_span_enable_disable()`, `vpp_gre_tunnel_add_del()` |

### Phase 2 Files (additional)

| File | Change | Description |
|---|---|---|
| `vppbld/repo/src/plugins/acl/acl_types.api` | Modify | Add `ACL_ACTION_API_PERMIT_MIRROR=3`; add encoded `mirror_action` (4-bit flags + 28-bit sw_if_index) to `acl_rule` |
| `vppbld/repo/src/plugins/acl/types.h` | Modify | Add `acl_mirror_action_t mirror_action` to `acl_rule_t` |
| `vppbld/repo/src/plugins/acl/dataplane_node.c` | Modify | Decode mirror flags; MIRROR_INGRESS clones immediately, MIRROR_EGRESS writes metadata for late sonic_ext clone |
| `vppbld/repo/src/plugins/acl/acl.c` | Modify | Add validation for mirror rules |
| `src/sonic-sairedis/vslib/vpp/SwitchVppAcl.cpp` | Modify | Handle `ACTION_MIRROR_INGRESS/EGRESS`; set `ACL_MIRROR_F_DEFERRED` only for MIRROR_EGRESS; maintain global `sonic-ext-egress-mirror` arc refcount (first add / last remove) |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.h` | Modify | Add `VPP_ACL_ACTION_API_PERMIT_MIRROR`, encoded `mirror_action` in rule |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.c` | Modify | Pass encoded `mirror_action` in ACL API |
| `vppbld/plugins/sonic_ext/egress_mirror_node.c` | Modify | Consume ACL-written mirror metadata and clone on late `interface-output`; support global arc add/remove lifecycle |

## Appendix B: VPP Existing API Reference

### SPAN API (`span.api`)

```c
enum span_state {
    SPAN_STATE_API_DISABLED = 0,
    SPAN_STATE_API_RX = 1,
    SPAN_STATE_API_TX = 2,
    SPAN_STATE_API_RX_TX = 3,
};

autoreply define sw_interface_span_enable_disable {
    vl_api_interface_index_t sw_if_index_from;
    vl_api_interface_index_t sw_if_index_to;
    vl_api_span_state_t state;
    bool is_l2;
};
```

### GRE Tunnel API (`gre.api`)

```c
enum gre_tunnel_type : u8 {
    GRE_API_TUNNEL_TYPE_L3 = 0,
    GRE_API_TUNNEL_TYPE_TEB,
    GRE_API_TUNNEL_TYPE_ERSPAN,
};

typedef gre_tunnel {
    vl_api_gre_tunnel_type_t type;
    vl_api_tunnel_mode_t mode;
    vl_api_tunnel_encap_decap_flags_t flags;
    u16 session_id;
    u32 instance;
    u32 outer_table_id;
    vl_api_interface_index_t sw_if_index;
    vl_api_address_t src;
    vl_api_address_t dst;
};
```

### ACL Plugin API (`acl_types.api`) — Current

```c
enum acl_action : u8 {
    ACL_ACTION_API_DENY = 0,
    ACL_ACTION_API_PERMIT = 1,
    ACL_ACTION_API_PERMIT_REFLECT = 2,
};

typedef acl_rule {
    vl_api_acl_action_t is_permit;
    vl_api_prefix_t src_prefix;
    vl_api_prefix_t dst_prefix;
    vl_api_ip_proto_t proto;
    u16 srcport_or_icmptype_first;
    u16 srcport_or_icmptype_last;
    u16 dstport_or_icmpcode_first;
    u16 dstport_or_icmpcode_last;
    u8 tcp_flags_mask;
    u8 tcp_flags_value;
};
```

### ERSPAN Type II Header (`packet.h`)

```c
typedef CLIB_PACKED (struct {
    u32 seq_num;
    union {
        struct {
            u16 ver_vlan;
            u16 cos_en_t_session;
            u32 res_index;
        } t2;
        u64 t2_u64;
    };
}) erspan_t2_t;
```
