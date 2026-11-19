# Objective 1 - Design Document: Investigated Modularization Mechanisms

LFX Mentorship | SONiC

This document walks through the three template-sharing mechanisms we found while investigating Objective 1. For each one it describes what the mechanism actually does, how Jinja resolves it when a file is rendered, a real example already in the repository, and where we used it in the `buffers.json.j2` / `qos.json.j2` migration.

## Summary

| Mechanism | What the device provides | Shared file | Used in our migration |
|---|---|---|---|
| 1. Shared include + topology variable | One variable, `default_topo` | `files/build_templates/buffers_config.j2` | All 29 `buffers.json.j2` files |
| 2. Shared include + overriding macros | Named macros for the blocks it overrides | `files/build_templates/qos_config.j2` | 5 `qos.json.j2` files |
| 3. Filesystem symlinks | Nothing: the file is a symlink | A real file in a vendor-shared profiles directory | Not used |

---

## Mechanism 1: Shared Include + Topology Variable

This is what `buffers.json.j2` uses. The device file sets one variable for its topology, then includes a template that every device shares, `files/build_templates/buffers_config.j2`.

### How it resolves at render time

1. `buffers.json.j2` sets `default_topo` (`t0`, `t1`, `t2`, `lt2`, or non-router roles like `l2`), then does `{%- include 'buffers_config.j2' %}`.
2. `{% include %}` shares the calling template's variables with whatever it includes, while `{% import %}` does not. So `default_topo` is visible inside `buffers_config.j2` even though `buffers_config.j2` never defines it itself.
3. `buffers_config.j2` uses that variable to build a filename: `{%- import 'buffers_defaults_%s.j2' % filename_postfix as defs with context %}`. The `%s` is plain string formatting: it turns `t0` into `buffers_defaults_t0.j2` and imports that file.
4. Whatever that import returns (`default_cable`, etc.) feeds into the `BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` / `BUFFER_QUEUE` sections that `buffers_config.j2` generates.

> **Note on `default_sku`.** `default_sku` (one per platform, in the form `<sku_name> <topology>`) is not read by `buffers_config.j2` at render time at all. It is a build-time file. During the migration we used its second field to work out what `default_topo` should be for each device. `default_sku` gave us the answer, but it is not part of the render path itself.

### Real example already in sonic-buildimage

```jinja
{%- set default_topo = 't0' %}
{%- include 'buffers_config.j2' %}
```

- Device file: <https://github.com/sonic-net/sonic-buildimage/blob/master/device/celestica/x86_64-cel_seastone-r0/Celestica-DX010-D48C8/buffers.json.j2>
- Shared template: <https://github.com/sonic-net/sonic-buildimage/blob/master/files/build_templates/buffers_config.j2>

### Used in our migration

All 29 `buffers.json.j2` files we migrated. `default_topo` for each came from that device's own `default_sku`, and the file itself shrank down to the same two lines shown above.

---

## Mechanism 2: Shared Include + Overriding Macros

`qos.json.j2` uses this one. It is a step up from Mechanism 1: instead of one variable, the device hands over whole blocks of content as named macros, and the shared template calls them if they exist.

### How it resolves at render time

1. `qos.json.j2` defines macros with names `qos_config.j2` already knows to look for, for example `{%- macro generate_wred_profiles() %} ... {%- endmacro %}`, then includes `qos_config.j2`.
2. The same scope sharing as in Mechanism 1 applies: `qos_config.j2` can see these macros even though it never defines them.
3. For each value it needs, `qos_config.j2` checks `{% if generate_wred_profiles is defined %}`. If the macro exists, it uses whatever the macro returns. If not, it falls back to its own hardcoded `AZURE` default.
4. The macro has to write out the whole `"KEY": { ... }` block itself, key name and braces included. There is no wrapper text around the call site in `qos_config.j2` to do that part for you.

`qos.json.j2` does not set its own topology at all. `qos_config.j2` pulls it from the sibling `buffers.json.j2` instead (it imports it and reads `buffer_defs.default_topo`). So a device's `qos.json.j2` cannot really be migrated until its `buffers.json.j2` already has `default_topo` set.

> **Worth flagging.** Unlike `CABLE_LENGTH` in `buffers_config.j2`, none of the keys in `qos_config.j2` can be turned off. Every key gets emitted one way or another. If a device's old file never had a certain key, migrating it adds that key back with the shared default value.

### Real example already in sonic-buildimage

```jinja
{%- macro generate_wred_profiles() %}
    "WRED_PROFILE": {
        "AZURE_LOSSLESS" : { ... }
    },
{%- endmacro %}

{%- include 'qos_config.j2' %}
```

- Device file: <https://github.com/sonic-net/sonic-buildimage/blob/master/device/mellanox/x86_64-mlnx_msn2700-r0/ACS-MSN2700/qos.json.j2>
- Shared template: <https://github.com/sonic-net/sonic-buildimage/blob/master/files/build_templates/qos_config.j2>
- PR that originally added this pattern: <https://github.com/sonic-net/sonic-buildimage/pull/2023>

### Used in our migration

The 5 `qos.json.j2` files we migrated: Accton AS7116, Celestica Midstone-200i_64x100nrz, Ingrasys S9130-32X and S9230-64X, and Inventec D6356. Each one only defines overrides for the keys its original file actually had, nothing more.

---

## Mechanism 3: Filesystem Symlinks

No Jinja is involved here at all. The device's file is just a symlink pointing at one real file, sometimes through more than one hop.

### How it resolves at render time

1. In git, the file at the device's path is stored as a symlink (mode `120000`). Its "content" is just the relative path text of whatever it points to.
2. The `sonic-cfggen` Jinja loader opens the path like any other file, and the OS follows the symlink transparently. Nothing Jinja-specific or build-specific needs to know this is happening.
3. Some of these chains go two levels deep: a device's `qos.json.j2` points at a locally named folder (say, `BALANCED`), and that folder is itself a symlink into a vendor-shared profiles directory that holds the actual file.
4. Change the one real file at the end of the chain and every device linking to it picks up the change immediately. Since it is just a filesystem link, it is not tied to `buffers.json.j2` or `qos.json.j2` specifically and would work for any file.

This is a vendor sharing config across their own SKU lineup, not something shared between different vendors.

### Real example already in sonic-buildimage

```text
Force10-S6100/qos.json.j2  ->  BALANCED
BALANCED  ->  ../../../common/profiles/th/6100/BALANCED
(resolves to) device/common/profiles/th/6100/BALANCED/qos.json.j2
```

- Device symlink: <https://github.com/sonic-net/sonic-buildimage/blob/master/device/dell/x86_64-dell_s6100_c2538-r0/Force10-S6100/qos.json.j2>
- Shared profile directory it resolves to: <https://github.com/sonic-net/sonic-buildimage/tree/master/device/common/profiles/th/6100/BALANCED>

### Used in our migration

We did not end up using this one. None of the devices in our `buffers.json.j2` / `qos.json.j2` batches had an existing shared profile directory to point at. It is included here because it is a real pattern already proven elsewhere in the repository, and it is worth keeping in mind for devices that are true hardware clones of each other.
