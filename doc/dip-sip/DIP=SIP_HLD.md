# DIP=SIP PTF Validation High Level Design

## Overview

The purpose of this test is to validate that SONiC switch supports routing of L3 packets with DIP=SIP.

## Topology

```
                    |-----------------------|
                    |                       |
|--------|          |-------|               |
|DST HOST|----------|DST RIF|               |
|--------|          |-------|               |
                    |                       |
                    |          DUT          |
                    |                       |
|--------|          |-------|               |
|SRC HOST|----------|SRC RIF|               |
|--------|          |-------|               |
                    |                       |
                    |-----------------------|
```

_Note_:

> Hosts are emulated using VMs  
> RIF types are PORT/LAG

## Sources

### Structure

```
sonic-mgmt
|
|-ansible
  |
  |-roles
    |
    |-test
      |
      |-files
      | |
      | |-ptftests
      |   |
      |   |-dip_sip.py
      |
      |-tasks
      | |
      | |-dip_sip.yml
      |
      |-vars
        |
        |-testcases.yml
```

### testcases.yml

This file defines testcase entry point.

### dip_sip.yml

This file contains logic related to artifacts collection and aggregation.  
It performs all the necessary prerequisite operations based on provided topology.

Supported topologies:

* t0
* t0-16
* t0-56
* t0-64
* t0-64-32
* t0-116
* t1
* t1-lag
* t1-64-lag

Workflow:

1. Gather minigraph info
2. Gather LLDP info
3. Get DST/SRC host MAC address
3. Get DST/SRC router MAC/IPv4/IPv6 address
4. Get DST/SRC port indices (PTF port numbers)
5. Run PTF test

_Note_:

> Depending on router type there can be more than one member, thus we need to calculate all the member indices

### dip_sip.py

This file contains core PTF logic.  
It provides mechanism for UDP packets composing/sending/receiving.

Supported parameters:

| Parameter       | Description                                                   |
|:--------------- |:------------------------------------------------------------- |
| testbed_type    | Testbed type                                                  |
| dst_host_mac    | Destination host MAC address                                  |
| src_host_mac    | Source host MAC address                                       |
| dst_router_mac  | Destination router MAC address                                |
| src_router_mac  | Source router MAC address                                     |
| dst_router_ipv4 | Destination router IPv4 address                               |
| src_router_ipv4 | Source router IPv4 address                                    |
| dst_router_ipv6 | Destination router IPv6 address                               |
| src_router_ipv6 | Source router IPv6 address                                    |
| dst_port_ids    | Destination port array of indices (when router has a members) |
| src_port_ids    | Source port array of indices (when router has a members)      |

## Description

### Testcase summary

Basically, PTF is used to construct two packets: data packet and expected packet.  
After data packet is sent using source port index, we are waiting expected packet on one of the destination port indices.

Default values:

* pkt_ttl_hlim=64

Values:

* dst_host_ipv4_ipv6=\<dst_router_ipv4_ipv6\>+1
* src_host_ipv4_ipv6=\<src_router_ipv4_ipv6\>+1

Data packet:

* DST_MAC=\<src_router_mac\>
* SRC_MAC=\<src_host_mac\>
* DST_IPv4_IPv6=\<dst_host_ipv4_ipv6\>
* SRC_IPv4_IPv6=\<dst_host_ipv4_ipv6\>
* TTL_HL=\<pkt_ttl_hlim\>

Expected packet:

* DST_MAC=\<dst_host_mac\>
* SRC_MAC=\<dst_router_mac\>
* DST_IPv4_IPv6=\<dst_host_ipv4_ipv6\>
* SRC_IPv4_IPv6=\<dst_host_ipv4_ipv6\>
* TTL_HL=\<pkt_ttl_hlim\>-1

### Expected results

Testcase is considered to be passed successfully if packet is routed between router interfaces, otherwise - failed.

_Note_:

> In case of failure the appropriate error message will be printed (including expected and received packet dumps)

## Examples

```bash
sudo -H ansible-playbook test_sonic.yml -i inventory --limit arc-switch1025-t0 -e testbed_name=arc-switch1025-t0 -e testbed_type=t0 -e testcase_name=dip_sip -vvvvv
```

_Note_:
> Logs are located here: /tmp/dip_sip.DipSipTest.\<timestamp\>.log
