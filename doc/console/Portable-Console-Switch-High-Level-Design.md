# Portable Console Device Design

## Revision

|  Rev  |   Date   |   Author   | Change Description |
| :---: | :------: | :--------: | ------------------ |
|  0.1  | 05/05/22 | Zhijian Li | Initial version    |

## Overview

In this design document, we provide the standard for adapting console devices to SONiC. If a vendor's console device implements this standard, it will work on any switch with SONiC installed.

## Assumption

1. In the current design, we only support **USB** console devices.
2. Only **one** vendor's console devices can work on a SONiC switch at the same time. If console devices from multiple vendors are plugged in at the same time, which vendor's devices will work is undefined behavior.
3. Multiple console devices of the **same model** from the **same vendor** can be daisy-chained to extend more console ports. Whether daisy-chaining is supported and how many devices are supported in daisy-chain depends on the vendor's implementation.

## Setup Portable Console Device in SONiC

After the console device is plugged into the SONiC switch, we need to set up the console device in SONiC for further use. The setup process includes:

  1. Install corresponding drivers.
  2. Map console interface from `/dev/ttyUSB<id>` to `/dev/console-<id>`. (Usually done with the help of [udev](https://wiki.debian.org/udev))
  3. Any other necessary steps.

Since we prefer the setup process completed after building SONiC image, a directory is provided to vendors to put all the files (eg. driver, udev `.rules`, etc.) they need. A `setup.sh` script file must be placed in this directory, which will be run **during the SONiC image build process**. After SONiC image has been built, all the necessary files will be installed.

![A flow diagram to explain the setup process](./Portable-Console-Switch-High-Level-Design/setup.png)

For example, vendor can prepare a `50-<vendor_name>-<model_name>.rules` file in this directory, and add the following lines in `setup.sh`:

```bash
cp ./50-<vendor_name>-<model_name>.rules /etc/udev/rules.d
```

Then SONiC will install the `.rules` correctly and load it when system boot.

### Udev `.rules` File Priority

*This part proposes conventions for vendors who use [udev](https://wiki.debian.org/udev) to map console interface.*

Since [`man udev`](https://man7.org/linux/man-pages/man7/udev.7.html) mentions that "all rules files are collectively sorted and processed in lexical order", the name of a udev `.rules` file usually start with a number which specifies the priority. The larger the number, the higher the priority the udev `.rules` file. If there is no special need, set the priority of the `.rules` file to 50. Then the file name will look like `50-<vendor_name>-<model_name>.rules`.

## CONFIG_DB Changes

### CONSOLE_SWITCH_TABLE

The `CONSOLE_SWITCH_TABLE` holds the configuration database for the purpose of console switch features. This table is filled by the management framework. Two new fields will be added to this table.

```
; Console switch feature table
key = CONSOLE_SWITCH:console_mgmt

; field = value
autodetect = "enabled"/"disabled" ; "enabled" means factory function will auto detect which vendor's device is plugged in
                                  ; "disabled" means factory function will read vendor_name from config_db
vendor_name = 1*255 VCHAR         ; vendor name of console switch
```

## Portable Console Device API Design

### API Code Directory Structure

All the portable console device API code should be put in `/sonic_platform_common/sonic_console/`. The directory structure is defined as below:

```
sonic_console/
├── __init__.py
├── console_base.py
├── factory.py
├── microsoft
│   ├── __init__.py
│   └── console_simulator.py
├── <vendor-name>
    └── <vendor-name>_<model-name>.py
```

Base class will be put in `console_base.py`. Factory function for creating concrete portable console device object will be put in `factory.py`. Classes implemented by vendor will be put in corresponding `<vendor-name>` directory. The implementations of different models of the same vendor should be put in the corresponding `<vendor-name>_<model-name>.py` files. For instance, the simulator implemented by Microsoft will be put in `microsoft/console_simulator.py`.

### Base Class Design

Base class for portable console device is defined like below:

```python
# console_base.py

class PortableConsoleDeviceBase:

    @classmethod
    def is_plugged_in(cls):
        """
        Retrives whether portable console device is plugged in or not.
        This method is recommended for all vendors to implement!

        :return: Boolean, True if portable console device is plugged in
                        , False otherwise.
        """
        raise NotImplementedError

    @classmethod
    def get_vendor_name(cls):
        """
        Retrives the vendor name of the `PortableConsoleDeviceBase` concrete subclass.
        This method is mandatory for factory method to create instance from manual configuration.

        :return: String, denoting vendor name of the `PortableConsoleDeviceBase` concrete subclass.
        """
        raise NotImplementedError

    @classmethod
    def get_model_name(cls):
        """
        Retrives the model name of the `PortableConsoleDeviceBase` concrete subclass.
        This method is mandatory for factory method to create instance from manual configuration.

        :return: String, denoting model name of the `PortableConsoleDeviceBase` concrete subclass.
        """
        raise NotImplementedError

    @classmethod
    def get_instance(cls):
        """
        Build and return portable console device object.

        :return: Object derived from `PortableConsoleDeviceBase`. If object cannot be created
                 (eg. due to device not plugged in), return None.
        """
        return NotImplementedError

    def get_serial_number(self):
        """
        Retrieves the serial number of portable console device.

        :return: String, denoting serial number of portable console device.
        """
        raise NotImplementedError

    def get_virtual_device_list(self):
        """
        Retrieves the line number and virtual device list of portable console device.

        :return: A dict, the key is line number (integer, 1-based),
                         the value is virtual device path (string).
                 eg.
                 {
                     1: "/dev/console-1",
                     2: "/dev/console-2",
                     ...
                 }
        """
        raise NotImplementedError

    def get_num_psus(self):
        """
        Retrieves the number of power supply units available on the portable console device.

        :return: An integer, the number of power supply units available on the portable console
                 device.
        """
        raise NotImplementedError

    def get_all_psus(self):
        """
        Retrieves all power supply units available on the portable console device.

        :return: A list of objects derived from `sonic_psu.pus_base.PsuBase` representing all
                 power supply units available on portable console device.
        """
        raise NotImplementedError

    def get_psu(self, index):
        """
        Retrieves power supply unit represented by (0-based) index <index>

        :param index: An integer, the index (0-based) of the power supply unit to retrieve
        :return: An objects derived from `sonic_psu.pus_base.PsuBase` representing the specified
                 power supply unit.
        """
        raise NotImplementedError
```

Vendors can simply inherit the base class and implement the interface methods. For the methods cannot support, vendors should raise a `TypeError` exception.

> This exception (`TypeError`) may be raised by user code to indicate that an attempted operation on an object is not supported, and is not meant to be.
> 
> --[Built-in Exceptions — Python documentation](https://docs.python.org/3/library/exceptions.html#TypeError)

For example, `PortableConsoleDeviceSimulator` will be implemented like:

```python
# microsoft/console_simulator.py
from sonic_console.console_base import PortableConsoleDeviceBase

class PortableConsoleDeviceSimulator(PortableConsoleDeviceBase):

    def __init__(self):
        pass

    @classmethod
    def is_plugged_in(cls):
        return False

    @classmethod
    def get_vendor_name(cls):
        return "Microsoft"

    @classmethod
    def get_model_name(cls):
        return "Simulator"

    @classmethod
    def get_instance(cls):
        return PortableConsoleDeviceSimulator()

    def get_serial_number(self):
        return "Microsoft-Simulator-S/N"

    def get_virtual_device_list(self):
        return {
            1: "/dev/console-1",
            2: "/dev/console-2",
            # ...
        }

    def get_num_psus(self):
        return 0

    def get_all_psus(self):
        return []

    def get_psu(self, index):
        return None
```

### Factory Function Design

Factory function `get_portable_console_device` supports three ways to identify which subclass should be used to create portable console device object:

1. Use function parameter `vendor_name` to specify which subclass to use. (Highest priority)
2. If `autodetect` is set to `disabled` in `config_db`, then use `vendor_name` in `config_db` to specify which subclass to use. (Second priority)
3. If `autodetect` is set to `enabled`, then use `is_plugged_in` method of all the derived subclass to detect which vendor's device is plugged in, and use the corresponding subclass. (Lowest priority but **recommended**)

The flow chart below describes how `get_portable_console_device` function works:

![factory-function-flow-chart.png](./Portable-Console-Switch-High-Level-Design/factory-function.png)

As mentioned above, only the third way is our recommendation, which can automatically find out which vendor's device is plugged in and create the corresponing object. The first and second ways are reserved for more flexibility, so they are given higher priority.

## SONiC CLI Design

### show console

#### show console summary

#### show console vendor-name

#### show console serial-number

### show psu

### config(?)

## Reference

* [udev - Linux dynamic device management](https://wiki.debian.org/udev)
* [udev(7) - Linux manual page](https://man7.org/linux/man-pages/man7/udev.7.html)