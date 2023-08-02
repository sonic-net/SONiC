# SONiC FIPS Deployment


Table of Contents
=================
* [Overview](#Overview)
* [Requirements](#Requirements)
* [Scopes](#Scopes)
* [SONiC Configuration for FIPS](#SONiC-Configuration-for-FIPS)
    * [FIPS None Enforce Mode](#FIPS-None-Enforce-Mode)
    * [FIPS Enforce Mode](#FIPS-Enforce-Mode)
* [SONiC FIPS State](#SONiC-FIPS-State)
* [SONiC reboot and upgarde](#SONiC-reboot-and-upgarde)
    * [SONiC warm-reboot or fast-reboot](#SONiC-warm-reboot-or-fast-reboot)
    * [SONiC upgrade](#SONiC-upgrade)
* [Test cases](#Test-cases)

## Revision

| Rev | Date     | Author          | Change Description |
|:---:|:--------:|:---------------:|--------------------|
| 0.1 | 06/24/23 | Xuhui Miao  | Initial version    |

## Overview
It is for the security requirement, the FIPS 140-3 feature should be enabled for the devices in the datacenters. This design document is to enable the FIPS for existing devices and new rollout devices, and to enable the FIPS config in the runtime in the SONiC config.

## Requirements
- Provide a way to enable/disable the FIPS in the runtime for control/management plane, such as sshd, telemetry, and restapi, without reboot data plane.
- Provide a way to enforce the FIPS for SONiC.

## Scopes
1. The FIPS 140-3 is only availabel on SONiC OS Version 11 or above.
2. FIPS is supported on branches: 202205, 202211, master.

## SONiC Configuration for FIPS
```json
{
    "FIPS": {
      "global": {
        "enable": "true",
        "enforce": "true"
      }
    }
}
```

| Key | Description |
|:----:|---------------------|
| enable | enable or not enable the FIPS, true is to enable, the default value is false  |
| enforce | enforce or not enforce the FIPS, true is to enforce, the default value is false |

If the enforce is true, then enable is ignored. If the enforce is not set, it supports to disable the FIPS in the runtime.

The enable setting is a transition mode for the scenario to change the devices from the FIPS none enforce mode to the enforce mode. It allows you to rollback the change without rebooting the devices if any issues in your datacenters.

### FIPS None Enforce Mode
It is supported to enable the [OpenSSL SymCrypt engine](https://github.com/microsoft/SymCrypt-OpenSSL) (see [design](https://github.com/sonic-net/SONiC/blob/master/doc/fips/SONiC-OpenSSL-FIPS-140-3.md)) in the runtime by using the FIPS flag file or Kernel options, (see [OpenSSL patch](https://github.com/sonic-net/sonic-fips/blob/main/src/openssl.patch/10-support-fips-mode.patch)).
To enable the FIPS feature in the runtime as below, but it is required to restart the relative services, such as sshd, docker container telemetry, docker container restapi, etc.
```
echo 1 > /etc/fips/fips_enabled
```
To disable the FIPS feature.
```
echo 0 > /etc/fips/fips_enabled
```

When using the flag file, it is required to mount the file to the docker container, or set the flag inside of the container then it will take effect. For the SONiC devices with the new images after the runtime configuration feature implemented, we will mount the file for all the containers. For the SONiC devices with the old images, we need to do the additional configuration, to set the flag file for each of the docker containers.

The sample script to enable FIPS for the devices with the old images:
```
mkdir -p /etc/fips
echo 1 > /etc/fips/fips_enabled
docker exec telemetry bash -c 'mkdir -p /etc/fips; echo 1 > /etc/fips/fips_enabled'
docker exec restapi bash -c 'mkdir -p /etc/fips; echo 1 > /etc/fips/fips_enabled'
docker restart telemetry restapi
systemctl restart sshd
```

The script will be automatically triggred when the DB FIPS config change detected by the [hostcfgd](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-host-services-data/debian/sonic-host-services-data.hostcfgd.service), so it does not need to run it manually again in the new images.

### FIPS enable Mode
It is required to reboot the SONiC device when changing the FIPS mode from the mode none-enforce to the enforce mode, or from the mode enforce to the mode none-enforce.
When installing the SONiC image at the first time, or upgrading the SONiC image, the default FIPS option is disabled by default (see [ENABLE_FIPS](https://github.com/sonic-net/sonic-buildimage/blob/6ba5b84d980983312f779ad65cfc8c90b9674707/rules/config#L292)). You can override the option in the build time to set ENABLE_FIPS=y, so it is not required for an additional reboot, after you install or upgrade the SONiC OS.

When you plan to enable the enforce mode for all datacenters, you can build the SONiC with FIPS enabled by default, and set the configuration enforce=true for all devices.

## SONiC FIPS State
The SONiC FIPS state in the redis STATE_DB as below:
| Key | Description |
|:----:|---------------------|
| enabled | The flag indicating whether the FIPS enabled, 1 enabled, others not enabled |
| enforced | The flag indicating whether the FIPS enforced, 1 enforced, others not enforced |

The redis dictionary key is FIPS_STAT\|state.

GitHub Pull Request for reference: https://github.com/sonic-net/sonic-host-services/pull/69

## SONiC reboot and upgarde
### SONiC warm-reboot or fast-reboot
SONiC ware-reboot/fast-reboot will initialize the kernel command line, it only has impact when the FIPS enforcement flag changed, either from enforce to none-enforce, or from none-enforce to enforce.

When the FIPS enforcement config changed, it is required to do the warm-reboot or fast-reboot to make the change take effect.

### SONiC upgrade
If upgrading the SONiC image from the SONiC OS with FIPS enforced, it will set the FIPS enforced mode for the next boot image automatically. If the FIPS enforced option not set, then the FIPS in the next image will depend on the default option in the new installation image. The default FIPS option in the installation image is None if the build option not changed.

The runtime FIPS option will set after running into the new image based on the configDB setting, it will not take any change during the process of the SONiC upgrade.

## Test cases

### Test case #1 – Test the FIPS enable mode

1. Setup the test environment to the FIPS None mode.
1. Change the ConfigDB setting to enable the FIPS.
1. Verify the required service restarted.
1. Verify the runtime config option changed to 1 in OpenSSL config file. 

### Test case #2 – Test the FIPS to disable

1. Setup the test environment to enable the FIPS.
1. Change the ConfigDB setting to disable the FIPS.
1. Verify the required service restarted.
1. Verify the runtime config option changed to 0 in OpenSSL config file. 

### Test case #3 – Test the FIPS enforce mode

1. Setup the test environment to the FIPS None mode.
1. Change the ConfigDB setting to enforce the FIPS.
1. Verify the required service restarted.
1. Verify the fips enforce command called.

### Test case #4 - Test the FIPS telemetry
1. Run the command collect the FIPS state.
2. Verify the expected values in the StateDB.
