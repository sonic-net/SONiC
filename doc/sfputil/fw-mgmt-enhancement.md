# Transceiver Firmware Management Enhancement

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
- [14. Open/Action Items](#14-openaction-items)
- [Appendix A: References](#appendix-a-references)
- [Appendix B: Example Output](#appendix-b-example-output)
- [Appendix C: Command Reference Quick Guide](#appendix-c-command-reference-quick-guide)

### 1. Revision

| Rev | Date       | Author        | Change Description                                  |
|-----|------------|---------------|-----------------------------------------------------|
| 0.1 | 2026-03-18 | Rohit Sharma  | Initial version                                     |
| 0.2 | 2026-05-18 | Rohit Sharma  | Addressed review comments                           |

### 2. Scope

This document describes the enhancement to the `sfputil` command-line utility to support firmware management operations for optical transceivers in SONiC. The enhancement adds filtering capabilities to both firmware version display and firmware upgrade commands, enabling operators to efficiently manage firmware across multiple transceivers based on interface lists or vendor part numbers.

This design is a built-in SONiC feature that extends the existing `sonic-utilities` package, specifically the `sfputil` CLI tool.

### 3. Definitions/Abbreviations

| Term    | Meaning                                            |
|---------|----------------------------------------------------|
| SFP     | Small Form-factor Pluggable transceiver            |
| QSFP    | Quad Small Form-factor Pluggable transceiver       |
| CMIS    | Common Management Interface Specification          |
| CDB     | Command Data Block (CMIS firmware update mechanism)|
| PN      | Part Number                                        |
| HLD     | High-Level Design                                  |
| CLI     | Command Line Interface                             |

### 4. Overview

Transceiver firmware management is a critical operational task in modern data center networks. As networks scale, managing firmware updates for hundreds or thousands of transceivers becomes increasingly challenging. This enhancement addresses this operational challenge by introducing advanced filtering and firmware upgrade capabilities to the `sfputil` utility.

The enhancement provides three key capabilities:
1. **Filtered firmware version display**: View firmware versions for specific subsets of transceivers
2. **Multi-transceiver firmware download**: Download firmware to multiple transceivers simultaneously based on interface lists or vendor part numbers without automatic activation
3. **Multi-transceiver firmware upgrade**: Upgrade firmware for multiple transceivers simultaneously based on interface lists or vendor part numbers

This feature integrates seamlessly with the existing SONiC platform architecture and leverages the established Platform API for transceiver management.

### 5. Requirements

This section lists all the requirements for the transceiver firmware management enhancement.

#### 5.1. Functional Requirements

1. **Interface List Filtering**: Support filtering operations by comma-separated list of interface names and ranges
2. **Vendor Part Number Filtering**: Support filtering operations by vendor part number(s)
3. **Tabular Display**: Provide compact tabular output format for firmware version information
4. **Concurrent Download**: Support concurrent firmware download operations across multiple transceivers without automatic activation
5. **Concurrent Upgrade**: Support concurrent firmware upgrade operations across multiple transceivers
6. **Progress Tracking**: Display download/upgrade progress for multi-port operations with remaining time estimation
7. **Error Handling**: Gracefully handle errors and provide clear feedback for failed operations
8. **Backward Compatibility**: Maintain compatibility with existing single-port operations

#### 5.2. Non-Functional Requirements

1. **Performance**: Leverage parallel processing for multi-port operations to minimize total upgrade time
2. **Usability**: Provide clear, intuitive command-line interface consistent with existing SONiC CLI patterns
3. **Observability**: Provide detailed status information before and after operations, with real-time progress and remaining time estimation
4. **Scalability**: Support operations on hundreds of transceivers simultaneously

### 6. Architecture Design

This section covers the changes required in the SONiC architecture. The enhancement builds upon the existing `sfputil` architecture and does not introduce new system components or modify the core SONiC architecture. It extends the existing CLI framework with additional filtering and parallel operation capabilities.

#### 6.1. System Architecture Overview

The feature is a built-in SONiC enhancement that modifies the `sonic-utilities` repository. No changes are required to the SONiC Application Extension infrastructure.

#### 6.2. Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     sfputil CLI                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  show fwversion [-i] [-p] [-t]                         │ │
│  │  firmware download [-i] [-p]                           │ │
│  │  firmware upgrade [-i] [-p]                            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Filtering & Selection Logic                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  - Parse interface lists                               │ │
│  │  - Match vendor part numbers                           │ │
│  │  - Validate port presence                              │ │
│  │  - Transceiver Deduplication                           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Firmware Download/Upgrade Logic                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ThreadPoolExecutor ()                                 │ │
│  │  - Concurrent firmware downloads                       │ │
│  │  - Summary status line                                 │ │
│  │  - Remaining time estimation                           │ │
│  │  - Status aggregation                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Platform API Layer                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  - get_transceiver_info()                              │ │
│  │  - get_module_fw_info()                                │ │
│  │  - get_module_fw_mgmt_feature()                        │ │
│  │  - cdb_start_firmware_download()                       │ │
│  │  - cdb_firmware_download_complete()                    │ │
│  │  - cdb_run_firmware()                                  │ │
│  │  - cdb_commit_firmware()                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 6.3. Repositories Modified

- **sonic-utilities**: Main repository containing the `sfputil` CLI tool
  - Modified files: `sfputil/main.py` (CLI command definitions and implementation)

#### 6.4. Module Dependencies

- **Platform API**: Existing dependency for transceiver hardware access
- **Click**: CLI framework (existing dependency)
- **concurrent.futures**: Python standard library for parallel processing
- **threading**: Python standard library for thread-safe status tracking
- **enlighten**: Progress bar library for visual feedback

### 7. High-Level Design

This section covers the high-level design of the feature enhancement.

#### 7.1. Feature Type

This is a built-in SONiC feature that extends the existing `sfputil` CLI utility.

#### 7.2. Modules and Sub-modules Modified

- **sfputil CLI module** (`sonic-utilities/sfputil/main.py`):
  - Enhanced `show fwversion` command with filtering options
  - Added `firmware download` command with multi-port support
  - Enhanced `firmware upgrade` command with multi-port support
  - Added filtering and selection logic
  - Added parallel processing engine for concurrent operations
  - Added helper functions for parallel transceiver info and firmware info retrieval

#### 7.3. CLI Command Enhancements

##### 7.3.1. Firmware Version Display Enhancement

**Command**: `sfputil show fwversion`

**New Options**:
- `-t`: Display output in compact tabular format
- `-i <INTERFACE_LIST>`: Filter by comma-separated interface names and ranges
- `-p <PART_NUMBER_LIST>`: Filter by comma-separated vendor part numbers

**Usage Examples**:
```bash
# Display firmware version for all transceivers in tabular format
sudo sfputil show fwversion -t

# Display firmware version for specific interfaces
sudo sfputil show fwversion -i Ethernet0,Ethernet4,Ethernet8

# Display firmware version for an interface range (range expanded to all matching present ports)
sudo sfputil show fwversion -i Ethernet16-80 -t

# Display firmware version using a mix of single interfaces and ranges
sudo sfputil show fwversion -i Ethernet0,Ethernet4,Ethernet16-80 -t

# Display firmware version for all transceivers with specific part number
sudo sfputil show fwversion -p ALPHA123456 -t

# Combine filters
sudo sfputil show fwversion -i Ethernet0,Ethernet4 -t
```

##### 7.3.2. Firmware Download Enhancement

**Command**: `sfputil firmware download`

**New Options**:
- `-i <INTERFACE_LIST> <FILEPATH>`: Download firmware for comma-separated interface list with specified firmware file. The list supports interface range syntax (e.g., `Ethernet16-80`) that can be intermixed with single interface entries
- `-p <PART_NUMBER_LIST> <FILEPATH>`: Download firmware for all ports matching vendor part number with specified firmware file

Both `-i` and `-p` can be specified multiple times to target different groups with different firmware files.

**Usage Examples**:
```bash
# Download firmware for specific interfaces
sudo sfputil firmware download -i Ethernet0,Ethernet4,Ethernet8 /path/to/firmware.bin

# Download firmware using an interface range (range expanded to all matching present ports)
sudo sfputil firmware download -i Ethernet16-80 /path/to/firmware.bin

# Download firmware using a mix of single interfaces and ranges
sudo sfputil firmware download -i Ethernet0,Ethernet4,Ethernet16-80 /path/to/firmware.bin

# Download firmware for all transceivers with specific part number
sudo sfputil firmware download -p Deltaxxxxxxxxxx004 /path/to/firmware_v1.2.3.bin

# Multiple vendor part numbers with different firmware files
sudo sfputil firmware download \
  -p Deltaxxxxxxxxxx004 IJKL_Deltaxxxxxxxxxx004_0101_0301.bin \
  -p Deltaxxxxxxxxxx005 IJKL_Deltaxxxxxxxxxx005_0103_0303.bin \
  -p Epsilonyyyyyyyyy06 MNOP_Epsilonyyyyyyyyy06-VFF_5.bin \
  -p Epsilonyyyyyyyyy07 MNOP_Epsilonyyyyyyyyy07_VFF.2.bin
```

**Download Process Flow**:
```
1. Parse and validate input parameters
2. Identify target ports based on filters; reject overlapping groups
   with conflicting firmware files (see Section 7.5.1)
3. Verify CMIS firmware-management capability per port via
   get_module_fw_mgmt_feature(); exclude unsupported ports with a
   per-port reason and proceed with the rest
4. Display pre-download status
5. Execute parallel firmware download operations per port:
   a. cdb_start_firmware_download()
   b. Download firmware payload to transceiver
   c. cdb_firmware_download_complete() to verify completion
   d. On ANY failure in steps a-c, issue the CDB Abort command to
      return the module to an idle state before reporting the failure.
      This prevents the module from being left in an indeterminate
      "download in progress" state that would block subsequent retries.
      Reference: CMIS_and_C-CMIS_support_for_ZR.md
6. Display failure cause table for any failed ports (stage, status
   code, decoded reason, recovery hint)
7. Display post-download status
8. Report final results
```

**Key Differences from Upgrade**:
- Download command only performs the firmware download step (CDB download)
- Does NOT automatically run/activate or commit the new firmware
- Operator must manually activate and commit firmware using separate commands if desired
- Useful for staged firmware updates where download and activation should be separated

##### 7.3.3. Firmware Upgrade Enhancement

**Command**: `sfputil firmware upgrade`

**New Options**:
- `-i <INTERFACE_LIST> <FILEPATH>`: Upgrade firmware for comma-separated interface list with specified firmware file. The list supports interface range syntax (e.g., `Ethernet16-80`) that can be intermixed with single interface entries
- `-p <PART_NUMBER_LIST> <FILEPATH>`: Upgrade firmware for all ports matching vendor part number with specified firmware file

Both `-i` and `-p` can be specified multiple times to target different groups with different firmware files.

**Usage Examples**:
```bash
# Upgrade firmware for a single port (existing functionality, verbose mode)
sudo sfputil firmware upgrade Ethernet0 /path/to/firmware.bin

# Upgrade firmware for specific interfaces
sudo sfputil firmware upgrade -i Ethernet0,Ethernet4,Ethernet8 /path/to/firmware.bin

# Upgrade firmware using an interface range (range expanded to all matching present ports)
sudo sfputil firmware upgrade -i Ethernet16-80 /path/to/firmware.bin

# Upgrade firmware using a mix of single interfaces and ranges
sudo sfputil firmware upgrade -i Ethernet0,Ethernet4,Ethernet16-80 /path/to/firmware.bin

# Upgrade firmware for all transceivers with specific part number
sudo sfputil firmware upgrade -p ALPHA123456 /path/to/firmware_v1.2.3.bin

# Multiple vendor part numbers with different firmware files
sudo sfputil firmware upgrade \
  -p ALPHA123456 /path/to/alpha_fw.bin \
  -p GAMMA67890 /path/to/gamma_fw.bin
```

**Upgrade Process Flow**:
```
1. Parse and validate input parameters
2. Identify target ports based on filters; reject overlapping groups
   with conflicting firmware files (see Section 7.5.1)
3. Verify CMIS firmware-management capability per port via
   get_module_fw_mgmt_feature(); exclude unsupported ports with a
   per-port reason and proceed with the rest
4. Display pre-upgrade status

   --- Phase 1/3: Download ---
5. Execute parallel firmware download per port:
   a. cdb_start_firmware_download()
   b. Download firmware payload
   c. cdb_firmware_download_complete()
   d. On ANY failure in steps a-c, issue the CDB Abort command for
      that port so the module returns to idle. The port is marked
      Failed(Download) and is EXCLUDED from Phase 2 and Phase 3. The
      remaining ports advance.

   --- Phase 2/3: Activate ---
6. For each port whose download completed cleanly:
   a. cdb_run_firmware() to activate the new image
   b. Verify firmware-switch completion

   --- Phase 3/3: Commit ---
7. For each port whose activation completed cleanly:
   a. cdb_commit_firmware()

8. Display failure cause table for any failed ports (stage, status
   code, decoded reason, recovery hint)
9. Display post-upgrade status
10. Report final results
```

#### 7.4. DB and Schema Changes

**No database schema changes are required.** The implementation uses existing STATE_DB tables:

- **STATE_DB:TRANSCEIVER_INFO**: Existing table for transceiver information (vendor, model, serial number)
- **STATE_DB:TRANSCEIVER_FIRMWARE_INFO**: Existing table for firmware version tracking

#### 7.5. Implementation Details

##### 7.5.1. Port Selection and Filtering

For `firmware download` / `firmware upgrade`, the CLI builds a deterministic **port-to-firmware mapping** before any firmware operation begins. For `show fwversion`, the same selection logic is used to produce a port set (no firmware file is involved).

**Per-group expansion:**

Each `-i <INTERFACE_LIST> <FILEPATH>` and `-p <PART_NUMBER_LIST> <FILEPATH>` instance on the command line forms one independent **group**. Groups are processed in the order they appear. For each group:

1. **Get Present Ports**: Query all ports with transceivers present via `get_present_sfp_ports_names_list()`, which skips RJ45 ports and ports without presence
2. **Expand Group Selector**:
   - For an `-i` group, parse each comma-separated token in `<INTERFACE_LIST>`.
   - For a `-p` group, match `<PART_NUMBER_LIST>` against the transceiver info `model` field across all present ports
3. **Intersect With Present Ports**: The group's expanded port set is intersected with the present ports
4. **Pair With Firmware File**: Each surviving port in the group is paired with the group's `<FILEPATH>`, producing `(port → firmware_path)` entries

**Combining groups into a single mapping:**

After all groups are expanded, the per-group entries are merged into a single port-to-firmware mapping that drives the parallel firmware operation. Overlap handling is deterministic and validated up front:

1. **Cross-type overlap between `-i` and `-p` is always rejected**: If a port is selected by **both** a `-p` group (via vendor-PN match) **and** an `-i` group (explicit interface or interface range), the command is rejected with `ERROR_INVALID_PORT` regardless of whether the two groups specify the same firmware file or different ones.
2. **Same firmware in multiple groups of the same type** (`-i` × `-i` or `-p` × `-p`): If a port appears in more than one group of the same type and all such groups specify the **same** firmware file path, the port is included once. No error.
3. **Conflicting firmware across groups of the same type** (`-i` × `-i` or `-p` × `-p`): If a port appears in more than one group of the same type with **different** firmware file paths, this is a configuration error. The CLI exits with `ERROR_INVALID_PORT`.
4. **Empty selection**: If, after all groups are processed, the merged mapping is empty (no present port matched any group), the CLI prints an informational message and exits without performing any firmware operation.

**Final validation:**

- Every explicitly named interface must resolve to a present port, otherwise exit with an `ERROR_INVALID_PORT` exit.
- Ports excluded purely because they fell within an unconfigured portion of an interface range are silently dropped, not treated as errors.

##### 7.5.1.1. Interface Range Expansion

The interface range syntax provides a concise way to target a contiguous block of ports without listing each one individually.

**Syntax:**

```
<PREFIX><START_INDEX>-<END_INDEX>
```

For example, `Ethernet16-80` represents the range starting at index 16 and ending at index 80, inclusive.
Malformed ranges shall result in CLI command getting rejected.

##### 7.5.2.  Transceiver Deduplication

When multiple Ethernet interfaces share the same physical transceiver, the system automatically deduplicates transceivers to avoid redundant operations and potential conflicts.

**Deduplication Criteria:**

Transceivers are identified as duplicates when they share the same serial number. This scenario occurs on certain platforms where multiple logical interfaces map to the same physical transceiver module.

**Selection Strategy:**

When duplicate transceivers are detected:
- The interface with the lowest port number is selected for the operation
- Ports are evaluated in numerical order (e.g., Ethernet0, Ethernet4, Ethernet8)
- Duplicate interfaces are excluded from processing

**Scope:**

Automatic deduplication is applied in the following operations:
- Firmware version display with tabular format (`-t` option)
- Multi-port firmware download operations (`-i` or `-p` options)
- Multi-port firmware upgrade operations (`-i` or `-p` options)

**Example:**

On a platform where `Ethernet0` and `Ethernet1` share the same transceiver (serial number: `ABC123`):
- `Ethernet0` is selected for firmware operations (lowest port number)
- `Ethernet1` is automatically excluded

**Benefits:**

1. **Efficiency**: Prevents redundant firmware downloads to the same physical hardware
2. **Safety**: Avoids conflicts from simultaneous operations on shared transceivers
3. **Accuracy**: Ensures each unique transceiver appears only once in firmware version displays
4. **Transparency**: Automatic handling requires no user configuration

##### 7.5.3. Parallel Processing

Multi-port operations leverage Python's `concurrent.futures.ThreadPoolExecutor` for parallel processing:

- **Concurrency Model**: Bounded worker pool (up to 128)
- **Error Isolation**: Failures in individual ports don't affect others; each port reports its own status
- **Thread Safety**: Port status updates are protected by a `threading.Lock`.

**Benefits**:
- Significant time savings for multi-port operations versus serial execution
- Real-time progress visibility

##### 7.5.4. Progress Display

The implementation provides two progress display modes:

**Single Port Mode** (when `port_name` is specified directly):
- Per-port `enlighten` progress bar showing download progress in bytes
- Verbose output for each firmware operation stage
- Bar format: `Ethernet128: Downloading  100%|####| 550532.00/550596.00 B [00:00]`

**Multi-Port Mode** (when using `-i` or `-p` flags):
- Summary status line showing aggregate counts per state, updated in real-time
- Remaining time estimation (begins after 15 seconds of download activity for accuracy)
- Format: `Progress: Not Started(0), Downloading FW(3), Activating FW(1), Committing FW(0), Upgraded(10), Failed(0)`
- Time estimate: `Remaining Time: 2 minutes 15 seconds`

**Status Tracking per port**:
- Pending
- Downloading Firmware
- Activating Firmware
- Committing Firmware
- Upgraded (success)
- Failed (with reason)

#### 7.6. Data Structures

##### 7.6.1. Port to Firmware Mapping
```python
port_to_firmware_map = {
    'Ethernet0': '/path/to/firmware.bin',
    'Ethernet4': '/path/to/firmware.bin',
    'Ethernet8': '/path/to/different_firmware.bin'
}
```

##### 7.6.2. Port Status Tracking
```python
port_status = {
    'Ethernet0': 'Downloading Firmware',
    'Ethernet4': 'Activating Firmware',
    'Ethernet8': 'Upgraded'
}
```

##### 7.6.3. Failure Information
```python
ports_failed_status_info = {
    'Ethernet0': {
        'stage': 'Activate',          # Download | Activate | Commit
        'status_code': 2,             # raw CDB/Platform API code
        'reason': 'Image rejected by transceiver; image incompatible',
        'recovery_hint': 'Use a firmware image matching the module PN/revision.',
    },
}
```

##### 7.6.4. Download Progress Tracking
```python
# Used for remaining time estimation in multi-port mode
download_progress = {
    'Ethernet0': (bytes_done, total_bytes, start_time),
    # Example: (275000, 550596, 1713200605.0)
}
```

##### 7.6.5. Transceiver Info Map
```python
# Fetched in parallel via get_transceiver_info_for_ports()
transceiver_info_map = {
    'Ethernet0': {'manufacturer': 'ABCD Corp', 'model': 'Thetazzzzzzzz003', 'serial': 'UR3T010005', ...},
    'Ethernet128': {'manufacturer': 'EFGH Systems', 'model': 'Alphaxxxxxxxx001', 'serial': 'A11CLA5', ...}
}
```

#### 7.7. Error Handling and Serviceability

The implementation includes comprehensive error handling:

1. **Input Validation** (performed before any firmware operation is dispatched):
   - Verify port names and ranges are valid
   - Ensure transceivers are present on every explicitly named target
   - **Verify CMIS firmware-management capability per target via `get_module_fw_mgmt_feature()`**.
   - Validate firmware file paths (existence, readability)
   - Reject overlapping `-i`/`-p` groups that map the same port to different firmware files (Section 7.5.1)

2. **Operation Errors**:
   - CDB command failures
   - Firmware download errors → CDB Abort is issued for the affected port so the module is returned to an idle state and can be retried cleanly (see download/upgrade flows in Section 7.3)
   - Firmware activation failures
   - Commit operation failures
   - Each failure is recorded with the failing stage (Download / Activate / Commit), the raw CDB/status code, a **decoded reason string**, and a **recovery hint** (see [Failure Reason Decoding](#771-failure-reason-decoding))

3. **User Feedback**:
   - Clear error messages
   - Specific failure reasons (numeric code + decoded reason text)
   - Actionable guidance (recovery hint per failure)

##### 7.7.1. Failure Reason Decoding

CDB and platform-API status codes returned by firmware operations are decoded into human-readable strings before display. The decoding table is maintained in `sfputil/main.py` and is sourced from the CMIS specification (CDB error codes) plus a small set of `sfputil`-internal failure modes (e.g., timeout, capability missing). The failure cause table in multi-port operations displays three columns:

| Column        | Source                                                                      |
|---------------|-----------------------------------------------------------------------------|
| Stage Failed  | Pipeline stage at which the failure occurred (Download / Activate / Commit) |
| Status Code   | Raw numeric code from the CDB/Platform API                                  |
| Reason        | Decoded human-readable description of the status code                       |

#### 7.8. Platform-Specific Considerations

This feature is platform-agnostic and works with any platform that implements the standard SONiC Platform API for transceiver management. No platform-specific changes are required.

**Platform Requirements:**
- Platform must implement the Platform API transceiver methods listed in Section 8
- Transceivers must support CMIS specification for firmware upgrade operations

#### 7.9. Scalability and Performance

- **Scalability**: Supports concurrent operations on multiple transceivers
- **Memory**: Low additional memory footprint (Less than 15 MB during firmware upgrade)

#### 7.10. Warmboot and Fastboot Requirements

No warmboot or fastboot dependencies.

#### 7.11. Docker Dependencies

No new Docker containers or dependencies. The feature runs within the existing host environment where `sfputil` is executed.

#### 7.12. Build Dependencies

No new build dependencies. Uses existing Python standard library and SONiC dependencies. In particular, `enlighten` is already declared in `sonic-utilities/setup.py` and is used by the current single-port `sfputil firmware upgrade` implementation — this enhancement reuses it without adding a new package requirement.

### 8. SAI API

No additional SAI support is required for this enhancement.

### 9. Configuration and Management

This section covers the configuration and management interfaces for the feature.

#### 9.1. Manifest

Not applicable

#### 9.2. CLI/YANG Model Enhancements

##### 9.2.1. CLI Enhancements

The feature extends the existing `sfputil` CLI with new options. All changes maintain backward compatibility with existing CLI usage.

**Show Firmware Version Command:**

```
# sfputil show fwversion --help
Usage: sfputil show fwversion [OPTIONS] [<port_name>]

  Show firmware version of the transceiver(s) (all ports if no port specified)

Options:
  -t                              Display firmware version in tabular format
  -i <INTERFACE_LIST>             Comma-separated list of interfaces. Each
                                  entity may be a single interface (Ethernet0)
                                  or an inclusive interface range
                                  (Ethernet16-80).
  -p <PART_NUMBER_LIST>           Comma-separated list of vendor part numbers
  --help                          Show this message and exit.
```

**Firmware Download Command:**

```
# sfputil firmware download --help
Usage: sfputil firmware download [OPTIONS]

  Download firmware to the transceiver(s) without automatic activation

Options:
  -i <INTERFACE_LIST> <FILEPATH>  Download firmware for comma-separated
                                  interface list with specified firmware file.
                                  Each entity may be a single interface or an
                                  inclusive interface range (e.g.,
                                  Ethernet16-80); tokens may be mixed.
                                  Example: -i Ethernet0,Ethernet4,Ethernet16-80
                                  /path/to/firmware.bin
  -p <PART_NUMBER_LIST> <FILEPATH>
                                  Download firmware for all ports with
                                  specified vendor part number using specified
                                  firmware file
  --help                          Show this message and exit.
```

**Firmware Upgrade Command:**

```
# sfputil firmware upgrade --help
Usage: sfputil firmware upgrade [OPTIONS] [PORT_NAME] [FILEPATH]

  Upgrade firmware on the transceiver

Options:
  -i <INTERFACE_LIST> <FILEPATH>  Upgrade firmware for comma-separated
                                  interface list with specified firmware file.
                                  Each entity may be a single interface or an
                                  inclusive interface range (e.g.,
                                  Ethernet16-80); tokens may be mixed.
                                  Example: -i Ethernet0,Ethernet4,Ethernet16-80
                                  /path/to/firmware.bin
  -p <PART_NUMBER_LIST> <FILEPATH>
                                  Upgrade firmware for all ports with
                                  specified vendor part number using specified
                                  firmware file
  --help                          Show this message and exit.
```

**Backward Compatibility:**
- Existing single-port commands continue to work without modification
- New options are additive and do not break existing scripts or workflows
- Command output format remains consistent with existing patterns

**CLI Framework:**
- Implementation uses Click framework (existing SONiC standard)
- No KLISH changes required (feature is CLICK-based only)

**Documentation Update:**
- The Command Reference (https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md) will be updated with the new CLI options

##### 9.2.2. YANG Model Changes

No YANG model changes are required.

#### 9.3. Config DB Enhancements

No Config DB changes are required.

### 10. Warmboot and Fastboot Design Impact

This enhancement has **no impact** on warmboot or fastboot operations.

### 11. Memory Consumption

Low additional memory footprint (Less than 15 MB during firmware upgrade).

### 12. Restrictions/Limitations

#### 12.1. Current Limitations

1. **Firmware File Management**:
   - Firmware files must be accessible on the local filesystem
   - No automatic firmware file download or repository management

2. **Vendor Part Number Matching**:
   - Exact string match required for vendor PN filtering (matches against the transceiver `model` field)
   - No wildcard or regex pattern matching

3. **Interface Validation**:
   - All explicitly specified interfaces must have transceivers present
   - Operation exits with `ERROR_INVALID_PORT` if any explicitly specified port is not present

4. **Interface Range Syntax**:
   - Range bounds use the form `<PREFIX><START>-<END>` (e.g., `Ethernet16-80`) and are inclusive on both ends
   - The interface prefix is implicit from the left-hand side; the form `Ethernet16-Ethernet80` is also accepted, but prefixes on both sides must match

#### 12.2. Operational Considerations

1. **Error Recovery**:
   - Failed ports are reported with stage (Download/Activate/Commit) and status code
   - Manual intervention required for persistent failures
   - Re-run upgrade with `-i` specifying only the failed ports

2. **Shared Transceiver Handling**:
   - Platforms where multiple interfaces share the same physical transceiver are automatically handled through deduplication
   - Only the lowest-numbered interface per unique transceiver (identified by serial number) will be processed
   - Duplicate interfaces are silently excluded from operations
   - See Section 7.5.1 (Transceiver Deduplication) for detailed behavior

### 13. Testing Requirements/Design

This section explains the testing strategy for the feature, including unit testing, system testing, and regression testing to ensure existing warmboot/fastboot requirements are met.

#### 13.1. Unit Test Cases

##### 13.1.1. Test Cases for Firmware Version Display

| Test Case ID | Description | Expected Result |
|--------------|-------------|-----------------|
| FW-SHOW-01 | Display firmware version for single port | Firmware details displayed |
| FW-SHOW-02 | Display firmware version with (`-t`) | Tabular format output |
| FW-SHOW-03 | Filter by single interface (`-i`) | Only specified interface shown |
| FW-SHOW-04 | Filter by multiple interfaces (`-i`) | Only specified interfaces shown |
| FW-SHOW-05 | Filter by vendor PN (`-p`) | Only matching transceivers shown |
| FW-SHOW-06 | Filter by non-existent vendor PN | "No matching ports" message |
| FW-SHOW-07 | Combine `-i` and `-t` | Filtered tabular output |
| FW-SHOW-08 | Invalid interface name | Error message displayed |
| FW-SHOW-09 | Interface without transceiver | Appropriate error handling |
| FW-SHOW-10 | Filter by interface range (`-i Ethernet16-80`) | Only configured ports within the range shown |
| FW-SHOW-11 | Filter by mixed range and single interfaces (`-i Ethernet0,Ethernet4,Ethernet16-80`) | Union of all matching ports shown, deduplicated |
| FW-SHOW-12 | Reversed range (`-i Ethernet80-16`) | Error message displayed, exits with `ERROR_INVALID_PORT` |
| FW-SHOW-13 | Malformed range (`-i Ethernet16-`) | Error message displayed, exits with `ERROR_INVALID_PORT` |
| FW-SHOW-14 | Range matching zero configured ports (`-i Ethernet9999-99999`) | "No matching ports for range" message displayed |

##### 13.1.2. Test Cases for Firmware Download

| Test Case ID | Description | Expected Result |
|--------------|-------------|-----------------|
| FW-DL-01 | Download with `-i` option | All specified ports downloaded |
| FW-DL-02 | Download with `-p` option | All matching ports downloaded |
| FW-DL-03 | Multiple `-p` options | All matching ports downloaded with correct firmware |
| FW-DL-04 | Invalid firmware file path | Error message displayed |
| FW-DL-05 | Non-existent interface | Error message displayed |
| FW-DL-06 | Interface without transceiver | Error message displayed |
| FW-DL-07 | Firmware download failure | Error reported with stage and status code |
| FW-DL-08 | Mixed success/failure scenario | Successful ports downloaded, failures reported |
| FW-DL-09 | No matching ports for vendor PN | Appropriate message displayed |
| FW-DL-10 | Verify firmware not auto-activated | Firmware downloaded but not running |
| FW-DL-11 | Download with interface range (`-i Ethernet16-80`) | All configured ports within range downloaded |
| FW-DL-12 | Download with mixed range and single interfaces (`-i Ethernet0,Ethernet4,Ethernet16-80`) | Union of all matching ports downloaded, deduplicated |
| FW-DL-13 | Reversed range (`-i Ethernet80-16`) | Error message displayed, exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-14 | Malformed range (`-i Ethernet16-`) | Error message displayed, exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-15 | Overlapping `-i` groups, same firmware file (e.g., `-i Ethernet0,Ethernet4 fw.bin -i Ethernet4,Ethernet8 fw.bin`) | Overlap accepted; `Ethernet4` deduplicated and downloaded once |
| FW-DL-16 | Overlapping `-i` groups, **different** firmware files (e.g., `-i Ethernet0,Ethernet4 fw_v1.bin -i Ethernet4,Ethernet8 fw_v2.bin`) | Conflict table printed listing `Ethernet4` with both candidate firmware files and group selectors; exits with `ERROR_INVALID_PORT` **before** any download is initiated |
| FW-DL-17 | Overlapping `-i` and `-p` groups, **different** firmware files (e.g., `-i Ethernet0 fw_a.bin -p VendorPN_X fw_b.bin` where `Ethernet0` has model `VendorPN_X`) | Conflict table printed listing `Ethernet0` with both candidate firmware files; exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-17a | Overlapping `-i` and `-p` groups, **same** firmware file (e.g., `-i Ethernet0 fw.bin -p VendorPN_X fw.bin` where `Ethernet0` has model `VendorPN_X`) | Cross-type overlap is rejected regardless of firmware path equality. Conflict table printed listing `Ethernet0` with the `-i` token and the `-p` selector; exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-17b | `-i` interface range overlapping with `-p` match (e.g., `-i Ethernet0-32 fw_a.bin -p VendorPN_X fw_b.bin` where some ports in the range have model `VendorPN_X`) | Conflict table printed for every port covered by both the expanded `-i` range and the `-p` match; exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-18 | Overlapping `-p` groups via partial PN match collision, **different** firmware files | Conflict table printed for every port matched by both PNs; exits with `ERROR_INVALID_PORT`; no download initiated |
| FW-DL-19 | Overlap with **same** firmware path expressed differently (e.g., `/tmp/fw.bin` vs `/tmp/./fw.bin`) | Paths normalized via `os.path.realpath`; treated as same firmware, accepted, deduplicated |

##### 13.1.3. Test Cases for Firmware Upgrade

| Test Case ID | Description | Expected Result |
|--------------|-------------|-----------------|
| FW-UPG-01 | Upgrade single port | Successful upgrade |
| FW-UPG-02 | Upgrade with `-i` option | All specified ports upgraded |
| FW-UPG-03 | Upgrade with `-p` option | All matching ports upgraded |
| FW-UPG-04 | Multiple `-p` options | All matching ports upgraded with correct firmware |
| FW-UPG-05 | Invalid firmware file path | Error message displayed |
| FW-UPG-06 | Non-existent interface | Error message displayed |
| FW-UPG-07 | Interface without transceiver | Error message displayed |
| FW-UPG-08 | Firmware download failure | Error reported with stage and status code |
| FW-UPG-09 | Firmware activation failure | Error reported with stage and status code |
| FW-UPG-10 | Mixed success/failure scenario | Successful ports upgraded, failures reported |
| FW-UPG-11 | No matching ports for vendor PN | Appropriate message displayed |
| FW-UPG-12 | Upgrade with interface range (`-i Ethernet16-80`) | All configured ports within range upgraded |
| FW-UPG-13 | Upgrade with mixed range and single interfaces (`-i Ethernet0,Ethernet4,Ethernet16-80`) | Union of all matching ports upgraded, deduplicated |
| FW-UPG-14 | Reversed range (`-i Ethernet80-16`) | Error message displayed, exits with `ERROR_INVALID_PORT`; no upgrade initiated |
| FW-UPG-15 | Malformed range (`-i Ethernet16-`) | Error message displayed, exits with `ERROR_INVALID_PORT`; no upgrade initiated |
| FW-UPG-16 | Overlapping `-i` groups, same firmware file (e.g., `-i Ethernet0,Ethernet4 fw.bin -i Ethernet4,Ethernet8 fw.bin`) | Overlap accepted; `Ethernet4` deduplicated and upgraded once |
| FW-UPG-17 | Overlapping `-i` groups, **different** firmware files (e.g., `-i Ethernet0,Ethernet4 fw_v1.bin -i Ethernet4,Ethernet8 fw_v2.bin`) | Conflict table printed listing `Ethernet4` with both candidate firmware files and group selectors; exits with `ERROR_INVALID_PORT` **before** any upgrade phase is initiated; module state unchanged |
| FW-UPG-18 | Overlapping `-i` and `-p` groups, **different** firmware files (e.g., `-i Ethernet0 fw_a.bin -p VendorPN_X fw_b.bin` where `Ethernet0` has model `VendorPN_X`) | Conflict table printed listing `Ethernet0`; exits with `ERROR_INVALID_PORT`; no upgrade initiated; module state unchanged |
| FW-UPG-18a | Overlapping `-i` and `-p` groups, **same** firmware file (e.g., `-i Ethernet0 fw.bin -p VendorPN_X fw.bin` where `Ethernet0` has model `VendorPN_X`) | Cross-type overlap is rejected regardless of firmware path equality. Conflict table printed listing `Ethernet0` with the `-i` token and the `-p` selector; exits with `ERROR_INVALID_PORT`; no upgrade initiated; module state unchanged |
| FW-UPG-18b | `-i` interface range overlapping with `-p` match (e.g., `-i Ethernet0-32 fw_a.bin -p VendorPN_X fw_b.bin` where some ports in the range have model `VendorPN_X`) | Conflict table printed for every port covered by both the expanded `-i` range and the `-p` match; exits with `ERROR_INVALID_PORT`; no upgrade initiated; module state unchanged |
| FW-UPG-19 | Overlapping `-p` groups via partial PN match collision, **different** firmware files | Conflict table printed for every port matched by both PNs; exits with `ERROR_INVALID_PORT`; no upgrade initiated |
| FW-UPG-20 | Overlap with **same** firmware path expressed differently (e.g., `/tmp/fw.bin` vs `/tmp/./fw.bin`) | Paths normalized via `os.path.realpath`; treated as same firmware, accepted, deduplicated |

#### 13.2. System Test Cases

##### 13.2.1. Functional Testing

**Test Scenario 1: Multi-Port Download by Vendor PN**
```bash
# Setup: Environment with multiple transceiver vendors
# Execute: Download firmware for multiple vendors
sudo sfputil firmware download \
  -p Deltaxxxxxxxxxx004 IJKL_Deltaxxxxxxxxxx004_0101_0301.bin \
  -p Deltaxxxxxxxxxx005 IJKL_Deltaxxxxxxxxxx005_0103_0303.bin \
  -p Epsilonyyyyyyyyy06 MNOP_Epsilonyyyyyyyyy06-VFF_5.bin \
  -p Epsilonyyyyyyyyy07 MNOP_Epsilonyyyyyyyyy07_VFF.2.bin

# Verify:
# 1. Only matching transceivers selected for each part number
# 2. Parallel download execution
# 3. All matching ports downloaded successfully
# 4. Firmware NOT automatically activated
# 5. Running firmware remains unchanged
# 6. Downloaded firmware available in inactive image
```

**Test Scenario 2: Download with Interface List**
```bash
# Execute: Download firmware for specific interfaces
sudo sfputil firmware download -i Ethernet0,Ethernet4,Ethernet8 /tmp/test_fw.bin

# Verify:
# 1. Pre-download status displayed
# 2. Summary progress line shown with state counts
# 3. Post-download status displayed
# 4. All specified ports downloaded successfully
# 5. Firmware remains inactive (not running)
```

**Test Scenario 3: Multi-Port Upgrade by Interface List**
```bash
# Setup: Prepare test environment with multiple transceivers
# Execute: Upgrade firmware for specific interfaces
sudo sfputil firmware upgrade -i Ethernet0,Ethernet4,Ethernet8 /tmp/test_fw.bin

# Verify:
# 1. Pre-upgrade status displayed
# 2. Summary progress line shown with state counts
# 3. Post-upgrade status displayed
# 4. All specified ports upgraded successfully
# 5. Firmware versions updated in STATE_DB
```

**Test Scenario 4: Multi-Port Upgrade by Vendor PN**
```bash
# Setup: Environment with mixed transceiver vendors
# Execute: Upgrade all transceivers from specific vendor
sudo sfputil firmware upgrade -p ALPHA123456 /tmp/alpha_fw.bin

# Verify:
# 1. Only matching transceivers selected
# 2. Parallel upgrade execution
# 3. All matching ports upgraded
# 4. Non-matching ports unaffected
```

**Test Scenario 5: Filtered Firmware Version Display**
```bash
# Execute: Display firmware version for specific vendor
sudo sfputil show fwversion -p ALPHA123456 -t

# Verify:
# 1. Only matching transceivers displayed
# 2. Tabular format used
# 3. All firmware fields populated correctly
```

**Test Scenario 6: Error Handling**
```bash
# Setup: Simulate firmware upgrade failure
# Execute: Upgrade with expected failure
sudo sfputil firmware upgrade -i Ethernet0 /tmp/test_fw.bin

# Verify:
# 1. Failure details reported with stage and status code
# 2. Failure cause table displayed
# 3. Post-upgrade status still displayed
# 4. System remains stable
# 5. Exit code is EXIT_FAIL
```

##### 13.2.2. Performance Testing

**Performance Metrics**

| Metric | Measurement Method |
|--------|-------------------|
| Single port download time | Time from start to completion |
| Multi-port download time | Time from start to completion |
| Single port upgrade time | Time from start to completion |
| Multi-port upgrade time | Time from start to completion |

##### 13.2.3. Warmboot/Fastboot Testing

Not applicable

### 14. Open/Action Items

Not applicable

## Appendix A: References

1. CMIS Specification: https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf
2. SONiC Platform API Documentation
3. Python concurrent.futures Documentation: https://docs.python.org/3/library/concurrent.futures.html
4. Click CLI Framework Documentation: https://click.palletsprojects.com/
5. SONiC Command Reference: https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md

## Appendix B: Example Output

### B.1. Firmware Version Display 

#### B.1.1 Standard format
```
# sfputil show fwversion Ethernet128
Interface: Ethernet128
Vendor Name: EFGH Systems 
Vendor PN: Alphaxxxxxxxx001
Vendor SN: A11CLA5
Image A Version: 255.2.0
Image B Version: 255.2.0
Factory Image Version: 37.2.3
Running Image: B
Committed Image: B
Active Firmware: 255.2.0
Inactive Firmware: 255.2.0
```

#### B.1.2 Tabular format
```
# sfputil show fwversion Ethernet128 -t
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      255.2.0    255.2.0    255.2.0   B          B
```

#### B.1.3 Filter by vendor PN
```
# sfputil show fwversion -p Alphaxxxxxxxx001 -t
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      255.2.0    255.2.0    255.2.0   B          B
Ethernet232  EFGH Systems   Alphaxxxxxxxx001  Z12CR69      255.2.0    255.2.0    255.2.0   B          B
Ethernet256  EFGH Systems   Alphaxxxxxxxx001  BR8C184      255.2.0    255.2.0    255.2.0   B          B
```

#### B.1.4 Filter by multiple vendor PNs

```
# sfputil show fwversion -p Alphaxxxxxxxx001,Thetazzzzzzzz003 -t
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet0    ABCD Corp      Thetazzzzzzzz003  UR3T010005   3.3.0      3.3.0      3.3.0     A          A
Ethernet8    ABCD Corp      Thetazzzzzzzz003  UR3T030047   3.3.0      3.3.0      3.3.0     A          A
Ethernet16   ABCD Corp      Thetazzzzzzzz003  UR19000007   3.3.0      3.3.0      3.3.0     A          A
Ethernet24   ABCD Corp      Thetazzzzzzzz003  UR3T030033   3.3.0      3.3.0      3.3.0     B          B
Ethernet56   ABCD Corp      Thetazzzzzzzz003  UR3T030010   3.3.0      3.3.0      3.3.0     A          A
Ethernet72   ABCD Corp      Thetazzzzzzzz003  UR3T010016   3.3.0      3.3.0      3.3.0     B          B
Ethernet88   ABCD Corp      Thetazzzzzzzz003  UR3T010004   3.3.0      3.3.0      3.3.0     B          B
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      2.3.0      2.3.0      2.3.0     B          B
Ethernet136  ABCD Corp      Thetazzzzzzzz003  UR3T030039   3.3.0      3.3.0      3.3.0     A          A
Ethernet176  ABCD Corp      Thetazzzzzzzz003  UR3T030018   3.3.0      3.2.0      3.2.0     B          B
Ethernet184  ABCD Corp      Thetazzzzzzzz003  UR3T030032   3.3.0      3.2.0      3.2.0     B          B
Ethernet232  EFGH Systems   Alphaxxxxxxxx001  Z12CR69      255.2.0    255.2.0    255.2.0   B          B
Ethernet256  EFGH Systems   Alphaxxxxxxxx001  BR8C184      255.2.0    255.2.0    255.2.0   B          B
```

### B.2. Firmware Download

### B.2.1 Multi-Port Firmware Download using -i option

```
# sfputil firmware download -i Ethernet0,Ethernet4,Ethernet8 ABCD_Corp_Thetazzzzzzzz003_V3_3.bin
Downloading image for 3 transceiver(s)

CDB: Firmware status before download:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet0    ABCD Corp      Thetazzzzzzzz003  UR3T010005   3.2.0      3.2.0      3.2.0     A          A
Ethernet4    ABCD Corp      Thetazzzzzzzz003  UR3T030047   3.2.0      3.2.0      3.2.0     A          A
Ethernet8    ABCD Corp      Thetazzzzzzzz003  UR19000007   3.2.0      3.2.0      3.2.0     A          A

CDB: Starting firmware download: 18:15:22

Progress: Not Started(0), Downloading FW(0), Downloaded(3), Failed(0)
Remaining Time: 0 seconds
CDB: Finished firmware download: 18:16:38. Time taken: 76 seconds

Succeeded: 3, Failed: 0

CDB: Firmware status after download:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet0    ABCD Corp      Thetazzzzzzzz003  UR3T010005   3.2.0      3.3.0      3.2.0     A          A
Ethernet4    ABCD Corp      Thetazzzzzzzz003  UR3T030047   3.2.0      3.3.0      3.2.0     A          A
Ethernet8    ABCD Corp      Thetazzzzzzzz003  UR19000007   3.2.0      3.3.0      3.2.0     A          A
```

### B.2.2 Multi-Port Firmware Download using -p option with multiple part numbers

```
# sfputil firmware download -p Deltaxxxxxxxxxx004 IJKL_Deltaxxxxxxxxxx004_0101_0301.bin -p Deltaxxxxxxxxxx005 IJKL_Deltaxxxxxxxxxx005_0103_0303.bin -p Epsilonyyyyyyyyy06 MNOP_Epsilonyyyyyyyyy06-VFF_5.bin -p Epsilonyyyyyyyyy07 MNOP_Epsilonyyyyyyyyy07_VFF.2.bin
Downloading image for 16 transceiver(s)

CDB: Firmware status before download:
Interface    Vendor Name    Vendor PN           Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ------------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet48   IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240001   1.1.0      1.1.0      1.1.0     A          A
Ethernet56   IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240002   1.1.0      1.1.0      1.1.0     A          A
Ethernet64   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250001   1.3.0      1.3.0      1.3.0     B          B
Ethernet72   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250002   1.3.0      1.3.0      1.3.0     B          B
Ethernet80   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250003   1.3.0      1.3.0      1.3.0     B          B
Ethernet96   MNOP Corp      Epsilonyyyyyyyyy06  MN4P170001   5.4.0      5.4.0      5.4.0     A          A
Ethernet104  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170002   5.4.0      5.4.0      5.4.0     A          A
Ethernet112  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170003   5.4.0      5.4.0      5.4.0     A          A
Ethernet120  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170004   5.4.0      5.4.0      5.4.0     A          A
Ethernet144  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170001   2.1.0      2.1.0      2.1.0     B          B
Ethernet152  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170002   2.1.0      2.1.0      2.1.0     B          B
Ethernet160  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170003   2.1.0      2.1.0      2.1.0     B          B
Ethernet168  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170004   2.1.0      2.1.0      2.1.0     B          B
Ethernet176  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170005   2.1.0      2.1.0      2.1.0     B          B
Ethernet184  IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240003   1.1.0      1.1.0      1.1.0     A          A
Ethernet192  IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250004   1.3.0      1.3.0      1.3.0     B          B

CDB: Starting firmware download: 18:25:10

Progress: Not Started(0), Downloading FW(0), Downloaded(16), Failed(0)
Remaining Time: 0 seconds
CDB: Finished firmware download: 18:28:45. Time taken: 215 seconds

Succeeded: 16, Failed: 0

CDB: Firmware status after download:
Interface    Vendor Name    Vendor PN           Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ------------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet48   IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240001   1.1.0      3.1.0      1.1.0     A          A
Ethernet56   IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240002   1.1.0      3.1.0      1.1.0     A          A
Ethernet64   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250001   3.3.0      1.3.0      1.3.0     B          B
Ethernet72   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250002   3.3.0      1.3.0      1.3.0     B          B
Ethernet80   IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250003   3.3.0      1.3.0      1.3.0     B          B
Ethernet96   MNOP Corp      Epsilonyyyyyyyyy06  MN4P170001   5.4.0      5.5.0      5.4.0     A          A
Ethernet104  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170002   5.4.0      5.5.0      5.4.0     A          A
Ethernet112  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170003   5.4.0      5.5.0      5.4.0     A          A
Ethernet120  MNOP Corp      Epsilonyyyyyyyyy06  MN4P170004   5.4.0      5.5.0      5.4.0     A          A
Ethernet144  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170001   2.2.0      2.1.0      2.1.0     B          B
Ethernet152  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170002   2.2.0      2.1.0      2.1.0     B          B
Ethernet160  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170003   2.2.0      2.1.0      2.1.0     B          B
Ethernet168  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170004   2.2.0      2.1.0      2.1.0     B          B
Ethernet176  MNOP Corp      Epsilonyyyyyyyyy07  MN2P170005   2.2.0      2.1.0      2.1.0     B          B
Ethernet184  IJKL Inc       Deltaxxxxxxxxxx004  IJ5K240003   1.1.0      3.1.0      1.1.0     A          A
Ethernet192  IJKL Inc       Deltaxxxxxxxxxx005  IJ5L250004   3.3.0      1.3.0      1.3.0     B          B
```

### B.2.3 Multi-Port Firmware Download Progress Indication

The firmware download progress is indicated by the number of interfaces in each stage.
Additionally, the module indicates the time remaining for the download operation to complete.

```
Progress: Not Started(22), Downloading FW(0), Downloaded(0), Failed(0)
Remaining Time: estimating...
│
▼
Progress: Not Started(0), Downloading FW(22), Downloaded(0), Failed(0)
Remaining Time: 1 minute 20 seconds
│
▼
Progress: Not Started(0), Downloading FW(12), Downloaded(10), Failed(0)
Remaining Time: 33 seconds
│
▼
Progress: Not Started(0), Downloading FW(0), Downloaded(20), Failed(2)
Remaining Time: 0 seconds
```

### B.2.4 Multi-Port Firmware Download Failure Scenario

```
...
CDB: Starting firmware download: 17:30:12

Progress: Not Started(0), Downloading FW(0), Downloaded(23), Failed(3)
Remaining Time: 0 seconds
CDB: Finished firmware download: 17:32:01. Time taken: 108 seconds

Succeeded: 23, Failed: 3

Failed ports:
Interface    Stage Failed      Status Code  Reason
-----------  --------------  -------------  ---------------------------------------------
Ethernet8    Download                    3  Invalid firmware image format
Ethernet72   Download                   64  Transfer timed out; module unresponsive
Ethernet504  Download                   69  Firmware rejected by transceiver; incompatible
...
```
### B.3. Firmware Upgrade

### B.3.1 Single Port Firmware Upgrade

```
# sfputil firmware upgrade Ethernet128 EFGH_Systems_Alphaxxxxxxxx001_V2_3.bin
Upgrading image for 1 transceiver(s)

CDB: Firmware status before upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      255.2.0    255.2.0    255.2.0   B          B

CDB: Starting firmware upgrade: 16:23:36
CDB: Starting firmware download
Ethernet128: Downloading   100%|################################################################| 550532.00/550596.00 B [00:00]
CDB: firmware download complete
Running firmware: Non-hitless Reset to Inactive Image
FW images switch successful : ImageA is running

CDB: Finished firmware upgrade: 16:24:45. Time taken: 69 seconds

Succeeded: 1, Failed: 0

CDB: Firmware status after upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      2.3.0      255.2.0    2.3.0     A          A

```

### B.3.2 Multi-Port Firmware Upgrade

### B.3.2.1 Multi-Port Firmware Upgrade using -i option

```
# sfputil firmware upgrade -i Ethernet248,Ethernet320,Ethernet384,Ethernet400 EFGH_Systems_Gammayyyyyyyy002-V2_5.bin
Upgrading image for 4 transceiver(s)

CDB: Firmware status before upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet248  EFGH Systems   Gammayyyyyyyy002  DC3CY1E      255.5.0    255.5.0    255.5.0   B          B
Ethernet320  EFGH Systems   Gammayyyyyyyy002  DC3A3MK      255.5.0    255.5.0    255.5.0   B          B
Ethernet384  EFGH Systems   Gammayyyyyyyy002  UDNEJCA      255.5.0    255.5.0    255.5.0   B          B
Ethernet400  EFGH Systems   Gammayyyyyyyy002  UDLCZVZ      255.5.0    255.5.0    255.5.0   B          B

CDB: Starting firmware upgrade: 16:43:25

--- Phase 1/3: Downloading firmware for 4 port(s) ---
CDB: Starting firmware download: 16:43:25

Progress: Not Started(0), Downloading FW(0), Downloaded(4), Failed(0)
Remaining Time: 0 seconds
CDB: Finished firmware download: 16:45:33. Time taken: 128 seconds

Succeeded: 4, Failed: 0

--- Phase 2/3: Activating firmware for 4 port(s) ---

--- Phase 3/3: Committing firmware for 4 port(s) ---

CDB: Finished firmware upgrade: 16:45:43. Time taken: 138 seconds

CDB: Firmware status after upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet248  EFGH Systems   Gammayyyyyyyy002  DC3CY1E      2.5.0      255.5.0    2.5.0     A          A
Ethernet320  EFGH Systems   Gammayyyyyyyy002  DC3A3MK      2.5.0      255.5.0    2.5.0     A          A
Ethernet384  EFGH Systems   Gammayyyyyyyy002  UDNEJCA      2.5.0      255.5.0    2.5.0     A          A
Ethernet400  EFGH Systems   Gammayyyyyyyy002  UDLCZVZ      2.5.0      255.5.0    2.5.0     A          A
```

### B.3.2.2 Multi-Port Firmware Upgrade using -p option

```
# sfputil firmware upgrade -p Gammayyyyyyyy002 EFGH_Systems_Gammayyyyyyyy002-VFF_5.bin -p Alphaxxxxxxxx001 EFGH_Systems_Alphaxxxxxxxx001_V2_3.bin
Upgrading image for 14 transceiver(s)

CDB: Firmware status before upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      255.2.0    255.2.0    255.2.0   B          B
Ethernet232  EFGH Systems   Alphaxxxxxxxx001  Z12CR69      255.2.0    255.2.0    255.2.0   B          B
Ethernet248  EFGH Systems   Gammayyyyyyyy002  DC3CY1E      2.5.0      255.5.0    2.5.0     A          A
Ethernet256  EFGH Systems   Alphaxxxxxxxx001  BR8C184      255.2.0    255.2.0    255.2.0   B          B
Ethernet320  EFGH Systems   Gammayyyyyyyy002  DC3A3MK      2.5.0      255.5.0    2.5.0     A          A
Ethernet336  EFGH Systems   Alphaxxxxxxxx001  JK4DQPD      255.2.0    255.2.0    255.2.0   B          B
Ethernet352  EFGH Systems   Alphaxxxxxxxx001  A11CLAP      255.2.0    255.2.0    255.2.0   B          B
Ethernet384  EFGH Systems   Gammayyyyyyyy002  UDNEJCA      2.5.0      255.5.0    2.5.0     A          A
Ethernet400  EFGH Systems   Gammayyyyyyyy002  UDLCZVZ      2.5.0      255.5.0    2.5.0     A          A
Ethernet416  EFGH Systems   Alphaxxxxxxxx001  Z12CR5Y      255.2.0    255.2.0    255.2.0   B          B
Ethernet480  EFGH Systems   Alphaxxxxxxxx001  HNABCQT      255.2.0    255.2.0    255.2.0   B          B
Ethernet488  EFGH Systems   Alphaxxxxxxxx001  HN9CYDK      255.2.0    255.2.0    255.2.0   B          B
Ethernet496  EFGH Systems   Alphaxxxxxxxx001  HN9CYAT      255.2.0    255.2.0    255.2.0   B          B
Ethernet504  EFGH Systems   Alphaxxxxxxxx001  HN7DQ6X      255.2.0    255.2.0    255.2.0   B          B

CDB: Starting firmware upgrade: 17:03:15

--- Phase 1/3: Downloading firmware for 14 port(s) ---
CDB: Starting firmware download: 17:03:15

Progress: Not Started(0), Downloading FW(0), Downloaded(14), Failed(0)
Remaining Time: 0 seconds
CDB: Finished firmware download: 17:05:11. Time taken: 116 seconds

Succeeded: 14, Failed: 0

--- Phase 2/3: Activating firmware for 14 port(s) ---

CDB: Finished firmware upgrade: 17:05:21. Time taken: 126 seconds

CDB: Firmware status after upgrade:
Interface    Vendor Name    Vendor PN         Vendor SN    Image A    Image B    Active    Running    Committed
-----------  -------------  ----------------  -----------  ---------  ---------  --------  ---------  -----------
Ethernet128  EFGH Systems   Alphaxxxxxxxx001  A11CLA5      2.3.0      255.2.0    2.3.0     A          A
Ethernet232  EFGH Systems   Alphaxxxxxxxx001  Z12CR69      2.3.0      255.2.0    2.3.0     A          A
Ethernet248  EFGH Systems   Gammayyyyyyyy002  DC3CY1E      2.5.0      255.5.0    255.5.0   B          B
Ethernet256  EFGH Systems   Alphaxxxxxxxx001  BR8C184      2.3.0      255.2.0    2.3.0     A          A
Ethernet320  EFGH Systems   Gammayyyyyyyy002  DC3A3MK      2.5.0      255.5.0    255.5.0   B          B
Ethernet336  EFGH Systems   Alphaxxxxxxxx001  JK4DQPD      2.3.0      255.2.0    2.3.0     A          A
Ethernet352  EFGH Systems   Alphaxxxxxxxx001  A11CLAP      2.3.0      255.2.0    2.3.0     A          A
Ethernet384  EFGH Systems   Gammayyyyyyyy002  UDNEJCA      2.5.0      255.5.0    255.5.0   B          B
Ethernet400  EFGH Systems   Gammayyyyyyyy002  UDLCZVZ      2.5.0      255.5.0    255.5.0   B          B
Ethernet416  EFGH Systems   Alphaxxxxxxxx001  Z12CR5Y      2.3.0      255.2.0    2.3.0     A          A
Ethernet480  EFGH Systems   Alphaxxxxxxxx001  HNABCQT      2.3.0      255.2.0    2.3.0     A          A
Ethernet488  EFGH Systems   Alphaxxxxxxxx001  HN9CYDK      2.3.0      255.2.0    2.3.0     A          A
Ethernet496  EFGH Systems   Alphaxxxxxxxx001  HN9CYAT      2.3.0      255.2.0    2.3.0     A          A
Ethernet504  EFGH Systems   Alphaxxxxxxxx001  HN7DQ6X      2.3.0      255.2.0    2.3.0     A          A
```

### B.3.2.2 Multi-Port Firmware Upgrade Failure Scenario

```
...
CDB: Starting firmware upgrade: 17:35:40

--- Phase 1/3: Downloading firmware for 26 port(s) ---
CDB: Starting firmware download: 17:35:40

Progress: Not Started(0), Downloading FW(0), Downloaded(22), Failed(4)
Remaining Time: 0 seconds
CDB: Finished firmware download: 17:37:28. Time taken: 108 seconds

Succeeded: 22, Failed: 4

--- Phase 2/3: Activating firmware for 22 port(s) ---

--- Phase 3/3: Committing firmware for 22 port(s) ---

CDB: Finished firmware upgrade: 17:37:37. Time taken: 116 seconds

Succeeded: 22, Failed: 4

Failed ports:
Interface    Stage Failed      Status Code  Reason
-----------  --------------  -------------  ---------------------------------------------
Ethernet16   Download                    3  Invalid firmware image format
Ethernet72   Download                   64  Transfer timed out; module unresponsive
Ethernet160  Download                    3  Invalid firmware image format
Ethernet384  Download                   69  Firmware rejected by transceiver; incompatible
...
```

## Appendix C: Command Reference Quick Guide

```bash
# Show firmware version for all ports (tabular)
sudo sfputil show fwversion -t

# Show firmware version for specific interfaces
sudo sfputil show fwversion -i Ethernet0,Ethernet4

# Show firmware version for an interface range
sudo sfputil show fwversion -i Ethernet16-80 -t

# Show firmware version mixing single interfaces and a range
sudo sfputil show fwversion -i Ethernet0,Ethernet4,Ethernet16-80 -t

# Show firmware version for specific vendor PN
sudo sfputil show fwversion -p Alphaxxxxxxxx001

# Show firmware version for a single port
sudo sfputil show fwversion Ethernet128

# Download firmware for multiple interfaces (without auto-activation)
sudo sfputil firmware download -i Ethernet0,Ethernet4 /path/to/firmware.bin

# Download firmware using an interface range
sudo sfputil firmware download -i Ethernet16-80 /path/to/firmware.bin

# Download firmware mixing single interfaces and a range
sudo sfputil firmware download -i Ethernet0,Ethernet4,Ethernet16-80 /path/to/firmware.bin

# Download firmware by vendor PN
sudo sfputil firmware download -p Deltaxxxxxxxxxx004 /path/to/firmware.bin

# Multiple vendor PNs with different firmware (download)
sudo sfputil firmware download \
  -p Deltaxxxxxxxxxx004 IJKL_Deltaxxxxxxxxxx004_0101_0301.bin \
  -p Deltaxxxxxxxxxx005 IJKL_Deltaxxxxxxxxxx005_0103_0303.bin \
  -p Epsilonyyyyyyyyy06 MNOP_Epsilonyyyyyyyyy06-VFF_5.bin \
  -p Epsilonyyyyyyyyy07 MNOP_Epsilonyyyyyyyyy07_VFF.2.bin

# Upgrade single port (verbose mode with per-port progress bar)
sudo sfputil firmware upgrade Ethernet0 /path/to/firmware.bin

# Upgrade multiple interfaces (summary progress mode)
sudo sfputil firmware upgrade -i Ethernet0,Ethernet4 /path/to/firmware.bin

# Upgrade using an interface range
sudo sfputil firmware upgrade -i Ethernet16-80 /path/to/firmware.bin

# Upgrade mixing single interfaces and a range
sudo sfputil firmware upgrade -i Ethernet0,Ethernet4,Ethernet16-80 /path/to/firmware.bin

# Upgrade by vendor PN
sudo sfputil firmware upgrade -p Alphaxxxxxxxx001 /path/to/alpha_fw.bin

# Multiple vendor PNs with different firmware (upgrade)
sudo sfputil firmware upgrade \
  -p Alphaxxxxxxxx001 /path/to/alpha_fw.bin \
  -p Gammayyyyyyyy002 /path/to/gamma_fw.bin
```
