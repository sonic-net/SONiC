# xcvrd CPO Support #

## Table of Content 

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 CMIS State Machine Management (CmisManagerTask)](#71-cmis-state-machine-management-cmismanagertask)
    - [7.1.1 Interface Gap Analysis](#711-interface-gap-analysis)
    - [7.1.2 Changes Required](#712-changes-required)
      - [7.1.2.1 CmisManagerTask Refactor](#7121-cmismanagertask-refactor)
      - [7.1.2.2 CpoManagerTask](#7122-cpomanagertask)
  - [7.2 DOM Telemetry (DomInfoUpdateTask)](#72-dom-telemetry-dominfoupdatetask)
    - [7.2.1 Interface Gap Analysis](#721-interface-gap-analysis)
    - [7.2.2 Changes Required](#722-changes-required)
      - [7.2.2.1 Database Schema for CPO](#7221-database-schema-for-cpo)
      - [7.2.2.2 CpoDomInfoUpdateTask](#7222-cpodominfoupdatetask)
      - [7.2.2.3 Introduce banked and non-banked aggregate getters in CmisApi and ElsfpApi](#7223-introduce-banked-and-non-banked-aggregate-getters-in-cmisapi-and-elsfpapi)
      - [7.2.2.4 Refactor of DomInfoUpdateTask Database Publishing Utilities](#7224-refactor-of-dominfoupdatetask-database-publishing-utilities)
  - [7.3 ELSFP Presence Detection (SfpStateUpdateTask)](#73-elsfp-presence-detection-sfpstateupdatetask)
    - [7.3.1 Interface Gap Analysis](#731-interface-gap-analysis)
    - [7.3.2 Changes Required](#732-changes-required)
  - [7.4 Port Device Access](#74-port-device-access)
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
        if not self.skip_cmis_mgr and self.sfp_obj_dict:
            cmis_manager = CmisManagerTask(self.namespaces, port_mapping_data, self.sfp_obj_dict, self.stop_event, skip_cmis_mgr=self.skip_cmis_mgr)
            cmis_manager.start()
            self.threads.append(cmis_manager)

        # Start the CPO manager
        # self.cpo_obj_dict contains all CPO ports
        cpo_manager = None
        if not self.skip_cpo_mgr and self.cpo_obj_dict:
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
            pport = self.port_mapping.get_logical_to_physical(lport)[0]
            for sibling_pport in self.get_oe_sibling_pports(pport):
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

Given that these methods are not providing much, `xcvrd` should be refactored to just directly call the `CmisApi` functions
and perform normalization in `xcvrd` helper methods. These thin wrapper functions can then be removed from `SfpOptoeBase`
afterwards. However, that is not a pre-requisite for CPO support and can be pursued in the future separately. The changes
in this HLD to add CPO support will not add any more methods like this to `SfpOptoeBase`, and will favour direct calls
against the `XcvrApi` instead.

##### 7.2.2 Changes Required

###### 7.2.2.1 Database Schema for CPO

For CPO, all OE data will be published to the existing `TRANSCEIVER_*` `STATE_DB` tables `DomInfoUpdateTask` publishes to, while
ELSFP data will be published to new parallel tables following the naming format `TRANSCEIVER_ELS_*` (e.g.
`TRANSCEIVER_ELS_DOM_SENSOR`, `TRANSCEIVER_ELS_STATUS_FLAG`). The rationale behind this approach is as follows:
- Keeping the two devices in separate tables means the existing table schemas are untouched, posing no risk
to current `STATE_DB` consumers.
- There is a clear, schema-enforced separation between what information is related to the OE and what is related to the ELSFP.
For example, there is no need to consider key collisions in this approach, which would be a concern if ELSFP information was
published to the regular `TRANSCEIVER_*` tables.
- The naming scheme `TRANSCEIVER_ELS_*` preserves the ability to grep for the Redis keys related to transceiver information,
since it shares the same prefix of `TRANSCEIVER_` with the existing tables.

###### 7.2.2.2 CpoDomInfoUpdateTask

A subclass of `DomInfoUpdateTask` will be introduced, called `CpoDomInfoUpdateTask`. Similarly to the `CpoManagerTask`,
this task will only be created to handle CPO ports and any traditional pluggable ports will continue to be handled
via the existing `DomInfoUpdateTask` which can run in parallel:
```python3
        # Start the dom sensor info update thread
        dom_info_update = None
        if self.sfp_obj_dict:
            dom_info_update = DomInfoUpdateTask(self.namespaces, port_mapping_data, self.sfp_obj_dict, self.stop_event, self.skip_cmis_mgr, self.dom_update_interval)
            dom_info_update.start()
            self.threads.append(dom_info_update)

        # Start the CPO dom sensor info update thread
        cpo_dom_info_update = None
        if self.cpo_obj_dict:
            cpo_dom_info_update = CpoDomInfoUpdateTask(self.namespaces, port_mapping_data, self.cpo_obj_dict, self.stop_event, False, self.dom_update_interval)
            cpo_dom_info_update.start()
            self.threads.append(cpo_dom_info_update)
```

This task will re-implement the high-level control flow of DOM logic for CPO so that information shared across logical
interfaces is read from the hardware only once per device. This is necessary for two reasons:
- Since OE and ELSFP devices are shared across multiple logical interfaces, duplicate information will be published to
each logical interface's database table. In the CPO task, non-banked information will be read from the hardware once
and published to the table for each logical interface associated with the OE or ELSFP. Banked information will be read
once per-interface, since that is unique. This approach will avoid the unnecessary use of i2c read bandwidth that would
occur if non-banked information was read once per logical interface.
- This is also necessary in order to treat any non-banked registers that have clear-on-read semantics correctly. If we
read non-banked information once per logical interface, then the logical interfaces sharing the same device will report
different information.

```python3
class CpoDomInfoUpdateTask(DomInfoUpdateTask):
    def task_worker(self):
        while not self.task_stopping_event.is_set():
            # Dictionaries containing device-shared data, keyed by the lowest
            # sibling physical port of each device sharing group. Discarded every
            # pass, so data is at most one polling interval old and no cache
            # invalidation policy is needed.
            oe_module_values = {}
            elsfp_module_values = {}

            for pport, cpo_obj in sorted(self.cpo_obj_dict.items()):
                # Presence is checked once per physical port via DeviceBase
                if not cpo_obj.get_presence():
                    continue

                # Module-scope (non-banked) OE data: read ONCE per OE. Non-banked
                # registers are bank-independent, so the first sibling pport
                # processed in this pass reads them through its own CmisApi and
                # the remaining siblings re-use the snapshot.
                oe_key = min(self.get_oe_sibling_pports(pport))
                if oe_key not in oe_module_values:
                    oe_module_values[oe_key] = self.dom_utils.get_transceiver_dom_module_values(pport)

                # ELSFP data: read ONCE per ELSFP sharing group
                elsfp_key = min(self.get_elsfp_sibling_pports(pport))
                if elsfp_key not in elsfp_module_values:
                    elsfp_module_values[elsfp_key] = self.elsfp_utils.get_elsfp_dom_module_values(pport)

                # Lane-scope (banked) data: unique to this physical port, since
                # the CPO object is bound to the bank covering this port's lanes
                oe_lane_values = self.dom_utils.get_transceiver_dom_lane_values(pport)
                elsfp_lane_values = self.elsfp_utils.get_elsfp_dom_lane_values(pport)

                # Publish to the first subport's logical interface, matching the
                # existing DomInfoUpdateTask convention for breakout groups
                lport = self.port_mapping.get_physical_to_logical(pport)[0]
                asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
                self.dom_db_utils.post_diagnostic_values_from_dict_to_db(
                    lport, self.xcvr_table_helper.get_dom_tbl(asic_index),
                    {**oe_module_values[oe_key], **oe_lane_values})
                self.dom_db_utils.post_diagnostic_values_from_dict_to_db(
                    lport, self.xcvr_table_helper.get_elsfp_dom_tbl(asic_index),
                    {**elsfp_module_values[elsfp_key], **elsfp_lane_values})

                # DOM flags, transceiver status, VDM and PM follow the same
                # pattern: module-scope reads de-duplicated via the non-banked
                # info dicts, lane-scope reads per physical port, published via
                # the from-dict primitives
                ...
```

The `get_oe_sibling_pports()` / `get_elsfp_sibling_pports()` helpers return the set of physical ports whose CPO objects share the
same underlying OE / ELSFP respectively, derived from the platform port mapping. These are described further in section
"7.4 Port Device Access".

###### 7.2.2.3 Introduce banked and non-banked aggregate getters in CmisApi and ElsfpApi

As shown above in the CPO DOM control flow, the aggregate `CmisApi` functions used by the DOM task will be split
into non-banked (module-scoped) and banked (lane-scope) variants. An analysis of the EEPROM pages read by each
aggregate shows that most of them mix module-level data (non-banked pages 00h-0Fh) and lane-level data (banked
pages 10h and above) in a single call:

| CmisApi function | Non-banked reads | Banked reads |
|---|---|---|
| `get_transceiver_dom_real_value` | temperature, voltage, laser temperature (00h, 01h) | tx/rx power, tx bias (11h) |
| `get_transceiver_dom_flags` | module flag bytes (00h) | lane alarm/warning flags (11h) |
| `get_transceiver_status` | module state, fault cause (00h) | datapath/config states, output status (10h, 11h) |
| `get_transceiver_status_flags` | module firmware fault (00h) | lane fault/LOS/LOL flags (11h) |
| `get_module_temperature`, `get_transceiver_threshold_info`, `get_transceiver_info_firmware_versions`, `get_lpmode` | all reads | — |
| `get_transceiver_pm`, VDM values/flags/thresholds | support/advertising bits only (01h) | all monitored data |

The mixed functions cannot be used as-is by the CPO DOM control flow (section 7.2.2.2), which needs to read module-scope data
once per device and lane-scope data once per physical port. Each mixed aggregate will therefore be split, with the existing
function re-implemented as the composition of the two new variants:

```python3
    def get_transceiver_dom_module_values(self):
        # Module-scope: temperature, voltage, laser temperature (pages 00h/01h)
        ...

    def get_transceiver_dom_lane_values(self):
        # Lane-scope: tx/rx power, tx bias (banked page 11h)
        ...

    def get_transceiver_dom_real_value(self):
        result = self.get_transceiver_dom_module_values()
        result.update(self.get_transceiver_dom_lane_values())
        return result
```

Re-implementing the aggregate as a composition (rather than leaving it as parallel code) keeps behavior for traditional
pluggables identical and means a vendor override of a scoped variant automatically stays consistent with the aggregate.

###### 7.2.2.4 Refactor of DomInfoUpdateTask Database Publishing Utilities

The per-port publishing entrypoints used by `DomInfoUpdateTask` (e.g. `post_port_dom_sensor_info_to_db`) and the
flag-publishing paths currently couple two steps in a single call — read the information from the transceiver EEPROM,
then publish it — and hard-code the target `TRANSCEIVER_*` tables. The CPO control flow (section 7.2.2.2) performs its
own reads, de-duplicated across the ports sharing a device, and publishes both OE and ELSFP data. To be re-usable by
the CPO task, the publishing code paths will be refactored so that:

- The values to publish are passed in as an argument, rather than being read from hardware inside the function.
- The target table is passed in as an argument, so the same code can publish to either the traditional
  `TRANSCEIVER_*` tables or the new `TRANSCEIVER_ELS_*` tables (`XcvrTableHelper` will gain accessors for the
  latter).

For instance, the `dom_db_utils.post_diagnostic_values_from_dict_to_db()` function used in the `CpoDomInfoUpdateTask`
snippet in section 7.2.2.2 is an example of this refactored publishing code path: the CPO control flow passes it the
values it has already collected along with the target table.

All remaining publishing logic — value normalization, `last_update_time` stamping, and the flag metadata handling
(change count, last set/clear time) — stays in these shared functions, used by both `DomInfoUpdateTask` and
`CpoDomInfoUpdateTask`. The existing per-port entrypoints are retained as thin "read, then publish" wrappers around
the shared functions, so behavior for traditional pluggable ports is unchanged, while the CPO control flow calls the
publish functions directly with the data it has already collected.

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

The philosophy of leveraging DeviceBase and the CmisApi should also work for this task. The same
refactoring to call the CmisApi directly instead of the thin wrapper functions on SfpOptoeBase that was
suggested in section "7.2 DOM Telemetry" above is a pre-requisite to enable code sharing between CPO
and traditional pluggables in this task.

##### 7.3.2 Changes Required

###### 7.3.2.1 CpoStateUpdateTask

A CPO specific `SfpStateUpdateTask` subclass will be introduced. The bulk of the existing logic can be re-used;
the differences for CPO are:

- **Transceiver info publishing**: both OE and ELSFP information must be published. The `SfpStateUpdateTask`
  logic that publishes transceiver info to Redis will be pulled into its own function that the CPO subclass
  overrides to publish OE information to the existing `TRANSCEIVER_INFO` table and ELSFP information to a new
  `TRANSCEIVER_ELS_INFO` table.
- **Threshold publishing on insertion**: OE thresholds are published to the existing
  `TRANSCEIVER_DOM_THRESHOLD` / `TRANSCEIVER_VDM_*_THRESHOLD` tables as today, and ELSFP threshold data
  provided by the ElsfpApi is published to the parallel `TRANSCEIVER_ELS_*` variants, following the schema
  approach in section 7.2.2.1.
- **Cleanup on plug-out and logical port removal**: the table list passed to `del_port_sfp_dom_info_from_db()`
  will be extended with the `TRANSCEIVER_ELS_*` tables so ELSFP entries are cleared alongside the existing
  `TRANSCEIVER_*` entries. This preserves the contract with orchagent in a backwards compatible manner, which
  reacts to the creation and deletion of the `TRANSCEIVER_INFO` table.
- **De-duplication of module-scope reads**: transceiver info and thresholds are module-scope data, and one
  ELSFP plug event affects all sibling physical ports sharing that ELSFP. The CPO subclass will read this data
  once per device and re-use it across sibling ports, mirroring the approach in section 7.2.2.2.

###### 7.3.2.2 Presence Change Event Handling

For CPO objects, `get_presence()` reports the presence of the ELSFP. The OE is co-packaged and always present,
so the ELSFP is the only removable device for a CPO port.

Insertion and removal detection is driven by the chassis-level `get_change_event()` call, which returns a
single stream of per-physical-port events. Since `SfpStateUpdateTask` and `CpoStateUpdateTask` run in parallel,
they cannot both call `get_change_event()` directly: it is a single blocking event stream, so each call would
consume events destined for both tasks. There is essentially no mechanism that would prevent the CPO task from
consuming events for traditional transceivers and vice-versa.

To address this, a new `get_elsfp_change_event()` function will be defined in the platform API alongside
`get_change_event()`. It follows the same semantics — blocking with a timeout, returning insertion/removal
events keyed by physical port, reported once for each physical port associated with the ELSFP — but reports
ELSFP events only. `CpoStateUpdateTask` blocks on `get_elsfp_change_event()` while `SfpStateUpdateTask`
continues to consume `get_change_event()` unchanged, giving each task its own independent event stream.

#### 7.4 Port Device Access

`xcvrd` needs to know how to differentiate between traditional pluggable ports and CPO ports. There is not
yet a standardized SFF-8024 identifier for CPO modules, so this will be solved by checking if the port is
a CPO port via the ChassisBase-provided CPO object access methods outlined in the ["Port Mapping for CPO"
HLD](https://github.com/sonic-net/SONiC/blob/master/doc/platform/port_mapping_for_cpo.md):
```python3
def is_cpo_port(physical_port):
    if platform_chassis is None:
        return False
    try:
        return platform_chassis.get_cpo(physical_port) is not None
    except (NotImplementedError, AttributeError, IndexError):
        return False
```
This will allow `xcvrd` to make a decision on whether a given port should be handled by the existing set of
tasks or the new set of CPO-specific tasks described in this HLD.

In the above sections, `xcvrd` also requires the ability to fetch which other physical ports share an
optical engine or ELSFP with the current physical port. To support that need, two new functions will
be implemented as utility functions for `xcvrd` code to use:
- `get_oe_sibling_pports` which fetches all other physical ports that share an OE.
- `get_elsfp_sibling_pports` which fetches all other physical ports that share an ELSFP.

### 8. SAI API 

This HLD proposes no SAI API changes.

### 9. Configuration and management 
N/A

### 10. Warmboot and Fastboot Design Impact  
N/A

### 11. Memory Consumption
No noticeable increase in memory consumption is expected due to the changes proposed in this HLD.

### 12. Restrictions/Limitations  

### 13. Testing Requirements/Design  
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### 13.1. Unit Test cases  

#### 13.2. System Test cases

### 14. Open/Action items - if any 

