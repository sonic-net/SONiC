# `aclshow` CACL Counters — High-Level Design

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Repositories and modules changed](#71-repositories-and-modules-changed)
  - [7.2 `caclmgrd` iptables counter poller](#72-caclmgrd-iptables-counter-poller)
  - [7.3 `aclshow` fallback and verbose view](#73-aclshow-fallback-and-verbose-view)
  - [7.4 COUNTERS_DB schema additions](#74-counters_db-schema-additions)
  - [7.5 Concurrency and failure handling](#75-concurrency-and-failure-handling)
  - [7.6 Security considerations](#76-security-considerations)
  - [7.7 Platform dependency](#77-platform-dependency)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test cases](#131-unit-test-cases)
  - [13.2 System Test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items)

---

## 1. Revision

| Rev | Change Description                                                              |
|-----|---------------------------------------------------------------------------------|
| 0.1 | Initial HLD for iptables-based CACL counters in `aclshow`.                      |

---

## 2. Scope

This document describes how `aclshow -a` is extended to display real packet / byte counters for Control-Plane ACL (CACL) rules, which today render `N/A`.

**In scope**

- A periodic iptables counter poller inside `caclmgrd` that publishes rule-level counters to `COUNTERS_DB`.
- Extensions in `aclshow` to consume those counters as a fallback whenever the SAI counter for a rule is `N/A`.
- A verbose iptables view (`aclshow -a -vv`) that dumps the raw IPv4 and IPv6 iptables tables.
- New `COUNTERS_DB` tables (`IPTABLES_COUNTER_RULE_MAP`, `COUNTERS:<rule_id>`) — no changes to `ACL_COUNTER_RULE_MAP` or existing SAI counter rows.

**Out of scope**

- Programming CACL rules into the ASIC.
- Changing the semantics or life-cycle of `CONFIG_DB:ACL_RULE` entries.
- Replacing SAI-based counters for data-plane ACL tables.
- New CONFIG_DB or YANG surfaces.

---

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| ACL | Access Control List |
| CACL | Control-Plane ACL — an ACL applied to CPU-bound traffic, implemented via host iptables |
| SAI | Switch Abstraction Interface |
| `caclmgrd` | Control-plane ACL manager daemon in `sonic-host-services` |
| `aclshow` | SONiC CLI utility that shows per-ACL-rule packet / byte counters |
| `COUNTERS_DB` | Redis DB #2 in SONiC that holds counter state |
| `rule_id` | Deterministic identifier for an iptables rule (ip version, chain, line number, target, protocol, interfaces, addresses) |

---

## 4. Overview

SONiC does not program CACL rules into the ASIC. `caclmgrd` renders each CACL rule as an `iptables` / `ip6tables` rule on the host, so no SAI ACL counter is created for it and `COUNTERS_DB` has no entry for it. As a result `aclshow -a` displays `N/A` for every CACL rule:

```
admin@t0-r1-Leaf0:~$ aclshow -a
RULE NAME          TABLE NAME            PRIO  PACKETS COUNT    BYTES COUNT
-----------------  ------------------  ------  ---------------  -------------
RULE_50_HTTPS      IPV4_PROTECT_HTTPS    9989  N/A              N/A
RULE_999_DENY_ALL  IPV4_PROTECT_HTTPS       1  N/A              N/A
RULE_10_ICMP       IPV4_PROTECT_RE       9999  N/A              N/A
...
```

Operators rely on `aclshow` to validate that control-plane protections are hitting. Today the only workaround is to correlate configured CACL rules to raw `iptables -L -v -n -x` output by hand — not scalable and inconsistent with the customer-facing tooling. This HLD fixes that gap by sourcing counters directly from iptables and surfacing them through the existing `aclshow` command.

---

## 5. Requirements

**Functional**

1. Populate real packet / byte counters in `aclshow -a` for every CACL rule that `caclmgrd` installs — both user-configured rules and implicit ones (BFD, BGP, DHCP, VXLAN, ICMP, traceroute, etc.).
2. Preserve existing `aclshow` behavior for data-plane ACLs (SAI counters keep flowing through `COUNTERS_DB` / `ACL_COUNTER_RULE_MAP` unchanged).
3. Keep CLI muscle memory intact: no new flags for the summary view.
4. Provide `aclshow -a -vv` as a verbose iptables dump for debugging why a specific rule did or did not match.
5. `-t <table>` and `-r <rule>` filters apply across both counter sources.

**Non-functional**

1. No new services, sockets, or DBus interfaces — cross-component communication is exclusively via `COUNTERS_DB`.
2. Poll cadence must not perceptibly load the box; a 10 s cadence is sufficient.
3. All `subprocess` calls into `iptables` must use argv lists (no `shell=True`, no string interpolation of untrusted input).
4. Rolling upgrades must be safe in either order — an image with only one side of the change must degrade gracefully.

**Exemptions / non-goals**

- No ASIC programming of CACL rules.
- No changes to CLI flags, CONFIG_DB, or YANG.
- No replacement of SAI counters for data-plane ACL tables.

---

## 6. Architecture Design

The design is split between two components that already own the relevant surfaces:

- **`caclmgrd`** (in `sonic-host-services`) gains a periodic polling thread that samples `iptables -L -v -n -x --line-numbers` (and the `ip6tables` equivalent) in every network namespace it manages, converts each rule to a `COUNTERS_DB` row, and — where possible — tags the row with the originating CACL `(table, rule)`.
- **`aclshow`** (in `sonic-utilities`) reads the new iptables counter rows out of `COUNTERS_DB`, aggregates them per CACL rule name, and falls back to those aggregated numbers whenever the SAI counter for a CACL rule is `N/A`. A new verbose iptables view is added.

Both sides communicate **exclusively through `COUNTERS_DB`** — no new DBus interface, no new sockets, and no changes to `caclmgrd`'s existing ACL translation logic.

```
        +----------------------+                  +------------------------+
        |   caclmgrd (host)    |                  |   aclshow (CLI)        |
        |----------------------|                  |------------------------|
        | 1. Build iptables    |                  | 1. Read SAI counters   |
        |    rules from        |                  |    from COUNTERS_DB    |
        |    CONFIG_DB         |                  |    (existing path)     |
        |                      |                  |                        |
        | 2. Track (namespace, |                  | 2. Read iptables       |
        |    chain, spec) ->   |   COUNTERS_DB    |    counters from       |
        |    (table, rule)     |  <------------>  |    IPTABLES_COUNTER_   |
        |    map               |                  |    RULE_MAP + COUNTERS |
        |                      |                  |                        |
        | 3. Every 10s:        |                  | 3. Aggregate iptables  |
        |    - run iptables    |                  |    counters by         |
        |      -L -v -n -x     |                  |    rule_name, use as   |
        |    - parse counters  |                  |    fallback when SAI   |
        |    - map -> table /  |                  |    counter is N/A      |
        |      rule name       |                  |                        |
        |    - push to         |                  | 4. In -vv mode, dump   |
        |      COUNTERS_DB     |                  |    raw iptables view   |
        +----------------------+                  +------------------------+
```

This is not a SONiC Application Extension; it is an in-tree change to two existing components.

---

## 7. High-Level Design

### 7.1 Repositories and modules changed

- `sonic-host-services` — a new periodic polling thread inside `caclmgrd`, plus a small `(iptables spec) → (CACL table, rule)` mapping table populated as rules are rendered.
- `sonic-utilities` — `aclshow` reads the new `COUNTERS_DB` tables and gains an iptables verbose view.

No changes to `sonic-swss`, `orchagent`, SAI, or `sonic-buildimage`.

### 7.2 `caclmgrd` iptables counter poller

A daemon polling thread runs alongside the existing manager loop and wakes up every **10 seconds**. On each tick it reads `iptables -L -v -n -x --line-numbers` and the `ip6tables` equivalent for every namespace it already manages, and pushes packet / byte counts into `COUNTERS_DB`. While rendering CACL rules, `caclmgrd` also records a mapping from the iptables rule spec back to the originating CACL `(table, rule)` — for user-configured rules and for implicit ones (`DEFAULT_ICMP`, `DEFAULT_BGP`, `DEFAULT_DHCP*`, etc.). TTL / HL system rules are tagged with a synthetic `SYSTEM_TRACEROUTE` label so the verbose view can still identify them. Rows that cannot be attributed (e.g. conntrack `RELATED,ESTABLISHED` accept, loopback accept) are still written to `COUNTERS_DB` with an empty `(table, rule)` and only surface in `-vv` output.

### 7.3 `aclshow` fallback and verbose view

SAI-based counters continue to feed data-plane ACL rows exactly as before. For every ACL rule whose SAI counter is `N/A`, `aclshow` looks up the rule name in the iptables counter table and, if present, substitutes the aggregated iptables packets / bytes (multiple iptables rows belonging to the same CACL rule are summed). In verbose mode (`-vv`), the summary is followed by full IPv4 and IPv6 iptables tables. `-t <table>` and `-r <rule>` filters apply across both counter sources.

Command surface (flags unchanged, semantics extended):

| Command              | Behavior                                                                              |
|----------------------|---------------------------------------------------------------------------------------|
| `aclshow`            | SAI counters only (existing default).                                                  |
| `aclshow -a`         | SAI counters + iptables fallback for CACL rules. `N/A` disappears for CACL entries.    |
| `aclshow -a -vv`     | Adds full IPv4 and IPv6 iptables tables underneath the summary.                        |
| `aclshow -t <table>` | Filter by table across both counter sources.                                           |
| `aclshow -r <rule>`  | Filter by rule across both counter sources.                                            |
| `aclshow -c`         | Unchanged — clears the SAI counter snapshot cache.                                     |

Example output with the fallback active:

```
admin@sonic:~$ aclshow -a
RULE NAME          TABLE NAME            PRIO  PACKETS COUNT    BYTES COUNT
-----------------  ------------------  ------  ---------------  -------------
RULE_50_HTTPS      IPV4_PROTECT_HTTPS    9989  0                0
RULE_999_DENY_ALL  IPV4_PROTECT_HTTPS       1  0                0
RULE_10_ICMP       IPV4_PROTECT_RE       9999  0                0
RULE_20_BGP        IPV4_PROTECT_RE       9998  0                0
...
```

And the appended verbose block:

```
================================================================================
IPv4 iptables Rules
================================================================================
CHAIN      NUM  TARGET  PROT  IN     OUT  SOURCE     DESTINATION      PACKETS COUNT    BYTES COUNT
-------  -----  ------  ----  -----  ---  ---------  -------------  ---------------  -------------
INPUT       10  DROP       0  *      *    0.0.0.0/0  10.1.0.32                    0              0
INPUT        1  ACCEPT     0  lo     *    127.0.0.1  0.0.0.0/0               244182       46210211
INPUT        2  ACCEPT     0  *      *    0.0.0.0/0  0.0.0.0/0             28829734     1775148695
...
```

### 7.4 COUNTERS_DB schema additions

Two new tables are introduced; existing `ACL_COUNTER_RULE_MAP` and `COUNTERS:<oid>` entries are untouched.

- **`IPTABLES_COUNTER_RULE_MAP`** — index that maps a stable `rule_id` (derived from IP version, chain, line number, target, protocol, interfaces, and addresses) to its `COUNTERS:<rule_id>` row.
- **`COUNTERS:<rule_id>`** — one row per iptables rule with packet / byte counts, the raw iptables descriptors (chain, num, target, prot, in, out, source, destination, extra) and, when known, the resolved CACL `table_name` / `rule_name`.

Because `rule_id` is deterministic per iptables ruleset, each poll simply overwrites the previous value and no explicit garbage collection is required.

### 7.5 Concurrency and failure handling

- The poller runs as a daemon thread and exits with the `caclmgrd` process via the existing signal path.
- Parse errors on a single iptables line are logged and skipped without aborting the poll cycle.
- `aclshow` treats a missing `IPTABLES_COUNTER_RULE_MAP` defensively: the fallback path simply does not fire and behavior matches the pre-change baseline.

### 7.6 Security considerations

- The polling thread runs inside `caclmgrd`, which already executes with the privileges required to program iptables; the change does not broaden that trust boundary.
- All `subprocess` invocations use argv lists (no `shell=True`, no string concatenation of untrusted input). The only inputs that affect the argv are the namespace prefix (already fully controlled by `caclmgrd`) and the fixed literal `["iptables"|"ip6tables", "-L", "-v", "-n", "-x", "--line-numbers"]`.
- Parsed fields (source / destination / extra) are written straight into `COUNTERS_DB` as strings and are never evaluated or fed back into a shell.
- `aclshow` only reads from `COUNTERS_DB` — no writes, no privilege escalation, no new IPC.

### 7.7 Platform dependency

Host-level change to two Python components. No ASIC or SAI interaction. Runs on all supported SONiC platforms; no vendor-specific enablement required.

---

## 8. SAI API

Not applicable. This feature does not use, add, or modify any SAI APIs — CACL counters are sourced from Linux iptables on the host, not from the ASIC.

---

## 9. Configuration and Management

### 9.1 Manifest

Not applicable — the change is delivered in the existing `sonic-host-services` and `sonic-utilities` packages, not as a SONiC Application Extension.

### 9.2 CLI/YANG model Enhancements

No new CLI flags or YANG leaves are added. Existing flags (`-a`, `-t`, `-r`, `-c`, `-vv`) have their semantics extended as summarized in §7.3. Existing `aclshow` behavior without `-a` is unchanged, so scripts that rely on the default output continue to work.

### 9.3 Config DB Enhancements

No `CONFIG_DB` schema changes. `COUNTERS_DB` gains two new tables (`IPTABLES_COUNTER_RULE_MAP` and `COUNTERS:<rule_id>`) as described in §7.4; existing `ACL_COUNTER_RULE_MAP` and `COUNTERS:<oid>` rows are untouched. Downward compatibility is preserved:

- On an image built without the `sonic-host-services` change, `IPTABLES_COUNTER_RULE_MAP` simply does not exist and `aclshow` degrades to its pre-change behavior (`N/A` for CACL rules).
- On an image built without the `sonic-utilities` change, `caclmgrd` keeps populating `COUNTERS_DB` but no CLI consumes it — harmless. Rolling upgrades are safe in either order.

---

## 10. Warmboot and Fastboot Design Impact

Neither the poller nor the CLI extension is in the data-plane or control-plane critical boot chain. Counters in `COUNTERS_DB` are transient and are simply repopulated on the next poll after `caclmgrd` comes back up. Existing warmboot / fastboot downtime targets are unaffected.

---

## 11. Memory Consumption

Bounded by the number of iptables rules on the host (typically low tens of rules per namespace). Each poll overwrites the previous row, so `COUNTERS_DB` size does not grow over time. `aclshow` builds its aggregation dictionary in-memory per invocation and releases it on exit.

---

## 12. Restrictions/Limitations

1. **Poll granularity.** Counters are refreshed every 10 seconds; sub-second precision is not available.
2. **Attribution completeness.** Iptables rules without a resolvable CACL `(table, rule)` (e.g. conntrack accept, loopback accept) only appear in the `-vv` view.
3. **Rule identity.** `rule_id` is derived from iptables position and match spec; renumbering the chain shifts identities and produces a fresh `COUNTERS:<rule_id>` row.
4. **Namespace scope.** Only namespaces already managed by `caclmgrd` are polled.
5. **No SAI or platform enablement**, and therefore no vendor-specific dependencies.

---

## 13. Testing Requirements/Design

### 13.1 Unit Test cases

- **Iptables parsing** — `iptables -L -v -n -x --line-numbers` output is parsed into the expected `rule_id` and counter fields, including protocol / interface / extra columns.
- **CACL attribution** — user-configured and implicit CACL rules resolve to the correct `(table, rule)` labels; system TTL / HL rules get `SYSTEM_TRACEROUTE`.
- **Unattributed rows** — rules with no CACL mapping still land in `COUNTERS_DB` with empty `(table, rule)`.
- **Aggregation** — multiple iptables rows tied to the same CACL rule are summed correctly in `aclshow`.
- **Fallback selection** — `aclshow -a` uses SAI counters when present and the iptables fallback only when the SAI counter is `N/A`.
- **Filter compatibility** — `-t <table>` and `-r <rule>` apply consistently to both counter sources.
- **Verbose view** — `aclshow -a -vv` emits full IPv4 and IPv6 iptables tables underneath the summary.
- **Missing table safety** — with `IPTABLES_COUNTER_RULE_MAP` absent, `aclshow` matches its pre-change baseline output.
- **Argv safety** — subprocess invocations use argv lists only, with no `shell=True` and no interpolation of external input.
- **Parse-error isolation** — a malformed iptables line is logged and skipped without aborting the poll cycle.

### 13.2 System Test cases

- End-to-end: apply representative CACL rules (HTTPS accept/deny, BGP, DHCP, ICMP), generate matching traffic, and verify counters in `aclshow -a`.
- Verify data-plane ACL rows continue to display SAI counters unchanged (regression).
- Warmboot / fastboot: verify counters repopulate after the reboot and boot-time targets are unaffected.

---

## 14. Open/Action items
