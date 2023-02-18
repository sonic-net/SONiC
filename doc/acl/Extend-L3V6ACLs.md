# Combine L3 ACL and L3V6 ACL Tables on supported platforms

## Introduction to L3 and L3V6 ACL Table Types
SONiC supports different in-built ACL Table types. These ACL table types have pre-defined set of ACL match-fields, ACL actions and bind points. L3 and L3V6 are such in-built ACL Table types. These ACL tables support packet actions like drop, redirect etc. 

L3 ACL Table type supports matching IPv4 fields like Source IPv4 address, Destination IPv4 address etc.
 Similarly, L3V6 ACL Table type supports matching IPv6 fields like Source IPv6 address, Destination IPv6 address etc.

## Problem overview
Currently SONiC creates separate SAI ACL tables for L3 and L3V6 ACLs. In some ASICs, if a user wants both v4 and v6 rules, they would end up using two hardware ACL tables instead of one. This is sub-optimal in ASICs where both v4 and v6 ACLs can be supported using the same hardware ACL table.
 
The proposal is to give the operator an ability to configure  L3 and L3V6 ACLs in the same hardware ACL Table wherever the underlying platform supports it. 

**Note**: SONiC already supports this optimization for MIRROR and MIRRORV6 ACL tables. Only L3 and L3V6 ACL tables have not been optimized so far.


