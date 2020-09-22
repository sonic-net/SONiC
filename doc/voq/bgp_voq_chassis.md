# BGP Setup for VoQ Chassis
# High Level Design Document

### Rev 1.0

# Table of Contents
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [1 Requirements](#1-requirements)
* [2 Design](#2-design)
  * [2.1 BGP Setup](#21-bgp-setup)
  * [2.2 iBGP Configuration](#22-ibgp-configuration)
  * [2.3 FRR Changes](#23-frr-changes)
  * [2.4 CONFIG_DB Changes](#24-config_db-changes)
  * [2.5 FRR Configuration Templates](#25-frr-configuration-templates)
  * [2.6 Mingraph Changes](#26-minigraph-changes)
* [3 Testing](#3-testing)

# Revision
| Rev |     Date    |       Author       | Change Description |
|:---:|:-----------:|:------------------:|--------------------|
| 1 | Sep-10 2020 | Joanne Mikkelson (Arista Networks) | Initial Version |

# About this Manual

This document describes how BGP will be configured on a VoQ chassis.

# Scope

The configuration described here is intended to ensure that routes programmed
for BGP-learned prefixes are the same for each ASIC Instance in a VoQ chassis.

This document describes:
- BGP configuration changes
- Changes to Minigraph and CONFIG_DB
- FRR configuration templates

# 1 Requirements

Traffic ingressing on any ASIC Instance should be routed the same, regardless of which
ASIC Instances learned the route from their eBGP peers.

To achieve this:
- Each ASIC Instance must advertise eBGP-learned routes to the other ASIC Instances in the chassis.
- Each ASIC Instance in a chassis should choose the same BGP route for each prefix.
- When ECMP is enabled and equal-cost routes are learned by any ASIC Instance, all ASIC Instances should compute the same ECMP nexthop.

# 2 Design

## 2.1 BGP Setup

All ASIC Instances in the chassis are members of the same AS.  All routes learned from
all neighboring eBGP routers must be learned on all ASIC Instances.  To accomplish this,
an iBGP full mesh will be established between all ASIC Instances, with the additional
paths feature enabled for neighbors in the mesh.

There may also be an iBGP route monitor in the network.  This route monitor
must be configured to peer with each ASIC Instance; otherwise it will not be
participating in the iBGP mesh and would not learn all the routes.

The following diagram shows the BGP sessions associated with three ASIC Instances in the
chassis, each with one or two eBGP peers.  The red lines are the new iBGP mesh.

![Example BGP Topology](./chassis_bgp_topology.png)

## 2.2 iBGP Configuration

Routers will automatically advertise routes learned from eBGP peers to iBGP
peers, with the nexthop unchanged.  We rely on the global neighbor table to
provide routes for each neighboring router to all ASIC Instances so that the nexthops are
recursively resolvable.  For example, a route readvertised from ASIC1 with a
nexthop of 10.0.1.2 would be recursively resolvable on ASIC2 over the
10.0.1.2/32 route created from the global neighbor table.

To ensure that each ASIC Instance computes the same ECMP group:
- Enable additional-path send all for each chassis iBGP peer.  If ASIC1 learns a route from both R1 and R4, both must be advertised to other ASIC Instances.
- Allow BGP to form ECMP groups with paths learned from both eBGP and iBGP peers.  The best path algorithm normally prefers eBGP paths (RFC 4271 section 9.1.2.2 step d).  Without this change, if a route is learned from R1, R2, and R4, ASIC1 would create ECMP group {R1,R4}, ASIC2 would use {R2}, and ASIC3 would use {R1,R2,R4}.
- The maximum ECMP group size must be set the same for eBGP and iBGP.
- Turn off the eBGP connected route check.  In an ECMP group with both eBGP- and iBGP-learned nexthops, the latter are not reachable over connected routes and would otherwise be discarded from the FIB, resulting in different forwarding on different ASIC Instances.

The FRR BGP configuration for these four changes is:
- `neighbor <neighbor> addpath-tx-all-paths`
- `bgp bestpath peer-type multipath-relax`
- `maximum-paths ibgp <n>` (where <n> is the same as used in `maximum-paths <n>`)
- `bgp disable-ebgp-connected-route-check`

Note that if more equal-cost paths are learned for a given route than the
maximum ECMP group size, each ASIC Instance may still choose a different subset of paths
to program.

## 2.3 FRR Changes

The second configuration mentioned above, “bgp bestpath peer-type
multipath-relax”, does not currently exist in FRR and will be added as part of
this proposal.  This is named to mirror the “bgp bestpath as-path
multipath-relax” configuration.

Configuring this will allow paths from different peer types to form an ECMP
group.  The best path algorithm is not changed otherwise, such that if a route
has both eBGP and iBGP paths in the ECMP group, an eBGP path will still be the
best path.  This route will be the one advertised to eBGP peers, as would be
the case without enabling the new configuration.  While the VoQ chassis system
requires the eBGP and iBGP maximum-paths size to be set the same, if they were
not, the eBGP size would be used for a mixed-type ECMP group, because the best
path is guaranteed to be eBGP.

## 2.4 CONFIG_DB Changes

CONFIG_DB currently contains three tables specifying BGP neighbors:
BGP_NEIGHBOR for typical router peers (R1 etc. in the diagram), BGP_MONITORS
for route monitor(s), and BGP_PEER_RANGE for dynamic peers.  A fourth table
will be added, BGP_VOQ_CHASSIS_NEIGHBOR, to include the ASIC Instance neighbors in the
iBGP mesh.  Entries in this table will use the same schema as BGP_NEIGHBOR.

This new table will allow the most natural use of the FRR configuration system,
where the database table dictates which templates are used to generate the FRR
configuration.

## 2.5 FRR Configuration Templates

BGP neighbors included in CONFIG_DB are translated from Jinja templates into
FRR configuration by a script running in the bgp docker called “bgpcfgd”.

Using the `general` templates used for BGP_NEIGHBOR peers would require adding
new peer groups to the general templates and a number of if-statements based on
some attribute of the BGP_NEIGHBOR entry.

Instead, entries in the BGP_VOQ_CHASSIS_NEIGHBOR table will use a new set of
`voq_chassis` templates rather than the `general` ones.  These templates will
include new peer-groups to encapsulate the neighbor configuration, as well as
the necessary instance-wide configuration (configuration changes 2-4 described
earlier).

## 2.6 Mingraph Changes

The script that converts the minigraph into CONFIG_DB entries will be modified
to place the VoQ chassis peers in the new BGP_VOQ_CHASSIS_NEIGHBOR table.  The
minigraph must be changed to indicate which peers should be in the new table
instead of the BGP_NEIGHBOR table.

We propose a new optional element in the BGPRouterDeclaration that indicates
whether this is a VoQ chassis neighbor.
```
      <a:BGPRouterDeclaration>
        <a:ASN>64542</a:ASN>
        <a:Hostname>OCPSCH0104001MS</a:Hostname>
        <a:RouteMaps/>
        <a:VoQChassisPeer>1</a:VoQChassisPeer>
      </a:BGPRouterDeclaration>
```

# 3 Testing

A new swss test using the virtual chassis topology will confirm that the newly
added FRR configuration controls whether or not otherwise equal-cost eBGP and
iBGP paths are included in the same ECMP group.

The bgpcfgd tests will be augmented with new `voq_chassis` data files to ensure
that the proper configuration is created for BGP_VOQ_CHASSIS_NEIGHBOR entries.

A test with VoQChassisPeer entries in the minigraph will be added to the
sonic-config-engine tests.
