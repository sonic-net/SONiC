# SONiC TAM Mirror on Drop (MOD) HLD #

## Table of Content 

### 1. Revision

| Rev | Date | Author | Change Description |
|-----|------|--------|--------------------|
| 0.1 | 2026-03-01 | | Initial draft |
| 0.2 | 2026-03-15 | | Architecture and SAI API sections added |
| 0.3 | 2026-04-01 | | Testing, memory, warmboot, open items completed; internal review draft |

### 2. Scope

This document describes the Mirror on Drop (MOD) feature in SONiC TAM infrastructure. MOD provides packet-level visibility into network drops by capturing and analyzing dropped packets with detailed metadata including drop reasons, queue information, and packet headers.

### 3. Definitions/Abbreviations 

| Term | Definition |
|------|------------|
| MOD | Mirror on Drop |
| DM | Drop Monitor |
| TAM | Telemetry and Monitoring |
| SAI | Switch Abstraction Interface |
| UDT | User Defined Trap |
| Genetlink | Generic Netlink — Linux kernel-to-userspace communication |
| IPFIX | IP Flow Information Export |
| IPP | Ingress Packet Processing |
| MMU | Memory Management Unit |
| EPP | Egress Packet Processing |
| ASIC | Application-Specific Integrated Circuit |
| SWSS | Switch State Service |
| SYNCD | Synchronization Daemon (SAI-to-ASIC bridge) |
| CRM | Critical Resource Monitor |
| OID | Object Identifier |
| SR_TCM | Single Rate Three Color Marker |
| CIR | Committed Information Rate |
| CBS | Committed Burst Size |
| YANG | Yet Another Next Generation (data modeling language) |
| RSS | Resident Set Size |
| HLD | High-Level Design |

### 4. Overview 

The MOD (Mirror on Drop) feature enables real-time monitoring and reporting of packet drop events from the switch ASIC to user space. When a packet is dropped in the forwarding pipeline, the MOD feature captures the packet metadata and sends it to a TAM agent for processing and export to external collectors.

### 5. Requirements

The following are the requirements for Mirror on Drop (MOD) support:

- Detect and report ASIC packet drop events (IPP, MMU, EPP stages) to user space in real time
- Support per-packet drop reporting (stateless) with 5-tuple, drop reason, and pipeline stage metadata
- Support aggregated per-flow drop statistics (stateful) with configurable aging
- Export drop telemetry to external collectors via IPFIX
- Support configurable hardware-based drop sampling rates
- Support CPU rate limiting via policer to protect against high-rate drop events
- Support optional flow-group filtering to scope monitoring to specific traffic flows
- Use `NET_DM` genetlink family / multicast group `events` as the kernel delivery channel
- Query SAI platform capability at runtime; silently disable MOD on unsupported platforms

**Exemptions (not supported in this release):**

- Direct hardware-to-collector export via front-panel ports
- gRPC-based collector export
- Configurable policer CIR/CBS via CLI

### 6. Architecture Design 

MOD is a **built-in SONiC feature** implemented via a new TAM Docker container with extensions to the existing SWSS and SYNCD containers. The existing SONiC architecture is not changed — MOD adds new components alongside existing ones.

![Solution Design](images/solution_design.png)

#### 6.1 New Components

- **TAM Docker Container**: New docker container hosting two daemons:
  - `tammgrd` — monitors CONFIG_DB TAM tables, validates configuration, writes to APPL_DB
  - `TAM Agent` — receives drop events via genetlink (`NET_DM` family), parses metadata, writes to COUNTERS_DB
- **tamOrch** — new orchestration agent added to the SWSS container, subscribes to APPL_DB `TAM_TABLE` and programs SAI TAM objects

#### 6.2 Modified Components

- **SWSS**: Addition of `tamOrch` agent
- **SYNCD**: Extended to support SAI TAM APIs and SAI Hostif genetlink APIs

#### 6.3 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ CONFIG_DB                                                       │
│ (TAM_SWITCH, TAM_COLLECTORS, TAM_SAMPLINGRATE,                  │
│  TAM_DROPMONITOR, TAM_DROPMONITOR_SESSIONS)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ TAM Docker Container                                            │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ tammgrd: Configuration Daemon                            │    │
│ │ - Monitors CONFIG_DB TAM tables                          │    │
│ │ - Validates configuration                                │    │
│ │ - Updates APPL_DB with TAM configuration                 │    │
│ └──────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ TAM Agent: Packet Drop Handler                           │    │
│ │ - Receives drop metadata via genetlink (NET_DM)          │    │
│ │ - Filters NET_DM_ORIGIN_HW events (hardware drops only)  │    │
│ │ - Parses 5-tuple, drop reason, queue, ingress port       │    │
│ │ - Writes drop statistics to COUNTERS_DB                  │    │
│ └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ APPL_DB                                                         │
│ (TAM_TABLE)                                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ SWSS Container                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ tamOrch: TAM Orchestration Agent                         │    │
│ │ - Subscribes to APPL_DB TAM_TABLE                        │    │
│ │ - Creates SAI TAM objects in dependency order            │    │
│ │ - Manages object lifecycle (create/delete/update)        │    │
│ └──────────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ SYNCD/SAI Layer                                                 │
│ - Creates genetlink family "NET_DM" / mcgrp "events"            │
│ - Configures hostif, trap group, user-defined trap (TAM type)   │
│ - Programs CPU queue policer for rate limiting                  │
│ - Programs hardware drop event monitoring                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ASIC/Hardware                                                   │
│ - Detects packet drops (IPP / MMU / EPP)                        │
│ - Applies configured sampling rate                              │
│ - Encapsulates drop metadata and sends to CPU                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.4 Configuration Flow

```
User (CLI / REST)
│
▼
CONFIG_DB (TAM_SWITCH, TAM_COLLECTORS, TAM_SAMPLINGRATE,
           TAM_DROPMONITOR, TAM_DROPMONITOR_SESSIONS)
│
▼
tammgrd (validates and transforms)
│
▼
APPL_DB (TAM_TABLE)
│
▼
tamOrch (creates SAI TAM objects)
│
▼
SYNCD/SAI (programs hardware, registers NET_DM genetlink family)
```

#### 6.5 Drop Event Flow

```
ASIC detects packet drop (IPP / MMU / EPP)
│
▼
CPU Queue (rate-limited via policer)
│
▼  genetlink: family=NET_DM, mcgrp=events
TAM Agent
│  (filters NET_DM_ORIGIN_HW, parses 5-tuple + drop reason)
▼
COUNTERS_DB (per-flow drop statistics with aging and poll intervals)
│
▼
Telemetry Container (reads COUNTERS_DB, exports via IPFIX to collector)
```

