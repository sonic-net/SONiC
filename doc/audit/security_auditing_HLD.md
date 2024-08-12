# SONiC Security Auditing

## Table of Content
- [SONiC Security Auditing](#sonic-security-auditing)
  - [Table of Content](#table-of-content)
  - [List of Tables](#list-of-tables)
  - [Revision](#revision)
          - [Table 1: Revision](#table-1-revision)
  - [Scope](#scope)
  - [1. Overview](#1-overview)
  - [2. Current Architecture Design](#2-current-architecture-design)
  - [3. High-level Design](#3-high-level-design)
    - [3.1 Design](#31-design)
    - [3.2 Audit Rules Review](#32-audit-rules-review)
          - [Table 2: Audit Rules Review](#table-2-audit-rules-review)
    - [3.3 Configuration design](#33-configuration-design)
      - [3.3.1 ConfigDB schema](#331-configdb-schema)
      - [3.3.2 YANG model](#332-yang-model)
      - [3.3.3 CLI design](#333-cli-design)
      - [3.3.4 Logrotate](#334-logrotate)
      - [3.3.5 Audit Rule Order](#335-audit-rule-order)
    - [3.4 Warmboot and Fastboot Design Impact](#34-warmboot-and-fastboot-design-impact)
    - [3.5 Timeline](#35-timeline)
    - [3.6 Security Compliance](#36-security-compliance)
    - [3.7 Supported Branches](#37-supported-branches)
  - [4. Testing Requirements/Design](#4-testing-requirementsdesign)
    - [4.1 Unit Test cases](#41-unit-test-cases)
          - [Table 3: Unit Test cases](#table-3-unit-test-cases)
    - [4.2 System Test cases](#42-system-test-cases)
          - [Table 4: System Test cases](#table-4-system-test-cases)

## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: Audit Rules Review](#table-2-audit-rules-review)
* [Table 3: Unit Test Cases](#table-3-unit-test-cases)
* [Table 4: System Test Cases](#table-4-system-test-cases)

## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/14/2024  | Mai Bui            | Initial version                   |

## Scope
This section describes the audit enhancement high-level design in SONiC.

## 1. Overview
This design aims to enhance the auditing capabilities within SONiC operating system using audit daemon (auditd). Auditing is the process of recording and analyzing the events that occur on the device. Auditing can help to detect unauthorized access, configuration changes, malicious activity, or system errors. Auditing can also provide evidence for forensic investigations, compliance audits, or incident response.

This document outlines the addition of several auditd rules to enhance the auditing capabilities on a SONiC device. These extra rules aim to provide thorough monitoring of important system activities, making the device more secure and better prepared for compliance and incident response.

## 2. Current Architecture Design
In SONiC, audit settings are centrally managed through a configuration file at `/etc/audit/auditd.conf`. Upon system startup, SONiC automatically compiles audit rules from the `/etc/audit/rules.d/` directory into a single file, `/etc/audit/audit.rules`, which auditd then loads. Here is a brief look at the relevant files:
- `/etc/audit/auditd.conf` - Main configuration file.
- `/etc/audit/audit.rules` - Loaded at startup, compiled from the individual rules in the rules.d directory.
- `/etc/audit/rules.d/` - Directory for individual rule files
  - `audisp-tacplus.rules`
  - `audit.rules`

## 3. High-level Design
### 3.1 Design
- Introduce a new file, `security-auditing.rules`, into the `/etc/audit/rules.d/` directory.
- Additionally, the `/etc/audit/plugins.d/syslog.conf` is modified (by setting `active = yes`) to enable sending auditd logs to a syslog server.
- ConfigDB schema design
- YANG model
- CLI commands enhancement
  - `config audit enable`
  - `config audit disable`
  - `show audit`
- Logrotate
- Audit rules ordering

### 3.2 Audit Rules Review
###### Table 2: Audit Rules Review
These rules will be included in the image and enabled by default.
| Rule name | Details |
|--------------------------|--------------------------|
| Critical files changes   | `-w /etc/passwd -p wa -k passwd_changes`<br>`-w /etc/shadow -p wa -k shadow_changes`<br>`-w /etc/group -p wa -k group_changes`<br>`-w /etc/sudoers -p wa -k sudoers_changes`<br>`-w /etc/hosts -p wa -k hosts_changes` |
| DNS changes              | `-w /etc/resolv.conf -p wa -k dns_changes` |
| Time changes             | `-w /etc/localtime -p wa -k time_changes` |
| Shutdown reboot          | `-w /var/log/wtmp -p wa -k shutdown_reboot` |
| Cron changes             | `-w /etc/crontab -p wa -k cron_changes`<br>`-w /etc/cron.d -p wa -k cron_changes`<br>`-w /etc/cron.daily -p wa -k cron_changes`<br>`-w /etc/cron.hourly -p wa -k cron_changes`<br>`-w /etc/cron.weekly -p wa -k cron_changes`<br>`-w /etc/cron.monthly -p wa -k cron_changes` |
| Modules                  | `-w /sbin/insmod -p x -k modules`<br>`-w /sbin/rmmod -p x -k modules`<br>`-w /sbin/modprobe -p x -k modules` |
| auth.log changes         | `-w /var/log/auth.log -p wa -k auth_logs` |
| Monitor binary dirs      | `-w /bin -p wa -k bin_changes`<br>`-w /sbin -p wa -k sbin_changes`<br>`-w /usr/bin -p wa -k usr_bin_changes`<br>`-w /usr/sbin -p wa -k usr_sbin_changes` |
| User group management    | `-a always,exit -F arch=b64 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management`<br>`-a always,exit -F arch=b32 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management` |
| File deletion            | `-a exit,always -F arch=b64 -S unlink -S unlinkat -F key=file_deletion`<br>`-a exit,always -F arch=b32 -S unlink -S unlinkat -F key=file_deletion` |
| Log changes              | `-w /var/log -p wa -k log_changes` |
| Docker related           | `-w /usr/bin/dockerd -p wa -k docker_daemon`<br>`-w /etc/docker/daemon.json -p wa -k docker_config`<br>`-w /lib/systemd/system/docker.service -p wa -k docker_service`<br>`-w /lib/systemd/system/docker.socket -p wa -k docker_socket`<br>`-a always,exit -F arch=b64 -S execve -F path=/usr/bin/docker -k docker_commands`<br>`-w /var/lib/docker/ -p wa -k docker_storage`<br>`-a always,exit -F arch=b64 -S setuid,setgid,bind,connect -F comm="/usr/bin/docker" -k docker_sys` |
| Process audit            | `-a never,exit -F path=/usr/bin/docker  -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/dockerd  -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/containerd -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/runc -F perm=x`<br>`-a never,exit -F path=/usr/bin/python* -F perm=x`<br>`-a exit,always -F arch=b64 -S execve -F key=process_audit`<br>`-a exit,always -F arch=b32 -S execve -F key=process_audit` |
| Network activity         | `-a exit,always -F arch=b64 -S connect,accept,sendto,recvfrom -F key=network_activity`<br>`-a exit,always -F arch=b32 -S connect,sendto,recvfrom -F key=network_activity` |
| Socket activity          | `-a always,exit -F arch=b64 -S socket -F key=socket_activity`<br>`-a always,exit -F arch=b32 -S socket -F key=socket_activity` |

### 3.3 Configuration design
#### 3.3.1 ConfigDB schema
```
{
    "AUDIT": {
      "config": {
        "enable": "true"
      }
    }
}
```
| Key       | Description                 |
| --------- | --------------------------- |
| enable    | enable or not enable the AUDIT, the default value is true  |

The AUDIT config is in the redis CONFIG_DB. The redis dictionary key is AUDIT|config.

| Key       | Description                 |
| --------- | --------------------------- |
| enabled   | The flag indicating whether the AUDIT enabled, 1 enabled, others not enabled  |

#### 3.3.2 YANG model
New YANG model `sonic-audit.yang` will be added.
```
module sonic-audit {

    yang-version 1.1;

    namespace "http://github.com/sonic-net/sonic-audit";

    prefix sonic-audit;

    import sonic-types {
        prefix stypes;
    }

    description "AUDIT YANG Module for SONiC OS";

    revision 2024-06-20 {
        description "First Revision";
    }

    container sonic-audit {

        container AUDIT {

            description "AUDIT part of config_db.json";

            container config {

                leaf enable {
                    description "This configuration identicates whether enable audit";
                    type stypes:boolean_type;
                    default "true";
                }
            }
            /* end of container config */
        }
        /* end of container AUDIT */
    }
    /* end of top level container */
}
/* end of module sonic-audit */
```

#### 3.3.3 CLI design
**show command**
- `show audit` - show all audit current active rules, including security auditing rules and tacplus accounting rules.
  ```
  admin@sonic:~$ show audit
  -a always,exit -F arch=b32 -S exit,execve,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a always,exit -F arch=b64 -S execve,exit,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a never,exit -F path=/usr/bin/docker -F perm=x -F key=process_audit
  -a never,exit -F path=/usr/bin/dockerd -F perm=x -F key=process_audit
  -a never,exit -F path=/usr/bin/containerd -F perm=x -F key=process_audit
  -a never,exit -F path=/usr/bin/runc -F perm=x -F key=process_audit
  -a never,exit -F path=/usr/bin/python* -F perm=x -F key=process_audit
  -a always,exit -F arch=b64 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management
  -a always,exit -F arch=b32 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management
  -a exit,always -F arch=b64 -S unlink -S unlinkat -F key=file_deletion
  -a exit,always -F arch=b32 -S unlink -S unlinkat -F key=file_deletion
  -a always,exclude -F msgtype=CRED_ACQ
  -a always,exclude -F msgtype=CRED_DISP
  -a always,exclude -F msgtype=CRED_REFR
  -a always,exclude -F msgtype=CWD
  -a always,exclude -F msgtype=LOGIN
  -a always,exclude -F msgtype=PATH
  -a always,exclude -F msgtype=PROCTITLE
  -a always,exclude -F msgtype=SERVICE_START
  -a always,exclude -F msgtype=SERVICE_STOP
  -a always,exclude -F msgtype=USER_ACCT
  -a always,exclude -F msgtype=USER_AUTH
  -a always,exclude -F msgtype=USER_CMD
  -a always,exclude -F msgtype=USER_END
  -a always,exclude -F msgtype=USER_START
  ```
  If security auditing is disabled, `show audit` will only show tacplus accounting rule.
  ```
  admin@sonic:~$ show audit
  -a always,exit -F arch=b32 -S exit,execve,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a always,exit -F arch=b64 -S execve,exit,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a always,exclude -F msgtype=CRED_ACQ
  -a always,exclude -F msgtype=CRED_DISP
  -a always,exclude -F msgtype=CRED_REFR
  -a always,exclude -F msgtype=CWD
  -a always,exclude -F msgtype=LOGIN
  -a always,exclude -F msgtype=PATH
  -a always,exclude -F msgtype=PROCTITLE
  -a always,exclude -F msgtype=SERVICE_START
  -a always,exclude -F msgtype=SERVICE_STOP
  -a always,exclude -F msgtype=USER_ACCT
  -a always,exclude -F msgtype=USER_AUTH
  -a always,exclude -F msgtype=USER_CMD
  -a always,exclude -F msgtype=USER_END
  -a always,exclude -F msgtype=USER_START
  ```

**config command**
- `config audit enable` -  enables all **security** audit rules (`security-auditing.rules`).
  ```
  admin@sonic:~$ config audit enable
  Security auditing is enabled.
  ```
- `config audit disable` - removes or disables all **security** audit rules.
  ```
  admin@sonic:~$ config audit disable
  Security auditing is disabled.
  ```

#### 3.3.4 Logrotate
The following settings in the /etc/logrotate.d/audit file set up log rotation for audit logs:
```
{
    rotate 30
    daily
    compress
    delaycompress
    notifempty
    missingok
    postrotate
        /etc/init.d/auditd restart
    endscript
}
```

This will:
- Rotate the logs daily (`daily`).
- Keep 30 days' worth of logs (`rotate 30`).
- Compress the logs after rotation (`compress`).
- Delay the compression of the most recent rotated log until the next rotation cycle (`delaycompress`).
- Skip rotation if the log file is empty (`notifempty`).
- Continue rotation without reporting an error if the log file is missing (`missingok`).
- Restart the auditd service after rotating the logs (`postrotate /etc/init.d/auditd restart endscript`).

#### 3.3.5 Audit Rule Order
For best performance, it is recommended that the events that occur the most should be at the top and the exclusions should be at the bottom on the list. 

### 3.4 Warmboot and Fastboot Design Impact
auditd will be stopped and then restarted as part of the reboot process, resulting in a gap in audit logs

### 3.5 Timeline
- Phase 1
  - Critical files changes
  - DNS changes
  - Time changes
  - Shutdown reboot
  - Cron changes
  - Modules
  - auth.log changes
  - Monitor binary directories
- Phase 2
  - User group management
  - File deletion
  - Log changes
  - Docker related
  - Process audit
  - Network activity
  - Socket activity

### 3.6 Security Compliance
The new rules will be assessed with the security team to ensure compliance.

### 3.7 Supported Branches
Ensure supporting 202311 branch.

## 4. Testing Requirements/Design
### 4.1 Unit Test cases
###### Table 3: Unit Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | Unit Test for config audit enable  |
| 2         | Unit Test for config audit disable |
| 3         | Unit Test for show audit           |

### 4.2 System Test cases
###### Table 4: System Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | System Test for audit enable test |
| 2         | System Test for audit disable test |
| 3         | System Test for log test - verify that audit accurately send logs to syslog server. |
| 4         | System Test for performance test |
| 5         | System Test for audit rule ordering test |
