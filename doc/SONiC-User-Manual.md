# SONiC USER MANUAL

Table of Contents
=================
   * [SONiC USER MANUAL](#sonic-user-manual)
   * [Table of Contents](#table-of-contents)
   * [Introduction](#introduction)
   * [1 Quick Start Guide](#1-quick-start-guide)
      * [1.1 Download Image](#11-download-image)
         * [1.1.1 Installation using a USB Thumb Drive](#111-installation-using-a-usb-thumb-drive)
         * [1.1.2 Installation Over The Network](#112-installation-over-the-network)
            * [1.1.2.1 Install SONiC ONIE Image](#1121-install-sonic-onie-image)
            * [1.1.2.2 Install SONiC EOS Image](#1122-install-sonic-eos-image)
   * [2 Login Username &amp; Password](#2-login-username--password)
      * [2.1 Default Login](#21-default-login)
      * [2.2 Configuring Username &amp; Password](#22-configuring-username--password)
      * [2.3 How to reset Password ](#23-how-to-reset-password)      
   * [3 Basic Configuration &amp; Show](#3-basic-configuration--show)
      * [3.1 Configuring Management Interface and Loopback Interface](#31-configuring-management-interface-and-loopback-interface)
      * [3.2 Software version &amp; Upgrade](#32-software-version--upgrade)
         * [3.2.1 Show Versions](#321-show-versions)
      * [3.2.2 Check features available in this version](#322-check-features-available-in-this-version)
      * [3.2.3 Upgrade Or Downgrade Version](#323-upgrade-or-downgrade-version)
         * [3.2.3.1 SONiC Installer](#3231-sonic-installer)
      * [3.3 Startup Configuration](#33-startup-configuration)
         * [3.3.1 Default Startup Configuration](#331-default-startup-configuration)
         * [3.3.2 Modify Configuration](#332-modify-configuration)
            * [3.3.2.1 Modify config_db.json](#3321-modify-config_dbjson)
            * [3.3.2.2 Modify minigraph.xml](#3322-modify-minigraphxml)
   * [4 Detailed Configuration &amp; Show](#4-detailed-configuration--show)
      * [4.2 Links to Different Configuration Sections](#42-links-to-different-configuration-sections)
   * [5 Example Configuration](#5-example-configuration)
   * [6 Troubleshooting](#6-troubleshooting)
      * [6.1 Basic Troubleshooting Commands](#61-basic-troubleshooting-commands)
      * [6.2 Port up/down Troubleshooting](#62-port-updown-troubleshooting)
      * [6.3 Investigating Packet Drops](#63-investigating-packet-drops)
      * [6.4 Physical Link Signal](#64-physical-link-signal)
      * [6.5 Isolate SONiC Device from the Network](#65-isolate-sonic-device-from-the-network)


 

# Introduction
SONiC is an open source network operating system based on Linux that runs on switches from multiple vendors and ASICs. SONiC offers a full-suite of network functionality, like BGP and RDMA, that has been production-hardened in the data centers of some of the largest cloud-service providers. It offers teams the flexibility to create the network solutions they need while leveraging the collective strength of a large ecosystem and community.

SONiC software shall be loaded in these [supported devices](https://github.com/sonic-net/SONiC/blob/sonic_image_md_update/supported_devices_platforms.md) and this User guide explains the basic steps for using the SONiC in those platforms.

Connect the console port of the device and use the 9600 baud rate to access the device. Follow the [Quick Start Guide](https://github.com/sonic-net/SONiC/wiki/Quick-Start) to boot the device in ONIE mode and install the SONiC software using the steps specified in the document and reboot the device. In some devices that are pre-loaded with SONiC software, this step can be skipped. 
Users shall use the default username/password "admin/YourPaSsWoRd" to login to the device through the console port.

After logging into the device, SONiC software can be configured in following three methods.
 1) [Command Line Interface](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md)
 2) [config_db.json](https://github.com/sonic-net/SONiC/wiki/Configuration) 
 3) [minigraph.xml](https://github.com/sonic-net/SONiC/wiki/Configuration-with-Minigraph-(~Sep-2017))
 
Users can use all of the above methods or choose either one method to configure and to view the status of the device.
This user manual explains the common commands & related configuration/show examples on how to use the SONiC device. Refer the above documents for more detailed information.


**Scope Of The Document**  
Information in this manual is based on the SONiC software version 201811 (build#32).

This manual provides some insights on the following.
1) First section explains how to load the SONiC image on the supported platforms
2) Next section explains how to login using default username & password, how to change password, how to configure management interface & loopback address configuration.
3) Next section how to check the software version running on the device, how to check the list of features available in this software version, how to upgrade to new software version, etc.,
4) Next section explains how to check the default startup configuration with which the device is currently running, how to load a new configuration to this device, etc., 
5) Next section explains how to check the interface/link/port status, basic cable connectivity status, port speed, etc.,
6) Next section provides the required web links to the corresponding documents (and sections) that explains the steps to configure "Interface","BGP", "ACL","COPP", "Mirroring", etc.,
7) Next section gives an example configuration for T0 topology
8) Next section gives basic information about troubleshooting and it provides the link to the detailed troubleshooting guide. 

Note that some parts of this document might be a repetition of few commands/paragraphs from other configuration documents (like "Command Reference", "Config DB Manual", "Troubleshooting Guide", etc.,). Refer those documents for detailed information.


# 1 Quick Start Guide 
This guide details the steps to install a SONiC image on your supported switch. 

## 1.1 Download Image

We have one SONiC Image per ASIC vendor. You can download SONiC Image [here](https://github.com/sonic-net/SONiC/wiki/Supported-Devices-and-Platforms)

You can also build SONiC from source and the instructions can be found [here](https://github.com/sonic-net/sonic-buildimage).

Once the image is available in your local machine, the image can be installed either by installing using a USB thumb drive or over the network as given in following sub-sections.
In case if the device is already preloaded with SONiC image, the device can be booted without the installation process.

### 1.1.1 Installation using a USB Thumb Drive
This sub-section explains how to transfer the image from an USB thumb drive into the device and install it.
Copy the downloaded SONiC image on the USB thumb drive. 
Remove the USB drive from your machine and insert it into the USB port on the front (or rear) panel of your ONIE enabled device. 
Power on the device and ONIE will discover the onie-installer file on the root of the USB drive and execute it.
TBD1: The above method need to be reviewed and corrected. The above information is taken from https://opencomputeproject.github.io/onie/user-guide/index.html

### 1.1.2 Installation Over The Network
This sub-section explains how to transfer the image from remote server into the device and install it.

#### 1.1.2.1 Install SONiC ONIE Image

1. Connect to switch via serial console.
  
  **Note**: By default, the SONiC console baud rate is 9600. You may need to change the baud rate in case you cannot see anything from the console after reboot.

1. (Optional) Some switches may come with a NOS which will require you to uninstall the existing NOS first before you install SONiC. To do so, simply boot into ONIE and select `Uninstall OS`:

    ```
                         GNU GRUB  version 2.02~beta2+e4a1fe391
     +----------------------------------------------------------------------------+
     |*ONIE: Install OS                                                           | 
     | ONIE: Rescue                                                               |
     | ONIE: Uninstall OS  <----- Select this one                                 |
     | ONIE: Update ONIE                                                          |
     | ONIE: Embed ONIE                                                           |
     +----------------------------------------------------------------------------+

          Use the ^ and v keys to select which entry is highlighted.          
          Press enter to boot the selected OS, `e' to edit the commands       
          before booting or `c' for a command-line.                           
    ```


1. Reboot the switch into ONIE and select `Install OS`:

    ```
                         GNU GRUB  version 2.02~beta2+e4a1fe391
     +----------------------------------------------------------------------------+
     |*ONIE: Install OS    <----- Select this one                                 | 
     | ONIE: Rescue                                                               |
     | ONIE: Uninstall OS                                                         |
     | ONIE: Update ONIE                                                          |
     | ONIE: Embed ONIE                                                           |
     +----------------------------------------------------------------------------+

          Use the ^ and v keys to select which entry is highlighted.          
          Press enter to boot the selected OS, `e' to edit the commands       
          before booting or `c' for a command-line.                           
    ```

1. Install SONiC. Here, we assume you have uploaded SONiC image onto a http server (`192.168.2.10`). Once you are in ONIE, you can first configure a management IP (`192.168.0.2/24`)and default gateway (`192.168.0.1`) for your switch, and then install the SONiC image from the http server. 

    ```
    ONIE:/ # ifconfig eth0 192.168.0.2 netmask 255.255.255.0
    ONIE:/ # ip route add default via 192.168.0.1
    ONIE:/ # onie-nos-install http://192.168.2.10/sonic-broadcom.bin
    ```

  **Note:** There are many options to install SONiC ONIE image on a ONIE-enabled switch. For more installation options, visit the [ONIE Quick Start Guide](https://github.com/opencomputeproject/onie/wiki/Quick-Start-Guide).

When NOS installation finishes, the box will reboot into SONiC by default.

```
                    GNU GRUB  version 2.02~beta2+e4a1fe391

+----------------------------------------------------------------------------+
|*SONiC-OS-7069cef                                                           | 
| ONIE                                                                       | 
+----------------------------------------------------------------------------+
```


#### 1.1.2.2 Install SONiC EOS Image

- **This section is only applicable if you plan to install a SONiC image on Arista switches.**

Installing SONiC EOS uses the same steps you would use to upgrade a normal EOS image. You simply download a SONiC EOS image to an Arista box, select to boot from the image and reload the box. 

```
localhost#copy http://192.168.2.10/sonic-aboot-broadcom.swi flash: 
Copy completed successfully.                                                    
localhost(config)#boot system flash:sonic-aboot-broadcom.swi  
localhost(config)#reload 
System configuration has been modified. Save? [yes/no/cancel/diff]:no 
Proceed with reload? [confirm] [type enter] 
 
Broadcast message from root@localhost 
        (unknown) at 8:22 ... 

..... (boot messages)

 
Debian GNU/Linux 8 sonic ttyS0 
 
sonic login:
```

# 2 Login Username & Password
This section explains the default username & password and how to change the password

## 2.1 Default Login

All SONiC devices support both the serial console based login and the SSH based login by default.
The default credential (if not modified at image build time) for login is admin/YourPaSsWoRd.
In case of SSH login, users can login to the management interface (eth0) IP address after configuring the same using serial console. 
Refer the next section for configuring the IP address for management interface.

  - Example:
  ```
  At Console:
  Debian GNU/Linux 9 sonic ttyS1

  sonic login: admin
  Password: YourPaSsWoRd

  SSH from any remote server to sonic can be done by connecting to SONiC IP
  user@debug:~$ ssh admin@sonic_ip_address(or SONIC DNS Name)
  admin@sonic's password:
  ```

By default, login takes the user to the default prompt from which all the show commands can be executed.  

On successful login, SONiC Welcome Message of the Day shall be printed as follows.

```
You are on
  ____   ___  _   _ _  ____
 / ___| / _ \| \ | (_)/ ___|
 \___ \| | | |  \| | | |
  ___) | |_| | |\  | | |___
 |____/ \___/|_| \_|_|\____|

-- Software for Open Networking In the Cloud --

Unauthorized access and/or use are prohibited.
All access and/or use are subject to monitoring.

admin@sonic:~$ 
```

Go Back To [Beginning of the document](#SONiC-COMMAND-LINE-INTERFACE-GUIDE) or [Beginning of this section](#Basic-Configuration-And-Show)

## 2.2 Configuring Username & Password  

There is no separate CLI for adding users and for changing passwords. 
Users shall use the linux commands "useradd" command to add new users.
Users shall use the linux command "passwd <username>" to change the password for the specific username.
	
## 2.3 How to reset Password  

This TSG gives the instruction of how to reset a SONiC switch password.

1. Edit Grub boot menu options
1.1 First you need to get into grub menu options. This menu is displayed right at the beginning of the boot.  You should get something similar to this, but not the exactly the same. 
Choose the choice Start with SONiC-:
  ![image.png](https://github.com/sonic-net/SONiC/blob/master/images/PW-1.png)

1.2 Now we attempt to edit grub's boot option. Press "e" to edit the first grub menu option and navigate to kernel line:
 ![image.png](https://github.com/sonic-net/SONiC/blob/master/images/PW-2.png)

1.3 Remove quiet  and add  init=/bin/bash
 ![image.png](https://github.com/sonic-net/SONiC/blob/master/images/PW-3.png)

1.4 Press Ctrl-x to boot

2. Remount / and /proc
2.1 After successfully boot you will be presented with bash command prompt:
 ![image.png](https://github.com/sonic-net/SONiC/blob/master/images/PW-4.png)

```
mount -o remount,rw / 
mount -o remount,rw /proc
```

3 Reset password
3.1 To reset an actual password is now simple as typing :
`passwd admin`
 
  ![image.png](https://github.com/sonic-net/SONiC/blob/master/images/PW-5.png)
 
```
sync
sudo reboot -f
```





# 3 Basic Configuration & Show

SONiC is managing configuration in a single source of truth - a redisDB instance that we refer as ConfigDB. Applications subscribe to ConfigDB and generate their running configuration correspondingly.

Details about ConfigDB and schema design, please find it [here](https://github.com/sonic-net/SONiC/wiki/Configuration) 

Before Sep 2017, we were using an XML file named minigraph.xml to configure SONiC devices. For historical documentation, please refer to [Configuration with Minigraph](https://github.com/sonic-net/SONiC/wiki/Configuration-with-Minigraph-(~Sep-2017))
 
SONiC includes commands that allow user to show platform, transceivers, L2, IP, BGP status, etc.

- [Command Reference](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md)

Note that all the configuration commands need root privileges to execute them and the commands are case-sensitive.
Show commands can be executed by all users without the root privileges.
Root privileges can be obtained either by using "sudo" keyword in front of all config commands, or by going to root prompt using "sudo -i".


## 3.1 Configuring Management Interface and Loopback Interface

The management interface (eth0) in SONiC is configured (by default) to use DHCP client to get the IP address from the DHCP server. Connect the management interface to the same network in which your DHCP server is connected and get the IP address from DHCP server.
The IP address received from DHCP server can be verified using the "/sbin/ifconfig eth0" linux command.

SONiC does not provide a CLI to configure the static IP for the management interface. There are few alternate ways by which a static IP address can be configured for the management interface.  
   1) use "ifconfig eth0" linux command (example: ifconfig eth0 10.11.12.13/24). This configuration won't be preserved across reboot.
      - Example:
   ```
   admin@sonic:~$ /sbin/ifconfig eth0 10.11.12.13/24
   ```   
Note that SONiC does not support management VRF and hence it is not possible to differentiate data traffic and management traffic. Work is in progress to support the mgmtVRF in Aug2019 release. 

   2) use config_db.json and configure the MGMT_INTERFACE key with the appropriate values. Refer [here](https://github.com/sonic-net/SONiC/wiki/Configuration#Management-Interface) 
   
   
   Add the following example configuration in a file (ex: mgmt_ip.json) and load it as follows.
   ```
   "MGMT_INTERFACE": {
        "eth0|10.11.12.13/24": {
            "gwaddr": "10.11.12.1"
        }
   }
   ```
   NOTE: If the interface IP address and default gateway were already present, users should remove them before loading the above configuration.
   
   Users can use the "show runningconfiguration all" to check the already configured MGMT_INTERFACE. Or, users can use the "redis-cli" command as follows to check the same.
```
   root@T1-2:/etc/sonic# redis-cli -n 4 keys "MGMT_INTERFACE*"
	1) "MGMT_INTERFACE|eth0|10.20.30.40/24"
```   
   In the above redis-cli command example, it gets the keys starting with MGMT_INTERFACE and it displays the already configured MGMT_INTERFACE in the CONFIG_DB.
   To remove this key from CONFIG_DB, users shall use the following redis-cli command.
```   
   redis-cli -n 4 DEL "MGMT_INTERFACE|eth0|10.20.30.40/24"
```   
   After removing the key, users can load the new configuration using "config load mgmt_ip.json" command and then do "systemctl restart interfaces-config" to make it effective. Users shall verify the configured management interface IP address value using "ifconfig" linux command.
      
   
   3) use minigraph.xml and configure "ManagementIPInterfaces" tag inside "DpgDesc" tag as given at the [page](https://github.com/sonic-net/SONiC/wiki/Configuration-with-Minigraph-(~Sep-2017))
   
Once the IP address is configured, the same can be verified using "/sbin/ifconfig eth0" linux command.
Users can SSH login to this management interface IP address from their management network.

  - Example:
   ```
   admin@sonic:~$ /sbin/ifconfig eth0
   eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
         inet 10.11.11.13  netmask 255.255.255.0  broadcast 10.11.12.255
   ```
   
The same method shall be used to configure the loopback interface address as follows.
1) "/sbin/ifconfig lo" linux command shall be used, OR,
2) Add the key LOOPBACK_INTERFACE & value in config_db.json and load it, OR,
3) use minigraph.xml and configure LoopbackIPInterfaces tag inside the "DpgDesc" tag.

   
Go Back To [Beginning of the document](#SONiC-COMMAND-LINE-INTERFACE-GUIDE) or [Beginning of this section](#Basic-Configuration-And-Show)



## 3.2 Software version & Upgrade  
This section explains how to check the current version of the software running in the device, how to check the features available in the version and how to upgrade/downgrade to different versions.

### 3.2.1 Show Versions 
 
**show version**  
This command displays software component versions of the currently running SONiC image. This includes the SONiC image version as well as Docker image versions.
This command displays relevant information as the SONiC and Linux kernel version being utilized, as well as the commit-id used to build the SONiC image. The second section of the output displays the various docker images and their associated id’s. 

- Usage:  
  show version  

- Example:
  ```
  admin@sonic:~$ show version
  SONiC Software Version: SONiC.HEAD.32-21ea29a
  Distribution: Debian 9.8
  Kernel: 4.9.0-8-amd64
  Build commit: 21ea29a
  Build date: Fri Mar 22 01:55:48 UTC 2019
  Built by: johnar@jenkins-worker-4

  Docker images:
  REPOSITORY                 TAG                 IMAGE ID            SIZE
  docker-syncd-brcm          HEAD.32-21ea29a     434240daff6e        362MB
  docker-syncd-brcm          latest              434240daff6e        362MB
  docker-orchagent-brcm      HEAD.32-21ea29a     e4f9c4631025        287MB
  docker-orchagent-brcm      latest              e4f9c4631025        287MB
  docker-lldp-sv2            HEAD.32-21ea29a     9681bbfea3ac        275MB
  docker-lldp-sv2            latest              9681bbfea3ac        275MB
  docker-dhcp-relay          HEAD.32-21ea29a     2db34c7bc6f4        257MB
  docker-dhcp-relay          latest              2db34c7bc6f4        257MB
  docker-database            HEAD.32-21ea29a     badc6fc84cdb        256MB
  docker-database            latest              badc6fc84cdb        256MB
  docker-snmp-sv2            HEAD.32-21ea29a     e2776e2a30b7        295MB
  docker-snmp-sv2            latest              e2776e2a30b7        295MB
  docker-teamd               HEAD.32-21ea29a     caf957cd2ad1        275MB
  docker-teamd               latest              caf957cd2ad1        275MB
  docker-router-advertiser   HEAD.32-21ea29a     b1a62023958c        255MB
  docker-router-advertiser   latest              b1a62023958c        255MB
  docker-platform-monitor    HEAD.32-21ea29a     40b40a4b2164        287MB
  docker-platform-monitor    latest              40b40a4b2164        287MB
  docker-fpm-quagga          HEAD.32-21ea29a     546036fe6838        282MB
  docker-fpm-quagga          latest              546036fe6838        282MB

  ```
Go Back To [Beginning of the document](#SONiC-COMMAND-LINE-INTERFACE-GUIDE) or [Beginning of this section](#Basic-Configuration-And-Show)

## 3.2.2 Check features available in this version

[SONiC roadmap planning](https://github.com/sonic-net/SONiC/wiki/Sonic-Roadmap-Planning) explains the various features that are added in every software release.
TBD: Is this enough? Need information from Xin.


## 3.2.3 Upgrade Or Downgrade Version 

SONiC software can be installed in two methods, viz, using "ONIE Installer" or by using "sonic-installer tool".
"ONIE Installer" shall be used as explained in the [QuickStartGuide](#Quick-Start-Guide)
"sonic-installer" shall be used as given below.


### 3.2.3.1 SONiC Installer
This is a command line tool available as part of the SONiC software; If the device is already running the SONiC software, this tool can be used to install an alternate image in the partition.
This tool has facility to install an alternate image, list the available images and to set the next reboot image.
 
**sonic-installer install**  

This command is used to install a new image on the alternate image partition.  This command takes a path to an installable SONiC image or URL and installs the image.

  - Usage:    
    sonic-installer install <path>  


- Example:
  ```	 
  admin@sonic:~$ sonic-installer install https://sonic-jenkins.westus.cloudapp.azure.com/job/xxxx/job/buildimage-xxxx-all/xxx/artifact/target/sonic-xxxx.bin
  New image will be installed, continue? [y/N]: y
  Downloading image...
  ...100%, 480 MB, 3357 KB/s, 146 seconds passed
  Command: /tmp/sonic_image
  Verifying image checksum ... OK.
  Preparing image archive ... OK.
  ONIE Installer: platform: XXXX
  onie_platform: 
  Installing SONiC in SONiC
  Installing SONiC to /host/image-xxxx
  Directory /host/image-xxxx/ already exists. Cleaning up...
  Archive:  fs.zip
     creating: /host/image-xxxx/boot/
    inflating: /host/image-xxxx/boot/vmlinuz-3.16.0-4-amd64  
    inflating: /host/image-xxxx/boot/config-3.16.0-4-amd64  
    inflating: /host/image-xxxx/boot/System.map-3.16.0-4-amd64  
    inflating: /host/image-xxxx/boot/initrd.img-3.16.0-4-amd64  
     creating: /host/image-xxxx/platform/
   extracting: /host/image-xxxx/platform/firsttime  
    inflating: /host/image-xxxx/fs.squashfs  
    inflating: /host/image-xxxx/dockerfs.tar.gz  
  Log file system already exists. Size: 4096MB
  Installed SONiC base image SONiC-OS successfully

  Command: cp /etc/sonic/minigraph.xml /host/

  Command: grub-set-default --boot-directory=/host 0

  Done
  ```

**sonic-installer list**  

This command displays information about currently installed images. It displays a list of installed images, currently running image and image set to be loaded in next reboot.

  - Usage:  
    sonic-installer list

- Example:  
   ```
  admin@sonic:~$ sonic-installer list 
  Current: SONiC-OS-HEAD.XXXX
  Next: SONiC-OS-HEAD.XXXX
  Available: 
  SONiC-OS-HEAD.XXXX
  SONiC-OS-HEAD.YYYY
  ```

**sonic-installer set_default**  

This command is be used to change the image which can be loaded by default in all the subsequent reboots.

  - Usage:  
    sonic-installer set_default <image_name>

- Example:
  ```   
  admin@sonic:~$ sonic-installer set_default SONiC-OS-HEAD.XXXX
  ```

**sonic-installer set_next_boot**  

This command is used to change the image that can be loaded in the *next* reboot only. Note that it will fallback to current image in all other subsequent reboots after the next reboot.

  - Usage:  
    sonic-installer set_next_boot <image_name>

- Example:
  ```
  admin@sonic:~$ sonic-installer set_next_boot SONiC-OS-HEAD.XXXX
  ```

**sonic-installer remove**  

This command is used to remove the unused SONiC image from the disk. Note that it's *not* allowed to remove currently running image.

  - Usage:  
    sonic-installer remove <image_name>

- Example:
  ```
  admin@sonic:~$ sonic-installer remove SONiC-OS-HEAD.YYYY
  Image will be removed, continue? [y/N]: y
  Updating GRUB...
  Done
  Removing image root filesystem...
  Done
  Command: grub-set-default --boot-directory=/host 0

  Image removed
  ```
 
Go Back To [Beginning of the document](#SONiC-COMMAND-LINE-INTERFACE-GUIDE) or [Beginning of this section](#Software-Installation-Commands)



## 3.3 Startup Configuration

This section explains how to check the default startup configuration with which the device is currently running and how to load a new configuration to this device.

### 3.3.1 Default Startup Configuration 

Users shall use the "show runningconfiguration" command to check the current running configuration. 
If users had not done any configuration change after the reboot, this will be same as the default startup configuration.
SONiC device contains the startup configuration in the file /etc/sonic/config_db.json. During reboot, this configuration will be loaded by default. 
Following are some of the keys that are configured by default in the config_db.json.
1) DEVICE_METADATA
2) MAP_PFC_PRIORITY_TO_QUEUE
3) QUEUE
4) PORT
5) CRM
6) PORT_QOS_MAP
7) NTP_SERVER
8) BUFFER_QUEUE
9) WRED_PROFILE
10) TC_TO_PRIORITY_GROUP_MAP
11) BUFFER_PROFILE
12) DEVICE_NEIGHBOR
13) DSCP_TO_TC_MAP
14) TC_TO_QUEUE_MAP
15) CABLE_LENGTH
16) SCHEDULER
17) BUFFER_POOL


SONiC provides an alternate method for loading the startup configuration from minigraph.xml from a remote server when DHCP is used. SONiC contains a file /etc/sonic/updategraph.conf that contains a flag "enabled" which is set to "false" by default. Similarly, management interface is configured to use DHCP by default for getting the management interface IP address from the DHCP server. Users can modify this flag to "true" and then reboot the device. SONiC will use DHCP to get the management IP address as well as the details about the configuration file minigraph.xml (DHCP server should have been configured to provide the details like management interface IP address, default route, configuration file name and the server IP address from this the configuration file should be fetched). SONiC shall contact the remote server and get the minigraph.xml and loads the same.


### 3.3.2 Modify Configuration  

#### 3.3.2.1 Modify config_db.json  
Users can directly edit & modify the file /etc/sonic/config_db.json or do a SCP and copy this file from a remote server. 
User can either do "config reload" command to load this new configuration, or users can simply reboot to make it effective.


#### 3.3.2.2 Modify minigraph.xml  

Users can directly edit & modify the file /etc/sonic/mingraph.xml or do a SCP and copy this file from a remote server. 
User can either do "config load_minigraph" command to load this new configuration, or users can simply reboot to make it effective.
Or, users can modify the "enabled" flag in /etc/sonic/updategraph.conf to true and then reboot the device as explained above.


# 4 Detailed Configuration & Show  

Basic cable connectivity shall be verified by configuring the IP address for the ports and by using the "ping" test.

## 4.2 Links to Different Configuration Sections

| # | Module    |  CLI Link | ConfigDB Link |  Remarks |
| --- | --- | --- | --- | --- |
| 1 |  Interface |[Interface CLI](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md#Interface-Configuration-And-Show-Commands) | [Interface ConfigDB](Configuration.md)| To view the details about the interface |
| 2 |  BGP |[BGP CLI](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md#BGP-Configuration-And-Show-Commands) | [BGP ConfigDB](Configuration.md)| To view the details about the BGP |
| 3 |  ACL |[ACL CLI](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md#ACL-Configuration-And-Show) | [ACL ConfigDB](Configuration.md)| To view the details about the ACL |
| 4 |  COPP |COPP CLI Not Available | [COPP ConfigDB](Configuration.md)| To view the details about the COPP |
| 5 |  Mirroring |[Mirroring CLI](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md#mirroring-configuration-and-show) | [Mirroring ConfigDB](Configuration.md)| To view the details about the Mirroring |



# 5 Example Configuration

Refer the following links/files for the example configuration based on CLI, ConfigDB and Minigraph.

  1)  [Example CLI Configuration File](Example_CLI.md)
  2)  [Example T0 ConfigDB](T0_config_db.json)
  3)  [Example T0 Minigraph.xml](T0_minigraph.xml)


# 6 Troubleshooting

This section captures some of the frequenently used troubleshooting commands and methods.
Users can refer the [Troubleshooting Guide](Troubleshooting-Guide.md) for more details about troubleshooting.

## 6.1 Basic Troubleshooting Commands

Users shall use "show techsupport" to collect the information from the device, shall use syslog to view the syslogs printed by the services, shall use the linux utitlies like "ping", "tcpdump", etc., to check the connectivity and packet tracing.

**show techsupport**  
This command gathers pertinent information about the state of the device; information is as diverse as syslog entries, database state, routing-stack state, etc., It then compresses it into an archive file. This archive file can be sent to the SONiC development team for examination.
Resulting archive file is saved as `/var/dump/<DEVICE_HOST_NAME>_YYYYMMDD_HHMMSS.tar.gz`
Few details that the dump includes are given below: 
-	Interface details  
-	Platform  details
-	Machine.conf 
-	Vlan configs
-	Routes
-	Sensor , transceiver details 
-	Syslog
-	Ip configs 
-	Bgp details 
-	Device Configs  (json/ minigraph) 


  - Usage:  
    show techsupport


- Example:
  ```	
  admin@sonic:~$ show techsupport
  ```

**syslog**  
  
-	System logs and event messages  from all dockers are captured via rsyslog  and saved in /var/log/syslog 
-	Console logs can be viewed using "show logging" command also. This command prints the information in syslog in console .
-	Show logging -f  will tail the output of syslogs in  console/ssh session.

**tcpdump**  

-	tcpdump is a common packet analyzer that runs under the sonic command line . It allows the user to display TCP/IP and other packets being transmitted or received over a network
ex: tcpdump -i Ethernet0 

## 6.2 Port up/down Troubleshooting  

All port related configuration done using CLI/ConfigDB/Minigraph are saved in the redis config database. Such configuration is handled by the appropriate modules and the result of such operation might be stored in the application database (APP_DB).
Once if the modules complete their operation, if the result needs to be programmed into the ASIC, same will be synchronized by syncd service and the result is stored in the ASIC_DB.

When user need to debug/troubleshoot any issue, the best is to verify all of these databases as explained below.
1) Check the configuration in the CONFIG_DB and status using "show" commands.
2) Check the application status of the application in APP_DB.
3) Check the ASIC related programming state and the status in ASIC_DB.
4) Check the actual ASIC.

1) How to check the configuration & status of ports?

Following "show" commands can be used to check the port status.

-	Show interface status ( up/down)
-	Show interface transceiver  presence 

Following "redis-dump" command can be used to dump the port configuraiton from the ConfigDB.

Example : 
```
root@sonic-z9100-02:~# redis-dump -d 4 -k  "PORT|Ethernet4" -y
{
  "PORT|Ethernet4": {
    "type": "hash",
    "value": {
      "admin_status": "up",
      "alias": "fiftyGigE1/2/1",
      "description": "Servers1:eth0",
      "index": "2",
      "lanes": "53,54",
      "mtu": "9100",
      "pfc_asym": "off",
      "speed": "50000"
    }
  }
  
```

Following redis-dump can be used to check the port status in the APP_DB.

Example:
```
root@sonic-z9100-02:~# redis-dump -d 0 -k *PORT_TABLE:Ethernet62* -y
{
  "PORT_TABLE:Ethernet62": {
    "type": "hash",
    "value": {
      "admin_status": "down",
      "alias": "fiftyGigE1/16/2",
      "description": "fiftyGigE1/16/2",
      "index": "16",
      "lanes": "95,96",
      "mtu": "9100",
      "oper_status": "down",
      "pfc_asym": "off",
      "speed": "50000"
    }
  }
```

Following redis-dump can be used to check the port status in the ASIC_DB.

Example:
```
root@sonic-z9100-02:~# redis-dump -d 1 -k  "ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x1000000000014"  -y
{
  "ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x1000000000014": {
    "type": "hash",
    "value": {
      "NULL": "NULL",
      "SAI_PORT_ATTR_ADMIN_STATE": "true",
      "SAI_PORT_ATTR_INGRESS_ACL": "oid:0xb000000000a61",
      "SAI_PORT_ATTR_MTU": "9122",
      "SAI_PORT_ATTR_PORT_VLAN_ID": "1000",
      "SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL": "24",
      "SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP": "oid:0x14000000000a34",
      "SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP": "oid:0x14000000000a35",
      "SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP": "oid:0x14000000000a38",
      "SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP": "oid:0x14000000000a39",
      "SAI_PORT_ATTR_SPEED": "50000"
    }
  }
```
  
Following is an example for checking the port status for Broadcom ASICs.
From command line, enter "bcmsh" to enter into Broadcom shell. Users can use "Ctrcl c" to come out of Broadcom shell.
In the broadcom shell, users shall use "ps" command to check the port state.

Example:
```
BCM : bcmcmd “ps”
       port      ena/link  Lanes  Speed Duplex   LinkScan  AutoNeg?   STPstate    pause  discrd  LrnOps   Interface MaxFrame  CutThru?  Loopback
       xe0( 50)  down      2      50G   FD       SW        No         Forward            None    FA       KR2       9122      No
       xe1( 51)  down      2      50G   FD       SW        No         Forward            None    FA       KR2       9122      No
       xe2( 54)  up        2      50G   FD       SW        No         Forward            None    FA       KR2       9122      No

```

## ​6.3 Investigating Packet Drops 
Packet drops can be investigated by viewing counters using the `show interfaces counters` command.

- **RX_ERR/TX_ERR** includes all physical layer (layer-2) related drops, such as FCS error, RUNT frames. If there is RX_ERR or TX_ERR, it usually indicates some physical layer link issues.

- **RX_DRP** include all layer-2, layer-3, ACL related drops in the switch ingress pipeline, drops due to insufficient ingress buffer.

- **TX_DRP** include mainly the egress buffer related drop due to congestion, including WRED drop.

- **RX_OVR/TX_OVR** counts the oversized packets.

- Example:
  ```
  admin@sonic:~$ show interfaces counters
        Iface            RX_OK      RX_RATE    RX_UTIL    RX_ERR    RX_DRP    RX_OVR            TX_OK      TX_RATE    TX_UTIL    TX_ERR    TX_DRP    TX_OVR
  -----------  ---------------  -----------  ---------  --------  --------  --------  ---------------  -----------  ---------  --------  --------  --------
    Ethernet0  471,729,839,997  653.87 MB/s     12.77%         0    18,682         0  409,682,385,925  556.84 MB/s     10.88%         0         0         0
    Ethernet4  453,838,006,636  632.97 MB/s     12.36%         0     1,636         0  388,299,875,056  529.34 MB/s     10.34%         0         0         0
    Ethernet8  549,034,764,539  761.15 MB/s     14.87%         0    18,274         0  457,603,227,659  615.20 MB/s     12.02%         0         0         0
   Ethernet12  458,052,204,029  636.84 MB/s     12.44%         0    17,614         0  388,341,776,615  527.37 MB/s     10.30%         0         0         0
   Ethernet16   16,679,692,972   13.83 MB/s      0.27%         0    17,605         0   18,206,586,265   17.51 MB/s      0.34%         0         0         0
   Ethernet20   47,983,339,172   35.89 MB/s      0.70%         0     2,174         0   58,986,354,359   51.83 MB/s      1.01%         0         0         0
   Ethernet24   33,543,533,441   36.59 MB/s      0.71%         0     1,613         0   43,066,076,370   49.92 MB/s      0.97%         0         0         0
  ```

## 6.4 Physical Link Signa​​l 

Use the following command to get optical signal strength. Note: not all types of links have such channel monitor values. The AOC and DAC cables do not have such values.

Generally, optical power should be greater than -10dBm.

- Example:
  ```
  admin@sonic:~$ show interfaces transceiver eeprom Ethernet12 --dom
  Ethernet12: SFP detected
  
          Connector : Unknown
          EncodingCodes : Unspecified
          ExtIdentOfTypeOfTransceiver : GBIC def not specified
          LengthOM3(UnitsOf10m) : 144
          RateIdentifier : Unspecified
          ReceivedPowerMeasurementType : Avg power
          TransceiverCodes :
                  10GEthernetComplianceCode : 10G Base-SR
                  InfinibandComplianceCode : 1X Copper Passive
          TypeOfTransceiver : QSFP
          VendorDataCode(YYYY-MM-DD Lot) : 2013-11-29 
          VendorName : MOLEX
          VendorOUI : MOL
          VendorPN : 1064141400
          VendorRev : E th
          VendorSN : G13474P0120
          ChannelMonitorValues :
                  RX1Power : -5.7398dBm
                  RX2Power : -4.6055dBm
                  RX3Power : -5.0252dBm
                  RX4Power : -12.5414dBm
                  TX1Bias : 19.1600mA
                  TX2Bias : 19.1600mA
                  TX3Bias : 19.1600mA
                  TX4Bias : 19.1600mA
          ChannelStatus :
                  Rx1LOS : Off
                  Rx2LOS : Off
                  Rx3LOS : Off
                  Rx4LOS : Off
                  Tx1Fault : Off
                  Tx1LOS : Off
                  Tx2Fault : Off
                  Tx2LOS : Off
                  Tx3Fault : Off
                  Tx3LOS : Off
                  Tx4Fault : Off
                  Tx4LOS : Off
          ModuleMonitorValues :
                  Temperature : 23.7500C
                  Vcc : 3.2805Volts
          StatusIndicators :
                  DataNotReady : Off
  ```


## 6.5 Isolate SONiC Device from the Ne​twork 

When there is suspicion that a SONiC device is dropping traffic and behaving abnormally, you may want to isolate the device from the network. Before isolating the device, please generate SONiC tech-support first.

You can shut down BGP sessions to neighbors using a form of the `config bgp shutdown` command. There are a few variations of this command, examples follow.

- Shutdown BGP session with neighbor by neighbor's hostname:
- Example:
  ```
  admin@sonic:~$ sudo config bgp shutdown neighbor SONIC02SPINE
  ```

- Shutdown BGP session with neighbor by neighbor's IP address:
- Example:
  ```
  admin@sonic:~$ sudo config bgp shutdown neighbor 192.168.1.124
  ```

- Shutdown BGP sessions with all neighbors:
- Example:
  ```
  admin@sonic:~$ sudo config bgp shutdown all
  ```
