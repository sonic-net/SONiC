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
		- [Adjacent Considerations](#adjacent-considerations)
		- [Profiling](#profiling)
	- [Use Cases](#use-cases)
		- [Datacenter Environment](#datacenter-environment)
		- [Enterprise Environment](#enterprise-environment)
		- [Edge Environment](#edge-environment)
	- [Configuration and Management](#configuration-and-management)
	- [Testing](#testing)
	- [Security Considerations](#security-considerations)
	- [References](#references)

### Revision

| Version | Date       | Author       | Description          |
|---------|------------|--------------|----------------------|
| 1.0     | 2024-07-30 | Amir Mazor    | Initial Draft        |

### Scope

This document will go over changes to be made to the SONiC build system in order to implement profiles for different types of devices.

### Definitions/Abbreviations

This section covers the abbreviations, if any, used in this high-level design document and their definitions.

### Overview

The purpose of this section is to give an overview of the Sonic Profiling feature and its architecture implementation in SONiC. The Sonic Profiling feature aims to simplify the configuration of feature sets typically needed for different use cases such as datacenter, enterprise, and edge environments.

### Requirements

#### Functional Requirements

- The system must support multiple profiles such as ENTERPRISE, DATACENTER, and EDGE.
- Each profile must have a predefined set of configurations optimized for its use case.

### Architecture Design

- **Configuration Files**: Each profile will have its own configuration file stored in a predefined directory.
- **Build System Integration**: The build system will be modified to include the selected profile's configuration during the build process.

### High-Level Design

- **Built-in Feature**: The Sonic Profiling feature will be a built-in feature of the SONiC build system.
- **Repositories**: Changes will be made to the `sonic-buildimage` repository.
- **SWSS and Syncd Changes**: No changes are expected in SWSS and Syncd as this is a build-time feature.
- **DB and Schema Changes**: No changes are expected in the database schema.
  
#### Adjacent Considerations

1. Verify which features/containers are deprecated in order to lessen the workload.
2. Standardize configuration variables to be BUILD/INSTALL and ENABLE for all features.
3. Install and enable all features, and look into how big the image is, and the CPU/mem usage of each docker container.
    - Some containers we could do extra work into decreasing the size (such as docker-nat).

#### Profiling

Create a rules/config file for every profile, and using a SONIC_PROFILE env variable to decide which config file to import.

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
source $CONFIG_FILE
```

Additional configurations can still be given that will override the profile settings.
If no SONIC_PROFILE is given, the default rules/config will be used.

### Use Cases

#### Datacenter Environment

In a datacenter environment, network devices often need to handle high traffic volumes with low latency. The Sonic Profiling feature allows for the selection of a "DATACENTER" profile during the build time, which includes configurations optimized for high performance and scalability.

**How the Feature Will Be Used:**

- During the build process, the `SONIC_PROFILE` environment variable is set to `DATACENTER`.
- The build system uses the `rules/config.DATACENTER` configuration file, which includes settings optimized for datacenter operations.
- These settings might include high-performance forwarding rules, optimized buffer sizes, and specific hardware acceleration features.

**Benefits:**

- **Performance Optimization:** Ensures that the network device is configured to handle high traffic volumes efficiently.
- **Scalability:** Provides configurations that support the scaling needs of large datacenter environments.
- **Consistency:** Ensures that all devices built with the `DATACENTER` profile have a consistent configuration, reducing the risk of misconfiguration.

By using the Sonic Profiling feature, network administrators can ensure that their devices are built with the optimal settings for their specific environment, leading to improved performance and reliability.

#### Enterprise Environment

In an enterprise environment, network devices often need to prioritize security and reliability. The Sonic Profiling feature allows for the selection of an "ENTERPRISE" profile during the build time, which includes configurations optimized for enterprise-grade deployments.

**How the Feature Will Be Used:**

- During the build process, the `SONIC_PROFILE` environment variable is set to `ENTERPRISE`.
- The build system uses the `rules/config.ENTERPRISE` configuration file, which includes settings optimized for enterprise operations.
- These settings might include enhanced security features, strict access control policies, and advanced monitoring capabilities.

**Benefits:**

- **Security:** Ensures that the network device is configured with the necessary security measures to protect sensitive enterprise data.
- **Reliability:** Provides configurations that prioritize fault tolerance and high availability, minimizing downtime and ensuring business continuity.
- **Compliance:** Helps organizations meet regulatory requirements by implementing industry best practices for network security and data protection.

By using the Sonic Profiling feature, enterprises can deploy network devices that meet their specific security and reliability needs, reducing the risk of cyber threats and ensuring smooth operations.

#### Edge Environment

In an edge environment, network devices often need to be deployed in remote locations with limited resources. The Sonic Profiling feature allows for the selection of an "EDGE" profile during the build time, which includes configurations optimized for edge deployments.

**How the Feature Will Be Used:**

- During the build process, the `SONIC_PROFILE` environment variable is set to `EDGE`.
- The build system uses the `rules/config.EDGE` configuration file, which includes settings optimized for edge operations.
- These settings might include power-saving features, lightweight containerization, and simplified management interfaces.

**Benefits:**

- **Resource Efficiency:** Ensures that the network device operates with minimal resource consumption, maximizing performance in resource-constrained environments.
- **Simplicity:** Provides configurations that are easy to deploy and manage in remote locations with limited IT support.
- **Flexibility:** Allows for customization based on specific edge use cases, such as IoT deployments or remote branch connectivity.

By using the Sonic Profiling feature, organizations can deploy network devices in edge environments with confidence, knowing that the devices are optimized for resource efficiency and simplicity.

### Configuration and Management

Various default configurations will be made, most notably for datacenter, enterprise and edge switches. Additional configuration profiles can be made by creating a config file in the rules directory in the format `config.<profile-name>`

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

This section lists any references used in the creation of this high-level design document. This can include:

- Related SONiC documentation.
- External standards and specifications.
- Research papers and articles.