= High-Level Design Document - No Default VRF Route Fallback
:toc: left
:toclevels: 4
:sectnums:

Revision History
| Rev | Date       | Author      | Description                                |
|-----|------------|-------------|--------------------------------------------|
| 1.0 | <Date>     | <Your Name> | Initial draft for VRF route fallback control |

== 1. Introduction
In current implementations of SONiC, the route lookup behavior can fall back to other VRFs (Virtual Routing and Forwarding) when a route is not found in a non-default VRF. This can lead to unintended consequences.

This document outlines a proposed solution to enhance SONiC's multi-VRF capabilities by providing a configurable mechanism to disable this fallback behavior. By introducing unreachable default routes in Linux VRF tables, the solution eliminates the need for kernel changes while allowing flexible, per-VRF and global configuration of fallback behavior.

== 2. Problem Description
When a route is not found in a specific non-default VRF, the Linux kernel, by default, performs a fallback route lookup in other VRFs in the order found in IP table rules. This behavior may not always align with network operators' intent, potentially leading to security risks or routing inaccuracies. A mechanism to disable this fallback—both globally and on a per-VRF basis—is required to provide more control and flexibility.

== 3. Feature Design

=== 3.1 High-Level Design
The proposed solution adds a configurable mechanism to disable fallback to other VRFs. This is achieved by introducing unreachable default routes in the corresponding Linux VRF tables. The solution does not require kernel-level changes and instead leverages SONiC's existing infrastructure, including `CONFIG_DB`, CLI utilities, and the VRF Manager Daemon (`vrfmgrd`).

*Key Features:*
* *Global and Per-VRF Configuration:* Operators can disable fallback globally or override it on a per-VRF basis.
* *Retain Default Behavior:* The system defaults to the current behavior (fallback allowed) unless explicitly configured otherwise.
* *Support for IPv4 and IPv6:* The solution ensures that both IPv4 and IPv6 routes are handled appropriately.

*Behavior Precedence:*
. Default behavior allows fallback unless explicitly disabled (same as today).
. Per-VRF configuration overrides the global setting.

=== 3.2 DB Schema Changes
The following tables will be added to `CONFIG_DB` to manage the fallback configuration.

==== 3.2.1 Global Setting
The `VRF_ROUTE_FALLBACK_GLOBAL` table will store the global fallback status for IPv4 and IPv6.

[source,json]
----
"VRF_ROUTE_FALLBACK_GLOBAL|ipv4": {
    "status": "enabled"
},
"VRF_ROUTE_FALLBACK_GLOBAL|ipv6": {
    "status": "disabled"
}
----

==== 3.2.2 Per-VRF Setting
The `VRF` table will be extended with an optional attribute to override the global setting on a per-VRF basis.

[source,json]
----
"VRF|VrfRed": {
    "fallback": "enabled"
},
"VRF|VrfBlue": {
    "fallback_v6": "disabled"
}
----

=== 3.3 CLI Enhancements (sonic-utilities)

==== 3.3.1 Configuration Commands
New CLI commands will be introduced to manage the global and per-VRF fallback settings.

.Usage Help
[source,bash]
----
user@sonic# config vrf route-fallback -h
Usage: config vrf route-fallback [OPTIONS] [ipv4|ipv6] [enable|disable]
  Configure route fallback globally or for a specific VRF

Options:
  -v, --vrf-name TEXT  VRF name
  -d, --delete         Delete override entry
  -?, -h, --help       Show this message and exit.
----

.Global Fallback Configuration Examples
[source,bash]
----
config vrf route-fallback ipv4 disable
config vrf route-fallback ipv6 enable
----

.Per-VRF Fallback Configuration Examples
[source,bash]
----
config vrf route-fallback ipv4 disable -v VrfRed
config vrf route-fallback ipv6 enable -v VrfBlue
----

==== 3.3.2 Show Command
A new `show` command will display the current fallback configuration.

.Sample Output
[literal]
----
user@sonic# show vrf-route-fallback
MGMT_VRF_CONFIG is not present.

Protocol: ipv4
Global Fallback: Enabled

VRF Name    Fallback (Override)
----------  ---------------------
VrfRed      Enabled

Protocol: ipv6
Global Fallback: Enabled

VRF Name    Fallback (Override)
----------  ---------------------
VrfRed      Enabled
----

==== 3.3.3 CLI Backend Processing
The CLI backend will be implemented with the following logic:
*   Implement CLI hooks to update `CONFIG_DB` with global and per-VRF fallback settings.
*   Validate VRF existence before processing per-VRF requests.
*   Use `swsscommon` or `sonic-db-cli` for database interaction.

=== 3.4 VRF Manager (vrfmgrd) Changes
The `vrfmgrd` daemon in `sonic-swss` will be responsible for applying the configuration.

*Responsibilities:*
* *Monitor:* `VRF_ROUTE_FALLBACK_GLOBAL` and `VRF` tables in `CONFIG_DB`.
* *Apply Logic:* Use the per-VRF value if defined; otherwise, use the global setting.
* *Add Unreachable Routes:* When fallback is disabled for a VRF, add an unreachable default route.
** `ip route add unreachable default metric 4278198272 vrf <VRF_NAME>`
** `ip -6 route add unreachable default metric 4278198272 vrf <VRF_NAME>`
* *Remove Unreachable Routes:* When fallback is enabled, remove the unreachable default route.
** `ip route del unreachable default vrf <VRF_NAME>`
** `ip -6 route del unreachable default vrf <VRF_NAME>`

NOTE: If a real default route (e.g., `0.0.0.0/0` or `::/0`) is configured in the VRF with a lower metric, it will take precedence over the unreachable default. The Linux kernel selects routes based on metric and prefix specificity, ensuring correct behavior.

=== 3.5 SAI and Hardware Impact
Unreachable routes must not be programmed into the ASIC hardware to avoid unnecessary table usage.

*Work Items:*
*   Update `vrfmgrd` or related components to tag unreachable routes as software-only.
*   Extend route orchestration logic to detect `unreachable` next-hop types and avoid programming them via SAI.
*   Ensure FRR or Zebra does not install or redistribute these unreachable routes into BGP or other routing protocols.

NOTE: The unreachable default route primarily affects software-forwarded packets—such as control-plane traffic, BGP sessions, and management traffic—by stopping fallback to other VRFs within the Linux kernel routing logic. This route is not intended to be used in hardware and has no impact on dataplane traffic handled by the ASIC. This allows operators to retain kernel-level route control without polluting the hardware FIB.

=== 3.6 Config Reload and Persistence
The feature must support configuration persistence across reboots and `config reload` operations.
*   Fallback settings and routes must persist.
*   Route reconciliation logic will be implemented at daemon startup to ensure the kernel state matches the configuration.

== 4. Testing Plan

=== 4.1 Unit Tests
*   CLI command behavior and validation (e.g., correct arguments, VRF existence).
*   `CONFIG_DB` schema integrity and backend processing logic.

=== 4.2 Integration Tests
*   Verify VRF route fallback behavior is disabled when the unreachable route is present.
*   Verify per-VRF settings correctly override the global setting.
*   Verify the global setting is applied correctly to all VRFs without an override.
*   Test IPv4 and IPv6 functionality independently.
*   Confirm persistence after `config reload` and system reboot.
*   Verify that unreachable routes are not programmed into the ASIC FIB.