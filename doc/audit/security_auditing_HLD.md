# SONiC Security Auditing

## Table of Content
- [SONiC Security Auditing](#sonic-security-auditing)
  - [Table of Content](#table-of-content)
  - [List of Tables](#list-of-tables)
  - [Revision](#revision)
  - [Scope](#scope)
  - [1. Overview](#1-overview)
  - [2. Current Architecture Design](#2-current-architecture-design)
  - [3. High-level Design](#3-high-level-design)
    - [3.1 Design](#31-design)
    - [3.2 Audit Rules Review](#32-audit-rules-review)
    - [3.3 Configuration design](#33-configuration-design)
      - [3.3.1 ConfigDB schema](#331-configdb-schema)
        - [3.3.1.1 AUDIT TABLE](#3311-audit-table)
        - [3.3.1.2 Config DB JSON Sample](#3312-config-db-json-sample)
        - [3.3.1.3 Redis Entries Sample](#3313-redis-entries-sample)
      - [3.3.2 YANG model](#332-yang-model)
      - [3.3.3 CLI design](#333-cli-design)
      - [3.3.4 Logrotate](#334-logrotate)
    - [3.4 Warmboot and Fastboot Design Impact](#34-warmboot-and-fastboot-design-impact)
    - [3.5 Timeline](#35-timeline)
    - [3.6 Performance](#36-performance)
    - [3.7 Audit Rule Order](#37-audit-rule-order)
    - [3.8 Security Compliance](#38-security-compliance)
  - [4. Testing Requirements/Design](#4-testing-requirementsdesign)
    - [4.1 Unit Test cases](#41-unit-test-cases)
    - [4.2 System Test cases](#42-system-test-cases)

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
- Introduce a new file, `security-auditing.rules`, into the `/etc/audit/rules.d/` directory
- A predefined set of rules (detailed in section 3.2) will be automatically enabled as the default configuration.
- Modify the `/etc/audit/plugins.d/syslog.conf` file by setting `active = yes` to enable the forwarding of auditd logs to a syslog server.
- ConfigDB schema design
- YANG model
- CLI commands to enable or disable all rules, with support for adding or removing individual rules for fine-grained control:
  - `show audit`
  - `config audit enable`
  - `config audit disable`
  - `config audit add <rule>`
  - `config audit remove <rule>`
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
| Process audit            | `-a never,exit -F path=/usr/bin/docker  -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/dockerd  -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/containerd -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/runc -F key=process_audit`<br>`-a never,exit -F path=/usr/bin/python* -F key=process_audit`<br>`-a exit,always -F arch=b64 -S execve -F key=process_audit`<br>`-a exit,always -F arch=b32 -S execve -F key=process_audit` |
| Network activity         | `-a exit,always -F arch=b64 -S connect,accept,sendto,recvfrom -F key=network_activity`<br>`-a exit,always -F arch=b32 -S connect,sendto,recvfrom -F key=network_activity` |
| Socket activity          | `-a always,exit -F arch=b64 -S socket -F key=socket_activity`<br>`-a always,exit -F arch=b32 -S socket -F key=socket_activity` |

### 3.3 Configuration design
#### 3.3.1 ConfigDB schema
##### 3.3.1.1 AUDIT TABLE
The database to be used is Config DB. A new AUDIT table will be added to the Config DB, which is responsible for storing audit configuration settings. This table allows the system to manage security auditing by defining whether auditing is enabled and specifying the rules to be applied. The structure of the AUDIT table is as follows
```
; Defines audit configuration information
key                          = AUDIT|config                 ; Audit configuration settings
; field                      = value
enable                       = boolean                      ; Indicates whether security auditing is enabled (true/false)
RULESET                      = list                         ; List of audit rule sets
name                         = 1*255VCHAR                   ; Name of the audit rule set
rule                         = 1*255VCHAR                   ; Audit rule definition in auditd format
```

##### 3.3.1.2 Config DB JSON Sample
The predefined list of rules in section 3.2 will be enabled as default. Example of how the audit rules might be represented in JSON format within the Config DB
```
{
    "AUDIT": {
        "config": {
            "enable": "true",
            "RULESET": [
                {
                    "name": "file_deletion",
                    "rules": [
                        "-a exit,always -F arch=b64 -S unlink -S unlinkat -F key=file_deletion",
                        "-a exit,always -F arch=b32 -S unlink -S unlinkat -F key=file_deletion"
                    ]
                },
                {
                    "name": "dns_changes",
                    "rules": [
                        "-w /etc/resolv.conf -p wa -k dns_changes"
                    ]
                }
            ]
        }
    }
}
```

##### 3.3.1.3 Redis Entries Sample
Once the AUDIT table is populated in the Config DB, the corresponding entries can be viewed in Redis. Below are example Redis commands and outputs
```
127.0.0.1:6379[4]> keys AUDIT|config
1) "AUDIT|config"

127.0.0.1:6379[4]> hgetall AUDIT|config
1) "enable"
2) "true"
3) "RULESET|file_deletion|1"
4) "-a exit,always -F arch=b64 -S unlink -S unlinkat -F key=file_deletion"
5) "RULESET|file_deletion|2"
6) "-a exit,always -F arch=b32 -S unlink -S unlinkat -F key=file_deletion"
7) "RULESET|dns_changes|1"
8) "-w /etc/resolv.conf -p wa -k dns_changes"
```

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

    revision 2024-08-12 {
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

                list RULESET {
                    key "name";
                    description "List of audit rules";

                    leaf name {
                        type string;
                        description "Name of the audit rule";
                    }

                    list rule {
                        key "rule";
                        type string;
                        description "Audit rule definition";
                    }
                }
            }
            /* end of container config */
        }
        /* end of container AUDIT */
    }
    /* end of top level container */
}
+/* end of module sonic-audit */
```

#### 3.3.3 CLI design
**show command**
- `show audit` - show all audit current active rules, including security auditing rules and tacplus accounting rules.
  ```
  admin@vlab-01:~$ show audit
  List of current .rules files in /etc/audit/rules.d/ directory
  audisp-tacplus.rules
  audit.rules
  security-auditing.rules

  List of all current active audit rules
  -a always,exit -F arch=b32 -S exit,execve,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a always,exit -F arch=b64 -S execve,exit,exit_group -F auid>1000 -F auid!=-1 -F key=tacplus
  -a always,exit -F arch=b64 -S socket -F key=socket_activity
  -a always,exit -F arch=b32 -S socket -F key=socket_activity
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
  admin@vlab-01:~$ show audit
  List of current .rules files in /etc/audit/rules.d/ directory
  audisp-tacplus.rules
  audit.rules

  List of all current active audit rules
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

**config command enable/disable**
- Usage
  ```
  config audit <enable/disable>
  ```
- `config audit enable` - enables all **security** audit rules (`security-auditing.rules`)
  ```
  admin@sonic:~$ config audit enable
  Security auditing is enabled.
  ```

- `config audit disable` - removes or disables all **security** audit rules
  ```
  admin@sonic:~$ config audit disable
  Security auditing is disabled.
  ```

**config command add/remove**
- Usage
  ```
  config audit add [--name <name>] [--rules <rules>]
  config audit remove [--name <name>]
  ```

- Requirements
  ```
  // --name and --rules are mandatory
  // --name specifies the audit key name. The --name value must exactly match the -k value in the --rules. 
      // Example: time_changes
  // --rules defines the audit rule in auditd format. The rule must include a key (-k) that exactly matches the --name value.
  // This ensures that the corresponding rule can be easily removed.
      // Example: -w /etc/localtime -p wa -k time_changes

  // A single --name value can be associated with multiple --rules entries. However, when adding rules, each rule must be added individually.
      // Example: User wants to add/remove these rules
      // -a always,exit -F arch=b64 -S socket -F key=socket_activity
      // -a always,exit -F arch=b32 -S socket -F key=socket_activity

      // Example CLI commands to add above rules:
          // Step 1: config audit add --name socket_activity --rules "-a always,exit -F arch=b64 -S socket -F key=socket_activity"
          // Step 2: config audit add --name socket_activity --rules "-a always,exit -F arch=b32 -S socket -F key=socket_activity"
      // Example CLI commands to remove above rules:
          // S tep 1: config audit remove --name socket_activity
  ```

- `config audit add` - add an individual audit rule  
  For example, `--name` value is `time_changes`, which is exactly same as `-k` value in `--rules`
  ```
  admin@sonic:~$ config audit add --name "time_changes"  --rules "-w /etc/localtime -p wa -k time_changes"
  Added time_changes rule
  ```

- `config audit remove` - remove an individual audit rule
  ```
  admin@sonic:~$ config audit remove --name "time_changes"
  Removed time_changes rule
  ```

#### 3.3.4 Logrotate
The following settings in the `/etc/logrotate.d/audit` file set up log rotation for audit logs:
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

### 3.6 Performance
Monitor memory and CPU utilization for auditd and kauditd processes over an hour

Tested device specs
SONiC Software Version: SONiC.20230531.22
Platform: x86_64-arista_7260cx3_64
HwSKU: Arista-7260CX3-C64

| Rule name | Tested Device |
|-----------|---------------|
| %CPU      | 1.0% - 2.0%   |
| %MEM      | 0.0% - 0.1%   |

Number of logs per key
| Audit Key | Count By Key |
|-----------|---------------|
| network_activity |	72021|
| socket_activity |	3312 |
| user_group_management	| 801 |
| process_audit	| 729 |
| file_deletion	| 529 |
| tacplus	| 259 |
| log_changes	| 199 |
| docker_storage | 156 |
| cron_changes | 6 |
| shutdown_reboot |	4 |
| modules	| 3 |
| auth_logs	| 1 |
| bin_changes	| 1 |
| time_changes | 1 |
| dns_changes	| 1 |
| sbin_changes | 1 |
| usr_bin_changes | 1 |
| usr_sbin_changes | 1 |
| docker_socket | 1 |
| docker_commands | 1 |
| docker_service | 1 |
| hosts_changes	| 1 |
| sudoers_changes	| 1 |
| docker_config	| 1 |
| docker_daemon	| 1 |

Processes in network_activity key
| Process | Count By Process |
|-----------|---------------|
| /usr/sbin/audisp-syslog | 41896 |
| /usr/sbin/rsyslogd | 11145 |
| /usr/sbin/snmpd | 8000 |
| /usr/bin/python3.9 | 7313 |
| /usr/bin/vtysh | 809 |
| /usr/bin/redis-check-rdb | 485 |
| /usr/bin/docker	| 354 |
| /usr/bin/teamd | 322 |
| /usr/sbin/lldpd	| 307 |
| /usr/sbin/audisp-tacplus | 276 |
| /usr/bin/sudo | 190 |
| /usr/sbin/sshd | 174 |
| /usr/bin/eventd	| 166 |
| /usr/bin/bash	| 116 |
| /bin/bash	| 114 |
| /usr/sbin/auditctl| 68 |
| /usr/sbin/lldpcli	| 55 |
| /usr/lib/frr/bgpd	| 44 |
| /usr/sbin/ntpd | 37 |
| /usr/lib/frr/zebra | 35 |
| /usr/bin/monit | 35 |
| /usr/lib/frr/staticd | 29 |
| /usr/sbin/cron | 19 |
| /usr/bin/systemctl | 15 |
| /usr/bin/rsyslog_plugin	| 12 |
| /usr/sbin/usermod	| 2 |
| /usr/bin/syncd | 2 |

### 3.7 Audit Rule Order
For best performance, it is recommended that the events that occur the most should be at the top and the exclusions should be at the bottom on the list. 

### 3.8 Security Compliance
The new rules will be assessed with the security team to ensure compliance.

## 4. Testing Requirements/Design
### 4.1 Unit Test cases
###### Table 3: Unit Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | Unit Test for config audit enable  |
| 2         | Unit Test for config audit disable |
| 3         | Unit Test for show audit           |
| 4         | Unit Test for config audit add     |
| 5         | Unit Test for config audit remove  |

### 4.2 System Test cases
###### Table 4: System Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | System Test for config audit enable test |
| 2         | System Test for configaudit disable test |
| 3         | System Test for log test - verify that audit accurately send logs to syslog server. |
| 4         | System Test for performance test |
| 5         | System Test for audit rule ordering test for default rules |
| 6         | System Test for config audit add rule test |
| 7         | System Test for config audit remove rule test |
