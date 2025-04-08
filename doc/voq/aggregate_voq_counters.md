# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [Repositories that need to be changed](#repositories-that-need-to-be-changed)
   * [SAI API](#sai-api)
   * [Configuration and management](#configuration-and-management)
      * [CLI](#cli)
   * [Testing Requirements/Design](#testing-requirementsdesign)
      * [System Test cases](#system-test-cases)  

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











