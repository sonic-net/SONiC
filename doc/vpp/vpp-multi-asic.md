# SONiC VPP Multi-ASIC Support — High Level Design

Rev v0.1

## Table of Contents

1. [Revisions](#1-revisions)
2. [Scope](#2-scope)
3. [Definitions/Abbreviations](#3-definitionsabbreviations)
4. [Overview](#4-overview)
5. [SONiC Multi-ASIC Requirements](#5-sonic-multi-asic-requirements)
6. [Design](#6-design)
7. [Packet Walks](#7-packet-walks)
8. [Restrictions and Unsupported Features](#8-restrictions-and-unsupported-features)
9. [Change Summary](#9-change-summary)
10. [Test Plan](#10-test-plan)
11. [Open Questions](#11-open-questions)
12. [References](#12-references)

## 1. Revisions

| Rev  | Date       | Author(s) | Changes       |
|------|------------|-----------|---------------|
| v0.1 | 17/11/2026 | yue-fred-gao | Initial draft |

## 2. Scope

This document describes how SONiC-VPP runs as a SONiC **multi-ASIC** device, with
one VPP instance per ASIC. The target is a virtual test platform for the SONiC
multi-ASIC control plane (namespaces, internal BGP, multi-ASIC CLI and services)
on top of the VPP dataplane. It is not intended as a production or
performance-oriented platform.

In scope:

- Frontend and backend ASICs, each emulated by its own `syncd` + VPP instance in
  its own network namespace.
- Backplane connectivity between frontend VPPs through dedicated
  **backend VPP** instances (no Linux bridge, no frontend-to-frontend links).
- **Two-stage (hop-by-hop) forwarding**: every VPP is an independent router.
- Routed internal links and internal port channels whose members are all on one
  VPP at each end.
- The standard SONiC multi-ASIC control plane: iBGP between frontend and backend
  ASICs, with route reflectors on the backend ASICs.

Out of scope (see [Section 8](#8-restrictions-and-unsupported-features)):

- One-stage (VOQ / system-port) forwarding. This is not intended or required by
  SONiC multi-asic topology.
- VLANs / bridge domains or port channels whose members span two VPP instances.
  This is not supported in SONiC multi-asic topology.
- Everflow: ACL-based ingress marking and egress mirroring.
- Production performance, DPDK NIC partitioning across ASICs, and warm reboot.

**Key point: no VPP dataplane change and no `sonic-sairedis` VPP (SAI) change is
required.** All of the work is in platform files, start-up scripts and packaging.

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| VPP | Vector Packet Processing — the software dataplane used by SONiC-VPP |
| ASIC | In this document, one emulated switching chip = one `syncd` container + one VPP process |
| Frontend ASIC | ASIC with front-panel (`Ext`) ports facing external peers |
| Backend ASIC | ASIC with only backplane (`Int`) ports, interconnecting frontend ASICs |
| Backplane / internal port | A port with role `Int` (`Ethernet-BP*`) connecting a frontend and a backend ASIC |
| Namespace | Linux network namespace `asicN` holding the containers and netdevs of ASIC N |
| RR | BGP route reflector |
| Two-stage forwarding | The ingress ASIC routes to a backend next hop; each ASIC on the path does its own lookup |
| One-stage forwarding | The ingress ASIC resolves the final egress port of another ASIC (VOQ model) — not used here |

## 4. Overview

SONiC already models a multi-ASIC box as several independent routers inside one
system: one namespace per ASIC, with its own databases, `swss`, `syncd`, `bgp`,
`teamd` and `lldp` containers. External traffic enters a frontend ASIC; traffic
destined to another frontend ASIC is routed over internal links to a backend
ASIC, which routes it to the egress frontend ASIC.

SONiC-VPP fits this model directly. Each `syncd@N` container runs its own VPP,
and VPP sees backplane ports as ordinary routed ports. Every forwarding decision
that crosses ASICs is made by the BGP control plane in each namespace, not by the
dataplane.

### 4.1 Reference topology

The reference platform reuses the 4-ASIC virtual-switch layout
(`device/virtual/x86_64-kvm_x86_64_4_asic-r0`): 2 frontend and 2 backend ASICs,
with 4 front-panel ports per frontend ASIC and 2 backplane links between each
frontend/backend pair.

Technically, 1 backend ASIC is enough but 2 has redundancy. We will follow VS
multi-asic topo to use 2 backends but can reduce it to 1 if resource usage needs
to be limited.

```
            External peers (eBGP)                External peers (eBGP)
                     |                                     |
              Ethernet0..12                         Ethernet16..28
          +----------+----------+             +----------+----------+
          |  asic0  (FrontEnd)  |             |  asic1  (FrontEnd)  |
          |  syncd0 + VPP       |             |  syncd1 + VPP       |
          +--+---------------+--+             +--+---------------+--+
     BP0,BP4 |       BP8,BP12|             BP16,BP20|      BP24,BP28|
             |               +--------+    +--------+               |
             |                        |    |                        |
             |               +--------|----+                        |
             |               |        +-------------------+         |
   BP32,BP36 |      BP40,BP44|                   BP64,BP68|         |BP72,BP76
          +--+---------------+--+             +-----------+---------+--+
          |  asic2  (BackEnd)   |             |  asic3  (BackEnd)      |
          |  syncd2 + VPP       |             |  syncd3 + VPP          |
          |  BGP route reflector|             |  BGP route reflector   |
          +---------------------+             +------------------------+

   BPn = Ethernet-BPn. Each frontend/backend pair is joined by 2 veth links,
   bundled as one internal port channel at each end.
   Each frontend ASIC connects to every backend ASIC; there are no
   frontend-frontend or backend-backend links.
```

| Frontend end | Backend end | Links |
|---|---|---|
| asic0 `Ethernet-BP0`, `Ethernet-BP4` | asic2 `Ethernet-BP32`, `Ethernet-BP36` | 2 × veth |
| asic0 `Ethernet-BP8`, `Ethernet-BP12` | asic3 `Ethernet-BP64`, `Ethernet-BP68` | 2 × veth |
| asic1 `Ethernet-BP16`, `Ethernet-BP20` | asic2 `Ethernet-BP40`, `Ethernet-BP44` | 2 × veth |
| asic1 `Ethernet-BP24`, `Ethernet-BP28` | asic3 `Ethernet-BP72`, `Ethernet-BP76` | 2 × veth |

The layout scales to any N frontend × M backend ASICs; only the platform files and
the topology script change.

## 5. SONiC Multi-ASIC Requirements

These are requirements of the SONiC multi-ASIC architecture
([SONiC multi-ASIC HLD](https://github.com/sonic-net/SONiC/blob/master/doc/multi_asic/SONiC_multi_asic_hld.md)).
They are platform-independent and already implemented in SONiC; SONiC-VPP must
satisfy them, not reimplement them.

### 5.1 One namespace per ASIC

- Each ASIC lives in its own Linux network namespace `asic0` … `asicN-1`.
- `bgp`, `lldp`, `teamd`, `swss`, `syncd` and `database` containers are replicated,
  one instance per namespace, started from systemd templates (`foo@N.service`).
- `systemd-sonic-generator` reads `NUM_ASIC` from `asic.conf` at boot and
  instantiates the per-namespace services.
- The host runs single instances of `database` (global DB), `pmon`, `snmp`,
  `telemetry` and `rsyslog`, which aggregate data from all namespaces.
- Containers receive `NAMESPACE_ID`, `NAMESPACE_PREFIX` and `NAMESPACE_COUNT` in
  their environment (`docker_image_ctl.j2`).

**For VPP:** one `syncd@N` container = one VPP process, with VPP's netdevs and
LCP host interfaces in namespace `asicN`.

### 5.2 Platform files

- `/usr/share/sonic/device/<platform>/asic.conf` with `NUM_ASIC=N`.
- One subdirectory per ASIC under the HWSKU directory (`<hwsku>/0/`, `<hwsku>/1/`, …),
  mounted into that ASIC's containers as `/usr/share/sonic/hwsku`.
- A per-ASIC `port_config.ini` with the `asic_port_name` and `role` columns. `Ext`
  marks front-panel ports and `Int` marks backplane ports (`Ethernet-BP*`). SONiC
  port names are unique across the whole device.

### 5.3 Configuration

- N+1 config files: `config_db.json` (host-wide items such as syslog and AAA)
  plus `config_db<N>.json` per ASIC, generated from a single multi-ASIC minigraph
  or provided directly.
- `DEVICE_METADATA` per ASIC: `asic_id`, `asic_name` (namespace) and `sub_role`
  (`FrontEnd` / `BackEnd`).
- **Router MAC**: all frontend ASICs use the system base MAC; each backend ASIC
  uses a distinct MAC (that of `eth0` in its namespace).
- **Loopbacks**: `Loopback0` carries the device-wide address advertised
  externally, identical on all ASICs. `Loopback4096` carries a per-ASIC, internal-only
  address used as the BGP router ID.
- Internal links are routed point-to-point interfaces, normally bundled as
  internal port channels (`PortChannel40xx`) with internal IP addresses.

### 5.4 BGP

- **iBGP between frontend and backend ASICs**: every frontend ASIC peers with
  every backend ASIC over the internal links (`BGP_INTERNAL_NEIGHBOR`). All ASICs
  share the device AS number.
- **Backend ASICs run as route reflectors**: the internal peer-group template
  marks internal peers `route-reflector-client` when `sub_role == BackEnd`
  (`dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`).
  This is how a route learned by one frontend ASIC reaches the other frontend
  ASICs without a frontend-frontend iBGP mesh.
- Internal neighbors are `next-hop-self`, so a frontend ASIC always resolves
  remote prefixes to a backend next hop on a backplane link.
- Frontend ASICs redistribute connected routes into BGP.
- eBGP to external peers exists only on frontend ASICs.
- Each namespace has its own `bgpd`, `zebra` and `fpmsyncd`; routes are
  programmed into that namespace's `APPL_DB` and from there into that ASIC's VPP.

### 5.5 Control-plane services

- LLDP runs in each namespace on both front-panel and backplane ports, so
  internal links are visible as LLDP neighbors.
- `teamd`/LACP runs per namespace and builds the internal port channels.
- Data ACLs (and Everflow ACLs on hardware platforms) are bound only to frontend
  ports on frontend ASICs; backend ASICs have no ACLs.
- Control-plane ACLs (iptables) are programmed in the host and in each namespace.

### 5.6 CLI

- `show` commands accept `-n/--namespace` and `-d/--display all|frontend`. By
  default they show all namespaces and external interfaces only.
- `config` commands for VLANs, port channels, static routes, subinterfaces, IPv6
  link-local and similar take `-n`, which is mandatory on multi-ASIC.
  `config save/load/reload/load_minigraph` operate on all config files.

## 6. Design

### 6.1 Forwarding model: two-stage only

Every VPP instance is an independent L3 router that knows only its own ports,
neighbors and routes:

- The **ingress frontend VPP** does a FIB lookup. For a prefix behind another
  frontend ASIC, the next hop (learned via iBGP from the backend RR) is a backend
  ASIC's address on an internal port channel. VPP rewrites the packet towards
  that next hop and transmits it on the backplane.
- The **backend VPP** receives an ordinary IP packet on a backplane port, does its
  own lookup and routes it to the egress frontend ASIC.
- The **egress frontend VPP** does a final lookup, resolves the external
  neighbor locally and transmits on the front-panel port.

Consequences, all consistent with SONiC on multi-ASIC hardware:

- TTL is decremented at each ASIC hop (3 for frontend → backend → frontend).
- ECMP/LAG hashing is recomputed on each ASIC. Different hash seeds per ASIC
  avoid polarization, but this is not required for functional tests.
- No per-packet metadata crosses VPP instances. In particular `vnet_buffer` and
  `sonic_ext_vnet_buf` are never carried across the backplane; each VPP starts
  from a fresh buffer.

### 6.2 No dataplane change

Every feature used in the multi-ASIC topology is one each VPP already supports as
a single-ASIC router:

| Multi-ASIC function | VPP mechanism | Change |
|---|---|---|
| Front-panel and backplane ports | Physical ports via af_packet (veth) or DPDK | None — a backplane port is just another port |
| Internal port channels | VPP bond, both ends local to their own VPP | None |
| Routed internal links, `Loopback0`, `Loopback4096` | RIF / loopback programming | None |
| Cross-ASIC routes | FIB entries with backend next hops from iBGP | None |
| ECMP over internal port channels | FIB load-balance + bond hashing | None |
| Neighbor resolution | Per-VPP ARP/ND on its own ports | None |
| BGP, LLDP, LACP, ARP/ND punt | Per-namespace host interfaces (LCP/tap) | None |
| Data ACL on frontend ports | Existing ACL support | None |
| Counters | Per-VPP stats → per-namespace `COUNTERS_DB` | None |

The SAI layer (`src/sonic-sairedis/vslib/vpp`) also needs no change:

- It reads `sonic_vpp_ifmap.ini` from `/usr/share/sonic/hwsku`, which in multi-ASIC
  is already the per-ASIC directory.
- It connects to VPP at `/run/vpp/api.sock`, which is private to each `syncd`
  container.

### 6.3 Backplane with backend VPP

- **Point-to-point links only.** Each backplane link is a veth pair with one end
  in a frontend namespace and the other in a backend namespace. This matches
  hardware, where each `Ethernet-BP*` port has exactly one peer, which is what
  minigraph, `BGP_INTERNAL_NEIGHBOR` and LLDP expect. A shared Linux bridge is
  not used.
- **Backend VPPs are the backplane.** Frontend ASICs are not connected to each
  other; all inter-frontend traffic is routed through a backend VPP.
- **Link transport.** VPP consumes the veths through af_packet (`host-<veth>`),
  the existing path for virtual ports. Performance is not a goal; af_packet keeps
  the setup simple and the backplane observable with `tcpdump`. memif is a
  possible later optimization and needs no design change.
- **Topology script.** The VS 4-ASIC `topology.sh` already:
  - moves front-panel NICs into the frontend namespaces;
  - creates the frontend ↔ backend veth pairs (MTU 9100);
  - names the veths `eth1..ethN` inside each namespace.

  The VPP platform reuses it as-is (or a copy with a different layout).

### 6.4 Platform and HWSKU files

The VPP multi-ASIC platform **is** `device/virtual/x86_64-kvm_x86_64_4_asic-r0`
(HWSKU `msft_four_asic_vs`), modified in place. No separate VPP platform
directory is added. This follows the single-ASIC precedent, where SONiC-VPP uses
the shared `device/virtual/x86_64-kvm_x86_64-r0` with `platform_asic=vpp`.
`platform/vpp/rules/onie.mk` already references the matching 4-ASIC ONIE
recovery ISO, which sets this platform string at install time.

The VPP-only files added below (`sonic_vpp_ifmap.ini`, `syncd_vpp_env`) sit next
to the existing VS files and are ignored by the VS SAI.

| File | Content |
|---|---|
| `asic.conf` | `NUM_ASIC=4` (unchanged) |
| `platform_asic` | `vpp`, same as `x86_64-kvm_x86_64-r0` |
| `<hwsku>/topology.sh` | Unchanged from VS |
| `<hwsku>/<N>/port_config.ini` | Unchanged from VS (`Ext`/`Int` roles) |
| `<hwsku>/<N>/sonic_vpp_ifmap.ini` | **New**: SONiC port → VPP interface for ASIC N |
| `<hwsku>/<N>/syncd_vpp_env` | **New**: static VPP start-up environment for ASIC N ([Section 6.6](#66-initial-configuration)) |

`sonic_vpp_ifmap.ini` uses the existing `<osif> <vpp-hwif>` format. Example for
frontend `asic0` (front panel `eth1..4`, backplane `eth5..8`):

```
Ethernet0     host-eth1
Ethernet4     host-eth2
Ethernet8     host-eth3
Ethernet12    host-eth4
Ethernet-BP0  host-eth5
Ethernet-BP4  host-eth6
Ethernet-BP8  host-eth7
Ethernet-BP12 host-eth8
```

and for backend `asic2` (backplane only):

```
Ethernet-BP32 host-eth1
Ethernet-BP36 host-eth2
Ethernet-BP40 host-eth3
Ethernet-BP44 host-eth4
```

### 6.5 Per-instance VPP start-up

Today the VPP start-up path assumes a single instance. The following changes make
it instance-aware; none affects single-ASIC behavior.

**Environment file.** `/etc/sonic/vpp/syncd_vpp_env` is a single file used by:

- `docker_image_ctl.j2.patch` (`--env-file` for `syncd`);
- `docker-syncd-vpp/scripts/vpp_init.sh`;
- `sonic-platform-modules-vpp/.../vpp_ports_setup.sh`;
- `vppcfg.service`.

Change: on multi-ASIC, use the static per-ASIC file
`/usr/share/sonic/device/<platform>/<hwsku>/<N>/syncd_vpp_env`
([Section 6.6](#66-initial-configuration)). On single-ASIC, keep
`/etc/sonic/vpp/syncd_vpp_env`. The per-ASIC file holds `VPP_DPDK_PORTS`,
`SONIC_NUM_PORTS`, `DPDK_DISABLE` and the resource knobs below for that ASIC only.

**`syncd.service`.** `per_namespace/syncd.service.j2.patch` calls
`vpp_ports_setup.sh start|stop` without the instance id. Change: pass `%i`, so
the script binds or restores only that ASIC's ports. With veth-only ports it is
a no-op.

**`vpp_init.sh`.** Change it to:

- source the per-ASIC env file (selected by `NAMESPACE_ID`);
- derive per-instance CPU settings — `main-core` is hard-coded to 2 and
  `workers 1` in `startup.conf.tmpl`. For the test platform use `VPP_WORKERS=0`
  and a per-ASIC `main-core` (or no pinning), so N VPPs do not compete for one
  polling core;
- keep `buffers-per-numa = PERPORT_BUF × SONIC_NUM_PORTS` per instance, with a
  smaller default `PERPORT_BUF` for multi-ASIC so N instances fit in the VM;
- not write the global `nr_hugepages`. With veth-only ports `DPDK_DISABLE=y` and
  hugepages are not used. If DPDK is used, size hugepages once on the host for
  all instances.

**Sockets and runtime state.** VPP's `cli.sock`, `api.sock` and `stats.sock`
are under `/run/vpp` inside each `syncd` container and are already isolated per
instance. `/run/vpp` must not be bind-mounted to the host.

**Host interfaces.** `syncd@N` shares the network namespace of `database@N`, so
the LCP host interfaces (`Ethernet*`, `Ethernet-BP*`, `PortChannel*`) that VPP
creates appear in `asicN`, where `bgp@N`, `lldp@N` and `teamd@N` expect them. No
change is needed.

### 6.6 Initial configuration

Multi-ASIC configuration comes **only from minigraph**. The platform's only
consumer is the multi-ASIC sonic-mgmt testbed, which loads a minigraph with
`deploy-mg` (`config load_minigraph`). That minigraph produces the complete
multi-ASIC configuration: host `config_db.json`, per-ASIC `config_db<N>.json`,
`sub_role`, internal port channels, `Loopback4096` and `BGP_INTERNAL_NEIGHBOR`.

The VPP factory-default hook `10-01-vpp-cfg-init` is not used, and needs no
change. It never runs on multi-ASIC: `config-setup` returns before running
factory-default hooks when `NUM_ASIC > 1` ("For multi-npu platform we don't
support config initialization"). Its other outputs are not needed either:

- `sonic_vpp_ifmap.ini` is static per ASIC ([Section 6.4](#64-platform-and-hwsku-files)).
- `syncd_vpp_env` is static per ASIC. With veth-only ports its content is fixed:
  `DPDK_DISABLE=y`, `VPP_DPDK_PORTS` = that ASIC's veths, `SONIC_NUM_PORTS`, and
  the resource knobs from [Section 6.5](#65-per-instance-vpp-start-up). It ships
  as `<hwsku>/<N>/syncd_vpp_env` next to the ifmap.

Until `deploy-mg` runs, the device boots with no ASIC configuration, the same
as the VS multi-ASIC platform.

### 6.7 vppcfgd

`vppcfg.service` is a single host service that writes `/etc/sonic/vpp/startup.conf`
when `VPP_CONF_DB=y`. Multi-ASIC phase 1 does not support `VPP_CONF_DB=y`; each
instance builds its start-up configuration from `startup.conf.tmpl` in
`vpp_init.sh`. A per-namespace `vppcfgd@N` can be added later if needed.

### 6.8 docker-sonic-vpp

The all-in-one `docker-sonic-vpp` container (`start_sonic.sh`) remains
single-ASIC. Multi-ASIC is supported only with the VM image (`sonic-vpp.img`)
running the standard per-namespace services.

## 7. Packet Walks

### 7.1 Transit: front-panel port on asic0 → front-panel port on asic1

```
 ext host A ── Ethernet0 [asic0 VPP]
                  ip4-input → ip4-lookup: prefix B via 10.1.0.x (asic2, iBGP from RR)
                  ip4-rewrite (TTL-1, dst MAC = asic2 router MAC) → bond PortChannel40xx
            ── Ethernet-BP0 ═══ veth ═══ Ethernet-BP32 ──
                                         [asic2 VPP]
                  ip4-input → ip4-lookup: prefix B via asic1 internal address
                  ip4-rewrite (TTL-1, dst MAC = asic1 router MAC) → bond PortChannel40yy
            ── Ethernet-BP40 ═══ veth ═══ Ethernet-BP16 ──
                                         [asic1 VPP]
                  ip4-input → ip4-lookup: prefix B connected/eBGP
                  ip4-rewrite (TTL-1, dst MAC = host B) → Ethernet16 ── ext host B
```

Each step is an ordinary single-ASIC VPP route. Reachability of prefix B on
asic0 depends only on asic1 → asic2 → asic0 route propagation through the
backend RR.

### 7.2 Control plane

- External BGP, LLDP, LACP and ARP/ND on front-panel ports are punted by the
  frontend VPP to its host interfaces in `asicN`, exactly as on single-ASIC.
- Internal iBGP sessions run between `Loopback4096`/internal addresses over the
  backplane port channels. The packets are punted to the host on the receiving
  VPP like any other BGP packet.
- LACP on internal port channels runs between `teamd@frontend` and
  `teamd@backend`. Each end's bond and its members belong to one VPP.

## 8. Restrictions and Unsupported Features

| Item | Status | Reason |
|---|---|---|
| One-stage (VOQ / system-port) forwarding | Not supported | Requires a global port/neighbor model and cross-VPP metadata; not needed for non-VOQ multi-ASIC |
| VLAN / bridge domain spanning two VPPs | Not supported | Not supported by SONiC multi-ASIC either; VLAN config is per namespace |
| Port channel with members on two VPPs | Not supported | Not supported by SONiC; internal port channels are supported because each end is local to one VPP |
| Everflow: ingress ACL marking with egress mirror in two VPPs | Not supported | Marking by ingress ACL can't be passed to egress VPP |
| Passing `vnet_buffer` / `sonic_ext_vnet_buf` across VPPs | Not supported by design | Buffer metadata is local to one VPP process and one buffer lifetime |
| `VPP_CONF_DB=y` (vppcfgd) | Not supported | Single host instance writes one `startup.conf` |
| `docker-sonic-vpp` all-in-one container | Single-ASIC only | Multi-ASIC requires the per-namespace services of the VM image |
| Warm reboot | Not covered | Out of scope for phase 1 |

**Everflow.** In SONiC multi-ASIC, mirror sessions are programmed on all frontend
ASICs, and each ASIC resolves its own monitor port, which may be a backplane port
channel. The GRE/ERSPAN packet is then routed by the remaining ASICs on its outer
header. Everflow ingress ACL marking and egress mirroring are supported but 
cannot span over 2 VPPs.
this is because:

- ingress ACL marking will be consumed by mirror sessions in the same VPP. The 
  marking is not passed to mirror sessions in the egress VPP. Everflow can be 
  configured in 3 VPPs (ingress frontend, backend, egress frontend) simultaneously
  for the same flow but 3 flow records will be generated.

## 9. Change Summary

No changes in `platform/vpp/vppbld` (VPP and plugins) or in
`src/sonic-sairedis/vslib/vpp`.

| Area | File(s) | Change |
|---|---|---|
| Platform | `device/virtual/x86_64-kvm_x86_64_4_asic-r0/` (modified in place) | `platform_asic=vpp`; static per-ASIC `sonic_vpp_ifmap.ini` and `syncd_vpp_env` |
| Env file | `platform/vpp/platform/mkrules/files/build_templates/docker_image_ctl.j2.patch` | `--env-file` = the per-ASIC `syncd_vpp_env` when `$DEV` is set |
| systemd | `.../per_namespace/syncd.service.j2.patch` | Pass `%i` to `vpp_ports_setup.sh` |
| Port setup | `sonic-platform-modules-vpp/files/usr/bin/vpp_ports_setup.sh` | Read the per-instance env file |
| VPP start-up | `docker-syncd-vpp/scripts/vpp_init.sh` | Per-instance env, CPU, buffers; no global hugepage write when DPDK is disabled |
| First boot | `sonic-platform-modules-vpp/.../10-01-vpp-cfg-init` | None — not run on multi-ASIC; configuration comes from minigraph |
| Image | `.../sonic_debian_extension.j2.patch` | Keep `vppcfg.service` disabled for multi-ASIC |
| Docs | `platform/vpp/docs/` | Multi-ASIC getting-started guide |

## 10. Test Plan

### 10.1 Bring-up

| ID | Test | Expected |
|---|---|---|
| MA-01 | Boot the 4-ASIC VPP image | `syncd@0..3` running; one VPP per container (`docker exec syncdN vppctl show version`) |
| MA-02 | Interfaces per ASIC | `vppctl show interface` in `syncdN` lists exactly the `host-ethX` from that ASIC's ifmap |
| MA-03 | Host interfaces | `ip -n asicN link` shows `Ethernet*` / `Ethernet-BP*` for that ASIC only |
| MA-04 | `show interface status -d all` | Front-panel and backplane ports up, grouped by namespace |
| MA-05 | Internal port channels | `show interfaces portchannel -d all` shows `PortChannel40xx` up on both ends |
| MA-06 | LLDP | `show lldp table -d all` shows internal neighbors (ASIC names) |
| MA-07 | Internal iBGP | `show ip bgp summary -d all` shows frontend ↔ backend sessions established |
| MA-08 | Route reflection | A prefix learned by eBGP on asic0 is present on asic1, via the backend |
| MA-09 | Transit forwarding | Traffic from a port on asic0 to a port on asic1 crosses a backend VPP; TTL is decremented 3 times |
| MA-10 | ECMP over backend | With 2 backend ASICs, asic0 has an ECMP route via both; flows spread over both backends |
| MA-11 | Backend failure | Shut a backend's internal port channels; traffic converges onto the remaining backend |
| MA-12 | Counters | `show interface counters -n asicN -d all` reflects per-VPP stats |

### 10.2 sonic-mgmt

Run the existing multi-ASIC-aware suites against the VPP multi-ASIC VM:

- `bgp/` (including internal session checks), `route/`, `ipfwd/`;
- `lldp/`, `pc/`, `acl/` (data ACL on frontend ports);
- `show_techsupport/` and multi-ASIC CLI tests.

## 11. References

- [SONiC multi-ASIC HLD](https://github.com/sonic-net/SONiC/blob/master/doc/multi_asic/SONiC_multi_asic_hld.md)
- [SONiC-VPP HLD](SONICVPP-HLD.md)
- [SONiC-VPP LAG HLD](vpp-lag.md)
- [SONiC-VPP mirror HLD](vpp-mirror.md)
- [SONiC-VPP Everflow via sonic_ext HLD](vpp-everflow-sonic-ext.md)