![TAM Data Flow](images/tam_data_flow.png)

### 7. High-Level Design 

This section covers the high level design of the TAM MOD feature. This section covers the following points in detail.

#### 7.1 Feature Classification

MOD is a **built-in SONiC feature** and not an Application Extension.

#### 7.2 Repositories Changed

| Repository | Change |
|---|---|
| `sonic-buildimage` | New TAM Docker container definition and supervisor config |
| `sonic-swss` | Add `tamOrch` orchestration agent to SWSS container |
| `sonic-swss-common` | New CONFIG_DB / APPL_DB / COUNTERS_DB table definitions |
| `sonic-utilities` | New CLI commands for TAM configuration |
| `sonic-yang-models` | New YANG models for TAM tables |

#### 7.3 tammgrd Changes (TAM Docker)

A new `tammgrd` daemon runs inside the TAM Docker container. It:

- Monitors the following CONFIG_DB tables: `TAM_SWITCH`, `TAM_COLLECTORS`, `TAM_SAMPLINGRATE`, `TAM_DROPMONITOR`
- Translates user configuration into APPL_DB entries for consumption by `tamOrch`
- Initializes a `COUNTERS_TAM_DM_TABLE` entry in COUNTERS_DB with default aging/poll-interval values on startup
- Propagates configuration changes incrementally (no full restart needed)

**CONFIG_DB → APPL_DB propagation:**

```
CONFIG_DB TAM_SWITCH        → APPL_DB APP_TAM_SWITCH_TABLE
CONFIG_DB TAM_COLLECTORS    → APPL_DB APP_TAM_COLLECTOR_TABLE
CONFIG_DB TAM_SAMPLINGRATE  → APPL_DB APP_TAM_SAMPLER_TABLE
CONFIG_DB TAM_DROPMONITOR   → APPL_DB APP_TAM_DROPMONITOR_TABLE
```

#### 7.4 SWSS Changes (tamOrch)

A new `tamOrch` orchestration agent is added to the SWSS container. It subscribes to the following APPL_DB tables populated by `tammgrd`:

- `APP_TAM_COLLECTOR_TABLE` — collector IP, port, and protocol
- `APP_TAM_SAMPLER_TABLE` — sampling rate configuration
- `APP_TAM_DROPMONITOR_TABLE` — drop monitor enable/disable and flow parameters

`tamOrch::doTask()` dispatches on table name:

```cpp
if (table_name == APP_TAM_COLLECTOR_TABLE)
    tamCheckCollectorAndFillValues();
else if (table_name == APP_TAM_SAMPLER_TABLE)
    tamCheckSamplerAndFillValues();
else if (table_name == APP_TAM_DROPMONITOR_TABLE) {
    if (status == "enable")        tam_create_drop_monitor();
    else if (status == "disable")  tam_remove_drop_monitor();
}
```

On `status=enable`, tamOrch creates 11 SAI objects in strict dependency order, then activates monitoring via the switch attribute:

```
 1. tam_report          (SAI_TAM_REPORT_TYPE_GENETLINK)
 2. tam_event_action    (references tam_report)
 3. tam_transport       (SAI_TAM_TRANSPORT_TYPE_NONE)
 4. policer             (CIR=1000 pps, CBS=2000, SR_TCM — rate-limits drop events to CPU)
 5. hostif              (SAI_HOSTIF_TYPE_GENETLINK, name="NET_DM", mcgrp="events")
 6. hostif_trap_group   (references policer)
 7. hostif_udt          (SAI_HOSTIF_USER_DEFINED_TRAP_TYPE_TAM, references trap_group)
 8. hostif_table_entry  (maps UDT → genetlink hostif channel)
 9. tam_collector       (references hostif_udt + tam_transport)
10. tam_event           (SAI_TAM_EVENT_TYPE_PACKET_DROP, references tam_event_action + tam_collector)
11. tam                 (references tam_event, bind point = SAI_TAM_BIND_POINT_TYPE_SWITCH)
--- activate ---
12. SAI_SWITCH_ATTR_TAM_OBJECT_ID ← tam_id   (starts hardware drop monitoring)
```

On `status=disable`, objects are deleted in exact reverse order (step 12 first, then 11→1) to avoid `SAI_STATUS_OBJECT_IN_USE` errors.

**tamOrch Data Flow:**

![tamOrch Data Flow](images/tamorch_data_flow.png)

#### 7.5 tamOrch State Machine

```
┌─────────────┐
│  DISABLED   │◄──────────────────────────────────────┐
│  (Initial)  │                                       │
└──────┬──────┘                                       │
       │ APP_TAM_DROPMONITOR status="enable"          │
       ▼                                              │
┌──────────────────────────────────────────┐          │
│  CREATING_DROPMONITOR_OBJECTS            │          │
│  Steps 1-11 (SAI object creation)        │          │
│  On any failure: rollback in reverse,    │          │
│  return to DISABLED                      │          │
└──────┬───────────────────────────────────┘          │
       │ All objects created successfully             │
       ▼                                              │
┌──────────────────────────────────────────┐          │
│  ENABLING                                │          │
│  Set SAI_SWITCH_ATTR_TAM_OBJECT_ID       │          │
└──────┬───────────────────────────────────┘          │
       │                                              │
       ▼                                              │
┌──────────────┐                                      │
│   ENABLED    │◄── config updates (no state change)  │
└──────┬───────┘                                      │
       │ APP_TAM_DROPMONITOR status="disable"         │
       ▼                                              │
┌──────────────────────────────────────────┐          │
│  DISABLING                               │          │
│  Clear SAI_SWITCH_ATTR_TAM_OBJECT_ID     │          │
└──────┬───────────────────────────────────┘          │
       │                                              │
       ▼                                              │
┌──────────────────────────────────────────┐          │
│  DELETING_OBJECTS                        │          │
│  Steps 11→1 (reverse dependency order)   │──────────┘
└──────────────────────────────────────────┘
```

#### 7.6 Error Handling

**Object creation failure — rollback strategy:**

If any SAI object creation call fails, all previously created objects are deleted in reverse order before returning to DISABLED state:

```cpp
sai_status_t status = sai_tam_api->create_tam_report(&tam_report_id, ...);
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to create TAM report: %d", status);
    return false;  // Nothing to roll back yet
}

status = sai_tam_api->create_tam_event_action(&tam_event_action_id, ...);
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to create TAM event action: %d", status);
    sai_tam_api->remove_tam_report(tam_report_id);  // Roll back step 1
    return false;
}
// ... continues for all 11 objects
```

**Common SAI error codes:**

