
# Steps to Bring-Up SONiC-VS

## Build Steps for `sonic-buildimage`

```bash
sudo gpasswd -a ${USER} docker

# Clone your forked repo for sonic-buildimage:
git clone --recurse-submodules https://github.com/sonic-net/sonic-buildimage

# Ensure the 'overlay' module is loaded on your development system
sudo modprobe overlay

# Enter the source directory
cd sonic-buildimage

make init

NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 SONIC_BUILD_JOBS=12 make configure PLATFORM=vs

NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 SONIC_BUILD_JOBS=12 make target/sonic-vs.img.gz
```

## Pre-requisites: Install and Configure KVM

- Check if virtualization is enabled:

```bash
kvm-ok  # If command not found, install the required packages
```

- Install KVM, libvirt, and bridge utils:

```bash
sudo apt install -y qemu-kvm virt-manager libvirt-daemon-system virtinst libvirt-clients bridge-utils
sudo systemctl enable --now libvirtd
sudo systemctl start libvirtd
```

- Confirm that the virtualization daemon is running:

```bash
sudo systemctl status libvirtd
```

- Add the current user to the KVM and libvirt groups:

```bash
sudo usermod -aG kvm $USER
sudo usermod -aG libvirt $USER
# Log out and log back in
```

- Fix potential libvirt socket issues:

```bash
sudo systemctl stop libvirtd
sudo setfacl -m user:$USER:rw /var/run/libvirt/libvirt-sock
sudo systemctl enable libvirtd
sudo systemctl start libvirtd
```

- Install `ebtables`:

```bash
sudo apt install -y ebtables
```

## Prepare the Host

- Add a bridge:

```bash
brctl addbr mgtbr0
sudo ifconfig mgtbr0 up
```

- Add another bridge:

```bash
sudo brctl addbr vmbr0
sudo ifconfig vmbr0 up
```

## Copy SONiC-VS Images and Config File

- Download sample config file:  
[sonic1-vs.xml](https://github.com/sonic-net/SONiC/tree/master/doc/test/sonic1-vs.xml)

```bash
sudo cp sonic1-vs.xml /var/lib/libvirt/images
```

- Create a new `hdd` folder and copy the image:

```bash
sudo mkdir /var/lib/libvirt/images/hdd
sudo cp sonic-vs.img.gz /var/lib/libvirt/images/hdd
sudo gunzip /var/lib/libvirt/images/hdd/sonic-vs.img.gz
```

## Start the VM

- Create a new instance:

```bash
sudo virsh create sonic1-vs.xml
```

- List all VMs:

```bash
sudo virsh list --all
```

- Shutdown the instance:

```bash
sudo virsh shutdown --domain sonic1-vs
```

- Access the VM via:

```bash
telnet localhost 7000
# User: admin
# Passwd: YourPaSsWoRd
```
