# Flow charts

```mermaid
%Allocate a New Profile
% allocate-profile.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Lua engine
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Allocate a profile
  Note over System, Buffer Manager: parameter: (speed, length, gearbox-model)
  Buffer Manager -->> Database Service: Check whether there has already been a profile for the (speed, length, gearbox-model) tuple
  alt if there is one existing
  Buffer Manager -->> System: Return the existing profile
  else it's the first time this speed and cable length tuple occurs in the system
  Buffer Manager -->>+ Lua engine: Calculate new headroom size via the well-known formula
  Lua engine -->>- Buffer Manager: Return headroom info
  Buffer Manager -->> Database Service: Insert the profile into APPL_DB.BUFFER_PROFILE
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Create a profile
  Buffer Orch -->>+ SAI: create_buffer_profile
  Buffer Orch -->>- Database Service: Finish
  end
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%Release a profile
%release-profile.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Release a profile
  Note over System, Buffer Manager: parameter: (profile name)
  Buffer Manager ->> Buffer Manager: Check whether the profile is statically configured (derived from CONFIG_DB.BUFFER_PROFILE)
  Buffer Manager ->> Buffer Manager: Check whether the profile is referenced any longer
  opt the profile isn't statically configured nor referenced any longer
  Buffer Manager -->> Database Service: Destroy the entry in the BUFFER_PROFILE table
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Remove a profile
  Buffer Orch -->>+ SAI: remove_buffer_profile
  Buffer Orch -->>- Database Service: Finish
  end
  end
  Buffer Manager -->>- System: Finish
```

```meimaid
%Calculate shared buffer pool size
%calculate-pool-size.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI
  participant Log

  System -->>+ Buffer Manager: Recalculate shared buffer pool size
  loop Iterate all port
  opt Port is admin up
  Buffer Manager ->> Buffer Manager: Accumulate the headroom size of all lossless PGs
  Buffer Manager ->> Buffer Manager: Accumulate the reserved size of all lossy PGs
  Buffer Manager ->> Buffer Manager: Accumulate the reserved size for egress traffic
  end
  end
  loop for each buffer pool
  opt buffer pool needs to be update size dynamically
  Buffer Manager -->> Database Service: Update BUFFER_POOL
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_POOL updated
  Buffer Orch -->>+ SAI: set_buffer_pool_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  Buffer Manager -->> Log: Log the old and new size of the pool in INFO level
  end
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%cable-length-speed-update.png
sequenceDiagram
  participant System
  participant Log
  participant Buffer Manager
  participant Database Service
  participant Lua engine
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: A port's speed or cable length updated
  Note over System, Buffer Manager: parameter (speed, cable length)
  loop for each PG configured on the port
  alt the PG is dynamically calculated
  Buffer Manager ->> Buffer Manager: Allocate new profile or reuse an existing one
  else [the PG is statically configured (headroom override)]
  Buffer Manager ->> Buffer Manager: Use the configured profile
  end
  Buffer Manager -->>+ Lua engine: Check whether headroom exceeds limit
  Lua engine -->>- Buffer Manager: Return result
  opt Headroom exceeds the limit
  Buffer Manager ->> Buffer Manager: Release the newly created profile
  Buffer Manager ->> Buffer Manager: Keep previous data in APPL_DB
  Buffer Manager -->> Log: Error message should be logged
  Buffer Manager -->> System: Process exit due to error
  end
  Buffer Manager -->> Database Service: Update APPL_DB.BUFFER_PG|<port>|<pg> table
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_PG|<port>|lossless_pg updated
  loop For each priority
  Buffer Orch -->> SAI: set_ingress_priority_group_attribute
  end
  Buffer Orch -->>- Database Service: Finish
  end
  end
  Buffer Manager ->> Buffer Manager: Calculate and deploy share buffer
  opt speed or cable length updated
  Buffer Manager ->> Buffer Manager: Check whether the old profile used is referenced by other ports any longer. Remove if no
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%Update static profile:
%static-profile-updated.png
sequenceDiagram
  participant System
  participant Log
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch

  System -->>+ Buffer Manager: Update static profile
  loop for each port who references this profile
  Buffer Manager ->> Buffer Manager: Calculate the accumulative headroom size of the port
  alt headroom exceeds the limit
  Buffer Manager -->> Log: An error message should be logged
  Buffer Manager -->> System: Procedure exit with APPL_DB untouched
  end
  end
  Buffer Manager -->> Database Service: Update corresponding buffer profile in APPL_DB
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Buffer profile updated
  Buffer Orch -->>+ SAI: set_buffer_profile_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  Buffer Manager ->> Buffer Manager: Recalculate the buffer pool size and program ASIC
  Buffer Manager -->>- System: Finish
```
