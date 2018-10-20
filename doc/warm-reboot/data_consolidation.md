# Data Consolidation in ProducerStateTable

### Problem Description
To support warm reboot, 
ProducerStateTable needs to support two additional APIs: `start_sync()` and `finish_sync()` operation. 

When `finish_sync()` is called, the database state should be synchornize the state only according to `set()` and `del()` operation called
in between `start_sync()` and `finish_sync()`, and not related to the previous state before `start_sync()` is called.

- However, the actual operations get passed to consumer should be optimized as best effort, so if an object was already present before `start_sync()`, 
we should not `del()` it and `set()` again.

- During the time span in between `start_sync()` and `finish_sync()`, we allow the database to be in a transient state. 

This design is based on the assumption that there is only one producer writing to a specific table. 


### Redis Objects
To implement this feature we are going to reuse the exiting Redis objects:

| Terminology   | Sample Redis Object  |
| ------------- | :-----------------:  |
| TableHash     | ` ROUTE_TABLE:25.78.106.0/27` |
| StateHash     | `_ROUTE_TABLE:25.78.106.0/27` |
| KeySet        | `ROUTE_TABLE_KEY_SET`      |
| DelKeySet     | `ROUTE_TABLE_DEL_SET`      |
| Channel       | `ROUTE_TABLE_CHANNEL`      |

Additionally, we are going to create a global `STRING` object `DATA_CONSOLIDATION_IN_PROGRESS` as a flag indicating the consolidation progress.

### Solution Outline
The basic idea is to let ProducerStateTable keep track of target state during the sync process,
and calculate the diff between old state and target state to generate a minimal set of `set()` and `del()` message to ConsumerStateTable when `finish_sync()` is called.

`StateHash` will be used to maintain target state. 
As we don't want `StateHash` to be modified by ConsumerStateTable when data consolidation is in progress, we make sure nothing will be added to `KeySet` or `DelKeySet` during the process.

### Operation Pseudo Code

#### `set()`

Current behavior:
```
SADD KeySet key
for attribute, value do
    HSET StateHash:key attibute value
end
PUBLISH Channel
```

Updated behavior:
```
if DATA_CONSOLIDATION_IN_PROGRESS != '1'
    SADD KeySet key
end
for field, value do
    HSET StateHash:key field value
end
if DATA_CONSOLIDATION_IN_PROGRESS != '1'
    PUBLISH Channel
end
```

#### `del()`

Current behavior:
```
SADD KeySet key
SADD DelKeySet key
DEL StateHash:key
PUBLISH Channel
```

Updated behavior:
```
if DATA_CONSOLIDATION_IN_PROGRESS != '1'
    SADD KeySet key
    SADD DelKeySet key
end
DEL StateHash:key
if DATA_CONSOLIDATION_IN_PROGRESS != '1'
    PUBLISH Channel
end
```

#### `start_sync()`
```
SET DATA_CONSOLIDATION_IN_PROGRESS '1'
# Drop all existing pending operations, to make sure StateHash marks target state
DEL KeySet
DEL DelKeySet
for key in KEYS StateHash:*
    DEL StateHash:key
end
```

#### `finish_sync()`
```
# For all old objects:
for key in KEYS TableHash:*
    length_old = HLEN TableHash:key
    length_new = HLEN StateHash:key
    
    # DEL is needed if object does not exist in new state, or any field is not presented in new state
    # SET is almost always needed, unless old state and new state exactly match each other
    #     (All old fields exists in new state, values match, and there is no additional field in new state)
    if length_old > length_new
        need_del = 1
        need_set = 1
    else
        {fields, values} = HGETALL TableHash:key
        need_del = 0
        need_set = 0
        for field, value
            new_value = HGET StateHash:key field
            if new_value == nil
                need_del = 1
                need_set = 1
                break
            if new_value != value
                need_set = 1
            end
        end
        if length_old != length_new
            need_set = 1
        end
    end
    
    if need_del == 1
       SADD DelKeySet key
    end
    if need_set == 1
       SADD KeySet key
    end
end

DEL DATA_CONSOLIDATION_IN_PROGRESS
PUBLISH Channel
```


#### `pop()` in ConsumerStateTable
As `finish_sync()` is translating data consolidation request into a minimal set of `set()` and `del()` operations that has the same contract with normal operations,
no change is needed for `pop()` and any other functions in ConsumerStateTable.
