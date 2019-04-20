# Vxlan SONiC
# fpmsyncd design
### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [Scope](#scope)

  * [1 Requirements](#1-requirements)

  * [2 Flows](#2-flows)

  * [3 Reference Tables](#3-reference-tables)

  * [4 Examples](#4-examples)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |      04/20/2019       |     Wei Bai   | Initial version                   |

# Scope
This document describes the design of fpmsyncd to support VNet routes. 

# Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| VRF                      | Virtual Routing and Forwarding |
| VNet                     | Virtual Network                |
| Vxlan                    | Virtual Extensible Local Area Network |
| VTEP                     | Vxlan Tunnel End Point         |

# 1 Requirements
This section describes the SONiC requirements for fpmsyncd in the context of VNet.

At a high level the following features should be supported:

Phase #1
- Should be able to identify VNet routes from all the receiving routes.
- Should be able to parse VNet routes and insert/delete the right entries into/from the App DB.

Phase #2
- Should be able to support warm restart for VNet routes.

# 2 Flows

# 3 Reference Tables

# 4 Examples




