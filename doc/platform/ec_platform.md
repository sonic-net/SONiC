## Feature Name
**Edgecore Switch Platform Support**

### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 01/28/2022  | Target Corporation | Initial version                   |

### Scope

This feature includes SONiC platform support for the following switch models
only:
- AS4630-54pe
- AS5835-54x
- AS7816-64x
- AS7326-56x

### Overview

This feature required adds/modifications to the following areas in the
sonic-buildimage repo:
- device/accton/
- platform/broadcom/sonic-platform-modules-accton/

No other SONiC submodules will be added or modified.

### Requirements

Due to missing or incomplate platform support the following SONiC show commands
are not functional:

- show platform fan
- show platform temperature
- show platform psustatus
- show platform syseeprom
- show interfaces transceiver presence
- show interfaces transceiver eeprom
- show interfaces transceiver eeprom --dom

The following SONiC utilities are also non-functional:
- sfputil
- psuutil
- psushow
- fanshow

Proper platform support is required to make these commands display
valid output.

In addition to the SONiC commands listed, the following issues exist:
- Incorrect management port default for eth0 on AS4630-54pe

### Architecture Design 

This feature utilizes the existing SONiC Platform Management API
implementation.  For each supported switch platform, the SONiC build
system will create a .deb package that includes all driver modules, utilities,
and sonic_platform wheel file.

The sonic_platform wheel package is installed in the base system and the
pmon container.  Processes (psud, thermalctld, xcvrd, etc.) running in the
pmon container will utilize the sonic_platform implementation to access
hardware components and write appropriate status to existing redis tables.

The platform specific install utility will take care of installing the
sonic_platform wheel file, installing platform drivers, creating i2c device
nodes, etc.

### High-Level Design 

Edgecore platform support requires the existing SONiC Platform Management API
infrastructure.  All changes will be made in the sonic-buildimage repository.

#### device/accton/ Updates

1. Add/update sonic_platform components and helper functions based on
hardware design
2. Update lane assignments if necessary
3. Update pmon process control
4. Update installer.conf
5. Update pmon_daemon_control.json
6. Update stable_size where appropriate

#### platform/broadcom/sonic-platform-modules-accton/ Updates

1. Add/update kernel driver files and Makefile
2. Add service file and script to rename management port (AS4630-54pe only)
3. Update wheel setup file
4. Add/update switch specific install utility

### SAI API 

No SAI changes are required for this feature.

### Configuration and management

No configuration is required for this feature.

### Warmboot and Fastboot Design Impact  

This feature does not have any dependencies or impacts on warmboot/fastboot.

### Restrictions/Limitations  

This feature only applies to the following Edgecore switch models:
- AS4630-54pe
- AS5835-54x
- AS7816-64x
- AS7326-56x

### Testing Requirements/Design

Since this feature is hardware-dependent, no unit tests have been added
and all test cases will be performed manually to verify this feature.

#### System Test cases

The following manual verification will be performed on each of the 4
switch models:
- Verify driver loaded

The following SONiC commands will be manually run on each of the 4 switch
models and output verified:

- show platform fan
- show platform temperature
- show platform psustatus
- show platform syseeprom
- show interfaces transceiver presence
- show interfaces transceiver eeprom
- show interfaces transceiver eeprom --dom
- sfputil
- psuutil
- psushow
- fanshow

The following will be performed on switch model AS4630-54pe only:
- General access to management port via ssh, scp

### Open/Action items

None

