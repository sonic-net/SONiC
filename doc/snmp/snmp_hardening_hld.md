# HLD: SNMP Agent Hardening – Critical Fixes

---

## 1. Problem Statement

The SONiC SNMP sub‑agent (`sonic_ax_impl`) is invoked by `snmp-subagent` inside the `snmp` docker. It periodically walks STATE_DB / COUNTERS_DB / CONFIG_DB rows to serve SNMP GETs / walks over the AgentX socket.

The agent crashes on a number of common and edge‑case data conditions that occur routinely during:

- **Early boot / cold start** — STATE_DB tables (`CHASSIS_INFO`, `PSU_INFO`, `FAN_DRAWER_INFO`, `PHYSICAL_ENTITY_INFO`, `TRANSCEIVER_INFO`) are populated asynchronously by `pmond` / `psud` / `syncd` / `xcvrd`. Any snmpwalk that races the daemons sees partial rows.
- **Transient swss/syncd restarts** — COUNTERS_DB rows briefly disappear.
- **Populating LAGs (PortChannels)** — a member interface can be enumerated in `LAG_TABLE` before its per‑port SAI counters row exists → `_get_counter()` returns `None`.
- **Malformed data** — a fan drawer key with no digit suffix, a `psu_num` value of `''`, a `position_in_parent` of `'N/A'`, a broken `/etc/resolv.conf`.

The observed failure modes fall into five classes, all of which surface as `[ax_interface] ERROR: MIBUpdater.start() caught an unexpected exception during update_data()` tracebacks:

| Class | Symptom | Example |
|---|---|---|
| Counter `None` in LAG sum | `TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'` | `InterfacesUpdater.get_counter`, `InterfaceMIBUpdater._get_counter`, `PfcPrioUpdater.requests_per_priority` |
| Missing dict key | `KeyError: 'type'`, `KeyError: '1:0'` | `XcvrCacheUpdater._update_entity_cache`, `QueueStatUpdater.update_data` (`del`) |
| Attribute never initialized before first use | `AttributeError: 'InterfaceMIBUpdater' object has no attribute 'lag_sai_map'` | `InterfaceMIBUpdater` |
| Misspelled method name | `AttributeError: 'PhysicalTableMIBUpdater' object has no attribute 'add_pending_entity_name_callback'` | `PhysicalTableMIBUpdater` |
| `int()` of empty / non‑numeric string | `ValueError: invalid literal for int() with base 10: ''` | `PhysicalSensorTableMIBUpdater.update_{psu,fan,thermal}_sensor_data`, `PowerStatusHandler._get_num_psus`, `FanStatusHandler.init_fan_trays` |

Because `MIBUpdater.start()` uses a single try/except at the top of the update loop, **any** unhandled exception halts the *entire* updater — SNMP polling stops for **all** ports / FRUs / sensors served by that updater, not just the affected one. Recovery requires a `supervisorctl restart snmp-subagent` and clean STATE_DB data.

Two concrete tracebacks that motivated this work (both filed by field reports):

```
[sonic_ax_impl] ERROR: PowerStatusHandler._get_psu_index() caught an unexpected
exception during _get_num_psus()
Traceback (most recent call last):
  File ".../ciscoEntityFruControlMIB.py", line 108, in _get_psu_index
    num_psus = self._get_num_psus()
  File ".../ciscoEntityFruControlMIB.py", line 68, in _get_num_psus
    raise ValueError("psu_num field empty")
ValueError: psu_num field empty
```

```
[ax_interface] ERROR: MIBUpdater.start() caught an unexpected exception during
update_data()
Traceback (most recent call last):
  File ".../rfc3433.py", line 640, in update_data
    self.update_thermal_sensor_data()
  File ".../rfc3433.py", line 596, in update_thermal_sensor_data
    thermal_position = int(thermal_position)
ValueError: invalid literal for int() with base 10: ''
```

We need **surgical defensive fixes** that preserve behavior on clean data and prevent crashes on missing or unexpected data.

---

## 2. Goals

- **G1.** Eliminate all crash paths in the SNMP agent that are triggered by missing / empty / unexpected DB data.
- **G2.** Never regress correctness on well‑formed data — happy‑path SNMP walk output must be byte‑identical.

## 2.1 Non‑Goals

- No wire‑format / OID / MIB schema changes.
- No changes to the AgentX transport, MIB registration, or PDU handling in `ax_interface`.
- No new dependencies. No new configuration knobs.
- No changes to `snmpd` (Net‑SNMP)
---

## 3. Design Approach

All fixes follow a small, consistent set of defensive patterns. This keeps the diff surface small and reviewers can validate each site against the pattern.

### 3.1 Defensive patterns

