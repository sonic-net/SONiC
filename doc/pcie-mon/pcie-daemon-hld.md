# SONiC PCIe Monitor service HLD #

### Rev 0.1 ###

### Revision
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |     Sujin Kang     | Initial version                   |

## About This Manual ##

This document is intend to monitor the platform PCIe devices and alert any problem on PCIe buses and devices.


## 1. PCIe Monitor service design ##

New PCIe Monitor service is designed to use the PcieUtil utility to check the current status of PCIe devices and buses and alert if there is any missing devices or any error while communicating on the PCIe buses.

### 1.1 Access PCIe devices and buses from platform container ###

PCIe device information can be accessed via read files under (e.g. `/sys/bus/pci/devices/0000:01:00.1m`), different vendors may have under different folders, these folder need to be mounted to platform container so pcied can access them. 


For the convenience of implementation and reduce the time consuming, pcie-mon.service will use the `pcieutil` which is the pcie diag tool. `pcieutil` is implemented based on platform_base.sonic_pcie.`PcieUtil` class.

1. `PcieUtil` should get the platform specific PCIe device information and monitor the PCIe device and bus status.

2. `PCIeUtil` will provide APIs `load_config_file`, `get_pcie_device` and `get_pcie_check` to get the expected PCIe device list and informations, to get the current PCIe device information, and check if any PCIe device is missing or if there is any PCIe bus error.

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
                 
### 1.3 PCIe daemon flow ###

pcie-mon.service.timer will be started by systemd during boot up and it will trigger the pcie-mon.service to spawn a thread to check PCIe device status in 10 seconds after rc.local.service is completed and it will periodically spawn to monitor the PCIe devices every 1 minutes.

Detailed flow as showed in below chart: 
![](https://github.com/Azure/SONiC/blob/master/images/pcie-mon.svg)


< TBA >

## Open Questions ##

1. Current PcieUtil is limited to check the PCIe device availablility based on the configuration. 
   Can we also add the PCIe AER detection into get_pcie_check() api? 
   some plugins like, say, collectd (https://wiki.opnfv.org/display/fastpath/PCIe+Advanced+Error+Reporting+Plugin)  

