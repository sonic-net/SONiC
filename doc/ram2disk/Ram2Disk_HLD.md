# ram2disk (LogKeeper) Design

## Revision

| Rev | Date | Author | Change Description |
|---|---|---|---|
| 0.1 | 7/29/2026 | Gaurav Nagesh | Initial Version |

## Glossary

| Term | Meaning |
|---|---|
| **EROFS** | Read-only filesystem error |
| **tmpfs** | Temporary File System that is RAM based |
| **rsync** | Remote synchronization utility |

## Scope/Purpose

`/var/log` is currently disk-backed. Frequent log appends, log rotation,
compression, and metadata updates create sustained write activity. Moving
`/var/log` to **tmpfs** reduces disk wear and lowers the likelihood of read-only
filesystem (`EROFS`) issues caused by storage failures or filesystem degradation.

The main drawback of using **tmpfs** is that it is volatile and logs are lost when the
system shuts down, reboots, or loses power. But logs are required for debugging,
post-incident analysis and understanding failures across boot sessions.

We therefore need a service, called **ram2disk** (also known as **LogKeeper**), that:

- Periodically copies logs from the tmpfs-backed `/var/log` to persistent disk in batches
- Performs a final synchronization during an orderly shutdown or reboot
- Restores active logs early during boot so logging can continue across sessions
- Retains previous boot sessions for later analysis
- Minimizes disk writes while preserving the same logical rotation history as
  `/var/log`

Ram2Disk relies on `rsync` utility program for the purpose of backing up logs to disk in a sequential manner in batches.

## Architecture / Design

### Overview

**ram2disk** separates active, frequently written logs from persistent historical
storage as follows:

- `/var/log` is backed by **tmpfs** and is the live source used by logging services
- `/var/log.disk` is the disk-backed destination used to preserve logs.
- Periodic synchronization copies changes from **tmpfs** to disk.

**Example view of system when ram2disk is enabled:**

```bash
admin@sonic:~$ df -h
Filesystem      Size  Used Avail Use% Mounted on
tmpfs           988M  116K  988M   1% /var/log
/dev/loop1      3.9G  3.1M  3.7G   1% /var/log.disk
```

```bash
sudo losetup -l /dev/loop1
NAME       SIZELIMIT OFFSET AUTOCLEAR RO BACK-FILE                   DIO LOG-SEC
/dev/loop1         0      0         1  0 /host/disk-img/var-log.ext4   0     512
```

> **Note:** When `/var/log` is not mounted on **tmpfs**, i.e., it is already
> disk-backed, then this is already the final copy and `/var/log.disk` will not
> exist and work as normal.

### Storage Layout on Disk

```bash
/var/log.disk/
|-- current_session/               # Live mirror of /var/log for this boot
|   |-- syslog
|   |-- syslog.1
|   |-- syslog.2.gz
|   |-- frr/bgpd.log
|   `-- ...
|-- session_<timestamp1>/          # Archived previous boot1
|-- session_<timestamp2>/          # Archived previous boot2
`-- .boot_id
```

- **`current_session/`** is the persistent mirror of the current boot's
  `/var/log`. Its active and rotated files are kept aligned with the tmpfs source
  during periodic synchronization.
- **`session_<timestampN>`** stores an immutable log snapshot from a past completed
  boot. Multiple session directories may be retained for historical analysis.
- **`.boot_id`** records the boot associated with **`current_session/`**. It allows
  **ram2disk** to detect a new boot and is also used to derive the archived session
  timestamp.

### Why Each Boot Needs a Separate Session Directory

Logrotate archive numbering is meaningful only within the current log history. A
new boot starts with a fresh tmpfs-backed `/var/log` and begins creating files such
as:

