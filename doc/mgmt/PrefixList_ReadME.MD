# BGP Prefix List Implementation — High Level Design (HLD)

# Revision
| Rev | Date       | Author         | Change Description                                                                                                                                                          |
|:---:|:----------:|:--------------:|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1 | 11/25/2025 | Soumya Gargari | Initial version                                                                                                                                                              |
| 0.2 | 06/19/2026 | Soumya Gargari | Added constraint catalog, prefix normalization, host-bits rejection, payload-side sequence-number validation, sequence-number leaf protection, post-xfmr auto-cleanup behavior |

## Table of Contents
1. Overview
2. User-Facing Constraints
3. Implementation Details
4. Validation Layers
5. Validation Rule Catalog
6. Prefix Normalization
7. Sequence-Number Uniqueness — Three Collision Modes
8. Self-Skip Semantics
9. Sequence-Number Leaf Protection
10. Post-Transformer Auto-Cleanup
11. YANG Model
12. Database Schema
13. Test Scenarios
14. API Examples
15. Error Catalog

---

## Overview

This document describes the implementation of BGP Prefix Lists in SONiC using OpenConfig YANG. The implementation supports CRUD operations on IPv4 and IPv6 prefix lists through gNMI / REST, with strict validation of prefix format, sequence-number uniqueness, mode / family alignment, and mask-length-range integrity.

### Key Features
- IPv4 and IPv6 prefix list support
- Strict IP-prefix normalization with host-bits rejection
- Sequence-number-based ordering with three-mode collision detection across both committed DB and in-flight payload
- PERMIT / DENY actions
- Sequence-number-leaf delete protection
- Auto-cleanup of empty `PREFIX_SET` container on last-prefix deletion
- Symmetric GET / DELETE by either raw or canonical URI form
- OpenConfig compliance, with `openconfig-routing-policy-ext` augments for `sequence-number` and `action`

### Component Responsibilities
1. **API Layer** — gNMI / REST request handling and OpenConfig schema validation
2. **Transformer Layer** — OpenConfig ↔ SONiC translation, DB key construction, cross-entry validation
3. **Validation Layer** — Format, host-bits, mode-family, mask-range, sequence-number uniqueness (DB + payload)
4. **Post-Transformer Layer** — Auto-cleanup of orphaned `PREFIX_SET` containers
5. **Redis CONFIG_DB** — Persistent storage in SONiC schema

---

## User-Facing Constraints

A client may attempt any of the following payloads. Each is **rejected by design**, with the validation hook that enforces it noted in the right column.

