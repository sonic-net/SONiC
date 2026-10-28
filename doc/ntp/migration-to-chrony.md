# SONiC Migration to Chrony

## Table of Contents

### Revision

| Rev | Date       | Author            | Description     |
|:---:|:----------:|:-----------------:|:----------------|
| 1.0 | 10/07/2024 | Saikrishna Arcot  | Initial version |

### Scope

This high-level design document is to document the move from ntpd to Chrony as
the NTP daemon in SONiC, along with the reasons why this was done and the
changes in behavior.

## Definitions

* NTP: Network Time Protocol
* RTC: Real Time Clock
* System time: the time that is used by userspace applications when they want to get the current time

## Overview

Today, in SONiC, the NTP daemon that is used is ntpd, the reference
implementation from the NTP Project. (Starting in the 202405 branch, NTPsec is
used instead, which is a fork of ntpd that has been security-hardened. The rest
of this document will still refer to it as ntpd, but all of the issues listed
below still apply.) This daemon is responsible for keeping the time on SONiC
devices synchronized to the actual time. In general, this daemon is doing a
good job of keeping the time correct. However, there are some critical
shortcomings with regards to how this daemon works:

1. SONiC intentionally disables long jumps in the ntpd configuration (ntpd
   calls these steps), because not all applications may be able to handle large
   changes in the system time, and instead expects the time to be slewed (i.e.
   gradually adjusted).  Specifically, if applications are using the current
   system time to determine when to do something, and there's a large time jump
   either backwards or forwards, then that application may no longer behave
   correctly. On a network device, this, in the worst case, could mean
   dataplane impact. However, ntpd doesn't support _fully_ disabling long
   jumps. This is seen in the fact that the
   `ntp/test_ntp.py::test_ntp_long_jump_disabled` test case passes, where ntpd
   is able to synchronize the system time when it's one hour off within 12
   minutes. This is because ntpd is doing a long jump to correct the time, even
   though it was configured to be slewed.
2. When slewing the time, ntpd disables the kernel time discipline. One of the
   effects of this is that the kernel will never know that the system time has
   been synchronized to the actual time, and thus will not update the
   hardware clock/RTC on the board with the correct time. When the kernel knows
   that the system time is synchronized, every 11 minutes, it will write the
   current system time to the hardware clock/RTC. Not syncing the system time
   to the hardware clock/RTC means that if the system were to be rebooted, then
   it would come back up with whatever time was recorded in the hardware clock,
   which might not be the actual time.  It is possible to manually sync the
   system time to the hardware clock, which is what is done in SONiC when the
   device is being rebooted (either cold, soft, fast, or warm). However, in the
   case of an unexpected device reload (power loss, kernel panic, etc.), this
   sync will not happen.
3. For ntpd to send and receive NTP packets from the upstream servers, it must
   be listening to port 123 of an interface or an IP address. This may be
   needed for symmetric associations, but for typical client-server
   associations, generally speaking, clients shouldn't need to be listening on
   port 123. This is because the packets coming back from the NTP server will
   be sent to the UDP port that the client sent out the packet on. The
   constraint that ntpd needs to be listening on each interface/address also
   complicates new addresses being added to an interface, or an interface being
   removed and/or added (due to runtime configuration changes). In these cases,
   ntpd needs to listen for new IP addresses being added (which it does), or
   the configuration needs to be updated.
4. There have been a few cases of ntpd no longer sending out NTP packets. It's
   unclear why this happens (upstream servers have been unreachable for too
   long, interfaces have been removed and re-added, or something else), but
   this causes issues with the system time drifting.

Ntpd was the only major daemon available for Linux until fairly recently. Now,
in the last few years, there are two other implementations:

* chrony: This is another implementation designed for systems which might not
  always be running or connected to the Internet (especially virtual machines).
  It's able to synchronize the time faster than ntpd.
* systemd-timesyncd: This is a SNTP client-only implementation built into
  systemd, and is enabled by default in Ubuntu and in Debian (starting with
  Bookworm).