| Error Code | Meaning | Recovery |
| --- | --- | --- |
| `SAI_STATUS_SUCCESS` | Operation succeeded | Continue |
| `SAI_STATUS_FAILURE` | Generic failure | Retry after delay |
| `SAI_STATUS_NOT_SUPPORTED` | Feature not supported on this platform | Disable TAM feature |
| `SAI_STATUS_NO_MEMORY` | Out of resources | Reduce sampling rate, retry |
| `SAI_STATUS_INSUFFICIENT_RESOURCES` | Hardware table full | Reduce config, retry |
| `SAI_STATUS_INVALID_PARAMETER` | Bad attribute value | Validate configuration |
| `SAI_STATUS_OBJECT_IN_USE` | Cannot delete — still referenced | Check deletion order |

**Pre-creation validation:** tamOrch validates that referenced collector and sampler entries exist in APPL_DB before attempting SAI object creation. If `sai_tam_api == nullptr`, TAM is silently disabled with a warning log (graceful degradation on platforms without SAI TAM support).

#### 7.7 Object Deletion Dependency Chain

The following deletion order is mandatory to avoid `SAI_STATUS_OBJECT_IN_USE` errors:

```
SAI_SWITCH_ATTR_TAM_OBJECT_ID (clear)
  → tam                (references tam_event)
  → tam_event          (references tam_event_action, tam_collector)
  → tam_collector      (references hostif_udt, tam_transport)
  → hostif_table_entry (references hostif_udt, hostif)
  → hostif_udt         (references hostif_trap_group)
  → hostif_trap_group  (references policer)
  → policer            (independent)
  → hostif             (independent)
  → tam_transport      (independent)
  → tam_event_action   (references tam_report)
  → tam_report         (independent)
```

#### 7.8 DB Changes

**COUNTERS_DB** is used for TAM MOD drop statistics:

| Table | Key | Fields | Written by | Read by |
| --- | --- | --- | --- | --- |
| `COUNTERS_TAM_DM_TABLE` | `global` | `aging-interval`, `poll-interval`, `status` | `tammgrd` on init | TAM Agent, Telemetry Container |
| `COUNTERS_TAM_DM_TABLE` | `<flow-key>` | `src-ip`, `dst-ip`, `src-port`, `dst-port`, `proto`, `drop-count`, `drop-reason`, `port`, `queue` | TAM Agent | Telemetry Container |

The TAM Agent receives drop metadata via genetlink, aggregates it using aging/polling intervals, and writes per-flow drop records to COUNTERS_DB:COUNTERS_TAM_DM_TABLE. The Telemetry Container reads this table and constructs IPFIX/gRPC export messages to the configured collector.

#### 7.9 Linux / Kernel Interface

The TAM Agent communicates with the kernel via the **Netlink Drop Monitor** (`NET_DM`) genetlink family:

- SAI creates the `NET_DM` genetlink family and multicast group `events` via the hostif framework
- The ASIC driver sends `genlmsg_multicast()` to the `NET_DM:events` group on each hardware drop event
- The TAM Agent subscribes to this group and receives messages containing 5-tuple, drop reason, ingress port, and egress queue
- `NET_DM_ATTR_ORIGIN` distinguishes hardware drops (`NET_DM_ORIGIN_HW`) from software drops (`NET_DM_ORIGIN_SW`)

#### 7.10 Platform Abstraction — CPU Queue

tamOrch does **not** configure or query CPU queue numbers directly. Queue assignment is handled implicitly by the vendor SAI implementation.

When tamOrch creates a `SAI_HOSTIF_USER_DEFINED_TRAP_TYPE_TAM` UDT and binds it to a trap group, the SAI layer automatically routes TAM packets to the appropriate CPU queue based on trap type. `SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE` is **not set** by tamOrch.

This follows the same pattern used by SONiC for BGP, LLDP, and LACP traps — queue assignment is a vendor SAI internal detail, keeping tamOrch 100% platform-agnostic.

#### 7.11 Warmboot and Fastboot

- **Warmboot**: TAM SAI objects are re-created after warm reboot. `tammgrd` and `tamOrch` re-read CONFIG_DB/APPL_DB on startup and recreate all objects. Drop monitoring resumes within the normal orchagent convergence window.
- **Fastboot**: TAM Docker startup is deferred until after the critical path (port/VLAN/route convergence). TAM does not participate in the critical-path startup sequence.

#### 7.12 Serviceability and Debug

**Logging:**

- `tamOrch` logs all SAI object create/delete operations and return codes at `NOTICE` level
- SAI errors logged at `ERROR` level with full status code
- `tammgrd` logs CONFIG_DB → APPL_DB propagation at `INFO` level

**Diagnostic commands:**

```bash
# Check TAM drop statistics in COUNTERS_DB
redis-cli -n 2 HGETALL "COUNTERS_TAM_DM_TABLE|global"
redis-cli -n 2 KEYS "COUNTERS_TAM_DM_TABLE|*"

# Verify SAI objects created in ASIC_DB
redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_TAM*"
redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF*"

# Check tammgrd APPL_DB entries
redis-cli -n 0 HGETALL "APP_TAM_DROPMONITOR_TABLE:global"

# Verify genetlink family registered
genl ctrl list | grep NET_DM
```

SAI API requirements, CLI, and ConfigDB schema are covered in Sections 8 and 9.

### 8. SAI API

The MOD feature does not introduce new SAI APIs. It uses existing SAI TAM, SAI Hostif, SAI Policer, and SAI Switch APIs. The following SAI objects are orchestrated by `tamOrch` to enable hardware drop monitoring.

#### 8.1 Object Creation Sequence

Objects must be created in the following dependency order:

```
 1. tam_report              (independent)
 2. tam_event_action        (depends on tam_report)
 3. tam_transport           (independent)
 4. policer                 (independent)
 5. hostif                  (independent)
 6. hostif_trap_group       (depends on policer)
 7. hostif_user_defined_trap (depends on hostif_trap_group)
 8. hostif_table_entry      (depends on hostif, hostif_user_defined_trap)
 9. tam_collector           (depends on hostif_user_defined_trap)
10. tam_event               (depends on tam_event_action, tam_collector)
11. tam                     (depends on tam_event)
12. switch_attribute        (depends on tam)
```

Deletion must follow exact reverse order (12 → 1) to avoid `SAI_STATUS_OBJECT_IN_USE` errors.

**SAI TAM API Call Sequence:**

![SAI TAM Interface](images/sai_tam_interface.png)

---

#### 8.2 Object 1: TAM Report

Defines the reporting mechanism. `SAI_TAM_REPORT_TYPE_GENETLINK` causes drop events to be sent to user space via a genetlink socket.

```cpp
sai_tam_api->create_tam_report(&tam_report_id, gSwitchId, attr_list);
```

