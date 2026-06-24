# SONiC Console Monitor

## High Level Design Document

### Revision

|  Rev  |   Date      |   Author   | Change Description |
| :---: | :---------: | :--------: | ------------------ |
|  0.1  | 12 Jan 2026 | Cliff Chen | Initial version    |
|  0.2  | 27 Jan 2026 | Cliff Chen | Multi-process architecture, separate PTY Bridge and Proxy services |

---

## Table of Contents

- [Terminology and Abbreviations](#terminology-and-abbreviations)
- [1. Feature Overview](#1-feature-overview)
  - [1.1 Feature Requirements](#11-feature-requirements)
- [2. Design Overview](#2-design-overview)
  - [2.1 Architecture](#21-architecture)
  - [2.2 DTE Side](#22-dte-side)
  - [2.3 DCE Side](#23-dce-side)
- [3. Detailed Design](#3-detailed-design)
  - [3.1 Frame Structure Design](#31-frame-structure-design)
  - [3.2 DTE Side Service](#32-dte-side-service)
  - [3.3 DCE Side Services](#33-dce-side-services)
- [4. Database Changes](#4-database-changes)
- [5. CLI](#5-cli)
- [6. Example Configuration](#6-example-configuration)
- [7. References](#7-references)

---

## Terminology and Abbreviations

| Term | Definition |
|------|------------|
| DCE | Data Communications Equipment - Console Server side |
| DTE | Data Terminal Equipment - SONiC Switch (managed device) side |
| Heartbeat | Periodic signal used to verify link connectivity |
| Oper | Operational state (Up/Unknown) |
| PTM | Pseudo Terminal Master - Master side of a PTY pair |
| PTS | Pseudo Terminal Slave - Slave side of a PTY pair |
| PTY | Pseudo Terminal - Virtual terminal interface |
| PTY Bridge | Process that creates and bridges PTY pairs using socat |
| Proxy | Intermediate proxy process handling serial communication and heartbeat filtering |
| socat | Multipurpose relay tool for bidirectional data transfer between two channels |
| TTY | Teletypewriter - Terminal device interface |

---

## 1. Feature Overview

In data center networks, Console Servers (DCE) connect to multiple SONiC Switches (DTE) via serial ports for out-of-band management and console access during failures. In emergency troubleshooting scenarios. If link failures are not detected in time or in advance, it significantly increases the difficulty and time cost of troubleshooting. 

The console monitor service provides real-time automatic detection of link Oper state, enabling observability for serial connections and allowing operations teams to monitor link health status instantly. It provides critical support during incident response, improving troubleshooting efficiency and reducing business interruption time.


### 1.1 Feature Requirements

*   **Connectivity Detection**
    *   Determine whether the DCE ↔ DTE serial link is available (Oper Up/Unknown)
*   **Non-Interference**
    *   Does not affect normal console operations, including remote device cold reboot and system reinstallation
*   **Robustness**
    *   Automatically resumes detection after device reboot

---

## 2. Design Overview

### 2.1 Architecture

This diagram shows the high-level architecture of the console monitor feature over a single console link, including both DCE and DTE sides. DTE regularly send heartbeat frames to DCE via physical serial link. DCE side Proxy process filters heartbeat frames, updates STATE_DB, and forwards non-heartbeat data to user applications via PTY Bridge.

```mermaid
flowchart LR
  subgraph DCE["DCE (Console Server)"]
    proxy_dce["console-monitor-proxy.service"]
    picocom["consutil (user)"]
    subgraph PTY["PTY Bridge"]
      pty_pts["/dev/ttyUSB1-PTS"]
      pty_ptm["/dev/ttyUSB1-PTM"]
    end
    TTY_DCE["/dev/ttyUSB1 (physical serial)"]
    state_db["STATE_DB"]
  end

  subgraph DTE["DTE (SONiC Switch)"]
    dte_service["console-monitor-dte.service"]
    TTY_DTE["/dev/ttyS0 (physical serial)"]
    config_db["CONFIG_DB"]
  end

  %% DTE side: service sends heartbeat directly to serial
  dte_service -- check enabled --> config_db
  dte_service -- heartbeat --> TTY_DTE

  %% physical link
  TTY_DTE <-- serial link --> TTY_DCE

  %% PTY pair connection
  pty_pts <-- Socat --> pty_ptm

  %% proxy owns serial, filters RX, bridges to PTM
  TTY_DCE <-- read/write --> proxy_dce
  proxy_dce -- filter heartbeat & forward --> pty_ptm
  proxy_dce -- update oper_state --> state_db

  %% user application connects to PTS
  picocom <-- interactive session --> pty_pts
```

### Key Decisions

*   The DCE side cannot determine the initial state of the DTE device (rebooting or normal), therefore DCE cannot proactively send probe data to DTE, as it may interfere with the bootloader

### 2.2 DTE Side

The DTE side dynamically responds to configuration changes via Redis keyspace notification. When the feature is enabled, it periodically sends heartbeat frames to verify link connectivity.

*   **Direct Serial Access**
    *   The service directly opens the physical serial port (e.g., `/dev/ttyS0`) for sending heartbeats
*   **Heartbeat Mechanism**
    *   Checks the `enabled` field of `CONSOLE_SWITCH|controlled_device` in CONFIG_DB at startup
    *   Listens to Redis keyspace notifications to dynamically respond to enabled state changes
    *   Sends heartbeat frames every 5 seconds only when enabled=yes
    *   DTE → DCE unidirectional transmission ensures DTE does not receive interfering data during reboot phase
*   **Collision Risk**
    *   Normal data streams may contain data matching the heartbeat frame format, causing false positives
    *   Heartbeat frame design minimizes collision probability

### 2.3 DCE Side

The DCE side uses a multi-process architecture that separates the control plane from the data plane, reducing fault radius and improving reliability. Each console link has its own independent PTY Bridge and Proxy processes managed by systemd.

#### 2.3.1 DCE Service

The `console-monitor-dce.service` is the main control service that manages PTY Bridge and Proxy services via systemctl.

*   **Configuration Monitoring**
    *   Monitors `CONSOLE_PORT` and `CONSOLE_SWITCH` tables in CONFIG_DB
    *   Dynamically starts/stops services based on configuration changes

#### 2.3.2 PTY Bridge

Each link has an independent `console-monitor-pty-bridge@<link_id>.service` that creates PTY pairs. Enable user side auto recovery and non-interruptive console access.

*   **PTY Pair Creation**
    *   Uses `socat` to create two linked pseudo-terminals
    *   PTS symlink: `/dev/<prefix><link_id>-PTS` (for user applications like picocom)
    *   PTM symlink: `/dev/<prefix><link_id>-PTM` (for Proxy process)

#### 2.3.3 Proxy

Each link has an independent `console-monitor-proxy@<link_id>.service` for serial communication and heartbeat detection.

*   **Exclusive Serial Ownership**
    *   The only process holding the physical serial port file descriptor
*   **Heartbeat Filtering**
    *   Identifies heartbeat frames, updates STATE_DB, and discards heartbeat data
*   **Data Passthrough**
    *   Non-heartbeat data is transparently forwarded to PTM
---

## 3. Detailed Design

### 3.1 Frame Structure Design

#### 3.1.1 Frame Format

```
+----------+--------+-----+------+------+--------+---------+-------+----------+
| SOF x 3  | Version| Seq | Flag | Type | Length | Payload | CRC16 | EOF x 3  |
+----------+--------+-----+------+------+--------+---------+-------+----------+
|    3B    |   1B   | 1B  |  1B  |  1B  |   1B   |   N B   |  2B   |    3B    |
+----------+--------+-----+------+------+--------+---------+-------+----------+
```

| Field | Size | Description |
|-------|------|-------------|
| SOF x 3 | 3 bytes | Frame header sync sequence, 0x05 0x05 0x05 |
| Version | 1 byte | Protocol version, currently 0x01 |
| Seq | 1 byte | Sequence number, 0x00-0xFF cyclic increment |
| Flag | 1 byte | Flag bits, reserved field, currently 0x00 |
| Type | 1 byte | Frame type |
| Length | 1 byte | Payload length (value <= 24) |
| Payload | N bytes | Optional data payload |
| CRC16 | 2 bytes | Checksum, big-endian (high byte first) |
| EOF x 3 | 3 bytes | Frame trailer sync sequence, 0x00 0x00 0x00 |

**Frame Length Limits:**

*   **Maximum Frame Length**
    *   Excluding frame header and trailer, does not exceed 64 bytes
    *   Length value <= 24
    *   Frame length <= buffer size ensures alignment recovery when reading from mid-frame
*   **Buffer Size**
    *   64 bytes, adjustable as needed

**CRC16 Calculation:**

*   **Algorithm**
    *   CRC-16/MODBUS
*   **Calculation Range**
    *   From Version to Payload (excluding escape characters, using raw data)
    *   Excludes frame header, CRC16 itself, and frame trailer
*   **Byte Order**
    *   Big-endian (high byte first, low byte last)

#### 3.1.2 Frame Type Definition

| Type | Value (Hex) | Description |
|------|-------------|-------------|
| HEARTBEAT | 0x01 | Heartbeat frame |
| Reserved | 0x02-0xFF | Future extension |

#### Flag Field Definition

Flag bits are reserved, currently defaults to 0x00

#### 3.1.3 Heartbeat Frame Example
```
05 05 05 01 00 00 01 00 XX XX 00 00 00
└──┬──┘ │  │  │  │  │  └──┬─┘ └──┬──┘
   │    │  │  │  │  │     │      └── EOF x 3 (frame trailer sync sequence)
   │    │  │  │  │  │     └── CRC16 (calculated value)
   │    │  │  │  │  └──────── Length: 0 (no payload)
   │    │  │  │  └─────────── Type: HEARTBEAT (0x01)
   │    │  │  └────────────── Flag: 0x00
   │    │  └───────────────── Seq: 0x00 (sequence number)
   │    └──────────────────── Version: 0x01
   └───────────────────────── SOF x 3 (frame header sync sequence)
```

#### 3.1.4 Design Decisions

*   **Reliable Detection**
    *   Uses SOF and EOF, supports alignment recovery when reading from mid-frame
    *   Uses special control characters as frame delimiters, limits maximum frame length, introduces sliding buffer to distinguish heartbeat frames from arbitrary byte streams
*   **Fault Tolerance**
    *   To prevent a single byte bit error from causing frame sync loss, uses 3 repeated frame delimiters as sync sequence
*   **Transparent Transmission**
    *   Escape mechanism ensures frame content can use arbitrary bytes

#### 3.1.5 Key Assumptions

*   User data streams will not contain special characters: 0x05 (SOF), 0x00 (EOF), 0x10 (DLE)
*   The probability of bit errors occurring consecutively in 3 bytes is negligible

#### 3.1.6 Special Character Definition

| Character | Value (Hex) | Name | Description |
|-----------|-------------|------|-------------|
| SOF | 0x05 | Start of Frame | Frame start character |
| EOF | 0x00 | End of Frame | Frame end character |
| DLE | 0x10 | Data Link Escape | Escape character |

**Delimiter ASCII Definitions:**

*   **SOF (0x05)**
    *   ASCII ENQ (Enquiry)
    *   Non-printable control character, not interpreted by modern terminals and shells
    *   Historically used for polling communication (master asking if slave is ready), no longer used in modern systems
*   **EOF (0x00)**
    *   ASCII NUL (Null)
    *   Null character, typically ignored by terminals
    *   C language string terminator, does not appear in normal text output
*   **DLE (0x10)**
    *   ASCII DLE (Data Link Escape)
    *   Non-printable control character, specifically designed for data link layer escaping
    *   Conforms to its historical semantics, used to mark that the following character requires special handling

**Sync Sequence Design:**

*   **Frame Header Sync Sequence**
    *   3 consecutive SOF characters: 0x05 0x05 0x05
    *   Receiving any single SOF triggers state transition, rather than requiring 3 consecutive SOFs
    *   A single SOF bit error will not cause frame sync loss
*   **Frame Trailer Sync Sequence**
    *   3 consecutive EOF characters: 0x00 0x00 0x00
    *   Similarly, receiving any single EOF character triggers state transition
    *   Similarly provides bit error tolerance

#### 3.1.7 Escape Rules

When frame content (between frame header and trailer) contains special characters, escaping is required:

| Original Byte | Escaped |
|---------------|---------|
| 0x05 (SOF) | 0x10 0x05 |
| 0x00 (EOF) | 0x10 0x00 |
| 0x10 (DLE) | 0x10 0x10 |

**Escape Processing Description:**

*   **Sender**
    *   Constructs raw frame content (Version + Seq + Flag + Type + Length + Payload)
    *   Calculates CRC16 (based on raw unescaped data)
    *   Escapes entire frame content (including CRC16)
    *   Finally adds frame header and trailer
*   **Receiver**
    *   After removing frame header and trailer, remaining raw data (including escape characters) is stored in frame buffer
    *   First unescape the buffer
    *   Then perform CRC16 verification
    *   After verification passes, extract field data

#### 3.1.8 Frame Detection and Filtering

![ConsoleMonitorDataFlow](Console-Monitor-High-Level-Design/ConsoleMonitorDataFlow.png)

**Buffer Design:**

Since frames may be split during read operations, a sliding buffer is needed to store received byte streams for frame detection.

- Fixed size of 64 bytes
- Responsible for distinguishing frame data from user data

**Detection Algorithm:**

```txt
PROCEDURE PROCESS(F, data)
    // F is a frame-filter object with fields:
    //   F.buffer        : sequence of bytes
    //   F.in_frame      : boolean
    //   F.escape_next   : boolean
    // And helper procedures:
    //   FLUSH_AS_USER_DATA(F)
    //   DISCARD_BUFFER(F)
    //   TRY_PARSE_FRAME(F)
    //   FLUSH_BUFFER(F)

    FOR each byte b in data DO
        IF F.escape_next = TRUE THEN
            // previous byte was DLE; treat b as normal data
            APPEND(F.buffer, b)
            F.escape_next ← FALSE

            IF LENGTH(F.buffer) ≥ MAX_FRAME_BUFFER_SIZE THEN
                FLUSH_BUFFER(F)
            END IF

        ELSE IF b = DLE THEN
            // mark next byte as escaped (but keep DLE in buffer)
            APPEND(F.buffer, b)
            F.escape_next ← TRUE

        ELSE IF b = SOF THEN
            IF F.in_frame = FALSE THEN
                // bytes before SOF are user data
                FLUSH_AS_USER_DATA(F)
            ELSE
                // SOF inside a frame => previous frame incomplete; discard
                DISCARD_BUFFER(F)
            END IF
            F.in_frame ← TRUE

        ELSE IF b = EOF THEN
            TRY_PARSE_FRAME(F)
            F.in_frame ← FALSE

        ELSE
            APPEND(F.buffer, b)

            IF LENGTH(F.buffer) ≥ MAX_FRAME_BUFFER_SIZE THEN
                FLUSH_BUFFER(F)
            END IF
        END IF
    END FOR
END PROCEDURE

```

**Timeout Handling**

When no new data arrives within the timeout period, flush or discard the buffer based on `in_frame` state:
*   Timeout is dynamically calculated based on baud rate: `timeout = (10 / baud) × MAX_FRAME_BUFFER_SIZE × 3`
    *   If not in frame: flush buffer as user data
    *   If in frame: frame is incomplete, discard buffer contents
    *   Finally exit in-frame state

*   Formula explanation: 
    *   Base transmission time: `(10 bits / baud rate) × MAX_FRAME_BUFFER_SIZE`
        *   10 bits per character (1 start + 8 data + 1 stop bit)
    *   3x safety margin accounts for system-level processing delays
    *   Ignored delays:
        *   Cable propagation delay: ~1.5μs for 300m datacenter distance (signal travels at ~2×10⁸ m/s)
        *   Optical-electrical conversion: 2-20μs for serial-to-fiber converters
        *   System processing overhead: USB-to-Serial chip buffering, kernel TTY layer, and scheduling jitter are absorbed by the 3x margin
    *   Physical and conversion delays (μs) are 3 orders of magnitude smaller than serial transmission time (ms), making them negligible in timeout calculation

**Common Baud Rates and Timeouts:**

| Baud Rate | Per-Byte Time | 64-Byte Transmission | Timeout (3x) |
|-----------|---------------|----------------------|--------------|
| 9600      | 1.04 ms       | 66.7 ms              | 200.1 ms     |
| 19200     | 0.52 ms       | 33.3 ms              | 99.9 ms     |
| 38400     | 0.26 ms       | 16.7 ms              | 50.1 ms      |
| 57600     | 0.17 ms       | 11.1 ms              | 33.3 ms      |
| 115200    | 0.09 ms       | 5.6 ms               | 16.8 ms      |



---

### 3.2 DTE Side Service

#### 3.2.1 Service: `console-monitor-dte.service`

The DTE side service implements heartbeat sending functionality, dynamically responding to configuration changes via Redis keyspace notification.

*   **Parameter Acquisition**
    *   The service directly reads `/proc/cmdline` at startup
    *   Parses `console=<TTYNAME>,<BAUD>` parameter to obtain TTY name and baud rate
    *   If baud rate is not specified, defaults to 9600
*   **Startup Flow**
    1.  Read `/proc/cmdline` to parse serial port configuration
    2.  Open physical serial port (e.g., `/dev/ttyS0`)
    3.  Connect to Redis CONFIG_DB
    4.  Check the `enabled` field of `CONSOLE_SWITCH|controlled_device`
    5.  Subscribe to Redis keyspace notification to listen for configuration changes
*   **Heartbeat Mechanism**
    *   Monitors the `enabled` field of `CONSOLE_SWITCH|controlled_device` in CONFIG_DB
    *   If `"yes"`, sends heartbeat frame to serial port every 5 seconds
    *   If not `"yes"`, stops sending heartbeats
    *   Responds to configuration changes in real-time via keyspace notification

#### 3.2.2 Architecture Diagram

```mermaid
flowchart LR
  subgraph DTE["DTE (SONiC Switch)"]
    dte_service["console-monitor-dte.service"]
    TTY_DTE["/dev/ttyS0 (physical serial)"]
    config_db["CONFIG_DB"]
    cmdline["/proc/cmdline"]
  end

  subgraph DCE["DCE (Console Server)"]
    TTY_DCE["/dev/tty_dce"]
  end

  %% DTE side: service sends heartbeat directly to serial
  dte_service -- read tty & baud --> cmdline
  dte_service -- check enabled --> config_db
  dte_service -- subscribe keyspace notification --> config_db
  dte_service -- heartbeat --> TTY_DTE

  %% physical link
  TTY_DTE <-- serial link --> TTY_DCE
```

#### 3.2.3 Service Startup and Management

The DTE side service is managed by systemd, reading serial port configuration from the kernel command line at startup.

1.  **Service Startup**
    *   `console-monitor-dte.service` starts after `multi-user.target`
    *   Service reads `/proc/cmdline` to parse `console=<TTYNAME>,<BAUD>` parameter
    *   Opens corresponding serial port and connects to Redis
    *   Begins listening for configuration changes

```mermaid
flowchart TD
  A["Bootloader starts Linux kernel"] --> B["Kernel parses command line"]
  B --> C["/proc/cmdline available"]
  C --> D["systemd (PID 1) starts"]
  D --> E["systemd builds dependency graph"]
  E --> F["multi-user.target starts"]
  F --> G["console-monitor-dte.service is pulled up"]
  G --> H["Service reads /proc/cmdline"]
  H --> I["Parse console=ttyS0,9600"]
  I --> J["Open /dev/ttyS0 serial port"]
  J --> K["Connect to Redis CONFIG_DB"]
  K --> L["Check enabled status"]
  L --> M["Subscribe to keyspace notification"]
  M --> N{"enabled=yes?"}
  N -- yes --> O["Send heartbeat frame every 5s"]
  N -- no --> P["Wait for configuration change"]
  O --> Q["Listen for configuration changes"]
  P --> Q
  Q --> N
```

---

### 3.3 DCE Side Services

The DCE side consists of three types of services working together:

| Service | Type | Description |
|---------|------|-------------|
| `console-monitor-dce.service` | Control Plane | Main service that monitors CONFIG_DB and manages other services |
| `console-monitor-pty-bridge@<link_id>.service` | Data Plane | Creates PTY pairs for each link using socat |
| `console-monitor-proxy@<link_id>.service` | Data Plane | Handles serial communication and heartbeat detection |

#### 3.3.1 Service Architecture

![ConsoleMonitorServiceArchitecture](Console-Monitor-High-Level-Design/ConsoleMonitorServiceArchitecture.png)

#### 3.3.2 Timeout Determination

Default timeout period is 15 seconds. If no heartbeat or user data is received during this period, timeout is triggered.

#### 3.3.3 Oper State Determination

![ConsoleMonitorOperStateTransition](Console-Monitor-High-Level-Design/ConsoleMonitorOperStateTransition.png)

Each link maintains independent state, using dual detection mechanism of heartbeat and data activity:

*   **State becomes UP**: When a heartbeat frame is received, Proxy resets the heartbeat timeout timer and sets oper state to UP
*   **State becomes UNKNOWN**: When heartbeat timeout (default 15 seconds) triggers, additionally checks for recent serial data activity:
    *   If there was data activity within the timeout period (even without heartbeat), reset timer and continue waiting
    *   If neither heartbeat nor data activity occurred, set oper state to UNKNOWN
    *   When no heartbeat or data is received, the root cause cannot be determined, it could be link layer failure, system layer failure, or software layer failure.

State changes are written to STATE_DB.

STATE_DB entries:

*   Key: `CONSOLE_PORT|<link_id>`
*   Field: `oper_state`, Value: `Up` / `Unknown`
*   Field: `last_state_change`, Value: `<timestamp>` (state change timestamp)

#### 3.3.4 Service Startup and Initialization

##### DCE Service Startup

The `console-monitor-dce.service` starts in the following order:

1.  **Wait for Dependencies**
    *   Starts after `config-setup.service` and `database.service`
2.  **Connect to Redis**
    *   Establishes connection to CONFIG_DB
3.  **Initial Sync (Check Console Feature)**
    *   Checks the `enabled` field of `CONSOLE_SWITCH|console_mgmt` in CONFIG_DB
    *   If `enabled` is not `"yes"`, service continues running but does not start any services
    *   If `enabled` is `"yes"`, starts PTY Bridge and Proxy services for each link
4.  **Subscribe to Configuration Changes**
    *   Monitors the following CONFIG_DB keyspace events:
        *   `CONSOLE_PORT|*` - Serial port configuration changes
        *   `CONSOLE_SWITCH|*` - Console feature toggle changes
5.  **Start Services for Each Link** (only when enabled=yes)
    *   For each serial port configuration in CONFIG_DB:
        *   Start `console-monitor-pty-bridge@<link_id>.service` first
        *   Then start `console-monitor-proxy@<link_id>.service`
6.  **Enter Main Loop**
    *   Listen for configuration changes and manage services accordingly

##### PTY Bridge Service Startup

The `console-monitor-pty-bridge@<link_id>.service` performs:

1.  **Read PTY Symlink Prefix**
    *   Reads device prefix (e.g., `ttyUSB`) from `<platform_path>/udevprefix.conf`
2.  **Execute socat**
    *   Replaces current process with socat command
    *   Creates PTY pair with symlinks:
        *   `/dev/<prefix><link_id>-PTS` (for user applications)
        *   `/dev/<prefix><link_id>-PTM` (for Proxy)

##### Proxy Service Startup

The `console-monitor-proxy@<link_id>.service` performs:

1.  **Wait for Dependencies to be available**
    *   Reads device prefix (e.g., `ttyUSB`) from `<platform_path>/udevprefix.conf`. Fallback to `ttyUSB` if the config file doesn't exists.
    *   Waits for CONFIG_DB configuration to be available
    *   Waits for physical device is available (e.g., `/dev/ttyUSB1`)
    *   Waits for PTM symlink is available (e.g., `/dev/ttyUSB1-PTM`)
2.  **Initialize Resources**
    *   Connect to STATE_DB
    *   Open physical serial port
    *   Open PTM device
    *   Create frame filter
3.  **Enter Main Loop**
    *   Process serial data, filter heartbeats, update STATE_DB
4.  **Initial State**
    *   If no heartbeat or data activity within 15 seconds, `oper_state` is set to `Unknown`
    *   After receiving first heartbeat, `oper_state` becomes `Up`

#### 3.3.5 Dynamic Configuration Changes

*   Monitors CONFIG_DB configuration change events (including `CONSOLE_PORT` and `CONSOLE_SWITCH`)
*   Dynamically adds, removes, or restarts Proxy instances for links
*   **Console Feature Toggle Response**:
    *   When `enabled` of `CONSOLE_SWITCH|console_mgmt` changes from `"yes"` to other values, stops all existing Proxies
    *   When `enabled` becomes `"yes"`, starts corresponding Proxies based on `CONSOLE_PORT` configuration

#### 3.3.6 Service Shutdown and Cleanup

##### DCE Service Shutdown

When `console-monitor-dce.service` receives shutdown signal:

*   Stops all Proxy services first (via systemctl)
*   Then stops all PTY Bridge services (via systemctl)

##### Proxy Service Shutdown

When `console-monitor-proxy@<link_id>.service` stops:

*   **STATE_DB Cleanup**
    *   Deletes `oper_state` and `last_state_change` fields
    *   Preserves `state`, `pid`, `start_time` fields managed by consutil
*   **Buffer Flush**
    *   If filter buffer is non-empty, flush to PTM

##### PTY Bridge Service Shutdown

When `console-monitor-pty-bridge@<link_id>.service` stops:

*   **PTY Symlinks** are removed when socat exits

---

## 4. Database Changes

### 4.1 CONFIG_DB

#### 4.1.1 CONSOLE_SWITCH Table

| Key Format | Field | Value | Description |
|------------|-------|-------|-------------|
| `CONSOLE_SWITCH\|controlled_device` | `enabled` | `yes` / `no` | Enable/disable DTE side heartbeat sending |
| `CONSOLE_SWITCH\|console_mgmt` | `enabled` | `yes` / `no` | Enable/disable DCE side console monitor service |

**Example:**

```bash
admin@sonic:~$ sonic-db-cli CONFIG_DB HGETALL "CONSOLE_SWITCH|controlled_device"
{'enabled': 'yes'}

admin@sonic:~$ sonic-db-cli CONFIG_DB HGETALL "CONSOLE_SWITCH|console_mgmt"
{'enabled': 'yes'}
```

### 4.2 STATE_DB

#### 4.2.1 CONSOLE_PORT Table

| Key Format | Field | Value | Description
|------------|-------|-------|-------------|
| `CONSOLE_PORT\|<link_id>` | `oper_state` | `Up` / `Unknown` | Link operational state
| `CONSOLE_PORT\|<link_id>` | `last_state_change` | `<timestamp>` | Oper state change timestamp

**Example:**

```bash
admin@sonic:~$ sonic-db-cli STATE_DB HGETALL "CONSOLE_PORT|1"
 1) "state"
 2) "idle"
 3) "pid"
 4) ""
 5) "start_time"
 6) ""
 7) "oper_state"
 8) "Unknown"
 9) "last_state_change"
10) "1737273845"

admin@sonic:~$ sonic-db-cli STATE_DB HGETALL "CONSOLE_PORT|2"
 1) "state"
 2) "busy"
 3) "pid"
 4) "12345"
 5) "start_time"
 6) "1737270000"
 7) "oper_state"
 8) "Up"
 9) "last_state_change"
10) "1737060245"
```

**Note:**
- `state`, `pid`, `start_time` are managed by consutil
- `oper_state`, `last_state_change` are managed by console-monitor-dce service

---

## 5. CLI

### 5.1 console-monitor Command

The `console-monitor` command is the unified entry point for all console monitor services.

```bash
console-monitor <subcommand> [options] [arguments]
```

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `pty-bridge <link_id>` | Run PTY bridge for a port (exec socat) |
| `dce` | Run DCE (Console Server) control service |
| `proxy <link_id>` | Run proxy for a specific serial port |
| `dte [tty_name] [baud]` | Run DTE (SONiC Switch) heartbeat service |

#### Common Options

| Option | Description |
|--------|-------------|
| `-l, --log-level` | Set log level: `debug`, `info`, `warning`, `error`, `critical` (default: `info`) |

#### Examples

```bash
# Run PTY bridge for link 1 (creates PTY pair via socat)
console-monitor pty-bridge 1

# Run DCE control service with debug logging
console-monitor dce -l debug

# Run proxy for link 1
console-monitor proxy 1

# Run proxy for link 2 with debug logging
console-monitor proxy -l debug 2

# Run DTE service (auto-detect TTY from /proc/cmdline)
console-monitor dte

# Run DTE service with specified TTY and baud rate
console-monitor dte -l debug ttyS0 9600
```

### 5.2 Show line

Alias of `consutil show`

The `show line` command now adds Oper State and State Duration display:

```
admin@sonic:~$ show line
```

Output:

```
  Line    Baud    Flow Control    PID    Start Time      Device    Oper State    State Duration
------  ------  --------------  -----  ------------  ----------  ------------  ----------------
     1    9600        Disabled      -             -   Terminal1             Up       3d16h24m34s
     2    9600        Disabled      -             -   Terminal2        Unknown           1h5m17s
```

New columns:

| Column Name | Description |
|-------------|-------------|
| Oper State | Current operational state of console link |
| State Duration | Duration of current state (format: XyXdXhXmXs, only shows non-zero parts) |

### 5.3 Configuration Commands

#### 5.3.1 Enable/Disable Console Heartbeat (DTE Side)

```bash
config console heartbeat {enable|disable}
```

Control console heartbeat transmission on controlled device (DTE side). When enabled, the DTE side service will send heartbeat frames regularly to verify link connectivity.

**Sample Usage:**

```bash
# Enable console heartbeat on DTE side
admin@switch:~$ sudo config console heartbeat enable

# Disable console heartbeat on DTE side
admin@switch:~$ sudo config console heartbeat disable

# Verify configuration
admin@switch:~$ sonic-db-cli CONFIG_DB HGETALL "CONSOLE_SWITCH|controlled_device"
```

#### 5.3.2 Enable/Disable Console Monitor (DCE Side)

```bash
config console {enable|disable}
```

Console monitor service share same command with [SONiC Console Switch Utility](https://github.com/sonic-net/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md#33136-enabledisable-console-switch-feature). When enabled, the DCE side service will monitor heartbeats and update link operational states.

**Sample Usage:**

```bash
# Enable console monitor on DCE side
admin@console-server:~$ sudo config console enable

# Disable console monitor on DCE side
admin@console-server:~$ sudo config console disable

# Verify configuration
admin@console-server:~$ sonic-db-cli CONFIG_DB HGETALL "CONSOLE_SWITCH|console_mgmt"
```

---

## 6. Example Configuration

**DCE Side - CONFIG_DB:**

Refer to [Example Configuration](https://github.com/sonic-net/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md#33136-enabledisable-console-switch-feature)

**DTE Side - CONFIG_DB:**

```json
{
  "CONSOLE_SWITCH": {
    "controlled_device": {
      "enabled": "yes"
    }
  }
}
```

---

## 7. References

1. [SONiC Console Switch High Level Design](https://github.com/sonic-net/SONiC/blob/master/doc/console/SONiC-Console-Switch-High-Level-Design.md#scope)
2. [Systemd Generator Man Page](https://www.freedesktop.org/software/systemd/man/systemd.generator.html)
3. [Systemd Getty Generator Source Code](https://github.com/systemd/systemd/blob/main/src/getty-generator/getty-generator.c)
4. [Getty Explanation](https://0pointer.de/blog/projects/serial-console.html)
5. [ASCII Code](https://www.ascii-code.com/)
6. [agetty(8) - Linux manual page](https://man7.org/linux/man-pages/man8/agetty.8.html)
7. [agetty source code](https://github.com/util-linux/util-linux/blob/master/term-utils/agetty.c)
