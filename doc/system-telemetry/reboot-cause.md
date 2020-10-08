# Reboot-cause information via telemetry agent

## Revision

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 09/02/20 | Sujin Kang  | Initial version    |

## Scope
-Enable sonic streaming telemetry agent to send Reboot-cause information

### Enable sonic streaming telemetry agent to send Reboot-cause information

#### Part 1
During the boot, the process-reboot-cause processes the last reboot-cause based on the hardware reboot-cause
and the software reboot-cause information and creates previous-reboot-cause.txt with the information as it does currently.
In addition to save the history of the previous reboot-cause, `process-reboot-cause` will save the previous
reboot cause information to "/host/reboot-cause/previous-reboot-cause/" with adding timestamp at the end of file name.
And the file will be formatted to be parsed easily.

The example shows the previous reboot-cause files stored in /host/reboot-cause/previous-reboot-cause/.
```
$ls /host/reboot-cause/previous-reboot-cause/
previous-reboot-cause-20200903T232033.txt
previous-reboot-cause-20200902T101105.txt
previous-reboot-cause-20200902T015048.txt
...
```
The following example shows the content of the previous reboot-cause file - previous-reboot-cause-20200903T232033.txt.
```
[
    {
        gen_time: "20200903T232033",
        cause: "reboot",
        user: "admin",
        time: "Thu 03 Sep 2020 11:15:30 PM UTC",
        comment: ""
    }
]
```

#### Part 2
A new service named as `post-process-reboot-cause.service` which will retrieve the saved reboot-cause files and read each reboot-cause information from the files
and save the reboot-cause information up to 10 entries to state-DB.
Verify the information from state-DB data is available via the cli command `show reboot-cause history` which is extended from `show reboot-cause`.

##### Reboot Cause Schema in state-DB

Here is the definition of Reboot-cause schema which will be stored in state-DB.
```
; Defines information for reboot-cause
key                     = REBOOT_CAUSE|<timestamp>         ; last reboot-cause processing time
; field                 = value
cause                   = STRING                         ; last reboot causek
time                    = STRING                         ; time when the last reboot was initiated
user                    = STRING                         ; user who the last reboot initiated
comment                 = STRING                         ; unstructured json format data
```

##### CLI output  and corresponding structure in state-DB for reboot-cause information

###### reboot-cause information

Currently `show reboot-cause` displays the last reboot-cause and performing `cat /host/reboot-cause/previous-reboot-cause.txt` to show the reboot-cause.
This will be same as current design.
With new design, `show reboot-cause history` will be added to display the previous `reboot-cause` up to 10 entries from state-DB.

The example shows the output of `show reboot-cause` which is same as current output and displays only the last reboot-cause.
```
$ show reboot-cause
User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:15:30 PM UTC]
```
Above output will be stored in the previous-reboot-cause.txt file and the reboot-cause information is also stored in state-DB as follows.
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
20200903T232033 reboot              User issued 'reboot' command [User: admin, Time: Thu 03 Sep 2020 11:15:30 PM UTC]
20200902T101105 Unknown             Unknown
20200902T015048 fast-reboot         User issued 'fast-reboot' command [User: admin, Time: Wed 02 Sep 2020 01:48:33 AM UTC]
```
Above output will be stored inside state-DB as follows for the previous reboot-cause in addition to the last reboot-cause
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
