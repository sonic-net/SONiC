# SONiC port naming convention change #

## Scope of the change ##

- Micorsoft proposes to change SONiC port naming convention to [Linux Network Interface Naming](http://tdt.rocks/linux_network_interface_naming.html)

## Current SONiC port naming convention ##
- Ethernet[0..(N-1)]       where N=32 or 64
- Ethernet[0,4,...,4(N-1)]

## Limits and incentives to change ##
- The port name prefix 'Ethernet' is too long.
- The port numbering doesn't match front panel numbering.
- To support chassis scenario.

## Proposal: new SONiC port naming convention ##
- et[sX]pY[abcd]
  - et: SONiC choice of port name prefix. (em, en ...)
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
1. Change port_config.ini alias column to use the new naming convention.
2. Break SONiC code dependency of 'Ethernet' prefix.
3. Break SONiC test dependency of 'Ethernet' prefix and/or 'Ethernet0'.
4. Change SONiC port name to new naming convention.
   (Note: at this stage, SONiC internal port names will match the same naming convention,
          Linux interface name will also match the same naming convention).

## Comments from the community ##
- When index starts from 1, there may or may not be a single entry waste depend on the implementation and programming language.
  - e.g. C/C++ array index starts from 0.