| Attribute | Value |
| --- | --- |
| `SAI_TAM_REPORT_ATTR_TYPE` | `SAI_TAM_REPORT_TYPE_GENETLINK` |

---

#### 8.3 Object 2: TAM Event Action

Links the event to the genetlink report object.

```cpp
sai_tam_api->create_tam_event_action(&tam_event_action_id, gSwitchId, attr_list);
```

| Attribute | Value |
| --- | --- |
| `SAI_TAM_EVENT_ACTION_ATTR_REPORT_TYPE` | `tam_report_id` |

---

#### 8.4 Object 3: TAM Transport

No transport layer is needed for genetlink delivery; type is set to `NONE`.

```cpp
sai_tam_api->create_tam_transport(&tam_transport_id, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_TAM_TRANSPORT_ATTR_TRANSPORT_TYPE` | `SAI_TAM_TRANSPORT_TYPE_NONE` | Genetlink handles delivery |
| `SAI_TAM_TRANSPORT_ATTR_SRC_PORT` | `0` | Not used with TYPE_NONE |
| `SAI_TAM_TRANSPORT_ATTR_DST_PORT` | `0` | Not used with TYPE_NONE |

---

#### 8.5 Object 4: Policer

Rate-limits drop events punted to CPU using SR_TCM. CIR/CBS values are currently hardcoded; making them configurable via CLI is a future enhancement (see Exemptions in Section 5).

```cpp
sai_policer_api->create_policer(&sai_policer_obj, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_POLICER_ATTR_METER_TYPE` | `SAI_METER_TYPE_PACKETS` | Rate limit by packet count |
| `SAI_POLICER_ATTR_MODE` | `SAI_POLICER_MODE_SR_TCM` | Single Rate Three Color Marker |
| `SAI_POLICER_ATTR_CIR` | `1000` | Committed Information Rate = 1000 pps |
| `SAI_POLICER_ATTR_CBS` | `2000` | Committed Burst Size = 2000 packets |
| `SAI_POLICER_ATTR_PIR` | `0` | Not used in SR_TCM mode |
| `SAI_POLICER_ATTR_PBS` | `0` | Not used in SR_TCM mode |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | `SAI_PACKET_ACTION_FORWARD` | Pass green packets to CPU |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | Drop yellow packets |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | Drop red packets |

---

#### 8.6 Object 5: Hostif (Genetlink Channel)

Creates the `NET_DM` genetlink family and `events` multicast group in the kernel for user space to receive drop events.

```cpp
sai_hostif_api->create_hostif(&sai_hostif_obj, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_HOSTIF_ATTR_TYPE` | `SAI_HOSTIF_TYPE_GENETLINK` | Genetlink socket type |
| `SAI_HOSTIF_ATTR_NAME` | `"NET_DM"` | Genetlink family name |
| `SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME` | `"events"` | Multicast group name |

---

#### 8.7 Object 6: Hostif Trap Group

Groups the TAM trap and attaches the policer for rate limiting. `SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE` is **not set** by `tamOrch` — the CPU queue is assigned implicitly by the SAI implementation when the TAM UDT is bound to this group in the next step.

```cpp
sai_hostif_api->create_hostif_trap_group(&trap_group_obj, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_HOSTIF_TRAP_GROUP_ATTR_POLICER` | `sai_policer_obj` | Attach rate-limiting policer |
| `SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE` | *(not set)* | Assigned implicitly by SAI on UDT bind |

---

#### 8.8 Object 7: Hostif User Defined Trap

Creates the TAM-type user-defined trap and associates it with the trap group. At this point the SAI implementation automatically assigns the appropriate CPU queue for TAM traffic based on the trap type.

```cpp
sai_hostif_api->create_hostif_user_defined_trap(&udt_obj, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_HOSTIF_USER_DEFINED_TRAP_ATTR_TYPE` | `SAI_HOSTIF_USER_DEFINED_TRAP_TYPE_TAM` | TAM-specific trap type |
| `SAI_HOSTIF_USER_DEFINED_TRAP_ATTR_TRAP_GROUP` | `trap_group_obj` | Associates with trap group |

---

#### 8.9 Object 8: Hostif Table Entry

Directs packets matching the UDT to the genetlink hostif channel.

```cpp
sai_hostif_api->create_hostif_table_entry(&table_entry_obj, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_HOSTIF_TABLE_ENTRY_ATTR_TYPE` | `SAI_HOSTIF_TABLE_ENTRY_TYPE_TRAP_ID` | Match on trap ID |
| `SAI_HOSTIF_TABLE_ENTRY_ATTR_TRAP_ID` | `udt_obj` | User-defined trap to match |
| `SAI_HOSTIF_TABLE_ENTRY_ATTR_CHANNEL_TYPE` | `SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK` | Use genetlink channel |
| `SAI_HOSTIF_TABLE_ENTRY_ATTR_HOST_IF` | `sai_hostif_obj` | Target hostif for delivery |

---

#### 8.10 Object 9: TAM Collector

Configures the collector endpoint for drop events.

```cpp
sai_tam_api->create_tam_collector(&tam_collector_id, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_TAM_COLLECTOR_ATTR_HOSTIF_TRAP` | `udt_obj` | Link to UDT for CPU punt |
| `SAI_TAM_COLLECTOR_ATTR_SRC_IP` | switch management IP | Sourced from CONFIG_DB `TAM_SWITCH` |
| `SAI_TAM_COLLECTOR_ATTR_DST_IP` | collector IP | Sourced from CONFIG_DB `TAM_COLLECTORS` |
| `SAI_TAM_COLLECTOR_ATTR_DSCP_VALUE` | `0` | Default DSCP |
| `SAI_TAM_COLLECTOR_ATTR_TRANSPORT` | `tam_transport_id` | Transport object (TYPE_NONE) |

---

#### 8.11 Object 10: TAM Event

Defines the drop event type to monitor, and which action and collector to use.

```cpp
sai_tam_api->create_tam_event(&tam_event_id, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_TAM_EVENT_ATTR_TYPE` | `SAI_TAM_EVENT_TYPE_PACKET_DROP` | Monitor packet drops |
| `SAI_TAM_EVENT_ATTR_ACTION_LIST` | `{tam_event_action_id}` | Action on drop event |
| `SAI_TAM_EVENT_ATTR_COLLECTOR_LIST` | `{tam_collector_id}` | Collector for drop events |
| `SAI_TAM_EVENT_ATTR_SWITCH_EVENT_TYPE` | platform-defined | SAI capability query at runtime |

The number of TAM event objects required is determined at runtime via SAI capability query. Implementations may require one event object covering all drop stages, or separate event objects per pipeline stage (IPP, MMU, EPP). This is an implementation detail handled transparently by the SAI layer.

---

