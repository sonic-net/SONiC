# Unsolicited announcement for router discovery HLD

## Table of contents

-   [Revision](#)
-   [Scope](#scope)
-   [Definitions/Abbreviations](#_Definitions/Abbreviations)
-   [Overview](#overview)
-   [Requirements](#requirements)
-   [Architecture design](#architecture-design)
-   [High level design](#high-level-design)
-   [SAI API](#configuration-and-management)
-   [Configuration and management](#_Configuration_and_management)
-   [Manifest - if the feature is an Application Extension](#_Manifest_(if_the)
-   [CLI/YANG model Enhancements](#cliyang-model-enhancements)
-   [Config DB Enhancements](#config-db-enhancements)
-   [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
-   [Memory Consumption](#memory-consumption)
-   [Restrictions/Limitations](#restrictionslimitations)
-   [Testing Requirements/Design](#testing-requirementsdesign)
    -   [Unit Test cases](#_Unit_Test_cases)
    -   [System Test cases](#_System_Test_cases)
-   [Open/Action items - if any](#openaction-items---if-any)

### 

### 

### 

### 

### Revision

| **Rev** | **Date** | **Author**         | **Change Description** |
|---------|----------|--------------------|------------------------|
| 1.0     | 22.8.24  | Lahav Friedlaender | Base version           |

### 

### Scope

In setups with statically configured static IP addresses, replacing a defected switch causes a stale connection to the new device. This is due to outdated neighbor entries in the setup’s router.

Since the router doesn’t have the updated MAC address, and the new device does not announce it’s MAC address, connection through the subnet doesn’t work until the entry ages.

This is also known as “silent hosts” problem commonly found in L2 ethernet networks.

To fix this issue, a switch can announce their MAC and IP addresses upon mgmt-interfaces linkup events.

### Definitions/Abbreviations

| Definitions/Abbreviation    | Description                                                                                                            |
|-----------------------------|------------------------------------------------------------------------------------------------------------------------|
| GARP                        | ARP message sent without request. Mainly used to notify other hosts in the network of a MAC address assignment change. |
| NA – neighbor advertisement | The IPv6 alternative to the ARP Reply in IPv4.                                                                         |
| Unsolicited NA              | NA message sent without request, similar to GARP.                                                                      |
| Linkup event                | An event that occurs while an interface is configured                                                                  |

### 

### Overview

### This feature extends on the networking capabilities of SONiC -

While static IP address is configured, any linkup event for mgmt interface will trigger IP address advertisement. For IPv4 it will be done by a GARP package, and for IPv6 it will be unsolicited NA.

### Requirements

### Module requirements are:

### 1. When static IP addresses are configured on any mgmt-interface, send unsolicited advertisement on any linkup event of mgmt. interfaces. This includes system boot events, physical cable reconnection and the following mgmt-interface configurations:

### state, mtu, autoconf, dhcp client state, speed, duplex, autoneg, vrf and updating static IP and gateway addresses.

### Also disabling hostname causes reset of networking in order to get a new hostname from DHCP. Meaning that unsetting hostname will also cause a package to be sent.

### 2. The feature will be enabled by default.

### 3. Do not send any packages when no static IP address is configured.

### 4. Do not send any packages when the feature is disabled.

### 5. Log errors when packages aren’t being sent.

### Architecture Design

Modified modules are:  
a. SONiC main module:  
 1. Interfaces configuration.  
 2. New script to send the expected messages.  
 3. New daemon ‘ifplugd’ – to monitor cable reconnection events.  
 4. New packages:  
 - libndp0: a required package for libndp-tools. The package version must be 1.8 or higher.  
 - libndp-tools: A package used to send unsolicited NA messages (IPv6). The package version must be 1.8 or higher.  
 - Ifplugd – A linux daemon that triggers events when a cable is physically reconnected.  
B. Sonic-utilities:  
 1. Configure feature state (enabled/disabled) and show feature state.

### High-Level Design

![A diagram of a diagram Description automatically generated](media/be62bbc277d418e77580c39bf6bb5a0c.png)

Linux triggers a ‘ifup’ event after interfaces configuration/during init flow. Using ‘ip’ commands in ‘etc/network/interfaces’, the host can call to ‘mgmt-unsolicited’ script only when a static IP address is configured. This is done using the following commad:  
‘’post-up mgmt-unsolicited.sh \<ipv4/ipv6\> \<interface-name\> \<static-IP-address\>”

The script verifies that the mgmt interfaces are up, and sends an unsolicited package if the feature is enabled.

Note that the feature configuration can cause the functionality to be disabled. The feature state is saved at ‘DEVICE_METADATA\|localhost’ table in “CONFIG_DB”.

The feature writes to syslog when sending an unsolicited message, or when a package is dropped.

### Configuration and management

This feature will support state configuration via CLI/RestAPI. The feature state can also be shown using CLI/RestAPI.

### CLI/YANG model Enhancements

The following commands are added to CLI:

-   ‘show mgmt-unsolicited’ – view the feature state:
-   ‘config mgmt-unsolicited \<enabled/disabled\>’ – confgiure the feature state. By default will be enabled.
-   Following field is added to the sonic-feature.yang file:

### Config DB Enhancements

As stated before, the feature state is saved at ‘DEVICE_METADATA\|localhost’ table in “CONFIG_DB”, under the field name: ‘mgmt_unsolicited_state’.

### Warmboot and Fastboot Design Impact

N/A.

### Memory Consumption

Memory consumption for the feature is constant, as the only addition to memory are the new packages, and the single process of ‘ifplugd’.  
Note that ‘ifplugd’ is a relatively low memory and CPU usage daemon – uses less than 0.1 precent of CPU and memory. This is due to its simple function and event trigger behavior.

### Restrictions/Limitations

N/A.

### Testing Requirements/Design

#### **White-Box Testing**

#### A. Feature enabled

#### 1. Feature is enabled

#### 2. change the ip address

#### 3. Check using tcpdump that the packet is sent from mgmt0 interface

#### 4. Once check manual form IT switch that it received the packet

#### 5. Logs – check log on sending the packet

#### B. Feature disabled

#### 1. Feature is disable, change the ip address

#### 2. Check using tcpdump that the packet is no GARP/NDP sent from mgmt0 interface

#### 

#### **Black-Box Testing**

#### A. Plug/unplug cable

#### 1. Plug out then plug in (check for packet)

#### 2. After linkup make sure we send the packet

#### B. Stress testing

#### 1. Configure static IP address for one of the mgmt interfaces.

#### 2. Configure multiple times different interface configuration that aren’t related to static IP address.

#### 3. Verify that packets are being sent according.

#### **Debug generate dump**

#### Tests should be added to verify logs during repeated mgmt-interfaces configuration.

#### **Init testing**

#### Tests should be added for sent packages during init flows, such as – init, reboot, reset factory and upgrade.

### Open/Action items - if any

N/A
