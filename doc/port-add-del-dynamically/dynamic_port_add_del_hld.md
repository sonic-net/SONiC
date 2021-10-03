# Delete or remove ports dynamically


# Table of Contents
  * [Revision](#revision)            
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)                        
  * [Initialization stage](#init-stage)
  * [Post init stage](#post-init)
  
  

#### Revision
| Rev |  Date   |       Author       | Change Description |
|:---:|:-------:|:------------------:|:------------------:|
| 0.1 | 2021-09 |    Tomer Israel    | Initial Version    |


## Motivation
The feature is to support adding or removing ports from the system dynamically after init stage.
The system can start with all the ports on config db or only several ports from the full ports or without any ports on config db (zero ports system).
The ports will be added or removed through the port table on config db.
Before removing a port the user is responsible to remove all dependencies of this port before removing it.


# About this Manual
This document provides general information about ports creation or removal in SONiC. The creation of ports on the init stage and creating or removing ports after init stage.
# Scope                                                                                  
This document describes the high level design of orchagent and the impact of creating/removing ports dynamically on other services. The design describes the current implementaion and suggestion to changes that needs to be implemented in order to fully support the dynamic create/remove of ports.


## Design


<a name="init-stage"></a>

# Initialization stage 

 
 ![Init stage](images/init_stage_diagram.png)
 
- **Portsyncd** read port config db info and push it to App db and will set PortConfigDone on App db when finished.
- **Portsorch** (orchagent) for every port added to the APP DB … will create port through SAI call and create also host interface for each time port is added to port APP table.
- **Portsyncd** will receive netlink notification for each host interface that was created, and update an entry on state db
- When all host interfaces are created **Portsyncd** is setting PortInitDone.


### App DB flags:
PortConfigDone – finished to configure ports on init
PortInitDone – all host interfaces were created 

Some services are waiting for these flags before they continue to run:
Orchagent is waiting for PortConfigDone before continuing to create the ports on SAI.
Xcvrd, buffermgrd, natmgr, natsync – waiting for PortInitDone

## Init types:
The Dynamic port add/remove configuration will be supported for both types of init types:<br />
•   Start the system with full ports on config db <br />
•   Start the system without some of the ports on config db<br />
•   Start the system with zero ports on config db<br />

**Note:** This is a new type of init that was never tested and will be supported.<br />
The zero-port system is a special case of this feature. <br />
Few PRs were already added in order to support zero ports init.<br />

after init stage we can add/remove ports dynamically through redis call to add/remove entry to/from port table on config db ("PORT")

## Init with zero ports:
Starting with zero ports requires new SKU for zero ports with these changes:<br />
**Port_confg.ini** – without entries<br />
**Hwsku.json** – without interfaces<br />
**Platform.json** – without interfaces<br />
**Sai xml** file – needs to be without port entries. <br />
Currently SAI is not supporting adding new ports that wasn’t exist on the sai xml file, so our tests will be with full ports on sai xml file and adding/removing ports that were exist on the sai xml.<br />

On this zero ports SKU the sonic-cfggen will generate config_db.json file without any ports.<br />
 
<a name="post-init"></a>

# Post init stage - dynamically

#### Add port:

 ![Add port](images/add_port_diagram.png)

1.  A process or a user can add port entry to the port table on Config DB. For example, the line card manager will add port entry to the port table.
2.  On portsyncd - Port set event is received from Config DB.
3.  Portsyncd is adding the new port info to App DB
4.  On portsorch (orchagent) - Port set event is received from App DB.
5.  Portsorch is creating the port on SAI.
6.  SDK is creating the port and the host interfaces.
7.  Host interface is created and Netlink event received on portsyncd.
8.  Portsyncd is adding a new port entry on state db.
9.  Events from ASIC DB received on portsorch when operstate are changing (up or down).
10. Portsorch are updating the operstate on App DB



#### Del port:

Del Port – Remove port element from config DB
Note: before removing a port, the port needs to be without any dependencies (ACL, VLAN, LAG, buffer pg).
For example: we need to remove the buffer pg that configured to a port and then remove the port.

 ![Remove port](images/remove_port_diagram.png)

1.  Before we remove a port, we need to remove all dependencies of these ports (vlan, acl, buffer…)
2.  A process or a user can remove port entry from the port table on Config DB. For example, line card manager will remove port entry.
3.  On portmgrd we receive delete event from Config DB.
4.  Portmgrd will remove this entry on App DB.
5.  Portsorch will receive remove entry event from the App DB.
6.  Portsorch will delete the port and the host interface on SAI.
7.  SAI will remove this port on SDK
8.  Host interface will be removed and netlink event will be received on portsyncd.
9.  Portsyncd will remove the port entry from state db


## Modules that “listen” to changes on config port table & App port table 

#### SWSS - Portsyncd:
•   ADD PORT - Receive new port from port config table, add the port info to APP DB (update speed, interface_type, autoneg, adv_speeds, adv_interface_types).<br />
when host interface was created add this port entry to state db<br />
•   DEL PORT – portmgrd is removing this entry from app db.<br />
when host interface was removed remove this port entry from state db


#### SWSS - Portsorch:
•   ADD PORT - Receive new port from port APP table -> create port on SAI -> create host interface -> add Flex counters<br />
Receive notification from ASIC DB when oper_state is changing, update the port oper_state on APP db.
•   DEL PORT - Receive del port from port APP table -> remove flex counters -> del port on SAI -> del host interface<br />

Currently the orchagent is adding/removing these flex counters:
-   PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP<br />
-   PORT_STAT_COUNTER_FLEX_COUNTER_GROUP<br />



Changes needs to be added:<br />
We need to add more port counters that will be add/removed dynamically whenever port is created or removed:
-   Queue port counters (queue & queue watermark counters)
-   PG counters
-   Debug counters: port ingress drops  (DEBUG_COUNTER config table)
-   Debug counters: port egress drops 
-   Pfc watchdog counters

In the current implementation these counters were created for all ports only after init stage is done.

 


#### PortMgrd:
- ADD Port: Set (admin_status, mtu, learn_mode, tpid) from config db to App db 
- Del port: Receive del port operation from port config table, remove this port from APP DB.

#### Sflowmgr:
Add port: Event from config db - Update the speed to sflow internal db.
Del port: Delete event from config db - remove the speed from sflow internal db.

#### Teammgrd:
Listen to events from state db, when entry is added -> add the port to lag

#### Macsecmgr:
Listen to events on cfg port table – the service will enable or disable macsec if macsec was configured on the port cfg table (using the macsec field)

#### PMON - Xcvrd:
Listen to events on cfg port table and update transeiver information <br />
https://github.com/Azure/sonic-buildimage/pull/8422 <br />
https://github.com/Azure/sonic-platform-daemons/pull/212

#### snampagent:
•   Add/remove port has no special treatment.
each time the snmpagent needs information from ports (oper_state, mtu, speed..) it reads from APP port table. Will be triggered on mib requests.

 
## Buffermgrd:

##### Add port:  
- If a port is added without a buffer configuration the buffer configuration the SDK will “decide” the default buffer values for this port.
- The user can add the port on admin state down -> later add the buffer configuration (static or dynamic) -> enable this port.
For example, in the line-card system case:
-   When line card is provisioned the line card manager is adding a port to config db, need to add the port with admin state “down”.
-   Line card manager will add the buffer configuration for this port through a default buffer cfg template.
-   Line cart manager will enable the port.

•   Pg_profile_lookup file has values that will be used for static buffer configuration.
for each port speed and cable length we have buffer size value, xon and xoff value <br />
For example:


|speed cable | cable | size  |  xon  |  xoff |  threshold |
|:----------:|:-----:|:-----:|:-----:|:-----:|:----------:|
|  10000     | 5m    | 49152 | 19456 | 29696 |      0     |
|  25000     | 5m    | 49152 | 19456 | 29696 |      0     |
|  40000     | 5m    | 49152 | 19456 | 29696 |      0     |
|  50000     | 5m    | 49152 | 19456 | 29696 |      0     |

On the line-card system we will use different types of line cards (maybe with different gearboxes), the values on the pg_profile_lookup will be used for all the types.<br />
we may need to consider using pg_profile_lookup.ini for each line card type.<br />
•   When port is added to the config db – the speed and the admin state is saved on internal db<br />
•   After port was added the user can add buffer configuration to this port (dynamic or static configuration) and only then the buffermgr will set the buffer configuration on App table<br />

•   We have rare situation of race condition in the add port flow:

 ![possible buffermgr race condition](images/buffermgr_possible_race.png)


 
 

##### Del port:
•   Before removing a port all buffer configuration needs to be removed

We have also possible way for race condition:

 ![possible buffermgr delete port race condition](images/buffermgr_possible_delete_race.png)

•   If the portsyncd is “quicker” than the buffermgr the orchagent will try to remove the port from SAI before the buffer configuration was removed.
•   Need to test this scenario in order to check if this race condition is reproducing or it’s rare scenario
•   Solution for this: 
Need to add to orchagent the ability to add the buffer configuration of a port and increase a reference counter for each port, in the same way ACL cfg on port is working. We already have infrastructure for this just need to add the buffer cfg to use it. If a port has with buffer cfg on – this port will not be removed.






#### LLDP – lldpmgrd – implementation today:
•   Add port: receive port entry set on port config db -> check if oper state is up or wait until oper state up event is received from app db  add lldp port entry  with lldpcli command
•   Del port: when host interface is removed from system lldp configuration is removed also.
 




 ![Add port - LLDP- current implementation](images/lldp_before.png)





Suggested change:
-   We will use the state DB to trigger the lldpmgr to add a port<br />
-   When the state db entry is added we know for sure that host interface was created properly and the lldpcli command will be executed properly. <br />
when host interface is not ready yet the lldpcli will be failed.<br />
-   The lldpcli is a tool that we can use in order to add ports to lldp.<br />

 ![add port - LLDP- suggested change](images/lldp_after.png)
 
 
### VS test

1.  Basic test (init with full ports): <br />
    - Start the system with full ports on system <br />
    - Remove all ports <br />
    - Verify ports were removed properly – show interfaces, sai/sdk dump <br />
    - Add all ports back to the system <br />
    - Verify ports were added properly – show interfaces, sai/sdk dump, lldp, snmp walk <br />
    - Run traffic and verify basic functionality of ports <br />
2.  Basic test (init with zero ports): <br />
    - Start the system with zero ports on system <br />
    - Verify ports not exists– show interfaces, sai/sdk dump <br />
    - Add all ports <br />
    - Verify ports were added properly – show interfaces, sai/sdk dump, lldp, snmp walk <br />
    - Run traffic and verify basic functionality of ports <br />
    - Remove all ports <br />
    - Verify ports were removed properly – show interfaces, sai/sdk dump <br />
    - Add all ports to the system again <br />
    - Verify ports were added properly – show interfaces, sai/sdk dump, lldp, snmp walk <br />
    - Run traffic and verify basic functionality of ports <br />
3.  Error flow - Add more than the max number of ports <br />
4.  Error flow - Add port with wrong value of lanes <br />
5.  Remove port and add a port in a loop <br />
6.  Start the system with zero ports
     - Add ports<br />
     - Add acl configuration to several ports from the system <br />
     - Add vlan configuration to several ports from the system <br />
     - Add lag configuration to several ports from the system <br />
     - Add buffer configuration to several ports from the system <br />
     - Verify all configuration added properly <br />


### system level testing
TBD

