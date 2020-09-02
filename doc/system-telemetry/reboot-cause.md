# Reboot-cause information via telemetry agent

## Revision

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 09/02/20 | Sujin Kang  | Initial version    |

## Scope
-Enable sonic streaming telemetry agent to send Reboot-cause information

### Enable sonic streaming telemetry agent to send Reboot-cause information

##### Part 1 
For 1st part, Daemon code will be added under sonic-buildimage/files/image_config.  A Daemon will start when OS starts. At every 2 min interval it will do following:  
Delete all entries for Reboot-cause information from state db  
Read Reboot-cause information from Reboot-cause history file
Update Reboot-cause information upto 10 entries to state-DB.  

Details of CLI and state-DB given below. 
Cli command to retrieve the Reboot-cause information
```
$ show reboot-cause
```
state-DB schema to store the Reboot-cause information
```
; Defines information for reboot-cause
key                     = REBOOT_CAUSE|timestamp         ; last reboot-cause processing time
; field                 = value
cause                   = STRING                         ; last reboot cause
time                    = STRING                         ; time when the last reboot was initiated
user                    = STRING                         ; user who the last reboot initiated
comment                 = STRING                         ; unstructured json format data
```
Along with data new entry for timestamp will be added up to 10 entries in state_db:  

```
REBOOT_CAUSE|timestamp
```

##### Part 2
Verify that from state-DB data is available via telemetry agent

##### CLI output  and corresponding structure in state-DB for reboot-cause information

###### reboot-cause information

Software User `reboot` cause example :
```
$ show reboot-cause
User issued 'reboot' command [User: admin, Time: Wed 02 Sep 2020 05:48:42 PM UTC]
```
above output will be stored inside state-DB as follows for the reboot-cause information
```
REBOOT_CAUSE|4276  
"cause"  
"reboot"  
"time"  
"Wed 02 Sep 2020 05:48:42 PM UTC"  
"user"  
"admin"  
"comment"  
""  
```
Hardware `Unknown` cause example : 
```
$ show reboot-cause
User issued 'reboot' command [User: admin, Time: Wed 02 Sep 2020 05:48:42 PM UTC]
```
above output will be stored inside state-DB as follows for the reboot-cause information
```
REBOOT_CAUSE|4170  
"cause"  
"Unknown"  
"time"  
""
"user"  
""
"comment"  
"faults reg: 00 00 00 00 00 00 00 00 00 00 00 00 00 00"  
```
