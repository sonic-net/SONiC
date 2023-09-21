

# README

DASH Flow SAI abstracts the flow state within DASH. In the quest for achieving cloud services, the control plane can generate a flow state table, performing operations such as adding, deleting, modifying, and querying. This specification guarantees alignment between the flow state table and flow states across different cloud providers and vendors. We propose an API to provide a vendor-neutral method for managing flow states, including uniform control of Programmable switches, SmartNICs, and Smart Switches.

DASH Flow SAI accommodates multiple flow tables and diverse flow entry operations. Primarily, it negates differences between vendors' implementations, offering universal interfaces. However, it acknowledges performance variations between DASH and SAI deployed on smart devices. For example, it supplies APIs to handle single and batch flows, with entry count as a limiting factor.

With DASH Flow SAI, it's possible to achieve varied cloud services requiring flow states. For instance, a cloud load balancer can add a flow decision entry and retrieve the flow entry via the data plane. It also lays the groundwork for DASH to provide basic services, such as high availability.



# DASH Flow SAI

| API                                   | Description                                                  |
| ------------------------------------- | :----------------------------------------------------------- |
| sai_dash_flow_create_table            | Create a new flow table                                      |
| sai_dash_flow_remove_table            | Remove a flow table                                          |
| sai_dash_flow_get_table_attribute     | Obtain the attributes of a flow table                        |
| sai_dash_flow_create_entry            | Add single new entry to a certain flow table                 |
| sai_dash_flow_bulk_create_entry       | Add multiple entries to a certain flow table                 |
| sai_dash_flow_remove_entry            | Remove single entry in a certain flow table                  |
| sai_dash_flow_bulk_remove_entry       | Remove multiple entries in a certain flow table              |
| sai_dash_flow_set_entry               | Set single entry in a certain flow table                     |
| sai_dash_flow_get_entry               | Get single entry in a certain flow table                     |
| sai_dash_flow_bulk_get_entry_callback | Request the vendor interate the flow_table and call the callback function |



## Flow state definition

We define the flow state as a hash table as follows:



### SAI protobuf defination

```c
typedef struct _sai_protobuf_t
{
    /* String in protobuf format */
    sai_s8_list_t protobuf;
  
} sai_protobuf_t;
```



### Flow state attribute definiation

```c
typedef enum _sai_flow_table_attr_t {
    /* Start of attributes */
    SAI_FLOW_TABLE_ATTR_START,

    /* ENI for the flow table */
    SAI_FLOW_TABLE_ATTR_ENI,

    /* Size attribute of the flow table */
    SAI_FLOW_TABLE_ATTR_SIZE,

    /* Expiry time attribute for entries in the flow table */
    SAI_FLOW_TABLE_ATTR_EXPIRE_TIME,

    /* Behavior attribute to track TCP states */
    SAI_FLOW_TABLE_ATTR_BEHAVIOR_TRACK_TCP_STATES,
  
    /* Reset a TCP connection if it is illegal */
    SAI_FLOW_TABLE_ATTR_TCP_RESET,

    /* Version of the flow table */
    SAI_FLOW_TABLE_ATTR_VERSION,

    /* Flag to specify how to use the key for the flow table */
    SAI_FLOW_TABLE_ATTR_KEY_FLAG,

    /* End of attributes */
    SAI_FLOW_TABLE_ATTR_END
     
} _sai_flow_table_attr_t;

```

### Flow state definiation



# Flow atrribute 

```c
typedef struct _sai_flow_state_t {
    /* Flow state Key */
    sai_dash_flow_key_t key;
  
    /* Flow state attribute list */
    sai_attribute_t *attr_list;
  
    /* Flow state atrribute count */
    uint32_t attr_count;

} sai_dash_flow_state_t;

```

### Flow state key

