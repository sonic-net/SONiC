<!-- omit from toc -->
# FRR-SONiC Protobuf Communication Channel #

<!-- omit from toc -->
## Table of Content 

<!-- TOC -->

- [1. Revision](#1-revision)
- [2. Definitions/Abbreviations](#2-definitionsabbreviations)
- [3. Scope](#3-scope)
- [4. Overview](#4-overview)
	- [4.1. Context](#41-context)
		- [4.1.1. Problem](#411-problem)
			- [4.1.1.1. Example](#4111-example)
		- [4.1.2. Solution](#412-solution)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
	- [7.1. FRR changes](#71-frr-changes)
	- [7.2. SONiC fpmsyncd changes](#72-sonic-fpmsyncd-changes)
	- [7.3. BGP container changes](#73-bgp-container-changes)
		- [7.3.1. Build FRR with the FPM Protobuf support](#731-build-frr-with-the-fpm-protobuf-support)
		- [7.3.2. Load the FPM Protobuf module on zebra startup](#732-load-the-fpm-protobuf-module-on-zebra-startup)
- [8. Testing Requirements/Design](#8-testing-requirementsdesign)
	- [8.1. Unit Test cases](#81-unit-test-cases)

<!-- /TOC -->

## 1. Revision  

| Rev  |    Date    |      Author                         | Change Description      |
| :--: | :--------: | :---------------------------------: | :---------------------: |
| 0.1  | 14/02/2024 | Carmine Scarpitta, Ahmed Abdelsalam | Initial version         |

## 2. Definitions/Abbreviations

| Definitions/Abbreviation | Description                               |
| ------------------------ | ----------------------------------------- |
| ASIC                     | Application specific integrated circuit   |
| BGP                      | Border Gateway Protocol                   |
| FIB                      | Forwarding Information Base               |
| FRR                      | Free Range Routing                        |
| FPM                      | Forwarding Plane Manager                  |
| Protobuf                 | Protocol Buffers                          |
| RIB                      | Routing Information Base                  |
| SRv6                     | Segment Routing over IPv6                 |
| SID                      | Segment Identifier                        |
| SONiC                    | Software for Open Networking in the Cloud |

## 3. Scope  

Extending the communication channel between FRR and SONiC to support the exchange of data encoded in Protobuf format.

## 4. Overview

SONiC has support for routing protocols such as BGP through the integration of the FRR routing suite. Routing protocols provided by FRR calculate their optimal routes and send them to an intermediary FRR daemon named *zebra*. Zebra, in turn, leverages the Forwarding Plane Manager (FPM) module to push these routes to SONiC. Finally, on the SONiC side, the SONiC fpmsyncd component receives the routes provided by FRR and writes them into the SONiC Redis database.

![FRR-SONiC Communication Channel Overview](images/fpm-overview.png)	
*Figure 1: FRR-SONiC Communication Channel Overview*

### 4.1. Context

#### 4.1.1. Problem

Currently, FRR communicates with SONiC using the Netlink message format. To program a route in SONiC, FRR first encodes the route in Netlink format, and then it sends the Netlink message to SONiC. However, since the Netlink format is primarily designed for transferring data between the kernel and user-space processes, it is tailored to the specific requirements and data model of the kernel and lacks some attributes required for supporting several features and use cases in SONiC. 

##### 4.1.1.1. Example

As an example, let's consider a scenario where FRR needs to program an SRv6 End.DT46 SID into the SONiC dataplane.
According to the current SONiC APPL DB schema ([doc/srv6/srv6_hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/srv6/srv6_hld.md#32-appdb-changes)), an SRv6 End.DT46 SID has seven attributes:

* `block_len`
* `node_len`
* `func_len`
* `arg_len`
* `ipv6_address`
* `action`
* `vrf`

In order to program an SRv6 End.DT46 SID in SONiC, FRR must provide all the above attributes. As shown in Figure 2, although it is possible to encode an SRv6 End.DT46 SID in Netlink format, the resulting Netlink message lacks some mandatory SID attributes, specifically `block_len`, `node_len`, `func_len` and `arg_len`, highlighted in red in Figure 2. Therefore, the Netlink message cannot be used to program the SID into the SONiC dataplane.

![FRR-SONiC Communication Channel Overview](images/example-srv6-sid.png)	
*Figure 2: Example: Netlink cannot be used to program an SRv6 SID in SONiC*

Note that SRv6 is merely one example, but similar issues may arise when implementing other features in the future.

#### 4.1.2. Solution

As mentioned before, the Netlink format is very specific to the Linux kernel and not suitable to support all use cases in SONiC. This issue has already been discussed in previous SONiC Routing WG meetings. The community has come to an agreement that we should migrate the communication channel between FRR and SONiC from the Netlink format to a kernel-independent format.
The chosen format is Protobuf.
Compared to Netlink, Protobuf has the advantage of not being tied to the kernel. As such, we can define the schema for the Protobuf message format and have it evolve independently to support all the use cases and features we want to support in SONiC.

However, since the migration effort is substantial (as it requires recoding all message types supported so far from Netlink to Protobuf), the community has come to an agreement that the migration should be gradual.

In the short term, we add support for exchanging information encoded in Protobuf format between FRR and SONiC.

* All new features are expected to use the Protobuf message format.
* Old features will be gradually migrated from Netlink to Protobuf.

Eventually, all messages will be transmitted in Protobuf format.

For further details, please refer to the SONiC Routing Working Group meeting notes and recording:
https://lists.sonicfoundation.dev/g/sonic-wg-routing/wiki/34083.


## 5. Requirements

This feature requires:

* FRR to be able to deliver information to SONiC using both Netlink and Protobuf message formats
* SONiC fpmsyncd to handle Protobuf messages and Netlink messages received from FRR
* SONiC fpmsyncd to SET/DEL entries (such as regular routes, SRv6 SIDs and SRv6 routes) to APPL_DB

## 6. Architecture Design

The scope of this document is describing the changes required to support exchanging information between FRR and SONiC using the Protobuf message format.

To support the Protobuf message format, we introduce a new FPM module in FRR, named `dplane_fpm_pb`. This module enables FRR to encode information using Protobuf as the message format and subsequently transmit the Protobuf message to SONiC.

On the SONiC side, we have a small daemon (`fpmsyncd`) that receives information from FRR and process it. We make some modifications to SONiC's `fpmsyncd`, allowing it to receive Protobuf messages from FRR, process them, and subsequently write the necessary information (such as SRv6 routes and SIDs) into the APPL_DB.

The following figure shows the changes to the SONiC Architecture:

![FRR-SONiC Protobuf Communication Channel - High-Level Architecture](images/fpm-pb-channel-architecture.png)	
*Figure 3: FRR-SONiC Protobuf Communication Channel - High-Level Architecture*

The new modules are colored in <span style="color:blue">blue</span>; the modified components are colored in <span style="color:green">green</span>.

## 7. High-Level Design 

### 7.1. FRR changes

In order to support transmitting information encoded in Protobuf format, we make some changes in FRR.

First, we add a new component called `dplane_fpm` (referred to as FPM) in FRR.
FPM establishes a communication channel with SONiC (specifically, SONiC `fpmsyncd`). This channel is used to transmit both Netlink and Protobuf messages.

FPM exports an `fpm_encoder_register()` API, which is used to add FPM encoders into the FPM system.

* We introduce a new module: the FPM Protobuf module (`dplane_fpm_pb`). This module provides capability to encode/decode information in Protobuf format. During its initialization, it uses the `fpm_encoder_register()` API to register as an FPM encoder.

* We make some changes to the existing FPM Netlink module (`dplane_fpm_nl`). This module provides capability to encode/decode information in Netlink format. During its initialization, it uses the `fpm_encoder_register()` API to register as an FPM encoder.

* The FPM Protobuf module has higher priority than the FPM Netlink module.

When FRR needs to transmit information, such as a route, to SONiC, it passes the data to FPM. Subsequently, FPM scans through the list of FPM encoders and selects the first encoder capable of encoding the requested data. Given that the Protobuf encoder holds a higher priority than the Netlink encoder, this means that FPM attempts to encode the information using the Protobuf encoder. If Protobuf is unable to encode the requested data, FPM falls back to the Netlink encoder. Following this, the chosen encoder encodes the information, and finally, FPM sends the resulting message to SONiC.

The FPM Protobuf module is disabled by default.
To enable the FPM Protobuf module in FRR, two steps are required:

* FRR must be compiled with the support for the FPM Protobuf module.
* The FRR zebra daemon must load the FPM Protobuf module during startup.

To implement these modifications, a PR has been submitted to the FRR repository and is currently under review: https://github.com/FRRouting/frr/pull/14173.

### 7.2. SONiC fpmsyncd changes

We make some changes in some of the SONiC components, namely `FpmLink` and `RouteSync`, which are part of the `fpmsyncd` process. The reason behind these changes is to enable `fpmsyncd` to process Protobuf messages received from FRR and write the necessary information (such as routes and SRv6 SIDs) to the SONiC APPL DB.

When SONiC `fpmsyncd` receives an FPM message from FRR, it passes the message to `FpmLink`. Then, `FpmLink` checks the message encoding and passes the message to the `processFpmMessageNetlink()` or `processFpmMessageProtobuf()` callback depending on the encoding type. Finally, the message is delivered to `RouteSync`, which is responsible for extracting the information (such as the route) contained in the Netlink/Protobuf message, and writing the data into the SONiC APPL DB.

As an example, the following sequence diagram shows the operations performed when FRR wants to program an SRv6 SID into the SONiC dataplane using the Protobuf format:

![FRR-SONiC Communication Channel - Protobuf Message](images/fpm-pb-sequence-diagram.png)	
*Figure 4: FRR-SONiC Communication Channel - Protobuf Message*

* FRR sends the SRv6 SID to FPM (1).
* FPM encodes the SRv6 SID using the Protobuf encoder and sends the FPM Protobuf message to SONiC (2).
* `fpmsyncd` receives the FPM Protobuf message and delivers the message to `FpmLink` (3).
* `FpmLink` checks the encoding type. Since the message is encoded in Protobuf, `FpmLink` passes the message to the `processFpmMessageProtobuf()` callback (4).
* This callback parses the Protobuf message and delivers the message to `RouteSync` (5).
* `RouteSync` checks the contents of the message. Since the message contains an SRv6 SID, it is delivered to the handler `onSrv6LocalSidMsg()` (6).
* `RouteSync` extracts the attributes of the SRv6 SID from the Protobuf message and writes the SRv6 SID entry to the APPL_DB (7).
* `OrchAgent` gets notified about the new SRv6 SID and programs the SID into the ASIC (8).
* The result of the operation is reported back to FRR over the feedback channel (9) (10) (11) (12) (13) (14).

### 7.3. BGP container changes

As mentioned earlier (see [Section 7.1](#71-frr-changes)), the FPM Protobuf support in FRR is optional.
This implies that the newly introduced FPM Protobuf module in FRR (`dplane_fpm_pb`) is disabled by default.

To activate the FPM Protobuf module in FRR, two steps are required:

* FRR must be compiled with the support for the FPM Protobuf module.
* The FRR zebra daemon must load the FPM Protobuf module during startup.

We make some modifications to the BGP container settings to accomplish this, as outlined in [Section 7.3.1](#731-build-frr-with-the-fpm-protobuf-support) and [Section 7.3.2](#732-load-the-fpm-protobuf-module-on-zebra-startup).


#### 7.3.1. Build FRR with the FPM Protobuf support

*sonic-buildimage* scripts compile FRR with the build-time options specified in the *debian/rules* file, located within the FRR repository.
To enable the FPM Protobuf module in FRR, FRR needs to be compiled with the `--enable-dplane-pb` and `--enable-protobuf` options.

A new patch file is introduced to compile FRR with the above options. Specifically, this patch adjusts the FRR build options specified within the FRR's *debian/rules* file as follows:

* The option `--disable-protobuf` is replaced with `--enable-protobuf`
* The option `--enable-dplane-pb` is added

```diff
...

override_dh_auto_configure:
	$(shell dpkg-buildflags --export=sh); \
	dh_auto_configure -- \
		--sbindir=/usr/lib/frr \
		--with-vtysh-pager=/usr/bin/pager \
		--libdir=/usr/lib/$(DEB_HOST_MULTIARCH)/frr \
		--with-moduledir=/usr/lib/$(DEB_HOST_MULTIARCH)/frr/modules \
		LIBTOOLFLAGS="-rpath /usr/lib/$(DEB_HOST_MULTIARCH)/frr" \
		--disable-dependency-tracking \
		\
		$(CONF_RPKI) \
		$(CONF_LUA) \
		$(CONF_PIM6) \
		--with-libpam \
		--enable-doc \
		--enable-doc-html \
		--enable-snmp \
		--enable-fpm \
-		--disable-protobuf \
+		--enable-protobuf \
		--disable-zeromq \
		--enable-ospfapi \
		--enable-bgp-vnc \
		--enable-multipath=256 \
		\
		--enable-user=frr \
		--enable-group=frr \
		--enable-vty-group=frrvty \
		--enable-configfile-mask=0640 \
		--enable-logfile-mask=0640 \
+		--enable-dplane-pb \
		# end

...
```

#### 7.3.2. Load the FPM Protobuf module on zebra startup

To enable the FPM Protobuf module in FRR, the FRR zebra daemon should be started with the `-M dplane_fpm_pb` option.
The command line options used to start zebra are specified in the *supervisord.conf.j2* template file, located within the *dockers/docker-fpm-frr/frr/supervisord/* directory of the *sonic-buildimage* repository.

We modify the template *supervisor.conf.j2* file to add the `-M dplane_fpm_pb` option:

```jinja2
[program:zebra]
command=/usr/lib/frr/zebra -A 127.0.0.1 -s 90000000 -M dplane_fpm_nl -M snmp --asic-offload=notify_on_offload -M dplane_fpm_pb
```

Including the `-M dplane_fpm_pb` option ensures that zebra loads the FPM Protobuf module during startup.

## 8. Testing Requirements/Design  

### 8.1. Unit Test cases  

* **Test case 1:** Receiving an SRv6 VPN route encoded using the Protobuf format
  1. Generate an FPM message containing an SRv6 VPN route encoded using Protobuf.
  2. Call `FpmLink::processFpmMessage()` with the generated FPM message.
  3. Verify the delivery of the FPM message to RouteSync by checking if `RouteSync.onMsgRaw()` is invoked.
  4. Ensure that the route is added to the ROUTE_TABLE of APPL_DB.

* **Test case 2:** Receiving an SRv6 SID encoded using the Protobuf format
  1. Generate an FPM message containing an SRv6 SID encoded using Protobuf.
  2. Call `FpmLink::processFpmMessage()` with the generated FPM message.
  3. Verify the delivery of the FPM message to RouteSync by checking if `RouteSync.onMsgRaw()` is invoked.
  4. Ensure that the route is added to the SRV6_MY_SID_TABLE of APPL_DB.
