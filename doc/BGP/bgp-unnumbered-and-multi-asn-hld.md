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
| FRR `v6only`      | FRR keyword on `neighbor X interface v6only` meaning the peer is unnumbered.                                                              |
| LLv6              | IPv6 link-local address (`fe80::/10`).                                                                                                    |
| `BGP_NEIGHBOR`    | Existing CONFIG_DB table; today keyed on IPv4/IPv6 address only.                                                                          |
| `bgpcfgd`         | SONiC daemon that reflects CONFIG_DB state into FRR config via Jinja templates.                                                           |
| IP2Me             | An ASIC route entry installed by SONiC for every locally-owned IP, trapping matching packets to CPU.                                      |
| VNET / VRF        | A non-default routing instance. In SONiC, VNETs are VxLAN-tunnel VRFs created by `VNETOrch`; bare VRFs are created by `VRFOrch`.          |

## Overview and Requirements

Today, SONiC bgpcfgd configures BGP exclusively through IP-keyed entries in `CONFIG_DB.BGP_NEIGHBOR`. There is no way to express:

```text
neighbor PortChannel101 interface v6only remote-as 64001
```

While FRR supports this and most modern DC fabrics rely on it, operators currently have to use either manual vtysh or `frrcfgd` to configure this, this HLD describes support for `bgpcfgd`, and additional support in orachagent/sonic-swss to enable LLv6 networking, specifically:

1. Extend `BGP_NEIGHBOR` so the key can be an **interface name** (`PortChannel*`, `Ethernet*`, `<vrf>|<intf>`). No new table; numbered-row schema unchanged.
2. Extend the FRR Jinja templates in `dockers/docker-fpm-frr/frr/bgpd/templates/general/` so an interface-keyed row renders the unnumbered FRR construct, while IP-keyed rows render the existing config byte-for-byte unchanged.
3. Add a `PEER_UNNUMBERED` peer-group at the FRR side, carrying the AF-agnostic policy infrastructure.
4. Extend orchagent (`vnetorch.cpp`, parallel to the merged `vrforch.cpp` change in PR #3973) so that LLv6 traffic destined to the device in a VNET is trapped to CPU
5. Extend orchagent(`vnetorch.cpp`) so that RFC 5549 duplicate-IP ECMP routes are programmed correctly in ASIC_DB
6. The rendered FRR session MUST come up over IPv6 link-local with `extended-next-hop` negotiated, so both IPv4 and IPv6 NLRI can be exchanged on the single session by default, if the user chooses to opt out of IPv4 prefixes announcements, then a `v6only: true` should be provided in the `BGP_NEIGHBOR` table
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
            "v6only": {{true/false}} (Optional and only applicable to BGP unnumbered, if absent defaulted to false) >>> New
```
Additions:
- Peer-name: will be accepted as a Interface, PortChannel, Vlan and Ethernet/Portchannel subinterface
- "v6only": Newly added optional field which is only applicable to BGP unnumbered, if set to true NO IPv4 announcements will occur over the LLv6 BGP unnumbered session, if absent, defaulted to false

Example configuration displaying the use of a Link Local Ipv6 interface with BGp Unnumbered(existing schema included for completeness):
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

The session-level peer-group is `PEER_UNNUMBERED` (FRR allows exactly one session-level peer-group binding per neighbor, regardless of which AF block it appears in). RFC 5549 capability negotiation happens automatically.

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
- v6only field in BGP_NEIGHBOR
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
