## New Platform Management API

### Overview

Every platform has a unique set of platform peripheral devices
- PSUs
- Fan modules
- SFP transceiver cages
- Environment sensors
- Front-panel LEDs
- etc.

These devices can vary by manufacturer, model, quantity, interface, ...

Challenge: Attempt to create a standardized, unified API to interface with all combinations of these devices

### SONiC Design Principles

1. Unified, standardized behavior
    - Consistent experience among all SONiC devices, regardless of underlying platform
    - Easy to understand, implement, test and debug

2. Kernel modules kept as simple as possible
    - Simply expose hardware registers
    - No control logic

3. Peripheral control logic implemented in user-space
    - Applications shared among all platforms
    - Standardized API defined by SONiC, implemented by vendors

### Current Solution

- Individual plugins, one per peripheral device type
  - sfputil.py, psuutil.py, eeprom.py, etc.
  - SONiC defines base classes, vendors must implement these classes in their plugins
  - All Platform-specific plugins live on disk in image, appropriate plugin is loaded at runtime after determining running platform
- Drawbacks
  - Lack of structure; Each plugin base class installed as its own Python package
  - As we add support for more devices, new plugins are necessary.
  - Vendors need to be made aware of new plugins. Not apparent.
  - When adding a new abstract method to a base class, one needs to add default implementation to *all* existing implementations

### New Solution

#### Concept

- Combine all plugin base classes into an object-oriented hierarchy
  - Hierarchy based on physical connection of devices
  - Object-orientation allows for definition of a generic "DeviceBase" class
    - Attributes shared by all/most devices inherited by all (Presence, Model #, Serial #, etc.)
- Installed as one Python package: "sonic_platform_base"
- Vendors implement entire package: "sonic_platform"
  - Appropriate platform-specific package will be installed during first boot, similar to platform drivers
- No longer abstract base classes
  - All abstract methods simply raise "NotImplementedError"
    - Adding new methods to the base classes will not break existing implementations
    - To ensure vendors are made aware of new methods, we will add a build-time or run-time test which will output all unimplemented methods

#### Implementation

- Source for new "sonic_platform" package will reside along with vendor's platform module source under the platform/... directory structure
- At build time, vendor ensures sonic_platform source is compiled into a Python wheel file
- Upon first boot after image installation, at the time the appropriate platform modules are installed, the following must also be done:
  1. Install the sonic_platform package in the host system
  2. Copy the sonic_platform Python wheel to the appropriate /usr/share/sonic/device/<PLATFORM>/ directory, which gets mounted in the Docker containers
- When the Platform Monitor (PMon) container starts, it will check whether a "sonic_platform" package is installed. If not, it will attempt to install a "sonic_platform\*.whl" file in the mounted directory as mentioned above.
- In the host system, applications will interact with the platform API for things like watchdog and reboot cause
- Daemons running in pmon container will be responsible for updating Redis State database with current metrics/status from platfrom hardware
- Command-line utilities in host image will query State DB to retrieve current platform peripheral metrics
- For more real-time data, such as transceiver optical data, a mechanism can be implemented CLI can notify daemons to retrieve data by writing to DB

#### New Platform API Hierarchy

- Platform
  - Chassis
    - Base MAC address
    - Serial number
    - System EEPROM info
    - Reboot cause
    - Hardware watchdog
    - Environment sensors
    - Front-panel LEDs
    - Status LEDs
    - Power supply unit[0 .. p-1]
    - Fan[0 .. f-1]
    - SFP cage[0 .. s-1]
    - Module[0 .. m-1] (Line card, supervisor card, etc.)
      - Environment sensors
      - Front-panel LEDs
      - Status LEDs
      - Power supply unit[0 .. p'-1]
      - Fan[0 .. f'-1]
      - SFP cage[0 .. s'-1]

### Sample code to print PSU1 presence using old API

```
#!/usr/bin/env python

import imp
import subprocess
import sys

# Global platform-specific psuutil class instance
platform_psuutil = None

# Returns platform and HW SKU
def get_platform_and_hwsku():
    try:
        proc = subprocess.Popen([SONIC_CFGGEN_PATH, '-H', '-v', PLATFORM_KEY],
                                stdout=subprocess.PIPE,
                                shell=False,
                                stderr=subprocess.STDOUT)
        stdout = proc.communicate()[0]
        proc.wait()
        platform = stdout.rstrip('\n')

        proc = subprocess.Popen([SONIC_CFGGEN_PATH, '-d', '-v', HWSKU_KEY],
                                stdout=subprocess.PIPE,
                                shell=False,
                                stderr=subprocess.STDOUT)
        stdout = proc.communicate()[0]
        proc.wait()
        hwsku = stdout.rstrip('\n')
    except OSError, e:
        raise OSError("Cannot detect platform")

    return (platform, hwsku)

# Loads platform specific psuutil module from source
def load_platform_psuutil():
    global platform_psuutil

    # Get platform and hwsku
    (platform, hwsku) = get_platform_and_hwsku()

    # Load platform module from source
    platform_path = ''
    if len(platform) != 0:
        platform_path = "/".join([PLATFORM_ROOT_PATH, platform])
    else:
        platform_path = PLATFORM_ROOT_PATH_DOCKER
    hwsku_path = "/".join([platform_path, hwsku])

    try:
        module_file = "/".join([platform_path, "plugins", PLATFORM_SPECIFIC_MODULE_NAME + ".py"])
        module = imp.load_source(PLATFORM_SPECIFIC_MODULE_NAME, module_file)
    except IOError, e:
        print("Failed to load platform module '%s': %s" % (PLATFORM_SPECIFIC_MODULE_NAME, str(e)), True)
        return -1

    try:
        platform_psuutil_class = getattr(module, PLATFORM_SPECIFIC_CLASS_NAME)
        platform_psuutil = platform_psuutil_class()
    except AttributeError, e:
        print("Failed to instantiate '%s' class: %s" % (PLATFORM_SPECIFIC_CLASS_NAME, str(e)), True)
        return -2

    return 0

# Load platform-specific psuutil class
err = load_platform_psuutil()
if err != 0:
    sys.exit(2)

presence = platform_psuutil.get_psu_presence(1)

print("PSU 1 presence: {}".format(presence))

```


### Sample code to print PSU1 status using new API

```
#!/usr/bin/env python

import sonic_platform

platform = sonic_platform.platform.Platform()

chassis = platform.get_chassis()
if not chassis:
    print("Error getting chassis!")
    sys.exit(1)

psu1 = chassis.get_psu(1)
if not psu1:
    print("Error getting psu1!")
    sys.exit(2)

presence = psu1.get_presence()

print("PSU 1 presence: {}".format(presence))
```

### New Platform API Framework location

https://github.com/sonic-net/sonic-platform-common/tree/master/sonic_platform_base
