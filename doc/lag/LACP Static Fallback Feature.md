# Adding Static LAG Fallback Feature #

## Table of Contents

### Revision

### Scope

This high-level design document is to extend the fallback feature in the teamd
daemon in SONiC to fall back to a static LAG (and not just a single-port LAG)
if the LACP protocol cannot be established.

### Definitions

* LACP: Link Aggregation Control Protocol
* PDU: Protocol Data Unit
* LAG: Link Aggregation Group

### Overview

In some cases (usually initial deployment or bootup), only basic or limited
networking may be available (i.e. no LACP support). During that time, it may be
necessary to have network connectivity to complete initialization or
configuration of the device. For this purpose, there is now single-port
fallback support in teamd. However, this alone may not completely work if the
device may use either/any of the ports (at its discretion) for sending packets.
With single-port fallback LAG, this becomes a problem if the port it decides to
send traffic on is not the port that has been chosen to be enabled.

In this case, the behavior that that device is using is closer to a static LAG
configuration, where that device assumes a static LAG until full
initialization/configuration happens, at which point a regular LACP LAG gets
formed. However, there is no support currently in SONiC for dynamically
switching between a static LAG and a LACP LAG. The goal of this HLD is to add
that support and describe the configuration options that would be added into
config DB.

### Requirements

- Switch running a supported SONiC with patches in libteam for this feature
- Configs set in SONiC to enable static LAG fallback

### Architecture Design

There's no change to the overall SONiC architecture. There are no new processes
or containers added or removed with this change.

### High-Level Design

If, in the SONiC configuration, fallback support is enabled, and static
fallback is chosen as the fallback method, then teamd will switch to using
static LAG if and only if the state of all ports is in defaulted state. In this
mode, all ports will be allowed to send and receive traffic, and it will be as
if the LAG is up as normal.

LACP PDUs will continue to be sent (with the flags being as if the LAG is
down). If LACP gets established, then fallback mode will be disabled.

### SAI API

There are no changes needed in the SAI API or in the implementation by vendors.

### Configuration and management

#### CLI

There will be one CLI modified to set the fallback mode. This is:

* `config portchannel add [--min-links <min_links>] [--fallback <fallback>] [--fallback-mode <fallback_mode>] <portchannel_name>`

Note the addition of the `--fallback-mode` argument, which accepts either
`single` or `static`.

Additionally, as part of these changes, `--fallback` will be tightened to
accept either `true` or `false`, instead of any value.

#### ConfigDB/YANG

This setting will be stored in CONFIG\_DB. Within the `PORTCHANNEL` table, for
each port channel, there may be a `fallback_method` field. The value for this
field may be either `single` or `static`. If this field is not present, then
the default (in teamd) is assumed to be `single`, matching current behavior.

DB migrator changes will not be required for this feature.

### Restrictions/Limitations

There are no restrictions or limitations with this feature being enabled.

### Testing Requirements/Design

To test this feature, the `test_po_update` test case in sonic-mgmt will be
modified to create a fallback LAG, both in single mode and in static mode. The
LAG coming up will be verified, and BGP establishment (thus, a basic traffic
test) will be verified.

# Pull requests

* [sonic-net/sonic-utilities: Add support for selecting the fallback mode for LAG](https://github.com/sonic-net/sonic-utilities/pull/4855)
* [sonic-net/sonic-buildimage: Add support for falling back to a static LAG if it is not established](https://github.com/sonic-net/sonic-buildimage/pull/29265)
* [sonic-net/sonic-mgmt: Test LAG fallback (both single and static)](https://github.com/sonic-net/sonic-mgmt/pull/27887)

# References

- [libteam](https://github.com/jpirko/libteam)
