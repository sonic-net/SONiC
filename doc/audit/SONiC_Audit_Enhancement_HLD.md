# SONiC Audit Enhancement

## Table of Content
- [SONiC Audit Enhancement](#sonic-audit-enhancement)
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
      - [3.3.2 CLI design](#332-cli-design)
    - [3.4 Warmboot and Fastboot Design Impact](#34-warmboot-and-fastboot-design-impact)
    - [3.5 Timeline](#35-timeline)
    - [3.6 Security Compliance](#36-security-compliance)
    - [3.7 Backward Compatibility](#37-backward-compatibility)
  - [4. Testing Requirements/Design](#4-testing-requirementsdesign)
    - [4.1 Unit Test cases](#41-unit-test-cases)
          - [Table 3: Unit Test cases](#table-3-unit-test-cases)
    - [4.2 System Test cases](#42-system-test-cases)
          - [Table 4: System Test cases](#table-4-system-test-cases)

## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: Rules Review](#table-2-rules-review)
* [Table 3: Unit Test Cases](#table-3-unit-test-cases)
* [Table 4: E2E Test Cases](#table-4-e2e-test-cases)

## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/14/2024  | Mai Bui            | Initial version                   |

## Scope
This section describes the audit enhancement high-level design in SONiC.

## 1. Overview
This design aims to enhance the auditing capabilities within SONiC operating system using audit daemon (auditd). Auditing is the process of recording and analyzing the events that occur on the device. Auditing can help to detect unauthorized access, configuration changes, malicious activity, or system errors. Auditing can also provide evidence for forensic investigations, compliance audits, or incident response.

## 2. Current Architecture Design
In SONiC, audit settings are centrally managed through a configuration file at `/etc/audit/auditd.conf`. Upon system startup, SONiC automatically compiles audit rules from the `/etc/audit/rules.d/` directory into a single file, `/etc/audit/audit.rules`, which auditd then loads. Here is a brief look at the relevant files:
- `/etc/audit/auditd.conf` - Main configuration file.
- `/etc/audit/audit.rules` - Loaded at startup, compiled from the individual rules in the rules.d directory.
- `/etc/audit/rules.d/` - Directory for individual rule files:
  - `audisp-tacplus.rules`
  - `audit.rules`

## 3. High-level Design
### 3.1 Design
- Introduce a new file, `custom-audit.rules`, into the `/etc/audit/rules.d/` directory.
- Additionally, the `/etc/audit/plugins.d/syslog.conf` is modified (by setting `active = yes`) to enable sending auditd logs to a syslog server.
- ConfigDB schema design
- CLI commands enhancement
  - `config audit enable`
  - `config audit disable`
  - `show audit`

### 3.2 Audit Rules Review
###### Table 2: Audit Rules Review
| Rule name | Details |
|--------------------------|--------------------------|
| Process audit            | `sudo auditctl -d never,exit -F path=/usr/bin/docker  -F key=process_audit`<br>`sudo auditctl -d never,exit -F path=/usr/bin/dockerd  -F key=process_audit`<br>`sudo auditctl -d never,exit -F path=/usr/bin/containerd -F key=process_audit`<br>`sudo auditctl -d never,exit -F path=/usr/bin/runc -F perm=x`<br>`sudo auditctl -d never,exit -F path=/usr/bin/python* -F perm=x`<br>`sudo auditctl -d exit,always -F arch=b64 -S execve -F key=process_audit`<br>`sudo auditctl -d exit,always -F arch=b32 -S execve -F key=process_audit` |
| File deletion            | `-a exit,always -F arch=b64 -S unlink -S unlinkat -F key=file_deletion`<br>`-a exit,always -F arch=b32 -S unlink -S unlinkat -F key=file_deletion` |
| Critical files changes   | `-w /etc/passwd -p wa -k passwd_changes`<br>`-w /etc/shadow -p wa -k shadow_changes`<br>`-w /etc/group -p wa -k group_changes`<br>`-w /etc/sudoers -p wa -k sudoers_changes`<br>`-w /etc/hosts -p wa -k hosts_changes` |
| auth.log changes         | `-w /var/log/auth.log -p wa -k auth_logs` |
| Network activity         | `-a exit,always -F arch=b64 -S connect,accept,sendto,recvfrom -F key=network_activity`<br>`-a exit,always -F arch=b32 -S connect,sendto,recvfrom -F key=network_activity` |
| DNS changes              | `-w /etc/resolv.conf -p wa -k dns_changes` |
| Socket activity          | `-a always,exit -F arch=b64 -S socket -F key=socket_activity`<br>`-a always,exit -F arch=b32 -S socket -F key=socket_activity` |
| Time changes             | `-w /etc/localtime -p wa -k time_changes` |
| Shutdown reboot          | `-w /var/log/wtmp -p wa -k shutdown_reboot` |
| Cron changes             | `-w /etc/crontab -p wa -k cron_changes`<br>`-w /etc/cron.d -p wa -k cron_changes`<br>`-w /etc/cron.daily -p wa -k cron_changes`<br>`-w /etc/cron.hourly -p wa -k cron_changes`<br>`-w /etc/cron.weekly -p wa -k cron_changes`<br>`-w /etc/cron.monthly -p wa -k cron_changes` |
| User group management    | `-a always,exit -F arch=b64 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management`<br>`-a always,exit -F arch=b32 -S setuid,setresuid,setreuid,setfsuid,setgid,setresgid,setregid,setfsgid -F key=user_group_management` |
| Modules                  | `-w /sbin/insmod -p x -k modules`<br>`-w /sbin/rmmod -p x -k modules`<br>`-w /sbin/modprobe -p x -k modules` |
| Sudo usage               | `-w /var/log/sudo.log -p wa -k sudo_usage` |
| Log changes              | `-w /var/log -p wa -k log_changes` |
| Docker related           | `-w /usr/bin/dockerd -p wa -k docker_daemon`<br>`-w /etc/docker/daemon.json -p wa -k docker_config`<br>`-w /lib/systemd/system/docker.service -p wa -k docker_service`<br>`-w /lib/systemd/system/docker.socket -p wa -k docker_socket`<br>`-a always,exit -F arch=b64 -S execve -F path=/usr/bin/docker -k docker_commands`<br>`-w /var/lib/docker/ -p wa -k docker_storage`<br>`-a always,exit -F arch=b64 -S execve -F path=/usr/bin/docker -k network_activity`<br>`-a always,exit -F arch=b64 -S setuid,setgid,bind,connect -F comm="/usr/bin/docker" -k docker_sys` |

### 3.3 Configuration design
#### 3.3.1 ConfigDB schema
```
{
    "AUDIT": {
      "global": {
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

#### 3.3.2 CLI design
- `config audit enable` - enables all audit rules including existing `audisp-tacplus.rules` and new `custom-audit.rules`.
- `config audit disable` - removes all audit rules.
- `show audit` - show audit enabled or disabled, if enabled, show all audit current active rules.

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
  - Sudo usage
  - User group management
  - File deletion
  - Log changes
  - Docker related
  - Process audit
  - Network activity
  - Socket activity

### 3.6 Security Compliance
The new rules will be assessed with the security team to ensure compliance.

### 3.7 Backward Compatibility
Ensure compatibility with the 202311 branch.

## 4. Testing Requirements/Design
### 4.1 Unit Test cases
###### Table 3: Unit Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | UT for config audit enable  |
| 2         | UT for config audit disable |
| 3         | UT for show audit           |

### 4.2 System Test cases
###### Table 4: System Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | E2E for audit enable test|
| 2         | E2E for audit disable test|
| 3         | E2E for log test - verify that audit accurately send logs to syslog server. |
