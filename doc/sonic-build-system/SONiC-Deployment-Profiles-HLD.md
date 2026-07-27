# SONiC Deployment Profiles

## High-Level Design Document

---

## Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Architecture Design](#architecture-design)
  - [Existing Configuration layering](#existing-configuration-layering)
  - [Proposed Configuration layering](#proposed-configuration-layering)
  - [Passing SONIC_PROFILE](#passing-sonic_profile)
- [High-Level Design](#high-level-design)
  - [Proposed Build Configuration Variables](#proposed-build-configuration-variables)
  - [Configuration files Changes](#configuration-files-changes)
  - [Fix Inconsistencies](#fix-inconsistencies)
  - [Preserve existing configuration variables](#preserve-existing-configuration-variables)
    - [Preserve SYSTEM_EVENTD computation](#preserve-system_eventd-computation)
    - [Preserve SONIC_INCLUDE pass-through](#preserve-sonic_include-pass-through)
    - [Preserve conditional checks in init_cfg.json.j2](#preserve-conditional-checks-in-init_cfgjsonj2)
  - [Canonical Feature Makefile Pattern](#canonical-feature-makefile-pattern)
- [Default Build Configuration Variables - Zero Regression](#default-build-configuration-variables---zero-regression)
- [Profile System](#profile-system)
  - [Build Configuration Variable Combinations](#build-configuration-variable-combinations)
  - [Listing Available Profiles](#listing-available-profiles)
  - [Inspecting profile feature settings](#inspecting-profile-feature-settings)
- [Adding a New Optional Docker Feature](#adding-a-new-optional-docker-feature)
  - [Checklist for a new feature](#checklist-for-a-new-feature)
    - [1. rules/config](#1-rulesconfig)
    - [2. rules/config.SONIC_PROFILE](#2-rulesconfigsonic_profile)
    - [3. Build and runtime wiring](#3-build-and-runtime-wiring)

---

## Revision

| Version | Date       | Author       | Description                          |
|---------|------------|--------------|--------------------------------------|
| 0.1     | 2024-07-30 | Amir Mazor   | Initial Draft                        |
| 0.2     | 2026-06-28 | Nitin Saxena | Refactored for latest SONiC          |

---

## Scope

This document describes SONiC deployment profiles - named, deployment-targeted
build configurations selected at build time - and the changes needed to align
build configuration variables with zero regression of stock builds.

## Definitions/Abbreviations
_SONIC_PROFILE_ is a proposed command-line argument in this HLD to `make` which
translates to include rules/config.\<SONIC_PROFILE> internally by the build
system.

## Overview

SONiC Deployment Profiles let users select a named build profile at image build
time (e.g. `DATACENTER`, `ENTERPRISE`) based on the target deployment use case.

This HLD positions SONiC to be more aligned with deployments beyond the datacenter use
cases. In a nutshell, for optional SONiC features, this HLD provides
controls to

- Build into the image exactly what is needed for the targeted deployment
- At boot time: which features to launch and when to launch (immediate or deferred)

The HLD achieves the above by

- Standardize how build configuration variables in _rules/config_ are applied
  across optional features with consistent behavior
- Preserve the existing build flow when no _SONIC_PROFILE_ is set, avoiding
  regression for stock builds. Also preserve existing variable names
  (INCLUDE_SYSTEM_XXX, container names and existing SONIC_INCLUDE_XXX) for
  backward compatibility.
- Add version-controlled, deployment-targeted profile files
  (**rules/config.\<SONIC_PROFILE>**) that define only the optional features
  needed for each deployment target
- When _SONIC_PROFILE_ is set, use _rules/config.\<SONIC_PROFILE\>_ instead of
  _rules/config_ configurations. Non-feature build settings are still used from
  _rules/config_ (eg: _SONIC_DPKG_CACHE_METHOD_ etc)
- Keep backward compatibility to allow local overriding of feature variables
  via _rules/config.user_. 
- Not impacting _core SONiC_ features like SWSS, orchagent, etc.

## Architecture Design

### Existing Configuration layering

```
                         ┌──────────────────────────┐
                         │       rules/config       │
                         └──────────────────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │    rules/config.user    │
                          │(overrides rules/config) │
                          └─────────────────────────┘
```
In existing build system, _rules/config_ holds optional features based build
configuration variables like _INCLUDE\_\<FEATURE\>_, _ENABLE\_\<FEATURE\>_.
_rules/config.user_ can override default values of variables locally.

Note that behavior of the _INCLUDE\_<FEATURE\>_ and _ENABLE\_\<FEATURE\>_
variables are **not** consistent across features in existing build system

### Proposed Configuration layering

```
                         ┌─────────────────────────────────┐
                         │          rules/config           │
                         └─────────────────────────────────┘
                            │                            │
                  <SONIC_PROFILE>== NULL         <SONIC_PROFILE> != NULL
                            │                            │
                            │              ┌─────────────▼─────────────────┐
                            │              │  rules/config.<SONIC_PROFILE> │
                            │              └─────────────┬─────────────────┘
                            │                            │
                            └─────────────▼──────────────┘
                                          │
                       ┌──────────────────▼───────────────────┐
                       │          rules/config.user           │
                       │         (highest precedence)         │
                       └──────────────────────────────────────┘
```
The same flow used in _Makefile.work_ and _slave.mk_.

- *rules/config stays the default configuration file*
- **When $(SONIC_PROFILE) is unset**, preserve existing build flow to avoid any
  regression. Streamline usage of _INCLUDE\_\<FEATURE>_ with consistent
definition of <u>_whether to build_</u>. Add missing _ENABLE\_\<FEATURE\>_
variables with consistent definition of <u>_whether to enable feature at
boot_</u>.  New _AUTORESTART\_\<FEATURE\>_ and _DELAY\_\<FEATURE\>_ are added
and described further in this HLD

- **When $(SONIC_PROFILE) is set**, include _rules/config.\<SONIC_PROFILE>_
  with white-listed configuration variables initialized for each optional
feature
   ```bash
    INCLUDE_<FEATURE> = y
    ENABLE_<FEATURE> = y
    AUTORESTART_<FEATURE>=y
    DELAY_<FEATURE>=y
   ```
- **`rules/config.user` follows existing override behavior.** Local overrides
  continue to work as today and take highest precedence, i.e. overriding
_rules/config_ or _rules/config.\<SONIC_PROFILE\>_ as applicable.

### Passing SONIC_PROFILE

_rules/config.\<SONIC_PROFILE>_ is loaded by passing _SONIC_PROFILE_ from the
top-level `make` command:

```bash
# Build with ENTERPRISE profile
make SONIC_PROFILE=ENTERPRISE target/sonic-vs.img.gz

# Build with ENTERPRISE profile, override one variable
make SONIC_PROFILE=ENTERPRISE ENABLE_NAT=n target/sonic-vs.img.gz
```

_Build will **fail** for a non-existent _rules/config.\<SONIC_PROFILE\>_ file._

---
## High-Level Design

### Proposed Build Configuration Variables

This HLD proposes to use the following _four_ mandatory fields for each
optional docker feature. Each variable controls behavior as explained below:

| Variable | Existing | When it applies | What it controls |
|---|---|---|---|
| _INCLUDE\_\<FEATURE>_ | Yes | Build | Selects what goes into the image at build time |
| _ENABLE\_\<FEATURE>_ | Partially | Boot | Boot state — enabled or disabled at startup |
| _DELAY\_\<FEATURE\>_ | No | Boot | Start timing — immediate or delayed until ports are configured |
| _AUTORESTART\_\<FEATURE>_ | No | Boot | Recovery — restart container automatically on failure |

**1. INCLUDE_\<FEATURE>**

Build-time — whether the feature is **built and installed** in the image. When
`n`, the feature/docker is not built and completely absent in the image. Fixed
inconsistency where some docker images are compiled(but not installed in image)
even when _INCLUDE\_<FEATURE\>_ is set to `n`

**2. ENABLE_\<FEATURE\>**

Runtime — whether the feature **starts on boot**. Only applies when
_INCLUDE\_\<FEATURE>_=`y`. _ENABLE\_\<FEATURE\>_ was missing for most of the
features which is fixed by this HLD. Hard-coded boot state in
_init_cfg.json.j2_ is now replaced with this variable per feature.

**3. AUTORESTART_\<FEATURE\>**

Runtime — whether the container is **automatically restarted on failure**. It
is initialized in config for all optional features.  (_init_cfg.json_
autorestart field).

**4. DELAY_\<FEATURE\>**

Runtime — whether start is **delayed until after port configuration**
(_init_cfg.json_ delayed field). When `y`, the feature uses a systemd timer
instead of starting immediately at boot.

### Configuration files Changes

- **`rules/config`**

Stock defaults for optional features remain in `rules/config` and used when
_SONIC_PROFILE_ is unset. Eg:

 ```makefile
 ifndef SONIC_PROFILE
 INCLUDE_<FEATURE> = y|n
 ENABLE_<FEATURE> = y|n
 AUTORESTART_<FEATURE> = y|n
 DELAY_<FEATURE> = y|n
 endif
 ```

 Makefile.work and slave.mk will have following include layering

 ```makefile
 include rules/config
 ifneq ($(SONIC_PROFILE),)
 -include rules/config.$(SONIC_PROFILE)
 endif
 -include rules/config.user
 ```
- **rules/config.\<SONIC_PROFILE>**

Profile authors set all four variables for each feature they **want** in the
image. Omitted features from _rules/config.\<SONIC_PROFILE\>_ are treated as
disabled from compilation (i.e. _INCLUDE\_\<FEATURE>_=`n`)

 ```makefile
 INCLUDE_NAT = y
 ENABLE_NAT = n
 AUTORESTART_NAT = y
 DELAY_NAT = n
 ```
- **rules/config.user**

Features can be overridden by `rules/config.user` by setting any or all build
configurable variables per feature:

  ```makefile
  INCLUDE_NAT = n
  ```
  ```makefile
  INCLUDE_SNMP = y
  ENABLE_SNMP = n
  ```
### Fix Inconsistencies

The current `rules/config` and feature `.mk` files contain several categories
of inconsistency that prevent reliable profile overrides. This HLD proposes to
fix these inconsistencies to align with the deployment profiling scheme presented
here.

**1. Streamline INCLUDE\_ behavior**

_INCLUDE\_\<FEATURE\>_ existed for most of the features (controlling build and
install) but some features are still compiled even when _INCLUDE\_\<FEATURE>
set to `n`.

**2. Add missing ENABLE\_ variables**

Most features have only _INCLUDE\_\<FEATURE>_, with no corresponding
_ENABLE\_\<FEATURE>_ to control whether the container starts by default on boot.

**3. Runtime Feature Control via init_cfg.json.j2**

Each features.append() entry in _init_cfg.json.j2_ is a 4-tuple

```jinja
(feature_name, boot_state, delayed, autorestart)
```
The runtime state is currently hardcoded in _init_cfg.json.j2_ for
_boot\_state_, _delayed_ and _autorestart_

```jinja
{# Current init_cfg.json.j2 — boot state is hardcoded per feature #}
{%- if include_nat == "y" %}
  {% do features.append(("nat", "disabled", false, "enabled")) %}
{%- endif %}
```
which are now controlled by _ENABLE\_\<FEATURE>_, _DELAY\_\<FEATURE\>_ and
_AUTORESTART\_\<FEATURE>_ variables 

```jinja
{%- if include_nat == "y" %}
{% do features.append(("nat", feat_enable(enable_nat), feat_delay(delay_nat), feat_autorestart(autorestart_nat))) %}
{%- endif %}
```
### Preserve existing configuration variables

#### Preserve SYSTEM_EVENTD computation

EVENTD is a special case where _ENABLE\_SYSTEM\_EVENTD_ is dependent on
_BUILD\_REDUCE\_IMAGE\_SIZE_ as follows

| INCLUDE_SYSTEM_EVENTD| BUILD_REDUCE_IMAGE_SIZE | Boot State|
|---|---|---|
| Y| Y | Disabled|
| Y| N | Enabled|

Since both _INCLUDE\_SYSTEM\_EVENTD_ and _BUILD\_REDUCE\_IMAGE\_SIZE_ can be
overloaded by both _rules/config.\<SONIC_PROFILE>_ and _rules/config.user_, a
_config-eventd-defaults.mk_ is added

```Makefile
# rules/config-eventd-defaults.mk
ifndef ENABLE_SYSTEM_EVENTD
ifeq ($(BUILD_REDUCE_IMAGE_SIZE),y)
ENABLE_SYSTEM_EVENTD := n
else
ENABLE_SYSTEM_EVENTD := y
endif
endif
```
_Makefile.work_ and _slave.mk_ include _config-eventd-defaults.mk_ as follows

```Makefile
include rules/config
ifneq ($(SONIC_PROFILE),)
-include rules/config.$(SONIC_PROFILE)
endif
-include rules/config.user
include rules/config-eventd-defaults.mk
```
#### Preserve SONIC_INCLUDE pass-through

_SONIC_INCLUDE\_\<FEATURE\>_ variables are preserved in Makefile.work for
backward compatibility. 

   ```bash
   # Makefile.work -> slave.mk
    SONIC_INCLUDE_SYSTEM_GNMI=$(INCLUDE_SYSTEM_GNMI) \
     ... ... \
    make -f slave.mk
   ```
#### Preserve conditional checks in init_cfg.json.j2

Certain features have runtime conditional checks to decide whether to launch
docker at boot: _TEAMD_, _MUX_, _MACSEC_, _RESTAPI_, and _DHCP_RELAY_. For
example:

```jinja
{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT'] %}disabled{% else %}enabled{% endif %}
```
Such conditional checks are further guarded by proposed configuration variables

```jinja
{%- if include_teamd == "y" %}
  {% if enable_teamd == "y" %}
    {% do features.append(("teamd",
      "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT'] %}disabled{% else %}enabled{% endif %}",
      feat_delay(delay_teamd),
      feat_autorestart(autorestart_teamd))) %}
  {% else %}
    {% do features.append(("teamd", "disabled", feat_delay(delay_teamd), feat_autorestart(autorestart_teamd))) %}
  {% endif %}
{%- endif %}
```
### Canonical Feature Makefile Pattern

After migration, every docker feature's `.mk` file must follow this pattern:

```makefile
ifeq ($(INCLUDE_NAT), y)
SONIC_DOCKER_IMAGES += $(DOCKER_NAT)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_NAT)
endif

ifeq ($(AUTORESTART_NAT), y)
SONIC_AUTORESTART_DOCKER_IMAGES += $(DOCKER_NAT)
endif

ifeq ($(DELAY_NAT), y)
SONIC_DELAYED_DOCKER_IMAGES += $(DOCKER_NAT)
endif
```
## Default Build Configuration Variables - Zero Regression

Default _ENABLE_*_, _AUTORESTART_*_, and _DELAY_*_ values match what was
previously hardcoded in _init_cfg.json.j2_. A build **without** _SONIC_PROFILE_
therefore produces the same _init_cfg.json_ as today for wired features (zero
regression).

| Feature | _INCLUDE_*_ | _ENABLE_*_ | _AUTORESTART_*_ | _DELAY_*_ | _Boot state (stock build)_ |
|---|---|---|---|---|---|
| _SYSTEM_GNMI_ | _y_ | _y_ | _y_ | _y_ | _enabled_ |
| _SYSTEM_BMP_ | _y_ | _n_ | _y_ | _n_ | _disabled_ |
| _SYSTEM_EVENTD_ | _y_ | _derived*_ | _y_ | _n_ | _disabled_ |
| _SYSTEM_TELEMETRY_ | _n_ | _y_ | _y_ | _y_ | _enabled_ |
| _SYSTEM_OTEL_ | _y_ | _n_ | _y_ | _n_ | _disabled_ |
| _ICCPD_ | _n_ | _n_ | _y_ | _n_ | _disabled_ |
| _STP_ | _n_ | _n_ | _y_ | _n_ | _not in init_cfg FEATURE*_ |
| _SNMP_ | _y_ | _y_ | _y_ | _y_ | _enabled_ |
| _LLDP_ | _y_ | _y_ | _y_ | _y_ | _enabled_ |
| _SFLOW_ | _y_ | _n_ | _y_ | _y_ | _disabled_ |
| _MGMT_FRAMEWORK_ | _y_ | _y_ | _y_ | _y_ | _enabled_ |
| _RESTAPI_ | _n_ | _y_ | _y_ | _n_ | _conditional checks preserved_ |
| _NAT_ | _y_ | _n_ | _y_ | _n_ | _disabled_ |
| _DHCP_RELAY_ | _y_ | _y_ | _y_ | _n_ | _conditional checks preserved_ |
| _DHCP_SERVER_ | _n_ | _n_ | _y_ | _n_ | _disabled_ |
| _P4RT_ | _n_ | _n_ | _y_ | _n_ | _disabled_ |
| _MACSEC_ | _y_ | _n_ | _y_ | _n_ | _conditional checks preserved_ |
| _TEAMD_ | _y_ | _y_ | _y_ | _n_ | _conditional checks preserved_ |
| _ROUTER_ADVERTISER_ | _y_ | _y_ | _y_ | _n_ | _enabled_ |
| _MUX_ | _y_ | _y_ | _y_ | _n_ | _conditional checks preserved_ |

_ENABLE_SYSTEM_EVENTD_ is derived in _rules/config-eventd-defaults.mk_ when unset.

For STP, _SONIC_INCLUDE_STP_ was used instead of _INCLUDE_STP_. This HLD adds
required configuration variables in _rules/config_.

_conditional checks preserved_: Refer to [Preserve conditional checks in
init_cfg.json.j2](#preserve-conditional-checks-in-init_cfgjsonj2)

## Profile System
### Build Configuration Variable Combinations

Build configuration variables also support the following valid combinations:

| Profile setting | Build / install | init_cfg boot state |
|---|---|---|
| _INCLUDE\_\<FEATURE> = n_ | Not built, not in image | FEATURE absent |
| _INCLUDE\_\<FEATURE> = y_ + _ENABLE\_\<FEATURE> = y_ | Built and installed | Enabled on boot |
| _INCLUDE\_\<FEATURE> = y_ + _ENABLE\_\<FEATURE> = n_ | **Built and installed** | **Disabled on boot** |

### Listing Available Profiles

Profile files follow the naming convention _rules/config.<PROFILE_NAME>_. To
list available profiles:

```bash
ls rules/config.* | grep -v config.user
```
### Inspecting profile feature settings

Profile authors and reviewers need a quick way to see, for a given
_SONIC_PROFILE_, which optional features are **built into the image** and which
will **start enabled on boot** — without running a full image build. This can
be done using

```bash
# Stock defaults
make show-sonic-profile

# Named profile
make SONIC_PROFILE=DATACENTER show-sonic-profile
```
## Adding a New Optional Docker Feature

Every new optional docker feature can be independently added in rules/config
without any obligation to add in rules/config.<SONIC_PROFILE>. However
community can consciously decide to add a particular feature to some or all
deployment profiles.

### Checklist for a new feature

Replace _<FEATURE>_ with the canonical name used in existing variables (e.g.
_NAT_, _SYSTEM_GNMI_, _STP_).

#### 1. rules/config

Add the four variables as follows:
```makefile
ifndef SONIC_PROFILE
INCLUDE_<FEATURE> = y|n
ENABLE_<FEATURE> = y|n
AUTORESTART_<FEATURE> = y|n
DELAY_<FEATURE> = y|n
endif
```
#### 2. rules/config.SONIC_PROFILE

For each _rules/config.\<SONIC_PROFILE>_, define all four variables for each
included feature. Omitted features stay at profile-mode with implicit `n`;
_rules/docker-*.mk_ does not build them.

#### 3. Build and runtime wiring

| Area | Action |
|---|---|
| _rules/docker-\<feature>.mk_ | Gate _SONIC_DOCKER_IMAGES_ / install lists on _ifeq ($(INCLUDE\_\<FEATURE>), y)_ |
| _Makefile.work_ | Export _INCLUDE_<FEATURE>_ (and _ENABLE_ / _AUTORESTART_ / _DELAY_ if used by templates) into the slave build; |
| _slave.mk_ | export lowercase variables for _init_cfg.json.j2_ (e.g. _export enable\_\<feature>=..._) where applicable |
| _files/build_templates/init_cfg.json.j2_ | Add new feature entry in feature.append() |
