<!-- omit in toc -->
# MACsec MKA Operational State and Key Rotation — SONiC High Level Design

***Revision***

| Rev | Date | Author | Change Description |
| :-: | :--: | :----- | ------------------ |
| 0.1 | | Liam Kearney | Initial version |

<!-- omit in toc -->
## Table of Contents

- [About this Manual](#about-this-manual)
- [Abbreviations](#abbreviations)
- [1 Design Invariants](#1-design-invariants)
- [2 Architecture and Dependencies](#2-architecture-and-dependencies)
- [3 Database Design](#3-database-design)
  - [3.1 CONFIG_DB profile](#31-configdb-profile)
  - [3.2 MKA session STATE_DB table](#32-mka-session-statedb-table)
  - [3.3 MKA participant STATE_DB table](#33-mka-participant-statedb-table)
- [4 Status Collection and Classification](#4-status-collection-and-classification)
  - [4.1 Collection and validation](#41-collection-and-validation)
  - [4.2 Runtime classification](#42-runtime-classification)
  - [4.3 Publication and failures](#43-publication-and-failures)
- [5 Configuration and Runtime Reconciliation](#5-configuration-and-runtime-reconciliation)
  - [5.1 Profile commands](#51-profile-commands)
  - [5.2 Desired and applied state](#52-desired-and-applied-state)
  - [5.3 Runtime authorization](#53-runtime-authorization)
  - [5.4 Replacement algorithm](#54-replacement-algorithm)
  - [5.5 Failure and retry](#55-failure-and-retry)
- [6 Show Command](#6-show-command)
  - [6.1 Compact output](#61-compact-output)
  - [6.2 Interface-specific output](#62-interface-specific-output)
- [7 Process Restart, Security, and Compatibility](#7-process-restart-security-and-compatibility)
- [8 Test Plan](#8-test-plan)
- [9 Rollout](#9-rollout)

## About this Manual

This document defines the SONiC-side integration for MACsec Key Agreement
(MKA) operational state, desired key configuration, safe per-port runtime
reconciliation, and `show macsec --mka`.

It accompanies:

- [MACsec Fallback CAK — wpa_supplicant High Level Design](MACsec_fallback_cak_hld.md),
  which owns the frozen WPA fallback-key behavior and control/status interface;
  and
- [MACsec SONiC High Level Design](MACsec_hld.md), which owns the existing
  CONFIG_DB, APP_DB, SecY, MACsecOrch, and SAI design.

Companion implementation pull requests:

- [sonic-swss-common#1251](https://github.com/sonic-net/sonic-swss-common/pull/1251)
- [sonic-swss#4827](https://github.com/sonic-net/sonic-swss/pull/4827)
- [sonic-buildimage#29102](https://github.com/sonic-net/sonic-buildimage/pull/29102)
- [sonic-wpa-supplicant#138](https://github.com/sonic-net/sonic-wpa-supplicant/pull/138)

This HLD changes SONiC only. It consumes the existing WPA interface and does
not change KaY/MKA state machines, principal selection, election, SAK rollover,
MACsecOrch, SAI, or vendor SDK behavior.

## Abbreviations

| Abbreviation | Description |
| ------------ | ----------- |
| CA | Secure Connectivity Association |
| CAK / CKN | Connectivity Association Key / CA Key Name |
| CP | Controlled Port |
| KaY | MACsec Key Agreement Entity |
| MI / MN | Member Identifier / Message Number |
| MKA | MACsec Key Agreement protocol |
| SA / SAK | Secure Association / Secure Association Key |
| SC / SCI | Secure Channel / Secure Channel Identifier |
| SecY | MACsec Security Entity |

## 1 Design Invariants

1. `macsecmgrd` is the sole writer of the namespace-local MKA session and
   participant STATE_DB tables. Existing MACsec APP_DB and ASIC-facing
   STATE_DB tables retain their dataplane meaning.
2. CONFIG_DB is authoritative desired state. Each owned runtime session tracks
   its exact applied and pending state independently.
3. `config macsec profile update` replaces one `old_ckn`-selected CA per
   invocation and requires an existing complete primary/fallback profile.
   Primary-only replacement uses a new profile and port rebind.
4. Direct CONFIG_DB primary-only changes remain valid desired state and are
   consumed by macsecmgrd.
5. Runtime mutation requires a fresh authoritative snapshot classified against
   the port's applied profile as **peerless**, **peer-present**, or **unknown**.
6. Peerless runtime may replace a CA without a live alternate. Peer-present
   runtime requires protected CP state and a live role-correct alternate.
   Unknown runtime fails closed.
7. Rollover is remove-old then add-new; no third participant is staged.
   Authorization is refreshed immediately before each remove, and a successful
   add is observed before applied state advances.
8. Ports reconcile independently. Runtime failure never rolls desired CONFIG_DB
   back, completed work is not repeated, and partial progress is represented
   truthfully.
9. Query health, desired/applied convergence, and last-success age are
   independent operational dimensions.
10. No CAK, SAK, authentication key, or derived key material is published,
    rendered, or logged. CKN is an identifier and may be exposed.
11. Process restart must reconstruct desired, applied, and pending state and
    obtain fresh status before resuming mutation.

## 2 Architecture and Dependencies

The existing dataplane path remains unchanged:

```text
wpa_supplicant / MACsec plugin
        |
        v
      APP_DB
        |
        v
   MACsecOrch --> SAI / SecY
        |
        v
ASIC-facing MACsec STATE_DB tables
```

The new control-plane status path is separate:

```text
existing WPA macsec_mka_list output
        |
        v
    macsecmgrd
        |
        v
MACSEC_MKA_SESSION_TABLE
MACSEC_MKA_PARTICIPANT_TABLE
        |
        +--> runtime reconciliation
        +--> show macsec --mka
```

The fallback feature exposes these existing session fields:

```text
PAE KaY status, Authenticated, Secured, Failed,
Actor Priority, Key Server Priority, Is Key Server,
Number of Keys Distributed, Number of Keys Received,
MKA Hello Time, actor_sci, key_server_sci
```

Participant fields are:

```text
participant_idx, ckn, mi, mn, active, retain,
is_principal, is_primary, live_peers, potential_peers,
is_key_server, is_elected
```

`is_primary` is the configured privileged/revertive role.
`is_principal` is dynamic CP ownership. A fallback can therefore have
`is_primary=false,is_principal=true`.

## 3 Database Design

### 3.1 CONFIG_DB profile

The existing `MACSEC_PROFILE|<profile>` fields are:

```text
primary_cak, primary_ckn,
fallback_cak (optional), fallback_ckn (optional),
and existing non-key profile fields
```

Primary CAK/CKN are required. Fallback CAK/CKN are optional as a pair. CKNs
must differ, CAKs must match the cipher suite, and key material remains secret.

Primary-only and paired profiles are valid CONFIG_DB states. The dual-CA
requirement belongs only to the CLI replacement command; it does not constrain
the schema or daemon ingestion of desired state.

### 3.2 MKA session STATE_DB table

`sonic-swss-common/common/schema.h` defines:

```cpp
#define STATE_MACSEC_MKA_SESSION_TABLE_NAME "MACSEC_MKA_SESSION_TABLE"
#define STATE_MACSEC_MKA_PARTICIPANT_TABLE_NAME "MACSEC_MKA_PARTICIPANT_TABLE"
```

Key: `MACSEC_MKA_SESSION_TABLE|<interface>`.

| Field | Source / meaning |
| ----- | ---------------- |
| `profile` | Effective CONFIG_DB profile |
| `kay_status` | WPA `PAE KaY status`, normalized to `active` / `not-active` |
| `authenticated` | WPA authenticated-only CP mode, lowercase boolean |
| `secured` | WPA MACsec-protected CP state, lowercase boolean |
| `failed` | WPA CP failure state, lowercase boolean |
| `actor_sci` | WPA `actor_sci`, normalized to 16 lowercase hex digits |
| `key_server_sci` | WPA `key_server_sci`; all-zero means no election |
| `actor_priority` | WPA Actor Priority |
| `key_server_priority` | WPA Key Server Priority |
| `is_key_server` | WPA Is Key Server, lowercase boolean |
| `keys_distributed` | WPA Number of Keys Distributed |
| `keys_received` | WPA Number of Keys Received |
| `mka_hello_time_ms` | WPA MKA Hello Time |
| `query_status` | Latest collection result: `ok` / `error` |
| `last_updated` | UTC timestamp of last successful validated query |
| `config_status` | Desired/applied agreement: `in-sync` / `degraded` |
| `config_error` | Optional redacted pending/failure reason |

`query_status`, `config_status`, and `last_updated` are orthogonal. A healthy
snapshot of old applied runtime can have
`query_status=ok,config_status=degraded`. No freshness field is stored.

Healthy protected CP state is:

```text
kay_status=active
authenticated=false
secured=true
failed=false
```

`authenticated=true,secured=false` means authenticated-only, unprotected CP
operation.

### 3.3 MKA participant STATE_DB table

Key: `MACSEC_MKA_PARTICIPANT_TABLE|<interface>|<normalized_ckn>`.

| Field | Source / meaning |
| ----- | ---------------- |
| `participant_index` | WPA `participant_idx`; diagnostic only |
| `mi` | Lowercase hexadecimal MI |
| `mn` | Message Number |
| `active` | Participant activity |
| `retain` | Existing WPA retain flag |
| `is_principal` | Current CP owner |
| `is_primary` | Configured privileged/revertive role |
| `live_peers` | Live peer count |
| `potential_peers` | Potential peer count |
| `is_key_server` | Participant key-server state |
| `is_elected` | Participant election state |

The normalized CKN is identity; participant list position is not. macsecmgrd is
the sole writer of both MKA tables in each namespace.

## 4 Status Collection and Classification

### 4.1 Collection and validation

Every 20 seconds, each namespace-local single-threaded macsecmgrd instance
sequentially queries every configured MACsec port. Each `macsec_mka_list` call
has a hard two-second deadline; timer executions do not overlap. Startup,
enable, reconnect, and reconciliation use the same bounded query path.

A failure marks only that port `query_status=error`, retains its last successful
fields and timestamp, and does not stop later ports.

A response is accepted only when required fields are unique and valid, all
booleans/integers/CKNs/MIs/SCIs normalize correctly, CKNs are unique, and no
more than one participant claims either principal or primary role. Unknown
fields are ignored; missing, duplicate, malformed, or partial known fields
reject the response.

The complete expected participant set comes from the port's `applied_profile`:
one primary for primary-only runtime, or primary plus fallback for paired
runtime. Expected CKNs and roles must match exactly, with no extras.

### 4.2 Runtime classification

| Classification | Evidence | Runtime consequence |
| -------------- | -------- | ------------------- |
| **Peerless** | Fresh successful query; actual CKN set exactly equals applied profile; roles correct; every expected participant has `live_peers=0` and `potential_peers=0` | Replacement may proceed without a live alternate |
| **Peer-present** | Same complete role-correct set; any expected participant has nonzero live or potential peers | Protected CP and live role-correct alternate required |
| **Unknown** | Query failure/staleness, missing/duplicate/unexpected participant, role mismatch, or missing/malformed peer count | No mutation; retain applied state and retry |

Administrative or operational down state is neither proof nor disproof of
peerlessness. An owned down runtime with fresh zero-peer evidence can proceed;
without authoritative evidence it remains pending. Retained zero-peer data
never authorizes mutation.

### 4.3 Publication and failures

A validated snapshot replaces session fields, upserts current participants,
deletes stale participant rows, sets `query_status=ok`, and advances
`last_updated`. `config_status` is `in-sync` only when desired and applied state
match; otherwise it is `degraded` with a redacted reason.

A response matching applied runtime but not desired CONFIG_DB remains a valid
observation: `query_status=ok,config_status=degraded`.

On query/parser/completeness failure, retain the last snapshot and timestamp,
set `query_status=error`, delete no participants, and log no secret material.
Before any successful query, publish only known metadata. Explicit MACsec
disable removes both session and participant rows.

Multi-ASIC publication and reconciliation are namespace-local. The CLI uses
existing namespace helpers to aggregate without collapsing identical CKNs on
different interfaces or namespaces.

## 5 Configuration and Runtime Reconciliation

### 5.1 Profile commands

Creation:

```text
sudo config macsec profile add <profile> \
  --primary_cak <encoded-cak> --primary_ckn <ckn> \
  [--fallback_cak <encoded-cak> --fallback_ckn <ckn>] \
  [existing profile options]
```

Primary CAK/CKN are required. Fallback arguments are optional as a pair; if
either is supplied both are required. CKNs and CAKs must pass existing hex,
length, salt-index, cipher-suite, and uniqueness validation.

Replacement:

```text
sudo config macsec profile update <profile> \
  --old_ckn <current-primary-or-fallback-ckn> \
  --new_ckn <replacement-ckn> \
  --new_cak <replacement-encoded-cak>
```

The existing profile must contain complete primary and fallback pairs.
`new_cak` and `new_ckn` are required, `old_ckn` selects exactly one configured
CA, the new CKN differs from both existing CKNs, same-CKN CAK replacement is
rejected, and unrelated fields are unchanged. One invocation replaces one CA;
changing both roles requires two writes or another management path.

A primary-only profile is valid but this update command rejects it, attached or
unattached, with create-new-profile/rebind guidance. Missing pair members are
ordinary invalid parameters. No error exposes CAK material.

Once CLI structural validation passes, one CONFIG_DB write records desired
state. Runtime MKA health, age, port status, roles, and peers are not write
gates. Other management paths can write primary-only desired changes;
macsecmgrd caches rather than rejects them.

### 5.2 Desired and applied state

CONFIG_DB is authoritative desired state. Per owned port, macsecmgrd tracks:

- desired profile;
- exact `applied_profile`;
- WPA network ID;
- pending old CKN/role after interruption; and
- expected runtime participant set.

Ports reconcile independently. An unsafe port does not block safe siblings;
completed ports are skipped on retry. A port without an owned runtime session
uses the latest desired profile on its next normal enable.

Unsupported desired transitions—fallback add/remove, non-key profile changes,
or same-CKN CAK changes—may remain degraded/pending. This design does not
promise universal runtime convergence.

### 5.3 Runtime authorization

Immediately before each destructive step, obtain a fresh bounded snapshot and
classify it against `applied_profile`.

- **Peerless:** proceed without alternate liveness.
- **Peer-present:** require healthy protected CP state and a role-correct active
  alternate with `live_peers >= 1`.
- **Unknown:** perform no mutation.

Peerless authorization applies to both primary-only and paired applied
runtimes. A peer-present primary-only runtime remains pending because no
alternate exists.

For primary replacement, fallback is the alternate; for fallback replacement,
primary is the alternate. `is_principal` remains observability, not configured
role proof.

Before authorization, no destructive mutation occurs. If neither path can be
proved, retain applied runtime, set `config_status=degraded`, record a redacted
pending reason, and retry. Down state alone is neither authorization nor a
blocker.

### 5.4 Replacement algorithm

| Selected role | Alternate role | Add command |
| ------------- | -------------- | ----------- |
| Primary | Fallback | `macsec_add_mka ckn=<new> cak=<new>` |
| Fallback | Primary | `macsec_add_mka ckn=<new> cak=<new> fallback=1` |

For each changed role:

1. query and classify the complete applied participant set;
2. authorize peerless or peer-present path;
3. remove the old CKN;
4. update the role's WPA network CKN/CAK;
5. add the replacement with the role-specific command;
6. query again and require the new CKN/role to be observed; and
7. advance applied state.

Rollover is remove-before-add; no third participant is staged. On the
peer-present path the alternate carries traffic. On the peerless path no live
or potential peer exists.

If already-accepted desired state differs in both roles, process at most two
roles in fixed order: primary then fallback. One CLI invocation still selects
only one role. Each role receives fresh authorization, and the first add must be
observed before fallback starts. First-role failure stops that port for the
current pass; other ports continue.

### 5.5 Failure and retry

Remove failure issues no add. Failure after remove preserves truthful pending
state; it does not claim the original runtime is intact. Runtime failure never
rolls desired CONFIG_DB back.

Retry first observes runtime. A replacement already present with the expected
role is treated as applied, avoiding duplicate add. Completed ports/roles are
not repeated. If primary succeeds and fallback fails, primary remains applied
and retry resumes fallback only.

Operational state always reflects the observed applied runtime. Ports sharing a
desired profile can temporarily expose different applied CKNs. Healthy observed
old or partially updated runtime can have
`query_status=ok,config_status=degraded`.

## 6 Show Command

```text
show macsec --mka
show macsec --mka Ethernet0
```

Existing show behavior is unchanged; `--mka` is mutually exclusive with other
status modes.

### 6.1 Compact output

```text
Interface  KaY     Secured Principal CKN   Role     Primary live peers Fallback live peers Local-KS Status Age
Ethernet0  active  true    001122...ddeeff primary  2                  1                   true     ok     2s
```

Rows sort by natural interface order, then namespace. Principal CKN/Role derive
from `is_principal`; primary/fallback live counts derive independently from the
unique `is_primary=true/false` participants. A missing/duplicate role or
malformed peer count renders `-`; any malformed role makes both counts `-`.
Primary-only profiles show `-` for fallback count.

`Age` derives only from `last_updated` or is `never`. `Status` is `ok` only for
query OK, config in-sync, and age at most 60 seconds; otherwise it combines
`query-error`/`query-unknown`, `config-degraded`/`config-unknown`, `stale`, and
`never-updated`. `Secured` remains the compact CP indication. Compact output
omits Key server SCI.

### 6.2 Interface-specific output

Detailed output retains PAE KaY status, Failed, Key server SCI, separate
query/config/error/timestamp diagnostics, Actor SCI, actor/key-server
priorities, local key-server state, key distribution/receive counters, MKA
hello time, and participant columns:

```text
CKN  Role  Principal  Active  Live  Potential  Key-server  Elected  MI  MN
```

`participant_index` and `retain` remain available in STATE_DB for diagnostics
and forward compatibility but are not operator-facing columns.

Raw `kay_status`, `authenticated`, `secured`, and `failed` remain in STATE_DB.
The CLI derives:

| Controlled port mode | Raw tuple |
| -------------------- | --------- |
| `unknown` | Required field missing/malformed |
| `failed` | `failed=true` |
| `secured` | `active,false,true,false` |
| `authenticated-only` | `active,true,false,false` |
| `inactive` | `not-active,false,false,false` |
| `inconsistent` | Any other valid tuple |

This presentation does not replace the runtime authorization tuple.

## 7 Process Restart, Security, and Compatibility

On macsecmgrd restart:

1. enumerate configured namespace-local ports and delete orphans;
2. restore latest desired profiles plus per-port applied/pending state;
3. rebuild network IDs and runtime participant state;
4. mark retained rows query-error until revalidated;
5. query each interface; and
6. resume reconciliation without replaying completed roles.

Fresh post-restart status is required before peerless mutation. The process
restart contract remains normative even where implementation is incomplete.

CAK, SAK, ICK, KEK, authentication/hash keys, and derived keys must never enter
STATE_DB, output, errors, or logs. CKN/SCI/MI and operational state may be
exposed. Secret-bearing commands and errors are redacted. Before rendering
free-form `config_error`, docker-macsec removes configured encoded/decoded CAKs,
stale 66/128/130-hex secret shapes, and contextual 64-hex CAK/key material while
preserving CKNs and explanatory text.

Primary-only profiles remain valid. Existing APP_DB/ASIC STATE_DB tables,
non-MKA show output, WPA behavior, MACsecOrch, and SAI are unchanged.

## 8 Test Plan

1. Schema/parser: exact final WPA fields, normalization, malformed/partial
   rejection, no key material.
2. Scheduler: 20-second non-overlapping sweep, two-second deadline, per-port
   failure isolation, bounded immediate queries.
3. CLI create: required primary pair, optional complete fallback pair, key/CKN
   validation.
4. CLI update: dual-CA-only, one selected role, primary-only rejection,
   replacement-only and secret-safe errors.
5. Desired acceptance: structurally valid update writes CONFIG_DB despite
   missing/stale/unhealthy runtime.
6. Direct desired state: primary-only accepted by daemon; unsupported shapes
   remain degraded without destructive action.
7. No runtime: latest desired profile used on future enable.
8. Peerless primary-only and paired runtime: exact applied participant set,
   zero live and potential peers, replacement without alternate.
9. Peer-present runtime: any live/potential peer requires protected CP and live
   role-correct alternate.
10. Unknown runtime: failed/stale query, missing/duplicate/unexpected CKN,
    wrong role, or malformed count prevents mutation.
11. Multi-port: unsafe ports do not block safe ports; completed ports skip on
    retry.
12. Multi-role: primary then fallback, fresh authorization and post-add
    observation per role, first failure stops that port, partial progress is
    retained.
13. Failure/retry: remove/add ambiguity, no duplicate add, desired state never
    rolled back.
14. Compact show: natural/namespace ordering, role-derived live counts,
    conservative unknowns, Status/Age, no compact Key server SCI.
15. Detailed show: controlled-port mode matrix, key-server and participant
    diagnostics, config mismatch.
16. Multi-ASIC: namespace locality and duplicate CKN/interface handling.
17. Restart: desired/applied/pending restoration, fresh requery, completed-role
    preservation.
18. Security: configured/stale encoded/decoded CAK redaction with CKN/context
    preserved.
19. Traffic: zero-loss peer-present primary/fallback rollover.

## 9 Rollout

Deliver the coupled feature in order:

1. `sonic-swss-common` table constants;
2. `sonic-swss` publication and reconciliation;
3. `sonic-buildimage` config/show CLI; and
4. `sonic-mgmt` integration and traffic tests.
