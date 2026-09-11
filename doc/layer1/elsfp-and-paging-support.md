# Paging support in CMIS memory maps and ELSFP support #

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
  - [Functional Requirements](#functional-requirements)
  - [Non-Functional Requirements](#non-functional-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Repositories Changed](#71-repositories-changed)
  - [7.2 Memory Map Abstraction Changes (cmis package)](#72-memory-map-abstraction-changes-cmis-package)
    - [7.2.1 Page constants](#721-page-constants)
    - [7.2.2 The CmisPage class](#722-the-cmispage-class)
    - [7.2.3 New CMIS pages](#723-new-cmis-pages)
    - [7.2.4 The CmisFlatMemMap and CmisMemMap classes](#724-the-cmisflatmemmap-and-cmismemmap-classes)
    - [7.2.5 Derived memory maps: C-CMIS and CDB](#725-derived-memory-maps-c-cmis-and-cdb)
  - [7.3 ELSFP Memory mapping](#73-elsfp-memory-mapping)
    - [7.3.1 ELSFP constants](#731-elsfp-constants)
    - [7.3.2 ElsfpPage classes](#732-ElsfpPage-classes)
    - [7.3.3 ElsfpMemMap class](#733-ElsfpMemMap-class)
    - [7.3.4 Custom Page remapping and vendor extensions](#734-custom-page-remapping-and-vendor-extensions)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG Model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test Cases](#131-unit-test-cases)
  - [13.2 System Test Cases](#132-system-test-cases)
- [14. Files Changed Summary](#14-files-changed-summary)
- [15. Code Changes](#15-code-changes)
- [References](#references)

### 1. Revision  

| Rev | Date       | Author | Change Description |
|-----|------------|--------|--------------------|
| 0.1 | 2025-02-03 | abhi-nexthop      | Initial version    |


### 2. Scope  

This high-level design document describes the design for adding paging support in CMIS memory maps and ELSFP support in SONiC.

### 3. Definitions/Abbreviations 

| Term | Definition |
|------|------------|
| CMIS | Common Management Interface Specification |
| I2C | Inter-Integrated Circuit |
| ELSFP | External Laser Small Form Factor Pluggable |

### 4. Overview 

The CMIS spec provides the memory layout for certain i2c transceivers. This layout consists of a fixed lower memory, and a paged upper memory. The upper memory has certain pages that are banked, providing a 3D memory layout for the device.

While SONiC does not currently provide banking support, it has been proposed in the [Banking HLD](https://github.com/sonic-net/SONiC/pull/2183) PR and this document depends on it.

CMIS layout (Taken from the Banking HLD PR):

| Memory Region | Address Range | Description |
|---------------|---------------|-------------|
| Lower Memory  | 0x00 - 0x7F   | Fixed, always accessible (128 bytes) |
| Upper Memory  | 0x80 - 0xFF   | Paged (128 bytes). Only certain pages support banking |

The ELSFP-CMIS spec is an extension of CMIS that provides memory specification for External Laser Sources. This is critical for emerging technologies such as CPO where optical engines and laser sources are used instead.

ELSFP describes Upper memory CMIS pages it supports in its memory map. Existing CMIS pages used:

| Page | Description |
|------|-------------|
| 0x00 | Administrative Information |
| 0x01 | Advertising |
| 0x02 | Threshold Information |
| 0x03 | User NV RAM |
| 0x9F | CDB Command/Response with local payload |
| A0-AF | CDB EPL extended payload segments |


While, SONiC registers these paged registers, it does not explicitly sort them in individual pages. As the CMIS spec grows and new specs that branch off CMIS are defined (such as ELSFP and C-CMIS) , more registers may be added and the memory map will continue to grow. Furthermore, currently, other memory classes such as the CCmisMemMap inherit the CMIS memory map and add their own registers. However, not all pages in the CMIS memory map are used by every device. For example, if an ELSFPMemoryMap object derives from the CMIS memory map, it will contain registers from pages that do not comply to the ELSFP spec. Therefore, there is a need to explicitly define pages and provide the ability to pick a subset of CMIS pages for a memory map.

In addition, the ELSFP spec describes new pages that are not currently implemented in SONiC and these will need to be defined

| Page | Description |
|------|-------------|
| 0x1A | ELSFP Advertisements, Flags |
| 0x1B | ELSFP Controls and Monitors |

### 5. Requirements

### Functional Requirements

1. Support paging in CMIS memory maps
2. Add ELSFP memory map and pages in SONiC

### Non-Functional Requirements

1. Existing maps should expose the same named fields at the same EEPROM offsets, so that `XcvrApi` consumers require no changes.
2. Easy remapping of pages to another page

### 6. Architecture Design 

This design depends on the implementation of the [Banking HLD](https://github.com/sonic-net/SONiC/pull/2183). The changes in this design however, do not affect the SONiC architecture. Rather, these changes are limited to a refactoring of the CMIS memory map to support paging and the addition of ELSFP pages.

### 7. High-Level Design 

### 7.1 Repositories Changed

All changes are in `sonic-platform-common`, under `sonic_platform_base/sonic_xcvr/`. The former `mem_maps/public/cmis.py` module becomes a `mem_maps/public/cmis/` package so that page classes, the C-CMIS and CDB maps, and the ELSFP map can live alongside the base CMIS map. `mem_maps/public/cmis/__init__.py` re-exports `CmisFlatMemMap` and `CmisMemMap`, so existing `from ...mem_maps.public.cmis import CmisMemMap` imports keep resolving.

| Change Type | Files |
|-------------|-------|
| Moved into package | `mem_maps/public/cmis.py` -> `mem_maps/public/cmis/cmis.py`, `mem_maps/public/c_cmis.py` -> `mem_maps/public/cmis/c_cmis.py`, `mem_maps/public/cdb.py` -> `mem_maps/public/cmis/cdb.py` |
| Added (CMIS pages) | `mem_maps/public/cmis/__init__.py`, `mem_maps/public/cmis/pages/__init__.py`, `mem_maps/public/cmis/pages/page.py`, `mem_maps/public/cmis/pages/consts.py`, `mem_maps/public/cmis/pages/page00_lower.py`, `page00_upper.py`, `page00_cdb.py`, `page01.py`, `page02.py`, `page04.py`, `page10.py`, `page11.py`, `page12.py`, `page13.py`, `page2f.py`, `page34.py`, `page35.py`, `page9f.py`, `page9f_cdb.py` |
| Added (ELSFP) | `mem_maps/public/cmis/elsfp/__init__.py`, `mem_maps/public/cmis/elsfp/elsfp.py`, `mem_maps/public/cmis/elsfp/pages/__init__.py`, `mem_maps/public/cmis/elsfp/pages/consts.py`, `mem_maps/public/cmis/elsfp/pages/page1a.py`, `mem_maps/public/cmis/elsfp/pages/page1b.py`, `fields/elsfp_consts.py`, `codes/public/elsfp.py` |
| Modified (import path or page conversion) | `api/public/cmis.py`, `xcvr_api_factory.py`, `mem_maps/amphenol/backplane.py`, `mem_maps/credo/aec_800g.py`, `codes/public/cmis.py`, `fields/consts.py`, `setup.py` |
| Tests | `tests/sonic_xcvr/test_cmis.py`, `test_ccmis.py`, `test_cdb.py`, `test_sfp_optoe_base.py` (modified), `tests/sonic_xcvr/test_elsfp.py` (added) |

### 7.2 Memory Map Abstraction Changes (cmis package)

All paths in this section are relative to `sonic_platform_base/sonic_xcvr/`.

#### 7.2.1 Page constants

**File**: `mem_maps/public/cmis/pages/consts.py`

Layout constants matching the optoe driver.

```python
# Constants matching optoe driver
CMIS_EEPROM_PAGE_SIZE = 128
CMIS_NUM_NON_BANKED_PAGES = 16   # pages 00h-0Fh
CMIS_ARCH_PAGES = 256            # architectural pages per bank

# CMIS page number constants
ADMINISTRATIVE_PAGE = 0x00
ADVERTISING_PAGE = 0x01
THRESHOLDS_PAGE = 0x02
...
```

#### 7.2.2 The CmisPage class

**File**: `mem_maps/public/cmis/pages/page.py`

A new base class `CmisPage` represents a single page in the CMIS memory map. It stores its page and bank numbers, owns a dictionary of field contributions keyed by `RegGroupField` name, and computes linear EEPROM offsets and and registers its fields onto a parent memory map.

The address calculation lives in the static method `linear_offset`, so that tests and callers without a page instance can use the same formula. `getaddr` is the instance-bound convenience wrapper. The formula follows the optoe driver layout: each bank is a full 256-page block.

```python
class CmisPage(XcvrMemMap):
    fields: Dict[str, List[XcvrField]]  # RegGroupField name -> list of member fields

    def __init__(self, codes, page, bank=0):
        super(CmisPage, self).__init__(codes)
        self._page = page
        self._bank = bank
        self.fields = {}

    @property
    def page(self):
        return self._page

    @property
    def bank(self):
        return self._bank

    @staticmethod
    def linear_offset(page, bank, offset, page_size=128):
        if page == 0 and offset < 128:
            # Lower memory: not affected by paging or banking
            return offset
        if page < CMIS_NUM_NON_BANKED_PAGES or 0x9F <= page <= 0xAF:
            bank = 0
        return (bank * CMIS_ARCH_PAGES + page) * page_size + offset

    def getaddr(self, offset, page_size=128):
        return CmisPage.linear_offset(self._page, self._bank, offset, page_size)

    def get_field_values(self, field: str):
        return self.fields[field]

    def register_fields(self, memmap):
        for key, contribs in self.fields.items():
            if not contribs:
                continue
            existing = getattr(memmap, key, None)
            field_key = key
            field_values = contribs
            if isinstance(existing, RegGroupField):
                field_key = existing.name
                field_values = sorted(
                    list(existing.fields) + list(contribs),
                    key=lambda f: f.get_offset(),
                )
            setattr(memmap, key, RegGroupField(field_key, *field_values))
```

#### 7.2.3 New CMIS pages

**Files**: `mem_maps/public/cmis/pages/page*.py`

All registers previously declared inline in `CmisFlatMemMap` and `CmisMemMap` are moved into one page class per module. Field names and EEPROM offsets are unchanged; only the field-declaration site moves. Page 00h is split into two classes because its lower half (offsets 0-127) is fixed memory and its upper half (offsets 128-255) is paged.

| Module | Class | Page |
|--------|-------|------|
| `page00_lower.py` | `CmisAdministrativeLowerPage` | 00h lower |
| `page00_upper.py` | `CmisAdministrativeUpperPage` | 00h upper |
| `page01.py` | `CmisAdvertisingPage` | 01h |
| `page02.py` | `CmisThresholdsPage` | 02h |
...

Two constructor conventions are used, depending on whether the page can be banked:

- Non-banked pages (00h-0Fh) take `(codes, page=<default>)` and always pass `bank=0` to `CmisPage`.
- Banked pages (10h and above) take `(codes, bank=0, page=<default>)`.

```python
class CmisAdvertisingPage(CmisPage):  # 01h, non-banked
    def __init__(self, codes, page=ADVERTISING_PAGE):
        super().__init__(codes, page=page, bank=0)
        self.fields[consts.ADVERTISING_FIELD] = [
            NumberRegField(consts.INACTIVE_FW_MAJOR_REV, self.getaddr(128), format="B", size=1),
            NumberRegField(consts.INACTIVE_FW_MINOR_REV, self.getaddr(129), format="B", size=1),
            ...
        ]
        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_SUPPORT, self.getaddr(163),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range(6, 8))
            ),
            ...
        ]

class CmisCdbMessagePage(CmisPage):  # 9Fh, banked constructor (bank clamped to 0 by linear_offset)
    def __init__(self, codes, bank=0, page=CDB_MESSAGE_PAGE):
        super().__init__(codes, page=page, bank=bank)
        # TRANS_CDB_FIELD contribution from page 9Fh; merged with the page 01h contribution
        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_RPL_LENGTH, self.getaddr(134), size=1, ro=False),
            NumberRegField(consts.CDB_RPL_CHKCODE, self.getaddr(135), size=1, ro=False),
        ]
        ...
```

#### 7.2.4 The CmisFlatMemMap and CmisMemMap classes

**File**: `mem_maps/public/cmis/cmis.py`

`CmisFlatMemMap` becomes the container for pages. It owns the `pages` list, the `add_pages` helper and the `bank` property, and composes only the two halves of page 00h. `CmisMemMap` inherits it and adds the upper pages. Only banked pages receive the `bank` argument.

```python
class CmisFlatMemMap(XcvrMemMap):
    def __init__(self, codes, bank=0):
        self._bank = bank
        super(CmisFlatMemMap, self).__init__(codes)
        self.pages = []
        self.add_pages(
            CmisAdministrativeLowerPage(codes),
            CmisAdministrativeUpperPage(codes),
        )

    def add_pages(self, *pages):
        self.pages.extend(pages)
        for page in pages:
            page.register_fields(self)
        # XcvrMemMap caches _fields on first get_field(); invalidate so newly
        # registered RegGroupFields are picked up on the next lookup.
        self._fields = None

    @property
    def bank(self):
        return self._bank


class CmisMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        super(CmisMemMap, self).__init__(codes, bank=bank)
        self.add_pages(
            CmisAdvertisingPage(codes),                           # 0x01
            CmisThresholdsPage(codes),                            # 0x02
            CmisLaneDatapathConfigPage(codes, bank=bank),         # 0x10
            ...          # 0x9F
        )
```

#### 7.2.5 Derived memory maps: C-CMIS and CDB

The other memory maps that previously subclassed `CmisMemMap` or defined CMIS-addressed fields inline are converted to the same page scheme, so that every CMIS-derived map declares its contents as a list of pages.

**C-CMIS** (`mem_maps/public/cmis/c_cmis.py`): `CCmisMemMap` still inherits `CmisMemMap` and adds the C-CMIS specific pages via `add_pages`. The field definitions move to `CCmisModuleConfigSupportPage` (04h), `CCmisMediaLaneFecPmPage` (34h) and `CCmisMediaLaneLinkPmPage` (35h).

```python
class CCmisMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super(CCmisMemMap, self).__init__(codes, bank=bank)
        self.add_pages(
            CCmisModuleConfigSupportPage(codes, bank=bank),  # 0x04
            CCmisMediaLaneFecPmPage(codes, bank=bank),       # 0x34
            CCmisMediaLaneLinkPmPage(codes, bank=bank),      # 0x35
        )
```

**CDB** (`mem_maps/public/cmis/cdb.py`): `CdbMemMap` is not a `CmisFlatMemMap`, but it addresses CMIS pages 00h and 9Fh. Its fields move to two page classes, `CdbAdminStatusPage` (the CDB1 status byte at page 00h offset 37) and `CdbLplMessagePage` (query status, firmware info and firmware management features in the page 9Fh LPL area). `CdbMemMap` carries its own `add_pages` helper identical to the one on `CmisFlatMemMap`.

```python
class CdbMemMap(XcvrMemMap):
    def __init__(self, codes):
        super(CdbMemMap, self).__init__(codes)
        self.cdb_cmds = {}
        self.pages = []
        self.add_pages(
            CdbAdminStatusPage(codes),   # 0x00, CDB1 status byte
            CdbLplMessagePage(codes),    # 0x9F, LPL message area
        )
```

### 7.3 ELSFP Memory mapping

#### 7.3.1 ELSFP constants

**File**: `sonic_platform_base/sonic_xcvr/fields/elsfp_consts.py`

New constant values are added for ELSFP registers in a new file.

```python

# page 0x1A
# ELSFP Advertisements 
OPTICAL_POWER_FIELD = "OpticalPower"
MAX_OPTICAL_POWER = "MaxOpticalPower"
MIN_OPTICAL_POWER = "MinOpticalPower"

LASER_BIAS_FIELD = "LaserBias"
MIN_LASER_BIAS = "MinLaserBias"
MAX_LASER_BIAS = "MaxLaserBias"
...
# Lane fault and warnings
FAULT_FLAG_LANE_FIELD = "FaultFlagLane"
...
# Lane setting and saving and restoring factory/customer settings
SAVE_RESTORE_FIELD = "SaveRestore"
SAVE_RESTORE_COMMAND = "SaveRestoreCommand"
SAVE_RESTORE_CONFIRM = "SaveRestoreConfirm"
# Alarms/warnings values, alarm/warning codes and masks for set lane bank
...
# Per lane enable/disable control and lane state for set lane bank
...
# Per lane output fiber link checked flag for selected lane bank 
...
# Additional per lane information 


# page 0x1B
# ELSFP Controls and Monitors 
BIAS_CURRENT_SETPOINT_FIELD = "BiasCurrentSetpoint"
OPT_POWER_SETPOINT_FIELD = "OptPowerSetpoint"
...
```

#### 7.3.2 ElsfpPage classes

**Files**: `sonic_platform_base/sonic_xcvr/mem_maps/public/cmis/elsfp/pages/page1a.py`, `mem_maps/public/cmis/elsfp/pages/page1b.py`, `mem_maps/public/cmis/elsfp/pages/consts.py`

Two new pages are created. The ElsfpAdvertisementsFlagsPage and the ElsfpControlsMonitorsPage corresponding to page 0x1A and 0x1B respectively. These will require the bank parameter in their constructor.

```python
class ElsfpAdvertisementsFlagsPage(CmisPage): #0x1A
    def __init__(codes, page=0x1A, bank=0):
        super(ElsfpAdvertisementsFlagsPage, self).__init__(codes, page, bank)
        self.fields[elsfp_consts.OPTICAL_POWER_FIELD] = [
          NumberRegField(elsfp_consts.MAX_OPTICAL_POWER, self.getaddr(128), size=2, ro=True),
          NumberRegField(elsfp_consts.MIN_OPTICAL_POWER, self.getaddr(130), size=2, ro=True),
        ]
        self.fields[elsfp_consts.LASER_BIAS_FIELD] = [
          NumberRegField(elsfp_consts.MAX_LASER_BIAS, self.getaddr(132), size=2, ro=True),
          NumberRegField(elsfp_consts.MIN_LASER_BIAS, self.getaddr(134), size=2, ro=True),
        ]
        .
        .
        .
        # How one would register 32 lanes, one per bit
        self.fields[elsfp_consts.FAULT_FLAG_LANE_FIELD] = [
          NumberRegField(elsfp_consts.FAULT_FLAG_LANE, self.getaddr(166),
              *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 32))
          )
        ]
        .
        .
        .

class ElsfpControlsMonitorsPage(CmisPage): #0x1B
    def __init__(codes, page=0x1B, bank=0):
        super(ElsfpControlsMonitorsPage, self).__init__(codes, page, bank)
        
        # Setpoint1 to Setpoint8, 2 bytes each
        self.fields[elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD] = [
          *(NumberRegField("%s%d" % (elsfp_consts.BIAS_CURRENT_SETPOINT, lane_number), self.getaddr(128), size=2, ro=False) for lane_number in range (0, 9)),
        ]
        .
        .
        .

```
#### 7.3.3 ElsfpMemMap class

The ElsfpMemMap will only take a subset of CMIS pages and add the ELSFP pages. It will also accept the bank parameter in its constructor.

```python
class ElsfpMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        super(ElsfpMemMap, self).__init__(codes, bank=bank)
        self.add_pages(
            # CMIS pages applicable to ELSFP
            CmisAdvertisingPage(codes),                   # 0x01
            CmisThresholdsPage(codes),                    # 0x02
            # ELSFP pages
            ElsfpAdvertisementsFlagsPage(codes, bank=bank),  # 0x1A
            ElsfpControlsMonitorsPage(codes, bank=bank),     # 0x1B
            .
            .
            .
        )
```

#### 7.3.4 Custom Page remapping and vendor extensions

Because every page class takes its page number as a constructor argument, a page can be remapped or duplicated without re-declaring its fields, and vendor-specific fields can be added by declaring a small `CmisPage` subclass and registering it with `add_pages`. Fields that a vendor page contributes to an existing `RegGroupField` are merged by `register_fields`.

**Remapping an existing page.** Consider Device 1 that controls Device 2, where Device 2's advertising page is exposed on the vendor-reserved page B0h of Device 1:

```python
class Device2AdvertisingPage(CmisAdvertisingPage):
    def __init__(self, codes, page=0xB0):
        # Same fields as CMIS page 01h, addressed on page 0xB0
        super().__init__(codes, page=page)

class Device1MemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super().__init__(codes, bank=bank)
        self.add_pages(Device2AdvertisingPage(codes))

### 8. SAI API

This does not affect SAI API.

### 9. Configuration and management 

No config changes as this remapping of existing memory is opaque to users.

#### 9.1. Manifest (if the feature is an Application Extension)

Not applicable.

#### 9.2. CLI/YANG model Enhancements 

No CLI changes.

#### 9.3. Config DB Enhancements  

No config changes.
		
### 10. Warmboot and Fastboot Design Impact  

No impact on warmboot and fastboot.

### 11. Memory Consumption

No significant memory consumption impact. The overhead of new classes is minimal.

### 12. Restrictions/Limitations  

1. Applies to CMIS devices only
2. Depends on Banking HLD to be implemented

### 13. Testing Requirements/Design  

#### 13.1. Unit Test cases  

Existing tests should continue to pass without changes in
`sonic-platform-common/tests/sonic_xcvr/test_cmis.py`

Add new tests for ELSFP memory map. in
`sonic-platform-common/tests/sonic_xcvr/test_elsfp.py`

register ELSFPMemoryMap with XcvrEeprom across different bank numbers like in test_cmis.py
- Read/Write supported CMIS pages
- Read/Write to supported ELSFP pages
- Attempt Read/Write to unsupported CMIS pages and expect exceptions

#### 13.2. System Test cases

No regression in existing XcvrApi operations.

### 14. Files Changed Summary

All paths are relative to `sonic-platform-common/sonic_platform_base/sonic_xcvr/` unless noted.

| File Path | Change Type | Description |
|-----------|-------------|-------------|
| `mem_maps/public/cmis/__init__.py` | Added | Package init; re-exports `CmisFlatMemMap`, `CmisMemMap` and layout constants so existing imports keep working |
| `mem_maps/public/cmis/cmis.py` | Moved + Modified | `CmisFlatMemMap` and `CmisMemMap` refactored into page containers with `add_pages` |
| `mem_maps/public/cmis/c_cmis.py` | Moved + Modified | `CCmisMemMap` composes pages 04h, 34h, 35h via `add_pages` |
| `mem_maps/public/cmis/cdb.py` | Moved + Modified | `CdbMemMap` composes `CdbAdminStatusPage` and `CdbLplMessagePage` |
| `mem_maps/public/cmis/pages/page.py` | Added | `CmisPage` base class: `linear_offset`, `getaddr`, `register_fields` |
| `mem_maps/public/cmis/pages/consts.py` | Added | CMIS layout constants and page-number constants |
| `mem_maps/public/cmis/pages/page*.py` | Added | One module per CMIS / C-CMIS / CDB page (00h lower, 00h upper, 00h CDB, 01h, 02h, 04h, 10h-13h, 2Fh, 34h, 35h, 9Fh, 9Fh CDB) |
| `mem_maps/public/cmis/pages/__init__.py` | Added | Re-exports all page classes and constants |
| `mem_maps/public/cmis/elsfp/elsfp.py` | Added | `ElsfpMemMap` composing pages 01h, 02h, 1Ah, 1Bh, 2Fh, 9Fh |
| `mem_maps/public/cmis/elsfp/pages/page1a.py` | Added | `ElsfpAdvertisementsFlagsCtrlPage` (page 1Ah) |
| `mem_maps/public/cmis/elsfp/pages/page1b.py` | Added | `ElsfpSetpointsMonitorsPage` (page 1Bh) |
| `mem_maps/public/cmis/elsfp/pages/consts.py` | Added | ELSFP page-number constants |
| `mem_maps/public/cmis/elsfp/__init__.py`, `elsfp/pages/__init__.py` | Added | Package inits and re-exports |
| `fields/elsfp_consts.py` | Added | ELSFP field-name constants |
| `codes/public/elsfp.py` | Added | `ElsfpCodes(CmisCodes)` with ELSFP code tables |
| `codes/public/cmis.py` | Modified | Adds `MODULE_FUNCTION_TYPE` codes and ELSFP-related VDM observable types |
| `fields/consts.py` | Modified | Adds `MODULE_FUNCTION_TYPE` and `EXTENDED_MODULE_INFO_FIELD` |
| `mem_maps/amphenol/backplane.py`, `mem_maps/credo/aec_800g.py` | Modified | Vendor maps converted to private `CmisPage` subclasses registered via `add_pages` |
| `api/public/cmis.py`, `xcvr_api_factory.py` | Modified | Import paths updated for the `cmis/` package |
| `sonic-platform-common/setup.py` | Modified | Registers the new `cmis`, `cmis.pages`, `cmis.elsfp`, `cmis.elsfp.pages` packages |
| `sonic-platform-common/tests/sonic_xcvr/test_cmis.py`, `test_ccmis.py`, `test_cdb.py`, `test_sfp_optoe_base.py` | Modified | Import paths and address-calculation tests moved to `CmisPage.linear_offset` |
| `sonic-platform-common/tests/sonic_xcvr/test_elsfp.py` | Added | Unit tests for `ElsfpMemMap` and `ElsfpCodes` |

### 15. Code Changes

The implementation is split into the following pull requests:

| PR # | Description | Repository | Link |
|------|-------------|------------|------|
| PR 1 | Memory Map Refactor into pages | sonic-platform-common | [sonic-net/sonic-platform-common#667](https://github.com/sonic-net/sonic-platform-common/pull/667) |
| PR 2 | ELSFP pages and Memory Map | sonic-platform-common | [sonic-net/sonic-platform-common#678](https://github.com/sonic-net/sonic-platform-common/pull/678) |



## References
- [OIF CMIS 5.3 Specification](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)
- [OIF ELSFP CMIS 1.0 Specification](https://www.oiforum.com/wp-content/uploads/OIF-ELSFP-CMIS-01.0.pdf)
