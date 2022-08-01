# Introduction
## Overview

During warm-reboot, the control plane can be down for a maximum of 90 seconds.
This is beacuse LACP PDUs are sent every 30 seconds, and the protocol allows for
up to 3 LACP PDUs to be missed before the LAG is considered down and data
traffic is disrupted.

It would be beneficial if it's possible to temporarily increase the timeout for
LACP PDUs on a LAG on both sides. Specifically, prior to starting warm-reboot,
the timeout could be increased by some amount (beyond the limits of the
protocol), and after warm-reboot, the timeout would be restored to the normal
value.

## Requirements

- Switch running a supported SONiC on both sides of the LAG

## Assumptions

TODO

## Limitations


Such a change is going against the LACP protocol, and as such, can only be
supported if both sides of the LAG are running SONiC, and they are running a
version of SONiC that understands this. If the peer side is not running a
supported version of SONiC, or it is not running SONiC, then the current
behavior is preseved.

# Background

LACP supports two rates for sending PDUs. There is a short rate, where a PDU is
sent every 1 second, and a long rate, where a PDU is sent every 30 seconds. Both
sides know what rate to expect from the other side. If 3 LACP PDUs are missed,
then the LAG is considered to be down, and data traffic is stopped. This results
in an effective timeout of 3 seconds when using the short rate and 90 seconds
when using the long rate.

# Changing Max Retries for Warmboot

As part of a SONiC device starting the warmboot process, LACP PDUs are sent to
all of the peers, to refresh the timers on the peers. This allows the warmboot
process the full 90 seconds for control plane to come back up and for PDUs to be
sent again after warmboot. However, if the peer device is notified that this
device is going through warmboot, then the number of retries can be increased,
and the timeout can be raised.

# Protocol

When warmboot is starting, along with refreshing the LACP PDUs, an additional
Ethernet packet will be sent to the peer specifying the number of retries to
perform. This Ethernet packet will have an ethertype of 0x6300, and will not
have an IPv4 or IPv6 layer on top of it. Instead, there will instead be multiple
TLV fields, similar to LACP.

The TLV types will be defined as follows:

| Value | Description         |
|-------|---------------------|
| 0x01  | Actor Information   |
| 0x02  | Partner Information |
| 0x03  | Retry Count         |

Both Actor Information and Partner Information have the following content:

| Starting byte | Length | Description     |
|---------------|--------|-----------------|
|      0        |   2    | System Priority |
|      2        |   6    | System ID       |
|      8        |   2    | Key             |
|     10        |   2    | Port Priority   |
|     12        |   2    | Port            |

Retry count have the following content:

| Starting byte | Length | Description     |
|---------------|--------|-----------------|
|      0        |   2    | New retry count |

When the retry count needs to be changed, the sending device must send a packet
with ethertype 0x6300, and the data will contain the Actor Information, Partner
Information, and Retry Count TLVs. The receiving device must validate the actor
and partner information, and then update the retry count as specified. No
acknowledgment packet is sent back.

# CLI

No new CLI options or config options will be added, as this is not meant to be
configurable.

# References

- [libteam](https://github.com/jpirko/libteam)
- [IEEE 802.3ad Standard for LACP](http://www.ieee802.org/3/ad/public/mar99/seaman_1_0399.pdf)
