# SONiC Syslog Sequential Index

## Table of Content
- [SONiC Syslog Sequential Index](#sonic-syslog-sequential-index)
  - [Table of Content](#table-of-content)
  - [List of Tables](#list-of-tables)
  - [Revision](#revision)
  - [Scope](#scope)
  - [1. Overview](#1-overview)
  - [2. Current Architecture Design](#2-current-architecture-design)
  - [3. High-level Design](#3-high-level-design)
    - [3.1 Design](#31-design)
    - [3.1 Sample Code Change](#31-sample-code-change)
  - [4. Testing Requirements/Design](#4-testing-requirementsdesign)
    - [4.1 System Test cases](#41-system-test-cases)

## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: System Test Cases](#table-4-system-test-cases)


## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/26/2024  | Mai Bui            | Initial version                   |

## Scope
This document outlines the implementation of a sequential index for syslog messages in SONiC. The goal is to enhance syslog by adding a unique sequential identifier to each message, making it easier to track message flow and detect any lost messages across different log files.

## 1. Overview
In SONiC, syslog messages are essential for monitoring system events and diagnosing issues. However, these messages currently lack a sequential identifier, which can make it challenging to:
- Determine the exact order of events.
- Detect missing messages, especially when messages are sent over unreliable networks like UDP.

By introducing a sequential index to each syslog message, we can:
- Easily track the sequence of events across all logs.
- Identify gaps in the sequence that indicate message loss.
- Improve overall system monitoring and troubleshooting.

## 2. Current Architecture Design
Currently, syslog messages in SONiC are handled by rsyslog and are written to various log files based on their type:
- `/var/log/syslog`: General system messages.
- `/var/log/auth.log`: Authentication-related messages.
- `/var/log/cron.log`: Cron job messages.

Each of these files records messages independently, and there is no shared sequence or identifier linking them together. Additionally:
- Messages are sent over UDP to remote log servers, which does not guarantee delivery.
- If messages are lost, there's no straightforward way to detect or account for them.

## 3. High-level Design
### 3.1 Design
The proposed solution is to modify the rsyslog configuration to include a global counter variable that acts as a sequential identifier for all syslog messages. Here's how it works:
- Initialize a Counter: Start a global counter at 0 when rsyslog starts.
- Increment the Counter: Increase the counter by 1 for every syslog message processed.
- Include the Counter in Logs: Modify the log message template to include the counter value at the beginning of each message.

Handling Successful Message Delivery:
- When all messages are delivered successfully, combining the logs from `/var/log/syslog`, `/var/log/auth.log`, and `/var/log/cron.log` will show a continuous sequence of IDs without gaps.
- Individual log files may have gaps because they record different types of messages, but the combined logs will be sequential.

Handling Message Loss:
- If messages are lost (e.g., due to UDP transmission issues), there will be gaps in the sequence of IDs even in the combined logs.
- By analyzing the sequence numbers, we can detect missing messages.

### 3.1 Sample Code Change
Modify the `/etc/rsyslog.conf` file as follows:
```
45c45
< $template SONiCFileFormat,"%timegenerated%.%timegenerated:::date-subseconds% %HOSTNAME% %syslogseverity-text:::uppercase% %syslogtag% %msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%\n"
---
> $template SONiCFileFormat,"%timegenerated%.%timegenerated:::date-subseconds% %HOSTNAME% %syslogseverity-text:::uppercase% ID:%$/counter% %syslogtag%%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%\n"
81a82,90
>
> if $/counter == "" then
>     set $/counter = 0;
>
> *.* {
>     set $/counter = $/counter + 1;
> }
>
```

Sample logs
```
2024 Sep 26 19:16:50.496445 strtk5-sn3800-01 INFO ID: systemd[1]: Stopping rsyslog.service - System Logging Service...
2024 Sep 26 19:16:50.497159 strtk5-sn3800-01 INFO ID:1 rsyslogd: [origin software="rsyslogd" swVersion="8.2302.0" x-pid="2683123" x-info="https://www.rsyslog.com"] exiting on signal 15.
2024 Sep 26 19:16:50.539056 strtk5-sn3800-01 INFO ID:2 systemd[1]: rsyslog.service: Deactivated successfully.
2024 Sep 26 19:16:50.539357 strtk5-sn3800-01 INFO ID:3 systemd[1]: Stopped rsyslog.service - System Logging Service.
2024 Sep 26 19:16:50.569378 strtk5-sn3800-01 INFO ID:4 systemd[1]: Starting rsyslog.service - System Logging Service...
2024 Sep 26 19:16:50.575072 strtk5-sn3800-01 INFO ID:5 rsyslogd: imuxsock: Acquired UNIX socket '/run/systemd/journal/syslog' (fd 3) from systemd.  [v8.2302.0]
2024 Sep 26 19:16:50.575164 strtk5-sn3800-01 INFO ID:6 rsyslogd: [origin software="rsyslogd" swVersion="8.2302.0" x-pid="2739183" x-info="https://www.rsyslog.com"] start
2024 Sep 26 19:16:50.575234 strtk5-sn3800-01 INFO ID:7 systemd[1]: Started rsyslog.service - System Logging Service.
```

## 4. Testing Requirements/Design
### 4.1 System Test cases
###### Table 2: System Test cases
| Test case | Description                 |
| --------- | --------------------------- |
| 1         | Confirm that the counter initializes and increments by 1 for each syslog message. |
| 2         | Generate various syslog messages and verify continuous IDs in combined logs. |
| 3         | Simulate message loss (e.g., drop UDP packets) and check for gaps in sequence IDs. |
| 4         | Restart rsyslog and ensure the counter resets or continues as expected. |
