Table of Contents
<!-- TOC -->
- [Scope](#scope)
- [Overview](#overview)
- [Quality Objective](#quality-objective)
- [Module design](#module-design)
  - [Overall design](#overall-design)
  - [Updated directory structure](#updated-directory-structure)
  - [Thresholds overview](#thresholds-overview)
  - [Thresholds configuration file](#thresholds-configuration-file)
  - [Thresholds template](#thresholds-template)
  - [Preliminary defaults](#preliminary-defaults)
- [Pytest plugin overview](#pytest-plugin-overview)
  - [Pytest option](#pytest-option)
  - [Pytest hooks](#pytest-hooks)
  - [Classes](#classes)
- [Interaction with dut](#interaction-with-dut)
- [Tests execution flaw](#tests-execution-flaw)
- [Extended info to print for error cases](#extended-info-to-print-for-error-cases)
- [Commands to fetch monitoring data](#commands-to-fetch-monitoring-data)
- [Possible future expansion](#possible-future-expansion)
  
<!-- /TOC -->

### Scope

This document describes the high level design of verification the hardware resources consumed by a device. The hardware resources which are currently verified are CPU, RAM and HDD.

This implementation will be integrated in test cases written on Pytest framework.

### Overview

During tests run test cases perform many manipulations with DUT including different Linux and SONiC configurations and sending traffic. 

To be sure that CPU, RAM and HDD resources utilization on DUT are not increasing within tests run, those parameters can be checked after each finished test case. 

Purpose of the current feature is to - verify that previously listed resources are not increasing during tests run. It achieves by performing verification after each test case. 

### Quality Objective
+ Ensure CPU consumption on DUT does not exceed threshold 
+ Ensure RAM consumption on DUT does not exceed threshold 
+ Ensure used space in the partition mounted to the HDD "/" root folder does not exceed threshold

### Module design
#### Overall design
The following figure depicts current feature integration with existed Pytest framework.

![](https://github.com/yvolynets-mlnx/SONiC/blob/dut_monitor/images/dut_monitor_hld/Load_flaw.jpg)

Newly introduced feature consists of:
+ Pytest plugin – pytest_dut_monitor.py. Plugin defines:
  + pytest hooks: pytest_addoption , pytest_configure, pytest_unconfigure
  + pytest fixtures: dut_ssh, dut_monitor
  + DUTMonitorPlugin – class to be registered as plugin. Define pytest fixtures described above
  + DUTMonitorClient - class to control DUT monitoring over SSH
+ Pytest plugin registers new option “--dut_monitor"
+ Python module - dut_monitor.py. Which is running on DUT and collects CPU, RAM and HDD data and writes it to the log files. There will be created three new files: cpu.log, ram.log, hdd.log.

#### Updated directory structure
+ ./sonic-mgmt/tests/thresholds.yml
+ ./sonic-mgmt/tests/plugins/pytest_dut_monitor.py
+ ./sonic-mgmt/tests/monitoring/dut_monitor.py

#### Thresholds overview
To be able to verify that CPU, RAM or HDD utilization are not critical on the DUT, there is a need to define specific thresholds.

List of thresholds:
+ Total system CPU consumption
+ Separate process CPU consumption
+ Time duration of CPU monitoring
+ Average CPU consumption during test run
+ Peak RAM consumption
+ RAM consumption delta before and after test run
+ Used disk space

```Total system CPU consumption``` - integer value (percentage). Triggers when total peak CPU consumption is >= to defined value during “Peak CPU monitoring duration” seconds.

```Separate process CPU consumption``` - integer value (percentage). Triggers when peak CPU consumption of any separate process is >= to defined value during “Peak CPU measurement duration” seconds.

```Time duration of CPU monitoring``` - integer value (seconds). Time frame. Used together with total or process peak CPU consumption verification.

```Average CPU consumption during test run``` - integer value (percentage). Triggers when the average CPU consumption of the whole system between start/stop monitoring (between start/end test) is >= to defined value.

```Peak RAM consumption``` – integer value (percentage). Triggers when RAM consumption of the whole system is >= to defined value.

```RAM consumption delta before and after test``` – integer value (percentage). Difference between consumed RAM before and after test case. Triggers when the difference is >= to defined value.

```Used disk space``` - integer value (percentage). Triggers when used disk space is >= to defined value.

#### Thresholds configuration file

As for now configuration files are stored in the sonic-mgmt/tests/ folder, thresholds config file, for now, can be stored here as well - ./sonic-mgmt/tests/thresholds.yml 

As different platforms have different hardware the proposal is to define thresholds per platform instead of common.

##### Thresholds template:
```code
Platform X:
    CPU_total: x
    CPU_process: x
    CPU_measure_duration: x
    CPU_total_average: x
    RAM_peak: x
    RAM_delta: x
    HDD_used: x

...
```
##### Preliminary defaults
Note: need to be tested to define accurately.

    CPU_total: 90
    CPU_process: 60
    CPU_measure_duration: 10
    CPU_total_average: 90
    RAM_peak: 80
    RAM_delta: 1
    HDD_used: 80

### Pytest plugin overview

#### Pytest option
To enable DUT monitoring for each test case the following pytest console option should be used - "--dut_monitor"

#### Pytest hooks
dut_monitor.py module defines the following hooks:
##### pytest_addoption(parser)
Register "--dut_monitor" option. This option used for trigger device monitoring.
##### pytest_configure(config)
Check whether "--dut_monitor" option is used, if so register DUTMonitorPlugin class as pytest plugin.
##### pytest_unconfigure(config)
Unregister DUTMonitorPlugin plugin.

### Classes
#### DUTMonitorClient class
Define API for:

+ Start monitoring on the DUT
+ Stop monitoring on the DUT. Compare measurements with defined thresholds
+ Execute remote commands via SSH
+ Track SSH connection with DUT
+ Automatically restore SSH connection with DUT while in monitoring mode

#### DUTMonitorPlugin class
Defines the following pytest fixtures:

##### dut_ssh(autouse=True, scope="session")
Establish SSH connection with a device. Keeps this connection during all tests run.

If the connection to the DUT is broken during monitoring phase (test performed DUT reboot), it will automatically try to restore connection during some time (for example 5 minutes).

If the connection will be restored, monitoring will be automatically restored as well and dut_monitor fixture will have monitoring results even if reboot occurred. So, monitoring results will not be lost if in some case DUT will be rebooted.

If the connection will not be restored, exception will be raised that DUT become inaccessible.

##### dut_monitor(dut_ssh, autouse=True, scope="function")
- Starts DUT monitoring before test start
- Stops DUT monitoring after test finish
- Get measured values and compare them with defined thresholds
- Pytest error will be generated if any of resources exceed the defined threshold.


### Interaction with dut

![](https://github.com/yvolynets-mlnx/SONiC/blob/dut_monitor/images/dut_monitor_hld/Dut_monitor_ssh.jpg)

### Tests execution flaw

+ Start pytest run with added “–dut_monitor” option
+ Before each test case - initialize DUT monitoring
+ Start reading CPU, RAM and HDD values every 2 seconds
+ Start test case
+ Wait the test case to finish
+ Stop reading CPU, RAM and HDD values
+ Display logging message with measured parameters
+ After the end of each test case compare obtained values with defined thresholds
+ Pytest error will be generated if any of resources exceed the defined threshold. Error message will also show extended output about consumed CPU, RAM and HDD, which is described below. Test case status like pass/fail still be shown separately. It gives possibility to have separate results for test cases (pass/fail) and errors if resources consumption exceed the threshold.


#### Extended info to print for error cases
Display output of the following commands:

+ df -h --total /*
+ ps aux --sort rss
+ docker stats --all --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

### Commands to fetch monitoring data

##### Fetch CPU consumption:
ps -A -o pcpu | tail -n+2 | python -c "import sys; print(sum(float(line) for line in sys.stdin))"
##### Fetch RAM consumption:
show system-memory
OR
ps -A -o rss | tail -n+2 | python -c "import sys; print(sum(float(line) for line in sys.stdin))"

##### Fetch HDD usage:
df -hm /


### Possible future expansion

Later this functionality can be integrated with some UI interface where will be displayed consumed resources and device health during regression run. As UI board can be used Grafana. 

It can be useful for DUT health debugging and for load/stress testing analysis.
