```mermaid
%Scripts can be rendered online by https://mermaid-js.github.io/mermaid-live-editor/edit
%Deploy flow
sequenceDiagram
    participant User
    participant CLI
    participant minigraph
    participant sonic cfggen
    participant buffer template
    participant DATABASE
    User ->> minigraph: set device type
    loop for each used port
        User ->> minigraph: set speed
        User ->> minigraph: set neighbor device name
        User ->> minigraph: set neighbor device detail
        User ->> minigraph: set other info (not related to buffer)
    end
    User ->>+ CLI: Execute "config load-minigraph"
    CLI ->>+ sonic cfggen: load minigraph
    sonic cfggen ->>+ minigraph: Load minigraph information
    minigraph ->>- sonic cfggen: Return minigraph info
    sonic cfggen ->> DATABASE: Set device type: ToRRouter, LeafRouter, or SpineRouter
    loop for each port
        sonic cfggen ->> DATABASE: Set port admin status to up if port is active
        sonic cfggen ->> DATABASE: Set port speed
        sonic cfggen ->> DATABASE: Set port's cable length according to both ends
    end
    Note over sonic cfggen, buffer template: Collect active ports and inactive ports
    loop for each port
        alt Neithbor is defined for the port
            sonic cfggen ->> buffer template: Add port to ACTIVE PORT set
        else
            rect rgb(255, 0, 255)
                sonic cfggen ->> buffer template: Add port to INACTIVE PORT set
            end
        end
    end
    sonic cfggen ->> sonic cfggen: Determine switch's topology according to its device type
    sonic cfggen ->> buffer template: Load buffer template according to SKU and topo
    buffer template ->> sonic cfggen: Return buffer templates
    Note over sonic cfggen, DATABASE: Generating buffer table items by rendering buffer templates.
    sonic cfggen ->> DATABASE: Generate default buffer pool objects
    sonic cfggen ->> DATABASE: Generate default buffer profile objects
    rect rgb(255, 0, 255)
        opt INACTIVE PORT is not empty
            sonic cfggen ->> DATABASE: Generate default zero buffer profile objects
        end
    end
    loop for each active port
        sonic cfggen ->> DATABASE: Generate BUFFER_QUEUE item for queue 0-2, 3-4, 5-6 for the port
        sonic cfggen ->> DATABASE: Generate BUFFER_PORT_INGRESS_PROFILE_LIST item
        sonic cfggen ->> DATABASE: Generate BUFFER_PORT_EGRESS_PROFILE_LIST item
        Note over sonic cfggen, DATABASE: Generat lossy PGs by rendering the buffer template if NO special script to generate them 
        sonic cfggen ->> DATABASE: Generate lossy BUFFER_PG item PG 0 for the port, using normal ingress lossy buffer profile
    end
    rect rgb(255, 0, 255)
        opt zero profiles exist
            Note over sonic cfggen, DATABASE: Generate items for inactive ports by rendering bufer template if zero profiles exist
            loop for each inactive port
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_QUEUE table for queue 0-7
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_PORT_INGRESS_PROFILE_LIST table
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_PORT_EGRESS_PROFILE_LIST table
                sonic cfggen ->> DATABASE: Generate zero buffer profile item for lossy PG 0 in BUFFER_PG table
            end
        end
    end
    sonic cfggen ->>- CLI: Finish
```

```mermaid
%Normal flow
sequenceDiagram
    participant User
    participant DATABASE
    participant buffer manager
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure cable length and speed or admin-status
    DATABASE ->> buffer manager: Update notification
    alt Handle the case port is admin-down
        rect rgb(255, 0, 255)
            buffer manager ->> DATABASE: Remove lossless buffer PG
        end
    else
        opt cable length or speed is not configured
            buffer manager ->> DATABASE: Finish (need retry)
        end
        opt buffer profile doesn't exist?
            buffer manager ->> buffer manager: Fetch headroom parameter according to cable length/speed
            buffer manager ->> DATABASE: Create buffer profile and push into BUFFER_PROFILE
            DATABASE ->>+ buffer orch: Update notification
            buffer orch ->>+ SAI: sai_buffer_api->create_buffer_profile
            SAI ->>- buffer orch: Finish
            buffer orch ->>- DATABASE: Finish
        end
        buffer manager ->> DATABASE: Create buffer PG and push into BUFFER_PG for PG 3-4
        DATABASE ->>+ buffer orch: Update notification
        loop for PG in [3, 4]
            Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
            Note over buffer orch, SAI: attr.value.oid = OID of corresponding buffer profile;
            buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute
            SAI ->>+ SDK: Set parameters of PG according to buffer profile
            SDK ->>- SAI: Finish
            SAI ->>- buffer orch: Finish
        end
        buffer orch ->>- DATABASE: Finish
    end
```

