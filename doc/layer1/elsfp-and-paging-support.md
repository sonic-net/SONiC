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
  - [7.2 Memory Map Abstraction Changes (cmis.py)](#72-memory-map-abstraction-changes-cmispy)
    - [7.2.1 The CmisPage class](#721-the-cmispage-class)
    - [7.2.2 New CMIS pages](#722-new-cmis-pages)
    - [7.2.3 The CmisMemMap class](#723-the-cmismemmap-class)
  - [7.3 ELSFP Memory mapping](#73-elsfp-memory-mapping)
    - [7.3.1 ELSFP constants](#731-elsfp-constants)
    - [7.3.2 ElsfpPage classes](#732-ElsfpPage-classes)
    - [7.3.3 ElsfpMemMap class](#733-ElsfpMemMap-class)
    - [7.3.4 Custom Page remapping](#734-custom-page-remapping)
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

1. Existing maps should remain functionally identical and cause no API changes
2. Easy remapping of pages to another page

### 6. Architecture Design 

This design depends on the implementation of the [Banking HLD](https://github.com/sonic-net/SONiC/pull/2183). The changes in this design however, do not affect the SONiC architecture. Rather, these changes are limited to a refactoring of the CMIS memory map to support paging and the addition of ELSFP pages.

### 7. High-Level Design 

### 7.1 Repositories Changed

| Repository | Files Modified |
|------------|----------------|
| sonic-platform-common | `sonic_xcvr/mem_maps/public/cmis.py` |


| Repository | Files Added |
|------------|----------------|
| sonic-platform-common | `sonic_xcvr/mem_maps/public/elsfp.py`, `sonic_xcvr/fields/elsfp_consts.py` |

### 7.2 Memory Map Abstraction Changes (cmis.py)

**File**: `src/sonic-platform-common/sonic_platform_base/sonic_xcvr/mem_maps/public/cmis.py`

#### 7.2.1 The CmisPage class

A new base class called the CmisPage is defined. This represents a single page in the CMIS memory map. It uses the same, banking compliant address calculation as CmisMemMap as defined in the Banking HLD, with the page and bank parameters being derived from the class member.
It provides a getter for fields that are defined in the page.

```python
class CmisPage(XcvrMemMap):
    fields = Dict[str, list[RegField]] # This is a Dictionary of list of fields
    def __init__(codes, page, bank):
      super(XcvrMemMap, self).__init__(codes)
      self._page = page
      self._bank = bank

    def getaddr(self, offset, page_size=128):
        if self._page == 0 and offset < 128:
            # Lower memory - not affected by banking
            return offset

        if self._bank == 0:
            # Bank 0: standard linear offset
            return self._page * page_size + offset
        else:
            # Banks 1+: only pages 10h-FFh (0x10+) are banked
            # Pages < 0x10 are never banked, even for bank > 0
            if self._page < 0x10:
                # Non-banked pages (00h-0Fh): same as bank 0
                return self._page * page_size + offset
            else:
                # Banked pages (10h-FFh): offset by bank * OPTOE_BANKED_PAGE_SIZE pages
                return ((self._bank * OPTOE_BANKED_PAGE_SIZE) + self._page) * page_size + offset

    def get_field_values(field : str):
        return self.fields[field]
```
#### 7.2.2 New CMIS pages

All pages registered in CmisMemMap are moved to their respective page classes.

Existing CMIS registers are grouped into their respective pages. For example, registers for CmisMemMap.ADVERTISING are moved to a AdvertisingCmisPage with the page number hardcoded to 0x01.

```python
  class CmisAdvertisingPage(CmisPage): #0x01
	    def __init__(codes, page=0x01, bank=0):
        super(CmisAdvertisingPage, self).__init__(codes, page, bank)
		        self.fields[consts.TRANS_CDB_FIELD] = [
              # Page number not required, only offset provided
              NumberRegField(consts.CDB_SUPPORT, self.getaddr(163),
                  *(RegBitField("Bit%d" % (bit), bit) for bit in range (6, 8))
              ),
              .
              .
              .
            ]
            self.fields[consts.ADVERTISING_FIELD] = [
                        NumberRegField(consts.INACTIVE_FW_MAJOR_REV, self.getaddr(128), format="B", size=1),
                        NumberRegField(consts.INACTIVE_FW_MINOR_REV, self.getaddr(129), format="B", size=1),
              .
              .
              .
            ]
  class CmisCdbMessagePage(CMISPage): #0x9F
    def __init__(codes, page=0x9F, bank=0):
        super(CmisCdbMessagePage, self).__init__(codes, page, bank)
        self.fields[consts.TRANS_CDB_FIELD] = [
          NumberRegField(consts.CDB_RPL_LENGTH, self.getaddr(134), size=1, ro=False),
          NumberRegField(consts.CDB_RPL_CHKCODE, self.getaddr(135), size=1, ro=False),
          .
          .
          .
        ]
        .
        .
        .

```
#### 7.2.3 The CmisMemMap class

The CmisMemMap class is refactored to be a container for CmisPage objects, while remaining functionally identical. A helper is added to get fields from multiple pages at once, since a single field may have registers across multiple pages.

```python
class CmisMemMap(XcvrMemMap):
    def get_field_from_pages(self, field_name, *pages):
        fields = []
        for page in pages:
            fields.extend(page.get_field_values(field_name))
        return fields

    def __init__(self, codes):
        super(CmisMemMap, self).__init__(codes)
        #CMIS pages
        self.administrative_upper_page = CMISAdministrativeUpperPage(codes) #0x00U
        self.advertising_page = CMISAdvertisingPage(codes) #0x01
        .
        .
        .
        self.cdb_message_page = CMISCDBMessagePage(codes) #0x9F
        self.TRANS_CDB= RegGroupField(consts.TRANS_CDB_FIELD,
            *self.get_field_from_pages(consts.TRANS_CDB_FIELD, self.advertising_page, self.cdb_message_page)
        )

        self.ADVERTISING = RegGroupField(consts.ADVERTISING_FIELD,
            *self.get_field_from_pages(consts.ADVERTISING_FIELD, self.advertising_page)
        )
        .
        .
        .
```

### 7.3 ELSFP Memory mapping

#### 7.3.1 ELSFP constants

**File**: `src/sonic-platform-common/sonic_platform_base/sonic_xcvr/fields/elsfp_consts.py`

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

**File**: `src/sonic-platform-common/sonic_platform_base/sonic_xcvr/mem_maps/public/elsfp.py`

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
    def __init__(self, codes, bank):
        super(ElsfpMemMap, self).__init__(codes, bank)
        #CMIS pages
        self.administrative_upper_page = CMISAdministrativeUpperPage(codes, bank=bank)
        self.advertising_page = CMISAdvertisingPage(codes, bank=bank)
        .
        .
        .
        #CMIS field registration
        self.ADVERTISING = RegGroupField(consts.ADVERTISING_FIELD,
            *self.get_field_from_pages(consts.ADVERTISING_FIELD, self.advertising_page)
        )
        .
        .
        .

        #ELSFP pages
        self.elsfp_advertisements_flags_page = ElsfpAdvertisementsFlagsPage(codes)
        self.elsfp_controls_monitors_page = ElsfpControlsMonitorsPage(codes)
        .
        .
        .
        #ELSFP field registration
        self.OPTICAL_POWER = RegGroupField(elsfp_consts.OPTICAL_POWER_FIELD,
            *self.elsfp_advertisements_flags_page.get_field_values(elsfp_consts.OPTICAL_POWER_FIELD)
        )
        self.LASER_BIAS = RegGroupField(elsfp_consts.LASER_BIAS_FIELD,
            *self.elsfp_advertisements_flags_page.get_field_values(elsfp_consts.LASER_BIAS_FIELD)
        )
        .
        .
        self.BIAS_CURRENT_SETPOINT = RegGroupField(elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD,
            *self.elsfp_controls_monitors_page.get_field_values(elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD)
        )
        .
        .
        .

```

#### 7.3.4 Custom Page remapping

The mechanism described here enables one to remap pages or duplicate pages for vendor specific implementations.

For example, consider Device 1 that controls Device 2. Device 2's advertising page is mapped onto a vendor reserved page B0.

This is how a vendor may implement this:

```python

class Device2AdvertisingPage(CmisAdvertisingPage):
    def __init__(codes, page=0xB0, bank=0):
        # Device 2's advertising page which is set to 0x01 ny default is mapped onto page 0xB0
        super(Device2AdvertisingPage, self).__init__(codes, page, bank)
        .
        .
        .
  
class Device1MemMap(CmisMemMap):
    def __init__(self, codes, bank):
        super(Device1MemMap, self).__init__(codes, bank)
        .
        .
        .
        self.device2_advertising_page = Device2AdvertisingPage(codes)
        .
        .
        .
```

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


## References
- [OIF CMIS 5.3 Specification](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)
- [OIF ELSFP CMIS 1.0 Specification](https://www.oiforum.com/wp-content/uploads/OIF-ELSFP-CMIS-01.0.pdf)
