<!-- omit in toc -->
# MACsec MKA Operational State and Key Rotation — SONiC High Level Design

***Revision***

| Rev | Date | Author | Change Description |
| :-: | :--: | :----- | ------------------ |
| 0.1 | | Liam Kearney | Initial version |

<!-- omit in toc -->
## Table of Contents

- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [1 Requirements](#1-requirements)
- [2 Background](#2-background)
  - [2.1 Existing fallback-CA behavior](#21-existing-fallback-ca-behavior)
  - [2.2 Existing MACsec database path](#22-existing-macsec-database-path)
  - [2.3 Existing WPA status dependency](#23-existing-wpa-status-dependency)
- [3 Database Design](#3-database-design)
  - [3.1 CONFIG_DB MACsec profile](#31-configdb-macsec-profile)
  - [3.2 MKA session STATE_DB table](#32-mka-session-statedb-table)
  - [3.3 MKA participant STATE_DB table](#33-mka-participant-statedb-table)
  - [3.4 Example records](#34-example-records)
- [4 macsecmgrd Status Collection](#4-macsecmgrd-status-collection)
  - [4.1 Existing-field mapping](#41-existing-field-mapping)
  - [4.2 Parsing and normalization](#42-parsing-and-normalization)
  - [4.3 Snapshot reconciliation](#43-snapshot-reconciliation)
  - [4.4 Refresh and freshness](#44-refresh-and-freshness)
  - [4.5 Failure and deletion behavior](#45-failure-and-deletion-behavior)
  - [4.6 Multi-ASIC locality](#46-multi-asic-locality)
- [5 Configuration Commands](#5-configuration-commands)
  - [5.1 Profile creation](#51-profile-creation)
  - [5.2 Replacement-by-old-CKN update](#52-replacement-by-old-ckn-update)
  - [5.3 Desired configuration acceptance](#53-desired-configuration-acceptance)
  - [5.4 Desired state and runtime convergence](#54-desired-state-and-runtime-convergence)
- [6 macsecmgrd Hot-Rollover Actioning](#6-macsecmgrd-hot-rollover-actioning)
  - [6.1 Common reconciliation model](#61-common-reconciliation-model)
  - [6.2 Primary rollover](#62-primary-rollover)
  - [6.3 Fallback rollover](#63-fallback-rollover)
  - [6.4 Failure, idempotency, and retry](#64-failure-idempotency-and-retry)
  - [6.5 Operational observability](#65-operational-observability)
- [7 Show Command](#7-show-command)
  - [7.1 Command form](#71-command-form)
  - [7.2 Compact output](#72-compact-output)
  - [7.3 Interface-specific output](#73-interface-specific-output)
- [8 Process and Container Restart](#8-process-and-container-restart)
- [9 Security Considerations](#9-security-considerations)
- [10 Backward Compatibility](#10-backward-compatibility)
- [11 Test Plan](#11-test-plan)
- [12 Rollout and Dependency Ordering](#12-rollout-and-dependency-ordering)

## About this Manual

This document describes the **SONiC-side integration** for MACsec Key Agreement
(MKA) operational state, desired key configuration, safe per-port runtime
reconciliation, and operator-facing show commands.

It is a companion to:

- [MACsec Fallback CAK — wpa_supplicant High Level Design](MACsec_fallback_cak_hld.md),
  which owns the fallback-CA behavior and all WPA supplicant design; and
- [MACsec SONiC High Level Design](MACsec_hld.md), which owns the existing
  CONFIG_DB, APP_DB, SecY programming, MACsecOrch, and SAI design.

Companion implementation pull requests:

- [sonic-swss-common#1251](https://github.com/sonic-net/sonic-swss-common/pull/1251)
  — shared STATE_DB table-name constants;
- [sonic-swss#4827](https://github.com/sonic-net/sonic-swss/pull/4827)
  — macsecmgrd publication, safety validation, and rollover actioning;
- [sonic-buildimage#29102](https://github.com/sonic-net/sonic-buildimage/pull/29102)
  — docker-macsec config and show commands; and
- [sonic-wpa-supplicant#138](https://github.com/sonic-net/sonic-wpa-supplicant/pull/138)
  — frozen fallback-key control/status dependency.

**WPA supplicant is unchanged by this design.** This document consumes only the
existing `wpa_cli` control and status interfaces provided by the fallback-CA
feature. It does not propose a new command, field, alias, output format, parser
compatibility mode, test, API, or code change in `sonic-wpa-supplicant`.

## Scope

**In scope:**

- CONFIG_DB primary/fallback CA configuration semantics;
- two new macsecmgrd-owned STATE_DB tables for MKA session and participant
  state;
- collection and normalization of fields already available through existing
  WPA control/status commands;
- use of STATE_DB and immediate WPA status as safety inputs to runtime
  key-rotation actioning;
- replacement-by-old-CKN profile update commands;
- exact macsecmgrd remove-then-add rollover actioning;
- failure, retry, reconciliation, freshness, restart, namespace, and security
  behavior;
- `show macsec --mka` and `show macsec --mka <interface>`; and
- SONiC-side repository and test impact.

**Out of scope:**

- any change to WPA supplicant, `sonic-wpa-supplicant`, KaY, MKA state
  machines, peer liveness, principal selection, key-server election, or status
  output;
- staging a third participant or make-before-break CA replacement;
- changes to MACsecOrch, SAI, vendor SDKs, or the existing dataplane schema;
- automatic or scheduled CAK rotation;
- fleet-wide rotation coordination; and
- exposing CAK, SAK, ICK, KEK, authentication keys, or derived key material.

## Abbreviations

| Abbreviation | Description |
| ------------ | ----------- |
| CA | Secure Connectivity Association |
| CAK / CKN | Connectivity Association Key / CA Key Name |
| CP | Controlled Port state machine |
| ICK | Integrity Check Key |
| KaY | MACsec Key Agreement Entity |
| KEK | Key Encryption Key |
| MI / MN | Member Identifier / Message Number |
| MKA | MACsec Key Agreement protocol |
| SA / SAK | Secure Association / Secure Association Key |
| SC / SCI | Secure Channel / Secure Channel Identifier |
| SecY | MACsec Security Entity |

## 1 Requirements

1. SONiC must publish MKA session and participant state for every configured
   MACsec interface without overloading existing ASIC-programming tables.
2. The state must be collected only from status fields already exposed by the
   fallback-CA WPA implementation.
3. The new STATE_DB tables must be owned and populated by `macsecmgrd`.
4. A transient query failure must preserve the last successful data while
   prominently reporting that the data is no longer healthy/current.
5. Explicit MACsec disable must remove all MKA operational rows for the port.
6. Participant identity must be interface plus normalized CKN, never WPA list
   position.
7. No key material may be published or rendered. CKN is an identifier and may
   be exposed.
8. `config macsec profile update` must be a replacement-by-old-CKN command for
   an existing profile that already contains complete primary and fallback
   CAK/CKN pairs.
9. The CLI must reject primary-only profile updates before CONFIG_DB mutation,
   whether the profile is attached or unattached. The supported replacement
   workflow for a primary-only profile is to create a new profile and rebind
   the affected port or ports. All supplied CAK/CKN arguments must form complete
   required pairs and pass normal parameter validation.
10. After structural CLI validation, CONFIG_DB is authoritative desired state.
    Runtime MKA health, freshness, port status, and participant state must not
    gate the desired profile write.
11. `macsecmgrd` must cache valid desired CONFIG_DB profiles, including direct
    primary-only changes from management paths other than this CLI, and
    reconcile each owned port independently against its exact applied runtime
    profile.
12. Immediately before destructive mutation, `macsecmgrd` must obtain a fresh
    authoritative WPA snapshot and classify the applied runtime as peerless,
    peer-bearing, or unknown.
13. An authoritatively peerless runtime may apply a replacement without a live
    alternate. A peer-bearing runtime must retain the strict protected-state
    and live-alternate proof. Unknown or unqueryable runtime must fail closed.
14. Safe sibling ports must not be blocked by an unsafe port using the same
    profile. Completed ports remain complete; deferred ports retain their exact
    applied and pending state for idempotent retry.
15. Rollover must remove the old participant before adding its replacement.
    No third participant is staged.
16. Remove failure must abort the current port before add. Add failure after
    successful remove must preserve truthful per-port applied/pending state and
    must not roll desired CONFIG_DB back.
17. `show macsec --mka` must make query failure, data age, and
    desired-vs-runtime inconsistency conspicuous.
18. Multi-ASIC systems must keep publication and safety decisions namespace
    local while allowing the show/config commands to aggregate correctly.
19. Each namespace-local `macsecmgrd` instance must be the sole writer of its
    MKA session and participant STATE_DB tables.
20. Periodic collection must sweep all configured MACsec ports in the local
    namespace every 20 seconds, querying them sequentially with a hard
    two-second deadline per port and without overlapping timer executions.
21. A failed query for one port must not stop collection for later ports in the
    same namespace.
22. The peer-bearing hitless path must require the healthy protected Controlled
    Port state:
    `kay_status=active`, `authenticated=false`, `secured=true`, and
    `failed=false`. Authenticated-only unprotected mode and inconsistent state
    combinations must be rejected.
23. Compact MKA output must report primary and fallback live-peer counts from
    the configured `is_primary` roles independently of current principal
    ownership. Missing, duplicate, malformed, or unclassifiable role state must
    render as unknown rather than being inferred from `is_principal`.

## 2 Background

### 2.1 Existing fallback-CA behavior

The companion fallback-CA HLD allows one primary and one optional fallback MKA
participant on a port. Both participants are configured concurrently, but only
one is **principal** and owns the Controlled Port. The primary is preferred
when eligible. If the primary is removed or loses its live peer, the fallback
can become principal and carry traffic.

Configured role and current ownership are different properties:

- `is_primary=true` identifies the one configured privileged/revertive CA;
  `is_primary=false` identifies a best-effort participant, represented by
  SONiC's configured fallback CA; and
- `is_principal` identifies the CA currently owning the Controlled Port.

At most one participant may have `is_primary=true`. The primary owns the
Controlled Port whenever eligible and reclaims it after becoming live again.
Therefore `is_primary=false,is_principal=true` is valid for the configured
fallback during primary failure or rotation.

This document relies on that existing behavior. It does not redefine or modify
it.

### 2.2 Existing MACsec database path

The current dataplane path is:

```text
wpa_supplicant / SONiC MACsec plugin
        |
        | MACSEC_PORT and MACSEC_{INGRESS,EGRESS}_{SC,SA}
        v
      APP_DB
        |
        v
   MACsecOrch
        |
        | SAI programming result
        v
     STATE_DB
```

The existing `MACSEC_PORT_TABLE`, SC tables, and SA tables represent
SecY/ASIC programming. They are owned by MACsecOrch and must retain that
meaning.

The MKA control-plane status path is separate:

```text
existing WPA control/status output
        |
        v
    macsecmgrd
        |
        | normalized operational state
        v
MACSEC_MKA_SESSION_TABLE
MACSEC_MKA_PARTICIPANT_TABLE
        |
        +--> config macsec profile update (safety checks)
        |
        +--> show macsec --mka
```

### 2.3 Existing WPA status dependency

`macsecmgrd` uses the existing `wpa_cli ... macsec_mka_list` and associated
status output defined by the fallback feature. The available session fields
are:

```text
PAE KaY status
Authenticated
Secured
Failed
Actor Priority
Key Server Priority
Is Key Server
Number of Keys Distributed
Number of Keys Received
MKA Hello Time
actor_sci
key_server_sci
```

The available participant fields are:

```text
participant_idx
ckn
mi
mn
active
retain
is_principal
is_primary
live_peers
potential_peers
is_key_server
is_elected
```

Every field proposed below maps to one of these existing values or to
macsecmgrd-derived metadata. This HLD and the companion fallback-CA HLD form
one coupled feature set; this design consumes that existing status contract
without adding or negotiating an alternative WPA format.

## 3 Database Design

### 3.1 CONFIG_DB MACsec profile

The existing profile schema contains:

```rfc5234
MACSEC_PROFILE|{{profile}}
    "primary_cak":{{encoded_cak}}
    "primary_ckn":{{ckn}}
    "fallback_cak":{{encoded_cak}} (OPTIONAL)
    "fallback_ckn":{{ckn}} (OPTIONAL)
    ... existing profile fields ...
```

Semantics:

- primary CAK and CKN are required;
- fallback CAK and CKN are optional but must be supplied together;
- primary and fallback CKN must differ;
- primary and fallback encoded CAK lengths must be compatible with the
  configured cipher suite and with each other;
- a CKN identifies one configured MKA participant; and
- CAK values remain CONFIG_DB secrets and never enter the new operational
  tables.

Primary-only and paired primary/fallback profiles are both valid CONFIG_DB
states. The dual-CA requirement applies specifically to
`config macsec profile update`, whose purpose is hitless in-place replacement.
It does not restrict the CONFIG_DB schema or macsecmgrd's ingestion of desired
state written by another management path.

A direct desired profile change can request a transition that is not currently
safe to apply—for example, a primary-only runtime with peers and no alternate
CA. macsecmgrd still caches that desired state. It retains the old applied
runtime, publishes a degraded desired-vs-applied mismatch, and performs no
destructive action until the runtime can be reconciled safely or a later
desired profile supersedes the request.

### 3.2 MKA session STATE_DB table

`sonic-swss-common/common/schema.h` adds:

```cpp
#define STATE_MACSEC_MKA_SESSION_TABLE_NAME "MACSEC_MKA_SESSION_TABLE"
#define STATE_MACSEC_MKA_PARTICIPANT_TABLE_NAME "MACSEC_MKA_PARTICIPANT_TABLE"
```

Session schema:

```rfc5234
MACSEC_MKA_SESSION_TABLE|{{interface}}
    "profile":{{profile}}
    "kay_status":{{active|not-active}}
    "authenticated":{{true|false}}
    "secured":{{true|false}}
    "failed":{{true|false}}
    "actor_sci":{{sci}}
    "key_server_sci":{{sci}}
    "actor_priority":{{priority}}
    "key_server_priority":{{priority}}
    "is_key_server":{{true|false}}
    "keys_distributed":{{count}}
    "keys_received":{{count}}
    "mka_hello_time_ms":{{milliseconds}}
    "query_status":{{ok|error}}
    "last_updated":{{utc_timestamp}}
    "config_status":{{in-sync|degraded}}
    "config_error":{{text}} (OPTIONAL)
```

| STATE_DB field | Existing source | Normalization / meaning |
| -------------- | --------------- | ----------------------- |
| `profile` | CONFIG_DB port attachment | Effective profile name |
| `kay_status` | `PAE KaY status` | `active` or `not-active` |
| `authenticated` | `Authenticated` | Controlled Port authenticated-only/unprotected mode; WPA `Yes`/`No` to lowercase boolean |
| `secured` | `Secured` | Controlled Port is MACsec protected; WPA `Yes`/`No` to lowercase boolean |
| `failed` | `Failed` | Controlled Port failure state; WPA `Yes`/`No` to lowercase boolean |
| `actor_sci` | `actor_sci` | Normalize `MAC@port` to 16 lowercase hex digits |
| `key_server_sci` | `key_server_sci` | Same SCI normalization; all-zero is valid before election |
| `actor_priority` | `Actor Priority` | Unsigned integer |
| `key_server_priority` | `Key Server Priority` | Unsigned integer |
| `is_key_server` | `Is Key Server` | WPA `Yes`/`No` to lowercase boolean |
| `keys_distributed` | `Number of Keys Distributed` | Unsigned integer |
| `keys_received` | `Number of Keys Received` | Unsigned integer |
| `mka_hello_time_ms` | `MKA Hello Time` | Milliseconds |
| `query_status` | macsecmgrd | Health of the latest collection attempt |
| `last_updated` | macsecmgrd | UTC time of the last successful query |
| `config_status` | macsecmgrd | Whether desired CONFIG_DB and applied participant roles/CKNs agree |
| `config_error` | macsecmgrd | Redacted reason for a degraded apply/reconciliation state |

`query_status` describes observation health; `config_status` describes
desired-vs-runtime agreement. They are intentionally independent.
`last_updated` is independent from both and records only the last successful
validated query. No derived `freshness` field is stored; config and show
consumers calculate age from `last_updated`.

`config_status` is per port. After one desired profile write, one port can be
`in-sync` while another remains `degraded` with its old applied profile. A
healthy snapshot of the old applied runtime can therefore have
`query_status=ok,config_status=degraded`; the observation is trustworthy even
though runtime has not converged to CONFIG_DB.

The WPA/IEEE Controlled Port fields are not cumulative success flags. Healthy
protected operation is `authenticated=false,secured=true,failed=false`.
`authenticated=true,secured=false` means authenticated-only Controlled Port
operation without MACsec protection; it is not the healthy protected state.
The `authenticated` field therefore must not be presented as “MKA
authentication succeeded.”

`macsecmgrd` is the sole writer of this table in each namespace.

### 3.3 MKA participant STATE_DB table

```rfc5234
MACSEC_MKA_PARTICIPANT_TABLE|{{interface}}|{{normalized_ckn}}
    "participant_index":{{index}}
    "mi":{{mi}}
    "mn":{{mn}}
    "active":{{true|false}}
    "retain":{{true|false}}
    "is_principal":{{true|false}}
    "is_primary":{{true|false}}
    "live_peers":{{count}}
    "potential_peers":{{count}}
    "is_key_server":{{true|false}}
    "is_elected":{{true|false}}
```

| STATE_DB field | Existing WPA field | Normalization / meaning |
| -------------- | ------------------ | ----------------------- |
| `participant_index` | `participant_idx` | Diagnostic only; never identity |
| `mi` | `mi` | Lowercase hexadecimal MI |
| `mn` | `mn` | Unsigned integer |
| `active` | `active` | WPA `Yes`/`No` to lowercase boolean |
| `retain` | `retain` | WPA `Yes`/`No` to lowercase boolean |
| `is_principal` | `is_principal` | Current Controlled Port owner |
| `is_primary` | `is_primary` | Privileged/revertive configured role |
| `live_peers` | `live_peers` | Unsigned peer count |
| `potential_peers` | `potential_peers` | Unsigned peer count |
| `is_key_server` | `is_key_server` | Participant key-server state |
| `is_elected` | `is_elected` | Participant election state |

The normalized CKN in the key is the stable participant identity. CKN is an
identifier and is safe to expose. `participant_index` can change after process
restart or participant recreation.

The remaining fields carry distinct operational meaning: `active` reports
participant activity, `is_principal` reports current Controlled Port
ownership, `is_primary` reports the configured privileged/revertive role,
`live_peers` and `potential_peers` report peer state, and the key-server fields
report election state.

The namespace-local `macsecmgrd` instance is also the sole writer of this
table.

### 3.4 Example records

Healthy primary and fallback:

```text
MACSEC_MKA_SESSION_TABLE|Ethernet0
    profile="mka-rotation"
    kay_status="active"
    authenticated="false"
    secured="true"
    failed="false"
    actor_sci="0011223344550001"
    key_server_sci="0011223344550001"
    actor_priority="16"
    key_server_priority="16"
    is_key_server="true"
    keys_distributed="7"
    keys_received="0"
    mka_hello_time_ms="2000"
    query_status="ok"
    last_updated="2026-09-15T01:14:52Z"
    config_status="in-sync"

MACSEC_MKA_PARTICIPANT_TABLE|Ethernet0|00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
    participant_index="0"
    mi="102030405060708090a0b0c0"
    mn="482"
    active="true"
    retain="false"
    is_principal="true"
    is_primary="true"
    live_peers="1"
    potential_peers="0"
    is_key_server="true"
    is_elected="true"

MACSEC_MKA_PARTICIPANT_TABLE|Ethernet0|ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100
    participant_index="1"
    mi="c0b0a0908070605040302010"
    mn="319"
    active="true"
    retain="false"
    is_principal="false"
    is_primary="false"
    live_peers="1"
    potential_peers="0"
    is_key_server="true"
    is_elected="true"
```

After the primary is removed during rollover, the fallback can be principal:

```text
MACSEC_MKA_PARTICIPANT_TABLE|Ethernet0|ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100
    participant_index="0"
    mi="c0b0a0908070605040302010"
    mn="324"
    active="true"
    retain="false"
    is_principal="true"
    is_primary="false"
    live_peers="1"
    potential_peers="0"
    is_key_server="true"
    is_elected="true"
```

The combination `is_primary=false,is_principal=true` is expected and means the
configured fallback/best-effort participant currently owns the Controlled
Port.

## 4 macsecmgrd Status Collection

### 4.1 Existing-field mapping

`macsecmgrd` invokes only existing WPA commands and parses only the fields
listed in §2.3. It does not request an output extension or infer a field that
WPA does not report.

In particular, macsecmgrd does not require, synthesize, or publish the removed
WPA `participant` management field.

Metadata not supplied by WPA is narrowly defined:

- `profile` comes from CONFIG_DB;
- `query_status` and `last_updated` describe collection;
- `config_status` and `config_error` describe desired-vs-runtime
  reconciliation.

### 4.2 Parsing and normalization

The daemon parses a command response into typed session and participant
structures before writing STATE_DB.

Validation includes:

- all required session fields are present and unique;
- each participant block contains all existing required participant fields;
- booleans accept the existing WPA `Yes`/`No` spelling and serialize as
  lowercase `true`/`false`;
- integers are valid and in implementation range;
- CKN, MI, and SCI values are valid;
- CKN is normalized to lowercase;
- no two participant blocks normalize to the same CKN; and
- no more than one participant claims `is_principal=true`; and
- no more than one participant claims `is_primary=true`.

Unknown fields can be ignored with a debug log. Missing, duplicate, malformed,
or partial known fields reject the response. Rejection follows the query-error
behavior in §4.5.

The parser targets one existing fallback-feature status format. It does not
translate between WPA variants.

### 4.3 Snapshot reconciliation

macsecmgrd's per-port `applied_profile` defines the expected participant set.
This lets SONiC validate completeness using only the existing WPA response,
including while desired CONFIG_DB and applied runtime differ.

On a successful normal-state query:

1. every expected runtime CKN must be present exactly once;
2. no unexpected CKN may be present;
3. the applied primary CKN must have `is_primary=true`;
4. if the applied profile has a fallback CKN, it must have
   `is_primary=false`;
5. configured roles must agree with macsecmgrd's applied state; and
6. the session and every participant block must validate.

Only then does macsecmgrd:

- replace the session fields;
- upsert every returned participant row;
- delete rows absent from the validated expected set;
- set `query_status=ok`;
- advance `last_updated`; and
- set `config_status=in-sync` when desired and applied state agree, otherwise
  set `config_status=degraded` with a redacted mismatch reason.

During a managed remove/add operation, macsecmgrd updates its expected runtime
set only after the corresponding existing control command succeeds. This
allows an intentional one-participant interval without mistaking it for a
truncated response.

If the response is syntactically valid but disagrees with the expected applied
runtime set, it is not a complete trustworthy observation: macsecmgrd follows
the query-error behavior in §4.5 and does not use that response as safety
evidence. A response that matches applied state but differs from desired
CONFIG_DB is publishable with `query_status=ok,config_status=degraded`; this is
how add/remove failures remain observable.

The same validated snapshot supports runtime peer classification:

- **peerless** — the actual participant CKN set exactly equals the CKN set in
  `applied_profile`; each participant is role-correct; no duplicate or
  unexpected participant exists; and every expected participant reports
  `live_peers=0` and `potential_peers=0`;
- **peer-bearing** — the participant set and roles are complete and valid, and
  any expected participant has a nonzero live or potential peer count; or
- **unknown** — query failure, stale data, a missing/duplicate/unexpected
  participant, a role mismatch, or a missing/malformed peer count.

Completeness is applied-profile aware. An applied primary-only runtime expects
exactly one primary participant. An applied paired runtime expects one primary
and one fallback participant. Missing evidence is never treated as zero peers,
and retained status from an earlier query cannot authorize mutation.

### 4.4 Refresh and freshness

Periodic collection is a full sweep of every configured MACsec port in the
local namespace every 20 seconds. `macsecmgrd` executes the sweep sequentially
in its single-threaded event loop. Each `macsec_mka_list` query has a hard
two-second deadline. Timer executions never overlap; a later timer execution
does not begin while the preceding sweep is still running.

If one port query times out or fails, only that interface follows the
query-error behavior in §4.5. The sweep continues with every later port in the
namespace.

Immediate queries at daemon startup, MACsec enable, rollover safety
revalidation, after successful participant remove/add, and after WPA control
reconnection use the same bounded query path and two-second per-query deadline.

`last_updated` is an ISO 8601 UTC timestamp of the last successful validated
query, not the last state change.

The config and show commands consider a snapshot stale once its age exceeds
60 seconds. Freshness is derived from `last_updated`; it is not stored in
STATE_DB.

### 4.5 Failure and deletion behavior

On query timeout, command failure, parse failure, or unexpected participant
set:

- preserve the last successful session fields;
- preserve participant rows;
- set `query_status=error`;
- do not advance `last_updated`;
- do not delete participant rows; and
- log the interface and reason without key material.

During a periodic namespace sweep, this error handling is per interface. A
failure does not stop or invalidate successful observations for other ports,
and collection proceeds to the next port.

Before any successful query, a minimal row may contain:

```text
profile="<profile>"
query_status="error"
config_status="<in-sync|degraded>"
config_error="<redacted reason>" (optional)
```

Unknown WPA values are omitted rather than fabricated as false, zero, or empty.

Explicit MACsec disable deletes the session row and all participant rows for
that interface immediately.

### 4.6 Multi-ASIC locality

The `macsecmgrd` instance controlling an interface writes only to that
interface's namespace-local STATE_DB.

The config and show commands use existing namespace/interface helpers to:

- locate every attached port in its owning namespace;
- read the correct session and participant rows;
- aggregate all-interface output; and
- keep identical CKNs on different interfaces or namespaces distinct.

## 5 Configuration Commands

### 5.1 Profile creation

```text
sudo config macsec profile add <profile> \
  --primary_cak <encoded-cak> --primary_ckn <ckn> \
  [--fallback_cak <encoded-cak> --fallback_ckn <ckn>] \
  [existing profile options]
```

Validation:

- primary CAK and CKN are required arguments;
- fallback CAK and CKN are optional as a pair; if either fallback argument is
  supplied, both are required;
- fallback CKN must differ from primary CKN;
- CKNs must be valid hexadecimal of the supported length;
- encoded CAKs must be valid hexadecimal in the existing encoded-key format;
- decoded CAK length must match the cipher suite; and
- primary/fallback encoded CAK lengths must satisfy the existing schema.

Profile creation supports primary-only and paired primary/fallback profiles.
A primary-only profile can be attached and used normally, but it is not
eligible for `config macsec profile update`. To replace its key through the
supported CLI, the operator creates a new profile and rebinds the affected port
or ports. This restriction belongs to the update command; it does not redefine
the CONFIG_DB schema or macsecmgrd's ingestion of direct desired-state changes.

### 5.2 Replacement-by-old-CKN update

```text
sudo config macsec profile update <profile> \
  --old_ckn <current-primary-or-fallback-ckn> \
  --new_ckn <replacement-ckn> \
  --new_cak <replacement-encoded-cak>
```

Semantics:

- before mutation, the existing profile must contain the required primary
  CAK/CKN pair and the required fallback CAK/CKN pair;
- `new_cak` and `new_ckn` are required replacement arguments;
- `old_ckn` must match exactly the configured primary or fallback CKN;
- `new_ckn` must differ from `old_ckn` and from the other configured CKN;
- same-CKN CAK replacement is rejected because the existing participant is
  keyed by CKN;
- update replaces one CA only;
- update does not add or remove a fallback;
- all unrelated profile fields remain unchanged;
- new CAK/CKN encoding and cipher-suite validation matches profile creation;
  and
- each command invocation replaces exactly the one CA selected by `old_ckn`.
  Replacing both roles requires two CLI invocations or a desired profile written
  through another management path; the command never adds the first fallback
  or removes the configured fallback.

A primary-only profile is rejected before CONFIG_DB mutation, whether attached
or unattached:

```text
Profile update requires configured primary and fallback CAK/CKN pairs;
create a new profile and rebind ports to replace a primary-only profile.
```

The error never includes CAK material. A structurally valid paired profile can
be updated whether attached or unattached. Attachment affects runtime
reconciliation, not desired-state acceptance.

Missing one member of any CAK/CKN pair is ordinary invalid-parameter handling,
not a separate update workflow. The command reports the missing required
argument and performs no CONFIG_DB mutation.

This is CLI validation only. A profile written by another management path
remains authoritative CONFIG_DB desired state, including a direct primary-only
change. macsecmgrd caches it and applies the runtime safety model in §6 rather
than rejecting desired-state ingestion.

### 5.3 Desired configuration acceptance

The config command validates profile structure and replacement semantics only:

- every supplied key definition contains its required CAK and CKN;
- the existing profile has the required primary and fallback CAK/CKN pairs;
- `old_ckn` selects one configured CA;
- replacement CKN and CAK pass uniqueness, encoding, length, and cipher-suite
  checks; and
- unrelated fields and the paired profile shape remain unchanged.

Once those checks pass, the command performs one CONFIG_DB profile write.
Runtime MKA state is not a desired-config write gate. In particular,
`query_status`, `config_status`, `last_updated`, Controlled Port state,
participant roles, live/potential peer counts, administrative state, and
operational state are not read to decide whether desired configuration may
advance.

Ports without an owned runtime session do not block the write. Their next
normal enable/session-creation path uses the latest desired profile directly
when the existing port-ready gate allows creation.

### 5.4 Desired state and runtime convergence

After any CONFIG_DB profile change, macsecmgrd caches the desired profile and
evaluates every tracked port independently.

For each owned runtime session whose `applied_profile` differs from desired
state, macsecmgrd obtains a fresh bounded WPA snapshot immediately before
action and classifies the applied runtime as peerless, peer-bearing, or
unknown using §4.3:

- a **peerless** port can apply the desired replacement immediately without a
  live alternate;
- a **peer-bearing** port uses the strict hitless protected-state and
  live-alternate preflight; and
- an **unknown** port is not modified.

Before runtime safety is authorized, macsecmgrd performs no destructive
mutation. A port for which neither peerless nor hitless authorization can be
proved—because status is unknown, query-failed, incomplete, malformed, or
peer-bearing without a live alternate—retains its current applied runtime,
publishes `config_status=degraded` with a redacted pending reason, and retries
later. Administrative or operational down state alone is neither authorization
nor a blocker: an owned down runtime with fresh authoritative zero-peer proof
uses the peerless path, while a down runtime without that proof remains
pending.

After a destructive step has succeeded, macsecmgrd records the observed
partial progress rather than claiming the original runtime is intact. Applied
and pending state truthfully identify which role was removed or replaced and
which work remains.

Ports are independent. A safe or authoritatively peerless port can complete
even when another port using the same profile remains degraded. Completed
ports are skipped on retry. Desired CONFIG_DB is never rolled back because one
runtime port cannot converge.

Runtime convergence may make partial progress within a port when desired state
already differs from the applied profile in both CA roles—for example, after a
direct CONFIG_DB update or after two CLI writes are coalesced before daemon
reconciliation. Roles are processed sequentially in a fixed order: primary
first, then fallback. Each role receives a new fresh classification immediately
before removal, and the successful add must be observed in a fresh status
snapshot before the next role is attempted. A first-role failure stops further
role changes for that port in the current pass, but does not stop other ports.

## 6 macsecmgrd Hot-Rollover Actioning

### 6.1 Common reconciliation model

`macsecmgrd` caches, per attached interface:

- latest desired profile;
- WPA network ID;
- exact per-port `applied_profile`;
- pending old CKN and role, when a replacement is interrupted; and
- the expected runtime participant set.

CONFIG_DB is authoritative desired state. On a profile update macsecmgrd caches
the desired profile and diffs it against each per-port `applied_profile`.
Profile processing continues across all tracked ports even if one cannot
reconcile. Ports already matching desired state are skipped on retry.

A missing owned runtime session is not failure. The desired profile remains
cached and the next normal enable creates the session directly from desired
state.

Hot reconciliation supports replacement of existing CKN identities. A direct
desired-state change that adds or removes the fallback role, changes non-key
profile fields, or replaces a CAK without changing its CKN can remain
`config_status=degraded`; this design does not promise runtime convergence for
unsupported transition shapes.

The daemon uses only existing WPA control commands from the fallback feature.
It does not create a temporary third participant.

The existing add command creates a primary when `fallback=1` is omitted and a
best-effort participant when `fallback=1` is present. WPA rejects adding a new
primary while another primary exists and requires the current primary to be
removed first. The existing delete path reruns election when the removed
participant was principal.

For an owned runtime that differs from desired state, macsecmgrd performs the
fresh classification defined in §4.3 immediately before mutation:

- **peerless applied runtime** — replacement is allowed without a live
  alternate. This includes a primary-only applied runtime when its sole primary
  participant is present, role-correct, and has zero live and potential peers;
- **peer-bearing applied runtime** — any live or potential peer on any applied
  CA requires the strict hitless path and a role-correct active alternate with
  at least one live peer; or
- **unknown applied runtime** — no participant mutation is allowed.

The complete expected participant set comes from `applied_profile`, not desired
state. A primary-only applied profile expects exactly one primary participant;
a paired applied profile expects one primary and one fallback participant.

If the already-accepted desired profile differs from applied state in both
roles, macsecmgrd processes at most two role replacements in one
profile-processing call, in fixed order: primary then fallback. This does not
mean one `config macsec profile update` invocation replaces two roles; the CLI
selects exactly one role with `old_ckn`. Each runtime role receives a fresh
preflight and immediate pre-remove query. The successful add must be observed
before the next role begins. Applied state advances after each observed
success.

### 6.2 Primary rollover

For each owned port whose applied primary differs from desired state:

1. query existing WPA status immediately before action;
2. classify the complete applied participant set;
3. if peerless, continue without alternate liveness; if peer-bearing, verify
   the configured fallback participant is present, role-correct, active, and
   has `live_peers >= 1`; if unknown, stop this port;
4. remove the current primary participant by old CKN using the existing
   `macsec_del_mka ckn=<old-primary-ckn>` command;
5. if removal succeeds, update the existing primary network configuration to
   the replacement CKN/CAK so reassociation cannot restore the old primary;
6. add the replacement with
   `macsec_add_mka ckn=<new-primary-ckn> cak=<new-cak>`; omitting
   `fallback=1` creates the primary;
7. query status immediately and require the replacement primary to be observed
   with the expected role before recording the role as applied; and
8. continue periodic reconciliation until the replacement is live and normal
   primary preference/principal ownership returns according to the existing
   WPA fallback design.

On the peer-bearing path, the established fallback carries the Controlled Port
between removal and add. On the peerless path, no live or potential peer exists,
so no peer traffic can be interrupted.

For a direct desired change from an applied primary-only runtime, the peerless
path can replace the sole primary without an alternate. If that primary has any
live or potential peer, the port remains degraded/pending because the hitless
path has no alternate.

### 6.3 Fallback rollover

For each owned port whose applied fallback differs from desired state:

1. query existing WPA status immediately before action;
2. classify the complete applied participant set;
3. if peerless, continue without primary liveness; if peer-bearing, verify the
   configured primary participant is present, role-correct, active, and has
   `live_peers >= 1`; if unknown, stop this port;
4. remove the old fallback participant by old CKN;
5. if removal succeeds, update the existing fallback network configuration to
   the replacement CKN/CAK;
6. add the replacement with
   `macsec_add_mka ckn=<new-fallback-ckn> cak=<new-cak> fallback=1`, which
   creates a best-effort participant with `is_primary=false`;
7. query status immediately and require the replacement fallback to be
   observed with the expected role before recording the role as applied; and
8. continue reconciliation until the replacement fallback is established.

On the peer-bearing path, the primary remains configured and carries traffic
throughout. If primary replacement completed earlier in the same pass, this
fallback preflight uses the new applied primary plus the old fallback and a new
fresh query; it is never authorized by the primary role's earlier snapshot.

### 6.4 Failure, idempotency, and retry

**Remove failure:**

- do not issue add;
- keep applied state pointing to the old participant;
- leave the surviving alternate untouched;
- set `config_status=degraded`;
- record a redacted `config_error`; and
- retry only after fresh safety validation.

The daemon does not claim that the old participant is absent merely because a
query failed.

**Network-configuration or add failure after successful remove:**

- never remove or reset the verified surviving CA;
- publish the successful one-participant status;
- keep desired CONFIG_DB as the authoritative requested profile;
- retain per-interface applied state showing the selected CA is absent;
- set `config_status=degraded` with a redacted reason; and
- retry the network update/add idempotently after fresh validation.

An add retry first queries status. If the replacement CKN is already present
with the expected role, the add is treated as complete rather than duplicated.
If the old CKN is still present after a reported remove success, the daemon
does not add a second participant; it marks the state degraded and
reconciles safely.

The surviving CA is never torn down as error recovery.

Runtime failure never rolls desired CONFIG_DB back. A failed port retains its
exact `applied_profile`, pending old CKN/role, and redacted configuration error.
If the first changed role fails, no later role is attempted for that port in
the current pass. If the first role succeeds and the second fails, the first
remains applied and only the incomplete role is retried. Other ports continue
independently.

The operation is bounded to the configured roles. No role already observed as
matching desired state is removed or added again on retry.

### 6.5 Operational observability

During successful primary rotation:

1. both participants initially exist and primary is principal;
2. the old primary row disappears after validated remove;
3. the fallback may show `is_primary=false,is_principal=true`;
4. the replacement primary row appears and gains a live peer; and
5. the replacement shows `is_primary=true`, and principal ownership reverts to
   it according to the existing WPA design.

During fallback rotation, the primary remains present/principal while the
fallback row changes.

If application fails, `query_status` continues to report collection health
while `config_status=degraded` reports CONFIG_DB-vs-runtime disagreement.

After one desired profile write, ports using that profile can temporarily show
different applied CKNs. A port can also temporarily contain a new primary and
old fallback when the first peerless role replacement succeeded and the second
remains pending. The operational tables remain truthful to each port's applied
runtime.

For a pending primary-only direct desired change, healthy query data for the
old applied primary can coexist with `config_status=degraded`. This means the
runtime is accurately observed but cannot yet be reconciled safely.

## 7 Show Command

### 7.1 Command form

The existing command accepts an optional positional interface, so MKA is
selected by an option rather than converting the command into a Click group:

```text
show macsec --mka
show macsec --mka Ethernet0
```

Existing `show macsec [interface]` output remains unchanged. `--mka` is
mutually exclusive with modes that replace the normal status view.

### 7.2 Compact output

```text
Interface  KaY     Secured Principal CKN   Role     Primary live peers Fallback live peers Local-KS Status                       Age
---------  ------  ------- --------------- -------- ------------------ ------------------- --------- ---------------------------- -----
Ethernet0  active  true    001122...ddeeff primary                    2                   1 true      ok                           2s
Ethernet8  active  true    89abcd...456789 fallback                   3                   4 false     query-error,config-degraded 18s
Ethernet16 active  true    ffeedd...221100 fallback                   0                   5 false     stale                        75s
Ethernet32 -       -       -               -                          -                   - -         query-unknown,config-unknown never
```

The compact view shows:

- interface;
- KaY and secured state;
- principal CKN and configured role;
- primary participant live-peer count;
- fallback/best-effort participant live-peer count;
- local key-server state;
- combined status; and
- age since the last successful validated update.

The displayed role is derived from `is_primary`: `primary` when true and
`fallback` (best-effort) when false. Principal ownership is resolved separately
from `is_principal`.

Primary and fallback live-peer counts are also derived from `is_primary`, not
from `is_principal`. The primary count comes from the single participant with
`is_primary=true`; the fallback count comes from the single participant with
`is_primary=false`. Thus a fallback can be principal while the two count
columns continue to describe both configured roles.

A role-derived count is displayed only when exactly one participant has that
role and its `live_peers` value is a valid unsigned integer. A missing role,
multiple participants claiming that role, or malformed `live_peers` renders
`-` for that role. If any participant has missing or malformed `is_primary`,
both role-derived columns render `-` because the participant set cannot be
partitioned safely. A primary-only profile therefore shows `-` for Fallback
live peers, not `0`.

A missing field renders as `-`, not a fabricated value.

Rows are sorted by natural interface order (`Ethernet0`, `Ethernet8`,
`Ethernet16`, not lexical `Ethernet0`, `Ethernet16`, `Ethernet8`), with
namespace as the secondary ordering key.

`Age` is derived only from `last_updated`; it is an elapsed duration or
`never` when no successful update exists. `Status` is `ok` only when
`query_status=ok`, `config_status=in-sync`, and age is at most 60 seconds.
Otherwise it combines concise independent flags:

- `query-error` or conservative `query-unknown`;
- `config-degraded` or conservative `config-unknown`;
- `stale` when age exceeds 60 seconds; and
- `never-updated` when age is `never`.

For example, a retained snapshot can show
`query-error,config-degraded,stale` while `Age` continues to report the time
since its last successful update.

`config-degraded` can also represent intentional pending convergence after a
desired profile write. In that case `query_status=ok` and a fresh Age can
truthfully describe the old or partially updated applied runtime while
CONFIG_DB already contains newer desired keys.

Compact `Status` deliberately describes observation freshness and
configuration consistency only. It does not duplicate Controlled Port state.
The separate `Secured` column is the compact protected/unprotected indication;
the detailed view derives one `Controlled port mode` value from the raw
`kay_status`, `authenticated`, `secured`, and `failed` fields. Consequently,
compact `Status=ok` is not by itself proof that a rotation is safe.

Removing Key-server SCI from the compact view does not change the detailed
session diagnostics; §7.3 continues to display Key server SCI.

### 7.3 Interface-specific output

The detailed view retains `PAE KaY status` and `Failed` as separate diagnostics.
It replaces only the raw `Authenticated` and `Secured` lines with one derived
`Controlled port mode`. The view also shows `config_status` and `config_error`,
followed by a participant table containing:

- full CKN;
- configured role;
- principal and active state;
- live and potential peer counts;
- key-server and election state;
- MI; and
- MN.

`participant_index` and `retain` remain in STATE_DB for diagnostics/forward
compatibility but are not operator-facing columns.

The raw session fields `kay_status`, `authenticated`, `secured`, and `failed`
remain in STATE_DB. The detailed CLI presents them as one derived
`Controlled port mode` field using this ordered mapping:

| Controlled port mode | Raw STATE_DB tuple |
| -------------------- | ------------------ |
| `unknown` | Any required field is missing or malformed |
| `failed` | `failed=true`, regardless of the other valid fields |
| `secured` | `kay_status=active,authenticated=false,secured=true,failed=false` |
| `authenticated-only` | `kay_status=active,authenticated=true,secured=false,failed=false` |
| `inactive` | `kay_status=not-active,authenticated=false,secured=false,failed=false` |
| `inconsistent` | Any other fully present, syntactically valid combination |

This derived field is presentation only. It does not replace the raw STATE_DB
fields or the exact protected-state tuple required by rotation safety
validation.

Example during primary rollover:

```text
$ show macsec --mka Ethernet0
Interface:            Ethernet0
Profile:              mka-rotation
PAE KaY status:       active
Controlled port mode: secured
Failed:               false
Actor SCI:            0011223344550001
Key server SCI:       0011223344550001
Actor priority:       16
Key server priority:  16
Local key server:     true
Keys distributed:     8
Keys received:        0
MKA hello time:       2000 ms
Query status:         ok
Config status:        in-sync
Last updated:         2026-09-15T01:15:02Z (2s ago)

CKN                                                               Role      Principal Active Live Potential Key-server Elected MI                       MN
----------------------------------------------------------------  --------  --------- ------ ---- --------- ---------- ------- ------------------------ ---
ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100  fallback  true      true      1         0 true       true    c0b0a0908070605040302010 324
```

When degraded, the detail view prints `config_error` prominently but never
prints key material.

## 8 Process and Container Restart

The new tables are operational cache rather than configuration.

On `macsecmgrd` restart:

1. enumerate configured local-namespace MACsec interfaces;
2. delete orphan rows for interfaces no longer configured;
3. mark retained configured rows `query_status=error` until revalidated;
4. restore latest desired profiles plus per-interface applied and pending
   reconciliation state;
5. rebuild network IDs and per-interface applied primary/fallback CKN state
   from CONFIG_DB plus existing runtime status;
6. immediately query each configured interface; and
7. replace retained rows after successful validation.

If CONFIG_DB and runtime participants disagree, publish
`config_status=degraded` and reconcile without deleting the known surviving CA.
Fresh post-restart status is required before classifying a pending runtime as
peerless; retained zero-peer data cannot authorize mutation after restart.

## 9 Security Considerations

The following must never appear in the new STATE_DB tables, show output, error
messages, or logs:

- primary or fallback CAK;
- SAK;
- ICK or KEK;
- authentication/hash keys; or
- derived key material.

CKN, SCI, MI, priorities, roles, state flags, and peer counts are identifiers
or operational state and may be exposed.

The config CLI and macsecmgrd must:

- use existing encoded-key handling;
- validate without echoing CAK values;
- redact secret-bearing command arguments from logs and exceptions;
- keep `config_error` free of key material; and
- preserve existing CONFIG_DB access controls.

Before displaying free-form `config_error`, docker-macsec applies
defense-in-depth redaction. It removes the currently configured encoded CAKs
and their decoded forms. It also removes stale CAK-shaped material: 66-, 128-,
and 130-hex-character secret shapes generally, and 64-hex-character values when
CAK/key-material context identifies them as secrets. CKN identifiers and
non-secret context such as interface names and explanatory error text remain
visible.

Tests poison input/configuration with sentinel secret values and assert that
neither STATE_DB nor `show macsec --mka` contains configured or decoded key
forms.

## 10 Backward Compatibility

- Primary-only profiles remain valid and publish one participant with
  `is_primary=true`.
- Existing profile fields and existing `show macsec [interface]` output are
  unchanged.
- Existing APP_DB and ASIC-facing STATE_DB tables are unchanged.
- WPA supplicant behavior and interfaces are unchanged by this design.
- Existing primary-only profiles remain valid for normal runtime operation.
  `config macsec profile update` intentionally rejects primary-only
  replacement, but direct CONFIG_DB changes remain authoritative desired state;
  macsecmgrd applies them only when its runtime safety rules permit.
- Structurally valid paired CLI updates write CONFIG_DB once and reconcile
  attached runtime sessions independently. Temporary per-port differences in
  applied CKNs are expected and exposed through `config_status`.

## 11 Test Plan

| # | Area | Scenario | Expected result |
| - | ---- | -------- | --------------- |
| 1 | Schema | Primary-only status | One session and one primary participant row; no secret fields |
| 2 | Schema | Primary plus fallback | Exactly one row has `is_primary=true`; the configured fallback has `is_primary=false` |
| 3 | Parser/schema | Current WPA participant fields, `Yes`/`No`, SCI, MI, and counters | Values normalize to schema types; removed `participant` field is neither required nor published |
| 4 | Parser | Missing/duplicate/malformed field or partial block | Query rejected; previous rows retained; `query_status=error` |
| 5 | Reconciliation | Response missing an expected runtime CKN | State marked error/degraded; no stale deletion |
| 6 | Reconciliation | Successful managed participant remove | Expected set advances after command success; only removed row is deleted |
| 7 | Lifecycle | Explicit MACsec disable | Session and all participant rows removed |
| 8 | Refresh | First query fails | Minimal metadata only; no fabricated fields |
| 9 | Refresh | Failure after success | Data retained, timestamp unchanged, query error visible |
| 10 | Refresh | Recovery | Valid snapshot replaces retained state and advances timestamp |
| 11 | Scheduler | Periodic namespace sweep | Every configured port is queried sequentially every 20 seconds; timer executions do not overlap |
| 12 | Scheduler | One port exceeds the two-second query deadline | Only that row becomes query-error; its prior data/timestamp remain; later ports are still queried |
| 13 | Scheduler | Startup, enable, or rollover safety query | Uses the same bounded two-second query path |
| 14 | Config CLI | Complete dual-CA profile replacement | One CONFIG_DB write occurs after structural validation; runtime STATE_DB is not read |
| 15 | Config CLI | Primary-only attached profile update | Rejected before CONFIG_DB mutation with create-new-profile/rebind guidance |
| 16 | Config CLI | Primary-only unattached profile update | Rejected identically; attachment does not relax the command contract |
| 17 | Config CLI | Missing required CAK/CKN pair member, same CKN, CKN collision, invalid encoding/length, or unsupported multi-field change | Rejected as invalid parameters before CONFIG_DB mutation |
| 18 | Config CLI | Complete dual-CA update with missing/stale/unhealthy MKA state | Desired CONFIG_DB write succeeds; runtime reconciliation is deferred to macsecmgrd |
| 19 | Config CLI | Error/advisory output | No CAK appears; primary-only rejection names the create-new-profile/rebind workflow |
| 20 | Desired state | Direct primary-only CONFIG_DB change | macsecmgrd caches desired state; ingestion is not rejected |
| 21 | Desired state | Direct unsupported shape such as fallback add/remove, non-key change, or same-CKN CAK change | Desired state is cached; runtime remains unchanged and degraded/pending rather than promising unsupported convergence |
| 22 | No runtime | Port has no owned session | Desired state does not block profile processing; future enable uses the latest desired profile |
| 23 | Peerless | Applied primary-only runtime has sole role-correct primary with zero live and potential peers | Primary replacement proceeds without an alternate |
| 24 | Peer-bearing | Applied primary-only runtime has any live peer | No remove/add; port remains degraded because no alternate exists |
| 25 | Peer-bearing | Applied primary-only runtime has any potential peer | No remove/add; potential peer prevents peerless classification |
| 26 | Peerless | Applied dual-CA runtime has zero live and potential peers on both roles | Selected role replacement proceeds without alternate liveness |
| 27 | Peer-bearing | Applied dual-CA runtime has any live or potential peer | Strict protected-state and role-correct live-alternate checks are required |
| 28 | Unknown | Expected applied CKN missing, extra/duplicate CKN, wrong role, or malformed peer count | No participant mutation; applied state retained and port degraded |
| 29 | Unknown | Query failure or stale retained snapshot previously showed zero peers | Retained zeros are not reused; no participant mutation |
| 30 | Multi-port | Unsafe first port, later safe/peerless port | Unsafe port remains pending; later port still reconciles |
| 31 | Multi-port | Safe/peerless first port, later unsafe port | First port remains complete; later port remains pending |
| 32 | Multi-port | Multiple safe ports | All reconcile independently in one profile-processing pass |
| 33 | Multi-role | Already-accepted desired state differs from applied state in primary and fallback | Primary then fallback complete sequentially in the same `loadProfile()` call; one CLI invocation still selects only one role |
| 34 | Multi-role | Per-role authorization | Each role gets a fresh preflight and immediate pre-remove query; first add is observed before second role begins |
| 35 | Multi-role | First role fails | Further role changes stop for that port in the current pass; other ports continue |
| 36 | Multi-role | First role succeeds, second role fails | First role remains applied; second role is degraded/pending |
| 37 | Retry | Partial multi-role progress | Completed role is skipped; retry resumes only the incomplete role |
| 38 | Remove failure | Existing participant remains | No add; degraded state reported; safe retry |
| 39 | Ambiguous add | Replacement was applied but command reported failure | Fresh observation recognizes the replacement; duplicate add is avoided |
| 40 | Show | Healthy primary/fallback state | Compact output shows primary and fallback live-peer counts from the unique `is_primary=true/false` rows, independent of principal ownership |
| 41 | Show | Fallback is principal | Principal CKN/Role shows fallback while Primary/Fallback live-peer columns still follow configured roles |
| 42 | Show | Primary-only profile | Primary live peers is shown; Fallback live peers is `-` |
| 43 | Show | Missing or duplicate configured role | The affected role-derived live-peer count is `-` |
| 44 | Show | Any participant has missing/malformed `is_primary` | Both role-derived live-peer counts are `-` |
| 45 | Show | Malformed `live_peers` | The affected role-derived live-peer count is `-` |
| 46 | Show | Compact versus detailed diagnostics | Compact header omits Key-server SCI; detailed output retains Key server SCI and participant Live/Potential columns |
| 47 | Show | Healthy protected state | Compact `Secured` is true; detail shows `PAE KaY status: active`, `Controlled port mode: secured`, and `Failed: false`; Status independently reflects query/config/age health |
| 48 | Show | Authenticated-only CP state | Compact `Secured` is false; detail shows `Controlled port mode: authenticated-only`; Status is not overloaded with CP flags |
| 49 | Show | Failed, inactive, contradictory, or incomplete CP state | Detail derives `failed`, `inactive`, `inconsistent`, or `unknown` according to the ordered mapping |
| 50 | Show | Query failure, age over 60 seconds, config degradation, or never-successful query | Status combines independent flags and cannot look healthy |
| 51 | Show | Config/runtime mismatch | Healthy observed old or partially updated runtime can have `query_status=ok,config_status=degraded` |
| 52 | Multi-ASIC | Same CKN on different ports/namespaces | Rows remain distinct; correct namespace is used |
| 53 | Process restart | macsecmgrd restarts with desired/applied/pending state and active WPA runtime | Desired and per-port progress are restored; fresh queries precede mutation; reconciliation resumes without replaying completed roles |
| 54 | Security | Poison config/status/error paths with current and stale encoded/decoded CAKs plus CKN/interface/error context | Every CAK form is redacted from STATE_DB/show/log output; CKN and non-secret context remain visible |
| 55 | Traffic | Peer-bearing supported primary/fallback rollover | Continuous bidirectional traffic has zero loss |

## 12 Rollout and Dependency Ordering

The companion WPA fallback-key behavior and the SONiC changes in this document
are delivered as one coupled feature set. The delivery order inside that set is:

1. **`sonic-swss-common`** — add shared table constants.
2. **`sonic-swss`** — add STATE_DB publication, safety revalidation, rollover
   actioning, and unit tests using the existing WPA interfaces.
3. **`sonic-buildimage`** — include the coupled fallback-key feature and add
   config safety checks and show commands.
4. **`sonic-mgmt`** — add integration, failure, process-restart, namespace, and
   lossless-traffic tests.

The components are released together as one coupled feature set.
