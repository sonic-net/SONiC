# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [Repositories that need to be changed](#repositories-that-need-to-be-changed)
   * [Configuration and management](#configuration-and-management)
   * [Testing Requirements/Design](#testing-requirementsdesign)
      * [System Test cases](#system-test-cases)
   * [Limitations and future work](#limitations-and-future-work)  

### Revision 
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 19-Nov-2024 | Harsis Yadav, Pandurangan R S, Vivek Kumar Verma (Arista Networks)               | Initial public version            | 

### Overview 

In a [distributed VOQ architecture](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) corresponding to each output VOQ present on an ASIC, there are VOQs present on every ASIC in the system. Each ASIC has its own set of VOQ stats maintained in the FSI that have to be gathered independently and can be hard to visualize, providing a non-cohesive experience.

### Requirements

Provide aggregate VOQ counters in a distributed VOQ architecture.

### Architecture Design 

No new architecture changes are required to SONiC. 

### High-Level Design

On multi-asic systems (fixed system or linecard) the redis databases corresponding to each namespace are exposed on the docker network (non-loopback IP): https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-database/docker-database-init.sh. And when the IP to be bound to redis instance is not loopback IP we start redis server in unprotected mode: https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-database/supervisord.conf.j2#L38

We can leverage this property to expose redis instances that correspond to each ASIC over midplane IP addresses in addition to docker network in case of a chassis based system using the shell script docker-database.sh by simple redis-commands.

```
redis-cli -h $ip -p $port config set bind "$bound_ips $midplane_ip"
redis-cli -h $ip -p $port config rewrite
```

This gives us access to each ASIC's redis instance from the supervisor. Then queuestat script can access the counters data and provide the user an aggregated view of the VOQ counters.

#### sonic-buildimage changes
`docker_image_ctl.j2` needs to be modified to incorporate changes in order expose namespace redis instances on linecards over midplane network.

PR: https://github.com/sonic-net/sonic-buildimage/pull/20803

#### sonic-swss-common changes
A new API will be added to sonicv2connector.cpp which can take the db name and host IP as an argument and connect us to the redis instance. The existing [API](https://github.com/sonic-net/sonic-swss-common/blob/202411/common/sonicv2connector.cpp#L18-L30) needs the db_name and the host_ip and port (or unix_socket) is decoded using [database_config.json](https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-database/database_config.json.j2). This API is tailored for use cases when you want to connect to the namespace redis instances from the same device. Our use case involves connecting to a redis instances over midplane IP hence the new API is needed. 

PR: https://github.com/sonic-net/sonic-swss-common/pull/1003

#### sonic-py-swsssdk changes
Same rationale as sonic-swss-common applies here as well. Also we would like to maintain parity between dbconnector.py between swsscommon and swsssdk so that we can write a unit test for this feature or even otherwise.

PR: https://github.com/sonic-net/sonic-py-swsssdk/pull/147

#### sonic-utilities changes
We would leverage the existing `show queue counters --voq` on the supervisor to connect to various forwarding ASIC's database instances and do a summation of VOQ counters corresponding to each system port.

PR: https://github.com/sonic-net/sonic-utilities/pull/3617

#### Repositories that need to be changed
   * sonic-buildimage 
   * sonic-swss-common 
   * sonic-py-swsssdk
   * sonic-utilities 

### Configuration and management 
#### CLI

From linecard - cmp217-5 for asic0 (existing CLI)
```
admin@cmp217-5:~$ show queue counters -n asic0 "cmp217-5|asic1|Ethernet256" --voq
For namespace asic0:
                      Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
--------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp217-5|asic1|Ethernet256   VOQ0             123             6150            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ1              12              600            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ2            1000            50000            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ3             456            22800            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ4             211            10550            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ5              45             2250            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ6              24             1200            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ7               0                0            0             0                     0
```

From linecard - cmp217-5 for asic1 (existing CLI)
```
admin@cmp217-5:~$ show queue counters -n asic1 "cmp217-5|asic1|Ethernet256" --voq
For namespace asic1:
                      Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
--------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp217-5|asic1|Ethernet256   VOQ0            1111            55550            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ1              45             2250            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ2               9              450            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ3              91             4550            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ4              55             2750            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ5              88             4400            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ6              21             1050            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ7              48            14437            0             0                     0

```

From supervisor (same command extended for sup.)

```
admin@cmp217:~$ show queue counters "cmp217-5|asic1|Ethernet256" --voq
                      Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
--------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp217-5|asic1|Ethernet256   VOQ0            1234            61700            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ1              57             2850            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ2            1009            50450            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ3             547            27350            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ4             266            13300            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ5             133             6650            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ6              45             2250            0             0                     0
cmp217-5|asic1|Ethernet256   VOQ7              52            15809            0             0                     0

```

### Testing Requirements/Design  
#### System Test cases
Send traffic across different ASICs and ensure aggregate counters are correctly displayed.

### Limitations and future work
1. Currently we are not exposing redis instance over midplane IP for single ASIC linecards as redis runs in protected mode.
2. Clear functionality is not supported as of now for aggregate VOQ counters.
