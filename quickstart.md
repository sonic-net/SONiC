# SONiC - Getting Started

## Description
This guide details the steps to install SONiC image on your switch. 

## Download Image

We have one SONiC Image per ASIC vendor. You can download SONiC Image from [here](https://github.com/Azure/SONiC/wiki/Supported-Devices-and-Platforms)

You can also build SONiC from source and the instructions can be found [here](https://github.com/Azure/sonic-buildimage).

## Installation

### Install SONiC ONIE Image


- Connect to switch via serial console.

- (Optional) Some switches may come with a NOS and you need to uninstall existing NOS first before you install SONiC. Boot into ONIE and select Uninstall OS.

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


- Reboot the into ONIE and select Install OS.

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

- Install SONiC. Here, we assume you have uploaded SONiC image onto a http server. Once you are in ONIE, you can first configure a management IP and default gateway for your switch, and then install the SONiC image from the http server. 

```
    ONIE:/ # ifconfig eth0 192.168.0.2 netmask 255.255.255.0
    ONIE:/ # ip route add default via 192.168.0.1
    ONIE:/ # onie-nos-install http://192.168.2.10/sonic-broadcom.bin
```

    **Note:** There are many options to install SONiC ONIE image on a ONIE-enabled switch. 
    For more installation options, visit the [ONIE](https://github.com/opencomputeproject/onie/wiki/Quick-Start-Guide).

When NOS installation finishes, the box will reboot into SONiC by default.

```
                         GNU GRUB  version 2.02~beta2+e4a1fe391

     +----------------------------------------------------------------------------+
     |*SONiC-OS-7069cef                                                           | 
     | ONIE                                                                       | 
     +----------------------------------------------------------------------------+
 ```

SONiC Login prompt. You can use user:```admin``` and password```YourPaSsWoRd``` to login for the first time.

 ```
    Debian GNU/Linux 8 sonic ttyS0

    sonic login: 
 ```

  **Note**: By default, SONiC console baud rate is 9600 and you might need to change the baud rate in case you cannot see anything from the console after reboot.

SONiC Welcome motd

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

### Install SONiC EOS Image

    This section is only applicable when you plan to install SONiC image on Arista switches.

Installing SONiC EOS uses the same step as you upgrade a normal EOS image. You download SONiC EOS image in an Arista box, select to boot from the image, and reload the box. 

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

## Configuration

SONiC is using device minigraph to configure the box. The minigraph file is at ```/etc/sonic/minigraph.xml```. SONiC generate the actually configuration for each docker based on this file. 

Device mini graph contains all the information about a given device in particularly it has all the information need to generate the device configuration as well as other data plan and control plane related information. At high level, the device minigraph contains following information. Here is the detailed description of [minigraph](minigraph.md).

-	Device information
  - Type/Role
  - SKU
  - Loopback address (IPV4 and IPV6)
  - Management address (IPV4 and IPV6)
-	Device Metadata 
  - Syslog servers
  - DHCP relay servers
  - NTP servers
-	Device Links
  - All the links start and end at the device.
  - Link Metadata 
     - Metadata associated with all the links (name value pairs).
-	DeviceDataPlaneInfo
  - Port channel
  - Vlan
  - ACL
  - IP addresses
-	BGP information 
  - BGP AS Number
  - Peers and Peering sessions 

## Command line and troubleshooting

SONiC uses Linux command line and you can use those commands to view platform, transceivers, L2, IP, BGP status, and etc. on.

- [Command Reference](command_reference.md)
- [Troubleshooting Connectivity](troubleshooting_conn.md)

