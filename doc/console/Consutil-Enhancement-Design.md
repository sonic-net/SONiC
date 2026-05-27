# SONiC Consutil Connect Path Enhancement

# High Level Design Document

#### Revision 0.1

# Table of Contents

- [SONiC Consutil Connect Path Enhancement](#sonic-consutil-connect-path-enhancement)
- [High Level Design Document](#high-level-design-document)
- [Revision 0.1](#revision-01)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
- [1 Feature Overview](#1-feature-overview)
  - [1.1 Background](#11-background)
  - [1.2 Goals](#12-goals)
  - [1.3 Non-goals](#13-non-goals)
- [2 Design](#2-design)
  - [2.1 Original Design](#21-original-design)
  - [2.2 New Design](#22-new-design)
  - [2.3 Byte-Path Comparison](#23-byte-path-comparison)
- [3 Performance Analysis](#3-performance-analysis)
  - [3.1 Reduction in Kernel/User-Space Copies](#31-reduction-in-kerneluser-space-copies)
  - [3.2 Per-Keystroke Latency](#32-per-keystroke-latency)
  - [3.3 Throughput and Aggregate CPU Load at Scale](#33-throughput-and-aggregate-cpu-load-at-scale)
- [4 Existing SONiC Integration and Impact](#4-existing-sonic-integration-and-impact)
  - [4.1 DB Changes](#41-db-changes)
  - [4.2 CLI](#42-cli)
  - [4.3 Error Handling](#43-error-handling)
  - [4.4 Testing](#44-testing)

# List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

[Table 2: Byte-path comparison](#table-2-byte-path-comparison)

[Table 3: Kernel/user-space copies per byte](#table-3-kerneluser-space-copies-per-byte)

# Revision


| Rev | Date       | Authors             | Change Description |
| --- | ---------- | ------------------- | ------------------ |
| 0.1 | 05/15/2026 | Henry Huang (Nokia) | Initial version    |


# About this Manual

This document describes an implementation enhancement of the `consutil connect` / `connect line` interactive console-attach path in `sonic-utilities`. It is a focused enhancement document that complements the existing [SONiC Console Switch HLD](./SONiC-Console-Switch-High-Level-Design.md). The user-facing CLI surface, CONFIG_DB schema, STATE_DB schema, and reverse-SSH mechanism are unchanged.

# Scope

In scope: the implementation of the connect path inside `sonic-utilities` (`consutil/lib.py`, `consutil/main.py`, `connect/main.py`).

Out of scope: any change to the `CONSOLE_SWITCH` / `CONSOLE_PORT` CONFIG_DB schema, the `STATE_DB CONSOLE_PORT|<line>` schema, the reverse-SSH `bash.bashrc` injection, and the broader Console Switch feature design (covered by `SONiC-Console-Switch-High-Level-Design.md`).

# Definition/Abbreviation

### Table 1: Abbreviations


| Term        | Meaning                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| picocom     | Userspace serial-terminal program used to drive `/dev/tty<DRIVER><N>`                                                          |
| pexpect     | Python library that wraps a child process inside a pseudo-terminal and forwards bytes between the parent's stdio and the child |
| pty         | Pseudo-terminal pair (master + slave)                                                                                          |
| TTY         | TeleTYpewriter, terminal device                                                                                                |
| `os.execvp` | POSIX `execve(2)` wrapper that replaces the current process image with a new program                                           |
| STATE_DB    | SONiC redis DB for runtime state                                                                                               |


# 1 Feature Overview

## 1.1 Background

`consutil connect <line>` and `connect line <line>` both eventually launch `picocom` against `/dev/tty<DRIVER><N>` so the operator can drive the remote serial console. As originally implemented, the byte-level path from the operator's terminal to the remote serial port traversed two nested pexpect-managed pty pairs and two intermediate Python processes. Every byte the operator typed was copied between kernel space and user space several times before it reached the UART driver, and the same was true in reverse for every byte the remote device sent back. None of those intermediates inspect or transform the bytes when being forwarded, except for the picocom status header.

## 1.2 Goals

1. Eliminate the nested pexpect layers and the redundant Python processes from the interactive console data path.
2. Preserve the existing CLI surface, exit codes, banner text, escape-character behavior, and STATE_DB schema.
3. Preserve all existing error semantics (`LineBusyError`, `InvalidConfigurationError`, `LineNotFoundError`).
4. Keep the implementation centralized in `sonic-utilities` (primarily `consutil/lib.py`, with necessary plumbing changes in `consutil/main.py`) allowing for easier future enhancements through a unified, platform-independent code path.

## 1.3 Non-goals

- Changes to CONFIG_DB or STATE_DB schemas.
- New CLI commands or options.
- Platform specific behavior.

# 2 Design

## 2.1 Original Design

The original `connect line <N>` flow used two `pexpect.spawn` calls and two Python processes:

```python
# connect/main.py (legacy)
proc = pexpect.spawn("consutil connect <N>")   # pexpect spawn #1, pty pair A
proc.interact()                                 # forwards bytes between user TTY and pty A

# consutil/main.py (legacy)
session = ConsolePortInfo.connect()             # internally pexpect.spawn(picocom), pty pair B
session.interact()                              # forwards bytes between pty A slave and pty B master
```

The resulting byte path between the operator's terminal and the serial UART:

```
user TTY  →  bash  →  connect.py  →  pty A  →  consutil.py  →  pty B  →  picocom  →  /dev/tty<DRIVER><N>
```

Three userspace processes (`connect.py`, `consutil.py`, `picocom`) and two pexpect-allocated pty pairs (A, B) sit between the user's terminal and the serial driver.

When `consutil connect <N>` was invoked directly, rather than `connect line <N>` via which reverse SSH connects, the outer pexpect layer was skipped, but the inner `pexpect.spawn(picocom)` inside `ConsolePortInfo.connect()` was still on the byte path, so console data performance is still less than optimal when bytes are unnecessarily copied between kernel and user spaces.

## 2.2 New Design

The new flow uses a single shared Python entry point and a single `os.execvp` into bash:

```python
# connect/main.py and consutil/main.py both call:
console_connect(target, db)                     # shared entry in consutil/lib.py

# consutil/lib.py — ConsolePortInfo.connect()
os.execvp("/bin/bash", [
    "/bin/bash", "-c", CONSOLE_SESSION_SCRIPT,
    "console_connect", line_num, escape_display, picocom_cmd,
])
```

`CONSOLE_SESSION_SCRIPT` is implemented as a short bash session host kept as a string literal in `consutil/lib.py` to avoid maintaining a separate bash script file. It:

1. Spawns picocom in the background with stdin/stdout bound directly to `/dev/tty`.
2. Publishes `STATE_DB CONSOLE_PORT|<N>` `state=busy` with picocom's pid and start time.
3. `wait`s for picocom.
4. On the EXIT trap: marks the line idle in STATE_DB and restores the terminal to the original mode captured via `stty -g` at session start.
5. Exits with picocom's return code so callers see picocom's actual exit status.

Because `os.execvp` replaces the Python process image, after the call there is no Python interpreter and no extra pty pair on the byte path. The resulting byte path is:

```
user TTY  →  picocom  →  /dev/tty<DRIVER><N>
```

## 2.3 Byte-Path Comparison

### Table 2: Byte-path comparison


|                                                                | Original                                 | New         |
| -------------------------------------------------------------- | ---------------------------------------- | ----------- |
| Userspace processes between user TTY and `/dev/tty<DRIVER><N>` | 3 (`connect.py`, `consutil.py`, picocom) | 1 (picocom) |
| Pseudo-terminal pairs in the byte path                         | 2 (pexpect pty A, pty B)                 | 0           |
| Python interpreter dispatches per keystroke (steady state)     | 2                                        | 0           |
| `pexpect.spawn` calls per `connect line` invocation            | 2                                        | 0           |


# 3 Performance Analysis

## 3.1 Reduction in Kernel/User-Space Copies

Every pexpect forwarder runs the loop:

```c
n = read(input_fd, buf, n);     /* kernel-space → user-space copy of n bytes */
write(output_fd, buf, n);       /* user-space → kernel-space copy of n bytes */
```

Each forwarder therefore performs one kernel→user copy and one user→kernel copy per byte, plus the cost of two syscalls (mode switch + scheduler entry) and the Python interpreter dispatch needed to run the `interact()` forwarding loop.

Counting copies for one byte traveling from the operator's keystroke to the remote UART (and the symmetric path back):

### Table 3: Kernel/user-space copies per byte


| Direction      | Original                                                                                                  | New                                            |
| -------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| user → remote  | `connect.py` (read+write) + `consutil.py` (read+write) + picocom (read pty + write UART) = **6 copies**   | picocom (read pty + write UART) = **2 copies** |
| remote → user  | picocom (read UART + write pty B) + `consutil.py` (read+write) + `connect.py` (read+write) = **6 copies** | picocom (read UART + write pty) = **2 copies** |
| **Round-trip** | **12 copies**                                                                                             | **4 copies**                                   |


The new design eliminates **8 of the 12 kernel/user-space copies** per byte round-trip which is a reduction of approximately **67%** in the per-byte syscall + copy cost on the local box, and a corresponding reduction in the number of context switches needed per byte.

## 3.2 Per-Keystroke Latency

The dominant local-host latency contributor in the original design is the chain of `read → schedule → write` operations through the two Python pexpect forwarders. Each forwarder adds, per byte:

- One syscall pair (read + write): ~1–2 µs each on x86, slightly more on ARM CO platforms.
- One process schedule round-trip (I/O wakeup): typically 5–50 µs depending on system load.
- Python interpreter dispatch to run the `interact()` callback: typically 10–100 µs depending on GIL contention and bytecode caching.

With two pexpect forwarders, the original design adds approximately **30–300 µs of local-host latency per keystroke**, on top of the picocom + UART path. The new design removes this overhead entirely by making bytes go directly from the user's pty to picocom to the UART driver.

For a single keystroke on an otherwise-idle box, this latency reduction is below human perception in both designs because the serial baud rate dominates. The improvement only becomes user-visible when many sessions share a constrained CPU (see §3.3).

## 3.3 Throughput and Aggregate CPU Load at Scale

End-to-end per-session throughput is bounded by the serial baud rate (`9600 → ~1 KB/s`, `115200 → ~11.5 KB/s`), which is always the dominant bottleneck regardless of design. Per-session throughput therefore does not change in any user-visible way.

The benefit at scale is in **aggregate CPU load on console-aggregator boxes**. Dedicated console platforms are deployed as CPU-centric appliances whose primary job is fronting **dozens of serial lines** simultaneously. Additionally, these platforms are expected to handle light CPU-forwarded IP traffic between a small number of Ethernet ports, possibly running BGP. A typical full-load configuration of a console box is designed to withstand up to 48 active sessions during a Point of Presence cut-over, fleet boot, or large maintenance window. In that scenario, the per-session forwarding cost of the connect path is what determines how many sessions the box can sustain in parallel without BGP session flap, operator-visible keystroke lag, or tail drops.

Per active session, the original design ran two Python `pexpect.interact()` byte-forwarding loops in addition to picocom while the new design runs only picocom. picocom is a tight C `read()/write()` loop and consumes roughly an order of magnitude less CPU per byte than the equivalent Python forwarder that includes interpreter dispatch + Python GIL contention + two extra r/w syscall pairs per byte.

For a fully loaded console box with **48 active sessions** under heavy traffic (e.g. boot logs streaming back from every attached device at once), the aggregate CPU saved by removing the 96 Python forwarders makes the new design **roughly 5–10× more efficient at full scale**, freeing the CPU to absorb simultaneous heavy console output without backpressure while leaving headroom for more application services such as BGP and other SONiC management services.

# 4 Existing SONiC Integration and Impact

This section summarises how the enhancement interacts with the rest of SONiC. The intent of the new design is to be a drop-in replacement: every external contract (CONFIG_DB / STATE_DB schemas, CLI surface, exit codes) is preserved, and only the internal byte-forwarding mechanism changes.

## 4.1 DB Changes

None.

CONFIG_DB tables (`CONSOLE_SWITCH|console_mgmt`, `CONSOLE_PORT|<N>`) and STATE_DB schema (`CONSOLE_PORT|<N>` with `state` / `pid` / `start_time`) are unchanged. The writer of the STATE_DB busy/idle transitions moves from the legacy Python `ConsoleSession` lifecycle into the inline bash script's `trap ... EXIT`, but the keyspace and value semantics are identical.

## 4.2 CLI

No CLI changes. `connect line <N>` and `consutil connect <N>` both behave identically from the operator's perspective:

- Same connection banner: `Successful connection to line [<N>]` / `Press ^<X> ^X to disconnect`.
- Same disconnect mechanism (`^A ^X` or whatever the configured escape character is).
- Same exit codes (see [§4.3](#43-error-handling)).

## 4.3 Error Handling

The exception-to-exit-code mapping is preserved in the shared `console_connect()` entry point:


| Exception                    | Exit Code  | Meaning                                                       |
| ---------------------------- | ---------- | ------------------------------------------------------------- |
| `LineBusyError`              | 5          | Line is already held by another picocom instance.             |
| `InvalidConfigurationError`  | 4          | Required CONFIG_DB attribute missing (typically `baud_rate`). |
| `LineNotFoundError`          | 3          | Target line not found.                                        |
| `OSError` (from `os.execvp`) | propagates | `/bin/bash` missing or not executable; extremely rare.        |


Inside the bash script, picocom's exit code is propagated as the script's exit code, so `consutil connect 1; echo $?` reports picocom's actual return value (e.g. `0` on a clean disconnect via the escape sequence).

## 4.4 Testing

Unit tests in `src/sonic-utilities/tests/console_test.py` are updated to reflect the new flow:

- `test_console_port_info_connect_device_busy` — busy detection now happens at the `STATE_DB CUR_STATE.state == busy` check before `os.execvp`. The test populates `CUR_STATE` with `state=busy` and asserts `LineBusyError`.
- `test_console_port_info_connect_connection_fail` — mocks `os.execvp` with `side_effect=OSError(...)` and asserts the `OSError` propagates.
- `test_console_port_info_connect_success` — mocks `os.execvp` with `side_effect=SystemExit(0)`, then asserts the `argv` passed to `os.execvp` matches the documented contract: `["/bin/bash", "-c", <script>, "console_connect", <line>, <escape>, <picocom_cmd>]`.

The remaining tests in the file are unaffected because they either mock `ConsolePortInfo.connect` directly or exercise paths that do not reach `os.execvp`.