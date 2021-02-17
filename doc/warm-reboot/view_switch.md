# View Switching in ProducerStateTable

### Problem Description
To support warm reboot, 
ProducerStateTable needs to support a feature that producer can create a temporary view for a table, 
into which write operation will not be synced to consumers immediately.
Instead, the producer can explicitly ask to apply the view, 
upon which all the objects in new view will get synced to consumer.

However, the actual operations get passed to consumer should be optimized as best effort, 
so if an object is present in both old view and new view, 
it should not be `del()` and `set()` again.

In order to archieve that, we are going to add two additional APIs: `create_temp_view()` and `apply_temp_view()`,
as well as modifying existing `del()` and `set()` API.

This design is based on the assumption that there is only one producer writing to a specific table. 
If there are multiple producer writing to a same table, the changes that 'secondary' producer write to the table
while 'main' producer was doing view switching might be lost during `apply_temp_view()`.


### Redis Objects and Memory Objects
As a reference, here are the exiting Redis objects corresponding to a certain table:

| Terminology   | Sample Redis Object  |
| ------------- | :-----------------:  |
| TableHash     | ` ROUTE_TABLE:25.78.106.0/27` |
| StateHash     | `_ROUTE_TABLE:25.78.106.0/27` |
| KeySet        | `ROUTE_TABLE_KEY_SET`      |
| DelKeySet     | `ROUTE_TABLE_DEL_SET`      |
| Channel       | `ROUTE_TABLE_CHANNEL`      |

We are not going to create additional Redis object to support the temporary view. 
Instead, an in-memory table `TableDump m_tempViewState` 
that shares a similar structure with TableHash and StateHash will be created to maintain the target state of the temporary view.
Additionally, a flag `bool m_tempViewActive` will indicates whether a temporary view is current being worked on or not.

### Operation Pseudo Code

#### `create_temp_view()`

Simply mark `m_tempViewActive` flag as active and initialize `m_tempViewState`.
```
m_tempViewActive = true;
m_tempViewState.clear(); 
```

#### `set()` and `del()`

When `m_tempViewActive == false`, current behavior of `set()` and `del()` won't be modified.

When `m_tempViewActive == true`, `set()` and `del()` will only modify temporary view content in `m_tempViewState` instead of writing into DB.

`set()`:

```
if (m_tempViewActive)
{
    for (const auto& iv: values)
    {
        m_tempViewState['key'][fvField(iv)] = fvValue(iv);
    }
}
else 
{
    # Current behavior
    SADD KeySet key
    for field, value do
        HSET StateHash:key field value
    end
    PUBLISH Channel
}
```

`del()`:

```
if (m_tempViewActive)
{
    m_tempViewState.erase('key');
}
else 
{
    # Current behavior
    SADD KeySet key
    SADD DelKeySet key
    DEL StateHash:key
    PUBLISH Channel
}
```

#### `apply_temp_view()`

To apply temporary view, there are several steps:
1. Drop all pending operations by clearing KeySet, DelKeySet, and StateHash
2. Dump content of current view
3. Compare current view and target view, generate a minimal set of `set()` and `del()` operations
4. Write to KeySet, DelKeySet, and StateHash accordingly, publish the change to the channel, and unset `m_tempViewActive` flag.

```
# Drop all pending operations first
DEL KeySet
DEL DelKeySet
for key in KEYS StateHash:*
    DEL StateHash:key
end

TableDump tableDump;
dump(tableDump);

std::vector<std::string> keysToSet;
std::vector<std::string> keysToDel;

// For all old objects
for (auto const& [key, fieldValueMap] : tableDump)
{
    // DEL is needed if object does not exist in new state, or any field is not presented in new state
    // SET is almost always needed, unless old state and new state exactly match each other
    //     (All old fields exists in new state, values match, and there is no additional field in new state)
    if (m_tempViewState.find(key) == m_tempViewState.end())         // Key does not exist in new view
    {
        keysToDel.emplace_back(key);
        continue;
    }
    newFieldValueMap = m_tempViewState[key];
    bool needDel = false;
    bool needSet = false;
    for (auto const& [field, value] : fieldValueMap)
    {
        if (newFieldValueMap.find(field) == newFieldValueMap.end()) // Field does not exist in new view
        {
            needDel = true;
            needSet = true;
            break;
        }
        if (newFieldValueMap[field] != value)                       // Field value changed
        {
            needSet = true;
        }
    }
    if (newFieldValueMap.size() > fieldValueMap.size())             // New field added
    {
        needSet = true;
    }
    if (needDel) keysToDel.emplace_back(key);
    if (needSet) keysToSet.emplace_back(key);
    else newFieldValueMap.erase(key);                               // If exactly match, no need to sync new state to StateHash in DB
}

// Generate a flat arg list from m_tempViewState to be written to m_tempViewActive
std::vector<std::string> keyFieldValueStates;
prepareStateHashArgument(keyFieldValueStates, m_tempViewState);

m_tempViewActive = false;
m_tempViewState.clear() 

for key, field, value in keyFieldValueStates do
    HSET StateHash:key field value
end
for key in keysToSet do
    SADD KeySet key
end
for key in keysToDel do
    SADD DelKeySet key
end
PUBLISH Channel
```

#### `pop()` in ConsumerStateTable
As `apply_temp_view()` is translating view switching operation into a set of standard `set()` and `del()` operations,
no change is needed for `pop()` and any other functions in ConsumerStateTable.


### Q&A

#### How about storing temporary view in DB instead?
Storing temporary view in DB has the benefit of allowing a second Producer to continue working on the temporary view when previous Producer accidentally crashed. However, it does introduce additional objects in DB which might be confusing, and implementing the complicate comparing logic is against the expected usage of Redis Lua script. 

As we have the assumption of only one producer working on a table at a certain time and recovery-on-the-spot of a Producer crashing during temp view operation is not a priotized requirement, we believe maintaining temporary view in Producer memory will lead to a sufficient but simpler design.

#### What if two field values are literally different but semantically same? E.g. '10.0.0.1,10.0.0.3' and '10.0.0.3,10.0.0.1' as `nexthop`.
As it is difficult for ProducerStateTable to understand all semantic meaning of different tables, we are counting on applications to ensure that semantic consistency implicts literal consistency. In the given example, `fpmsyncd` will need to sort addresses of next hops before `SET` to ProducerStateTable so that ProducerStateTable will be able to compare the field correctly.

