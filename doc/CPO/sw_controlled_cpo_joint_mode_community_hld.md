# SW-controlled CPO in Joint Mode

## Table of Contents

- [SW-controlled CPO in Joint Mode](#sw-controlled-cpo-in-joint-mode)
  - [Table of Contents](#table-of-contents)
  - [1. Revision](#1-revision)
  - [2. Overview](#2-overview)
  - [3. Definitions/Abbreviations](#3-definitionsabbreviations)
  - [4. Scope](#4-scope)
    - [Out of Scope (Current Revision):](#out-of-scope-current-revision)
    - [Added in Rev 0.2:](#added-in-rev-02)
    - [Added in Rev 0.3:](#added-in-rev-03)
  - [5. Requirements](#5-requirements)
  - [6. Architecture Design](#6-architecture-design)
  - [7. High-Level Design](#7-high-level-design)
    - [7.1 Per-Bank Transceiver Object](#71-per-bank-transceiver-object)
    - [7.2 CMIS State Machine Thread for CPO Modules](#72-cmis-state-machine-thread-for-cpo-modules)
    - [7.3 DOM: CPO API Wiring](#73-dom-cpo-api-wiring)
      - [7.3.1 Vendor Extensions](#731-vendor-extensions)
      - [7.3.2 New Files](#732-new-files)
    - [7.4 DOM: CPO EEPROM Layout and STATE\_DB Mapping](#74-dom-cpo-eeprom-layout-and-state_db-mapping)
      - [7.4.1 Adding a Vendor CDB Command](#741-adding-a-vendor-cdb-command)
      - [7.4.2 STATE\_DB Integration via Aggregator Overrides](#742-state_db-integration-via-aggregator-overrides)
    - [Platform Implementation Alignment](#platform-implementation-alignment)
  - [8. SAI API](#8-sai-api)
  - [9. Configuration and management](#9-configuration-and-management)
    - [9.1. Manifest (if the feature is an Application Extension)](#91-manifest-if-the-feature-is-an-application-extension)
    - [9.2. CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
    - [9.3. Config DB Enhancements](#93-config-db-enhancements)
  - [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
  - [11. Memory Consumption](#11-memory-consumption)
  - [12. Restrictions/Limitations](#12-restrictionslimitations)
  - [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [14. Open/Action items - if any](#14-openaction-items---if-any)

---
<br>

## 1. Revision

| Rev | Date       | Author       | Change Description |
|-----|------------|--------------|--------------------|
| 0.1 | 2026-03-31 | Tomer Shalvi | Initial version.   |
| 0.2 | 2026-05-04 | Natanel Gerbi | DOM: CPO data plane -- vendor CPO subclasses (one OE component, one or more ELS components) using B0..B3 vendor mirror pages and CDB commands, exposed to STATE_DB via aggregator-method overrides. No daemon changes. |
| 0.3 | 2026-06-14 | Natanel Gerbi | Align §7.3 with the upstream `CpoBase` / `OeBase` / `ElsfpBase` + `CpoApiFactory` hierarchy under `sonic_xcvr/cpo/`. Add §7.1: per-bank transceiver object becomes a `CpoBase`, sibling of `SfpBase` under a new `XcvrBase` parent. |
<br>

## 2. Overview

**CPO (Co-Packaged Optics)** is a system architecture in which optical components are integrated directly with the switch ASIC, rather than implemented as external pluggable transceivers (e.g., QSFP-DD, OSFP). This integration reduces electrical trace length and improves overall system power efficiency.

At the hardware level, a CPO module is composed of:
* **Optical Engine (OE)** — responsible for electrical-to-optical and optical-to-electrical signal conversion.
* **External Laser Source (ELS)** — providing continuous laser light used by the Optical Engines for transmission.

CPO systems support two operational models:
* **Separate Mode**, where the host directly accesses and manages the underlying components (e.g., OEs and ELSs). See *port_mapping_for_cpo.md* section 2.
* **Joint Mode**, where the host interacts with a CPO module abstraction, without directly managing the underlying components.

To preserve compatibility with existing SONiC and SAI workflows, we introduce a **Virtual CPO Module (or vModule)** that mimics the behavior of a traditional optical module by providing a logical abstraction that exposes a single unified CMIS interface for both the integrated Optical Engine (OE) and External Laser Sources (ELS).

A vModule exposes **32 lanes**, compared to 8 lanes in standard pluggable modules. transceiver. More information regarding 32-lane modules support can be found in *cmis_banking_support.md* section 7.8.

<br>


![vModule3.png](vModule3.png)

## 3. Definitions/Abbreviations

| Term   | Definition |
|--------|------------|
| CPO    | Co-Packaged Optics |
| CMIS   | Common Management Interface Specification |
| vModule| Virtual Module |
| ELS    | External Laser Source |
| OE     | Optical Engine |
| SM     | State Machine |
| FW     | Firmware |
| SW     | Software |
| EEPROM | Electrically Erasable Programmable Read-Only Memory |
| DOM    | Digital Optical Monitoring |
| VDM    | Versatile Diagnostics Monitoring |
| CDB    | Command Data Block |
| ELSFP  | External Laser Source Forward Path |

<br>


## 4. Scope

This document defines the **SW-controlled CPO in Joint Mode**, where SONiC sees CPO modules and interacts with them through the CPO abstraction layer, leveraging the existing CMIS-based host management flows.

Note: the **Separate Mode**, where the host system directly interacts with and manages the underlying optical hardware components is defined in *port_mapping_for_cpo.md* section 2.

The main objective of this document is to demonstrate that supporting Joint Mode:
* Does **not require fundamental changes** to the SONiC architecture.
* Requires only **minor extensions in the generic CMIS host management logic**.
* Relies on **platform-level implementations as defined in existing community HLDs**, with platform-specific behavior described where applicable.

This document builds on existing community HLDs and extends them to support Joint Mode, without redefining them:
* [port_mapping_for_cpo](https://github.com/nexthop-ai/SONiC/blob/274228b44de9edbbf6f1585c9bb7392853cbbc08/doc/platform/port_mapping_for_cpo.md)
* [cmis_banking_support](https://github.com/bobby-nexthop/SONiC/blob/0b09f1cc3e91853fcbabb29efb76fa6ea4b9647d/doc/layer1/cmis_banking_support.md)

### Out of Scope (Current Revision):

This revision of the HLD focuses on the **link-up flow for SW-controlled CPO ports in Joint Mode**.  
The following aspects are **not covered in this revision**, are currently **under development**, and will be addressed in future updates:

* Error handling: A protection mechanism will be introduced to handle CPO-related faults (e.g., thermal events and laser power anomalies).  
* Firmware upgrade: Firmware upgrade support for CPO modules is out of scope for this revision and will be defined in a future update.  
* CLI enhancements: Additional CLI command for CPO vendor-specific error statuses.  

### Added in Rev 0.2:

* DOM: CPO telemetry statistics design, extending the existing DOM flow to include OE telemetry and ELS monitoring statistics via the CPO abstraction EEPROM. The design uses **vendor CPO subclasses of `CmisApi`** (one for the Optical Engine, one for the External Laser Source), composed under a thin wrapper. ELS exposes its CMIS-shaped surface through **vendor mirror pages B0..B3** (re-using the standard CMIS page classes at non-standard page numbers). The data is published to STATE_DB by overriding the existing `CmisApi` aggregator methods, so **no changes are required in `xcvrd`, the STATE_DB schema, or the polling loop**. See Section 7.3.

### Added in Rev 0.3:
* Per-bank transceiver object (§7.1): the per-bank object exposed to chassis / `xcvrd` for a CPO module is a `CpoBase` instead of an `Sfp(SfpBase)` -- both now sit under a new common `XcvrBase` parent.
* DOM: re-aligned the CPO API wiring (§7.3) on top of the upstream `CpoBase` / `OeBase` / `ElsfpBase` / `CpoDeviceBase` / `CpoApiFactory` / `CpoHardwareInfo` surface and the `EepromReadWriteMixin` / `OptoeEepromReadWriteMixin` split, instead of dispatching CPO from `xcvr_api_factory.create_xcvr_api()`. The `CmisApi`-based DOM aggregation (§7.4) is unchanged in shape -- it just sits on the upstream OE / ELSFP `CpoDeviceBase` APIs.
<br>


## 5. Requirements

**Functional Requirements:**
* Support CPO abstraction layer that exposes one or more CPO (virtual) modules, each module has OE and ELS, and is accessible via a single CMIS interface. 
* While working in CPO Joint Mode, the system shall work directly with the CPO abstraction.
* The system shall support correct instantiation of the transceiver object for CPO modules (module type id 0x80).
* The system shall allow CPO modules to be configured via the existing CMIS state machine.
* The system shall support CPO-specific CMIS memory map(s) for the ELS (External Laser Source) and the OE (Optical Engine).
* The system shall collect and publish CPO-specific OE and ELS telemetry (temperature, voltage, laser monitors, lane status) to STATE_DB via the existing DOM polling mechanism, without requiring changes to `xcvrd`, the STATE_DB schema, or the polling loop.

**Non-Functional Requirements:**
* The solution shall maximize the reuse of existing CMIS infrastructure to avoid changing generic code.
* The solution shall remain aligned with existing community HLDs without redefining them.

<br>


## 6. Architecture Design

## 7. High-Level Design

In Joint Mode, SONiC continues to operate using the existing CMIS host management architecture, using exactly the same xcvrd logic, without introducing changes to the overall control flow.

As a result, the following extensions are needed:

### 7.1 Per-Bank Transceiver Object

Chassis and `xcvrd` reach a transceiver through a single per-bank transceiver object whose API (`get_transceiver_info()`, `get_presence()`, ...) is currently defined on `SfpBase`. CPO modules need the same API but should not inherit from `SfpBase`, since they are not SFPs.

The fix is to lift that shared API into a new **`XcvrBase`** parent and make `SfpBase` and `CpoBase` siblings under it:

```text
                       DeviceBase
                          │
                       XcvrBase
              ┌───────────┴────────────┐
          SfpBase                   CpoBase
              │                  (composes OeBase
        SfpOptoeBase              + ElsfpBase, §7.3.1)
```

Concretely, the platform's per-bank transceiver object for a CPO module is a `CpoBase` instead of an `Sfp(SfpBase)`. Callers up the stack are unaffected -- they only depend on the `XcvrBase` API surface, so the CMIS state machine (§7.2) and DOM polling loop (§7.3, §7.4) are unchanged (see *Platform Implementation Alignment* below).


### 7.2 CMIS State Machine Thread for CPO Modules

The CMIS state machine thread is responsible for module configuration. It orchestrates the bring-up of a CMIS transceiver, transitioning it from the inserted state to a ready-for-traffic state.  
To support CPO modules, the existing `CmisManagerTask` thread in `xcvrd` will be extended to handle the `CPO` module type. No new dedicated CPO configuration thread will be introduced.
The only required change in this area is to add `CPO` to the list of CMIS module types handled by `CmisManagerTask`:

```python
CMIS_MODULE_TYPES = ['QSFP-DD', 'QSFP_DD', 'OSFP', 'OSFP-8X', 'QSFP+C', 'CPO']
```

With this change, CPO modules will be processed by the existing CMIS state machine flow.


### 7.3 DOM: CPO API Wiring

#### 7.3.1 Vendor Extensions

Onboarding a vendor adds two parallel stacks, one for the OE and one for the ELSFP:

**1. Per-component CMIS stack** -- for each of OE and ELSFP, add the following classes (the CDB rows are only needed if the vendor uses CDB for telemetry / control):

| Layer            | OE                                       | ELSFP                                                 | Lives under                          |
|------------------|------------------------------------------|-------------------------------------------------------|--------------------------------------|
| Codes            | `Vendor1CpoOeCodes`                      | `Vendor1CpoElsCodes`                                  | `sonic_xcvr/codes/<vendor>/`         |
| MemMap           | `Vendor1CpoOeMemMap(CmisMemMap)`         | `Vendor1CpoElsMemMap(ElsfpCmisMemMap)`                | `sonic_xcvr/mem_maps/<vendor>/`      |
| API              | `Vendor1CpoOeCmisApi(CmisApi)`           | `Vendor1CpoElsCmisApi(ElsfpCmisApi)`                  | `sonic_xcvr/api/<vendor>/`           |
| CDB Codes *(optional)*  | `Vendor1CpoOeCdbCodes`            | `Vendor1CpoElsCdbCodes`                               | `sonic_xcvr/cdb/<vendor>/`           |
| CDB MemMap *(optional)* | `Vendor1CpoOeCdbMemMap(CdbMemMap)` | `Vendor1CpoElsCdbMemMap(CdbMemMap)`                  | `sonic_xcvr/cdb/<vendor>/`           |

The DOM aggregator merge that ends up in STATE_DB is implemented inside the API row, via `super().<aggregator>()` + `dict.update()` -- see §7.4.2. For the CDB rows, see §7.4.1 for the per-command extension pattern (reply page + `CDBCommand` + API getter).

**2. Device wiring** -- per component, add:

| Role          | OE                                  | ELSFP                                     | What it does                                                                 |
|---------------|-------------------------------------|-------------------------------------------|------------------------------------------------------------------------------|
| Product enum entry  | `OeId.Vendor1<Product>`       | `ElsfpId.Vendor1<Product>`                | A new member added directly to the upstream `OeId` / `ElsfpId` enum for each vendor product variant.  |
| API factory branch | `OeApiFactory.create_api()` branch for `OeId.Vendor1<Product>` | `ElsfpApiFactory.create_api()` branch for `ElsfpId.Vendor1<Product>` | Added in-place to the existing upstream factory: `if hardware_id.<id> == OeId.Vendor1<Product>: return self._create_api(<Vendor>CpoOe{Codes,MemMap,CmisApi})`. A vendor `*ApiFactory` subclass is only needed if the vendor wants its own helpers (e.g. NVIDIA's `_get_elsfp_lower_mem_offset` lookup). |
| Device class  | `Vendor1OeBase(OeBase / OptoeOeBase / ...)` | `Vendor1ElsfpBase(ElsfpBase / OptoeElsfpBase / ...)` | The class the platform instantiates -- typically only needed to plumb in the right EEPROM transport via an `EepromReadWriteMixin`. |

#### 7.3.2 New Files

The files added by this HLD on top of the existing `sonic_xcvr/cpo/` infrastructure are:

Per `sonic_xcvr/` convention, per-vendor extensions live under a `<vendor>/` sub-directory of each subtree (`codes/`, `mem_maps/`, `api/`, `cdb/`). The `cpo/` package holds the shared public base classes (`CpoBase`, `OeBase`, `ElsfpBase`, `CpoApiFactory`, `OeId` / `ElsfpId`), so vendor entries are added directly to `cpo/oe.py` and `cpo/elsfp.py`.

```text
sonic-platform-common/sonic_platform_base/sonic_xcvr/
├── cpo/
│   ├── oe.py                          
│   └── elsfp.py                       
│
├── codes/<vendor>/
│   ├── cpo_oe.py                      Vendor1CpoOeCodes
│   └── cpo_els.py                     Vendor1CpoElsCodes
│
├── mem_maps/<vendor>/
│   ├── cpo_oe.py                      Vendor1CpoOeMemMap(CmisMemMap)
│   └── cpo_els.py                     Vendor1CpoElsMemMap(ElsfpCmisMemMap)
│
├── api/<vendor>/
│   ├── cpo_oe.py                      Vendor1CpoOeCmisApi(CmisApi)
│   └── cpo_els.py                     Vendor1CpoElsCmisApi(ElsfpCmisApi)
│
└── cdb/<vendor>/                                                              (optional, only if vendor uses CDB)
    ├── cpo_oe_codes.py                Vendor1CpoOeCdbCodes
    ├── cpo_oe_memmap.py               Vendor1CpoOeCdbMemMap
    ├── cpo_els_codes.py               Vendor1CpoElsCdbCodes
    └── cpo_els_memmap.py              Vendor1CpoElsCdbMemMap
```

### 7.4 DOM: CPO EEPROM Layout and STATE_DB Mapping

OE and ELS data are contributed by the vendor `CmisApi` / `MemMap` subclasses from §7.3.1's CMIS-stack: each vendor `CmisApi` overrides the relevant `CmisApi.get_transceiver_*()` aggregator and chains `super()` + `dict.update()` to add its CPO-specific fields (§7.4.2). ELS-side keys stay `els_*`-prefixed so OE and ELS dicts merge cleanly. The result rides the existing aggregator path, so **no changes are required in `xcvrd`, in the STATE_DB schema, or in the polling loop**.

#### 7.4.1 Adding a Vendor CDB Command

A vendor CDB-driven getter is built from three small pieces. The vendor `CdbMemMap` just **extends** the upstream one -- it inherits all standard CDB commands and pages, and adds new attributes for its own. Each new command needs:

1. **A reply page** -- subclass `CdbEplMessagePage` (CMIS A0h) or `CdbLplMessagePage` (CMIS 9Fh) depending on where the reply lives, and register the reply's typed fields under a group name.
2. **A `CDBCommand`** -- subclass that wires the opcode, the EPL / LPL frame lengths, the reply group name (`rpl_field`), and packs the LPL-request payload in `encode()`.
3. **An API getter** -- one method on the vendor `CmisApi` that calls `cdb_handler.send_cmd()` + `cdb_handler.read_reply()` and returns the decoded dict.

A vendor `CdbMemMap` then registers the reply page (via `add_pages()`) and the command (as a fresh attribute):

```python
class Vendor1CpoOeCdbMemMap(CdbMemMap):
    def __init__(self, codes):
        super().__init__(codes)
        # Extend with a vendor reply page (CMIS page A0h, EPL message area)
        self.add_pages(Vendor1CpoOeTelemetryPage(codes))
        # Extend with a vendor CDB command
        self.vendor1_cpo_oe_read_telemetry_cmd = CdbReadOeTelemetry()
```

`add_pages()` merges the vendor page's typed fields onto the memmap; `_get_all_cdb_cmds()` discovers any `CDBCommand` attribute on `self` by `cmd_id`. So upstream command-id dispatch and field lookup pick the new vendor entries up transparently, with no other layer changes.

#### 7.4.2 STATE_DB Integration via Aggregator Overrides

The vendor `CmisApi` subclasses from §7.3.1 contribute their CPO-specific fields by overriding the relevant `CmisApi` aggregators (`get_transceiver_info`, `get_transceiver_dom_real_value`, `get_transceiver_status_flags`, ...) and chaining `super()` + `dict.update()` to inherit the upstream contributions:

* **Vendor OE component (e.g. `Vendor1CpoOeCmisApi`)** -- inherits the standard CMIS dict via `super()` and overlays its OE-specific extension (e.g. OE CDB telemetry).
* **Vendor ELS component (e.g. `Vendor1CpoElsCmisApi`)** -- inherits the generic ELSFP dict via `super()` and overlays its ELS-specific extension (vendor mirror pages, ELS CDB readouts). All extension keys stay `els_*`-prefixed, so an OE-dict + ELS-dict merge by a consumer is collision-free.

**example OE:**

```python
class Vendor1CpoOeCmisApi(CmisApi):
    def get_transceiver_vdm_real_value(self):
        result = super().get_transceiver_vdm_real_value()
        result.update(self.get_oe_telemetry())   # vendor OE CDB
        return result
```

**example ELS:**

```python
class Vendor1CpoElsCmisApi(ElsfpCmisApi):
    def get_transceiver_status_flags(self):
        result = super().get_transceiver_status_flags()
        result.update(self.get_els_laser_monitoring())  # vendor ELS CDB
        return result
```

<br>

### Platform Implementation Alignment
From the platform implementation perspective, the design aligns completely with the approaches described in the community HLDs. With the `XcvrBase` split from §7.1, the per-bank transceiver object for a CPO module is a `CpoBase` (a sibling of `SfpBase` under `XcvrBase`) instead of an `Sfp(SfpBase)` -- chassis and `xcvrd` see the same `XcvrBase`-shaped interface either way, so the alignment points below are unchanged in spirit, only the per-bank object's class hierarchy changes:

* As described in the *cmis_banking_support.md* (section 7.8.2), the platform will expose one per-bank transceiver object per CPO bank. This structure in Joint mode is illustrated below:

    ![sfp_object_structure_2.png](sfp_object_structure_2.png)

    * Lane-to-port-object mapping is not handled in generic SONiC logic and is instead implemented in the platform layer.
    * Platform code also handles plug-in/plug-out events: The CPO abstraction in Joint mode allows SONiC to interact with the module as if it were a traditional pluggable device, including handling plug-in and plug-out events of the ELS. The chassis continues to listen for change events from the lower layers and notifies *xcvrd* accordingly. The key difference is that, instead of monitoring physical pluggable modules, the system now monitors CPO modules. This approach enables maximal reuse of the existing codebase and results in minimal changes required to support SW-controlled operation in Joint mode.
    * This structure explains why no changes are required in the CMIS state machine logic: The CMIS state machine operates at the **logical port level**, where the list of logical ports is derived from the *CONFIG_DB.PORT table*. This model remains unchanged in Joint Mode. With the per-bank approach:
        * Each per-bank transceiver object continues to represent up to 8 lanes.
        * Multiple logical ports may share the same module index, as in existing pluggable module implementations.
        * As a result, from the CMIS state machine perspective, the system behavior remains unchanged, regardless of whether the underlying 8-lane unit is a traditional pluggable transceiver (an `Sfp(SfpBase)`) or a CPO bank (a `CpoBase`).

* As described in the *port_mapping_for_cpo.md* section 7.3.2, the per-bank `CpoBase` objects will follow the same structure, including references to the underlying OE and ELS components, together with the associated bank index (*cmis_banking_support.md* section 7.8.3). The instantiation of these objects will be done in platform chassis (*port_mapping_for_cpo.md* section 7.3.3) and rely on platform configuration files (e.g., a JSON file similar to `optical_devices.json`, as proposed in *port_mapping_for_cpo.md* section 7.1).

<br>


## 8. SAI API

## 9. Configuration and management

### 9.1. Manifest (if the feature is an Application Extension)

### 9.2. CLI/YANG model Enhancements

In addition to the bank-aware EEPROM access commands introduced in *cmis_banking_support.md* (section 7.9), this design introduces an update to the following CLI command for monitoring CPO-specific error statuses:

**Syntax:**
`show interfaces transceiver error-status [<interface_name>] [-hw]`

This command extends the existing transceiver status reporting to include **CPO vendor-specific error conditions**, such as laser or fiber-related failures.

*Example output of `show interfaces transceiver error-status`.*

```text
show interfaces transceiver error-status [<interface_name>] [-hw]

Port         Error Status
-----------  ---------------
Ethernet0    OK
Ethernet4    OK
Ethernet8    Laser high power
Ethernet12   Fiber check failure
...
```

### 9.3. Config DB Enhancements

No Config DB changes are required (Except for the *associated_devices* field added to the *CONFIG_DB.PORT table*, mentioned in *port_mapping_for_cpo.md*, section 9.2).

<br>


## 10. Warmboot and Fastboot Design Impact

## 11. Memory Consumption

## 12. Restrictions/Limitations

## 13. Testing Requirements/Design

## 14. Open/Action items - if any