```bash

Before Reboot / Shutdown :
Logs are in sync between the two

tmpfs /var/log/                                 Disk /var/log.disk/
-----------------                               ----------------
syslog                                           syslog
syslog.1                                         syslog.1
syslog.2.gz                                      syslog.2.gz
...                                              ...
...                                              ...
syslog.100.gz                                    syslog.100.gz



After Reboot / Shutdown :
tmpfs will be initially empty and slowly start to fill up as shown below 


Example1 : sync here will overwrite disk files 
tmpfs /var/log/                                  Disk /var/log.disk/
---------------                                 --------------
syslog                                           syslog
                                                 syslog.1
                                                 syslog.2.gz
                                                 ...
                                                 ...
                                                 syslog.100.gz


Example2 : sync here will overwrite disk files 
tmpfs /var/log/                                  Disk /var/log.disk/
---------------                                 --------------
syslog                                           syslog
syslog.1                                         syslog.1
                                                 syslog.2.gz
                                                 ...
                                                 ...
                                                 syslog.100.gz


Example3 : sync here will overwrite disk files 
tmpfs /var/log/                                  Disk /var/log.disk/
---------------                                 --------------
syslog                                           syslog
syslog.1                                         syslog.1
syslog.2.gz                                      syslog.2.gz
                                                 ...
                                                 ...
                                                 syslog.100.gz

                                          
```

The persistent disk may already contain archives from a much older history,
possibly extending to `syslog.100.gz` or beyond. Reusing the same disk directory
across boots would mix two independent numbering sequences. The new boot's
`syslog.1` and `syslog.2.gz` would not correspond to the old files with those
names, and rotation replay could no longer reliably keep tmpfs and disk aligned.

Copying every historical archive from disk back into tmpfs at boot does not make
sense as it increases boot-time work and mixes historical logs with the new boot's
active rotation sequence.

For these reasons, the previous boot's **`current_session/`** directory is moved to
a separate **`session_<timestamp>/`** directory. Only active logs are restored to
tmpfs. The new boot then starts with a fresh **`current_session/`**, while older
sessions remain available on disk for analysis without interfering with current
log rotation.

### Ram2Disk Modes of Operation

#### Periodic Sync

- Determine rotations since the previous sync.
- Replay equivalent renames in **`current_session/`**
- Run **rsync** from `/var/log/` to **`current_session/`**
- Remove old sessions or archives when disk usage is too high.

#### Boot Restore

- Restore active, non-rotated logs from the previous **`current_session/`** into
  tmpfs.
- Rename the previous **`current_session/`** to a timestamped session directory
  **`session_<timestamp1>/`**
- Create a fresh **`current_session/`** for the new boot.

#### Orderly Pre-shutdown

- Perform one final rotation replay and rsync without cleanup to sync all the logs
  to disk before shutdown

### Need for Rotation Detection and Why Plain rsync Is Not Sufficient

Log files are continuously appended, while logrotate periodically renames and
compresses them:

```bash
syslog       -> syslog.1
syslog.1     -> syslog.2.gz
syslog.2.gz  -> syslog.3.gz
```

**rsync** cannot clearly distinguish these files and end up copying/overwriting
files which are redundant. So, if **ram2disk** runs rsync after this shift without
first applying the same rename operations to the disk copy, rsync sees files at
new paths and may transfer archive contents again.

The central design problem is therefore not only copying changed bytes.
**ram2disk** must know how many rotations occurred between sync runs and replay
those rename operations on the persistent mirror before running rsync.

Now there are two approaches in how **ram2disk** can determines the number of
logrotate cycles that occurred since the previous sync:

- **Approach 1** - detects the rotation count indirectly by comparing archive files
  in tmpfs and on disk
- **Approach 2** - detects the rotation count directly using the logrotate verbose
  option

The approaches differ only in how **ram2disk** determines the number of logrotate
cycles that occurred since the previous sync. Both approaches use the general
architecture, storage layout and lifecycle described above.

### Approach 1: Infer Rotation by Comparing Files

It maintains explicit lists of logs whose rotation behavior is known and uses a
function called **`detect_shift`** to infer how many rotations occurred since the
previous sync.

