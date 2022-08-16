# SONiC Syslog Message Rate Limit Configuration Per Container#

## Table of Content

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

### Scope

This document is the design document for syslog message rate limit configuration per container.

### Definitions/Abbreviations

N/A

### Overview

Logging in SONiC is organized with rsyslogd. Each container has its own rsyslogd instance plus a daemon running on host side. The rsyslogd instance which is running on the host is used to collect the messages from within containers and store them at certain path (E.g. /var/log/syslog). Rsyslog config file are generated from templates:

- Container scope:
  - Multi ASIC: https://github.com/Azure/sonic-buildimage/blob/master/files/image_config/rsyslog/rsyslog-container.conf.j2
  - Single ASIC: https://github.com/Azure/sonic-buildimage/blob/master/dockers/docker-base/etc/rsyslog.conf
- Host scope: https://github.com/Azure/sonic-buildimage/blob/master/files/image_config/rsyslog/rsyslog.conf.j2

Currently, each container has hardcoded message rate limiting to avoid receiving flooded log messages:

```
$SystemLogRateLimitInterval 300
$SystemLogRateLimitBurst 20000
```
There is no rate limiting configured on host side for now.

The SystemLogRateLimitInterval determines the amount of time that is being measured for rate limiting. The SystemLogRateLimitBurst defines the amount of messages, that have to occur in the time limit of SystemLogRateLimitInterval, to trigger rate limiting. For example, SystemLogRateLimitInterval=300, SystemLogRateLimitBurst=20000, it means that if one daemon generate more than 20000 messages in 300 seconds, rsyslogd will start to drop messages after that(FIFO).

This feature allows user to configure SystemLogRateLimitInterval and SystemLogRateLimitBurst for host, containers.

### Requirements

- Support syslog message rate limit configuration for host and containers
- New CLI for rate limit configuration
- Have rate limit configuration persistent
- Default rate limit shall be applied if no configuration provided
- Both multi ASIC and single ASIC platform shall use rsyslog-container.conf.j2 as template
- APP extension shall be able to declare its capability of this feature
- APP extension is responsible for reading/listening rate limit configuration from CONFIG DB and set rsyslog configuration accordingly.

### Architecture Design

rsyslog.conf.j2 and rsyslog-container.conf.j2 shall be extended to accept template variable for SystemLogRateLimitInterval and SystemLogRateLimitBurst. rsyslog.conf for single ASIC platform will be removed and replaced by rsyslog-container.conf.j2.

Host side:

![host_config_on_fly](/doc/syslog/images/host_rate_limit_config_flow.svg).

Change syslog message rate limit while container is running:

![container_config_on_fly](/doc/syslog/images/container_rate_limit_config_flow.svg).

For app extension, CLI shall only put the configuration to CONFIG DB and let app extension itself to handle it. How app extension handle CONFIG DB change is out of the feature scope.

Load syslog message rate limit configuration during startup is already covered by existing flow, no change of the flow is required:

- Host: rsyslog-config service automatically loads rate limit configuration from CONFIG DB and apply it to rsyslog
- Container: each container have a startup script which automatically generates rsyslog configuration and apply it to rsyslog in container

> Note: according to test, syslog rate limit configuration on host side would not affect container side.

### High-Level Design

Changes shall be made into sonic-utilities, sonic-buildimage. CLI changes of sonic-utilities will be covered by chapter "Configuration and management".

> Note: Code present in this design document is only for demonstrating the design idea, it is not production code.

#### init_cfg.json.j2
New tables shall be added to CONFIG DB to store the rate limit configuration. init_cfg.json.j2 shall be extended to define the default value for each built-in containers.

```
...
    "SYSLOG_CONFIG": {
        "GLOBAL": {
            "rate_limit_interval" : "0",
            "rate_limit_burst" : "0"
        }
    },
    "SYSLOG_CONFIG_FEATURE": {
{%- for feature, _, _, _ in features %}
        "{{feature}}": {
            "rate_limit_interval" : "300",
            "rate_limit_burst": "20000"
        }{%if not loop.last %},{% endif -%}
{% endfor %}
    }
...
```

