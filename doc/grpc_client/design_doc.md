## gRPC client for active-actve DualToR scenario design

## Revision

| Rev | Date     | Author          | Change Description |
|:---:|:--------:|:---------------:|--------------------|
| 0.1 | 04/1/22 | Vaibhav Dahiya  | Initial version    |

## Scope

### Overview

This document summarizes the approach taken to accommodate gRPC client
for DualToR active active scenario. The gRPC client daemon's
main purpose is to provide a way for linkmgr to exchange RPC's with SoC
and do this within SONiC PMON docker


Challenge: to provide an interface for gRPC daemon to exchange RPC's with the gRPC server running on the SoC
           over a secure channel using a loopback IP. The RPC's exchanged with SoC
           would help linkmgr state machine make decisions as to transition the DualToR
           into active/standby depending on the state of the SoC 


### gRPC client communicate to SoC over Loopback IP

#### Background

- We need a way to communicate to SoC using a Loopback IPv4 which is not adversitised to public. This Loopback IP is a well defined IP which is allowed in SoC firewall rules, hence
the requirement to communicate over a pre-defined IPv4 address. 

  - The Best approach would be BIND the socket using the gRPC to Loopback interface using gRPC API. The socket_mutator API is available in C++, which allows us to accomplish this. However the gRPC client is prposed Python daemon run inside PMON container. As such as long as library does not expose this API in Python, this is not an easy workaround. The github issue is filed for gRPC library.
  - Adding a Kernel Route. We could add a Kernel Route to the soc IP. For example
    ```
       sudo ip route add <soc IP> via <vlan IP> src <Loopback IP>
    ```
  - Te issue with adding a Kernel Route is the route_cheker will fail for this, since vlan IP is the HOST's own vlan IP within SONiC as such no real neighbor is present
  - SWSS orchagent will complain about not able to istall the entry in ASIC, the entry will be present in APP DB but not present inside ASIC. This would deem more worarounds necessary to be able to use this approach.
  - using IPTABLES rule. For Example
    ```
        sudo iptables -t nat -A POSTROUTING --destination <soc IP> -j SNAT --to-source <LoopBack IP>
    ```

#### Proposed Solution

- use the IPTABLES rule approach as with this approach, this workaround is cleaner in a sense there are no more workarounds after adding the rule. Caclmgrd will check the CONFIG DB DEVICE_METADATA and upon learning this is ToR with subtype DualToR, will add the IPTABLES rule.
    ```
        DEVICE_METADATA | localhost
        type: ToRRouter
	subtype: DualToR 
    ```
    ```
        LINKMGR_CABLE|PORTNAME
        soc_ipv4: <soc IP>
    ```
- The update_control_plane_nat_acls in caclmgrd will look for the above configuration and upon getting the config, it will add the POSTROUTING nat rules

#### Rationale


  - This approach would add the rule for all the soc IP's contained to DualToR, and SoC server and gRPC client would be able to communicate over agreed IP 

#### gRPC commuication over secure channel

#### Background
  
- gRPC listener aka Server would need some way to autheticate that it is a valid and secure way for communication to the SoC.
  
#### Proposed Solution

- gRPC would basically use TLS for establishing a secure channel. We will get certs pulled by acms container and turned into a certificate and a key file, and we would use these to create a secure channel.

    ```
    'grpc_client_crt': '/etc/sonic/credentials/grpc_client.crt',
    'grpc_clinet_key': '/etc/sonic/credentials/grpc_client.key', 
    ```

    ```
    key = open('/etc/sonic/credentials/grpc_client.key', 'rb').read()
    cert_chain = open('/etc/sonic/credentials/grpc_client.crt', 'rb').read()
    credential = grpc.ssl_channel_credentials(
            private_key=key,
            certificate_chain=cert_chain)

    with grpc.secure_channel("{}:50075".format(host), credential) as channel:
        
        stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(channel)
        # perform RPC's
    ```
#### gRPC client initialization

- gRPC client should not be initialized for all images/configurations. Here the premise will be taken that the gRPC client will be initailzed only for DualToR active-active scenario.

#### Proposed Solution
- the proposal is to have a dualtortype field in DEVICE_METADATA table inside CONFIG_DB. During PMON initilazation once the sonic-cfggen has been rendered, it can check for DualToRtype field inide DEVICE_METADATA and if it is active-active/both it will initailze the grpc client daemon. 
    ```
        DEVICE_METADATA | localhost
        type: ToRRouter
	subtype: DualToR 
	DualToRtype: active-active/Both
    ```

    ```
        {% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR'%}
        {% if DEVICE_METADATA['localhost']['DualToRtype'] == 'active-active' or DEVICE_METADATA['localhost']['DualToRtype'] == 'Both'%}
    ```

#### Rationale
- This logic eases the utilization of gRPC client only confined to DualToR configurations meant for active-active scenario.