| # | What the user may try                                                                                            | Why it's not allowed                                                                                              | Enforced by                                  |
|:-:|------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| 1 | IP prefix with host bits set (e.g. `192.168.1.1/24`, `2001:db8::1/64`)                                            | A prefix-list entry matches a *network*, not a host. Storing a host address as a prefix is meaningless and ambiguous. | `validatePrefixListFormat`                    |
| 2 | Non-canonical IPv6 spellings (e.g. `0::/64`, `2001:db8:0:0::/32`, `2001:0db8::/32`)                                | Multiple spellings of the same network would otherwise produce duplicate DB rows and break GET / DELETE.            | `validatePrefixListFormat` (auto-normalizes)  |
| 3 | `mask-length-range` syntax other than `MIN..MAX` or single value (e.g. `8-24`, `8:24`, `abc..def`)                  | Range is a typed contract; arbitrary separators would be silently misread.                                          | `validateMaskLengthRange`                     |
| 4 | `mask-length-range` where `MIN > MAX` (e.g. `24..12`)                                                              | Inverted range matches nothing and is almost always a typo.                                                         | `validateMaskLengthRange`                     |
| 5 | Single-value `mask-length-range` that does not equal the prefix length (e.g. `10.0.0.0/8` with `24..24`)            | Single value form means "exact length"; mismatch yields an entry that can never match.                              | `validateMaskLengthRange`                     |
| 6 | Range whose `MIN`/`MAX` neither equals the prefix length (e.g. `10.0.0.0/8` with `12..24`)                          | OpenConfig convention requires the prefix length to be an endpoint of the range.                                    | `validateMaskLengthRange`                     |
| 7 | `ip-prefix` family different from the enclosing `prefix-set` `mode` (e.g. IPv4 prefix inside an IPV6 set)            | Family must match; the DB key carries `mode` and routes use it for table selection.                                 | `getPrefixIpType` + family compare            |
| 8 | A `/prefix` entry with no `sequence-number` (CREATE / UPDATE / REPLACE)                                            | `sequence-number` is part of the redis key — without it there is no key to write under.                              | `getSeqNumber`                                |
| 9 | UPDATE / PATCH / REPLACE that changes only the `sequence-number` of an existing entry (same `ip-prefix`, new seq)   | seqNum is encoded in the key; in-place change would create a *second* row, leaving the original orphaned.            | `validateUniqueSeqNumber` (mode 1)            |
| 10 | Two different prefixes in the same set sharing one `sequence-number` (across requests or in one payload)            | Evaluation order in routing policy is defined by seqNum; sharing makes ordering undefined.                          | `validateUniqueSeqNumber` (mode 2)            |
| 11 | A single payload that contains the same prefix written two different ways (e.g. `0::/64` and `::/64`)               | Both YANG list entries collapse to one DB key; the second write would silently overwrite the first.                 | `validateUniqueSeqNumber` (mode 1b, payload walk) |
| 12 | DELETE on the `sequence-number` leaf alone (e.g. `.../config/sequence-number`)                                     | The leaf lives inside the key; it cannot be removed without removing the whole row. Caller should DELETE the entry. | `YangToDb_rpol_prefix_list_prefix_seq_xfmr`   |
| 13 | DELETE of an entry using a raw URI form when the DB row is stored under the canonical form (or vice versa)         | Lookup must be symmetric with write — otherwise the row appears "missing" to the client that created it.            | `validatePrefixListFormat` on read path       |
| 14 | DELETE of the last `/prefix` in a set, expecting the `PREFIX_SET` container to remain                              | An empty `PREFIX_SET` is an orphan; we clean it up so the namespace stays consistent without a second request.       | `routing_policy_post_xfmr` (auto-cleanup)     |
| 15 | Idempotent re-PATCH of an entry's `sequence-number` to its *current* value                                          | **Accepted.** Re-asserting the same value is a legal no-op; self-skip logic prevents false-positive collision.       | `validateUniqueSeqNumber` self-skip           |

Constraints 9–11 (sequence-number collisions) are unified into one rule engine — see Sequence-Number Uniqueness — Three Collision Modes.

---

## Implementation Details

### File Structure
```
sonic-mgmt-common/
├── translib/transformer/
│   ├── xfmr_prefix_list.go          # Transformer implementation
│   └── xfmr_prefix_list_test.go     # Regression test suite (testapp build tag)
├── models/yang/
│   └── sonic-routing-policy-sets.yang
└── models/yang/extensions/
    └── openconfig-routing-policy-ext.yang   # sequence-number + action augments
```

### Key Constants
```go
BGP_PREFIX_TABLE              = "PREFIX"
BGP_PREFIX_SET_TABLE          = "PREFIX_SET"

SONIC_BGP_PREFIX_MODE_IPV4    = "IPv4"          // DB form
SONIC_BGP_PREFIX_MODE_IPV6    = "IPv6"          // DB form
OC_BGP_PREFIX_MODE_IPV4       = "IPV4"          // OpenConfig enum
OC_BGP_PREFIX_MODE_IPV6       = "IPV6"          // OpenConfig enum

SONIC_BGP_PREFIX_ACTION_PERMIT = "permit"       // DB form
SONIC_BGP_PREFIX_ACTION_DENY   = "deny"         // DB form
OC_BGP_PREFIX_ACTION_PERMIT    = "PERMIT"       // OpenConfig enum
OC_BGP_PREFIX_ACTION_DENY      = "DENY"         // OpenConfig enum
```

---

## Validation Layers

Validation runs in **layers**, each guarding a distinct invariant.

| Layer | Function                         | Invariant guarded                                                                            |
|:-----:|----------------------------------|----------------------------------------------------------------------------------------------|
| L1    | `validateMaskLengthRange`        | mask-range syntax; bounds; alignment with prefix length                                       |
| L2    | `validatePrefixListFormat`       | CIDR syntax; family detection; host-bits rejection; normalization                             |
| L3    | `getPrefixIpType` + family check | `ip-prefix` family matches enclosing `prefix-set` `mode`                                      |
| L4    | `getSeqNumber`                   | `sequence-number` is present (mandatory for CRU)                                              |
| L5    | `validateUniqueSeqNumber`        | Cross-entry uniqueness across both committed DB rows and in-flight payload siblings           |
| L6    | post-xfmr                        | Auto-cleanup of empty `PREFIX_SET` container on last-prefix deletion                          |

