# 1. Scope
This document describes the high-level design for orchagent in handling SAI failures


# 2. Failure Handling Framework
### 2.1 Requirements for failure handling functions in orchagent
1. Allow different handling for Create/Set/Remove operations.
1. Allow each Orch to have its specific handling logic.
1. Adapt handling logic based on SAI API type and SAI status.
1. Escalate the failure to upper layers when the failure cannot be handled in orchagent.

### 2.2 An overview of the failure handling framework
An illustrative figure of the failure handling framework is shown below.
The orchagent generates SAI calls according to the information in APPL_DB given by upper layer.
In the case of SAI failures, the orchagent gets the failure status via the feedback mechanism in synchronous mode.
Based on the failure information, the failure handling functions in orchagent make the first attempt to address the failure.
An ERROR_DB is also introduced to suppport escalation to upper layers.
In the scenario where orchagent is unable to resolve the problem, the failure handling functions would escalate the failure to upper layers by pushing the failure into the ERROR_DB.
<img src="Framework.png">

### 2.3 Failure handling functions in Orchagent
#### 2.3.1 Failure handling functions
To support a failure handling logic in general while also allow each orch to have its specific logic, we include the following virtual functions in Orch
1. `virtual bool handleSaiCreateStatus(sai_api_t api, sai_status_t status, void *context = nullptr)`
2. `virtual bool handleSaiSetStatus(sai_api_t api, sai_status_t status, void *context = nullptr)`
3. `virtual bool handleSaiRemoveStatus(sai_api_t api, sai_status_t status, void *context = nullptr)`

The three functions handle SAI failures in create, set, and remove operations, respectively.
With the type of SAI API and SAI status as an input, the function could handle the failure according to the two information.

In the scenario where a specific logic is required in one of the Orchs, this design allows the Orch to inherit the function and include the specific login in the inherited function.

The function also allows an optional input `context`, which allow to pass context (e.g., object entry, attribute, etc.) into the function so that it could escalate the information to the ERROR_DB and upper layers.

#### 2.3.2 Possible execution results
1. Return True --  No crash, no retry

The failure handling function should return true when the failed SAI call does not require a retry after executing the funciton.
This behavior should happen in two scenraios:
    
* The failure is properly handled without need for another attempt (e.g., the SAI status is `SAI_STATUS_ITEM_NOT_FOUND` in remove operation).

* The failure is unable to be handled in orchagent and another attempt is not likely to resolve the failure. In such scenario, the funciton should prevent orchagent from retrying and escalate the failure to upper layers.

2. Return False --  No crash, retry

The failure handling function should return true when the failed SAI call may be resolved in a subsequent attempt.

3. exit(EXIT_FAILURE) -- Crash and trigger SwSS auto-restart

Some of the failures can be resolved by restarting SwSS.
In the scenario where such failures happens, the failure handling function in orchagent should exit with `EXIT_FAILURE` and trigger SwSS auto restart.



### 2.4 DB changes
An ERROR_DB will be introduced to escalate the failures from orchagent to upper layers such as fpmsyncd.

The schema of ERROR_DB is designed as follows: `is a counter needed?`
```
ERROR_{{SAI_API}}_TABLE|entry
    "opcode": {{method}}
    "status": {{sai_status}}
    {{attr1}}: {{value1}}
    {{attr2}}: {{value2}}
    ...
```

The tables in ERROR_DB correspond to the SAI API type (e.g., ERROR_ROUTE_TABLE, ERROR_NEIGH_TABLE, etc.), and the key of each entry corresponds to the entry of SAI failure.

The field `opcode` indicates the method that failed. 
Possible values include `CREATE/SET/DELETE`.

The field `status` saves the status of the SAI operation (e.g., SAI_STATUS_NOT_SUPPORTED, SAI_STATUS_FAILURE).

The ERROR_DB also include a list of attributes and the corresponding values that the failed operation tries to set.
  
An example ERROR_DB entry for route table and neighbor table in BGP error handling is available at https://github.com/Azure/SONiC/blob/master/doc/error-handling/error_handling_design_spec.md#3431-Error-Tables
```
ERROR_ROUTE_TABLE|prefix
    "opcode": {{method}}
    "nexthop": {{list_of_nexthops}}
    "intf": ifindex ? PORT_TABLE.key
    "status": {{return_code}}
```

```
ERROR_NEIGH_TABLE|INTF_TABLE.name/ VLAN_INTF_TABLE.name / LAG_INTF_TABLE.name|prefix
    "opcode": {{method}}
    "neigh": {{mac_address}}
    "family": {{ip_address_family}}
    "status": {{return_code}}
```

# 3. Failure handling logic in orchagent
### 3.1 Failure status that could be handled in orchagent
| SAI status | Create | Set | Remove |
|-----|-----|-----|-----|
| ITEM ALREADY EXISTS           | `Set the  corresponding attribute instead?` | Should not happen. No retry. | Should not happen. No retry. |
| ITEM NOT FOUND                | Should not happen. No retry. | `Create the item and set attribute?` | No retry. 
| OBJECT IN USE                 | Should not happen. No retry. | Retry for a few times | Retry for a few times |

<!-- | SAI status | Create | Set | Remove |
|-----|-----|-----|-----|
| FAILURE                       | | | |
| NOT SUPPORTED                 | | | |
| NO MEMORY                     | Escalate, no retry. | Escalate, no retry. | Escalate, no retry. |
| INSUFFICIENT RESOURCES        | Escalate, no retry. | Escalate, no retry. | Escalate, no retry. |
| INVALID PARAMETER             | Escalate, no retry. | Escalate, no retry. | Should not happen. Escalate, no retry. |
| ITEM ALREADY EXISTS           | `Set the attribute instead?` | Should not happen. Escalate, no retry. | Should not happen. Escalate, no retry. |
| ITEM NOT FOUND                | Should not happen. Escalate, no retry. | `Create the item instead?` | No retry. |
| BUFFER OVERFLOW               | | | |
| INVALID PORT NUMBER           | | | |
| INVALID PORT MEMBER           | | | |
| INVALID VLAN ID               | | | |
| UNINITIALIZED                 | | | |
| TABLE FULL                    | | | |
| MANDATORY ATTRIBUTE MISSING   | | | |
| NOT IMPLEMENTED               | | | |
| ADDR NOT FOUND                | | | |
| OBJECT IN USE                 | Should not happen. Escalate, no retry. | Retry for a few times | Retry for a few times |
| INVALID OBJECT ID             | | | |
| Others                        | Escalate, no retry. |  Escalate, no retry. | Escalate, no retry. | -->



### 3.2 SAI API specific handling logic
TODO: Add SAI API specific handling logic


### 3.3 Orch specific handling logic
TODO: Add Orch specific handling logic
