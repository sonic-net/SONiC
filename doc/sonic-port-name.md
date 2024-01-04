# SONiC port naming convention change #

## Scope of the change ##

- Micorsoft proposes to change SONiC port naming convention to [Linux Network Interface Naming](http://tdt.rocks/linux_network_interface_naming.html)
- Nvidia proposes to extend the front panel port name to supported different prefixs to be defined in a shared regex that will be implemented in phase 1.

## Current SONiC port naming convention ##
- Ethernet[0..(N-1)]       where N=32 or 64
- Ethernet[0,4,...,4(N-1)]

## Limits and incentives to change ##
- The port name prefix 'Ethernet' is too long.
- The port numbering doesn't match front panel numbering.
- To support chassis scenario.
- To support distinguishing between different types of front panel ports in a maintainable fashion.
- Specifically, Nvidia is planning to bring up a system with 'service' ports (in addition to the regular ethernet data ports) - these
  are lower speed ports that used for connection to accelerators, internal loopbacks and more.

## Proposal: new SONiC port naming convention ##
Phase 1 (prefix change only):
- Instead of "Ethernet" we can add "Ethernet|Service|etp" and use any of the options in the hw definitions file.
- Beside of changing the prefix (Ethernet), everything else will be kept.

- (FRONT_PANNEL_REGEX)[0..(N-1)]       where N=32 or 64
- (FRONT_PANEL_REGEX)[0,4,...,4(N-1)]
   
 where FRONT_PANEL_REGEX is a common regex that includes all the supported prefixes - e.g. "Ethernet|Service|et"
- Examples
  - Etherent[0..N-3], Service[N-3..N-1] - system with two 'types' of ports
  - et[0..N-1]

Phase 2 (chassis and breakout changes):

- (FRONT_PANNEL_REGEX)[sX]pY[abcd]
  - FRONT_PANNEL_REGEX (e.g. ("et|Service"): SONiC choices of port name prefix. (em, en ...)
  - Optional:  sX, slot X, X = 1, 2, ... Usually X starts from 1.
  - Mandatory: pY, front panel port Y, Usually Y starts from 1.
  - Optional:  [abcd], port breakout.

- Examples
  - No breakout ports: etp1, etp2, ... etp32
  - 2-way breakout ports: etp16a, etp16b
  - 4-way breakout ports: etp18a, etp18b, etp18c, etp18d
  - Chassis and line cards: ets0p1, ets1p10

## Unsolved issues ##
- Port channel naming convention

## Change stages ##
Phase 1
1. Update the schema.h with the new regex (currently just change to regex that only have "Ethernet")
2. Update SONiC code dependency of 'Ethernet' prefix to use the new regex instead:
  - sonic-config-engine - portconfig.py
  - sonic-py-common - interface.py
  - sonic-py-swsssdk - port_util.py
  - sonic-utilities - pfc / pfcwd / scripts (ipintutil, sfpshow) / sfputil / utilities_common (intf_filter.pym, platform_sfputil_helper)
  - sonic_platform_base - sfputilbase.py
  - sonic-platform-daemons - ycable
  - portsyncd - linksync.cpp
  - sonic-snmp - interface tables initiation
  - sonic-device-data tests (hwsku|platform_json_checker)
3. On introducing a new prefix - just update the regex (and set the device hw configuration files), everything else should work

Phase2
1. Change port_config.ini alias column to use the new naming convention.
2. Break SONiC code dependency of 'Ethernet' prefix.
3. Break SONiC test dependency of 'Ethernet' prefix and/or 'Ethernet0'.
4. Change SONiC port name to new naming convention.
   (Note: at this stage, SONiC internal port names will match the same naming convention,
          Linux interface name will also match the same naming convention).

## Comments from the community ##
- When index starts from 1, there may or may not be a single entry waste depend on the implementation and programming language.
  - e.g. C/C++ array index starts from 0.


