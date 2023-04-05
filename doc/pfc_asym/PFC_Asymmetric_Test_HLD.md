# Asymmetric PFC Test Plan

* [Overview](#Overview)
   * [Scope](#Scope)
   * [Testbed](#Testbed)
* [Setup configuration](#setup-configuration)
* [Existed modules refactoring](#existed-modules-refactoring)
* [Python  modules to setup and run test](#python-modules-to-setup-and-run-test)
   * [Python modules](#python-modules)
   * [PFC storm global variables](#pfc-storm-global-variables)
   * [PTF test case execution](#ptf-test-case-execution)
   * [Pytest fixtures](#pytest-fixtures)
		* [deploy_pfc_gen](#deploy_pfc_gen)
		* [setup](#setup)
		* [pfc_storm_template](#pfc_storm_template)
		* [pfc_storm_runner](#pfc_storm_runner)
		* [enable_pfc_asym](#enable_pfc_asym)
* [Test](#Test)
* [Test cases](#Test-cases)

## Overview
The purpose is to test functionality of Asymmetric PFC on the SONIC based DUT, closely resembling production environment.

### Scope
The test is targeting a running SONIC system with fully functioning configuration. The purpose of the test is to perform functional testing of Asymmetric PFC on SONIC system. There will be reused existed PTF test suite for PFC Asymmetric which is located at https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/roles/test/files/saitests/pfc_asym.py.

### Testbed
The test will run on the following testbeds:
* T0-x (all T0 configurations)

### DUT image
RPC image is required

## Setup configuration
No setup pre-configuration is required, test will configure and clean-up all the configuration.

## Existed modules refactoring
There is already existed PFC asymmetric test cases which use PTF to send traffic.

Test suite location

https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/roles/test/files/saitests/pfc_asym.py

It requires several updates:

1. Packets sending speed can be increased by using multiprocessing instead of multithreading library.

https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/roles/test/files/saitests/pfc_asym.py#L83


Replace ```threading.Thread``` to use ```multiprocessing.Process``` instead.

2. Looks like there is a redundancy in generating configuration file for ARP responder.

https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/roles/test/files/saitests/pfc_asym.py#L56

Fix the loop to store file only once


## Python  modules to setup and run test

### Python modules
*New test suite will be developed:*

```tests/pfc_asym/pfc_asym.py```

### PFC storm global variables
```
PFC_GEN_FILE = "pfc_gen.py"
```
PFC packets generator file name which is running on fanout
```
PFC_FRAMES_NUMBER = 1000000
```
Number of pause frames to send
```
PFC_QUEUE_INDEX = 0xff
```
Specify which priority will use non zero pause frame time


### PTF test case execution
To run existed PTF test cases there will be used ```tests/ptf_runner.py``` module

### Pytest fixtures
Preparation before test cases run will be executed in the following pytest fixtures:
- setup
- pfc_storm_template
- pfc_storm_runner
- deploy_pfc_gen
- flush_neighbors


### deploy_pfc_gen (scope="module", autouse=True)

To simulate that neighbors are overloaded (send many PFC frames) there is used PFC packets generator which is running on Fanout switch.
File location - ```roles/test/files/helpers/pfc_gen.py```

Currnet fixture deploys ```roles/test/files/helpers/pfc_gen.py``` to the fanout host.
This step can be different for different platforms. Below there is description how it works for Mellanox and Arista cases, also how to add support of another platform type.

#### Notes
The logic of ```pfc_gen.py``` deployment is not changing here, it just perform already existed logic for ```pfc_gen.py``` deployment.

**Mellanox platform**

PFC packet generator is automatically deployed during fanout deployment procedure.

Example of deploying fanout for Mellanox:
```
ansible-playbook -i lab fanout.yml -l ${FANOUT} --become --tags pfcwd_config -vvvv
```

**Arista platform**

Deploy steps:
- Ensure destination directory exists on fanout:
"/mnt/flash/"
- Create pfc generator file in case it doesn't exist
"/mnt/flash/pfc_gen.py"
- Deploy PFC generator to the fanout switch:
Copy "roles/test/files/helpers/pfc_gen.py" to "/mnt/flash" directory

**Other platforms**

Tests currently support deployment of arista fanout switches, **to support other platforms:**

1. Add platform specific logic to deploy pfc packet generator automatically in ```deploy_pfc_gen``` pytest fixture.
Or manualy deploy ```roles/test/files/helpers/pfc_gen.py``` and ensure the file is available on fanout switch.

2. Create ```pfc_storm_[sku].j2``` and ```pfc_storm_stop_[sku].j2``` under ```ansible/roles/test/templates/```
to trigger pfc storm **start/stop** action.

3. Set ```pfc_storm_start``` and ```pfc_storm_stop``` variables to platform-specific template names
in ```pfc_storm_template``` pytest fixture


### setup (scope="module")
This fixture performs initial steps which is required for test case execution, defined in Setup/Teardown sections.

Also it compose data which is used as input parameters for PTF test cases, and PFC - RX and TX masks which is used in test case logic.

Collected data is returned by fixture as dictionary object and is available to use in pytest test cases.

*Setup steps*

- Ensure topology is T0, skip tests run otherwise
- Gather minigraph facts about the device
- Get server ports OIDs
	```docker exec -i database redis-cli --raw -n 2 HMGET COUNTERS_PORT_NAME_MAP {server_ports_names}```
- Get server ports info
- Get non server port info
- Set unique MACs to PTF interfaces
	Run on PTF host- tests/scripts/change_mac.sh
- Set ARP responder:
	- Copy ARP responder to PTF
		```src=tests/scripts/arp_responder.py; dst=/opt```
	- Copy ARP responder supervisor configuration to the PTF container
		```
		src=tests/scripts/arp_responder.conf.j2
		dest=/etc/supervisor/conf.d/arp_responder.conf
		```
	- Update supervisor configuration
		Execute on PTF container:
		```
		supervisorctl reread
		supervisorctl update
		```
- Copy PTF tests to PTF host
	```src=roles/test/files/ptftests dest=/root```
- Copy SAI tests to PTF host
	```src=roles/test/files/saitests dest=/root```
- Copy PTF portmap to PTF host
	Copy default, if existed vendor specific, copy vendor specific
	```
	src=ansible/roles/test/files/mlnx/default_interface_to_front_map.ini
	dst=/root/default_interface_to_front_map.ini
	```

*Teardown steps*

- Verify PFC value is restored to default
- Remove PTF tests from PTF container
- Remove SAI tests from PTF container
- Remove portmap from PTF container
- Remove ARP responder
- Restore supervisor configuration

*Return dictionary in format*

```
{"pfc_bitmask": {
      "pfc_mask": [VALUE],
      "pfc_rx_mask": [VALUE],
      "pfc_tx_mask": [VALUE]
 },
 "ptf_test_params": {
    "port_map_file": [VALUE],
    "server": [VALUE],
    "server_ports": [VALUE],
    "non_server_port": [VALUE],
    "router_mac": [VALUE],
    "pfc_to_dscp": [VALUE],
    "lossless_priorities": [VALUE],
    "lossy_priorities": [VALUE]
 }
}
```

*Get lossless and lossy priorities*

- Get buffer PG keys
	```buf_pg_keys = docker exec -i database redis-cli --raw -n 4 KEYS *BUFFER_PG*```
- Get buffer PG profiles
	```docker exec -i database redis-cli -n 4 HGET {buf_pg_keys} "profile"```
- Get lossless priorities based on obtained buffer PG profiles
- Get lossy priorities based on obtained buffer PG profiles

*Get PFC to DSCP mapping*

* Get DSCP to TC map key
	```dscp_to_tc_key = docker exec -i database redis-cli --raw -n 4 KEYS *DSCP_TO_TC_MAP*```
* Get DSCP to TC map hash keys
	```dscp_to_tc_keys= docker exec -i database redis-cli --raw -n 4 HKEYS "{dscp_to_tc_key}"```

* Get DSCP to TC map
	```dscp_to_tc = docker exec -i database redis-cli -n 4 HGET {dscp_to_tc_keys} {dscp_to_tc_keys_item}```
* Get PFC to DSCP map
	```combine dscp_to_tc with dscp_to_tc_keys```


### pfc_storm_template (scope="module")
Creates dictionary which items will be used to start/stop PFC generator on fanout switch.
Dictionary values depends on fanout HWSKU (MLNX-OS, Arista or others)

*Return dictionary in format*
```
{"file": {
    "pfc_storm_start": [VALUE],
    "pfc_storm_stop": [VALUE]
  },
 "template_params": {
      "pfc_gen_file": PFC_GEN_FILE,
      "pfc_queue_index": PFC_QUEUE_INDEX,
      "pfc_frames_number": PFC_FRAMES_NUMBER,
      "pfc_fanout_interface": [VALUE],
      "ansible_eth0_ipv4_addr": [VALUE],
      "pfc_asym": True
  }
}
```

For HWSKU equal to "MLNX-OS":

      pfc_storm_start = "pfc_storm_mlnx.j2"
      pfc_storm_stop = "pfc_storm_stop_mlnx.j2"

For HWSKU equal to "Arista":

      pfc_storm_start = "pfc_storm_arista.j2"
      pfc_storm_stop = "pfc_storm_stop_arista.j2"


### pfc_storm_runner (scope="function")

*Setup steps*

* Start PFC generator on fanout switch
```
fanout.exec_template(pfc_storm_template["pfc_storm_start"], pfc_storm_template["template_params"])
```

*Teardown steps*

* Stop PFC generator on fanout switch
```
fanout.exec_template(pfc_storm_template["pfc_storm_stop"], pfc_storm_template["template_params"])
```

 
### enable_pfc_asym (scope="function")

*Setup steps*

* Enable asymmetric PFC on all server interfaces

For every server port(setup["server_ports"]) execute command:

```config interface pfc asymmetric [SERVER_PORT] on```

*Teardown steps*

* Disable asymmetric PFC on all server interfaces

For every server port(setup["server_ports"]) execute command:

```config interface pfc asymmetric [SERVER_PORT] off```

### flush_neighbors (scope="function", autouse=True)
Perform ARP table clear before start of each test case by executing ```sonic-clear arp``` command.
To help eliminate issues related to neighbors resolution.

## Test
The purpose of the tests cases is to perform functional testing of Asymmetric PFC on SONIC system.
General idea is to check how DUT behaves with enabled/disabled asymmetric PFC on server ports while DUT is overloaded with receiving PFC frames, which simulates that neighbors are overloaded by traffic.

To specify number of server ports to use can be used pytest option ```--server_ports_num```

## Test cases

### Test case # 1 – Asymmetric PFC Off TX pause frames
#### Test objective
Asymmetric PFC is disabled. Verify that DUT generates PFC frames only on lossless priorities when asymmetric PFC is disabled

#### Used fixtures
setup

#### Test steps
- Setup:
  - Start ARP responder
  - Limit maximum bandwith rate on the destination port by setting "1" into SAI port attribute SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID
  
- Clear all counters for all ports
- Get lossless priorities
- Get lossy priorities
- Get server ports info
- Get non server port info (Portchannel peers)
- Send 10000 packets for lossless priorities from all server ports (src) to non-server port (dst)
- Verify that some packets are dropped on src ports, which means that Rx queue is full
- Verify that PFC frames are generated for lossless priorities from src ports
- Send 10000 packets for lossy priorities from all server ports (src) to non-server port (dst)
- Verify that PFC frames are not generated for lossy priorities

- Teardown:
  - Restore maximum bandwith rate on the destination port by setting "0" into SAI port attribute SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID
   - Stop ARP responder

### Test case # 2 – Asymmetric PFC Off RX pause frames
#### Test objective
Asymmetric PFC is disabled. Verify that while receiving PFC frames DUT drops packets only for lossless priorities (RX and Tx queue buffers are full)

#### Used fixtures
setup, pfc_storm_runner

#### Test steps
- Setup:
  - Start ARP responder

- Clear all counters for all ports
- Get lossless priorities
- Get lossy priorities
- Get server ports info
- Get non server port info (Portchannel peers)
- Send 10000 packets for lossy priorities from non-server port (src) to all server ports (dst)
- Verify that packets are not dropped on src port
- Verify that packets are not dropped on dst ports
- Verify that packets are transmitted from dst ports
- Send 10000 packets for lossless priorities from non-server port (src) to all server ports (dst)
- Verify that some packets are dropped on src port, which means that Rx queue is full
- Verify that some packets are dropped on dst ports, which means that Tx buffer is full

- Teardown:
  - Stop ARP responder

### Test case # 3 – Asymmetric PFC On TX pause frames
#### Test objective
Asymmetric PFC is enabled. Verify that DUT generates PFC frames only on lossless priorities when asymmetric PFC is enabled

#### Used fixtures
setup, enable_pfc_asym

#### Test steps
- Setup:
  - Start ARP responder
  - Limit maximum bandwith rate on the destination port by setting "1" into SAI port attribute SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID

- As SAI attributes stores PFC values like a bit vector, calculate bitmask for each PFC mode according to configured "lossless" priorities to have possibility to check that asymmetric PFC configuration for RX and TX queues was applied correctly for configured PFC mode:
  - Calculate bitmask for the PFC value
  - Calculate bitmask for the asymmetric PFC Tx value
  - Calculate bitmask for the asymmetric PFC Rx value

- Verify asymetric PFC mode is enabled on each server port
- Get asymmetric PFC Rx value for all server ports
- Verify asymmetric PFC Rx value for each server port
- Get asymmetric PFC Tx value for all server ports
- Verify asymmetric PFC Tx value for all server ports

- Clear all counters for all ports
- Get lossless priorities
- Get lossy priorities
- Get server ports info
- Get non server port info (Portchannel peers)

- Send 10000 packets for lossless priorities from all server ports (src) to non-server port (dst)
- Verify that some packets are dropped on src ports, which means that Rx queue is full
- Verify that PFC frames are generated for lossless priorities
- Send 10000 packets for lossy priorities from all server ports (src) to non-server port (dst)
- Verify that PFC frames are not generated for lossy priorities

- Verify PFC value is restored to default

- Teardown:
  - Restore maximum bandwith rate on the destination port by setting "0" into SAI port attribute SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID
   - Stop ARP responder

### Test case # 4 – Asymmetric PFC On Rx pause frames on all priorities
#### Test objective
Asymmetric PFC is enabled. Verify that while receiving PFC frames DUT handle PFC frames on all priorities when asymetric mode is enabled

#### Used fixtures
setup, pfc_storm_runner, enable_pfc_asym

#### Test steps
- Setup:
  - Start ARP responder

- Clear all counters for all ports
- Get lossless priorities
- Get lossy priorities
- Get server ports info
- Get non server port info (Portchannel peers)
- Send 10000 packets for lossy priorities from non-server port (src) to all server ports (dst)
- Verify that packets are not dropped on src port
- Verify that some packets are dropped on dst ports, which means that Tx buffer is full
- Send 10000 packets for lossless priorities from non-server port (src) to all server ports (dst)
- Verify that some packets are dropped on src port, which means that Rx queue is full
- Verify that some packets are dropped on dst ports, which means that Tx buffer is full

- Teardown:
  - Stop ARP responder
