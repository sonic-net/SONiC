# BGP Unnumbered (RFC 5549) and Multi ASN Support in SONiC

## Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Definitions / Abbreviations](#definitions--abbreviations)
- [Overview and Requirements](#overview-and-requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
  - [CONFIG_DB schema for BGP Unnumbered](#config_db-schema-for-bgp-unnumbered)
  - [Rendered FRR config](#rendered-frr-config)
  - [VNET / non-default VRF support (orchagent)](#vnet--non-default-vrf-support-orchagent)
- [Implementation Approaches](#implementation-approaches)
  - [Approach 1 — Template dispatcher with `numbered/` and `unnumbered/` subdirs](#approach-1--template-dispatcher-with-numbered-and-unnumbered-subdirs)
  - [Approach 2 — Inlined templates](#approach-2--inlined-templates)
  - [CONFIG_DB schema for Multi ASN Support](#config_db-schema-for-multi-asn-support)
  - [bgpcfgd support for Multi ASN support](#bgpcfgd-support-for-multi-asn-support)
- [Configuration and Management](#configuration-and-management)
- [Warmboot and Fastboot](#warmboot-and-fastboot)
- [Testing](#testing)
- [References](#references)

## Revision

| Rev | Date       | Author    | Change Description                                                                                                                  |
| --- | ---------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 0.1 | 2026-05-16 | anish-n   | Initial draft. Captures issue #26960 use case and approach                              |

## Scope

This HLD adds support for **unnumbered BGP** over IPv6 link-local, IPv4 advertisements over an IPv6 nexthop(RFC 5549 extended-next-hop) and Multi ASN support in SONiC through  `CONFIG_DB` → `bgpcfgd` → `FRR`. It tracks the solution for [sonic-net/sonic-buildimage#26960](https://github.com/sonic-net/sonic-buildimage/issues/26960), and additionally includes changes to support unnumbered BGP in a VNET/VRF space

In scope:

- `BGP_NEIGHBOR` key-namespace broadening to accept an interface name.
- FRR Jinja-template changes to `dockers/docker-fpm-frr/frr/bgpd/templates/general/` with two viable template approaches
- Orchagent changes (`vnetorch.cpp`) for IPv6 link-local IP2Me 
- Orachagent changes (`vnetorch.cpp`) to support ECMP across multiple LLv6 nexthops
- Multi ASN support in SONiC, following FRR's support for this feature https://docs.frrouting.org/en/latest/bgp.html#multiple-autonomous-systems


## Definitions / Abbreviations

| Term              | Definition                                                                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Unnumbered BGP    | A BGP session that runs over an IPv6 link-local address discovered via Router Advertisements, with no globally routable IP on either end. |
| RFC 5549 / 8950   | "Advertising IPv4 NLRI with an IPv6 Next Hop." Announced as the `extended-next-hop` BGP capability.                                       |
| LLv6              | IPv6 link-local address (`fe80::/10`).                                                                                                    |
| `BGP_NEIGHBOR`    | Existing CONFIG_DB table; today keyed on IPv4/IPv6 address only.                                                                          |
| `bgpcfgd`         | SONiC daemon that reflects CONFIG_DB state into FRR config via Jinja templates.                                                           |
| IP2Me             | An ASIC route entry installed by SONiC for every locally-owned IP, trapping matching packets to CPU.                                      |
| VNET / VRF        | A non-default routing instance. In SONiC, VNETs are VxLAN-tunnel VRFs created by `VNETOrch`; bare VRFs are created by `VRFOrch`.          |

## Overview and Requirements

Today, SONiC bgpcfgd configures BGP exclusively through IP-keyed entries in `CONFIG_DB.BGP_NEIGHBOR`. There is no way to express:

```text
neighbor PortChannel101 interface remote-as 64001
```

While FRR supports this and most modern DC fabrics rely on it, operators currently have to use either manual vtysh or `frrcfgd` to configure this, this HLD describes support for `bgpcfgd`, and additional support in orachagent/sonic-swss to enable LLv6 networking, specifically:

1. Extend `BGP_NEIGHBOR` so the key can be an **interface name** (`<vrf>|<intf>`, `PortChannel*`, `Ethernet*`, `Po.<subtintf>*`). No new table; numbered-row schema unchanged.
2. Extend the FRR Jinja templates in `dockers/docker-fpm-frr/frr/bgpd/templates/general/` so an interface-keyed row renders the unnumbered FRR BGP config, while IP-keyed rows render the existing config
3. Add a `PEER_UNNUMBERED` peer-group at the FRR side, carrying multi Address Family config
4. Extend orchagent (`vnetorch.cpp`, parallel to the merged `vrforch.cpp` change in PR #3973) so that LLv6 traffic destined to the device in a VNET is trapped to CPU and addionally extend it so that RFC 5549 duplicate-IP ECMP routes are programmed correctly in ASIC_DB
5. The rendered BGP session will come up over IPv4 if an IPv4 /30 or /31 IP is configured on the interface. If an IPv4 address is not configured, it will discover the peer's IPv6 link local address using Router Advertisements received from the peer. Upon discovering the v6 link local address of the peer it will establish the session over v6 link local(https://docs.frrouting.org/en/latest/bgp.html#clicmd-neighbor-PEER-interface-v6only-peer-group-NAME). 
6. For these sessions we configure the BGP attribute `extended-next-hop`, so both IPv4 and IPv6 NLRI can be exchanged on the single session, and we enable both v4 and v6 address families by default, an optional new field `af: v4/v6/both` is introduced, such that if just v4 neighbor/bgp activation is desired then af should be specified as v4, just v6 then v6, and both if v4 and v6 both are desired over this session, with the default being both for BGP unnumbered. This is an attribute in the `BGP_NEIGHBOR` table
7. Unnumbered BGP MUST work for neighbors that live in the **default** VRF **and** in a **non-default VRF / VNET**. This implies:
   - **LLv6 IP2Me** routes (`fe80::/10` catch-all) MUST be installed in every non-default VR at create time so that BGP TCP/179 and NDP packets in that VRF are trapped to CPU instead of silently dropped.
   - **RFC 5549 ECMP** routes (multiple egress interfaces sharing the same well-known link-local nexthop placeholder, e.g. `169.254.0.1`) MUST be programmed as multi-member next-hop groups in `ASIC_DB`, not collapsed to a single next-hop.

In addition to the above, we introduce changes in bgpcfgd to accept an ASN on a per VRF/VNET level, so that a BGP session using a different ASN can be initated on SONiC, this is based on FRR feature support for the same: https://docs.frrouting.org/en/latest/bgp.html#multiple-autonomous-systems

## Architecture Design

No new daemons, managers, or tables.

```
                       (unchanged today)
+---------------+         +-----------+         +----------------------+
|  CONFIG_DB    | ----->  | bgpcfgd   | <-----> | FRR (bgpd via vtysh) |
|  BGP_NEIGHBOR |         | managers  |         |                      |
+---------------+         +-----------+         +----------------------+
                                ^
                                |
                                v
                +--------------------------------------+
                | templates/general/                   |
                |   instance.conf.j2                   |   
                |   peer-group.conf.j2                 |   
                |   policies.conf.j2                   |
                +--------------------------------------+

+----------------------+        +---------------+         +-----------+         +----------------------+
| FRR (bgpd via vtysh) |        |CONFIG_DB: VNET| ----->  | swss /    | ----->  | syncd → SAI → ASIC   |
|     Routes           |        |  VRF, INTF    |         | orchagent |         |                      |
|                      | -----> |APP_DB: Routes |         | (vnetorch,|         |                      |
+----------------------+        +---------------+         |  vrforch) |         |                      |
                                                          +-----------+         +----------------------+
                                                                |                     ^
                                                                v  (this HLD)        /
                                                +--------------------------------------+
                                                | On VR create:                        |
                                                |   addLinkLocalRouteToMe(fe80::/10)   |
                                                | doRouteTask<VNetVrfObject>:          |
                                                |   RFC 5549 dup-IP ECMP fan-out       |
                                                +--------------------------------------+
```



## High-Level Design

### CONFIG_DB schema for BGP Unnumbered
#### BGP_NEIGHBOR schema:

```
BGP_NEIGHBOR|{{VRF/VNET-name}}|{{Peer-name}}:
		        "admin_status": {{up/down}}, (Optional)
            "asn": {{Peer ASN}},
            "holdtime": {{BGP Hold Time}}, (Optional, default 180)
            "keepalive": {{BGP Keep Alive Time}}, (Optional, default 60)
            "name": {{Peer name}},
            "nhopself": {{nhopself}}, (Optional)
            "rrclient": {{rrclient}}, (Optional)
            "af": {{v4/v6/both}} (Optional and only applicable to BGP unnumbered for now, if absent defaulted to both) >>> New
```
Additions:
- Peer-name: will be accepted as a Interface, PortChannel, Vlan and Ethernet/Portchannel subinterface
- "af": Newly added optional field which is only applicable to BGP unnumbered, if set to v4, only the v4 advertisements will be activated, if set to v6, only the v6 advertisements will be activated, and if set to both OR absent this data member both v4 and v6 are activated  

Example configuration displaying the use of a Link Local Ipv6 interface with BGP Unnumbered(existing schema included for completeness):
```
PORTCHANNEL_INTERFACE|PortChannel102
    ipv6_use_link_local_only = enable

BGP_NEIGHBOR|PortChannel102
    asn = 64600
    admin_status = up
    local_addr = 10.1.0.32
    name = ARISTA02T1
```

#### Rendered FRR config

For an unnumbered neighbor:

```
router bgp 65100
  neighbor PEER_UNNUMBERED peer-group
  neighbor PortChannel102 interface peer-group PEER_UNNUMBERED
  neighbor PEER_UNNUMBERED capability extended-nexthop
  neighbor PortChannel102 remote-as 64600
  neighbor PortChannel102 description ARISTA02T1
  address-family ipv4 unicast
    neighbor PEER_UNNUMBERED route-map FROM_BGP_PEER_UNNUMBERED in
    neighbor PEER_UNNUMBERED route-map TO_BGP_PEER_UNNUMBERED out
    neighbor PortChannel102 activate
  exit-address-family
  address-family ipv6 unicast
    neighbor PEER_UNNUMBERED route-map FROM_BGP_PEER_UNNUMBERED in
    neighbor PEER_UNNUMBERED route-map TO_BGP_PEER_UNNUMBERED out
    neighbor PortChannel102 activate
  exit-address-family
!
route-map FROM_BGP_PEER_UNNUMBERED permit 100
route-map TO_BGP_PEER_UNNUMBERED   permit 100
```

*Key callouts in the above config:*
-The session-level peer-group is `PEER_UNNUMBERED` instead of a v4 specific peer group and another v6 specific peer group as it is defined for the numbered BGP sessions. This is because FRR allows exactly one session-level peer-group binding per neighbor, regardless of which AF block it appears in
- ```neighbor <intf> activate``` in the v4 and v6 block is driven by the `af` data member in `BGP_NEIGHBOR` table
- ```neighbor PEER_UNNUMBERED capability extended-nexthop```: If you are peering over a v6 Global Address then turning on this command will allow BGP to install v4 routes with v6 nexthops if you do not have v4 configured on interfaces.

### VNET / non-default VRF support (orchagent)

Unnumbered BGP inside a VNET requires two orchagent changes, both in `orchagent/vnetorch.cpp`. These mirror the already-merged `vrforch.cpp` change in PR #3973 (which only covered bare VRFs created via `VRFOrch`).

#### 1. LLv6 IP2Me route in every VNET VR

`RouteOrch`'s constructor installs `fe80::/10` IP2Me only in the **default** virtual router. Without an equivalent install in VNET VRs, BGP TCP/179 and NDP packets sourced/destined to an LLv6 address inside a VNET are silently dropped at the chip.

#### 2. RFC 5549 duplicate-IP ECMP in `doRouteTask<VNetVrfObject>`

For unnumbered ECMP, FRR/Zebra installs every path via the same well-known LLv6 placeholder (e.g. `169.254.0.1`) — only the egress interface differs across paths. Today's `doRouteTask<VNetVrfObject>` builds the next-hop-group string from `nh.ips.getIpAddresses()`, which is a `set<IpAddress>` that **de-duplicates** equal IPs. Result: every ECMP member beyond the first is silently dropped, and the route is programmed as a single next-hop instead of an NHG.

Fix: Preserve the original IP addresses in a vector/string instead of a set.


## Implementation Approaches

Two implementations were prototyped end-to-end . Both produce identically rendered FRR config. They differ only in code organisation.

### Approach 1 — Template dispatcher with `numbered/` and `unnumbered/` subdirs
Draft PR: https://github.com/sonic-net/sonic-buildimage/pull/27308
Splits each top-level template into two parallel implementations under `general/numbered/` and `general/unnumbered/`, with a thin macro dispatcher in `general/router.j2`:

```
dockers/docker-fpm-frr/frr/bgpd/templates/general/
├── router.j2                       (new — dispatcher macro)
├── instance.conf.j2                (2-line wrapper: calls general_routing("instance"))
├── peer-group.conf.j2              (2-line wrapper)
├── policies.conf.j2                (2-line wrapper)
├── numbered/{instance,peer-group,policies}.conf.j2     (verbatim copies of upstream)
└── unnumbered/{instance,peer-group,policies}.conf.j2   (unnumbered branch)
```

```jinja
{# router.j2 #}
{% macro general_routing(template_name) %}
{%- set is_unnumbered = neighbor_addr is defined
                       and not ((neighbor_addr | ipv4) or (neighbor_addr | ipv6)) -%}
{%- if is_unnumbered -%}
{%- include "bgpd/templates/general/unnumbered/" + template_name + ".conf.j2" -%}
{%- else -%}
{%- include "bgpd/templates/general/numbered/"   + template_name + ".conf.j2" -%}
{%- endif -%}
{% endmacro %}
```

**Pros:** file-level separation; the `numbered/` files are byte-identical to upstream master; easy to add a third branch depending on various metadata, possibility of splitting v4 and v6 in the future and simplify the reading and maintenance of BGP templates.

**Cons:** Unified changes and logic is less possible, and the same changes may need to be replicated across multiple templates

### Approach 2 — Inlined templates
Draft PR: https://github.com/sonic-net/sonic-buildimage/pull/27370
Keeps the existing three template files in place and adds an `{% if is_unnumbered %} … {% else %} … {% endif %}` guard inside each. No new files, no subdirs, no dispatcher.

```
dockers/docker-fpm-frr/frr/bgpd/templates/general/
├── instance.conf.j2     (inline if/else for unnumbered)
├── peer-group.conf.j2   (inline if/else; emits PEER_UNNUMBERED in unnumbered branch)
└── policies.conf.j2     (inline if/else; emits FROM/TO_BGP_PEER_UNNUMBERED in unnumbered branch)
```


**Pros:** smallest possible diff (3 files changed, 0 added, 0 moved); single file per concept; no new template indirection; conceptually closest to "this is exactly what you'd write if you'd designed unnumbered support from day one."

**Cons:** Complexity in managing files increased, unnumbered peer groups are not entirely compatible with existing v4 and v6 peers which increases branching logic.


**Recommendation:** **Approach 2 (inlined).** For now choose Approach 2, and then take up an effort to split the templates logically across v4, v6, unnumbered or other possible metadata differences for different neighbor types

### CONFIG_DB schema for Multi ASN Support
#### VNET schema:
```
VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "scope": {{"default"}} (OPTIONAL)
    "peer_list": {{vnet_name_list}} (OPTIONAL)
    "asn": {{router's asn for BGP session}} (OPTIONAL) >>> New
```
Similar to the above, asn support can be introduced to VRF config_db tables

#### Rendered FRR configuration using the ASN above
```
  router bgp 4210000101 vrf Vnet1001
    ...
  exit
```

### bgpcfgd support for Multi ASN support
- Check if BGP_NEIGHBOR is configured on a VNET
- Acquire the VNET table associated with the BGP_NEIGHBOR
- Check if VNET table has an asn field set
- Use the asn field in the router bgp command as part of applying any operation, sample code can be found below

```python
cmd = (
  "router bgp %s vrf %s\n %s\n"
  % (vrf_asn if vrf_asn else bgp_asn, vrf, enable_bgp_suppress_fib_pending_cmd)
) + cmd + "\nexit"
```

## Configuration and Management

### CLI / YANG

#### Yang
Yang models will be enhanced to support:
- Interfaces as Peer name in BGP_NEIGHBOR
- af field in BGP_NEIGHBOR
- VNET table asn field to modify the VRF BGP instance's ASN

#### CLI

`show ip bgp summary`, `show bgp summary`, and `show runningconfiguration bgp` already display interface-keyed and ASN information correctly (native FRR behavior). No changes required

## Warmboot and Fastboot

Unnumbered BGP uses RA-driven peer discovery. On a warm-boot, FRR's BGP graceful-restart restarts the control plane while the data plane preserves forwarding. The kernel must continue to advertise/accept RAs through the warm-boot window for the LL address to remain stable — this is the existing behavior when `ipv6_use_link_local_only=enable` is set.

No additional warmboot-handler or fastboot-handler changes. Control-plane downtime is unchanged relative to numbered BGP.

## Testing

### Unit tests (bgpcfgd)

- IP-keyed `neighbor_addr` renders numbered branch only (asserts `PEER_V4`/`PEER_V6` present, `PEER_UNNUMBERED` absent).
- Interface-keyed `neighbor_addr` renders unnumbered branch only (asserts `neighbor X interface peer-group PEER_UNNUMBERED`, both AFs activated, `FROM/TO_BGP_PEER_UNNUMBERED` route-maps present).
- `neighbor_addr` undefined renders the numbered branch (preserves golden tests).

The full bgpcfgd suite MUST continue to pass.

### Unit tests (orchagent / sonic-swss)

`sonic-swss/tests/test_vnet.py` adds:

- `test_vnet_local_route_ecmp_duplicate_ip` — two ifnames + same nexthop IP create a 2-member NHG with two distinct RIFs in ASIC_DB.
- `test_vnet_local_route_ecmp_transition` — route oscillates `2-NH → 1-NH → 2-NH`; verifies NHG creation, removal, and re-creation cleanly.

### Integration tests (sonic-mgmt)

`tests/bgp/test_bgp_link_local.py` has three variants:

| Variant                  | Path tested                                | Before this HLD | After this HLD |
| ------------------------ | ------------------------------------------ | --------------- | -------------- |
| `[portchannel]`          | Full CONFIG_DB → bgpcfgd → FRR             | Skipped         | Runs           |
| `[ethernet]`             | Same, on a physical port                   | Skipped         | Runs           |
| `[portchannel-frrtest]`  | bgpcfgd stopped; FRR-direct (sanity)       | Runs            | Runs           |


Additionally, VNET specific bgp_link local test case will be introduced which tests:
- BGP establishment for a VNET BGP session using unnumbered BGP
- 2nd BGP establishment for a VNET BGP session using unnumbered BGP
- Test datapath ECMP to the 2 nexthops, ie both nexthops receive packets

## References

- https://github.com/sonic-net/sonic-buildimage/issues/26960
- https://docs.frrouting.org/en/latest/bgp.html#multiple-autonomous-systems
- https://github.com/sonic-net/sonic-buildimage/pull/27308
- https://github.com/sonic-net/sonic-buildimage/pull/27370
