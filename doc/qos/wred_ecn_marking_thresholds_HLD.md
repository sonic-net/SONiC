# WRED Profile Independent ECN Marking Thresholds

## Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
  - [CONFIG_DB: WRED_PROFILE additions](#config_db-wred_profile-additions)
  - [Orchagent (QosOrch)](#orchagent-qosorch)
  - [ECT enablement and backward compatibility](#ect-enablement-and-backward-compatibility)
  - [Capability handling](#capability-handling)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
  - [CONFIG_DB Enhancements](#config_db-enhancements)
  - [CLI/YANG model Enhancements](#cliyang-model-enhancements)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Warmboot and Fastboot Performance Impact](#warmboot-and-fastboot-performance-impact)
- [Memory Consumption](#memory-consumption)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
- [Open/Action items](#openaction-items)

## Revision

| Rev | Date       | Author               | Change Description |
|-----|------------|----------------------|--------------------|
| 0.1 | 2026-07-01 | Anant Kishor Sharma (HPE) | Initial version |

## Scope

This document describes the high-level design for adding **independent ECN marking
thresholds** to the SONiC `WRED_PROFILE` object. It covers the CONFIG_DB schema
additions, the `orchagent` (QosOrch) changes that program the corresponding SAI WRED
attributes, the YANG model additions, and the backward-compatibility and capability
handling. It does not change the WRED drop behavior or introduce any new SAI header.

## Definitions/Abbreviations

| Term | Definition |
|------|------------|
| WRED | Weighted Random Early Detection |
| ECN  | Explicit Congestion Notification |
| ECT  | ECN-Capable Transport |
| AQM  | Active Queue Management |

## Overview

Today a SONiC `WRED_PROFILE` exposes a single set of per-color queue-depth thresholds
(`{green,yellow,red}_{min,max}_threshold`) that drive **both** random early drop and
ECN marking. When ECN is enabled for a color (via the `ecn` field), packets of that
color are ECN-marked instead of dropped, but the marking uses the **same** thresholds
as the drop curve. There is no way to mark ECN at a queue depth different from where
drop begins.

Standard AQM practice is to **mark before drop**: start ECN-marking at a lower queue
depth than where WRED drop begins, so that congestion is signaled (ECN) well before
packets are lost (drop). This feature adds an **independent** set of per-color ECN
marking thresholds and a per-color mark probability to `WRED_PROFILE`, decoupled from
the WRED drop thresholds, and programs them through the existing SAI WRED ECN
attributes.

## Requirements

1. Add per-color (green/yellow/red) **independent ECN marking** min/max thresholds and
   a mark probability to `WRED_PROFILE`, distinct from the WRED drop thresholds.
2. Program the new values via the existing SAI WRED ECN attributes; **no SAI header
   (API) change** is required.
3. **Backward compatible:** when the new fields are not configured, ECN behavior is
   unchanged. This is the SAI-defined fallback — per the SAI WRED attribute definitions,
   in the absence of `SAI_WRED_ATTR_ECN_<COLOR>_MIN/MAX_THRESHOLD` the ECT traffic uses
   `SAI_WRED_ATTR_<COLOR>_MIN/MAX_THRESHOLD` (the drop thresholds), and in the absence of
   `SAI_WRED_ATTR_ECN_<COLOR>_MARK_PROBABILITY` it uses `SAI_WRED_ATTR_<COLOR>_DROP_PROBABILITY`.
4. **Capability-gated:** program the new attributes only where the platform/SAI reports
   support for them; otherwise ignore them gracefully (best-effort) without failing the
   profile.
5. Validate the configuration: `max >= min` per color; a color's ECN threshold is only
   valid when that color is enabled in the profile's `ecn` mode; mark probability in the
   range `0..100`.

## Architecture Design

There is no architectural change. The feature extends the existing WRED programming
path: `WRED_PROFILE` in CONFIG_DB → `QosOrch` → SAI `WRED` object attributes. No new
tables, daemons, or channels are introduced.

## High-Level Design

### CONFIG_DB: WRED_PROFILE additions

Nine optional fields are added to `WRED_PROFILE` (three per color):

| Field | Type | Description |
|-------|------|-------------|
| `ecn_green_min_threshold`     | byte_count | Queue depth (bytes) at which ECN marking begins for green packets |
| `ecn_green_max_threshold`     | byte_count | Queue depth (bytes) at which all green packets are ECN marked |
| `ecn_green_mark_probability`  | percentage (0..100) | Mark probability for green packets between the ECN min/max |
| `ecn_yellow_min_threshold`    | byte_count | As above, yellow |
| `ecn_yellow_max_threshold`    | byte_count | As above, yellow |
| `ecn_yellow_mark_probability` | percentage (0..100) | As above, yellow |
| `ecn_red_min_threshold`       | byte_count | As above, red |
| `ecn_red_max_threshold`       | byte_count | As above, red |
| `ecn_red_mark_probability`    | percentage (0..100) | As above, red |

All fields are optional. When a color's ECN threshold fields are omitted, that color's
ECN marking continues to use the existing WRED drop thresholds (unchanged behavior).

### Orchagent (QosOrch)

`QosOrch` (`WredMapHandler`) is extended to parse the new field names when handling a
`WRED_PROFILE` update and to program the corresponding SAI `WRED` attributes:

- Threshold fields map to `SAI_WRED_ATTR_ECN_<COLOR>_{MIN,MAX}_THRESHOLD` (`sai_uint32_t`).
- Mark-probability fields map to `SAI_WRED_ATTR_ECN_<COLOR>_MARK_PROBABILITY` (`sai_uint32_t`, `0..100`).
- The CONFIG_DB/YANG thresholds are `uint64` (consistent with the existing WRED drop
  thresholds) while the SAI attributes are `sai_uint32_t`, so `QosOrch` narrows the values
  when building the attribute list.
- To avoid transiently programming `min > max` during an update, min/max are sequenced
  using a normal-and-deferred attribute queue: whichever bound would violate the ordering
  against the currently stored value is deferred and applied after the other.
- The ECN attributes are applied **best-effort** — each is set individually and a failed
  `set_wred_attribute` is logged and skipped, leaving the base WRED drop behavior intact
  (mirroring how `PortsOrch` applies optional port attributes).

### ECT enablement and backward compatibility

The per-WRED ECN threshold attributes only take effect when the switch-level attribute
`SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE` is `true` (per the SAI definition). `QosOrch`
enables it **once**, lazily — the first time a profile programs ECN threshold attributes —
and **before** the per-WRED ECN attributes are set, satisfying the SAI validity requirement.

`SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE` is switch-global. Enabling it is safe for
existing profiles: by the SAI attribute semantics above, a profile that does not configure
ECN threshold fields continues to use its WRED drop thresholds for ECN, so no existing
behavior changes.

### Capability handling

`QosOrch` queries SAI capability before programming, using `sai_query_attribute_capability`
for both the per-WRED ECN threshold attributes (`SAI_OBJECT_TYPE_WRED`) and the switch
control (`SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE`). On platforms that do not support them,
the ECN fields are skipped and the switch control is left disabled, without failing the
`WRED_PROFILE` programming.

## SAI API

No SAI header change is required. The feature uses attributes already defined in SAI:

| SAI attribute | Purpose |
|---------------|---------|
| `SAI_WRED_ATTR_ECN_GREEN_MIN_THRESHOLD` / `..._MAX_THRESHOLD` | Green ECN mark thresholds |
| `SAI_WRED_ATTR_ECN_GREEN_MARK_PROBABILITY` | Green ECN mark probability |
| `SAI_WRED_ATTR_ECN_YELLOW_MIN_THRESHOLD` / `..._MAX_THRESHOLD` | Yellow ECN mark thresholds |
| `SAI_WRED_ATTR_ECN_YELLOW_MARK_PROBABILITY` | Yellow ECN mark probability |
| `SAI_WRED_ATTR_ECN_RED_MIN_THRESHOLD` / `..._MAX_THRESHOLD` | Red ECN mark thresholds |
| `SAI_WRED_ATTR_ECN_RED_MARK_PROBABILITY` | Red ECN mark probability |
| `SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE` | Enable ECN threshold-based marking (switch-global) |

Notes on the SAI attributes:

- The ECN threshold attributes are `sai_uint32_t` (thresholds in bytes, range `1 .. max
  buffer size`, default `0` = maximum buffer size; mark probability `0..100`, default `100`).
- They are `@validonly` when `SAI_WRED_ATTR_ECN_MARK_MODE` enables the corresponding color
  (`SAI_ECN_MARK_MODE_{GREEN,YELLOW,RED,GREEN_YELLOW,GREEN_RED,YELLOW_RED,ALL}`, which the
  CONFIG_DB `ecn` field maps to) **and** `SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE == true`.
- In the absence of an ECN threshold / probability attribute, ECT traffic falls back to the
  corresponding WRED drop threshold / drop probability (backward-compatible behavior).

## Configuration and management

### CONFIG_DB Enhancements

Example `WRED_PROFILE` with drop thresholds and independent ECN marking thresholds
(ECN marking begins at a lower depth than drop):

```json
{
    "WRED_PROFILE": {
        "AZURE_LOSSLESS": {
            "wred_green_enable":   "true",
            "green_min_threshold": "1048576",
            "green_max_threshold": "2097152",
            "ecn":                 "ecn_all",
            "ecn_green_min_threshold":    "262144",
            "ecn_green_max_threshold":    "524288",
            "ecn_green_mark_probability": "5"
        }
    }
}
```

### CLI/YANG model Enhancements

The `sonic-wred-profile` YANG model adds the nine leaves above (`uint64`; the
`*_mark_probability` leaves are range `0..100`). Two classes of `must` constraints are
added:

- `max >= min` for each color's ECN thresholds.
- Each ECN field requires the matching color to be enabled in the profile's `ecn` mode
  (e.g. `ecn_green_*` requires `ecn` ∈ {`ecn_green`, `ecn_green_yellow`, `ecn_green_red`,
  `ecn_all`}).

No new CLI command is required; the fields are configurable through the existing
CONFIG_DB / `config qos` flows. CLI enhancement can be added as a follow-up.

## Warmboot and Fastboot Design Impact

None. The new fields live in CONFIG_DB and are reconciled on warm/fast boot exactly like
the existing `WRED_PROFILE` fields. No new dynamic state is introduced.

## Warmboot and Fastboot Performance Impact

None.

## Memory Consumption

None. The feature adds a small, fixed number of optional fields per `WRED_PROFILE` entry
and introduces no new runtime data structures beyond the attributes programmed to SAI.

## Restrictions/Limitations

- The feature is programmed on a best-effort basis and is gated on SAI capability; on
  platforms that do not support the SAI WRED ECN threshold attributes the fields are
  ignored (a failed per-attribute set is logged and skipped, leaving drop behavior intact).
- When the new fields are unset, ECN marking follows the WRED drop thresholds, preserving
  existing behavior.
- Enabling independent ECN thresholds sets the switch-global
  `SAI_SWITCH_ATTR_ECN_ECT_THRESHOLD_ENABLE`; this is done once, lazily, and only when a
  profile uses the feature on a supporting platform. Existing profiles that do not configure
  ECN thresholds are unaffected (they continue using their WRED drop thresholds for ECN).

## Testing Requirements/Design

### Unit Test cases

- `orchagent` `QosOrch` unit tests (`tests/mock_tests/qosorch_ut.cpp`): verify that
  configuring the independent ECN threshold/probability fields programs the expected
  `SAI_WRED_ATTR_ECN_*` attributes, that min/max update ordering is respected, and that
  unsupported platforms skip the fields. (Implemented in sonic-swss #4719.)
- `sonic-yang-models` tests (`tests/yang_model_tests/tests/qos.json`): positive case for
  a valid configuration and negative cases for `max < min` and for an ECN threshold set
  without the matching color enabled in `ecn`. (Implemented in sonic-buildimage #28164.)

### System Test cases

- Configure a `WRED_PROFILE` with independent ECN marking thresholds lower than the drop
  thresholds, bind it to a queue, and verify via ASIC_DB that the `WRED` object carries
  the `SAI_WRED_ATTR_ECN_*` attributes.
- Verify that omitting the new fields leaves ECN behavior unchanged (regression).

## Open/Action items

- Optional `config`/`show` CLI helpers for the independent ECN thresholds (follow-up).
