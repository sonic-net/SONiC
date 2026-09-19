# SONiC Generic HWSKU Definition and Qualification Workflow HLD

## Table of Content

- [1 Revision](#1-revision)
- [2 Scope](#2-scope)
- [3 Definitions/Abbreviations](#3-definitionsabbreviations)
- [4 Overview](#4-overview)
- [5 Requirements](#5-requirements)
- [6 Architecture Design](#6-architecture-design)
- [7 High-Level Design](#7-high-level-design)
  - [7.1 Default HWSKU definition](#71-default-hwsku-definition)
  - [7.2 Deprecate or converge HWSKU-specific configurations](#72-deprecate-or-converge-hwsku-specific-configurations)
    - [7.2.1 Deprecate port and breakout configurations](#721-deprecate-port-and-breakout-configurations)
    - [7.2.2 Converge lossless PG profiles](#722-converge-lossless-pg-profiles)
    - [7.2.3 Converge QoS related settings](#723-converge-qos-related-settings)
    - [7.2.4 Converge buffer-related settings](#724-converge-buffer-related-settings)
    - [7.2.5 Converge SAI and SDK-related settings](#725-converge-sai-and-sdk-related-settings)
    - [7.2.6 Converge media settings](#726-converge-media-settings)
    - [7.2.7 Do not generate non-default HWSKU folders](#727-do-not-generate-non-default-hwsku-folders)
  - [7.3 Step 4: Qualification workflow](#73-step-4-qualification-workflow)
    - [7.3.1 Qualification requirements](#731-qualification-requirements)
    - [7.3.2 sonic-mgmt workflow updates](#732-sonic-mgmt-workflow-updates)
- [8 SAI API](#8-sai-api)
- [9 Configuration and Management](#9-configuration-and-management)
  - [9.1 CLI/YANG model Enhancements](#91-cliyang-model-enhancements)
  - [9.2 Config DB Enhancements](#92-config-db-enhancements)
- [10 Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
  - [10.1 Warmboot and Fastboot Performance Impact](#101-warmboot-and-fastboot-performance-impact)
- [11 Memory Consumption](#11-memory-consumption)
- [12 Restrictions/Limitations](#12-restrictionslimitations)
- [13 Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test cases](#131-unit-test-cases)
  - [13.2 System Test cases](#132-system-test-cases)
- [14 Open/Action items](#14-openaction-items)
- [15 References](#15-references)

## 1 Revision

| Rev | Date       | Author      | Change Description |
|:---:|:-----------|:------------|:-------------------|
| 0.1 | 11/06/2025 | Riff Jiang  | Initial version |
| 0.2 | 02/26/2026 | Bing Wang   | Added SAI profile and qualification updates |
| 0.3 | 03/23/2026 | Bing Wang   | Reworked into SONiC HLD structure and clarified workflow deliverables |

## 2 Scope

This document describes the high-level design for defining, delivering, and qualifying generic HWSKUs in SONiC.

The scope of this HLD is the workflow and artifact model needed to reduce the number of per-breakout HWSKUs that must be authored and qualified independently. It covers the responsibilities associated with requirement definition, platform artifact delivery, and SONiC integration across repositories such as `sonic-buildimage`, `sonic-mgmt`, and `SONiC/doc`.

This HLD is intentionally focused on platform definition and qualification workflow. It is not a runtime data plane feature design for SWSS, Syncd, or SAI.

## 3 Definitions/Abbreviations

| Term | Definition |
|------|------------|
| HWSKU | Hardware SKU. A hardware configuration identified by platform family, model, and port breakout or use-case-specific settings. |
| Generic HWSKU | A base HWSKU that captures platform-wide capabilities and defaults without binding the design to a single breakout configuration. |
| Platform requirements owner | The organization or team defining the target platform requirements and qualification expectations. |
| Platform maintainer | The party responsible for providing platform-specific implementation artifacts and qualification results. |
| Port breakout | Splitting one physical port into multiple logical ports. |
| QoS | Quality of Service. |
| RDMA | Remote Direct Memory Access. |
| OS ratio | Oversubscription ratio. |
| SAI | Switch Abstraction Interface. |
| SI settings | Signal integrity settings for optics or copper media. |

## 4 Overview

Traditional SONiC onboarding has relied on many pre-defined HWSKUs, often one per breakout configuration or deployment scenario. That model makes requirements explicit, but it does not scale well as modern platforms support more breakout combinations, optics, media tuning options, and QoS variants.

The goal of this HLD is to define a community-reviewable workflow for onboarding platforms with a generic HWSKU model. The intent is to reduce duplicated platform artifacts, make qualification more reusable across related breakout variants, and keep the implementation path explicit across `sonic-buildimage`, `sonic-mgmt`, and associated tooling.

## 5 Requirements

Platforms adopting the generic HWSKU model should satisfy the following requirements:

- Define a base HWSKU for the platform instead of requiring a separate pre-defined HWSKU for every expected breakout mode.
- Describe the maximum supported breakout capability and the common per-port feature set, including items such as speed, auto-negotiation, FEC, and supported optics.
- Allow deployment-specific QoS, buffer, media, and qualification requirements to be layered on top of the base platform definition instead of being duplicated in many HWSKU folders.
- Preserve compatibility with current SONiC onboarding flows during transition, while enabling a simpler long-term artifact model.
- Minimize impact to existing platforms and allow incremental adoption, starting with new platforms.

## 6 Architecture Design

This design does not introduce a new SONiC runtime component. Instead, it defines a workflow and artifact model across existing SONiC repositories and scripts.

The following repositories and components are impacted:

- `SONiC/doc`
  - HLD and process documentation for generic HWSKU onboarding and qualification.
- `sonic-buildimage`
  - Platform artifacts such as `default_sku`, `platform.json`, shared templates, QoS/buffer settings, SAI profile templates, and media/SI settings.
- `sonic-mgmt`
  - Inventory metadata, deployment logic, qualification selection, and testbed preparation for breakout-specific validation.
- Management and utility scripts
  - Scripts and helpers that currently assume HWSKU-local files such as `port_config.ini`, `hwsku.json`, or HWSKU-specific templates.

The design has two phases:

- Transition phase
  - Generic HWSKU onboarding must work with the current SONiC configuration and deployment flow, including environments that still use minigraph-based generation.
- Target phase
  - Platform capabilities and common templates are owned at the platform level, while deployment-specific `PORT` and `BREAKOUT_CFG` data come from the effective configuration source used by the system.

Generic HWSKU must not depend exclusively on future migration to `golden_config_db.json`. It should remain implementable with current flows and become simpler as newer configuration models are adopted.

## 7 High-Level Design

### 7.1 Default HWSKU definition

A HWSKU with minimum breakout mode should be defined for each platform. The naming convention continues to follow the existing platform naming pattern:

```text
<Manufacturer>-<Model>-<Minimum Breakout Mode>
```

The name represents the platform at the minimum breakout view, meaning one logical port per physical port.

Examples:

- `Mellanox-SN5640-P64`
- `Arista-7060X6-64PE-B-P64`
- `Nokia-IXR7220-H6-P128`

The HWSKU with minimum breakout is defined as the default HWSKU or base HWSKU. The default HWSKU should be referenced by the `default_sku` file under the platform directory.

### 7.2 Deprecate or converge HWSKU-specific configurations

Historically, one HWSKU definition often contained all of the following:

- Port configurations, such as `port_config.ini`
- Default port breakout mode, such as `hwsku.json`
- Lossless PG profiles, such as `pg_profile_lookup.ini`
- QoS related settings, such as `qos.json.j2`
- Buffer related settings, such as `buffer_ports.j2`, `buffers.json.j2` and `buffers_defaults.j2` for different roles
- SAI and SDK related settings, such as `sai.profile`, `config.bcm` and `sai.xml`
- Media settings for optics, such as `media_settings.json` and `optics_si_settings.json`

For generic HWSKU enablement, these HWSKU-specific settings should either be removed from per-HWSKU folders or converged into platform-level shared configurations.

The goal is a clear target state:

- Platform capability and common defaults are defined once at platform level.
- Deployment-specific configuration is derived from the active system configuration.
- Breakout-specific qualification remains explicit.

The following sections describe the expected direction for each artifact type.

#### 7.2.1 Deprecate port and breakout configurations

A typical `port_config.ini` is shown below.

```ini
# name       lanes                            alias  index  speed   fec
Ethernet0    17,18,19,20,21,22,23,24          etp1    1      800000  rs
Ethernet8    1,2,3,4,5,6,7,8                  etp2    2      800000  rs
Ethernet16   9,10,11,12,13,14,15,16           etp3    3      800000  rs
Ethernet24   25,26,27,28,29,30,31,32          etp4    4      800000  rs
```
This file defines port names and aliases, lanes, port index, speed, and FEC configuration. Today, `port_config.ini` is referenced by `minigraph.py` when generating the `PORT` table in `config_db`, and by some utility scripts that read port configuration.

A typical `hwsku.json` file specifies the default breakout mode for the current HWSKU. The major purpose of `hwsku.json` is to generate the `BREAKOUT_CFG` table in `config_db` when loading minigraph.
```json
{
    "interfaces": {
        "Ethernet0": {
            "default_brkout_mode": "1x800G[400G]"
        },
        "Ethernet8": {
            "default_brkout_mode": "1x800G[400G]"
        },
        "Ethernet16": {
            "default_brkout_mode": "1x800G[400G]"
        },
        ...
    }
}
```
In the long-term target state, `PORT` and `BREAKOUT_CFG` should come from the active configuration source rather than from HWSKU-local static files. `golden_config_db.json` is one possible source of that data, but generic HWSKU should not rely on that migration being complete before adoption begins.

Here is the intended direction for `port_config.ini` and `hwsku.json`:

1. ASIC and SDK initialization should follow effective `PORT` and `BREAKOUT_CFG` data from `config_db`.
2. New platforms adopting generic HWSKU should avoid introducing new HWSKU-specific `port_config.ini` and `hwsku.json` files where the same information can be provided through platform capability data and active configuration.
3. Platform capability and supported breakout modes should be documented at platform level, for example in `platform.json` and accompanying platform documentation.
4. Existing code paths that read `port_config.ini` or `hwsku.json` must be updated to tolerate their absence and to use the platform-level or active configuration source instead.

This means the document is not proposing that `hwsku.json` disappears everywhere immediately. It is proposing that generic HWSKU onboarding move away from using HWSKU-local copies of these files as the primary source of truth.

#### 7.2.2 Converge lossless PG profiles

A typical lossless PG profile lookup table is shown below:
```ini
# PG lossless profiles
# speed cable  size   xon    xoff   threshold
10000   5m  19456  19456  20480  0
25000   5m  19456  19456  21504  0
40000   5m  19456  19456  24576  0
```
Since it is a lookup table, all supported or required port speed and cable length combinations can be stored in a common `pg_profile_lookup.ini` at platform level. The file can be placed in the default HWSKU folder.

SONiC code also needs to be improved so that `pg_profile_lookup.ini` in the platform folder is used when the file is not present in the HWSKU folder.

#### 7.2.3 Converge QoS related settings

For most HWSKUs, the `qos.json.j2` is just a reference to template file `qos_config.j2`. 

```json
{%- include 'qos_config.j2' %}
```
For these HWSKUs, the preferred approach is to remove `qos.json.j2` from the HWSKU folder. SONiC code then needs to fall back to `qos_config.j2` in the template folder when `qos.json.j2` is not present.

Some HWSKUs also define dedicated macros in `qos.json.j2`. These are usually used to generate HWSKU-specific WRED configurations or QoS mappings such as `DSCP_TO_TC_MAP` and `TC_TO_QUEUE_MAP`.

```json
{%- macro generate_wred_profiles() %}
    "WRED_PROFILE": {
        "AZURE_LOSSLESS" : {
            "wred_green_enable"      : "true",
            "wred_yellow_enable"     : "true",
            "wred_red_enable"        : "true",
            ...
        }
    },
{%- endmacro %}
{%- macro  generate_normal_dscp_to_tc_map() -%}
        {
            "0" : "1",
            "1" : "1",
            "2" : "1",
            "3" : "3",
            ...
            "63": "1"
        }
{%- endmacro -%}
```
For these HWSKUs, the recommendation is to converge QoS templates into a common file located in the platform folder. The template should then be rendered according to input from `config_db`. For example:
```json
{{%- macro generate_dscp_to_tc_map() %}
    "DSCP_TO_TC_MAP": {
{% if ('type' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['type'] == 'LeafRouter') %}
        "AZURE_UPLINK":
        {{ generate_normal_dscp_to_tc_map() }},
        "AZURE":
        {{ generate_dscp_to_tc_map_with_addition_lossless_pgs_n_queues() }}
{% endif %}
    },
{%- endmacro %}
``` 

#### 7.2.4 Converge buffer-related settings

Typically, there are three different kinds of buffer-related configurations in the HWSKU folder.

- buffers.json.j2

  For most HWSKUs, `buffers.json.j2` is only a reference to `buffers_config.j2`. The recommended direction is to move it to the platform folder and share the common file across HWSKUs.


```ini
  {%- set default_topo = 't0' %}
  {%- include 'buffers_config.j2' %}
```

- buffers_defaults_t0.j2/buffers_defaults_t1.j2/buffers_defaults_t2.j2

  `BUFFER_POOL` and `BUFFER_PROFILE` tables are defined in these template files. A typical `buffer_defaults` template file is shown below.

```json
  {%- set default_cable = '5m' %}

  {%- include 'buffer_ports.j2' %}

  {%- macro generate_buffer_pool_and_profiles() %}
      "BUFFER_POOL": {
          "ingress_lossless_pool": {
              ...
          },
          "egress_lossless_pool": {
              ...
          }
      },
      "BUFFER_PROFILE": {
          "egress_lossy_profile": {
              ...
          },
          "egress_lossless_profile": {
              ...
          },
          "ingress_lossy_profile": {
              ...
          }
      },
  {%- endmacro %}
```

There are three options for these HWSKU-specific buffer configurations:

1. Use a unified set of values for all HWSKUs on a platform.
2. Render the values according to port breakout mode and/or device role.
3. Calculate the values dynamically according to port breakout mode. An example is [buffers_defaults_objects.j2](https://github.com/sonic-net/sonic-buildimage/blob/master/device/mellanox/x86_64-nvidia_sn5600-r0/Mellanox-SN5600-C256S1/buffers_defaults_objects.j2).


#### 7.2.5 Converge SAI and SDK-related settings

SAI and SDK-related settings are platform-dependent. Typically, there are two kinds of settings:
- sai.profile

  This file contains a set of key-value pairs. `sai.profile` is referenced at runtime by the syncd init script, which passes it to the syncd binary.

  ```
  SAI_INIT_CONFIG_FILE=/usr/share/sonic/hwsku/config.bcm
  SAI_NUM_ECMP_MEMBERS=96
  SAI_NHG_HIERARCHICAL_NEXTHOP=false
  ``` 

  The guidance for `sai.profile` is to move HWSKU-specific SAI settings into `config_db` where possible. If there is no SAI API available, the key-value pair should be moved into a common template profile file in the platform folder. The template should be rendered according to input from `config_db`.

- SDK or ASIC-related settings

  SDK or ASIC-related settings are platform-dependent. For example, they may be represented as an XML file on a `Mellanox` platform and as a YAML file on a `Broadcom` platform.
  
  The guidance is to avoid HWSKU-specific settings in SDK configuration wherever possible. Instead, the configuration should be driven by `config_db`, or generated dynamically according to port breakout mode.
  
  If HWSKU specific settings have to be used, the guidance is to render different SDK configurations according to the input from `config_db`. An example is [sai.profile](https://github.com/sonic-net/sonic-buildimage/blob/master/device/celestica/x86_64-cel_seastone_2-r0/Seastone_2/sai.profile.j2).

#### 7.2.6 Converge media settings

Some HWSKUs also include media or optics-related settings. These configuration files define per-port or per-media (optic/cable) tuning parameters.

Such parameters should be defined in the platform folder instead of in the HWSKU folder.


#### 7.2.7 Do not generate non-default HWSKU folders

Once the configuration files currently stored in HWSKU folders are deprecated or moved to the platform folder, the recommendation for new platforms is to avoid generating non-default HWSKU folders.

To support this, SONiC scripts need to be improved so that configuration and show commands continue to work when only the default HWSKU folder exists.


### 7.3 Step 4: Qualification workflow

Qualification continues to be executed against concrete HWSKUs or breakout-specific operating points even when the base platform uses a generic HWSKU model.

#### 7.3.1 Qualification requirements

The qualification request should still identify the actual breakout variant under test. For example:

- `Mellanox-SN5640-C512S2`

Two qualification models are supported:

- Current model:
  - Specify HWSKU, topology, and required tests explicitly for each variant.
- Optimized model:
  - Select one or two representative base variants and run broad coverage there.
  - For other variants of the same platform, run a reduced qualification set focused on data plane and QoS deltas.

Examples of representative qualification:

- Run full `t0` and `t1` coverage on a maximum-scale breakout variant.
- Run reduced delta coverage for smaller breakout variants on the same platform.

#### 7.3.2 sonic-mgmt workflow updates

To support generic HWSKU qualification, `sonic-mgmt` is expected to support:

- Inventory metadata that reflects the desired breakout mode.
- Minigraph deployment logic that can operate against a generic base HWSKU.
- Mapping or symlink handling from a concrete breakout-specific HWSKU name to the generic base HWSKU, for example:

```text
Mellanox-SN5640-C512S2 -> Mellanox-SN5640
```

- Re-evaluation of templates after minigraph deployment so that QoS and other derived parameters are applied correctly.


## 8 SAI API

This workflow HLD does not introduce new SAI APIs.

The expectation is that existing platform-specific SAI profiles, SDK configuration mechanisms, and breakout-capable platform data models are used where needed. Any additional SAI capability required by a specific platform should be handled by the corresponding implementation HLD or platform onboarding work, not by this workflow document.

## 9 Configuration and Management

### 9.1 CLI/YANG model Enhancements

No new user-facing CLI or YANG model is introduced by this workflow HLD.

Any CLI or management changes required to consume generic HWSKU data should be documented in the corresponding implementation HLD for the affected repository.

### 9.2 Config DB Enhancements

This HLD does not define a new CONFIG_DB table or schema.

However, it does rely on existing configuration tables such as `PORT`, `BREAKOUT_CFG`, and `DEVICE_METADATA` becoming the effective source for runtime configuration selection. The main change in this document is how platform artifacts are organized and selected, not the addition of new Config DB tables.


## 10 Warmboot and Fastboot Design Impact

This workflow itself does not change warmboot or fastboot behavior.

Warm reboot expectations remain part of platform qualification requirements. If a specific platform implementation changes boot-time behavior, warmboot behavior, or fastboot timing, that impact must be captured in the corresponding implementation HLD and validation plan.

### 10.1 Warmboot and Fastboot Performance Impact

No direct runtime performance impact is introduced by this document.

Any impact would come from concrete implementation changes in `sonic-buildimage`, `sonic-mgmt`, or platform-specific templates, and should be analyzed in those follow-on implementation documents.

## 11 Memory Consumption

No direct memory impact is expected from this workflow HLD because it defines process and artifact organization rather than a new runtime feature.

## 12 Restrictions/Limitations

The current design has the following limitations:

- It is better suited for new platforms than for large-scale retrofitting of old platforms.
- Some platforms may still require breakout-specific SDK or template special casing, which reduces the benefit of a unified base HWSKU.
- Some current scripts and deployment flows still assume HWSKU-local files and will require follow-on implementation work before the target model is fully achieved.


## 13 Testing Requirements/Design

Testing for this HLD is primarily workflow and artifact validation rather than unit testing of a new runtime component.

The design should be validated through:

- Documentation review of the generic HWSKU process.
- Review of platform deliverables for `platform.json`, `default_sku`, shared QoS artifacts, shared buffer artifacts, SAI/SDK templates, and media/SI tuning.
- Where transition compatibility is needed, verify fallback behavior for legacy consumers of `port_config.ini` and `hwsku.json`.
- Verification that `sonic-mgmt` can select and deploy the intended breakout-specific testbed configuration.
- Qualification execution against at least one representative base variant and one derived breakout-specific variant.

### 13.1 Unit Test cases

There are no direct unit tests for this workflow document itself.

Follow-on implementation changes in `sonic-mgmt` or platform tooling should add unit tests where logic is modified.

### 13.2 System Test cases

Representative system validation should include:

- Deploying a generic base HWSKU and confirming the expected platform defaults are applied.
- Deploying a breakout-specific qualification variant and confirming the derived QoS and template data are applied correctly.
- Running qualification suites for representative topologies such as `t0` and `t1`.
- Verifying result reporting remains tied to the concrete tested breakout configuration.

## 14 Open/Action items

- Define the minimum implementation changes required in `sonic-buildimage`, `sonic-mgmt`, and helper scripts before generic HWSKU onboarding can be enabled broadly.
- Decide whether platform capability documentation should be represented only in `platform.json` or also in a human-readable platform-level document.
- Define the transition plan for environments that still depend on minigraph-generated `PORT` and `BREAKOUT_CFG` content.
- Clarify the preferred strategy for buffer convergence: unified values, rendered values, or fully dynamic calculation.
- Define qualification rules for when reduced coverage is acceptable for derived breakout variants.

## 15 References

- [SONiC dynamic port breakout feature high level design](https://github.com/sonic-net/SONiC/blob/master/doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md)
- [Enhancement: Clean up `port_config.ini` dependencies for HWSKUs that use `hwsku.json` instead of `port_config.ini`](https://github.com/sonic-net/sonic-buildimage/issues/24494)
- [Enhancement: Enhance `hwsku.json` to support generic HWSKU](https://github.com/sonic-net/sonic-buildimage/issues/25718)
- [Enhancement: Move `pg_profile_lookup.ini` to a shared place for all HWSKU on a specific platform](https://github.com/sonic-net/sonic-buildimage/issues/25716)
- [Enhancement: Unified SAI profile and SDK configuration across different HWSKU](https://github.com/sonic-net/sonic-buildimage/issues/25720)
- [Enhancement: Enhance buffer and QoS template to support generic HWSKU](https://github.com/sonic-net/sonic-buildimage/issues/25747)
- [Enhancement: Ensure minigraph-based provisioning is compatible with generic HWSKU](https://github.com/sonic-net/sonic-buildimage/issues/25751)

