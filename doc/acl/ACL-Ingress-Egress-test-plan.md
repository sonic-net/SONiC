# ACL Ingress & Egress Test Plan

- [ACL Ingress & Egress Test Plan](#acl-ingress--egress-test-plan)
  - [The existing test plan and scripts](#the-existing-test-plan-and-scripts)
    - [Problems of existing ingress ACL testing](#problems-of-existing-ingress-acl-testing)
  - [Ingress & egress ACL testing strategy](#ingress--egress-acl-testing-strategy)
    - [The testing strategy](#the-testing-strategy)
    - [Work need to be done](#work-need-to-be-done)
    - [ACL tables and ACL rules](#acl-tables-and-acl-rules)
      - [The DATAINGRESS ACL table and its ruls](#the-dataingress-acl-table-and-its-ruls)
      - [The DATAEGRESS ACL table and its ruls](#the-dataegress-acl-table-and-its-ruls)
      - [Counters of ACL rules](#counters-of-acl-rules)
    - [ACL tests](#acl-tests)

## The existing test plan and scripts

The existing test plan: https://github.com/sonic-net/SONiC/wiki/ACL-test-plan

The existing acl test scripts covered ingress ACL on SONiC switch. Supported topo: t1, t1-lag, t1-64-lag

Below are the covered ACL rules:
```
$ acl-loader show rule
Table    Rule          Priority    Action    Match
-------  ------------  ----------  --------  ----------------------------
DATAACL  RULE_1        9999        FORWARD   SRC_IP: 10.0.0.2/32
DATAACL  RULE_2        9998        FORWARD   DST_IP: 192.168.0.16/32
DATAACL  RULE_3        9997        FORWARD   DST_IP: 172.16.2.0/32
DATAACL  RULE_4        9996        FORWARD   L4_SRC_PORT: 4661
DATAACL  RULE_5        9995        FORWARD   IP_PROTOCOL: 126
DATAACL  RULE_6        9994        FORWARD   TCP_FLAGS: 0x12/0x12
DATAACL  RULE_7        9993        DROP      SRC_IP: 10.0.0.3/32
DATAACL  RULE_8        9992        FORWARD   SRC_IP: 10.0.0.3/32
DATAACL  RULE_9        9991        FORWARD   L4_DST_PORT: 4661
DATAACL  RULE_10       9990        FORWARD   L4_SRC_PORT_RANGE: 4656-4671
DATAACL  RULE_11       9989        FORWARD   L4_DST_PORT_RANGE: 4640-4687
DATAACL  RULE_12       9988        FORWARD   IP_PROTOCOL: 1
                                             SRC_IP: 10.0.0.2/32
DATAACL  RULE_13       9987        FORWARD   IP_PROTOCOL: 17
                                             SRC_IP: 10.0.0.2/32
DATAACL  DEFAULT_RULE  1           DROP      ETHER_TYPE: 2048
```

The existing acl testing script inserts a set of rules into the DATAACL table of type "l3". A default rule is always added by acl-loader.
Any packets that do not match higher priority rules will hit the default rule and be dropped.
To verify that the ingress ACL rules are working, the PTF script send various packets matching higher priority rules. These packets should pass through the rules and be forwarded by switch. The PTF script then can verify appearance of these packets on corresponding egress ports.

### Problems of existing ingress ACL testing

* Most of the rules covered FORWARD action. Coverage of DROP action is not enough.
* "aclshow -a" can show counters of ACL rules. Checking counters is not covered.
* The packets intended for matching RULE_12 and RULE_13 are matched by RULE_1 firstly. RULE_12 and RULE_13 are never hit.
* Logging of the PTF script needs improvement. If a case failed, failed case is not in ansible log. Need to check PTF log to find out exactly which case failed.

## Ingress & egress ACL testing strategy

### The testing strategy

In a summary, to cover egress ACL testing, we plan to:
* Improve the existing ingress ACL scripts to address the current problems
* Extend the scripts to cover egress ACL testing

To test egress ACL, we need another ACL table with `stage` property set to `egress`. When the `stage` property is not set, it takes default value `ingress`. The builtin DATAACL table could be reused. But for simplicity, two ACL tables will be added, one for ingress, one for egress:

ACL Table | Type | Bind to | Stage | Description
----------|------|---------|-------|-------------
DATAINGRESS | L3 | All ports | Ingress | For testing ingress ACL
DATAEGRESS | L3 | All ports | Egress | For testing egress ACL

When t1 topology is used, the tables can bind to all ports. When t1-lag and t1-64-lag topologies are used, the ports connected to spine routers are all in portchannel. For these ports, the added ACL tables should not directly bind to them. Instead, the portchannels should be binded to the ACL tables.

A same set of improved ACL rules can be used for both ingress and egress ACL testing. While testing ingress ACL, it is always possible to hit the rules. While testing egress ACL, destination IP address of the injected packet must be routable. Otherwise, the injected packet would never get a chance to hit the egress rule.

For completness, both packet flow directions will be covered:
* TOR ports -> SPINE ports: Inject packet into tor ports. Set destination IP address to BGP routes learnt on spine ports. Check the packet on spine ports.
* SPINE ports -> TOR ports: Inject packet into spine ports. Set destination IP address to BGP routes learnt on tor ports. Check the packet on tor ports.

### Work need to be done

Work need to be done based on this strategy and existing scripts:
* Update the existing acltb.yml script:
  * Backup config_db. 
  * Create ACL tables and load ACL rules for testing.
  * Run the PTF scritp.
  * Restore configuration after testing.
* Update the PTF script
  * Add more test cases for the improved set of ACL rules.
  * Improve logging of the PTF script. Output more detailed information of failed case in ansible log.
* Improve the ACL rules
  * The same set of existing ACL rules could be reused. Load the same set of rules to different tables during testing.
  * Improve the existing ACL rules to address issue that RULE_12 and RULE_13 are not hit.
  * Extend the existing ACL rules to cover more DROP action. The PTF script should be extended accordingly too.
  * Change source IP to addresses that are not used by other devices in current topologies
  * Add two rules to always allow BGP packets. Othewise, BGP routes will be lost.
* Add a new ansible module for gathering ACL counters in DUT switch.
* Check counters of ACL rules after each PTF script execution.

### ACL tables and ACL rules
The builtin ACL tables DATAACL will not be used. Will add 2 new L3 ACL tables for testing:

ACL Table | Type | Bind to | Stage | Description
----------|------|---------|-------|-------------
DATAINGRESS | L3 | All ports | Ingress | For testing ingress ACL
DATAEGRESS | L3 | All ports | Egress | For testing egress ACL

The ACL rules will be improved too:
* Add a new set of rules RULE_14 to RULE_26 for testing DROP action.
* RULE_12 and RULE_13 should use source IP address different with RULE_1, for example 20.0.0.4/32. Otherwise packets with source IP 20.0.0.2/32 would always match RULE_1 and never hit RULE_12 and RULE_13. The PTF script testing case 10 and 11 need to use this new source IP address for the injected packets.
* RULE_25 and RULE_26 should use source IP address different with: RULE_1, RULE_12, RULE_13 and RULE_14. Otherwise, RULE_25 and RULE_26 will never be hit.
* RULE_27 and RULE_28 are added to always alow BGP traffic. Otherwise, BGP traffic would be blocked by the DEFAULT_RULE.

The ACL rules should not be all loaded at the same time.

Example of updated ACL tables and rules:

#### The DATAINGRESS ACL table and its ruls
The ACL rules for DATAINGRESS ACL table should only be loaded when testing ingress ACL.
```
$ acl-loader show rule
Table        Rule          Priority    Action    Match
-----------  ------------  ----------  --------  ----------------------------
DATAINGRESS  RULE_1        9999        FORWARD   SRC_IP: 20.0.0.2/32
DATAINGRESS  RULE_2        9998        FORWARD   DST_IP: 192.168.0.16/32
DATAINGRESS  RULE_3        9997        FORWARD   DST_IP: 172.16.2.0/32
DATAINGRESS  RULE_4        9996        FORWARD   L4_SRC_PORT: 4621
DATAINGRESS  RULE_5        9995        FORWARD   IP_PROTOCOL: 126
DATAINGRESS  RULE_6        9994        FORWARD   TCP_FLAGS: 0x1b/0x1b
DATAINGRESS  RULE_7        9993        DROP      SRC_IP: 20.0.0.3/32
DATAINGRESS  RULE_8        9992        FORWARD   SRC_IP: 20.0.0.3/32
DATAINGRESS  RULE_9        9991        FORWARD   L4_DST_PORT: 4631
DATAINGRESS  RULE_10       9990        FORWARD   L4_SRC_PORT_RANGE: 4656-4671
DATAINGRESS  RULE_11       9989        FORWARD   L4_DST_PORT_RANGE: 4640-4687
DATAINGRESS  RULE_12       9988        FORWARD   IP_PROTOCOL: 1
                                                 SRC_IP: 20.0.0.4/32
DATAINGRESS  RULE_13       9987        FORWARD   IP_PROTOCOL: 17
                                                 SRC_IP: 20.0.0.4/32
DATAINGRESS  RULE_14       9986        DROP      SRC_IP: 20.0.0.6/32
DATAINGRESS  RULE_15       9985        DROP      DST_IP: 192.168.0.17/32
DATAINGRESS  RULE_16       9984        DROP      DST_IP: 172.16.3.0/32
DATAINGRESS  RULE_17       9983        DROP      L4_SRC_PORT: 4721
DATAINGRESS  RULE_18       9982        DROP      IP_PROTOCOL: 127
DATAINGRESS  RULE_19       9981        DROP      TCP_FLAGS: 0x24/0x24
DATAINGRESS  RULE_20       9980        FORWARD   SRC_IP: 20.0.0.7/32
DATAINGRESS  RULE_21       9979        DROP      SRC_IP: 20.0.0.7/32
DATAINGRESS  RULE_22       9978        DROP      L4_DST_PORT: 4731
DATAINGRESS  RULE_23       9977        DROP      L4_SRC_PORT_RANGE: 4756-4771
DATAINGRESS  RULE_24       9976        DROP      L4_DST_PORT_RANGE: 4740-4787
DATAINGRESS  RULE_25       9975        DROP      IP_PROTOCOL: 1
                                                 SRC_IP: 20.0.0.8/32
DATAINGRESS  RULE_26       9974        DROP      IP_PROTOCOL: 17
                                                 SRC_IP: 20.0.0.8/32
DATAINGRESS  RULE_27       9973        FORWARD   L4_SRC_PORT: 179
DATAINGRESS  RULE_28       9972        FORWARD   L4_DST_PORT: 179
DATAINGRESS  DEFAULT_RULE  1           DROP      ETHER_TYPE: 2048
```

#### The DATAEGRESS ACL table and its ruls
The ACL rules for DATAEGRESS ACL table should only be loaded when testing egress ACL.
```
$ acl-loader show rule
Table        Rule          Priority    Action    Match
----------  ------------  ----------  --------  ----------------------------
DATAEGRESS  RULE_1        9999        FORWARD   SRC_IP: 20.0.0.2/32
DATAEGRESS  RULE_2        9998        FORWARD   DST_IP: 192.168.0.16/32
DATAEGRESS  RULE_3        9997        FORWARD   DST_IP: 172.16.2.0/32
DATAEGRESS  RULE_4        9996        FORWARD   L4_SRC_PORT: 4621
DATAEGRESS  RULE_5        9995        FORWARD   IP_PROTOCOL: 126
DATAEGRESS  RULE_6        9994        FORWARD   TCP_FLAGS: 0x1b/0x1b
DATAEGRESS  RULE_7        9993        DROP      SRC_IP: 20.0.0.3/32
DATAEGRESS  RULE_8        9992        FORWARD   SRC_IP: 20.0.0.3/32
DATAEGRESS  RULE_9        9991        FORWARD   L4_DST_PORT: 4631
DATAEGRESS  RULE_10       9990        FORWARD   L4_SRC_PORT_RANGE: 4656-4671
DATAEGRESS  RULE_11       9989        FORWARD   L4_DST_PORT_RANGE: 4640-4687
DATAEGRESS  RULE_12       9988        FORWARD   IP_PROTOCOL: 1
                                                 SRC_IP: 20.0.0.4/32
DATAEGRESS  RULE_13       9987        FORWARD   IP_PROTOCOL: 17
                                                 SRC_IP: 20.0.0.4/32
DATAEGRESS  RULE_14       9986        DROP      SRC_IP: 20.0.0.6/32
DATAEGRESS  RULE_15       9985        DROP      DST_IP: 192.168.0.17/32
DATAEGRESS  RULE_16       9984        DROP      DST_IP: 172.16.3.0/32
DATAEGRESS  RULE_17       9983        DROP      L4_SRC_PORT: 4721
DATAEGRESS  RULE_18       9982        DROP      IP_PROTOCOL: 127
DATAEGRESS  RULE_19       9981        DROP      TCP_FLAGS: 0x24/0x24
DATAEGRESS  RULE_20       9980        FORWARD   SRC_IP: 20.0.0.7/32
DATAEGRESS  RULE_21       9979        DROP      SRC_IP: 20.0.0.7/32
DATAEGRESS  RULE_22       9978        DROP      L4_DST_PORT: 4731
DATAEGRESS  RULE_23       9977        DROP      L4_SRC_PORT_RANGE: 4756-4771
DATAEGRESS  RULE_24       9976        DROP      L4_DST_PORT_RANGE: 4740-4787
DATAEGRESS  RULE_25       9975        DROP      IP_PROTOCOL: 1
                                                 SRC_IP: 20.0.0.8/32
DATAEGRESS  RULE_26       9974        DROP      IP_PROTOCOL: 17
                                                 SRC_IP: 20.0.0.8/32
DATAEGRESS  RULE_27       9973        FORWARD   L4_SRC_PORT: 179
DATAEGRESS  RULE_28       9972        FORWARD   L4_DST_PORT: 179
DATAEGRESS  DEFAULT_RULE  1           DROP      ETHER_TYPE: 2048
```

#### Counters of ACL rules
Use the `aclshow` command can check counters of ACL rules.
```
$ aclshow -a
RULE NAME     TABLE NAME    TYPE      PRIO  ACTION      PACKETS COUNT    BYTES COUNT
------------  ------------  ------  ------  --------  ---------------  -------------
RULE_1        DATAINGRESS   L3        9999  FORWARD                 0              0
RULE_2        DATAINGRESS   L3        9998  FORWARD                 0              0
RULE_3        DATAINGRESS   L3        9997  FORWARD                 0              0
RULE_4        DATAINGRESS   L3        9996  FORWARD                 0              0
RULE_5        DATAINGRESS   L3        9995  FORWARD                 0              0
RULE_6        DATAINGRESS   L3        9994  FORWARD                 0              0
RULE_7        DATAINGRESS   L3        9993  DROP                    0              0
RULE_8        DATAINGRESS   L3        9992  FORWARD                 0              0
RULE_9        DATAINGRESS   L3        9991  FORWARD                 0              0
RULE_10       DATAINGRESS   L3        9990  FORWARD                 0              0
RULE_11       DATAINGRESS   L3        9989  FORWARD                 0              0
RULE_12       DATAINGRESS   L3        9988  FORWARD                 0              0
RULE_13       DATAINGRESS   L3        9987  FORWARD                 0              0
RULE_14       DATAINGRESS   L3        9986  DROP                    0              0
RULE_15       DATAINGRESS   L3        9985  DROP                    0              0
RULE_16       DATAINGRESS   L3        9984  DROP                    0              0
RULE_17       DATAINGRESS   L3        9983  DROP                    0              0
RULE_18       DATAINGRESS   L3        9982  DROP                    0              0
RULE_19       DATAINGRESS   L3        9981  DROP                    0              0
RULE_20       DATAINGRESS   L3        9980  FORWARD                 0              0
RULE_21       DATAINGRESS   L3        9979  DROP                    0              0
RULE_22       DATAINGRESS   L3        9978  DROP                    0              0
RULE_23       DATAINGRESS   L3        9977  DROP                    0              0
RULE_24       DATAINGRESS   L3        9976  DROP                    0              0
RULE_25       DATAINGRESS   L3        9975  DROP                    0              0
RULE_26       DATAINGRESS   L3        9974  DROP                    0              0
RULE_27       DATAINGRESS   L3        9973  FORWARD               256          19584
RULE_28       DATAINGRESS   L3        9972  FORWARD               283          28219
DEFAULT_RULE  DATAINGRESS   L3           1  DROP                    6            420
```

### ACL tests

Overall steps of automation script:
* Backup config_db. 
* Create ACL tables before testing.
* Load ACL rules to DATAINGRESS for ingress ACL testing.
* Run the PTF script to cover different packet injection directions.
* Test other scenarios and run the PTF script:
  * Toggle all the switch ports.
  * Use incremental update to load the ACL rules.
  * Save config and reboot.
* Remove the ACL from DATAINGRESS.
* Load ACL rules to DATAEGRESS for egress ACL testing.
* Run the PTF script to cover different packet injection directions.
* Test other scenarios and run the PTF script:
  * Toggle all the switch ports.
  * Use incremental update to load the ACL rules.
  * Save config and reboot.
* Remove the ACL from DATAEGRESS.
* Restore configuration after testing.

For each packet direction of ingress and egress testing, all of these tests must be executed in the PTF script:

* Test 0 - unmatched packet - dropped

* Test 1 - source IP match - forwarded
* Test 2 - destination IP match - forwarded
* Test 3 - L4 source port match - forwarded
* Test 4 - L4 destination port match - forwarded
* Test 5 - IP protocol match - forwarded
* Test 6 - TCP flags match - forwarded
* Test 7 - source port range match - forwarded
* Test 8 - destination port range match - forwarded
* Test 9 - rules priority - dropped
* Test 10 - ICMP source IP match - forwarded
* Test 11 - UDP source IP match - forwarded

* Test 12 - source IP match - dropped
* Test 13 - destination IP match - dropped
* Test 14 - L4 source port match - dropped
* Test 15 - L4 destination port match - dropped
* Test 16 - IP protocol match - dropped
* Test 17 - TCP flags match - dropped
* Test 18 - source port range match - dropped
* Test 19 - destination port range match - dropped
* Test 20 - rules priority - forwarded
* Test 21 - ICMP source IP match - dropped
* Test 22 - UDP source IP match - dropped
