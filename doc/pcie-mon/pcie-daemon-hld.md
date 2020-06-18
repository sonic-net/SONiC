# SONiC PCIe Monitoring services HLD #

### Rev 0.1 ###

### Revision
 | Rev |     Date    |       Author       | Change Description                             |
 |:---:|:-----------:|:------------------:|------------------------------------------------|
 | 0.1 |             |     Sujin Kang     | Initial version                                |
 | 0.2 |             |     Sujin Kang     | Add rescan for pcie device missing during boot | 
 |     |             |                    | Add pcied to PMON for runtime monitoring       |

## About This Manual ##

This document is intend to give the idea of how to monitor the platform PCIe devices and alert any problem on PCIe buses and devices on SONiC using pcie-mon service and pcied on PMON container.


## 1. PCIe Monitor service design ##

New PCIe Monitor service is designed to use the PcieUtil utility to check the current status of PCIe devices and buses and alert if there is any missing devices or any error while communicating on the PCIe buses.

PCIe device monitoring will be done in two separate services, `pcie-mon.service` which is a systemd service, will monitor the PCIe device during the boot time and `pcied` which is a daemon in PMON container will monitor during the runtime.

First, pcie-mon.service will be added to check the pcie device enumeration status, trigger the pci device rescan if there is any missing device and indicate any device missing to the party that are interested in the device enumeration, for example, kernel_bde driver, platform drivers and etc.

Second, pcid in PMON will perform the periodic pcie device check during the run time.

Both pcie-mon.service and pcied will update the state db with the PCIe device status whenever it changes.

### 1.1 Access the PCIe devices and buses from platform ###

PCIe device information can be accessed via read files under (e.g. `/sys/bus/pci/devices/0000:01:00.1`), different vendors may have under different folders, these folder need to be mounted to platform container so pcied can access them. 

For the convenience of implementation and reduce the time consuming, pcie-mon.service will use the `pcieutil` which is the pcie diag tool. `pcieutil` is implemented based on platform_base.sonic_pcie.`PcieUtil` class.

1. `pcieutil` should get the platform specific PCIe device information and monitor the PCIe device and bus status with PcieUtil.get_pcie_check and update the STATE_DB based on get_pcie_check results.

2. `PcieUtil` will provide APIs `load_config_file`, `get_pcie_device` and `get_pcie_check` to get the expected PCIe device list and informations, to get the current PCIe device information, and check if any PCIe device is missing or if there is any PCIe bus error.

![pcieinfo_design](https://github.com/Azure/SONiC/blob/master/doc/pcieinfo_design.md)

### 1.2 PCIe device configuration file ###

PcieUtil needs to get the expected PCIe device information to check the PCIe device status periodically, which is different for each platform/hardware sku.

Each vendor need to generate the PCIe device configuration file name as pcie.yml and locate the file under device/<platform>/<hardware_skus>/plugins. 

Example) Location: `device/celestica/x86_64-cel_seastone-r0/plugins/pcie.yaml`

```
...
- bus: '01'
  dev: '00'
  fn: '0'
  id: b960
  name: 'Ethernet controller: Broadcom Limited Broadcom BCM56960 Switch ASIC'
- bus: '01'
  dev: '00'
  fn: '1'
  id: b960
  name: 'Ethernet controller: Broadcom Limited Broadcom BCM56960 Switch ASIC'
```

### 1.3 PCIe device status check ###


The default PCIe device check function, get_pcie_check is implemented in PcieUtil class at sonic_platform_base/sonic_pcie/pcie_common.py.
It loads the PCIe device configuration file and compares them with the enumerated devices based on the platform sysfs device tree under /sys/bus/pci/devices/.

Here we define a common platform API to in class `PcieBase`: 

    @abc.abstractmethod
    def get_pcie_check(self, timeout=0):
        """
         Check Pcie device with config file
         Returns:
            A list including pcie device and test result info
        """
        return []

Each vendor need to implement this function in `PcieBase` plugin if vendor has any additional pcie healthy check method.

PcieUtil calls this API to check the PCIe device status, following example code showing how this API will be called:

    while True:
        status, device_dict = platform_pcieutil.get_pcie_check()
        if(status):
            for key, value in device_dict.iteritems():
                print("Device on PCIe bus: %s" was %s" % (key, value))
                 
### 1.4 PCIe Monitor Service `pcie-mon.service` flow ###

pcie-mon.service will be started by systemd during boot up and it will spawn a thread to check PCIe device status and perform the rescan pci devices if there is any missing devices after rc.local.service is completed and it will update the state db with pcie device satus during the `pcieutil pcie-chek` call so that the dependent services/container or kernel driver can be started or stopped based on the status.

Detailed flow as showed in below chart: 
![](https://github.com/Azure/SONiC/blob/master/images/pcie-mon.svg)


### 1.5 PCIe daemon `pcied` flow ###

pcied will be started by PMON container will continue monitoring the PCIe device status during run time and it will check the PCIe device status periodically every 1 minute and update the state db when the status is checked.

Detailed flow as showed in below chart:
![](https://github.com/Azure/SONiC/blob/master/images/pcied.svg)


< TBA >
## Open Questions ##

1. Current PcieUtil is limited to check the PCIe device availablility based on the configuration. 
   Can we also add the PCIe communication error status check using AER detection into get_pcie_check() api or with a separate api? 
   some plugins like, say, collectd (https://wiki.opnfv.org/display/fastpath/PCIe+Advanced+Error+Reporting+Plugin)  