L1 – L4 are per-entry (cheap, local). L5 walks two sources. L6 runs once per delete request.

### Operation-specific behavior

| Operation                              | L1 | L2 | L3 | L4 | L5 | L6 |
|----------------------------------------|:--:|:--:|:--:|:--:|:--:|:--:|
| CREATE / UPDATE / REPLACE              | ✓  | ✓  | ✓  | ✓  | ✓  |    |
| DELETE (whole prefix entry)            | ✓  | ✓  |    |    |    | ✓  |
| DELETE (sequence-number leaf only)     | —  | —  | —  | —  | —  | —  ← **rejected outright** |
| GET                                    | ✓  | ✓  |    |    |    |    |

---

## Validation Rule Catalog

### Mask-length-range rules (L1)

```
ip-prefix has length P; mask-length-range may be:
  • empty                  → accepted (no constraint)
  • single value V         → V == P required
  • range MIN..MAX         → MIN <= MAX required, AND P == MIN || P == MAX
```

| Input                        | Verdict   | Reason                                       |
|------------------------------|-----------|----------------------------------------------|
| `10.0.0.0/8`, `8..24`        | accepted  | P=8 matches MIN                              |
| `10.0.0.0/8`, `8..8`         | accepted  | P=8 matches both endpoints                   |
| `10.0.0.0/8`, `24..24`       | rejected  | single-value form, P ≠ V                     |
| `10.0.0.0/8`, `12..24`       | rejected  | P=8 is neither MIN(12) nor MAX(24)           |
| `10.0.0.0/8`, `24..12`       | rejected  | MIN > MAX                                    |
| `10.0.0.0/8`, `8-24`         | rejected  | wrong separator                              |

### Prefix-format rules (L2)

```
For ip-prefix P/N:
  • N must be in [0..32] (IPv4) or [0..128] (IPv6)
  • net.ParseCIDR(P/N) must succeed
  • Parsed IP must equal the network address (no host bits set)
  • Canonical form (net.IPNet.String()) is the DB-side spelling
```

| Input                  | Family | Verdict   | Stored as                       |
|------------------------|:------:|-----------|---------------------------------|
| `10.0.0.0/8`           | IPv4   | accepted  | `10.0.0.0/8`                    |
| `10.0.0.5/8`           | IPv4   | rejected  | host bits set                   |
| `2001:db8::/32`        | IPv6   | accepted  | `2001:db8::/32`                 |
| `2001:db8:0:0::/32`    | IPv6   | accepted  | `2001:db8::/32` (normalized)    |
| `0::/64`               | IPv6   | accepted  | `::/64` (normalized)            |
| `2001:db8::1/64`       | IPv6   | rejected  | host bits set                   |
| `10.0.0.0/33`          | IPv4   | rejected  | bad mask length                 |
| `2001:db8::/129`       | IPv6   | rejected  | bad mask length                 |

**Unified wording:** both families return `"Prefix has host bits set: expected <canonical>, got <input>"`.

### Mode / family alignment (L3)

