# Generic SAI Extension Critical Resource Monitoring (CRM)

## Table of Content
- [Introduction](#Itroduction)
- [Scope](#Scope)
- [Requirements](#Requirements)
- [Highlevel Design](#Highlevel-Design)
- [Unit Test Automation](#Unit-Test-Automation)

## Revision
| Rev  |   Date    |                        Author                        | Change Description                 |
| :--: | :-------: | :--------------------------------------------------: | :--------------------------------: |
| 0.1  | 1/17/2023 | Intel                                                |  Initial Revision                  |

## Introduction <a name="Introduction"></a>
High Level Design for critical resource monitoring (crm) in SONiC for Generic SAI Extension tables.

## Scope <a name="Scope"></a>
The scope of the design is to publish CRM counts, for Generic SAI Extension tables, into the COUNTERS-DB. Support for existing generic crm configurations that is applicable to all resources, like polling interval, is in the scope of this document. No additional configuration specific to extension tables resource is in the scope.

## Requirements <a name="Requirements"></a>
- Support reporting of used counts
- Support reporting of available counts
- Support default watermark checks

## Highlevel Design <a name="Highlevel-Design"></a>
New crm resource type enum - CrmResourceType::CRM_EXT_TABLE
  - Each extension table specific stats are stored in,
    m_resourcesMap.at(CrmResourceType::CRM_EXT_TABLE).countersMap[EXT_TABLE_STATS:"table-name"]

All existing generic crm configuration, like polling-interval, is applicable to this new crm type.

Currently supported default watermark check for other existing crm resource types is also applicable to every extension table under this new crm type.


### API to retrieve available counts
sai_object_type_get_availability() is an existing SAI API used to query any resource specific availability count. The same API is to be used to query generic SAI extension table resource availability as well. API call is to have following object-type and attributes as parameters,

  - object-type    : SAI_OBJECT_TYPE_GENERIC_PROGRAMMABLE
  - attribute-id   : SAI_GENERIC_PROGRAMMABLE_ATTR_OBJECT_NAME

respective data-plane implementing this API should return resource count available for the corresponding extension table matching the generic programmable object name

### APIs for used counter book-keeping
- CrmOrch::incCrmExtTableUsedCounter()
- CrmOrch::decCrmExtTableUsedCounter()

P4Orch extension table manager is responsible to call APIs when a specific entry for extension table is successfully created or removed.

### Example of CRM counts of extension table o/p in redis
Example o/p for VIPV4_TABLE with max capacity of 1024

```text
127.0.0.1:6379[2]> KEYS *EXT_TABLE_STATS*
 1) "CRM:EXT_TABLE_STATS:EXT_VIPV4_TABLE"

127.0.0.1:6379[2]> HGETALL "CRM:EXT_TABLE_STATS:EXT_VIPV4_TABLE"
1) "crm_stats_extension_table_used"
2) "1"
3) "crm_stats_extension_table_available"
4) "1023"
```

## Unit Test Automation <a name="Unit-Test-Automation"></a>
P4Orch pytest automation
- Enhance current viplb generic sai extension test automation to insert validation for crm
  - after viplb table entry is programmed, get crm used counters
  - validate used counter has value 1 since 1 viplb entry is programmed
  - after viplb table entry is removed, get crm used counters
  - validate used counter has value 0 since there are no more any entries in viplb table
