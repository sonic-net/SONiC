# Design to store the firmware version info to the STATE DB

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [Overview](#overview)
  * [1. Requirements ](#1-requirements)
  * [2. Architeture Design](#2-architecture-design)
  * [3. High Level Design](#3-high-level-design)
  * [4. DesignSAI API](#designsai-api)
  * [5. Configuration and management](#configuration-and-management)
  * [6. Memory Consumption](#memory-consumption)
  * [7. Testing](#testing)

# Revision

| Rev   | Date          | Author               | Change Description                   |
| :---: | :-----------: | :------------------: | -------------------------------------|
  0.1   |  08/11/2025    |  Nishanth           |  Initial draft — populate STATE_DB with firmware-version per component|

# Scope

- This HLD describes adding component firmware (FPD) version information into SONiC's STATE_DB during chassis initialization. 
- The data will be written under a new COMPONENT_INFO table in STATE_DB, keyed by component name and storing a firmware-version field. 
- This is a read-only population step performed by sonic-chassisd at chassis DB init.

# Definitions/Abbreviations

| **Term**         | **Meaning**                                                                                           |
|------------------|-------------------------------------------------------------------------------------------------------|
| SONiC            | Software for Open Networking in the Cloud|
| FPD              | Field Programmable Device (firmware-programmable device)|
| STATE_DB         | Redis DB holding runtime state (in this repo’s deployments typically DB 6)|
| CONFIG_DB        | Redis DB for persistent configuration|
| COMPONENT_INFO   | New table name in STATE_DB to hold component firmware info|
| sonic-chassisd   | SONiC daemon that initializes / monitors chassis platform data|
| platform_chassis | Platform API object that enumerates chassis components|
| UT               | Unit/Test verification steps (redis-dump example provided)|

# Overview

### Problem
Telemetry need an easy, consistent place in SONiC to read current firmware versions of chassis components (BIOS, FPGAs, CPLDs, SSD, TAM, etc.). Previously, it had to be queried via platform APIs or vendor-specific interfaces.

### Solution 
Populate STATE_DB with COMPONENT_INFO|<component-name> hash entries during chassis DB initialization. 
Each hash will contain firmware-version: `<version-string>`.
This makes firmware versions available to telemetry, CLI tooling, and third-party consumers via the standard DB reading mechanisms.

### Implementation point 
The change will be implemented in sonic-chassisd/scripts/chassis_db_init (a Python script that runs during chassis init) and will use platform_chassis.get_all_components() + comp.get_firmware_version() to build and set the DB entries.

# 1. Requirements

#### Functional
On chassis DB init, populate STATE_DB with COMPONENT_INFO|<component> entries for all components returned by platform_chassis.get_all_components().
Each entry must contain field firmware-version with the component’s firmware string (e.g., "1.8").
If a component has no firmware version available, store an empty string or unknown (implementation detail below).
Multiple consumers (telemetry, scripts, CLI tooling) should be able to read these entries without calling platform API.

#### Non-functional
Minimal boot-time impact.
No growing memory usage while feature is disabled.
Backwards compatible (no breaking changes to existing tables or keys).

#### Exemptions / Not supported
This HLD does not introduce write-back of firmware versions to Config DB.
No CLI or YANG changes are included.

# 2. Architecture Design

#### How this fits existing SONiC architecture
This is an out-of-band, read-only population of STATE_DB performed by sonic-chassisd during chassis DB initialization `(script path: sonic-chassisd/scripts/chassis_db_init)`.
No existing architecture modules (SWSS, syncd, SAI) need changes. The STATE_DB is already the place for runtime state and is read by telemetry and other tools.
The sonic-chassisd daemon will continue to run as before with an additional initialization routine that creates/updates the COMPONENT_INFO table.

#### Application Extension
This is a built-in change to sonic-chassisd (not an App Extension).

# 3. High-Level Design

#### Built-in or Extension
Built-in SONiC feature: modification to sonic-chassisd.

#### Modules / Sub-modules modified
sonic-chassisd/scripts/chassis_db_init — script updated to populate COMPONENT_INFO in STATE_DB.

Minor dependency on platform API: platform_chassis.get_all_components() and component interface methods.

#### Repositories changed
sonic-platform/sonic-chassisd (or sonic-buildimage pack that contains sonic-chassisd) — exact repo path matching SONiC tree where sonic-chassisd lives.

#### Module / sub-module interfaces and dependencies
Dependency: platform API must provide:

platform_chassis.get_all_components() -> list of component objects

comp.get_name() -> component name string

comp.get_firmware_version() -> version string or None

sonic-chassisd will use swsscommon.Table(state_db, COMPONENT_INFO_TABLE) to write entries.

#### SWSS and Syncd changes
None. This feature only writes to STATE_DB and does not require changes in SWSS or syncd.

#### DB and Schema changes
New logical table in STATE_DB: COMPONENT_INFO

Key format: COMPONENT_INFO|<component_name>

Value (hash fields):

firmware-version : string (e.g., "1.8")

Persistence: STATE_DB entries are runtime and expected to be ephemeral (no change to Config DB). If desired, an expiry could be added; current design does not require TTL.

Validate DB index: example UT uses DB 6 (commonly STATE_DB). The HLD assumes STATE_DB is mapped to DB index 6 — use system config to verify in your deployment.

#### Linux dependencies and interface
Requires Python runtime used by sonic-chassisd scripts.

Requires swsscommon Python bindings to operate on Redis.

#### Warm reboot requirements/dependencies
No changes required for warm reboot persistence beyond existing warmboot behavior.

Because entries are runtime-state in STATE_DB, they are expected to be repopulated on init after warmboot if chassis_db_init runs during warmboot. If chassis_db_init is skipped during warmboot, consider adding a warmboot-aware path to repopulate the table.

#### Fastboot requirements/dependencies
Minimal impact. Running the script adds a small number of Redis writes; it should not be on the critical fastboot path. If chassis_db_init runs as part of boot-critical tasks, ensure the operation is non-blocking or runs early in parallel if necessary.

#### Scalability and performance impact
Number of writes = number of chassis components (small, typically < 20). CPU and Redis load negligible.

Read traffic may increase as telemetry consumers read these keys but this is expected and minimal.

#### Memory requirements
Each hash entry is tiny (a few bytes per component). Negligible memory use.

#### Docker dependency
No new Docker containers. Changes are inside sonic-chassisd container/process.

#### Build dependency
Include the updated script in sonic-chassisd package; standard build for that package. No external build dependencies.

#### Management interfaces
SNMP: No changes.

CLI: No changes by default. Operators can use existing DB inspection utilities (e.g., redis-dump, sonic-db-cli) to read STATE_DB entries.

RESTAPI / gNMI: No changes required in this HLD. Telemetry consumers that read STATE_DB can surface this info.

#### Serviceability and Debug
Logging: sonic-chassisd should log an informational message for each component written to DB and log warnings if firmware version is missing/unavailable.

Example logs: INFO: wrote COMPONENT_INFO|IOFPGA firmware-version=1.8

WARNING: component Aikido returned no firmware-version

Tracing: add debug-level trace for the full list returned by get_all_components() when debug enabled.

Counters: Not required.

Verification: UT step uses redis-dump -d 6 -y -k "COMPONENT_INFO*".

#### Platform specificity
Platform vendors must implement get_all_components() and get_firmware_version() for their chassis platform if not already present. If a platform does not support firmware query for a component, return empty or None and log appropriately.

# 4. DesignSAI API
No change to SAI APIs is required for this feature. The design uses platform chassis APIs (platform-specific) and writes to STATE_DB only.

# 5. Configuration and management

####  Manifest
No manifest is required.

####  CLI/YANG model Enhancements
No CLI or YANG changes as part of this HLD.

####  Config DB Enhancements
No Config DB changes required.

# 6. Memory Consumption
   - No persistent memory usage while the feature is disabled.
   - While enabled, memory cost is the size of the small hash entries in STATE_DB — negligible.

# 7. Testing
Run on DUT to list keys and contents in STATE_DB:

Example: dump STATE_DB (DB 6) keys matching COMPONENT_INFO
`redis-dump -d 6 -y -k "COMPONENT_INFO*"`

#### Example expected output:
```
root@sonic:/home/cisco# redis-dump -d 6 -y -k "COMPONENT_INFO*"
{
  "COMPONENT_INFO|Aikido": {
    "expireat": 1749034477.8798983,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "1.7"
    }
  },
  "COMPONENT_INFO|BIOS": {
    "expireat": 1749034477.8799129,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "0-4"
    }
  },
  "COMPONENT_INFO|IOFPGA": {
    "expireat": 1749034477.8799255,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "1.8"
    }
  },
  "COMPONENT_INFO|SSD": {
    "expireat": 1749034477.87991,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "0.2"
    }
  },
  "COMPONENT_INFO|TAM": {
    "expireat": 1749034477.879916,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "2.7"
    }
  },
  "COMPONENT_INFO|iocpld0": {
    "expireat": 1749034477.8799045,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "0.2"
    }
  },
  "COMPONENT_INFO|iocpld1": {
    "expireat": 1749034477.8799193,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "0.2"
    }
  },
  "COMPONENT_INFO|pwrcpld": {
    "expireat": 1749034477.8799224,
    "ttl": -0.001,
    "type": "hash",
    "value": {
      "firmware-version": "0.11"
    }
  }
}

```




