# Bgpcfgd Dynamic Peer Modification Support
# High Level Design Document
### Rev 1.0

# Table of Contents
  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Use case](#use-case)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
    * [1.2 Scalability requirements](#12-scalability-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
    * [2.2 State DB](#22-state-db)
    * [2.3 CLI](#23-cli)
    * [2.4 Bgpcfgd](#24-bgpcfgd)
    * [2.5 Docker-FPM-FRR bgpd templates](#25-docker-fpm-frr-bgpd-template)
  * [3 Test Plan](#3-test-plan)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 04/09/2025  |    Anish Narsian   | Initial version                   |
| 1.0 | 07/02/2025  |    Anish Narsian   | All comments addressed            |

# About this Manual
This document provides the high level design to support enhanced CRUD operations on dynamic bgp peers(ie: bgp listen ranges) using a standard template-based mechanism, as well as the CLI design for some useful per VRF BGP commands.

# Use case
SDN(Software Defined Networking) is used to program SONiC devices for various use cases, and we intend to extend this to BGP configurations, specifically dynamic BGP peers. To that extent we intend to support enhanced CRUD operations on dynamic peer types, including modifying peer ranges and supporting modification and deletion of their associated configurations like route maps, prefix lists and peer groups using the standard template mechanism.


# Definitions/Abbreviation
###### Table 1: Abbreviations
| Abbreviation             | Meaning                        |
|--------------------------|--------------------------------|
| BGP                      | Border Gateway Protocol        |
| BGPCFGD                  | BGP configuration daemon       |
| VNET                     | Virtual Network                |
| VRF                      | Virtual Routing and Forwarding |


# 1 Requirements Overview
## 1.1 Functional requirements
This section describes the SONiC requirements for supporting enhanced CRUD operations for dynamic bgp peers:
- Configurable in VNET/VRFs, but equally applicable to default VRF
- Dynamic peers' listen ranges must be modifiable at runtime such that ranges can be added and removed(changing today's behavior of being a create only attribute)
- Dynamic peer updates/deletes should allow for changes to associated configurations like route-maps, peer-groups, prefix-lists etc
- Ability to track the configuration of a dynamic BGP peer via a State DB entry which is queryable by the SDN controller
- CLI commands to show VRF/VNET BGP neighbors

## 1.2 Scalability requirements
###### Table 2: Scalability
| Component                | Expected value              |
|--------------------------|-----------------------------|
| Number of Dynamic BGP Peers each with route-map, prefix-list and peer-group|2k total, ~1 per VNET/VRF|
| Number of listen ranges|4k total, ~2 per VNET/VRF|
| Size of each Route-map, Prefix-list|<10|


# 2 Modules Design

## 2.1 Config DB
Existing Config DB tables will be used to achieve this, no new Config DB table is introduced
```
BGP_PEER_RANGE|{{VRF/VNET-name}}|{{Peer-name}}:
    "ip_range": [{{Range of IPs to add to listen range}}],
    "name": {{Peer-name}},
    "peer_asn": {{Peer's ASN number}}, (Optional)
    "src_address": {{Src IP to initiate session}} (Optional)
```

## 2.2 State DB
Following new table will be added to State DB.
Use case: The SDN controller which programs neighbors will query the following state DB entry to confirm if the required entry is processed by bgpcfgd and programmed successfully. 
```
BGP_PEER_CONFIGURED_TABLE|{{VRF/VNET-name}}|{{Peer-name}}:
    "ip_range": [{{Range of IPs to add to listen range}}],
    "name": {{Peer-name}},
    "peer_asn": {{Peer's ASN number}}, (Optional)
    "src_address": {{Src IP to initiate session}} (Optional)
```
Unless otherwise stated, the attributes are mandatory.

While the above shows the State DB schema for a dynamic peer, the schema for static peers bear the same table name format of ```BGP_PEER_CONFIGURED_TABLE|{{VRF/VNET-name}}|{{Peer-name}}```, but the key value pairs under the table will be those which are used to configure static peers.

## 2.3 CLI
The following CLIs will be added, each of these will have similar CLI outputs to their ```default VRF``` counterparts which are widely in use today:
```
1. show ip bgp vrf {vrf_name} summary
2. show ip bgp vrf {vrf_name} network
3. show ip bgp vrf {vrf_name} neighbors
4. show ipv6 bgp vrf {vrf_name} summary
5. show ipv6 bgp vrf {vrf_name} network
6. show ipv6 bgp vrf {vrf_name} neighbors
```

## 2.4 Bgpcfgd
The following modifications will be made to bgpcfgd to support the new scenario:
1. BGPPeerMgrBase will check, at init time, if an update template file exists as follows ```"bgpd/templates/" + self.constants["bgp"]["peers"][peer_type]["template_dir"] + "/" + update.conf.j2```.  
   The `update.conf.j2` file is a Jinja2 template used to define the configuration updates for dynamic BGP peers.
2. If one exists, then we will consider this device as supporting updates to the peer_type in question, and we append the update template to the list of templates which can be rendered:
```
        self.templates["update"] = self.fabric.from_file(update_template_path)
```
3. If an update template is supported and the peer_type is dynamic, we will identify the set of ip_ranges which are added, and those which are deleted as part of the operation. The modified ranges will be identified in bgpcfgd by running a vtysh command to get the current bgp listen ranges configured and running a diff against the newly passed in ranges, the calculated diff will be passed in as additional kwargs(add_ranges, delete_ranges) and rendered via the update template, sample code:
```
        kwargs = {
            'vrf': vrf,
            'neighbor_addr': nbr,
            'bgp_session': data,
            'delete_ranges': ip_ranges_to_del,
            'add_ranges': ip_ranges_to_add
        }
        try:
            cmd = self.templates["update"].render(**kwargs)
```
4. Note that the default behavior when no update template is defined, is one where nothing executes during update peer operations, thereby making this change fully backward compatible and requiring no breaking changes in terms of templates for users of bgpcfgd.
4. We expose similar logic as listed in 1, 2 for a delete handling, ie we add a delete template under self.templates["delete"] if such a template exists in the directory structure
5. Upon a delete peer ocurring, we render the delete template(instead of executing the current behavior of ```no neighbor {{ neighbor addr}}```), on the other hand if a delete template is not defined then the default behavior of ```no neighbor {{ neighbor addr}}``` applies as usual, thereby making this change backward compatible.
6. Bgpcfgd will write a State DB entry per the schema from section 2.2. This will be utilized by the SDN controller to identify what has been processed by bgpcfgd in terms of configuration.

## 2.5 Docker-FPM-FRR bgpd template:
### Background:
BGP configurations via templates are rendered via 3 different files: instance.conf.j2, policies.conf.j2, peer-group.conf.j2, and these j2 files are able to further branch out and invoke other usecase specific j2 files OR add usecase specific configuration within the same j2 file. These templates define various configurations for peers, route-maps, peer-groups, prefix-lists and more...

### New changes:
An update.conf.j2 and delete.conf.j2 will be defined in the same folder path structure as above, and similar branch out logic like the existing j2 files can be used with update.conf.j2 and delete.conf.j2. The update.conf.j2 and delete.conf.j2 will host the required logic to not only modify and delete the peers respectively, but also modify/delete associated configurations like route maps, peer groups, prefix lists etc. For the the purposes of this design we aim to simplify and only have a single j2 for update and delete each, which implies that update.j2 and delete.j2 will contain configuration that spans across all 3 types of config: instance, peer-group and policies. The alternate approach we considered  was defining an update/delete version for each type of config, thereby defining multiple templates as follows: instance.update.conf.j2, policies.update.conf.j2, peer-group.update.conf.j2, instances.delete.conf.j2, policies.delete.conf.j2, peer-group.delete.conf.j2. We preferred the former approach of a single update.conf.j2 and delete.conf.j2 because of the simplicity it brings, moving to the latter model can be taken up in the future if use-cases for update and delete expand beyond and it becomes important to have more segregation of configuration across instance, policies and peer groups for the newly added update and delete operations.

# 3 Test Plan
Bgpcfgd, CLI and template changes will have corresponding UTs.

New SONiC-mgmt tests will be introduced to test the following:
1. Update template, and that new peer ranges are applied
2. Verify that rendering the update template does not impact existing BGP sessions
2. Delete template, and verify that the whole dynamic peer group is removed
3. BGP session creation on a VNET
4. CLI validation
5. State DB validation:
   - Ensure consistency between the State DB and the configuration applied.
6. Scale test with 2/4k BGP sessions established, with PTF based traffic going through each of the vnet/sessions, we will check that switch's CPU and memory usage are in acceptable ranges and that other control plane actions of the switch are unimpacted by the high scale of BGP sessions
7. Stress tests, including:
   - Config reload/reboot, measuring the time taken for the sessions to re-establish, we establish a base line by testing and will then set targets for improvement(if required)
   - Modify dynamic sessions at full scale, ensuring that the newly added and removed sessions take effect in acceptable time(<1 minute)