For each configured rotating log, **`detect_shift`** tests candidate shifts from 1
through 8. For a candidate shift `N`, it compares the sizes of two consecutive
compressed archives:

```bash
tmpfs:  base.(N+2).gz and base.(N+3).gz
disk:   base.2.gz     and base.3.gz
```

If both size and checksum pairs match for two consecutive files, the function
assumes that the disk's former `.2.gz` and `.3.gz` files shifted by `N` positions
in tmpfs. The **`mirror_renames`** function then replays that many rotations in the
persistent **`current_session/`** tree before rsync runs.

Using two consecutive files reduces the chance that unrelated archives with the
same size/checksum produce a false match.

### Approach 2: Record Rotation Events from logrotate

Instead of writing our own algorithm for detecting rotation, Approach 2 obtains the
information directly from logrotate itself. Logrotate with verbose output enabled
(`-v`) will provide all information needed. So, we write a wrapper on top of
logrotate called **`logrotate-warpper.sh`**.

For a normal logrotate invocation, the wrapper:

1. Runs the real logrotate binary with verbose output enabled (`-v`).
2. Captures verbose diagnostics.
3. Parses the `rotating log <base_filename> ...` entries emitted for rotations that
   actually happen.
4. Increments a per-file counter in
   **`/dev/shm/logrotate/rotation_counts`**.
5. Returns the real logrotate exit code and preserves requested verbose or error
   output.

**Example:**

`/dev/shm/logrotate/status`:

```bash
logrotate state -- version 2
"/var/log/syslog" 2026-7-31-3:0:0
"/var/log/dpkg.log" 2026-7-31-3:0:0
"/var/log/auth.log" 2026-7-31-3:0:0
"/var/log/syslog_counter.log" 2026-7-31-3:0:0
"/var/log/apt/term.log" 2026-7-31-3:0:0
"/var/log/frr/bgpd.log" 2026-7-31-3:0:0
"/var/log/apt/history.log" 2026-7-31-3:0:0
"/var/log/telemetry.log" 2026-7-31-3:0:0
"/var/log/alternatives.log" 2026-7-31-3:0:0
"/var/log/swss/sairedis.rec" 2026-7-31-3:0:0
```

`/dev/shm/logrotate/rotation_counts`:

```bash
/var/log/syslog 2
/var/log/auth.log 1
/var/log/frr/bgpd.log 3
/var/log/swss/sairedis.rec 1
```

Counter access is protected with **`flock`**, allowing logrotate and **ram2disk** to
update or consume the counter file without corrupting it.



### Trade-offs between the two approaches


#### Approach 1 

- Does not modify or wrap the system logrotate executable.
  contents from disk.

- ram2disk must manually maintain the list of logs that may rotate. A new or
  renamed logrotate target can be missed until the script is updated.
- Detection duplicates work already performed by logrotate. logrotate knows
  exactly which files it rotated, while this approach reconstructs that event
  afterward.
- Limitation on the maximum number of log rotations detected
- It needs two prior consecutive `.gz` archives. Newly introduced logs or logs
  with shallow retention may not provide enough history for detection.
- Logs with different logrotate policies require separate handling or explicit
  categorization.


#### Approach 2

- Uses logrotate as the source of truth for which files actually rotated.
- Removes the fixed eight-rotation detection limit.
- Naturally supports newly added logrotate targets under `/var/log`

- Requires system integration through a diverted logrotate wrapper. Packaging,
  upgrades, removal, and recovery procedures must preserve `logrotate.real`.
- Depends on the format of logrotate's verbose output. A logrotate upgrade that
  changes the `rotating log ...` diagnostic format could stop event extraction.

Design Decision - Approach 2 is selected. Approach 2 delegates rotation-count detection to the component that performs the
rotation. By forcing logrotate verbose mode internally and recording actual
rotation events, ram2disk receives more accurate input without independently
reconstructing what logrotate already knows. ram2disk remains responsible only for
replaying those known rotations on the disk mirror and synchronizing changed data.



