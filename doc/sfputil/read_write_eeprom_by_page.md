# sfputil | add the ability to read/write any byte from EERPOM both by page and offset #

## Table of Content

### Revision

### Scope

This document describes SONiC feature to read/write cable EEPROM data via SONiC CLI.

### Definitions/Abbreviations

N/A

### Overview

CLI sfputil shall be extended to support reading/writing cable EEPROM by page and offset. This implementation is based on existing platform API `sfp.read_eeprom` and `sfp.write_eeprom`.

### Requirements

- Support reading/writing cable EEPROM data by page, offset and size. For sff8472, wire address "a0h" or "a2h" must be provided by user.
- Support basic validation for input parameter such as page, offset and size.
- Support reading/writing cable EEPROM for all types of cables except RJ45.
- Support non flat memory mode reading/writing. In this mode, user shall proved page and offset according to the standard. For example, CMIS page 1h starting offset is 128, offset less than 128 shall be treated as invalid.
- Support flat memory mode reading/writing (Phase 2). In this mode, the EEPROM memory shall be treated as continues flat memory. This design document will not discuss this mode.
- Vendor who does not support `sfp.read_eeprom` and `sfp.write_eeprom` is expected to raise `NotImplementedError`, this error shall be properly handled
- Others error shall be treated as read/write failure
- Vendor specific implementation is not required but still possible.


### Architecture Design

The current architecture is not changed.

### High-Level Design

Submodule sonic-platform-common and sonic-utilities shall be extended to support this feature. Vendor specific implementation is not required but still possible.

#### sonic-platform-common

The existing API `sfp.read_eeprom` and `sfp.write_eeprom` accept "overall offset" as parameter. They have no concept of page. If user wants to use it, user has to convert page and offset to "overall offset" manually. Different cable types use different covert method according to the standard. So, it is not user friendly to provide such API directly to user. Two new API shall be added to support this feature:

```python

def read_eeprom_by_page(self, page, offset, size, wire_addr=None, flat=False):
    """
    Read EEPROM by page

    Args:
        page: EEPROM page number. Raise ValueError for invalid page.
        offset: EEPROM page offset. Raise ValueError for invalid offset.
        size: Read size. Raise ValueError for invalid size.
        wire_addr: Wire address. Only valid for sff8472. Raise ValueError for invalid wire address.
        flat: Read mode.

    Returns:
        A string contains the hex format EEPROM data.
    """
    raise NotImplementedError

def write_eeprom_by_page(self, page, offset, data, wire_addr=None, flat=False):
    """
    Write EEPROM by page

    Args:
        page: EEPROM page number. Raise ValueError for invalid page.
        offset: EEPROM page offset. Raise ValueError for invalid offset.
        data: Binary EEPROM data.
        wire_addr: Wire address. Only valid for sff8472. Raise ValueError for invalid wire address.
        flat: Write mode.

    Returns:
        True if write successfully else False
    """
    raise NotImplementedError
```

`sfp_optoe_base.SfpOptoeBase` shall implement these new APIs so that vendor does not have to implement it (Vendor specific implementation is also possible).

```python
def read_eeprom_by_page(self, page, offset, size, wire_addr=None, flat=False):
    api = self.get_xcvr_api()
    overall_offset = api.get_overall_offset(page, offset, size, wire_addr, flat) if api is not None else None
    if overall_offset is None:
        return None
    return self.read_eeprom(overall_offset, size)

def write_eeprom_by_page(self, page, offset, data, wire_addr=None, flat=False):
    api = self.get_xcvr_api()
    overall_offset = api.get_overall_offset(page, offset, len(data), wire_addr, flat) if api is not None else None
    if overall_offset is None:
        return False
    return self.write_eeprom(overall_offset, len(data), data)
```

> Note: Not all bytes are valid for write. User is responsible to give a valid page and offset according to standard and cable vendor user manual. SONiC does not do such validation. If user writes data to a read only byte, vendor platform API shall return False but this is not guaranteed.

Each API implementation shall implement `get_overall_offset` function based on standard.

##### CMIS implementation

Passive cable:
- Valid page: 0
- Valid offset: 0-255