## Table of Contents 
- [Combine L3 ACL and L3V6 ACL Tables on supported platforms](#combine-l3-acl-and-l3v6-acl-tables-on-supported-platforms)
  - [Introduction to L3 and L3V6 ACL Table Types](#introduction-to-l3-and-l3v6-acl-table-types)
  - [Problem overview](#problem-overview)
  - [Table of Contents](#table-of-contents)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Terminology](#terminology)
    - [Overview](#overview)
    - [Requirements](#requirements)
    - [Architecture Design](#architecture-design)
    - [High-Level Design](#high-level-design)
      - [Option-A: Follow the _existing_ optimization for Mirror ACL table](#option-a-follow-the-existing-optimization-for-mirror-acl-table)
        - [Pros](#pros)
        - [Cons](#cons)
      - [Option-B: Include IPv4 match fields in table type L3V6](#option-b-include-ipv4-match-fields-in-table-type-l3v6)
        - [Pros](#pros-1)
        - [Cons](#cons-1)
      - [Option-C: Create a new ACL Table Type L3V4V6](#option-c-create-a-new-acl-table-type-l3v4v6)
        - [Pros and Cons](#pros-and-cons)
      - [Implementation](#implementation)
        - [Orchagent](#orchagent)
        - [STATE\_DB](#state_db)
    - [SAI API](#sai-api)
    - [Configuration and management](#configuration-and-management)
    - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
    - [Restrictions/Limitations](#restrictionslimitations)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test cases](#unit-test-cases)
      - [System Test cases](#system-test-cases)

### Revision  

| Rev | Date     | Author          | Change Description |
|:---:|:--------:|:---------------:|--------------------|
| 0.1 | 18/Feb/23 | Ravindranath (**Marvell**)   | Initial Version.  |

### Scope  


This document provides the high level design in SONiC to combine L3 and L3V6 ACL tables in SAI on supported hardware.

### Terminology



| SONiC User ACL Table Types     | Description |
|---------------|--------------------|
| __L3__ ACL table type | A built-in ACL table type in SONiC that can match __IPv4__ fields along with incoming port and support ACL redirect and packet ACL actions.|
| __L3V6__ ACL  table type | A built-in ACL table type in SONiC that can match __IPv6__ fields along with incoming port  and support redirect and packet ACL actions.|
| __Mirror__ ACL  table type | A built-in ACL table type in SONiC that can match __IPv4__ fields and supports __Mirror__ ACL action. |
| __MirrorV6__ ACL  table type | A built-in ACL table type in SONiC that can match __IPv6__ fields and supports __Mirror__ ACL action. |
| __Custom__ ACL  table types | A recent enhancement where one or more ACL table types can be created by the user specifying the match-field list, action-list and the bindpoint-types list.|


### Overview 

This document describes the orchagent support by which user created L3 ACL table and L3V6 ACL tables are combined into a single SAI/ASIC ACL table on platforms optimized for this feature.

In several ASICs,  IPv4 and IPv6 ACL rules can be supported in the same ACL table. Further, in many hardware, when the hardware tables (TCAMs) are configured to match IPv6 addresses, the hardware can use the same resources to match the corresponding IPv4 packet fields without incurring additional hardware resources. For example, IPv6 Destination address (128b) and IPv4 Destination address (32b) keys can be fit using only 128 bits instead of 128 + 32bits.


<p align=center>
<img src="img/acl-hw-merge.png" alt="Hardware optimization for matching v4 in V6 ACL Table optimization">
</p>


 So in these types of hardware, during ACL table creation, when a v6 match field is added, it is desirable to add the corresponding v4 match field. This does not cost any extra hardware resource and at the same time gives the user the flexibility to create IPv4 ACL rules in these ACL tables.

Note: SAI lacks a mechanism to identify this platform capability and it is left for the NOS to customise the ACL tables based on the platform type.
Refer https://github.com/opencomputeproject/SAI/pull/1408#issue-1126526787

### Requirements

1. Support v6 and v4 ACL rules with a single underlying SAI ACL table.
   * This will be enabled only on platforms needing this optimization.
2. Allow the operator the flexibility to choose when to use this optimization
3. Reduce the amount of changes that the operator must do to their existing ACL configuration to use this optimization.


### Architecture Design 

 ACL Orchagent is enhanced to achieve these requirements. This design is largely similar to the existing optimization done in SONiC for Mirror ACL tables. There are no architecture changes to current SONiC.

### High-Level Design 

The following design options were considered for implementing this solution:
-  **Option-A**: Follow the existing SONiC behavior to combine Mirror ACL table and MirrorV6 ACL table.
-  **Option-B**: Extend the existing L3V6 ACL table type to include v4 fields.
-  **Option-C**: Create a new ACL table type that combines v4 and v6 say L3V4V6.


#### Option-A: Follow the _existing_ optimization for Mirror ACL table

Today, Orchagent already optimizes Mirror and MirrorV6 ACL table creation for platforms that support it. Orchagent does this by using a static compile time check to determine platforms that support v4 and v6 Mirror ACL rules in the same ACL table. On these platforms, when user creates a MirrorV4 (or a MirrorV6) ACL table in the CONFIG_DB, orchagent creates a single SAI ACL Table that has both v4 and v6 match fields. Later, when the user creates another MirrorV6 (or a MirrorV4) ACL table with the same ACL direction in CONFIG_DB, orchagent reuses the previously created SAI ACL table.

The below diagram illustrates the behavior of the optimization in supported platforms when both these ACL tables are created in the same ACL direction, say ingress. 
The user sees two different ACL tables irrespective of the platform. Orchagent, internally enables the optimization based on the platform and this is transparent to the end user. 

<p align=center>
<img src="img/acl-mirror-merge.png" alt="Current Mirror ACL Table optimization">
</p>

##### Pros
- Ease for the operator: the operator does not need to change their ACL configuration based on the platform. The operator configuration remains identical, and orchagent internally does the merging based on the platform type.

##### Cons
However, this mechanism has several disadvantages

- Today, the MirrorV4 and v6 ACL tables are combined based on platform specific checks done at compile time.  These are done using platform names since SAI does not have a mechanism to detect the ASIC capability to combine tables. The flip side of these platform checks is that the platform vendor has to  decide at compile time between these two choices: either always combine or never combine. There is no mechanism to configure this based on the deployments/customers. In some deployments, when the operator has no v6 rules, we would need the optimization disabled so that the hardware TCAM tables width can be reduced. However disabling this optimization would need a new build.

- SONiC cannot support more than one ACL table type of Mirror. If Orchagent has to support multiple mirror ACL tables, then orchagent has to identify which Mirror table is to be combined with which MirrorV6 table. This would need additional inputs from the operator.
  
- With the optimization enabled, the user configuration in CONFIG_DB and the actual ASIC_DB configuration are different. Say the user configures the Mirror ACL table to ports P1 and P2 and MirrorV6 table to port P3 and P4. Orchagent configures the ASIC to bind the combined table to only the ports configured on Mirror ACL table i.e., ports P1 and P2. Ports P3 and P4 do not undergo the ACL table lookup contrary to user's configuration. 
- Similarly, when the user deletes one of the ACL tables, orchagent deletes the combined ACL table from the hardware even though the user expects the other ACL table to still be present and bound to the attached ports.
  

#### Option-B: Include IPv4 match fields in table type L3V6

As explained before, in several ASIC platforms, including v4 matchfields along with v6 matchfields does not cost extra hardware resources. Hence, on these platforms, v4 matchfields will be included in table type L3V6. In the below table, the second column shows the matchfields in current L3V6 ACL table. The third column shows the matchfields that will be added to L3V6 on platforms that needs this optimization.

    /*
     * Type of Tables and Supported Match Types 
     * |----------------------------------------------------|
     * |                      |   Original   | New L3V6 on  |
     * |    Match Type        |   L3V6       | optimized    |
     * |                      |              | platforms    |
     * |----------------------------------------------------|
     * | MATCH_OUTER_VLAN_ID  |      √       |      √       |
     * |----------------------------------------------------|
     * | MATCH_ACL_IP_TYPE    |      √       |      √       |
     * | MATCH_ETHER_TYPE     |              |      √       |
     * |----------------------------------------------------|
     * | MATCH_SRC_IPV6       |      √       |      √       |
     * | MATCH_DST_IPV6       |      √       |      √       |
     * | MATCH_SRC_IP         |              |      √       |
     * | MATCH_DST_IP         |              |      √       |
     * |----------------------------------------------------|
     * | MATCH_ICMPV6_TYPE    |      √       |      √       |
     * | MATCH_ICMPV6_CODE    |      √       |      √       |
     * | MATCH_ICMP_TYPE      |              |      √       |
     * | MATCH_ICMP_CODE      |              |      √       |
     * |----------------------------------------------------|
     * | MATCH_IP_PROTOCOL    |      √       |      √       |
     * | MATCH_NEXT_HEADER    |      √       |      √       |
     * | ---------------------------------------------------|
     * | MATCH_L4_SRC_PORT    |      √       |      √       |
     * | MATCH_L4_DST_PORT    |      √       |      √       |
     * | MATCH_TCP_FLAGS      |      √       |      √       |
     * |----------------------------------------------------|
     */

##### Pros


-  Operator can create multiple L3 and L3V6 ACL tables. This would not be possible if we use option-A.
- Gives the flexibility to the operator to utilize unused space in L3V6 ACL table for L3 ACL rules. 
<p align=right>
<img src="img/acl-merge.png" alt="New L3/L3V6 ACL Table optimization">
</p>

- If there are many v4 rules and many v6 rules, the user can continue to use separate L3 and L3V6 ACL Tables.

<p align=right>
<img src="img/acl-dont-merge.png" alt="New L3/L3V6 ACL Table optimization">
</p>

- No impact on other platforms  
  
##### Cons
- If the operator decides to use the optimization, the operator needs to modify the ACL configuration, i.e., operator must modify the V4 ACL rules that need to be placed in L3V6 ACL table- the rule's ACL Table is renamed to the L3V6 ACL table.

#### Option-C: Create a new ACL Table Type L3V4V6

Create a new built-in table type called L3V4V6 with the following match types:


    /*
     * Supported Match Types in a new table type L3V4V6
     * |-------------------------------------|
     * |                      |              |
     * |    Match Type        |  New L3V4V6  |
     * |                      |              |
     * |-------------------------------------|
     * | MATCH_OUTER_VLAN_ID  |      √       |
     * |-------------------------------------|
     * | MATCH_ACL_IP_TYPE    |      √       |
     * | MATCH_ETHER_TYPE     |      √       |
     * |-------------------------------------|
     * | MATCH_SRC_IPV6       |      √       |
     * | MATCH_DST_IPV6       |      √       |
     * | MATCH_SRC_IP         |      √       |
     * | MATCH_DST_IP         |      √       |
     * |-------------------------------------|
     * | MATCH_ICMPV6_TYPE    |      √       |
     * | MATCH_ICMPV6_CODE    |      √       |
     * | MATCH_ICMP_TYPE      |      √       |
     * | MATCH_ICMP_CODE      |      √       |
     * |-------------------------------------|
     * | MATCH_IP_PROTOCOL    |      √       |
     * | MATCH_NEXT_HEADER    |      √       |
     * | ------------------------------------|
     * | MATCH_L4_SRC_PORT    |      √       |
     * | MATCH_L4_DST_PORT    |      √       |
     * | MATCH_TCP_FLAGS      |      √       |
     * |-------------------------------------|
     */


##### Pros and Cons
All the pros and cons of option-B (extending L3V6 ACL table) applies here as well.
Additionally, option-C has the below cons:
- Need platform checks to determine which platforms can support combined v4 and v6 ACL table.
- Even on platforms that support combined v4 and v6 ACL tables, we need additional checks to identify which platforms are optimized to have v4 and v6 in the same ACL table.

#### Implementation

Based on the above design considerations, option-B is implemented.
Additionally, a new field is added to the ACL capability in STATE_DB to help applications identify the platforms where v4 fields can be matched in L3V6 ACL tables without additional hardware costs.

##### Orchagent

Today, during the initialization of AclOrch, the default built-in ACL table types are created. In this proposal, using platform specific checks, AclOrch identifies platforms where v4 fields can be matched in L3V6 ACL tables without additional hardware costs. On these identified platforms v4 matchfields are supported in L3V6 table.

  ``` aclorch::init() -> initDefaultTableTypes() -> addAclTableType(TABLE_TYPE_L3V6) {```
  
  ```
   
            :
            :
            if ( /* platform optimizes v4 in L3V6Table */) {
              .withMatch(make_shared<AclTableMatch>(SAI_ACL_TABLE_ATTR_FIELD_ETHER_TYPE))
              .withMatch(make_shared<AclTableMatch>(SAI_ACL_TABLE_ATTR_FIELD_SRC_IP))
              .withMatch(make_shared<AclTableMatch>(SAI_ACL_TABLE_ATTR_FIELD_DST_IP))
              .withMatch(make_shared<AclTableMatch>(SAI_ACL_TABLE_ATTR_FIELD_ICMP_TYPE))
              .withMatch(make_shared<AclTableMatch>(SAI_ACL_TABLE_ATTR_FIELD_ICMP_CODE))
            }
            :
            :
    }
  
   ```


##### STATE_DB

A new field called `optimized_V4_in_L3V6` is added to the ACL capability in STATE_DB. This field is set to true by orchagent during AclOrch init on platforms where v4 fields can be matched in L3V6 ACL tables without additional hardware costs. This provides an interface to the operator to identify the platforms where the operator can choose to add IPv4 ACL rules in L3V6 ACL tables. In the future, this field can be used to validate configuration workflows to prevent a user from adding L3 ACL rules to L3V6 ACL table on unsupported platforms.

```
127.0.0.1:6379[6]> hgetall "ACL_STAGE_CAPABILITY_TABLE|INGRESS"
  :
  :
5) "optimized_V4_in_L3V6"
6) "true"


127.0.0.1:6379[6]> hgetall "ACL_STAGE_CAPABILITY_TABLE|EGRESS"
  :
  :
5) "optimized_V4_in_L3V6"
6) "true"
```

### SAI API 

There are no new SAI APIs required for this feature.

### Configuration and management 
No new CLI or datamodel changes are introduced.  
		
### Warmboot and Fastboot Design Impact  
There is no impact on warmboot or fastboot.

### Restrictions/Limitations  
None.

### Testing Requirements/Design  

#### Unit Test cases  
- Verify ACL Capability in STATE_DB on supported platforms.
    - The new field `optimized_V4_in_L3V6` must be true.
- Verify ACL Capability in STATE_DB on non-supported platforms.
    - The new field `optimized_V4_in_L3V6` must be false.
- Create IPv4 ACL rules (match SRC-IP, DST-IP, ICMP Type, ICMP Code, EtherType) on L3V6 ACL table.
  - This MUST pass in supported platforms
  - This should fail with meaningful error messages in non-supported platforms.
- On supported platforms, test full ACL workflow: create V4 and V6 ACL Rules on L3V6 ACL Table type, set packet action, get the ACL rules and counters, delete ACL rules and then delete the ACL table.
  
#### System Test cases
* Modify existing sonic-mgmt(PTF) __test_acl.py__ to test v4 ACL rules using L3V6 ACL table  *on supported platforms*
  * Traffic Testing must pass for v4 and v6
  