#### rsyslog.conf.j2

```
{% if SYSLOG_CONFIG is defined %}
{% if 'GLOBAL' in SYSLOG_CONFIG %}
{% if 'rate_limit_interval' in SYSLOG_CONFIG['GLOBAL']%}
{% set rate_limit_interval = SYSLOG_CONFIG['GLOBAL']['rate_limit_interval'] %}
{% endif %}
{% if 'rate_limit_burst' in SYSLOG_CONFIG['GLOBAL']%}
{% set rate_limit_burst = SYSLOG_CONFIG['GLOBAL']['rate_limit_burst'] %}
{% endif %}
{% endif %}
{% endif %}

{% if rate_limit_interval is defined %}
$SystemLogRateLimitInterval {{ rate_limit_interval }}
{% endif %}
{% if rate_limit_burst is defined %}
$SystemLogRateLimitBurst {{ rate_limit_burst }}
{% endif %}
```

#### rsyslog-container.conf.j2

```
{% set rate_limit_interval = '300' %}
{% set rate_limit_burst = '20000' %}

{% if SYSLOG_CONFIG_FEATURE is defined %}
{% if container_name in SYSLOG_CONFIG_FEATURE %}
{% if 'rate_limit_interval' in SYSLOG_CONFIG_FEATURE[container_name]%}
{% set rate_limit_interval = SYSLOG_CONFIG_FEATURE[container_name]['rate_limit_interval'] %}
{% endif %}
{% if 'rate_limit_burst' in SYSLOG_CONFIG_FEATURE[container_name]%}
{% set rate_limit_burst = SYSLOG_CONFIG_FEATURE[container_name]['rate_limit_burst'] %}
{% endif %}
{% endif %}
{% endif %}

$SystemLogRateLimitInterval {{ rate_limit_interval }}
$SystemLogRateLimitBurst {{ rate_limit_burst }}
```

#### docker_image_ctl.j2

Function `updateSyslogConf` in the template currently only works for multi ASIC platform, it shall be extended to work for both multi ASIC and single ASIC platform. The only difference between multi ASIC and single ASIC platform is the target IP of rsyslog.

- Mulit ASIC: target IP of rsyslog is get from docker0 IP which is already implemented in docker_image_ctl.j2
- Single ASIC: target IP of rsyslog is always 127.0.0.1.

Meanwhile, the file https://github.com/Azure/sonic-buildimage/blob/master/dockers/docker-base/etc/rsyslog.conf as well as any code processing it shall be removed.

#### APP extension

APP extension shall be able to expose its constant syslog capability by adding a new field to manifest:

```
root@sonic:/home/admin# spm show package manifest what-just-happened
{
    ...
    "service": {
        ...
        "syslog": {
            "support-rate-limit": "true",
            "customized-rate-limit": "false"
        }
        ...
    }
    ...
}
```

support-rate-limit: indicates if this APP extension supports configuring rate limit. This field affected CLI behavior: if true, CLI shall put rate limit configuration to CONFIG DB; otherwise, CLI shall reject the configuration.
customized-rate-limit: indicates if this APP extension is using "SONiC official way" to configure rate limit. Effective only if support-rate-limit is true. This field affected CLI behavior: if false, CLI shall generated rsyslogd configuration file by rendering rsyslog-container.conf.j2, coping it to relevant container and restart rsyslogd by supervisorctl command; otherwise, app extension shall handle CONFIG DB change and set log rate limit accordingly. "SONiC official way" means:

- Using rsyslogd
- Configuration of rsyslogd is generated by rsyslog-container.conf.j2
- rsyslogd can be managed by supervisorctl



The capability shall also be saved to CONFIG DB to allow easy access by management plane:

```
root@sonic:/home/admin# cat /etc/sonic/config_db.json
{
    "FEATURE": {
        ...
        "what-just-happened": {
            ...
            "support_syslog_rate_limit": "True",
            "has_customized_syslog_rate_limit": "False"
            ...
        }
        ...
}
```

Also, default value shall be provided to https://github.com/Azure/sonic-utilities/blob/master/sonic_package_manager/service_creator/feature.py:

