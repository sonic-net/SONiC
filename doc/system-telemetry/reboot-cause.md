# Reboot-cause information via telemetry agent

## Revision

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 09/02/20 | Sujin Kang  | Initial version    |

## Scope
-Enable sonic streaming telemetry agent to send Reboot-cause information which is stored in state-db with the reboot-cause processed timestamp.

### Enable sonic streaming telemetry agent to send Reboot-cause information

#### Part 1
During the boot, the `determine-reboot-cause` service ( previously `process-reboot-cause`) determines the last reboot-cause based on the hardware reboot-cause
and the software reboot-cause information and `determine-reboot-cause` service will save the JSON-formatted last previous
reboot cause information to "/host/reboot-cause/history/" with adding timestamp at the end of file name.
`determine-reboot-cause` also will also create a symbolic link of the last reboot cause file to "/host/reboot-cause/previous-reboot-cause.json"

The example shows the previous reboot-cause files stored in /host/reboot-cause/history/.
```
admin@sonic:~$ ls /host/reboot-cause/history/
reboot-cause-2020_10_09_01_56_59.json
reboot-cause-2020_10_09_02_00_53.json
reboot-cause-2020_10_09_02_33_06.json
reboot-cause-2020_10_09_04_53_58.json
...
```

The following example shows the content of the previous reboot-cause file - reboot-cause-2020_10_09_04_53_58.json.
```
admin@sonic:~$ sudo cat /host/reboot-cause/history/reboot-cause-2020_10_09_04_53_58.json
{"comment": "", "gen_time": "2020_10_09_04_53_58", "cause": "warm-reboot", "user": "admin", "time": "Fri Oct  9 04:51:47 UTC 2020"}
```
```
[
    {
        gen_time: "2020_10_09_04_53_58",
        cause: "warm-reboot",
        user: "admin",
        time: "Fri Oct  9 04:51:47 UTC 2020"
        comment: ""
    }
]
```

#### Part 2
A new service named as `process-reboot-cause.service` which will retrieve the saved reboot-cause files and read each reboot-cause information from the files
and save the reboot-cause information up to 10 entries to state-DB.
Verify the information from state-DB data is available via the cli command `show reboot-cause history` which is extended from `show reboot-cause`.

##### Reboot Cause Schema in state-DB

Here is the definition of Reboot-cause schema which will be stored in state-DB.
```
; Defines information for reboot-cause
key                     = REBOOT_CAUSE|<timestamp>         ; last reboot-cause processing time
; field                 = value
cause                   = STRING                         ; last reboot cause
time                    = STRING                         ; time when the last reboot was initiated
user                    = STRING                         ; user who the last reboot initiated
comment                 = STRING                         ; unstructured json format data
```

##### CLI output  and corresponding structure in state-DB for reboot-cause information

###### reboot-cause information

`show reboot-cause` displays the last reboot-cause saved in "/host/reboot-cause/previous-reboot-cause.json".
This will be same as current design but the file will be symbolic-linked to the last saved file with time stamp.
With new design, `show reboot-cause history` will be added to display the previous reboot-cause information up to 10 entries from state-DB.

The example shows the output of `show reboot-cause` which is same as current output and displays only the last reboot-cause.
```
admin@sonic:~$ show reboot-cause
User issued 'warm-reboot' command [User: admin, Time: Fri Oct  9 04:51:47 UTC 2020]
```

And the reboot-cause information is also stored in state-DB as follows.
```
REBOOT_CAUSE|2020_10_09_04_53_58
"cause"
"warm-reboot"
"time"
"Fri Oct  9 04:51:47 UTC 2020"
"user"
"admin"
"comment"
""
```

The example shows the output of `show reboot-cause history` and the previous reboot cause stored in state-DB in addition to the last reboot-cause.
```
admin@sonic:~$ show reboot-cause history
name                 cause        time                          user    comment
-------------------  -----------  ----------------------------  ------  ---------
2020_10_09_04_53_58  warm-reboot  Fri Oct  9 04:51:47 UTC 2020  admin
2020_10_09_02_33_06  reboot       Fri Oct  9 02:29:44 UTC 2020  admin
2020_10_09_02_00_53  fast-reboot  Fri Oct  9 01:58:04 UTC 2020  admin
2020_10_09_01_56_59  reboot       Fri Oct  9 01:53:49 UTC 2020  admin
```
Above output will be stored inside state-DB as follows for the previous reboot-cause in addition to the last reboot-cause
```
admin@sonic:~$ redis-cli -n 6 keys "REBOOT_CAUSE|*"
1) "REBOOT_CAUSE|2020_10_09_04_53_58"
2) "REBOOT_CAUSE|2020_10_09_02_33_06"
3) "REBOOT_CAUSE|2020_10_09_02_00_53"
4) "REBOOT_CAUSE|2020_10_09_01_56_59"

admin@sonic:~$ redis-cli -n 6 hgetall "REBOOT_CAUSE|2020_10_09_04_53_58"
1) "cause"
2) "warm-reboot"
3) "time"
4) "Fri Oct  9 04:51:47 UTC 2020"
5) "user"
6) "admin"
7) "comment"
8) ""

admin@sonic:~$ redis-cli -n 6 hgetall  "REBOOT_CAUSE|2020_10_09_02_33_06"
1) "cause"
2) "reboot"
3) "time"
4) "Fri Oct  9 02:29:44 UTC 2020"
5) "user"
6) "admin"
7) "comment"
8) ""

admin@sonic:~$ redis-cli -n 6 hgetall  "REBOOT_CAUSE|2020_10_09_02_00_53"
1) "cause"
2) "fast-reboot"
3) "time"
4) "Fri Oct  9 01:58:04 UTC 2020"
5) "user"
6) "admin"
7) "comment"
8) ""

admin@sonic:~$ redis-cli -n 6 hgetall  "REBOOT_CAUSE|2020_10_09_01_56_59"
1) "cause"
2) "reboot"
3) "time"
4) "Fri Oct  9 01:53:49 UTC 2020"
5) "user"
6) "admin"
7) "comment"
8) ""

```
