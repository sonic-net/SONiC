<!-- omit in toc -->
# SONiC Remote Syslog Facility and Severity Selector

## High Level Design document

## Table of contents

- [Revision](#revision)
- [About this manual](#about-this-manual)
- [Scope](#scope)
- [Definitions and abbreviations](#definitions-and-abbreviations)
- [1. Introduction](#1-introduction)
  - [1.1. Feature overview](#11-feature-overview)
  - [1.2. Problem statement](#12-problem-statement)
  - [1.3. Requirements](#13-requirements)
    - [1.3.1. Functional requirements](#131-functional-requirements)
    - [1.3.2. Command interface](#132-command-interface)
    - [1.3.3. Non-functional requirements](#133-non-functional-requirements)
- [2. Design](#2-design)
  - [2.1. Architecture overview](#21-architecture-overview)
  - [2.2. Syslog facilities on SONiC](#22-syslog-facilities-on-sonic)
  - [2.3. Rsyslog selector semantics](#23-rsyslog-selector-semantics)
  - [2.4. Configuration data model](#24-configuration-data-model)
    - [2.4.1. Config DB schema](#241-config-db-schema)
    - [2.4.2. Default and precedence rules](#242-default-and-precedence-rules)
    - [2.4.3. Backward compatibility](#243-backward-compatibility)
  - [2.5. sonic-buildimage changes](#25-sonic-buildimage-changes)
    - [2.5.1. rsyslog.conf.j2](#251-rsyslogconfj2)
    - [2.5.2. YANG model](#252-yang-model)
    - [2.5.3. Configuration pipeline](#253-configuration-pipeline)
  - [2.6. sonic-utilities changes](#26-sonic-utilities-changes)
    - [2.6.1. Shared validation (`syslog_util`)](#261-shared-validation-syslog_util)
    - [2.6.2. CLI](#262-cli)
  - [2.7. Control flows](#27-control-flows)
    - [2.7.1. Add server with selector](#271-add-server-with-selector)
    - [2.7.2. Update selector on existing server](#272-update-selector-on-existing-server)
  - [2.8. Multi-destination example](#28-multi-destination-example)
  - [2.9. Warm / fast boot](#29-warm--fast-boot)
- [3. Error handling](#3-error-handling)
- [4. Event logging](#4-event-logging)
- [5. Test plan](#5-test-plan)
  - [5.1. sonic-utilities unit tests](#51-sonic-utilities-unit-tests)
  - [5.2. sonic-buildimage](#52-sonic-buildimage)
  - [5.3. System / VS tests](#53-system--vs-tests)

## Revision

| Rev | Date       | Author              | Description |
|:---:|:----------:|:-------------------:|:------------|
| 0.1 | 23/11/2025 | (draft)             | Initial HLD for per-server syslog facility and severity selector |

## About this manual

This document describes the high-level design for configuring **per remote syslog server** which syslog messages are forwarded, using standard **facility** and **severity** selectors. The design spans the **sonic-buildimage** and **sonic-utilities** repositories.

This document is an extension of [syslog-design.md](syslog-design.md). Terminology, SSIP parameters, global severity, filters, `omfwd` mapping, DB schema conventions, and the configuration agent flow are defined there and are not duplicated here except where this feature adds or changes behavior.

## Scope

**In scope**

- Per-server `facility` and `severity` fields in `SYSLOG_SERVER` (Config DB).
- Rendering of rsyslog priority selectors (`facility.severity`) in host `rsyslog.conf.j2`.
- CLI to configure selectors at server add time and via a dedicated `config syslog selector` command group.
- `show syslog` display of facility and severity per server.
- YANG extension for `facility` on `SYSLOG_SERVER_LIST`.

**Out of scope**

- Changing syslog facility used by individual SONiC daemons or containers.
- Regex include/exclude filters (`filter` / `filter_regex`) — unchanged; may be combined with facility/severity selectors on the same server entry.
- TCP/TLS syslog transport extensions beyond what SSIP already defines.
- Per-ASIC remote syslog selector differences (host `rsyslog-config` only; same as existing remote syslog).

## Definitions and abbreviations

| Term | Meaning |
|:-----|:--------|
| Facility | Syslog facility class (e.g. `daemon`, `local4`, `kern`). In rsyslog rules, `*` means all facilities. |
| Severity / priority | Syslog severity (debug … crit). Rsyslog selectors use “this level and higher” semantics for a given facility. |
| Selector | Rsyslog rule prefix of the form `facility.severity` that gates the following `omfwd` action. |
| SSIP | Syslog Source IP and extended remote server options (source, VRF, protocol, filter, severity). |
| Config DB | Redis `CONFIG_DB` (database 4). |
| `rsyslog-config` | Host systemd unit that renders `/etc/rsyslog.conf` from Config DB and restarts `rsyslog`. |

> **Note:** “Facility” is a standard syslog/RFC 5424 concept. It is unrelated to the SONiC `FEATURE` table (`bgp`, `swss`, etc.), except that many container daemons log under `daemon` while FRR logs under `local4`.

## 1. Introduction

### 1.1. Feature overview

Operators often run multiple syslog collectors: one for security/audit, one for routing (BGP), and one for general platform logs. SONiC already supports:

- Multiple `SYSLOG_SERVER` destinations.
- Per-server minimum **severity** (and global default severity).
- Optional message **filter** regex.

This enhancement adds an explicit per-server **facility** selector and clarifies **severity** as a pair forming a standard rsyslog priority rule before each `omfwd` forward action. That allows forwarding, for example, only `local4.notice` (FRR) to collector A while collector B still receives `*.*` (all messages), without regex filters.

### 1.2. Problem statement

Before this change:

- Per-server `severity` was supported in YANG/Config DB, but **facility** was fixed to `*` in the generated rsyslog configuration.
- Operators could not easily split routing logs from other daemon logs when both share similar message text.
- Severity-only filtering could not express “BGP/FRR facility only” semantics.

### 1.3. Requirements

#### 1.3.1. Functional requirements

1. Store optional `facility` and `severity` per `SYSLOG_SERVER` key.
2. Render valid rsyslog selector lines for each server: `{facility}.{severity} action(omfwd …)`.
3. When only one of facility or severity is configured, apply documented defaults for the missing half.
4. Preserve existing servers with no selector fields (behavior equivalent to prior `*.{global-or-notice}` rendering).
5. Restart `rsyslog-config` after CLI changes (same as other syslog server mutations).

#### 1.3.2. Command interface

| Command | Purpose |
|:--------|:--------|
| `config syslog add <server> [--facility …] [--severity …] …` | Create server; optional selector at create time |
| `config syslog selector set <server> [--facility …] [--severity …]` | Update one or both selector fields on existing server |
| `config syslog selector del <server>` | Remove both `facility` and `severity` from server entry |
| `show syslog` | Tabular view includes FACILITY and SEVERITY columns |

At least one of `--facility` or `--severity` is required for `selector set`.

#### 1.3.3. Non-functional requirements

- Backward compatible Config DB and config reload.
- Input validation in CLI (allowed facility and severity enumerations).
- No new host daemon; reuse `rsyslog-config.service`.
- Consistent with `sonic-syslog.yang` severity enumeration used elsewhere in SONiC.

## 2. Design

### 2.1. Architecture overview

```
+-------------+     config/show syslog      +------------------+
|  Operator   | --------------------------> | sonic-utilities  |
+-------------+                             | (config/syslog,  |
                                            |  show/syslog,    |
                                            |  syslog_util)    |
                                            +--------+---------+
                                                     |
                                                     | CONFIG_DB
                                                     v
                                            +------------------+
                                            | SYSLOG_SERVER    |
                                            |  facility        |
                                            |  severity        |
                                            +--------+---------+
                                                     |
                              CONFIG_DB poll / boot  |
                                                     v
                                            +------------------+
                                            | rsyslog-config   |
                                            | sonic-cfggen +   |
                                            | rsyslog.conf.j2  |
                                            +--------+---------+
                                                     |
                                                     v
                                            +------------------+
                                            | rsyslogd (host)  |
                                            | omfwd -> remote  |
                                            +------------------+
```

CLI writes Config DB only. The host renders and applies rsyslog configuration; container logs still flow to the host rsyslog as today.

### 2.2. Syslog facilities on SONiC

Typical assignments (informational for operators designing selectors):

| Traffic | Typical facility | Notes |
|:--------|:-----------------|:------|
| Most Python/C++ SONiC daemons (`Logger` default) | `user` or `daemon` | `sonic_py_common.Logger` often uses `LOG_USER` / daemon facility via `/dev/log`. |
| FRR (`bgpd`, `zebra`, …) | `local4` | FRR configs use `log facility local4`. |
| Kernel | `kern` | Kernel messages via `imklog`. |

Valid CLI facility values (normalized to lowercase in Config DB):

`*` (alias `all`), `kern`, `user`, `mail`, `daemon`, `auth`, `syslog`, `local0` … `local7`

Aliases accepted at CLI: `all` → `*`, `kernel` → `kern`, `system_daemon` → `daemon`.

### 2.3. Rsyslog selector semantics

For each `SYSLOG_SERVER` entry, the template emits:

```text
{facility}.{severity}
action(type="omfwd" Target="…" …)
```

- **Facility** `*` — all facilities.
- **Severity** — minimum level forwarded for matching facility; rsyslog uses “this priority and higher” (more severe) for traditional selectors.

Existing optional regex filter lines (if configured) remain **above** the selector line, unchanged from SSIP.

Severity strings in Config DB match `rsyslog-severity` in YANG: `none`, `debug`, `info`, `notice`, `warn`, `error`, `crit`.

### 2.4. Configuration data model

#### 2.4.1. Config DB schema

Table: `SYSLOG_SERVER|<server_ip_or_name>`

| Field | Type | Description |
|:------|:-----|:------------|
| `facility` | string | Optional. Syslog facility selector; `*` if omitted at render time. |
| `severity` | string | Optional. Minimum severity; see precedence below. |
| … | … | Existing SSIP fields: `source`, `port`, `vrf`, `protocol`, `filter`, `filter_regex`, etc. |

Table: `SYSLOG_CONFIG|GLOBAL`

| Field | Relevance |
|:------|:----------|
| `severity` | Default minimum severity for servers that do not set `severity` when rendered. |

**Example**

```json
{
    "SYSLOG_SERVER": {
        "10.1.1.1": {
            "port": "514",
            "vrf": "default",
            "facility": "local4",
            "severity": "notice"
        },
        "10.1.1.2": {
            "port": "514",
            "vrf": "default"
        }
    },
    "SYSLOG_CONFIG": {
        "GLOBAL": {
            "severity": "info"
        }
    }
}
```

#### 2.4.2. Default and precedence rules

At **render** time (`rsyslog.conf.j2`):

| Configured | Rendered facility | Rendered severity |
|:-----------|:------------------|:------------------|
| neither | `*` | `SYSLOG_CONFIG.GLOBAL.severity`, or `*` if global unset |
| facility only | configured value | global severity or `*` |
| severity only | `*` | configured value |
| both | configured | configured |

At **CLI** validation:

- Invalid facility or severity strings are rejected before Config DB write.
- `selector set` requires at least one of `--facility` or `--severity`.

#### 2.4.3. Backward compatibility

- Servers without `facility` / `severity` keys behave as before: facility `*`, severity from global default chain.
- No migration script required.
- `config syslog selector del` removes only selector fields; other server attributes remain.

### 2.5. sonic-buildimage changes

#### 2.5.1. rsyslog.conf.j2

For each server in `SYSLOG_SERVER`:

1. Read `facility` (default `*`).
2. Read `severity` with fallback: per-server → `SYSLOG_CONFIG.GLOBAL.severity` → `*`.
3. Emit `{facility}.{severity}` immediately before the existing `omfwd` action line.

Sanitization of injected values (strip newlines, quotes, `%`, etc.) matches other SSIP template fields.

#### 2.5.2. YANG model

File: `src/sonic-yang-models/yang-models/sonic-syslog.yang`

- Add `leaf facility` under `SYSLOG_SERVER_LIST` (string type; CLI enforces enumeration; YANG may be extended later with an enumeration typedef).
- Existing `leaf severity` on the server list continues to represent per-server minimum severity.

Management framework / OpenConfig translators should accept the new leaf where `SYSLOG_SERVER` is mapped.

#### 2.5.3. Configuration pipeline

Unchanged from SSIP:

1. `rsyslog-config.service` invokes `sonic-cfggen` with Config DB JSON.
2. Validates rendered config, installs `/etc/rsyslog.conf`, restarts `rsyslog`.

sonic-utilities triggers `systemctl restart rsyslog-config` after successful Config DB updates.

### 2.6. sonic-utilities changes

#### 2.6.1. Shared validation (`syslog_util`)

Module: `syslog_util/common.py`

- `SYSLOG_FIELD_FACILITY`, `SYSLOG_FIELD_SEVERITY` — Config DB field names.
- `normalize_syslog_facility()` — validation and alias normalization.
- `normalize_syslog_severity()` — validation, aliases (`warning` → `warn`, etc.).

Used by both `config/syslog.py` and `show/syslog.py` for consistent behavior.

#### 2.6.2. CLI

**config**

```bash
# Add collector for FRR logs only
sudo config syslog add 10.1.1.1 --facility local4 --severity notice

# Later, broaden severity
sudo config syslog selector set 10.1.1.1 --severity info

# Revert to default selector (use global severity, all facilities)
sudo config syslog selector del 10.1.1.1
```

**show**

```bash
admin@sonic:~$ show syslog
SERVER IP    SOURCE IP    PORT    VRF       FACILITY    SEVERITY
-----------  -----------  ------  --------  ----------  --------
10.1.1.1     N/A          514     default   local4      notice
10.1.1.2     N/A          514     default   N/A         N/A
```

`N/A` in show output means the field is unset in Config DB (defaults apply at render time).

### 2.7. Control flows

#### 2.7.1. Add server with selector

1. Operator runs `config syslog add` with optional `--facility` / `--severity`.
2. CLI validates IP, VRF, source, facility, severity.
3. CLI writes `SYSLOG_SERVER|<ip>` hash.
4. CLI restarts `rsyslog-config`.
5. `rsyslog-config` regenerates config; `rsyslogd` loads new rules.
6. Matching messages forward to remote target per selector.

#### 2.7.2. Update selector on existing server

1. Operator runs `config syslog selector set` (server must exist).
2. CLI `mod_entry` updates only provided fields.
3. `rsyslog-config` restart; other server fields unchanged.

### 2.8. Multi-destination example

Operator goal:

- `10.0.0.1` — all logs at `info` and above.
- `10.0.0.2` — FRR (`local4`) at `notice` and above.

Config DB (conceptual):

```json
"SYSLOG_SERVER": {
    "10.0.0.1": { "severity": "info" },
    "10.0.0.2": { "facility": "local4", "severity": "notice" }
}
```

Generated rsyslog fragment:

```text
*.info
action(type="omfwd" Target="10.0.0.1" …)

local4.notice
action(type="omfwd" Target="10.0.0.2" …)
```

### 2.9. Warm / fast boot

Config is persistent in Config DB. After reboot, `rsyslog-config` renders the same selectors. No warm-boot-specific state.

## 3. Error handling

| Condition | Behavior |
|:----------|:---------|
| Invalid facility or severity | CLI error; no Config DB change |
| `selector set` with neither facility nor severity | Usage error |
| `selector del` when no selector configured | ClickException |
| Server does not exist for selector commands | Usage error (invalid server) |
| `rsyslog-config` restart failure | CLI reports failure; operator checks `journalctl -u rsyslog-config` |

## 4. Event logging

| Event | Severity |
|:------|:---------|
| Server add / delete success | NOTICE |
| Selector set / del success | NOTICE |
| Config DB or restart failure | ERROR |

Messages use existing sonic-utilities syslog logger identifiers.

## 5. Test plan

### 5.1. sonic-utilities unit tests

File: `tests/syslog_test.py`

- Add server with `--facility local4 --severity notice` → Config DB fields set.
- `selector set` updates facility/severity; partial update retains other field.
- `selector del` removes facility and severity.
- `selector set` without facility or severity fails with required-field message.

### 5.2. sonic-buildimage

- YANG model tests: optional positive/negative cases for `facility` on `SYSLOG_SERVER` (when added to `tests/yang_model_tests`).
- `sonic-config-engine` / template tests: verify rendered `local4.notice` / `*.info` lines for sample JSON inputs.

### 5.3. System / VS tests

1. Configure two remote servers with different facility/severity on VS image.
2. Inspect `/etc/rsyslog.conf` for correct selector lines.
3. Generate FRR log (local4) and generic daemon log; verify forwarding split with packet capture or mock collector.
4. Reload `config reload` / reboot — selectors persist.
5. Regression: server without selector fields matches pre-change rsyslog output.