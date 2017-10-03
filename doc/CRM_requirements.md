# Critical Resource Monitoring

## Overview
This document captures the SONiC requirements for monitoring critical ASIC resources by polling SAI attributes. At a high level, the following support is expected:
1.	User must be able to query (via CLI/Show command) the current usage/availability of critical resources
2.	System must log WARNING if there are any resources that exceeds a pre-defined threshold value

## Requirement
This section captures a list of CLI requirements for monitoring the Critical Resources. It also requires that appropriate logging must be provided for all these resources if the usage exceeds the threshold. 
1.	User shall be able to query currently used number of IPv4 routes and number of available entries
2.	User shall be able to query currently used number of IPv6 routes and number of available entries
3.	User shall be able to query currently used number of IPv4 Nexthops and number of available entries
4.	User shall be able to query currently used number of IPv6 Nexthops and number of available entries
5.	User shall be able to query currently used number of IPv4 Neighbors and number of available entries
6.	User shall be able to query currently used number of IPv6 Neighbors and number of available entries
7.	User shall be able to query currently used number of Nexthop group member and number of available entries
8.	User shall be able to query currently used number of Nexthop group objects and number of available entries
9.	User shall be able to query currently used number of ACL TCAM and number of available entries
  -	ACL Table 
  -	ACL Group
  -	ACL Entries
  -	ACL Counters/Statistics
  
10.	User shall be able to query currently used number of FDB entries and number of available entries

### Notes
For the ALARM notification, user can specify the threshold values in hysterisis mode. A WARNING shall be raised if the value exceeds an _upper_ threshold and CLEAR when the threshold goes below the configured _lower_ value. 
User must be able to configure the threshold parameters.
1. In percentage OR
2. In actual used count OR
3. In actual free count 

The configured values shall be updated in the CONFIG_DB. The default upper threshold for which there is no user configuration is capped generically as 85%. If the usage exceeds 85% threshold, then a WARNING is logged. The default lower threshold for which there is no user configuration can be capped at 70%. If the usage reduces below 70%, then a CLEAR is logged.  
The SYSLOG Warning message must be in the following format:
 
"<Date/Time> <Device Name> WARNING \<Process name>: THRESHOLD_EXCEEDED for <TH_TYPE> <CR name> <%> Used count \<value> free count \<value>"

"<Date/Time> <Device Name> NOTICE \<Process name>: THRESHOLD_CLEAR for <TH_TYPE> <CR name> <%>  Used count \<value> free count \<value>"

<TH_TYPE> = <TH_PERCENTAGE, TH_USED, TH_FREE> 

The default polling time can be limited to every 5 minutes. These messages must be suppressed after printing for 10 times. 

## Implementation
In regards to CLI command to query the USED and AVAILABLE numbers, SAI provides API to query the current available entries. This means, Orchagent shall keep track of the respective entries that are programmed and implements the logic to calculate the Used/Available entries. 

To poll the counter values from SAI, suggest to follow the same approach as FLEX Counters where syncd can update the values to COUNTER_DB and _critical_resource_monitoring_ process can fetch the information from COUNTER_DB and perform the calculations. This can be further discussed in the Design meeting. 
