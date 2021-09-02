# Feature Name
Timezone and System Clock Configuration in Management Framework

# High Level Design Document

#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 07/10/2021 |   Bing Sun         | Initial version                   |
| 0.2 | 07/19/2021 |   Bing Sun         | address review comments to add timezone offset in the logs |
| 0.3 | 08/26/2021 |   Bing Sun         | add section for timestamp in CLI/REST output |
      


# About this Manual

This document describes configuration of timezone and system clock using the management framework.    
It also discusses the mechanisms to keep timezone consistent across the host and containers.     

# Scope

This document covers the following,     
1. "configuration" and "show" commands for timezone based on the OpenConfig YANG model    
2. mechanisms to keep timezone consistent across the host and containers    
3. "configuration" and "show" commands for timezone based on the SONiC YANG model    
4. Daylight Saving Time (DST)    
5. timezone from DHCP option      
6. include timezone information in the timestamp      
7. system clock configuration       
 
# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| DST                      | Daylight Saving Time                |
| local time               | The time that is applicable for the device per timezone at which the device is located |
| NTP                      | Network Time Protocol               |
      
# 1 Feature Overview
**Timezone**   
    
Device maintains two kinds of times, "Universal time" and "local time". The system time is always kept in UTC and converted in applications to local time as needed. "Univeral time" (or "UTC time") is either set by NTP if configured, or by manually configured time and date. "local time" is the adjusted time based on timezone configuration. Without timezone configured, "local time" is the same as the "Universal time".
      
