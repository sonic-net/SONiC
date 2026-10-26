# IS-IS Northbound CLI Configuration

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [Overview](#overview)
- [Requirements](#requirements)
- [High Level Design](#high-level-design)
- [Config DB Enhancement](#config-db-enhancement)
- [CLI Reference](#cli-reference)
  - [Global Configuration](#global-configuration)
  - [Interface Configuration](#interface-configuration)
  - [Operational Commands](#operational-commands)
- [Configuration Example](#configuration-example)
- [References](#references)

### Revision

| Revision | Date        | Author  | Change Description |
| -------- | ----------- | ------- | ------------------ |
| 1.0      | Oct 26 2026 | Unraous | Initial proposal   |

### Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| IS-IS | Intermediate System to Intermediate System routing protocol |
| ConfigDB | SONiC Redis database used to store persistent configuration |
| VRF | Virtual Routing and Forwarding instance |
| NET | Network Entity Title identifying an IS-IS system and area |
| LSP | Link State PDU |
| FRR | Free Range Routing |

### Scope

This document describes the SONiC northbound Click CLI for configuring and monitoring IS-IS. It covers global process settings, interface settings, ConfigDB ownership, and operational show commands. IS-IS protocol behavior and FRR integration details are described in the related buildimage HLD.

### Overview

The IS-IS CLI provides `config isis` commands for process-level configuration and `config interface isis` commands for interface-level configuration. Configuration commands write to ConfigDB. The FRR management framework consumes the IS-IS ConfigDB tables and applies the corresponding configuration to FRR. The `show isis` command group retrieves operational state through FRR's `vtysh` interface.

### Requirements

1. The SONiC image must include the IS-IS CLI commands and the IS-IS support provided by the FRR management framework.
2. IS-IS process configuration is scoped to a VRF. When a VRF argument is omitted, the CLI uses `default`.
3. Interface commands operate on an existing interface alias.
4. The IS-IS process must be enabled before setting its NET, level, or dynamic-hostname option.

### High Level Design

The configuration and show paths are:

```text
config isis / config interface isis
              |
              v
          ConfigDB
              |
              v
           frrcfgd
              |
              v
             FRR

show isis ---> vtysh ---> FRR operational state
```

Configuration is split between three ConfigDB tables: `ISIS_GLOBALS` for process attributes, `ISIS_GLOBALS_TIMERS` for global LSP timers, and `ISIS_INTERFACE` for interface attributes. The CLI does not generate FRR configuration files directly.

### Config DB Enhancement

| ConfigDB table | Purpose |
| -------------- | ------- |
| `ISIS_GLOBALS` | IS-IS process settings, including NET, level, and dynamic hostname |
| `ISIS_GLOBALS_TIMERS` | LSP MTU, refresh interval, and lifetime |
| `ISIS_INTERFACE` | Per-interface enable state, metric, circuit type, and passive state |

The table schema and FRR translation behavior are defined by the related buildimage change.

### CLI Reference

All commands are run on the SONiC device with `sudo` or an equivalent privileged shell.

#### Global Configuration

| Command | Description |
| ------- | ----------- |
| `config isis enable [VRF]` | Enable IS-IS for the specified VRF. The default VRF is `default`. |
| `config isis disable [VRF]` | Disable IS-IS for the specified VRF. |
| `config isis net NET [VRF]` | Set the IS-IS NET for the specified VRF. |
| `config isis level {level-1\|level-2\|level-1-2} [VRF]` | Set the IS-IS level for the specified VRF. |
| `config isis hostname {enabled\|disabled} [VRF]` | Enable or disable dynamic hostname support for the specified VRF. |
| `config isis timer lsp-mtu MTU [VRF]` | Set the LSP MTU. Valid range: 128–4352. |
| `config isis timer lsp-refresh SECONDS [VRF]` | Set the LSP refresh interval. Valid range: 1–65535 seconds. |
| `config isis timer lsp-lifetime SECONDS [VRF]` | Set the LSP lifetime. Valid range: 350–65535 seconds. |

#### Interface Configuration

| Command | Description |
| ------- | ----------- |
| `config interface isis enable INTERFACE` | Enable IS-IS on an interface. |
| `config interface isis disable INTERFACE` | Disable IS-IS on an interface. |
| `config interface isis metric INTERFACE METRIC` | Set the interface metric. Valid range: 1–16777215. |
| `config interface isis circuit-type INTERFACE {p2p\|lan}` | Set the IS-IS circuit type. |
| `config interface isis passive INTERFACE {enable\|disable}` | Enable or disable passive mode on an interface. |

#### Operational Commands

| Command | Description |
| ------- | ----------- |
| `show isis summary` | Display IS-IS process summary. |
| `show isis neighbor` | Display IS-IS neighbors. |
| `show isis database` | Display the link-state database. |

Each show command accepts `-j` or `--json` for JSON output, and `-n` or `--namespace NAMESPACE` to select an ASIC namespace on a multi-ASIC device.

### Configuration Example

The following example enables IS-IS in the default VRF, configures a NET and Level 2 operation, and enables IS-IS on `Ethernet0` as a point-to-point circuit:

```shell
sudo config isis enable
sudo config isis net 49.0001.0000.0000.0001.00
sudo config isis level level-2
sudo config interface isis enable Ethernet0
sudo config interface isis circuit-type Ethernet0 p2p
sudo config interface isis metric Ethernet0 20

show isis summary
show isis neighbor
show isis database
```

### References

- [IS-IS enhancement HLD](https://github.com/sonic-net/sonic-buildimage/pull/28789) describes the FRR management framework, ConfigDB schema, and daemon integration.
- [IS-IS Click CLI implementation](https://github.com/sonic-net/sonic-utilities/pull/4738) implements the commands documented here.
- [Community Force10 7-node topology](https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/vars/topo_force10-7nodes.yml) provides the reusable topology definition for multi-node protocol testing.