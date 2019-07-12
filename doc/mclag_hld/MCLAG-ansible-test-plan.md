# MCLAG feature test plan <!-- omit in toc -->

- [overview](#overview)
  - [Scope](#Scope)
  - [Testbed](#Testbed)
  - [Topology](#Topology)
    - [Physical topology](#Physical-topology)
    - [Logical topologies](#Logical-topologies)
    - [mclag logical topology](#mclag-logical-topology)
  - [Application scenarios](#Application-scenarios)
    - [L2 scenario](#L2-scenario)
    - [L3 scenario](#L3-scenario)
    - [VXLAN scenario](#VXLAN-scenario)
- [Setup configuration](#Setup-configuration)
  - [Setup of DUT switch](#Setup-of-DUT-switch)
  - [Ansible scripts to setup and run test](#Ansible-scripts-to-setup-and-run-test)
    - [Command to deploy the topo t0-mclag](#Command-to-deploy-the-topo-t0-mclag)
    - [Deploy the initial configuration for both devices separately (with an extra parameter dut_no)](#Deploy-the-initial-configuration-for-both-devices-separately-with-an-extra-parameter-dutno)
    - [mclag_config_dut2.yml](#mclagconfigdut2yml)
    - [mclag.yml](#mclagyml)
- [PTF Test](#PTF-Test)
  - [Input files for PTF test](#Input-files-for-PTF-test)
  - [Traffic validation in PTF](#Traffic-validation-in-PTF)
- [Test cases](#Test-cases)
  - [Summary](#Summary)
  - [L2 scenario test cases](#L2-scenario-test-cases)
    - [Test case L2#1 - mclag info check and verify data forwarding is correct through mclag](#Test-case-L21---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag)
    - [Test case L2#2 - Verify data forwarding is correct when mclag enabled interface status change](#Test-case-L22---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change)
    - [Test case L2#3 - Verify data forwarding is correct when peer-link status change](#Test-case-L23---Verify-data-forwarding-is-correct-when-peer-link-status-change)
    - [Test case L2#4 - Verify data forwarding is correct when keepalive link status change](#Test-case-L24---Verify-data-forwarding-is-correct-when-keepalive-link-status-change)
    - [Test case L2#5 - Verify data forwarding is correct when peer-link and keepalive link status both change](#Test-case-L25---Verify-data-forwarding-is-correct-when-peer-link-and-keepalive-link-status-both-change)
    - [Test case L2#6 - Verify data forwarding is correct when active device of mclag status change](#Test-case-L26---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change)
    - [Test case L2#7 - Verify data forwarding is correct when standby device of mclag status change](#Test-case-L27---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change)
    - [Test case L2#8 - Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-L28---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot)
    - [Test case L2#9 - Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-L29---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot)
  - [L3 scenario test cases](#L3-scenario-test-cases)
    - [Test case L3#1 - mclag info check and verify data forwarding is correct through mclag](#Test-case-L31---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag)
    - [Test case L3#2 - Verify data forwarding is correct when mclag enabled interface status change](#Test-case-L32---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change)
    - [Test case L3#3 - Verify data forwarding is correct when keepalive link status change](#Test-case-L33---Verify-data-forwarding-is-correct-when-keepalive-link-status-change)
    - [Test case L3#4 - Verify data forwarding is correct when active device of mclag status change](#Test-case-L34---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change)
    - [Test case L3#5 - Verify data forwarding is correct when standby device of mclag status change](#Test-case-L35---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change)
    - [Test case L3#6 - Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-L36---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot)
    - [Test case L3#7 - Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-L37---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot)
  - [VXLAN scenario test cases](#VXLAN-scenario-test-cases)
    - [Test case VXLAN#1 - mclag info check and verify data forwarding is correct through mclag](#Test-case-VXLAN1---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag)
    - [Test case VXLAN#2 - Verify data forwarding is correct when mclag enabled interface status change](#Test-case-VXLAN2---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change)
    - [Test case VXLAN#3 - Verify data forwarding is correct when peer-link status change](#Test-case-VXLAN3---Verify-data-forwarding-is-correct-when-peer-link-status-change)
    - [Test case VXLAN#4 - Verify data forwarding is correct when keepalive link status change](#Test-case-VXLAN4---Verify-data-forwarding-is-correct-when-keepalive-link-status-change)
    - [Test case VXLAN#5 - Verify data forwarding is correct when peer-link and keepalive link status both change](#Test-case-VXLAN5---Verify-data-forwarding-is-correct-when-peer-link-and-keepalive-link-status-both-change)
    - [Test case VXLAN#6 - Verify data forwarding is correct when active device of mclag status change](#Test-case-VXLAN6---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change)
    - [Test case VXLAN#7 - Verify data forwarding is correct when standby device of mclag status change](#Test-case-VXLAN7---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change)
    - [Test case VXLAN#8 - Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-VXLAN8---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot)
    - [Test case VXLAN#9 - Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-VXLAN9---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot)
- [TODO](#TODO)

## overview

The purpose is to test functionality of MCLAG on the SONIC switch DUT, closely resembling production environment.

### Scope

The test is running on real SONIC switch with testbed's basic configuration. The purpose of the test isn't targeting to specific class or API which are coverd by vs test cases, but functional test of MCLAG on SONIC system.

### Testbed

The test will run on the following testbed (**docker ptf must support teamd**):

- t0-mclag

### Topology

#### Physical topology

MCLAG test must use two DUTs, you can connect those two DUTs to two different leaf fanout switches, or connect those two DUTs to the same leaf fanout switch. The part in the red box needs to be added on the original SONiC test topology.

SONiC testbed overview can be found at [here](https://github.com/Azure/sonic-mgmt/blob/master/ansible/doc/README.testbed.Overview.md)

![testbed server Physical topo](https://github.com/shine4chen/SONiC/blob/mclag-test-case/images/mclag_hld/testbed-server-physical-topo.png)

#### Logical topologies

Testbeds t0-mclag is modified based on the Testbeds t0.

![testbed t0 topo](https://github.com/shine4chen/SONiC/blob/mclag-test-case/images/mclag_hld/testbed-t0-topo.png)

![testbed t0 mclag topo](https://github.com/shine4chen/SONiC/blob/mclag-test-case/images/mclag_hld/testbed-t0-mclag-topo.png)

#### mclag logical topology

![mclag logical topo](https://github.com/shine4chen/SONiC/blob/mclag-test-case/images/mclag_hld/mclag-logical-topo.png)

### Application scenarios

#### L2 scenario

All links to server ports are L2 mode, and peer-link must allow all vlans to be used. DUT is the gateway of the servers. DUT binds MCLAG's vlan interface IP address to be the same except peer-link.

#### L3 scenario

All links to server ports are L3 mode, the peer-link is optional. DUT is the gateway of the servers. DUT binds MCLAG's interface ip address must be the same except peer-link.

#### VXLAN scenario

All links to server ports are L2 mode. DUT is the gateway of the servers. DUT binds MCLAG's vlan interface IP address to be the same except peer-link.

## Setup configuration

### Setup of DUT switch

Setup of SONIC DUT will be done by Ansible script. During setup Ansible will copy JSON file containing configuration for mclag to the DUT. Config utility will be used to push configuration to the SONiC DB.

**Template**

```jason
"MC_LAG": {
    "<mclag-id>": {
        "local_ip": "<IP>",
        "peer_ip": "<IP>",
        "peer_link": "peer_link_name",
        "mclag_interface": "PortChanne_id"
    }
}
```

**Attributes**

```jason
"<mclag-id>"      =   Description: mclag domain id
                     Attr status: mandatory
                     Value range: 1-65535
"local_ip"        =   Description: local ip address for mclag
                     Attr status: mandatory
                     Value range: A valid IPv4 address
"peer_ip"         =   Description: peer ip address for mclag
                     Attr status: mandatory
                     Value range: A valid IPv4 address
"peer_link"       =   Description: peer link Ethernet name or PortChannel name
                     Attr status: mandatory(For L3 scenario, this is optional)
                     Value range: Ethernet, PortChannel or Tunnel name
"mclag_interface" =   Description: PortChannel name which bind mclag
                     Attr status: mandatory
                     Value range: PortChannel name
```

**Example**

```jason
"MC_LAG": {
    "100": {
        "local_ip": "10.100.1.1",
        "peer_ip": "10.100.1.2",
        "peer_link": "PortChannel0100",
        "mclag_interface": "PortChannel0001, PortChannel0002, PortChannel0003, PortChannel0004, PortChannel0005, PortChannel0006, PortChannel0007, PortChannel0008, PortChannel0009, PortChannel0010, PortChannel0011, PortChannel0012, PortChannel0013, PortChannel0014, PortChannel0015, PortChannel0016, PortChannel0017, PortChannel0018, PortChannel0019, PortChannel0020, PortChannel0021, PortChannel0022, PortChannel0023, PortChannel0024"
    }
}
```

### Ansible scripts to setup and run test

#### Command to deploy the topo t0-mclag

- ./testbed-cli.sh add-topo vms-t0-mclag ~/.password

#### Deploy the initial configuration for both devices separately (**with an extra parameter dut_no**)

- ansible-playbook -i lab config_sonic_basedon_testbed.yml -l "dut1_name" -e vm_base="VM0300" -e topo=t0-mclag -e deploy=True -e save=True -e testbed_name=vms-t0-mclag -e dut_no=1
- ansible-playbook -i lab config_sonic_basedon_testbed.yml -l "dut2_name" -e vm_base="VM0300" -e topo=t0-mclag -e deploy=True -e save=True -e testbed_name=vms-t0-mclag-dut2 -e dut_no=2

#### mclag_config_dut2.yml

mclag_config_dut2.yml when run with testname “mclag_config_dut2” will do the following:

- Generate mclag configuration on DUT2.
- Generate some port info of DUT2

#### mclag.yml

mclag.yml when run with testname “mclag” will do the following:

- Generate and apply mclag configuration on two DUTs.
- Run test.
- Clean up dynamic and temporary mclag configuration.

## PTF Test

### Input files for PTF test

PTF test will generate traffic between ports and make sure it passes according to the mclag configuration. Depending on the testbed topology and the existing configuration (e.g. ECMP, LAGS, etc) packets may arrive to different ports. Therefore ports connection information will be generated from the minigraph and supplied to the PTF script.

### Traffic validation in PTF

Depending on the test PTF test will verify the packet arrived or dropped.

## Test cases

### Summary

| NO. | Test case info |

| -: | - | - |

[L2 scenario test cases](#L2-scenario-test-cases) |

| 1 | [mclag info check and verify data forwarding is correct through mclag](#Test-case-L2#1---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag) |

| 2 | [Verify data forwarding is correct when mclag enabled interface status change](#Test-case-L2#2---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change) |

| 3 | [Verify data forwarding is correct when peer-link status change](#Test-case-L2#3---Verify-data-forwarding-is-correct-when-peer-link-status-change) |

| 4 | [Verify data forwarding is correct when keepalive link status change](#Test-case-L2#4---Verify-data-forwarding-is-correct-when-Keepalive-link-status-change) |

| 5 | [Verify data forwarding is correct when peer-link and keepalive link status both change](#Test-case-L2#5---Verify-data-forwarding-is-correct-when-peer-link-and-Keepalive-link-status-both-change) |

| 6 | [Verify data forwarding is correct when active device of mclag status change](#Test-case-L2#6---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change) |

| 7 | [Verify data forwarding is correct when standby device of mclag status change](#Test-case-L2#7---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change) |

| 8 | [Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-L2#8---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot) |

| 9 | [Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-L2#9---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot) |

[L3 scenario test cases](#L3-scenario-test-cases) |

| 1 | [mclag info check and verify data forwarding is correct through mclag](#Test-case-L3#1---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag) |

| 2 | [Verify data forwarding is correct when mclag enabled interface status change](#Test-case-L3#2---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change) |

| 3 | [Verify data forwarding is correct when keepalive link status change](#Test-case-L3#3---Verify-data-forwarding-is-correct-when-keepalive-link-status-change) |

| 4 | [Verify data forwarding is correct when active device of mclag status change](#Test-case-L3#4---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change) |

| 5 | [Verify data forwarding is correct when standby device of mclag status change](#Test-case-L3#5---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change) |

| 6 | [Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-L3#6---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot) |

| 7 | [Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-L3#7---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot) |

[VXLAN scenario test cases](#VXLAN-scenario-test-cases) |

| 1 | [mclag info check and verify data forwarding is correct through mclag](#Test-case-VXLAN#1---mclag-info-check-and-verify-data-forwarding-is-correct-through-mclag) |

| 2 | [Verify data forwarding is correct when mclag enabled interface status change](#Test-case-VXLAN#2---Verify-data-forwarding-is-correct-when-mclag-enabled-interface-status-change) |

| 3 | [Verify data forwarding is correct when peer-link status change](#Test-case-VXLAN#3---Verify-data-forwarding-is-correct-when-peer-link-status-change) |

| 4 | [Verify data forwarding is correct when keepalive link status change](#Test-case-VXLAN#4---Verify-data-forwarding-is-correct-when-Keepalive-link-status-change) |

| 5 | [Verify data forwarding is correct when peer-link and keepalive link status both change](#Test-case-VXLAN#5---Verify-data-forwarding-is-correct-when-peer-link-and-Keepalive-link-status-both-change) |

| 6 | [Verify data forwarding is correct when active device of mclag status change](#Test-case-VXLAN#6---Verify-data-forwarding-is-correct-when-active-device-of-mclag-status-change) |

| 7 | [Verify data forwarding is correct when standby device of mclag status change](#Test-case-VXLAN#7---Verify-data-forwarding-is-correct-when-standby-device-of-mclag-status-change) |

| 8 | [Verify data forwarding is correct when active devices of mclag warm-reboot](#Test-case-VXLAN#8---Verify-data-forwarding-is-correct-when-active-devices-of-mclag-warm-reboot) |

| 9 | [Verify data forwarding is correct when standby devices of mclag warm-reboot](#Test-case-VXLAN#9---Verify-data-forwarding-is-correct-when-standby-devices-of-mclag-warm-reboot) |

### L2 scenario test cases

#### SetUp: Load mclag L2 configuration files to dut and load it  <!-- omit in toc -->

#### Test case L2#1 - mclag info check and verify data forwarding is correct through mclag

##### Test objective <!-- omit in toc -->

Verify that mclag info is correct when mclag build ok.

Verify data forwarding is correct through mclag when mclag build ok.

##### Test steps <!-- omit in toc -->

1. Verify ping succeed between mclag peers.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive is ok.
3. Verify standby device changes its LACP system ID to be the same as active device.
4. Servers(including orphan ports) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reach to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
6. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#2 - Verify data forwarding is correct when mclag enabled interface status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when mclag enabled interface status change.

##### Test steps <!-- omit in toc -->

1. mclag enabled interface status change to down.
2. Servers(exclude down ports) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
3. "show mac" command verify the macs learned on down port before will point to the peer-link.
4. "show arp" command verify the arps learned on down port before will point to the peer-link.
5. mclag enabled interface status recover to up.
6. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
7. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
8. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#3 - Verify data forwarding is correct when peer-link status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when peer-link status change.

##### Test steps <!-- omit in toc -->

1. Peer-link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive is still ok.
3. Servers(exclude orphan ports) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device.
6. Peer-link status recover to up.
7. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
8. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
9. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#4 - Verify data forwarding is correct when keepalive link status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when keepalive link status change.

##### Test steps <!-- omit in toc -->

1. Keepalive link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to error.
3. Verify standby device changes its LACP system ID to the local default
4. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on standby device orphan ports will be deleted.
6. "show arp" command verify the arps learned on standby device orphan ports will be deleted.
7. Keepalive link status recover to up.
8. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to ok.
9. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
10. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
11. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#5 - Verify data forwarding is correct when peer-link and keepalive link status both change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when peer-link and keepalive link status both change.

##### Test steps <!-- omit in toc -->

1. Peer-link and keepalive link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to error.
3. Verify standby device changes its LACP system ID to the local default
4. Servers(exclude orphan ports and those ports link to standby device of mclag) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on standby device orphan ports will be deleted.
6. "show arp" command verify the arps learned on standby device orphan ports will be deleted.
7. Peer-link and keepalive link status recover to up.
8. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to ok.
9. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
10. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
11. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#6 - Verify data forwarding is correct when active device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Active device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to error.
3. Servers(exclude ports which link to active device of mclag) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command on standby device verify the macs learned on active device orphan ports will be deleted.
5. "show arp" command on standby device verify the arps learned on active device orphan ports will be deleted.
6. Active device of mclag status recover to up.
7. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to ok.
8. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
9. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
10. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#7 - Verify data forwarding is correct when standby device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to error.
3. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command on standby device verify the macs learned on active device orphan ports will be deleted.
5. "show arp" command on standby device verify the arps learned on active device orphan ports will be deleted.
6. Standby device of mclag status recover to up.
7. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to ok.
8. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
9. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
10. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#8 - Verify data forwarding is correct when active devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Active device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on standby device.
3. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L2#9 - Verify data forwarding is correct when standby devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on active device.
3. Servers will send packets to others Servers and VMs(send L2 packets to servers that belong to the same vlan, and send L3 packets to VMs and servers belonging to other vlans). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### TearDown: Set default configuration <!-- omit in toc -->

### L3 scenario test cases

#### SetUp: Load mclag L3 configuration files to dut and load it <!-- omit in toc -->

#### Test case L3#1 - mclag info check and verify data forwarding is correct through mclag

##### Test objective <!-- omit in toc -->

Verify that mclag info is correct when mclag build ok.

Verify data forwarding is correct through mclag when mclag build ok.

##### Test steps <!-- omit in toc -->

1. Verify ping succeed between mclag peers.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive is ok.
3. Verify standby device changes its LACP system ID to be the same as active device.
4. Servers(including orphan ports) will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reach to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device(Services on orphan ports forwarding support by routing protocol or static route).

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#2 - Verify data forwarding is correct when mclag enabled interface status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when mclag enabled interface status change.

##### Test steps <!-- omit in toc -->

1. mclag enabled interface status change to down.
2. Servers(exclude down ports) will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
3. mclag enabled interface status recover to up.
4. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#3 - Verify data forwarding is correct when keepalive link status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when keepalive link status change.

##### Test steps <!-- omit in toc -->

1. Keepalive link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to error.
3. Verify standby device changes its LACP system ID to the local default
4. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. Keepalive link status recover to up.
6. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to ok.
7. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#4 - Verify data forwarding is correct when active device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Active device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to error.
3. Servers(exclude ports which link to active device of mclag) will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. Active device of mclag status recover to up.
5. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to ok.
6. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#5 - Verify data forwarding is correct when standby device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to error.
3. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. Standby device of mclag status recover to up.
5. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to ok.
6. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#6 - Verify data forwarding is correct when active devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Active device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on standby device.
3. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case L3#7 - Verify data forwarding is correct when standby devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on active device.
3. Servers will send packets to others Servers and VMs(send L3 packets to other servers and VMs). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### TearDown: Set default configuration <!-- omit in toc -->

### VXLAN scenario test cases

#### SetUp: Load mclag VXLAN configuration files to dut and load it  <!-- omit in toc -->

#### Test case VXLAN#1 - mclag info check and verify data forwarding is correct through mclag

##### Test objective <!-- omit in toc -->

Verify that mclag info is correct when mclag build ok.

Verify data forwarding is correct through mclag when mclag build ok.

##### Test steps <!-- omit in toc -->

1. Verify ping succeed between mclag peers.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive is ok.
3. Verify standby device changes its LACP system ID to be the same as active device.
4. Servers(including orphan ports) will send packets to others Servers. When packet reach to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
6. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#2 - Verify data forwarding is correct when mclag enabled interface status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when mclag enabled interface status change.

##### Test steps <!-- omit in toc -->

1. mclag enabled interface status change to down.
2. Servers(exclude down ports) will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
3. "show mac" command verify the macs learned on down port before will point to the peer-link.
4. "show arp" command verify the arps learned on down port before will point to the peer-link.
5. mclag enabled interface status recover to up.
6. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
7. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
8. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#3 - Verify data forwarding is correct when peer-link status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when peer-link status change.

##### Test steps <!-- omit in toc -->

1. Peer-link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive is still ok.
3. Servers will send packets to others Servers(exclude orphan ports). When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device.
6. Peer-link status recover to up.
7. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
8. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
9. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

**Expected test result: Failed**

#### Test case VXLAN#4 - Verify data forwarding is correct when keepalive link status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when keepalive link status change.

##### Test steps <!-- omit in toc -->

1. Keepalive link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to error.
3. Verify standby device changes its LACP system ID to the local default
4. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on standby device orphan ports will be deleted.
6. "show arp" command verify the arps learned on standby device orphan ports will be deleted.
7. Keepalive link status recover to up.
8. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to ok.
9. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
10. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
11. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#5 - Verify data forwarding is correct when peer-link and keepalive link status both change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when peer-link and keepalive link status both change.

##### Test steps <!-- omit in toc -->

1. Peer-link and keepalive link status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to error.
3. Verify standby device changes its LACP system ID to the local default
4. Servers(exclude orphan ports and those ports link to standby device of mclag) will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
5. "show mac" command verify the macs learned on standby device orphan ports will be deleted.
6. "show arp" command verify the arps learned on standby device orphan ports will be deleted.
7. Peer-link and keepalive link status recover to up.
8. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive change to ok.
9. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
10. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
11. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

**Expected test result: Failed**

#### Test case VXLAN#6 - Verify data forwarding is correct when active device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Active device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to error.
3. Servers(exclude ports which link to active device of mclag) will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command on standby device verify the macs learned on active device orphan ports will be deleted.
5. "show arp" command on standby device verify the arps learned on active device orphan ports will be deleted.
6. Active device of mclag status recover to up.
7. "mclagdctl -i \<mclag-id\> dump state" command on standby device verify mclag keepalive change to ok.
8. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
9. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
10. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#7 - Verify data forwarding is correct when standby device of mclag status change

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby device of mclag status change.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag status change to down.
2. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to error.
3. Servers(exclude ports which link to standby device of mclag) will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command on standby device verify the macs learned on active device orphan ports will be deleted.
5. "show arp" command on standby device verify the arps learned on active device orphan ports will be deleted.
6. Standby device of mclag status recover to up.
7. "mclagdctl -i \<mclag-id\> dump state" command on active device verify mclag keepalive change to ok.
8. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
9. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
10. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#8 - Verify data forwarding is correct when active devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when active devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Active device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on standby device.
3. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### Test case VXLAN#9 - Verify data forwarding is correct when standby devices of mclag warm-reboot

##### Test objective <!-- omit in toc -->

Verify data forwarding is correct when standby devices of mclag warm-reboot.

##### Test steps <!-- omit in toc -->

1. Standby device of mclag warm-reboot.
2. "mclagdctl -i \<mclag-id\> dump state" command verify mclag keepalive keep ok on active device.
3. Servers will send packets to others Servers. When packet reaches to SONIC DUT, it will forward to the correct destination. PTF will receive a copy of the packet and perform validations described in validation of Traffic.
4. "show mac" command verify the macs learned on mclag enabled interface are the same on both mclag device. The macs learned on orphan ports will point to the peer-link on another device.
5. "show arp" command verify the arps learned on mclag enabled interface are the same on both mclag device. The arps learned on orphan ports will point to the peer-link on another device.

##### Expected test result: Pass <!-- omit in toc -->

#### TearDown: Set default configuration <!-- omit in toc -->

## TODO

Peer-link cannot be closed in the VXLAN scenario, and the following two testcases will fail.
- Test case VXLAN#3 - Verify data forwarding is correct when peer-link status change
- Test case VXLAN#5 - Verify data forwarding is correct when peer-link and keepalive link status both change