`prefix-set.mode` (IPV4 | IPV6) must match the family detected from `ip-prefix`. Mode is sourced from the payload first (current request's `PrefixSet.Config.Mode`), then CONFIG_DB (`PREFIX_SET|<name>.mode`), defaulting to IPV4 if neither carries it.

---

## Prefix Normalization

All write paths (CRU) and read paths (GET, DELETE) call `validatePrefixListFormat` to normalize the prefix **before** building the DB key. Normalization is `net.IPNet.String()`-based and is the single source of truth for what the DB key looks like.

```
Raw input         →  Canonical (DB) form
─────────────────    ─────────────────────
0::/64            →  ::/64
2001:db8:0:0::/32 →  2001:db8::/32
2001:0db8::/32    →  2001:db8::/32
10.0.0.0/8        →  10.0.0.0/8      (already canonical)
```

**Why both write and read normalize:** without symmetry, a row created under the canonical key cannot be retrieved using the original raw URI. Both directions now resolve to the same key.

**URI vs payload key spelling:** OpenConfig YANG list keys are strings, not semantic objects. A client may legally write:
- URI: `[ip-prefix=::/64]`
- Payload: `"ip-prefix": "0::/64"`

`getSeqNumber` tries **both** the URI spelling and the normalized spelling when looking up `sequence-number` in `ygRoot`, so either form succeeds.

---

## Sequence-Number Uniqueness — Three Collision Modes

`validateUniqueSeqNumber` is the heart of cross-entry validation. It runs for every CRU on a `/prefix` entry and walks **two sources**:

1. **Committed DB rows** — read via `GetKeysPattern("PREFIX|<set>|*|*|*")`
2. **Sibling entries in the current request payload** — walked from `inParams.ygRoot`

The payload walk is necessary because xfmr functions only build a write map; nothing is committed until the framework finalizes all xfmr calls. While the key xfmr is processing entry K, sibling entries in the same request are still in the in-memory write map and invisible to `GetKeysPattern`.

### Rule table (applied identically to both sources)

| Mode | Existing key vs Incoming key                | Verdict (CRU) | Verdict (other oper) | Source where reachable | Rationale                                                                                  |
|:----:|---------------------------------------------|---------------|----------------------|------------------------|---------------------------------------------------------------------------------------------|
| 1    | same `(ip, mask)`, **different** seq         | **reject**    | no-op                | DB + payload           | seqNum is in the redis key; in-place change is unsafe → caller must DELETE + re-CREATE     |
| 1b   | same `(ip, mask)`, **same** seq              | **reject**    | n/a                  | payload only           | Two YANG list entries collapsing to same DB key → second write would silently overwrite first |
| 2    | **different** `(ip, mask)`, **same** seq     | **reject**    | reject               | DB + payload           | Two distinct prefixes sharing a seqNum → evaluation order undefined                         |

**Mode 1b is unreachable from the DB source** by redis-key uniqueness. A defensive nil return is kept in code for safety.

### Error wordings

| Mode | Wording                                                                              |
|:----:|--------------------------------------------------------------------------------------|
| 1    | `same prefix is configured with different sequence`                                   |
| 1b   | `duplicate prefix entry in payload (multiple spellings of <ip>)`                      |
| 2    | `Same sequence number is configured with different rule <seq>, delete it first`       |

### Non-determinism note (for test authors)

`GetKeysPattern` returns Redis KEYS results in unordered fashion. When a fixture deliberately triggers **multiple** collision modes simultaneously (e.g. PATCH A's seq to B's seq), either mode-1 or mode-2 may fire first depending on which row Redis returns first. Both are correct rejections; test assertions should accept either wording in such cases (helper: `expectSetRejectedWithOneOf`).

---

## Self-Skip Semantics

An entry must not flag itself as a collision. Self-skip rules differ by source because the identity of "self" differs:

| Source  | Self-skip predicate                                                                              | Why                                                                                                                            |
|---------|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| DB row  | full normalized-key match: `(existingIp, existingMask, existingSeq) == (norm, mask, seq)`        | Idempotent re-assert of an already-committed row should be a no-op                                                              |
| Payload | raw YANG list-key match: `(k.IpPrefix, k.MasklengthRange) == (originalPrefix, mask)`             | YANG list keys are unique strings; the entry the framework is currently calling us about is identified by its raw URI predicate |

This is why idempotent re-PATCH of an entry's `sequence-number` to its current value is accepted — the DB self-skip kicks in.

---

## Sequence-Number Leaf Protection

The `sequence-number` leaf is exposed under `openconfig-routing-policy-ext`. It is **encoded in the redis key**, not as a hash field.

| Oper                      | Behavior                                                                                                                                                                            |
|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CREATE / UPDATE / REPLACE | No-op return (`map[string]string{}`). The seqNum is built into the key by `YangToDb_rpol_prefix_list_prefix_key_xfmr`; no separate field to write.                                  |
| DELETE                    | **Rejected** with `InvalidArgsError`: `sequence-number cannot be deleted in isolation; delete the whole prefix entry instead`.                                                       |

The caller's correct path to change a seqNum is: DELETE the whole `/prefix` entry, then re-CREATE with the desired seqNum.

`DbToYang_rpol_prefix_list_prefix_seq_xfmr` reads `sequence-number` back from component `[1]` of the DB key for GET responses.

---

## Post-Transformer Auto-Cleanup

```go
routing_policy_post_xfmr(inParams XfmrParams) error
```

**Behavior on DELETE of `/prefix-set/<N>/prefixes/prefix[...]`:**

1. Read `PREFIX|<N>|*` keys from CONFIG_DB.
2. If exactly **one** key remains (i.e. this delete will remove the last entry), inject a `subOpDataMap` DELETE for `PREFIX_SET|<N>`.
3. The framework commits both deletes atomically.

| Initial state              | Action            | Final DB state                                  |
|----------------------------|-------------------|-------------------------------------------------|
| 3 prefixes in set `S`      | DELETE 1 prefix   | 2 prefixes in `S`; `PREFIX_SET|S` intact         |
| 2 prefixes in set `S`      | DELETE 1 prefix   | 1 prefix in `S`; `PREFIX_SET|S` intact           |
| 1 prefix in set `S`        | DELETE the prefix | **No `PREFIX` rows; `PREFIX_SET|S` also gone**   |

This eliminates orphaned-set inconsistency without forcing the client to issue two DELETEs.

---

## YANG Model

### YANG Tree

```
module: openconfig-routing-policy
  +--rw routing-policy
     +--rw defined-sets
     |  +--rw prefix-sets
     |  |  +--rw prefix-set* [name]
     |  |     +--rw name        -> ../config/name
     |  |     +--rw config
     |  |     |  +--rw name?                    string
     |  |     |  +--rw mode?                    enumeration
     |  |     |  +--rw oc-rp-ext:description?   string
     |  |     +--ro state
     |  |     |  +--ro name?                    string
     |  |     |  +--ro mode?                    enumeration
     |  |     |  +--ro oc-rp-ext:description?   string
     |  |     +--rw prefixes
     |  |        +--rw prefix* [ip-prefix masklength-range]
     |  |           +--rw ip-prefix           -> ../config/ip-prefix
     |  |           +--rw masklength-range    -> ../config/masklength-range
     |  |           +--rw config
     |  |           |  +--rw ip-prefix                    oc-inet:ip-prefix
     |  |           |  +--rw masklength-range?            string
     |  |           |  +--rw oc-rp-ext:sequence-number?   uint32
     |  |           |  +--rw oc-rp-ext:action?            enumeration
     |  |           +--ro state
     |  |              +--ro ip-prefix                    oc-inet:ip-prefix
     |  |              +--ro masklength-range?            string
     |  |              +--ro oc-rp-ext:sequence-number?   uint32
     |  |              +--ro oc-rp-ext:action?            enumeration
```

### Notes on the augmentations

- `oc-rp-ext:sequence-number` (uint32) — augmented into both `prefix/config` and `prefix/state`. Forms component `[1]` of the SONiC `PREFIX` redis key. Mandatory on CRU; cannot be deleted in isolation.
- `oc-rp-ext:action` (enumeration: `PERMIT` | `DENY`) — augmented into both `prefix/config` and `prefix/state`. Maps to SONiC `action` field (`permit` | `deny`).
- `oc-rp-ext:description` (string) — augmented into `prefix-set/config` and `prefix-set/state`. Reserved for future use.

### SONiC schema
The transformer-side validation supersedes the SONiC `must` constraint on `sequence_number` uniqueness; the cross-source walk in `validateUniqueSeqNumber` is authoritative.

---

## Database Schema

### `PREFIX` table
```
Key   : PREFIX|<set-name>|<seq>|<ip-prefix>|<masklength-range>
Fields: action  (permit|deny)
        mode    (IPv4|IPv6)
```

### `PREFIX_SET` table
```
Key   : PREFIX_SET|<set-name>
Fields: mode    (IPv4|IPv6)
```

### Key Formation Rules

| Rule | Description                                                                                      |
|:----:|--------------------------------------------------------------------------------------------------|
| K1   | `ip-prefix` portion of the key is **always** the canonical (normalized) form                      |
| K2   | `sequence-number` is part of the key; in-place modification is forbidden (mode 1)                |
| K3   | Two PREFIX rows sharing `(set, ip, mask)` cannot exist (mode 1 + redis key uniqueness)            |
| K4   | Two PREFIX rows sharing `(set, seq)` cannot exist (mode 2)                                       |
| K5   | Deletion of the last PREFIX in a set also deletes the `PREFIX_SET` container (post-xfmr)         |

---

## Test Scenarios

The regression suite in `xfmr_prefix_list_test.go` (built under the `testapp` tag) covers:

| Test                                         | Scenario                                                                                                  |
|----------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `Test_ipv6_zero_short_form`                  | POST `0::/64` lands under canonical `::/64`                                                                |
| `Test_ipv6_embedded_zeros`                   | POST `2001:db8:0:0::/32` lands under `2001:db8::/32`                                                       |
| `Test_ipv6_host_bits_rejected`               | IPv6 host bits rejected with unified wording                                                                |
| `Test_get_delete_both_uri_forms`             | GET / DELETE works with either raw or canonical URI form                                                   |
| `Test_h2_update_duplicate_seq_rejected`      | PATCH / PUT reusing another prefix's seqNum is rejected (accepts mode-1 or mode-2 wording — non-determinism note above) |
| `Test_payload_dup_after_normalization`       | Single payload with same-prefix two spellings / same-seq diff-prefix / etc.                                |
| `Test_delete_sequence_number_leaf_rejected`  | DELETE on `/config/sequence-number` and `/state/sequence-number` rejected; row intact                      |
| `Test_oc_bgp_invalid_operations`             | Same prefix with different seqs rejected; mode-mismatch rejected                                            |

---

## API Examples

### Create an IPv6 set with one entry (canonical input)
```bash
gnmi_set -update_path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=v6_set]" \
  -update_val '{
    "config": {"name":"v6_set", "mode":"IPV6"},
    "prefixes": {"prefix": [{
       "ip-prefix": "2001:db8::/32",
       "masklength-range": "32..48",
       "config": {
         "ip-prefix": "2001:db8::/32",
         "masklength-range": "32..48",
         "sequence-number": 10,
         "action": "PERMIT"
       }
    }]}
  }'
```

### Create with non-canonical input (auto-normalized)
```bash
# Client sends "0::/64", DB row is keyed "::/64"
gnmi_set -update_path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=0::/64][masklength-range=64..64]/config" \
  -update_val '{"ip-prefix":"0::/64", "masklength-range":"64..64", "sequence-number":20, "action":"PERMIT"}'

# Retrieve using either form:
gnmi_get -path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=0::/64][masklength-range=64..64]"   # ✓
gnmi_get -path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=::/64][masklength-range=64..64]"     # ✓
```

### Reject: same prefix, different seq (mode 1)
```bash
# v6_set already has "2001:db8::/32" at seq=10
gnmi_set -update_path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=2001:db8::/32][masklength-range=32..48]/config/sequence-number" \
  -update_val '{"openconfig-routing-policy-ext:sequence-number": 11}'
# → "same prefix is configured with different sequence"
```

### Reject: different prefix, same seq (mode 2)
```bash
# v6_set already has "2001:db8::/32" at seq=10
gnmi_set -update_path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=2001:dead::/32][masklength-range=32..48]/config" \
  -update_val '{"ip-prefix":"2001:dead::/32","masklength-range":"32..48","sequence-number":10,"action":"PERMIT"}'
# → "Same sequence number is configured with different rule 10, delete it first"
```

### Reject: payload contains two spellings of same prefix
```bash
# Single POST payload with both "0::/64" and "::/64"
# → "duplicate prefix entry in payload (multiple spellings of ::/64)"
```

### Reject: DELETE on sequence-number leaf
```bash
gnmi_set -delete_path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=2001:db8::/32][masklength-range=32..48]/config/sequence-number"
# → "sequence-number cannot be deleted in isolation; delete the whole prefix entry instead"
```

### Last-prefix delete → auto-cleanup
```bash
# v6_set has only "2001:db8::/32" left
gnmi_set -delete_path ".../prefix-set[name=v6_set]/prefixes/prefix[ip-prefix=2001:db8::/32][masklength-range=32..48]"
# Result: PREFIX row removed AND PREFIX_SET|v6_set row removed atomically.
```

---

## Error Catalog

| Error                                                                                              | Layer       | Trigger                                                                |
|----------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------|
| `Invalid IP prefix format: <p>`                                                                     | L1          | malformed CIDR in mask-range validator                                  |
| `Invalid prefix length in IP prefix: <p>`                                                           | L1          | non-numeric mask                                                        |
| `Single mask-length-range value <V> must match the IP prefix length <P>`                            | L1          | single-value form, V ≠ P                                                |
| `IP prefix length <P> must be at the start (<MIN>) or end (<MAX>) of mask-length-range <m>`         | L1          | P not endpoint                                                          |
| `Invalid mask-length-range: min <MIN> greater than max <MAX>`                                       | L1          | MIN > MAX                                                               |
| `Invalid mask-length-range format: <m>`                                                             | L1          | wrong separator                                                         |
| `Invalid prefix format, expected CIDR notation`                                                     | L2          | no `/` in prefix                                                        |
| `Invalid IP address in prefix`                                                                      | L2          | `net.ParseIP` fail                                                      |
| `Invalid IPv4 prefix length` / `Invalid IPv6 prefix length`                                          | L2          | mask out of range                                                       |
| `Prefix has host bits set: expected <canonical>, got <input>`                                        | L2          | non-network address (unified wording)                                   |
| `Invalid ip_prefix format: <err>`                                                                   | L2          | wrapper around L2 internal errors                                       |
| `ip_prefix <p> does not match prefix-set mode <m>`                                                  | L3          | family mismatch                                                         |
| `Only IPv4 and IPv6 are supported for prefix-sets mode`                                              | L3          | unsupported enum                                                        |
| `Sequence number is mandatory for prefix entry. Please provide sequence number.`                     | L4          | seqNum missing in payload and not in DB                                 |
| `same prefix is configured with different sequence`                                                  | L5 mode 1   | `(ip, mask)` match, seq differs                                         |
| `duplicate prefix entry in payload (multiple spellings of <ip>)`                                    | L5 mode 1b  | payload siblings collapse to same DB key                                |
| `Same sequence number is configured with different rule <seq>, delete it first`                     | L5 mode 2   | seq match, `(ip, mask)` differs                                         |
| `sequence-number cannot be deleted in isolation; delete the whole prefix entry instead`              | seq xfmr    | DELETE on `/config/sequence-number` or `/state/sequence-number`         |
| `Prefix entry not found: <ip>|<mask>`                                                                | key xfmr    | GET/DELETE on a non-existent entry                                      |

---

## Performance Considerations

| Aspect                          | Impact                                                                                       |
|---------------------------------|----------------------------------------------------------------------------------------------|
| Mask/format validation          | O(1) per entry — pure string + `net.ParseCIDR`                                                |
| `validateUniqueSeqNumber`       | O(N + M) per CRU, where N = `PREFIX|<set>|*` row count, M = payload siblings in same set      |
| `getSpecificSeqNumberFromDb`    | One `GetKeysPattern` per CRU for seqNum resolution path                                       |
| Post-xfmr last-prefix detection | One `GetKeysPattern` per DELETE                                                              |

Scaling: typical prefix sets hold tens to low hundreds of entries; validation overhead is negligible relative to per-request gNMI / REST framing.

---

## Troubleshooting

### Verifying canonical storage
```bash
# After POST with raw "0::/64", DB should show canonical form:
redis-cli -n 4 keys 'PREFIX|*|::/64|*'
```

### Confirming auto-cleanup
```bash
# After deleting the last /prefix:
redis-cli -n 4 keys 'PREFIX|my_set|*'      # → (empty)
redis-cli -n 4 keys 'PREFIX_SET|my_set'    # → (empty)
```

### Diagnosing seq-uniqueness rejections
Production logs print which collision mode fired and which source detected it:
```
validateUniqueSeqNumber[db]: same prefix configured with different sequence (existing seq=10, new seq=20, ip=2001:db8:a::/48|48..64, oper=UPDATE)
validateUniqueSeqNumber[db]: same sequence number 20 is configured with different rule 2001:db8:b::/48|48..64
validateUniqueSeqNumber[payload]: duplicate prefix entry (two spellings of ::/64|64..64 at seq=10)
```
Tag `[db]` vs `[payload]` identifies the source; the rest pinpoints the conflicting pair.

---

## Conclusion

This revision delivers BGP Prefix Lists with a complete validation surface:

- **Canonicalization** is end-to-end symmetric (write + read), so every spelling of a given prefix maps to exactly one DB row
- **Host-bits** are uniformly rejected with one wording for both families
- **Sequence-number uniqueness** is enforced across both committed DB and in-flight payload, with a three-mode rule catalog that covers every collision shape
- **The sequence-number leaf** is protected from in-isolation DELETE
- **Last-prefix delete** correctly auto-cleans the `PREFIX_SET` container
- **Idempotent re-asserts** are preserved via per-source self-skip predicates, so well-formed clients are never penalized

The regression suite (`xfmr_prefix_list_test.go`) pins each invariant with a dedicated test, and the cross-source collision walk has explicit non-determinism notes for any future test relying on Redis iteration.
