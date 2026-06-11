# SONiC NameLabelMapper Utility 

## Table of Contents
- [Introduction](#introduction)
- [Purpose and Scope](#purpose-and-scope)
- [Architecture and Design](#architecture-and-design)
- [Developer Guide](#developer-guide)
- [Warm Boot Integration](#warm-boot-integration)
- [Best Practices](#best-practices)

## Introduction

The NameLabelMapper is a utility class within the orchagent designed to bridge the gap between human-readable/application-level object keys and fixed-length unique labels required by certain SAI attributes or hardware entries. 

In SONiC, objects are often identified by complex strings (e.g., a combination of table names and entry keys). However, some SAI objects require a unique identifier that is easier to manage, persistent across restarts, and consistent during Warm Boot operations.

## Purpose and Scope

The primary goals of the NameLabelMapper are: 

- **Persistent Mapping :** Maintain a 1:1 mapping between a complex object key and a unique label.
- **Warm Boot Continuity :** Ensure that the same object key retains its original label after an orchagent restart to prevent hardware-software mismatches.
- **Centralized Management :** Provide a unified interface for different Orchestrators (e.g., P4Orch) to handle label allocation.
- **Database Synchronization :** Automatically back up mappings to the STATE_DB to ensure they persist across process crashes or planned reboots.

## Architecture and Design

### Data Storage

Mappings are stored in-memory using an array of hash maps, indexed by the SAI object type. This ensures that lookups are O(1) and namespaced by their functional category.

```
// Internal cache structure
std::unordered_map<std::string, std::string> m_labelTables[SAI_OBJECT_TYPE_MAX]; 
```

### Database Schema

The mapper interacts with the STATE_DB to ensure persistence. 

- **DB Name :** STATE_DB
- **Table Name :** SAI_KEY_LABEL_MAP
- **Key :** OBJECT_TYPE|TABLE_NAME:OBJECT_NAME (e.g., SAI_OBJECT_TYPE_POLICER|POLICER_TABLE:MyPolicer1)
- **Field :** label 
- **Value :** The unique generated string (e.g., a microsecond timestamp).

### Label Generation

Labels are currently generated using high-resolution microsecond timestamps (system_clock). This provides a simple, monotonically increasing unique identifier suitable for most mapping requirements.

## Developer Guide

### Accessing the Mapper
The mapper is instantiated globally in Orchdaemon. To use it in any orchestrator, include the header and reference the global pointer:
```bash
#include "namelabelmapper.h"
extern NameLabelMapper *gLabelMapper; 
```

### Key Functions

| Function | Description |
| -------- | ----------- |
| **`allocateLabel`** | Checks if a label exists for a key. If not, generates and saves a new one. |
| **`addLabelToAttr`** | A helper that allocates a label and automatically populates a sai_attribute_t structure. |
| **`getLabel`** | Simple retrieval of an existing label. Returns false if not found. |
| **`generateKeyFromTableAndObjectName`** | Standardizes key creation by joining a table name and object name with a colon (:). |
| **`saveMapperToDb`** | Forces a synchronization of all in-memory mappings to the STATE_DB. |

### Code Example: Allocating a Label for a Policer

```
std::string label;
std::string mapper_key = gLabelMapper->generateKeyFromTableAndObjectName("APP_POLICER_TABLE", "Policer_A"); 

// Check if label exists, if not, it will be created 
if (!gLabelMapper->allocateLabel(SAI_OBJECT_TYPE_POLICER, mapper_key, label))
{
    SWSS_LOG_NOTICE("New label %s allocated for Policer_A", label.c_str());
}

// Alternatively, use the attribute helper 
sai_attribute_t attr; 
gLabelMapper->addLabelToAttr(SAI_OBJECT_TYPE_POLICER, "APP_POLICER_TABLE", "Policer_A", attr, SAI_POLICER_ATTR_LABEL, mapper_key, label); 
```

## Warm Boot Integration
The NameLabelMapper is a critical component for Warm Boot: 

- **Restoration :** During OrchDaemon::warmRestoreAndSyncUp, readMapperFromDb() is called to reload all previous mappings from STATE_DB into the cache. 
- **Reconciliation :** Orchestrators perform their "bake" and "sync" cycles. By calling getLabel, they retrieve the identifiers used before the reboot, ensuring SAI attribute consistency.
- **Cleanup :** Once reconciliation is finished, deleteMapperInDb() can be called to clear stale entries, followed by a fresh saveMapperToDb() to persist only the active state. 

## Best Practices
- **Consistency :** Always use generateKeyFromTableAndObjectName to avoid manual string concatenation errors.
- **Object Types :** Ensure you use the correct sai_object_type_t to avoid collisions across different types of networking objects. 
- **Memory Management :** The mapper is intended to live for the duration of the orchagent process. Do not manually delete the global instance.
