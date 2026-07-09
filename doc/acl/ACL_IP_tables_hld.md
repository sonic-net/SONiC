# aclshow CACL Counters — High Level Design

`aclshow -a` is not working for CACL rules (all counters show `N/A`)

## 1. Problem Statement

SONiC does not program Control-Plane ACL (CACL) rules into the ASIC. Instead `caclmgrd` renders each CACL rule as an `iptables` / `ip6tables` rule on the host. Because CACL rules never reach the ASIC, no SAI ACL counter is created for them, and `COUNTERS_DB` has no entry for them either. As a result `aclshow -a` renders `N/A` in the `PACKETS COUNT` and `BYTES COUNT` columns for every CACL rule:

```
admin@t0-r1-Leaf0:~$ aclshow -a
RULE NAME          TABLE NAME            PRIO  PACKETS COUNT    BYTES COUNT
-----------------  ------------------  ------  ---------------  -------------
RULE_50_HTTPS      IPV4_PROTECT_HTTPS    9989  N/A              N/A
RULE_999_DENY_ALL  IPV4_PROTECT_HTTPS       1  N/A              N/A
RULE_10_ICMP       IPV4_PROTECT_RE       9999  N/A              N/A
...
```

Operators rely on `aclshow` to validate that control-plane protections are hitting; today the only workaround is to correlate configured CACL rules to raw `iptables -L -v -n -x` output by hand, which is not scalable and does not match customer-facing tooling.

## 2. Goals

- Populate real packet / byte counters in the `aclshow -a` output for every CACL rule that `caclmgrd` installs, including both user-configured rules and implicit rules (e.g. BFD, BGP, DHCP, VXLAN, ICMP, traceroute).
- Preserve the existing behaviour of `aclshow` for data-plane ACLs: SAI counters keep flowing through `COUNTERS_DB / ACL_COUNTER_RULE_MAP`.
- Do not require changes to CLI muscle memory: `aclshow -a` continues to be the single command an operator runs.
- Provide a verbose view (`aclshow -a -vv`) that dumps the raw iptables / ip6tables tables (chain, num, target, prot, in, out, source, destination, `dpt`/`dpts` extras) so an operator can debug why a specific rule did or did not match.

## 3. Non-Goals

- Programming CACL rules into the ASIC.
- Changing the semantics or life-cycle of `CONFIG_DB:ACL_RULE` entries.
- Replacing SAI-based counters for data-plane ACL tables.

## 4. High-Level Design

The design is split into two cooperating components that already own the relevant surfaces:

1. **`caclmgrd`** (in `sonic-host-services`) is extended with a periodic polling thread that samples `iptables -L -v -n -x --line-numbers` (and the `ip6tables` equivalent) in every network namespace it manages, converts each rule to a `COUNTERS_DB` row, and — where possible — tags the row with the originating CACL table / rule name.
2. **`aclshow`** (in `sonic-utilities`) is extended to read the new iptables counter rows out of `COUNTERS_DB`, aggregate them per CACL rule name, and fall back to those aggregated numbers whenever the SAI counter for a CACL rule is `N/A`. A new verbose iptables view is added for `aclshow -a`, `aclshow -t <table>` and `aclshow -r <rule>`.

Both sides communicate exclusively through `COUNTERS_DB` — no new DBus interface, no new sockets, and no changes to `caclmgrd`'s existing ACL translation logic.

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

## 5. Component Design

### 5.1 `caclmgrd` changes (sonic-host-services)

`caclmgrd` gains a periodic iptables counter poller:

- A daemon polling thread runs alongside the existing manager loop and wakes up every 10 seconds.
- On each tick it reads `iptables -L -v -n -x` and the ip6tables equivalent for every namespace it already manages, and pushes the packet / byte counts into `COUNTERS_DB`.
- While rendering CACL rules, `caclmgrd` also records a mapping from the iptables rule spec back to the originating CACL `(table, rule)`
  — both for user-configured rules and for implicit rules such as `DEFAULT_ICMP`, `DEFAULT_BGP`, `DEFAULT_DHCP*`. TTL / HL system rules are tagged with a synthetic `SYSTEM_TRACEROUTE` label so the verbose view can still identify them.
