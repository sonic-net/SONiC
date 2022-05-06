# Portable Console Device API Design

## Revision

|  Rev  |   Date   |   Author   | Change Description |
| :---: | :------: | :--------: | ------------------ |
|  0.1  | 05/05/22 | Zhijian Li | Initial version    |

## Background

Support console device on different SONiC switches.

## Assumption

1. Only support **USB** console device.
2. Only support **one** console device per SONiC switch.

## Setup Portable Console Device in SONiC

After console device be plugged in the SONiC switch, we need to setup the console device in SONiC for further use. The setup process includes:

  1. Install corresponding drivers.
  2. Prepare a udev `.rules` file in `/etc/udev/rules.d/` which can map console interface from `/dev/ttyUSB<id>` to `/dev/console-<id>`.
  3. Any other necessary steps.

Since we prefer the setup process complete after building SONiC image, a directory is provided to vendors to put all the files (eg. driver, udev `.rules`, etc.) they need. A `setup.sh` script file must be placed in this directory, which will be run during the SONiC image build process. After SONiC image has been built, all the necessary files will be installed.

For example, vendor can prepare a `<vendor_name>-<model_name>.rules` file in this directory, and add the following lines in `setup.sh`:

```bash
cp ./<vendor_name>-<model_name>.rules /etc/udev/rules.d
```

Then SONiC will install the `.rules` correctly and load it when system boot.

## Portable Console Device API Design

### API Code Directory Structure

All the portable console device API code should be put in `/sonic_platform_common/sonic_portable_console_device/`. The directory structure looks like below:

```
sonic_portable_console_device/
  ├── __init__.py
  ├── base.py
  ├── factory.py
  ├── vendor_1.py
  └── vendor_2.py
```

Base class will be put in `base.py`. Classes implemented by vendor will be put in corresponding `<vendor-name>.py`. Factory function for creating actual portable console device object will be put in `factory.py`. 

### Base Class Design

Base class for portable console device is defined like below:

```python
# base.py

class PortableConsoleDeviceBase:
    def __init__(self):
        pass

    def is_plugged_in(self):
        raise NotImplementedError

    def get_serial_number(self):
        raise NotImplementedError

    def get_vendor_name(self):
        raise NotImplementedError

    def get_virtual_device_list(self):
        raise NotImplementedError
```

Vendors can simply inherit the base class and implement the interface methods. For the methods cannot support, vendors can also raise a `NotImplementedError` exception.

### Factory Function Design

Factory function `get_portable_console_device` supports three ways to identify which class should be used to create portable console device object. The code will look like:

```python
# factory.py

from .vendor_1 import PortableConsoleDeviceVendor1
from .vendor_2 import PortableConsoleDeviceVendor2

PORTABLE_CONSOLE_DEVICE_MAPPING = {
    # '<vendor-name>': VendorClass
    'Vendor1': PortableConsoleDeviceVendor1,
    'Vendor2': PortableConsoleDeviceVendor2,
}

def get_portable_console_device(vendor=None):
    # Firstly, try to use argument `vendor_name` to create the object.
    if vendor in PORTABLE_CONSOLE_DEVICE_MAPPING:
        return PORTABLE_CONSOLE_DEVICE_MAPPING[vendor]()

    # Secondly, try to read vendor_name from /etc/sonic/portable_console_device.
    try:
        with open('/etc/sonic/portable_console_device', mode='r') as cfg:
            vendor = cfg.read().strip()
    except FileNotFoundError:
        pass
    if vendor in PORTABLE_CONSOLE_DEVICE_MAPPING:
        return PORTABLE_CONSOLE_DEVICE_MAPPING[vendor]()

    # Finally, automatically detect which vendor's device is plugged in. (recommanded)
    for Device in PORTABLE_CONSOLE_DEVICE_MAPPING.values():
        device = Device()
        try:
            if device.is_plugged_in():
                return device
        except Exception:
            continue
    
    return None
```

As mentioned above, only the third way is our recommendation, which can automatically find out which vendor's device is plugged in and create the corresponing object. The first and second ways are reserved for more flexibility, so they are given higher privilege.

The `is_plugged_in` method is defined as below:

```python
# base.py

class PortableConsoleDeviceBase:
    def is_plugged_in(self):
        """
        This API returns whether console device is plugged in or not.
        This method is recommended for all vendors to implement!

        Args:

        Returns:
            a boolean, True if vendor's console device is plugged in
                     , False if vendor's console device is not plugged in.
        """
        raise NotImplementedError
```

If vendor cannot implement the `is_plugged_in` API, the vendor name must be manually configured in `/etc/sonic/portable_console_device` after the device plugged in. Otherwise, the portable console device object cannot be created.
