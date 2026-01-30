# I2C Transceiver Page Banking Support HLD

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Repositories Changed](#71-repositories-changed)
  - [7.2 Kernel Driver Changes (optoe.c)](#72-kernel-driver-changes-optoec)
  - [7.3 Memory Map Abstraction Changes (cmis.py)](#73-memory-map-abstraction-changes-cmispy)
  - [7.5 CLI Utility Changes (sfputil)](#75-cli-utility-changes-sfputil)
  - [7.6 Linear Offset Calculation](#76-linear-offset-calculation)
  - [7.7 Backwards Compatibility](#77-backwards-compatibility)
  - [7.8 API Design for Multi-Bank Modules](#78-api-design-for-multi-bank-modules)
  - [7.9 DB and Schema Changes](#79-db-and-schema-changes)
  - [7.10 SWSS and Syncd Changes](#710-swss-and-syncd-changes)
  - [7.11 Sequence Diagram](#711-sequence-diagram)
  - [7.12 Implementation Phases](#712-implementation-phases)
  - [7.13 Platform Dependencies](#713-platform-dependencies)
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

## 1. Revision

| Rev | Date       | Author | Change Description |
|-----|------------|--------|--------------------|
| 0.1 | 2026-01-20 | bobby-nexthop      | Initial version    |

## 2. Scope

This high-level design document describes the implementation of page banking support for I2C transceivers (CMIS devices) in SONiC. Currently, the optoe kernel driver only supports Bank 0 pages. This enhancement enables access to all banks as defined in the CMIS specification, which is required for multi-lane modules with more than 8 lanes.

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| CMIS | Common Management Interface Specification |
| I2C | Inter-Integrated Circuit |
| QSFP-DD | Quad Small Form Factor Pluggable Double Density |
| OSFP | Octal Small Form Factor Pluggable |
| VDM | Versatile Diagnostics Monitoring |
| SFP-DD | Small Form Factor Pluggable Double Density |
| optoe | Optical Transceiver Open EEPROM driver |

## 4. Overview

The CMIS specification defines a 3D memory addressing scheme using Bank Select (byte 0x7E) and Page Select (byte 0x7F) registers. The current SONiC implementation only supports Bank 0, limiting access to lane-specific registers for modules with more than 8 lanes.

### CMIS Memory Architecture

| Memory Region | Address Range | Description |
|---------------|---------------|-------------|
| Lower Memory  | 0x00 - 0x7F   | Fixed, always accessible (128 bytes) |
| Upper Memory  | 0x80 - 0xFF   | Paged (128 bytes). Only certain pages support banking (see below) |

**Note**: Not all upper memory pages support banking. According to the CMIS specification, only the following page ranges can be banked:
- Pages 0x10 to 0x1F (lane-specific registers)
- Pages 0x20 to 0x2F (VDM and lane-specific data)
- Page 0x9F
- Pages 0xA0 to 0xAF

Other upper memory pages (e.g., 0x00-0x0F, 0x30-0x9E) are not bankable and always refer to Bank 0.

### Control Registers

| Register | Address | Purpose |
|----------|---------|---------|
| Bank Select | 0x7E (byte 126) | Selects active bank |
| Page Select | 0x7F (byte 127) | Selects active page within bank |

### Banking Use Cases

- **Lane-specific registers**: Pages 10h-1Fh, 20h-2Fh and 0x30-0x3F
  - Bank 0: Lanes 1-8
  - Bank 1: Lanes 9-16
  - Bank 2: Lanes 17-24, etc.
- **VDM (Vendor Diagnostic Monitoring)**: Pages 20h-2Fh

## 5. Requirements

### Functional Requirements

1. Support reading/writing to banks 0-7 on CMIS devices (per optoe driver limit)
2. Maintain backward compatibility with existing Bank 0 operations
3. Extend CLI utilities to accept bank parameter
4. Update Python xcvr library to support bank-aware field access
5. Auto-detect banking support by reading CMIS Banks Supported field (Page 01h, Byte 155)
6. Use 1-byte I2C writes for transceivers without banking support; 2-byte writes only when banking is advertised

### Non-Functional Requirements

1. Minimize I2C overhead when switching banks
2. No performance degradation for Bank 0 operations
3. Support for all CMIS-compliant transceivers (QSFP-DD, OSFP, SFP-DD)

## 6. Architecture Design

This feature modifies the following components in the SONiC architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Space                                  │
├─────────────────────────────────────────────────────────────────┤
│  sfputil CLI  ──►  sonic_xcvr library  ──►  XcvrEeprom          │
│      │                    │                      │              │
│      │              CmisMemMap.getaddr()         │              │
│      ▼                    ▼                      ▼              │
│  bank parameter    bank-aware offset      read/write with       │
│  in commands       calculation            linear offset         │
├─────────────────────────────────────────────────────────────────┤
│                     Kernel Space                                │
├─────────────────────────────────────────────────────────────────┤
│  optoe.c driver                                                 │
│      │                                                          │
│      ├── optoe_translate_offset() ── calculate bank from offset │
│      │                                                          │
│      └── optoe_eeprom_update_client() ── write bank select reg  │
├─────────────────────────────────────────────────────────────────┤
│                     Hardware                                    │
├─────────────────────────────────────────────────────────────────┤
│  I2C Bus ──► Transceiver EEPROM (Bank Select 0x7E, Page 0x7F)   │
└─────────────────────────────────────────────────────────────────┘
```

No changes to the overall SONiC architecture are required. This feature extends existing transceiver management components.

## 7. High-Level Design

### 7.1 Repositories Changed

| Repository | Files Modified |
|------------|----------------|
| sonic-linux-kernel | `drivers/misc/eeprom/optoe.c` |
| sonic-platform-common | `sonic_xcvr/mem_maps/public/cmis.py`, `sonic_xcvr/fields/xcvr_field.py` |
| sonic-utilities | `sfputil/main.py` |

### 7.2 Kernel Driver Changes (optoe.c)

**File**: `drivers/misc/eeprom/optoe.c`

**Reference Implementation**: [sonic-net/sonic-linux-kernel PR #473](https://github.com/sonic-net/sonic-linux-kernel/pull/473)

**Key Changes**:

#### 7.2.1 New Constants

```c
#define OPTOE_BANK_SELECT_REG         0x7E
#define OPTOE_DEFAULT_BANK_SIZE       0    /* disabled by default */
#define OPTOE_MAX_SUPPORTED_BANK_SIZE 8
#define OPTOE_NON_BANKED_PAGE_SIZE    16   /* pages 00h-0Fh are not banked */
#define OPTOE_BANKED_PAGE_SIZE        240  /* pages 10h-FFh are banked */
```

#### 7.2.2 New sysfs Interface: `bank_size`

A new sysfs entry `bank_size` is added to enable and configure bank support:

- **Default value**: 0 (bank support disabled)
- **Valid range**: 0-8
- **Only applicable to**: `optoe3` device class (CMIS devices)

```c
static ssize_t show_bank_size(struct device *dev,
            struct device_attribute *dattr, char *buf)
{
    /* Returns current bank_size value */
}

static ssize_t set_bank_size(struct device *dev,
            struct device_attribute *attr,
            const char *buf, size_t count)
{
    /* Only supported for CMIS devices (optoe3) */
    if (optoe->dev_class != CMIS_ADDR)
        return -EINVAL;

    /* When enabling bank (bank_size > 0), automatically set write_max to 2
     * to comply with CMIS 5.3 section 8.2.15 which mandates both bank and
     * page values be updated in a single WRITE operation */
    if (optoe->bank_size > 0 && optoe->write_max == 1)
        optoe->write_max = 2;
}
```

**Usage**:
```bash
# Check current bank size
cat /sys/class/i2c-dev/i2c-1/device/1-0050/bank_size

# Enable 4 banks
echo 4 | sudo tee /sys/class/i2c-dev/i2c-1/device/1-0050/bank_size
```

#### 7.2.3 Linear Address Mapping

Banked pages are mapped into a linear address space starting after non-banked pages:

```
+-------------------------------+
|        Lower Page (128 bytes) |  offset 0-127
+-------------------------------+
|  Upper Page (Bank 0, Page 0h) |  offset 128-255
+-------------------------------+
|  Upper Page (Bank 0, Page 1h) |  offset 256-383
+-------------------------------+
|             ...               |
+-------------------------------+
| Upper Page (Bank 0, Page FFh) |  (end of bank 0)
+-------------------------------+
| Upper Page (Bank 1, Page 10h) |  (banked pages start at page 10h)
+-------------------------------+
|             ...               |
+-------------------------------+
| Upper Page (Bank 1, Page FFh) |
+-------------------------------+
| Upper Page (Bank 2, Page 10h) |
+-------------------------------+
|             ...               |
+-------------------------------+
```

**EEPROM size calculation**:
```c
static uint32_t one_addr_eeprom_size_with_bank(uint32_t bank_size)
{
    bank_size = bank_size == 0 ? 1 : bank_size;
    return (bank_size * OPTOE_BANKED_PAGE_SIZE + OPTOE_NON_BANKED_PAGE_SIZE + 1)
           * OPTOE_PAGE_SIZE;
}
```

#### 7.2.4 Bank/Page Calculation from Offset

```c
static uint8_t optoe_translate_offset(struct optoe_data *optoe,
        loff_t *offset, struct i2c_client **client, uint8_t *bank)
{
    unsigned int page = 0;
    /* ... existing offset translation ... */

    page = (*offset >> 7) - 1;
    *offset = OPTOE_PAGE_SIZE + (*offset & 0x7f);

    /* Calculate bank from page number */
    *bank = page < OPTOE_PAGE_SIZE ? 0 :
            (page - OPTOE_NON_BANKED_PAGE_SIZE) / OPTOE_BANKED_PAGE_SIZE;
    page = page - *bank * OPTOE_BANKED_PAGE_SIZE;

    return page;
}
```

#### 7.2.5 CMIS-Compliant Bank/Page Write

Per CMIS 5.3 Section 8.2.15, when changing bank, both bank and page must be written in a single I2C WRITE operation:

```c
if (page > 0) {
    if (optoe->num_banks > 1) {
        /* Multi-bank device: always write both bank and page */
        char buf[2] = {bank, page};
        ret = optoe_eeprom_write(optoe, client, buf,
            OPTOE_BANK_SELECT_REG, 2);
    } else {
        /* Single-bank device: only write page register */
        ret = optoe_eeprom_write(optoe, client, &page,
            OPTOE_PAGE_SELECT_REG, 1);
    }
}
```

### 7.3 Memory Map Abstraction Changes (cmis.py)

**File**: `src/sonic-platform-common/sonic_platform_base/sonic_xcvr/mem_maps/public/cmis.py`

The Python layer must calculate linear offsets that match the optoe driver's address mapping:

```python
# Constants matching optoe driver
OPTOE_PAGE_SIZE = 128
OPTOE_NON_BANKED_PAGE_SIZE = 16   # pages 00h-0Fh
OPTOE_BANKED_PAGE_SIZE = 240      # pages 10h-FFh

# Extended implementation
def getaddr(self, page, offset, page_size=128, bank=0):
    """
    Calculate linear offset for optoe driver.

    For bank 0: linear_offset = (page + 1) * 128 + byte_in_page
    For bank > 0 (pages 10h-FFh only):
        linear_offset = (256 + (bank - 1) * 240 + (page - 16) + 1) * 128 + byte_in_page
    """
    if page == 0 and offset < 128:
        # Lower memory
        return offset

    if bank == 0:
        # Bank 0: pages 00h-FFh
        return (page + 1) * page_size + (offset % page_size)
    else:
        # Banks 1+: only pages 10h-FFh are banked
        # Offset into banked region
        # 1 = lower
        # page = page num
        # bank * OPTOE_BANKED_PAGE_SIZE = num of 'banked pages chunks' to skip to get to our desired page
        return ( ( bank * OPTOE_BANKED_PAGE_SIZE ) + page + 1 ) * page_size + (offset % page_size)
```

### 7.5 CLI Utility Changes (sfputil)

**File**: `src/sonic-utilities/sfputil/main.py`

```python
# Add bank parameter to page dump commands
@click.option('--bank', default=0, type=int, help='Bank number (default: 0)')
def read_eeprom(port, page, bank):
    # Include bank in offset calculation
    pass

@click.option('--bank', default=0, type=int, help='Bank number (default: 0)')
def write_eeprom(port, page, bank):
    # Include bank in offset calculation
    pass
```

### 7.6 Linear Offset Calculation

The optoe driver maps the entire transceiver memory into a linear address space. The mapping accounts for the fact that only pages 0x10-0xFF are banked (240 pages per bank), while pages 0x00-0x0F are not banked (16 pages, always bank 0).

**Constants** (from PR #473):
```c
#define OPTOE_PAGE_SIZE           128   /* bytes per page */
#define OPTOE_NON_BANKED_PAGE_SIZE 16   /* pages 00h-0Fh */
#define OPTOE_BANKED_PAGE_SIZE    240   /* pages 10h-FFh */
```

**Linear Address Space Layout**:
```
Offset Range              | Content
--------------------------|------------------------------------------
0 - 127                   | Lower Memory (128 bytes)
128 - 2175                | Bank 0, Pages 00h-0Fh (non-banked, 16 pages)
2176 - 32895              | Bank 0, Pages 10h-FFh (240 pages)
32896 - 63615             | Bank 1, Pages 10h-FFh (240 pages)
63616 - 94335             | Bank 2, Pages 10h-FFh (240 pages)
...                       | (continues for additional banks)
```

**EEPROM Size Calculation**:
```c
uint32_t eeprom_size = (bank_size * OPTOE_BANKED_PAGE_SIZE
                       + OPTOE_NON_BANKED_PAGE_SIZE + 1) * OPTOE_PAGE_SIZE;

/* For bank_size = 4: (4 * 240 + 16 + 1) * 128 = 125,568 bytes */
```

**To extract bank, page, and byte from linear offset** (from `optoe_translate_offset`):
```c
/* Calculate page from offset */
page = (offset >> 7) - 1;    /* offset / 128 - 1 */
phy_offset = OPTOE_PAGE_SIZE + (offset & 0x7f);  /* 128 + (offset % 128) */

/* Calculate bank from page */
/* Note: OPTOE_PAGE_SIZE (128) here acts as a threshold for virtual page numbers.
 * Virtual pages 0-127 correspond to Bank 0 pages 00h-7Fh, which are always bank 0.
 * Virtual pages 128+ require bank calculation. */
if (page < OPTOE_PAGE_SIZE) {
    bank = 0;  /* Virtual pages 0-127 are always in Bank 0 */
} else {
    bank = (page - OPTOE_NON_BANKED_PAGE_SIZE) / OPTOE_BANKED_PAGE_SIZE;
    page = page - bank * OPTOE_BANKED_PAGE_SIZE;
}
```

**Example**: Accessing Bank 1, Page 0x11, byte 0x82

```
Step 1: Calculate Linear Offset
─────────────────────────────────
Bank 0: 256 pages (00h-FFh) × 128 bytes = 32768 bytes
Bank 0 occupies offsets: 128 to 32895 (after 128-byte lower memory)

Bank 1, Page 10h starts at: 128 + (256 × 128) = 32896
Bank 1, Page 11h starts at: 32896 + 128 = 33024

Byte 0x82 = 130 decimal, which is offset 2 within upper page (130 - 128 = 2)

Linear Offset = 33024 + 2 = 33026

Step 2: Extraction (what optoe driver does)
─────────────────────────────────────────────
page = (33026 >> 7) - 1 = 258 - 1 = 257
phy_offset = 128 + (33026 & 0x7f) = 128 + 2 = 130 (0x82) ✓

bank = (257 - 16) / 240 = 241 / 240 = 1 ✓
adjusted_page = 257 - (1 × 240) = 17 = 0x11 ✓
```

### 7.7 Backwards Compatibility

To ensure backwards compatibility with existing transceivers that may not handle 2-byte I2C writes correctly, the implementation reads the **Banks Supported** field from the transceiver before enabling banking.

#### 7.7.1 CMIS Banks Supported Field

Per CMIS 5.x specification, the Banks Supported field is located at:

| Location | Description |
|----------|-------------|
| Page 01h, Byte 142, Bits 1-0 | Number of banks for lane-specific registers |

**Encoding**:

| Value | Banks Supported |
|-------|-----------------|
| 000b  | 1 bank (Bank 0 only) |
| 001b  | 2 banks |
| 010b  | 4 banks |
| 011b  | 8 banks |

#### 7.7.2 Detection Logic

Before enabling banking, the software performs the following checks:

```python
def get_banks_supported(self):
    """
    Read Banks Supported field from Page 01h, Byte 142, Bits 1-0.
    Returns the number of banks supported (1, 2, 4, or 8).
    """
    banks_supported_raw = self.read_field(consts.BANKS_SUPPORTED_FIELD)
    if banks_supported_raw is None:
        return 1  # Default to Bank 0 only
```

#### 7.7.3 I2C Write Behavior

| Condition | bank_size sysfs | I2C Write Behavior |
|-----------|-----------------|-------------------|
| Banks Supported > 1 | Set to advertised value | 2-byte writes (bank + page) per CMIS 5.3 Section 8.2.15 |
| Banks Supported = 1 or field unreadable | 0 (disabled) | 1-byte writes (page only) - legacy behavior |

This ensures:
1. **New transceivers** with banking support use the 2-byte bank+page writes
2. **Existing transceivers** continue using 1-byte page-only writes, avoiding potential compatibility issues

#### 7.7.4 Field Definition Changes

Add to `sonic_xcvr/fields/consts.py`:

```python
BANKS_SUPPORTED_FIELD = "BanksSupported"
```

Add to `sonic_xcvr/mem_maps/public/cmis.py` in `MODULE_CHAR_ADVT`:

```python
NumberRegField(consts.BANKS_SUPPORTED_FIELD, self.getaddr(0x1, 142),
    *(RegBitField("Bit%d" % bit, bit) for bit in range(0, 2))
),
```

#### 7.7.5 Initialization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  Transceiver Initialization                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Read Page 01h, Byte 155 (Banks Supported)                   │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                            │
│              │ Banks Supported > 1?│                            │
│              └─────────────────────┘                            │
│                    │           │                                │
│                   YES          NO                               │
│                    │           │                                │
│                    ▼           ▼                                │
│     ┌──────────────────┐  ┌──────────────────┐                  │
│     │ Set bank_size    │  │ Keep bank_size=0 │                  │
│     │ to advertised    │  │ (legacy mode)    │                  │
│     │ value            │  │                  │                  │
│     └──────────────────┘  └──────────────────┘                  │
│                    │           │                                │
│                    ▼           ▼                                │
│     ┌──────────────────┐  ┌──────────────────┐                  │
│     │ 2-byte I2C write │  │ 1-byte I2C write │                  │
│     │ (bank + page)    │  │ (page only)      │                  │
│     └──────────────────┘  └──────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.8 API Design for Multi-Bank Modules

Modules with more than 8 lanes (e.g., 16, 24, or 32 lanes) require banking support. These modules are typically configured as multiple logical interfaces in SONiC, where each interface handles a subset of lanes. This section describes how the API design handles bank selection transparently.

#### 7.8.1 Design Problem

Consider a 32-lane OSFP module configured as 4 x 1.6T interfaces:

| Logical Interface | Lanes | Bank |
|-------------------|-------|------|
| Ethernet0 | 1-8 | 0 |
| Ethernet8 | 9-16 | 1 |
| Ethernet16 | 17-24 | 2 |
| Ethernet24 | 25-32 | 3 |

Each interface only needs data for its 8 lanes, not all 32. The API currently returns all lanes (hardcoded to 8)
```
Physical Module (32 lanes)
         │
         ▼
    ┌─────────┐
    │   SFP   │  ◄── Single object for entire transceiver
    │ Object  │
    └─────────┘
         │
         ├──► get_tx_power() returns [lane1...lane32]
         ├──► tx_disable_channel(channel, disable)  ◄── channel is a bitmask for lanes 1-8 only
         │
    ┌────┴────┬─────────┬─────────┐
    ▼         ▼         ▼         ▼
Ethernet0  Ethernet8  Ethernet16  Ethernet24
(lanes 1-8) (lanes 9-16) (lanes 17-24) (lanes 25-32)
```

#### 7.8.2 Recommended Approach: Thread-Safe SfpView Pattern

The recommended design uses long-lived `SfpView` wrappers to provide thread-safe access to banked transceivers. Each SfpView is created once at chassis init and cached per interface. Each view has its own xcvr_api instance with bank context set.

```
Physical Module (32 lanes, index=1)
         │
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   Shared SFP Object                         │
    │                   (one per physical module)                 │
    └─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    SfpView        SfpView        SfpView        SfpView
    (bank=0)       (bank=1)       (bank=2)       (bank=3)
    own xcvr_api   own xcvr_api   own xcvr_api   own xcvr_api
         │              │              │              │
         ▼              ▼              ▼              ▼
    Ethernet0      Ethernet8      Ethernet16     Ethernet24
```

**Benefits:**
- **Thread-safe** - each view has its own xcvr_api with bank set, no shared mutable state
- **Backwards compatible** - existing code using `get_sfp(index)` continues to work (defaults to bank 0)
- **Efficient** - For interface scope access, reduce i2c writes from 4 (entire module) to 1 (bank only)
- **Bank is explicitly configured** in `platform.json`

#### 7.8.3 Implementation Changes by Layer

##### Layer 1: Platform Chassis (`chassis_base.py`)

The Chassis caches SfpViews per interface at init. The existing `get_sfp()` method is updated to return an `SfpView` instead of a raw SFP object, accepting an optional `bank` parameter:

```python
class Chassis:
    def __init__(self):
        # ... existing init code ...
        self._sfp_view_cache = {}  # Cache for SfpView objects keyed by (index, bank)
        self._port_config = self._load_platform_json()  # Load interface config from platform.json

    def get_sfp(self, index, bank=0):
        """
        Returns an SfpView for a specific physical module and bank.

        For backwards compatibility, bank defaults to 0. Existing callers
        that use get_sfp(index) will continue to work unchanged.

        Args:
            index: Physical module index
            bank: Bank number (default: 0 for backwards compatibility)

        Returns:
            SfpView wrapping the SFP with the specified bank context
        """
        # Check if we have a cached view for this index/bank combination
        cache_key = (index, bank)
        if cache_key not in self._sfp_view_cache:
            sfp = self._sfp_list[index]
            self._sfp_view_cache[cache_key] = SfpView(sfp, bank)
        return self._sfp_view_cache[cache_key]

    def get_bank_for_logical_port(self, interface_name):
        """
        Returns the bank number for a logical port from platform.json.

        Args:
            interface_name: Logical interface name (e.g., "Ethernet8")

        Returns:
            Bank number (0 if not specified in config)
        """
        return self._port_config.get(interface_name).get("bank", 0)
```

##### Layer 2: SfpView (`sfp_view.py`)

`SfpView` is a long-lived, thread-safe wrapper around an SFP object. Each view caches its own xcvr_api instance with bank context set. It uses `__getattr__` to delegate all other methods to the underlying SFP:

```python
class SfpView:
    """Thread-safe view of an SFP with a specific bank context."""

    def __init__(self, sfp, bank=0):
        self._sfp = sfp
        self._bank = bank
        self._xcvr_api = None  # Own cached api, not shared

    def __getattr__(self, name):
        """Delegate all other methods to underlying SFP."""
        return getattr(self._sfp, name)

    def get_xcvr_api(self):
        """Returns xcvr_api with bank context set (cached per view)."""
        if self._xcvr_api is None:
            # Create a new api instance for this view using the factory
            self._xcvr_api = self._sfp._xcvr_api_factory.create_xcvr_api()
            self._xcvr_api.set_bank(self._bank)
        return self._xcvr_api

    def refresh_xcvr_api(self):
        """Refresh the cached xcvr_api (e.g., after transceiver hot-swap)."""
        self._xcvr_api = None
```

In the case for CPO seperate mode there is an SfpView per OE and ELS:
```python
class CpoSeperateSfp:
    """Composite view for CPO with separate OE and ELSFP devices."""

    def __init__(self, oe_view: SfpView, elsfp_view: SfpView):
        self._oe_view = oe_view
        self._elsfp_view = elsfp_view
        self._xcvr_api = None

    def get_xcvr_api(self):
        if self._xcvr_api is None:
            self._xcvr_api = CpoSeperateCmisApi(
                self._oe_view.get_xcvr_api(),
                self._elsfp_view.get_xcvr_api()
            )
        return self._xcvr_api
```

##### Layer 3: CMIS API (`api/public/cmis.py`)

Add `set_bank()` method and use internal `_bank` attribute when accessing banked pages:

```python
class CmisApi:
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        self.xcvr_eeprom = xcvr_eeprom
        self._bank = 0  # Default bank

    def set_bank(self, bank):
        """Set the bank context for this API instance."""
        self._bank = bank

    def get_tx_power(self):
        """Returns TX power for lanes in the current bank (8 values)."""
        tx_power_support = self.get_tx_power_support()
        if not tx_power_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]

        tx_power = self.xcvr_eeprom.read(consts.TX_POWER_FIELD, bank=self._bank)
        if tx_power is not None:
            return [tx_power['TxPower%dField' % i] for i in range(1, self.NUM_CHANNELS + 1)]
        return ["N/A" for _ in range(self.NUM_CHANNELS)]

    # Module-level methods don't need bank - always read from bank 0
    def get_module_temperature(self):
        """Temperature is on non-banked page - no bank parameter needed."""
        return self.xcvr_eeprom.read(consts.MODULE_TEMPERATURE_FIELD)
```

In the case for CPO seperate mode there is a new class that handles calls to the correct device (OE or ELS)
```python
class CpoSeperateCmisApi:
    """Composite API that routes calls to appropriate device."""

    def __init__(self, oe_api, elsfp_api):
        self._oe_api = oe_api
        self._elsfp_api = elsfp_api

    # data from OE
    def get_oe_rx_power(self):
        return self._oe_api.get_rx_power()

    # data from ELSFP
    def get_eslfp_tx_power(self):
        return  self._elsfp_api.get_tx_power()
```

##### Layer 4: XcvrEeprom (`xcvr_eeprom.py`)

**No changes required.** The XcvrEeprom layer remains unchanged. Bank context is stored on the mem_map and accessed by fields when calculating offsets:

```python
def read(self, field_name):
    """Read a field from the transceiver EEPROM."""
    field = self.mem_map.get_field(field_name)
    offset = field.get_offset()  # Field uses mem_map.getaddr() which uses mem_map._bank
    # Read from sysfs at calculated offset
    ...

def write(self, field_name, value):
    """Write a value to the transceiver EEPROM."""
    field = self.mem_map.get_field(field_name)
    offset = field.get_offset()  # Field uses mem_map.getaddr() which uses mem_map._bank
    # Write to sysfs at calculated offset
    ...
```

##### Layer 5: Memory Map (`mem_maps/public/cmis.py`)

The `getaddr()` method calculates linear offsets with bank awareness (already covered in Section 7.3).

#### 7.8.4 Platform Configuration (platform.json)

The bank is explicitly defined per interface in `platform.json`:

```json
{
    "interfaces": {
        "Ethernet0": {
            "index": 1,
            "bank": 0,
            "lanes": "1,2,3,4,5,6,7,8"
        },
        "Ethernet8": {
            "index": 1,
            "bank": 1,
            "lanes": "9,10,11,12,13,14,15,16"
        },
        "Ethernet16": {
            "index": 1,
            "bank": 2,
            "lanes": "17,18,19,20,21,22,23,24"
        },
        "Ethernet24": {
            "index": 1,
            "bank": 3,
            "lanes": "25,26,27,28,29,30,31,32"
        }
    }
}
```

**Key points:**
- All four interfaces share the same physical module (`index: 1`)
- Each interface has its own `bank` value (0, 1, 2, 3)
- The `bank` field is optional; if omitted, defaults to 0 (backwards compatible)

#### 7.8.5 Call Flow Example

```
xcvrd (processing "Ethernet8", which maps to index=1, bank=1 in platform.json)
  │
  ├─► get_bank_for_logical_port("Ethernet8")  ──► returns 1 (cached from platform.json)
  │
  ├─► get_sfp(index=1, bank=1)  ──► returns cached SfpView (bank=1)
  │
  ├─► sfp.get_xcvr_api()
  │       │
  │       └─► returns cached xcvr_api (with _bank=1 already set)
  │
  └─► api.get_tx_power()
          │
          └─► xcvr_eeprom.read(TX_POWER_FIELD)
                  │
                  └─► getaddr(page=0x11, offset=154, bank=1) ──► linear offset for Bank 1
                          │
                          └─► sysfs read ──► returns [tx_power lanes 9-16]
```

**xcvrd pseudo-code:**

```python
# xcvrd iterates over interfaces
for interface_name in ["Ethernet0", "Ethernet8", "Ethernet16", "Ethernet24"]:
    # Look up bank from platform.json via chassis
    bank = platform_chassis.get_bank_for_logical_port(interface_name)

    # Get cached SfpView with bank context
    sfp_view = platform_chassis.get_sfp(index, bank)

    # Get cached xcvr_api (already has bank set)
    api = sfp_view.get_xcvr_api()

    # API calls use the view's bank context automatically
    info = api.get_transceiver_info()
    tx_power = api.get_tx_power()
    # ...
```

#### 7.8.6 Files Changed Summary

| Repository | File | Change |
|------------|------|--------|
| sonic-platform-common | `sonic_platform_base/chassis_base.py` | Update `get_sfp()` to return `SfpView`, add bank parameter |
| sonic-platform-common | `sonic_platform_base/sfp_view.py` | New file: `SfpView` class with own cached xcvr_api |
| sonic-platform-common | `sonic_xcvr/api/public/cmis.py` | Add `set_bank()`, use `self._bank` in banked methods |
| sonic-platform-common | `sonic_xcvr/xcvr_eeprom.py` | Add `bank` parameter to `read()`/`write()` |
| sonic-platform-common | `sonic_xcvr/mem_maps/public/cmis.py` | Bank-aware `getaddr()` (Section 7.3) |
| Platform vendors | `platform.json` | Add `bank` field per interface |
### 7.9 DB and Schema Changes

No database schema changes are required for this feature.

### 7.10 SWSS and Syncd Changes

No changes required to SWSS or Syncd.

### 7.11 Sequence Diagram

```
User                sfputil              xcvr_eeprom           optoe.c              Transceiver
  |                    |                      |                   |                      |
  |-- read bank=1 ---->|                      |                   |                      |
  |   page=0x10, byte  |                      |                   |                      |
  |                    |-- getaddr(0x10,      |                   |                      |
  |                    |    byte, bank=1)---->|                   |                      |
  |                    |   = linear_offset    |                   |                      |
  |                    |                      |-- read(offset) -->|                      |
  |                    |                      |                   |                      |
  |                    |                      |                   |  Per CMIS 5.3 8.2.15:|
  |                    |                      |                   |  Write bank+page in  |
  |                    |                      |                   |  single I2C operation|
  |                    |                      |                   |                      |
  |                    |                      |                   |-- write 2 bytes ---->|
  |                    |                      |                   |   @0x7E: [0x01,0x10] |
  |                    |                      |                   |                      |
  |                    |                      |                   |-- read upper mem --->|
  |                    |                      |<---- data --------|<----- data --------- |
  |<----- data --------|<----- data ----------|                   |                      |
  |                    |                      |                   |                      |
  |                    |                      |                   |-- write 2 bytes ---->|
  |                    |                      |                   |   @0x7E: [0x00,0x00] |
  |                    |                      |                   |   (restore to bank 0)|
```

**Note**: Per CMIS 5.3 Section 8.2.15, when changing bank, both BankSelect (0x7E) and PageSelect (0x7F) must be written in a single I2C WRITE operation. The module does not process the BankSelect value until PageSelect is written.

### 7.12 Implementation Phases

| Phase | Description | Components |
|-------|-------------|------------|
| 1 | Kernel Driver | Add bank select register handling, extend linear address space |
| 2 | Python Layer | Extend `getaddr()` with bank parameter, add bank-aware fields |
| 3 | API Layer | Implement SFP view per logical port, add bank context |
| 4 | Utilities | Add bank parameter to CLI commands, update VDM APIs |

### 7.13 Platform Dependencies

This feature requires CMIS-compliant transceivers that support banking. Transceivers without banking support (flat memory modules) will continue to work with Bank 0.

## 8. SAI API

No SAI API changes are required for this feature. Transceiver EEPROM access is handled through the optoe kernel driver and sysfs interface, not through SAI.

## 9. Configuration and Management

### 9.1 Manifest

Not applicable - this is a built-in feature, not an Application Extension.

### 9.2 CLI/YANG Model Enhancements

**New CLI Options**:

```bash
# Read EEPROM with bank selection
sfputil read-eeprom -p <port> --page <page> --bank <bank> --size <size>

# Write EEPROM with bank selection
sfputil write-eeprom -p <port> --page <page> --bank <bank> --offset <offset> --data <data> -- size <size>
```

**Backward Compatibility**: The `--bank` option defaults to 0, maintaining compatibility with existing CLI usage.

### 9.3 Config DB Enhancements

No Config DB changes are required.

## 10. Warmboot and Fastboot Design Impact

This feature has no impact on warmboot or fastboot functionality.

## 11. Memory Consumption

No significant memory impact. Additional bank/page metadata is minimal.

## 12. Restrictions/Limitations

1. Only applicable to CMIS devices
2. Not applicable to legacy SFP/QSFP (SFF-8472/SFF-8636) modules
3. Maximum 8 banks supported by optoe driver (`OPTOE_MAX_SUPPORTED_BANK_SIZE`)
4. Bank switching requires a 2-byte I2C write (bank+page) vs 1-byte for Bank 0, plus a restore operation to return to Bank 0 after access

## 13. Testing Requirements/Design

### 13.1 Unit Test Cases

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| UT-01 | Read from Bank 0, Page 0 (default) | Data returned correctly |
| UT-02 | Read from Bank 1, Page 16 | Correct bank/page selected |
| UT-03 | Write to Bank 1, Page 17 | Data written to correct location |
| UT-04 | Linear offset calculation | Correct bank/page/byte extracted |
| UT-05 | Backward compatibility (no bank param) | Defaults to Bank 0 |

### 13.2 System Test Cases

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| ST-01 | Bank 0 operations on QSFP-DD/OSFP | No regression |
| ST-02 | Bank switching on 16-lane module (Not possible currently) | Lanes 9-16 accessible via Bank 1 |
| ST-04 | Performance: Bank 0 only access | No performance degradation |
| ST-05 | Performance: Bank switching | Acceptable I2C overhead |
| ST-06 | Flat memory module handling | Graceful handling when banking not supported |

## References
- [OIF CMIS 5.3 Specification](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf)
- [sonic-net/sonic-linux-kernel PR #473: optoe: Add CMIS Bank support](https://github.com/sonic-net/sonic-linux-kernel/pull/473)
- optoe kernel driver source code
