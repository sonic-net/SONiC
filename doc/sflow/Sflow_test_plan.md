# SFlow Test Plan

## Overview

The purpose is to test the functionality of the sFlow monitoring system on the SONIC switch DUT . The test assumes that the Sonic device has been preconfigured according to the t0 topology.

### Scope

The test is targeting a running SONIC system with fully functioning configuration. Rather, it is testing the functionality of sFlow on the SONIC system by verifying that sFlow is monitoring traffic flow data correctly.

## Test Structure

### Setup Configuration

The test will run on the t0 testbed:

![testbed-t0.png](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/img/testbed-t0.png?raw=true)

- 1 port from each port channel is used for traffic. Sflow is enabled on these 4 ports 
- 2 ports  from Vlan1000 are removed and used  to reach sflow collector in ptf docker .
- Traffic is sent from ptf docker with different packet sizes to the port channel interfaces  which are enabled with sflow .
- Collection is implemented using the sflowtool. Counter sampling output and flow sampling output are directed to a text file. The test script parses the text file and validates the data according to the polling/sampling rate configured and the interfaces enabled.
- Sflowtool to be installed in ptf docker to run these tests

### Test Cases

#### Test Case #1

##### Test objective

Verify that the SFLOW_COLLECTOR configuration additions and configuration deletions are processed by hsflowd.

| #    | Steps                                                        | Expected Result                                              |
| ---- | :----------------------------------------------------------- | ------------------------------------------------------------ |
| 1.   | 1. Enable sflow on  4 interfaces( port channel  intf), "  <br />2. Add a single collector with default port (6343), <br />3. Enable sFlow globally,<br />4. Send traffic | The configurations should be reflected in “show sflow” and "show sflow interface". <br />Traffic is sent to portchannel interfaces and Samples should be received by the collector . |
| 2.   | 1. Remove the  configured collector <br />2. Send Traffic <br />3. Add the collector back <br />4. Send traffic | The configurations should be reflected in “show sflow” and "show sflow interface". <br />When removed the collector should not receive and samples. Upon re adding the samples  should be received by the collector . |
| 3.   | 1. Add one more  collector with non default udp  port (6344) <br />2. Send traffic | The configurations should be reflected in “show sflow” and "show sflow interface". Samples should be received by both collectors. |
| 4.   | 1. Remove the second configured collector <br />2. Send traffic | Samples should continue to be received by the first collector with default  udp port |
| 5.   | 1. Add back the second collector.<br />2. Send Traffic       | Samples should continue to be received by both  the collectors. |
| 6    | Attempt to add 1 more collector for total of 3 .<br />config sflow collector add <*collector name*> <*ip*>". | An error message should be returned stating that only two collectors are supported. |
| 6.   | Remove the first configured collector with default port      | Samples should continue to be received only by the second collector with non default port . |

#### Test Case #2

##### Test objective

Verify that it is possible to change the counter polling interval using the SFLOW table

| #    | Steps                                                        | Expected Result                                              |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 1.   | 1. Enable Sflow on  4 interfaces<br /> 2. Enable sFlow globally.<br /> 3. Add two collectors. | Both collectors should be receiving samples at the default counter polling rate of 20 seconds. |
| 2.   | 1. Configure the counter polling interval to 0 seconds,      | Counter polling should be disabled and both collectors should not receive counter  samples. |
| 3.   | 1. Configure the counter polling interval to 60 seconds,     | Both collectors should be receiving samples at a counter polling rate of 60 seconds. |

#### Test Case #3

##### Test objective

Verify that it is possible to change the agent-id using the SFLOW table

| #    | Steps                                                        | Expected Result                                              |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 1.   | Add an agent-id with Loopback ip .<br />2. Send Traffic      | The configurations should be reflected in “show sflow” and both collectors should receive samples with the agent-id configured. |
| 2.   | 1. Remove the agent-id, "config sflow agent-id del".<br />2. Send Traffic | Both collectors should be receiving samples with the previously configured agent-id |
| 3.   | 1. Add an agent-id as eth0 ip.<br />2. Send Traffic          | Both collectors should receive samples with the agent-id configured. |

#### Test Case #4

##### Test objective

Verify that interfaces can be enabled/disabled using additions/deletions in SFLOW_SESSION table

| #    | Steps                                                        | Expected Result                                              |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 1.   | 1. Enable Sflow on  4 interfaces with 512 as sampling rate <br />2. Send traffic | The samples received by both collectors should reflect the changes. |
| 2.   | 1. Disable  Sflow on 2 interfaces,<br />2. Send traffic      | The samples received by both collectors should reflect the changes. |

#### Test Case #5

##### Test objective

Verify that it is possible to change the sampling rate per interface using SFLOW_SESSION interface sample rate field

| #    | Steps                                                        | Expected Result                                              |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 1.   | 1. Enable Sflow on  4 interfaces with 512 as sampling rate <br />2. Send traffic <br />3. Configure one interface sampling rate of 256, and configure another interface with 1024 as sampling rate. <br />4. Send Traffic | The configurations should be reflected in “show sflow” and "show sflow interface"<br />The samples received by both collectors should reflect the changes. |
| 2.   | 1. Enable sFlow globally,<br /> 2. Change the sampling rate for all the interfaces to 512 on all interfaces. | The samples received by both collectors should reflect the changes. |

#### Test Case #6

##### Test objective

Save the config and , restarting the unit should result in sFlow coming up with saved configuration.

| #    | Steps                                                        | Expected Result                                              |
| ---- | :----------------------------------------------------------- | ------------------------------------------------------------ |
| 1.   | 1. Enable 4 interfaces <br />2. Enable sFlow globally, "config sflow enable". <br />3. Set the polling interval to 80.<br />4. Save the configuration and then reboot.<br />5. Send traffic | The configurations should be reflected in “show sflow” and "show sflow interfaces".<br />The samples received by both collectors should reflect the changes.<br />counter samples should be received at 80 s interval |
| 2.   | 1. Disable sFlow globally<br /> 2. Save the configuration and then reboot.<br />3. Send Traffic | The configurations should be reflected in “show sflow” and "show sflow interfaces".<br /> Collectors should not receive samples |
| 3.   | 1. Enable sFlow, . <br />2. Add two collectors, <br />3. Enable 4 interfaces with 512 as  sampling rate  <br />4. Config save and do fast-reboot<br /> 5. Send Traffic | The configurations should be reflected in “show sflow” "show sflow interfaces". |