#### 8.12 Object 11: TAM

Binds the TAM event(s) to the switch bind point, enabling monitoring globally across all ports.

```cpp
sai_tam_api->create_tam(&tam_id, gSwitchId, attr_list);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_TAM_ATTR_EVENT_OBJECTS_LIST` | `{tam_event_id}` | Event(s) to monitor |
| `SAI_TAM_ATTR_TAM_BIND_POINT_TYPE_LIST` | `{SAI_TAM_BIND_POINT_TYPE_SWITCH}` | Bind to switch (all ports) |

---

#### 8.13 Object 12: Switch Attribute Binding

Activates drop monitoring by binding the TAM object to the switch. This is the final step — no drop events are reported until this attribute is set.

```cpp
sai_switch_api->set_switch_attribute(gSwitchId, &switch_attr);
```

| Attribute | Value | Notes |
| --- | --- | --- |
| `SAI_SWITCH_ATTR_TAM_OBJECT_ID` | `tam_id` | Activates TAM on switch |

To disable, clear this attribute first before deleting any other objects.

### 9. Configuration and management

MOD is not an Application Extension — Section 9.1 (Manifest) is not applicable.

#### 9.1 Manifest

Not applicable. MOD is a built-in SONiC feature, not an Application Extension.

---

#### 9.2 CONFIG_DB Schema

The following CONFIG_DB tables are introduced. All tables are defined in `sonic-swss-common` and validated by corresponding YANG models in `sonic-yang-models`.

##### TAM_SWITCH Table

Defines the switch-level TAM identity used as the source IP in TAM collector encapsulation.

```
TAM_SWITCH|device
    "switch-id": <IPv4>      # Switch management/loopback IP, used as collector src-ip
    "device-id": <uint32>    # Optional device identifier
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `switch-id` | IPv4 address | Yes | Used as `SAI_TAM_COLLECTOR_ATTR_SRC_IP` |
| `device-id` | uint32 | No | Optional platform identifier |

Only one entry is allowed (key must be `device`).

---

##### TAM_COLLECTORS Table

Defines the external collector endpoint for IPFIX export.

```
TAM_COLLECTOR|<name>
    "ip":       <IPv4 or IPv6>   # Collector IP address
    "port":     <1-65535>        # Collector UDP/TCP port
    "protocol": "UDP"            # Transport protocol (UDP or TCP, default: UDP)
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `ip` | IPv4 or IPv6 | Yes | Used as `SAI_TAM_COLLECTOR_ATTR_DST_IP` |
| `port` | 1–65535 | Yes | Collector port |
| `protocol` | UDP \| TCP | No | Default: UDP |

Maximum 1 collector supported in this release.

---

##### TAM_SAMPLINGRATE Table

Defines the hardware drop event sampling rate.

```
TAM_SAMPLER|<name>
    "rate": <uint32>    # 1 = capture all drops (1:1); N = capture 1 in N drops
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `rate` | uint32 (1–65535) | Yes | Rate of 1 captures every drop |

---

##### TAM_FEATURES Table

Enables or disables individual TAM features and sets their poll intervals.

```
TAM_FEATURES|DROPMONITOR
    "status":        "ACTIVE"    # ACTIVE or INACTIVE
    "poll-interval": "1000"      # Polling interval in milliseconds (1000–30000)
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `status` | ACTIVE \| INACTIVE | Yes | Controls feature enable/disable |
| `poll-interval` | 1000–30000 ms | No | Default: 1000 ms |

---

##### TAM_DROPMONITOR Table

Global drop monitor configuration parameters.

```
TAM_DROPMONITOR|global
    "aging-interval":  "60"          # Seconds before a flow entry is aged out (1–1800)
    "poll-interval":   "10"          # Seconds between COUNTERS_DB updates (1–1800)
    "monitor-mode":    "stateful"    # stateless or stateful
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `aging-interval` | 1–1800 s | No | Default: 60 s |
| `poll-interval` | 1–1800 s | No | Default: 10 s |
| `monitor-mode` | stateless \| stateful | No | Default: stateful |

---

##### TAM_DROPMONITOR_SESSIONS Table

Binds a flow group, collector, and sampler into a drop monitor session.

```
TAM_DROPMONITOR_SESSIONS|<name>
    "flowgroup":   "<acl-rule-name>"    # Reference to ACL flow group
    "collector":   "<collector-name>"   # Reference to TAM_COLLECTORS entry
    "sample-rate": "<sampler-name>"     # Reference to TAM_SAMPLINGRATE entry
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `flowgroup` | string | No | ACL rule for scoped monitoring; omit for all traffic |
| `collector` | string | Yes | Must exist in `TAM_COLLECTORS` |
| `sample-rate` | string | Yes | Must exist in `TAM_SAMPLINGRATE` |

---

#### 9.3 YANG Validation Rules

YANG models in `sonic-yang-models` enforce the following constraints:

| Table | Field | Constraint |
| --- | --- | --- |
| `TAM_SWITCH` | `switch-id` | Valid IPv4 address; single entry only |
| `TAM_COLLECTORS` | `ip` | Valid IPv4 or IPv6 address |
| `TAM_COLLECTORS` | `port` | Integer 1–65535 |
| `TAM_COLLECTORS` | `protocol` | Enum: UDP, TCP |
| `TAM_SAMPLINGRATE` | `rate` | uint32, 1–65535 |
| `TAM_DROPMONITOR` | `aging-interval` | Integer 1–1800 |
| `TAM_DROPMONITOR` | `poll-interval` | Integer 1–1800 |
| `TAM_DROPMONITOR` | `monitor-mode` | Enum: stateless, stateful |
| `TAM_DROPMONITOR_SESSIONS` | `collector` | leafref → `TAM_COLLECTORS` entry |
| `TAM_DROPMONITOR_SESSIONS` | `sample-rate` | leafref → `TAM_SAMPLINGRATE` entry |

All `leafref` references are validated at commit time — configuration fails if a referenced object does not exist.

---

#### 9.4 CLI

New CLI commands are added to `sonic-utilities` under the `tam` group (Click-based).

**Configuration commands:**

```bash
# Set switch identity
config tam switch-id <ip>

# Add a collector
config tam collector add <name> --ip <ip> --port <port> [--protocol UDP|TCP]
config tam collector del <name>

# Add a sampler
config tam sampler add <name> --rate <rate>
config tam sampler del <name>

# Enable / disable drop monitor feature
config tam feature dropmonitor enable
config tam feature dropmonitor disable

# Set drop monitor parameters
config tam dropmonitor aging-interval <seconds>
config tam dropmonitor poll-interval <seconds>
config tam dropmonitor mode stateless|stateful

# Add / remove a drop monitor session
config tam dropmonitor session add <name> --collector <c> --sample-rate <s> [--flowgroup <fg>]
config tam dropmonitor session del <name>
```

