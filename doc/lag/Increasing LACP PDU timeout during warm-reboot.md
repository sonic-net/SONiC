# Increasing LACP PDU timeout during warm-reboot #

## Table of Contents

### Revision

### Scope

This high-level design document is to add a feature to teamd and define a
custom LACP PDU packet to allow changing the number of maximum retries done
before the LAG session is torn down.

### Definitions

* LACP: Link Aggregation Control Protocol
* PDU: Protocol Data Unit
* LAG: Link Aggregation Group

### Overview

During warm-reboot, the control plane can be down for a maximum of 90 seconds.
This is beacuse LACP PDUs are sent every 30 seconds, and the protocol allows for
up to 3 LACP PDUs to be missed before the LAG is considered down and data
traffic is disrupted.

It would be beneficial if it's possible to temporarily increase the timeout for
LACP PDUs on a LAG on both sides. Specifically, prior to starting warm-reboot,
the timeout could be increased by some amount (beyond the limits of the
protocol), and after warm-reboot, the timeout would be restored to the normal
value.

### Requirements

- Switch running a supported SONiC with patches in libteam for this feature on
  both sides of the LAG

### Architecture Design

There's no change to the overall SONiC architecture. There are no new processes
or containers added or removed with this change.

### High-Level Design

#### Background

LACP supports two rates for sending PDUs. There is a short rate, where a PDU is
sent every 1 second, and a long rate, where a PDU is sent every 30 seconds. Both
sides know what rate to expect from the other side. If 3 LACP PDUs are missed,
then the LAG is considered to be down, and data traffic is stopped. This results
in an effective timeout of 3 seconds when using the short rate and 90 seconds
when using the long rate.

#### Protocol

To change the number of retries, a new LACP version 0xf1 will be defined. This
version will indicate that there will be two new TLV types named Actor Retry
Count (0x80) and Partner Retry Count (0x81) will be defined.

The packet structure for LACP version 0xf1 will look as follows:

| Starting byte | Length | Description                      | Value |
|---------------|--------|----------------------------------|-------|
|      0        |   1    | LACP Version                     | 0xf1  |
|      1        |   1    | Actor Info TLV Type              | 0x01  |
|      2        |   1    | Actor Info TLV Length            |  20   |
|      3        |   18   | Actor Info TLV Data              |       |
|      21       |   1    | Partner Info TLV Type            | 0x02  |
|      22       |   1    | Partner Info TLV Length          |  20   |
|      23       |   18   | Partner Info TLV Data            |       |
|      41       |   1    | Collector Info TLV Type          | 0x03  |
|      42       |   1    | Collector Info TLV Length        |  16   |
|      43       |   14   | Collector Info TLV Data          |       |
|      57       |   1    | Actor Retry Count TLV Type       | 0x80  |
|      58       |   1    | Actor Retry Count TLV Length     |   4   |
|      59       |   2    | Actor Retry Count TLV Data       |       |
|      61       |   1    | Partner Retry Count TLV Type     | 0x81  |
|      62       |   1    | Partner Retry Count TLV Length   |   4   |
|      63       |   2    | Partner Retry Count TLV Data     |       |
|      65       |   1    | Terminator TLV Type              | 0x00  |
|      66       |   1    | Terminator TLV Length            |   0   |
|      67       |   42   | Padding                          |       |

Compared to the regular LACP PDU packet, the changes are as follows:
* The LACP Version field has been changed from 0x01 to 0xf1.
* Two TLVs (Actor Retry Count, and Partner Retry Count) have been added after
  the Collector Info TLV.
* The padding has been reduced from 50 bytes to 42 bytes.

The Actor Retry Count and Partner Retry Count TLVs have the following content:

| Starting byte | Length | Description     |
|---------------|--------|-----------------|
|      0        |   1    | Retry count     |
|      1        |   1    | Padding         |

If either side wants to use a non-standard retry count (i.e. retry count set to
something besides 3), then they must send a LACP version 0xf1 packet. This
packet will include the retry count of both peers. The receiving device must
validate the peer's information and then update the retry count that the peer
wants to use.

This retry count is valid until any of the following occurs:

* A new retry count is sent
* A duration of 3 minutes times the retry count passes
* The LACP session goes down for whatever reason (because the new retry count
  expires, because the link goes down, etc.)
* The peer device sends a version 0x01 LACP PDU (without the retry count TLVs)

Except for the first event, after any of these happen, the standard retry count
of 3 applies.

If both sides want to use the standard retry count of 3 instead, they are
recommended to send a regular LACP version 0x01 packet, so that the current
standard is being followed.

#### Changing Max Retries for Warmboot

As part of a SONiC device starting the warmboot process, currently, LACP PDUs
are sent to all of the peers, to refresh the timers on the peers. This allows
the warmboot process the full 90 seconds for control plane to come back up and
for PDUs to be sent again after warmboot.

Now, the retry count on the local device will be changed to 5 retries (instead
of the standard 3 retries). This will cause teamd to send out LACP PDUs with
the above-defined version 0xf1 of the protocol, including the new retry count.
This should be done only after verifying through some method that the peer side
understands this feature. Teamd will not wait for an acknowledgment packet.

After warmboot is done, and teamd has started up after warmboot, teamd will now
be using the default standard retry count of 3. Because of this, it will send a
standard LACP PDU packet (with version 0x01). When the peer teamd client
receives this packet, it will know that this side's retry count should be
changed back to 3.

### SAI API

There are no changes needed in the SAI API or by vendors.

### Configuration and management

#### CLI

There will be two CLIs added to get and set the retry count. These are:

* `config portchannel retry-count get <portchannel_name>`
* `config portchannel retry-count set <portchannel_name> <retry_count>`

`<portchannel_name>` must refer to a valid, existing portchannel name.
`<retry_count>` must refer to a retry count between 3 and 10.

Changes done with this CLI is NOT preserved across reboots, and not saved in
any DB.

### Restrictions/Limitations

Such a change as described in this HLD is going against the LACP protocol, and
as such, can only be supported if both sides of the LAG are running SONiC, and
they are running a version of SONiC that understands this. If the peer side is
not running a supported version of SONiC, or it is not running SONiC, then
setting a custom retry count may cause the LAG to go down.

### Testing Requirements/Design

To test this feature, a T0 topology with SONiC neighbors will be used.  Test
cases will be added to get and set the retry count via CLI. In addition, a test
case will be added to increase the retry count and do a warm-reboot, and verify
that after warm-reboot, the SONiC neighbors did not bring down the LAG, and
that after the T0 comes up, the retry count has been set to 3.

# Pull requests

* [sonic-net/sonic-utilities: Add CLI configuration options for teamd retry count feature](https://github.com/sonic-net/sonic-utilities/pull/2642)
* [sonic-net/sonic-buildimage: teamd: Add support for custom retry counts for LACP sessions](https://github.com/sonic-net/sonic-buildimage/pull/13453)

# References

- [libteam](https://github.com/jpirko/libteam)
- [IEEE 802.3ad Standard for LACP](http://www.ieee802.org/3/ad/public/mar99/seaman_1_0399.pdf)
