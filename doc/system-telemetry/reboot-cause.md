# Reboot-cause information via telemetry agent

## Revision

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 09/02/20 | Sujin Kang  | Initial version    |

## Scope
-Enable sonic streaming telemetry agent to send Reboot-cause information

### Enable sonic streaming telemetry agent to send Reboot-cause information

##### Part 1 
For 1st part, process-reboot-cause copies the previous-reboot-cause.txt 
to "/host/reboot-cause/previous-reboot-cause/" with adding timestamp 
at the end of file name after processing the reboot-cause.
Currently previous-reboot-cause.txt is plan text format but this file content will be formatized to be parsed easily.
Read each reboot-cause information from saved previous-reboot-cause files
And update reboot-cause information upto 10 entries to state-DB.  

The example shows the previous reboot-cause files stored in /host/reboot-cause/previous-reboot-cause/.
```
$ls /host/reboot-cause/previous-reboot-cause/
previous-reboot-cause-20200903T232033.txt
previous-reboot-cause-20200902T101105.txt
previous-reboot-cause-20200902T015048.txt
```
The following example shows the content of the previous reboot-cause file - previous-reboot-cause-20200903T232033.txt.
```
TIMESTATEMP: "20200903T232033"
CAUSE: "reboot"
USER: "admin"
TIME: "Thu 03 Sep 2020 11:15:30 PM UTC"
COMMENT: "User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:15:30 PM UTC]" 
```

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

Currently `show reboot-cause` displays the last reboot-cause and performing `cat /host/reboot-cause/previous-reboot-cause.txt` to show the reboot-cause. 
With new design, the reboot-cause will be read from state-DB and displayed with new format.
`show reboot-cause history` will be added and displays the previous `reboot-cause` upto 10 entries from state-DB.

The example shows the output of `show reboot-cause` which is same as current output and displays only the last reboot-cause.
```
$ show reboot-cause
User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:15:30 PM UTC]
```
above output will be stored inside state-DB as follows for the reboot-cause information
```
REBOOT_CAUSE|20200903T112033
"cause"  
"reboot"  
"time"  
"Thu 03 Sep 2020 11:15:30 PM UTC"  
"user"  
"admin"  
"comment"  
"User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:15:30 PM UTC]"  
```

The example shows the output of `show reboot-cause history` and the previous reboot cause stored in state-DB in addition to the last reboot-cause.
```
$ show reboot-cause history
TIMESTAMP       REBOOT-CAUSE        Details
20200903T232033 reboot              User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:20:33 PM UTC]
20200902T101105 Unknown             Unknown
20200902T015048 fast-reboot         User issued 'fast-reboot' command [User: admin, Time: Wed 02 Sep 2020 01:48:33 AM UTC]
```
above output will be stored inside state-DB as follows for the previous reboot-cause in addition to the last reboot-cause
```
REBOOT_CAUSE|20200902T101105
"cause"  
"Unknown"  
"time"  
""
"user"  
""
"comment"  
"Unknown"
```
```
REBOOT_CAUSE|20200902T015048
"cause"  
"fast-reboot"  
"time"  
"Wed 02 Sep 2020 01:48:33 AM UTC"  
"user"  
"admin"  
"comment"  
"User issued 'fast-reboot' command [User: admin, Time: Wed 02 Sep 2020 01:48:33 AM UTC]"  
```