```c
/**
 * @brief Flow key for network and transport layer information.
 */
typedef struct _sai_dash_flow_key_t {
    /* @brief Source IP address */
    sai_ip_address_t src_ip;

    /* @brief Destination IP address */
    sai_ip_address_t dst_ip;

    /* @brief IP Protocol (e.g., TCP(6) or UDP(17)) */
    sai_uint8_t ip_protocol;

    /* @brief Transport Layer Information (TCP/UDP/ICMP) */
    sai_dash_ha_flow_l4_info_t l4_info;
} sai_dash_flow_key_t;

/**
 * @brief Union representing L4 flow information for various protocols.
 */
typedef union _sai_dash_ha_flow_l4_info_t {
    /* @brief TCP/UDP information */
    sai_dash_ha_flow_tcp_udp_info_t tcp_udp;

    /* @brief ICMP information */
    sai_dash_ha_flow_icmp_info_t icmp;
} sai_dash_ha_flow_l4_info_t;

/**
 * @brief Structure representing L4 information for TCP and UDP flows.
 */
typedef struct _sai_dash_ha_flow_tcp_udp_info_t {
    /* @brief Source port */
    sai_uint16_t src_port;

    /* @brief Destination port */
    sai_uint16_t dst_port;
} sai_dash_ha_flow_tcp_udp_info_t;

/**
 * @brief Structure representing L4 information for ICMP flows.
 */
typedef struct _sai_dash_ha_flow_icmp_info_t {
    /* @brief ICMP Type */
    sai_uint32_t type;

    /* @brief ICMP code */
    sai_uint32_t code;

    /* @brief ICMP ID */
    sai_uint32_t id;
} sai_dash_ha_flow_icmp_info_t;

```



### Flow state attribute definiation

The content of "attribute" and "protobuf" can be the same, but their usage differs. "Attribute" allows for incremental updates to a single property, while "protobuf" requires a full update.



```C++
typedef enum _sai_flow_state_metadata_attr_t {
    /* Starting marker for attributes */
    SAI_FLOW_ATTR_START,

    /* Version of the policy for this flow. Type: [uint32_t] */
    SAI_FLOW_STATE_ATTR_VERSION,

    /* Metadata of the policy results in protobuf format. Type: [sai_protobuf_t] */
    SAI_FLOW_STATE_ATTR_METADATA_PROTOBUF,

    /* Indicates if the flow entry is bi-directional. Type: [sai_uint8_t] Default: True (1) */
    SAI_FLOW_STATE_ATTR_BIDIRECTIONAL,
    
    /* Direction of the flow entry. Type: [sai_uint8_t] */
    SAI_FLOW_STATE_ATTR_DIRECTION,

    /* For single directional entries, this represents the key of the reverse direction. Type: [sai_dash_flow_key_t] */
    SAI_FLOW_STATE_ATTR_REVERSE_DIRECTION_KEY,
  
    /* Result of the policy. Type: [sai_dash_policy_result_t] */
    SAI_FLOW_METADATA_ATTR_POLICY_RESULT,

    /* Destination Protocol Address. Type: [sai_ip_address_t] */
    SAI_FLOW_METADATA_ATTR_DEST_PA,

    /* ID for metering class. Type: [sai_uint64_t] */
    SAI_FLOW_METADATA_ATTR_METERING_CLASS,

    /* Information required for rewriting. Type: [sai_dash_rewrite_info_t] */
    SAI_FLOW_METADATA_ATTR_REWRITE_INFO,

    /* Vendor-specific metadata details. Type: [sai_u8_list_t] */
    SAI_FLOW_METADATA_ATTR_VENDOR_METADATA,

    /* Ending marker for attributes */
    SAI_FLOW_METADATA_ATTR_END

} sai_flow_metadata_attr_t;

```



### Flow state protobuf definiation

```protobuf
syntax = "proto3";

message SaiDashFlowMetadata {
    uint32 version = 1;
    SaiDashPolicyResult policy_result = 2;
    /* Destination PA IP address */
    string dest_pa = 3; 
    uint64 metering_class = 4;
    SaiDashHaRewriteInfo rewrite_info = 5;
    /* Vendor specific metadata */
    bytes vendor_metadata = 6; 
}

enum SaiDashPolicyResult {
    SAI_DASH_HA_POLICY_RESULT_NONE = 0;
    SAI_DASH_HA_POLICY_RESULT_ALLOW = 1;
    SAI_DASH_HA_POLICY_RESULT_DENY = 2;
}

enum SaiDashHaRewriteFlags {
    SAI_DASH_HA_REWRITE_NONE = 0; /* Default, unused value */
    SAI_DASH_HA_REWRITE_IFLOW_DMAC = 1;
    SAI_DASH_HA_REWRITE_IFLOW_SIP = 2;
    SAI_DASH_HA_REWRITE_IFLOW_SPORT = 4;
    SAI_DASH_HA_REWRITE_IFLOW_VNI = 8;
    SAI_DASH_HA_REWRITE_RFLOW_SIP = 16;
    SAI_DASH_HA_REWRITE_RFLOW_DIP = 32;
    SAI_DASH_HA_REWRITE_RFLOW_DPORT = 64;
    SAI_DASH_HA_REWRITE_RFLOW_SPORT = 128;
    SAI_DASH_HA_REWRITE_RFLOW_VNI = 256;
}

message SaiDashHaRewriteInfo {
    /* Bitmap of SaiDashHaRewriteFlags */
    uint64 rewrite_flags = 1; 
    /* Initiator Flow DMAC */
    string iflow_dmac = 2; 
    /* Initiator Flow Source IP address */
    string iflow_sip = 3; 
    /* Initiator Flow L4 Source Port */
    uint32 iflow_sport = 4; 
    /* Initiator Flow VNID */
    uint32 iflow_vni = 5; 
    /* Reverse Flow Source IP address */
    string rflow_sip = 6; 
    /* Reverse Flow Destination IP address */
    string rflow_dip = 7; 
    /* Reverse Flow Destination Port */
    uint32 rflow_dport = 8;
    /* Reverse Flow Source Port */
    uint32 rflow_sport = 9; 
    /* Reverse Flow VNID */
    uint32 rflow_vni = 10; 
}
```



