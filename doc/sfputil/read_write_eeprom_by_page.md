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
- User shall provide page and offset according to the standard. For example, CMIS page 1h starting offset is 128, offset less than 128 shall be treated as invalid.
- Vendor who does not support `sfp.read_eeprom` and `sfp.write_eeprom` is expected to raise `NotImplementedError`, this error shall be properly handled
- Others error shall be treated as read/write failure


### Architecture Design

The current architecture is not changed.

### High-Level Design

Submodule sonic-utilities shall be extended to support this feature.

#### sonic-utilities

Two new CLIs shall be added to sfputil module:

- sfputil read-eeprom
- sfputil write-eeprom

For detail please check chapter [CLI/YANG model Enhancements](#cliyang-model-enhancements)

The existing API `sfp.read_eeprom` and `sfp.write_eeprom` accept "overall offset" as parameter. They have no concept of page. If user wants to use it, user has to convert page and offset to "overall offset" manually. Different cable types use different covert method according to the standard. So, it is not user friendly to provide such API directly to user. sonic-utilities shall provide the function to translate from page offset to overall offset.

##### CMIS validation

Passive cable:
- Valid page: 0
- Valid offset: 0-255

Active cable:
- Valid page: 0-255
= Valid offset: page 0 (0-255), other (128-255)

For active cable, there is no "perfect" page validation as it is too complicated. User is responsible to make sure the page existence according to cable user manual.

Example:
```
sfputil read-eeprom -p Ethernet0 -n 0 -o 255 -s 1               # valid
sfputil read-eeprom -p Ethernet0 -n 0 -o 255 -s 2               # invalid size, out of range, 255+2=257 is not a valid offset
sfputil read-eeprom -p Ethernet0 -n 0 -o 256 -s 1               # invalid offset 256 for page 0, must be in range [0, 255]
sfputil read-eeprom -p Ethernet0 -n 1 -o 0 -s 1                 # invalid offset 0 for page 1, must be >=128
```

##### sff8436 and sff8636 validation

Passive cable:
- Valid page: 0
- Valid offset: 0-255

Active cable:
- Valid page: 0-255
- Valid offset: page 0 (0-255), other (128-255)

For active cable, there is no "perfect" page validation as it is too complicated. User is responsible to make sure the page existence according to cable user manual.

```
sfputil write-eeprom -p Ethernet0 -n 0 -o 255 -d ff            # valid
sfputil write-eeprom -p Ethernet0 -n 0 -o 255 -d ff00          # invalid size, out of range, 255+2=257 is not a valid offset
sfputil write-eeprom -p Ethernet0 -n 0 -o 256 -d ff            # invalid offset 256 for page 0, must be in range [0, 255]
sfputil write-eeprom -p Ethernet0 -n 1 -o 0 -d ff              # invalid offset 0 for page 1, must be >=128
```

##### sff8472 validation

Passive cable:
- Valid wire address: [A0h] (case insensitive)
- Valid offset: A0h (0-128)

Active cable:
- Valid wire address: [A0h, A2h] (case insensitive)
- Valid offset: A0h (0-255), A2h (0-255)

```
sfputil read-eeprom -p Ethernet0 -n 0 -o 0 -s 1 --wire-addr a0h               # valid
sfputil read-eeprom -p Ethernet0 -n 0 -o 0 -s 2 --wire-addr A0h               # invalid size, out of range, 255+2=257 is not a valid offset
sfputil read-eeprom -p Ethernet0 -n 1 -o 0 -s 1 --wire-addr a2h               # invalid offset 256 for page 0, must be in range [0, 255]
sfputil read-eeprom -p Ethernet0 -n 1 -o 0 -s 1 --wire-addr a0h               # invalid offset 0 for page 1, must be >=128
```

### SAI API

N/A

### Configuration and management

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

##### sfputil read-eeprom

```
admin@sonic:~$ sfputil read-eeprom --help
Usage: sfputil read-eeprom [OPTIONS]

  Read SFP EEPROM data

Options:
  -p, --port <logical_port_name>  Logical port name  [required]
  -n, --page <page>               EEPROM page number  [required]
  -o, --offset <offset>           EEPROM offset within the page  [required]
  -s, --size <size>               Size of byte to be read  [required]
  --no-format                     Display non formatted data
  --wire-addr TEXT                Wire address of sff8472
  --help                          Show this message and exit.
```

Example:

```
sfputil read-eeprom -p Ethernet0 -n 0 -o 100 -s 2
        00000064 4a 44                                            |..|

sfputil read-eeprom -p Ethernet0 -n 0 -o 0 -s 32
        00000000 11 08 06 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
        00000010 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|

sfputil read-eeprom -p Ethernet0 -n 0 -o 100 -s 2 --no-format
4a44
```

##### sfputil write-eeprom

```
admin@sonic:~$ sfputil write-eeprom --help
Usage: sfputil write-eeprom [OPTIONS]

  Write SFP EEPROM data

Options:
  -p, --port <logical_port_name>  Logical port name  [required]
  -n, --page <page>               EEPROM page number  [required]
  -o, --offset <offset>           EEPROM offset within the page  [required]
  -d, --data <data>               Hex string EEPROM data  [required]
  --wire-addr TEXT                Wire address of sff8472
  --verify                        Verify the data by reading back
  --help                          Show this message and exit.
```

Example:

```
sfputil write-eeprom -p Ethernet0 -n 0 -o 100 -d 4a44

sfputil write-eeprom -p Etherent0 -n 0 -o 100 -d 4a44 --verify
Error: Write data failed! Write: 4a44, read: 0000.
```

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact

N/A

### Memory Consumption

No memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration.

### Restrictions/Limitations

- Vendor should support plaform API `sfp.read_eeprom` and `sfp.write_eeprom` to support this feature.

### Testing Requirements/Design

#### Unit Test cases

- sonic-utilities unit test shall be extended to cover new subcommands

#### System Test cases

### Open/Action items - if any
