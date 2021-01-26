# CPU queue stats

Network switches and routers typically have one port connected to the CPU (where the control software runs). This port is referenced as a CPU port on this document. Multiple egress queues on the CPU port helps differentiate traffic and avoid one kind of traffic overwhelming the other. Switch control software installs rules that identify control protocol packets and trap them to a particular queue on the CPU port. Please refer to COPP for more details.

The knowledge of various queue statistics help us identify the current health and reason for any packet drops. SONiC already has commands to examine port and queue statistics associated with front panel ports. The same is extended to examine the CPU queue stats. The watermark commands can also be extended to display the buffer utilization associated with these CPU queues (not included in this HLD).

For example the command *show queue counters <port-name>* which displays the below given statistics starts to display CPU queue statistics as well.

```
root@sonic:/home/admin# show queue counters Ethernet0
     Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
---------  -----  --------------  ---------------  -----------  ------------
Ethernet0    UC0               0                0            0             0
Ethernet0    UC1               0                0            0             0
Ethernet0    UC2               0                0            0             0
Ethernet0    UC3               0                0            0             0
Ethernet0    UC4               0                0            0             0
Ethernet0    UC5               0                0            0             0
Ethernet0    UC6               0                0            0             0
Ethernet0    UC7               0                0            0             0
Ethernet0    UC8               0                0            0             0
Ethernet0    UC9               0                0            0             0
Ethernet0   MC10               0                0            0             0
Ethernet0   MC11               0                0            0             0
Ethernet0   MC12               0                0            0             0
Ethernet0   MC13               0                0            0             0
Ethernet0   MC14               0                0            0             0
Ethernet0   MC15               0                0            0             0
Ethernet0   MC16               0                0            0             0
Ethernet0   MC17               0                0            0             0
Ethernet0   MC18               0                0            0             0
Ethernet0   MC19               0                0            0             0
```

On current SONiC code base, the command returns *Port doesn't exist! CPU* as the CPU port is not understood by SONiC.

```
root@sonic:/home/admin# show queue counters CPU
Port doesn't exist! CPU
```

The proposed changes make the command return the actual supported CPU queues and its stats.

```
root@L15:/home/admin# show queue counters CPU
  Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
------  -----  --------------  ---------------  -----------  ------------
   CPU    MC0               0                0            0             0
   CPU    MC1               0                0            0             0
   CPU    MC2               0                0            0             0
   CPU    MC3               0                0            0             0
   CPU    MC4               0                0            0             0
   CPU    MC5               0                0            0             0
   CPU    MC6               0                0            0             0
   CPU    MC7               0                0            0             0
   CPU    MC8              14             1484            0             0
   CPU    MC9             175            63092            0             0
   CPU   MC10            1810           123080            0             0
   CPU   MC11               0                0            0             0
   CPU   MC12               0                0            0             0
   CPU   MC13               0                0            0             0
   CPU   MC14               0                0            0             0
   CPU   MC15               0                0            0             0
   CPU   MC16           75778          6470474            0             0
   CPU   MC17               0                0            0             0
   CPU   MC18           21837          6601410            0             0
   CPU   MC19               0                0            0             0
   CPU   MC20               0                0            0             0
   CPU   MC21               0                0            0             0
   CPU   MC22               0                0            0             0
   CPU   MC23              76            10032            0             0
   CPU   MC24               0                0            0             0
   CPU   MC25               0                0            0             0
   CPU   MC26               0                0            0             0
   CPU   MC27               0                0            0             0
   CPU   MC28               0                0            0             0
   CPU   MC29               0                0            0             0
   CPU   MC30               0                0            0             0
   CPU   MC31               0                0            0             0
   CPU   MC32               0                0            0             0
   CPU   MC33               0                0            0             0
   CPU   MC34               0                0            0             0
   CPU   MC35               0                0            0             0
   CPU   MC36               0                0            0             0
   CPU   MC37               0                0            0             0
   CPU   MC38               0                0            0             0
   CPU   MC39               0                0            0             0
   CPU   MC40               0                0            0             0
   CPU   MC41               0                0            0             0
   CPU   MC42               0                0            0             0
   CPU   MC43               0                0            0             0
   CPU   MC44               0                0            0             0
   CPU   MC45               0                0            0             0
   CPU   MC46               0                0            0             0
   CPU   MC47               0                0            0             0
```


The following COUNTER_DB maps include details for the CPU port and queues.   
COUNTERS_PORT_NAME_MAP   
COUNTERS_QUEUE_NAME_MAP   
COUNTERS_QUEUE_PORT_MAP   
COUNTERS_QUEUE_TYPE_MAP   
COUNTERS_QUEUE_INDEX_MAP   

Port and queue counters:   
COUNTERS:oid:<port-oid>   
COUNTERS:oid:<queue-oid>   



Minor code changes are made on *sonic-swss* repo to fetch the supported queues on CPU port and update the flex counters-db maps to include CPU port and its queues. Single line changes were made to *sonic-py-swsssdk*, *sonic-snmpagent* and *sonic-utilities* repos to ignore the newly added CPU port while iterating over the front panel ports. *sonic-sairedis* repo changes are made to enable cpu queues on vslib.
Syncd periodically fetches the CPU port stats, CPU queues stats along with other flex counter stats and updates the counters-DB.

SAI calls:   
get_port_attribute() API with attribute *SAI_PORT_ATTR_QOS_NUMBER_OF_QUEUES* to fetch the number of CPU queues supported by switch and *SAI_PORT_ATTR_QOS_QUEUE_LIST* to fetch the list of CPU queues.

List of PRs associated with this change:   
https://github.com/Azure/sonic-swss/pull/1544   
https://github.com/Azure/sonic-py-swsssdk/pull/98   
https://github.com/Azure/sonic-utilities/pull/1314   
https://github.com/Azure/sonic-snmpagent/pull/182   
https://github.com/Azure/sonic-sairedis/pull/732     