### Flow state query type

```c++
typedef enum _sai_flow_state_query_type_t{
    SAI_FLOW_TABLE_ENTRY_QUERY_SRCIP,
    SAI_FLOW_TABLE_ENTRY_QUERY_SRCPORT,
    SAI_FLOW_TABLE_ENTRY_QUERY_DSTIP,
    SAI_FLOW_TABLE_ENTRY_QUERY_DSTPORT,
    SAI_FLOW_TABLE_ENTRY_QUERY_PROTO,
    SAI_FLOW_TABLE_ENTRY_QUERY_ALL,
    SAI_FLOW_TABLE_ENTRY_QUERY_ALL_AGED,
    SAI_FLOW_TABLE_ENTRY_QUERY_VERSION_LESS_THAN,
    SAI_FLOW_TABLE_ENTRY_QUERY_VERSION_LESS_THAN_OR_EQUAL_TO,
    SAI_FLOW_TABLE_ENTRY_QUERY_VERSION_EQUAL_TO,
    SAI_FLOW_TABLE_ENTRY_QUERY_VERSION_GREATER_THAN,
    SAI_FLOW_TABLE_ENTRY_QUERY_VERSION_GREATER_THAN_OR_EQUAL_TO
} sai_flow_state_query_type_t;
```



## Usage of DASH Flow SAI APIs 

### sai_dash_flow_create_table

> - **Decription**: Create a new flow table
>   - **Usage**: `sai_dash_flow_create_table(flow_table_id, attr_count, attr_list)`
> - **Input**: 
>   - `uint32_t attr_count`: number of attributes
>   - `sai_attribute_t *attr_list`: array of attributes
> - **Output**:
>   - `sai_object_id_t *flow_table_id`: flow table id allocated by the vendor  
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_remove_table 

> - **Decription**: Remove a flow table
> - **Usage**: `sai_dash_flow_remove_table(flow_table_id)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id to be removed
> - **Output**: none
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_get_table_attribute

> - **Decription**: Obtain the attributes of a flow table
> - **Usage**: `sai_dash_flow_get_table_count(flow_table_id, attr_count, attr_list)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id
>   - `uint32_t attr_count`: number of attributes
> - **Output**: 
> - **Input and Output**:
>   - `sai_attribute_t *attr_list`: attr_list Array of attributes
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_create_entry

> - **Decription**: Add single new entry to a certain flow table
> - **Usage**: `sai_dash_flow_create_entry(flow_table_id, flow_key, attr_count, attr_list)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id 
>   - `const sai_dash_flow_key_t *flow_key` key of the flow
>   - `uint32_t attr_count`: number of attributes
>   - `sai_attribute_t *attr_list`: attr_list Array of attributes
> - **Output**: none
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_bulk_create_entry

> - **Decription**: Add single new entry to a certain flow table
> - **Usage**: `sai_dash_flow_bulk_create_entry(flow_table_id, flow_count, flow_key[], attr_count[], *attr_list[], mode, *object_statuses)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id 
>   - `uint32_t flow_count`: count of entries
>   - `const sai_dash_flow_key_t flow_key[]` key of the flow
>   - `uint32_t attr_count[]`: number of attributes
>   - `sai_attribute_t *attr_list[]`: array of attributes
>   - `sai_bulk_op_error_mode_t mode`: bulk operation error handling mode.
> - **Output**: 
>   - `sai_status_t *object_statuses`: object_statuses List of status for every object. Caller needs to allocate the buffer.
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_remove_entry 