## ram2disk Implementation Details

Files in `ram2disk/`:

| File | Responsibility |
|---|---|
| `logrotate-wrapper.sh` | Producer that detects completed rotations and records per-file counts |
| `logrotate-counter-functions.sh` | Shared counter and locking library used by the producer and consumer |
| `ram2disk.sh` | Consumer that reads rotation counts, replays renames, synchronizes logs, restores logs, and performs cleanup |
| `ram2disk.service` | Runs the periodic `ram2disk.sh sync` operation |
| `ram2disk.timer` | Schedules the periodic service |
| `ram2disk-restore.service` | Runs boot-time restore before rsyslog begins writing |


### Systemd Integration

- `ram2disk.timer` schedules `ram2disk.service` every ten minutes, starting at
  minute 5.
- `ram2disk.service` runs `/usr/local/bin/ram2disk.sh sync` after logrotate and only
  when `/var/log.disk` is mounted.
- `ram2disk-restore.service` runs `/usr/local/bin/ram2disk.sh restore` during boot,
  after the required mounts are available and before `rsyslog.service` and
  `syslog.socket`.

### Producer-Consumer Flow

The implementation uses the following flow:

```bash

PRODUCER :
----------------------------------------

logrotate.timer
        |
        v
logrotate.service
        |
        v
logrotate-wrapper.sh
        |
        | records completed rotations
        v
/dev/shm/logrotate/rotation_counts



CONSUMER :
----------------------------------------

ram2disk.timer
        |
        v
ram2disk.sevice
        |
        v
ram2disk.sh sync ------------------> read and clear counters under flock 
        |                               |
        |                               |  (dev/shm/logrotate/rotation_counts)
        |                               |
        |<------------------------------+                       
        |
        |
        | replay rotations
        | rsync remaining changes from tmpfs
        | 
        v
/var/log.disk/current/

```



`logrotate-wrapper.sh` is the **producer** of rotation-count information.
`ram2disk.sh` is the **consumer**. Both use functions from
`logrotate-counter-functions.sh` so counter updates and consumption follow the
same locking and file-update rules.


### `logrotate-wrapper.sh`: Rotation Count Producer

The wrapper is installed in place of the stock logrotate command by using
`dpkg-divert`. The original executable remains available as `/usr/sbin/logrotate.real`


### Reason for dpkg-divert of the original logrotate binary

I could have avoided renaming and replacing the original from `/usr/sbin/logrotate` to `/usr/sbin/logrotate.real` and using `logrotate-wrapper.sh` as `/usr/sbin/logrotate` by just replacing the executable call in the `logrotate.service` file as shown 

```
ExecStart=/usr/sbin/logrotate --state /dev/shm/logrotate/status /etc/logrotate.conf

to instead using the wrapper directly like this 

ExecStart=/usr/local/bin/logrotate-wrapper.sh --state /dev/shm/logrotate/status /etc/logrotate.conf 
```

Now in this, whenever logrotate.timer would trigger the logroate.service and the wrapper would execute and populate the `/dev/shm/logrotate/rotation_counts` but if for any other purpose, say during troubleshooting we wanted to manually force a logroate, we/a user currently do `logrotate -f /etc/logrotate.conf` and the logrotation will happen but will not be recorded in the `rotation_counts` file and will break the ram2disk syncing mechanism. 

We could document and suggest to use the `logrotate-wrapper.sh` moving forword from now on instead of directly using logrotate but it is difficult to always keep in mind and follow it as well as prevent any other future service/nettasks which might use logrotate directly. So in order to avoid this, no matter how `logrotate` is invoked (directly by a user or any other service/task/script in the future) should populate the `rotation_counts` file and not break ram2disk. Hence the reason for using `dpkg-divert` which will help prevent overwrites to the wrapper during upgrade of logrotate package. 

