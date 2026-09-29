# Dynamic SAI Profile Configuration via CONFIG_DB
#### Rev 1.0

## Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [1. Overview](#1-overview)
  * [2. Motivation](#2-motivation)
  * [3. Requirements](#3-requirements)
  * [4. Design](#4-design)
      * [4.1 SAI_PROFILE CONFIG_DB Table](#41-sai_profile-config_db-table)
      * [4.2 YANG Model](#42-yang-model)
      * [4.3 Template Rendering](#43-template-rendering)
      * [4.4 Vendor Integration](#44-vendor-integration)
      * [4.5 Precedence and Safety](#45-precedence-and-safety)
  * [5. CLI](#5-cli)
  * [6. Test Plan](#6-test-plan)
  * [7. Upgrade/Downgrade Considerations](#7-upgradedowngrade-considerations)
  * [8. Open Questions](#8-open-questions)

### Revision
| Rev | Date       | Author           | Change Description |
|:---:|:----------:|:-----------------|:--------------------|
| 1.0 | 09/29/2025 | Shiyan Wang (bingwang-ms) | Initial revision |

## About this Manual
This document describes a mechanism to inject arbitrary SAI profile
key/value pairs (rendered into `/etc/sai.d/sai.profile`, consumed by
`syncd`/the vendor SAI implementation) from CONFIG_DB, without requiring
a schema or template change every time a new SAI tunable is introduced on
a given platform.

## 1. Overview
`sai.profile` is a flat `KEY=VALUE` file read by `syncd` at startup and
passed to the vendor SAI implementation as its initialization profile
(`sai_query_attribute_capability`/profile map consumed via
`sai_api_query`/`sai_service_method_table_t.profile_get_value`). Today,
across supported platforms, this file is produced in one of two ways:

* **Fully static** — a plain `sai.profile` file checked into the hwsku
  directory (the majority of platforms today).
* **Partially templated** — a `sai.profile.j2` Jinja2 template rendered
  at container startup via
  `sonic-cfggen -d -t sai.profile.j2 > /etc/sai.d/sai.profile`
  (`-d` pulls live CONFIG_DB data). Today this is only used to make a
  structural decision (e.g. which `SAI_INIT_CONFIG_FILE` to select based
  on `DEVICE_METADATA.localhost.type`); any other keys placed in these
  templates today are still hardcoded literal values.

This HLD proposes a **generic, vendor-agnostic CONFIG_DB table**
(`SAI_PROFILE`) plus a **shared Jinja2 rendering snippet** so that both
the *key name* and *value* of any SAI profile tunable can be supplied
from CONFIG_DB, and reused unmodified by every hwsku/platform's
`sai.profile.j2`.

## 2. Motivation
Different vendors (and even different ASIC generations from the same
vendor) require completely disjoint sets of SAI profile keys, for
example:

* Broadcom: `SAI_NUM_ECMP_MEMBERS`, `SAI_NHG_HIERARCHICAL_NEXTHOP`
* Mellanox/NVIDIA: `SAI_INDEPENDENT_MODULE_MODE`,
  `SAI_WCMP_NORMALIZATION_MAX_TOTAL_WEIGHT`,
  `SAI_DUMP_STORE_PATH`, `SAI_ASYNC_ROUTING_ENABLED`

A schema that tries to enumerate every vendor's SAI knob as a named YANG
leaf does not scale — every new SAI tunable, on every vendor, would
require a YANG/schema change and a new template stanza. A single
generic name/value table lets:

* Operators tune SAI behavior at runtime (via `config`/`sonic-db-cli`)
  without an image rebuild.
* Different hwskus/platforms carry entirely different sets of keys using
  the exact same rendering template code.
* New SAI tunables be added purely as data (CONFIG_DB defaults), with no
  template or YANG change required for the common case.

## 3. Requirements
* A CONFIG_DB table that can hold an arbitrary number of `key=value`
  string pairs, where both the key name and the value are data, not
  schema.
* A shared, vendor-agnostic Jinja2 template snippet that renders every
  entry in the table as one `KEY=VALUE` line.
* No regression for hwskus/platforms that do not use this table — output
  must be unchanged if the table is absent or empty.
* This table must not replace or override the structural
  `SAI_INIT_CONFIG_FILE` selection logic (which stays explicit,
  device-type-driven code in each `sai.profile.j2`).
* Values must be treated as opaque strings — this table intentionally
  performs no vendor-specific semantic validation, since that is not
  enumerable generically across vendors/ASICs.

## 4. Design

### 4.1 SAI_PROFILE CONFIG_DB Table
A new table, `SAI_PROFILE`, keyed by the profile key name itself:

```
"SAI_PROFILE": {
    "SAI_NUM_ECMP_MEMBERS": {
        "value": "128"
    },
    "SAI_NHG_HIERARCHICAL_NEXTHOP": {
        "value": "false"
    }
}
```

Each row corresponds 1:1 to a `KEY=VALUE` line that will be written into
`/etc/sai.d/sai.profile`. Rows are populated from per-hwsku
`config_db.json` defaults at build time, and/or may be modified at
runtime via `sonic-db-cli`/`config` for tuning without a reflash.

### 4.2 YANG Model
A minimal, intentionally loose YANG model validates only structural
correctness (a well-formed key name and a non-empty value), not
per-vendor semantics:

```yang
module sonic-sai-profile {

    yang-version 1.1;
    namespace "http://github.com/sonic-net/sonic-sai-profile";
    prefix sai-profile;

    import sonic-types {
        prefix stypes;
    }

    description "SAI_PROFILE table YANG Module for SONiC. Provides a generic, vendor-agnostic mechanism to inject arbitrary SAI init-config key/value pairs, rendered into /etc/sai.d/sai.profile, without requiring per-key schema changes as new SAI knobs are introduced.";

    revision 2025-09-29 {
        description "Initial revision.";
    }

    container sonic-sai-profile {

        container SAI_PROFILE {

            description "SAI_PROFILE table in config_db.json. Each entry maps directly to one KEY=VALUE line written into /etc/sai.d/sai.profile at syncd startup.";

            list SAI_PROFILE_LIST {
                key "name";
                description "A SAI profile key/value entry keyed by name.";

                leaf name {
                    description "SAI profile key name. Must exactly match the SAI environment variable name expected by the vendor's SAI/SDK implementation, e.g. SAI_NUM_ECMP_MEMBERS.";
                    type string {
                        length 1..255;
                        pattern "[A-Z][A-Z0-9_]*";
                    }
                }

                leaf value {
                    description "Value for this SAI profile key, rendered verbatim as a string. Interpretation/validation of the value is the vendor SAI/SDK implementation's responsibility, not this schema's.";
                    type string {
                        length 1..255;
                    }
                    mandatory true;
                }
            }
        }
    }
}
```

### 4.3 Rendering Mechanism
A shared, reusable Jinja2 partial renders every row in `SAI_PROFILE`
generically:

```jinja2
{# src/sonic-config-engine/data/sai_profile_dynamic.j2 #}
{%- if SAI_PROFILE is defined %}
{%- for key, entry in SAI_PROFILE.items() %}
{{ key }}={{ entry.value }}
{% endfor %}
{%- endif %}
```

The template lives under `sonic-config-engine`'s `data/` directory,
which its `setup.py` installs to `/usr/share/sonic/templates` as
package data. Every container built `FROM docker-config-engine-trixie`
(including `syncd`) installs this package, so the template resolves
without any extra `-t`/path configuration or per-container mount.

Rather than requiring every hwsku's `sai.profile`/`sai.profile.j2` to
individually opt in with a Jinja `{% include %}`, a generic,
vendor-agnostic shell helper, `apply_sai_profile_configdb()`, was added
to `syncd/scripts/syncd_init_common.sh` in `sonic-sairedis`:

```bash
apply_sai_profile_configdb()
{
    local profile_file="$1"
    local dynamic_template="$TEMPLATES_DIR/sai_profile_dynamic.j2"
    local rendered

    if [[ -f "$dynamic_template" ]]; then
        rendered="$(sonic-cfggen -d -t "$dynamic_template")"
        if [[ -n "$rendered" ]]; then
            # ">>" creates profile_file if it does not already exist, so
            # entries are applied even with no pre-existing sai.profile.
            echo "$rendered" >> "$profile_file"
            logger -t syncd_init_common "SAI_PROFILE CONFIG_DB entries applied to $profile_file: ..."
        fi
    fi
}
```

Each vendor's `config_syncd_*()` function calls this helper as the very
last step before handing its final profile file to `syncd` (`-p
<file>`). It is a no-op when `SAI_PROFILE` is empty/absent, so **no
per-hwsku template change is required at all** to support this table —
it works uniformly for both static `sai.profile` files and rendered
`sai.profile.j2` files, and even when a vendor has **no pre-existing
sai.profile at all** (`>>` creates `profile_file` if it doesn't already
exist). Whenever entries are actually applied, a `logger` call emits a
syslog line naming the target file and every `KEY=VALUE` pair appended
— visible in syslog without needing to enable syncd's own verbose/debug
logging (`Syncd::loadProfileMap()` already logs every parsed key via
`SWSS_LOG_INFO`, but that's suppressed at syncd's default `NOTICE` log
level).

### 4.4 Vendor Integration
| Vendor | Integration |
|---|---|
| Broadcom | `config_syncd_bcm()` calls `apply_sai_profile_configdb()` on whichever profile file it ultimately selects (`/tmp/sai.profile`, `/etc/sai.d/sai.profile`, or a writable copy of `$HWSKU_DIR/sai.profile`), right before setting `-p`. The copy step tolerates a missing source file, so `SAI_PROFILE` entries are applied even if a hwsku has no static `sai.profile` at all. No hwsku template change needed. |
| Mellanox/NVIDIA | `config_syncd_mlnx()` calls `apply_sai_profile_configdb()` on `/tmp/sai.profile` as the last step, after its existing `awk -F= '!seen[$1]++'` (first-occurrence-wins) de-duplication and all other derived settings (MAC address, warm-boot paths, DSCP remapping, extra profile) — guaranteeing `SAI_PROFILE` entries still win despite that vendor's own first-wins convention. No hwsku template change needed. |
| Other vendors | Not yet wired up; any `config_syncd_*` function can adopt `SAI_PROFILE` support with a single `apply_sai_profile_configdb <final_profile_file>` call as a follow-up. |

### 4.5 Precedence and Safety
* `SAI_PROFILE` entries are strictly additive — they never replace or
  override `SAI_INIT_CONFIG_FILE` or other structural lines, which
  remain explicit template/script code.
* If the `SAI_PROFILE` table is absent or empty,
  `apply_sai_profile_configdb()` appends nothing, so the final profile
  file is byte-for-byte identical to today's output — fully backward
  compatible.
* If a vendor has no pre-existing static `sai.profile` at all,
  `apply_sai_profile_configdb()` still creates the file from
  `SAI_PROFILE` CONFIG_DB entries alone — an earlier revision of the
  Broadcom integration required a pre-existing file (a `cp` failure on
  a missing source silently left `/tmp/sai.profile` absent, so entries
  were dropped with no error/log); this has been fixed so entries are
  always applied regardless of whether a static baseline exists. Note
  `SAI_INIT_CONFIG_FILE` is still reserved and cannot be supplied via
  `SAI_PROFILE`, so a fully CONFIG_DB-only profile is still unlikely to
  be sufficient for a real ASIC/SDK to initialize.
* This table intentionally does not gate/validate individual SAI
  semantics; a malformed value is passed through and will surface as a
  SAI/SDK initialization failure, exactly as a manually-edited static
  `sai.profile` would today.
* **Duplicate/conflicting keys**: `syncd` parses the final profile file
  in `Syncd::loadProfileMap()` (`sonic-sairedis`) by reading it line by
  line, splitting on the first `=`, and assigning into a `std::map` —
  a plain overwrite with no duplicate-key detection or warning, and
  later lines always win. Because `apply_sai_profile_configdb()` is
  called as the very last step in each vendor's `config_syncd_*()`
  function, a `SAI_PROFILE` entry whose key matches an existing
  hardcoded static key is always rendered last and therefore silently
  wins, overriding that static default, regardless of any
  vendor-specific de-duplication earlier in the script. This is
  intentional and is exactly how tuning a key without an image rebuild
  is meant to work. A key can never collide with another `SAI_PROFILE`
  entry, since CONFIG_DB stores the table as a hash keyed uniquely by
  `name`.

## 5. CLI
No new CLI commands are introduced by this HLD; existing generic
mechanisms are sufficient:

* `sonic-db-cli CONFIG_DB HSET "SAI_PROFILE|<KEY>" value "<VALUE>"`
* `sonic-db-cli CONFIG_DB HGETALL "SAI_PROFILE|<KEY>"`

A follow-up HLD/PR may add first-class `config`/`show` subcommands if
operator ergonomics require it; this is called out as a possible future
enhancement, not a blocking requirement for the initial implementation.

## 6. Test Plan
* YANG model unit tests: valid entry, invalid key name pattern, missing
  `value` leaf.
* Jinja2 template unit test (`sonic-config-engine` `test_j2files.py`
  style): render `sai.profile.j2` with a populated `SAI_PROFILE` table
  and assert the exact expected output; render with the table absent and
  assert output is unchanged from the pre-existing baseline.
* End-to-end: on a lab device, populate `SAI_PROFILE`, restart `syncd`,
  confirm `/etc/sai.d/sai.profile` contains the expected lines and
  `syncd` initializes successfully.

## 7. Upgrade/Downgrade Considerations
* New table, no existing data to migrate.
* On downgrade to an image without this feature, any `SAI_PROFILE`
  entries in CONFIG_DB are simply ignored (unknown table), no crash or
  validation failure expected.

## 8. Open Questions
* Should a future revision add typed sub-schemas (e.g. per-vendor YANG
  augmentations) for a curated subset of "well-known" keys, while
  keeping this generic table as the escape hatch for everything else?
* Should `config`/`show` CLI wrappers be added in the same phase, or as
  a fast-follow?
