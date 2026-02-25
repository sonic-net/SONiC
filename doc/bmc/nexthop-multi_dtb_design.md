# Multi-DTB Design for SONiC BMC Support

## Table of Contents

### 1. Revision

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 2026-02-25  | chander-nexthop | Initial draft |

### 2. Scope

This document describes the scope of multi-DTB (Device Tree Binary) support for SONiC BMC platform. It enables a single SONiC image to support multiple vendor BMC implementations based on AspeedTech AST27xx SoC, eliminating the need for per-vendor images.

### 3. Definitions/Abbreviations

| Term | Definition |
| ---- | ---------- |
| BMC | Baseboard Management Controller |
| DTB | Device Tree Binary |
| DTS | Device Tree Source |
| FIT | Flattened Image Tree |
| SoC | System on Chip |

### 4. Overview

Many vendors that make switches running SONiC are looking to add a Baseboard Management Controller (BMC) based on AspeedTech AST27xx SoC to their system designs. These BMC SoCs will run SONiC. It is desirable to have a single SONiC image for this purpose instead of having per-vendor images. This document proposes a design to achieve the same.

#### Background Information

Support for the necessary kernel drivers for the AST27xx SOC has already been added to the SONiC Linux Kernel Repository via https://github.com/sonic-net/sonic-linux-kernel/pull/522.

When compiled with the necessary kernel options, the SONiC arm64 kernel will have all the requisite device drivers needed for this SoC.

Support for building a SONiC image, `sonic-aspeed-arm64.bin` with `PLATFORM=aspeed` and `PLATFORM_ARCH=arm64` is being done via PR https://github.com/sonic-net/sonic-buildimage/pull/24898.

In this, we will add the common makefiles, exclude docker containers and debian packages not applicable to the BMC platform, add new docker containers for console management and Redfish APIs, add aspeed specific systemd services like bring up usb network device etc. It will also have the infrastructure outlined here for all vendors to use this same image for their SoC's.

### 5. Requirements