**Show commands:**

```bash
# Show global TAM switch config
show tam switch

# Show collectors
show tam collectors

# Show samplers
show tam samplers

# Show drop monitor status and config
show tam dropmonitor config

# Show live drop statistics from COUNTERS_DB
show tam dropmonitor statistics
```

---

#### 9.5 CONFIG_DB → APPL_DB Propagation

`tammgrd` monitors CONFIG_DB and propagates changes to APPL_DB:

| CONFIG_DB Table | APPL_DB Table |
| --- | --- |
| `TAM_SWITCH` | `APP_TAM_SWITCH_TABLE` |
| `TAM_COLLECTORS` | `APP_TAM_COLLECTOR_TABLE` |
| `TAM_SAMPLINGRATE` | `APP_TAM_SAMPLER_TABLE` |
| `TAM_FEATURES\|DROPMONITOR` | `APP_TAM_DROPMONITOR_TABLE` (sets `status`) |
| `TAM_DROPMONITOR` | `APP_TAM_DROPMONITOR_TABLE` (sets parameters) |
| `TAM_DROPMONITOR_SESSIONS` | `APP_TAM_DROPMONITOR_TABLE` (per-session keys) |

`tamOrch` in SWSS subscribes to APPL_DB and calls SAI APIs on changes.
		
### 10. Warmboot and Fastboot Design Impact

#### 10.1 Warmboot

TAM MOD has no impact on the warmboot data-plane continuity guarantee. The feature operates entirely in the control plane (SAI object programming and CPU-path event processing) — it does not modify forwarding tables, port state, or any path that carries production traffic.

**Behavior during warmboot:**

- SAI TAM objects are **not preserved** across a warm reboot. The SAI/ASIC state is torn down and rebuilt by orchagent on restart.
- On startup, `tammgrd` re-reads all TAM tables from CONFIG_DB and re-populates APPL_DB.
- `tamOrch` subscribes to APPL_DB on startup and recreates all 12 SAI objects in dependency order.
- Drop monitoring resumes within the normal orchagent convergence window (same as other orchagent-managed features).
- Any drop events that occur during the convergence window are not captured — this is acceptable since the window is brief and telemetry data is best-effort.

**No additional warmboot stalls are introduced.** TAM Docker startup is independent of the critical convergence path.

#### 10.2 Fastboot

TAM Docker does **not** participate in the critical-path startup sequence. It can be delayed without impacting port bring-up, VLAN programming, or route convergence.

- TAM Docker is started after the critical path completes.
- `tammgrd` and the TAM Agent have no dependencies on port state or routing tables.
- No Jinja template rendering or heavy CPU processing is performed during boot.
- No third-party dependencies are updated by this feature.

**Boot time impact: None** when the feature is disabled. When enabled, TAM Docker startup adds negligible overhead (daemon initialization + Redis subscribe calls) well outside the critical path.

#### 10.3 Warmboot and Fastboot Performance Impact Summary

| Aspect | Impact | Notes |
| --- | --- | --- |
| Data-plane downtime | None | TAM is control-plane only |
| Boot critical chain stalls | None | TAM Docker not in critical path |
| CPU-heavy boot processing | None | No template rendering or heavy I/O |
| Third-party dependency changes | None | No new dependencies |
| Docker delay possible | Yes | TAM Docker can be fully deferred |
| Drop monitoring gap on reboot | Brief | Events during orchagent convergence window are not captured |
| Feature disabled overhead | None | No memory or CPU cost when TAM_FEATURES\|DROPMONITOR is INACTIVE |

### 11. Memory Consumption

#### 11.1 Feature Disabled

When `TAM_FEATURES|DROPMONITOR` is set to `INACTIVE` (or the TAM Docker is not started):

- **No SAI objects are created** — zero ASIC table entries consumed
- **No COUNTERS_DB entries** — `COUNTERS_TAM_DM_TABLE` is empty
- **No genetlink socket** — no kernel memory allocated for `NET_DM` family
- **tammgrd memory** — minimal (~2 MB RSS for the Python daemon, subscribe-only mode)
- **TAM Agent memory** — zero (not started when feature is INACTIVE)

Memory consumption when disabled is therefore bounded by the TAM Docker container base overhead only (~20–30 MB total for the container runtime), which is consistent with other SONiC feature dockers.

#### 11.2 Feature Enabled — Control Plane Objects

| Component | Memory | Notes |
| --- | --- | --- |
| 12 SAI TAM/Hostif/Policer objects | ~1 KB | Kernel + SAI object metadata |
| `tamOrch` in-memory state | ~50 KB | SAI OID cache, APPL_DB subscriber |
| `tammgrd` daemon | ~5 MB RSS | Python process with Redis subscribers |
| TAM Agent process | ~10 MB RSS | Genetlink socket + flow state table |

#### 11.3 COUNTERS_DB Growth (Stateful Mode)

In stateful mode, the TAM Agent writes one Redis hash entry per active drop flow into `COUNTERS_TAM_DM_TABLE`. Each entry holds 9 fields (5-tuple + drop-count + drop-reason + port + queue).

| Parameter | Value |
| --- | --- |
| Per-flow entry size | ~500 bytes (Redis hash with 9 string fields) |
| Max concurrent flows | Platform-dependent (bounded by `aging-interval`) |
| Aging | Flows are expired after `aging-interval` seconds of inactivity |
| Growth bound | Bounded — stale flows are removed; no unbounded growth |

With default `aging-interval=60s` and typical datacenter traffic patterns, the number of concurrent drop flows is small (tens to low hundreds). At 500 bytes/flow, 1000 concurrent flows consume ~500 KB in COUNTERS_DB — negligible.

In stateless mode, no per-flow state is accumulated; each drop event is exported immediately with no Redis write.

#### 11.4 Summary

| Scenario | Additional Memory |
| --- | --- |
| Feature compiled in, disabled by config | ~0 MB (no TAM Docker started) |
| Feature enabled, no active drops | ~15 MB (container + daemons, no DB growth) |
| Feature enabled, stateless mode | ~15 MB (no COUNTERS_DB growth) |
| Feature enabled, stateful mode, 1000 active flows | ~15.5 MB (~500 KB COUNTERS_DB) |
### 12. Restrictions/Limitations

