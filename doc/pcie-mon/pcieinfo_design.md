## Motivation
Add a PCIe Diag tool for SONiC. This tool including three commands    
### Commands

    show platform pcieinfo     -----> Show current device PCIe info
    show platform pcieinfo -c  -----> Check whether the PCIe info is correct   
    pcieutil pcie_generate     -----> Generate an PCIe info congfig file

## Implementation 
### show utility update
New item under menu `platform` in `show/main.py`  
It will execute `pcieutil [options]`command

**Syntax**

     show  platform pcieinfo         ---->  pcieutil pcie_show
     show  platform pcieinfo --check ---->  pcieutil pcie_check
     show  platform pcieinfo -c      ---->  pcieutil pcie_check


### pcieutil utility
New utility in `sonic-utilities/pcieutil/`  
It will import device plugin `pcie_commonl.py` and print the output returned by different API functions  

**Syntax:**

    pcieutil pcie_show
This command will show the current PCIe info of current device

    pcieutil pcie_check
This command will compare the pcie info it got currently with config file pcie.yaml

    pcieutil pcie_generate
This command will generate pcie.yaml which used to record the original pcie info,to avoid use it by mistake,this command can not be executed by `show platform pcieinfo` command,but you can use it alone

**Common API**

Location: `sonic_platform_base/sonic_pice/pcie_common.py`

Function: This file is used to fulfill the main interfaces including functions

* **get_pcie_device()**
     * Return a list including current pcie info of the device;
* **get_pcie_check()**
    * Return a list including compare the result of comparison,if not found the config file pcie.yaml .it will raise a system erron and exit
* **dump_conf_yaml()**
    * To generate pcie.yaml which used to record the original pcie info
    
**Config file**

Location: `device/Platofrm/plugins/pcie.yaml`

Function: This file is used to as a standard to distinguish the device PCIe info. for different platform, config file will locate in differnet path

***Format***

    - bus: '00'
      dev: '00'
      fn: '0'
      id: 1f0c
      name: 'Host bridge: Intel Corporation Atom processor C2000 SoC Transaction Router'
    - bus: '00'
      dev: '01'
      fn: '0'
      id: 1f10
      name: 'PCI bridge: Intel Corporation Atom processor C2000 PCIe Root Port 1'
    - bus: '00'
      dev: '02'
      fn: '0'
      id: 1f11
      name: 'PCI bridge: Intel Corporation Atom processor C2000 PCIe Root Port 2'
    - bus: '00'
      dev: '03'
      fn: '0'
      id: 1f12
      name: 'PCI bridge: Intel Corporation Atom processor C2000 PCIe Root Port 3'
    ......

## Command Output

    root@sonic:~# show platform pcieinfo
    ==============================Display PCIe Device===============================
    ......
    bus:dev.fn 01:00.0 - dev_id=0xb960, Ethernet controller: Broadcom Limited Device b960
    bus:dev.fn 01:00.1 - dev_id=0xb960, Ethernet controller: Broadcom Limited Device b960

    root@sonic:~# show platform pcieinfo -c
    ===============================PCIe Device Check================================
    Error: [Errno 2] No such file or directory: '/usr/share/sonic/device/x86_64-cel_seastone-r0/plugins/pcie.yaml'
    Not found config file, please add a config file manually, or generate it by running [pcieutil pcie_generate]

    root@sonic:~# pcieutil pcie_generate
    Are you sure to overwrite config file pcie.yaml with current pcie device info? [y/N]: y
    generate config file pcie.yaml under path /usr/share/sonic/device/x86_64-cel_seastone-r0/plugins

    root@sonic:~# show platform pcieinfo -c
    ===============================PCIe Device Check================================
    ......
    PCI Device: Ethernet controller: Broadcom Limited Device b960 ------------------ [Passed]
    PCI Device: Ethernet controller: Broadcom Limited Device b960 ------------------ [Passed]
    PCIe Device Checking All Test ----------->>> PASSED

    root@sonic:~# show platform pcieinfo -c
    ===============================PCIe Device Check================================
    ......
    PCI Device: Ethernet controller: Broadcom Limited Device b960 ------------------ [Failed]
    PCI Device: Ethernet controller: Broadcom Limited Device b960 ------------------ [Passed]
    PCIe Device Checking All Test ----------->>> FAILED
           

## Open questions