```
DEFAULT_SYSLOG_FEATURE_CONFIG = {
    'rate_limit_interval': '300',
    'rate_limit_burst': '20000'
}
```

### SAI API

N/A

### Configuration and management

#### CLI change

Config rate limit:

```
config syslog rate-limit-host --interval <interval> --burst <burst>
config syslog rate-limit-container <service_name> --interval <interval> --burst <burst>

Example:
config syslog rate-limit-host --interval 300 --burst 20000
config syslog rate-limit-host --interval 300
config syslog rate-limit-host --burst 20000
config syslog rate-limit-container bgp --interval 300 --burst 20000
```

> Note: set interval or burst to 0 will disable rate limit.

Show rate limit:

```
show syslog rate-limit-host
show syslog rate-limit-container [<service_name>]

Example:
show syslog rate-limit-host
INTERVAL     BURST
----------   --------
500          50000

show syslog rate-limit-container
SERVICE    INTERVAL     BURST
--------   ----------   --------
bgp        500          N/A
snmp       300          20000
swss       2000         12000

show syslog rate-limit-container bgp
SERVICE    INTERVAL     BURST
--------   ----------   --------
bgp        500          5000
```

#### YANG model

```yang
...
container SYSLOG_CONFIG {

    description "SYSLOG_CONFIG part of config_db.json";

    container GLOBAL {
        leaf rate_limit_interval {
            description "Message rate limit interval";
            type uint32 {
                range 0..2147483647;
            }
        }

        leaf rate_limit_burst {
            description "Message rate limit burst";
            type uint32 {
                range 0..2147483647;
            }
        }
    }
    /* end of list SYSLOG_CONFIG_LIST */
}
/* end of container SYSLOG_CONFIG */

container SYSLOG_CONFIG_FEATURE {

    description "SYSLOG_CONFIG_FEATURE part of config_db.json";

    list SYSLOG_CONFIG_FEATURE_LIST {

        key "service";

        leaf service {
            description "Service name";
            type leafref {
                path "/feature:sonic-feature/feature:FEATURE/feature:FEATURE_LIST/feature:name";
            }
        }

        leaf rate_limit_interval {
            description "Message rate limit interval";
            type uint32 {
                range 0..2147483647;
            }
        }

        leaf rate_limit_burst {
            description "Message rate limit burst";
            type uint32 {
                range 0..2147483647;
            }
        }
    }
    /* end of list SYSLOG_CONFIG_FEATURE_LIST */
}
/* end of container SYSLOG_CONFIG_FEATURE */
...


container FEATURE {

    description "feature table in config_db.json";

    list FEATURE_LIST {
        ...

        leaf support_syslog_rate_limit {
            description "This configuration indicates if the feature support configuring syslog rate limit";
            type stypes:boolean_type;
            default "false";
        }

        leaf has_customized_syslog_rate_limit {
            description "This configuration indicates if the feature has customized syslog rate limit configuration";
            type stypes:boolean_type;
            default "false";
        }

        ...
    }
}
```

### Warmboot and Fastboot Design Impact

N/A

### Restrictions/Limitations

1. Cannot support container not registered to FEATURE table
2. Persist syslog configuration for database container will not be loaded on next reboot/reload.
3. Configuring rate limit would cause rsyslogd dropping some log messages because it will restart rsyslogd.

### Testing Requirements/Design

#### Unit Test cases
1. Verify command "config syslog rate-limit-host"
2. Verify command "config syslog rate-limit-container"
3. Verify command "show syslog rate-limit-host"
4. Verify command "show syslog rate-limit-container"

#### sonic-mgmt Test cases

Two new test case shall be added:

##### test_syslog_rate_limit_container

1.	Loop each container
2.	Change the syslog rate limit of current container
3.	Use a generated script to print log from current container which is fast enough to hit the limit
4.	Check syslog that some logs are dropped

##### test_syslog_rate_limit_host

1.	Change the syslog rate limit of host
2.	Use a generated script to print log from host which is fast enough to hit the limit
3.	Check syslog that some logs are dropped

#### Open questions:
1. How about have an agent to handle syslog rate limit configuration change in each container?