Systemd-timesyncd has limited configuration options, and while it might be
sufficient as a simple NTP client, it only implements SNTP (which is now
generally discouraged since it provides reduced accuracy), and will step the
clock for large changes. Therefore, chrony is the better option here.

### Requirements

For SONiC, the NTP daemon needs to support the following:

* Connect to one or more NTP servers, via interfaces that may be added or
  removed (such as front-panel ports or port channels)
  * If the NTP server(s) are not reachable, then it should keep retrying
* Keep the system time close to the actual time
* Only slew the clock, and never step the clock except upon request
* Keep the hardware clock in sync with the system clock (or allow the kernel to
  synchronize the hardware clock)
* Optionally act as an NTP server, for other devices that want to use this
  device as its upstream server
* Optionally have NTP servers configured via DHCP

## Overview of chrony

Chrony is a NTP daemon first released in 2014 that is smaller than ntpd and
claims to synchronize the time faster than ntpd. It supports most features of
ntpd and can probably be used as a replacement to ntpd in most environments.

### Advantages of replacing ntpd with chrony

For SONiC's purposes, there are specific advantages that chrony has over ntpd:

* It will only slew the system clock, and not step the system clock unless
  explicitly requested in the config file or `chronyc` (the client application
  to control `chronyd`).
* Unless specified via a config option, chrony will use the system's routing
  rules to determine what interface to send NTP packets to for each source, and
  will listen for a response on the socket that it opens. In other words, the
  list of interfaces to listen on doesn't need to be specified, and a permanent
  socket doesn't need to be kept open (unlike ntpd). If it is desired that NTP
  packets are sent via a specific interface, then the config option
  `bindacqdevice` can be used to specify this interface. Similarly,
  `bindacqaddress` can be used to specify an IPv4 or IPv6 address.
* If `rtcsync` is enabled in the configuration, then the kernel will get a
  notification that the time is synchronized, which will allow it to sync the
  hardware clock/RTC. Otherwise, chrony can manage the hardware clock/RTC.
* There's a separate communication method (Unix socket and UDP port 323) for
  talking to and configuring `chronyd` itself. `ntpd` uses the same port for
  daemon configuration/information as NTP packets. This can help with
  security/firewalls.

### Disadvantages of replacing ntpd with chrony

There are also a couple minor disadvantages as well:

* When chrony is acting as an NTP server (not just as a client), chrony can
  listen on only one interface or on one IPv4 and one IPv6 address. This means
  that unlike ntpd, where there may be multiple sockets (one per interface or
  per IP address) listening for NTP packets from client, chrony will have only
  two sockets (one for IPv4, one for IPv6) open. That being said, chrony can be
  told which IP addresses/subnets to allow/deny packets from. This means that
  chrony can be told to listen on all addresses (i.e. not be bound to a single
  interface, and listen on 0.0.0.0 and ::), and specify which subnets are
  allowed to talk to chrony through the use of `allow` and `deny` config
  options (i.e. `allow 10.2.0.0/16` and `deny 10.2.3.0/24`). Alternatively, a
  firewall (such as iptables) can be used to allow/block UDP port 123 packets
  from selected interfaces/IP subnets.
* Tools that work with `ntpd` such as `ntpq` and `ntpstat` will not work with
  chrony, as they use different protocols for communication. Fortunately,
  `chronyc` can serve as a replacement to all necessary functions of `ntpq` and
  `ntpstat`, but with possibly different output formats.

### Conclusion

Given the issues that the usage of ntpd have revealed, chrony's differences in
behavior (always slewing the time, optionally updating the hardware clock/RTC,
and reduced scope of permanently open sockets) are a major improvement over
ntpd. For the disadvantages listed here, there are at least workarounds that
can be used. These workarounds are listed above.

For this reason, it makes sense to migrate to chrony.

## Migrating from ntpd to chrony in SONiC

### Configuration

In terms of SONiC configuration changes, there are no configuration changes
required for migrating from ntpd to chrony. All of the configuration
information passed in can be translated to chrony's syntax.

For chrony's configuration file, there are differences in the configuration
options that are available. The major ones of note are:
* Chrony doesn't require listening on an interface to be able to send and
  receive NTP packets on it.
