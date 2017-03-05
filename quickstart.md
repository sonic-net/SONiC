# SONiC - Getting Started

## Description
This guide details the steps to install SONiC image on your switch. 

## Download Image

We have one SONiC Image per ASIC vendor. You can download SONiC Image from [here](https://github.com/Azure/SONiC/wiki/Supported-Devices-and-Platforms)

You can also build SONiC from scratch and build instructions can be found [here](https://github.com/Azure/sonic-buildimage).

## Installation

### Install SONiC ONIE Image


- Connect to switch via serial console

- Reboot the into ONIE and select Install OS.

```
                         GNU GRUB  version 2.02~beta2+e4a1fe391
     +----------------------------------------------------------------------------+
     |*ONIE: Install OS                                                           | 
     | ONIE: Rescue                                                               |
     | ONIE: Uninstall OS                                                         |
     | ONIE: Update ONIE                                                          |
     | ONIE: Embed ONIE                                                           |
     +----------------------------------------------------------------------------+

          Use the ^ and v keys to select which entry is highlighted.          
          Press enter to boot the selected OS, `e' to edit the commands       
          before booting or `c' for a command-line.                           
```

- Install SONiC. 

    **Note** There are many options to install SONiC ONIE image on a ONIE-enabled switch. 
    For more installation options, visit the [project wiki](https://github.com/opencomputeproject/onie/wiki/Quick-Start-Guide).

Here, we assume you have uploaded SONiC image onto a http server. Once you are in ONIE, you can first configure a management IP and default gateway for your switch, and then install the SONiC image from the http server.

```
    ONIE:/ # ifconfig eth0 192.168.0.2 netmask 255.255.255.0
    ONIE:/ # ip route add default via 192.168.0.1
    ONIE:/ # onie-nos-install http://192.168.2.10/sonic-broadcom.bin
```

When installation finishes, it will reboot the box and then boot into SONiC by default.

```
                         GNU GRUB  version 2.02~beta2+e4a1fe391

     +----------------------------------------------------------------------------+
     |*SONiC-OS-7069cef                                                           | 
     | ONIE                                                                       | 
     +----------------------------------------------------------------------------+
 ```

SONiC Login prompt
 ```
    Debian GNU/Linux 8 sonic ttyS0

    sonic login: 
 ```

  **Note**: By default, SONiC console baud rate is 9600. You can use ```admin``` and ```YourPaSsWoRd``` to login.

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

_This section is only applicable when you plan to install SONiC image on Arista switches_


## Configuration

SONiC is using ```/etc/sonic/minigraph.xml``` to configure the box. 

Describe minigraph high level structure here.

## Command line and troubleshooting

SONiC uses Linux command line and you can use those commands to view platform, transceivers, L2, IP, BGP status, and etc. on.

- [Command Reference](command_reference.md)
- [Troubleshooting Connectivity](troubleshooting_conn.md)