> - **Decription**: Remove single entry in a certain flow table
> - **Usage**: `sai_dash_flow_remove_entry(flow_table_id, flow_key)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id 
>   - `const sai_dash_flow_key_t *flow_key` key of the flow
> - **Output**: none
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_set_entry 

> - **Decription**: Set single entry in a certain flow table
> - **Usage**: `sai_dash_flow_set_entry(flow_table_id, flow_key, attr_count, attr_list)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id 
>   - `const sai_dash_flow_key_t *flow_key` key of the flow
>   - `uint32_t *attr_count`: number of attributes
>   - `sai_attribute_t *attr_list`: attr_list Array of attributes
> - **Output**: None
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_get_entry

> - **Decription**: Get single entry in a certain flow table
> - **Usage**: `sai_dash_flow_get_entry(flow_table_id, flow_key, attr_count, attr_list)`
> - **Input**: 
>   - `sai_object_id_t flow_table_id`: flow table id 
>   - `const sai_dash_flow_key_t *flow_key` key of the flow
>   - `uint32_t *attr_count`: number of attributes
> - **Output: ** None
> - **Input and Output**: 
>   - `sai_attribute_t *attr_list`: attr_list Array of attributes
> - **Return**: 
>   - `sai_status_t`: status code



### sai_dash_flow_bulk_get_entry_callback 

> - **Decription**: Request the vendor interate the flow_table and call the callback function.
> - **Usage**: `sai_dash_flow_bulk_get_entry_callback(flow_table_id, flow_key, query_type, attr_count, attr_list, callback_function, timeout, finish)`
> - **Input**: 
>  - `sai_object_id_t flow_table_id`:  flow table id 
>   - `const sai_dash_flow_key_t *flow_key` key of the flow
>   - `const sai_flow_state_query_type_t type`: the type of queried flow state
>   - `uint32_t *attr_count`: number of attributes
> - `sai_attribute_t *attr_list`: attr_list Array of attributes
>   - `void *callback_function`: the function to callback when interate the flow table
>   - `callback_function(flow_table_id, flow_key[], attr_count[], attr_list[])`
>     - **Input**: none
>     - **Output**:
>       - `sai_object_id_t flow_table_id`:  flow table id 
>       - `const sai_dash_flow_key_t *flow_key[]`
>       - `uint32_t *attr_count[]`: number of attributes
>       - `sai_attribute_t *attr_list[]`: attr_list Array of attributes
>     - **Return**: none
>   - `int timeout`: the timeout expires
> - **Output**:
>
>   -  `int *finish`: indicate if the bulk get is done
> - **Return**: 
>
>   - `sai_status_t`: status code



#  Example 

When a service intends to use DASH Flow SAI, it should first establish a flow table via the `sai_dash_flow_create_table()` function. After the table creation, the programmer can add, delete, modify, or retrieve flow entries to/from the table. For instance, when DASH HA needs to perform bulk sync from the active DPU to the standby DPU, it should initially fetch the entry from the active DPU using `sai_dash_flow_bulk_get_entry()`, then transmit the flow entries to the standby DPU via the control plane. The standby DPU subsequently calls `sai_dash_flow_bulk_create_entry()`to add entries to the corresponding flow table. The DPU should have a built-in flow table aging capability, eliminating the need to scan all entries. 

This example describes how to create a flow state table, and how to operate flow entries.



## Flow Entry

#### Create Key

```c
/* Initialize a sai_dash_flow_key_t structure */
sai_dash_flow_key_t flow_key;

/* For this example, let's assume the following IP address structures for simplicity */
typedef struct {
    char address[16];  /* Assuming IPv4 string format */
} sai_ip_address_t;

/* Initialize and set properties for the flow key */

/* Source IP */
strncpy(flow_key.src_ip.address, "10.0.0.1", sizeof(flow_key.src_ip.address));

/* Destination IP */
strncpy(flow_key.dst_ip.address, "192.168.1.1", sizeof(flow_key.dst_ip.address));

/* IP Protocol - TCP */
flow_key.ip_protocol = 6; /* TCP */

/* L4 Information - Assuming TCP flow */
flow_key.l4_info.tcp_udp.src_port = 12345;
flow_key.l4_info.tcp_udp.dst_port = 80;
```

#### Create attribute

