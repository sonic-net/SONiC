# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for preserving the contents of the CoPP (Sonic Control Plane Policing) tables during reboot for faster LAG creation in order to improve fast-reboot's dataplane downtime.

# Requirements

The following are the high level requirements for preserving CoPP tables contents during reboot.

1. CoPP Tables shouldn't be cleared from APP DB by DB migrator.
2. coppmgr mergeConfig logic should be enhanced to:
    1. Ignore setting existing entries.
    2. Overwrite entry when value differs, use value from default init file merged with user configuration.
    3. Delete entries with keys that are not supported in the copp default initialization (backward compatibility).
    4. In case an entry exists in user's configuration file or in the default json initialization file while missing from the preserved CoPP table it will be add to the table as a new entry.

# Design Proposal

## Current behavior

In the current implementation DB migrator clears CoPP tables contents and it is being initialized with default values at startup. This process takes some time and leads to that LACP are being missed shortly after reboot since LACP trap is not set yet, thus delaying LAG creation and extending dataplane downtime during fast-reboot.

## Proposed behavior

With the new proposal, the CoPP tables contents will be preserved during reboot, i.e. they won't be cleared by DB migrator. Then, initializing CoPP tables in startup phase for any key-value entry it will be checked if such entry exists, in case it does, the entry will be ignored. In case there is an entry with the same key but with different value preserved from prior reboot the existing entry will be deleted and a new entry will be added to the CoPP tables with the key and the new value.
In addition, for backwards compatibility, in case CoPP tables preserve an entry with a key that is not supported (i.e. such key is not present in the json default initialization file) it will be deleted from the CoPP tables during merge.
The solution of deleting old entry and creating a new one instead is proposed since there is no SAI implementation to check for overwrites and this might lead to trying to re-create create-only entries which will cause orchagent crash.

# Flows

## DB migrator copp tables handling logic

The following flow captures the DB migrator proposed functionality.

![](/images/copp/copp_dbmigrator_flow.png)

## coppmgr mergeConfig logic

The following flow captures CoPP manager configuration merge proposed functionality.

![](/images/copp/coppmgr_merge_logic.png)

# Manual tests
1. Perform fast-reboot with value set according to user's configuration (whether it is the same as default values or not) for one of the CoPP tables contents, in the specific case - LACP. Examine that it is being preserved through reboot process including DB migration and preserves the value after coppmgr merge logic without additional set operation.
2. Perform fast-reboot with value that is different from user's configuration (whether user's configuration is same as default value or not) for one of the CoPP tables contents, in the specific case - LACP. Examine that it is being deleted and a new entry is being added to the table instead of it during the coppmgr merge logic.
3. Perform reboot to previous SONiC version that doesn't support one of CoPP entries that were found in the table prior to the reboot. Check that the entry is being preserved through DB migration and being cleared in the coppmgr merge logic.
4. Remove one of CoPP table entries before rebooting and examine that it is missing on startup and being added as a new entry during coppmgr merge.
