`class BaillyApi(CmisApi):class BaillyApi(CmisApi):`

# HLD: CPO Firmware Upgrade CMIS Bailly API

## Table of Contents

- [HLD: CPO Firmware Upgrade CMIS Bailly API](#hld-cpo-firmware-upgrade-cmis-bailly-api)
  - [Table of Contents](#table-of-contents)
  - [1. Revision](#1-revision)
  - [2. Scope](#2-scope)
  - [3. Background \& Class Hierarchy](#3-background--class-hierarchy)
    - [3.1 Original Community Class Structure](#31-original-community-class-structure)
    - [3.2 CPO Extension Architecture Adjustment](#32-cpo-extension-architecture-adjustment)
    - [3.3. Class Inheritance Design](#33-class-inheritance-design)
  - [4. CDB Opcode Reuse \& Override Rule](#4-cdb-opcode-reuse--override-rule)
    - [4.1 Default Reuse Rule](#41-default-reuse-rule)
    - [4.2 Example Implementation of BaillyCdbFwHandler](#42-example-implementation-of-baillycdbfwhandler)
  - [5. Full CDB Command Call Flow (Unchanged Upper Layer)](#5-full-cdb-command-call-flow-unchanged-upper-layer)
  - [6. Core Design Benefits](#6-core-design-benefits)
  - [7. Open Items](#7-open-items)
  - [8. Summary](#8-summary)

## 1. Revision

| Rev | Date         | Author     | Change Description                                                                                                                                                                     |
| --- | ------------ | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1 | 2026-08-02   | KroosMicas | Initial version: Focus on extending base`CdbFwHandler` via inheritance for CPO; reuse standard 0x0100/0101/0102/0104/0107/0109/010A CDB commands, override only differentiated logic |
| 0.2 | 2026‑08‑08 | KroosMicas | Split three independent handler`McuCdbFwHandler` / `OeCdbFwHandler` / `ElsCdbFwHandler` for MCU / OE / ELS partitions;                                                           |

## 2. Scope

This HLD only covers the CDB firmware handler extension design inside CPO firmware upgrade stack, **excludes CLI layer**.
Core design principle:

1. Reuse community base `CdbFwHandler` as parent class for all standard CDB firmware opcodes (0x0100,0x0101,0x0102,0x0104,0x0107,0x0109,0x010A).
2. Create three vendor‑specific sub‑classes inherited from CdbFwHandler:
   1. `McuCdbFwHandler: for MCU / CMIS controller partition`
   2. `OeCdbFwHandler: for OE / PRISM partition`
   3. `ElsCdbFwHandler: for ELS‑RLM partition`
3. Inheritance chain: `CmisCdbFw` → `CmisApi(CmisCdbFw, XcvrApi)` → `BaillyApi(CmisApi)`.
4. `BaillyApi` adds  **three new properties** : `cdb_mcu_fw_hdlr`, `cdb_oe_fw_hdlr`, `cdb_els_fw_hdlr`. Each property lazy‑instantiates its corresponding partition handler instance.
5. All upper-layer firmware flow logic inside `CmisCdbFw` remains unchanged, transparent to caller.

> Note: The original single overridden `cdb_fw_hdlr` property from parent `CmisCdbFw` is **not used** for CPO multi‑partition scenario. CPO uses three newly‑added partition‑specific handler properties instead.

## 3. Background & Class Hierarchy

### 3.1 Original Community Class Structure

```python
# Base CDB firmware handler with all 7 standard CDB firmware opcodes
class CdbFwHandler:
    def get_fw_status(self):       # 0x0100
    def start_fw_download(self):   # 0x0101
    def abort_fw_download(self):   # 0x0102
    def write_lpl_block(self):     # 0x0103 LPL
    def write_epl_block(self):     # 0x0104 EPL
    def complete_fw_download(self):# 0x0107
    def run_fw_image(self):        # 0x0109
    def commit_fw_image(self):     # 0x010A

# CDB firmware capability wrapper, provides high-level upgrade APIs
class CmisCdbFw:
    @property
    def cdb_fw_hdlr(self):
        if self._cdb_fw_hdlr is None:
            self._cdb_fw_hdlr = self._create_cdb_fw_handler()
        return self._cdb_fw_hdlr

    def _create_cdb_fw_handler(self):
        # Default: create standard base handler
        return CdbFwHandler(self.xcvr_eeprom.reader, self.xcvr_eeprom.writer, self._cdb_mem_map)

# Unified CMIS transceiver API, inherits CmisCdbFw to get all CDB firmware methods
class CmisApi(CmisCdbFw, XcvrApi):
    pass
```

- `CmisCdbFw` is the upper API layer, all firmware operations forward to `self._cdb_fw_hdlr`;
- Base `CdbFwHandler` implements standard CMIS CDB firmware command logic for common pluggable modules;
- Bailly‑CPO hardware contains three independent firmware partitions (MCU, OE, ELS‑RLM). Each partition needs its own isolated handler instance.CPO hardware (MCU/OE/ELS partitioned firmware) has customized CDB processing logic for partial opcodes, so inheritance extension is introduce.

### 3.2 CPO Extension Architecture Adjustment

Step 1: Vendor partition‑specific handler sub‑classes, inherit community CdbFwHandler

```Python
class McuCdbFwHandler(CdbFwHandler):
    """Handler dedicated for MCU / CMIS controller partition"""
    def __init__(self, reader, writer, cdb_map):
        super().__init__(reader, writer, cdb_map)
    # Re‑use parent method by default; override only MCU‑specific opcode logic if needed

class OeCdbFwHandler(CdbFwHandler):
    """Handler dedicated for OE / PRISM partition"""
    def __init__(self, reader, writer, cdb_map):
        super().__init__(reader, writer, cdb_map)
    # Example: OE needs strip 4‑byte start‑address header during EPL write
    def write_epl_block(self, address, data):
        stripped_data = data[4:]
        return super().write_epl_block(address, stripped_data)

class ElsCdbFwHandler(CdbFwHandler):
    """Handler dedicated for ELS‑RLM partition"""
    def __init__(self, reader, writer, cdb_map):
        super().__init__(reader, writer, cdb_map)
    # Re‑use parent method by default; override only ELS‑RLM‑specific opcode logic if needed
```

Step 2: BaillyApi(CmisApi) adds three lazy‑load handler properties

```Python
class BaillyApi(CmisApi):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cdb_mcu_fw_hdlr = None
        self._cdb_oe_fw_hdlr = None
        self._cdb_els_fw_hdlr = None

    @property
    def cdb_mcu_fw_hdlr(self):
        """Lazy‑load handler for MCU partition"""
        if not self._init_cdb_fw_handler:
            return None
        if self._cdb_mcu_fw_hdlr is None:
            self._cdb_mcu_fw_hdlr = McuCdbFwHandler(
                self.xcvr_eeprom.reader,
                self.xcvr_eeprom.writer,
                self._cdb_mem_map,
            )
        return self._cdb_mcu_fw_hdlr

    @property
    def cdb_oe_fw_hdlr(self):
        """Lazy‑load handler for OE partition"""
        if not self._init_cdb_fw_handler:
            return None
        if self._cdb_oe_fw_hdlr is None:
            self._cdb_oe_fw_hdlr = OeCdbFwHandler(
                self.xcvr_eeprom.reader,
                self.xcvr_eeprom.writer,
                self._cdb_mem_map,
            )
        return self._cdb_oe_fw_hdlr

    @property
    def cdb_els_fw_hdlr(self):
        """Lazy‑load handler for ELS‑RLM partition"""
        if not self._init_cdb_fw_handler:
            return None
        if self._cdb_els_fw_hdlr is None:
            self._cdb_els_fw_hdlr = ElsCdbFwHandler(
                self.xcvr_eeprom.reader,
                self.xcvr_eeprom.writer,
                self._cdb_mem_map,
            )
        return self._cdb_els_fw_hdlr
```

note:

`BaillyApi` **does NOT modify / override parent `cdb_fw_hdlr` property** inherited from `CmisCdbFw`.

The original `cdb_fw_hdlr` remains available for traditional single‑partition CMIS module compatibility, but  **is not used by CPO firmware upgrade workflow** .

CPO business layer explicitly selects `cdb_mcu_fw_hdlr` / `cdb_oe_fw_hdlr` / `cdb_els_fw_hdlr` according to target component.

### 3.3. Class Inheritance Design

```
Community Base Handler
        └── CdbFwHandler
              ├─ McuCdbFwHandler  (CPO‑MCU vendor subclass)
              ├─ OeCdbFwHandler  (CPO‑OE vendor subclass)
              └─ ElsCdbFwHandler (CPO‑ELS‑RLM vendor subclass)

Community API hierarchy
CmisCdbFw
    ↓
CmisApi(CmisCdbFw, XcvrApi)
    ↓
BaillyApi(CmisApi)
    ├─ @property cdb_mcu_fw_hdlr → returns McuCdbFwHandler instance
    ├─ @property cdb_oe_fw_hdlr  → returns OeCdbFwHandler instance
    └─ @property cdb_els_fw_hdlr → returns ElsCdbFwHandler instance
```

* `CmisApi` inherits `CmisCdbFw`, so it owns the original `cdb_fw_hdlr` property and all high-level firmware APIs (`module_fw_download`, `module_fw_run`, etc.).
* `BaillyApi` inherits `CmisApi`, and overrides the `cdb_fw_hdlr` property.
* When any firmware API inside `CmisCdbFw` accesses `self.cdb_fw_hdlr`, it will resolve to the overridden property in `BaillyApi`, returning `BaillyCdbFwHandler` instance.
* No changes required to `CmisCdbFw`, `CmisApi`, or any upper calling logic; vendor differentiation is fully encapsulated in `BaillyApi` + `BaillyCdbFwHandler`.

## 4. CDB Opcode Reuse & Override Rule

### 4.1 Default Reuse Rule

Each partition handler (`McuCdbFwHandler` / `OeCdbFwHandler` / `ElsCdbFwHandler`) inherits all methods from base `CdbFwHandler`:

1. If partition processing logic conforms to standard CMIS CDB specification:  **do NOT override** , directly call parent class implementation.
2. If partition requires special register offset, payload pre‑processing, partition‑specific handshake sequence: override corresponding method inside that partition’s handler class only.

Mapping between CDB opcode and base handler method:

| CDB Opcode | Base`CdbFwHandler`Method | Reuse Policy                                                                             |
| ---------- | -------------------------- | ---------------------------------------------------------------------------------------- |
| 0x0001     | enter_password(password)   | Default reuse parent; override if partition has special auth flow                        |
| 0x0100     | get_fw_status()            | Default reuse parent; override only when partition status register layout differs        |
| 0x0101     | start_fw_download()        | Default reuse parent; override if partition needs special initialization before download |
| 0x0102     | abort_fw_download()        | Default reuse parent; override only for partition‑specific cleanup                      |
| 0x0103     | write_lpl_block()          | Default reuse parent                                                                     |
| 0x0104     | write_epl_block()          | Default reuse parent; e.g. OE overrides for header‑stripping                            |
| 0x0107     | complete_fw_download()     | Default reuse parent; override if partition adds extra CRC / metadata check              |
| 0x0109     | run_fw_image()             | Default reuse parent; override for partition‑specific reset mode                        |
| 0x010A     | commit_fw_image()          | Default reuse parent; override for partition non‑volatile persist logic                 |

### 4.2 Handler Sub‑class Example Implementation

```python
class OeCdbFwHandler(CdbFwHandler):
    def __init__(self, reader, writer, cdb_map):
        super().__init__(reader, writer, cdb_map)

    # No override → transparently use parent: get_fw_status(), start_fw_download(), abort_fw_download()

    def write_epl_block(self, address, data):
        """OE partition special: strip leading 4‑byte hardware start‑address header from payload"""
        stripped_data = data[4:]
        return super().write_epl_block(address, stripped_data)

    # Other methods reuse base‑class implementation without modification
```

## 5. Full CDB Command Call Flow (Unchanged Upper Layer)

Upper business layer (CPO firmware upgrade manager from cpoutil HLD) selects corresponding handler property according to target component(mcu / oe / els):

```
BaillyApi instance
    ├─ When target component = mcu → self.cdb_mcu_fw_hdlr (McuCdbFwHandler)
    ├─ When target component = oe  → self.cdb_oe_fw_hdlr  (OeCdbFwHandler)
    └─ When target component = els → self.cdb_els_fw_hdlr (ElsCdbFwHandler)

Example for OE download flow:
api.cdb_oe_fw_hdlr.enter_password(password)          #0x0001
api.cdb_oe_fw_hdlr.start_fw_download(imgpath)        #0x0101
loop: api.cdb_oe_fw_hdlr.write_epl_block(address,data) #0x0104 (OE overridden version)
api.cdb_oe_fw_hdlr.complete_fw_download()            #0x0107
api.cdb_oe_fw_hdlr.run_fw_image(mode=0x01)           #0x0109
api.cdb_oe_fw_hdlr.commit_fw_image()                 #0x010A

Status / recovery example:
api.cdb_oe_fw_hdlr.get_fw_status()                   #0x0100
api.cdb_oe_fw_hdlr.abort_fw_download()              #0x0102
```

* All low‑level opcode logic is encapsulated inside each partition handler instance.
* Upper layer business code only selects which handler property to invoke; does not modify any opcode implementation.
* Upstream community classes `CmisCdbFw`, `CmisApi`, `CdbFwHandler` remain untouched.

## 6. Core Design Benefits

* **Zero intrusion to community upstream code** : All vendor‑specific logic is isolated inside three sub‑classes (`McuCdbFwHandler` / `OeCdbFwHandler` / `ElsCdbFwHandler`) and `BaillyApi` extended properties. No patches to `CmisCdbFw` / `CmisApi` / `CdbFwHandler`.
* **Partition isolation** : MCU / OE / ELS each owns independent handler instance; state (download session, error status) is isolated per partition, no cross‑partition state pollution.
* **Fine‑grained override capability** : Only override the exact method that differs for a given partition; maximum reuse of standard CMIS‑CDB base‑class logic.
* **Consistent method signature** : Reuse community `CdbFwHandler` function signatures, no custom‑named vendor‑only APIs. Upper‑layer code uses uniform method interface across all three partitions.
* **Lazy‑instantiation** : Handler objects are created on first access; avoid unnecessary resource consumption for unused partitions.
* **Compliant with SONiC XcvrApi extension pattern** : Vendor‑specific `BaillyApi` inherits standard `CmisApi`.

## 7. Open Items

If any

## 8. Summary

* Inheritance tree: `CdbFwHandler` (community base) → three partition‑specific sub‑classes: `McuCdbFwHandler`, `OeCdbFwHandler`, `ElsCdbFwHandler`.
* `BaillyApi(CmisApi)` adds three new lazy‑load read‑only properties: `cdb_mcu_fw_hdlr`, `cdb_oe_fw_hdlr`, `cdb_els_fw_hdlr`. Each property instantiates its corresponding partition‑handler instance.
* Original parent‑class `cdb_fw_hdlr` property from `CmisCdbFw` is preserved for compatibility but  **not used by CPO multi‑partition upgrade workflow** .
* Each partition handler reuses base `CdbFwHandler` opcode‑methods by default; override only when hardware partition requires special processing.
* Upper‑level upgrade manager selects correct handler property by target component(mcu / oe / els), then invoke standard handler methods; community upstream source files are unchanged.
