# xcvrd CPO Support #

## Table of Content 

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1. Unit Test cases](#131-unit-test-cases)
  - [13.2. System Test cases](#132-system-test-cases)
- [14. Open/Action items - if any](#14-openaction-items---if-any)

### 1. Revision  
| Rev |     Date     |       Author       | Change Description                                                               |
|:---:|:------------:|:------------------:|----------------------------------------------------------------------------------|
| 0.1 |  07/02/2026  |  Brian Gallagher   | Initial version                                                                  |

### 2. Scope  

The scope of this HLD is to define how `xcvrd` will use the CPO platform API objects introduced in the [Port Mapping for CPO Platforms](https://github.com/sonic-net/SONiC/pull/2211) HLD. This includes:
- DOM telemetry (DomInfoUpdateTask)
- CMIS state machine management (CmisManagerTask)
- Transceiver presence management (SfpStateUpdateTask)

### 3. Definitions/Abbreviations 

| Term | Definition |
|------|------------|
| CMIS | Common Management Interface Specification |
| CPO | Co-packaged Optics |
| OE | Optical Engine |
| ELSFP | External Laser Small Factor Pluggable |
| DOM | Digital Optical Monitoring |

### 4. Overview 

This HLD covers:
- the changes required to refactor `xcvrd` to support the usage of platform APIs that are not traditional SfpBase-derived objects while maximizing code re-use
- how CPO support for DOM telemetry, CMIS state machine management and physical port device presence management will be added to `xcvrd`

### 5. Requirements

This section list out all the requirements for the HLD coverage and exemptions (not supported) if any for this design.

### 6. Architecture Design 

This HLD does not propose any architectural changes to SONiC.

### 7. High-Level Design 

The primary problem posed by the `xcvrd` integration with CPO platform APIs is that they are not guaranteed to
expose the same interface that traditional SfpBase-derived objects do, which makes code re-use difficult.
This HLD proposes to solve this problem by committing to the following shared interfaces:
- CPO objects inherit from DeviceBase, so hardware interaction like presence detection is a common interface between SfpBase and CPO objects.
- CPO objects will expose a CmisApi, so any CMIS related logic can leverage the API instance to interact with the hardware irrespective of whether it is a SfpBase or CPO object.

For each of the tasks in `xcvrd` (`CmisManagerTask`, `SfpStateUpdateTask`, `DomInfoUpdateTask`), a CPO-specific subclass will be introduced. Each subclass
will aim to re-use as much code as possible from the original task code, overriding methods where necessary to introduce any required custom logic for CPO hardware.

| Task | CPO Subclass |
|------|--------------|
| CmisManagerTask | CpoManagerTask |
| DomInfoUpdateTask | CpoDomInfoUpdateTask |
| SfpStateUpdateTask | CpoStateUpdateTask |

#### 7.1 CMIS State Machine Management (CmisManagerTask)

##### 7.1.1 Interface Gap Analysis

| Call | Present on CPO objects |
|------|:----------------------:|
| `sfp.get_presence()` | yes, via DeviceBase |
| `sfp.get_xcvr_api()` | yes, via CpoBase |

The philosophy of leveraging DeviceBase and the CmisApi exposed via `get_xcvr_api()` will work for this task, allowing code to be re-used without changes.

##### 7.1.2 Changes Required

###### 7.1.2.1 CmisManagerTask Refactor

`CmisManagerTask` currently iterates over every logical interface, and internally decides whether it should process a given port. When introducing `CpoManagerTask`, 
we will need to ensure that `CmisManagerTask` does not attempt to touch any CPO ports. This will be addressed by refactoring CmisManagerTask to accept a dictionary
of ports it is responsible for. Internally, it will then decide to skip any port that is not present in the dictionary passed to it.
```python3
        # Start the CMIS manager
        # self.sfp_obj_dict contains all traditional pluggable ports
        cmis_manager = None
        if not self.skip_cmis_mgr:
            cmis_manager = CmisManagerTask(self.namespaces, port_mapping_data, self.sfp_obj_dict, self.stop_event, skip_cmis_mgr=self.skip_cmis_mgr)
            cmis_manager.start()
            self.threads.append(cmis_manager)

        # Start the CPO manager
        # self.cpo_obj_dict contains all CPO ports
        cpo_manager = None
        if self.cpo_obj_dict:
            cpo_manager = CpoManagerTask(self.namespaces, port_mapping_data, self.cpo_obj_dict, self.stop_event)
            cpo_manager.start()
            self.threads.append(cpo_manager)
```

This will allow both a `CmisManagerTask` and `CpoManagerTask` to run in parallel and manage their respective ports.

###### 7.1.2.2 CpoManagerTask

A `CpoManagerTask` will be introduced to handle CPO ports. Initially this will be a minimal skeleton that re-uses the `CmisManagerTask` logic as-is,
since the current logic of managing the state machine at the granularity of logical interfaces should be entirely re-usable for current CPO hardware.

There is only one area of the state machine that requires some additional logic for CPO: during `handle_cmis_dp_deinit_state` when the state
machine handles the DPDeinit state. In this function, if a module is already in low power mode, ALL lanes of the device are deinitialized and
disabled:
```python3
        # Deinit and disable all lanes if we are in ModuleLowPwr to avoid unintentional
        # initialization of other datapaths during transition to ModuleReady
        if self.check_module_state(api, ['ModuleLowPwr']):
            self.log_notice("{}: ModuleLowPwr detected, set datapath deinit and disable Tx output for all lanes".format(lport))
            deinit_host_lanes_mask = self.port_dict[lport]['max_host_lanes_mask']
            disable_media_lanes_mask = self.port_dict[lport]['max_media_lanes_mask']
```
To replicate this logic for CPO, all lanes of an optical engine would have to be deinitialized and disabled if the optical engine is in low
power mode, since low power mode is a module-wide state. This requires fetching all other interfaces that share the same underlying OE and
disabling / deinitializing their lanes. See the below code snippet outlining `CpoManagerTask` for how this could be implemented simply.

Later on, if further customization of state machine logic is required to aid in debugging or manage extra steps in the state machine for CPO,
the `CmisManagerTask` can be refactored and/or methods can be overriden in `CmisManagerTask` by `CpoManagerTask`.

```python3
class CpoManagerTask(CmisManagerTask):
    def __init__(self, namespaces, port_mapping, sfp_obj_dict, main_thread_stop_event, skip_cpo_mgr=False):
        super().__init__(namespaces, port_mapping, sfp_obj_dict, main_thread_stop_event,
                         skip_cmis_mgr=skip_cpo_mgr)
        self.name = "CpoManagerTask"

    def log_debug(self, message):
        super().log_debug("CPO: {}".format(message))

    def log_notice(self, message):
        super().log_notice("CPO: {}".format(message))

    def log_error(self, message):
        super().log_error("CPO: {}".format(message))

    def handle_cmis_dp_deinit_state(self, lport):
        # Fetch all sibling physical ports that share this optical engine
        # and disable and deinitialize their lanes.
        api = self.port_dict[lport].get('api')
        if self.check_module_state(api, ['ModuleLowPwr']):
            for sibling_pport in self.get_oe_sibling_pports(lport):
                sibling_api = self.sfp_obj_dict[sibling_pport].get_xcvr_api()
                sibling_api.set_datapath_deinit(0xff)
                sibling_api.tx_disable_channel(0xff, True)
        # Run the existing logic that handles the physical port associated
        # with the current logical interface.
        return super().handle_cmis_dp_deinit_state(lport)
```

#### 7.2 DOM Telemetry (DomInfoUpdateTask)

##### 7.2.1 Interface Gap Analysis

| Call | Present on CPO objects |
|------|:----------------------:|
| `get_presence` | yes, via DeviceBase |
| `get_xcvr_api` | yes, via CpoBase |
| `get_lpmode` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_temperature` | no, but it is a thin wrapper around a CmisApi function of a similar name (`get_module_temperature`) |
| `get_transceiver_dom_real_value` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_dom_flags` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_threshold_info` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_status` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_status_flags` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `is_transceiver_vdm_supported` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `is_vdm_statistic_supported` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_vdm_real_value_basic` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_vdm_real_value_statistic` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_vdm_flags` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_vdm_thresholds` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `freeze_vdm_stats` / `unfreeze_vdm_stats` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_vdm_freeze_status` / `get_vdm_unfreeze_status` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_info_firmware_versions` | no, but it is a thin wrapper around a CmisApi function of the same name |
| `get_transceiver_pm` | no, but it is a thin wrapper around a CmisApi function of the same name |

The philosophy of leveraging `DeviceBase` and `CmisApi` interfaces upholds here again, with a slight caveat. A lot of the functions
used by `DomInfoUpdateTask` are thin wrappers around `CmisApi` functions that provide some output normalization. For example:
```python3
class SfpOptoeBase(SfpBase, OptoeEepromReadWriteMixin):
    ...
    def get_transceiver_status(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_status() if api is not None else None
```

##### 7.2.2 Changes Required

###### 7.2.2.1 Refactor xcvrd to no longer use SfpOptoeBase functions

Many of the functions on `SfpOptoeBase` (`get_transceiver_vdm_real_value_basic`, `get_tx_bias` and `get_transceiver_info` for example) are very
thin wrappers around `CmisApi` functions, providing basic normalization. Most just check whether `self.xcvr_api` is None before calling the API
method in order to avoid an exception being thrown.

`xcvrd` should be refactored to just directly call the `CmisApi` functions and perform normalization in `xcvrd` helper methods. These thin
wrapper functions can then be removed from `SfpOptoeBase` afterwards. That will allow us to rely on the `xcvr_api` for both SfpBase and CPO
objects in the DOM task.

###### 7.2.2.2 Refactor of DomInfoUpdateTask Database Publishing Utilities

The `DomInfoUpdateTask` currently uses many utilities to collect information and publish it to the database. Many of these functions follow
the form of:
1. Read information from transceiver EEPROM
2. Publish to DB

These functions will be refactored to allow customization of step 1, so that CPO can read information from both the optical engine and
the ELSFP before publishing both to the database. This will maximize code re-use while allow CPO to diverge in its high-level control flow.

###### 7.2.2.3 CpoDomInfoUpdateTask

A subclass of `DomInfoUpdateTask` will be introduced, called `CpoDomInfoUpdateTask`. This task will re-implement the high-level DOM logic
for CPO, dealing with things like de-duplicating non-banked information across interfaces that share the same device. However, the same utilities
to publish information to STATE_DB will be re-used.

#### 7.3 ELSFP Presence Detection (SfpStateUpdateTask)

##### 7.3.1 Interface Gap Analysis

| Call | Present on CPO objects |
|------|:----------------------:|
| get_presence | yes, via DeviceBase |
| is_replaceable | yes, via DeviceBase |
| get_xcvr_api | yes, via CpoBase |
| remove_xcvr_api | yes, via CpoBase |
| get_transceiver_info | no, but is a thin wrapper around a CmisApi function of the same name |
| get_error_description | no, but is a thin wrapper around a CmisApi function of the same name |
| get_transceiver_threshold_info | no, but is a thin wrapper around a CmisApi function of the same name |
| get_transceiver_vdm_thresholds | no, but is a thin wrapper around a CmisApi function of the same name |

The philosophy of leveraging DeviceBase and the CmisApi should also work for this task. We will require
the same refactoring to call the CmisApi instead of the thin wrapper functions on SfpOptoeBase that we
need to do for the DOM telemetry above.

##### 7.3.2 Changes Required

A CPO specific `SfpStateUpdateTask` subclass will be introduced. All of the existing logic can be re-used, but
the only difference will be the logic to publish transceiver info to Redis. For CPO, we will need to publish
both OE and ELSFP related information here. As a result, the `SfpStateUpdateTask` will be refactored to pull
the logic that publishes to Redis into its own function that can be overriden in the CPO subclass to publish
both OE and ELSFP information.

#### 7.4 Port Device Access

TODO: How `xcvrd` accesses CPO objects on the Chassis object and differentiates between what is a CPO port
and what is a traditional pluggable port.

Two options:
1. Define new `get_cpo()` accessors on ChassisBase and store CPO ports on in a `self.cpo_list` instance variable separate to `self.sfp_list`
2. Re-use `self.sfp_list`, but just store a `CpoBase`-derived object in that list for any CPO ports.

Option 1 will require more work in `xcvrd`, but provides a cleaner separation between CPO and traditional pluggables.
Option 2 requires less work, because more code can be re-used in `xcvrd`.

### 8. SAI API 

This HLD proposes no SAI API changes.

### 9. Configuration and management 
This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.
If there is breaking change which may impact existing platforms, please call out in the design and get platform vendors reviewed. 

### 10. Warmboot and Fastboot Design Impact  
N/A

### 11. Memory Consumption
This sub-section covers the memory consumption analysis for the new feature: no memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration. 

### 12. Restrictions/Limitations  

### 13. Testing Requirements/Design  
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### 13.1. Unit Test cases  

#### 13.2. System Test cases

### 14. Open/Action items - if any 