| # | Restriction | Details |
| --- | --- | --- |
| 1 | **Ingress drops only** | Current implementation monitors ingress pipeline drops (IPP, MMU). Egress MOD is not supported in this release. |
| 2 | **CPU punting required** | All drop events are delivered to user space via the CPU genetlink path. Direct hardware-to-collector IPFIX export via front-panel ports is not supported (see Section 5 Exemptions). |
| 3 | **Kernel genetlink dependency** | The `NET_DM` genetlink family must be supported by the kernel. Minimum kernel version with genetlink drop monitor support required. |
| 4 | **SAI TAM capability required** | If the platform SAI does not support `SAI_TAM_REPORT_TYPE_GENETLINK`, the feature is silently disabled at startup with a warning log. No error is raised. |
| 5 | **Policer CIR/CBS not configurable** | Policer parameters (CIR=1000 pps, CBS=2000) are hardcoded. High-rate drop events exceeding this limit are silently dropped at the policer. CLI configuration of CIR/CBS is a future enhancement. |
| 6 | **Single collector per session** | Only one TAM collector is supported per drop monitor session in this release. Multi-collector support is a future enhancement. |
| 7 | **No gRPC export** | Telemetry export to collectors uses IPFIX only. gRPC-based export is not supported in this release (see Section 5 Exemptions). |
| 8 | **Stateful mode flow table size** | The number of concurrent tracked flows in stateful mode is bounded by available Redis memory and the configured `aging-interval`. No hard per-session flow limit is enforced in software; platform hardware may impose limits. |
| 9 | **No per-port scoping without flowgroup** | Without a configured `flowgroup`, drop monitoring applies globally to all traffic on all ports. Per-port scoping requires an ACL flow group referencing specific ports. |

### 13. Testing Requirements/Design

TAM MOD testing covers unit tests (component-level), system tests (end-to-end), scale tests, and warmboot/fastboot regression. The warmboot requirement of zero data-plane disruption must continue to be met — TAM MOD introduces no forwarding-path dependency, so no regression is expected.

---

#### 13.1 Unit Test Cases

##### 13.1.1 CONFIG_DB Schema Validation

| Test | Pass Criteria |
| --- | --- |
| `TAM_SWITCH|device` with valid IPv4 `switch-id` | Entry accepted, propagated to APPL_DB |
| `TAM_SWITCH|device` with invalid IP (e.g. `"abc"`) | YANG validation rejects with error |
| `TAM_COLLECTORS` with `port` outside 1–65535 | YANG validation rejects |
| `TAM_SAMPLINGRATE` with `rate=0` | YANG validation rejects |
| `TAM_DROPMONITOR` with `aging-interval=0` | YANG validation rejects |
| `TAM_DROPMONITOR_SESSIONS` with `collector` referencing non-existent entry | leafref validation rejects |
| `TAM_DROPMONITOR_SESSIONS` with `sample-rate` referencing non-existent entry | leafref validation rejects |

##### 13.1.2 tammgrd CONFIG_DB → APPL_DB Propagation

| Test | Pass Criteria |
| --- | --- |
| Add `TAM_SWITCH` entry | `APP_TAM_SWITCH_TABLE` entry created in APPL_DB |
| Add `TAM_COLLECTORS` entry | `APP_TAM_COLLECTOR_TABLE` entry created in APPL_DB |
| Add `TAM_SAMPLINGRATE` entry | `APP_TAM_SAMPLER_TABLE` entry created in APPL_DB |
| Set `TAM_FEATURES\|DROPMONITOR` status to `ACTIVE` | `APP_TAM_DROPMONITOR_TABLE` `status=enable` set |
| Delete `TAM_COLLECTORS` entry | Corresponding APPL_DB entry removed |
| Update `TAM_DROPMONITOR` `aging-interval` | APPL_DB entry updated without daemon restart |
| tammgrd initialises `COUNTERS_TAM_DM_TABLE\|global` on startup | Entry exists in COUNTERS_DB with default aging/poll values |

##### 13.1.3 tamOrch SAI Object Creation and Rollback

| Test | Pass Criteria |
| --- | --- |
| `APP_TAM_DROPMONITOR_TABLE` `status=enable` received | All 12 SAI objects created in dependency order; `SAI_SWITCH_ATTR_TAM_OBJECT_ID` set |
| Inject SAI failure at step N (for N=1..11) | All previously created objects rolled back; tamOrch returns to DISABLED state |
| `sai_tam_api == nullptr` (unsupported platform) | Feature silently disabled; warning logged; no crash |
| `APP_TAM_DROPMONITOR_TABLE` `status=disable` received | `SAI_SWITCH_ATTR_TAM_OBJECT_ID` cleared first; all objects deleted in reverse order (12 → 1) |
| Re-enable after disable | Second enable creates all 12 objects cleanly |

##### 13.1.4 tamOrch State Machine Transitions

| Test | Pass Criteria |
| --- | --- |
| Initial state is DISABLED | No SAI objects exist |
| enable → CREATING → ENABLING → ENABLED | All transitions logged at NOTICE level |
| SAI failure during CREATING | Transition back to DISABLED; objects cleaned up |
| disable from ENABLED | Transition through DISABLING → DELETING → DISABLED |
| Config update (non-status field) while ENABLED | State remains ENABLED; no object recreation |

##### 13.1.5 TAM Agent Genetlink Handling

| Test | Pass Criteria |
| --- | --- |
| `NET_DM_ORIGIN_HW` message received | 5-tuple, drop-reason, port, queue extracted; written to COUNTERS_DB |
| `NET_DM_ORIGIN_SW` message received | Message discarded; no COUNTERS_DB write |
| Malformed genetlink message | Discarded with error log; no crash |
| Stateless mode enabled | Drop event exported immediately; no COUNTERS_DB entry written |
| Stateful mode: duplicate flow key received | Existing COUNTERS_DB entry's `drop-count` incremented |
| Aging expiry: flow inactive > `aging-interval` | COUNTERS_DB entry for that flow removed |

---

#### 13.2 System Test Cases

##### 13.2.1 Basic End-to-End Drop Detection

| Step | Expected Result |
| --- | --- |
| Configure TAM switch-id, collector, sampler, enable dropmonitor | All CONFIG_DB tables populated; APPL_DB propagated; SAI objects created |
| Generate traffic that causes ASIC ingress drops (e.g. ACL deny, TTL=0) | Drop events delivered via `NET_DM:events` genetlink |
| Poll `COUNTERS_TAM_DM_TABLE` in COUNTERS_DB | Per-flow entries appear with correct 5-tuple, drop-count, drop-reason, port, queue |
| Verify IPFIX export at collector | Collector receives IPFIX flow records corresponding to detected drops |

##### 13.2.2 Enable / Disable Lifecycle

| Step | Expected Result |
| --- | --- |
| Disable drop monitoring (`TAM_FEATURES\|DROPMONITOR` status=INACTIVE) | `SAI_SWITCH_ATTR_TAM_OBJECT_ID` cleared; all SAI objects deleted; drop events stop |
| Re-enable | SAI objects recreated; drop monitoring resumes |
| Repeat enable/disable 10 times | No resource leaks; ASIC_DB has correct object count each cycle |

