# Ip Interface Loopback Action Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| rif_loopback_action_hld | [https://github.com/sonic-net/SONiC/doc/ip-interface/loopback-action/ip-interface-loopback-action-design.md]|


## Overview
RIF loopback action is a feature which allows user to change the way router handles routed packets with egress port equal to ingress port.

1. When RIF loopback action is configured to drop, routed packet ingress port and egress port can not be equal. In other words, if routed packet entered the router from a port and destined to egress from the same one, it will be dropped.
2. When RIF loopback action is configured to forward, routed packet ingress port and egress port can be equal.
3. Default loopback action in SAI is forward. SONiC will rely on SAI default (the motivation here is not to change the behaviour if other SAI vendors have different default).


## Requirements

#### The Rif loopback action is support on following ip interface:
1. Ethernet interface
2. Vlan interface
3. PortChannel interface
4. Ethernet sub-interface
5. PortChannel sub-interface

#### This feature will support the following commands:

1. config: set RIF loopback action
2. show: display loopback action of all RIFs

#### This feature will provide error handling for the next situations:

1. Invalid action
2. Invalid interface
3. Non ip interface

### Scope

The test is to verify the loopback action can be configured, and the loopback traffic can be forwarded/droppped as expect according to the action configured on the ip interface.   

### Scale / Performance

No scale test related

### Related **DUT** CLI commands

#### Config
The following command can be used to configure loopback action on L3 interface:
```
config interface ip loopback-action <interface-name> <action>
```
action options: "drop", "forward"

Examples:
```
config interface ip loopback-action Ethernet248 drop
config interface ip loopback-action Vlan100 forward
config interface ip loopback-action PortChannel1 drop
config interface ip loopback-action Ethernet0.10 drop
config interface ip loopback-action Po10.10 drop
```

#### Show
The following command can be used to show loopback action:
```
show ip interfaces loopback-action 
```
Example:
```
show ip interfaces loopback-action
Interface     Action      
------------  ----------  
Ethernet248   drop     
Vlan100       forward     
PortChannel1  drop
Ethernet0.10  drop
Po10.10       drop
```
### Related DUT configuration files

```
"INTERFACE": {
    "Ethernet248": {
        "loopback_action": "drop"
    },
},
"PORTCHANNEL_INTERFACE": {
    "PortChannel1": {
        "loopback_action": "drop"
    },
},
"VLAN_INTERFACE": {
    "Vlan100": {
        "loopback_action": "drop"
    },
},
"VLAN_SUB_INTERFACE": {
    "Ethernet0.10": {
        "admin_status": "up",
        "loopback_action": "drop",
        "vlan": "10"
    },
    "Po10.10": {
        "loopback_action": "drop",
        "admin_status": "up",
        "vlan": "10"
    }
}
```
### Supported topology
The test will be supported on any topology


## Test cases

### Test cases #1 - Verify the loopback action can be configured and worked as expect,the interface type will cover all the 5 types of ip interface.
1. Verify the default action with sending traffic: 
   - Verify the traffic will be forwarded as expected.
   - The RIF TX_ERR counter will not increase as expected
2. Configure the loopback action to drop on the interface with cli command
3. Verify the the loopback action is configured correctly with show cli command.
4. Send traffic to do the validation: 
   - Verify the traffic will be dropped as expected.
   - The RIF TX_ERR counter will increase as expected
5. Change it back to forward
6. Verify the the loopback action is configured correctly with show cli command.
7. Send traffic to do the validation
   - Verify the traffic will be forwarded as expected.
   - The RIF TX_ERR counter will not increase.
   
### Test cases #2 - Disable/Enable the interface and check if the loopback action still work, the interface type will cover all types of ip interface except vlan interface.
1. Configure the loopback action on the interface, some to drop, some to forward.
2. Disable the interfaces
3. Enable the interfaces back
4. Verify the loopback action is not changed with show cli command.
5. Send traffic to do the validation: 
   - Verify the traffic will be dropped/forwarded as expected.
   - The RIF TX_ERR counter will increase on the interface that the loopback action is configured to drop
   - The RIF TX_ERR counter will not increase on the interface that the loopback action is configured to forward

### Test cases #3 - Verify loopback action is saved after reboot(config reload, reboot, fast-reboot, warm-reboot), the interface type will cover all the 5 types of ip interface.
1. Configure the loopback action on the interface, some to drop, some to forward.
2. Config save -y
3. Do reboot(config reload/reboot/fast-reboot/warm-reboot)
4. Verify the loopback action is saved correctly with show cli command.
5. Send traffic to do the validation: 
   - Verify the traffic will be dropped as expected.
   - The RIF TX_ERR counter will increase on the interface that the loopback action is configured to drop
   - The RIF TX_ERR counter will not increase on the interface that the loopback action is configured to forward