```c
/* Initialize the SAI_FLOW_STATE_ATTR_METADATA_PROTOBUF attribute */
SaiDashFlowMetadata flow_metadata = SAI_DASH_FLOW_METADATA__INIT;

/* Set properties for the flow metadata */
flow_metadata.version = 1;
flow_metadata.policy_result = SAI_DASH_POLICY_RESULT__SAI_DASH_HA_POLICY_RESULT_ALLOW;
flow_metadata.dest_pa = "192.168.1.1";
flow_metadata.metering_class = 1001;

/* Initialize and set properties for the rewrite info */
SaiDashHaRewriteInfo rewrite_info = SAI_DASH_HA_REWRITE_INFO__INIT;
rewrite_info.rewrite_flags = SAI_DASH_HA_REWRITE_FLAGS__SAI_DASH_HA_REWRITE_IFLOW_DMAC |
                             SAI_DASH_HA_REWRITE_FLAGS__SAI_DASH_HA_REWRITE_IFLOW_SIP;
rewrite_info.iflow_dmac = "AA:BB:CC:DD:EE:FF";
rewrite_info.iflow_sip = "10.0.0.1";
rewrite_info.iflow_sport = 12345;
rewrite_info.iflow_vni = 1002;

/* Assign the rewrite info to the flow metadata */
flow_metadata.rewrite_info = &rewrite_info;

/* Serialize the protobuf message to bytes */
unsigned len = sai_dash_flow_metadata__get_packed_size(&flow_metadata);
uint8_t *buf = malloc(len);
sai_dash_flow_metadata__pack(&flow_metadata, buf);

sai_attribute_t sai_attrs_list[1];
sai_attrs_list[0].id = SAI_FLOW_STATE_ATTR_METADATA_PROTOBUF;
sai_attr_list[0].value = buf;

## 2.Length

/* Use the buffer as desired, e.g., as an attribute */
/* ... */

/* Free the allocated buffer */
free(buf);

```



## Flow Table Operation

#### Create Flow Table

```c
/* Attributes for the flow table */
uint32_t attr_count = ...; // Specify the number of attributes
sai_attribute_t *attr_list = ...; // Provide the specific array of attributes

/* Create a new flow table */
sai_status_t status = sai_dash_flow_create_table(&flow_table_id, attr_count, attr_list);
if (status != SAI_STATUS_SUCCESS) {
    /* handle the error */
}
```

#### Add Flow Entries

```c
/* Add multiple flow entries to the table in bulk */
uint32_t flow_count = num_flow_states;
const sai_dash_flow_key_t flow_key[] = ...; // Provide the specific array of flow keys
uint32_t attr_count[] = ...; // Specify the number of attributes for each flow
sai_attribute_t *attr_list[] = ...; // Provide the specific arrays of attributes for each flow
sai_status_t object_statuses[] = ...; // Buffer to store statuses for each flow

status = sai_dash_flow_bulk_create_entry(flow_table_id, flow_count, flow_key, attr_count, attr_list, SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR, object_statuses);
if (status != SAI_STATUS_SUCCESS) {
    /* handle error */
}

```

#### Retrieve Flow Entries

```c
/* Retrieve multiple flow entries and call the callback function to further process */
/* Define the callback function */
void process_flow_state(sai_object_id_t flow_table_id, const sai_dash_flow_key_t* key[], uint32_t* attr_count[], sai_attribute_t* attr_list[]) {
    for (uint32_t i = 0; i < attr_count[i]; i++) {
        /* Process each flow entry in the list... */
    }
}

/* Retrieve the flow entries from the table using the specified keys */
status = sai_dash_flow_bulk_get_entry_callback(flow_table_id, &key, SAI_FLOW_TABLE_ENTRY_QUERY_ALL, &attr_count, &attr_list, process_flow_state, 3 * aging_time, &finish);
if (status != SAI_STATUS_SUCCESS) {
    /* handle error */
}
/* The callback function process_flow_state will be invoked for each key in flow_keys */

while (!finish) {
  /* The bulk get is ongoing */
  sleep(1);
}
/* The bulk get is done */

```

#### Remove flow entry

```c
/* Remove the flow entry from the table */
status = sai_dash_flow_remove_entry(flow_table_id, &example_flow_state.key);
if (status != SAI_STATUS_SUCCESS) {
    /* handle error */
}

```

#### Remove flow table

```c
/* Finally, remove the flow table */
status = sai_dash_flow_remove_table(flow_table_id);
if (status != SAI_STATUS_SUCCESS) {
    /* handle error */
}
```





