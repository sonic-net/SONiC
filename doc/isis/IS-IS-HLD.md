# IS-IS Protocol Integration HLD

## Revision

| Revision | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | Oct 26 2026 | Unraous | Initial proposal |
| 1.1 | Nov 5 2026 | Unraous | Review alignment and integration test plan |
| 1.2 | Nov 18 2026 | Unraous | Three-table contract, named instances, independent L1/L2 parameters and full CLI |

## Scope and requirements

The baseline is FRR **10.7.1**, SONiC package **10.7.1-sonic-0**. Ranges,
defaults, source protocols and operational commands follow this version and
SONiC build options. Redistribution from `sharp` requires sharpd in the image.

IS-IS (Intermediate System to Intermediate System) runs in the bgp container
after zebra, using the shared supervisord daemon policy. The image must include
isisd, the utilities CLI and the FRR management framework.
Set `DEVICE_METADATA|localhost.frr_mgmt_framework_config=true` and restart the
corresponding bgp container before using this configuration path.

Instances are named within a VRF (Virtual Routing and Forwarding instance).
Non-default VRFs must exist. An interface binds to one instance in its actual
VRF; PortChannel member ports cannot be configured. Routed Ethernet,
PortChannel, VLAN, loopback and VLAN subinterfaces use existing interface tables.

## Configuration and runtime paths

```text
config isis / config interface isis
                  |
                  v
               ConfigDB
                  |
                  v
                frrcfgd ----> vtysh ----> FRR isisd

startup ConfigDB ----> packaged isisd.conf.j2 ----> FRR isisd
show isis configuration ----> ConfigDB
other show isis commands ----> rvtysh / vtysh ----> FRR
```

The implementation extends the existing handler and startup template.
Failed command application uses the framework's existing logging and cache
behavior. Failed state is not recorded as successfully applied. Subsequent
explicit configuration events use the normal handler path; there is no
automatic retry, rollback or compensation.

Routes use the existing FRR/zebra and SONiC route programming path. No new
APP_DB, ASIC_DB, STATE_DB or COUNTERS_DB tables, SWSS/syncd changes or SAI APIs
are required. Metric style is fixed to **wide**.

## ConfigDB schema

ConfigDB scalar values are strings. YANG supplies omitted defaults and validates
the final configuration. `route_map` is a list referencing `ROUTE_MAP_SET`,
with at most one item.

| Table | Key | Contents |
| --- | --- | --- |
| `ISIS_GLOBALS` | VRF\|instance | Instance attributes, per-level LSP/SPF intervals, SPF backoff |
| `ISIS_INTERFACE` | VRF\|interface | Parent instance, AF switches, interface attributes and per-level metric/Hello |
| `ISIS_REDISTRIBUTE` | VRF\|instance\|AF\|source\|level\|table_id | Redistribution metric and route-map |

### ISIS_GLOBALS

Row existence creates an instance. There is no global enable field.
An instance with no explicit attributes is retained using the standard
`NULL: NULL` ConfigDB sentinel. Instance names are 1–64 characters, matching
`[A-Za-z0-9_][A-Za-z0-9_.-]*`.

| Field | Type / range | Default |
| --- | --- | --- |
| net_title | NET matching `[0-9a-fA-F]{2}(\.[0-9a-fA-F]{4}){3,9}\.00` | optional |
| level | level-1, level-2, level-1-2 | level-1-2 |
| dynamic_hostname | boolean | true |
| lsp_mtu | 128–4352 bytes | 1497 |
| ipv6_multi_topology | boolean | false |
| overload | boolean | false |
| overload_on_startup | 0–86400 seconds | 0 |
| lsp_refresh_interval_level_1 / _level_2 | 1–65235 seconds | 900 |
| lsp_lifetime_level_1 / _level_2 | 350–65535 seconds | 1200 |
| lsp_generation_interval_level_1 / _level_2 | 1–120 seconds | 30 |
| spf_minimum_interval_level_1 / _level_2 | 1–120 seconds | 1 |
| spf_init_delay | 0–60000 milliseconds | optional |
| spf_short_delay | 0–60000 milliseconds | optional |
| spf_long_delay | 0–60000 milliseconds | optional |
| spf_hold_down | 0–60000 milliseconds | optional |
| spf_time_to_learn | 0–60000 milliseconds | optional |

Each instance saves one optional NET (Network Entity Title); it can be set or
replaced later. Without a NET the instance cannot establish normal adjacency.
Instances in the same VRF share a system ID; setting a NET validates system ID
consistency, and NET deletion requires a match to the saved NET. Instance
deletion, NET deletion and replacement use the corresponding FRR commands.
FRR owns the shared system-ID runtime state.

Each level independently satisfies `lifetime >= refresh + 300` and
`generation < refresh`, including omitted defaults. LSP updates render the
complete `lsp-timers level-N gen-interval ... refresh-interval ... max-lifetime ...`
command using all three effective values. SPF backoff has all five fields or
none, with `hold_down > time_to_learn`. Backoff controls SPF scheduling while
preserving the two minimum intervals.

### ISIS_INTERFACE

