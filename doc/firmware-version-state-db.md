# Design to store the firmware version info to the STATE DB
Design to store the firmware version info to the STATE DB

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [Overview](#overview)
  * [1. Requirements ](#1-requirements)
  * [2. Architeture Design](#2-architecture-design)
  * [DesignSAI API](#designsai-api)
  * [Configuration and management](#configuration-and-management)
  * [Memory Consumption](#memory-consumption)
  * [Testing](#testing)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision

| Rev   | Date          | Author               | Change Description                  |
| :---: | :-----------: | :------------------: | ----------------------------------- |
| 0.1   | 08/11/2025    | Nishanth             | Initial draft — populate STATE_DB   |
                                                  with firmware-version per component

# Scope

This HLD describes adding component firmware (FPD) version information into SONiC's STATE_DB during chassis initialization. 
The data will be written under a new COMPONENT_INFO table in STATE_DB, keyed by component name and storing a firmware-version field. 
This is a read-only population step performed by sonic-chassisd at chassis DB init.

# Definitions/Abbreviations

SONiC — Software for Open Networking in the Cloud
FPD — Field Programmable Device (firmware-programmable device)
STATE_DB — Redis DB holding runtime state (in this repo’s deployments typically DB 6)
CONFIG_DB — Redis DB for persistent configuration
COMPONENT_INFO — New table name in STATE_DB to hold component firmware info
sonic-chassisd — SONiC daemon that initializes / monitors chassis platform data
platform_chassis — Platform API object that enumerates chassis components
UT — Unit/Test verification steps (redis-dump example provided)

# Overview

Problem: 
Telemetry need an easy, consistent place in SONiC to read current firmware versions of chassis components (BIOS, FPGAs, CPLDs, SSD, TAM, etc.). Previously, it had to be queried via platform APIs or vendor-specific interfaces.

Solution: 
Populate STATE_DB with COMPONENT_INFO|<component-name> hash entries during chassis DB initialization. Each hash will contain firmware-version: <version-string>. 
This makes firmware versions available to telemetry, CLI tooling, and third-party consumers via the standard DB reading mechanisms.

Implementation point: 
The change will be implemented in sonic-chassisd/scripts/chassis_db_init (a Python script that runs during chassis init) and will use platform_chassis.get_all_components() + comp.get_firmware_version() to build and set the DB entries.

# 1. Requirements

Functional:
On chassis DB init, populate STATE_DB with COMPONENT_INFO|<component> entries for all components returned by platform_chassis.get_all_components().
Each entry must contain field firmware-version with the component’s firmware string (e.g., "1.8").
If a component has no firmware version available, store an empty string or unknown (implementation detail below).
Multiple consumers (telemetry, scripts, CLI tooling) should be able to read these entries without calling platform API.

Non-functional:
Minimal boot-time impact.
No growing memory usage while feature is disabled.
Backwards compatible (no breaking changes to existing tables or keys).

Exemptions / Not supported:
This HLD does not introduce write-back of firmware versions to Config DB.
No CLI or YANG changes are included.

# 2. Architecture Design

How this fits existing SONiC architecture
This is an out-of-band, read-only population of STATE_DB performed by sonic-chassisd during chassis DB initialization (script path: sonic-chassisd/scripts/chassis_db_init).
No existing architecture modules (SWSS, syncd, SAI) need changes. The STATE_DB is already the place for runtime state and is read by telemetry and other tools.
The sonic-chassisd daemon will continue to run as before with an additional initialization routine that creates/updates the COMPONENT_INFO table.

Application Extension
This is a built-in change to sonic-chassisd (not an App Extension).


#  DesignSAI API
No change to SAI APIs is required for this feature. The design uses platform chassis APIs (platform-specific) and writes to STATE_DB only.

#  Configuration and management

##  Manifest
No manifest is required.

##  CLI/YANG model Enhancements
No CLI or YANG changes as part of this HLD.

##  Config DB Enhancements
No Config DB changes required.

#  Memory Consumption
   - No persistent memory usage while the feature is disabled.
   - While enabled, memory cost is the size of the small hash entries in STATE_DB — negligible.

#  Testing
Run on DUT to list keys and contents in STATE_DB:

Example: dump STATE_DB (DB 6) keys matching COMPONENT_INFO
redis-dump -d 6 -y -k "COMPONENT_INFO*"

Example expected output:

{
  "COMPONENT_INFO|Aikido": { "type":"hash", "value": { "firmware-version": "1.7" } },
  "COMPONENT_INFO|BIOS":   { "type":"hash", "value": { "firmware-version": "0-4" } },
  "COMPONENT_INFO|IOFPGA": { "type":"hash", "value": { "firmware-version": "1.8" } }
}







