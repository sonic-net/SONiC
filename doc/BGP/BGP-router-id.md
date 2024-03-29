# BGP Router ID Explicitly Configured

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [Overview](#overview)
- [Requirements](#requirements)
- [High Level Design](#high-level-design)
- [Config DB Enhancement](#config-db-enhancement)
    - [DEVICE_METADATA](#device_metadata)

### Revision

| Revision | Date        | Author           | Change Description |
| -------- | ----------- | ---------------- | ------------------ |
| 1.0      | Mar 27 2024 | Yaqiang Zhu, Jing Kan | Initial proposal   |

### Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| FRR | A free and open source Internet routing protocol suite for Linux and Unix platforms |
| BGP Router ID | 32-bit value that uniquely identifies a BGP device |
| AS | Autonomous System |

### Scope

This document describes a mechanism to allow user explicitly configure BGP router id.

### Overview

Currently, there are some BGP hard codings in SONiC:
1. BGP router id was defined as a 32-bit value that uniquely identifies a BGP device. SONiC uses Loopback0 IPv4 address as BGP router id. This coupling prevents users from using customized router id. And FRR would choose an IP address in device to be BGP router id if Loopback0 IPv4 address doesn't exist. If the router id choosen by FRR is not unique in AS, it would be considered an error.
2. SONiC wouldn't add BGP peer when there is not Loopback0 IPv4 exists. It would cause BGP cannot establish.

Below is current workflow about BGP and router id, only includes contents related to Loopback0.

1. After bgp container started, configuration file `/etc/frr/bgpd.conf` for bgpd would be rendered. It will use Loopback0 IPv4 address as BGP router id, if it doesn't exist, the BGP router id wouldn't be specified.
2. bgpd start with configuration rendered before. If BGP router id is not specified, it would choose an IP address in device to be BGP router id.
3. After bgpcfgd started, it will add bgp peer depends on whether Loopback0 IPv4 exist.

<p align=center>
<img src="img/origin_bgp_seq.png" alt="Figure 1. Origin bgp seq" width=700>
</p>

### Requirements

Add support to allow user explicitly configure BGP router id.

### High Level Design

2 aspects enhancement:

1. Add a field `bgp_router_id` in `CONFIG_DB["DEVICE_METADATA"]["localhost"]` to support explicitly configure BGP router id. If `CONFIG_DB["DEVICE_METADATA"]["localhost"]["bgp_router_id"]` configured, always use it as BGP router id no matter whether Loopback0 IPv4 exist. With this change, the new BGP router id configuration behavior will be like follow. To be clarified that when bgp_router_id doesn't be configured, the behavior is totally same as previously.

|           | Loopback0 IPv4 address exists | Loopback0 IPv4 address doesn't exist |
|--------------|-------|------------|
| bgp_router_id configured | Honor bgp_router_id | Honor bgp_router_id |
| bgp_router_id doesn't be configured | Honor Loopback0 IPv4 address | FRR default router ID value is selected as a IP Address of the device. When router zebra is not enabled bgpd can’t get interface information so router-id is set to 0.0.0.0 |

2. Remove strong dependencies on Loopback0 IPv4 address when adding BGP peer in the situation that bgp_router_id is configured.With this change, the new BGP peer adding behavior will be like follow. To be clarified that when bgp_router_id doesn't be configured, the behavior is totally same as previously.

|          | Loopback0 IPv4 address exists | Loopback0 IPv4 address doesn't exist |
|--------------|-------|------------|
| bgp_router_id configured | Add BGP peer | Add BGP peer |
| bgp_router_id doesn't be configured | Add BGP peer | Do not add BGP peer |

Below is new workflow, the main changes are in `1.` and `3.`.

1. After bgp container started, configuration file `/etc/frr/bgpd.conf` for bgpd is would be rendered.
   * If CONFIG_DB`["DEVICE_METADATA"]["localhost"]["bgp_router_id"]` exists, use it as BGP router id.
   * Else if Loopback0 IPv4 address exists, use it as BGP router id.
   * Else, BGP router id wouldn't be specified.
2. bgpd start with configuration rendered before. If router id is not specified, it would choose an IP address in device to be router id, which would cause BGP cannot work if the router id is not unique in network.
3. After bgpcfgd started, it will start BGP peer based on configuration.
   * If Loopback0 IPv4 address exists, continue to add BGP peer.
   * Else if CONFIG_DB`["DEVICE_METADATA"]["localhost"]["bgp_router_id"]` exists, continue to add BGP peer.
   * Else, do nothing.

<p align=center>
<img src="img/new_bgp_seq.png" alt="Figure 2. New bgp seq" width=700>
</p>

### Config DB Enhancement

#### DEVICE_METADATA

**Configuration schema in ABNF format:**

```abnf
; DEVICE_METADATA table
key             = DEVICE_METADATA|localhost ; Device metadata configuration table
; field         = value
bgp_router_id   = inet:ipv4-address         ; Customized BGP router id
```

**Sample of CONFIG DB snippet:**

```json
{
    "DEVICE_METADATA": {
        "localhost": {
            "bgp_router_id": "10.1.0.32"
        }
    }
}
```

**Snippet of `sonic-device_metatadata.yang`:**

```
module sonic-device_metadata {
    container sonic-device_metadata {
        container DEVICE_METADATA {
            container localhost {
                leaf bgp_router_id {
                    type inet:ipv4-address
                }
            }
            /* end of container localhost */
        }
        /* end of container DEVICE_METADATA */
    }
    /* end of top level container */
}
/* end of module sonic-device_metadata */
```
