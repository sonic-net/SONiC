<!-- omit from toc -->
# DASH SONiC KVM

<!-- omit from toc -->
# Table of contents

- [1 Motivation](#1-motivation)
- [2 Architecture](#2-architecture)
- [3 Modules](#3-modules)
  - [3.1 BMv2 (dataplane engine)](#31-bmv2-dataplane-engine)
  - [3.2 Dataplane APP](#32-dataplane-app)
  - [3.3 SAIRedis](#33-sairedis)
  - [3.4 SWSS](#34-swss)
  - [3.5 GNMI/APP DB](#35-gnmiapp-db)
  - [3.6 Other SONiC Services](#36-other-sonic-services)
- [4 Dataflow](#4-dataflow)
  - [4.1 Data plane](#41-data-plane)
  - [4.2 Control plane](#42-control-plane)
- [5 KVM topology](#5-kvm-topology)
  - [5.1 Single device mode testbed](#51-single-device-mode-testbed)
  - [5.1.1 Create DPU testbed](#511-create-dpu-testbed)
  - [5.1.2 Connect to the DPU](#512-connect-to-the-dpu)
  - [5.1.3 gnmi client access](#513-gnmi-client-access)
  - [5.2 DPU with VPP NPU testbed](#52-dpu-with-vpp-npu-testbed)

# 1 Motivation

1. Provide a Proof of Concept (POC) for development and collaboration. Utilizing the typical SONiC workflow, we can leverage this virtual switch image to construct a virtual testbed, eliminating the need for a complete hardware device. This virtual DPU image enables the creation of a mixed hardware-software testbed or a software-only testbed, applicable to both the control plane and the data plane.
2. Enable Continuous Integration(CI) via Azure Pipelines (Azp) for SONiC repositories, like sonic-buildimage, sonic-swss and so on.

# 2 Architecture

![BMv2 virtual SONiC](../../images/dash/bmv2-virtual-sonic.svg)

# 3 Modules

## 3.1 BMv2 (dataplane engine)

This component is the original P4 BMv2 container image, which serves as the data plane implementation - usually in hardware.
It attaches three types of interfaces: system port(Ethernet), line port(eth), and DPDK port(CPU).
- Ethernet is used as the system port. Protocol services like BGP and LLDP perform send/receive operations on these interfaces.
- eth is used as the line port. These are native interfaces in KVM for communication between the inside and outside. The eth port and Ethernet port is one-to-one mapping.
- CPU is used for the DPDK port. The dataplane APP directly manipulates the traffic on these ports.

## 3.2 Dataplane APP

Due to the P4 and BMv2 limitation, such as flow creation, flow resimulation and etc, in this virtual DPU, our implementation is based on the VPP framework with the CPU interface to enhance the dataplane engine for these extra functions in the dataplane app module. Meanwhile, this dataplane APP loads the generated shared library, saidash, which communicates with BMv2 via GRPC. For the SAI APIs that will not be used by DASH/DPU SONiC, the SAI implementation will be mocked, as long as SWSS could work, e.g. DTEL. Additionally, this component connects with sairedis through a shim SAI agent(dashsai server - remote dashsai client).

We will have a dedicated doc on the data plane app for more details.

## 3.3 SAIRedis

In the original virtual SONiC, SAIRedis will load the saivs. However, in the new SONiC DASH virtual DPU, it will load the remote dashsai client mentioned above.

## 3.4 SWSS

The SWSS on this virtual DPU is almost the same as the one used in the physical DPU. We don't need to make any special changes to it.

## 3.5 GNMI/APP DB

The GNMI and APP DB are identical to the physical device. However, in this virtual image, we support two modes: DPU mode and single device mode. The details of these two modes will be described in the following section.

## 3.6 Other SONiC Services

We plan to keep the other services, such as BGP, LLDP, and others. these services will be kept, so the KVM runs the same way as how SONiC runs on the real DPU.

# 4 Dataflow
## 4.1 Data plane

All data plane traffic will enter the BMv2 simple switch and be forwarded to the target port based on the P4 logic imported on BMv2.

Here is an example about the data plane
```mermaid
graph TD

%% LLDP packet
    eth1 --> packet_dispatcher{"Packet dispatcher"}
    packet_dispatcher -->|LLDP| Ethernet0;
    Ethernet0 --> lldp_process["LLDP process"];

%% Normal VNET packet
    packet_dispatcher -->|DASH| dash_pipeline{"DASH Pipeline"}
    dash_pipeline -->|VNet| eth2;

%% TCP SYN packet
    dash_pipeline -->|"TCP SYN"| cpu0_in[CPU0];
    cpu0_in[CPU0] --> dataplane_app["Dataplane APP"];
    dataplane_app["Dataplane APP"] --> cpu0_out[CPU0];
    cpu0_out[CPU0] --> dash_pipeline
```

## 4.2 Control plane

In the physical SmartSwitch, configuration is forwarded via GNMI in the NPU. So, in the virtual SONiC environment, the SWSS module is capable of receiving configuration from an external GNMI service through the management port, eth-midplane. However, in the single device mode, the GNMI service can also be run within the KVM and directly forward the configuration to the local SWSS module.

# 5 KVM topology

This section describes the steps to setup a virtual DPU testbed, please check a [pre-learning document](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/README.testbed.VsSetup.md) to setup your environment and download the EOS container. Beginning the following steps, I assume you have got the cEOS image with the specific version(https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/group_vars/all/ceos.yml) and sonic-mgmt containers.


- The normal SONiC KVM image without DPU dataplane can be downloaded from: https://sonic-build.azurewebsites.net/api/sonic/artifacts?branchName=master&platform=vs&target=target/sonic-vs.img.gz
- The DPU SONiC KVM image with dataplane will be released at the next stage

## 5.1 Single device mode testbed

## 5.1.1 Create DPU testbed

```shell

# Login to your sonic-mgmt container
ssh -i ~/.ssh/id_rsa_docker_sonic_mgmt zegan@172.17.0.2

# CD to the ansible directory
cd /data/sonic-mgmt/ansible

# Build the DPU testbed
./testbed-cli.sh -t vtestbed.yaml -m veos_vtb  add-topo vms-kvm-dpu password.txt
./testbed-cli.sh -t vtestbed.yaml -m veos_vtb deploy-mg vms-kvm-dpu veos_vtb password.txt

```

If you are lucky, your testbed should pass all testcases via following commands

``` shell
# Login to your sonic-mgmt container
ssh -i ~/.ssh/id_rsa_docker_sonic_mgmt zegan@172.17.0.2

# CD to the tests directory
cd /data/sonic-mgmt/tests

# Run testcases
./run_tests.sh -u -n vms-kvm-dpu -d vlab-01 -m individual -e --skip_sanity -e --disable_loganalyzer  -c dash/test_dash_vnet.py -f vtestbed.yaml -i ../ansible/veos_vtb -e "--skip_dataplane_checking"
```

## 5.1.2 Connect to the DPU

``` shell
# Login to the DPU, the default password is `password` and the default mgmt IP address is `10.250.0.101`
sshpass -p 'password' ssh -o TCPKeepAlive=yes -o ServerAliveInterval=30 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no  admin@10.250.0.101

```

## 5.1.3 gnmi client access

Once dash test cases are completed, we can find required certificates in sonic-mgmt container.

```
# The certificates are in /tmp directory
user@mgmt:~$ ls -l /tmp/e55648be-5a9c-49da-bcf7-645b1a926fb6
total 40
-rw-r--r-- 1 user user   99 Apr 12 05:52 extfile.cnf
-rw------- 1 user user 1675 Apr 12 05:52 gnmiCA.key
-rw-r--r-- 1 user user 1131 Apr 12 05:52 gnmiCA.pem
-rw-r--r-- 1 user user   41 Apr 12 05:52 gnmiCA.srl
-rw-r--r-- 1 user user 1017 Apr 12 05:52 gnmiclient.crt
-rw-r--r-- 1 user user  907 Apr 12 05:52 gnmiclient.csr
-rw------- 1 user user 1679 Apr 12 05:52 gnmiclient.key
-rw-r--r-- 1 user user 1070 Apr 12 05:52 gnmiserver.crt
-rw-r--r-- 1 user user  907 Apr 12 05:52 gnmiserver.csr
-rw------- 1 user user 1675 Apr 12 05:52 gnmiserver.key
```

Please install gnmi_cli_py from https://github.com/lguohan/gnxi/tree/master/gnmi_cli_py.

Restart GNMI server with server certificates:

```
# Run below commands on DUT
docker exec gnmi supervisorctl stop gnmi-native
docker exec gnmi bash -c "/usr/bin/nohup /usr/sbin/telemetry -logtostderr --port 50052 --server_crt /etc/sonic/telemetry/gnmiserver.crt --server_key /etc/sonic/telemetry/gnmiserver.key --ca_crt /etc/sonic/telemetry/gnmiCA.pem -gnmi_native_write=true -v=10 >/root/gnmi.log 2>&1 &"
```

Follow below example to run GNMI client:

```
# /root/update1 and /root/update2 are protobuf value for DASH table
python2 /root/gnxi/gnmi_cli_py/py_gnmicli.py --timeout 30 -t 10.0.0.88 -p 50052 -xo sonic-db -rcert /root/gnmiCA.pem -pkey /root/gnmiclient.key -cchain /root/gnmiclient.crt -m set-update --xpath  /APPL_DB/localhost/DASH_APPLIANCE_TABLE[key=123] /APPL_DB/localhost/DASH_VNET_TABLE[key=Vnet1] --value  $/root/update1 $/root/update2
```

## 5.2 DPU with VPP NPU testbed

TBD