Active cable:
- Valid page: 0-255
= Valid offset: page 0 (0-255), other (128-255)

For active cable, there is no "perfect" page validation as it is too complicated. User is responsible to make sure the page existence according to cable user manual.

Example:
```python
sfp.read_eeprom_by_page(page=0, offset=255, size=1) # valid
sfp.read_eeprom_by_page(page=0, offset=255, size=2) # invalid size, out of range, 255+2=257 is not a valid offset
sfp.read_eeprom_by_page(page=0, offset=256, size=1) # invalid offset 256 for page 0, must be in range [0, 255]
sfp.read_eeprom_by_page(page=1, offset=0, size=1)   # invalid offset 0 for page 1, must be >=128
```

##### sff8436 and sff8636 implementation

Passive cable:
- Valid page: 0
- Valid offset: 0-255

Active cable:
- Valid page: 0-255
- Valid offset: page 0 (0-255), other (128-255)

For active cable, there is no "perfect" page validation as it is too complicated. User is responsible to make sure the page existence according to cable user manual.

```python
sfp.write_eeprom_by_page(page=0, offset=255, bytearray.fromhex('ff'))   # valid
sfp.write_eeprom_by_page(page=0, offset=255, bytearray.fromhex('ff00')) # invalid size, out of range, 255+2=257 is not a valid offset
sfp.write_eeprom_by_page(page=0, offset=256, bytearray.fromhex('ff'))   # invalid offset 256 for page 0, must be in range [0, 255]
sfp.write_eeprom_by_page(page=1, offset=0, bytearray.fromhex('ff'))     # invalid offset 0 for page 1, must be >=128
```

##### sff8472 implementation

Passive cable:
- Valid wire address: [A0h] (case insensitive)
- Valid offset: A0h (0-128)

Active cable:
- Valid wire address: [A0h, A2h] (case insensitive)
- Valid offset: A0h (0-255), A2h (0-255)

```python
sfp.read_eeprom_by_page(0, 0, 1, wire_addr='a0h') # valid
sfp.read_eeprom_by_page(0, 0, 1, wire_addr='A0h') # valid, wire address is case insensitive
sfp.read_eeprom_by_page(1, 0, 1, wire_addr='a2h') # valid
sfp.read_eeprom_by_page(1, 0, 1, wire_addr='a0h') # invalid page 1, wire address a0h has no page 1
```

#### sonic-utilities

Two new CLIs shall be added to sfputil module:

- sfputil read-eeprom
- sfputil write-eeprom

For detail please check chapter "CLI/YANG model Enhancements".

### SAI API

N/A

### Configuration and management

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

##### sfputil read-eeprom

```
admin@sonic:~$ sfputil read-eeprom --help
Usage: sfputil read-eeprom [OPTIONS] <port_name> <page> <offset> <size>

  Read SFP EEPROM data

Options:
  --no-format             Display non formatted data.
  --wire-addr             Wire address of sff8472.
  --help                  Show this message and exit.
```

Example:

```
sfputil read-eeprom Ethernet0 0 100 2
00000064 4a 44                                            |..|

sfputil read-eeprom Ethernet0 0 0 32
00000000 11 08 06 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
00000010 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|

sfputil read-eeprom Ethernet0 0 100 2 --no-format
4a44
```

##### sfputil write-eeprom

```
admin@sonic:~$ sfputil write-eeprom --help
Usage: sfputil write-eeprom [OPTIONS] <port> <page> <offset> <data>

  Write SFP EEPROM data

Options:
  --wire-addr             Wire address of sff8472.
  --help                  Show this message and exit.
```

Example:

```
sfputil write-eeprom Ethernet0 0 100 4a44
```

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact

N/A

### Memory Consumption

No memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration.

### Restrictions/Limitations

- Vendor should support plaform API `sfp.read_eeprom` and `sfp.write_eeprom` to support this feature.
- For dependent mode, module EEPROM might be managed by FW and cannot be written. CLI shall provide proper message for such situation.

### Testing Requirements/Design

#### Unit Test cases

- sonic-utilities unit test shall be extended to cover new subcommands
- sonic-platform-common unit test shall be extended to cover new APIs

#### System Test cases

### Open/Action items - if any