- Iptables rows that cannot be attributed (e.g. conntrack `RELATED,ESTABLISHED` accept, loopback accept) are still written to `COUNTERS_DB` with an  empty `(table, rule)` — they are only surfaced in the `-vv` output, never in the summary.

### 5.2 `aclshow` changes (sonic-utilities)

`aclshow` learns about a second counter source:

- SAI-based counters continue to feed data-plane ACL rows exactly as before.
- For every ACL rule whose SAI counter is `N/A`, `aclshow` looks up the rule name in the iptables counter table and, if present, substitutes the aggregated iptables packets / bytes. Multiple iptables rows that belong to the same CACL rule are summed.
- In verbose mode (`-vv`), the summary is followed by full IPv4 and IPv6 iptables tables so operators can debug matches directly.
- The `-t <table>` and `-r <rule>` filters apply to both counter sources.

Command surface (flags unchanged, semantics extended):

| Command              | Behaviour                                                                              |
|----------------------|----------------------------------------------------------------------------------------|
| `aclshow`            | SAI counters only (existing default).                                                  |
| `aclshow -a`         | SAI counters + iptables fallback for CACL rules. `N/A` disappears for CACL entries.    |
| `aclshow -a -vv`     | Adds full IPv4 and IPv6 iptables tables underneath the summary.                        |
| `aclshow -t <table>` | Filter by table across both counter sources.                                           |
| `aclshow -r <rule>`  | Filter by rule across both counter sources.                                            |
| `aclshow -c`         | Unchanged — clears the SAI counter snapshot cache.                                     |

### 5.3 Data Model — `COUNTERS_DB`

Two new tables are introduced; existing `ACL_COUNTER_RULE_MAP` and
`COUNTERS:<oid>` entries are untouched.

- `IPTABLES_COUNTER_RULE_MAP` — index that maps a stable `rule_id` (derived from ip version, chain, line number, target, protocol, interfaces and addresses) to its `COUNTERS:<rule_id>` row.
- `COUNTERS:<rule_id>` — one row per iptables rule with packet / byte counts, the raw iptables descriptors (chain, num, target, prot, in, out, source, destination, extra) and, when known, the resolved CACL `table_name` / `rule_name`.

Because `rule_id` is deterministic per iptables ruleset, each poll simply overwrites the previous value and no explicit garbage collection is required.

### 5.4 Concurrency & failure handling

- The poller runs as a daemon thread; it exits with the caclmgrd process via the existing signal path.
- Iptables is invoked with argv lists (never `shell=True`), so no input is interpolated into a shell command line.
- Parse errors on a single iptables line are logged and skipped without aborting the poll cycle.
- `aclshow` treats a missing `IPTABLES_COUNTER_RULE_MAP` defensively: the fallback path simply does not fire and behaviour matches the pre-change baseline.

## 6. Example Output

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

With verbose mode, the iptables detail is appended:

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

## 8. Backwards Compatibility

- No CONFIG_DB schema changes.
- No YANG model changes.
- No changes to `sonic-swss` / `orchagent` / SAI counter plumbing.
- On any image built without the sonic-host-services change, `IPTABLES_COUNTER_RULE_MAP` will simply not exist, and `aclshow` degrades to its pre-change behaviour (`N/A` for CACL rules).
- On any image built without the sonic-utilities change, `caclmgrd` keeps populating `COUNTERS_DB` but no CLI consumes it — this is harmless and makes rolling upgrades safe in either order.

## 9. Security Considerations

- The polling thread runs inside caclmgrd, which already executes with the privileges required to program iptables; the change does not broaden that trust boundary.
- All `subprocess` invocations use argv lists (no `shell=True`, no string concatenation of untrusted input). The only inputs that affect the argv are the namespace prefix (already fully controlled by caclmgrd) and the fixed literal `["iptables"|"ip6tables", "-L", "-v", "-n", "-x", "--line-numbers"]`.
- Parsed fields (source / destination / extra) are written straight into `COUNTERS_DB` as strings; they are never evaluated or fed back into a shell.
- `aclshow` only reads from `COUNTERS_DB` — no writes, no privilege escalation, no new IPC.

