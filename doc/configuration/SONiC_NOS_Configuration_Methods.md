SONiC NOS Configuration Methods
===============================

> [Description:](#description)
>
> [1. Command Line Interface (CLI)](#command-line-interface-cli)
>
> [1.1. config CLI](#config-cli)
>
> [1.2. show CLI](#show-cli)s
>
> [2. sonic-cfggen Tool](#sonic-cfggen-tool)
>
> [3. Editing config\_db.json
> Directly](#editing-config_db.json-directly)
>
> [4. REST API (RESTCONF)](#rest-api-restconf)
>
> [5. gNMI (gRPC Network Management
> Interface)](#gnmi-grpc-network-management-interface)
>
> [6. Automation Tools (Ansible, NAPALM,
> etc.)](#automation-tools-ansible-napalm-etc.)
>
> [8. Advanced Routing with vtysh
> (FRRouting)](#advanced-routing-with-vtysh-frrouting)
>
> [9. Configuration Database (Redis)](#configuration-database-redis)
>
> [10. Apply Patch ](#--apply-patch)

Description:
------------

This document provides a comprehensive overview of the configuration
methods supported by SONiC (Software for Open Networking in the Cloud).
Each method serves a specific operational purpose, ranging from
interactive command-line configuration to automation at scale.

**1. Command Line Interface (CLI)**
-------------------------------

The CLI is the most direct and user-friendly interface for managing
SONiC. It is particularly useful for network administrators who perform
hands-on configuration or monitoring tasks.

### 1.1 config CLI

**Purpose:**\
The config CLI is used to apply configuration changes that are written
into SONiC's internal configuration database (Redis Config DB). These
changes are persistent and survive system reboots when saved.

**Functionality:**\
The config CLI provides intuitive commands for configuring core network
components such as interfaces, VLANs, and BGP neighbors.

**Usage:**

-   The config saves command commits changes permanently by updating
    */etc/sonic/config\_db.json*.

-   This method is ideal for manual configuration by operators during
    initial setup or routine changes.

### 1.2 show CLI

**Purpose:**\
The show CLI allows administrators to query the current state of the
system. It is used to retrieve live operational data without modifying
any configuration.

**Usage:**

-   These commands are read-only and are essential for monitoring,
    troubleshooting, and verifying configurations.

-   Suitable for on-demand operational checks during network health
    assessments.

**2. sonic-cfggen Tool**
--------------------

**Purpose:**\
sonic-cfggen is a command-line utility that acts as a bridge between
JSON-based configurations and the Redis configuration database.

**Usage:**

-   This tool is ideal for programmatic configuration, scripting, and
    automation workflows.

Input JSON must conform to the schema expected by SONiC. Otherwise,
errors will occur during write operations.

**3. Editing config** \_db.json Directly
------------------------------------

The config\_db.json file located at /etc/sonic/config\_db.json serves as
the persistent configuration snapshot loaded during system startup.
Editing this file allows for offline configuration of SONiC.

**Steps:**

-   Open the configuration file in a text editor: \> *sudo vi
    /etc/sonic/config\_db.json*

-   Apply the changes by reloading the configuration: \> *config reload
    -y*

**Usage:**

-   This method provides full visibility and control over the complete
    configuration in a single file.

-   Configuration can be version-controlled using Git for auditability
    and rollback.

Syntax errors or inconsistencies can cause system startup failures. Use
caution and consider validation before applying changes.

**4. REST API (RESTCONF)**
----------------------

RESTCONF is a REST-based protocol that enables programmatic access to
configuration and operational data using YANG models. It is commonly
used for integrating SONiC with external orchestration and automation
systems.

**Purpose:**\
Provides network-wide management through standard RESTful API calls.
Supports both configuration and operational state retrieval.

**Usage:**

-   RESTCONF must be explicitly enabled and properly secured.

-   Authentication and access control mechanisms should be enforced.

-   Compatible with OpenConfig YANG models, making it ideal for
    multi-vendor environments.

**Use Cases:**

-   Integration with cloud controllers

-   Remote monitoring and configuration

-   Building network dashboards or tools

**5. gNMI (gRPC Network Management Interface)**
-------------------------------------------

gNMI is a high-performance, gRPC-based protocol that allows for
efficient configuration and telemetry streaming. It is optimized for
scalable, cloud-native environments.

**Purpose:** \
Supports real-time configuration changes and continuous state monitoring
via telemetry streams.

**Usage:**

-   Requires a gNMI-compatible client such as gnmic.

-   Offers secure, scalable communication over gRPC.

-   Supports both ONCE and STREAM telemetry modes.

**Use Cases:**

-   Real-time network monitoring

-   Config pushing in large data centers

-   Integration with observability tools like Prometheus.

**6. Automation Tools (Ansible, NAPALM, etc.)**
-------------------------------------------

SONiC integrates with several industry-standard automation frameworks to
support Infrastructure-as-Code (IaC) and continuous deployment
practices.

**Purpose:**\
Enables configuration management at scale through reusable playbooks and
declarative logic.

**Usage:**

-   Modules are available for interfaces, BGP, VLANs, ACLs, and more.

-   Can be used in CI/CD pipelines for automated rollouts.

-   Ideal for managing multiple SONiC switches simultaneously.

**Use Cases:**

-   Bulk device configuration

-   Compliance validation

-   Scheduled configuration updates

**7. Zero-Touch Provisioning (ZTP)**
--------------------------------

ZTP enables SONiC devices to be automatically configured upon first boot
using scripts delivered via DHCP or USB.

**Purpose:**\
Streamlines deployment of devices by eliminating manual configuration
steps.

**Supported Methods:**

-   DHCP Option 67

-   USB drive with provisioning scripts

**Script Capabilities:**

-   Fetch and apply configuration

-   Modify Redis Config DB

-   Start or configure system services

**Key Notes:**

-   ZTP execution logs are stored in */var/log/ztp.log*.

-   Scripts must be well-tested to avoid boot failures.

**Use Cases:**

-   Factory-based provisioning

-   Large-scale remote deployment

-   Dynamic onboarding in data centers

**8. Advanced Routing with vtysh (FRRouting)**
------------------------------------------

FRRouting (FRR) is the routing protocol suite embedded within SONiC. It
offers a CLI interface *(vtysh)* for advanced configuration of protocols
like BGP, OSPF, and others.

**Purpose:**\
Provides direct, protocol-level control for fine-grained routing
adjustments and testing.

**Usage:**

-   Changes made via vtysh are not persistent unless explicitly
    reflected in the configuration database.

-   Designed for advanced users, protocol testing, and temporary
    debugging.

**Use Cases:**

-   Rapid protocol configuration for experiments

-   Troubleshooting adjacency or convergence issues

-   Live diagnostics during network events

**9. Configuration Database (Redis)**
---------------------------------

SONiC utilizes Redis, an in-memory key-value store, as its central
configuration and state database. This design enables high-speed access
and real-time update propagation across system components.

**Purpose:**\
Advanced users can interact directly with Redis using the redis-cli tool
to inspect or manipulate the configuration database (specifically
database number 4, which corresponds to Config DB).

**Usage:**

-   Direct access is primarily used for debugging and low-level
    inspection.

-   Modifications via Redis CLI bypass SONiC's validation mechanisms and
    may lead to inconsistent system behavior if used improperly.

**10. - - apply-patch Command**
---------------------------

**Purpose:**\
The --apply-patch command is a sub-command within the SONiC config-cli
tool. It is used to apply changes in a structured configuration patch
format which will be in JSON or YAML gets applied to the SONiC NOS. This
command enables updates to the running-config without requiring a full
system reload or manual editing of configuration files.

**Usage:**

-   This type of modification is considered as a Dynamic update because
    the changes are applied directly to the ConfigDB which shows an
    immediate effect without actually rebooting the device.

-   Also supports a flag called **--dry-run** which actually helps in
    validating the patch before applying it to the config i.e pushing to
    the ConfigDB. This helps in catching the error in the patch\
    **Ex: Unsupported keys and values,** **Invalid Syntax format etc.**

-   Also Supports **Checkpoint & Rollback Features**. Checkpoint is like
    saving the current config (say A), so that when a Rollback happens,
    the effected config (say B) will get reverted to the last saved
    checkpoint config (A).
