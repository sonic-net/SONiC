## Table of Content

- [Table of Content](#table-of-content)
	- [Revision](#revision)
	- [Scope](#scope)
	- [Definitions/Abbreviations](#definitionsabbreviations)
	- [Overview](#overview)
	- [Requirements](#requirements)
		- [Functional Requirements](#functional-requirements)
	- [Architecture Design](#architecture-design)
	- [High-Level Design](#high-level-design)
		- [Standardize Build Configurations](#standardize-build-configurations)
			- [Inconsistent Configurations](#inconsistent-configurations)
			- [Solution](#solution)
		- [Profiling](#profiling)
		- [Adjacent Considerations](#adjacent-considerations)
	- [Use Cases](#use-cases)
		- [Datacenter Environment](#datacenter-environment)
		- [Enterprise Environment](#enterprise-environment)
		- [Custom Environment](#custom-environment)
	- [Testing](#testing)
	- [Security Considerations](#security-considerations)
	- [References](#references)

### Revision

| Version | Date       | Author       | Description          |
|---------|------------|--------------|----------------------|
| 1.0     | 2024-07-30 | Amir Mazor   | Initial Draft        |

### Scope

This document outlines enhancements to the SONiC build system, focusing on implementing build profiles and standardizing build configurations to support various deployment environments.

### Definitions/Abbreviations

This section covers the abbreviations, if any, used in this high-level design document and their definitions.

### Overview

The SONiC Profiling feature simplifies the configuration of feature sets tailored for different use cases, such as enterprise and datacenter environments. As SONiC expands into areas like AI and enterprise networks, each use case requires specific configurations. The introduction of standardized build profiles addresses this need by streamlining the build process and ensuring that each deployment type receives the appropriate settings.

### Requirements

#### Functional Requirements

- Support multiple profiles such as ENTERPRISE, DATACENTER, and future profiles.
- Each profile must include a predefined set of configurations optimized for its respective use case.

### Architecture Design

- **Configuration Files**: Each profile will have its own configuration file stored in a predefined path within the build system.
- **Build System Integration**: The build system will be enhanced to include the selected profile's configuration during the build process.
- **Standardization**: Configuration settings within the build system will be standardized to ensure consistency and ease of future enhancements.

### High-Level Design

- **Built-in Feature**: The Sonic Profiling feature will be a built-in feature of the SONiC build system.
- **Repositories**: Changes will be made to the `sonic-buildimage` repository.
- **SWSS and Syncd Changes**: No changes are expected in SWSS and Syncd as this is a build-time feature.
- **DB and Schema Changes**: No changes are expected in the database schema.

#### Standardize Build Configurations

##### Inconsistent Configurations

Currently, the infrastructure lacks clarity in managing configurations, leading to inconsistencies. For instance, consider the **docker-nat** configuration:

In rules/config, the line `INCLUDE_NAT = y` is intended to "*build docker-nat for NAT support.*" However, even when this variable is set to "*y*," the docker-nat image is built but not enabled by default. This differs from configurations like `INCLUDE_SYSTEM_EVENTD = y`, where both the build and default enablement occur.

This inconsistency leads to varying interpretations among developers regarding what "including" a feature actually does.

Another example of an inconsistent configuration is in **docker-eventd**:

Here, the eventd docker is always built, but it is only installed if `INCLUDE_SYSTEM_EVENTD = y`:

```makefile
SONIC_DOCKER_IMAGES += $(DOCKER_EVENTD)
ifeq ($(INCLUDE_SYSTEM_EVENTD), y)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_EVENTD)
endif
```

In contrast, for other dockers like **docker-nat**, the image is only built and installed if `INCLUDE_NAT = y`:

```makefile
ifeq ($(INCLUDE_NAT), y)
SONIC_DOCKER_IMAGES += $(DOCKER_NAT)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_NAT)
endif
```

##### Solution

To streamline profile creation and enhance the clarity of configurations, standardized environment variables will be introduced. These changes will ensure consistent interpretation and implementation of configurations across all features:

- All features that implement a docker container will have the following environment variables:
  - `BUILD_SONIC_<FEATURE>`: Builds the relevent source code associated with the feature
  - `INSTALL_SONIC_<FEATURE>`: Installs the docker container into the SONiC image
  - `ENABLE_SONIC_<FEATURE>`: Enables the docker container by default when starting the SONiC image.
  - `DELAY_SONIC_<FEATURE>`: Delays the start of the docker container
  - `AUTORESTART_SONIC_<FEATURE>`: Automatically restarts the container after failure.

#### Profiling

Create a rules/config file for every profile, and using a SONIC_PROFILE env variable to decide which config file to import.

The following block of code will be added to `makefile.work`.

```bash
# Check if SONIC_PROFILE is set
if [ -z "$SONIC_PROFILE" ]; then
    echo "SONIC_PROFILE is not set. Using default configuration."
    CONFIG_FILE="rules/config"
else
    CONFIG_FILE="rules/config.$SONIC_PROFILE"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Configuration file $CONFIG_FILE does not exist. Using default configuration."
        CONFIG_FILE="rules/config"
    fi
fi

# Import the configuration file
include $CONFIG_FILE
```

Additional configurations can override the profile settings during the build process. If no `SONIC_PROFILE` is provided, the default configuration file will be used.

#### Adjacent Considerations

1. Identify and remove deprecated features/containers to reduce maintenance overhead.
2. Evaluate the impact on image size and resource usage when all features are enabled. Consider optimizing containers like docker-nat for size reduction.

### Use Cases

#### Datacenter Environment

In a datacenter environment, network devices are often required to manage high traffic volumes with minimal latency. The SONiC Profiling feature enables the selection of a "DATACENTER" profile during build time, incorporating configurations specifically optimized for high-performance requirements.

**Feature Usage:**

- During the build process, set the SONIC_PROFILE environment variable to DATACENTER.
- The build system will reference the rules/config.DATACENTER configuration file, which includes settings optimized for datacenter operations.
- For example, these settings might remove the DHCP server container or add dual-TOR (top-of-rack) capabilities.

By utilizing the SONiC Profiling feature, network administrators can ensure that their devices are configured with the most suitable settings for datacenter environments, enhancing both performance and reliability.

#### Enterprise Environment

In an enterprise environment, network devices must often prioritize security and reliability. The SONiC Profiling feature allows for the selection of an "ENTERPRISE" profile during build time, incorporating configurations optimized for enterprise-grade deployments.

**Feature Usage:**

- During the build process, set the SONIC_PROFILE environment variable to ENTERPRISE.
- The build system will use the rules/config.ENTERPRISE configuration file, which includes settings optimized for enterprise operations.
- For example, these settings may enable MACsec (Media Access Control Security) and NAT (Network Address Translation) capabilities.

By leveraging the SONiC Profiling feature, enterprises can deploy network devices tailored to meet their specific security and reliability requirements, thereby reducing the risk of cyber threats and ensuring seamless operations.

#### Custom Environment

Organizations may create and utilize custom profiles tailored to their unique needs. Additional configuration profiles can be created by adding a config file in the rules directory in the format config.<profile-name>. While using the SONiC profile, any configurations can be overridden during the build process by setting environment variables. For example: make SONIC_PROFILE=ENTERPRISE DEFAULT_PASSWORD='foo' target/sonic-vs.img.gz.

This approach provides greater flexibility, allowing organizations to use an existing configuration file as a template while customizing it to better align with their specific requirements.

### Testing

- Check how PTF and other testing suites interacts with features (disabled and enabled)
	- Do changes need to be made to PTF specifically
	- Does every profile need it's own PTF? Can these be changed in runtime?
		- Automatic detection?

### Security Considerations

This section discusses any security considerations related to the Sonic Profiling feature. It should cover:

- Potential security risks.
- Mitigation strategies.
- Impact on existing security measures.

### References

This section lists any references used in the creation of this high-level design document.