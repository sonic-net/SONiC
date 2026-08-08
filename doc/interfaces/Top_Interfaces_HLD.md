# SONiC Top N Interfaces HLD
#### Rev 0.1

### Table of Content
- [List of Tables](#list-of-tables)
- [List of Figures](#list-of-figures)
- [1 Revision](#1-revision)
- [2 Scope](#2-scope)
- [3 Definitions/Abbreviations](#3-definitionsabbreviations)
- [4 Overview](#4-overview)
- [5 Requirements](#5-requirements)
- [6 Architecture Design](#6-architecture-design)
- [7 High-Level Design](#7-high-level-design)
- [8 SAI API](#8-sai-api)
- [9 Configuration and management](#9-configuration-and-management)
- [10 Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11 Things to be Considered](#11-things-to-be-considered)
- [12 Testing Requirements/Design](#12-testing-requirementsdesign)
    - [12.1 Unit Test cases](#121-unit-test-cases)
- [13 Stretch Goals](#13-stretch-goals)

## List of Tables
* [Table 1: Revision](#1-revision)
* [Table 2: Abbreviations](#3-definitionsabbreviations)

## List of Figures
* [Figure 1: High-Level Architecture](#6-architecture-design)
* [Figure 2: CLI Execution Flow](#cli-execution-flow)

## 1 Revision
| Rev |     Date    |       Author            | Change Description                |
|:---:|:-----------:|:-----------------------:|-----------------------------------|
| 0.1 | 2026-05-29  | Rishik Yalamanchili     | Initial version |

## 2 Scope
This document describes the high level design of the Top N Interfaces by Traffic feature. It covers:
1. The addition of a `top` subcommand to the existing `show interfaces counters` CLI group within `sonic-utilities`.
2. The extension of the `scripts/portstat` script with new flags for top-N filtering and sorting.
3. The addition of a `get_top_n()` method to the existing `Portstat` class in `utilities_common/portstat.py`.

No changes are required to `sonic-swss`, `orchagent`, Lua plugins, Config DB, or any daemon. The entire feature is implemented within the `sonic-utilities` repository as a **thin filter** on top of existing infrastructure.

## 3 Definitions/Abbreviations
### Table 1: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| RX                       | Receive / Ingress traffic                  |
| TX                       | Transmit / Egress traffic                  |
| BPS                      | Bytes Per Second (as stored in RATES: table by port_rates.lua) |
| PPS                      | Packets Per Second                         |
| OID                      | SAI Object Identifier                      |
| EWMA                     | Exponential Weighted Moving Average        |

## 4 Overview

This document provides general information about the design and implementation of the `show interfaces counters top` feature in SONiC. This feature enables network operators to instantaneously identify the top N interfaces carrying the highest traffic by leveraging the pre-computed rate values already maintained in the `COUNTERS_DB RATES:` table by the existing `port_rates.lua` Flex Counter plugin.

SONiC exposes per-interface traffic counters via COUNTERS_DB and provides CLI tools such as `portstat` and `show interfaces counters` to display them. The existing `show interfaces counters rates` command (backed by `portstat -R`) can display current rates for all interfaces, but operators currently lack a mechanism to quickly identify which interfaces are carrying the **highest** traffic at any given time.

In large-scale deployments with hundreds of ports, manually scanning counter output to find congested interfaces is inefficient and error-prone. Operators need a single command that returns the top N busiest interfaces, ranked by throughput, instantaneously.

### 4.1 Proposed Solution

This feature introduces `show interfaces counters top` as a **thin filter on top of the existing `Portstat` class**. The design reads the `RATES:<oid>` entries that `orchagent`'s `port_rates.lua` plugin already maintains, sorts them by a user-selected key, and displays the top N results.

**Key properties:**
- **Instantaneous**: Results appear in ~50ms (single Redis read pass), with no blocking delay.
- **Numerically consistent**: The rates shown are identical to those displayed by `show interfaces counters rates`, since both read from the same `RATES:` table.
- **Zero backend changes**: No new daemons, no new DB tables, no Lua script modifications, no orchagent changes.

### 4.2 Design Philosophy

The design follows the principle of **maximum reuse of existing infrastructure**:

```
┌──────────────────────────────────────────────────────────────────┐
│ Existing Infrastructure (unchanged)                              │
│                                                                  │
│   ASIC → syncd → COUNTERS:<oid> → port_rates.lua → RATES:<oid>   │
│                                                                  │
│   Portstat class: get_cnstat_dict() → ratestat_dict              │
│   Portstat class: get_port_state(), get_port_speed()             │
│   netstat.py: format_brate(), format_prate(), format_util()      │
└──────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ NEW: Thin Filter   │
                    │                    │
                    │ get_top_n()        │
                    │ Sort + Rank + Top  │
                    │ top CLI command    │
                    └────────────────────┘
```

This approach ensures that the `top` command benefits from all existing and future improvements to the rate computation pipeline (e.g., improved EWMA tuning, FEC BER enhancements) without any additional maintenance burden.

## 5 Requirements

### 5.1 Functional Requirements

- The CLI command must return the top N interfaces **instantaneously** by default, leveraging pre-computed rates in the `COUNTERS_DB RATES:` table. There must be no `time.sleep()` or blocking delay under normal operation.

- The interfaces must be rankable by different keys: `total`, `rx`, `tx`, and `util` (utilization).

- The rank must be capable of sorting by `bps` (Bytes per second) or `pps` (Packets per second).

- The default sort key must be `total` throughput (`RX + TX`), and the default unit `pps`.

- The CLI must be capable of producing JSON formatted output for automation systems.

- The output should provide deterministic tie-breaking for interfaces with identical rates (e.g., multiple interfaces with 0 bps should be naturally sorted by name using `natsorted`).

### 5.2 CLI Requirements

A new CLI command will be introduced as a subcommand of `show interfaces counters`:

```
show interfaces counters top [OPTIONS]

Options:
  -n, --count INTEGER          Number of top interfaces to show. Default: 5.
  --sort [rx|tx|total|util]    Sort key. Default: total.
  --units [bps|pps]            Rank by bytes/sec or packets/sec. Default: pps.
  -j, --json                   JSON output.
  --verbose                    Print the underlying command.
```

**Design decisions for the CLI surface:**

1. **Placement under `counters`**: The command is placed at `show interfaces counters top` rather than `show interfaces top`. This is consistent with the existing CLI tree where all counter-related views (`rates`, `errors`, `fec-stats`, `trim`, `detailed`) are subcommands of `counters`.

2. **Backward compatibility**: The `top` feature introduces a new subcommand of `counters` and new flags in `portstat`. Backward compatibility is fully maintained. No existing CLI commands, scripts, or automation workflows are affected.

### 5.3 Scalability Requirements

- The command execution time must remain sub-second regardless of the number of ports, as it performs a single pass through the `ratestat_dict` already loaded in memory by `Portstat.get_cnstat_dict()`.

- The sorting operation is `O(N log N)` where N is the number of ports. For a 512-port system, this is negligible (~500 comparisons).

- No additional Redis operations are introduced beyond what `Portstat.get_cnstat_dict()` already performs. The `top` filter is a pure Python in-memory operation on the data already fetched.

## 6 Architecture Design

The feature relies on a read-only consumer model. The new CLI command simply reads the data it already produces and applies a sort-and-filter operation.

```mermaid
graph TB
    subgraph "ASIC Hardware"
        A[Physical Ports<br/>SAI_PORT_STAT_IF_IN_OCTETS<br/>SAI_PORT_STAT_IF_OUT_OCTETS<br/>SAI_PORT_STAT_IF_IN_UCAST_PKTS<br/>SAI_PORT_STAT_IF_OUT_UCAST_PKTS]
    end

    subgraph "syncd Container"
        B[syncd<br/>SAI API Counter Collection]
    end

    subgraph "COUNTERS_DB (Redis DB 2)"
        C["COUNTERS:&lt;oid&gt;<br/>Raw SAI counters (unchanged)"]
        D["RATES:&lt;oid&gt;<br/>RX_BPS, TX_BPS, RX_PPS, TX_PPS<br/>(computed by port_rates.lua, unchanged)"]
        G["COUNTERS_PORT_NAME_MAP<br/>Interface name → OID mapping (unchanged)"]
    end

    subgraph "SWSS Container: Flex Counter (unchanged)"
        H["port_rates.lua<br/>EWMA rate computation<br/>Runs every POLL_INTERVAL (default 1s)"]
    end

    subgraph "Host: sonic-utilities CLI"
        I["show interfaces counters top<br/>NEW Click subcommand"]
        J["scripts/portstat -X N --sort ...<br/>MODIFIED: new flags"]
        K["Portstat.get_top_n()<br/>NEW method: sort + rank + top N"]
    end

    A -->|"SAI stats query"| B
    B -->|"Write counters"| C
    C -->|"Read current + last counters"| H
    H -->|"Compute EWMA rates"| D
    G -->|"Name → OID lookup"| K
    D -->|"Read pre-computed rates"| K
    I -->|"Builds argv, invokes"| J
    J -->|"Instantiates Portstat, calls get_top_n()"| K
```

**Architecture summary:**
- The architecture diagram is **read-only from the CLI's perspective**. Everything to the left of the "Host: sonic-utilities CLI" box is existing infrastructure that remains completely unchanged.



## 7 High-Level Design

### 7.1 Modules Design

In `sonic-utilities/utilities_common/portstat.py`, two new methods are added to the `Portstat` class to handle the core logic:

**1. `get_top_n()`: Sort and rank interfaces**

```python
def get_top_n(self, ratestat_dict, n, sort_key='total', units='pps'):
    """
    Sort interfaces by the specified rate key and return the top N.

    Args:
        ratestat_dict: OrderedDict mapping port_name -> RateStats namedtuple
        n: Number of top interfaces to return
        sort_key: 'rx', 'tx', 'total', or 'util'
        units: 'bps' or 'pps'

    Returns:
        List of (port_name, RateStats) tuples, sorted descending by the
        specified key, with natsorted tie-breaking for deterministic output.
    """
    pass
```

**Key design decisions for `get_top_n()`:**

1. **`safe_float()` helper**: The `RATES:` table may contain `N/A` values when the rate plugin has not yet initialized or when a specific field is not supported by the platform. All `N/A` values are treated as `0.0` for sorting purposes.

2. **Utilization fallback**: When `RX_UTIL` / `TX_UTIL` are `N/A` (which is the common case since `port_rates.lua` does not set these fields), utilization is computed on-the-fly from `RX_BPS` and the port speed. This mirrors the existing behavior in `cnstat_diff_print()`.

3. **`natsort` tie-breaking**: When multiple interfaces have the same rate value (e.g., multiple idle interfaces at 0 bps), they are ordered by natural sort order of the interface name. This ensures `Ethernet2` appears before `Ethernet10`, and the output is deterministic across runs. The `natsort` library is already imported in `portstat.py`.

4. **No mutation**: The method does not modify `ratestat_dict`. It creates a new sorted list and returns a slice.


**2. `top_n_diff_print()`: Format and display the top N table**

```python
def top_n_diff_print(self, cnstat_new_dict, cnstat_old_dict, ratestat_dict,
                    top_n_count, sort_key, units, use_json):
    """
    Display the top N interfaces ranked by the specified rate key.

    Rates come from the RATES: table.

    Args:
        cnstat_new_dict: Current counter stats (unused, passed for signature compatibility)
        cnstat_old_dict: Previous counter stats (unused)
        ratestat_dict: Rate stats from RATES: table
        top_n_count: Number of top interfaces to display
        sort_key: 'rx', 'tx', 'total', or 'util'
        units: 'bps' or 'pps'
        use_json: Whether to output JSON
    """
    pass
```

**Key design decisions for `top_n_diff_print()`:**

1. **Reuse of existing formatters**: The method reuses `format_brate()`, `format_prate()`, and `format_util()` from `utilities_common/netstat.py`, which are the exact same functions used by the existing `portstat -R` display. This ensures visual consistency with `show interfaces counters rates`.

2. **UTIL column**: The `UTIL` column shows the maximum of RX and TX utilization for the interface. This represents the "bottleneck" direction. The JSON output provides both `rx_util_pct` and `tx_util_pct` separately for consumers that need directional utilization.

3. **JSON structure**: The JSON output includes metadata (`sampled_at`, `sort_key`) and a flat array of interface objects.

### 7.2 Flows

#### CLI Execution Flow

The following sequence diagram shows the internal call chain when an operator runs `show interfaces counters top -n 5 --sort total`:

```mermaid
sequenceDiagram
    participant User as Operator
    participant Click as Click CLI<br/>(show/interfaces/__init__.py)
    participant Script as scripts/portstat
    participant PS as Portstat class<br/>(utilities_common/portstat.py)
    participant CDB as COUNTERS_DB
    participant APPL as APPL_DB

    User->>Click: show interfaces counters top -n 5 --sort total
    Click->>Click: Build argv: portstat -X 5 --sort total --units pps
    Click->>Script: clicommon.run_command(cmd)
    
    Script->>Script: Parse args: top_n_count=5, sort_key=total, units=pps
    Script->>PS: Portstat()
    Script->>PS: get_cnstat_dict()
    
    Note over PS, CDB: Existing Portstat data collection
    PS->>CDB: HGETALL COUNTERS_PORT_NAME_MAP
    CDB-->>PS: Port name → OID mapping
    
    loop For each port
        PS->>CDB: HGET COUNTERS:<oid> (counter values)
        PS->>CDB: HGET RATES:<oid> RX_BPS, RX_PPS,<br/>TX_BPS, TX_PPS, RX_UTIL, TX_UTIL
    end
    
    PS-->>Script: (cnstat_dict, ratestat_dict)
    
    Script->>PS: top_n_diff_print(cnstat_dict, {}, ratestat_dict,<br/>top_n_count=5, sort_key=total, units=pps)
    
    Note over PS: Check RATES: availability
    PS->>PS: Verify at least one port has non-N/A rates
    
    PS->>PS: get_top_n(ratestat_dict, 5, 'total', 'pps')
    
    Note over PS: Sort by (rx_bps + tx_bps) descending,<br/>natsorted tie-breaking
    
    loop For each of top 5 interfaces
        PS->>APPL: Get port_speed and port_state
        PS->>PS: format_brate(), format_prate(), format_util()
    end
    
    PS->>PS: tabulate(table, header)
    PS-->>User: Formatted table output
```


## 8 SAI API

N/A

## 9 Configuration and management

### 9.1 CLI Commands

#### show interfaces counters top

#### Basic usage: show top 5 interfaces (default)

```bash
admin@sonic:~$ show interfaces counters top
Sampled at 2026-06-25 10:14:03

  RANK  IFACE          STATE      RX_BPS       RX_PPS      TX_BPS       TX_PPS    TOTAL_BPS     TOTAL_PPS     UTIL
------  -----------  -------  ----------  -----------  ----------  -----------  -----------  ------------  -------
     1  Ethernet120        U  852.13 MB/s  1047000.00/s  783.22 MB/s  962500.00/s  1635.35 MB/s  2009500.00/s  85.21%
     2  Ethernet112        U  621.09 MB/s   763000.00/s  598.04 MB/s  735000.00/s  1219.13 MB/s  1498000.00/s  62.11%
     3  Ethernet64         U  482.01 MB/s   593000.00/s  521.57 MB/s  641000.00/s  1003.58 MB/s  1234000.00/s  52.16%
     4  Ethernet0          U  321.55 MB/s   395000.00/s  301.23 MB/s  370000.00/s   622.78 MB/s   765000.00/s  32.15%
     5  Ethernet48         U  211.06 MB/s   259000.00/s  198.92 MB/s  244500.00/s   409.98 MB/s   503500.00/s  21.11%
```

#### Custom count

```bash
admin@sonic:~$ show interfaces counters top -n 3
Sampled at 2026-06-25 10:14:05

  RANK  IFACE          STATE      RX_BPS       RX_PPS      TX_BPS       TX_PPS    TOTAL_BPS     TOTAL_PPS     UTIL
------  -----------  -------  ----------  -----------  ----------  -----------  -----------  ------------  -------
     1  Ethernet120        U  852.13 MB/s  1047000.00/s  783.22 MB/s  962500.00/s  1635.35 MB/s  2009500.00/s  85.21%
     2  Ethernet112        U  621.09 MB/s   763000.00/s  598.04 MB/s  735000.00/s  1219.13 MB/s  1498000.00/s  62.11%
     3  Ethernet64         U  482.01 MB/s   593000.00/s  521.57 MB/s  641000.00/s  1003.58 MB/s  1234000.00/s  52.16%
```

#### Sort by RX traffic

```bash
admin@sonic:~$ show interfaces counters top -n 5 --sort rx
Sampled at 2026-06-25 10:14:10

  RANK  IFACE          STATE      RX_BPS       RX_PPS      TX_BPS       TX_PPS    TOTAL_BPS     TOTAL_PPS     UTIL
------  -----------  -------  ----------  -----------  ----------  -----------  -----------  ------------  -------
     1  Ethernet120        U  852.13 MB/s  1047000.00/s  783.22 MB/s  962500.00/s  1635.35 MB/s  2009500.00/s  85.21%
     2  Ethernet112        U  621.09 MB/s   763000.00/s  598.04 MB/s  735000.00/s  1219.13 MB/s  1498000.00/s  62.11%
     3  Ethernet64         U  482.01 MB/s   593000.00/s  521.57 MB/s  641000.00/s  1003.58 MB/s  1234000.00/s  52.16%
     4  Ethernet0          U  321.55 MB/s   395000.00/s  301.23 MB/s  370000.00/s   622.78 MB/s   765000.00/s  32.15%
     5  Ethernet48         U  211.06 MB/s   259000.00/s  198.92 MB/s  244500.00/s   409.98 MB/s   503500.00/s  21.11%
```

#### Sort by utilization

```bash
admin@sonic:~$ show interfaces counters top -n 5 --sort util
Sampled at 2026-06-25 10:14:15

  RANK  IFACE          STATE      RX_BPS       RX_PPS      TX_BPS       TX_PPS    TOTAL_BPS     TOTAL_PPS     UTIL
------  -----------  -------  ----------  -----------  ----------  -----------  -----------  ------------  -------
     1  Ethernet120        U  852.13 MB/s  1047000.00/s  783.22 MB/s  962500.00/s  1635.35 MB/s  2009500.00/s  85.21%
     2  Ethernet112        U  621.09 MB/s   763000.00/s  598.04 MB/s  735000.00/s  1219.13 MB/s  1498000.00/s  62.11%
     3  Ethernet64         U  482.01 MB/s   593000.00/s  521.57 MB/s  641000.00/s  1003.58 MB/s  1234000.00/s  52.16%
     4  Ethernet0          U  321.55 MB/s   395000.00/s  301.23 MB/s  370000.00/s   622.78 MB/s   765000.00/s  32.15%
     5  Ethernet48         U  211.06 MB/s   259000.00/s  198.92 MB/s  244500.00/s   409.98 MB/s   503500.00/s  21.11%
```

#### Rank by packets per second

```bash
admin@sonic:~$ show interfaces counters top -n 3 --units pps
Sampled at 2026-06-25 10:14:20

  RANK  IFACE          STATE      RX_BPS       RX_PPS      TX_BPS       TX_PPS    TOTAL_BPS     TOTAL_PPS     UTIL
------  -----------  -------  ----------  -----------  ----------  -----------  -----------  ------------  -------
     1  Ethernet120        U  852.13 MB/s  1047000.00/s  783.22 MB/s  962500.00/s  1635.35 MB/s  2009500.00/s  85.21%
     2  Ethernet8          U   13.37 MB/s   900000.00/s    1.35 MB/s  800000.00/s    14.72 MB/s  1700000.00/s    N/A
     3  Ethernet112        U  621.09 MB/s   763000.00/s  598.04 MB/s  735000.00/s  1219.13 MB/s  1498000.00/s  62.11%
```


#### JSON output

```bash
admin@sonic:~$ show interfaces counters top -n 3 --json --units bps
{
    "sampled_at": "2026-06-25T10:14:25.118000",
    "sort_key": "total_bps",
    "count": 3,
    "interfaces": [
        {
            "rank": 1,
            "iface": "Ethernet120",
            "state": "U",
            "rx_bps": 852130000.0,
            "rx_pps": 1047000.0,
            "tx_bps": 783220000.0,
            "tx_pps": 962500.0,
            "total_bps": 1635350000.0,
            "total_pps": 2009500.0,
            "rx_util_pct": 68.17,
            "tx_util_pct": 62.66
        },
        {
            "rank": 2,
            "iface": "Ethernet112",
            "state": "U",
            "rx_bps": 621090000.0,
            "rx_pps": 763000.0,
            "tx_bps": 598040000.0,
            "tx_pps": 735000.0,
            "total_bps": 1219130000.0,
            "total_pps": 1498000.0,
            "rx_util_pct": 49.69,
            "tx_util_pct": 47.84
        },
        {
            "rank": 3,
            "iface": "Ethernet64",
            "state": "U",
            "rx_bps": 482010000.0,
            "rx_pps": 593000.0,
            "tx_bps": 521570000.0,
            "tx_pps": 641000.0,
            "total_bps": 1003580000.0,
            "total_pps": 1234000.0,
            "rx_util_pct": 38.56,
            "tx_util_pct": 41.73
        }
    ]
}
```



#### All interfaces have zero traffic

```bash
admin@sonic:~$ show interfaces counters top -n 3
Sampled at 2026-06-25 10:14:40

  RANK  IFACE          STATE      RX_BPS     RX_PPS      TX_BPS     TX_PPS    TOTAL_BPS      TOTAL_PPS     UTIL
------  -----------  -------  ----------  ---------  ----------  ---------  -----------  -------------  -------
     1  Ethernet0          U    0.00 B/s     0.00/s    0.00 B/s     0.00/s     0.00 B/s         0.00/s   0.00%
     2  Ethernet4          U    0.00 B/s     0.00/s    0.00 B/s     0.00/s     0.00 B/s         0.00/s   0.00%
     3  Ethernet8          U    0.00 B/s     0.00/s    0.00 B/s     0.00/s     0.00 B/s         0.00/s   0.00%
```

Note: Interfaces with identical (zero) rates are tie-broken by natural sort order of the interface name.

### 9.2 Config DB Enhancements

N/A

## 10 Warmboot and Fastboot Design Impact

N/A

## 11 Things to be Considered

1. **`RATES:` population varies by platform:** Some vendor SDKs disable specific stats. When a counter is unavailable, the corresponding `RATES:<oid>` field will be `N/A`. The `safe_float()` helper safely treats these as `0.0` for sorting, ensuring the CLI gracefully handles incomplete data.
2. **VOQ chassis path:** On supervisor cards, `Portstat.collect_stat_from_lc()` reads from `CHASSIS_STATE_DB` using a different schema. The rate fields (`rx_bps`, `tx_bps`, etc.) are present there too, and populate the same dictionary that the `top` filter operates on. (Needs one VOQ-fixture test to confirm).
3. **EWMA α value limitation:** The smoothing factor is configured per-deployment in `RATES:PORT`. A short microburst won't show up in these stats since it gets diluted by the EWMA smoothing. Users investigating microbursts should be directed to the watermark counters (`show queue watermark`) instead.

## 12 Testing Requirements/Design

#### Unit Test cases 

The unit tests will be provided during implementation.

## 13 Stretch Goals

The following features are not part of the initial implementation but could be added as follow-up PRs:

#### 13.1 `--threshold` Flag

A `--threshold X` flag would show only interfaces exceeding X bytes/sec (or packets/sec). This is useful for alerting scripts that want to identify congested interfaces above a specific watermark.

**Example:**
```bash
show interfaces counters top --threshold 1000000000
# Only shows interfaces with total rate > 1 GB/s
```

#### 13.2 `--reverse` Flag

A `--reverse` flag would sort ascending instead of descending, showing the **least** busy interfaces. This is useful for capacity planning and identifying underutilized interfaces.