- SONiC image should boot with the DTB compiled from the DTS file a vendor has created.
- Vendor specific configuration changes (for example, which console tty of the SoC connects to their control plane's console) must be supported.
- Vendors should be able to add their own software like kernel modules, utility scripts etc to the image and that software must take effect when the image is booted on their card.
- U-Boot should use the correct DTB to load during SONiC boot.
- SONiC should properly set up `/host/machine.conf`, so PLATFORM is inferred correctly.
- Vendors should be able to package their own software like kernel modules, utility scripts, configuration files etc to the image.
- Changes to bring up SONiC on a new SOC should be minimal.

The proposed design outlined below attempts to address these requirements with a caveat. It is expected that vendors will submit their DTS files as patches, using the standard `src/sonic-linux-kernel` patch workflow, so that those DTS files will be compiled into device tree binaries (DTB's) as part of the kernel build. This is to avoid any extraneous dependency for the sonic-linux-kernel build.

### 6. Architecture Design

#### 6.1. Design Overview

The design hinges on the fact that a single FIT image can contain multiple DTB's and the boot loader, U-Boot, in this case, can pick a specific DTB to load. U-Boot can use any mechanism available to arrive at the DTB to load (ex. Builtin during compilation or reading some EEPROM region or some device registers). It is beyond the scope of this document to precisely specify the mechanism U-Boot would use.

However it is assumed that U-Boot will store the DTB file name to load into an environment variable called `bootconf`. This way, SONiC installer can use that variable for in place substitution when setting up the U-Boot environment during install of a SONiC image.

#### 6.2. Boot Flow

For example, SONiC installer, when setting up an image to boot, would use bootconf without specifying what it is. U-Boot is expected to define it to the right DTB:

```bash
fw_printenv sonic_image_1
sonic_image_1=run sonic_bootargs; run sonic_boot_load; bootm $loadaddr#conf-$bootconf
```

This way when during boot the appropriate DTB too is loaded. The kernel exposes the information from that DTB in `/proc/device-tree`.

#### 6.3. Platform Detection and Configuration

After SONiC boots up, the file `/host/machine.conf` is used to arrive at the PLATFORM and SONiC would set up `/usr/share/sonic/platform` to point into the vendor+platform directory under `/device`. So, it becomes imperative that `/host/machine.conf` will have to be set up properly for the SONiC's workflow.

To do this, this design proposes to use a systemd service that will run once upon first boot. This systemd service will look into `/proc/device-tree/compatible` and will map the string therein to the platform and set up the `/host/machine.conf`.

The design assumes a single DTB per vendor card. Revisions, if any, need to have a different DTB name and U-Boot must be able to differentiate between the revisions to set up bootconf. However this design doesn't preclude the possibility of multiple DTB names pointing to the same PLATFORM name.

#### 6.4. Vendor-Specific Software Support

To support vendor specific software like kernel modules, scripts etc, we would use the existing lazy install feature of SONIC that lets platform specific packages to be packaged into the image but installed at run time during first boot. Therefore there would be a per vendor `sonic-platform-module-<vendor>` directory under `platform/aspeed`, where a vendor can define debian packages per card they create. All these .debs would be packaged into the image but installed at runtime using the existing lazy install mechanism supported by the rc.local service.

#### 6.5. Directory Layout

```
platform/aspeed/
├── one-image.mk
├── onie-image-arm64.conf
├── platform-modules-ast-evb.mk        # Makefile for EvalBrd .deb
├── platform-modules-nexthop.mk        # Makefile for NextHop .deb
├── platform_arm64.conf
├── rules.mk
├── scripts
│   ├── sonic-machine-conf-init.sh
│   ├── sonic-platform-init.sh
│   ├── sonic-uboot-env-init.sh
│   └── sonic-usb-network-init.sh
├── sonic-platform-modules-ast-evb     # Vendor specific Dir
│   ├── ast2700                        # Vendor card sub-dir
│   │   ├── build
│   │   │   ├── bdist.linux-aarch64
│   │   │   └── lib
│   │   │       └── sonic_platform
│   │   │           ├── __init__.py
│   │   │           ├── chassis.py
│   │   │           └── platform.py
│   │   ├── obmc-console
│   │   │   └── server.tty.conf
│   │   ├── scripts
│   │   ├── setup.py
│   │   ├── sonic_platform
│   │   │   ├── __init__.py
│   │   │   ├── chassis.py
│   │   │   ├── fan.py
│   │   │   ├── fan_drawer.py
│   │   │   ├── platform.py
│   │   │   ├── thermal.py
│   │   │   └── watchdog.py
│   │   └── systemd
│   ├── debian
│   │   ├── changelog
│   │   ├── control
│   │   ├── rules
│   │   └── sonic-platform-ast-evb-ast2700.postinst
│   └── setup.py
├── sonic-platform-modules-nexthop     # Vendor Nexthop
│   ├── b27                            # Nexthop's BMC card
│   │   ├── build
│   │   │   ├── bdist.linux-aarch64
│   │   │   └── lib
│   │   │       └── sonic_platform
│   │   │           ├── __init__.py
│   │   │           ├── chassis.py
│   │   │           └── platform.py
│   │   ├── obmc-console
│   │   │   └── server.tty.conf
│   │   ├── scripts
│   │   │   └── switch_cpu_utils.sh
│   │   ├── setup.py
│   │   └── sonic_platform
│   │       ├── __init__.py
│   │       ├── chassis.py
│   │       ├── fan.py
│   │       ├── fan_drawer.py
│   │       ├── platform.py
│   │       ├── thermal.py
│   │       └── watchdog.py
│   ├── debian
│   │   ├── changelog
│   │   ├── control
│   │   ├── rules
│   │   └── sonic-platform-aspeed-nexthop-b27.postinst
│   └── setup.py
├── sonic_fit.its
└── systemd
    ├── sonic-machine-conf-init.service
    ├── sonic-platform-init.service
    ├── sonic-uboot-env-init.service
    └── sonic-usb-network-init.service

device/aspeed/arm64-aspeed_ast2700_evb-r0/
├── asic.conf
├── default_sku
├── installer.conf
├── platform.json
├── platform_asic
├── platform_components.json
├── platform_env.conf
├── pmon_daemon_control.json
└── system_health_monitoring_config.json

device/nexthop/arm64-nexthop_b27-r0/
├── asic.conf
├── default_sku
├── installer.conf
├── platform.json
├── platform_asic
├── platform_components.json
├── platform_env.conf
├── pmon_daemon_control.json
└── system_health_monitoring_config.json
```

#### 6.7. Build & Boot Flow Diagram

![Build & Boot Flow Diagram](images/nexthop-multi_dtb_design.png)

### 7. Vendor Work Flow For New SoCs

#### 7.1. Create DTS File
- Create `.dts` file for their card and submit to `src/sonic-linux-kernel` as a patch. This approach is preferred over say having the DTS file in a vendor specific directory under `platform/aspeed/vendor/` to avoid a dependency on such files to build the kernel.

#### 7.2. Update U-Boot
- Make changes to U-Boot to detect the card type, arrive at DTB file to use and set it in the U-Boot var `bootconf`

#### 7.3. Create Device Directory
- Create a directory under `device/<vendor>` ex. `device/aspeed/arm64-aspeed_ast2700_evb-r0/` and put `platform_env.conf`, `default_sku` etc as files inside it. `device/aspeed/arm64-aspeed_ast2700_evb-r0/` defines the same for the evaluation board and can be used as reference.

#### 7.4. Create Platform Modules Directory
Add a directory under `platform/aspeed/sonic-platform-modules-<vendor>/` (ex. `platform/aspeed/sonic-platform-modules-ast-evb`) and, for each card type they have, add a subdirectory with the card name and under that the following directories and files:

##### 7.4.1. sonic_platform/
- `{__init__.py, platform.py, chassis.py etc}`
- These need inherit from their respective classes defined by `sonic_platform_base`

##### 7.4.2. scripts/
- Any scripts vendors want to install go here

##### 7.4.3. obmc-console/server.tty.conf
- Specify the BMC tty that maps to the switch cpu's console tty.

##### 7.4.4. setup.py
- Defines setup with vendor specific attributes
- Can use `platform/aspeed/sonic-platform-modules-ast-evb/ast2700/` as reference

##### 7.4.5. Create (first time) OR Update platform-modules-ast-evb.mk

#### 7.5. Edits to Common Files

##### 7.5.1. Edit sonic_fit.its

Add details about their DTB in `platform/aspeed/sonic_fit.its`. Use `ast2700-evb` in this file as reference.
- Under `images` section
- Under `configurations` section

##### 7.5.2. Edit sonic-machine-conf-init.sh

Edit `platform/aspeed/sonic-machine-conf-init.sh` and add a condition to the 'if block' at line 37, something like below. Please note that the PLATFORM string MUST match the directory name created for the vendor under `device/aspeed`:

```bash
if echo "$COMPATIBLE" | grep -q "vendorA-evb"; then
    PLATFORM="arm64-aspeed_ast2700_vendorA"
    MACHINE="aspeed_ast2700"
    log "Detected Aspeed AST2700 EVB platform"
fi
```

#### 7.6. Create or Update Makefile

Create or Update Makefile `platform/aspeed/platform-modules-<vendor>.mk`:

```makefile
# NextHop Platform modules
#
# NOTE: When adding more platforms (e.g., b28), use add_extra_package:
#   ASPEED_NEXTHOP_B28_PLATFORM_MODULE = sonic-platform-aspeed-nexthop-b28_1.0_arm64.deb
#   $(ASPEED_NEXTHOP_B28_PLATFORM_MODULE)_PLATFORM = arm64-nexthop_b28-r0
#   $(eval $(call add_extra_package,$(ASPEED_NEXTHOP_B27_PLATFORM_MODULE),$(ASPEED_NEXTHOP_B28_PLATFORM_MODULE)))

ASPEED_NEXTHOP_B27_PLATFORM_MODULE = sonic-platform-aspeed-nexthop-b27_1.0_arm64.deb
$(ASPEED_NEXTHOP_B27_PLATFORM_MODULE)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-nexthop
$(ASPEED_NEXTHOP_B27_PLATFORM_MODULE)_PLATFORM = arm64-nexthop_b27-r0
SONIC_DPKG_DEBS += $(ASPEED_NEXTHOP_B27_PLATFORM_MODULE)
```