##### 13.2.3 Sampling Rate

| Test | Expected Result |
| --- | --- |
| Set `rate=1` (1:1 — capture every drop) | All drops appear in COUNTERS_DB |
| Set `rate=10` (1:10) | Approximately 1 in 10 drops reported (within ±20% tolerance) |
| Change rate while feature is enabled | Updated rate takes effect without feature restart |

##### 13.2.4 Stateful Mode — Flow Aging

| Step | Expected Result |
| --- | --- |
| Generate drops for a specific 5-tuple flow | Entry created in `COUNTERS_TAM_DM_TABLE` |
| Stop generating drops; wait > `aging-interval` seconds | Entry removed from COUNTERS_DB |
| Verify no stale entries remain | `KEYS COUNTERS_TAM_DM_TABLE|*` returns only `global` and active flows |

##### 13.2.5 Stateless Mode

| Test | Expected Result |
| --- | --- |
| Set `monitor-mode=stateless`; generate drops | No per-flow entries written to COUNTERS_DB |
| Verify IPFIX export still occurs | Collector receives per-event IPFIX records without aggregation |

##### 13.2.6 CPU Policer Rate Limiting

| Test | Expected Result |
| --- | --- |
| Generate drops at rate > 1000 pps (CIR) | Policer drops excess events; CPU not overwhelmed |
| Verify system stability under >10k pps drop rate | No orchagent crash; no memory growth; switch remains stable |
| Verify policed events are silently dropped (not queued) | COUNTERS_DB growth stays bounded |

##### 13.2.7 Warmboot Regression

| Step | Expected Result |
| --- | --- |
| Enable TAM drop monitoring; verify SAI objects created | Baseline established |
| Trigger warm reboot | Zero data-plane downtime for production flows (existing warmboot SLA met) |
| After reboot, verify orchagent converges and recreates TAM SAI objects | All 12 SAI objects present in ASIC_DB |
| Generate drops after reboot | Drop monitoring resumes; COUNTERS_DB populated correctly |
| Measure additional warmboot stall introduced by TAM | Must be zero seconds additional stall |

##### 13.2.8 Fastboot Regression

| Test | Expected Result |
| --- | --- |
| TAM enabled; perform fastboot | Boot critical path (port/VLAN/route convergence) completes within existing SLA |
| TAM Docker starts after critical path | No TAM-related delays in critical-path logs |

---

#### 13.3 Scale Test Cases

| Test | Pass Criteria |
| --- | --- |
| High drop rate: sustain >10,000 pps drop events | CPU policer limits to ≤1000 pps; system stable; no memory growth after stabilization |
| Concurrent flows: 1000 unique 5-tuple flows dropping simultaneously (stateful) | All 1000 entries appear in COUNTERS_DB; total COUNTERS_DB growth ≤ 1 MB |
| Long-running stability: run drop monitoring continuously for 24 hours | No memory leaks in TAM Agent or tammgrd; COUNTERS_DB entries age out correctly; no daemon restarts |
| Repeated enable/disable: 100 rapid cycles | No ASIC resource exhaustion; final state is consistent with expected object count |

### 14. Open/Action items

| # | Item | Type | Notes |
| --- | --- | --- | --- |
| 1 | **TAM_DROPMONITOR_SESSIONS per-session SAI object mapping** | Design Gap | Section 9.2 defines the `TAM_DROPMONITOR_SESSIONS` CONFIG_DB table and Section 7.4 shows `tamOrch` handles a single global drop monitor. The mapping of per-session entries to individual SAI objects (separate `tam_event` + `tam_collector` per session, or a shared object with ACL flowgroup reference) is not yet designed. This must be resolved before per-session scoping can be implemented. |
| 2 | **IPFIX template format for drop records** | Design Gap | The IPFIX export format (template ID, field order, field encoding) used by the TAM Agent / Telemetry Container to encode `COUNTERS_TAM_DM_TABLE` entries into IPFIX flow records is not specified in this HLD. A separate IPFIX template specification is needed for collector interoperability. |
| 3 | **`show tam dropmonitor statistics` output format** | Design Gap | The CLI show command is listed in Section 9.4 but the tabular output format (column names, units, sorting) is not defined. This must be specified before the `sonic-utilities` PR is submitted. |
| 4 | **Configurable policer CIR/CBS via CLI** | Future Enhancement | Policer parameters are currently hardcoded (CIR=1000 pps, CBS=2000). Add `config tam dropmonitor policer --cir <pps> --cbs <pkts>` command and corresponding `TAM_DROPMONITOR` CONFIG_DB fields. Listed as Exemption in Section 5 and Restriction #5 in Section 12. |
| 5 | **Multi-collector support** | Future Enhancement | Only one TAM collector is supported per session (Section 12, Restriction #6). Support multiple collectors per session for redundancy or fan-out export to multiple monitoring systems. Requires changes to `TAM_DROPMONITOR_SESSIONS` schema and `tamOrch` SAI object creation. |
| 6 | **Egress MOD support** | Future Enhancement | Current implementation covers ingress drops only (IPP, MMU). Extending monitoring to egress pipeline drops (EPP) requires additional SAI bind points and separate event object types. Listed as Restriction #1 in Section 12. |
| 7 | **gRPC-based collector export** | Future Enhancement | Telemetry export currently uses IPFIX only. Add gRPC/gNMI export as an alternative transport for collector compatibility with modern streaming telemetry systems. Listed as Exemption in Section 5 and Restriction #7 in Section 12. |
| 8 | **Cross-platform drop reason normalization** | Future Enhancement | Drop reason codes in `COUNTERS_TAM_DM_TABLE` are currently platform-defined (SAI implementation-specific). A normalized drop reason enumeration (mapped from platform codes) would improve collector portability across different hardware platforms. |
| 9 | **PR merge order dependency** | Dependency | The following PRs must be merged in order: (1) `sonic-swss-common` — CONFIG_DB / APPL_DB / COUNTERS_DB table definitions; (2) `sonic-yang-models` — YANG models for TAM tables; (3) `sonic-swss` — `tamOrch` agent; (4) `sonic-buildimage` — TAM Docker container; (5) `sonic-utilities` — CLI commands. The `sonic-swss` PR cannot be merged until `sonic-swss-common` changes are available in the build environment. |
| 10 | **Minimum kernel version requirement** | Design Gap | Section 12 Restriction #3 notes that the `NET_DM` genetlink family requires a minimum kernel version. The exact minimum version (and which SONiC branches it applies to) needs to be confirmed and documented in the platform requirements. |


