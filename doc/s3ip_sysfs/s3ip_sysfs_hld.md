# S3IP sysfs specification and S3IP sysfs framework HLD #

## Table of Content 

 * [Scope](#scope)
 * [Definitions/Abbreviation](#definitionsabbreviation)
 * [1. Overview](#1-overview)
 * [2. S3IP sysfs specification](#2-s3ip-sysfs-specification)
   * [2.1 S3IP sysfs specification scenario](#21-s3ip-sysfs-specification-scenario)
   * [2.2 Design of the S3ip sysfs specification](#22-design-of-the-s3ip-sysfs-specification)
 * [3. S3IP sysfs framework](#3-s3ip-sysfs-framework)
   * [3.1 S3IP sysfs framework scenario](#31-s3ip-sysfs-framework-scenario)
   * [3.2 S3IP sysfs framework design](#32-s3ip-sysfs-framework-design)
   * [3.3 Porting guide](#33-porting-guide)


### Revision  
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 | 08/16/2022  |     timstian       | Initial version                   |

### Scope  
This document describes the SONiC sysfs specification and the design of the SONiC sysfs generation framework.

### Definitions/Abbreviations 
| Abbreviation             | Description                                       |
|--------------------------|---------------------------------------------------|
| S3IP                     | Simplified Switch System Integration Program      |
| CPLD                     | Complex Programmable Logic Device                 |
| I2C                      | Inter-Integrated Circuit                          |
| SAI                      | Switch Abstraction Interface                      |
| ODM                      | Original Design Manufacturer

### 1. Overview 

SONiC is designed to be portable to a variety of network devices. Many devices share the same ASIC platform and only differ in device-specific hardware components, such as PSUs, fan modules, and environment sensors. Currently, ODM vendor provides drivers to expose the device-specific hardware through sysfs, allowing SONiC to communicate with them, as described in the [Porting Guide](https://github.com/sonic-net/SONiC/wiki/Porting-Guide). However, many inefficient porting works are still required for SONiC developers due to different drivers from different devices. 

The S3IP sysfs specification defines a unified interface to access peripheral hardware on devices from different vendors, making it easier for SONiC to support different devices and platforms.

**Requirements for S3IP sysfs:**
1. Should be able to work with the existing platform APIs
2. The hierarchy of sysfs path structure should be defined in a specification.
3. The sysfs path in the specification should be defined clearly, thus, platform API and test cases can be reused.
4. The sysfs directory structure can be generated automatically through the framework.
5. Support reuse of the old driver sysfs paths without redeveloping new drivers.

**S3IP background Introduction**

Simplified Switch System Integration Program, aka [S3IP](http://www.s3ip.org/), is the subproject of the Open Data Center Committee, aka [ODCC](http://www.opendatacenter.cn/introduction-en.html). S3IP is a joint initiative of six Internet companies in China, including Baidu, Alibaba, Tencent, Meituan, JD.com, and Kuaishou. Focusing on the network field, S3IP aims to solve the common problems in the integration process of the upper layer software and the lower layer equipment and establish a standardized ecology. The standardized design is more friendly to equipment manufacturers and enterprise users (such as the Internet), easier to integrate, more efficient to solve problems with the help of ecological forces, and faster to implement new technologies in the ecosystem.

S3IP sysfs contains two sections:

- sysfs specification: specifies the sysfs directory structure and file content
- sysfs framework: generate the sysfs directory structure that conforming to the specification.

### 2. S3IP sysfs specification
#### 2.1 S3IP sysfs specification scenario

Figure2-1 where S3IP sysfs is used.

![scenario](/images/s3ip_sysfs/s3ip_sysfs_scenario.svg)

The S3IP sysfs specification is represented as an organized sysfs directory structure on white-box devices. Device management software and debugging tools need to access hardware through this interface.

Both vendors and users should comply with the S3IP sysfs specification. Device vendors focus on the specification implementation, while users verify the usability of the device against this specification. Vendors should provide software access to every sensor capable of being read. For any available sensor, vendors shall provide S3IP sysfs access.

Figure2-2 S3IP sysfs diretory demo

![demo](/images/s3ip_sysfs/s3ip_sysfs_demo.png)

#### 2.2 Design of the S3ip sysfs specification
Design Principles
 - Unified, well-specified behavior, consistent experience among all SONiC devices, regardless of underlying platform; 
 - Easy to understand, implement, test and debug
 - The sysfs root directory must be "/sys_switch", and the directory and its subdirectories or files can be soft links. For example, it is legal to link a file from /sys to /sys_switch.
 - The contents of files in sysfs should be generated dynamically, using the same mechanism as the file contents in the /sys path of the Linux system.
 - Sysfs has no specific CPU architecture requirements.
 - Each file in sysfs represents a hardware property, and the property unit should be omitted.
 - When a switch contains multiple devices of the same type, sysfs must be uniquely identified by the natural numbers 1 to n. For example, /sys_switch/fan/fan1 represents information about fan number 1
 - This specification defines the path name, permissions, data type, and data unit for each hardware
 - The sysfs path defined in this specification must exist, and the file content should be "NA" if no hardware is available.

S3IP sysfs specification : [specification](/doc/s3ip_sysfs/s3ip_sysfs_specification.md)

S3IP sysfs specification hierarchy overview
- sys_switch
  - cpld
    - number
    - cpld1
       - alias
       - type
       - ...
  - psu
  - syseeprom
  - sysled
  - transceiver
  - temp_sensor
  - vol_sensor
  - cur_sensor
  - watchdog
  - slot
  - fpga


### 3. S3IP sysfs framework
#### 3.1 S3IP sysfs framework scenario
The goal of the S3IP sysfs framework is to make it easy for vendors to generate sysfs directory structures that conform to the S3IP sysfs specification. 

![framework_scenario](/images/s3ip_sysfs/s3ip_sysfs_framework_scenario.svg)

S3IP sysfs framework contains two parts。
 - S3ip_sysfs_service: kernel module management, configuration file parsing and /sys_switch directory generation.
 - S3ip_sysfs_framework: the framework kernel module.

#### 3.2 S3IP sysfs framework design
Design Principles
 - Keep kernel modules as simple as possible.
 - Reuse sysfs paths of existing drivers as much as possible.
 - Easy to implement and debug.

The process for creating /sys_switch/

![setup_flow](/images/s3ip_sysfs/s3ip_sysfs_setup_flow.svg)

Flow to get the fan speed

![get_flow](/images/s3ip_sysfs/s3ip_sysfs_get_info_flow.svg)

 the code for submission:
 - Two device platforms that conform to the S3IP sysfs specification will be submitted to the buildimage repository
 - S3ip sysfs framework will be submitted to the sonic-platform-common repository 

##### 3.2.1 s3ip sysfs kernel module

The specification is not only a guideline, but also contains requirements for implementation. The kernel module is designed to make it easy to meet those details. 

S3IP sysfs kernel module(aka s3ip_sysfs.ko) provided the following features:

1. Register/unregister mechanisms to interact with the s3ip_sysfs.ko.

2. Dynamically generate/destroy the corresponding directory when a driver that uses s3ip_sysfs.ko is installed/uninstalled.  

Sample code for the watchdog interactive interface, The s3ip_sysfs.ko implements this code

```
struct s3ip_sysfs_watchdog_drivers_s {
    ssize_t (*get_watchdog_identify)(char *buf, size_t count);
    ssize_t (*get_watchdog_state)(char *buf, size_t count);
    ssize_t (*get_watchdog_timeleft)(char *buf, size_t count);
    ssize_t (*get_watchdog_timeout)(char *buf, size_t count);
    int (*set_watchdog_timeout)(int value);
    ssize_t (*get_watchdog_enable_status)(char *buf, size_t count);
    int (*set_watchdog_enable_status)(int value);
};

extern int s3ip_sysfs_watchdog_drivers_register(struct s3ip_sysfs_watchdog_drivers_s *drv);
extern void s3ip_sysfs_watchdog_drivers_unregister(void);
 
```

Sample code exposes watchdog register to sysfs, This code should be implemented by the vendor

```
#define WDT_INFO(fmt, args...) LOG_INFO("watchdog: ", fmt, ##args)
...
/*
 * demo_set_watchdog_enable_status - Used to set watchdog enable status,
 * @value: enable status value, 0: disable, 1: enable
 *
 * This function returns 0 on success,
 * otherwise it returns a negative value on failed.
 */
static int demo_set_watchdog_enable_status(int value)
{
    /* add vendor codes here */
    return -ENOSYS;
}

static struct s3ip_sysfs_watchdog_drivers_s drivers = {
    /*
     * set ODM watchdog sensor drivers to /sys/s3ip/watchdog,
     * if not support the function, set corresponding hook to NULL.
     */
    .get_watchdog_identify = demo_get_watchdog_identify,
    .get_watchdog_state = demo_get_watchdog_state,
    .get_watchdog_timeleft = demo_get_watchdog_timeleft,
    .get_watchdog_timeout = demo_get_watchdog_timeout,
    .set_watchdog_timeout = demo_set_watchdog_timeout,
    .get_watchdog_enable_status = demo_get_watchdog_enable_status,
    .set_watchdog_enable_status = demo_set_watchdog_enable_status,
};

static int __init watchdog_dev_drv_init(void)
{
    int ret;

    WDT_INFO("watchdog_init...\n");

    ret = s3ip_sysfs_watchdog_drivers_register(&drivers);
    if (ret < 0) {
        WDT_ERR("watchdog drivers register err, ret %d.\n", ret);
        return ret;
    }
    WDT_INFO("watchdog create success.\n");
    return 0;
}

static void __exit watchdog_dev_drv_exit(void)
{
    s3ip_sysfs_watchdog_drivers_unregister();
    WDT_INFO("watchdog_exit success.\n");
    return;
}

module_init(watchdog_dev_drv_init);
module_exit(watchdog_dev_drv_exit);
```

##### 3.2.2 s3ip sysfs service
Workflow of the S3ip sysfs service
- Delete old data, such as the /sys_switch directory and subdirectories
- Install kernel modules, including s3ip_sysfs.ko and other driver kernel modules
- Parse the configuration file and create the /sys_switch directory

The S3ip sysfs service (aka s3ip_sysfs.service) configuration file is designed to simplify the /sys_switch directory creation process.
The configuration file contains the following metadata:
- path: Indicates the specific path of /sys_switch
- type: Indicates the type of the path 
  - string: fixed string type
  - path: real path type
- value: indicates the real path or fixed string

Sample configuration file to make /sys_switch witch S3ip sysfs Service 

```
{
  "s3ip_syfs_paths": [
    # The /sys_switch/fan/num path specify the number of fans on the platform. This configuration makes the path read-only and return "6" in string format.
    {
      "path": "/sys_switch/fan/num",
      "type" : "string",
      "value" : "6",
      "description": "number of fan"
    },
    # The /sys_switch/syseeprom path specify the syseeprom information. This configuration makes the path linked to /sys/class/i2c_adapter/i2c-block/hwmon/hwmon1/eeprom2/2-0048, so we can reuse old driver sysfs path
    {
      "path":"/sys_switch/syseeprom",
      "Type":"path",
      "Value":"/sys/class/i2c_adapter/i2c-block/hwmon/hwmon1/eeprom2/2-0048"
    },
    # the /sys_switch/fan give you all fan infomations. This configuration makes the path linked to /sys/s3ip/fan, so we can use driver base on the s3ip sysfs kernel module framework
    {
      "path":"/sys_switch/fan ",
      "Type":"path",
      "value":"/sys/s3ip/fan"
    }
  ]
}
```
#### 3.3 Porting guide
1. git clone sonic-buildimage to get the S3IP framework, the path framework is at sonic-buildimage/platform/s3ip-sysfs
2. Verify the availability of the S3IP framework on the host computer
 - Generate a host package, run the following command
     - sonic-buildimage/platform/s3ip-sysfs/build.sh
 - Install the package, run the following command
     - dpkg -i s3ip-sysfs_1.0.0_amd64.deb
 - Check the /sys_switch directory, run the following command
     - tree -psv /sys_switch/
3. Porting S3IP sysfs framework to platform project
 - Create the S3IP sysfs service configuration file. 
     - Modify sonic-buildimage/platform/s3ip-sysfs/scripts/s3ip_sysfs_conf.json to create a configuration file
     - This file should be installed to /etc/s3ip/s3ip_sysfs_conf.json on the device
 - Implement the platform hardware driver, and export parameters through s3ip_sysfs.ko
     - s3ip_sysfs. ko is generated by compiling sonic-buildimage/platform/s3ip-sysfs/s3ip_sysfs_frame source code
 - Install the s3ip-sysfs.service on the device
    - Copy service file sonic-buildimage/platform/s3ip-sysfs/scripts/s3ip-sysfs.service to the project.
    - The service file needs to be installed in /etc/systemd/system/s3ip-sysfs.service on the device.
    - When the platform package is installed, the vendor should enable s3ip-sysfs.service and start this service automatically when the device reboot
    - After the platform package is uninstalled, the vendor should disable the s3ip-sysfs.service and remove the service file
4. Self-test after integration
   - Ensure that the /sys_switch directory conforms to the S3IP sysfs specification 
   - Hardware property information can be read and written normally

### 4 Compare with [PDDF](https://github.com/sonic-net/SONiC/blob/master/doc/platform/brcm_pdk_pddf.md)

The S3IP sysfs specification is intended to provide a more general set of hardware access interfaces. Using sysfs is definitely the best option, as it fits into the Linux design philosophy of everything being a file, and there are more tools and languages to deal with it.

For traditional driver engineers, The S3IP SYSFS interface is very friendly and easy to debug, they only need to care about the content and format of the sysfs node. So the learning cost is zero and it's easy to understand and implement. 

For ODM vendors new to SONIC, opt for PDDF because you can do platform adaptation with a configuration file, which is cool and popular.

S3IP SYSFS and PDDF both share similar goals of reducing vendor adaptation effort and increasing the reusability of device management software.

However, there are many differences between the two frameworks, which are listed below. ODM vendors can choose the framework based on actual requirements.

| Item  | S3IP sysfs|PDDF|
|-|-|-|
|Requirements| The requirements are put forward from the user's perspective, and the sysfs node is summarized from the actual operation experience. The goal is to unify the interface for device management | The requirements are proposed from technical point of view aimed at platform driver and APIs development in SONiC. Only those SysFS which are required by SONiC platform APIs are exposed.
|Ecosystem | Devices compliant with S3IP SYSFS specification have been widely used in data centers.<br> The [S3IP](http://www.s3ip.org/) project involved both vendors and users[S3IP] (including Tencent, Alibaba, Baidu, Kuaishou, Meituan, Jingdong and more than a dozen ODM vendors). Vendors and users complete a closed-loop of requirements, standards and debugging tools that have the ability to iterate continuously. | PDDF is a new framework and it is developed in the SONiC context. Some ODM platforms are already using PDDF. PDDF is an underlying framework which ODMs can use for faster development but it does not exposes any fixed SysFS nodes to the user.
|Development Mode | Regular development model,<br>Programming is required to implement the requirements. <br>ODM venders need to provide professional driver support for customers，Customers validating device with sysfs| ODM vendors can use common PDDF kernel drivers and user space common platform APIs. Only some platform specific device data needs to be provided by the ODMs in the form of JSON files. Validation is via usual SONiC CLIs.
|Flexible | 1.Bus independent, The hardware support:<br>Fan<br>PSU<br>System EEPROM<br>Transceivers<br>CPLD<br>FPGA<br>System LED<br>Temperature sensors<br>Current sensors<br>Voltage sensors<br>Slot<br>Watchdog<br><br>2.Support scenarios with many customization requirements, such as FPGA-Polling, BMC management hardware and firmware upgrades <br><br>3.Normalized SYSFS is easy for hardware fault identification and prediction <br><br>4.Easy to debug for ODM users, and they need not care about the bus topology |PDDF can be used on the platforms which use I2C bus to communicate with the peripheral devices. Platforms which use BMC can also be brought up using PDDF. In future PDDF would be supported on platform using PCIE FPGA devices.
|code position |  https://github.com/sonic-net/sonic-buildimage/tree/master/platform/s3ip-sysfs| https://github.com/sonic-net/sonic-buildimage/tree/master/platform/pddf

PDDF is not incompatible with S3IP SYSFS, we will combine the two parts into two Phases:

Phase 1: The S3IP SYSFS Framework is integrated into the SONiC community so that Chinese ODM vendors can more easily contribute their existing platforms to the community, and other vendors can also have the opportunity to adapt their platforms according to S3IP specifications and expand their business opportunities in China. This is good for SONiC community ecosystem;

Phase 2: PDDF and the S3IP SYSFS Framework will be integrated and presented as a framework, which makes more sense. Consumers decide whether to comply with the S3IP SYSFS specification by customizing the options provided by the framework.

### SAI API 
N/A
### Configuration and management 
N/A
#### Manifest (if the feature is an Application Extension)
Paste a preliminary manifest in a JSON format.
#### CLI/YANG model Enhancements 
N/A
#### Config DB Enhancements  
N/A
### Warmboot and Fastboot Design Impact  
N/A
### Restrictions/Limitations  

### Testing Requirements/Design  

New test cases need to be added

1. Verify that the read and write properties of the sysfs node are as expected

2. Whether the value of the sysfs node is as expected

#### Unit Test cases  
N/A
#### System Test cases
N/A
### Open/Action items - if any 
N/A
	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.