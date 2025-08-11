# Design to store the firmware version info to the STATE DB
Design to store the firmware version info to the STATE DB


# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [Overview](#overview)
  * [1. Requirements ](#1-requirements)
  * [2. Functional Description](#2-functional-description)
  * [3. Design](#3-design)	  
  * [4. Flow Diagrams](#4-flow-diagrams)
  * [5. Serviceability and Debug](#5-serviceability-and-debug)
  * [6. Warm Boot Support](#6-warm-boot-support)
  * [7. Scalability](#7-scalability)
  * [8. Unit Test](#8-unit-test)

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
Problem: telemetry/monitoring consumers and administrators need an easy, consistent place in SONiC to read current firmware versions of chassis components (BIOS, FPGAs, CPLDs, SSD, TAM, etc.). Previously, consumers had to query platform APIs or vendor-specific interfaces.

Solution: populate STATE_DB with COMPONENT_INFO|<component-name> hash entries during chassis DB initialization. Each hash will contain firmware-version: <version-string>. This makes firmware versions available to telemetry, CLI tooling, and third-party consumers via the standard DB reading mechanisms.

Implementation point: the change will be implemented in sonic-chassisd/scripts/chassis_db_init (a Python script that runs during chassis init) and will use platform_chassis.get_all_components() + comp.get_firmware_version() to build and set the DB entries.

# 1 Requirements
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
