# Dump SFP EEPROM page data in show techsupport command #

## Table of Content

### Revision

### Scope

SONiC show techsupport command provides the ability to collect system dump for debug purpose. Module EEPROM data is important information for PHY issue debugging, but it is not part of show techsupport command. This design will enhance show techsupport command to contain module EEPROM data.

### Definitions/Abbreviations

N/A

### Overview

1. Existing CLI `sfputil show eeprom-hexdump` shall be extended to dump EEPROM pages in a single call.
2. Show techsupport command shall be extended to call `sfputil show eeprom-hexdump` command to collect module EEPROM data.

### Requirements

1. Show techsupport command shall collect module EEPROM raw data
2. All existing cable types shall be supported except RJ45
3. Vendor specific implementation is not required but still possible.

### Architecture Design

The current architecture is not changed

### High-Level Design

Submodule sonic-utilities shall be changed. By default, vendor platform API implementation is not required.

#### sonic-utilities

##### generate_dump change

1. New subcommand `sfputil show eeprom-hexdump` shall be used to dump module EEPROM data
2. EEPROM data shall be saved to path `$TARDIR/dump/`

Sample code:
```
save_cmd "sfputil show eeprom-hexdump" "interface.xcvrs.eeprom.raw" &
```

##### sfputil change

Existing subcommand `eeprom-hexdump` shall be extended to dump eeprom data for all existing cables except RJ45. Currently, `sfputil show eeprom-hexdump` accept two options `--port` and `--page`. It shall be extended like this:

1. `sfputil show eeprom-hexdump --port <port> --page <page>`: dump given page for given port
2. `sfputil show eeprom-hexdump --port <port>`: dump page 0 for given port (to keep backwardcompatible)
3. `sfputil show eeprom-hexdump --page <page>`: dump given page for all ports, validate that page must be in range [0,255]. User is repsonsible for making sure the page existence.
4. `sfputil show eeprom-hexdump`: dump available pages for all ports. Available pages for different cable types are described below.

`sfputil show eeprom-hexdump` shall dump pages based on cable type:

- CMIS
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 10h, 11h (128-255), CDB page 0x9f if available (128-255), 400G ZR pages 30h, 31h, 32h, 33h, 34h, 35h, 38h, 39h, 3ah, 3bh if available (128-255)
- sff8436
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 3h (128-255)
- sff8472
  - passive: page 0h (0-127) if flat memory else (0-255) 
  - active: page 0h (0-127) if flat memory else (0-255), 1h, 2h (128-255)
- sff8636
  - copper: page 0h (0-255)
  - optical: pages 0h (0-255), 1h, 2h, 3h (128-255)

> Note: it is very complicated to dump all possible pages. So, only basic pages shall be dumped in the current implementation.  

Sample output:

```
sfputil show eeprom-hexdump
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

Dumping module EEPROM pages takes memory which shall be freed after finishing the command.

### Restrictions/Limitations

Vendor should support platform API `sfp.read_eeprom` to support this feature.

### Testing Requirements/Design

#### Unit Test cases

- sonic-utilities unit test shall be extended to cover changes for subcommand `sfputil show eeprom-dump`

#### System Test cases

### Open/Action items - if any
