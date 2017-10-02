
# Critical Resource Monitoring

## Overview
This document captures the SONiC requirements for monitoring critical ASIC resources by polling SAI attributes. At a high level, the following support is expected:
1.	User must be able to query (via CLI/Show command) the current usage/availability of critical resources
2.	System must log WARNING if there are any resources that exceeds a pre-defined threshold value

## Summary of resources
This section captures a list of CLI requirements for monitoring the Critical Resources. It also requires that appropriate logging must be provided for all these resources if the usage exceeds the threshold. 
1.	User shall be able to query currently used number of IPv4 routes and number of available entries
2.	User shall be able to query currently used number of IPv6 routes and number of available entries
3.	User shall be able to query currently used number of IPv4 Nexthops and number of available entries
4.	User shall be able to query currently used number of IPv6 Nexthops and number of available entries
5.	User shall be able to query currently used number of IPv4 Neighbors and number of available entries
6.	User shall be able to query currently used number of IPv6 Neighbors and number of available entries
7.	User shall be able to query currently used number of Nexthop group member and number of available entries
8.	User shall be able to query currently used number of Nexthop group objects and number of available entries
9.	User shall be able to query currently used number of ACL TCAM and number of available entries
  -	ACL Table 
  -	ACL Group
  -	ACL Entries
  -	ACL Counters/Statistics
  
10.	User shall be able to query currently used number of FDB entries and number of available entries