| Field | Type / range | Default |
| --- | --- | --- |
| instance_name | Same-VRF parent instance name | required |
| ipv4_enabled | boolean | false |
| ipv6_enabled | boolean | false |
| level | level-1, level-2, level-1-2 | level-1-2 |
| network_type | lan, p2p | lan |
| passive | boolean | false |
| metric_level_1 / _level_2 | 0–16777215 | 10 |
| hello_interval_level_1 / _level_2 | 1–600 seconds | 3 |
| hello_multiplier_level_1 / _level_2 | 2–100 | 10 |

AF (address family) enable creates the row with explicit parent binding.
Disabling the final AF deletes the entire row and its parameters; re-enabling
uses defaults. Attribute commands require at least one AF enabled. Changing
instance requires disabling both AFs first.

Saved L1/L2 attributes are independent. Runtime level is the intersection of
instance and interface levels; an empty intersection is rejected. Parent level
changes reapply circuit levels without rewriting saved interface fields.
LAN uses each level's Hello parameters; P2P uses L1 Hello parameters and retains
L2 values for a later return to LAN. `level` maps to `isis circuit-type`,
while `network_type=p2p` maps to `isis network point-to-point`.

The key VRF must match actual interface ownership. Routed-interface base-row
events detach old bindings when ownership no longer matches; prefix-row events
do not move bindings. To move an interface using CLI, remove its IS-IS binding,
change its actual VRF, then enable the AF against a same-VRF instance.

### ISIS_REDISTRIBUTE

| Key / field | Values / range | Default |
| --- | --- | --- |
| addr_family | ipv4, ipv6 | key |
| src_protocol (IPv4) | kernel, connected, local, static, rip, ospf, bgp, eigrp, nhrp, vnc, babel, sharp, openfabric, table | key |
| src_protocol (IPv6) | kernel, connected, local, static, ripng, ospf6, bgp, nhrp, vnc, babel, sharp, openfabric, table | key |
| level | level-1, level-2 | key |
| table_id | Ordinary source: 0; table source: 1–65535 | key |
| metric | 0–16777215 | 0 |
| route_map | ROUTE_MAP_SET name list, at most one item | optional |

The parent must exist and support the requested level. Different table IDs
are independent rows; redistribution to both levels uses two rows. `add`
completely replaces a same-key policy: an omitted metric becomes 0 and an omitted
route-map removes the old filter. Deletion removes the whole policy.

## SONiC CLI

The three groups support group-level `--namespace <ns>`, selecting both
ConfigDB and the bgp container. Example:
`config interface isis --namespace asic0 ipv4 Ethernet0 enable --instance CORE`.
Configuration commands support `--vrf <vrf>` (omitted below), defaulting to
`default`; interface VRF must match actual ownership. Per-level configuration
defaults to `--level both`.

Setters save explicit values, including explicit defaults. `reset` removes
the selected fields, restores effective defaults and preserves other fields
and the row. NET and SPF backoff use their own `del` commands. AF has no reset.

### Instance commands

```text
config isis add <instance>
config isis del <instance>
config isis net <instance> <NET>
config isis net del <instance> <NET>
config isis level <instance> <level-1|level-2|level-1-2>
config isis <dynamic-hostname|ipv6-multi-topology|overload> <instance> <enable|disable>
config isis lsp-mtu <instance> <bytes>
config isis overload-on-startup <instance> <seconds>
config isis <lsp-refresh-interval|max-lsp-lifetime|lsp-gen-interval|spf-interval> <instance> <seconds> [--level <level-1|level-2|both>]
config isis spf-backoff <instance> --init-delay <ms> --short-delay <ms> --long-delay <ms> --hold-down <ms> --time-to-learn <ms>
config isis spf-backoff del <instance>
config isis reset <instance> <level|dynamic-hostname|lsp-mtu|ipv6-multi-topology|overload|overload-on-startup>
config isis reset <instance> <lsp-refresh-interval|max-lsp-lifetime|lsp-gen-interval|spf-interval> [--level <level-1|level-2|both>]
```

`add` preserves an existing instance. `del` requires removal of interface
references and deletes the instance and its redistribution rows. Default VRF
uses FRR `router isis <instance>`; other VRFs use
`router isis <instance> vrf <vrf>`. `level-2` maps to `is-type level-2-only`.
Dynamic hostname uses `[no] hostname dynamic`, not the router's global hostname.
IPv6 multi-topology and AF enable are independent.

### Interface commands

```text
config interface isis <ipv4|ipv6> <ifname> enable --instance <instance> [--vrf <vrf>]
config interface isis <ipv4|ipv6> <ifname> disable [--vrf <vrf>]
config interface isis del <ifname> [--vrf <vrf>]
config interface isis passive <ifname> <enable|disable> [--vrf <vrf>]
config interface isis level <ifname> <level-1|level-2|level-1-2> [--vrf <vrf>]
config interface isis network-type <ifname> <lan|p2p> [--vrf <vrf>]
config interface isis <metric|hello-interval|hello-multiplier> <ifname> <value> [--level <level-1|level-2|both>] [--vrf <vrf>]
config interface isis reset <ifname> <level|network-type|passive> [--vrf <vrf>]
config interface isis reset <ifname> <metric|hello-interval|hello-multiplier> [--level <level-1|level-2|both>] [--vrf <vrf>]
```

