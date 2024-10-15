# SYNCD Optimization for SONiC

## Table of Contents

- [SYNCD Optimization for SONiC](#syncd-optimization-for-sonic)
  - [Table of Contents](#table-of-contents)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Terminology](#terminology)
    - [Overview](#overview)
    - [Requirements](#requirements)
    - [Architecture Design](#architecture-design)
    - [Implementation](#implementation)
	  - [sonic-utilities](#sonic-utilities)
	  - [SWSS](#SWSS)
	  - [SWSS-common](#SWSS-common)
	  - [SAI-Redis](#SAI-Redis)
      - [SAI API](#sai-api)
      - [YANG model changes](#yang-model-changes)
      - [CLI](#cli)
	- [Warmboot and Fastboot Design Impact]
	- [Testing Requirements/Design]
	- [Unit Test cases]
	- [System Test cases]

### Revision

| Rev |   Date   |          Author           | Change Description |
| :-: | :------: | :-----------------------: | ------------------ |
| 0.1 | 10/15/24 | Aviram Dali (**Marvell**) | Initial Draft      |

### Scope

The scope of this document is to design the handling of taking a SAI dump during show techsupport call 

### Terminology

| Term      | Definition                              |
| --------- | --------------------------------------- |
| ASIC      | Application Specific Integrated Circuit |
| SYNCD     | ASIC Synchronization Service            |
| SAI       | Switch Abstraction Interface            |
| API       | Application Programmable Interface      |
| SWSS      | Switch State Service                    |


### Overview
SAI dump file usually includes, SDK info and configuration , SAI stats, capture of SAI lower layer states like registers vales etc...
Currently, the SAI dump file is generated only during SAI failures by executing a dedicated executable named "saidump", which linkage with the SAI lib during initialization it creates a new switch in redundant mode. This new feature allows users to generate a SAI debug dump file using command such as show tech-support not necessarily during failure, and the dump file will be generated directly from the syncd process. 


### Requirements
Each vendor can add to its specific implantation part of the `show techsupport` a simple call to a new API to generate the SAI debug dump file.

### Architecture Design

1. A user command, such as `show techsupport` triggers the `generate_sai_dump` bash script, which writes the file name to the STATE DB.
2. A new orchestration agent, `DbgGenDumpOrch`, is triggered to handle the request.
3. `DbgGenDumpOrch` writes the file name to the ASIC DB and sets a new operation `REDIS_ASIC_STATE_COMMAND_DBG_GEN_DUMP` for syncd.
4. Syncd calls the global SAI API `dbgGenerateDump` to generate the debug dump file, which is saved in syncd's file system.
5. Syncd sends a reply back to `DbgGenDumpOrch`.
6. `DbgGenDumpOrch` analyzes the response.
7. `DbgGenDumpOrch` updates the result in the STATE DB.
8. The user command retrieves the result.
9. The debug dump file is pulled on success.

The below diagram explains the sequence when a SAI failure happens
![](/images/generate_debug_dump_file.JPG)


### Implementation

#### sonic-utilities
Add a new script to the Debian file system named `gen_sai_dbg_dump_lib.sh`, which includes the `generate_sai_dump` API. This function takes the desired file name as an argument and initiates the generation of a SAI debug dump file by performing the following steps:

- Set the file name in the STATE DB to trigger the dump generation.
- Poll the STATE DB for the result with timeout of 10 seconds.
- Delete the relevant entries from the STATE DB after triggering the dump file.
- Ensure that the generated file exists.


**Show Techsupport**  
- Introduced a new generic API, `generate_sai_dbg_dump_file`, in `generate_dump.sh` (invoked by the "show techsupport" command) to create a debug dump file. This change allows each vendor to call this API in their vendor-specific implementation
- After the file is generated, it is moved into the techsupport folder.

#### SWSS
- A new orchestration agent, `DbgGenDumpOrch`, has been introduced, which is triggered by updates in the STATE DB.
- It updates syncd by writing to the ASIC DB and waits for a response. Once received, it writes the result back to the STATE DB, allowing the calling application to retrieve the file.

#### SWSS-common
- add new tables name 

#### SAI-Redis
- Implemented a new global API, `dbgGenerateDump`, in the `SaiInterface` class, ensuring that all derived classes provide the corresponding implementation, including the vendor SAI class to call the global API `sai_dbg_generate_dump`.
- Added a new syncd operation, `REDIS_ASIC_STATE_COMMAND_DBG_GEN_DUMP`, which invokes the SAI API to generate the debug dump file.

#### SAI API
There are currently no new SAI APIs required for this feature.

#### YANG model changes
No Changes.

#### CLI
No changes.

### Warmboot and Fastboot Design Impact
There is no impact on warmboot or fastboot

### Testing Requirements/Design

#### Unit Test cases

#### System Test cases
Verify if the dump in techsupport contains the SAI failure dump is collected.

