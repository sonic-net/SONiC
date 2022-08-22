# S3IP Sysfs 标准和S3IP sysfs framework HLD（OCP的子项目） #

## Table of Content 

 * [Scope](#scope)
 * [Definitions/Abbreviation](#definitionsabbreviation)
 * [Overview](#overview)
 * [Requirements](#requirements)


### Revision  
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 |0.1  |2022-8-16    |     timstian       |Initial version                    |
### Scope  
本文档用于介绍SONiC sysfs标准和SONiC sysfs生成框架的设计

### Definitions/Abbreviations 
| Abbreviation             | Description                                       |
|--------------------------|---------------------------------------------------|
| S3IP                     | Simplified Switch System Integration Program      |
| CPLD                     | Complex Programmable Logic Device                 |
| I2C                      | Inter-Integrated Circuit                          |
| SAI                      | Switch Abstraction Interface                      |
| ODM                      | Original Design Manufacturer

### 1. Overview 
不同的平台有不同的外围硬件，如何用统一的接口来管理这些硬件，一直以来是SONiC社区的挑战。
SONiC社区已经提供了platform api机制（参考 https://github.com/sonic-net/SONiC/blob/master/doc/platform_api/new_platform_api.md），通常platform api通过sysfs接口访问硬件。例如，一个风扇插入设备，platform api就可以从sysfs节点读取风扇的转速、序列号等信息。
ODM模式联合开发过程中，用户往往会定制硬件（如CPLD）以提高设备可用性，硬件厂商需要编写定制化的驱动导出sysfs节点用来访问硬件，然后再通过platform api适配到更上层的管理软件。
不同硬件平台，厂商适配工作面临了如下挑战：
1、定制的硬件（如CPLD），硬件厂商驱动导出的sysfs没有规范可依据，sysfs节点呈现不是结构的
2、相同类型的设备，在不同的硬件上sysfs路径不同，无法重复利用platform api的适配代码，重复适配的工作量大
3、用于测试sysfs的测试用例，无法不断积累
4、无组织的sysfs给硬件异常、platform api异常定位带来困难
S3IP sysfs标准可以解决上述问题。如大家所知，SAI提供了统一ASIC抽象层，芯片厂商只要适配一次，控制平面的软件就可以复用，降低了适配成本。s3ip sysfs想要达到相同的效果，厂商将新的硬件平台适配S3IP sysfs标准后，管理软件、调试手段、测试用例就可以复用。

S3IP sysfs分为两部分：
sysfs标准：规定sysfs目录结构和文件内容
sysfs框架：帮助生成符合S3IP sysfs标准的sysfs目录结构。

### 2. S3IP sysfs standard
#### 2.1 S3IP sysfs标准使用的场景
#### 2.1 S3IP sysfs standard scenario

Figure2-1 shows where S3IP sysfs is used.

![scenario](/images/s3ip_sysfs/s3ip_sysfs_scenario.svg)

S3IP sysfs标准，在白盒设备上表现为有组织的sysfs目录结构。设备管理软件、调试工具需要通过该接口访问硬件。
S3IP sysfs标准是厂商和用户都遵守的标准。这样厂商可以集中精力适配S3IP sysfs标准，降低了platform api适配工作量，用户可以依赖sysfs 标准验收产品的。
Figure2-1 S3IP sysfs  demo

![demo](/images/s3ip_sysfs/s3ip_sysfs_demo.png)

#### 2.2 Design of the S3ip SYSFS standard
Design Principles, Unified, standardized behavior, Consistent experience among all SONiC devices, regardless of underlying platform; Easy to understand, implement, test and debug
1. 白盒交换机 Sysfs（以下简称 Sysfs）的根目录必须为/sys_switch，该目录以及其子目录或文件可为软连接。例如，将/sys 目录下的文件软连接到/sys_switch 目录中。
2. Sysfs 中文件的内容宜动态生成，内容生成机制与 linux 系统/sys 目录下的文件内容生成机制相同。
3. Sysfs 没有特定的 CPU 架构要求， 应支持 linux 适配的 CPU 架构。
4. Sysfs 中每个文件代表一种硬件属性，属性单位省略。
5. 交换机包含多个相同类型器件时， Sysfs 必须用 1 到 n 的自然数唯一标识。例如/sys_switch/fan/fan1 代表编号为 1 风扇的信息
6. 本规范定义了 Sysfs，具体内容包括中各硬件对应的路径名称和文件名称，文件读写权限，数据类型，数据单位。
7. 本规范定义的 Sysfs 路径必须存在，如果没有对应硬件，文件内容应为“NA”。
8. Sysfs 可提供/sys_switch/info 文件，内容为全部硬件的信息，格式为 json 格式。

S3IP sysfs specifiction : [specifiction](/doc/s3ip_sysfs/s3ip_sysfs_specification.md)

S3IP sysfs Hierarchy
- sys_switch
  - cpld
    - number
    - cpld1
       - alias
       - type
       - ...
  - fan
    - number
    - fan1
      - model_name
      - hardware_version
  - psu
  - syseeprom
  - sysled
  - transceiver
  - temp_sensor
  - vol_sensor
  - cur_sensor
  - watchdog
  - slot


### 3. S3IP sysfs framework
#### 3.1 S3IP sysfs framework scenario
The goal of the S3IP sysfs framework is to make it easy for vendors to generate sysfs directory structures that conform to the S3IP sysFS standard. 

![framework_scenario](/images/s3ip_sysfs/s3ip_sysfs_framework_scenario.svg)
 
#### 3.2 Architecture Design
Design Principles
 - Kernel modules kept as simple as possible，Simply expose parameters
 - Reuse sysfs paths of existing drivers as much as possible
 - The service provides the functionality of sysfs path mapping
 - Easy to implement and debug

S3IP sysfs framework contains two parts。
 - S3ip_sysfs_service: provides sysfs path mapping, S3IP framework kernel module installation, and other functions
 - S3ip_sysfs_frame: S3IP framework kernel module

![setup_flow](/images/s3ip_sysfs/s3ip_sysfs_setup_flow.svg)

![get_flow](/images/s3ip_sysfs/s3ip_sysfs_get_info_flow.svg)

Structure of the code:
 - In the buildimage directory, the S3IP sysFS compliant TENCENT_TCS84 device product,
 -At https://github.com/sonic-net/sonic-platform-common, s3ip sysfs framework and s3ip sysfs service

代码的结构：
1. 在buildimage目录，符合s3ip sysfs标准的tencent_tcs84 device产品，
2. 在https://github.com/sonic-net/sonic-platform-common，s3ip sysfs framework

##### 3.2.1 s3ip sysfs kernel module
s3ip sysfs kernel module包含了符合S3IP Sysfs的标准推荐实现。
提供了如下特性：
1、为不同类型硬件提供了单独头文件。如风扇的框架头文件为s3ip_fan.h；电源的框架头文件为s3ip_psu.h
2、不同类型硬件驱动，使用动态注册/解注册机制与S3IP sysfs框架交互。
3、不同类型硬件（如电源）sysfs驱动，在insmod时，会在/sys/s3ip/下动态生成对应目录结构（如/sys/s3ip/psu）。
4、不同类型硬件（如电源）sysfs驱动，在rmmod时，会销毁/sys/s3ip对应目录
5、S3IP sysfs框架头文件和驱动文件


厂商适配时，以风扇驱动为例,fan.ko会引用s3ip_sysfs.ko的符号，注册回调函数，安装fan.ko后，会形成完整的/sys/s3ip/fan/目录。

//风扇、电源灯，具体驱动的处理函数
int fan_speed_get(para){…}
int fan_speed_set(para){…}

//回调函数结构体定义
Struct fan_driver driver={
.get_cb = fan_speed_get,
.set_cb = fan_speed_set,
…
}
//sysfs回调注册
int module_init()
{
     …
     s3ip_sysfs_fan_register(& driver);
     …
}
//sysfs回调解注册
module_exit()
{
    s3ip_sysfs_fan_unregister()
}



##### 3.2.1 s3ip sysfs service

s3ip sysfs service 启动完成的工作
  - 删除/sys_switch目录下的历史遗留信息
  - 安装内核ko文件
  - 解析配置文件，创建/sys_switch目录

s3ip sysfs service配置文件的目的在于简化/sys_switch映射流程，降低出错概率。
配置文件包含如下内容：
 - “path”：/sys_switch的具体路径
 - “type”： /sys_switch路径对应信息的类型。
     string：字符串类型，访问/sys_switch路径时，会直接返回固定字符串信息
     path：路径类型，访问/sys_switch路径时, 会重定向到真实路径
 - “value”：路径对应的值

示例1
{“path” : “/sys_switch/fan/num”,
 “type” : “string”,
 “value” : “6”}
风扇数量是平台相关的信息，不需要通过访问内核获取。/sys_switch/fan/num路径会映射成只读权限的普通文件，文件内容为6

示例2
{“path” : “/sys_switch/syseeprom”,
 “type” : “path”,
 “value” : “/sys/class/i2c-adapter/i2c-2/2-0048/hwmon/hwmon1/eeprom”}
syseeprom信息需要通过i2c总线获取。/sys_switch/syseeprom路径会软链接到/sys/class/i2c-adapter/i2c-2/2-0048/hwmon/hwmon1/eeprom，这样社区驱动sysfs路径的复用

示例3
{“path” : “/sys_switch/psu/psu1/in_power”,
 “type” : “path”,
 “value” : “/sys/s3ip/psu/psu1/in_power”}
电源1功率信息需要通过i2c总线获取。 /sys_switch/psu/psu1/in_power 会软链接到/sys/s3ip/psu/psu1/in_power，这样可以实时获取电源功率信息

示例4
{“path” : “/sys_switch/fan/fan1”,
 “type” : “path”,
 “value” : “/sys/s3ip/fan/fan1”}
使用S3IP框架时，风扇1的全部信息，可以通过目录级别映射获取。 /sys_switch/fan/fan1目录会软链接到/sys/s3ip/fan/fan1目录，减少配置文件的长度


### 3.3 Port guide
1、git clone S3IP Sysfs代码
  git clone https://gitlab.com/s3ip1/sysfs.git 
2、编译验证代码可用性
  //编译生成编译主机可用deb包
  dpkg-buildpackage -rfakeroot -b -us -uc
  //安装该deb包
  dpkg -i s3ip-sysfs_1.0.0_amd64.deb
  //查看/sys_switch目录
  tree  -psv /sys_switch/

3、编译集成
    a、sysfs的配置文件（每款设备一个），用来控制/sys_switch目录映射
        开源代码中示例s3ip/scripts/s3ip_sysfs_conf.json，移植源码目录中，根据实际设备情况修改后，要求该文件最终安装到/etc/s3ip/s3ip_sysfs_conf.json
    b、厂商驱动完成特定平台sysfs的实现
         厂商根据实际驱动情况，实现sysfs驱动(ko)
    c、将s3ip-sysfs服务安装的系统中
       开源代码中示例s3ip/scripts/ s3ip-sysfs.service ，移植源码目录中，要求该文件最终安装到/etc/systemd/system/s3ip-sysfs.service；
       【可选】修改s3ip-sysfs服务，完成内核模块的安装和卸载安装platform deb包时，需要在安装后，使能s3ip-sysfs服务，并设置开机启动
       卸载platform deb包时，需要在卸载后，禁用s3ip-sysfs服务，并取消开机启动
4、集成后自测（确保符合S3IP Sysfs标准，并且保证获取数据的正确性）。
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
需要添加新的测试用例
1、确认sysfs节点的读写属性是否符合预期
2、sysfs节点的值是否符合预期

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.