This information details the steps to install SONiC and apply a basic configuration.

# Prerequisites
- [ONIE](http://www.opencompute.org/wiki/Networking/ONIE)-compliant switch (for this guide, we'll be using a Dell S6000-ON)
- DHCP server (reachable by the target device)
- HTTP server (to host the install image)

## Example Environment Topology
```
+----------+       +-----------+
|          |       |           |
|   Web    |       |           |
|  Server  +-------+           |
|   .10    |       |           |
+----------+       |           |
                   |           |
+----------+       |           |
|          |       |           |
|   DHCP   |       |    L2     |
|  Server  +-------+  Network  |
|   .254   |       |           |
+----------+       |           |
                   |           |
+----------+       |           |
|          |       |           |
|   SONiC  |       |           |
|  Switch  +-------+           |
|   .128   |       |           |
+----------+       +-----------+


Subnet: 192.168.0.1/24
DHCP Range: 192.168.0.128 - 253
Web: 192.168.0.10
DHCP: 192.168.0.254
Switch: 192.168.0.128

```

## Installation

### Preparing the Image
Build instructions for SONiC can be found at under the [build image project](https://github.com/Azure/sonic-buildimage).

Once the image has been created, host the image via HTTP.

### ONIE Boot
_The remainder of this guide will assume that your switch is able to boot into [ONIE](http://www.opencompute.org/wiki/Networking/ONIE)._

Configure the DHCP server option url to point to the SONiC image. As an example with `dnsmasq` and in the respective `.conf`:
```
# Note MAC specific to the mgmt port and apply a static lease.
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.0.128,set:onie

# Specify Option 114 and point to the image URL.
dhcp-option=tag:onie,114,"http://HTTPSERVER/path/to/binary/sonic.bin"
```

With DHCP configured, power cycling the switch should initiate the process of:

- DHCP lease acquisition
- Image download
- Image installation

For more information regarding booting with ONIE visit the [project wiki](https://github.com/opencomputeproject/onie/wiki/Quick-Start-Guide).

### Machine Configuration

There's a fair amount of post-install configuration ahead and we've gone ahead and published a project to help you along:

[Azure / sonic-mgmt](https://github.com/Azure/sonic-mgmt)
> Tools for managing, configuring and monitoring SONiC

In short, this does the work of:

- Host configuration
- Daemon installs & configuration
- Template composition for common services
- System startup

## System Reference
- [Command Reference](command_reference.md)
- [Troubleshooting Connectivity](troubleshooting_conn.md)


## External Links
- [ONIE](http://www.opencompute.org/wiki/Networking/ONIE)
- [dnsmasq](http://www.thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html)
- [Ansible](http://docs.ansible.com/)
