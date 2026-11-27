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
- [4 Status Collection and Publication](#4-status-collection-and-publication)
  - [4.1 Collection and validation](#41-collection-and-validation)
  - [4.2 Desired and observed state](#42-desired-and-observed-state)
  - [4.3 Publication and failures](#43-publication-and-failures)
- [5 Configuration and Runtime Reconciliation](#5-configuration-and-runtime-reconciliation)
  - [5.1 Profile commands](#51-profile-commands)
  - [5.2 Desired and applied state](#52-desired-and-applied-state)
  - [5.3 Best-effort runtime convergence](#53-best-effort-runtime-convergence)
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
(MKA) operational state, desired key configuration, best-effort per-port runtime
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
3. `config macsec profile update_cak` replaces one `old_ckn`-selected CA per
   invocation and requires an existing complete primary/fallback profile.
   The configured alternate is an operator-facing structural precondition, not
   a runtime liveness guarantee. Primary-only replacement uses a new profile
   and port rebind.
4. Direct CONFIG_DB primary-only changes remain valid desired state and are
   consumed by macsecmgrd.
5. macsecmgrd does not gate runtime mutation on query freshness, peer counts,
   Controlled Port state, or alternate-CA liveness. It applies valid desired
   key changes directly to the owned WPA session without restarting the port or
   supplicant.
6. Rollover is remove-old then add-new; no third participant is staged. A
   successful add is observed before applied state advances, and a failed add
   is retried.
7. Ports reconcile independently. Runtime failure never rolls desired CONFIG_DB
   back, completed work is not repeated, and partial progress is represented
   truthfully.
8. An MKA session row marks one complete structurally valid WPA observation.
   A failed, unreachable, malformed, or partial query removes that port's
   session marker and participant rows without affecting other ports.
9. No CAK, SAK, authentication key, or derived key material is published,
    rendered, or logged. CKN is an identifier and may be exposed.
10. Graceful shutdown deletes owned MKA rows. Startup purges all namespace-local
    rows owned by that daemon before reconstructing desired/applied/pending
    state, resuming best-effort convergence, and republishing valid observations.

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

The session row is the validity marker for one complete structurally valid
observation. Participant rows are published first and the session row last.
Consumers ignore participant rows when the session row is absent.

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
| `query_status` | `ok` for the complete valid observation represented by this row |
| `last_updated` | UTC timestamp of that successful validated query |
| `config_status` | Desired/applied agreement: `in-sync` / `degraded` |
| `config_error` | Optional redacted pending/failure reason |

A valid observation of old or partially updated applied runtime can have
`config_status=degraded`. Query failure is represented by row absence, not by
a failure-only row or a retained prior observation.

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

## 4 Status Collection and Publication

### 4.1 Collection and validation

Every 20 seconds, each namespace-local single-threaded macsecmgrd instance
sequentially queries every configured MACsec port. Each `macsec_mka_list` call
has a hard two-second deadline; timer executions do not overlap. Startup,
enable, reconnect, and reconciliation use the same bounded query path.

A failure removes only that port's session row and all participant rows, and
does not stop later ports. No stale or success-shaped observation remains.

A response is accepted only when required fields are unique and valid, all
booleans/integers/CKNs/MIs/SCIs normalize correctly, CKNs are unique, and no
more than one participant claims either principal or primary role. Unknown
fields are ignored; missing, duplicate, malformed, or partial known fields
reject the response.

A structurally complete response with zero participants is a valid observation
and can publish `config_status=degraded`. A response containing a partial
participant block is invalid; the producer cannot infer that a syntactically
complete empty participant list was truncated by WPA.

### 4.2 Desired and observed state

A successful query is an operational observation, not authorization for
configuration mutation. macsecmgrd compares the observed CKNs and roles with
desired CONFIG_DB and its tracked applied/pending state. An exact desired match
is `config_status=in-sync`; old, missing, additional, role-mismatched, or
partially replaced participants are `config_status=degraded`.

Live/potential peer counts, principal ownership, Controlled Port state, and
administrative state remain important diagnostics. They do not block or permit
reconciliation. The operator is responsible for
sequencing profile updates so that an expected traffic interruption is
acceptable and the configured alternate can carry traffic where required.
For an intentionally staged healthy dual-CA sequence, the operator may require
the alternate to be active, peered, and protecting traffic before updating the
other CA; zero loss is then a valid system-test expectation, not a daemon
authorization rule or guarantee.

Each successful periodic query also compares observed participants with the
expected runtime identities for the current supported reconciliation state.
Missing or unexpected participants are runtime drift: publish degraded status
and schedule best-effort repair. This does not make unsupported desired
fallback presence changes valid.

### 4.3 Publication and failures

A validated snapshot deletes obsolete participant rows, upserts current
participants, then writes the session row last. `config_status` is `in-sync`
only when desired and observed applied state match; otherwise it is `degraded`
with a redacted reason.

A response matching applied runtime but not desired CONFIG_DB remains a valid
observation with `config_status=degraded`.

On query timeout, WPA unreachability, parser failure, or incomplete/malformed
response, remove that interface's session row first and then all participant
rows with the interface prefix. Redis multi-key operations are not atomic; the
ordering ensures consumers stop treating the port as a valid observation
before participant cleanup completes. Do not infer actual CA absence, port
state, or desired/applied convergence from the missing session row. Query
failure does not itself block internal best-effort configuration retry.
Explicit MACsec disable also removes both session and participant rows.

Graceful shutdown deletes all MKA rows owned by that namespace-local daemon.
At startup, before the first query or publish, the daemon purges its entire
two-table MKA scope through its STATE_DB connector, including rows for ports no
longer configured. Graceful shutdown performs this purge before port teardown.
A hard crash can leave rows transiently stale until process restart performs
startup purge; this accepted interval uses no TTL or consumer-side age
heuristic. Cleanup is limited to the two dedicated macsecmgrd tables in that
connector namespace; it does not delete another namespace or producer's state.

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
sudo config macsec profile update_cak <profile> \
  --old_ckn <current-primary-or-fallback-ckn> \
  --new_ckn <replacement-ckn> \
  --new_cak <replacement-encoded-cak>
```

The existing profile must contain complete primary and fallback pairs.
`new_cak` and `new_ckn` are required, `old_ckn` selects exactly one configured
CA, the new CKN differs from both existing CKNs, same-CKN CAK replacement is
rejected, and unrelated fields are unchanged. One invocation replaces one CA;
changing both roles requires two writes or another management path.

The opposite role's complete CAK/CKN pair must therefore be configured before
the CLI accepts a rotation. "Available" means configured, not live, peered,
principal, secured, or queryable. The command intentionally leaves runtime
traffic-safety sequencing to the operator.

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

Ports reconcile independently. A failing port does not block siblings;
completed ports are skipped on retry. A port without an owned runtime session
uses the latest desired profile on its next normal enable.

Supported existing-role replacements in valid primary-only or paired desired
shapes are reconciled best-effort. Fallback addition/removal, non-key profile
changes, same-CKN CAK changes, or directly swapping primary and fallback
identities without an intermediate free CKN remain degraded/pending. A role
swap must be staged through an intermediate key/CKN. This design provides
best-effort convergence, not universal success.

### 5.3 Best-effort runtime convergence

For each owned WPA runtime, macsecmgrd compares desired and tracked applied
state and pipes the required MKA control changes directly to wpa_supplicant.
It does not restart the supplicant, disable/re-enable MACsec, or bounce the
port.

No query, peer, principal, active-role, Controlled Port, administrative-state,
or live-alternate preflight gates this action. These values remain observable
through STATE_DB and `show macsec --mka`, but macsecmgrd makes no hitless or
traffic-continuity guarantee. The CLI's configured-alternate requirement is a
structural operator safeguard only; direct CONFIG_DB writers can bypass it,
and macsecmgrd still attempts convergence.

The operator must order primary and fallback rotations so that the other
configured CA is usable when traffic continuity matters. A WPA rejection is
treated as runtime degradation to report and retry, not as a reason to restart
the port or roll desired CONFIG_DB back.

### 5.4 Replacement algorithm

| Selected role | Alternate role | Add command |
| ------------- | -------------- | ----------- |
| Primary | Fallback | `macsec_add_mka ckn=<new> cak=<new>` |
| Fallback | Primary | `macsec_add_mka ckn=<new> cak=<new> fallback=1` |

For each changed role:

1. identify the desired/applied role difference and any pending operation;
2. remove the old CKN when it is still present;
3. update the role's WPA network CKN/CAK fields to the desired replacement;
4. add the replacement with the role-specific command;
5. query status and require the desired CKN/role to be observed; and
6. advance applied state.

Replacement remains remove-before-add; no third participant is staged.
Key replacement is live and in place, but whether an alternate carries traffic
is outside the daemon's guarantee.

If already-accepted desired state differs in both roles, process at most two
roles in deterministic collision-aware order. The default is primary then
fallback. If the desired primary CKN is still occupied by the applied fallback,
replace fallback first to free that identity; a direct primary/fallback role
swap remains unsupported. One CLI invocation still selects only one role. The
first add must be observed before the second role starts. First-role failure
stops that port for the current pass; other ports continue.

### 5.5 Failure and retry

A failed remove prevents dependent update/add work in that pass and is retried.
Failure after remove preserves truthful pending state; it does not claim the
original runtime is intact. Runtime failure never rolls desired CONFIG_DB back.

If update succeeds but add fails or WPA does not expose the replacement,
macsecmgrd records a redacted error, sets `config_status=degraded`, and retries
the add on later reconciliation passes without restarting the port. Retry first
observes runtime when possible. A replacement already present with the expected
role is treated as applied, avoiding duplicate add. Completed ports/roles are
not repeated. If primary succeeds and fallback fails, primary remains applied
and retry resumes fallback only.

Persistent WPA rejection remains degraded and visible; it does not become a
success-shaped state whenever a successful observation exists. If WPA cannot
be queried, STATE_DB contains no MKA observation for that port while internal
pending/degraded state and retries continue.

Periodic reconciliation repairs supported runtime drift without restarting the
port: remove an unexpected observed CKN, re-add a missing configured
participant, then query again to verify. A superseded pending replacement
remains part of observed runtime accounting; if present, it is removed before
adding the newer desired CKN and can therefore bridge an otherwise colliding
transition. Failed repair commands remain degraded and are retried.

Operational state always reflects the observed applied runtime. Ports sharing a
desired profile can temporarily expose different applied CKNs. Healthy observed
old or partially updated runtime can have `config_status=degraded`.

## 6 Show Command

```text
show macsec --mka
show macsec --mka Ethernet0
```

Existing non-MKA show behavior is unchanged; `--mka` is mutually exclusive
with other status modes.

### 6.1 Compact output

```text
Interface  KaY     Secured Principal CKN   Role     prim./fall. live peers Local-KS Keys distributed
Ethernet0  active  true    001122...ddeeff primary  1/1                      true     7
```

Rows sort by natural interface order, then namespace. Principal CKN/Role derive
from `is_principal`. `prim./fall. live peers` formats independently derived
counts from the unique `is_primary=true/false` participants as
`<primary>/<fallback>`. A missing/duplicate role or malformed peer count renders
that portion `-`; any malformed role renders `-/-`. Primary-only profiles show
the absent fallback portion as `-`, for example `2/-`.

`Keys distributed` is the numeric `keys_distributed` counter, never SAK key
material; an absent or malformed value renders `-`.

`Secured` remains the compact CP indication. Compact output omits Key server
SCI, Status, and Age. An interface with no complete valid MKA session row
produces no MKA-specific compact row; participant rows without a session marker
are ignored.

### 6.2 Interface-specific output

Detailed output retains PAE KaY status, Failed, Key server SCI,
configuration/error diagnostics, Actor SCI, actor/key-server priorities, local
key-server state, key distribution/receive counters, MKA hello time, and
participant columns:

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

This presentation is operational evidence, not a runtime mutation gate.
If the selected interface has no complete valid MKA observation, the command
prints no MKA-specific session or participant data.
Neither compact nor detailed output renders `query_status`/`last_updated` as
Status/Age.

## 7 Process Restart, Security, and Compatibility

On macsecmgrd restart:

1. purge both dedicated MKA tables through the daemon's namespace-local
   STATE_DB connector, including rows for unconfigured old ports;
2. restore latest desired profiles plus per-port applied/pending internal state;
3. rebuild network IDs and runtime participant state;
4. resume reconciliation without replaying completed roles;
5. query each configured interface; and
6. publish only complete valid observations.

Reconciliation does not wait for peer/liveness proof after restart. The process
restart contract remains normative even where implementation is incomplete.
Graceful shutdown performs the same owned-row deletion. A hard crash may expose
old rows only until the supervised process restarts and executes startup purge;
no TTL is defined.

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
6. Direct desired state: supported existing-role replacements in valid
   primary-only/paired shapes are attempted; fallback presence changes,
   same-CKN replacement, and direct role swap without an intermediate identity
   remain degraded.
7. No runtime: latest desired profile used on future enable.
8. CLI safety boundary: selected-role rotation requires the other complete
   configured CAK/CKN pair but does not inspect runtime peers or health.
9. Direct action: peer counts, query freshness, CP state, principal, active
   role, port state, and alternate liveness do not gate in-place remove/update/add.
10. Direct CONFIG_DB: supported primary-only replacement is attempted
    best-effort despite the CLI restriction.
11. Multi-port: failing ports do not block siblings; completed ports skip on
    retry.
12. Multi-role: primary-first by default, fallback-first when required to free
    the desired primary CKN, post-add observation per role, first failure stops
    that port, and partial progress is retained.
13. Failure/retry: remove/add ambiguity, failed add retried, superseded pending
    target collision handling, persistent WPA rejection degraded, no duplicate
    add, desired state never rolled back.
14. Compact show: natural/namespace ordering, role-derived live counts,
    combined `prim./fall. live peers`, numeric Keys distributed, no Status/Age
    or compact Key server SCI, and no row without a valid session observation.
15. Detailed show: controlled-port mode matrix, key-server and participant
    diagnostics, config mismatch.
16. Multi-ASIC: namespace locality and duplicate CKN/interface handling.
17. Query cleanup: timeout/unreachable/malformed/partial response removes the
    affected session marker first, then its participants; other ports remain,
    and a later complete response publishes participants before session.
18. Drift/restart: timer removal of unexpected CKNs, re-addition of missing
    configured participants, post-repair verification, startup namespace purge,
    graceful-shutdown cleanup, desired/applied/pending restoration, and no TTL
    or port restart.
19. Empty observation: a structurally complete zero-participant response is
    published degraded; a partial participant block clears the port rows.
20. Security: configured/stale encoded/decoded CAK redaction with CKN/context
    preserved.
21. Live actioning: no supplicant/port restart; an operator-staged healthy
    dual-CA sequence may require zero loss, while arbitrary update disruption
    is not a daemon correctness failure.

## 9 Rollout

Deliver the coupled feature in order:

1. `sonic-swss-common` table constants;
2. `sonic-swss` publication and reconciliation;
3. `sonic-buildimage` config/show CLI; and
4. `sonic-mgmt` integration and traffic tests.