```mermaid
%Create queue flow

sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure an entry in BUFFER_QUEUE
    DATABASE ->>+ buffer orch: Update notification
    buffer orch ->> buffer orch: Fetch the OID of buffer profile
    loop for queue in list
    Note over buffer orch, SAI: attr.id = SAI_QUEUE_ATTR_BUFFER_PROFILE_ID
    Note over buffer orch, SAI: attr.value.oid = OID of corresponding buffer profile;
    buffer orch ->>+ SAI: sai_queue_api->set_queue_attribute(queue, &attr)
    SAI ->>+ SDK: Set parameters of the queue according to buffer profile
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%Create port profile list flow

sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure an entry in BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST
    DATABASE ->>+ buffer orch: Update notification
    loop for profile in profile_list
    buffer orch ->> buffer orch: Fetch the OID of buffer profile
    buffer orch ->> buffer orch: Insert the OID to oid_list
    end
    loop for queue in list
    alt BUFFER_PORT_INGRESS_PROFILE_LIST
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST
    else BUFFER_PORT_EGRESS_PROFILE_LIST
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST
    end
    Note over buffer orch, SAI: attr.value.oid = oid_list
    buffer orch ->>+ SAI: sai_port_api-->set_port_attribute(port, &attr)
    loop for each OID in oid_list
    SAI ->>+ SDK: Set parameters of the port buffer pool according to buffer profile
    SDK ->>- SAI: Finish
    end
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%Dynamic-port-init
sequenceDiagram
    participant Kernel stack
    participant port manager
    participant ports orchagent
    participant buffer manager
    participant buffer manager internal data
    participant SAI
    participant CONFIG_DB
    participant APPL_DB
    participant STATE_DB
    CONFIG_DB ->> port manager: A port is heard from CONFIG_DB
    loop for each attribute of the port
        port manager ->> Kernel stack: Set corresponding port attributes in kernel netdev
        port manager ->> APPL_DB: Push the attribute into APPL_DB.PORT_TABLE
    end
    APPL_DB ->> ports orchagent: A port is heard from APPL_DB
    ports orchagent ->> ports orchagent: Initialize the port (other steps omitted)
    ports orchagent ->> SAI: query maximum number of queues
    loop for each queue
        ports orchagent ->> ports orchagent: Initialize the queue
    end
    ports orchagent ->> SAI: query maximum number of PGs
    loop for each queue
        ports orchagent ->> ports orchagent: Initialize the queue
    end
    ports orchagent ->> SAI: query maximum headroom size of the port
    ports orchagent ->> STATE_DB: Push maximum numbers into STATE_DB.BUFFER_MAX_PARAM_TABLE
    rect rgb(255, 0, 255)
        STATE_DB ->> buffer manager: Maximum numbers of the port heard
        buffer manager ->> buffer manager internal data: Generate ID maps of all queues and PGs
    end
```

```mermaid
%Dynamic-original-flow
sequenceDiagram
    participant User
    participant CONFIG_DB
    participant buffer manager
    participant APPL_DB
    participant buffer orch
    participant SAI
    participant SDK
    User ->> CONFIG_DB: Shutdown the port
    CONFIG_DB ->> buffer manager: Update notification
    loop for each buffer PG object
        buffer manager ->> APPL_DB: remove the object from APPL_DB
        APPL_DB ->> buffer orch: Update notification
        Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
        Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID
        buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute
        SAI ->>+ SDK: Set the reserved size and headroom size to 0
        SDK ->>- SAI: Finish
        SAI ->>- buffer orch: Finish
    end
```

```mermaid
%Dynamic-new-flow
sequenceDiagram
    participant User
    participant CONFIG_DB
    participant buffer manager
    participant APPL_DB
    User ->> CONFIG_DB: Shutdown the port
    CONFIG_DB ->> buffer manager: Update notification
    rect rgb(255, 0, 255)
        opt zero profiles haven't been inserted to APPL_DB
            buffer manager ->> APPL_DB: Insert zero pools and profiles into APPL_DB
        end
        loop for each buffer PG configured on the port
            alt lossless
                alt support removing PGs
                    buffer manager ->> APPL_DB: Remove the buffer item from BUFFER_PG table
                else
                    buffer manager ->> APPL_DB: Apply zero profile to the PG in BUFFER_PG table
                end
            else
                buffer manager ->> APPL_DB: Apply zero profile to the PG in BUFFER_PG table
            end
        end
        opt (Not all PGs on which zero profile needs to be applied are configured) and (removing PGs is supported)
            loop for each of the rest PGs
                buffer manager ->> APPL_DB: Apply zero profile to the PG in BUFFER_PG table
            end
        end
        loop for each buffer queue configured on the port
            buffer manager ->> APPL_DB: Apply zero profile to the queue in BUFFER_QUEUE table
        end
        opt (Not all queues on which zero profile needs to be applied are configured) and (removing queues is supported)
            loop for each of the rest PGs
                buffer manager ->> APPL_DB: Apply zero profile to the queue in BUFFER_QUEUE table
            end
        end
        buffer manager ->> APPL_DB: Set the profile of the buffer object to the zero buffer profile
        loop For each profile_list in [BUFFER_PORT_INGRESS_PROFILE_LIST, BUFFER_PORT_EGRESS_PROFILE_LIST]
            loop For each profile in profile_list
                buffer manager ->> buffer manager: Fetch the zero profile of the pool referenced by the profile
                buffer manager ->> buffer manager: Add the zero_profile to the list
            end
            buffer manager ->> APPL_DB: Update the profile list
        end
    end
```
