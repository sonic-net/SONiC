# SSD Cleanup #

## Table of Content 

### Revision  
| Rev | Date             | Author                  | Change Description                                           |
|:---:|:----------------:|:-----------------------:|:------------------------------------------------------------:|
| 0.1 |                  | Itamar Talomn           | Initial version                                              |

### Scope  

This document describes the design details for automatic ssd cleanup on a SONiC switch. The feature is dependent on the monit service to monitor the ssd usage, alert the user on reaching the error threshold and trigger the ssd cleanup script. This document will focus on the cleanup flow and will not cover the whole monit (and healthd) flow.

### Definitions/Abbreviations 

Monit - monitoring service which is used in SONiC to monitor the file system among other resources.

### Overview 

SONiC requires some amount of free disk space to operate correctly. In order to avoid reaching a state where there is no more space left, some preventive measures need to be exercised. Specifically, we would like to alert the user that the disk is getting filled (covered under the current implementaion) and, in the case where the free space has reached a critical level, perform a cleanup operation (the enhancement covered in this document).

### Requirements

Requirements:

1. Vendors set the free space _Warning_ (e.g. < 5 GiB of free space) and _Critical_ (e.g. < 3.5 GiB of free space) thresholds and can their own cleanup targets. If no thresholds are set, the feature will be disabled and the current behavior will remain.
2. In case the disk usage has stably exceeded the _Warning threshold_ – we would alert the user via system health (which include logging, LED and CLI health status).
3.	In case the disk usage has exceeded the _Critical threshold_ – we would perform ssd cleanup to try to bring down the disk usage to under the _Warning threshold_.

Exemptions
1. The feature is not user configurable, as with other monitoring tasks executed by Monit.
2. Cleaning inside docker containers is not supported at this stage.

### Architecture Design 

![System chart](./ssd_cleanup_arch.png "Figure 1: SSD Cleanup Arch")

In SONiC, System health monitors critical services/processes and peripheral device status and leverage system log, system status LED to and CLI command output to indicate the system status. In the current implementation, System health monitor relies on Monit service to monitor the file system and to trigger an alert in case an alert threshold has been stably exceeded.

We will extend the Monit service, in case the disk usage has reached critical level, to execute a cleanup utility.
In addition, to support the init flow, we will also check and perform ssd cleanup on system init.

The health status is visiable via 'show system-health' commands.


### High-Level Design 

![Module chart](./ssd_cleanup_module.png "Figure 1: SSD Cleanup Module Design")

#### Vendor Definitions

We will add a 'SSDCleanupData' property on ChassisBase that return the following information:
_WarningThreshold_ - the free space threshold (in GiB) for Monit to trigger a warning. The default will be align with the current implementation which is 90% of the filesystem size.
_CriticalThershold_ - the free space threshold (in GiB) for Monit to trigger the cleanup script. The default is None to keep the current implementation.
_CleanupTargets_ - a list of (_name_, _directory-path_, _filename-pattern_) tuples, which will be cleaned in order until the _WarningThreshold_ is reached. E.g.
    [
    ("ASIC FW Directory", '/path/to/fw-files/', '.*\.mfa'),
    ("STATS Directory", '/path/to/stats-files/', '.*'),
    ]


#### Utility Scripts
The follwoing scripts will be added to sonic-py-common:

_check_ssd_usage_ - checks if the free-space of the file-system reached the vendor defined _Warning_ or _Critical_ thresholds and output the result in the format that Monit expects.

_ssd_cleanup_ - performs a cleanup on the vendor defined _CleanupTargets_. The target directories will be cleaned in order and the files inside each directories will be cleaned from old to new. If in any point, the _WarningThreshold_ check pass - it will stop the cleanup. This assueres we only remove the minimal number of files needed to return to healthy state.

#### Monit Configuration Update
The current check on 'monit/conf.d/sonic-host' is

    check filesystem root-overlay with path /
        if space usage > 90% for 10 times within 20 cycles then alert repeat every 1 cycles

and will be replaced with

    check program root-overlay with path "/usr/bin/check_ssd_usage"
        # we have passed the warning threshold
        if status == 1 for 10 times within 20 cycles then alert repeat every 1 cycles
        # we have reached critical usage threshold
        if status == 2 then exec "/usr/bin/ssd_cleanup"


#### Database

No change from current implementation, system-health service will populate system health data (including the disk usage, under the root-overlay field) to "SYSTEM_HEALTH_INFO" table in STATE DB.


### SAI API 
NA

### Configuration and management 
None for now, see exemption number 1.

#### Manifest (if the feature is an Application Extension)
NA
		
### Warmboot and Fastboot Design Impact  
No impact.

### Memory Consumption
No impact.

### Restrictions/Limitations  
The script is not guaranteed to bring down the disk-usage to under the alert threshold. It only covers specific areas in the file system.

### Testing Requirements/Design  
1. Check default health state is OK
2. Check filling up space until the warning threshold is reached trigger system-health event (Log error, CLI output)
3. Check filling up space until the critical threshold is reached trigger system-health event and execute the cleanup script
3a. Check cleanup script logic - order of targets (as defined in the Chassis object)
3b. Check cleanup script logic - order of files (from old to new)
3c. Check cleanup script logic - stop when free space is under the warning threshold
3d. Make sure system-health is restored
4. Stress - fill all the file-system until we cannot write into disk (expect errors), make sure cleanup restore the system to healthy state