**P1 — Guard `int()` conversions of DB string fields.**

```python
if is_null_empty_str(pos):        # existing helper: '', 'N/A', 'None', non-str
    continue
try:
    pos = int(pos)
except (ValueError, TypeError):
    mibs.logger.warning("Invalid <field> for {}: '{}'".format(name, pos))
    continue
```

**P2 — Guard `dict['x']` accesses when the row can be partial.**

```python
if transceiver_info.get('type', '') == RJ45_PORT_TYPE:  # was: transceiver_info['type']
    return
```

**P3 — Guard `dict.get_all()` returning `None` (empty STATE_DB row).**

```python
info = statedb.get_all(...)
if not info:
    return False   # or 0, or skip iteration
```

**P4 — Treat `None` as `0` when summing counters over LAG members.**

```python
val = self._get_counter(mibs.get_index_from_str(member), counter_name)
counter_value += val if val is not None else 0
```

**P5 — Never mutate a list while iterating it; collect survivors into a fresh list.**

```python
valid = []
for entry in sorted(entries):
    if _bad(entry):
        continue
    valid.append(entry)
entries = valid
```

**P6 — `dict.pop(key, None)` instead of `del dict[key]` for the "row disappeared" case.**

**P7 — Initialize every attribute referenced by any method in `__init__`, before any `reinit_data()` / `update_data()` runs.**

**P8 — Narrow `except Exception` to the specific exception classes the code can actually raise, and include the exception in the log message.**

```python
except (OSError, IndexError) as e:
    mibs.logger.warning("Cannot read domain from /etc/resolv.conf using {}: {}"
                        .format(self.hostname, e))
```

**P9 — Prefer `dict.get()` with a sensible default over `dict[key]` for optional STATE_DB fields.**

### 3.2 Log‑level policy

| Condition | Level | Rationale |
|---|---|---|
| STATE_DB row not yet populated (expected transient) | `DEBUG` | Not actionable; would spam syslog on every early‑boot walk |
| STATE_DB row present but a field is empty (`''`, `'N/A'`) | `DEBUG` for known‑empty PSU/fan positions; `WARNING` for `chassis_info.psu_num == ''` because that's a data‑model violation | Distinguish "not populated yet" from "wrong" |
| STATE_DB field present but non‑numeric where numeric expected | `WARNING` | Data‑model violation; should be alerted on |
| Malformed `/etc/resolv.conf` | `WARNING` (once per get_sys_name call) | Not fatal — falls back to bare hostname |
| Unhandled exception in MIBUpdater | `ERROR` | Kept as‑is |

---

## 4. Observability & Logging

All new log lines use the existing `sonic_ax_impl.mibs.logger`. There are no new logger names, no new syslog categories, no new file targets.

Message conventions (grep‑friendly for on‑device debugging):

- `"No chassis info in STATE_DB; treating as 0 PSUs"` — early boot / missing chassis
- `"psu_num field empty in CHASSIS_INFO; treating as 0 PSUs"` — pmond hasn't populated
- `"Invalid psu_num value '{}' in CHASSIS_INFO; treating as 0 PSUs"` — data violation
- `"Invalid psu_position for {}: '{}'"`, `"Invalid fan_position for {}: '{}'"`, `"Empty fan_parent_position for {}"`, `"Invalid fan_parent_position for {}: '{}'"`, `"Invalid thermal position for {}: '{}'"` — rfc3433 guards
- `"Cannot read domain from /etc/resolv.conf Using {} in sysName: {}"` — sysName fallback

No new counters, no new metrics. If we later want SNMP‑agent healthchecks to alert on these, the standard mechanism is to grep `snmp-subagent` from syslog for `WARNING` at level `WARNING` — no work needed here.

---

## 5. Backward Compatibility

| Dimension | Impact |
|---|---|
| SNMP wire format | None. All MIBs still register the same OIDs with the same types. |
| SNMP walk output on **well‑formed** data | Byte‑identical (verified by full‑walk diff on a healthy DUT). |
| SNMP walk output on **partial** data | Improved: previously the walk stopped at the first crash. Now the walk completes with the affected sub‑ids skipped or reported as `0` / `notPresent`. |
| Log volume on a healthy DUT | Unchanged (all new guards trigger only on abnormal data). |
| Log volume on a broken DUT | Increased: previously one ERROR traceback, now one WARNING per malformed row per update cycle. This is intentional. |
| Public Python API of `sonic_ax_impl` | One rename: `_add_pending_entity_name_callback` → `add_pending_entity_name_callback`. Not called anywhere else in the SONiC codebase; verified by `rg` across all submodules. |
| Redis / STATE_DB schema | No changes required. |

