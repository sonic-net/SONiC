<!-- omit in toc -->
# BGP Supress FIB Pending #

<!-- omit in toc -->
## Table of Content

- [1. Scope](#1-scope)
- [2. Definitions/Abbreviations](#2-definitionsabbreviations)
- [3. Overview](#3-overview)
- [4. Requirements](#4-requirements)
- [5. Architecture Design](#5-architecture-design)
- [6. High-Level Design](#6-high-level-design)
  - [6.1. BGP Docker container startup](#61-bgp-docker-container-startup)
  - [6.2. RouteOrch](#62-routeorch)
  - [6.3. FPMsyncd](#63-fpmsyncd)
  - [6.4. Response Channel Performance considerations](#64-response-channel-performance-considerations)
- [7. SAI API](#7-sai-api)
- [8. Configuration and management](#8-configuration-and-management)
  - [8.1. Config DB Enhancements](#81-config-db-enhancements)
    - [8.1.1. APP_STATE_LOGGING](#811-app_state_logging)
    - [8.1.2. DEVICE_METADATA](#812-device_metadata)
  - [8.2. Manifest (if the feature is an Application Extension)](#82-manifest-if-the-feature-is-an-application-extension)
  - [8.3. CLI/YANG model Enhancements](#83-cliyang-model-enhancements)
    - [8.3.1. APP_STATE_LOGGING](#831-app_state_logging)
    - [8.3.2.  DEVICE_METADATA](#832--device_metadata)
- [9. Warmboot and Fastboot Design Impact](#9-warmboot-and-fastboot-design-impact)
  - [9.1. Warm Reboot](#91-warm-reboot)
  - [9.2. Fast Reboot](#92-fast-reboot)
- [10. Restrictions/Limitations](#10-restrictionslimitations)
- [11. Testing Requirements/Design](#11-testing-requirementsdesign)
  - [11.1. Unit Test cases](#111-unit-test-cases)
  - [11.2. VS Test cases](#112-vs-test-cases)
  - [11.3. System Test cases](#113-system-test-cases)
- [12. Open/Action items - if any](#12-openaction-items---if-any)

<!-- omit in toc -->
### 1. Revision

| Revision | Date        | Author           | Change Description |
| -------- | ----------- | ---------------- | ------------------ |
| 1.0      | Sep 15 2022 | Stepan Blyshchak | Initial proposal   |

### 1. Scope

This document describes a feedback mechanism that allows BGP not to adveritise routes that haven't been programmed yet or failed to be programmed to ASIC.

### 2. Definitions/Abbreviations

| Definitions/Abbreviation | Description                  |
| ------------------------ | ---------------------------- |
| BGP                      | Border Gateway Protocol      |
| FRR                      | Free Range Routing           |
| SWSS                     | Switch state service         |
| SYNCD                    | ASIC syncrhonization service |
| FPM                      | Forwarding Plane Manager     |
| SAI                      | Switch Abstraction Interface |
| OID                      | Object Identifier            |

### 3. Overview

The FRR implementation of BGP advertises prefixes learnt from a peer to other peers even if the routes do not get installed in the FIB. There can be scenarios where the hardware tables in some of the routers (along the path from the source to destination) is full which will result in all routes not getting installed in the FIB. If these routes are advertised to the downstream routers then traffic will start flowing and will be dropped at the intermediate router.

The solution is to provide a configurable option to check for the FIB install status of the prefixes and advertise to peers if the prefixes are successfully installed in the FIB. The advertisement of the prefixes are suppressed if it is not installed in FIB.

The following conditions apply will apply when checking for route installation status in FIB:

- The advertisement or suppression of routes based on FIB install status applies only for newly learnt routes from peer (routes which are not in BGP local RIB).
- If the route received from peer already exists in BGP local RIB and route attributes have changed (best path changed), the old path is deleted and new path is installed in FIB. The FIB install status will not have any effect. Therefore only when the route is received first time the checks apply.
- The feature will not apply for routes learnt through other means like redistribution to bgp from other protocols. This is applicable only to peer learnt routes.
- If a route is installed in FIB and then gets deleted from the dataplane, then routes will not be withdrawn from peers. This will be considered as dataplane issue.
- The feature will slightly increase the time required to advertise the routes to peers since the route install status needs to be received from the FIB
- If routes are received by the peer before the configuration is applied, then the bgp sessions need to be reset for the configuration to take effect.
- If the route which is already installed in dataplane is removed for some reason, sending withdraw message to peers is not currently supported.

[FRR documentation reference](https://github.com/FRRouting/frr/blob/master/doc/user/bgp.rst)

Consider the following scenario:

<!-- omit in toc -->
##### Figure 1. Use case scenario

<p align=center>
<img src="img/pic.png" alt="Figure 1. Use case scenario">
</p>

The problem with BGP programming occurs after the T1 switch is rebooted:
1. First, the T1 FRR learns a default route from at least 1 T2
2. The T0 advertises it’s prefixes to T1
3. FRR advertises the prefixes to T2 without waiting for them to be programmed in the ASIC
4. T2 starts forwarding traffic for prefixes not yet programmed, according to T1’s routing table, T1 sends it back to a default route – same T2


When the traffic is bounced back on lossless queue, buffers on both sides are overflown, credit loop happens, with PFC storm and watchdog triggered shutting down the port.
To avoid that, the route programming has to be synchronous down to the ASIC to avoid credit loops.

### 4. Requirements

- ```RouteOrch``` must use the ```ResponsePublisher``` API to create a feedback channel and write each route entry programming status for the ```fpmsyncd``` to consume
- The response channel can be turned off based on user configuration in a new ```APP_STATE_LOGGING``` table in CONFIG DB. This configuration is applied at startup and can't be changed while the system is running, requiring a ```config reload```
- A configuration knob ```bgp-suppress-fib-pending``` in ```DEVICE_METADATA``` table in CONFIG DB to control the enablement of the feature is required. This configuration is applied at startup and can't be changed while the system is running, requiring a ```config reload```. This knob can only be enabled if the corresponding response channel is enabled in ```APP_STATE_LOGGING```
- ```fpmsyncd``` must consume the responses from ```RouteOrch``` when the feature is enabled and communicate the status of a route back to ```zebra``` using ```FPM``` channel
- ```FRR``` must support ```bgp suppress-fib-pending``` as well as response channel via ```FPM```. Available as part of ```FRR``` 8.4 or requires a patched 8.2 release
- Link-local2ME, IP2Me routes responses aren't published
- MPLS, VNET routes are out of scope of this document

### 5. Architecture Design

Described functionality does not require changes to the current SONiC architecture. This design follows existing SONiC architecture approaches and uses existing SONiC infrastrcuture.

### 6. High-Level Design

#### 6.1. BGP Docker container startup

BGP configuration template ```bgpd.main.j2``` requires update to support the new field ```bgp-suppress-fib-pending``` and configure FRR accordingly. The startup flow of BGP container is described below:

<!-- omit in toc -->
##### Figure 2. BGP Configuration Flow Diagram

```mermaid
%%{
  init: {
    "theme": "forest",
    "sequence": {
      "rightAngles": true,
      "showSequenceNumbers": true
    }
  }
}%%
sequenceDiagram
    participant CONFIG_DB
    participant A as BGP /usr/bin/docker_init.sh
    participant S as sonic-cfggen
    participant T as bgpd.main.j2
    participant E as /etc/frr/bgpd.conf

    activate A

    A -->> S: /usr/share/sonic/templates/bgpd/gen_bgpd.conf.j2

    activate S

    S -->> T: <br>

    activate T

    CONFIG_DB -->> T: DEVICE_METADATA|localhost

    alt "bgp-suppress-fib-pending" == "enabled"
        T --> E: configure "bgp suppress-fib-pending" for router
    end


    deactivate T

    deactivate S

    A -->> A: start supervisord

    deactivate A
```

This configuration is supported in both ```unified``` and ```separated``` FRR configuration modes. Configuration template snippet *bgpd.main.conf.j2*:

```jinja2
router bgp {{ DEVICE_METADATA['localhost']['bgp_asn'] }}
{% if DEVICE_METADATA['localhost']['bgp-suppress-fib-pending'] == 'enabled' %}
  bgp suppress-fib-pending
{% endif %}
```


#### 6.2. RouteOrch

<!-- omit in toc -->
#### ResponsePublisher in RouteOrch

```RouteOrch``` need to use existing ```ResponsePublisher``` API to be able to publish responses into ```APPL_STATE_DB```.

A snippet of ```ResponsePublisher```'s API that is going to be used is given below. The ```state_attrs``` argument is used when a ```SET``` operation for a route entry in ```ROUTE_TABLE``` was performed successfully but the actual set of next hops differs from the intent. When the ```intent_attrs``` vector is empty it implies a ```DEL``` operations.

```c++
void ResponsePublisher::publish(const std::string &table, const std::string &key,
                                const std::vector<swss::FieldValueTuple> &intent_attrs,
                                const ReturnCode &status,
                                const std::vector<swss::FieldValueTuple> &state_attrs,
                                bool replace = false) override;
```

Example usage in ```RouteOrch```:

```c++
m_publisher.publish(APP_ROUTE_TABLE_NAME, kfvKey(kofvs), kfvFieldsValues(kofvs), ReturnCode(saiStatus), actualFvs, true);
```

<!-- omit in toc -->
#### RouteOrch Route Set Flow

```RouteOrch``` handles both local routes, pointing to local router interface, as well as next hop routes. On ```SET``` operation received in ```RouteOrch``` the ```RouteBulker``` is filled with create/set SAI operations depending on whether the route entry for the corresponding prefix was already created. In normal circumstances when next hop group is successfully created or found to be already existing the route entry is created or set with the corresponding next hop group SAI OID. The ```RouteOrch``` then calls ```RouteBulker::flush()``` that will form a bulk API call to SAIRedis. In ```RouteOrch::addRoutePost()``` the resulting object statuses are then collected and if some CREATE/SET operation failed orchagent calls ```abort()```, otherwise, on success, ```RouteOrch::addRoutePost()``` should publish the route programming status. Since there is no graceful handling of failed SAI operation the ```ResponsePublisher::publish()``` will be only called for a successfully programmed routes. In case a pre-condition for route programming is unmet, i.e unresolved neighbors in next hop group, the route entry programming is retried later and in such case there is no publishing of the result of the operation to ```APPL_STATE_DB``` until a pre-condition check is passed.

*A note on a temporary route*:

A special handling exists in ```RouteOrch``` for a case when there can't be more next hop groups created. In this case ```RouteOrch``` creates, a so called, "temporary" route, using only 1 next hop from the group and using it's ```SAI_OBJECT_TYPE_NEXT_HOP``` OID as ```SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID```. In this case, ```RouteOrch::addRoutePost()``` has to publish the route entry status as well as the actual ```nexthop``` field to ```APPL_STATE_DB```. A *temporary* route is kept in the ```m_toSync``` queue to be later on reprogrammed when sufficient resources are available for full next hop group creation.


<!-- omit in toc -->
##### Figure 3. RouteOrch Route Set Flow

```mermaid
%%{
  init: {
    "theme": "forest",
    "sequence": {
      "rightAngles": true,
      "showSequenceNumbers": true
    }
  }
}%%
sequenceDiagram
  participant APPL_DB
  participant RouteOrch
  participant RouteBulker
  participant ResponsePublisher
  participant APPL_STATE_DB
  participant ASIC_DB
  participant SYNCD

  APPL_DB --) RouteOrch: ROUTE_TABLE Notification
  activate RouteOrch

  RouteOrch ->> RouteOrch: doTask()

  loop For each entry in m_toSync
    alt NHG exist or can be added
      RouteOrch ->> RouteBulker: RouteBulker.create_entry() / RouteBulker.set_entry_attribute()
      activate RouteBulker
      RouteBulker -->> RouteOrch: <br>
      deactivate RouteBulker
    else NH can't be added
      Note right of RouteOrch: 1 NH is selected and addRoute()<br>is called with temporary NH
      RouteOrch ->> RouteBulker: RouteBulker.create_entry() / RouteBulker.set_entry_attribute()
      activate RouteBulker
      RouteBulker -->> RouteOrch: <br>
      deactivate RouteBulker
    end
  end

  Note left of RouteOrch: On any error/pre-condition failed<br>RouteOrch is retrying to program <br>the route on next iteration<br>In this case no response is written<br>

  RouteOrch ->> RouteBulker: RouteBulker.flush()
  activate RouteBulker
  RouteBulker ->> ASIC_DB: sai_route_api->create_route_entries()
  activate ASIC_DB
  ASIC_DB ->> SYNCD: sai_route_api->create_route_entries()
  activate SYNCD
  SYNCD -->> ASIC_DB: sai_status_t *object_statuses
  deactivate SYNCD
  ASIC_DB -->> RouteBulker: sai_status_t *object_statuses
  deactivate ASIC_DB

  RouteBulker ->> ASIC_DB: sai_route_api->set_route_entries_attribute()
  activate ASIC_DB
  ASIC_DB ->> SYNCD: sai_route_api->set_route_entries_attribute()
  activate SYNCD
  SYNCD -->> ASIC_DB: sai_status_t *object_statuses
  deactivate SYNCD
  ASIC_DB -->> RouteBulker: sai_status_t *object_statuses
  deactivate ASIC_DB

  RouteBulker -->> RouteOrch: <br>
  deactivate RouteBulker

  loop For each status in RouteBulker
    alt SAI_STATUS_SUCCESS
        RouteOrch ->> ResponsePublisher: ResponseBulisher.publish()
        activate ResponsePublisher
        ResponsePublisher ->> APPL_STATE_DB: <br>
        activate APPL_STATE_DB
        APPL_STATE_DB -->> ResponsePublisher: <br>
        deactivate APPL_STATE_DB
        Note right of RouteOrch: Publish actual FVs <br>(in case of temporary route only 1 NH is added)
        ResponsePublisher -->> RouteOrch: <br>
        deactivate ResponsePublisher
    else
        RouteOrch ->> RouteOrch: abort
    end
  end

  deactivate RouteOrch
```

<!-- omit in toc -->
#### RouteOrch Route delete Flow

<!-- omit in toc -->
##### Figure 4. RouteOrch Route Delete Flow

Similar processing happens on ```DEL``` operation for a prefix from ```ROUTE_TABLE```. The removed prefixes are filled in ```RouteBulker``` which are then flushed forming a bulk remove API call to SAIRedis. ```RouteOrch::removeRoutePost()``` then collects the object statuses and if the status is not SAI_STATUS_SUCCESS orchagent ```abort()```s, otherwise it should publish the result via ```ResponsePublisher::publish()``` leaving ```intent_attrs``` vector empty which will remove the corresponding state key from ```APPL_STATE_DB```.

```mermaid
%%{
  init: {
    "theme": "forest",
    "sequence": {
      "rightAngles": true,
      "showSequenceNumbers": true
    }
  }
}%%
sequenceDiagram
  participant APPL_DB
  participant RouteOrch
  participant RouteBulker
  participant ResponsePublisher
  participant APPL_STATE_DB
  participant ASIC_DB
  participant SYNCD

  APPL_DB --) RouteOrch: ROUTE_TABLE Notification
  activate RouteOrch

  RouteOrch ->> RouteOrch: doTask()

  loop For each entry in m_toSync
    RouteOrch ->> RouteBulker: RouteBulker.remove_entry()
    activate RouteBulker
    RouteBulker -->> RouteOrch: <br>
    deactivate RouteBulker
  end

  Note left of RouteOrch: On any error/pre-condition failed<br>RouteOrch is retrying to remove <br>the route on next iteration<br>In this case no response is written<br>

  RouteOrch ->> RouteBulker: RouteBulker.flush()
  activate RouteBulker
  RouteBulker ->> ASIC_DB: sai_route_api->remove_route_entries()
  activate ASIC_DB
  ASIC_DB ->> SYNCD: sai_route_api->remove_route_entries()
  activate SYNCD
  SYNCD -->> ASIC_DB: sai_status_t *object_statuses
  deactivate SYNCD
  ASIC_DB -->> RouteBulker: sai_status_t *object_statuses
  deactivate ASIC_DB

  RouteBulker -->> RouteOrch: <br>
  deactivate RouteBulker

  loop For each status in RouteBulker
    alt SAI_STATUS_SUCCESS
        RouteOrch ->> ResponsePublisher: ResponseBulisher.publish()
        activate ResponsePublisher
        ResponsePublisher ->> APPL_STATE_DB: <br>
        activate APPL_STATE_DB
        APPL_STATE_DB -->> ResponsePublisher: <br>
        deactivate APPL_STATE_DB
        Note right of RouteOrch: Publish the status and remove entry from APPL_STATE_DB
        ResponsePublisher -->> RouteOrch: <br>
        deactivate ResponsePublisher
    else
        RouteOrch ->> RouteOrch: abort
    end
  end

  deactivate RouteOrch
```

#### 6.3. FPMsyncd

<!-- omit in toc -->
##### Figure 5. FPMsyncd response processing

TODO

#### 6.4. Response Channel Performance considerations

Route programming performance is one of crucial characteristics of a network switch. It is desired to program a lot of route entries as quick as possible. SONiC has optimized route programming pipeline levaraging Redis Pipeline in ```ProducerStateTable``` as well as SAIRedis bulk APIs. Redis pipelining is a technique for improving performance by issuing multiple commands at once without waiting for the response to each individual command. Such an optimization gives around ~5x times faster processing for ```Publisher/Subscriber``` pattern using a simple python script as a test.

The following table shows the results for publishing 10k messages with and without Redis Pipeline proving the need for pipeline support for ```ResponseChannel```:

| Scenario                         | Time (sec) |
| -------------------------------- | ---------- |
| Publish 10k messages             | 2.41       |
| Publish 10k messages (Pipelined) | 0.43       |

Adding a feedback mechanism to the system introduces a delay as each of the component needs to wait for the reply from the lower layer counterpart in order to proceed. SONiC has already moved to synchronous SAI Redis pipeline a route programming performance degradation caused by it is leveled by the use of SAIRedis Bulk API.

By introducing a response channel it is required to leverage Redis Pipeline, so that the route configuration producer using Redis Pipeline with ```ProducerStateTable``` also receives route programming status responses produced by pipelined ```NotificationProducer``` which is part of ```ResponsePublisher```.

On the other side, ```fpmsyncd``` does not wait for each individual route status but rather performs an asynchronous processing.

The following schema represents communication methods between components:

```mermaid
%%{
  init: {
    "theme": "forest"
  }
}%%
flowchart LR
    zebra("</br>zebra</br></br>") -- FPM channel --> fpmsyncd("</br>fpmsyncd</br></br>")
    fpmsyncd -- "ProducerStateTable (Pipelined)" --> RouteOrch("</br>RouteOrch</br></br>")
    RouteOrch -. "ResponsePublisher (Pipelined)" -.-> fpmsyncd
    fpmsyncd -. FPM channel -.-> zebra
    RouteOrch -- "SAIRedis Bulk API" --> syncd("</br>syncd</br></br>")
    syncd -. "SAIRedis Bulk Reply" -.-> RouteOrch
```

A ```ResponsePublisher``` must have a constructor that accepts a ```RedisPipeline``` and a flag ```buffered``` to make it use the pipelining. The constructor is similar to one in use with ```ProducerStateTable```:

```c++
ResponsePublisher::ResponsePublisher(RedisPipeline *pipeline, bool buffered = false);
```

### 7. SAI API

No new SAI API or changes to SAI design and behaviour needed for this functionality.

### 8. Configuration and management

#### 8.1. Config DB Enhancements

##### 8.1.1. APP_STATE_LOGGING

Configuration schema in ABNF format:

```abnf
; APP_STATE_LOGGING table
key   = APP_STATE_LOGGING|ROUTE_TABLE ; Configuration for ROUTE_TABLE
state = "enabled"/"disabled"          ; Enable/disable response logging for ROUTE_TABLE
```

Sample of CONFIG DB snippet given below:

```json
{
    "APP_STATE_LOGGING": {
        "ROUTE_TABLE": {
            "state": "enabled"
        }
    }
}
```

##### 8.1.2. DEVICE_METADATA

Configuration schema in ABNF format:

```abnf
; DEVICE_METADATA table
key                      = DEVICE_METADATA|localhost ; Device metadata configuration table
bgp-suppress-fib-pending = "enabled"/"disabled"      ; Globally enable/disable BGP suppress-fib-pending feature,
                                                     ; by default this flag is disabled
```

Sample of CONFIG DB snippet given below:

```json
{
    "DEVICE_METADATA": {
        "localhost": {
            "bgp-suppress-fib-pending": "enabled"
        }
    }
}
```

This configuration is backward compatible. Upgrade from a SONiC version that does not support this feature does not change the user's expected behaviour as this flag is set to be disabled by default.

#### 8.2. Manifest (if the feature is an Application Extension)

This feature is implemented as part of existing BGP and SWSS containers, no manifest changes are required.

#### 8.3. CLI/YANG model Enhancements

##### 8.3.1. APP_STATE_LOGGING

A new table ```APP_STATE_LOGGING``` and a corresponding YANG model is added:

```yang
module sonic-app-state-logging {
    yang-version 1.1;

    namespace "http://github.com/Azure/sonic-app-state-logging";
    prefix app-state-logging;

    description "APP_STATE_LOGGING YANG module for SONiC OS";

    revision 2022-09-15 {
        description "Initial revision";
    }

    container sonic-app-state-logging {
        container APP_STATE_LOGGING {
            description "Controls the enablement of a response channel per APPL_DB table";

            container ROUTE_TABLE {
                description "Configure response channel for ASIC route configuration";

                leaf state {
                    description "Enablement state of response channel for the given table";
                    type enumeration {
                        enum enabled;
                        enum disabled;
                    }
                    default disabled;
                }
            }
        }
    }
}
```

Note that response channel for ROUTE_TABLE can be enabled regardless of ```synchronous_mode``` as we might still get a response from ```RouteOrch``` validation logic as well as ```SAIRedis``` validation.

##### 8.3.2.  DEVICE_METADATA

A new leaf is added to ```sonic-device_metadata/sonic-device_metadata/DEVICE_METADATA/localhost``` called ```bgp-suppress-fib-pending``` which can be set to ```"enable"``` or ```"disable"```.

Snippet of ```sonic-device_metatadata.yang```:

```yang
module sonic-device_metadata {
    import sonic-app-state-logging {
        prefix app-state-logging;
    }

    revision 2022-09-15 {
        description "Add BGP suppress FIB pending configuration knob";
    }

    container sonic-device_metadata {
        container DEVICE_METADATA {
            description "DEVICE_METADATA part of config_db.json";

            container localhost{
                leaf bgp-suppress-fib-pending {
                    description "Enable BGP suppress FIB pending feature. BGP will wait for route
                                 FIB intallation before announcing routes. This configuration requires
                                 restarting BGP sessions.";
                    type enumeration {
                        enum enabled;
                        enum disabled;
                    }
                    default disabled;

                    must "((current() = 'disabled') or (current() = 'enabled' and ../synchronous_mode = 'enable'
                           and /app-state-logging:sonic-app-state-logging/app-state-logging:
                               APP_STATE_LOGGING/app-state-logging:
                               ROUTE_TABLE/app-state-logging:state = 'enabled'))" {
                        error-message "ASIC synchronous mode and APP_STATE_LOGGIN for ROUTE_TABLE must
                                       be enabled in order to enable BGP suppress FIB pending feature";
                    }
                }
            }
        }
    }
}
```

This knob can only be set to ```"enable"``` when syncrhonous SAI configuration mode is on. This constraint is guaranteed by the ```must``` expression for this leaf.

No python ```click```-based CLI command nor ```KLISH``` CLI is planned to be implemented for this functionality.

### 9. Warmboot and Fastboot Design Impact

#### 9.1. Warm Reboot

Warm reboot process remains unchanged. With BGP Graceful Restart, peers are keeping advertised routes in the FIB while the switch restarts.


#### 9.2. Fast Reboot

TODO

### 10. Restrictions/Limitations

### 11. Testing Requirements/Design

Regression test, VS test and unit testing are required for this functionality.

Fast/warm reboot regression test suite needs to be ran and verified no degradation introduced by the feature.

#### 11.1. Unit Test cases

TODO

#### 11.2. VS Test cases

TODO

#### 11.3. System Test cases

TODO

### 12. Open/Action items - if any

TODO