* When acting as a NTP server, chrony can only listen on one interface (or one
  IPv4 and one IPv6 address), whereas ntpd can open any number of sockets
  listening on port 123.
* Chrony doesn't have a default panic threshold, whereas ntpd does by default.
  A panic threshold means that if the time received via NTP is too different
  than the system time (i.e. greater than the panic threshold), then the NTP
  daemon will exit immediately instead of doing anything, and expect the system
  administrator to first correct the system time to the actual time. For
  SONiC's purposes, we do not want the panic threshold to be set. Chrony
  doesn't set one, whereas ntpd does set a threshold of 1000 seconds by default
  (which can be overridden).
* ntpd's configuration specified what each subnet was allowed to do, whereas
  chrony doesn't quite have that. This is partly because the configuration
  control for chrony is on a different port entirely (UDP port 323 instead of
  UDP port 123), this making it easier to be firewalled off and/or configured
  separtely. In addition, chrony will default to using a client-server
  relationship instead of symmetric relationship (where both sides will sync
  time with each other), unless the `peer` keyword is used instead of `server`.
* Chrony also allows storing the NTP servers in a separate file, making it
  possible to reload the daemon and have it reread the servers instead of
  restarting the whole daemon. At this time, this is not used in SONiC.
* Chrony configuration file can specify `rtcsync` to tell the kernel that the
  system time is now synchronized, and the kernel can then synchronize the
  hardware clock/RTC with the system time. However, this would mean that if the
  system time is significantly different from the actual time, then the
  hardware clock/RTC will not get updated until the system time is synchronized
  to the actual time, which may take months. As an alternative, chrony can
  manage the hardware clock/RTC. With this, it will immediately update the
  hardware clock/RTC with the actual time, while the system time is gradually
  slewed. This will be the configuration chosen for SONiC.

### Monitoring

For the purpose of making time synchronization issues more visible, a Monit
check will be added to verify that the time is currently synchronized to one or
more NTP servers. If Monit sees that if the time is not synchronized for 3
minutes, then a message will be printed every 5 minutes saying that the time is
not synchronized.

Sample messsage:

```
2024 Nov  7 01:36:00.154986 vlab-01 ERR monit[735]: 'ntp' status failed (1) -- NTP is not synchronized with servers
```

## SAI API

There are no changes needed in the SAI API or in the implementation by vendors.

## Configuration and management

### Config DB

There are no changes to the config DB schema.

### CLI

The output of the `show ntp` CLI will change as the output format of `chronyc`
is different. There will be no other changes specifically related to this.

However, `config ntp` will have additional options added. Specifically, it will
accept `--iburst`, `--version`, and `--association-type` arguments when adding
a NTP server, to enable iburst, specify the NTP association version, or specify
the association type, respectively. This is to address the gap that while these
options could be configured via `config_db.json`, there is no CLI option to
configure this.

Examples:

```
sudo config ntp add --iburst 10.250.0.1
```

## Restrictions/Limitations

There are expected to be no new restrictions or limitations with this change.

## Testing Requirements/Design

The existing NTP test cases will be updated to support chrony. In addition, the
long jump disabled test case will be expected to fail for chrony; that is, the
time should *not* be synchronized after 12 minutes.

# Pull requests

* [sonic-net/sonic-utilities: Switch to using chrony instead of ntpd](https://github.com/sonic-net/sonic-utilities/pull/3574)
* [sonic-net/sonic-host-services: Update hostcfgd to start chrony instead of ntp-config or ntpd](https://github.com/sonic-net/sonic-host-services/pull/170)
* [sonic-net/sonic-buildimage: Switch from ntpd to chrony](https://github.com/sonic-net/sonic-buildimage/pull/20497)
* [sonic-net/sonic-mgmt: Add support for testing chrony](https://github.com/sonic-net/sonic-mgmt/pull/15008)

# References

* [chrony FAQ](https://chrony-project.org/faq.html)
* [chrony.conf man page](https://chrony-project.org/doc/4.6.1/chrony.conf.html)
