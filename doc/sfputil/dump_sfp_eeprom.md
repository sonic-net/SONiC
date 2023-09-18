# Dump SFP EEPROM page data in show techsupport command #

## Table of Content

### Revision

### Scope

SONiC show techsupport command provides the ability to collect system dump for debug purpose. Module EEPROM data is important information for PHY issue debugging, but it is not part of show techsupport command. This design will enhance show techsupport command to contain module EEPROM data.

### Definitions/Abbreviations

N/A

### Overview

1. A new CLI `sfputil show eeprom-hexdump-all` shall dump EEPROM pages in a single call.
2. Show techsupport command shall be extended to call `sfputil show eeprom-hexdump-all` command to collect module EEPROM data.

### Requirements

1. Show techsupport command shall collect module EEPROM raw data
2. All existing cable types shall be supported except RJ45
3. Vendor specific implementation is not required but still possible.

### Architecture Design

The current architecture is not changed

### High-Level Design

Submodule sonic-platform-common and sonic-utilities shall be changed. By default, vendor platform API implementation is not required.

#### sonic-platform-common

##### sfp_base change

A new API `dump_eeprom` shall be added to `sfp_base.SfpBase`. This API shall be used by `sfputil show eeprom-hexdump-all` command to collect module EEPROM data.

```python
def dump_eeprom(self, page=None):
    """
    Dump all EEPROM data for this SFP

    Args:
        page: EEPROM page number, dump all pages if page is None

    Returns:
        A string contains the hex format EEPROM data
    """
    raise NotImplementedError
```

##### sfp_optoe_base change

`sfp_optoe_base.SfpOptoeBase` shall implement the new API `dump_eeprom` so that vendor does not have to implement it (Vendor specific implementation is also possible).

```python
def dump_eeprom(self, page=None):
    api = self.get_xcvr_api()
    return api.dump_eeprom(page) if api is not None else None
```

##### sonic_xcvr change

Following sonic_xcvr API implementation shall implement the new API `dump_eeprom`:

- sonic_xcvr.api.public.cmis
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 10h, 11h (128-255)
- sonic_xcvr.api.public.sff8436
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 3h (128-255)
- sonic_xcvr.api.public.sff8472
  - copper: page A0h (0-128)
  - optical: page A0h (0-255), A2h (0-255)
- sonic_xcvr.api.public.sff8636
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 3h (128-255)

#### sonic-utilities

##### generate_dump change

1. New subcommand `sfputil show eeprom-hexdump-all` shall be used to dump module EEPROM data
2. EEPROM data shall be saved to path `$TARDIR/dump/`

Sample code:
```
save_cmd "sfputil show eeprom-hexdump-all" "interface.xcvrs.eeprom.raw" &
```

Note: dumping EEPROM data might cause firmware busy, the command shall not be run parallel with save_saidump to avoid hardware access conflict.

##### sfputil change

A new subcommand `eeprom_hexdump_all` shall be added to `sfputil show` command group. The comamnd shall dump eeprom data for all existing cables except RJ45.

Sample output:

```
EEPROM hexdump for module 1
        Lower page 0h
        00000000 11 08 06 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000010 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000020 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000030 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000040 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000050 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000060 00 00 00 00 00 00 00 00  00 00 00 00 00 01 08 00 |................|
        00000070 00 10 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|

        Upper page 0h
        00000000 11 08 06 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000010 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000020 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000030 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000040 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000050 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000060 00 00 00 00 00 00 00 00  00 00 00 00 00 01 08 00 |................|
        00000070 00 10 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|

        Page 1h
        00000000 11 08 06 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000010 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000020 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000030 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000040 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000050 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000060 00 00 00 00 00 00 00 00  00 00 00 00 00 01 08 00 |................|
        00000070 00 10 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|

...

EEPROM hexdump for module 2

...
```

####

### SAI API

N/A

### Configuration and management

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

No YANG model changes. CLI changes has been described in section #### sfputil change

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact

N/A

### Memory Consumption

No memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration.

### Restrictions/Limitations

Vendor should support platform API `sfp.read_eeprom` to support this feature.

### Testing Requirements/Design

#### Unit Test cases

sonic-utilities unit test shall be extended to cover new subcommand `sfputil show eeprom-dump-all`
sonic-platform-common unit test shall be extended to cover new API `sfp.dump_eeprom`

#### System Test cases

### Open/Action items - if any
