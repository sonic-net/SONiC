SONiC on-demand show command execution via gNMI
=============================================

# Table of contents
- [Goals](#goals)
- [Problems to solve](#problems-to-solve)
- [What we bring in](#what-we-bring-in)
- [Use case](#use-case)
- [gNMI client](#gnmi-client)
- [New design (HLD)](#new-design-hld)
- [Details](#details)
- [STATS update](#stats-update)
- [Examples](#examples)
- [Requirements](#requirements)
- [Test](#test)
- [Future plan](#future-plan)

# Goals
1. Provide a way to execute show CLI commands on device (on-demand) and get the output.
2. Avoid interactive login to the device for command execution.
3. Return output in JSON format equivalent to CLI output.
4. Support throttling targets:
   - Up to 32 parallel command executions per device.
   - Up to 100 maximum concurrent connections.

# Problems to solve
Existing tools (or new tools) that require device data for lifecycle workflows do not always have near real-time access to SONiC state.

Today, data collection generally happens in two ways:
1. Log in to the device and run CLI commands.
   - This needs manual or scripted login workflows.
   - It introduces device access/security overhead.
   - It is slower due to multiple execution steps.
2. Use telemetry service output.
   - Telemetry is interval-based for many workflows.
   - Not all show command outputs are available.

Below is the diagram for current execution paths.

## Current flow diagram
![Current Flow](https://microsoft.sharepoint.com/:i:/t/Aznet/IQDNfCwS9H8fTpUN0eg-_69iAUhdl4jJVCjtCFIuzg_LCgA?e=kYVQWU)

# What we bring in
1. Enable gNMI protocol support for on-demand retrieval/streaming of device data.
2. Expose APIs that automation can call and consume in JSON format.
3. Provide near real-time, on-demand execution controlled by the caller.
4. Keep execution resource usage low.
   - Memory: ~194 MB (P90)
   - CPU: ~4% (P90) 
5. Provide native gNMI benefits such as parallel streams and secure transport.
6. Enable top-level AAA integration so automation can access data without interactive shell login.

## New flow (desired) diagram
![New Flow](https://microsoft.sharepoint.com/:i:/t/Aznet/IQBg1L-WMkr9Q5dD8ypgWGe9AVlX9ADRiyqlhWYSsZ7Lgoo?e=8B1QDv)

# Use case
A system issue is detected (reactive or proactive signal). As a first-level check, operators commonly run commands such as:
- `show version`
- `show reboot-cause`

With this design, automation/agents can fetch equivalent output through gNMI APIs.

For `show reboot-cause`:

## Current CLI output
$ show reboot-cause history

| Name                | Cause  | Time                              | User  | Comment |
|---------------------|--------|-----------------------------------|-------|---------|
| 2026_03_06_23_22_55 | reboot | Fri Mar 6 11:20:41 PM UTC 2026    | admin | N/A     |
| 2026_03_06_23_12_54 | reboot | Fri Mar 6 11:10:42 PM UTC 2026    | admin | N/A     |

## gNMI output
```json
{
  "reboot_cause": {
    "history": {
      "Name": "2025_06_30_05_20_10",
      "Cause": "reboot",
      "Time": "Mon Jun 30 05:18:35 AM UTC 2025",
      "User": "admin",
      "Comment": "N/A"
    }
  }
}
{
  "reboot_cause": {
    "history": {
      "Name": "2025_05_14_19_33_09",
      "Cause": "Power Loss",
      "Time": "Wed May 14 07:30:02 PM UTC 2025",
      "User": "admin",
      "Comment": "Unknown"
    }
  }
}
```

# gNMI client
Any gNMI client can be used to query this data from SONiC.

On device, Telemetry container runs the gNMI server using server certificate and trusted CA roots. A client certificate can be:
- Issued by a CA already present in SONiC trusted root, or
- Issued by a new CA that is explicitly added to SONiC trusted root.

Once certificates are configured, the gNMI client communicates with the gNMI server in Telemetry container.

## Example get command
```bash
./gnmi_cli -client_types=gnmi \
  -a <DEVICE-IP>:<PORT> \
  -ca <path_to_CA_crt> \
  -client_crt <path_to_client_crt> \
  -client_key <path_to_client_key> \
  -t OTHERS -logtostderr \
  -qt p -pi 10s -q show/interface/status/Ethernet0
```

# New design (HLD)
**TODO:** Replace with final HLD diagram image/link.

![HLD](https://microsoft.sharepoint.com/:i:/t/Aznet/IQCdYjwiFfnAQottXCMk2z94AeGgbtNZvsIwzRlswSU-iS0?e=tFk9u4)

# Details
Show commands retrieve data from multiple backends:
- Redis
- System files
- Shell commands
- vtysh
- Hardware sysfs
- Streaming/system command sources

A Go-based library is implemented to collect data from these sources and is linked with gNMI server in Telemetry container.

Query path analysis resulted in two virtual path types for gNMI Get APIs.

## 1. Non-parameterized query
No parameter is required.

```bash
./gnmi_cli -client_types=gnmi \
  -a <DEVICE-IP>:<PORT> \
  -ca <path_to_CA_crt> \
  -client_crt <path_to_client_crt> \
  -client_key <path_to_client_key> \
  -t OTHERS -logtostderr \
  -qt p -pi 10s -q show/reboot_cause/history
```

## 2. Parameterized query
A parameter is required.

```bash
./gnmi_cli -client_types=gnmi \
  -a <DEVICE-IP>:<PORT> \
  -ca <path_to_CA_crt> \
  -client_crt <path_to_client_crt> \
  -client_key <path_to_client_key> \
  -t OTHERS -logtostderr \
  -qt p -pi 10s -q show/interface[interface=Ethernet0]/status
```

# STATS update
The stats are maintained to capture the status of service.  
Intend is to track the progress and create monitoring on these stats. Same monitoring can be used to create alerts.  
Note: Below mentioned data is collected manually, right now we don't have such stats dumped in DB/Logs.
**TODO:** Update the stats data from gNMI Watchdog results

## Counters
- `show-cmd-requests-total`
  - Total gNMI on-demand show requests accepted by telemetry service.
- `show-cmd-responses-success`
  - Total successful responses sent to gNMI clients.
- `show-cmd-responses-failed`
  - Total failed responses due to internal execution or mapping errors.
- `show-cmd-missed-slow-receiver`
  - Total responses dropped due to client-side back pressure or slow receive path.
- `show-cmd-throttled-requests`
  - Total requests rejected by throttling controls.
- `show-cmd-active-sessions`
  - Current active concurrent client sessions.

## Latency
- `show-cmd-latency-avg-ms`
  - Average latency over moving window for recent requests.
- `show-cmd-latency-p95-ms`
  - 95th percentile latency over moving window.
- `show-cmd-latency-p99-ms`
  - 99th percentile latency over moving window.

Latency is computed as:

`< response timestamp > - < request accepted timestamp >`

## Update behavior
- The update of service is linked with telemetry container.
- Health of service is also determined via telemetry container.

# Examples
## Example 1: reboot cause history
```bash
./gnmi_cli -client_types=gnmi \
  -a <DEVICE-IP>:<PORT> \
  -ca <path_to_CA_crt> \
  -client_crt <path_to_client_crt> \
  -client_key <path_to_client_key> \
  -t OTHERS -logtostderr \
  -qt p -pi 10s -q show/reboot_cause/history
```

```json
{
  "reboot_cause": {
    "history": {
      "Name": "2025_06_30_05_20_10",
      "Cause": "reboot",
      "Time": "Mon Jun 30 05:18:35 AM UTC 2025",
      "User": "admin",
      "Comment": "N/A"
    }
  }
}
{
  "reboot_cause": {
    "history": {
      "Name": "2025_05_14_19_33_09",
      "Cause": "Power Loss",
      "Time": "Wed May 14 07:30:02 PM UTC 2025",
      "User": "admin",
      "Comment": "Unknown"
    }
  }
}
```

## Example 2: interface status
```bash
./gnmi_cli -client_types=gnmi \
  -a <DEVICE-IP>:<PORT> \
  -ca <path_to_CA_crt> \
  -client_crt <path_to_client_crt> \
  -client_key <path_to_client_key> \
  -t OTHERS -logtostderr \
  -qt p -pi 10s -q show/interface[interface=Ethernet0]/status
```

```json
{
  "show/interface/status/Ethernet0": {
    "Interface": "Ethernet0",
    "Speed": "1000",
    "MTU": "1500",
    "Oper": "up",
    "Admin": "up"
  }
}
```

  # Requirements
  1. Support up to 32 parallel command executions per device.
  2. Support up to 100 concurrent client connections.
  3. Preserve AAA-based authentication and authorization controls for all requests.
  4. Return output in structured JSON format equivalent to CLI semantics.
  5. Support both non-parameterized and parameterized query paths.
  6. Ensure secure transport using mutual TLS certificates.
  7. Expose operational counters and latency metrics through DB and gNMI stream.

  # Test
  Tests are required to keep behavior stable across releases and to validate concurrency, reliability, and output consistency.  
  From below list #1, #2 are already taken care.

 **TODO:** How should we provide the container tests to community and capture here.

  1. Unit tests
    - Validate path-to-handler mapping for non-parameterized and parameterized queries.
    - Validate JSON output schema for each supported show command.
    - Validate failure paths (invalid parameter, unsupported path, backend timeout).
  2. Functional tests
    - Run representative commands (`show reboot-cause`, `show interface status`) and compare against expected output.
    - Validate certificate-based client authentication and authorization behavior.
  3. Scale and throttling tests
    - Validate 32 parallel command execution target per device.
    - Validate 100 concurrent client connection target.
    - Validate throttling counters and rejection behavior under overload.
  4. Resiliency tests
    - Validate behavior during telemetry container restart.
    - Validate timeout handling for slow backend data sources.

# Future plan
1. Enable the Stats and configure  monitoring/alerting on it.
2. Expand virtual path coverage for additional show commands.
3. Using new go-lang library in CLI calls.
4. Add schema validation for output consistency across releases.
5. Add formal SLA definitions for latency and throughput.
6. Add unit and scale tests for concurrency and throttling behavior.
7. Publish API/query path catalog for automation consumers.