## Conclusion

Normal log writes occur in tmpfs, persistent writes are batched by
ram2disk, and logrotate's own rotation decisions are reused to keep the disk mirror
aligned. This reduces avoidable archive retransfers, preserves logs across orderly
reboots, retains prior boot sessions for analysis, and minimizes the custom logic
needed to infer rotation behavior.



## Additional Notes

### ram2disk Commands and Examples

The main script accepts three operating modes :
```bash
/usr/local/bin/ram2disk.shram2disk.sh --help
Usage: /usr/local/bin/ram2disk.sh {sync|restore|pre-shutdown}
```

#### 1] Periodic Sync

```bash
/usr/local/bin/ram2disk.sh sync
```

This mode:

1. Reads recorded logrotate counts.
2. Replays those rotations in `/var/log.disk/current/`.
3. Runs rsync from tmpfs to disk.
4. Cleans old sessions or archives if disk usage is above the configured limit.

Example rsync command used by the script:

```bash
rsync -a --inplace --no-whole-file /var/log/ /var/log.disk/current/
```

Important options:

- `-a` preserves the directory tree, timestamps, permissions, ownership, and other
  file attributes.
- `--inplace` updates the destination file directly instead of creating a complete
  temporary replacement file.
- `--no-whole-file` enables rsync's delta-transfer behavior even for a local copy,
  reducing the amount of changed data written to disk.

#### 2] Boot-Time Restore

```bash
/usr/local/bin/ram2disk.sh restore
```

This restores active logs from the previous `current/` directory into tmpfs,
archives the previous boot as `session_<timestamp>/`, creates a new `current/`, and
records the new boot ID. Rotated archives are excluded from the restore.

#### 3] Final Shutdown Sync

```bash
/usr/local/bin/ram2disk.sh pre-shutdown
```

This replays pending rotations and performs a final rsync before shutdown or
reboot. It skips cleanup so shutdown is not delayed by deleting historical data.


#### logrotate Wrapper Example

Callers continue to invoke logrotate normally:

```bash
/usr/sbin/logrotate /etc/logrotate.conf
```

The wrapper internally runs the real binary with verbose detection:

```bash
/usr/sbin/logrotate.real -v /etc/logrotate.conf
```

If the caller explicitly requests debug mode, the wrapper passes it through
without recording rotations:

```bash
/usr/sbin/logrotate --debug /etc/logrotate.conf
```

### Rotation Counter File Example

The wrapper stores one path and accumulated rotation count per line in:

```text
/dev/shm/logrotate/rotation_counts
```

Example:

```text
/var/log/syslog 2
/var/log/auth.log 1
/var/log/frr/bgpd.log 3
/var/log/swss/sairedis.rec 1
```

This means:

- `syslog` rotated twice since the last successful counter consumption.
- `auth.log` rotated once.
- `frr/bgpd.log` rotated three times.
- `swss/sairedis.rec` rotated once.

During the next sync, ram2disk replays the indicated number of rotations for each
path in `/var/log.disk/current_session/` before invoking rsync. The current implementation
then resets the consumed counters to zero.


### Note on rsync internals

ram2disk uses:

```bash
rsync -a --inplace --no-whole-file /var/log/ /var/log.disk/current_session/
```

- **`-a` / `--archive`** recursively copies the directory tree and preserves
  file attributes such as permissions, ownership, and timestamps.
- **`--no-whole-file`** forces rsync's delta-transfer algorithm for this local
  copy so matching destination blocks can be reused and only changed data needs
  to be transferred.
- **`--inplace`** updates the existing destination file directly instead of
  creating a complete temporary replacement, reducing temporary space and
  avoiding writes to unchanged matching regions.
- In normal working, rsync buffers changed data and generally writes
  it in batches of up to **256 KiB**. Actual storage I/O can still vary because
  of partial buffers and the filesystem or block layer.