By default, the system time is set to UTC (Coordinated Universal Time) time. When a specific timezone is configured, it is used by the device to convert the system time (UTC) to local time.    
This feature provides the capability to set a specific timezone from the tzdata package (https://www.iana.org/time-zones). The list of standard timezones are specified at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones.
    
After a specific timezone is configured, SONiC host and the containers will use the new timezone and updated local time for log timestamps. And the timestamp should include UTC offset. The UTC offset should change for a timezone observing DST when DST starts and ends.    
    
The tzdata package includes timezone information, changeover dates for daylight savings and summer time. It is updated periodically to reflect changes to timezone boundaries, UTC offsets, and daylight-saving rules. Using tzdata, "local time" is adjusted automatically whee summer-time starts and ends. There is no need of an extra command for handling the DST.             
    
With Management Framework, timezone can be set and queried based on Openconfig YANG model as well as  SONiC YANG model.  
      
**optional items**   
     
1. DHCP timezone offset and name options   
SONiC already request DHCP timezone offset in the existing code. Though backend is not handling it.    
In addtion, DHCP server can specify the timezone name that the systems should be using as specified in [RFC4833]. E-SONiC does not request this option as of now from the DHCP servers.    
Either option may force the clients to use the same timezone.    
    
2. System clock    
This feature also provides the capability to configure the system clock time and date.
Note that if the system is synchronized with a NTP server, the manually enterred time will be overriden eventually.
The new time and date should be consistent on the host and containers.
    
## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities

#### 1.1.1.1 add/delete timezone 
```
clock timezone US/Hawaii
```
Add/delete timezone in the Redis CONFIG DB. Only one timezone can be configured.    

#### 1.1.1.2 Get timezone 
```
show clock timezone
```
Get the local timezone information from timedatectl output. For example,      

    ```
    sonic# show clock timezone
      US/Pacific (PDT, -0700)
    ```    

    ```
    root@sonic:~# timedatectl
          Local time: Thu 2021-07-22 21:32:59 PDT
      Universal time: Fri 2021-07-23 04:32:59 UTC
            RTC time: Fri 2021-07-23 04:32:59
           Time zone: US/Pacific (PDT, -0700)
    ```
    
### 1.1.2 Backend mechanisms to support timezone/clock configuration and query 

#### 1.1.2.1 add/delete timezone 
This creates or deletes the CLOCK entry in the Redis ConfigDB.

```
   "CLOCK": {
        "system": {
            "timezone_name": "US/Hawaii"
        }
    }
```

A change in the CLOCK entry triggers hostcfgd to start the CLOCK configuration script which ensures the timezone and timestamp to be consistent across host and various containers.   
         
For the host:   
         
1. change the local timezone on the host via command "timedatectl set-timezone <new_timezone>"  
   "local time" is now modified by linking the file /etc/localtime to the /usr/share/zoneinfo/<timezone_name> directory.      
2. retart rsyslog to apply the updated time via command "systemctl restart rsyslog.service"    
        
For the containers:     
1. Create a script in each container to handle    
    - symbolic link /etc/localtime to the corresponding timezone under /usr/share/zoneinfo/    
    - restart rsyslog service    
   hostcfgd will trigger this script in each container upon detecting database timezone change.    

2. For the logs not based on syslog, special handling needs to be applied.    
       
   For example in mgmt-framework container, rest_server.log is based on glog.   
         
   The transformer function needs to listen for CLOCK CONFIG DB change and updates the local timezone for glog.   
       
   And glog.go will have a patch to process the local timezone.       
    
   Below is an example of updated timestamp in the logs. The UTC offset is the difference in hours and minutes from UTC for a specific timezone. Note that the UTC offset for the same timezone will be different depending on if DST is active.      
   ```
   Jul 20 00:00:30.251175-07:00 2021     
   ...
   Nov 18 00:06:14.025528-08:00 2021  

   ```

### 1.1.3 Timestamp conversion    
When no timezone is configured, all timestamps use UTC time or epoch ticks. When a timezone is configured, timestamps displayed in the frontend have to be in the correct local time based on timezone configuration.    
There are 3 types of timestamps in the OPENCONFIG YANG:    
1. timestamp is of type string in the OPENCONFIG YANG and in the database, it is in the form of "%Y-%M-%D %h:%m:%s"    
   We need to make sure that timestamp shown in the frontend is in the correct local time, for both CLI and REST.    
   An example of this case is the timestamp in "/oc-if:interfaces/oc-if:interface/oc-eth:ethernet/oc-intf-ext:reason-events/oc-intf-ext:reason-event/oc-intf-ext:state/oc-intf-ext:timestamp".    
   In the APPL_DB "IF_REASON_TABLE", it is seen as "timestamp":"2021-08-27 14:22:24". The same format would be displayed in the CLI and REST.    
         
2. timestamp is of type date-and-time (RFC3339 format) in the OPENCONFIG YANG and in the database, it is in the form of "%Y%M%D %h:%m:%s"    
   We need to make sure that timestamp shown in the frontend is in correct local time, for both CLI and REST.    
   An example of this case is the timestamp in the "openconfig-platform:components/component/state/temperature/timestamp".       
   In the STATE_DB "TEMPERATURE_INFO" TABLE, it is seen as "timestamp":"20210827 06:20:56". The same format would be displayed in the CLI and REST.
        
   For case 1 and case 2, backend timestamp in the database will be kept as UTC based. For example, timestamps in "IF_REASON_TABLE" talbe and "TEMPERATURE_INFO" table may use UTC time, and the transformer functions will convert the UTC time to local time when send the response or notification to the frontend.
    
```
admin@sonic:~$ date
Thu 26 Aug 2021 04:15:10 AM PDT

sonic#show platform temperature
TH - Threshold
-------------------------------------------------------------------------------------------------------------------------------------------------------------
Name Temperature High TH Low TH Critical High TH Critical Low TH Warning Timestamp
-------------------------------------------------------------------------------------------------------------------------------------------------------------
ASIC On-board 35 75 0 80 N/A false 20210826 04:15:21
CPU On-board 29 68 0 72 N/A false 20210826 04:15:21
Inlet Airflow Sensor 24 62 0 65 N/A false 20210826 04:15:23
PSU1 Airflow Sensor 26 65 0 70 N/A false 20210826 04:15:24
PSU2 Airflow Sensor 25 65 0 70 N/A false 20210826 04:15:24
System Front Left 24 65 0 72 N/A false 20210826 04:15:22
System Front Middle 30 75 0 80 N/A false 20210826 04:15:23
System Front Right 24 65 0 72 N/A false 20210826 04:15:23
```
             
3. timestamp is of type timetick64 in the OPENCONFIG YANG and in the backend, it is epoch (ticks)    
   We need to make sure the timestamp shown in the CLI is converted to the correct local time based on the timezone, and  it is shown as epoch ticks in the REST.    
   An example of this case is the timestamp in the "openconfig-system-ext:core-file-records/core-file-record/timestamp".    
   In the backend, it has the form of "timestamp": "1630035254326013". The same will be shown in the REST output. In the CLI, it is converted to the local time based on the timezone.  
``` 
   sonic# show core list    
        TIME               PID    SIG COREFILE EXE    
   2021-08-26 20:34:14    13514   6   present  orchagent    
    
   admin@sonic:~$ date    
   Thu 26 Aug 2021 08:53:10 PM PDT    
```           
     
### 1.1.4 Functional Requirements

Provide management framework support to          
- configure timezone     
- query timezone     
- configure time and date    
- query time and date     
    
### 1.1.5 Configuration and Management Requirements
- CLI style configuration and show commands    
- REST API support    
- gNMI Support    
           
### 1.1.6 Configurations not supported by this feature using management framework:
- support configuration of timezone abbreviations with offset to UTC        
- support get timezone from dhcp option           
           
### 1.1.7 Scalability Requirements
No specific scalability requirement for this feature.

### 1.1.8 Warm Boot Requirements
Configured timezone should survive warm boot. No specific handling is required.    
    
## 1.2 Design Overview

### 1.2.1 Basic Approach
Implement timezone configuration using transformer in sonic-mgmt-framework.             

### 1.2.2 Container
The front end code changes in the management-framework container includes:  
     
**Timezone:**    
    
- XML file for the CLI    
- Python script to handle CLI request (actioner)    
- Jinja template to render CLI output (renderer)    
- front-end code to support "show running-configuration"    
- OpenConfig YANG model in openconfig-system.yang to set and get configured timezone in the configDB    
- OpenConfig RPC YANG model to get timezone from timedatectl output, including UTC offset    
- SONiC clock model in sonic-system-clock.yang to set and get configured timezone in the configDB       
       
**time and date**   
     
Details to be added.      
      
### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure timezone via gNMI, REST and CLI interfaces.    
Manage/configure time&date via gNMI, REST and CLI interfaces.    
           
## 2.2 Functional Description
Provide CLI, gNMI and REST supports for timezone related configurations.
            
## 2.3 Backend change to support new configurations
**timezone**       
     
- transformer functions to    
   * set "system" as key for CLOCK table in CONFIG DB   
   * rpc function to get output of timedatectl for OpenConfig YANG    
   * subscribe to listen for CLOCK change in CONFIG DB    
   * set local timezone for glog   
- customer cvl validation function to reject timezone if the timezone name does not exist under /usr/share/zoneinfo. This is for the case when timezone configuration is done from SONiC YANG.     
- glog patch to handle local timezone change for the timestamp    
- SONiC click CLI enhancement if possible.         
    
# 3 Design
    
## 3.1 Overview    
Suppport timezone and time&date configuration in Management Framework.    
    
## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow users to make CLOCK change in CONFIG DB, and to get CLOCK configuration.

```
   "CLOCK": {
        "system": {
            "timezone_name": "US/Hawaii"
        }
    }
```
    
### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models

YANG models needed for timezone handling in the management framework:
1. **openconfig-system.yang**    
    
3. **sonic-system-clock.yang**    
     
Supported yang objects and attributes:    
    
```diff
+ module: openconfig-system.yang

+     +--rw system
      ...
+         +--rw clock
+         |  +--rw config
+         |  |  +--rw timezone-name?   timezone-name-type
+         |  +--ro state
+         |     +--ro timezone-name?   timezone-name-type
```

```diff
+  module: openconfig-system-private.yang

+  rpcs:
+    +---x get-timezone
+       +--ro output
+          +--ro utc-offset?      string
+          +--ro timezone-abbr?   string
```

```diff
+    module: sonic-system-clock
+      +--rw sonic-system-clock
+         +--rw CLOCK
+            +--rw CLOCK_LIST* [systemclock_key]
+               +--rw systemclock_key    enumeration
+               +--rw timezone_name?     string

```

### 3.6.2 CLI


#### 3.6.2.1 Configuration Commands

##### 3.6.2.1.1 Configure Timezone    

All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#

sonic(config)# clock?
    clock  Configure clock

sonic(config)# clock
  timezone  Configure timezone

sonic(config)# clock timezone ?
  Africa/             Africa timezones
  America/            America timezones
  Antarctica/         Antarctica timezones
  Arctic/             Arctic timezones
  Asia/               Asia timezones
  Atlantic/           Atlantic timezones
  Australia/          Australia timezones
  Brazil/             Brazil timezones
  Canada/             Canada timezones
  CET                 CET timezone
  Chile/              Chile timezones
  CST6CDT             CST6CDT timezone
  Cuba                Cuba timezone
  EET                 EET timezone
  Egypt               Egypt timezone
  Eire                Eire timezone
  EST                 EST timezone
  EST5EDT             EST5EDT timezone
  Etc/                Etc timezones
  Europe/             Europe timezones
  GB                  GB timezone
  GB-Eire             GB-Eire timezone
  GMT                 GMT timezone
  GMT+0               GMT+0 timezone
  GMT-0               GMT-0 timezone
  GMT0                GMT0 timezone
  Greenwich           Greenwich timezone
  Hongkong            Hongkong timezone
  HST                 HST timezone
  Iceland             Iceland timezone
  Indian/             Indian timezones
  Iran                Iran timezone
  Israel              Israel timezone
  Jamaica             Jamaica timezone
  Japan               Japan timezone
  Kwajalein           Kwajalein timezone
  Libya               Libya timezone
  MET                 MET timezone
  Mexico/             Mexico timezones
  MST                 MST timezone
  MST7MDT             MST7MDT timezone
  Navajo              Navajo timezone
  NZ                  NZ timezone
  NZ-CHAT             NZ-CHAT timezone
  Pacific/            Pacific timezones
  Poland              Poland timezone
  Portugal            Portugal timezone
  PRC                 PRC timezone
  PST8PDT             PST8PDT timezone
  ROC                 ROC timezone
  ROK                 ROK timezone
  Singapore           Singapore timezone
  Turkey              Turkey timezone
  UCT                 UCT timezone
  Universal           Universal timezone
  US/                 US timezones
  UTC                 UTC timezone
  W-SU                W-SU timezone
  WET                 WET timezone
  Zulu                Zulu timezone

sonic(config)# clock timezone US/Hawaii
sonic(config)#

```

##### 3.6.2.1.2 Delete Timezone 
```
sonic(config)#no clock timezone
sonic(config)#

```

##### 3.6.2.1.3 Set time and date 

```
sonic# clock
  set  Set the system date and time

sonic# clock set
  String  Enter the current time in <HH:MM:SS> format

sonic# clock set 10:20:55
  String  Enter the date in <YYYY-MM-DD> format

sonic# clock set 10:20:55 2021-07-12

```

#### 3.6.2.2 Show commands

##### 3.6.2.2.1 show timezone
```
sonic# show clock
  timezone  Show the system clock timezone
  <cr>

sonic# show clock timezone
 US/Hawaii (HST, -1000)

``` 

##### 3.6.2.2.2 Show time and date 
```
sonic# show clock
Wed 01 Sep 2021 03:02:06 PM JST
```
    
##### 3.6.2.2.4 Show running-configuration

```
sonic# show running-configuration | grep timezone
clock timezone US/Hawaii

```
    
#### 3.6.2.3 Debug Commands
```
From CLI:

show clock 

```

```
From shell:

timedatectl

ls -l /etc/localtime
ls -l /etc/timezone

zdump -v /etc/localtime | grep 2021

date
```

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing timezone configuration information from CONFIG DB.
PUT  - Create timezone configuration into CONFIG DB.
POST - Add timezone configuration into CONFIG DB.
PATCH - Update existing timezone configuraiton CONFIG DB.
DELETE - Delete existing timezone configuration from CONFIG DB.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support
Configured timezone should survive warm boot. No specific handling is required.
    
# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### Configuration via CLI
**timezone**    
    
| Test Name | Test Description |
| :-------- | :----- |
| Configure timezone | Verify CLOCK is installed correctly in the CONFIG DB, verify host and containers have the new timezone, and new logs are using the updated time |
| Delete timezone | Verify CLOCK is deleted from the CONFIG DB, verify host and containers use UTC, and new logs are using the updated time  |
| show timezone | Verify timezone, UTC offset and timezone abbrevation is displayed correctly based on if DST is active|
| timezones with DST   | Verify that DST changes automatically when the time reaches summer-time start or end |
| timezones without DST | Verify that no DST changes happen | 
       
**time and date**
       
Details to be added    

#### Configuration via gNMI

Same as CLI configuration test but using gNMI request.
Additional tests will be done to set timezone at different levels of YANG models.

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done at different levels of YANG models.

#### Configuration via REST (POST/PUT/PATCH)

Same as CLI configuration test but using REST POST/PUT/PATCH request.
Additional tests will be done at different levels of YANG models.


#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done at different levels of YANG models.


# 10 Internal Design Information
