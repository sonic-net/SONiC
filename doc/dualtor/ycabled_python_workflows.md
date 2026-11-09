# ycabled in Rust, appendix A: Python ycabled workflows

This appendix to [ycabled in Rust](ycabled_to_rust_hld.md) is its Section 3.3. It describes each workflow of Python ycabled, and what it writes on success and on failure. ycabled-rs does the same, except for the differences in [Section 4.5](ycabled_to_rust_hld.md#45-deliberate-behavior-differences).

## Content

- [ycabled in Rust, appendix A: Python ycabled workflows](#ycabled-in-rust-appendix-a-python-ycabled-workflows)
  - [Content](#content)
  - [3.3.1 Active-standby toggle](#331-active-standby-toggle)
  - [3.3.2 Active-standby probe](#332-active-standby-probe)
  - [3.3.3 Active-active toggle (self and peer)](#333-active-active-toggle-self-and-peer)
  - [3.3.4 Active-active forwarding state probe](#334-active-active-forwarding-state-probe)
  - [3.3.5 gRPC channel lifecycle](#335-grpc-channel-lifecycle)
  - [3.3.6 GracefulRestart](#336-gracefulrestart)
  - [3.3.7 Cable insertion and removal](#337-cable-insertion-and-removal)
  - [3.3.8 Telemetry](#338-telemetry)
  - [3.3.9 CLI commands](#339-cli-commands)
  - [3.3.10 Runtime knobs](#3310-runtime-knobs)

## 3.3.1 Active-standby toggle

1. orchagent writes APPL_DB `HW_MUX_CABLE_TABLE:<port>` `state` = `active` or `standby`.
2. ycabled reads `read_side` from STATE_DB `HW_MUX_CABLE_TABLE` and calls `toggle_mux_to_tor_a()` (upper ToR) or `toggle_mux_to_tor_b()` (lower ToR): active with read_side 1 means the upper ToR, active with read_side 2 means the lower ToR, and standby means the other one. If read_side is not 1 or 2, it calls `get_read_side()` first.
3. It writes STATE_DB `MUX_METRICS_TABLE` `xcvrd_switch_<state>_start` and `_end`, then STATE_DB `HW_MUX_CABLE_TABLE` `state`, `read_side` and `active_side`. The mux direction is not read back after the toggle.
   - **Success:** `state` is the requested state, `active_side` the side the mux was toggled to (1 for the upper ToR, 2 for the lower ToR), and `read_side` is unchanged.
   - **Failure:** the driver returns anything but `True`, raises, or the port has no driver. `state` is `unknown`, in the metrics field names too (`xcvrd_switch_unknown_start` and `_end`), and `active_side` is -1. `read_side` keeps its value, unless the cable is absent or its read side had to be read again and could not be; then it is -1 too. Nothing is retried.

```mermaid
sequenceDiagram
    participant L as linkmgrd
    participant O as orchagent
    participant Y as ycabled (YCableTableUpdateTask)
    participant P as Platform API
    participant D as Vendor driver and Y-cable
    L->>O: APPL_DB MUX_CABLE_TABLE Ethernet0 state=standby
    Note over O: MuxCableOrch reprograms neighbors and routes
    O->>Y: APPL_DB HW_MUX_CABLE_TABLE Ethernet0 state=standby
    Y->>Y: read_side from STATE_DB HW_MUX_CABLE_TABLE
    Y->>P: get_presence()
    opt read_side is not 1 or 2
        Y->>D: get_read_side()
    end
    Y->>D: toggle_mux_to_tor_a() or toggle_mux_to_tor_b()
    D-->>Y: True or False
    Note over Y: STATE_DB MUX_METRICS_TABLE<br/>xcvrd_switch_standby_start, xcvrd_switch_standby_end
    Y-->>O: STATE_DB HW_MUX_CABLE_TABLE state=standby<br/>(unknown if absent or failed), read_side, active_side
    Note over O: MuxStateOrch compares it with its own state
    O-->>L: STATE_DB MUX_CABLE_TABLE state=standby (unknown if they differ)
```

## 3.3.2 Active-standby probe

linkmgrd writes APPL_DB `MUX_CABLE_COMMAND_TABLE:<port>` `command=probe`. ycabled reads `read_side` from STATE_DB `HW_MUX_CABLE_TABLE`, calls `get_mux_direction()`, and writes APPL_DB `MUX_CABLE_RESPONSE_TABLE` `response`:

- **Success:** the direction is 1 or 2. `response` is `active` if it equals read_side, `standby` if not.
- **Failure:** the cable is absent, the port has no driver, or `get_mux_direction()` raises or returns anything but 1 or 2. `response` is `unknown`. Nothing is retried.
- **Read side not 1 or 2:** 0 (the NIC side) or -1 (not readable) never equals the direction, so `response` is `standby` (issue 31 in [Section 3.7](ycabled_python_known_issues.md#37-known-issues)).
- **Ignored:** a command other than `probe`, or a port without a STATE_DB `HW_MUX_CABLE_TABLE` entry. Nothing is written.

```mermaid
sequenceDiagram
    participant L as linkmgrd
    participant Y as ycabled (YCableTableUpdateTask)
    participant P as Platform API
    participant D as Vendor driver and Y-cable
    L->>Y: APPL_DB MUX_CABLE_COMMAND_TABLE Ethernet0 command=probe
    Y->>Y: read_side from STATE_DB HW_MUX_CABLE_TABLE
    Y->>P: get_presence()
    Y->>D: get_mux_direction()
    D-->>Y: 1 (upper ToR) or 2 (lower ToR)
    Y-->>L: APPL_DB MUX_CABLE_RESPONSE_TABLE Ethernet0<br/>response=active if it equals read_side, else standby (unknown on error)
```

## 3.3.3 Active-active toggle (self and peer)

- **Self:** APPL_DB `HW_MUX_CABLE_TABLE:<port>` `state` → `SetAdminForwardingPortState(portid=[read_side], state=[1 or 0])`, with read_side from STATE_DB `HW_MUX_CABLE_TABLE`.
- **Peer:** APPL_DB `HW_FORWARDING_STATE_PEER:<port>` `state` → the same with `portid=[1 - read_side]`, with read_side from STATE_DB `HW_MUX_CABLE_TABLE_PEER`.
- **Written:** STATE_DB `MUX_METRICS_TABLE` `xcvrd_switch_self_<state>_start` and `_end` (`peer` for a peer toggle), then `state`, `read_side` and `active_side` in the STATE_DB table read_side came from. `read_side` is written back unchanged. Unlike active-standby, `active_side` is the state the SoC reports, not a side number.
- **Success:** the reply names the requested port id. `state` is the requested state, and `active_side` the reported one, `active` or `standby`. If the SoC reports the opposite of the request, `state` is still the requested one.
- **Failure:** the RPC fails or reaches its 0.5 s deadline, or the reply is empty or names another port id. `state` and `active_side` are `unknown`, in the metrics field names too (`xcvrd_switch_self_unknown_start` and `_end`). Nothing is retried.
- **No channel:** ycabled tries once to set it up again. If that fails, it writes the same as for a failed RPC, without calling the SoC.
- **Read side -1** (no usable Loopback3): the request still goes to the SoC, with port id -1, or 2 for the peer (issue 30).
- **Ignored:** a state other than `active` or `standby`, or a port without an entry in the table. Nothing is written.

```mermaid
sequenceDiagram
    participant L as linkmgrd
    participant O as orchagent
    participant Y as ycabled (YCableTableUpdateTask)
    participant S as NIC SoC
    alt Self toggle
        L->>O: APPL_DB MUX_CABLE_TABLE Ethernet0 state=standby
        O->>Y: APPL_DB HW_MUX_CABLE_TABLE Ethernet0 state=standby
        Y->>Y: read_side from STATE_DB HW_MUX_CABLE_TABLE
        Y->>S: SetAdminForwardingPortState(portid=[read_side], state=[0])
        S-->>Y: AdminReply(portid, state)
        Note over Y: STATE_DB MUX_METRICS_TABLE xcvrd_switch_self_standby_*
        Y-->>O: STATE_DB HW_MUX_CABLE_TABLE state, read_side, active_side
        O-->>L: STATE_DB MUX_CABLE_TABLE state
    else Peer toggle
        L->>Y: APPL_DB HW_FORWARDING_STATE_PEER Ethernet0 state=standby
        Y->>Y: read_side from STATE_DB HW_MUX_CABLE_TABLE_PEER
        Y->>S: SetAdminForwardingPortState(portid=[1 - read_side], state=[0])
        S-->>Y: AdminReply(portid, state)
        Note over Y: STATE_DB MUX_METRICS_TABLE xcvrd_switch_peer_standby_*
        Y-->>L: STATE_DB HW_MUX_CABLE_TABLE_PEER state, read_side, active_side
    end
    Note over Y,S: No channel: set it up again once, otherwise write unknown
```

Because one thread handles every port, a SoC that does not answer delays the toggles of the other ports:

```mermaid
sequenceDiagram
    participant L as linkmgrd
    participant O as orchagent
    participant Y as ycabled (YCableTableUpdateTask)
    participant S0 as SoC of Ethernet0 (not responding)
    participant S4 as SoC of Ethernet4
    L->>O: APPL_DB MUX_CABLE_TABLE Ethernet0, Ethernet4 = standby
    O->>Y: APPL_DB HW_MUX_CABLE_TABLE Ethernet0 = standby
    O->>Y: APPL_DB HW_MUX_CABLE_TABLE Ethernet4 = standby
    Y->>S0: SetAdminForwardingPortState
    Note over Y,S0: thread blocked until the 0.5 s deadline
    Y-->>O: STATE_DB HW_MUX_CABLE_TABLE Ethernet0 = unknown
    Y->>S4: SetAdminForwardingPortState (0.5 s late)
    S4-->>Y: reply
    Y-->>O: STATE_DB HW_MUX_CABLE_TABLE Ethernet4 = standby
    O-->>L: STATE_DB MUX_CABLE_TABLE Ethernet4 = standby
```

## 3.3.4 Active-active forwarding state probe

linkmgrd writes APPL_DB `FORWARDING_STATE_COMMAND:<port>` `command=probe`. ycabled reads `read_side` from STATE_DB `HW_MUX_CABLE_TABLE`, calls `QueryAdminForwardingPortState(portid=[0, 1], state=[0, 0])`, and writes APPL_DB `FORWARDING_STATE_RESPONSE` `response` for this ToR and `response_peer` for the peer:

- **Success:** the reply has two port ids and two states. `response` is `active` if `state[read_side]` is true and `standby` if it is false, and `response_peer` likewise from `state[1 - read_side]`. The port ids in the reply are not checked.
- **Failure:** the RPC fails or reaches its 0.5 s deadline, or the reply does not have two port ids and two states. Both are `unknown`. Nothing is retried.
- **No channel:** ycabled tries once to set it up again. If that fails, both are `unknown`, without calling the SoC.
- **Read side -1** (no usable Loopback3): the RPC is still made, and both are `unknown`.
- **Probe counters:** every RPC, successful or not, increments the counters that telemetry publishes in `MUX_CABLE_INFO`.
- **Ignored:** a command other than `probe`, or a port without a STATE_DB `HW_MUX_CABLE_TABLE` entry. Nothing is written.

```mermaid
sequenceDiagram
    participant L as linkmgrd
    participant Y as ycabled (YCableTableUpdateTask)
    participant S as NIC SoC
    L->>Y: APPL_DB FORWARDING_STATE_COMMAND Ethernet0 command=probe
    Y->>Y: read_side from STATE_DB HW_MUX_CABLE_TABLE
    Y->>S: QueryAdminForwardingPortState(portid=[0, 1])
    S-->>Y: AdminReply(state=[ToR 0, ToR 1])
    Y-->>L: APPL_DB FORWARDING_STATE_RESPONSE Ethernet0<br/>response=state[read_side], response_peer=state[1 - read_side]
    Note over Y: The probe counters that telemetry<br/>publishes in MUX_CABLE_INFO go up by one
```

## 3.3.5 gRPC channel lifecycle

- **Target:** `soc_ipv4` from `MUX_CABLE`, or `soc_ipv6` if there is no IPv4 address, without the prefix length. IPv6 is written as `[addr]:50075`.
- **Creation:** channels are created at startup, when a cable is inserted, and by a toggle or probe of a port without one, which tries once. They are not recreated when CONFIG_DB changes.
- **Connectivity:** a callback records every state change (`READY`, `CONNECTING`, `IDLE`, `TRANSIENT_FAILURE`, `SHUTDOWN`) for `MUX_CABLE_INFO.grpc_connection_status`. On `TRANSIENT_FAILURE` or `IDLE` it also writes APPL_DB `FORWARDING_STATE_RESPONSE` `response=failure`, which linkmgrd handles as a connection failure.

```mermaid
sequenceDiagram
    participant Y as ycabled
    participant G as grpcio channel
    participant S as NIC SoC
    participant L as linkmgrd
    Note over Y: At startup, on insertion, or at the first<br/>toggle or probe of a port without a channel
    Y->>Y: target soc_ipv4 (or soc_ipv6) port 50075 from CONFIG_DB MUX_CABLE,<br/>TLS settings from CONFIG_DB GRPCCLIENT
    Y->>G: create the channel, subscribe to connectivity changes
    G->>S: connect on the first RPC
    loop every connectivity change
        G-->>Y: callback(state), on a grpcio thread
        Note over Y: grpc_connection_status = state, published in MUX_CABLE_INFO
        opt TRANSIENT_FAILURE or IDLE
            Y-->>L: APPL_DB FORWARDING_STATE_RESPONSE Ethernet0 response=failure
        end
    end
```

## 3.3.6 GracefulRestart

For each `MUX_CABLE` port with a SoC address (active-standby ports too, once any port is active-active), ycabled calls `NotifyGracefulRestartStart(tor)`, with `tor` = `UPPER_TOR` if read_side is 0 and `LOWER_TOR` otherwise, and reads the stream. When the stream ends, it waits `period` seconds from the last response (20 s if there was none or the call failed) and subscribes again. Responses are only logged; nothing is written to the DB.

```mermaid
sequenceDiagram
    participant Y as ycabled (YCableAsyncNotificationTask)
    participant S as NIC SoC
    Note over Y: One asyncio client per MUX_CABLE port with a SoC address
    loop forever
        Y->>S: NotifyGracefulRestartStart(tor)<br/>tor = UPPER_TOR if read_side is 0, else LOWER_TOR
        loop while the stream lasts
            S-->>Y: GracefulAdminResponse(guid, msgtype, notifytype, period)
            Note over Y: logged only
        end
        Note over Y,S: The stream is over, or the call failed
        Y->>Y: wait period of the last response, 20 s if there was none
    end
```

## 3.3.7 Cable insertion and removal

ycabled subscribes to STATE_DB `TRANSCEIVER_INFO`, written by xcvrd:

- **SET (inserted):** ignored if the port's driver is already initialized ([#882](https://github.com/sonic-net/sonic-platform-daemons/pull/882)); otherwise the port is initialized as at startup, with its cable type read again from CONFIG_DB `MUX_CABLE`.
- **DEL (removed):** STATE_DB `HW_MUX_CABLE_TABLE` gets `state=unknown` and `active_side=-1`, and the driver instance is dropped. `MUX_CABLE_INFO` and `MUX_CABLE_STATIC_INFO` are kept.

```mermaid
sequenceDiagram
    participant X as xcvrd
    participant Y as ycabled (YcableStateUpdateTask)
    participant P as Platform API
    participant D as Vendor driver and Y-cable
    participant S as NIC SoC
    participant T as STATE_DB
    alt Inserted
        X->>Y: STATE_DB TRANSCEIVER_INFO Ethernet0 SET
        alt Driver already initialized
            Note over Y: ignored
        else active-standby
            Y->>P: get_presence(), get_transceiver_info()
            Note over Y: vendor and model select the driver module
            Y->>D: create the driver, get_vendor()
            Y->>D: get_read_side(), get_mux_direction()
            Y->>T: HW_MUX_CABLE_TABLE, MUX_CABLE_STATIC_INFO,<br/>and MUX_CABLE_INFO for the first cable
        else active-active
            Note over Y: nothing more if the port already has a channel (issue 21)
            Y->>S: create the channel, QueryAdminForwardingPortState
            Y->>T: HW_MUX_CABLE_TABLE, HW_MUX_CABLE_TABLE_PEER, placeholder MUX_CABLE_INFO
        end
    else Removed
        X->>Y: STATE_DB TRANSCEIVER_INFO Ethernet0 DEL
        Y->>T: HW_MUX_CABLE_TABLE state=unknown, active_side=-1
        Note over Y: drop the driver, keep<br/>MUX_CABLE_INFO and MUX_CABLE_STATIC_INFO
    end
```

## 3.3.8 Telemetry

Every 60 s after the previous pass ends, for every port whose `MUX_CABLE.state` is valid, unless `XCVRD_LOG|Y_CABLE.disable_telemetry` is `True`:

- **active-standby:** 27 `MUX_CABLE_INFO` fields from the vendor driver (mux direction, switch counts, eye heights, temperatures, voltages, link status, firmware versions). If the port has no driver, nothing is written, and ERR "Error: Could not get port instance for muxcable info for Y cable port \<port\>" is logged. While a firmware download runs on the port, the firmware versions are copied from what `MUX_CABLE_INFO` already holds instead of being read from the cable; the other fields are still read from the cable.
- **active-active:** 4 RPCs (`QueryLinkState`, `QueryOperationPortState`, `QueryAdminForwardingPortState`, `QueryServerVersion`) fill 15 `MUX_CABLE_INFO` fields. The probe counters written are the counts before this pass, `unknown` until the first query of that kind.
- **Cable absent (either type):** the 27 active-standby fields are written with placeholder values (`unknown` or `N/A`).

`MUX_CABLE_STATIC_INFO` (read_side and 30 cursor values, active-standby only) is written at initialization only.

```mermaid
sequenceDiagram
    participant Y as ycabled (YcableInfoUpdateTask)
    participant D as Vendor driver and Y-cable
    participant S as NIC SoC
    participant T as STATE_DB MUX_CABLE_INFO
    loop 60 s after the previous pass
        loop each port whose MUX_CABLE state is valid, unless telemetry is disabled
            alt Cable absent
                Y->>T: 27 active-standby fields with placeholder values
            else active-standby
                Y->>D: mux direction, switch counts, eye heights, temperatures,<br/>voltages, link status, firmware versions
                D-->>Y: values
                Y->>T: 27 active-standby fields
            else active-active
                Y->>S: QueryLinkState, QueryOperationPortState,<br/>QueryAdminForwardingPortState, QueryServerVersion
                S-->>Y: replies
                Y->>T: 15 active-active fields
            end
        end
    end
    Note over Y,D: During a firmware download, the versions<br/>come from MUX_CABLE_INFO, not the cable
```

## 3.3.9 CLI commands

1. The CLI deletes old entries in the command, argument, response and result tables of the command.
2. For some commands, it writes the arguments to APPL_DB `<CMD>_ARG:<port>`.
3. It writes APPL_DB `<CMD>:<port>` with `<command field>=<value>`.
4. It waits on STATE_DB `<RSP>|<port>` for the response field, with a timeout of 1 s to 1000 s depending on the command.
5. ycabled calls the vendor driver. For an active-active `hwmode muxdirection` it answers the state it last published in STATE_DB `HW_MUX_CABLE_TABLE`, and asks the SoC only if there is none. It writes any result rows to STATE_DB `<RES>|<port>`, then the response field, then deletes the command key.

**Firmware versions during a download:** the vendor driver sets its `download_firmware_status` attribute to in progress when `download_firmware()` starts, and to finished or failed when it ends; ycabled only reads it. While it is in progress, `show muxcable firmware version` and telemetry ([Section 3.3.8](#338-telemetry)) do not call `get_firmware_version()`. They answer the nine `version_<nic|self|peer>_<active|inactive|next>` fields from STATE_DB `MUX_CABLE_INFO`: `N/A` if the port has no entry, `None` for a missing field. The values are therefore those of the last telemetry pass before the download. The command still reads the read side from the cable, to tell self from peer. Once the download has finished or failed, versions are read from the cable again; a failed download is also logged at ERR.

The command tables are listed in [Section 3.5.5](ycabled_to_rust_hld.md#355-cli-command-tables).

```mermaid
sequenceDiagram
    participant C as show or config muxcable
    participant Y as ycabled (YCableCliUpdateTask)
    participant D as Vendor driver, or the SoC
    C->>C: delete old command, argument, response and result entries
    opt Commands with arguments
        C->>Y: APPL_DB XCVRD_*_CMD_ARG Ethernet0 arguments
    end
    C->>Y: APPL_DB XCVRD_*_CMD Ethernet0 command field=value
    Note over C: waits for the response, 1 s to 1000 s depending on the command
    Y->>D: the command's driver calls
    D-->>Y: result
    Note over Y,D: active-active hwmode muxdirection answers from STATE_DB<br/>HW_MUX_CABLE_TABLE, and asks the SoC only if there is none
    opt Commands with results
        Y-->>C: STATE_DB XCVRD_*_RES Ethernet0 rows
    end
    Y-->>C: STATE_DB XCVRD_*_RSP Ethernet0 response field
    Y->>Y: delete APPL_DB XCVRD_*_CMD Ethernet0
```

## 3.3.10 Runtime knobs

CONFIG_DB `XCVRD_LOG|Y_CABLE`:

- `log_verbosity` = `debug` or `notice` sets the log level.
- `disable_telemetry` = `True` or `False` stops or resumes telemetry. It is written by `config muxcable telemetry`.

```mermaid
sequenceDiagram
    participant A as config muxcable telemetry, or an operator
    participant Y as ycabled (YCableCliUpdateTask)
    participant T as ycabled (YcableInfoUpdateTask)
    Note over A,Y: At startup, ycabled sets log_verbosity=notice
    A->>Y: CONFIG_DB XCVRD_LOG Y_CABLE log_verbosity, disable_telemetry
    Y->>Y: set the log level to debug or notice
    Y->>T: disable_telemetry flag, a process global
    Note over T: Each port of the next pass checks the flag
```