`del` removes both AFs and the row. FRR interface context is
`interface <ifname>` for default or `interface <ifname> vrf <vrf>` otherwise.
AF enable maps to `ip router isis <instance>` or `ipv6 router isis <instance>`.

### Redistribution commands

```text
config isis redistribute add <instance> <AF> <source> <level-1|level-2> [--table-id <1-65535>] [--metric <value>] [--route-map <name>]
config isis redistribute del <instance> <AF> <source> <level-1|level-2> [--table-id <1-65535>]
```

AF is ipv4/ipv6. Table sources require `--table-id`; ordinary sources reject it.

### Operational commands

```text
show isis configuration [--vrf <vrf>] [--instance <instance>]
show isis summary [--vrf <vrf|all>] [--json]
show isis interface [<ifname>|--detail] [--vrf <vrf|all>] [--json]
show isis neighbor [<system-id>|--detail] [--vrf <vrf|all>] [--json]
show isis database [<lsp-id>] [--detail] [--vrf <vrf|all>] [--json]
show isis route [--level <level-1|level-2>] [--prefix-sid] [--backup] [--algorithm <128-255|all>] [--vrf <vrf|all>] [--json]
show isis topology [--level <level-1|level-2>] [--algorithm <128-255|all>] [--vrf <vrf|all>] [--json]
show isis hostname [--vrf <vrf|all>]
show isis spf-delay-ietf [--vrf <vrf|all>]
show isis flex-algo [<128-255>] [--vrf <vrf|all>]
show isis fast-reroute summary [--level <level-1|level-2>] [--vrf <vrf|all>]
show isis segment-routing node [--algorithm <128-255|all>]
show isis mpls-te router [--vrf <vrf|all>]
show isis mpls-te interface [<ifname>]
show isis mpls-te database [vertex [<id>]|edge [<IP>]|subnet [<prefix>]] [--detail|--json] [--vrf <vrf|all>]
show isis mpls ldp-sync [interface <ifname|all>]
```

Configuration displays saved and effective ConfigDB values. Other show commands
query FRR runtime state; VRF-capable entries default to `default`.
Interface/name and neighbor/system-ID are mutually exclusive with detail.
Database permits LSP ID and detail together. MPLS-TE database detail and JSON
are mutually exclusive. Runtime visibility into FRR features does not add
configuration support for those features.

## Configuration example

```shell
sudo config isis add CORE
sudo config isis net CORE 49.0001.0000.0000.0001.00
sudo config isis level CORE level-2
sudo config interface isis ipv4 Ethernet0 enable --instance CORE
sudo config interface isis ipv6 Ethernet0 enable --instance CORE
sudo config interface isis network-type Ethernet0 p2p
sudo config interface isis metric Ethernet0 20 --level level-2
sudo config interface isis ipv4 Loopback0 enable --instance CORE
sudo config interface isis passive Loopback0 enable
sudo config isis redistribute add CORE ipv4 connected level-2 --metric 30
sudo config save -y
show isis configuration --instance CORE
show isis neighbor
show isis database --detail
```

Equivalent saved rows:

```json
{
  "ISIS_GLOBALS": {
    "default|CORE": {"net_title": "49.0001.0000.0000.0001.00", "level": "level-2"}
  },
  "ISIS_INTERFACE": {
    "default|Ethernet0": {"instance_name": "CORE", "ipv4_enabled": "true", "ipv6_enabled": "true", "network_type": "p2p", "metric_level_2": "20"},
    "default|Loopback0": {"instance_name": "CORE", "ipv4_enabled": "true", "passive": "true"}
  },
  "ISIS_REDISTRIBUTE": {
    "default|CORE|ipv4|connected|level-2|0": {"metric": "30"}
  }
}
```

## Persistence and limits

Persist using `config save -y`. Cold startup reconstructs configuration from
ConfigDB using the packaged template or the existing command replay path.
This change does not establish IS-IS graceful restart, warm-reboot state
restoration or fastboot route preservation. Matching utilities/buildimage
versions are required; there is no old CLI compatibility or automatic schema
migration. Remove IS-IS configuration before downgrading to an older schema.

No new SNMP, REST or gNMI bindings are defined. Validation requirements for
configuration, binding, restart and forwarding are specified in the
[integration test plan](IS-IS-Test-Plan.md).

## References

- [Buildimage implementation PR #28789](https://github.com/sonic-net/sonic-buildimage/pull/28789)
- [Utilities CLI PR #4738](https://github.com/sonic-net/sonic-utilities/pull/4738)
- [Seven-node tests PR #28767](https://github.com/sonic-net/sonic-mgmt/pull/28767)
- [FRR 10.7.1 source baseline](https://github.com/FRRouting/frr/tree/f8c0b08dcb0c78f9e42b9b86ae70b049e4e617c1)
- [Force10 seven-node topology](https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/vars/topo_force10-7nodes.yml)
