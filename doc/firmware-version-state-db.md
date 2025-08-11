# Design to store the firmware version info to the STATE DB
Design to store the firmware version info to the STATE DB


# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# 1 Revision

| Rev   | Date          | Author               | Change Description                  |
| :---: | :-----------: | :------------------: | ----------------------------------- |
| 0.1   | 08/11/2025    | Nishanth             | Initial draft — populate STATE_DB   |
|       |               |                      |  with firmware-version per component|


# 2 Scope

This HLD describes adding component firmware (FPD) version information into SONiC's STATE_DB during chassis initialization. 
The data will be written under a new COMPONENT_INFO table in STATE_DB, keyed by component name and storing a firmware-version field. 
This is a read-only population step performed by sonic-chassisd at chassis DB init.

