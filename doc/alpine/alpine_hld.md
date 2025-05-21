# ALPINE High Level Design

## Table of Contents
## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations]
- [Overview]
- Requirements
- Architecture Design
- High-Level Design
  * Alpine Virtual Switch (AVS)
    + SwitchStack Container
    + ASIC Simulation Container
    + Ports
    + Why 2-containers?
  * Alpine KNE Deployment (AKD)
    + Nodes
    + Links
- SAI API
- Configuration and management
- Warmboot and Fastboot Design Impact
- Memory Consumption
- Restrictions/Limitations
- Testing Requirements/Design
- Open/Action items

## 1. Revision
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
|v0.1 |05/01/2019  |Padmanabhan Narayanan | Initial version
|v0.2 |05/20/2019  |Padmanabhan Narayanan | Updated based on internal review comments
|v0.3 |06/11/2019  |Padmanabhan Narayanan | Update CLIs, remove sflowcfgd
|v0.4 |06/17/2019  |Padmanabhan Narayanan | Add per-interface configurations, counter mode support and <br /> unit test cases. Remove genetlink CLI
|v0.5 |07/15/2019  |Padmanabhan Narayanan | Update CLI and DB schema based on comments from InMON : <br> Remove max-datagram-size from collector config <br/>Add CLI for counter polling interval <br/>Remvoe default header-size <br/>Add "all" interfaces option <br/> Separate CLI to set agent-id<br/>
|v1.0 |09/13/2019  |Sudharsan | Updating sequence diagram for various CLIs
|v1.1 |10/23/2019  |Padmanabhan Narayanan | Update SAI section to use SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME instead of ID. Note on genetlink creation. Change admin_state values to up/down instead of enable/disable to be consistent with management framework's sonic-common.yang.
|v1.2 |03/07/2021  | Garrick He | Add VRF support and fix interface admin-status output.
|v1.3 |01/24/2023  | Rajkumar (Marvell) | Add Egress Sflow support.

Initial version

Scope
This document captures the high-level design of an Alpine Virtual Switch (AVS). AVS is part of ALPINE - a switchstack simulation framework which also consists of a deployment model (AKD).
