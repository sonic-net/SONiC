## gRPC client for active-actve DualToR scenario design

  
Table of Contents
=================
* [Scope](#scope)
* [Requirements](#Requirements)
* [gRPC client communicate to SoC over Loopback IP](#)
* [gRPC commuication over secure channel](#)
* [gRPC client initialization](#)
* [gRPC commuication to NIC simulator](#)


## Revision

| Rev | Date     | Author          | Change Description |
|:---:|:--------:|:---------------:|--------------------|
| 0.1 | 04/1/22 | Vaibhav Dahiya  | Initial version    |

## Scope
gRPC client design doc which would communicate with the SoC/ Nic-simulator tests in SONiC MGMT.
### Overview

This document summarizes the approach taken to accommodate gRPC client
for DualToR active active scenario. The gRPC client daemon's
main purpose is to provide a way for linkmgr to exchange RPC's with SoC
and do this within SONiC PMON docker


## Requirements

- to provide an interface for gRPC daemon to exchange RPC's with the gRPC server running on the SoC over a secure channel using a loopback IP.
- The RPC's exchanged with SoC would help linkmgr state machine make decisions as to transition the DualToR into active/standby state depending on the state of the SoC 
- the client communication to the SoC should go over proposed Loopback IP.
- gRPC client communication with Nic-simulator should be accomodated as part of this design doc.

## gRPC client communicate to SoC over Loopback IP

#### Background

- We need a way to communicate to SoC using a Loopback IPv4 which would not be adversitised to public from SONiC DualToR. This Loopback IP requirement arises because SoC has firewall rules which would not allow normal traffic to pass through. In Normal scenario the interface inside the subnet, which would be a vlan IP, would be the source IP of the packet going to the SoC for gRPC.As such we would need to use a well defined IP(Loopback IP) which would be allowed in SoC firewall rules, hence the requirement to communicate over a pre-defined IPv4 address. 

#### Possible Solutions for Loopback IP
- The Best approach would be BIND the socket which is used by the gRPC channel to Loopback interface using a gRPC API. There is a socket_mutator API which is available in C++, which allows us to accomplish this, and was also tested inside the lab. However the gRPC client is proposed to be written in Python, because platform API is installed inside PMON(Python) as well as in DualToR Active/Standby scenrio ycabled is also written in Python. The gRPC client logic is proposed to be run inside PMON container. Since the gRPC library does not expose this API in Python, nor does it expose the socket, this is not an easy workaround. The github issue is filed for this issue inside gRPC Github repo.

- Another approach could be adding a Kernel Route. We could add a Kernel Route to the SoC IP. For example
    ```
       sudo ip route add <SoC IP> via <vlan IP> src <Loopback IP>
    ```
  - The issue with adding a Kernel Route is the route_checker will fail for this route, since vlan IP is the HOST's own vlan IP within SONiC as such no real neighbor is present, hence the route_checker will not be able to validate this entry
  - SWSS orchagent will also complain about not able to install the entry in ASIC, since the entry will be present in APP DB but not present inside ASIC. This would deem more workarounds necessary to be able to accomodate this route using this approach.
  - For the kernel route approach we would have to accomodate these issues listed above 
- using an IPTABLES rule. We could add a POSTROUTING rule to the SNAT table with destination as SoC IP and source as Loopback IP. For Example
    ```
        sudo iptables -t nat -A POSTROUTING --destination <SoC IP> -j SNAT --to-source <LoopBack IP>
    ```
    - There could be single SNAT entry for the entire subnet which is covers all the SoC IP's connected to the ToR

#### Proposed Solution

- use the IPTABLES rule approach as with this approach, there are no more workarounds necessary after adding the rule. Caclmgrd will check the CONFIG DB DEVICE_METADATA and upon learning this is ToR with subtype DualToR, will add the IPTABLES rule, after checking the MUX_CABLE table inside CONFIG_DB.
    ```
        DEVICE_METADATA | localhost
        type: ToRRouter
	    subtype: DualToR 
    ```
    ```
        MUX_CABLE|PORTNAME
        SoC_IPv4: <SoC IP>
    ```
- The update_control_plane_nat_acls subroutine in caclmgrd will check for the above configuration and upon getting the config, it will add the POSTROUTING SNAT rule
- Currently the NAT rules which exist are only for trapping the SNMP packets coming in the front panel interface in the linux network namespace and sent to the docker0 subnet 240.12.1.x. These NAT rules which are present are for SNMP packets, which are destined for UDP + dest port 161
- Adding this new POSTROUTING rule should not cause any issues to the forwarding behavior to the ToR.
- caclmgrd will not be needed to be restarted in this approach. The SNAT iptables entry would be a one time install when caclmgrd starts. 
   For Example
```
admin@sonic:~$ sudo iptables -L -n -v -t nat --line-numbers  

Chain POSTROUTING (policy ACCEPT 0 packets, 0 bytes)
num   pkts bytes target     prot opt in     out     source               destination
1        0     0 SNAT       all  --  *      *       0.0.0.0/0            10.10.10.10          to:10.212.64.2
```

#### Rationale

  - This approach conveniently adds the rule for all the SoC IP's needed to be communivating with DualToR over gPRC, and SoC server and gRPC client would be able to communicate over agreed IP. 

## gRPC commuication over secure channel

#### Background
  
- gRPC listener aka Server would need some way to autheticate that it is a valid and secure way for communication to the SoC.
  
#### Proposed Solution

- gRPC client would basically use TLS for establishing a secure channel. We will get certs pulled by acms container and turned into a certificate and a key file, and we would use these to create a secure channel.

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
#### gRPC client authentication with Nic-Simulator
gRPC also would need to be authenticated with the server which would be run for SONiC-MGMT tests. For this the proposal is to add self generated certs in  as a task when NiC-Simulator would be injected. This would be similar to the way mux-simulator is injected today. This way when the gRPC client
is initiating the channels, it would be able to form a secure channel

## gRPC client initialization

- gRPC client should not be initialized for all images/configurations. Here the premise will be taken that the gRPC client would only be initailzed only for DualToR active-active scenario.

#### Proposed Solution
- the proposal is to have a cable_type field in MUX_CABLE table inside CONFIG_DB. During PMON initilazation once the configuration has been rendered, and CONFIG_DB is populated and if it is active-active it will initailze the grpc client daemon logic for that PORT. For the lifetime of gRPC daemon, it will monitor this PORT as gRPC port only and not muxcable port
-
    ```
        MUX_CABLE|PORTNAME
        SoC_IPv4: <SoC IP>
        cable_type: active_active
    ```
    This part is only for discussion- Should we seperate out the logic for gRPC or should we keep both ycabled and gRPC in the same daemon. We could have an extra field for DualToRType type. 
    ```
        DEVICE_METADATA | localhost
        type: ToRRouter
        subtype: DualToR 
        DualToRType: active-active/Both
    ```
#### Rationale
- This logic eases the utilization of gRPC client only confined to DualToR configurations meant for active-active scenario.

## gRPC communication with Nic-Simulator
 
- the gRPC server hosted on the server in the lab, needs to know a request originating from the client, belongs to which Port. As in the case of real SoC the gRPC server only has the knowledge of a single PORT, it does not need to distinguish between requests for different ports. However the gRPC server inside the lab will not have knowledge about the requests are orginating for different PORTs.

#### Proposed Solution using gRPC interceptor inside the client.

- Interceptor is an effective way to put additional data inside the RPC originating from the client. The idea is to add the SoC_IP belonging to the port inside the intercept channel when the requests are being sent.
- The interceptor channel wuld be created at Nic-Simulator injection time, and the meta_data entry would be populated.

For example
```
with grpc.insecure_channel("%s:%s" % (server, port)) as insecure_channel:
        metadata_interceptor = MetadataInterceptor(("grpc_server", "SoC_IP"))
        with grpc.intercept_channel(insecure_channel, metadata_interceptor) as channel:
            stub = nic_simulator_grpc_service_pb2_grpc.DualTorServiceStub(channel)
```

- the gRPC server listening to the requests would decode the meta_data and serve the requests for gRPC client by associating the SoC_IP with the port



