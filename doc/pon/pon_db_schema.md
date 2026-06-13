# PON DB Schema

## Contents

- [Summary](#summary)
- [YANG Model](#yang-model)
- [CONFIG_DB](#config-db)
  - [`PON_CONTROLLER`](#pon-controller)
  - [`PON_DOWNSTREAM_QOS_MAP_MAP`](#pon-downstream-qos-map-map)
  - [`PON_OLT_INTF`](#pon-olt-intf)
  - [`PON_OLT_INTF_NETWORK`](#pon-olt-intf-network)
  - [`PON_OLT_INTF_ONU`](#pon-olt-intf-onu)
  - [`PON_OLT_INTF_ONU_OLT_SERVICE`](#pon-olt-intf-onu-olt-service)
  - [`PON_OLT_INTF_ONU_SERVICE_GEMPORT`](#pon-olt-intf-onu-service-gemport)
  - [`PON_OLT_INTF_ONU_SERVICE_TCONT`](#pon-olt-intf-onu-service-tcont)
  - [`PON_OLT_PLUG`](#pon-olt-plug)
  - [`PON_OLT_PLUG_FW_BANK_FILE`](#pon-olt-plug-fw-bank-file)
  - [`PON_ONU`](#pon-onu)
  - [`PON_ONU_FW_BANK_FILE`](#pon-onu-fw-bank-file)
  - [`PON_ONU_OLT_SERVICE`](#pon-onu-olt-service)
  - [`PON_ONU_OLT_SERVICE_NETWORK`](#pon-onu-olt-service-network)
  - [`PON_ONU_SERVICE_CONFIG_VALUE`](#pon-onu-service-config-value)
  - [`PON_ONU_TEMPLATE_OLT_SERVICE`](#pon-onu-template-olt-service)
  - [`PON_ONU_TEMPLATE_OLT_SERVICE_NETWORK`](#pon-onu-template-olt-service-network)
  - [`PON_ONU_TEMPLATE_ONU`](#pon-onu-template-onu)
  - [`PON_ONU_TEMPLATE_ONU_FW_BANK_FILE`](#pon-onu-template-onu-fw-bank-file)
  - [`PON_ONU_TEMPLATE_SERVICE_CONFIG_VALUE`](#pon-onu-template-service-config-value)
  - [`PON_ONU_TEMPLATE_UNI`](#pon-onu-template-uni)
  - [`PON_ONU_UNI`](#pon-onu-uni)
  - [`PON_SERVICE_CONFIG_PROFILE_ANI_G`](#pon-service-config-profile-ani-g)
  - [`PON_SERVICE_CONFIG_PROFILE_CARDHOLDER`](#pon-service-config-profile-cardholder)
  - [`PON_SERVICE_CONFIG_PROFILE_CIRCUIT_PACK`](#pon-service-config-profile-circuit-pack)
  - [`PON_SERVICE_CONFIG_PROFILE_ENHANCED_FEC_PM_HIST_DATA`](#pon-service-config-profile-enhanced-fec-pm-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_ENHANCED_TC_PERF_MON_HIST_DATA`](#pon-service-config-profile-enhanced-tc-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM`](#pon-service-config-profile-ethernet-frame-extended-pm)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM64_BIT`](#pon-service-config-profile-ethernet-frame-extended-pm64-bit)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_DOWNSTREAM`](#pon-service-config-profile-ethernet-frame-perf-mon-hist-data-downstream)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_UPSTREAM`](#pon-service-config-profile-ethernet-frame-perf-mon-hist-data-upstream)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA`](#pon-service-config-profile-ethernet-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA3`](#pon-service-config-profile-ethernet-perf-mon-hist-data3)
  - [`PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA`](#pon-service-config-profile-extended-vlan-tagging-operation-configuration-data)
  - [`PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_DSCP_TO_PBIT_MAPPING_DSCP_TO_PBIT_MAPPING_ENTRY`](#pon-service-config-profile-extended-vlan-tagging-operation-configuration-data-dscp-to-pbit-mapping-dscp-to-pbit-mapping-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_ENTRY`](#pon-service-config-profile-extended-vlan-tagging-operation-configuration-data-received-frame-vlan-tagging-operation-table-received-frame-vlan-tagging-operation-table-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_FEC_PERF_MON_HIST_DATA`](#pon-service-config-profile-fec-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PERF_MON_HIST_DATA`](#pon-service-config-profile-gal-ethernet-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PROFILE`](#pon-service-config-profile-gal-ethernet-profile)
  - [`PON_SERVICE_CONFIG_PROFILE_GEM_INTERWORKING_TP`](#pon-service-config-profile-gem-interworking-tp)
  - [`PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP`](#pon-service-config-profile-gem-port-network-ctp)
  - [`PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP_PERF_MON_HIST_DATA`](#pon-service-config-profile-gem-port-network-ctp-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_HEADER`](#pon-service-config-profile-header)
  - [`PON_SERVICE_CONFIG_PROFILE_HEADER_COMPATIBILITY_VENDOR_MODEL`](#pon-service-config-profile-header-compatibility-vendor-model)
  - [`PON_SERVICE_CONFIG_PROFILE_HEADER_INPUTS_EXT_INPUT`](#pon-service-config-profile-header-inputs-ext-input)
  - [`PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE`](#pon-service-config-profile-ieee8021p-mapper-service-profile)
  - [`PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE_DSCP_TO_P_BIT_MAPPING_DSCP_TO_P_BIT_MAPPING_ENTRY`](#pon-service-config-profile-ieee8021p-mapper-service-profile-dscp-to-p-bit-mapping-dscp-to-p-bit-mapping-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_IPV6_HOST_CONFIG_DATA`](#pon-service-config-profile-ipv6-host-config-data)
  - [`PON_SERVICE_CONFIG_PROFILE_IP_HOST_CONFIG_DATA`](#pon-service-config-profile-ip-host-config-data)
  - [`PON_SERVICE_CONFIG_PROFILE_IP_HOST_PERF_MON_HIST_DATA`](#pon-service-config-profile-ip-host-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_LARGE_STRING`](#pon-service-config-profile-large-string)
  - [`PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PERF_MON_HIST_DATA`](#pon-service-config-profile-mac-bridge-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_CONFIGURATION_DATA`](#pon-service-config-profile-mac-bridge-port-configuration-data)
  - [`PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_PERF_MON_HIST_DATA`](#pon-service-config-profile-mac-bridge-port-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_SERVICE_PROFILE`](#pon-service-config-profile-mac-bridge-service-profile)
  - [`PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP`](#pon-service-config-profile-multicast-gem-interworking-tp)
  - [`PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV4_MULTICAST_ADDRESS_TABLE_IPV4_MULTICAST_ADDRESS_TABLE_ENTRY`](#pon-service-config-profile-multicast-gem-interworking-tp-ipv4-multicast-address-table-ipv4-multicast-address-table-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV6_MULTICAST_ADDRESS_TABLE_IPV6_MULTICAST_ADDRESS_TABLE_ENTRY`](#pon-service-config-profile-multicast-gem-interworking-tp-ipv6-multicast-address-table-ipv6-multicast-address-table-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_OLT_G`](#pon-service-config-profile-olt-g)
  - [`PON_SERVICE_CONFIG_PROFILE_ONU2_G`](#pon-service-config-profile-onu2-g)
  - [`PON_SERVICE_CONFIG_PROFILE_ONU_G`](#pon-service-config-profile-onu-g)
  - [`PON_SERVICE_CONFIG_PROFILE_ONU_OPERATIONAL_PERF_MON_HIST_DATA`](#pon-service-config-profile-onu-operational-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_PPTP_RS232_RS485_UNI`](#pon-service-config-profile-pptp-rs232-rs485-uni)
  - [`PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE`](#pon-service-config-profile-priority-queue)
  - [`PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_PACKET_DROP_QUEUE_THRESHOLD`](#pon-service-config-profile-priority-queue-packet-drop-queue-threshold)
  - [`PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PERF_MON_HIST_DATA`](#pon-service-config-profile-rs232-rs485-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PORT_OPER_CFG_DATA`](#pon-service-config-profile-rs232-rs485-port-oper-cfg-data)
  - [`PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_OPERATION`](#pon-service-config-profile-ssh-server-operation)
  - [`PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_PORT_DATA`](#pon-service-config-profile-ssh-server-port-data)
  - [`PON_SERVICE_CONFIG_PROFILE_TCONT`](#pon-service-config-profile-tcont)
  - [`PON_SERVICE_CONFIG_PROFILE_TCP_UDP_CONFIG_DATA`](#pon-service-config-profile-tcp-udp-config-data)
  - [`PON_SERVICE_CONFIG_PROFILE_TCP_UDP_PERF_MON_HIST_DATA`](#pon-service-config-profile-tcp-udp-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA64_BIT`](#pon-service-config-profile-threshold-data64-bit)
  - [`PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_ONE`](#pon-service-config-profile-threshold-data-one)
  - [`PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_TWO`](#pon-service-config-profile-threshold-data-two)
  - [`PON_SERVICE_CONFIG_PROFILE_TRAFFIC_DESCRIPTOR`](#pon-service-config-profile-traffic-descriptor)
  - [`PON_SERVICE_CONFIG_PROFILE_TRAFFIC_SCHEDULER`](#pon-service-config-profile-traffic-scheduler)
  - [`PON_SERVICE_CONFIG_PROFILE_VIRTUAL_ETHERNET_INTERFACE_PT`](#pon-service-config-profile-virtual-ethernet-interface-pt)
  - [`PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA`](#pon-service-config-profile-vlan-tagging-filter-data)
  - [`PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA_VLAN_FILTER_LIST_VLAN_FILTER_LIST_ENTRY`](#pon-service-config-profile-vlan-tagging-filter-data-vlan-filter-list-vlan-filter-list-entry)
  - [`PON_SERVICE_CONFIG_PROFILE_XG_PON_DOWNSTREAM_MGMT_PERF_MON_HIST_DATA`](#pon-service-config-profile-xg-pon-downstream-mgmt-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_XG_PON_TC_PERF_MON_HIST_DATA`](#pon-service-config-profile-xg-pon-tc-perf-mon-hist-data)
  - [`PON_SERVICE_CONFIG_PROFILE_XG_PON_UPSTREAM_MGMT_PERF_MON_HIST_DATA`](#pon-service-config-profile-xg-pon-upstream-mgmt-perf-mon-hist-data)
  - [`PON_SLA_PROFILE`](#pon-sla-profile)
  - [`PON_SLA_PROFILE_CONTROLLER`](#pon-sla-profile-controller)
- [STATE_DB](#state-db)
  - [`PON_CONTROLLER_ONU_FW_UPGRADE_STATE`](#pon-controller-onu-fw-upgrade-state)
  - [`PON_CONTROLLER_STATE`](#pon-controller-state)
  - [`PON_CONTROLLER_SYSTEM_STATUS_OLT`](#pon-controller-system-status-olt)
  - [`PON_CONTROLLER_SYSTEM_STATUS_OLT_ONU`](#pon-controller-system-status-olt-onu)
  - [`PON_FIRMWARE_FILENAME_STATE`](#pon-firmware-filename-state)
  - [`PON_OLT_INTF_NETWORK_STATE`](#pon-olt-intf-network-state)
  - [`PON_OLT_INTF_NNI_NETWORK_LEARNING_TABLE_STATE`](#pon-olt-intf-nni-network-learning-table-state)
  - [`PON_OLT_INTF_ONU_FW_UPGRADE_STATE`](#pon-olt-intf-onu-fw-upgrade-state)
  - [`PON_OLT_INTF_ONU_OPERATIONAL_STATE`](#pon-olt-intf-onu-operational-state)
  - [`PON_OLT_INTF_ONU_SERVICE_GEMPORT_STATE`](#pon-olt-intf-onu-service-gemport-state)
  - [`PON_OLT_INTF_ONU_SERVICE_TCONT_STATE`](#pon-olt-intf-onu-service-tcont-state)
  - [`PON_OLT_INTF_ONU_STATE`](#pon-olt-intf-onu-state)
  - [`PON_OLT_INTF_PROTECTION_UNDETECTED_ONU_STATE`](#pon-olt-intf-protection-undetected-onu-state)
  - [`PON_OLT_INTF_STATE`](#pon-olt-intf-state)
  - [`PON_OLT_PLUG_FW_BANK_VERSION_STATE`](#pon-olt-plug-fw-bank-version-state)
  - [`PON_OLT_PLUG_FW_UPGRADE_STATUS`](#pon-olt-plug-fw-upgrade-status)
  - [`PON_OLT_PLUG_STATE`](#pon-olt-plug-state)
  - [`PON_ONU_FW_BANK_VERSION_STATE`](#pon-onu-fw-bank-version-state)
  - [`PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_MAP_STATE`](#pon-onu-olt-service-downstream-qos-map-map-state)
  - [`PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE`](#pon-onu-olt-service-downstream-qos-map-state)
  - [`PON_ONU_OLT_SERVICE_NETWORK_STATE`](#pon-onu-olt-service-network-state)
  - [`PON_ONU_OLT_SERVICE_STATE`](#pon-onu-olt-service-state)
  - [`PON_ONU_STATE`](#pon-onu-state)
  - [`PON_ONU_UNI_LEARNED_ADDRESSES_STATE`](#pon-onu-uni-learned-addresses-state)
  - [`PON_ONU_UNI_STATE`](#pon-onu-uni-state)
- [COUNTERS_DB](#counters-db)
  - [`PON_OLT_INTF_STATISTICS_BINNED`](#pon-olt-intf-statistics-binned)
  - [`PON_OLT_PLUG_STATISTICS_BINNED_ENV`](#pon-olt-plug-statistics-binned-env)
  - [`PON_OLT_PLUG_STATISTICS_BINNED_NNI`](#pon-olt-plug-statistics-binned-nni)
  - [`PON_OLT_PLUG_STATISTICS_BINNED_TEMP`](#pon-olt-plug-statistics-binned-temp)
  - [`PON_OLT_STATISTICS_ACCUMULATING`](#pon-olt-statistics-accumulating)
  - [`PON_OLT_STATISTICS_ACCUMULATING_ENV`](#pon-olt-statistics-accumulating-env)
  - [`PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING`](#pon-olt-statistics-accumulating-pon-flooding)
  - [`PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_NNI_NETWORK`](#pon-olt-statistics-accumulating-pon-flooding-nni-network)
  - [`PON_OLT_STATISTICS_ACCUMULATING_TEMP`](#pon-olt-statistics-accumulating-temp)
  - [`PON_OLT_STATISTICS_BINNED_PON_FLOODING`](#pon-olt-statistics-binned-pon-flooding)
  - [`PON_OLT_STATISTICS_BINNED_PON_FLOODING_NETWORK`](#pon-olt-statistics-binned-pon-flooding-network)
  - [`PON_ONU_STATISTICS_ACCUMULATING_OLT_PON`](#pon-onu-statistics-accumulating-olt-pon)
  - [`PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_OMCC`](#pon-onu-statistics-accumulating-olt-pon-omcc)
  - [`PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_SERVICE`](#pon-onu-statistics-accumulating-olt-pon-service)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ENHANCED_TC_PM`](#pon-onu-statistics-accumulating-onu-enhanced-tc-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM`](#pon-onu-statistics-accumulating-onu-ethernet-frame-extended-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT`](#pon-onu-statistics-accumulating-onu-ethernet-frame-extended-pm-64bit)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`](#pon-onu-statistics-accumulating-onu-ethernet-frame-pm-downstream)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_UPSTREAM`](#pon-onu-statistics-accumulating-onu-ethernet-frame-pm-upstream)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM`](#pon-onu-statistics-accumulating-onu-ethernet-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM3`](#pon-onu-statistics-accumulating-onu-ethernet-pm3)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_FEC_PM`](#pon-onu-statistics-accumulating-onu-fec-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_GAL_ETHERNET_PM`](#pon-onu-statistics-accumulating-onu-gal-ethernet-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_GEM_PORT_NETWORK_CTP_PM`](#pon-onu-statistics-accumulating-onu-gem-port-network-ctp-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_IP_HOST_PERF_MON_HIST_DATA`](#pon-onu-statistics-accumulating-onu-ip-host-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_MAC_BRIDGE_PORT_PM`](#pon-onu-statistics-accumulating-onu-mac-bridge-port-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_OPERATIONAL_PM`](#pon-onu-statistics-accumulating-onu-operational-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_PON`](#pon-onu-statistics-accumulating-onu-pon)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_RS232_RS485_PERF_MON_HIST_DATA`](#pon-onu-statistics-accumulating-onu-rs232-rs485-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_TCP_UDP_PERF_MON_HIST_DATA`](#pon-onu-statistics-accumulating-onu-tcp-udp-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_DOWNSTREAM_MGMT_PM`](#pon-onu-statistics-accumulating-onu-xg-pon-downstream-mgmt-pm)
  - [`PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_UPSTREAM_MGMT_PM`](#pon-onu-statistics-accumulating-onu-xg-pon-upstream-mgmt-pm)
  - [`PON_ONU_STATISTICS_BINNED`](#pon-onu-statistics-binned)
  - [`PON_ONU_STATISTICS_BINNED_OLT_PON`](#pon-onu-statistics-binned-olt-pon)
  - [`PON_ONU_STATISTICS_BINNED_OLT_PON_OMCC`](#pon-onu-statistics-binned-olt-pon-omcc)
  - [`PON_ONU_STATISTICS_BINNED_OLT_PON_SERVICE`](#pon-onu-statistics-binned-olt-pon-service)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ENHANCED_TC_PM`](#pon-onu-statistics-binned-onu-enhanced-tc-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM`](#pon-onu-statistics-binned-onu-ethernet-frame-extended-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT`](#pon-onu-statistics-binned-onu-ethernet-frame-extended-pm-64bit)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`](#pon-onu-statistics-binned-onu-ethernet-frame-pm-downstream)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_UPSTREAM`](#pon-onu-statistics-binned-onu-ethernet-frame-pm-upstream)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM`](#pon-onu-statistics-binned-onu-ethernet-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM3`](#pon-onu-statistics-binned-onu-ethernet-pm3)
  - [`PON_ONU_STATISTICS_BINNED_ONU_FEC_PM`](#pon-onu-statistics-binned-onu-fec-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_GAL_ETHERNET_PM`](#pon-onu-statistics-binned-onu-gal-ethernet-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_GEM_PORT_NETWORK_CTP_PM`](#pon-onu-statistics-binned-onu-gem-port-network-ctp-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_IP_HOST_PERF_MON_HIST_DATA`](#pon-onu-statistics-binned-onu-ip-host-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_BINNED_ONU_MAC_BRIDGE_PORT_PM`](#pon-onu-statistics-binned-onu-mac-bridge-port-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_OPERATIONAL_PM`](#pon-onu-statistics-binned-onu-operational-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_PON`](#pon-onu-statistics-binned-onu-pon)
  - [`PON_ONU_STATISTICS_BINNED_ONU_RS232_RS485_PERF_MON_HIST_DATA`](#pon-onu-statistics-binned-onu-rs232-rs485-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_BINNED_ONU_TCP_UDP_PERF_MON_HIST_DATA`](#pon-onu-statistics-binned-onu-tcp-udp-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_BINNED_ONU_XG_PON_DOWNSTREAM_MGMT_PM`](#pon-onu-statistics-binned-onu-xg-pon-downstream-mgmt-pm)
  - [`PON_ONU_STATISTICS_BINNED_ONU_XG_PON_UPSTREAM_MGMT_PM`](#pon-onu-statistics-binned-onu-xg-pon-upstream-mgmt-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_ENHANCED_TC_PM`](#pon-onu-statistics-streaming-onu-enhanced-tc-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`](#pon-onu-statistics-streaming-onu-ethernet-frame-pm-downstream)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_UPSTREAM`](#pon-onu-statistics-streaming-onu-ethernet-frame-pm-upstream)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_PM`](#pon-onu-statistics-streaming-onu-ethernet-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_FEC_PM`](#pon-onu-statistics-streaming-onu-fec-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_GAL_ETHERNET_PM`](#pon-onu-statistics-streaming-onu-gal-ethernet-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_GEM_PORT_NETWORK_CTP_PM`](#pon-onu-statistics-streaming-onu-gem-port-network-ctp-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_RS232_RS485_PERF_MON_HIST_DATA`](#pon-onu-statistics-streaming-onu-rs232-rs485-perf-mon-hist-data)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_DOWNSTREAM_MGMT_PM`](#pon-onu-statistics-streaming-onu-xg-pon-downstream-mgmt-pm)
  - [`PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_UPSTREAM_MGMT_PM`](#pon-onu-statistics-streaming-onu-xg-pon-upstream-mgmt-pm)

## Summary

- CONFIG_DB tables: **85**
- STATE_DB tables: **25**
- COUNTERS_DB tables: **64**

## YANG Model

```
module: sonic-pon
  +--rw sonic-pon
     +--rw PON_CONTROLLER
     |  +--rw PON_CONTROLLER_LIST* [controller-name]
     |     +--rw controller-name                  string
     |     +--rw device-id                        string
     |     +--rw allow-unprovisioned-onus?        boolean
     |     +--rw create-date?                     yang:date-and-time
     |     +--rw olt-timeout?                     uint32
     |     +--rw statistics-sample?               uint32
     |     +--rw logging-controller-console?      spt:logging-level
     |     +--rw logging-controller-file?         spt:logging-level
     |     +--rw logging-controller-syslog?       spt:logging-level
     |     +--rw logging-controller-database?     spt:logging-level
     |     +--rw logging-olt-console?             spt:logging-enable
     |     +--rw logging-olt-file?                spt:logging-enable
     |     +--rw logging-olt-syslog?              spt:logging-enable
     |     +--rw olt-management-interface-name?   string
     |     +--rw unprovisioned-age?               uint32
     |     +--rw refresh-state-on-olt-change?     boolean
     +--rw PON_DOWNSTREAM_QOS_MAP_MAP
     |  +--rw PON_DOWNSTREAM_QOS_MAP_MAP_LIST* [name cos]
     |     +--rw name                  string
     |     +--rw cos                   uint8
     |     +--rw olt-service-offset?   uint8
     +--rw PON_OLT_INTF
     |  +--rw PON_OLT_INTF_LIST* [olt-name port-id]
     |     +--rw olt-name                              string
     |     +--rw device-id?                            string
     |     +--rw port-id                               -> /sport:sonic-port/PORT/PORT_LIST/name
     |     +--rw pon-enable?                           boolean
     |     +--rw discovery-period?                     uint32
     |     +--rw downstream-fec?                       boolean
     |     +--rw encryption?                           spt:olt-encryption-mode
     |     +--rw encryption-key-time?                  uint16
     |     +--rw error-detection-maximum-hec-ratio?    uint8
     |     +--rw error-detection-minimum-hec-sample?   uint16
     |     +--rw error-detection-maximum-ratio?        uint8
     |     +--rw error-detection-minimum-sample?       uint16
     |     +--rw guard-time?                           uint32
     |     +--rw max-frame-size?                       uint32
     |     +--rw pon-id?                               uint32
     |     +--rw pon-tag?                              string
     |     +--rw aging-time?                           uint16
     +--rw PON_OLT_INTF_NETWORK
     |  +--rw PON_OLT_INTF_NETWORK_LIST* [olt-name vlan-id]
     |     +--rw olt-name                -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw network-id?             uint16
     |     +--rw learning-limit?         uint16
     |     +--rw flooding-gemport-id?    uint16
     |     +--rw vlan-id                 uint16
     |     +--rw flooding-sla-profile?   string
     +--rw PON_OLT_INTF_ONU
     |  +--rw PON_OLT_INTF_ONU_LIST* [olt-name onu-serial-number]
     |     +--rw olt-name             -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw onu-serial-number    string
     |     +--rw onu-id?              uint16
     |     +--rw disable?             boolean
     +--rw PON_OLT_INTF_ONU_OLT_SERVICE
     |  +--rw PON_OLT_INTF_ONU_OLT_SERVICE_LIST* [olt-name onu-serial-number service-port-id]
     |     +--rw olt-name             -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw onu-serial-number    -> /sonic-pon/PON_OLT_INTF_ONU/PON_OLT_INTF_ONU_LIST/onu-serial-number
     |     +--rw service-port-id      uint32
     |     +--rw unicast-id?          uint16
     +--rw PON_OLT_INTF_ONU_SERVICE_TCONT
     |  +--rw PON_OLT_INTF_ONU_SERVICE_TCONT_LIST* [olt-name onu-serial-number olt-service-id]
     |     +--rw olt-name             -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw onu-serial-number    -> /sonic-pon/PON_OLT_INTF_ONU/PON_OLT_INTF_ONU_LIST/onu-serial-number
     |     +--rw olt-service-id       uint32
     |     +--rw alloc-id?            uint16
     +--rw PON_OLT_INTF_ONU_SERVICE_GEMPORT
     |  +--rw PON_OLT_INTF_ONU_SERVICE_GEMPORT_LIST* [olt-name onu-serial-number olt-service-id]
     |     +--rw olt-name             -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw onu-serial-number    -> /sonic-pon/PON_OLT_INTF_ONU/PON_OLT_INTF_ONU_LIST/onu-serial-number
     |     +--rw olt-service-id       uint32
     |     +--rw gemport-id?          uint16
     |     +--rw tcont-ref?           -> /sonic-pon/PON_OLT_INTF_ONU_SERVICE_TCONT/PON_OLT_INTF_ONU_SERVICE_TCONT_LIST/olt-service-id
     +--rw PON_OLT_PLUG_FW_BANK_FILE
     |  +--rw PON_OLT_PLUG_FW_BANK_FILE_LIST* [olt-name bank-id]
     |     +--rw olt-name    -> /sonic-pon/PON_OLT_PLUG/PON_OLT_PLUG_LIST/olt-name
     |     +--rw bank-id     uint8
     |     +--rw file?       string
     |     +--rw version?    string
     +--rw PON_ONU_TEMPLATE_ONU
     |  +--rw PON_ONU_TEMPLATE_ONU_LIST* [onu-template-name]
     |     +--rw onu-template-name                  string
     |     +--rw vlan-id?                           uint16
     |     +--rw fw-bank-ptr?                       uint16
     |     +--rw service-config?                    string
     |     +--rw service-config-omci-stats?         boolean
     |     +--rw fw-upgrade-backoff-delay?          uint32
     |     +--rw fw-upgrade-backoff-divisor?        uint32
     |     +--rw fw-upgrade-download-format?        spt:fw-download-format
     |     +--rw fw-upgrade-end-download-timeout?   uint32
     |     +--rw fw-upgrade-maximum-retries?        uint32
     |     +--rw fw-upgrade-maximum-window-size?    uint32
     |     +--rw fw-upgrade-response-timeout?       uint32
     +--rw PON_ONU_TEMPLATE_ONU_FW_BANK_FILE
     |  +--rw PON_ONU_TEMPLATE_ONU_FW_BANK_FILE_LIST* [onu-template-name bank-id]
     |     +--rw onu-template-name    -> /sonic-pon/PON_ONU_TEMPLATE_ONU/PON_ONU_TEMPLATE_ONU_LIST/onu-template-name
     |     +--rw bank-id              uint8
     |     +--rw file?                string
     |     +--rw version?             string
     +--rw PON_ONU_TEMPLATE_OLT_SERVICE
     |  +--rw PON_ONU_TEMPLATE_OLT_SERVICE_LIST* [onu-template-name olt-service-id]
     |     +--rw onu-template-name     string
     |     +--rw olt-service-id        uint32
     |     +--rw downstream-qos-map?   string
     |     +--rw enable?               boolean
     |     +--rw learning-limit?       uint16
     |     +--rw sla-profile?          string
     |     +--rw tcont-service-ref?    string
     +--rw PON_ONU_TEMPLATE_OLT_SERVICE_NETWORK
     |  +--rw PON_ONU_TEMPLATE_OLT_SERVICE_NETWORK_LIST* [onu-template-name olt-service-id vlan-id]
     |     +--rw onu-template-name    string
     |     +--rw olt-service-id       -> /sonic-pon/PON_ONU_TEMPLATE_OLT_SERVICE/PON_ONU_TEMPLATE_OLT_SERVICE_LIST/olt-service-id
     |     +--rw network-id?          uint16
     |     +--rw vlan-id              uint16
     +--rw PON_ONU_TEMPLATE_SERVICE_CONFIG_VALUE
     |  +--rw PON_ONU_TEMPLATE_SERVICE_CONFIG_VALUE_LIST* [onu-template-name cfg-name]
     |     +--rw onu-template-name    string
     |     +--rw cfg-name             spt:pon-string64nz
     |     +--rw value                union
     |     +--rw value-type?          spt:service-config-value-type
     +--rw PON_ONU_TEMPLATE_UNI
     |  +--rw PON_ONU_TEMPLATE_UNI_LIST* [onu-template-name port-id]
     |     +--rw onu-template-name    string
     |     +--rw port-id              string
     |     +--rw duplex?              spt:duplex-mode
     |     +--rw enable?              boolean
     |     +--rw max-frame-size?      uint32
     |     +--rw poe?                 boolean
     |     +--rw speed?               spt:speed-mode
     +--rw PON_ONU
     |  +--rw PON_ONU_LIST* [onu-name]
     |     +--rw onu-name                           string
     |     +--rw device-id                          string
     |     +--rw template-ref?                      string
     |     +--rw vlan-id?                           uint16
     |     +--rw fw-bank-ptr?                       uint16
     |     +--rw realtime-stats?                    boolean
     |     +--rw service-config?                    string
     |     +--rw service-config-omci-stats?         boolean
     |     +--rw fw-upgrade-backoff-delay?          uint32
     |     +--rw fw-upgrade-backoff-divisor?        uint32
     |     +--rw fw-upgrade-download-format?        spt:fw-download-format
     |     +--rw fw-upgrade-end-download-timeout?   uint32
     |     +--rw fw-upgrade-maximum-retries?        uint32
     |     +--rw fw-upgrade-maximum-window-size?    uint32
     |     +--rw fw-upgrade-response-timeout?       uint32
     +--rw PON_ONU_OLT_SERVICE
     |  +--rw PON_ONU_OLT_SERVICE_LIST* [onu-name olt-service-id]
     |     +--rw onu-name              -> /sonic-pon/PON_ONU/PON_ONU_LIST/onu-name
     |     +--rw olt-service-id        uint32
     |     +--rw downstream-qos-map?   string
     |     +--rw enable?               boolean
     |     +--rw learning-limit?       uint16
     |     +--rw sla-profile?          string
     |     +--rw tcont-service-ref?    string
     +--rw PON_ONU_OLT_SERVICE_NETWORK
     |  +--rw PON_ONU_OLT_SERVICE_NETWORK_LIST* [onu-name olt-service-id vlan-id]
     |     +--rw onu-name          -> /sonic-pon/PON_ONU/PON_ONU_LIST/onu-name
     |     +--rw olt-service-id    -> /sonic-pon/PON_ONU_OLT_SERVICE/PON_ONU_OLT_SERVICE_LIST/olt-service-id
     |     +--rw network-id?       uint16
     |     +--rw vlan-id           uint16
     +--rw PON_ONU_SERVICE_CONFIG_VALUE
     |  +--rw PON_ONU_SERVICE_CONFIG_VALUE_LIST* [onu-name cfg-name]
     |     +--rw onu-name      -> /sonic-pon/PON_ONU/PON_ONU_LIST/onu-name
     |     +--rw cfg-name      spt:pon-string64nz
     |     +--rw value         union
     |     +--rw value-type?   spt:service-config-value-type
     +--rw PON_ONU_UNI
     |  +--rw PON_ONU_UNI_LIST* [onu-name port-id]
     |     +--rw onu-name          -> /sonic-pon/PON_ONU/PON_ONU_LIST/onu-name
     |     +--rw port-id           string
     |     +--rw duplex?           spt:duplex-mode
     |     +--rw enable?           boolean
     |     +--rw max-frame-size?   uint32
     |     +--rw poe?              boolean
     |     +--rw speed?            spt:speed-mode
     +--rw PON_ONU_FW_BANK_FILE
     |  +--rw PON_ONU_FW_BANK_FILE_LIST* [onu-name bank-id]
     |     +--rw onu-name    -> /sonic-pon/PON_ONU/PON_ONU_LIST/onu-name
     |     +--rw bank-id     uint8
     |     +--rw file?       string
     |     +--rw version?    string
     +--rw PON_SERVICE_CONFIG_PROFILE_HEADER
     |  +--rw PON_SERVICE_CONFIG_PROFILE_HEADER_LIST* [name]
     |     +--rw name       string
     |     +--rw title?     string
     |     +--rw version?   string
     +--rw PON_SERVICE_CONFIG_PROFILE_HEADER_COMPATIBILITY_VENDOR_MODEL
     |  +--rw PON_SERVICE_CONFIG_PROFILE_HEADER_COMPATIBILITY_VENDOR_MODEL_LIST* [vendor-id name]
     |     +--rw vendor-id    string
     |     +--rw name         -> /sonic-pon/PON_SERVICE_CONFIG_PROFILE_HEADER/PON_SERVICE_CONFIG_PROFILE_HEADER_LIST/name
     |     +--rw model*       string
     +--rw PON_SERVICE_CONFIG_PROFILE_HEADER_INPUTS_EXT_INPUT
     |  +--rw PON_SERVICE_CONFIG_PROFILE_HEADER_INPUTS_EXT_INPUT_LIST* [name db-ref]
     |     +--rw name      -> /sonic-pon/PON_SERVICE_CONFIG_PROFILE_HEADER/PON_SERVICE_CONFIG_PROFILE_HEADER_LIST/name
     |     +--rw db-ref    omci-types:omci-db-ref
     |     +--rw type?     omci-types:header-input-type
     +--rw PON_SERVICE_CONFIG_PROFILE_ANI_G
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ANI_G_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name       string
     |     +--rw managed-entity-id                 omci-types:omci-uint16
     |     +--rw gem-block-length?                 omci-types:omci-uint16
     |     +--rw sf-threshold?                     omci-types:omci-uint8
     |     +--rw sd-threshold?                     omci-types:omci-uint8
     |     +--rw arc?                              omci-types:omci-uint8
     |     +--rw arc-interval?                     omci-types:omci-uint8
     |     +--rw lower-optical-threshold?          omci-types:omci-uint8
     |     +--rw upper-optical-threshold?          omci-types:omci-uint8
     |     +--rw lower-transmit-power-threshold?   omci-types:omci-uint8
     |     +--rw upper-transmit-power-threshold?   omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_CARDHOLDER
     |  +--rw PON_SERVICE_CONFIG_PROFILE_CARDHOLDER_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw expected-plugin-unit-type?     omci-types:omci-uint8
     |     +--rw expected-port-count?           omci-types:omci-uint8
     |     +--rw expected-equipment-id?         omci-types:omci-string
     |     +--rw invoke-protection-switch?      omci-types:omci-uint8
     |     +--rw arc?                           omci-types:omci-uint8
     |     +--rw arc-interval?                  omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_CIRCUIT_PACK
     |  +--rw PON_SERVICE_CONFIG_PROFILE_CIRCUIT_PACK_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw administrative-state?          omci-types:omci-uint8
     |     +--rw bridged-or-ip-ind?             omci-types:omci-uint8
     |     +--rw card-configuration?            omci-types:omci-uint8
     |     +--rw power-sched-override?          omci-types:omci-uint32
     +--rw PON_SERVICE_CONFIG_PROFILE_ENHANCED_FEC_PM_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ENHANCED_FEC_PM_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-64-bit-id?      omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ENHANCED_TC_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ENHANCED_TC_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-64-bit-id?      omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-id?             omci-types:omci-uint16
     |     +--rw parent-me-class?               omci-types:omci-uint16
     |     +--rw parent-me-instance?            omci-types:omci-uint16
     |     +--rw accumulation-disable?          omci-types:omci-uint16
     |     +--rw tca-disable?                   omci-types:omci-uint16
     |     +--rw control-fields?                omci-types:omci-uint16
     |     +--rw tci?                           omci-types:omci-uint16
     |     +--rw reserved?                      omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM64_BIT
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM64_BIT_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-id?             omci-types:omci-uint16
     |     +--rw parent-me-class?               omci-types:omci-uint16
     |     +--rw parent-me-instance?            omci-types:omci-uint16
     |     +--rw accumulation-disable?          omci-types:omci-uint16
     |     +--rw tca-disable?                   omci-types:omci-uint16
     |     +--rw control-fields?                omci-types:omci-uint16
     |     +--rw tci?                           omci-types:omci-uint16
     |     +--rw reserved?                      omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_DOWNSTREAM
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_DOWNSTREAM_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_UPSTREAM
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_UPSTREAM_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA3
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA3_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw association-type?              omci-types:omci-uint8
     |     +--rw input-tpid?                    omci-types:omci-uint16
     |     +--rw output-tpid?                   omci-types:omci-uint16
     |     +--rw downstream-mode?               omci-types:omci-uint8
     |     +--rw associated-me-pointer?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_ENTRY_LIST* [service-config-profile-name id managed-entity-id received-frame-vlan-tagging-operation-table-entry-id]
     |     +--rw service-config-profile-name                             string
     |     +--rw id                                                      string
     |     +--rw managed-entity-id                                       omci-types:omci-uint16
     |     +--rw received-frame-vlan-tagging-operation-table-entry-id    uint8
     |     +--rw filter-outer-priority?                                  omci-types:omci-uint16
     |     +--rw filter-outer-vid?                                       omci-types:omci-uint16
     |     +--rw filter-outer-tpid-de?                                   omci-types:omci-uint16
     |     +--rw pad1?                                                   omci-types:omci-uint16
     |     +--rw filter-inner-priority?                                  omci-types:omci-uint16
     |     +--rw filter-inner-vid?                                       omci-types:omci-uint16
     |     +--rw filter-inner-tpid-de?                                   omci-types:omci-uint16
     |     +--rw pad2?                                                   omci-types:omci-uint16
     |     +--rw filter-ether-type?                                      omci-types:omci-uint16
     |     +--rw treatment-tags-to-remove?                               omci-types:omci-uint16
     |     +--rw pad3?                                                   omci-types:omci-uint16
     |     +--rw treatment-outer-priority?                               omci-types:omci-uint16
     |     +--rw treatment-outer-vid?                                    omci-types:omci-uint16
     |     +--rw treatment-outer-tpid-de?                                omci-types:omci-uint16
     |     +--rw pad4?                                                   omci-types:omci-uint16
     |     +--rw treatment-inner-priority?                               omci-types:omci-uint16
     |     +--rw treatment-inner-vid?                                    omci-types:omci-uint16
     |     +--rw treatment-inner-tpid-de?                                omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_DSCP_TO_PBIT_MAPPING_DSCP_TO_PBIT_MAPPING_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_DSCP_TO_PBIT_MAPPING_DSCP_TO_PBIT_MAPPING_ENTRY_LIST* [service-config-profile-name id managed-entity-id dscp]
     |     +--rw service-config-profile-name    string
     |     +--rw id                             string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw dscp                           uint8
     |     +--rw priority?                      uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_FEC_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_FEC_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PROFILE
     |  +--rw PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PROFILE_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw max-gem-payload-size?          omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_GEM_INTERWORKING_TP
     |  +--rw PON_SERVICE_CONFIG_PROFILE_GEM_INTERWORKING_TP_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name     string
     |     +--rw managed-entity-id               omci-types:omci-uint16
     |     +--rw gem-port-network-ctp-pointer?   omci-types:omci-uint16
     |     +--rw interworking-option?            omci-types:omci-uint8
     |     +--rw service-profile-pointer?        omci-types:omci-uint16
     |     +--rw interworking-tp-pointer?        omci-types:omci-uint16
     |     +--rw gal-profile-pointer?            omci-types:omci-uint16
     |     +--rw gal-loopback-configuration?     omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP
     |  +--rw PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name                string
     |     +--rw managed-entity-id                          omci-types:omci-uint16
     |     +--rw port-id?                                   omci-types:omci-uint16
     |     +--rw tcont-pointer?                             omci-types:omci-uint16
     |     +--rw direction?                                 omci-types:omci-uint8
     |     +--rw traffic-management-pointer-upstream?       omci-types:omci-uint16
     |     +--rw traffic-descriptor-profile-pointer?        omci-types:omci-uint16
     |     +--rw priority-queue-pointer-downstream?         omci-types:omci-uint16
     |     +--rw traffic-desc-profile-pointer-downstream?   omci-types:omci-uint16
     |     +--rw encryption-key-ring?                       omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE
     |  +--rw PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name                  string
     |     +--rw managed-entity-id                            omci-types:omci-uint16
     |     +--rw tp-pointer?                                  omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-0?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-1?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-2?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-3?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-4?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-5?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-6?   omci-types:omci-uint16
     |     +--rw interwork-tp-pointer-for-p-bit-priority-7?   omci-types:omci-uint16
     |     +--rw unmarked-frame-option?                       omci-types:omci-uint8
     |     +--rw default-p-bit-assumption?                    omci-types:omci-uint8
     |     +--rw tp-type?                                     omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE_DSCP_TO_P_BIT_MAPPING_DSCP_TO_P_BIT_MAPPING_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE_DSCP_TO_P_BIT_MAPPING_DSCP_TO_P_BIT_MAPPING_ENTRY_LIST* [service-config-profile-name id managed-entity-id dscp]
     |     +--rw service-config-profile-name    string
     |     +--rw id                             string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw dscp                           omci-types:omci-uint8
     |     +--rw priority?                      omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_IP_HOST_CONFIG_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_IP_HOST_CONFIG_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw ip-options?                    omci-types:omci-uint8
     |     +--rw onu-identifier?                omci-types:omci-string
     |     +--rw ip-address?                    omci-types:omci-ipv4-address
     |     +--rw mask?                          omci-types:omci-ipv4-address
     |     +--rw gateway?                       omci-types:omci-ipv4-address
     |     +--rw primary-dns?                   omci-types:omci-ipv4-address
     |     +--rw secondary-dns?                 omci-types:omci-ipv4-address
     |     +--rw relay-agent-options?           omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_IP_HOST_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_IP_HOST_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_IPV6_HOST_CONFIG_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_IPV6_HOST_CONFIG_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw ip-options?                    omci-types:omci-uint8
     |     +--rw onu-identifier?                omci-types:omci-string
     |     +--rw ipv6-address?                  omci-types:omci-ipv6-address
     |     +--rw default-router?                omci-types:omci-ipv6-address
     |     +--rw primary-dns?                   omci-types:omci-ipv6-address
     |     +--rw secondary-dns?                 omci-types:omci-ipv6-address
     |     +--rw on-link-prefix?                omci-types:omci-string
     |     +--rw relay-agent-options?           omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_LARGE_STRING
     |  +--rw PON_SERVICE_CONFIG_PROFILE_LARGE_STRING_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw number-of-parts?               omci-types:omci-uint8
     |     +--rw part-1?                        omci-types:omci-string
     |     +--rw part-2?                        omci-types:omci-string
     |     +--rw part-3?                        omci-types:omci-string
     |     +--rw part-4?                        omci-types:omci-string
     |     +--rw part-5?                        omci-types:omci-string
     |     +--rw part-6?                        omci-types:omci-string
     |     +--rw part-7?                        omci-types:omci-string
     |     +--rw part-8?                        omci-types:omci-string
     |     +--rw part-9?                        omci-types:omci-string
     |     +--rw part-10?                       omci-types:omci-string
     |     +--rw part-11?                       omci-types:omci-string
     |     +--rw part-12?                       omci-types:omci-string
     |     +--rw part-13?                       omci-types:omci-string
     |     +--rw part-14?                       omci-types:omci-string
     |     +--rw part-15?                       omci-types:omci-string
     +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_CONFIGURATION_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_CONFIGURATION_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw bridge-id-pointer?             omci-types:omci-uint16
     |     +--rw port-num?                      omci-types:omci-uint8
     |     +--rw tp-type?                       omci-types:omci-uint8
     |     +--rw tp-pointer?                    omci-types:omci-uint16
     |     +--rw port-priority?                 omci-types:omci-uint16
     |     +--rw port-path-cost?                omci-types:omci-uint16
     |     +--rw port-spanning-tree-ind?        omci-types:omci-uint8
     |     +--rw deprecated1?                   omci-types:omci-uint8
     |     +--rw deprecated2?                   omci-types:omci-uint8
     |     +--rw outbound-td-pointer?           omci-types:omci-uint16
     |     +--rw inbound-td-pointer?            omci-types:omci-uint16
     |     +--rw mac-learning-depth?            omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_SERVICE_PROFILE
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_SERVICE_PROFILE_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name      string
     |     +--rw managed-entity-id                omci-types:omci-uint16
     |     +--rw spanning-tree-ind?               omci-types:omci-uint8
     |     +--rw learning-ind?                    omci-types:omci-uint8
     |     +--rw port-bridging-ind?               omci-types:omci-uint8
     |     +--rw priority?                        omci-types:omci-uint16
     |     +--rw max-age?                         omci-types:omci-uint16
     |     +--rw hello-time?                      omci-types:omci-uint16
     |     +--rw forward-delay?                   omci-types:omci-uint16
     |     +--rw unknown-mac-address-discard?     omci-types:omci-uint8
     |     +--rw mac-learning-depth?              omci-types:omci-uint8
     |     +--rw dynamic-filtering-ageing-time?   omci-types:omci-uint32
     +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name     string
     |     +--rw managed-entity-id               omci-types:omci-uint16
     |     +--rw gem-port-network-ctp-pointer?   omci-types:omci-uint16
     |     +--rw interworking-option?            omci-types:omci-uint8
     |     +--rw service-profile-pointer?        omci-types:omci-uint16
     |     +--rw interworking-tp-pointer?        omci-types:omci-uint16
     |     +--rw gal-profile-pointer?            omci-types:omci-uint16
     |     +--rw gal-loopback-configuration?     omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV4_MULTICAST_ADDRESS_TABLE_IPV4_MULTICAST_ADDRESS_TABLE_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV4_MULTICAST_ADDRESS_TABLE_IPV4_MULTICAST_ADDRESS_TABLE_ENTRY_LIST* [service-config-profile-name id managed-entity-id ipv4-multicast-address-table-entry-id]
     |     +--rw service-config-profile-name              string
     |     +--rw id                                       string
     |     +--rw managed-entity-id                        omci-types:omci-uint16
     |     +--rw ipv4-multicast-address-table-entry-id    uint8
     |     +--rw gem-port-id?                             omci-types:omci-uint16
     |     +--rw secondary-key?                           omci-types:omci-uint16
     |     +--rw ip-multicast-da-range-start?             omci-types:omci-ipv4-address
     |     +--rw ip-multicast-da-range-stop?              omci-types:omci-ipv4-address
     +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV6_MULTICAST_ADDRESS_TABLE_IPV6_MULTICAST_ADDRESS_TABLE_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV6_MULTICAST_ADDRESS_TABLE_IPV6_MULTICAST_ADDRESS_TABLE_ENTRY_LIST* [service-config-profile-name id managed-entity-id ipv6-multicast-address-table-entry-id]
     |     +--rw service-config-profile-name              string
     |     +--rw id                                       string
     |     +--rw managed-entity-id                        omci-types:omci-uint16
     |     +--rw ipv6-multicast-address-table-entry-id    uint8
     |     +--rw gem-port-id?                             omci-types:omci-uint16
     |     +--rw secondary-key?                           omci-types:omci-uint16
     |     +--rw lsb-ip-multicast-da-range-start?         omci-types:omci-string
     |     +--rw lsb-ip-multicast-da-range-stop?          omci-types:omci-string
     |     +--rw msb-ip-multicast-da?                     omci-types:omci-string
     +--rw PON_SERVICE_CONFIG_PROFILE_OLT_G
     |  +--rw PON_SERVICE_CONFIG_PROFILE_OLT_G_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw olt-vendor-id?                 omci-types:omci-string
     |     +--rw equipment-id?                  omci-types:omci-string
     |     +--rw version?                       omci-types:omci-string
     |     +--rw time-of-day?                   omci-types:omci-string
     +--rw PON_SERVICE_CONFIG_PROFILE_ONU2_G
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ONU2_G_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw security-mode?                 omci-types:omci-uint8
     |     +--rw current-connectivity-mode?     omci-types:omci-uint8
     |     +--rw priority-queue-scale-factor?   omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_ONU_G
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ONU_G_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw battery-backup?                omci-types:omci-uint8
     |     +--rw administrative-state?          omci-types:omci-uint8
     |     +--rw credentials-status?            omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_ONU_OPERATIONAL_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_ONU_OPERATIONAL_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_PPTP_RS232_RS485_UNI
     |  +--rw PON_SERVICE_CONFIG_PROFILE_PPTP_RS232_RS485_UNI_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw administrative-state?          omci-types:omci-uint8
     |     +--rw port-mode?                     omci-types:omci-uint8
     |     +--rw baud-rate?                     omci-types:omci-uint8
     |     +--rw data-bits?                     omci-types:omci-uint8
     |     +--rw parity?                        omci-types:omci-uint8
     |     +--rw stop-bits?                     omci-types:omci-uint8
     |     +--rw flow-control?                  omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE
     |  +--rw PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name             string
     |     +--rw managed-entity-id                       omci-types:omci-uint16
     |     +--rw allocated-queue-size?                   omci-types:omci-uint16
     |     +--rw discard-block-counter-reset-interval?   omci-types:omci-uint16
     |     +--rw threshold-value-for-discarded-blocks?   omci-types:omci-uint16
     |     +--rw related-port?                           omci-types:omci-uint32
     |     +--rw traffic-scheduler-pointer?              omci-types:omci-uint16
     |     +--rw weight?                                 omci-types:omci-uint8
     |     +--rw back-pressure-operation?                omci-types:omci-uint16
     |     +--rw back-pressure-time?                     omci-types:omci-uint32
     |     +--rw back-pressure-occur-queue-threshold?    omci-types:omci-uint16
     |     +--rw back-pressure-clear-queue-threshold?    omci-types:omci-uint16
     |     +--rw packet-drop-max-p?                      omci-types:omci-uint16
     |     +--rw queue-drop-w-q?                         omci-types:omci-uint8
     |     +--rw drop-precedence-colour-marking?         omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_PACKET_DROP_QUEUE_THRESHOLD
     |  +--rw PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_PACKET_DROP_QUEUE_THRESHOLD_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              -> /sonic-pon/PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE/PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_LIST/managed-entity-id
     |     +--rw min-green?                     omci-types:omci-uint16
     |     +--rw max-green?                     omci-types:omci-uint16
     |     +--rw min-yellow?                    omci-types:omci-uint16
     |     +--rw max-yellow?                    omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PORT_OPER_CFG_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PORT_OPER_CFG_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw tcp-udp-ptr?                   omci-types:omci-uint16
     |     +--rw pptp-ptr?                      omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_OPERATION
     |  +--rw PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_OPERATION_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw server-action?                 omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_PORT_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_PORT_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw tcp-udp-ptr?                   omci-types:omci-uint16
     |     +--rw ssh-server-ptr?                omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_TCONT
     |  +--rw PON_SERVICE_CONFIG_PROFILE_TCONT_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw alloc-id?                      omci-types:omci-uint16
     |     +--rw policy?                        omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_TCP_UDP_CONFIG_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_TCP_UDP_CONFIG_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw port-id?                       omci-types:omci-uint16
     |     +--rw protocol?                      omci-types:omci-uint8
     |     +--rw tos-diffserv-field?            omci-types:omci-uint8
     |     +--rw ip-host-ptr?                   omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_TCP_UDP_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_TCP_UDP_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA64_BIT
     |  +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA64_BIT_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-value-1?             omci-types:omci-uint64
     |     +--rw threshold-value-2?             omci-types:omci-uint64
     |     +--rw threshold-value-3?             omci-types:omci-uint64
     |     +--rw threshold-value-4?             omci-types:omci-uint64
     |     +--rw threshold-value-5?             omci-types:omci-uint64
     |     +--rw threshold-value-6?             omci-types:omci-uint64
     |     +--rw threshold-value-7?             omci-types:omci-uint64
     |     +--rw threshold-value-8?             omci-types:omci-uint64
     |     +--rw threshold-value-9?             omci-types:omci-uint64
     |     +--rw threshold-value-10?            omci-types:omci-uint64
     |     +--rw threshold-value-11?            omci-types:omci-uint64
     |     +--rw threshold-value-12?            omci-types:omci-uint64
     |     +--rw threshold-value-13?            omci-types:omci-uint64
     |     +--rw threshold-value-14?            omci-types:omci-uint64
     +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_ONE
     |  +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_ONE_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-value-1?             omci-types:omci-uint32
     |     +--rw threshold-value-2?             omci-types:omci-uint32
     |     +--rw threshold-value-3?             omci-types:omci-uint32
     |     +--rw threshold-value-4?             omci-types:omci-uint32
     |     +--rw threshold-value-5?             omci-types:omci-uint32
     |     +--rw threshold-value-6?             omci-types:omci-uint32
     |     +--rw threshold-value-7?             omci-types:omci-uint32
     +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_TWO
     |  +--rw PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_TWO_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-value-8?             omci-types:omci-uint32
     |     +--rw threshold-value-9?             omci-types:omci-uint32
     |     +--rw threshold-value-10?            omci-types:omci-uint32
     |     +--rw threshold-value-11?            omci-types:omci-uint32
     |     +--rw threshold-value-12?            omci-types:omci-uint32
     |     +--rw threshold-value-13?            omci-types:omci-uint32
     |     +--rw threshold-value-14?            omci-types:omci-uint32
     +--rw PON_SERVICE_CONFIG_PROFILE_TRAFFIC_DESCRIPTOR
     |  +--rw PON_SERVICE_CONFIG_PROFILE_TRAFFIC_DESCRIPTOR_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw cir?                           omci-types:omci-uint32
     |     +--rw pir?                           omci-types:omci-uint32
     |     +--rw cbs?                           omci-types:omci-uint32
     |     +--rw pbs?                           omci-types:omci-uint32
     |     +--rw colour-mode?                   omci-types:omci-uint8
     |     +--rw ingress-colour-marking?        omci-types:omci-uint8
     |     +--rw egress-colour-marking?         omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_TRAFFIC_SCHEDULER
     |  +--rw PON_SERVICE_CONFIG_PROFILE_TRAFFIC_SCHEDULER_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw tcont-pointer?                 omci-types:omci-uint16
     |     +--rw policy?                        omci-types:omci-uint8
     |     +--rw priority-weight?               omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_VIRTUAL_ETHERNET_INTERFACE_PT
     |  +--rw PON_SERVICE_CONFIG_PROFILE_VIRTUAL_ETHERNET_INTERFACE_PT_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name                string
     |     +--rw managed-entity-id                          omci-types:omci-uint16
     |     +--rw administrative-state?                      omci-types:omci-uint8
     |     +--rw interdomain-service-config-profile-name?   omci-types:omci-string
     |     +--rw tcp-udp-pointer?                           omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw forward-operation?             omci-types:omci-uint8
     |     +--rw number-of-entries?             omci-types:omci-uint8
     +--rw PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA_VLAN_FILTER_LIST_VLAN_FILTER_LIST_ENTRY
     |  +--rw PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA_VLAN_FILTER_LIST_VLAN_FILTER_LIST_ENTRY_LIST* [service-config-profile-name id managed-entity-id vlan-filter-entry-id]
     |     +--rw service-config-profile-name    string
     |     +--rw id                             string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw vlan-filter-entry-id           uint8
     |     +--rw vlan-id?                       omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_DOWNSTREAM_MGMT_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_DOWNSTREAM_MGMT_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_TC_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_TC_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_UPSTREAM_MGMT_PERF_MON_HIST_DATA
     |  +--rw PON_SERVICE_CONFIG_PROFILE_XG_PON_UPSTREAM_MGMT_PERF_MON_HIST_DATA_LIST* [service-config-profile-name managed-entity-id]
     |     +--rw service-config-profile-name    string
     |     +--rw managed-entity-id              omci-types:omci-uint16
     |     +--rw threshold-data-1-2-id?         omci-types:omci-uint16
     +--rw PON_SLA_PROFILE
     |  +--rw PON_SLA_PROFILE_LIST* [sla-profile-name]
     |     +--rw sla-profile-name                        string
     |     +--rw downstream-guaranteed-rate?             uint32
     |     +--rw downstream-guaranteed-maximum-burst?    uint32
     |     +--rw downstream-best-effort-rate?            uint32
     |     +--rw downstream-best-effort-maximum-burst?   uint32
     |     +--rw upstream-fixed-rate?                    uint32
     |     +--rw upstream-guaranteed-rate?               uint32
     |     +--rw upstream-guaranteed-maximum-burst?      uint32
     |     +--rw upstream-priority?                      uint8
     |     +--rw upstream-best-effort-rate?              uint32
     |     +--rw upstream-best-effort-maximum-burst?     uint32
     |     +--rw upstream-best-effort-priority?          uint8
     +--rw PON_SLA_PROFILE_CONTROLLER
     |  +--rw PON_SLA_PROFILE_CONTROLLER_LIST* [name]
     |     +--rw name    -> /sonic-pon/PON_SLA_PROFILE/PON_SLA_PROFILE_LIST/sla-profile-name
     +--rw PON_OLT_PLUG
     |  +--rw PON_OLT_PLUG_LIST* [olt-name]
     |     +--rw olt-name              -> /sonic-pon/PON_OLT_INTF/PON_OLT_INTF_LIST/olt-name
     |     +--rw debug-log-level?      spt:logging-level
     |     +--rw fw-bank-ptr?          uint16
     |     +--rw nni-max-frame-size?   uint32
     +--ro PON_CONTROLLER_STATE
     |  +--ro PON_CONTROLLER_STATE_LIST* [name]
     |     +--ro name                           string
     |     +--ro timestamp?                     yang:date-and-time
     |     +--ro allow-unprovisioned-onus?      boolean
     |     +--ro config-read-failed?            boolean
     |     +--ro interface?                     string
     |     +--ro olt-timeout?                   uint32
     |     +--ro statistics-sample?             uint32
     |     +--ro version?                       string
     |     +--ro unprovisioned-age?             uint32
     |     +--ro refresh-state-on-olt-change?   boolean
     +--ro PON_CONTROLLER_ONU_FW_UPGRADE_STATE
     |  +--ro PON_CONTROLLER_ONU_FW_UPGRADE_STATE_LIST* [name onu-id]
     |     +--ro name      string
     |     +--ro onu-id    string
     +--ro PON_CONTROLLER_SYSTEM_STATUS_OLT
     |  +--ro PON_CONTROLLER_SYSTEM_STATUS_OLT_LIST* [controller-name mac-address]
     |     +--ro controller-name              string
     |     +--ro mac-address                  yang:mac-address
     |     +--ro olt-state?                   string
     |     +--ro onu-active-count?            uint32
     |     +--ro switch-chassis-id?           string
     |     +--ro switch-ipv4-address?         string
     |     +--ro switch-ipv6-address?         string
     |     +--ro switch-port-description?     string
     |     +--ro switch-port-id?              string
     |     +--ro switch-system-description?   string
     |     +--ro switch-system-name?          string
     +--ro PON_CONTROLLER_SYSTEM_STATUS_OLT_ONU
     |  +--ro PON_CONTROLLER_SYSTEM_STATUS_OLT_ONU_LIST* [name mac-address onu-serial-number]
     |     +--ro name                 string
     |     +--ro mac-address          -> /sonic-pon/PON_CONTROLLER_SYSTEM_STATUS_OLT/PON_CONTROLLER_SYSTEM_STATUS_OLT_LIST/mac-address
     |     +--ro onu-serial-number    string
     |     +--ro onu-state?           string
     +--ro PON_OLT_INTF_STATE
     |  +--ro PON_OLT_INTF_STATE_LIST* [olt-name port-id]
     |     +--ro olt-name                              string
     |     +--ro timestamp?                            yang:date-and-time
     |     +--ro fiber-reach?                          enumeration
     |     +--ro laser-shutdown?                       string
     |     +--ro loss-of-signal?                       boolean
     |     +--ro pon-enable?                           boolean
     |     +--ro discovery-period?                     uint32
     |     +--ro downstream-fec?                       boolean
     |     +--ro encryption?                           spt:olt-encryption-mode
     |     +--ro encryption-key-time?                  uint16
     |     +--ro error-detection-maximum-hec-ratio?    uint8
     |     +--ro error-detection-minimum-hec-sample?   uint16
     |     +--ro error-detection-maximum-ratio?        uint8
     |     +--ro error-detection-minimum-sample?       uint16
     |     +--ro guard-time?                           uint32
     |     +--ro mac-address?                          yang:mac-address
     |     +--ro max-frame-size?                       uint32
     |     +--ro pon-id?                               uint32
     |     +--ro pon-tag?                              string
     |     +--ro protection-auto-protect?              string
     |     +--ro protection-fast-failover?             boolean
     |     +--ro protection-inactivity-alarm?          string
     |     +--ro protection-status?                    string
     |     +--ro protection-watch?                     enumeration
     |     +--ro protection-last-switchover-time?      yang:date-and-time
     |     +--ro protection-last-switchover-type?      string
     |     +--ro port-id                               string
     |     +--ro device-id?                            string
     |     +--ro aging-time?                           uint16
     +--ro PON_OLT_INTF_ONU_STATE
     |  +--ro PON_OLT_INTF_ONU_STATE_LIST* [olt-name onu-serial-number]
     |     +--ro olt-name             -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro onu-serial-number    string
     |     +--ro onu-id?              uint16
     |     +--ro disable?             boolean
     +--ro PON_OLT_INTF_ONU_FW_UPGRADE_STATE
     |  +--ro PON_OLT_INTF_ONU_FW_UPGRADE_STATE_LIST* [olt-name onu-serial-number]
     |     +--ro olt-name             -> /sonic-pon/PON_OLT_INTF_ONU_STATE/PON_OLT_INTF_ONU_STATE_LIST/olt-name
     |     +--ro onu-serial-number    string
     +--ro PON_OLT_INTF_ONU_OPERATIONAL_STATE
     |  +--ro PON_OLT_INTF_ONU_OPERATIONAL_STATE_LIST* [olt-name id]
     |     +--ro olt-name             -> /sonic-pon/PON_OLT_INTF_ONU_STATE/PON_OLT_INTF_ONU_STATE_LIST/olt-name
     |     +--ro id                   string
     |     +--ro operational-state?   enumeration
     +--ro PON_OLT_INTF_NETWORK_STATE
     |  +--ro PON_OLT_INTF_NETWORK_STATE_LIST* [olt-name vlan-id]
     |     +--ro olt-name                                             -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro network-id?                                          uint16
     |     +--ro learning-limit?                                      uint16
     |     +--ro pon-flood-id?                                        uint16
     |     +--ro vlan-id                                              uint16
     |     +--ro flooding-sla-downstream-guaranteed-rate?             uint32
     |     +--ro flooding-sla-downstream-guaranteed-maximum-burst?    uint32
     |     +--ro flooding-sla-downstream-best-effort-rate?            uint32
     |     +--ro flooding-sla-downstream-best-effort-maximum-burst?   uint32
     +--ro PON_OLT_INTF_NNI_NETWORK_LEARNING_TABLE_STATE
     |  +--ro PON_OLT_INTF_NNI_NETWORK_LEARNING_TABLE_STATE_LIST* [olt-name network-id mac-address]
     |     +--ro olt-name       -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro network-id     -> /sonic-pon/PON_OLT_INTF_NETWORK_STATE/PON_OLT_INTF_NETWORK_STATE_LIST/network-id
     |     +--ro mac-address    yang:mac-address
     |     +--ro unicast-id?    uint16
     +--ro PON_OLT_INTF_ONU_SERVICE_TCONT_STATE
     |  +--ro PON_OLT_INTF_ONU_SERVICE_TCONT_STATE_LIST* [olt-name onu-serial-number service-port-id]
     |     +--ro olt-name             -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro onu-serial-number    -> /sonic-pon/PON_OLT_INTF_ONU_STATE/PON_OLT_INTF_ONU_STATE_LIST/onu-serial-number
     |     +--ro service-port-id      uint32
     |     +--ro alloc-id?            uint16
     +--ro PON_OLT_INTF_ONU_SERVICE_GEMPORT_STATE
     |  +--ro PON_OLT_INTF_ONU_SERVICE_GEMPORT_STATE_LIST* [olt-name onu-serial-number service-port-id]
     |     +--ro olt-name             -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro onu-serial-number    -> /sonic-pon/PON_OLT_INTF_ONU_STATE/PON_OLT_INTF_ONU_STATE_LIST/onu-serial-number
     |     +--ro service-port-id      uint32
     |     +--ro gemport-id?          uint16
     |     +--ro tcont-ref?           -> /sonic-pon/PON_OLT_INTF_ONU_SERVICE_TCONT_STATE/PON_OLT_INTF_ONU_SERVICE_TCONT_STATE_LIST/service-port-id
     +--ro PON_OLT_INTF_PROTECTION_UNDETECTED_ONU_STATE
     |  +--ro PON_OLT_INTF_PROTECTION_UNDETECTED_ONU_STATE_LIST* [olt-name id]
     |     +--ro olt-name    -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro id          string
     +--ro PON_OLT_PLUG_FW_UPGRADE_STATUS
     |  +--ro PON_OLT_PLUG_FW_UPGRADE_STATUS_LIST* [name]
     |     +--ro name                -> /sonic-pon/PON_OLT_PLUG_STATE/PON_OLT_PLUG_STATE_LIST/name
     |     +--ro bank?               uint16
     |     +--ro fx-code?            uint32
     |     +--ro file?               string
     |     +--ro status?             string
     |     +--ro upgrade-duration?   string
     |     +--ro upgrade-time?       yang:date-and-time
     +--ro PON_OLT_PLUG_FW_BANK_VERSION_STATE
     |  +--ro PON_OLT_PLUG_FW_BANK_VERSION_STATE_LIST* [name bank-id]
     |     +--ro name       -> /sonic-pon/PON_OLT_PLUG_STATE/PON_OLT_PLUG_STATE_LIST/name
     |     +--ro bank-id    uint8
     |     +--ro version?   string
     +--ro PON_OLT_INTF_STATISTICS_BINNED
     |  +--ro PON_OLT_INTF_STATISTICS_BINNED_LIST* [olt-name olt-stats-id]
     |     +--ro olt-name                       -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id                   yang:date-and-time
     |     +--ro timestamp?                     yang:date-and-time
     |     +--ro offline-onus-count?            uint64
     |     +--ro online-onus-count?             uint64
     |     +--ro pon-fec-seconds?               uint64
     |     +--ro rx-bw-ethernet-rate-bps?       uint64
     |     +--ro rx-bw-overhead-burst-bps?      uint64
     |     +--ro rx-bw-overhead-fec-bps?        uint64
     |     +--ro rx-bw-overhead-total-bps?      uint64
     |     +--ro rx-bw-packet-used-bps?         uint64
     |     +--ro rx-bw-total-free-bps?          uint64
     |     +--ro rx-bw-total-used-bps?          uint64
     |     +--ro rx-bw-total-util?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-frames?           uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-omci-mic-errors?            uint64
     |     +--ro rx-optical-level-idle?         decimal64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-frames?               uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro rx-unmatched-drops?            uint64
     |     +--ro total-onus-count?              uint64
     |     +--ro tx-bw-ethernet-rate-bps?       uint64
     |     +--ro tx-bw-overhead-fec-bps?        uint64
     |     +--ro tx-bw-overhead-framing-bps?    uint64
     |     +--ro tx-bw-overhead-total-bps?      uint64
     |     +--ro tx-bw-packet-used-bps?         uint64
     |     +--ro tx-bw-total-free-bps?          uint64
     |     +--ro tx-bw-total-used-bps?          uint64
     |     +--ro tx-bw-total-util?              uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-encrypted-frames?           uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-idle-octets?                uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-oam?                        uint64
     |     +--ro tx-optical-level?              decimal64
     |     +--ro tx-plain-frames?               uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro uninventoried-onus-count?      uint64
     |     +--ro unprovisioned-onus-count?      uint64
     +--ro PON_OLT_PLUG_STATISTICS_BINNED_ENV
     |  +--ro PON_OLT_PLUG_STATISTICS_BINNED_ENV_LIST* [olt-name olt-stats-id]
     |     +--ro olt-name         -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id     -> /sonic-pon/PON_OLT_INTF_STATISTICS_BINNED/PON_OLT_INTF_STATISTICS_BINNED_LIST/olt-stats-id
     |     +--ro current?         decimal64
     |     +--ro transmit-bias?   decimal64
     |     +--ro voltage?         decimal64
     +--ro PON_OLT_PLUG_STATISTICS_BINNED_NNI
     |  +--ro PON_OLT_PLUG_STATISTICS_BINNED_NNI_LIST* [olt-name olt-stats-id]
     |     +--ro olt-name                      -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id                  -> /sonic-pon/PON_OLT_INTF_STATISTICS_BINNED/PON_OLT_INTF_STATISTICS_BINNED_LIST/olt-stats-id
     |     +--ro rx-broadcast-octets?          uint64
     |     +--ro rx-crc32-drops?               uint64
     |     +--ro rx-encrypted-frames?          uint64
     |     +--ro rx-encrypted-octets?          uint64
     |     +--ro rx-filtered-frames?           uint64
     |     +--ro rx-frames-1024_1518?          uint64
     |     +--ro rx-frames-128_255?            uint64
     |     +--ro rx-frames-1519_plus?          uint64
     |     +--ro rx-frames-256_511?            uint64
     |     +--ro rx-frames-512_1023?           uint64
     |     +--ro rx-frames-64?                 uint64
     |     +--ro rx-frames-65_127?             uint64
     |     +--ro rx-frames-broadcast?          uint64
     |     +--ro rx-frames-green?              uint64
     |     +--ro rx-frames-multicast?          uint64
     |     +--ro rx-frames-unicast?            uint64
     |     +--ro rx-multicast-octets?          uint64
     |     +--ro rx-oam?                       uint64
     |     +--ro rx-oam-octets?                uint64
     |     +--ro rx-other-cascading-bytes?     uint64
     |     +--ro rx-other-cascading-packets?   uint64
     |     +--ro rx-overflow-drops?            uint64
     |     +--ro rx-overflow-octets?           uint64
     |     +--ro rx-plain-frames?              uint64
     |     +--ro rx-plain-octets?              uint64
     |     +--ro rx-too-long-drops?            uint64
     |     +--ro rx-too-short-drops?           uint64
     |     +--ro rx-unicast-octets?            uint64
     |     +--ro tomi-requests?                uint64
     |     +--ro tomi-resp-time-avg?           uint64
     |     +--ro tomi-resp-time-max?           uint64
     |     +--ro tomi-resp-time-min?           uint64
     |     +--ro tomi-responses?               uint64
     |     +--ro tomi-time-to-send-avg?        uint64
     |     +--ro tomi-time-to-send-max?        uint64
     |     +--ro tomi-time-to-send-min?        uint64
     |     +--ro tomi-timeouts?                uint64
     |     +--ro tx-broadcast-octets?          uint64
     |     +--ro tx-cascading-bytes?           uint64
     |     +--ro tx-cascading-packets?         uint64
     |     +--ro tx-encrypted-frames?          uint64
     |     +--ro tx-frames-1024_1518?          uint64
     |     +--ro tx-frames-128_255?            uint64
     |     +--ro tx-frames-1519_plus?          uint64
     |     +--ro tx-frames-256_511?            uint64
     |     +--ro tx-frames-512_1023?           uint64
     |     +--ro tx-frames-64?                 uint64
     |     +--ro tx-frames-65_127?             uint64
     |     +--ro tx-frames-broadcast?          uint64
     |     +--ro tx-frames-green?              uint64
     |     +--ro tx-frames-multicast?          uint64
     |     +--ro tx-frames-unicast?            uint64
     |     +--ro tx-multicast-octets?          uint64
     |     +--ro tx-non_control-octets?        uint64
     |     +--ro tx-oam?                       uint64
     |     +--ro tx-oam-octets?                uint64
     |     +--ro tx-plain-frames?              uint64
     |     +--ro tx-unicast-octets?            uint64
     +--ro PON_OLT_PLUG_STATISTICS_BINNED_TEMP
     |  +--ro PON_OLT_PLUG_STATISTICS_BINNED_TEMP_LIST* [olt-name olt-stats-id]
     |     +--ro olt-name        -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id    -> /sonic-pon/PON_OLT_INTF_STATISTICS_BINNED/PON_OLT_INTF_STATISTICS_BINNED_LIST/olt-stats-id
     |     +--ro asic?           uint64
     |     +--ro laser?          uint64
     |     +--ro xcvr?           uint64
     +--ro PON_OLT_STATISTICS_BINNED_PON_FLOODING
     |  +--ro PON_OLT_STATISTICS_BINNED_PON_FLOODING_LIST* [olt-name olt-stats-id flood-id]
     |     +--ro olt-name                      -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id                  -> /sonic-pon/PON_OLT_INTF_STATISTICS_BINNED/PON_OLT_INTF_STATISTICS_BINNED_LIST/olt-stats-id
     |     +--ro flood-id                      uint16
     |     +--ro tx-bw-best-effort-sla-util?   uint64
     |     +--ro tx-bw-best-effort-sla-bps?    uint64
     |     +--ro tx-bw-guaranteed-sla-util?    uint64
     |     +--ro tx-bw-guaranteed-sla-bps?     uint64
     |     +--ro tx-bw-total-sla-util?         uint64
     |     +--ro tx-bw-total-sla-bps?          uint64
     |     +--ro tx-encrypted-octets?          uint64
     |     +--ro tx-frames-1024_1518?          uint64
     |     +--ro tx-frames-128_255?            uint64
     |     +--ro tx-frames-1519_plus?          uint64
     |     +--ro tx-frames-256_511?            uint64
     |     +--ro tx-frames-512_1023?           uint64
     |     +--ro tx-frames-64?                 uint64
     |     +--ro tx-frames-65_127?             uint64
     |     +--ro tx-frames-broadcast?          uint64
     |     +--ro tx-frames?                    uint64
     |     +--ro tx-frames-multicast?          uint64
     |     +--ro tx-frames-unicast?            uint64
     |     +--ro tx-multi-broadcast-octets?    uint64
     |     +--ro tx-plain-octets?              uint64
     |     +--ro tx-rate-bps?                  uint64
     |     +--ro tx-total-octets?              uint64
     |     +--ro tx-unicast-octets?            uint64
     +--ro PON_OLT_STATISTICS_BINNED_PON_FLOODING_NETWORK
     |  +--ro PON_OLT_STATISTICS_BINNED_PON_FLOODING_NETWORK_LIST* [olt-name olt-stats-id flood-id]
     |     +--ro olt-name        -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-stats-id    -> /sonic-pon/PON_OLT_INTF_STATISTICS_BINNED/PON_OLT_INTF_STATISTICS_BINNED_LIST/olt-stats-id
     |     +--ro flood-id        -> /sonic-pon/PON_OLT_STATISTICS_BINNED_PON_FLOODING/PON_OLT_STATISTICS_BINNED_PON_FLOODING_LIST/flood-id
     |     +--ro vlan-id*        uint16
     +--ro PON_OLT_STATISTICS_ACCUMULATING_ENV
     |  +--ro PON_OLT_STATISTICS_ACCUMULATING_ENV_LIST* [olt-name]
     |     +--ro olt-name         -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro current?         decimal64
     |     +--ro transmit-bias?   decimal64
     |     +--ro voltage?         decimal64
     +--ro PON_OLT_STATISTICS_ACCUMULATING
     |  +--ro PON_OLT_STATISTICS_ACCUMULATING_LIST* [olt-name]
     |     +--ro olt-name                       -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro offline-onus-count?            uint64
     |     +--ro online-onus-count?             uint64
     |     +--ro pon-fec-seconds?               uint64
     |     +--ro rx-bw-ethernet-rate-bps?       uint64
     |     +--ro rx-bw-overhead-burst-bps?      uint64
     |     +--ro rx-bw-overhead-fec-bps?        uint64
     |     +--ro rx-bw-overhead-total-bps?      uint64
     |     +--ro rx-bw-packet-used-bps?         uint64
     |     +--ro rx-bw-total-free-bps?          uint64
     |     +--ro rx-bw-total-used-bps?          uint64
     |     +--ro rx-bw-total-util?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-frames?           uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-omci-mic-errors?            uint64
     |     +--ro rx-optical-level-idle?         decimal64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-frames?               uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro rx-unmatched-drops?            uint64
     |     +--ro total-onus-count?              uint64
     |     +--ro tx-bw-ethernet-rate-bps?       uint64
     |     +--ro tx-bw-overhead-fec-bps?        uint64
     |     +--ro tx-bw-overhead-framing-bps?    uint64
     |     +--ro tx-bw-overhead-total-bps?      uint64
     |     +--ro tx-bw-packet-used-bps?         uint64
     |     +--ro tx-bw-total-free-bps?          uint64
     |     +--ro tx-bw-total-used-bps?          uint64
     |     +--ro tx-bw-total-util?              uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-encrypted-frames?           uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-idle-octets?                uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-oam?                        uint64
     |     +--ro tx-optical-level?              decimal64
     |     +--ro tx-plain-frames?               uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro uninventoried-onus-count?      uint64
     |     +--ro unprovisioned-onus-count?      uint64
     +--ro PON_OLT_STATISTICS_ACCUMULATING_TEMP
     |  +--ro PON_OLT_STATISTICS_ACCUMULATING_TEMP_LIST* [olt-name]
     |     +--ro olt-name    -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro asic?       uint64
     |     +--ro laser?      uint64
     |     +--ro xcvr?       uint64
     +--ro PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING
     |  +--ro PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_LIST* [olt-name olt-id]
     |     +--ro olt-name                      -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-id                        uint16
     |     +--ro tx-bw-best-effort-sla-util?   uint64
     |     +--ro tx-bw-best-effort-sla-bps?    uint64
     |     +--ro tx-bw-guaranteed-sla-util?    uint64
     |     +--ro tx-bw-guaranteed-sla-bps?     uint64
     |     +--ro tx-bw-total-sla-util?         uint64
     |     +--ro tx-bw-total-sla-bps?          uint64
     |     +--ro tx-encrypted-octets?          uint64
     |     +--ro tx-frames-1024_1518?          uint64
     |     +--ro tx-frames-128_255?            uint64
     |     +--ro tx-frames-1519_plus?          uint64
     |     +--ro tx-frames-256_511?            uint64
     |     +--ro tx-frames-512_1023?           uint64
     |     +--ro tx-frames-64?                 uint64
     |     +--ro tx-frames-65_127?             uint64
     |     +--ro tx-frames-broadcast?          uint64
     |     +--ro tx-frames?                    uint64
     |     +--ro tx-frames-multicast?          uint64
     |     +--ro tx-frames-unicast?            uint64
     |     +--ro tx-multi-broadcast-octets?    uint64
     |     +--ro tx-plain-octets?              uint64
     |     +--ro tx-rate-bps?                  uint64
     |     +--ro tx-total-octets?              uint64
     |     +--ro tx-unicast-octets?            uint64
     +--ro PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_NNI_NETWORK
     |  +--ro PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_NNI_NETWORK_LIST* [olt-name olt-id]
     |     +--ro olt-name    -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
     |     +--ro olt-id      uint16
     |     +--ro vlan-tag*   string
     +--ro PON_ONU_STATE
     |  +--ro PON_ONU_STATE_LIST* [onu-name]
     |     +--ro onu-name                           string
     |     +--ro timestamp?                         yang:date-and-time
     |     +--ro onu-id?                            uint16
     |     +--ro cvid?                              uint16
     |     +--ro equipment-id?                      string
     |     +--ro fw-bank-ptr?                       uint16
     |     +--ro fw-version?                        string
     |     +--ro hardware-version?                  string
     |     +--ro last-provisioning-time?            yang:date-and-time
     |     +--ro mac-address?                       yang:mac-address
     |     +--ro manufacturer?                      string
     |     +--ro model?                             string
     |     +--ro online-time?                       yang:date-and-time
     |     +--ro realtime-stats?                    boolean
     |     +--ro registration-id?                   string
     |     +--ro alloc-id-omcc?                     uint16
     |     +--ro host-mac-address?                  yang:mac-address
     |     +--ro laser-bias-current?                uint64
     |     +--ro logical-id?                        string
     |     +--ro logical-password?                  string
     |     +--ro omci-txn-correlation-id?           uint16
     |     +--ro omcc-version?                      yang:hex-string
     |     +--ro temperature?                       decimal64
     |     +--ro uptime?                            uint64
     |     +--ro voltage?                           decimal64
     |     +--ro registration-id-hex?               yang:hex-string
     |     +--ro serial-number?                     string
     |     +--ro service-config?                    string
     |     +--ro vendor?                            string
     |     +--ro fw-upgrade-backoff-delay?          uint32
     |     +--ro fw-upgrade-backoff-divisor?        uint32
     |     +--ro fw-upgrade-download-format?        spt:fw-download-format
     |     +--ro fw-upgrade-end-download-timeout?   uint32
     |     +--ro fw-upgrade-maximum-retries?        uint32
     |     +--ro fw-upgrade-maximum-window-size?    uint32
     |     +--ro fw-upgrade-response-timeout?       uint32
     |     +--ro server-state?                      string
     |     +--ro registration-disallowed?           boolean
     |     +--ro bank?                              uint16
     |     +--ro current-window?                    uint8
     |     +--ro fx-code?                           string
     |     +--ro file?                              string
     |     +--ro negotiated-window?                 uint8
     |     +--ro progress?                          uint8
     |     +--ro retries?                           uint8
     |     +--ro sent-blocks?                       uint32
     |     +--ro status?                            string
     |     +--ro total-blocks?                      uint32
     |     +--ro upgrade-duration?                  string
     |     +--ro upgrade-time?                      yang:date-and-time
     |     +--ro aborted?                           boolean
     |     +--ro failures?                          uint32
     |     +--ro version-mismatches?                uint32
     +--ro PON_ONU_STATISTICS_BINNED
     |  +--ro PON_ONU_STATISTICS_BINNED_LIST* [onu-name onu-stats-id]
     |     +--ro onu-name                            -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro olt-pon-rx-optical-level?           decimal64
     |     +--ro olt-pon-tx-optical-level?           decimal64
     |     +--ro olt-pon-rx-deregistrations?         uint64
     |     +--ro olt-pon-rx-registrations?           uint64
     |     +--ro olt-pon-fiber-distance?             decimal64
     |     +--ro olt-pon-equalization-delay?         uint64
     |     +--ro olt-pon-round-trip-time?            uint64
     |     +--ro olt-pon-one-way-delay?              uint64
     |     +--ro olt-pon-rx-acc-fec-bytes?           uint64
     |     +--ro olt-pon-rx-acc-fec-correct-bytes?   uint64
     |     +--ro olt-pon-rx-acc-fec-error-bytes?     uint64
     |     +--ro olt-pon-rx-pre-fec-ber?             string
     |     +--ro olt-pon-rx-post-fec-ber?            string
     |     +--ro onu-stats-id                        yang:date-and-time
     |     +--ro timestamp?                          yang:date-and-time
     +--ro PON_ONU_OLT_SERVICE_STATE
     |  +--ro PON_ONU_OLT_SERVICE_STATE_LIST* [onu-name olt-service-id]
     |     +--ro onu-name                                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro olt-service-id                              uint32
     |     +--ro enable?                                     boolean
     |     +--ro learning-limit?                             uint16
     |     +--ro tcont-service-ref?                          string
     |     +--ro unicast-id?                                 uint16
     |     +--ro upstream-priority-treatment?                enumeration
     |     +--ro upstream-priority-value?                    uint8
     |     +--ro sla-downstream-guaranteed-rate?             uint32
     |     +--ro sla-downstream-guaranteed-maximum-burst?    uint32
     |     +--ro sla-downstream-best-effort-rate?            uint32
     |     +--ro sla-downstream-best-effort-maximum-burst?   uint32
     |     +--ro sla-upstream-fixed-rate?                    uint32
     |     +--ro sla-upstream-guaranteed-rate?               uint32
     |     +--ro sla-upstream-guaranteed-maximum-burst?      uint32
     |     +--ro sla-upstream-priority?                      uint8
     |     +--ro sla-upstream-best-effort-rate?              uint32
     |     +--ro sla-upstream-best-effort-maximum-burst?     uint32
     |     +--ro sla-upstream-best-effort-priority?          uint8
     |     +--ro downstream-qos-map?                         string
     +--ro PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE
     |  +--ro PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE_LIST* [onu-name olt-service-id]
     |     +--ro onu-name          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro olt-service-id    -> /sonic-pon/PON_ONU_OLT_SERVICE_STATE/PON_ONU_OLT_SERVICE_STATE_LIST/olt-service-id
     |     +--ro type?             string
     +--ro PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_MAP_STATE
     |  +--ro PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_MAP_STATE_LIST* [onu-name olt-service-id priority]
     |     +--ro onu-name              -> /sonic-pon/PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE/PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE_LIST/onu-name
     |     +--ro olt-service-id        -> /sonic-pon/PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE/PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE_LIST/olt-service-id
     |     +--ro priority              uint8
     |     +--ro olt-service-offset?   uint8
     +--ro PON_ONU_OLT_SERVICE_NETWORK_STATE
     |  +--ro PON_ONU_OLT_SERVICE_NETWORK_STATE_LIST* [onu-name olt-service-id network-id]
     |     +--ro onu-name          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro olt-service-id    -> /sonic-pon/PON_ONU_OLT_SERVICE_STATE/PON_ONU_OLT_SERVICE_STATE_LIST/olt-service-id
     |     +--ro network-id        uint16
     |     +--ro vlan-id?          uint16
     +--ro PON_ONU_UNI_STATE
     |  +--ro PON_ONU_UNI_STATE_LIST* [onu-name port-id]
     |     +--ro onu-name             -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro port-id              string
     |     +--ro duplex?              string
     |     +--ro enable?              boolean
     |     +--ro managed-entity-id?   uint16
     |     +--ro max-frame-size?      uint32
     |     +--ro poe?                 boolean
     |     +--ro speed?               string
     |     +--ro state?               string
     +--ro PON_ONU_UNI_LEARNED_ADDRESSES_STATE
     |  +--ro PON_ONU_UNI_LEARNED_ADDRESSES_STATE_LIST* [onu-name port-id]
     |     +--ro onu-name           -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro port-id            -> /sonic-pon/PON_ONU_UNI_STATE/PON_ONU_UNI_STATE_LIST/port-id
     |     +--ro learned-address*   yang:mac-address
     +--ro PON_ONU_FW_BANK_VERSION_STATE
     |  +--ro PON_ONU_FW_BANK_VERSION_STATE_LIST* [onu-name bank-id]
     |     +--ro onu-name    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro bank-id     uint8
     |     +--ro version?    string
     +--ro PON_ONU_STATISTICS_BINNED_OLT_PON
     |  +--ro PON_ONU_STATISTICS_BINNED_OLT_PON_LIST* [onu-name onu-stats-id]
     |     +--ro onu-name              -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id          -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro rx-optical-level?     decimal64
     |     +--ro tx-optical-level?     decimal64
     |     +--ro rx-deregistrations?   uint64
     |     +--ro rx-registrations?     uint64
     |     +--ro fiber-distance?       decimal64
     |     +--ro equalization-delay?   uint64
     |     +--ro round-trip-time?      uint64
     |     +--ro one-way-delay?        uint64
     +--ro PON_ONU_STATISTICS_BINNED_OLT_PON_OMCC
     |  +--ro PON_ONU_STATISTICS_BINNED_OLT_PON_OMCC_LIST* [onu-name onu-stats-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro bad-key-exchanges?             uint64
     |     +--ro good-key-exchanges?            uint64
     |     +--ro omci-oam-requests?             uint64
     |     +--ro omci-oam-resp-time-avg?        uint64
     |     +--ro omci-oam-resp-time-max?        uint64
     |     +--ro omci-oam-resp-time-min?        uint64
     |     +--ro omci-oam-responses?            uint64
     |     +--ro omci-oam-time-to-send-avg?     uint64
     |     +--ro omci-oam-time-to-send-max?     uint64
     |     +--ro omci-oam-time-to-send-min?     uint64
     |     +--ro omci-oam-timeouts?             uint64
     |     +--ro ploam-timeouts?                uint64
     |     +--ro rx-all-bandwidth-reqs?         uint64
     |     +--ro rx-bad-icv-drops?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-control-octets?             uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-key-mismatch-octets?        uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-oam?                        uint64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-rate-bps?                   uint64
     |     +--ro rx-security-drop-octets?       uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-control-octets?             uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-grant-ups-tq?               uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-oam?                        uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-ploam-ds-ranging-time?      uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro tx-upstream-slots?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_PON
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_PON_LIST* [onu-name onu-stats-id]
     |     +--ro onu-name            -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id        -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro rx-optical-level?   decimal64
     |     +--ro tx-optical-level?   decimal64
     +--ro PON_ONU_STATISTICS_BINNED_OLT_PON_SERVICE
     |  +--ro PON_ONU_STATISTICS_BINNED_OLT_PON_SERVICE_LIST* [onu-name onu-stats-id service-port-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro service-port-id                uint8
     |     +--ro bad-key-exchanges?             uint64
     |     +--ro enable-count?                  uint64
     |     +--ro good-key-exchanges?            uint64
     |     +--ro omci-oam-requests?             uint64
     |     +--ro omci-oam-resp-time-avg?        uint64
     |     +--ro omci-oam-resp-time-max?        uint64
     |     +--ro omci-oam-resp-time-min?        uint64
     |     +--ro omci-oam-responses?            uint64
     |     +--ro omci-oam-time-to-send-avg?     uint64
     |     +--ro omci-oam-time-to-send-max?     uint64
     |     +--ro omci-oam-time-to-send-min?     uint64
     |     +--ro omci-oam-timeouts?             uint64
     |     +--ro ploam-timeouts?                uint64
     |     +--ro rx-all-bandwidth-reqs?         uint64
     |     +--ro rx-bw-best-effort-sla-util?    uint64
     |     +--ro rx-bw-best-effort-sla-bps?     uint64
     |     +--ro rx-bw-fixed-sla-util?          uint64
     |     +--ro rx-bw-fixed-sla-bps?           uint64
     |     +--ro rx-bw-guaranteed-sla-util?     uint64
     |     +--ro rx-bw-guaranteed-sla-bps?      uint64
     |     +--ro rx-bw-total-sla-util?          uint64
     |     +--ro rx-bw-total-sla-bps?           uint64
     |     +--ro rx-bad-icv-drops?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-control-octets?             uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-frames?           uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-key-mismatch-octets?        uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-frames?               uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-rate-bps?                   uint64
     |     +--ro rx-security-drop-octets?       uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro tx-bw-best-effort-sla-util?    uint64
     |     +--ro tx-bw-best-effort-sla-bps?     uint64
     |     +--ro tx-bw-guaranteed-sla-util?     uint64
     |     +--ro tx-bw-guaranteed-sla-bps?      uint64
     |     +--ro tx-bw-total-sla-util?          uint64
     |     +--ro tx-bw-total-sla-bps?           uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-control-octets?             uint64
     |     +--ro tx-encrypted-frames?           uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-plain-frames?               uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-ploam-ds-ranging-time?      uint64
     |     +--ro tx-rate-bps?                   uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro tx-upstream-slots?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_FEC_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_FEC_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                       uint16
     |     +--ro corrected-bytes?            uint64
     |     +--ro corrected-code-words?       uint64
     |     +--ro fec-seconds?                uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro threshold-data-half-id?     uint64
     |     +--ro total-code-words?           uint64
     |     +--ro uncorrectable-code-words?   uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                      -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                  -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                         uint16
     |     +--ro direction?                    enumeration
     |     +--ro broadcast-frames?             uint64
     |     +--ro crc-errored-frames?           uint64
     |     +--ro drop-events?                  uint64
     |     +--ro frames?                       uint64
     |     +--ro frames-1024-to-1518-octets?   uint64
     |     +--ro frames-128-to-255-octets?     uint64
     |     +--ro frames-256-to-511-octets?     uint64
     |     +--ro frames-512-to-1023-octets?    uint64
     |     +--ro frames-64-octets?             uint64
     |     +--ro frames-65-to-127-octets?      uint64
     |     +--ro interval-end-time?            uint64
     |     +--ro multicast-frames?             uint64
     |     +--ro octets?                       uint64
     |     +--ro oversize-frames?              uint64
     |     +--ro undersize-frames?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                      -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                  -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                         uint16
     |     +--ro direction?                    enumeration
     |     +--ro broadcast-frames?             uint64
     |     +--ro crc-errored-frames?           uint64
     |     +--ro drop-events?                  uint64
     |     +--ro frames?                       uint64
     |     +--ro frames-1024-to-1518-octets?   uint64
     |     +--ro frames-128-to-255-octets?     uint64
     |     +--ro frames-256-to-511-octets?     uint64
     |     +--ro frames-512-to-1023-octets?    uint64
     |     +--ro frames-64-octets?             uint64
     |     +--ro frames-65-to-127-octets?      uint64
     |     +--ro interval-end-time?            uint64
     |     +--ro multicast-frames?             uint64
     |     +--ro octets?                       uint64
     |     +--ro oversize-frames?              uint64
     |     +--ro undersize-frames?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_DOWNSTREAM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_DOWNSTREAM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                          uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_UPSTREAM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_UPSTREAM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                          uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                               -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                           -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                                  uint16
     |     +--ro alignment-error-counter?               uint64
     |     +--ro buffer-overflows-on-receive?           uint64
     |     +--ro buffer-overflows-on-transmit?          uint64
     |     +--ro carrier-sense-error-counter?           uint64
     |     +--ro deferred-transmission-counter?         uint64
     |     +--ro excessive-collision-counter?           uint64
     |     +--ro fcs-errors?                            uint64
     |     +--ro frames-too-long?                       uint64
     |     +--ro internal-mac-receive-error-counter?    uint64
     |     +--ro internal-mac-transmit-error-counter?   uint64
     |     +--ro interval-end-time?                     uint64
     |     +--ro late-collision-counter?                uint64
     |     +--ro multiple-collisions-frame-counter?     uint64
     |     +--ro single-collision-frame-counter?        uint64
     |     +--ro sqe-counter?                           uint64
     |     +--ro threshold-data-half-id?                uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_IP_HOST_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_IP_HOST_PERF_MON_HIST_DATA_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                  -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id              -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                     uint16
     |     +--ro dns-errors?               uint64
     |     +--ro dhcp-timeouts?            uint64
     |     +--ro icmp-errors?              uint64
     |     +--ro internal-error?           uint64
     |     +--ro interval-end-time?        uint64
     |     +--ro ip-address-conflict?      uint64
     |     +--ro out-of-memory?            uint64
     |     +--ro threshold-data-half-id?   uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_RS232_RS485_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_RS232_RS485_PERF_MON_HIST_DATA_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                       uint16
     |     +--ro incoming-bytes-from-chip?   uint64
     |     +--ro incoming-bytes-from-pon?    uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro outgoing-bytes-from-chip?   uint64
     |     +--ro outgoing-bytes-from-pon?    uint64
     |     +--ro threshold-data-half-id?     uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_TCP_UDP_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_TCP_UDP_PERF_MON_HIST_DATA_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                  -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id              -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                     uint16
     |     +--ro accept-failed?            uint64
     |     +--ro bind-failed?              uint64
     |     +--ro interval-end-time?        uint64
     |     +--ro listen-failed?            uint64
     |     +--ro select-failed?            uint64
     |     +--ro socket-failed?            uint64
     |     +--ro threshold-data-half-id?   uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ENHANCED_TC_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ENHANCED_TC_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                                -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                                       uint16
     |     +--ro lods-event-count?                           uint64
     |     +--ro lods-event-restored-count?                  uint64
     |     +--ro fragment-xgem-frames?                       uint64
     |     +--ro interval-end-time?                          uint64
     |     +--ro onu-reactivation-by-lods-events?            uint64
     |     +--ro psbd-hec-error-count?                       uint64
     |     +--ro received-bytes-in-nonidle-xgem-frames?      uint64
     |     +--ro transmitted-bytes-in-nonidle-xgem-frames?   uint64
     |     +--ro transmitted-xgem-frames?                    uint64
     |     +--ro unknown-profile-count?                      uint64
     |     +--ro xgem-hec-lost-words-count?                  uint64
     |     +--ro xgem-key-errors?                            uint64
     |     +--ro xgem-hec-error-count?                       uint64
     |     +--ro xgtc-hec-error-count?                       uint64
     |     +--ro threshold-data-64-bit-id?                   uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM3
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM3_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                          uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro drop-events?                   uint64
     |     +--ro fragments?                     uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro jabbers?                       uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_GAL_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_GAL_ETHERNET_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                   -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                          uint16
     |     +--ro discarded-downstream-frames?   uint64
     |     +--ro discarded-upstream-frames?     uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro threshold-data-half-id?        uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_GEM_PORT_NETWORK_CTP_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_GEM_PORT_NETWORK_CTP_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                     -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                 -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                        uint16
     |     +--ro encryption-key-errors?       uint64
     |     +--ro interval-end-time?           uint64
     |     +--ro received-gem-frames?         uint64
     |     +--ro received-payload-bytes?      uint64
     |     +--ro threshold-data-half-id?      uint64
     |     +--ro transmitted-gem-frames?      uint64
     |     +--ro transmitted-payload-bytes?   uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_OPERATIONAL_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_OPERATIONAL_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                      -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                             uint16
     |     +--ro cpu-percent-utilization?          uint64
     |     +--ro errors-in-operations?             uint64
     |     +--ro flash-size-available?             uint64
     |     +--ro flash-utilization?                uint64
     |     +--ro interval-end-time?                uint64
     |     +--ro ram-size-available?               uint64
     |     +--ro ram-utilization?                  uint64
     |     +--ro software-errors?                  uint64
     |     +--ro threshold-data-half-id?           uint64
     |     +--ro temperature-sensor-description?   uint64
     |     +--ro temperature-sensor-value?         uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_MAC_BRIDGE_PORT_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_MAC_BRIDGE_PORT_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                      -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                             uint16
     |     +--ro delay-exceeded-discard-counter?   uint64
     |     +--ro forwarded-frame-counter?          uint64
     |     +--ro interval-end-time?                uint64
     |     +--ro mtu-exceeded-discard-counter?     uint64
     |     +--ro received-and-discarded-counter?   uint64
     |     +--ro received-frame-counter?           uint64
     |     +--ro threshold-data-half-id?           uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_XG_PON_DOWNSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_XG_PON_DOWNSTREAM_MGMT_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                                   -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                               -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                                      uint16
     |     +--ro interval-end-time?                         uint64
     |     +--ro threshold-data-half-id?                    uint64
     |     +--ro ploam-mic-error-count?                     uint64
     |     +--ro downstream-ploam-message-count?            uint64
     |     +--ro profile-messages-received?                 uint64
     |     +--ro ranging-time-messages-received?            uint64
     |     +--ro deactivate-onu-id-messages-received?       uint64
     |     +--ro disable-serial-number-messages-received?   uint64
     |     +--ro request-registration-messages-received?    uint64
     |     +--ro assign-alloc-id-messages-received?         uint64
     |     +--ro key-control-messages-received?             uint64
     |     +--ro sleep-allow-messages-received?             uint64
     |     +--ro baseline-omci-messages-received-count?     uint64
     |     +--ro extended-omci-messages-received-count?     uint64
     |     +--ro assign-onu-id-omci-messages-received?      uint64
     |     +--ro omci-mic-error-count?                      uint64
     +--ro PON_ONU_STATISTICS_BINNED_ONU_XG_PON_UPSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_BINNED_ONU_XG_PON_UPSTREAM_MGMT_PM_LIST* [onu-name onu-stats-id me-id]
     |     +--ro onu-name                        -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-stats-id                    -> /sonic-pon/PON_ONU_STATISTICS_BINNED/PON_ONU_STATISTICS_BINNED_LIST/onu-stats-id
     |     +--ro me-id                           uint16
     |     +--ro interval-end-time?              uint64
     |     +--ro threshold-data-half-id?         uint64
     |     +--ro upstream-ploam-message-count?   uint64
     |     +--ro serial-number-message-count?    uint64
     |     +--ro registration-message-count?     uint64
     |     +--ro key-report-message-count?       uint64
     |     +--ro acknowledge-message-count?      uint64
     |     +--ro sleep-request-message-count?    uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_LIST* [onu-name]
     |     +--ro onu-name              -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro rx-optical-level?     decimal64
     |     +--ro tx-optical-level?     decimal64
     |     +--ro rx-deregistrations?   uint64
     |     +--ro rx-registrations?     uint64
     |     +--ro fiber-distance?       decimal64
     |     +--ro equalization-delay?   uint64
     |     +--ro round-trip-time?      uint64
     |     +--ro one-way-delay?        uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_OMCC
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_OMCC_LIST* [onu-name]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro bad-key-exchanges?             uint64
     |     +--ro enable-count?                  uint64
     |     +--ro good-key-exchanges?            uint64
     |     +--ro omci-oam-requests?             uint64
     |     +--ro omci-oam-resp-time-avg?        uint64
     |     +--ro omci-oam-resp-time-max?        uint64
     |     +--ro omci-oam-resp-time-min?        uint64
     |     +--ro omci-oam-responses?            uint64
     |     +--ro omci-oam-time-to-send-avg?     uint64
     |     +--ro omci-oam-time-to-send-max?     uint64
     |     +--ro omci-oam-time-to-send-min?     uint64
     |     +--ro omci-oam-timeouts?             uint64
     |     +--ro ploam-timeouts?                uint64
     |     +--ro rx-all-bandwidth-reqs?         uint64
     |     +--ro rx-bw-best-effort-sla-util?    uint64
     |     +--ro rx-bw-best-effort-sla-bps?     uint64
     |     +--ro rx-bw-fixed-sla-util?          uint64
     |     +--ro rx-bw-fixed-sla-bps?           uint64
     |     +--ro rx-bw-guaranteed-sla-util?     uint64
     |     +--ro rx-bw-guaranteed-sla-bps?      uint64
     |     +--ro rx-bw-total-sla-util?          uint64
     |     +--ro rx-bw-total-sla-bps?           uint64
     |     +--ro rx-bad-icv-drops?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-control-octets?             uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-frames?           uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-key-mismatch-octets?        uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-oam?                        uint64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-frames?               uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-reports?                    uint64
     |     +--ro rx-rate-bps?                   uint64
     |     +--ro rx-security-drop-octets?       uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro tx-bw-best-effort-sla-util?    uint64
     |     +--ro tx-bw-best-effort-sla-bps?     uint64
     |     +--ro tx-bw-guaranteed-sla-util?     uint64
     |     +--ro tx-bw-guaranteed-sla-bps?      uint64
     |     +--ro tx-bw-total-sla-util?          uint64
     |     +--ro tx-bw-total-sla-bps?           uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-control-octets?             uint64
     |     +--ro tx-encrypted-frames?           uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-gates?                      uint64
     |     +--ro tx-grant-ups-tq?               uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-oam?                        uint64
     |     +--ro tx-plain-frames?               uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-ploam-ds-ranging-time?      uint64
     |     +--ro tx-rate-bps?                   uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro tx-upstream-slots?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_PON
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_PON_LIST* [onu-name]
     |     +--ro onu-name            -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro rx-optical-level?   decimal64
     |     +--ro tx-optical-level?   decimal64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_SERVICE
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_SERVICE_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint8
     |     +--ro bad-key-exchanges?             uint64
     |     +--ro enable-count?                  uint64
     |     +--ro good-key-exchanges?            uint64
     |     +--ro omci-oam-requests?             uint64
     |     +--ro omci-oam-resp-time-avg?        uint64
     |     +--ro omci-oam-resp-time-max?        uint64
     |     +--ro omci-oam-resp-time-min?        uint64
     |     +--ro omci-oam-responses?            uint64
     |     +--ro omci-oam-time-to-send-avg?     uint64
     |     +--ro omci-oam-time-to-send-max?     uint64
     |     +--ro omci-oam-time-to-send-min?     uint64
     |     +--ro omci-oam-timeouts?             uint64
     |     +--ro ploam-timeouts?                uint64
     |     +--ro rx-all-bandwidth-reqs?         uint64
     |     +--ro rx-bw-best-effort-sla-util?    uint64
     |     +--ro rx-bw-best-effort-sla-bps?     uint64
     |     +--ro rx-bw-fixed-sla-util?          uint64
     |     +--ro rx-bw-fixed-sla-bps?           uint64
     |     +--ro rx-bw-guaranteed-sla-util?     uint64
     |     +--ro rx-bw-guaranteed-sla-bps?      uint64
     |     +--ro rx-bw-total-sla-util?          uint64
     |     +--ro rx-bw-total-sla-bps?           uint64
     |     +--ro rx-bad-icv-drops?              uint64
     |     +--ro rx-bandwidth-reqs?             uint64
     |     +--ro rx-crc32-drops?                uint64
     |     +--ro rx-crc8-errors?                uint64
     |     +--ro rx-control-octets?             uint64
     |     +--ro rx-empty-slots?                uint64
     |     +--ro rx-encrypted-frames?           uint64
     |     +--ro rx-encrypted-octets?           uint64
     |     +--ro rx-encrypted-segments?         uint64
     |     +--ro rx-errored-bip-bits?           uint64
     |     +--ro rx-errored-bip-blocks?         uint64
     |     +--ro rx-fec-corrected-blocks?       uint64
     |     +--ro rx-fec-corrections?            uint64
     |     +--ro rx-fec-good-blocks?            uint64
     |     +--ro rx-fec-uncorrectable-blocks?   uint64
     |     +--ro rx-filtered-frames?            uint64
     |     +--ro rx-frames-1024_1518?           uint64
     |     +--ro rx-frames-128_255?             uint64
     |     +--ro rx-frames-1519_plus?           uint64
     |     +--ro rx-frames-256_511?             uint64
     |     +--ro rx-frames-512_1023?            uint64
     |     +--ro rx-frames-64?                  uint64
     |     +--ro rx-frames-65_127?              uint64
     |     +--ro rx-frames-green?               uint64
     |     +--ro rx-good-bip-blocks?            uint64
     |     +--ro rx-hec-errors?                 uint64
     |     +--ro rx-idle-octets?                uint64
     |     +--ro rx-key-mismatch-octets?        uint64
     |     +--ro rx-mpcp-ploam?                 uint64
     |     +--ro rx-multi-broadcast-octets?     uint64
     |     +--ro rx-overflow-drops?             uint64
     |     +--ro rx-overflow-octets?            uint64
     |     +--ro rx-plain-frames?               uint64
     |     +--ro rx-plain-octets?               uint64
     |     +--ro rx-plain-segments?             uint64
     |     +--ro rx-ploam-mic-errors?           uint64
     |     +--ro rx-rate-bps?                   uint64
     |     +--ro rx-security-drop-octets?       uint64
     |     +--ro rx-too-long-drops?             uint64
     |     +--ro rx-too-short-drops?            uint64
     |     +--ro rx-total-octets?               uint64
     |     +--ro rx-unicast-octets?             uint64
     |     +--ro tx-bw-best-effort-sla-util?    uint64
     |     +--ro tx-bw-best-effort-sla-bps?     uint64
     |     +--ro tx-bw-guaranteed-sla-util?     uint64
     |     +--ro tx-bw-guaranteed-sla-bps?      uint64
     |     +--ro tx-bw-total-sla-util?          uint64
     |     +--ro tx-bw-total-sla-bps?           uint64
     |     +--ro tx-bandwidth-reqs?             uint64
     |     +--ro tx-control-octets?             uint64
     |     +--ro tx-encrypted-frames?           uint64
     |     +--ro tx-encrypted-octets?           uint64
     |     +--ro tx-encrypted-segments?         uint64
     |     +--ro tx-frames-1024_1518?           uint64
     |     +--ro tx-frames-128_255?             uint64
     |     +--ro tx-frames-1519_plus?           uint64
     |     +--ro tx-frames-256_511?             uint64
     |     +--ro tx-frames-512_1023?            uint64
     |     +--ro tx-frames-64?                  uint64
     |     +--ro tx-frames-65_127?              uint64
     |     +--ro tx-frames-broadcast?           uint64
     |     +--ro tx-frames-green?               uint64
     |     +--ro tx-frames-multicast?           uint64
     |     +--ro tx-frames-unicast?             uint64
     |     +--ro tx-mpcp-ploam?                 uint64
     |     +--ro tx-multi-broadcast-octets?     uint64
     |     +--ro tx-plain-frames?               uint64
     |     +--ro tx-plain-octets?               uint64
     |     +--ro tx-plain-segments?             uint64
     |     +--ro tx-ploam-ds-ranging-time?      uint64
     |     +--ro tx-rate-bps?                   uint64
     |     +--ro tx-total-octets?               uint64
     |     +--ro tx-unicast-octets?             uint64
     |     +--ro tx-upstream-slots?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_FEC_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_FEC_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                      uint16
     |     +--ro corrected-bytes?            uint64
     |     +--ro corrected-code-words?       uint64
     |     +--ro fec-seconds?                uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro threshold-data-half-id?     uint64
     |     +--ro total-code-words?           uint64
     |     +--ro uncorrectable-code-words?   uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ENHANCED_TC_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ENHANCED_TC_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                      uint16
     |     +--ro lods-event-count?                           uint64
     |     +--ro lods-event-restored-count?                  uint64
     |     +--ro fragment-xgem-frames?                       uint64
     |     +--ro interval-end-time?                          uint64
     |     +--ro onu-reactivation-by-lods-events?            uint64
     |     +--ro psbd-hec-error-count?                       uint64
     |     +--ro received-bytes-in-nonidle-xgem-frames?      uint64
     |     +--ro transmitted-bytes-in-nonidle-xgem-frames?   uint64
     |     +--ro transmitted-xgem-frames?                    uint64
     |     +--ro unknown-profile-count?                      uint64
     |     +--ro xgem-hec-lost-words-count?                  uint64
     |     +--ro xgem-key-errors?                            uint64
     |     +--ro xgem-hec-error-count?                       uint64
     |     +--ro xgtc-hec-error-count?                       uint64
     |     +--ro threshold-data-64-bit-id?                   uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                      -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                        uint16
     |     +--ro direction?                    enumeration
     |     +--ro broadcast-frames?             uint64
     |     +--ro crc-errored-frames?           uint64
     |     +--ro drop-events?                  uint64
     |     +--ro frames?                       uint64
     |     +--ro frames-1024-to-1518-octets?   uint64
     |     +--ro frames-128-to-255-octets?     uint64
     |     +--ro frames-256-to-511-octets?     uint64
     |     +--ro frames-512-to-1023-octets?    uint64
     |     +--ro frames-64-octets?             uint64
     |     +--ro frames-65-to-127-octets?      uint64
     |     +--ro interval-end-time?            uint64
     |     +--ro multicast-frames?             uint64
     |     +--ro octets?                       uint64
     |     +--ro oversize-frames?              uint64
     |     +--ro undersize-frames?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT_LIST* [onu-name onu-id]
     |     +--ro onu-name                      -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                        uint16
     |     +--ro direction?                    enumeration
     |     +--ro broadcast-frames?             uint64
     |     +--ro crc-errored-frames?           uint64
     |     +--ro drop-events?                  uint64
     |     +--ro frames?                       uint64
     |     +--ro frames-1024-to-1518-octets?   uint64
     |     +--ro frames-128-to-255-octets?     uint64
     |     +--ro frames-256-to-511-octets?     uint64
     |     +--ro frames-512-to-1023-octets?    uint64
     |     +--ro frames-64-octets?             uint64
     |     +--ro frames-65-to-127-octets?      uint64
     |     +--ro interval-end-time?            uint64
     |     +--ro multicast-frames?             uint64
     |     +--ro octets?                       uint64
     |     +--ro oversize-frames?              uint64
     |     +--ro undersize-frames?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_UPSTREAM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_UPSTREAM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                               -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                 uint16
     |     +--ro alignment-error-counter?               uint64
     |     +--ro buffer-overflows-on-receive?           uint64
     |     +--ro buffer-overflows-on-transmit?          uint64
     |     +--ro carrier-sense-error-counter?           uint64
     |     +--ro deferred-transmission-counter?         uint64
     |     +--ro excessive-collision-counter?           uint64
     |     +--ro fcs-errors?                            uint64
     |     +--ro frames-too-long?                       uint64
     |     +--ro internal-mac-receive-error-counter?    uint64
     |     +--ro internal-mac-transmit-error-counter?   uint64
     |     +--ro interval-end-time?                     uint64
     |     +--ro late-collision-counter?                uint64
     |     +--ro multiple-collisions-frame-counter?     uint64
     |     +--ro single-collision-frame-counter?        uint64
     |     +--ro sqe-counter?                           uint64
     |     +--ro threshold-data-half-id?                uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM3
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM3_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro drop-events?                   uint64
     |     +--ro fragments?                     uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro jabbers?                       uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_GAL_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_GAL_ETHERNET_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro discarded-downstream-frames?   uint64
     |     +--ro discarded-upstream-frames?     uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro threshold-data-half-id?        uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_GEM_PORT_NETWORK_CTP_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_GEM_PORT_NETWORK_CTP_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                     -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                       uint16
     |     +--ro encryption-key-errors?       uint64
     |     +--ro interval-end-time?           uint64
     |     +--ro received-gem-frames?         uint64
     |     +--ro received-payload-bytes?      uint64
     |     +--ro threshold-data-half-id?      uint64
     |     +--ro transmitted-gem-frames?      uint64
     |     +--ro transmitted-payload-bytes?   uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_IP_HOST_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_IP_HOST_PERF_MON_HIST_DATA_LIST* [onu-name onu-id]
     |     +--ro onu-name                  -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                    uint16
     |     +--ro dns-errors?               uint64
     |     +--ro dhcp-timeouts?            uint64
     |     +--ro icmp-errors?              uint64
     |     +--ro internal-error?           uint64
     |     +--ro interval-end-time?        uint64
     |     +--ro ip-address-conflict?      uint64
     |     +--ro out-of-memory?            uint64
     |     +--ro threshold-data-half-id?   uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_OPERATIONAL_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_OPERATIONAL_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                            uint16
     |     +--ro cpu-percent-utilization?          uint64
     |     +--ro errors-in-operations?             uint64
     |     +--ro flash-size-available?             uint64
     |     +--ro flash-utilization?                uint64
     |     +--ro interval-end-time?                uint64
     |     +--ro ram-size-available?               uint64
     |     +--ro ram-utilization?                  uint64
     |     +--ro software-errors?                  uint64
     |     +--ro threshold-data-half-id?           uint64
     |     +--ro temperature-sensor-description?   uint64
     |     +--ro temperature-sensor-value?         uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_MAC_BRIDGE_PORT_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_MAC_BRIDGE_PORT_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                          -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                            uint16
     |     +--ro delay-exceeded-discard-counter?   uint64
     |     +--ro forwarded-frame-counter?          uint64
     |     +--ro interval-end-time?                uint64
     |     +--ro mtu-exceeded-discard-counter?     uint64
     |     +--ro received-and-discarded-counter?   uint64
     |     +--ro received-frame-counter?           uint64
     |     +--ro threshold-data-half-id?           uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_RS232_RS485_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_RS232_RS485_PERF_MON_HIST_DATA_LIST* [onu-name onu-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                      uint16
     |     +--ro incoming-bytes-from-chip?   uint64
     |     +--ro incoming-bytes-from-pon?    uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro outgoing-bytes-from-chip?   uint64
     |     +--ro outgoing-bytes-from-pon?    uint64
     |     +--ro threshold-data-half-id?     uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_TCP_UDP_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_TCP_UDP_PERF_MON_HIST_DATA_LIST* [onu-name onu-id]
     |     +--ro onu-name                  -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                    uint16
     |     +--ro accept-failed?            uint64
     |     +--ro bind-failed?              uint64
     |     +--ro interval-end-time?        uint64
     |     +--ro listen-failed?            uint64
     |     +--ro select-failed?            uint64
     |     +--ro socket-failed?            uint64
     |     +--ro threshold-data-half-id?   uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_DOWNSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_DOWNSTREAM_MGMT_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                                   -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                     uint16
     |     +--ro interval-end-time?                         uint64
     |     +--ro threshold-data-half-id?                    uint64
     |     +--ro ploam-mic-error-count?                     uint64
     |     +--ro downstream-ploam-message-count?            uint64
     |     +--ro profile-messages-received?                 uint64
     |     +--ro ranging-time-messages-received?            uint64
     |     +--ro deactivate-onu-id-messages-received?       uint64
     |     +--ro disable-serial-number-messages-received?   uint64
     |     +--ro request-registration-messages-received?    uint64
     |     +--ro assign-alloc-id-messages-received?         uint64
     |     +--ro key-control-messages-received?             uint64
     |     +--ro sleep-allow-messages-received?             uint64
     |     +--ro baseline-omci-messages-received-count?     uint64
     |     +--ro extended-omci-messages-received-count?     uint64
     |     +--ro assign-onu-id-omci-messages-received?      uint64
     |     +--ro omci-mic-error-count?                      uint64
     +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_UPSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_UPSTREAM_MGMT_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                        -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                          uint16
     |     +--ro interval-end-time?              uint64
     |     +--ro threshold-data-half-id?         uint64
     |     +--ro upstream-ploam-message-count?   uint64
     |     +--ro serial-number-message-count?    uint64
     |     +--ro registration-message-count?     uint64
     |     +--ro key-report-message-count?       uint64
     |     +--ro acknowledge-message-count?      uint64
     |     +--ro sleep-request-message-count?    uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                               -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                 uint16
     |     +--ro alignment-error-counter?               uint64
     |     +--ro buffer-overflows-on-receive?           uint64
     |     +--ro buffer-overflows-on-transmit?          uint64
     |     +--ro carrier-sense-error-counter?           uint64
     |     +--ro deferred-transmission-counter?         uint64
     |     +--ro excessive-collision-counter?           uint64
     |     +--ro fcs-errors?                            uint64
     |     +--ro frames-too-long?                       uint64
     |     +--ro internal-mac-receive-error-counter?    uint64
     |     +--ro internal-mac-transmit-error-counter?   uint64
     |     +--ro interval-end-time?                     uint64
     |     +--ro late-collision-counter?                uint64
     |     +--ro multiple-collisions-frame-counter?     uint64
     |     +--ro single-collision-frame-counter?        uint64
     |     +--ro sqe-counter?                           uint64
     |     +--ro threshold-data-half-id?                uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_UPSTREAM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_UPSTREAM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro broadcast-packets?             uint64
     |     +--ro crc-errored-packets?           uint64
     |     +--ro drop-events?                   uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro multicast-packets?             uint64
     |     +--ro octets?                        uint64
     |     +--ro oversize-packets?              uint64
     |     +--ro packets?                       uint64
     |     +--ro packets-1024-to-1518-octets?   uint64
     |     +--ro packets-128-to-255-octets?     uint64
     |     +--ro packets-256-to-511-octets?     uint64
     |     +--ro packets-512-to-1023-octets?    uint64
     |     +--ro packets-64-octets?             uint64
     |     +--ro packets-65-to-127-octets?      uint64
     |     +--ro threshold-data-half-id?        uint64
     |     +--ro undersize-packets?             uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_RS232_RS485_PERF_MON_HIST_DATA
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_RS232_RS485_PERF_MON_HIST_DATA_LIST* [onu-name onu-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                      uint16
     |     +--ro incoming-bytes-from-chip?   uint64
     |     +--ro incoming-bytes-from-pon?    uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro outgoing-bytes-from-chip?   uint64
     |     +--ro outgoing-bytes-from-pon?    uint64
     |     +--ro threshold-data-half-id?     uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_GAL_ETHERNET_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_GAL_ETHERNET_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                       -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                         uint16
     |     +--ro discarded-downstream-frames?   uint64
     |     +--ro discarded-upstream-frames?     uint64
     |     +--ro interval-end-time?             uint64
     |     +--ro threshold-data-half-id?        uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_GEM_PORT_NETWORK_CTP_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_GEM_PORT_NETWORK_CTP_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                     -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                       uint16
     |     +--ro encryption-key-errors?       uint64
     |     +--ro interval-end-time?           uint64
     |     +--ro received-gem-frames?         uint64
     |     +--ro received-payload-bytes?      uint64
     |     +--ro threshold-data-half-id?      uint64
     |     +--ro transmitted-gem-frames?      uint64
     |     +--ro transmitted-payload-bytes?   uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_ENHANCED_TC_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_ENHANCED_TC_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                      uint16
     |     +--ro lods-event-count?                           uint64
     |     +--ro lods-event-restored-count?                  uint64
     |     +--ro fragment-xgem-frames?                       uint64
     |     +--ro interval-end-time?                          uint64
     |     +--ro onu-reactivation-by-lods-events?            uint64
     |     +--ro psbd-hec-error-count?                       uint64
     |     +--ro received-bytes-in-nonidle-xgem-frames?      uint64
     |     +--ro transmitted-bytes-in-nonidle-xgem-frames?   uint64
     |     +--ro transmitted-xgem-frames?                    uint64
     |     +--ro unknown-profile-count?                      uint64
     |     +--ro xgem-hec-lost-words-count?                  uint64
     |     +--ro xgem-key-errors?                            uint64
     |     +--ro xgem-hec-error-count?                       uint64
     |     +--ro xgtc-hec-error-count?                       uint64
     |     +--ro threshold-data-64-bit-id?                   uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_DOWNSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_DOWNSTREAM_MGMT_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                                   -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                                     uint16
     |     +--ro interval-end-time?                         uint64
     |     +--ro threshold-data-half-id?                    uint64
     |     +--ro ploam-mic-error-count?                     uint64
     |     +--ro downstream-ploam-message-count?            uint64
     |     +--ro profile-messages-received?                 uint64
     |     +--ro ranging-time-messages-received?            uint64
     |     +--ro deactivate-onu-id-messages-received?       uint64
     |     +--ro disable-serial-number-messages-received?   uint64
     |     +--ro request-registration-messages-received?    uint64
     |     +--ro assign-alloc-id-messages-received?         uint64
     |     +--ro key-control-messages-received?             uint64
     |     +--ro sleep-allow-messages-received?             uint64
     |     +--ro baseline-omci-messages-received-count?     uint64
     |     +--ro extended-omci-messages-received-count?     uint64
     |     +--ro assign-onu-id-omci-messages-received?      uint64
     |     +--ro omci-mic-error-count?                      uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_UPSTREAM_MGMT_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_UPSTREAM_MGMT_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                        -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                          uint16
     |     +--ro interval-end-time?              uint64
     |     +--ro threshold-data-half-id?         uint64
     |     +--ro upstream-ploam-message-count?   uint64
     |     +--ro serial-number-message-count?    uint64
     |     +--ro registration-message-count?     uint64
     |     +--ro key-report-message-count?       uint64
     |     +--ro acknowledge-message-count?      uint64
     |     +--ro sleep-request-message-count?    uint64
     +--ro PON_ONU_STATISTICS_STREAMING_ONU_FEC_PM
     |  +--ro PON_ONU_STATISTICS_STREAMING_ONU_FEC_PM_LIST* [onu-name onu-id]
     |     +--ro onu-name                    -> /sonic-pon/PON_ONU_STATE/PON_ONU_STATE_LIST/onu-name
     |     +--ro onu-id                      uint16
     |     +--ro corrected-bytes?            uint64
     |     +--ro corrected-code-words?       uint64
     |     +--ro fec-seconds?                uint64
     |     +--ro interval-end-time?          uint64
     |     +--ro threshold-data-half-id?     uint64
     |     +--ro total-code-words?           uint64
     |     +--ro uncorrectable-code-words?   uint64
     +--ro PON_FIRMWARE_FILENAME_STATE
     |  +--ro PON_FIRMWARE_FILENAME_STATE_LIST* [filename]
     |     +--ro filename    string
     +--ro PON_OLT_PLUG_STATE
        +--ro PON_OLT_PLUG_STATE_LIST* [name]
           +--ro name                          -> /sonic-pon/PON_OLT_INTF_STATE/PON_OLT_INTF_STATE_LIST/olt-name
           +--ro fw-bank-ptr?                  uint16
           +--ro fw-version?                   string
           +--ro hardware-version?             string
           +--ro manufacturer?                 string
           +--ro manufacturer-model?           string
           +--ro manufacturer-serial-number?   string
           +--ro model?                        string
           +--ro online-time?                  yang:date-and-time
           +--ro production-code?              string
           +--ro serial-number?                string
           +--ro uptime?                       uint64
           +--ro switch-chassis-id?            string
           +--ro switch-ipv4-address?          string
           +--ro switch-ipv6-address?          string
           +--ro switch-port-description?      string
           +--ro switch-port-id?               string
           +--ro switch-system-description?    string
           +--ro switch-system-name?           string
           +--ro fw-upgrade-bank?              uint16
           +--ro fw-upgrade-fx-code?           uint32
           +--ro fw-upgrade-file?              string
           +--ro fw-upgrade-status?            string
           +--ro fw-upgrade-duration?          string
           +--ro fw-upgrade-time?              yang:date-and-time
           +--ro hw-failure?                   string
```

## CONFIG_DB

### `PON_CONTROLLER`

- **Key:** `controller-name`
- **Description:** List of PON Controller configuration records.

| Field | Type | Description |
| --- | --- | --- |
| `controller-name` *(key)* | string (length 0..256) | Name identifier used by the NETCONF interface to reference this PON Controller. |
| `device-id` | string (mandatory) | PON Controller identifier (PON Controller MAC Address or 'Default'). |
| `allow-unprovisioned-onus` | boolean (default true) | Allow unprovisioned ONUs to complete registration with PON Controller. When false, the controller only allows ONUs that have been inventoried on an OLT to complete registration. |
| `create-date` | date-and-time | User configurable timestamp to record the date and time of when device was created. |
| `olt-timeout` | uint32 (default 300) | The amount of time for OLT to be locked to a controller. If an OLT doesn't receive OAM from the PON Controller in this time period, it will release its lock to allow another PON controller to manage it. |
| `statistics-sample` | uint32 (units seconds; default 300) | Minimum time between OLT statistic samples. After this amount of time, statistics will be gathered for the network devices. |
| `logging-controller-console` | logging-level (enum: emergency, alert, critical, error, warning, notice, …; default info) | Severity level for log messages sent to the console. |
| `logging-controller-file` | logging-level (enum: emergency, alert, critical, error, warning, notice, …; default info) | Severity level for log messages sent to the log file. |
| `logging-controller-syslog` | logging-level (enum: emergency, alert, critical, error, warning, notice, …; default info) | Severity level for log messages sent to the Syslog. |
| `logging-controller-database` | logging-level (enum: emergency, alert, critical, error, warning, notice, …; default info) | Severity level for logs messages sent to the database. |
| `logging-olt-console` | logging-enable (enum: enable, disable; default disable) | Enable log messages sent to the console. |
| `logging-olt-file` | logging-enable (enum: enable, disable; default disable) | Enable log messages sent to the log file. |
| `logging-olt-syslog` | logging-enable (enum: enable, disable; default disable) | Enable log messages sent to the Syslog. |
| `olt-management-interface-name` | string |  |
| `unprovisioned-age` | uint32 (range 60..86400; units seconds; default 900) | The amount of time an ONU will be kept in the Unprovisioned ONUs list, when no longer attempting registration. |
| `refresh-state-on-olt-change` | boolean (default false) | When true, the PON Controller detects OLT changes by comparing the OLT-G OMCI ME 'equipment_id' attribute and performs a MIB Upload to refresh the current MIB data when a change is detected. |

### `PON_DOWNSTREAM_QOS_MAP_MAP`

- **Key:** `name`, `cos`
- **Description:** Mapping entry that classifies VLAN CoS bit values to a desinstation GPON XGEM Port or EPON LLID (OLT-Service) offset.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | string |  |
| `cos` *(key)* | uint8 (range 0..7) | VLAN CoS/Priority bit value for this classifier. |
| `olt-service-offset` | uint8 (range 0..7) | Destination GPON XGEM Port or EPON LLID offset that the start/end CoS values are classified to. |

### `PON_OLT_INTF`

- **Key:** `olt-name`, `port-id`
- **Description:** List of OLTs.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | string (length 0..256) | Name identifier used by the NETCONF interface to reference this OLT device. |
| `device-id` | string | OLT device identifier (OLT MAC Address or 'Default'). |
| `port-id` *(key)* | leafref → name |  |
| `pon-enable` | boolean (default false) | Enable the PON Optics on the module. |
| `discovery-period` | uint32 (range 0 \| 100..10000; units milliseconds; default 3000) | Amount of time between discovery slots on the PON. A setting of '0' will disable discovery. |
| `downstream-fec` | boolean (default true) | Enable Forward Error Correction in the downstream direction. |
| `encryption` | olt-encryption-mode (enum: disabled, bidirectional, broadcast, downstream; default disabled) | Enable the OLT for PON MAC layer encryption of data. |
| `encryption-key-time` | uint16 (range 60..3600; units seconds; default 600) | Time between changing encryption keys. |
| `error-detection-maximum-hec-ratio` | uint8 (range 0..100; units percent; default 20) | Maximum percentage of HEC errors to disable an ONU. |
| `error-detection-minimum-hec-sample` | uint16 (range 0..1000; units GPON headers; default 100) | Minimum number of HEC error samples to consider for error-detection-maximum-ratio. |
| `error-detection-maximum-ratio` | uint8 (range 0..100; units percent; default 20) | Maximum percentage of errored upstream bursts to disable an ONU. |
| `error-detection-minimum-sample` | uint16 (range 0..1000; units Upstream Bursts; default 100) | Minimum number of upstream bursts to consider for error-detection-maximum-ratio. |
| `guard-time` | uint32 (range 16..1000; units upstream-slots(12.8ns); default 64) | Amount of dead time between upstream burst slots. The Guard Time should be enough for slot jitter and ONU laser off time. |
| `max-frame-size` | uint32 (range 1518..9600; units octets; default 9600) | Maximum frame size allowed at the PON receiver from DA to CRC32. |
| `pon-id` | uint32 (default 0) | Unique 32-bit value assigned to each PON. |
| `pon-tag` | string (length 0\|16) | PON-TAG description in burst profile message. |
| `aging-time` | uint16 (range 60..3600; units seconds; default 300) | Dynamic MAC Address aging time. When the aging time expires, the address is removed from the Dynamic MAC learning table. |

### `PON_OLT_INTF_NETWORK`

- **Key:** `olt-name`, `vlan-id`
- **Description:** List of networks to pre-define.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `network-id` | uint16 (range 0..999) | Index for this entry. |
| `learning-limit` | uint16 (range 0..2046; default 2046) | Dynamic MAC learning table size limit for this NNI Network. A value of '0' disables MAC Learning for this NNI Network. |
| `flooding-gemport-id` | uint16 (range 1154..1278\|1280..1534\|1919..2046\|5121..5374\|5376..5630\|5632..5886\|5888..6013) | Flooding (Broadcast DA, Multicast DA, unknown DA downstream packets) XGEM Port ID (XGS mode only) to use for this network. |
| `vlan-id` *(key)* | uint16 (range 0..4095) | VLAN id used to identify packets on the NNI network. |
| `flooding-sla-profile` | string | SLA profile for the flooding link on this NNI network. |

### `PON_OLT_INTF_ONU`

- **Key:** `olt-name`, `onu-serial-number`
- **Description:** EPON Mode: ONU MAC addresses for ONUs expected on this OLT. The LLID is automatically assigned in EPON mode. XGS-PON Mode: For each ONU (defined by Vendor ID + Vendor SN) and service port on the ONU, the Allocation ID to use for the service port. Use 65535 or don't specify for automatic assignment.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `onu-serial-number` *(key)* | string (length 0..256) | EPON Mode: ONU MAC address. XGS-PON Mode: ONU serial number (defined by Vendor ID + Vendor SN). |
| `onu-id` | uint16 (range 1..128) | XGS-PON Mode only: The allocation ID, XGEM port ID, and ONU ID number assigned to this ONU for carry OMCI management messages. |
| `disable` | boolean (default false) | When true, the disable serial number PLOAM message will be sent to this ONU if it tries to register. |

### `PON_OLT_INTF_ONU_OLT_SERVICE`

- **Key:** `olt-name`, `onu-serial-number`, `service-port-id`
- **Description:** List of OLT Service ports.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `onu-serial-number` *(key)* | leafref → onu-serial-number | References PON_OLT_INTF_ONU_LIST. |
| `service-port-id` *(key)* | uint32 (range 0..7) | OLT Service port number. |
| `unicast-id` | uint16 (range 1154..1278 \| 1280..1534) | EPON Mode: The LLID to use for the service port. Use 65535 or don't specify for automatic assignment. Valid LLID range is 5121..6013, excluding 5375, 5631, 5887. XGS-PON Mode: The Allocation ID to use for the service port. Use 65535 or don't specify for automatic assignment. Valid ALLOC-ID range is 1154..1534, excluding 1279. |

### `PON_OLT_INTF_ONU_SERVICE_GEMPORT`

- **Key:** `olt-name`, `onu-serial-number`, `olt-service-id`
- **Description:** List of OLT GEM ports.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `onu-serial-number` *(key)* | leafref → onu-serial-number | References PON_OLT_INTF_ONU_LIST. |
| `olt-service-id` *(key)* | uint32 (range 0..7) | OLT Service port number. |
| `gemport-id` | uint16 | GEM port ID for the service port. |
| `tcont-ref` | leafref → olt-service-id | References the TCONT entry associated with this GEM port. |

### `PON_OLT_INTF_ONU_SERVICE_TCONT`

- **Key:** `olt-name`, `onu-serial-number`, `olt-service-id`
- **Description:** List of OLT Service ports.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `onu-serial-number` *(key)* | leafref → onu-serial-number | References PON_OLT_INTF_ONU_LIST. |
| `olt-service-id` *(key)* | uint32 (range 0..7) | OLT Service port number. |
| `alloc-id` | uint16 (range 1154..1278 \| 1280..1534) | EPON Mode: The LLID to use for the service port. Use 65535 or don't specify for automatic assignment. Valid LLID range is 5121..6013, excluding 5375, 5631, 5887. XGS-PON Mode: The Allocation ID to use for the service port. Use 65535 or don't specify for automatic assignment. Valid ALLOC-ID range is 1154..1534, excluding 1279. |

### `PON_OLT_PLUG`

- **Key:** `olt-name`
- **Description:** PON OLT plug attributes regrouped from PON_OLT_INTF.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `debug-log-level` | logging-level (enum: emergency, alert, critical, error, warning, notice, …; default disable) | Enables debug logging for this OLT. |
| `fw-bank-ptr` | uint16 (range 0..3\|65535; default 65535) | Firmware pointer to select bank (0 to 3) to be active on OLT. When this value changes, the OLT will be reset to load the firmware in the bank. |
| `nni-max-frame-size` | uint32 (range 1518..12500; default 9600) | Maximum number of frame bytes from the DA to CRC32 for NNI receive path. (EPON-1518 to 12500) (XGSPON-1518 to 9600). |

### `PON_OLT_PLUG_FW_BANK_FILE`

- **Key:** `olt-name`, `bank-id`
- **Description:** The database files to get firmware for the firmware banks on the OLT Module. The OLT module supports 4 banks of firmware. The list is ordered Bank0, Bank1, Bank2, and Bank3.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_LIST. |
| `bank-id` *(key)* | uint8 (range 0..3) | Index for this entry. |
| `file` | string (length 0..256) | Name of the firmware file. |
| `version` | string (length 0..256) | Name of the firmware file. |

### `PON_ONU`

- **Key:** `onu-name`
- **Description:** List of ONUs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | string (length 0..256) | Name identifier used by the NETCONF interface to reference this ONU device. |
| `device-id` | string (length 0..256; mandatory) | ONU device identifier (XGS-PON: Vendor + SSN; EPON, link MAC Address, or 'Default'). |
| `template-ref` | string | Reference to the ONU template to use for this ONU. |
| `vlan-id` | uint16 (range 0..4095) | VID for Add CTag service configuration. |
| `fw-bank-ptr` | uint16 (range 0..1\|65535; default 65535) | Current Firmware bank pointer. A value of '65535' disables ONU firmware upgrade. |
| `realtime-stats` | boolean (default false) | Enables the ONU state files to show all statistics on every cycle. |
| `service-config` | string (length 0..64; units 'Disabled' or 'Add CTag' or 'Unmodified' or <Service Config Name>; default Disabled) | ONU Service Configuration has 3 generic built-in modes and the ability to load a service configuration from the database. EPON supports 'Disabled' or 'Unmodified'. XGS supports all 3 configurations and service configuration files. |
| `service-config-omci-stats` | boolean (default false) | GPON ONLY: When set to true, no OMCI PM MEs will be automatically configured by the Controller. The PM MEs need to be specified in the ONU's SRV-CFG file. |
| `fw-upgrade-backoff-delay` | uint32 (range 1..10; units seconds; default 5) | Time to wait before retransmitting an window. |
| `fw-upgrade-backoff-divisor` | uint32 (range 1..2; default 2) | Controls the size of the send window during retransmissions. A value of '2' reduces the send window size by half for each retransmission. A value of '1' disables the backoff. |
| `fw-upgrade-download-format` | fw-download-format (enum: baseline-omci, extended-omci; default baseline-omci) | The format of OMCI the PON Controller will use to upgrade the ONU, regardless of the OMCC Version it reported. |
| `fw-upgrade-end-download-timeout` | uint32 (range 0..600; units seconds; default 0) | Time to wait for the final acknowledgement during firmware upgrade. Increase the value to the allow the ONU additional time to write the firmware image to flash. The PON Controller automatically calculates the end-download-timeout when set to a value of zero. |
| `fw-upgrade-maximum-retries` | uint32 (range 1..10; default 4) | Maximum number of times a window is retransmitted before terminating the ONU firmware upgrade and reporting an error. |
| `fw-upgrade-maximum-window-size` | uint32 (range 16..256; units bytes; default 64) | The maximum send window sized used for transfering firmware to the ONU. |
| `fw-upgrade-response-timeout` | uint32 (range 3..120; units seconds; default 3) | The time in seconds to wait for an acknowledgement from the ONU during firmware upgrade. |

### `PON_ONU_FW_BANK_FILE`

- **Key:** `onu-name`, `bank-id`
- **Description:** EPON: firmware source filename for firmware download if version doesn't match. XGS-PON: firmware source filenames for bank 0 (1st in list) and bank 1 if version doesn't match.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_LIST. |
| `bank-id` *(key)* | uint8 (range 0..1) | Index for this entry. |
| `file` | string (length 0..64) | Name of the firmware file. |
| `version` | string (length 0..64) | Version. |

### `PON_ONU_OLT_SERVICE`

- **Key:** `onu-name`, `olt-service-id`
- **Description:** OLT Configuration for the services. 0 to 7 services can be configured. A service is an XGEM Port ID/Alloc ID in XGS-PON or LLID in EPON.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_LIST. |
| `olt-service-id` *(key)* | uint32 (range 0..7) | OLT Service Port number. |
| `downstream-qos-map` | string (length 0..64) | Reference to a Downstream QoS Map. Used with multiple XGem configurations. |
| `enable` | boolean (default false) | True to enable this service port. False to disable it. |
| `learning-limit` | uint16 (range 0..2046; default 2046) | Dynamic MAC learning table size limit for this service port. A value of '0' disables MAC Learning for this service. |
| `sla-profile` | string (length 0..64; default Max) | Service level agreements for the service flow. |
| `tcont-service-ref` | string | none - OLT Service Port operates as a TCONT + XGem Port. GPON ONLY: TCONT OLT Service Port reference used to configure multiple XGem Ports for a single TCONT. When the value is set to a 'none', this OLT Service port operates as a TCONT + XGem Port. When the value references another OLT Service Port 0..7, this OLT Service port operates as an XGem Port only. When operating as an XGem only, this value must reference another OLT Service Port operating in TCONT + XGem mode. |

### `PON_ONU_OLT_SERVICE_NETWORK`

- **Key:** `onu-name`, `olt-service-id`, `vlan-id`
- **Description:** NNI (switch interface) Networks List of NNI VLAN network(s) through the service flow. VLAN Networks are defined by the SVLAN VID and two CVLAN VIDs. PON Networks for this service flow. List of PON VLAN network(s) through service flow. VLAN Networks are defined by the SVLAN VID and two CVLAN VIDs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_LIST. |
| `olt-service-id` *(key)* | leafref → olt-service-id | References PON_ONU_OLT_SERVICE_LIST. |
| `network-id` | uint16 (range 0..999) | Index for this entry. |
| `vlan-id` *(key)* | uint16 (range 0..4095) | VID for Add CTag service configuration. |

### `PON_ONU_SERVICE_CONFIG_VALUE`

- **Key:** `onu-name`, `cfg-name`
- **Description:** Service configuration file parameter 'onu-name' = 'value' pairs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_LIST. |
| `cfg-name` *(key)* | pon-string64nz | Name of the service configuration parameter (e.g., 'CVID UNI'). |
| `value` | union (mandatory) | Service configuration parameter value. |
| `value-type` | service-config-value-type (enum: array, automatic, boolean, double, int32, int64, …; default int32) | Defines the data type for the 'value' attribute. |

### `PON_ONU_TEMPLATE_OLT_SERVICE`

- **Key:** `onu-template-name`, `olt-service-id`
- **Description:** OLT Configuration for the services. 0 to 7 services can be configured. A service is an XGEM Port ID/Alloc ID in XGS-PON or LLID in EPON.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | string |  |
| `olt-service-id` *(key)* | uint32 (range 0..7) | OLT Service Port number. |
| `downstream-qos-map` | string (length 0..64) | Reference to a Downstream QoS Map. Used with multiple XGem configurations. |
| `enable` | boolean (default false) | True to enable this service port. False to disable it. |
| `learning-limit` | uint16 (range 0..2046; default 2046) | Dynamic MAC learning table size limit for this service port. A value of '0' disables MAC Learning for this service. |
| `sla-profile` | string (length 0..64; default Max) | Service level agreements for the service flow. |
| `tcont-service-ref` | string | none - OLT Service Port operates as a TCONT + XGem Port. GPON ONLY: TCONT OLT Service Port reference used to configure multiple XGem Ports for a single TCONT. When the value is set to a 'none', this OLT Service port operates as a TCONT + XGem Port. When the value references another OLT Service Port 0..7, this OLT Service port operates as an XGem Port only. When operating as an XGem only, this value must reference another OLT Service Port operating in TCONT + XGem mode. |

### `PON_ONU_TEMPLATE_OLT_SERVICE_NETWORK`

- **Key:** `onu-template-name`, `olt-service-id`, `vlan-id`
- **Description:** NNI (switch interface) Networks List of C-VLAN ID(s) through the service flow. VLAN Networks are defined by the SVLAN VID and two CVLAN VIDs. PON Networks for this service flow. List of PON VLAN network(s) through service flow. VLAN Networks are defined by the SVLAN VID and two CVLAN VIDs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | string |  |
| `olt-service-id` *(key)* | leafref → olt-service-id | References PON_ONU_TEMPLATE_OLT_SERVICE_LIST. |
| `network-id` | uint16 (range 0..999) | Index for this entry. |
| `vlan-id` *(key)* | uint16 (range 0..4095) | VID for Add CTag service configuration. |

### `PON_ONU_TEMPLATE_ONU`

- **Key:** `onu-template-name`
- **Description:** ONU specific settings.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | string | References PON_ONU_TEMPLATE_LIST. |
| `vlan-id` | uint16 (range 0..4095) | VID for Add CTag service configuration. |
| `fw-bank-ptr` | uint16 (range 0..1\|65535; default 65535) | Current Firmware bank pointer. A value of '65535' disables ONU firmware upgrade. |
| `service-config` | string (length 0..64; units 'Disabled' or 'Add CTag' or 'Unmodified' or <Service Config Name>; default Disabled) | ONU Service Configuration has 3 generic built-in modes and the ability to load a service configuration from the database. EPON supports 'Disabled' or 'Unmodified'. XGS supports all 3 configurations and service configuration files. |
| `service-config-omci-stats` | boolean (default false) | GPON ONLY: When set to true, no OMCI PM MEs will be automatically configured by the Controller. The PM MEs need to be specified in the ONU's SRV-CFG file. |
| `fw-upgrade-backoff-delay` | uint32 (range 1..10; units seconds; default 5) | Time to wait before retransmitting an window. |
| `fw-upgrade-backoff-divisor` | uint32 (range 1..2; default 2) | Controls the size of the send window during retransmissions. A value of '2' reduces the send window size by half for each retransmission. A value of '1' disables the backoff. |
| `fw-upgrade-download-format` | fw-download-format (enum: baseline-omci, extended-omci; default baseline-omci) | The format of OMCI the PON Controller will use to upgrade the ONU, regardless of the OMCC Version it reported. |
| `fw-upgrade-end-download-timeout` | uint32 (range 0..600; units seconds; default 0) | Time to wait for the final acknowledgement during firmware upgrade. Increase the value to the allow the ONU additional time to write the firmware image to flash. The PON Controller automatically calculates the end-download-timeout when set to a value of zero. |
| `fw-upgrade-maximum-retries` | uint32 (range 1..10; default 4) | Maximum number of times a window is retransmitted before terminating the ONU firmware upgrade and reporting an error. |
| `fw-upgrade-maximum-window-size` | uint32 (range 16..256; units bytes; default 64) | The maximum send window sized used for transfering firmware to the ONU. |
| `fw-upgrade-response-timeout` | uint32 (range 3..120; units seconds; default 3) | The time in seconds to wait for an acknowledgement from the ONU during firmware upgrade. |

### `PON_ONU_TEMPLATE_ONU_FW_BANK_FILE`

- **Key:** `onu-template-name`, `bank-id`
- **Description:** EPON: firmware source filename for firmware download if version doesn't match. XGS-PON: firmware source filenames for bank 0 (1st in list) and bank 1 if version doesn't match.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | leafref → onu-template-name | References PON_ONU_TEMPLATE_ONU_LIST. |
| `bank-id` *(key)* | uint8 (range 0..1) | Index for this entry. |
| `file` | string (length 0..64) | Name of the firmware file. |
| `version` | string (length 0..64) | Version. |

### `PON_ONU_TEMPLATE_SERVICE_CONFIG_VALUE`

- **Key:** `onu-template-name`, `cfg-name`
- **Description:** Service configuration file parameter 'onu-template-name' = 'value' pairs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | string |  |
| `cfg-name` *(key)* | pon-string64nz | Name of the service configuration parameter (e.g., 'CVID UNI'). |
| `value` | union (mandatory) | Service configuration parameter value. |
| `value-type` | service-config-value-type (enum: array, automatic, boolean, double, int32, int64, …; default int32) | Defines the data type for the 'value' attribute. |

### `PON_ONU_TEMPLATE_UNI`

- **Key:** `onu-template-name`, `port-id`
- **Description:** Configurations for the UNI ports on the ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-template-name` *(key)* | string |  |
| `port-id` *(key)* | string | Identifier for this UNI port. |
| `duplex` | duplex-mode (enum: auto, full, half; default auto) | Sets the duplex for the Ethernet port. |
| `enable` | boolean | Admin enable or disable for the UNI port. |
| `max-frame-size` | uint32 (default 2000) | Set the maximum frame size on UNI port. |
| `poe` | boolean (default false) | GPON ONLY: Enable Power over Ethernet (PoE) on the UNI port. |
| `speed` | speed-mode (enum: auto, 10, 100, 1000, 2500, 5000, …; default auto) | Sets the speed of the Ethernet port. |

### `PON_ONU_UNI`

- **Key:** `onu-name`, `port-id`
- **Description:** Configurations for the UNI ports on the ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_LIST. |
| `port-id` *(key)* | string | Identifier for this UNI port. |
| `duplex` | duplex-mode (enum: auto, full, half; default auto) | Sets the duplex for the Ethernet port. |
| `enable` | boolean | Admin enable or disable for the UNI port. |
| `max-frame-size` | uint32 (default 2000) | Set the maximum frame size on UNI port. |
| `poe` | boolean (default false) | GPON ONLY: Enable Power over Ethernet (PoE) on the UNI port. |
| `speed` | speed-mode (enum: auto, 10, 100, 1000, 2500, 5000, …; default auto) | Sets the speed of the Ethernet port. |

### `PON_SERVICE_CONFIG_PROFILE_ANI_G`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ANI_G_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string | Service configuration profile identifier that scopes ANI-G managed entities. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID for ANI-G. The value indicates the physical position of the PON interface. |
| `gem-block-length` | omci-uint16 | Queue occupancy reporting granularity for DBA, expressed in bytes. |
| `sf-threshold` | omci-uint8 | Signal fail BER threshold exponent y, where threshold is 10^(-y). |
| `sd-threshold` | omci-uint8 | Signal degrade BER threshold exponent x, where threshold is 10^(-x). |
| `arc` | omci-uint8 | Alarm-reporting control (ARC) value. |
| `arc-interval` | omci-uint8 | Alarm-reporting control interval. |
| `lower-optical-threshold` | omci-uint8 | Lower received optical power threshold used for low-power alarm detection. |
| `upper-optical-threshold` | omci-uint8 | Upper received optical power threshold used for high-power alarm detection. |
| `lower-transmit-power-threshold` | omci-uint8 | Lower transmit optical launch power threshold for low transmit power alarm. |
| `upper-transmit-power-threshold` | omci-uint8 | Upper transmit optical launch power threshold for high transmit power alarm. |

### `PON_SERVICE_CONFIG_PROFILE_CARDHOLDER`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_CARDHOLDER_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string | Service configuration profile identifier that scopes Cardholder managed entities. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID that uniquely identifies the Cardholder instance. |
| `expected-plugin-unit-type` | omci-uint8 | Provisioned expected circuit pack type for the slot. |
| `expected-port-count` | omci-uint8 | Expected number of ports in the circuit pack. |
| `expected-equipment-id` | omci-string | Expected specific equipment identifier for the circuit pack. |
| `invoke-protection-switch` | omci-uint8 | Protection switching control value used by OLT to control protection state. |
| `arc` | omci-uint8 | Alarm-reporting control (ARC) value. |
| `arc-interval` | omci-uint8 | Alarm-reporting control interval. |

### `PON_SERVICE_CONFIG_PROFILE_CIRCUIT_PACK`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_CIRCUIT_PACK_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string | Service configuration profile identifier that scopes Circuit pack managed entities. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID that uniquely identifies the Circuit pack instance. |
| `administrative-state` | omci-uint8 | Administrative state of this circuit pack instance (for example lock or unlock). |
| `bridged-or-ip-ind` | omci-uint8 | Indicates whether an Ethernet interface is bridged, IP router based, or both. |
| `card-configuration` | omci-uint8 | Configuration selector for configurable circuit pack variants. |
| `power-sched-override` | omci-uint32 | Power shed override mask controlling ports excluded from power shedding. |

### `PON_SERVICE_CONFIG_PROFILE_ENHANCED_FEC_PM_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ENHANCED_FEC_PM_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string | Service configuration profile identifier that scopes Enhanced FEC PM entities. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID linked to ANI-G or TWDM channel context. |
| `threshold-data-64-bit-id` | omci-uint16 | Reference to threshold data 64-bit managed entity containing PM thresholds. |

### `PON_SERVICE_CONFIG_PROFILE_ENHANCED_TC_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ENHANCED_TC_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string | Service configuration profile identifier that scopes Enhanced TC PM entities. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID linked to ANI-G context for this PM instance. |
| `threshold-data-64-bit-id` | omci-uint16 | Reference to threshold data 64-bit managed entity containing PM thresholds. |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_FRAME_EXTENDED_PM_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. To facilitate discovery, the identification of instances sequentially starting with 1 is encouraged. (R, set-by-create) (mandatory) (2 bytes). |
| `threshold-data-id` | omci-uint16 | threshold data id. |
| `parent-me-class` | omci-uint16 | parent me class. |
| `parent-me-instance` | omci-uint16 | parent me instance. |
| `accumulation-disable` | omci-uint16 | accumulation disable. |
| `tca-disable` | omci-uint16 | tca disable. |
| `control-fields` | omci-uint16 | control fields. |
| `tci` | omci-uint16 | tci. |
| `reserved` | omci-uint16 | reserved. |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_EXTENDED_PM64_BIT`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_FRAME_EXTENDED_PM64_BIT_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. To facilitate discovery, it is encouraged to identify instances sequentially starting with 1. (R, set-by-create) (mandatory) (2 bytes). |
| `threshold-data-id` | omci-uint16 | threshold data id. |
| `parent-me-class` | omci-uint16 | parent me class. |
| `parent-me-instance` | omci-uint16 | parent me instance. |
| `accumulation-disable` | omci-uint16 | accumulation disable. |
| `tca-disable` | omci-uint16 | tca disable. |
| `control-fields` | omci-uint16 | control fields. |
| `tci` | omci-uint16 | tci. |
| `reserved` | omci-uint16 | reserved. |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_DOWNSTREAM`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_FRAME_PERF_MON_HIST_DATA_DOWNSTREAM_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of a MAC bridge port configuration data. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_FRAME_PERF_MON_HIST_DATA_UPSTREAM`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_FRAME_PERF_MON_HIST_DATA_UPSTREAM_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of a MAC bridge port configuration data. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the PPTP Ethernet UNI. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 and 2 MEs that contains PM threshold values. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_ETHERNET_PERF_MON_HIST_DATA3`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ETHERNET_PERF_MON_HIST_DATA3_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the PPTP Ethernet UNI. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute provides a unique number for each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `association-type` | omci-uint8 | Association type: This attribute identifies the type of the ME associated with this extended VLAN tagging ME. Values are assigned as follows. 0 MAC bridge port configuration data 1 IEEE 802.1p mapper service profile 2 Physical path termination point Ethernet UNI 3 IP host config data or IPv6 host config data 4 Physical path termination point xDSL UNI 5 GEM IW termination point 6 Multicast GEM IW termination point 7 Physical path termination point MoCA UNI 8 Reserved 9 Ethernet flow termination point 10 Virtual Ethernet interface point 11 MPLS pseudowire termination point 12 EFM bonding group (R,W, set-by-create) (mandatory) (1byte) NOTE 1 If a MAC bridge is configured, code points 1, 5, 6 and 11 are associated with the ANI side of the MAC bridge. Code point 0 is associated with the ANI or UNI side, depending on the location of the MAC bridge port. The other code points are associated with the UNI side. When the extended VLAN tagging ME is associated with the ANI side, it behaves as an upstream egress rule, and as a downstream ingress rule when the downstream mode attribute is equal to 0. When the extended VLAN tagging ME is associated with the UNI side, the extended VLAN tagging ME behaves as an upstream ingress rule, and as a downstream egress rule when the downstream mode attribute is equal to 0. |
| `input-tpid` | omci-uint16 | Input TPID: This attribute gives the special TPID value for operations on the input (filtering) side of the table. Typical values include 0x88A8 and 0x9100. (R,W) (mandatory) (2bytes). |
| `output-tpid` | omci-uint16 | Output TPID: This attribute gives the special TPID value for operations on the output (tagging) side of the table. Typical values include 0x88A8 and 0x9100. (R,W) (mandatory) (2bytes). |
| `downstream-mode` | omci-uint8 |  |
| `associated-me-pointer` | omci-uint16 | Associated ME pointer: This attribute points to the ME with which this extended VLAN tagging operation configuration data ME is associated. (R,W, set-by- create) (mandatory) (2bytes) NOTE 5 When the association type is xDSL, the two MSBs may be used to indicate a bearer channel. |

### `PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_DSCP_TO_PBIT_MAPPING_DSCP_TO_PBIT_MAPPING_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `dscp`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_MANAGED_ENTITY_DSCP_TO_PBIT_MAPPING_DSCP_TO_PBIT_MAPPING_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute provides a unique number for each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `dscp` *(key)* | uint8 | DSCP Value. |
| `priority` | uint8 | P-bit value. |

### `PON_SERVICE_CONFIG_PROFILE_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `received-frame-vlan-tagging-operation-table-entry-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_EXTENDED_VLAN_TAGGING_OPERATION_CONFIGURATION_DATA_MANAGED_ENTITY_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_RECEIVED_FRAME_VLAN_TAGGING_OPERATION_TABLE_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute provides a unique number for each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `received-frame-vlan-tagging-operation-table-entry-id` *(key)* | uint8 |  |
| `filter-outer-priority` | omci-uint16 | filter outer priority. |
| `filter-outer-vid` | omci-uint16 | filter outer vid. |
| `filter-outer-tpid-de` | omci-uint16 | filter outer tpid de. |
| `pad1` | omci-uint16 | pad1. |
| `filter-inner-priority` | omci-uint16 | filter inner priority. |
| `filter-inner-vid` | omci-uint16 | filter inner vid. |
| `filter-inner-tpid-de` | omci-uint16 | filter inner tpid de. |
| `pad2` | omci-uint16 | pad2. |
| `filter-ether-type` | omci-uint16 | filter ether type. |
| `treatment-tags-to-remove` | omci-uint16 | treatment tags to remove. |
| `pad3` | omci-uint16 | pad3. |
| `treatment-outer-priority` | omci-uint16 | treatment outer priority. |
| `treatment-outer-vid` | omci-uint16 | treatment outer vid. |
| `treatment-outer-tpid-de` | omci-uint16 | treatment outer tpid de. |
| `pad4` | omci-uint16 | pad4. |
| `treatment-inner-priority` | omci-uint16 | treatment inner priority. |
| `treatment-inner-vid` | omci-uint16 | treatment inner vid. |
| `treatment-inner-tpid-de` | omci-uint16 | treatment inner tpid de. |

### `PON_SERVICE_CONFIG_PROFILE_FEC_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_FEC_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the ANI-G or a TWDM channel. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_GAL_ETHERNET_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the GEM IW TP. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_GAL_ETHERNET_PROFILE`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_GAL_ETHERNET_PROFILE_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `max-gem-payload-size` | omci-uint16 | Maximum GEM payload size: This attribute defines the maximum payload size generated in the associated GEM IW TP ME. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_GEM_INTERWORKING_TP`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_GEM_INTERWORKING_TP_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `gem-port-network-ctp-pointer` | omci-uint16 | GEM port network CTP connectivity pointer: This attribute points to an instance of the GEM port network CTP. (R,W, set-by-create) (mandatory) (2bytes). |
| `interworking-option` | omci-uint8 | Interworking option: This attribute identifies the type of non-GEM function that is being interworked. The options are as follows. 0 Circuit-emulated TDM 1 MAC bridged LAN 2 Reserved 3 Reserved 4 Video return path 5 IEEE 802.1p mapper 6 Downstream broadcast 7 MPLS PW TDM service (R,W, set-by-create) (mandatory) (1byte). |
| `service-profile-pointer` | omci-uint16 | Service profile pointer: This attribute points to an instance of a service profile: CES service profile if IW option=0 MAC bridge service profile if IW option=1 Video return path service profile if IW option=4 IEEE 802.1p mapper service profile if IW option=5 Null pointer if IW option=6 CES service profile if IW option=7 (R,W, set-by-create) (mandatory) (2bytes) NOTE The video return path (VRP) service profile is defined in [ITU-T G.984.4]. |
| `interworking-tp-pointer` | omci-uint16 | Not used 1: This attribute is set to 0 and not used. (R,W, set-by-create) (mandatory) (2bytes). |
| `gal-profile-pointer` | omci-uint16 | GAL profile pointer: This attribute points to an instance of the GAL profile. The relationship between the IW option and the related GAL profile is as follows. Interworking option GAL profile type 0 Null pointer 1 GAL Ethernet profile 3 GAL Ethernet profile for data service 4 GAL Ethernet profile for video return path 5 GAL Ethernet profile for IEEE 802.1p mapper 6 Null pointer 7 Null pointer (R,W, set-by-create) (mandatory) (2bytes). |
| `gal-loopback-configuration` | omci-uint8 | GAL loopback configuration: This attribute sets the loopback configuration when using GEM mode: 0 No loopback 1 Loopback of downstream traffic after GAL The default value of this attribute is 0. When the IW option is 6 (downstream broadcast), this attribute is not used. (R,W) (mandatory) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_GEM_PORT_NETWORK_CTP_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `port-id` | omci-uint16 | Port-ID: This attribute is the port-ID of the GEM port associated with this CTP. (RWSC) (mandatory) (2bytes) NOTE 1 While nothing forbids the existence of several GEM port network CTPs with the same port-ID value, downstream traffic is modelled as being delivered to all such GEM port network CTPs. Be aware of potential difficulties associated with defining downstream flows and aggregating PM statistics. |
| `tcont-pointer` | omci-uint16 | T-CONT pointer: This attribute points to a T-CONT instance. (R,W, set-by- create) (mandatory) (2bytes). |
| `direction` | omci-uint8 | Direction: This attribute specifies whether the GEM port is used for UNI- to-ANI (1), ANI-to-UNI (2), or bidirectional (3) connection. (R,W, set-by- create) (mandatory) (1byte). |
| `traffic-management-pointer-upstream` | omci-uint16 | Traffic management pointer for upstream: If the traffic management option attribute in the ONU-G ME is 0 (priority controlled) or 2 (priority and rate controlled), this pointer specifies the priority queue ME serving this GEM port network CTP. If the traffic management option attribute is 1 (rate controlled), this attribute redundantly points to the T-CONT serving this GEM port network CTP. (R,W, set-by-create) (mandatory) (2bytes). |
| `traffic-descriptor-profile-pointer` | omci-uint16 | Traffic descriptor profile pointer for upstream: This attribute points to the instance of the traffic descriptor ME that contains the upstream traffic parameters for this GEM port network CTP. This attribute is used when the traffic management option attribute in the ONU-G ME is 1 (rate controlled), specifying the PIR/PBS to which the upstream traffic is shaped. This attribute is also used when the traffic management option attribute in the ONU-G ME is 2 (priority and rate controlled), specifying the CIR/CBS/PIR/PBS to which the upstream traffic is policed. (R,W, set-by-create) (optional) (2bytes) See also Appendix II. |
| `priority-queue-pointer-downstream` | omci-uint16 | Priority queue pointer for downstream: This attribute points to the instance of the priority queue used for this GEM port network CTP in the downstream direction. It is the responsibility of the OLT to provision the downstream pointer in a way that is consistent with the bridge and mapper connectivity. If the pointer is null, downstream queueing is determined by other mechanisms in the ONU. (R,W, set-by-create) (mandatory) (2bytes) NOTE 2 If the GEM port network CTP is associated with more than one UNI (downstream multicast), the downstream priority queue pointer defines a pattern (e.g., queue number 3 for a given UNI) to be replicated (i.e., to queue number 3) at the other affected UNIs. |
| `traffic-desc-profile-pointer-downstream` | omci-uint16 | Traffic descriptor profile pointer for downstream: This attribute points to the instance of the traffic descriptor ME that contains the downstream traffic parameters for this GEM port network CTP. This attribute is used when the traffic management option attribute in the ONU-G ME is 1 (rate controlled), specifying the PIR/PBS to which the downstream traffic is shaped. This attribute is also used when the traffic management option attribute in the ONU-G ME is 2 (priority and rate controlled), specifying the CIR/CBS/PIR/PBS to which the downstream traffic is policed. (R,W, set-by-create) (optional) (2bytes) See also Appendix II. |
| `encryption-key-ring` | omci-uint8 | Encryption key ring: This attribute is defined in ITU-T G.987 systems only. It specifies whether the associated GEM port is encrypted, and if so, which key ring it uses. (R, W, set-by-create) (optional) (1 byte) 0 (default) No encryption. The downstream key index is ignored, and upstream traffic is transmitted with key index 0. 1 Unicast payload encryption in both directions. Keys are generated by the ONU and transmitted to the OLT via the PLOAM channel. 2 Broadcast (multicast) encryption. Keys are generated by the OLT and distributed via the OMCI. 3 Unicast encryption, downstream only. Keys are generated by the ONU and transmitted to the OLT via the PLOAM channel. Other values are reserved. |

### `PON_SERVICE_CONFIG_PROFILE_GEM_PORT_NETWORK_CTP_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_GEM_PORT_NETWORK_CTP_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the GEM port network CTP. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_HEADER`

- **Key:** `name`
- **Description:** PON_SERVICE_CONFIG_PROFILE_HEADER configuration.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | string | ONU vendor name. |
| `title` | string | Description for this service configuration. |
| `version` | string | Capability of configuration file format. |

### `PON_SERVICE_CONFIG_PROFILE_HEADER_COMPATIBILITY_VENDOR_MODEL`

- **Key:** `vendor-id`, `name`
- **Description:** PON_SERVICE_CONFIG_PROFILE_HEADER_COMPATIBILITY_VENDOR_MODEL configuration.

| Field | Type | Description |
| --- | --- | --- |
| `vendor-id` *(key)* | string |  |
| `name` *(key)* | leafref → name | References PON_SERVICE_CONFIG_PROFILE_HEADER_LIST. |

### `PON_SERVICE_CONFIG_PROFILE_HEADER_INPUTS_EXT_INPUT`

- **Key:** `name`, `db-ref`
- **Description:** PON_SERVICE_CONFIG_PROFILE_HEADER_INPUTS_EXT_INPUT configuration.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | leafref → name | References PON_SERVICE_CONFIG_PROFILE_HEADER_LIST. |
| `db-ref` *(key)* | omci-db-ref | Path referencing a specific collection and field in the database. |
| `type` | header-input-type (enum: string, integer) | Input data type. |

### `PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_IEEE8021P_MAPPER_SERVICE_PROFILE_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `tp-pointer` | omci-uint16 |  |
| `interwork-tp-pointer-for-p-bit-priority-0` | omci-uint16 | Interwork TP pointer for P-bit priority 0: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-1` | omci-uint16 | Interwork TP pointer for P-bit priority 1: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-2` | omci-uint16 | Interwork TP pointer for P-bit priority 2: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-3` | omci-uint16 | Interwork TP pointer for P-bit priority 3: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-4` | omci-uint16 | Interwork TP pointer for P-bit priority 4: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-5` | omci-uint16 | Interwork TP pointer for P-bit priority 5: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-6` | omci-uint16 | Interwork TP pointer for P-bit priority 6: (R,W, set-by-create) (mandatory) (2bytes). |
| `interwork-tp-pointer-for-p-bit-priority-7` | omci-uint16 | Interwork TP pointer for P-bit priority 7: (R,W, set-by-create) (mandatory) (2bytes). |
| `unmarked-frame-option` | omci-uint8 | Unmarked frame option: This attribute specifies how the ONU should handle untagged Ethernet frames received across the associated interface. Although it does not alter the frame in any way, the ONU routes the frame as if it were tagged with P bits (PCP field) according to the following code points. 0 Derive implied PCP field from DSCP bits of received frame 1 Set implied PCP field to a fixed value specified by the default P-bit assumption attribute (R,W, set-by-create) (mandatory) (1byte) Untagged downstream frames are passed through the mapper transparently. |
| `default-p-bit-assumption` | omci-uint8 | Default P-bit assumption: This attribute is valid when the unmarked frame option attribute is set to 1. In its LSBs, the default P-bit assumption attribute contains the default PCP field to be assumed. The unmodified frame is then directed to the GEM IW TP indicated by the interwork TP pointer mappings. (R,W, set-by-create) (mandatory) (1byte). |
| `tp-type` | omci-uint8 | TP type: This attribute identifies the type of TP associated with the mapper. 0 Mapper used for bridging-mapping 1 Mapper directly associated with a PPTP Ethernet UNI 2 Mapper directly associated with an IP host config data or IPv6 host config data ME 3 Mapper directly associated with an Ethernet flow termination point 4 Mapper directly associated with a PPTP xDSL UNI 5 Reserved 6 Mapper directly associated with a PPTP MoCA UNI 7 Mapper directly associated with a virtual Ethernet interface point 8 Mapper directly associated with an IW VCC termination point 9 Mapper directly associated with an EFM bonding group (R,W, set-by-create) (optional) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_IEEE8021P_MAPPER_SERVICE_PROFILE_DSCP_TO_P_BIT_MAPPING_DSCP_TO_P_BIT_MAPPING_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `dscp`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_IEEE8021P_MAPPER_SERVICE_PROFILE_MANAGED_ENTITY_DSCP_TO_P_BIT_MAPPING_DSCP_TO_P_BIT_MAPPING_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `dscp` *(key)* | omci-uint8 | DSCP Value. |
| `priority` | omci-uint8 | P-bit value. |

### `PON_SERVICE_CONFIG_PROFILE_IPV6_HOST_CONFIG_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_IPV6_HOST_CONFIG_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The ONU creates as many instances as there are independent IP stacks on the ONU. To facilitate discovery, IP and IPv6 host config data MEs should be numbered from 0 upwards. The ONU must create IP(v4) and IPv6 host config data MEs with separate ME IDs, such that other MEs can use a single TP type attribute to link with either. (R) (mandatory) (2 bytes). |
| `ip-options` | omci-uint8 | IP options: This attribute is a bit map that enables or disables IP-related options. The value 1 enables the option while 0 disables it. The default value of this attribute is 0. 0x01 Enable DHCP 0x02 Respond to pings 0x04 Respond to traceroute messages 0x08 Enable IP stack 0x10..0x80 Reserved (R,W) (mandatory) (1byte). |
| `onu-identifier` | omci-string | Onu identifier: A unique ONU identifier string. If set to a non-null value, this string is used instead of the MAC address in retrieving DHCPv6 parameters. If the string is shorter than 25 characters, it must be null terminated. Its default value is 25 null bytes. (R,W) (mandatory) (25bytes) Several attributes of this ME may be paired together into two categories, manual settings and current values. While this ME instance is administratively locked, it provides no IPv6 connectivity to the external world. Especially if manual provisioning is to be used, it is important that the ME remain locked until provisioning is complete. While autoconfiguration is disabled, the current values are the same as the manual settings. While autoconfiguration is enabled, the current values are those autoconfigured on the basis of RAs, assigned by DHCPv6, or undefined (empty tables) if no values have (yet) been assigned. |
| `ipv6-address` | omci-ipv6-address | IPv6 address: The manually provisioned IPv6 address used for routed IPv6 host services. The address remains valid until reprovisioned, i.e., the preferred and valid lifetimes of this address are infinite. The default value of this attribute is the undefined address 0. (R, W) (mandatory) (16 bytes). |
| `default-router` | omci-ipv6-address | Default router: The manually provisioned IPv6 address of the default router. The default value of this attribute is the undefined address 0. (R,W) (mandatory) (16bytes). |
| `primary-dns` | omci-ipv6-address | Primary DNS: The manually provisioned IPv6 address of the primary DNS server. The default value of this attribute is the undefined address 0. (R,W) (mandatory) (16bytes). |
| `secondary-dns` | omci-ipv6-address | Secondary DNS: The manually provisioned IPv6 address of the secondary DNS server. The default value of this attribute is the undefined address 0. (R,W) (mandatory) (16bytes). |
| `on-link-prefix` | omci-string | On-link prefix: This attribute is the manually provisioned on-link prefix used for destination IPv6 addresses of IPv6 host services. The attribute is structured as follows. Prefix length, number of leading bits in the prefix that are valid (1 byte) Prefix (16 bytes) (R,W) (optional) (17 bytes). |
| `relay-agent-options` | omci-uint16 | Relay agent options: This attribute is a pointer to a large string ME whose content specifies one or more DHCP relay agent options. (R, W) (optional) (2bytes) The meaning and interpretation of the large string's contents are identical to that described in the IP host config data definition in clause 9.4.1. |

### `PON_SERVICE_CONFIG_PROFILE_IP_HOST_CONFIG_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_IP_HOST_CONFIG_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The ONU creates as many instances as there are independent IPv4 stacks on the ONU. To facilitate discovery, IP host config data MEs should be numbered from 0 upwards. The ONU should create IP(v4) and IPv6 host config data MEs with separate ME IDs, such that other MEs can use a single TP type attribute to link with either. (R) (mandatory) (2 bytes). |
| `ip-options` | omci-uint8 | IP options: This attribute is a bit map that enables or disables IP-related options. The value 1 enables the option while 0 disables it. The default value of this attribute is 0. 0x01 Enable DHCP 0x02 Respond to pings 0x04 Respond to traceroute messages 0x08 Enable IP stack 0x10..0x80 Reserved (R,W) (mandatory) (1byte). |
| `onu-identifier` | omci-string | Onu identifier: A unique ONU identifier string. If set to a non-null value, this string is used instead of the MAC address in retrieving dynamic host configuration protocol (DHCP) parameters. If the string is shorter than 25 characters, it must be null terminated. Its default value is 25 null bytes. (R,W) (mandatory) (25bytes) Several attributes of this ME may be paired together into two categories, manual settings and current values. While the IP stack is disabled, there is no IP connectivity to the external world from this ME instance. While DHCP is disabled, the current values are always the same as the manual settings. While DHCP is enabled, the current values are those assigned by DHCP, or undefined (0) if DHCP has never assigned values. |
| `ip-address` | omci-ipv4-address |  |
| `mask` | omci-ipv4-address |  |
| `gateway` | omci-ipv4-address |  |
| `primary-dns` | omci-ipv4-address | Primary DNS: The manually provisioned IPv6 address of the primary DNS server. The default value of this attribute is the undefined address 0. (R,W) (mandatory) (16bytes). |
| `secondary-dns` | omci-ipv4-address | Secondary DNS: The manually provisioned IPv6 address of the secondary DNS server. The default value of this attribute is the undefined address 0. (R,W) (mandatory) (16bytes). |
| `relay-agent-options` | omci-uint16 | Relay agent options: This attribute is a pointer to a large string ME whose content specifies one or more DHCP relay agent options. (R, W) (optional) (2bytes) The meaning and interpretation of the large string's contents are identical to that described in the IP host config data definition in clause 9.4.1. |

### `PON_SERVICE_CONFIG_PROFILE_IP_HOST_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_IP_HOST_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the IP host configuration data or IPv6 host configuration data ME. (R, set-by-create) (mandatory) (2 bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_LARGE_STRING`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_LARGE_STRING_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The value 0xFFFF is reserved. When the large string is to be used as an IPv6 address, the value 0 is also reserved. The OLT should create large string MEs starting at 1 (or 0), and numbering upwards. The ONU should create large string MEs starting at 65534 (0xFFFE) and numbering downwards. (R,set-by-create) (mandatory) (2bytes). |
| `number-of-parts` | omci-uint8 |  |
| `part-1` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-2` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-3` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-4` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-5` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-6` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-7` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-8` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-9` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-10` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-11` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-12` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-13` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-14` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |
| `part-15` | omci-string | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, Part 8, Part 9, Part 10, Part 11, Part 12, Part 13, Part 14, Part 15: (R,W) (mandatory) (25bytes * 15 attributes). |

### `PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MAC_BRIDGE_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the MAC bridge service profile. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by- create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_CONFIGURATION_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MAC_BRIDGE_PORT_CONFIGURATION_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `bridge-id-pointer` | omci-uint16 | Bridge ID pointer: This attribute points to an instance of the MAC bridge service profile. (R,W, set-by-create) (mandatory) (2bytes). |
| `port-num` | omci-uint8 | Port num: This attribute is the bridge port number. It must be unique among all ports associated with a particular MAC bridge service profile. (R,W, set-by-create) (mandatory) (1byte). |
| `tp-type` | omci-uint8 | TP type: This attribute identifies the type of TP associated with this MAC bridge port. Valid values are as follows. 1 Physical path termination point Ethernet UNI 2 Interworking virtual circuit connection (VCC) termination point 3 IEEE 802.1p mapper service profile 4 IP host config data or IPv6 host config data 5 GEM interworking termination point 6 Multicast GEM interworking termination point 7 Physical path termination point xDSL UNI part 1 8 Physical path termination point VDSL UNI 9 Ethernet flow termination point 10 Reserved 11 Virtual Ethernet interface point 12 Physical path termination point MoCA UNI 13 Ethernet in the first mile (EFM) bonding group (R,W, set-by-create) (mandatory) (1byte). |
| `tp-pointer` | omci-uint16 |  |
| `port-priority` | omci-uint16 | Port priority: This attribute denotes the priority of the port for use in (rapid) spanning tree algorithms. The range is 0..255. (R,W, set-by-create) (optional) (2bytes). |
| `port-path-cost` | omci-uint16 | Port path cost: This attribute specifies the contribution of the port to the path cost towards the spanning tree root bridge. The range is 1..65535. (R,W, set-by-create) (mandatory) (2bytes). |
| `port-spanning-tree-ind` | omci-uint8 | Port spanning tree ind: The Boolean value true enables (R)STP LAN topology change detection at this port. The value false disables topology change detection. (R,W, set-by-create) (mandatory) (1byte). |
| `deprecated1` | omci-uint8 | Deprecated 1: This attribute is not used. If present, it should be ignored by both the ONU and the OLT, except as necessary to comply with OMCI message definitions. (R,W, set-by-create) (optional) (1byte). |
| `deprecated2` | omci-uint8 | Deprecated 2: This attribute is not used. If present, it should be ignored by both the ONU and the OLT, except as necessary to comply with OMCI message definitions. (R,W, set-by-create) (1byte) (optional). |
| `outbound-td-pointer` | omci-uint16 | Outbound TD pointer: This attribute points to a traffic descriptor that limits the traffic rate leaving the MAC bridge. (R,W) (optional) (2byte). |
| `inbound-td-pointer` | omci-uint16 | Inbound TD pointer: This attribute points to a traffic descriptor that limits the traffic rate entering the MAC bridge. (R,W) (optional) (2byte). |
| `mac-learning-depth` | omci-uint8 | MAC learning depth: This attribute specifies the maximum number of MAC addresses to be learned by this MAC bridge port. The default value 0 specifies that there is no administratively imposed limit. (R,W, set-by-create) (optional) (1byte) NOTE 2 If this attribute is not zero, its value overrides the value set in the MAC learning depth attribute of the MAC bridge service profile. |

### `PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_PORT_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MAC_BRIDGE_PORT_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the MAC bridge port configuration data ME. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_MAC_BRIDGE_SERVICE_PROFILE`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MAC_BRIDGE_SERVICE_PROFILE_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The first byte is the slot ID. In an integrated ONU, this value is 0. The second byte is the bridge group ID. (R, set-by-create) (mandatory) (2bytes). |
| `spanning-tree-ind` | omci-uint8 | Spanning tree ind: The Boolean value true specifies that a spanning tree algorithm is enabled. The value false disables (rapid) spanning tree. (R,W, set-by-create) (mandatory) (1byte). |
| `learning-ind` | omci-uint8 | Learning ind: The Boolean value true specifies that bridge learning functions are enabled. The value false disables bridge learning. (R,W, set-by-create) (mandatory) (1byte). |
| `port-bridging-ind` | omci-uint8 | Port bridging ind: The Boolean value true specifies that bridging between UNI ports is enabled. The value false disables local bridging. (R,W, set-by-create) (mandatory) (1byte). |
| `priority` | omci-uint16 | Priority: This attribute specifies the bridge priority in the range 0..65535. The value of this attribute is copied to the bridge priority attribute of the associated MAC bridge configuration data ME. (R,W, set-by-create) (mandatory) (2bytes). |
| `max-age` | omci-uint16 | Max age: This attribute specifies the maximum age (in 256ths of a second) of received protocol information before its entry in the spanning tree listing is discarded. The range is 0x0600 to 0x2800 (6..40s) in accordance with [IEEE802.1D]. (R,W, set-by-create) (mandatory) (2bytes). |
| `hello-time` | omci-uint16 | Hello time: This attribute specifies how often (in 256ths of a second) the bridge advertises its presence via hello packets, while acting as a root or attempting to become a root. The range is 0x0100 to 0x0A00 (1..10s). (R,W, set-by-create) (mandatory) (2bytes) NOTE [IEEE 802.1D] specifies the compatibility range for hello time to be 1..2s. |
| `forward-delay` | omci-uint16 | Forward delay: This attribute specifies the forwarding delay (in 256ths of a second) when the bridge acts as the root. The range is 0x0400 to 0x1E00 (4..30s) in accordance with [IEEE 802.1D]. (R,W, set-by-create) (mandatory) (2bytes). |
| `unknown-mac-address-discard` | omci-uint8 | Unknown MAC address discard: The Boolean value true specifies that MAC frames with unknown DAs be discarded. The value false specifies that such frames be forwarded to all allowed ports. (R,W, set-by-create) (mandatory) (1byte). |
| `mac-learning-depth` | omci-uint8 | MAC learning depth: This attribute specifies the maximum number of UNI MAC addresses to be learned by the bridge. The default value 0 specifies that there is no administratively imposed limit. (R,W, set-by-create) (optional) (1byte). |
| `dynamic-filtering-ageing-time` | omci-uint32 | Dynamic filtering ageing time: This attribute specifies the age of dynamic filtering entries in the bridge database, after which unrefreshed entries are discarded. In accordance with clause 7.9.2 of [IEEE 802.1D] and clause 8.8.3 of [IEEE 802.1Q], the range is 10..1 000 000s, with a resolution of 1s and a default of 300s. The value 0 specifies that the ONU uses its internal default. (R, W, set-by-create) (optional) (4 bytes). |

### `PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MULTICAST_GEM_INTERWORKING_TP_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The value 0xFFFF is reserved. (R, set-by-create) (mandatory) (2bytes). |
| `gem-port-network-ctp-pointer` | omci-uint16 | GEM port network CTP connectivity pointer: This attribute points to an instance of the GEM port network CTP that is associated with this multicast GEM IW TP. (R,W, set-by-create) (mandatory) (2bytes). |
| `interworking-option` | omci-uint8 | Interworking option: This attribute identifies the type of non-GEM function that is being interworked. The option can be as follows. 0 This value is a 'no-op' or 'don't care'. It should be used when the multicast GEM IW TP is associated with several functions of different types. It can optionally be used in all cases, since the necessary information is available elsewhere. The previous code points are retained for backward compatibility: 1 MAC bridged LAN 3 Reserved 5 IEEE 802.1p mapper (R,W, set-by-create) (mandatory) (1byte). |
| `service-profile-pointer` | omci-uint16 | Service profile pointer: This attribute is set to 0 and not used. For backward compatibility, it may also be set to point to a MAC bridge service profile or IEEE 802.1p mapper service profile. (R,W, set-by-create) (mandatory) (2bytes). |
| `interworking-tp-pointer` | omci-uint16 | Not used 1: This attribute is set to 0 and not used. (R,W, set-by-create) (mandatory) (2bytes). |
| `gal-profile-pointer` | omci-uint16 | GAL profile pointer: This attribute is set to 0 and not used. For backward compatibility, it may also be set to point to a GAL Ethernet profile. (R,W, set-by-create) (mandatory) (2bytes). |
| `gal-loopback-configuration` | omci-uint8 | Not used 2: This attribute is set to 0 and not used. (R,W, set-by-create) (mandatory) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV4_MULTICAST_ADDRESS_TABLE_IPV4_MULTICAST_ADDRESS_TABLE_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `ipv4-multicast-address-table-entry-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MULTICAST_GEM_INTERWORKING_TP_MANAGED_ENTITY_IPV4_MULTICAST_ADDRESS_TABLE_IPV4_MULTICAST_ADDRESS_TABLE_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The value 0xFFFF is reserved. (R, set-by-create) (mandatory) (2bytes). |
| `ipv4-multicast-address-table-entry-id` *(key)* | uint8 |  |
| `gem-port-id` | omci-uint16 | gem port id. |
| `secondary-key` | omci-uint16 | secondary key. |
| `ip-multicast-da-range-start` | omci-ipv4-address | ip multicast da range start. |
| `ip-multicast-da-range-stop` | omci-ipv4-address | ip multicast da range stop. |

### `PON_SERVICE_CONFIG_PROFILE_MULTICAST_GEM_INTERWORKING_TP_IPV6_MULTICAST_ADDRESS_TABLE_IPV6_MULTICAST_ADDRESS_TABLE_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `ipv6-multicast-address-table-entry-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_MULTICAST_GEM_INTERWORKING_TP_MANAGED_ENTITY_IPV6_MULTICAST_ADDRESS_TABLE_IPV6_MULTICAST_ADDRESS_TABLE_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The value 0xFFFF is reserved. (R, set-by-create) (mandatory) (2bytes). |
| `ipv6-multicast-address-table-entry-id` *(key)* | uint8 |  |
| `gem-port-id` | omci-uint16 | gem port id. |
| `secondary-key` | omci-uint16 | secondary key. |
| `lsb-ip-multicast-da-range-start` | omci-string | lsb ip multicast da range start. |
| `lsb-ip-multicast-da-range-stop` | omci-string | lsb ip multicast da range stop. |
| `msb-ip-multicast-da` | omci-string | msb ip multicast da. |

### `PON_SERVICE_CONFIG_PROFILE_OLT_G`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_OLT_G_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. There is only one instance, number 0. (R) (mandatory) (2bytes). |
| `olt-vendor-id` | omci-string | OLT vendor ID: This attribute identifies the OLT vendor. It is the same as the four most significant bytes of an ONU serial number specified in the respective TC layer specification. Upon instantiation, this attribute comprises all spaces. (R,W) (mandatory) (4bytes). |
| `equipment-id` | omci-string | Equipment ID: This attribute may be used to identify the specific type of OLT. The default value of all spaces indicates that equipment ID information is not available or applicable to the OLT being represented. (R,W) (mandatory) (20bytes). |
| `version` | omci-string | Version: This attribute identifies the version of the OLT as defined by the vendor. The default left-justified ASCII string '0' (padded with trailing nulls) indicates that version information is not available or applicable to the OLT being represented. (R,W) (mandatory) (14bytes). |
| `time-of-day` | omci-string | Time of day information: This attribute provides the information required to achieve time of day synchronization between a reference clock at the OLT and a local clock at the ONU. This attribute comprises two fields: the first field (4bytes) is the sequence number of the specified GEM superframe. The second field (10bytes) is TstampN as defined in clause 10.4.6 of [ITU-T G.984.3], clause 13.2 of [ITU-T G.987.3] and clause 13.2 of [ITU-T G.989.3], using the timestamp format of clause 5.3.3 of [IEEE 1588]. The value 0 in all bytes is reserved as a null value. (R,W) (optional) (14bytes) NOTE In ITU-T G.987/ITU-T G.989 systems, the superframe count field of the time of day information attribute contains the 32 LSBs of the actual counter. |

### `PON_SERVICE_CONFIG_PROFILE_ONU2_G`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ONU2_G_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. There is only one instance, number 0. (R) (mandatory) (2bytes). |
| `security-mode` | omci-uint8 |  |
| `current-connectivity-mode` | omci-uint8 | Current connectivity mode: This attribute specifies the Ethernet connectivity model that the OLT wishes to use. The following code points are defined. NOTE 2 It is not implied that an ONU supports a given connectivity model only when that model is explicitly selected by this attribute. The ONU is free to support additional models at any and all times. (R, W) (optional) (1 byte). |
| `priority-queue-scale-factor` | omci-uint16 | Priority queue scale factor: If this optional attribute is implemented, it specifies the scale factor of several attributes of the priority queue ME of clause9.2.10. The default value of this attribute is 1. (R, W) (optional) (2bytes) NOTE 3 Some legacy implementations may take the queue scale factor from the GEM block length attribute of the ANI-G ME. That option is discouraged in new implementations. |

### `PON_SERVICE_CONFIG_PROFILE_ONU_G`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ONU_G_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. There is only one instance, number 0. (R) (mandatory) (2bytes). |
| `battery-backup` | omci-uint8 |  |
| `administrative-state` | omci-uint8 | Administrative state: This attribute locks (1) and unlocks (0) the functions performed by the ONU as an entirety. Administrative state is further described in clause A.1.6. (R,W) (mandatory) (1byte). |
| `credentials-status` | omci-uint8 | Credentials status: This attribute permits the OLT to signal to the ONU whether its credentials are valid or not. The behaviour of the ONU is not specified, but might, for example, include displaying an error screen to the user. (R, W) (optional) (1byte) Values include: 0 Initial state, status indeterminate 1 Successful authentication 2 Logical ONU ID (LOID) error 3 Password error 4 Duplicate LOID Other values are reserved. |

### `PON_SERVICE_CONFIG_PROFILE_ONU_OPERATIONAL_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_ONU_OPERATIONAL_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. There is only one instance, number 0. (R) (mandatory) (2 bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 managed entity that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R, W, Set by create) (mandatory) (2 bytes). |

### `PON_SERVICE_CONFIG_PROFILE_PPTP_RS232_RS485_UNI`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_PPTP_RS232_RS485_UNI_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. This 2byte number is directly associated with the physical position of the UNI. The first byte is the slot ID (defined in clause 9.1.5). The second byte is the port ID, with range 1..255. (R) (mandatory) (2bytes). |
| `administrative-state` | omci-uint8 | Administrative state: This attribute locks (1) and unlocks (0) the functions performed by this ME. Administrative state is further described in clause A.1.6. (R,W) (mandatory) (1byte). |
| `port-mode` | omci-uint8 | Port mode: This attribute indicates the working mode of the RS232/RS485 controller chipset. Valid values are as follows. 0 half-duplex 1 full duplex (mandatory) (1byte). |
| `baud-rate` | omci-uint8 | Baud_rate: This attribute specifies the working baud rate of RS232/RS485 port. Valid values are as follows. 0 300 bit/s 1 600 bit/s 2 1200 bit/s 3 2400 bit/s 4 4800 bit/s 5 9600 bit/s 6 19200 bit/s 7 38400 bit/s 8 43000 bit/s 9 56000 bit/s 10 57600 bit/s 11 115200 bit/s (R,W, set-by-create) (mandatory) (1byte). |
| `data-bits` | omci-uint8 | Data_bits: This attribute specifies the bits of the data. Valid values are as follows. 5 5 bits 6 6 bits 7 7 bits 8 8 bits (R,W, set-by-create) (mandatory) (1byte). |
| `parity` | omci-uint8 | Parity: This attribute specifies the parity of the data. Valid values are as follows. 0 no parity 1 odd parity 2 even parity (R,W, set-by-create) (mandatory) (1byte). |
| `stop-bits` | omci-uint8 | Stop_bits: This attribute specifies the number of stop bits of the data. Valid values are as follows. 1 1 bit 2 2 bits (R,W, set-by-create) (mandatory) (1byte). |
| `flow-control` | omci-uint8 | Flow_control: This attribute specifies the flow control of the data. Valid values are as follows. 0 no flow control 1 hardware flow control (RTS/CTS) 2 software flow control (Xon/Xoff) (R,W, set-by-create) (mandatory) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_PRIORITY_QUEUE_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. The MSB represents the direction (1: upstream, 0:downstream). The 15 LSBs represent a queue ID. The queue ID is numbered in ascending order by the ONU itself. It is strongly encouraged that the queue ID be formulated to simplify finding related queues. One way to do this is to number the queues such that the related port attributes are in ascending order (for the downstream and upstream queues separately). The range of downstream queue ids is 0 to 0x7FFF and the range of upstream queue ids is 0x8000 to 0xFFFF. (R) (mandatory) (2bytes). |
| `allocated-queue-size` | omci-uint16 | Allocated queue size: This attribute identifies the allocated size of this queue, in bytes, scaled by the priority queue scale factor attribute of the ONU2-G. (R, W) (mandatory) (2 bytes). |
| `discard-block-counter-reset-interval` | omci-uint16 | Discard-block counter reset interval: This attribute represents the interval in milliseconds at which the counter resets itself. (R,W) (optional) (2bytes). |
| `threshold-value-for-discarded-blocks` | omci-uint16 | Threshold value for discarded blocks due to buffer overflow: This attribute specifies the threshold for the number of bytes (scaled by the priority queue scale factor attribute of the ONU2-G) discarded on this queue due to buffer overflow. Its value controls the declaration of the block loss alarm. (R, W) (optional) (2bytes). |
| `related-port` | omci-uint32 | Related port: This attribute represents the slot, port/T-CONT and priority information associated with the instance of priority queue ME. This attribute comprises 4bytes. In the upstream direction, the first 2bytes are the ME ID of the associated T-CONT, the first byte of which is a slot number, the second byte a T-CONT number. In the downstream direction, the first byte is the slot number and the second byte is the port number of the queue's destination port. The last 2bytes represent the priority of this queue. The range of priority is 0 to 0x0FFF. The value 0 indicates the highest priority and 0x0FFF indicates the lowest priority. The priority field is meaningful if multiple priority queues are associated with a T-CONT or traffic scheduler whose scheduling discipline is strict priority. (R, W) (mandatory) (4 bytes) NOTE 3 If flexible port configuration is supported, the related port attribute is meaningful only if the traffic scheduler pointer attribute value is null. Otherwise, the related port attribute is ignored. NOTE 4 The related port attribute is read-only, unless otherwise specified by the QoS configuration flexibility attribute of the ONU2-G ME. If port flexibility is supported, the second byte, the port or T-CONT number, may be changed. If priority flexibility is supported, the third and fourth bytes may be changed. The OMCI set command must contain 4bytes to match the attribute size, but the ONU must ignore all bytes that are not specified to be flexible. If flexible configuration is not supported, the ONU should reject an attempt to set the related port with a parameter error result-reason code. |
| `traffic-scheduler-pointer` | omci-uint16 | Traffic scheduler pointer: This attribute points to the traffic scheduler ME instance that is associated with this priority queue. This pointer is used when this priority queue is connected with a traffic scheduler. The default value is a null pointer (0). (R, W) (mandatory) (2 bytes) NOTE 5 When the QoS configuration flexibility attribute of the ONU2-G ME allows flexible assignment of the traffic scheduler, the OLT may configure the traffic scheduler pointer to refer to any traffic scheduler in the same slot. If traffic scheduler flexibility is not permitted by the QoS configuration flexibility attribute, the OLT may use the traffic scheduler pointer attribute only by pointing to another traffic scheduler ME that is associated with the same T-CONT as the priority queue itself. The ONU should reject an attempt to violate these conditions with a parameter error result-reason code. |
| `weight` | omci-uint8 | Weight: This attribute represents weight for WRR scheduling. At a given priority level, capacity is distributed to non-empty queues in proportion to their weights. In the upstream direction, this weight is meaningful if several priority queues are associated with a traffic scheduler or T-CONT whose policy is WRR. In the downstream direction, this weight is used by a UNI in a WRR fashion. Upon ME instantiation, the ONU sets this attribute to 1. (R,W) (mandatory) (1byte). |
| `back-pressure-operation` | omci-uint16 | Back pressure operation: This attribute enables (0) or disables (1) back pressure operation. Its default value is 0. (R,W) (mandatory) (2bytes). |
| `back-pressure-time` | omci-uint32 | Back pressure time: This attribute specifies the duration in microseconds of the back-pressure signal. It can be used as a pause time for an Ethernet UNI. Upon ME instantiation, the ONU sets this attribute to 0. (R,W) (mandatory) (4bytes). |
| `back-pressure-occur-queue-threshold` | omci-uint16 | Back pressure occur queue threshold: This attribute identifies the threshold queue occupancy, in bytes, scaled by the priority queue scale factor attribute of the ONU2-G, to start sending a back-pressure signal. (R, W) (mandatory) (2bytes). |
| `back-pressure-clear-queue-threshold` | omci-uint16 | Back pressure clear queue threshold: This attribute identifies the threshold queue occupancy, in bytes, scaled by the priority queue scale factor attribute of the ONU2-G, to stop sending a back-pressure signal. (R, W) (mandatory) (2bytes). |
| `packet-drop-max-p` | omci-uint16 | Packet drop max_p: This attribute is a composite of two 1byte values, the probability of dropping a coloured packet when the queue occupancy lies just below the maximum threshold for packets of that colour. The first value is the green packet max_p, and the second value is the yellow packet max_p. The probability, max_p, is determined by adding one to the unsigned value (0..255) of this attribute and dividing the result by 256. The default for each value is 255. (R,W) (optional) (2bytes). |
| `queue-drop-w-q` | omci-uint8 | Queue drop w_q: This attribute determines the averaging coefficient, w_q, as described in [b-Floyd]. The averaging coefficient, w_q, is equal to 2-Queue_drop_w_q. For example, when queue drop_w_q has the value 9, the averaging coefficient, w_q, is 1/512= 0.0019. The default value is 9. (R,W) (optional) (1byte). |
| `drop-precedence-colour-marking` | omci-uint8 | Drop precedence colour marking: This attribute specifies how drop precedence is marked on ingress packets to the priority queue. The default value is 0. 0 No marking (treat all packets as green) 1 Internal marking (from traffic descriptor ME) 2 DEI [IEEE 802.1ad] 3 PCP 8P0D [IEEE 802.1ad] 4 PCP 7P1D [IEEE 802.1ad] 5 PCP 6P2D [IEEE 802.1ad] 6 PCP 5P3D [IEEE 802.1ad] 7 DSCP AF class [IETF RFC 2597] (R,W) (optional) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_PACKET_DROP_QUEUE_THRESHOLD`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_PRIORITY_QUEUE_MANAGED_ENTITY_PACKET_DROP_QUEUE_THRESHOLD configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | leafref → managed-entity-id | References PON_SERVICE_CONFIG_PROFILE_PRIORITY_QUEUE_LIST. |
| `min-green` | omci-uint16 | min green. |
| `max-green` | omci-uint16 | max green. |
| `min-yellow` | omci-uint16 | min yellow. |
| `max-yellow` | omci-uint16 | max yellow. |

### `PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_RS232_RS485_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the PPTP RS232/RS485 UNI. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 id: This attribute points to an instance of the threshold data 1 and 2 MEs that contains PM threshold values. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_RS232_RS485_PORT_OPER_CFG_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_RS232_RS485_PORT_OPER_CFG_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `tcp-udp-ptr` | omci-uint16 | TCP/UDP pointer: This pointer associates the RS232/RS485 port operation configuration with the TCP/UDP config data ME to be used for communication with the serial server. The default value is 0xFFFF, a null pointer. (R,W) (mandatory) (2bytes). |
| `pptp-ptr` | omci-uint16 | PPTP pointer: This attribute points to the PPTP RS232/RS485 UNI ME that serves the serial data acquisition function. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_OPERATION`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_SSH_SERVER_OPERATION_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed Entity Id. |
| `server-action` | omci-uint8 | Server Action. |

### `PON_SERVICE_CONFIG_PROFILE_SSH_SERVER_PORT_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_SSH_SERVER_PORT_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed Entity Id. |
| `tcp-udp-ptr` | omci-uint16 | Tcp Udp Ptr. |
| `ssh-server-ptr` | omci-uint16 | Ssh Server Ptr. |

### `PON_SERVICE_CONFIG_PROFILE_TCONT`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_TCONT_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. This 2byte number indicates the physical capability that realizes the T-CONT. It may be represented as 0xSSBB, where SS indicates the slot ID that contains this T-CONT (0 for the ONU as a whole), and BB is the T-CONT ID, numbered by the ONU itself. T-CONTs are numbered in ascending order, with the range 0..255 in each slot. (R) (mandatory) (2bytes). |
| `alloc-id` | omci-uint16 | Alloc-ID: This attribute links the T-CONT with the alloc-ID assigned by the OLT in the assign_alloc-ID PLOAM message. The respective TC layer specification should be referenced for the legal values for that system. Prior to the setting of this attribute by the OLT, this attribute has an unambiguously unusable initial value, namely the value 0x00FF or 0xFFFF for ITU-T G.984 systems, and the value 0xFFFF for all other ITU-T GTC based PON systems. (R,W) (mandatory) (2bytes). |
| `policy` | omci-uint8 | Policy: This attribute indicates the T-CONT's traffic scheduling policy. Valid values: 0 Null 1 Strict priority 2 WRR Weighted round robin (R, W) (mandatory) (1 byte) NOTE This attribute is read-only, unless otherwise specified by the QoS configuration flexibility attribute of the ONU2-G ME. If flexible configuration is not supported, the ONU should reject an attempt to set it with a parameter error result-reason code. |

### `PON_SERVICE_CONFIG_PROFILE_TCP_UDP_CONFIG_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_TCP_UDP_CONFIG_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. It is recommended that the ME ID be the same as the port number. (R, set-by- create) (mandatory) (2bytes). |
| `port-id` | omci-uint16 | Port ID: This attribute specifies the port number that offers the TCP/UDP service. (R,W, set-by-create) (mandatory) (2bytes). |
| `protocol` | omci-uint8 | Protocol: This attribute specifies the protocol type as defined by [b-IANA] (protocol numbers), for example UDP (0x11). (R,W, set-by-create) (mandatory) (1byte). |
| `tos-diffserv-field` | omci-uint8 | TOS/diffserv field: This attribute specifies the value of the TOS/diffserv field of the IPv4 header. The contents of this attribute may contain the type of service per [IETF RFC 2474] or a DSCP. Valid values for DSCP are as defined by [b-IANA] (differentiated services field code points). (R,W, set-by-create) (mandatory) (1byte). |
| `ip-host-ptr` | omci-uint16 | IP host pointer: This attribute points to the IP host config data or IPv6 host config data ME associated with this TCP/UDP data. Any number of ports and protocols may be associated with an IP host. (R, W, set-by-create) (mandatory) (2 bytes). |

### `PON_SERVICE_CONFIG_PROFILE_TCP_UDP_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_TCP_UDP_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the TCP/UDP config data ME. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA64_BIT`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_THRESHOLD_DATA64_BIT_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed Entity Id. |
| `threshold-value-1` | omci-uint64 | Threshold Value 1. |
| `threshold-value-2` | omci-uint64 | Threshold Value 2. |
| `threshold-value-3` | omci-uint64 | Threshold Value 3. |
| `threshold-value-4` | omci-uint64 | Threshold Value 4. |
| `threshold-value-5` | omci-uint64 | Threshold Value 5. |
| `threshold-value-6` | omci-uint64 | Threshold Value 6. |
| `threshold-value-7` | omci-uint64 | Threshold Value 7. |
| `threshold-value-8` | omci-uint64 | Threshold Value 8. |
| `threshold-value-9` | omci-uint64 | Threshold Value 9. |
| `threshold-value-10` | omci-uint64 | Threshold Value 10. |
| `threshold-value-11` | omci-uint64 | Threshold Value 11. |
| `threshold-value-12` | omci-uint64 | Threshold Value 12. |
| `threshold-value-13` | omci-uint64 | Threshold Value 13. |
| `threshold-value-14` | omci-uint64 | Threshold Value 14. |

### `PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_ONE`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_THRESHOLD_DATA_ONE_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes) The following seven attributes specify threshold values for seven thresholded counters in associated PM history data MEs. The definition of each PM history ME includes a table that links each thresholded counter to one of these threshold value attributes. |
| `threshold-value-1` | omci-uint32 | Threshold value1: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-2` | omci-uint32 | Threshold value2: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-3` | omci-uint32 | Threshold value3: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-4` | omci-uint32 | Threshold value4: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-5` | omci-uint32 | Threshold value5: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-6` | omci-uint32 | Threshold value6: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-7` | omci-uint32 | Threshold value7: (R,W, set-by-create) (mandatory) (4bytes). |

### `PON_SERVICE_CONFIG_PROFILE_THRESHOLD_DATA_TWO`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_THRESHOLD_DATA_TWO_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Its value is the same as that of the paired threshold data1instance. (R, set- by-create) (mandatory) (2bytes) The following seven attributes specify threshold values for seven thresholded counters in associated PM history data MEs. The definition of each PM history ME includes a table that links each thresholded counter to one of these threshold value attributes. |
| `threshold-value-8` | omci-uint32 | Threshold value8: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-9` | omci-uint32 | Threshold value9: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-10` | omci-uint32 | Threshold value10: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-11` | omci-uint32 | Threshold value11: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-12` | omci-uint32 | Threshold value12: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-13` | omci-uint32 | Threshold value13: (R,W, set-by-create) (mandatory) (4bytes). |
| `threshold-value-14` | omci-uint32 | Threshold value14: (R,W, set-by-create) (mandatory) (4bytes). |

### `PON_SERVICE_CONFIG_PROFILE_TRAFFIC_DESCRIPTOR`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_TRAFFIC_DESCRIPTOR_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. (R, set-by-create) (mandatory) (2bytes). |
| `cir` | omci-uint32 | CIR: This attribute specifies the committed information rate, in bytes per second. The default is 0. (R,W, set-by-create) (optional) (4bytes). |
| `pir` | omci-uint32 | PIR: This attribute specifies the peak information rate, in bytes per second. The default value 0 accepts the ONU's factory policy. (R,W, set-by-create) (optional) (4bytes). |
| `cbs` | omci-uint32 | CBS: This attribute specifies the committed burst size, in bytes. The default is 0. (R,W, set-by-create) (optional) (4bytes). |
| `pbs` | omci-uint32 | PBS: This attribute specifies the peak burst size, in bytes. The default value 0 accepts the ONU's factory policy. (R,W, set-by-create) (optional) (4bytes). |
| `colour-mode` | omci-uint8 | Colour mode: This attribute specifies whether the colour marking algorithm considers pre-existing marking on ingress packets (colour-aware) or ignores it (colour-blind). In colour-aware mode, packets can only be demoted (from green to yellow or red, or from yellow to red). The default value is 0. 0 Colour-blind 1 Colour-aware (R,W, set-by-create) (optional) (1byte). |
| `ingress-colour-marking` | omci-uint8 |  |
| `egress-colour-marking` | omci-uint8 |  |

### `PON_SERVICE_CONFIG_PROFILE_TRAFFIC_SCHEDULER`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_TRAFFIC_SCHEDULER_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. This 2byte number indicates the physical capability that realizes the traffic scheduler. The first byte is the slot ID of the circuit pack with which this traffic scheduler is associated. For a traffic scheduler that is not associated with a circuit pack, the first byte is 0xFF. The second byte is the traffic scheduler id, assigned by the ONU itself. Traffic schedulers are numbered in ascending order with the range 0..0xFF in each circuit pack or in the ONU core. (R) (mandatory) (2bytes). |
| `tcont-pointer` | omci-uint16 | T-CONT pointer: This attribute points to a T-CONT instance. (R,W, set-by- create) (mandatory) (2bytes). |
| `policy` | omci-uint8 | Policy: This attribute represents scheduling policy. Valid values include: 0 Null 1 Strict priority 2 WRR (weighted round robin) The traffic scheduler derives priority or weight values for its tributary traffic schedulers or priority queues from the tributary MEs themselves. (R, W) (mandatory) (1 byte) NOTE 3 This attribute is read-only unless otherwise specified by the QoS configuration flexibility attribute of the ONU2-G ME. If flexible configuration is not supported, the ONU should reject an attempt to set the policy attribute with a parameter error result-reason code. |
| `priority-weight` | omci-uint8 | Priority/weight: This attribute represents the priority for strict priority scheduling or the weight for WRR scheduling. This value is used by the next upstream ME, as indicated by the T-CONT pointer attribute or traffic scheduler pointer attribute. If the indicated pointer has policy=strict priority, this value is interpreted as a priority (0 is the highest priority, 255 the lowest). If the indicated pointer has policy=WRR, this value is interpreted as a weight. Higher values receive more bandwidth. Upon ME instantiation, the ONU sets this attribute to 0. (R,W) (mandatory) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_VIRTUAL_ETHERNET_INTERFACE_PT`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_VIRTUAL_ETHERNET_INTERFACE_PT_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. When used independently of a cardholder and circuit pack, the ONU should assign IDs in the sequence 1, 2, .... When used in conjunction with a cardholder and circuit pack, this 2 byte number indicates the physical position of the VEIP. The first byte is the slot ID (defined in clause 9.1.5). The second byte is the port ID, with the range 1..255. The values 0 and 0xFFFF are reserved. (R) (mandatory) (2 bytes). |
| `administrative-state` | omci-uint8 | Administrative state: This attribute locks (1) and unlocks (0) the functions performed by this ME. Administrative state is further described in clause A.1.6. (R,W) (mandatory) (1byte). |
| `interdomain-service-config-profile-name` | omci-string |  |
| `tcp-udp-pointer` | omci-uint16 | TCP/UDP pointer: This attribute points to an instance of the TCP/UDP config data ME, which provides for OMCI management of the non-OMCI management domain's IP connectivity. If no OMCI management of the non-OMCI domain's IP connectivity is required, this attribute may be omitted or set to its default, a null pointer. (R,W) (optional) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_VLAN_TAGGING_FILTER_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the MAC bridge port configuration data ME. (R, set-by-create) (mandatory) (2bytes). |
| `forward-operation` | omci-uint8 | Forward operation: When a frame passes through the MAC bridge port, it is processed according to the operation specified by this attribute, in accordance with Table9.3.11-1. Figure 9.3.11-3 illustrates the treatment of frames according to the provisioned action possibilities. Tagged and untagged frames are treated separately, but both in accordance with Figure 9.3.11-3. While all forwarding operations are plausible, only actions 0x10 and 0x12 are necessary to construct a VLAN mapper and an 802.1p mapper, respectively. (R,W, set-by- create) (mandatory) (1byte) Table 9.3.11-1 contains duplicate entries due to simplification of the original set of actions. Table 9.3.11-1 and the actions listed are discussed in detail in the following. |
| `number-of-entries` | omci-uint8 | Number of entries: This attribute specifies the number of valid entries in the VLAN filter list. (R,W, set-by-create) (mandatory) (1byte). |

### `PON_SERVICE_CONFIG_PROFILE_VLAN_TAGGING_FILTER_DATA_VLAN_FILTER_LIST_VLAN_FILTER_LIST_ENTRY`

- **Key:** `service-config-profile-name`, `id`, `managed-entity-id`, `vlan-filter-entry-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_VLAN_TAGGING_FILTER_DATA_MANAGED_ENTITY_VLAN_FILTER_LIST_VLAN_FILTER_LIST_ENTRY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `id` *(key)* | string | Table entry number starting at '0'. |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the MAC bridge port configuration data ME. (R, set-by-create) (mandatory) (2bytes). |
| `vlan-filter-entry-id` *(key)* | uint8 |  |
| `vlan-id` | omci-uint16 | VLAN ID. |

### `PON_SERVICE_CONFIG_PROFILE_XG_PON_DOWNSTREAM_MGMT_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_XG_PON_DOWNSTREAM_MGMT_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the ANI-G. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. Since no threshold value attribute number exceeds 7, a threshold data 2 ME is optional. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_XG_PON_TC_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_XG_PON_TC_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the ANI-G. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: This attribute points to an instance of the threshold data 1 ME that contains PM threshold values. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SERVICE_CONFIG_PROFILE_XG_PON_UPSTREAM_MGMT_PERF_MON_HIST_DATA`

- **Key:** `service-config-profile-name`, `managed-entity-id`
- **Description:** PON_SERVICE_CONFIG_PROFILE_OMCI_CLASS_OMCI_CLASS_XG_PON_UPSTREAM_MGMT_PERF_MON_HIST_DATA_MANAGED_ENTITY configuration.

| Field | Type | Description |
| --- | --- | --- |
| `service-config-profile-name` *(key)* | string |  |
| `managed-entity-id` *(key)* | omci-uint16 | Managed entity ID: This attribute uniquely identifies each instance of this ME. Through an identical ID, this ME is implicitly linked to an instance of the ANI-G. (R, set-by-create) (mandatory) (2bytes). |
| `threshold-data-1-2-id` | omci-uint16 | Threshold data 1/2 ID: No thresholds are defined for this ME. For uniformity with other PM, the attribute is retained and shown as mandatory, but it should be set to a null pointer. (R,W, set-by-create) (mandatory) (2bytes). |

### `PON_SLA_PROFILE`

- **Key:** `sla-profile-name`
- **Description:** List of SLA profiles.

| Field | Type | Description |
| --- | --- | --- |
| `sla-profile-name` *(key)* | string (length 0..256) | Name identifier used by the NETCONF interface to reference this SLA profile. |
| `downstream-guaranteed-rate` | uint32 (range 0..10000000; units kbps; default 128) | Guaranteed (high priority) rate in kbps. |
| `downstream-guaranteed-maximum-burst` | uint32 (range 16000..1000000; units bytes; default 256000) | Maximum burst size in Kilobytes. The guaranteed rate is enforced at this burst size. |
| `downstream-best-effort-rate` | uint32 (range 0..10000000; units kbps; default 10000000) | Best Effort (low priority) rate in kbps. |
| `downstream-best-effort-maximum-burst` | uint32 (range 16000..1000000; units bytes; default 256000) | Maximum burst size in Kilobytes. The best effort rate is enforced at this burst size. |
| `upstream-fixed-rate` | uint32 (range 0..8000000; units kbps; default 0) | Fixed grant rate in kbps. This is an unsolicited grant by the DBA regardless of need. |
| `upstream-guaranteed-rate` | uint32 (range 0..10000000; units kbps; default 128) | Guaranteed (high priority) rate in kbps. |
| `upstream-guaranteed-maximum-burst` | uint32 (range 16000..1000000; units bytes; default 409600) | Maximum burst size in Kilobytes. The guaranteed rate is enforced at this burst size. |
| `upstream-priority` | uint8 (range 1..8; default 1) | Priority level for the guaranteed portion of the SLA. |
| `upstream-best-effort-rate` | uint32 (range 0..10000000; units kbps; default 10000000) | Best Effort (low priority) rate in kbps. |
| `upstream-best-effort-maximum-burst` | uint32 (range 16000..1000000; units bytes; default 409600) | Maximum burst size in Kilobytes. The best effort rate is enforced at this burst size. |
| `upstream-best-effort-priority` | uint8 (range 1..8; default 1) | Priority level for the Best Effort portion of the SLA. |

### `PON_SLA_PROFILE_CONTROLLER`

- **Key:** `name`
- **Description:** PON Controller related configuration.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | leafref → sla-profile-name | References PON_SLA_PROFILE_LIST. |

## STATE_DB

### `PON_CONTROLLER_ONU_FW_UPGRADE_STATE`

- **Key:** `name`, `onu-id`
- **Description:** The list of ONUs currently performing firmware upgrades on the PON Controller.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | string |  |
| `onu-id` *(key)* | string | ONU device identifier (XGS-PON: ONU Serial Number). |

### `PON_CONTROLLER_STATE`

- **Key:** `name`
- **Description:** List of PON Controllers.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | string | Name identifier used by the NETCONF interface to reference this PON Controller. |
| `timestamp` | date-and-time | The last update for this state file. |
| `allow-unprovisioned-onus` | boolean | When false, the controller only allows ONUs that have been inventoried on an OLT to complete registration. |
| `config-read-failed` | boolean | When true, the configuration file is not a valid format and can't be read by the controller. All processing is stopped on this device until this error is fixed. |
| `interface` | string | Network interface used by the controller. |
| `olt-timeout` | uint32 | The amount of time that the PON controller will lock an OLT for exclusive management. When this timer expires, another PON controller can take control of the OLT. |
| `statistics-sample` | uint32 (units seconds) | Current statistic sample interval. |
| `version` | string | Version of the controller. |
| `unprovisioned-age` | uint32 (units seconds) | The amount of time an ONU will be kept in the Unprovisioned ONUs list, when no longer attempting registration. |
| `refresh-state-on-olt-change` | boolean | Current state of refresh state on olt change. |

### `PON_CONTROLLER_SYSTEM_STATUS_OLT`

- **Key:** `controller-name`, `mac-address`
- **Description:** The list of OLTs currently registered on this PON Controller.

| Field | Type | Description |
| --- | --- | --- |
| `controller-name` *(key)* | string | References PON_CONTROLLER_SYSTEM_STATUS_LIST. |
| `mac-address` *(key)* | mac-address | OLT MAC address. |
| `olt-state` | string | The current state of the OLT. |
| `onu-active-count` | uint32 | The number of ONUs that are active on this OLT. |
| `switch-chassis-id` | string | MAC address of switch. |
| `switch-ipv4-address` | string | IP Address of the switch. |
| `switch-ipv6-address` | string | IP Address of the switch. |
| `switch-port-description` | string | String description of the port. |
| `switch-port-id` | string | String identification for the port. |
| `switch-system-description` | string | System Description. |
| `switch-system-name` | string | Name for the Switch. |

### `PON_CONTROLLER_SYSTEM_STATUS_OLT_ONU`

- **Key:** `name`, `mac-address`, `onu-serial-number`
- **Description:** The list of ONUs currently registered on this OLT.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | string |  |
| `mac-address` *(key)* | leafref → mac-address | References PON_CONTROLLER_SYSTEM_STATUS_OLT_LIST. |
| `onu-serial-number` *(key)* | string | EPON Mode: ONU MAC address. XGS-PON Mode: ONU serial number (defined by Vendor ID + Vendor SN). |
| `onu-state` | string | The current state of the ONU. |

### `PON_FIRMWARE_FILENAME_STATE`

- **Key:** `filename`
- **Description:** PON_FIRMWARE_FILENAME_STATE configuration.

| Field | Type | Description |
| --- | --- | --- |
| `filename` *(key)* | string |  |

### `PON_OLT_INTF_NETWORK_STATE`

- **Key:** `olt-name`, `vlan-id`
- **Description:** List of the NNI Networks configured on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `network-id` | uint16 | Index of entry. |
| `learning-limit` | uint16 | Dynamic MAC learning table size limit for this NNI Network. A value of '0' indicates that MAC Learning is disabled for this NNI Network. |
| `pon-flood-id` | uint16 | XGEM Port ID or LLID for unknown/multicast/broadcast frames from this network. |
| `vlan-id` *(key)* | uint16 (range 0..4095) | VLAN id used to identify packets on the NNI network. |
| `flooding-sla-downstream-guaranteed-rate` | uint32 (units kbps) | Guaranteed (high priority) rate in kbps. |
| `flooding-sla-downstream-guaranteed-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The guaranteed rate is enforced at this burst size. |
| `flooding-sla-downstream-best-effort-rate` | uint32 (units kbps) | Best Effort (low priority) rate in kbps. |
| `flooding-sla-downstream-best-effort-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The best effort rate is enforced at this burst size. |

### `PON_OLT_INTF_NNI_NETWORK_LEARNING_TABLE_STATE`

- **Key:** `olt-name`, `network-id`, `mac-address`
- **Description:** The MAC address learning table for this uplink port. A list of MAC Addresses and source XGEM port IDs (XGS-PON) or LLIDs (EPON).

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `network-id` *(key)* | leafref → network-id | References PON_OLT_INTF_NETWORK_STATE_LIST. |
| `mac-address` *(key)* | mac-address | MAC address of the learned CPE. |
| `unicast-id` | uint16 | XGEM Port ID or EPON LLID that the CPE was learned on. |

### `PON_OLT_INTF_ONU_FW_UPGRADE_STATE`

- **Key:** `olt-name`, `onu-serial-number`
- **Description:** The list of ONUs currently performing firmware upgrades on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_ONU_STATE_LIST. |
| `onu-serial-number` *(key)* | string | ONU device identifier (XGS-PON ONU serial number). |

### `PON_OLT_INTF_ONU_OPERATIONAL_STATE`

- **Key:** `olt-name`, `id`
- **Description:** Consolidated list of ONUs with their operational state.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_ONU_STATE_LIST. |
| `id` *(key)* | string | ONU device identifier (EPON ONU MAC \| XGS-PON ONU serial number). |
| `operational-state` | enumeration (enum: registered, deregistered, disabled, disallowed-admin, disallowed-error, disallowed-registration-id, …) | Current operational state of the ONU. |

### `PON_OLT_INTF_ONU_SERVICE_GEMPORT_STATE`

- **Key:** `olt-name`, `onu-serial-number`, `service-port-id`
- **Description:** List of OLT GEM ports.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `onu-serial-number` *(key)* | leafref → onu-serial-number | References PON_OLT_INTF_ONU_STATE_LIST. |
| `service-port-id` *(key)* | uint32 | OLT Service port number. |
| `gemport-id` | uint16 | GEM port ID for this service port. |
| `tcont-ref` | leafref → service-port-id | References PON_OLT_INTF_ONU_SERVICE_TCONT_STATE_LIST. |

### `PON_OLT_INTF_ONU_SERVICE_TCONT_STATE`

- **Key:** `olt-name`, `onu-serial-number`, `service-port-id`
- **Description:** List of OLT Service ports.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `onu-serial-number` *(key)* | leafref → onu-serial-number | References PON_OLT_INTF_ONU_STATE_LIST. |
| `service-port-id` *(key)* | uint32 | OLT Service port number. |
| `alloc-id` | uint16 | EPON Mode: LLID value for this service port XGS-PON Mode: Allocation ID and XGEM Port ID used on this service port. |

### `PON_OLT_INTF_ONU_STATE`

- **Key:** `olt-name`, `onu-serial-number`
- **Description:** ONU related status.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `onu-serial-number` *(key)* | string | EPON Mode: ONU MAC address. XGS-PON Mode: ONU serial number (defined by Vendor ID + Vendor SN). |
| `onu-id` | uint16 | XGS-PON Mode only: The allocation ID, XGEM port ID, and ONU ID number assigned to this ONU for carry OMCI management messages. |
| `disable` | boolean | When true, the disable serial number PLOAM message will be sent to this ONU if it tries to register. |

### `PON_OLT_INTF_PROTECTION_UNDETECTED_ONU_STATE`

- **Key:** `olt-name`, `id`
- **Description:** List of ONUs not currently seen by the Standby OLT.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `id` *(key)* | string | ONU device identifier. |

### `PON_OLT_INTF_STATE`

- **Key:** `olt-name`, `port-id`
- **Description:** List of OLTs.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | string | Name identifier used by the NETCONF interface to reference this OLT device. |
| `timestamp` | date-and-time | The last update for this state file. |
| `fiber-reach` | enumeration (enum: extended-0to40km, extended-40to60km, extended-20to40km, extended-10to30km, short, standard, …) | The current fiber reach configured on this OLT. |
| `laser-shutdown` | string | Indicates the cause of a laser shutdown. |
| `loss-of-signal` | boolean | There are no ONUs registered on the OLT. |
| `pon-enable` | boolean | Current state of PON Optics on the module. |
| `discovery-period` | uint32 | Current OLT discovery time interval. |
| `downstream-fec` | boolean | Current Forward Error Correction in the downstream direction. |
| `encryption` | olt-encryption-mode (enum: disabled, bidirectional, broadcast, downstream) | Current OLT PON MAC layer encryption mode. |
| `encryption-key-time` | uint16 (units seconds) | Time between changing encryption keys. |
| `error-detection-maximum-hec-ratio` | uint8 (units percent) | Maximum percentage of HEC errors to disable an ONU. |
| `error-detection-minimum-hec-sample` | uint16 (units GPON headers) | Minimum number of HEC error samples to consider for error-detection-maximum-ratio. |
| `error-detection-maximum-ratio` | uint8 (units percent) | Maximum percentage of errored upstream bursts to disable an ONU. |
| `error-detection-minimum-sample` | uint16 (units Upstream Bursts) | Minumum number of upstream bursts to consider for error-detection-maximum-ratio. |
| `guard-time` | uint32 | Current dead time between upstream burst slots. |
| `mac-address` | mac-address | GPON MAC Address. |
| `max-frame-size` | uint32 | Current maximum frame size allowed at the PON receiver. |
| `pon-id` | uint32 | Unique 32-bit value assigned to each PON. |
| `pon-tag` | string | PON-TAG description in burst profile message. |
| `protection-auto-protect` | string | Current automatic protection status of this OLT. |
| `protection-fast-failover` | boolean | Current state of the protection fast failover. |
| `protection-inactivity-alarm` | string | Inactivity alarm status (Raised or Cleared). |
| `protection-status` | string | Current PON protection status. |
| `protection-watch` | enumeration (enum: disabled, enabled, enabled-switchover) | Current protection watch status of this OLT. |
| `protection-last-switchover-time` | date-and-time | Timestamp of the last PON protection switchover. |
| `protection-last-switchover-type` | string | Type of the last PON protection switchover. |
| `port-id` *(key)* | string (length 0..256) |  |
| `device-id` | string (length 0..256) |  |
| `aging-time` | uint16 (units seconds) | Dynamic MAC Address aging time. When the aging time expires, the address is removed from the Dynamic MAC learning table. |

### `PON_OLT_PLUG_FW_BANK_VERSION_STATE`

- **Key:** `name`, `bank-id`
- **Description:** The version of firmware in the 4 banks on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | leafref → name | References PON_OLT_PLUG_STATE_LIST. |
| `bank-id` *(key)* | uint8 | Index for this entry. |
| `version` | string | Firmwre version. |

### `PON_OLT_PLUG_FW_UPGRADE_STATUS`

- **Key:** `name`
- **Description:** Firmware upgrade status. If a firmware upgrade is currently in-progress, the current status is reported. Otherwise, the status is reported for the last firmware upgrade performed for this OLT.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | leafref → name | References PON_OLT_PLUG_STATE_LIST. |
| `bank` | uint16 | Last firmware bank number (software download ME ID) firmware was downloaded to. |
| `fx-code` | uint32 | OLT Software Download error code. |
| `file` | string | Name of the file to download. |
| `status` | string | Software download status (Downloading, Success, Failed). |
| `upgrade-duration` | string | Length of time in hours, minutes, and seconds for the OLT upgrade to complete. |
| `upgrade-time` | date-and-time | Timestamp reporting time the OLT was upgraded. |

### `PON_OLT_PLUG_STATE`

- **Key:** `name`
- **Description:** List of OLT plug state entries.

| Field | Type | Description |
| --- | --- | --- |
| `name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `fw-bank-ptr` | uint16 | Current Firmware bank pointer. |
| `fw-version` | string | The current running version of firmware. |
| `hardware-version` | string | OLT module hardware revision. |
| `manufacturer` | string | Manufacturer of the module. |
| `manufacturer-model` | string | Manufacturer model of the module. |
| `manufacturer-serial-number` | string | OLT subassembly serial number. |
| `model` | string | Manufacturer Model Name. |
| `online-time` | date-and-time | The last time the Controller successfully completed configuration of the OLT. |
| `production-code` | string | Device production code. |
| `serial-number` | string | The serial number for the Module. This value is assigned by the vendor of the OLT module and is often OLT-<MAC Address>. |
| `uptime` | uint64 (units milliseconds) | The time since the OLT module was reset. |
| `switch-chassis-id` | string | MAC address of switch. |
| `switch-ipv4-address` | string | IP Address of the switch. |
| `switch-ipv6-address` | string | IP Address of the switch. |
| `switch-port-description` | string | String description of the port. |
| `switch-port-id` | string | String identification for the port. |
| `switch-system-description` | string | System Description. |
| `switch-system-name` | string | Name for the Switch. |
| `fw-upgrade-bank` | uint16 | Last firmware bank number (software download ME ID) firmware was downloaded to. |
| `fw-upgrade-fx-code` | uint32 | OLT Software Download error code. |
| `fw-upgrade-file` | string | Name of the file to download. |
| `fw-upgrade-status` | string | Software download status (Downloading, Success, Failed). |
| `fw-upgrade-duration` | string | Length of time in hours, minutes, and seconds for the OLT upgrade to complete. |
| `fw-upgrade-time` | date-and-time | Timestamp reporting time the OLT was upgraded. |
| `hw-failure` | string | Current hardware failure status. |

### `PON_ONU_FW_BANK_VERSION_STATE`

- **Key:** `onu-name`, `bank-id`
- **Description:** Current firmware contents of ONU banks.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `bank-id` *(key)* | uint8 | Index for this entry. |
| `version` | string | Firmware version. |

### `PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_MAP_STATE`

- **Key:** `onu-name`, `olt-service-id`, `priority`
- **Description:** Mapping entry that classifies VLAN CoS bit values to a desinstation GPON XGEM Port or EPON LLID (OLT-Service) offset.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE_LIST. |
| `olt-service-id` *(key)* | leafref → olt-service-id | References PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE_LIST. |
| `priority` *(key)* | uint8 | Priority (CoS bit) value. |
| `olt-service-offset` | uint8 | Destination GPON XGEM Port or EPON LLID offset that the start/end CoS values are classified to. |

### `PON_ONU_OLT_SERVICE_DOWNSTREAM_QOS_MAP_STATE`

- **Key:** `onu-name`, `olt-service-id`
- **Description:** Downstream QoS Map.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `olt-service-id` *(key)* | leafref → olt-service-id | References PON_ONU_OLT_SERVICE_STATE_LIST. |
| `type` | string | Type of Downstream QoS Map. |

### `PON_ONU_OLT_SERVICE_NETWORK_STATE`

- **Key:** `onu-name`, `olt-service-id`, `network-id`
- **Description:** List of C-VLAN IDs through the service flow List of PON VLAN network through service flow.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `olt-service-id` *(key)* | leafref → olt-service-id | References PON_ONU_OLT_SERVICE_STATE_LIST. |
| `network-id` *(key)* | uint16 | Index for this entry. |
| `vlan-id` | uint16 (range 0..4095) | VLAN ID. |

### `PON_ONU_OLT_SERVICE_STATE`

- **Key:** `onu-name`, `olt-service-id`
- **Description:** The OLT provisioned services for this ONU. An entry exists for each service on the OLT for this ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `olt-service-id` *(key)* | uint32 | OLT Service Port number. |
| `enable` | boolean | If the service port is currently enabled or disabled. |
| `learning-limit` | uint16 | Dynamic MAC learning table size limit for this service port. A value of '0' indicates that MAC Learning is disabled for this service. |
| `tcont-service-ref` | string | none - OLT Service Port operates as a TCONT + XGem Port. GPON ONLY: Reference to a OLT Service Port operating in TCONT + XGem mode. A blank value indicates this OLT Service Port is operating as TCONT + XGem. Otherwise, a non-empty value indicates this OLT Serice Port is operating in XGem-only mode, where the value references another OLT Service Port that serves as the TCONT for this XGem Port. |
| `unicast-id` | uint16 | XGEM Port ID or LLID for unicast traffic on this service port. |
| `upstream-priority-treatment` | enumeration (enum: copy, set) | Treatment of priority (CoS) bits in VLAN tags added or translated by the OLT for frames received upstream from the ONU. |
| `upstream-priority-value` | uint8 | VLAN tag priority value to insert in frames when the upstream-priority-treatment attribute is 'set'. |
| `sla-downstream-guaranteed-rate` | uint32 (units kbps) | Guaranteed (high priority) rate in kbps. |
| `sla-downstream-guaranteed-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The guaranteed rate is enforced at this burst size. |
| `sla-downstream-best-effort-rate` | uint32 (units kbps) | Best Effort (low priority) rate in kbps. |
| `sla-downstream-best-effort-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The best effort rate is enforced at this burst size. |
| `sla-upstream-fixed-rate` | uint32 (units kbps) | Fixed grant rate in kbps. This is an unsolicited grant by the DBA regardless of need. |
| `sla-upstream-guaranteed-rate` | uint32 (units kbps) | Guaranteed (high priority) rate in kbps. |
| `sla-upstream-guaranteed-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The guaranteed rate is enforced at this burst size. |
| `sla-upstream-priority` | uint8 | Priority level for the guaranteed portion of the SLA. |
| `sla-upstream-best-effort-rate` | uint32 (units kbps) | Best Effort (low priority) rate in kbps. |
| `sla-upstream-best-effort-maximum-burst` | uint32 (units kBytes) | Maximum burst size in Kilobytes. The best effort rate is enforced at this burst size. |
| `sla-upstream-best-effort-priority` | uint8 | Priority level for the Best Effort portion of the SLA. |
| `downstream-qos-map` | string | Name of the downstream QoS map applied to this OLT service port. |

### `PON_ONU_STATE`

- **Key:** `onu-name`
- **Description:** List of ONUs.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | string | Name identifier used by the NETCONF interface to reference this ONU device. |
| `timestamp` | date-and-time | The last update for this state file. |
| `onu-id` | uint16 | XGS-PON ONLY: ONU ID used on the PON. |
| `cvid` | uint16 | VID for Add CTag service configuration. |
| `equipment-id` | string | XGS-PON ONLY: Equipment ID as reported by the ONU through G.988 ONU-G. |
| `fw-bank-ptr` | uint16 | Current value of the firmware bank pointer. |
| `fw-version` | string | Current firmware running on the ONU. |
| `hardware-version` | string | XGS-PON ONLY: Hardware version reported by the ONU. |
| `last-provisioning-time` | date-and-time | The last time the Controller completed provisioning service for the ONU. |
| `mac-address` | mac-address | EPON ONLY: MAC Address for this ONU. |
| `manufacturer` | string | Manufacturer of the ONU. |
| `model` | string | Model name for the ONU. |
| `online-time` | date-and-time | The last time the ONU successfully completed registration with the OLT. |
| `realtime-stats` | boolean | Enables the ONU state files to show all statistics on every cycle. |
| `registration-id` | string | XGS-PON ONLY: ID used for this ONU during PLOAM registration. This value is sometimes used to authenticate the ONU. |
| `alloc-id-omcc` | uint16 | ONU ID used on the PON. |
| `host-mac-address` | mac-address | MAC Address of the IP Host running on this ONU. |
| `laser-bias-current` | uint64 (units microamp) | Current in microAmps. This is reported by the XGS ONU when an Optical Line Supervision Test is performed on the ONU. |
| `logical-id` | string | Logical ID programmed in XGS-PON ONU. |
| `logical-password` | string | Logical Password programmed in XGS-PON ONU. |
| `omci-txn-correlation-id` | uint16 | Last OMCI transaction correllation identifier sent by the PON Controller to the ONU. |
| `omcc-version` | hex-string | This attribute identifies the version of the OMCC protocol being used by the ONU. |
| `temperature` | decimal64 (frac-digits 3; units degrees celsius) | Temperature in degrees Celsius. This is reported by the XGS ONU when an Optical Line Supervision Test is performed on the ONU. |
| `uptime` | uint64 (units centiseconds) | The time since the ONU module was reset. |
| `voltage` | decimal64 (frac-digits 3; units millivolt) | Power Feed Voltage in milliVolts. This is reported by the XGS ONU when an Optical Line Supervision Test is performed on the ONU. |
| `registration-id-hex` | hex-string | 72-character (36-byte) hex-string Registration ID for this ONU. |
| `serial-number` | string | ONU serial number. |
| `service-config` | string | Current ONU service configuration. |
| `vendor` | string | ONU Vendor. This is normally the chip vendor for the ONU. |
| `fw-upgrade-backoff-delay` | uint32 (units seconds) | Time to wait before retransmitting an window. |
| `fw-upgrade-backoff-divisor` | uint32 | Controls the size of the send window during retransmissions. A value of '2' reduces the send window size by half for each retransmission. A value of '1' disables the backoff. |
| `fw-upgrade-download-format` | fw-download-format (enum: baseline-omci, extended-omci) | The format of OMCI the PON Controller will use to upgrade the ONU, regardless of the OMCC Version it reported. |
| `fw-upgrade-end-download-timeout` | uint32 (units seconds) | Time to wait for the final acknowledgement during firmware upgrade. Increase the value to the allow the ONU additional time to write the firmware image to flash. The PON Controller automatically calculates the end-download-timeout when set to a value of zero. |
| `fw-upgrade-maximum-retries` | uint32 | Maximum number of times a window is retransmitted before terminating the ONU firmware upgrade and reporting an error. |
| `fw-upgrade-maximum-window-size` | uint32 (units bytes) | The maximum send window sized used for transfering firmware to the ONU. |
| `fw-upgrade-response-timeout` | uint32 (units seconds) | The time in seconds to wait for an acknowledgement from the ONU during firmware upgrade. |
| `server-state` | string | The last reported SSH Server status. |
| `registration-disallowed` | boolean | When true, the OLT is not allowing the ONU to register because the OLT is not specified in the ONU configuration file. This value is only true for Disallowed Admin and not for Disallowed Error. |
| `bank` | uint16 | Last firmware bank number (software download ME ID) firmware was downloaded to. |
| `current-window` | uint8 | Current window size for the software download. |
| `fx-code` | string | OMCI Software Download error code as defined in G.988. |
| `file` | string | Name of the file to download. |
| `negotiated-window` | uint8 | Initial negotiated window size for the software download. |
| `progress` | uint8 (units Percent complete 0..100) | Name of the file to download. |
| `retries` | uint8 | Number of retries during the software download. |
| `sent-blocks` | uint32 | Current number of blocks sent for the software download. |
| `status` | string | Software download status (Downloading, Success, Failed). |
| `total-blocks` | uint32 | Total number of blocks for the software download. |
| `upgrade-duration` | string | Length of time in hours, minutes, and seconds for the ONU upgrade to complete. |
| `upgrade-time` | date-and-time | Timestamp reporting time the ONU was upgraded. |
| `aborted` | boolean | When true, the ONU firmware upgrade has been aborted. |
| `failures` | uint32 | Failure count from the latest firmware upgrade on this ONU. |
| `version-mismatches` | uint32 | Version mismatch count from the latest firmware upgrade on this ONU. |

### `PON_ONU_UNI_LEARNED_ADDRESSES_STATE`

- **Key:** `onu-name`, `port-id`
- **Description:** List of CPE MAC addresses learned on the UNI port.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `port-id` *(key)* | leafref → port-id | References PON_ONU_UNI_STATE_LIST. |

### `PON_ONU_UNI_STATE`

- **Key:** `onu-name`, `port-id`
- **Description:** Status of the UNI ports on the ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `port-id` *(key)* | string | Identifier for this UNI port. |
| `duplex` | string | Sets the duplex for the Ethernet port. |
| `enable` | boolean | Current enable state of the Ethernet port. |
| `managed-entity-id` | uint16 | OMCI Managed Entity Identifier for the UNI. |
| `max-frame-size` | uint32 | Maximum Frame size limit on UNI receive. |
| `poe` | boolean | GPON ONLY: Power over Ethernet (PoE) status for the UNI port. |
| `speed` | string | Set the speed of the Ethernet port. |
| `state` | string | The link status of the UNI Ethernet port. |

## COUNTERS_DB

### `PON_OLT_INTF_STATISTICS_BINNED`

- **Key:** `olt-name`, `olt-stats-id`
- **Description:** List containing the statistics history for this device.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | date-and-time | Timestamp when the statistics were collected. |
| `timestamp` | date-and-time | Timestamp when the statistics were collected. |
| `offline-onus-count` | uint64 | Number of ONUs which were known to the OLT but are no longer active. This includes ONUs which are deregistered or have been disabled, administratively disallowed, disallowed due to too many errors detected from the ONU, or disallowed due to a mismatched PON Registration ID. |
| `online-onus-count` | uint64 | Number of ONUs which are active. This includes ONUs which are registered or unspecified. |
| `pon-fec-seconds` | uint64 | Forward Error Correction on the PON in seconds. |
| `rx-bw-ethernet-rate-bps` | uint64 | Receive BW Ethernet Rate bps. |
| `rx-bw-overhead-burst-bps` | uint64 | Receive BW Overhead Burst bps. |
| `rx-bw-overhead-fec-bps` | uint64 | Receive BW Overhead FEC bps. |
| `rx-bw-overhead-total-bps` | uint64 | Receive BW Overhead Total bps. |
| `rx-bw-packet-used-bps` | uint64 | Receive BW Packet Used bps. |
| `rx-bw-total-free-bps` | uint64 | Receive BW Total Free bps. |
| `rx-bw-total-used-bps` | uint64 | Receive BW Total Used bps. |
| `rx-bw-total-util` | uint64 | Receive BW Total Util. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-omci-mic-errors` | uint64 | Receive OMCI MIC Errors. |
| `rx-optical-level-idle` | decimal64 (frac-digits 3; units dBm) | Receive Optical Level Idle. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `rx-unmatched-drops` | uint64 | Receive Unmatched Drops. |
| `total-onus-count` | uint64 | Number of ONUs which are known to the OLT. This includes both Online and Offline ONUs. |
| `tx-bw-ethernet-rate-bps` | uint64 | Transmit BW Ethernet Rate bps. |
| `tx-bw-overhead-fec-bps` | uint64 | Transmit BW Overhead FEC bps. |
| `tx-bw-overhead-framing-bps` | uint64 | Transmit BW Overhead Framing bps. |
| `tx-bw-overhead-total-bps` | uint64 | Transmit BW Overhead Total bps. |
| `tx-bw-packet-used-bps` | uint64 | Transmit BW Packet Used bps. |
| `tx-bw-total-free-bps` | uint64 | Transmit BW Total Free bps. |
| `tx-bw-total-used-bps` | uint64 | Transmit BW Total Used bps. |
| `tx-bw-total-util` | uint64 | Transmit BW Total Util. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-idle-octets` | uint64 | Transmit Idle Octets. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-oam` | uint64 | Transmit OAM. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit Optical Level. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `uninventoried-onus-count` | uint64 | Number of ONUs which are active but not inventoried. |
| `unprovisioned-onus-count` | uint64 | Number of ONUs which are currently unprovisioned. |

### `PON_OLT_PLUG_STATISTICS_BINNED_ENV`

- **Key:** `olt-name`, `olt-stats-id`
- **Description:** OLT device environmental statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | leafref → olt-stats-id | References PON_OLT_INTF_STATISTICS_BINNED_LIST. |
| `current` | decimal64 (frac-digits 3; units microamp) | Current. |
| `transmit-bias` | decimal64 (frac-digits 3; units microamp) | Transmit Bias. |
| `voltage` | decimal64 (frac-digits 3; units millivolt) | Voltage. |

### `PON_OLT_PLUG_STATISTICS_BINNED_NNI`

- **Key:** `olt-name`, `olt-stats-id`
- **Description:** OLT NNI port statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | leafref → olt-stats-id | References PON_OLT_INTF_STATISTICS_BINNED_LIST. |
| `rx-broadcast-octets` | uint64 | Receive Broadcast Octets. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-broadcast` | uint64 | Receive Frames Broadcast. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-frames-multicast` | uint64 | Receive Frames Multicast. |
| `rx-frames-unicast` | uint64 | Receive Frames Unicast. |
| `rx-multicast-octets` | uint64 | Receive Multicast Octets. |
| `rx-oam` | uint64 | Receive OAM. |
| `rx-oam-octets` | uint64 | Receive OAM Octets. |
| `rx-other-cascading-bytes` | uint64 | Receive Other Cascading Bytes. |
| `rx-other-cascading-packets` | uint64 | Receive Other Cascading Packets. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `tomi-requests` | uint64 | TOMI Requests. |
| `tomi-resp-time-avg` | uint64 (units microseconds) | TOMI Resp Time Avg. |
| `tomi-resp-time-max` | uint64 (units microseconds) | TOMI Resp Time Max. |
| `tomi-resp-time-min` | uint64 (units microseconds) | TOMI Resp Time Min. |
| `tomi-responses` | uint64 | TOMI Responses. |
| `tomi-time-to-send-avg` | uint64 (units microseconds) | TOMI Time to Send Avg. |
| `tomi-time-to-send-max` | uint64 (units microseconds) | TOMI Time to Send Max. |
| `tomi-time-to-send-min` | uint64 (units microseconds) | TOMI Time to Send Min. |
| `tomi-timeouts` | uint64 | TOMI Timeouts. |
| `tx-broadcast-octets` | uint64 | Transmit Broadcast Octets. |
| `tx-cascading-bytes` | uint64 | Transmit Cascading Bytes. |
| `tx-cascading-packets` | uint64 | Transmit Cascading Packets. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-multicast-octets` | uint64 | Transmit Multicast Octets. |
| `tx-non_control-octets` | uint64 | Transmit Non-Control Octets. |
| `tx-oam` | uint64 | Transmit OAM. |
| `tx-oam-octets` | uint64 | Transmit OAM Octets. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |

### `PON_OLT_PLUG_STATISTICS_BINNED_TEMP`

- **Key:** `olt-name`, `olt-stats-id`
- **Description:** OLT device temperatures.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | leafref → olt-stats-id | References PON_OLT_INTF_STATISTICS_BINNED_LIST. |
| `asic` | uint64 (units degrees celsius) | ASIC temperature. |
| `laser` | uint64 (units degrees celsius) | Laser temperature. |
| `xcvr` | uint64 (units degrees celsius) | Transceiver temperature. |

### `PON_OLT_STATISTICS_ACCUMULATING`

- **Key:** `olt-name`
- **Description:** OLT PON port statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `offline-onus-count` | uint64 | Number of ONUs which were known to the OLT but are no longer active. This includes ONUs which are deregistered or have been disabled, administratively disallowed, disallowed due to too many errors detected from the ONU, or disallowed due to a mismatched PON Registration ID. |
| `online-onus-count` | uint64 | Number of ONUs which are active. This includes ONUs which are registered or unspecified. |
| `pon-fec-seconds` | uint64 | Forward Error Correction on the PON in seconds. |
| `rx-bw-ethernet-rate-bps` | uint64 | Receive BW Ethernet Rate bps. |
| `rx-bw-overhead-burst-bps` | uint64 | Receive BW Overhead Burst bps. |
| `rx-bw-overhead-fec-bps` | uint64 | Receive BW Overhead FEC bps. |
| `rx-bw-overhead-total-bps` | uint64 | Receive BW Overhead Total bps. |
| `rx-bw-packet-used-bps` | uint64 | Receive BW Packet Used bps. |
| `rx-bw-total-free-bps` | uint64 | Receive BW Total Free bps. |
| `rx-bw-total-used-bps` | uint64 | Receive BW Total Used bps. |
| `rx-bw-total-util` | uint64 | Receive BW Total Util. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-omci-mic-errors` | uint64 | Receive OMCI MIC Errors. |
| `rx-optical-level-idle` | decimal64 (frac-digits 3; units dBm) | Receive Optical Level Idle. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `rx-unmatched-drops` | uint64 | Receive Unmatched Drops. |
| `total-onus-count` | uint64 | Number of ONUs which are known to the OLT. This includes both Online and Offline ONUs. |
| `tx-bw-ethernet-rate-bps` | uint64 | Transmit BW Ethernet Rate bps. |
| `tx-bw-overhead-fec-bps` | uint64 | Transmit BW Overhead FEC bps. |
| `tx-bw-overhead-framing-bps` | uint64 | Transmit BW Overhead Framing bps. |
| `tx-bw-overhead-total-bps` | uint64 | Transmit BW Overhead Total bps. |
| `tx-bw-packet-used-bps` | uint64 | Transmit BW Packet Used bps. |
| `tx-bw-total-free-bps` | uint64 | Transmit BW Total Free bps. |
| `tx-bw-total-used-bps` | uint64 | Transmit BW Total Used bps. |
| `tx-bw-total-util` | uint64 | Transmit BW Total Util. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-idle-octets` | uint64 | Transmit Idle Octets. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-oam` | uint64 | Transmit OAM. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit Optical Level. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `uninventoried-onus-count` | uint64 | Number of ONUs which are active but not inventoried. |
| `unprovisioned-onus-count` | uint64 | Number of ONUs which are currently unprovisioned. |

### `PON_OLT_STATISTICS_ACCUMULATING_ENV`

- **Key:** `olt-name`
- **Description:** OLT device environmental statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `current` | decimal64 (frac-digits 3; units microamp) | Current. |
| `transmit-bias` | decimal64 (frac-digits 3; units microamp) | Transmit Bias. |
| `voltage` | decimal64 (frac-digits 3; units millivolt) | Voltage. |

### `PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING`

- **Key:** `olt-name`, `olt-id`
- **Description:** OLT PON Flooding (link) statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-id` *(key)* | uint16 | OLT PON Flood ID (GPON: Multicast XGEM Port ID, EPON: Multicast LLID). |
| `tx-bw-best-effort-sla-util` | uint64 | Transmit BW Best Effort SLA Util. |
| `tx-bw-best-effort-sla-bps` | uint64 | Transmit BW Best Effort SLA bps. |
| `tx-bw-guaranteed-sla-util` | uint64 | Transmit BW Guaranteed SLA Util. |
| `tx-bw-guaranteed-sla-bps` | uint64 | Transmit BW Guaranteed SLA bps. |
| `tx-bw-total-sla-util` | uint64 | Transmit BW Total SLA Util. |
| `tx-bw-total-sla-bps` | uint64 | Transmit BW Total SLA bps. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames` | uint64 | Transmit Frames. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-rate-bps` | uint64 | Transmit Rate bps. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |

### `PON_OLT_STATISTICS_ACCUMULATING_PON_FLOODING_NNI_NETWORK`

- **Key:** `olt-name`, `olt-id`
- **Description:** List of VLAN Tags identifying the NNI Networks using this PON Flood ID.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-id` *(key)* | uint16 | OLT PON Flood ID (GPON: Multicast XGEM Port ID, EPON: Multicast LLID). |

### `PON_OLT_STATISTICS_ACCUMULATING_TEMP`

- **Key:** `olt-name`
- **Description:** OLT device temperatures.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `asic` | uint64 (units degrees celsius) | ASIC temperature. |
| `laser` | uint64 (units degrees celsius) | Laser temperature. |
| `xcvr` | uint64 (units degrees celsius) | Transceiver temperature. |

### `PON_OLT_STATISTICS_BINNED_PON_FLOODING`

- **Key:** `olt-name`, `olt-stats-id`, `flood-id`
- **Description:** OLT PON Flooding (link) statistics.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | leafref → olt-stats-id | References PON_OLT_INTF_STATISTICS_BINNED_LIST. |
| `flood-id` *(key)* | uint16 | OLT PON Flood ID (GPON: Multicast XGEM Port ID, EPON: Multicast LLID). |
| `tx-bw-best-effort-sla-util` | uint64 | Transmit BW Best Effort SLA Util. |
| `tx-bw-best-effort-sla-bps` | uint64 | Transmit BW Best Effort SLA bps. |
| `tx-bw-guaranteed-sla-util` | uint64 | Transmit BW Guaranteed SLA Util. |
| `tx-bw-guaranteed-sla-bps` | uint64 | Transmit BW Guaranteed SLA bps. |
| `tx-bw-total-sla-util` | uint64 | Transmit BW Total SLA Util. |
| `tx-bw-total-sla-bps` | uint64 | Transmit BW Total SLA bps. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames` | uint64 | Transmit Frames. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-rate-bps` | uint64 | Transmit Rate bps. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |

### `PON_OLT_STATISTICS_BINNED_PON_FLOODING_NETWORK`

- **Key:** `olt-name`, `olt-stats-id`, `flood-id`
- **Description:** List of VLAN Tags identifying the NNI Networks using this PON Flood ID.

| Field | Type | Description |
| --- | --- | --- |
| `olt-name` *(key)* | leafref → olt-name | References PON_OLT_INTF_STATE_LIST. |
| `olt-stats-id` *(key)* | leafref → olt-stats-id | References PON_OLT_INTF_STATISTICS_BINNED_LIST. |
| `flood-id` *(key)* | leafref → flood-id | References PON_OLT_STATISTICS_BINNED_PON_FLOODING_LIST. |

### `PON_ONU_STATISTICS_ACCUMULATING_OLT_PON`

- **Key:** `onu-name`
- **Description:** PON statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `rx-optical-level` | decimal64 (frac-digits 3; units dBm) | Receive optical level. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit optical level. |
| `rx-deregistrations` | uint64 | Number of times the ONU has deregistered. |
| `rx-registrations` | uint64 | Number of times the ONU has completed registration. |
| `fiber-distance` | decimal64 (frac-digits 3; units kilometers) | Reports the ONU fiber distance in kilometers. |
| `equalization-delay` | uint64 (units upstream-slots(12.8ns)) | XGS-PON ONLY: Equalization delay assigned by the OLT to an ONU to ensure that the ONU's transmissions are aligned on a common upstream time reference. |
| `round-trip-time` | uint64 (units TQ(16ns)) | EPON ONLY: Calculated Route Trip Time (RTT) between the OLT and ONU. |
| `one-way-delay` | uint64 (units microseconds) | One way delay reported for an ONU. |

### `PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_OMCC`

- **Key:** `onu-name`
- **Description:** GPON: OMCI channel statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `bad-key-exchanges` | uint64 | Bad Key Exchanges. |
| `enable-count` | uint64 | Number of times the OLT-Service was activated. |
| `good-key-exchanges` | uint64 | Good Key Exchanges. |
| `omci-oam-requests` | uint64 | OMCI/OAM Requests. |
| `omci-oam-resp-time-avg` | uint64 (units microseconds) | OMCI/OAM Resp Time Avg. |
| `omci-oam-resp-time-max` | uint64 (units microseconds) | OMCI/OAM Resp Time Max. |
| `omci-oam-resp-time-min` | uint64 (units microseconds) | OMCI/OAM Resp Time Min. |
| `omci-oam-responses` | uint64 | OMCI/OAM Responses. |
| `omci-oam-time-to-send-avg` | uint64 (units microseconds) | OMCI/OAM Time to Send Avg. |
| `omci-oam-time-to-send-max` | uint64 (units microseconds) | OMCI/OAM Time to Send Max. |
| `omci-oam-time-to-send-min` | uint64 (units microseconds) | OMCI/OAM Time to Send Min. |
| `omci-oam-timeouts` | uint64 | OMCI/OAM Timeouts. |
| `ploam-timeouts` | uint64 | PLOAM Timeouts. |
| `rx-all-bandwidth-reqs` | uint64 | Receive All Bandwidth Reqs. |
| `rx-bw-best-effort-sla-util` | uint64 | Receive BW Best Effort SLA Util. |
| `rx-bw-best-effort-sla-bps` | uint64 | Receive BW Best Effort SLA bps. |
| `rx-bw-fixed-sla-util` | uint64 | Receive BW Fixed SLA Util. |
| `rx-bw-fixed-sla-bps` | uint64 | Receive BW Fixed SLA bps. |
| `rx-bw-guaranteed-sla-util` | uint64 | Receive BW Guaranteed SLA Util. |
| `rx-bw-guaranteed-sla-bps` | uint64 | Receive BW Guaranteed SLA bps. |
| `rx-bw-total-sla-util` | uint64 | Receive BW Total SLA Util. |
| `rx-bw-total-sla-bps` | uint64 | Receive BW Total SLA bps. |
| `rx-bad-icv-drops` | uint64 | Receive Bad ICV Drops. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-control-octets` | uint64 | Receive Control Octets. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-key-mismatch-octets` | uint64 | Receive Key Mismatch Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-oam` | uint64 | Receive OAM. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-reports` | uint64 | Receive REPORTs. |
| `rx-rate-bps` | uint64 | Receive Rate bps. |
| `rx-security-drop-octets` | uint64 | Receive Security Drop Octets. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `tx-bw-best-effort-sla-util` | uint64 | Transmit BW Best Effort SLA Util. |
| `tx-bw-best-effort-sla-bps` | uint64 | Transmit BW Best Effort SLA bps. |
| `tx-bw-guaranteed-sla-util` | uint64 | Transmit BW Guaranteed SLA Util. |
| `tx-bw-guaranteed-sla-bps` | uint64 | Transmit BW Guaranteed SLA bps. |
| `tx-bw-total-sla-util` | uint64 | Transmit BW Total SLA Util. |
| `tx-bw-total-sla-bps` | uint64 | Transmit BW Total SLA bps. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-control-octets` | uint64 | Transmit Control Octets. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-gates` | uint64 | Transmit GATEs. |
| `tx-grant-ups-tq` | uint64 | Transmit Grant UPS Tq. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-oam` | uint64 | Transmit OAM. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-ploam-ds-ranging-time` | uint64 | Transmit PLOAM DS Ranging Time. |
| `tx-rate-bps` | uint64 | Transmit Rate bps. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `tx-upstream-slots` | uint64 | Transmit Upstream Slots. |

### `PON_ONU_STATISTICS_ACCUMULATING_OLT_PON_SERVICE`

- **Key:** `onu-name`, `onu-id`
- **Description:** OLT-Service Port statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint8 | OLT-Service Port number. |
| `bad-key-exchanges` | uint64 | Bad Key Exchanges. |
| `enable-count` | uint64 | Number of times the OLT-Service was activated. |
| `good-key-exchanges` | uint64 | Good Key Exchanges. |
| `omci-oam-requests` | uint64 | OMCI/OAM Requests. |
| `omci-oam-resp-time-avg` | uint64 (units microseconds) | OMCI/OAM Resp Time Avg. |
| `omci-oam-resp-time-max` | uint64 (units microseconds) | OMCI/OAM Resp Time Max. |
| `omci-oam-resp-time-min` | uint64 (units microseconds) | OMCI/OAM Resp Time Min. |
| `omci-oam-responses` | uint64 | OMCI/OAM Responses. |
| `omci-oam-time-to-send-avg` | uint64 (units microseconds) | OMCI/OAM Time to Send Avg. |
| `omci-oam-time-to-send-max` | uint64 (units microseconds) | OMCI/OAM Time to Send Max. |
| `omci-oam-time-to-send-min` | uint64 (units microseconds) | OMCI/OAM Time to Send Min. |
| `omci-oam-timeouts` | uint64 | OMCI/OAM Timeouts. |
| `ploam-timeouts` | uint64 | PLOAM Timeouts. |
| `rx-all-bandwidth-reqs` | uint64 | Receive All Bandwidth Reqs. |
| `rx-bw-best-effort-sla-util` | uint64 | Receive BW Best Effort SLA Util. |
| `rx-bw-best-effort-sla-bps` | uint64 | Receive BW Best Effort SLA bps. |
| `rx-bw-fixed-sla-util` | uint64 | Receive BW Fixed SLA Util. |
| `rx-bw-fixed-sla-bps` | uint64 | Receive BW Fixed SLA bps. |
| `rx-bw-guaranteed-sla-util` | uint64 | Receive BW Guaranteed SLA Util. |
| `rx-bw-guaranteed-sla-bps` | uint64 | Receive BW Guaranteed SLA bps. |
| `rx-bw-total-sla-util` | uint64 | Receive BW Total SLA Util. |
| `rx-bw-total-sla-bps` | uint64 | Receive BW Total SLA bps. |
| `rx-bad-icv-drops` | uint64 | Receive Bad ICV Drops. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-control-octets` | uint64 | Receive Control Octets. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-key-mismatch-octets` | uint64 | Receive Key Mismatch Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-rate-bps` | uint64 | Receive Rate bps. |
| `rx-security-drop-octets` | uint64 | Receive Security Drop Octets. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `tx-bw-best-effort-sla-util` | uint64 | Transmit BW Best Effort SLA Util. |
| `tx-bw-best-effort-sla-bps` | uint64 | Transmit BW Best Effort SLA bps. |
| `tx-bw-guaranteed-sla-util` | uint64 | Transmit BW Guaranteed SLA Util. |
| `tx-bw-guaranteed-sla-bps` | uint64 | Transmit BW Guaranteed SLA bps. |
| `tx-bw-total-sla-util` | uint64 | Transmit BW Total SLA Util. |
| `tx-bw-total-sla-bps` | uint64 | Transmit BW Total SLA bps. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-control-octets` | uint64 | Transmit Control Octets. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-ploam-ds-ranging-time` | uint64 | Transmit PLOAM DS Ranging Time. |
| `tx-rate-bps` | uint64 | Transmit Rate bps. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `tx-upstream-slots` | uint64 | Transmit Upstream Slots. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ENHANCED_TC_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Enhanced TC statistics reported by ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this TC. |
| `lods-event-count` | uint64 | Counts the number of state transitions from O5.1 to O6. |
| `lods-event-restored-count` | uint64 | Counts the number of LODS cleared events. |
| `fragment-xgem-frames` | uint64 | Counts the number of XGEM frames that represent fragmented SDUs, as indicated by the LF bit = 0. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `onu-reactivation-by-lods-events` | uint64 | Counts the number of LODS events resulting in ONU reactivation without synchronization being reacquired. |
| `psbd-hec-error-count` | uint64 | Counts HEC errors in any of the fields of the downstream physical sync block. |
| `received-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of received bytes in non-idle XGEM frames. |
| `transmitted-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of transmitted bytes in non-idle XGEM frames. |
| `transmitted-xgem-frames` | uint64 | Counts the number of non-idle XGEM frames transmitted. If an SDU is fragmented, each fragment is an XGEM frame and is counted as such. |
| `unknown-profile-count` | uint64 | Counts the number of grants received whose specified profile was not known to the ONU. |
| `xgem-hec-lost-words-count` | uint64 | Counts the number of 4 byte words lost because of an XGEM frame HEC error. In general, all XGTC payload following the error is lost, until the next PSBd event. |
| `xgem-key-errors` | uint64 | Counts the number of downstream XGEM frames received with an invalid key specification. |
| `xgem-hec-error-count` | uint64 | Counts the number of instances of an XGEM frame HEC error. |
| `xgtc-hec-error-count` | uint64 | Counts HEC errors detected in the XGTC header. |
| `threshold-data-64-bit-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: MAC Bridge Port statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `direction` | enumeration (enum: downstream, upstream) | Direction of the traffic flow for this statistics entry. |
| `broadcast-frames` | uint64 | broadcast frames. |
| `crc-errored-frames` | uint64 | crc errored frames. |
| `drop-events` | uint64 | drop events. |
| `frames` | uint64 | frames. |
| `frames-1024-to-1518-octets` | uint64 | frames 1024 to 1518 octets. |
| `frames-128-to-255-octets` | uint64 | frames 128 to 255 octets. |
| `frames-256-to-511-octets` | uint64 | frames 256 to 511 octets. |
| `frames-512-to-1023-octets` | uint64 | frames 512 to 1023 octets. |
| `frames-64-octets` | uint64 | frames 64 octets. |
| `frames-65-to-127-octets` | uint64 | frames 65 to 127 octets. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-frames` | uint64 | multicast frames. |
| `octets` | uint64 | octets. |
| `oversize-frames` | uint64 | oversize frames. |
| `undersize-frames` | uint64 | undersize frames. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: MAC Bridge Port 64-bit statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `direction` | enumeration (enum: downstream, upstream) | Direction of the traffic flow for this statistics entry. |
| `broadcast-frames` | uint64 | broadcast frames. |
| `crc-errored-frames` | uint64 | crc errored frames. |
| `drop-events` | uint64 | drop events. |
| `frames` | uint64 | frames. |
| `frames-1024-to-1518-octets` | uint64 | frames 1024 to 1518 octets. |
| `frames-128-to-255-octets` | uint64 | frames 128 to 255 octets. |
| `frames-256-to-511-octets` | uint64 | frames 256 to 511 octets. |
| `frames-512-to-1023-octets` | uint64 | frames 512 to 1023 octets. |
| `frames-64-octets` | uint64 | frames 64 octets. |
| `frames-65-to-127-octets` | uint64 | frames 65 to 127 octets. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-frames` | uint64 | multicast frames. |
| `octets` | uint64 | octets. |
| `oversize-frames` | uint64 | oversize frames. |
| `undersize-frames` | uint64 | undersize frames. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_FRAME_PM_UPSTREAM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Ethernet UNI port statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `alignment-error-counter` | uint64 | alignment error counter. |
| `buffer-overflows-on-receive` | uint64 | buffer overflows on receive. |
| `buffer-overflows-on-transmit` | uint64 | buffer overflows on transmit. |
| `carrier-sense-error-counter` | uint64 | carrier sense error counter. |
| `deferred-transmission-counter` | uint64 | deferred transmission counter. |
| `excessive-collision-counter` | uint64 | excessive collision counter. |
| `fcs-errors` | uint64 | fcs errors. |
| `frames-too-long` | uint64 | frames too long. |
| `internal-mac-receive-error-counter` | uint64 | internal mac receive error counter. |
| `internal-mac-transmit-error-counter` | uint64 | internal mac transmit error counter. |
| `interval-end-time` | uint64 | interval end time. |
| `late-collision-counter` | uint64 | late collision counter. |
| `multiple-collisions-frame-counter` | uint64 | multiple collisions frame counter. |
| `single-collision-frame-counter` | uint64 | single collision frame counter. |
| `sqe-counter` | uint64 | sqe counter. |
| `threshold-data-half-id` | uint64 | threshold data half id. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_ETHERNET_PM3`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with ethernet messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | Total number of received good packets directed to the broadcast address. This does not include multicast packets. |
| `drop-events` | uint64 | Total number of events in which packets were dropped due to a lack of resources. |
| `fragments` | uint64 | Total number of packets received that were less than 64 octets long. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `jabbers` | uint64 | Total number of packets received that were longer than 1518 octets. |
| `multicast-packets` | uint64 | Total number of received good packets directed to a multicast address. This does not include broadcast packets. |
| `octets` | uint64 | Total number of octets received from the CPE, including those in bad packets. |
| `packets` | uint64 | Total number of packets received, including bad packets, broadcast packets and multicast packets. |
| `packets-64-octets` | uint64 | Total number of received packets (including bad packets) that were 64 octets long. |
| `packets-65-to-127-octets` | uint64 | Total number of received packets (including bad packets) that were 65 to 127 octets long. |
| `packets-128-to-255-octets` | uint64 | Total number of received packets (including bad packets) that were 128 to 255 octets long. |
| `packets-256-to-511-octets` | uint64 | Total number of received packets (including bad packets) that were 256 to 511 octets long. |
| `packets-512-to-1023-octets` | uint64 | Total number of received packets (including bad packets) that were 512 to 1023 octets long. |
| `packets-1024-to-1518-octets` | uint64 | Total number of received packets (including bad packets) that were 1024 to 1518 octets long. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `undersize-packets` | uint64 | Counts the number of frames discarded due to PPPoE filtering. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_FEC_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: FEC statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `corrected-bytes` | uint64 | corrected bytes. |
| `corrected-code-words` | uint64 | corrected code words. |
| `fec-seconds` | uint64 | fec seconds. |
| `interval-end-time` | uint64 | interval end time. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `total-code-words` | uint64 | total code words. |
| `uncorrectable-code-words` | uint64 | uncorrectable code words. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_GAL_ETHERNET_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with gal ethernet messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `discarded-downstream-frames` | uint64 | Counts the number of downstream GEM frames discarded for any reason. |
| `discarded-upstream-frames` | uint64 | Counts the number of upstream frames discarded prior to GEM encapsulation (due to congestion). |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_GEM_PORT_NETWORK_CTP_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with gem port network ctp messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `encryption-key-errors` | uint64 | Counts GEM frames with erroneous encryption key indexes. If the GEM port is not encrypted, this attribute counts any frame with a key index not equal to 0. If the GEM port is encrypted, this attribute counts any frame whose key index specifies a key that is not known to the ONU. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `received-gem-frames` | uint64 | Counts GEM frames received correctly on the monitored GEM port. A correctly received GEM frame is one that does not contain uncorrectable errors and has a valid header error check (HEC). |
| `received-payload-bytes` | uint64 | Counts user payload bytes received on the monitored GEM port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `transmitted-gem-frames` | uint64 | Counts GEM frames transmitted on the monitored GEM port. |
| `transmitted-payload-bytes` | uint64 | Counts user payload bytes transmitted on the monitored GEM port. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_IP_HOST_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-id`
- **Description:** ME collects PM data related to an IP host.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this IP host. |
| `dns-errors` | uint64 | Counts DNS errors received. |
| `dhcp-timeouts` | uint64 | Counts DHCP timeouts received. |
| `icmp-errors` | uint64 | Counts ICMP errors received. |
| `internal-error` | uint64 | Incremented whenever the ONU encounters an internal error condition such as a driver interface failure in the IP stack. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `ip-address-conflict` | uint64 | Incremented whenever the ONU detects a conflicting IP address on the network. A conflicting IP address is one that has the same value as the one curently assigned to the ONU. |
| `out-of-memory` | uint64 | Incremented whenever the ONU encounters an out of memory condition in the IP stack. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_MAC_BRIDGE_PORT_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: ME collects PM data related to a mac bridge port.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this mac bridge port. |
| `delay-exceeded-discard-counter` | uint64 | Counts frames discarded on this port because transmission was delayed. |
| `forwarded-frame-counter` | uint64 | Counts frames transmitted successfully on this port. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `mtu-exceeded-discard-counter` | uint64 | Counts frames discarded on this port because the MTU was exceeded. |
| `received-and-discarded-counter` | uint64 | Counts frames received on this port that were discarded due to errors. |
| `received-frame-counter` | uint64 | Counts frames received on this port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_OPERATIONAL_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with operational messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `cpu-percent-utilization` | uint64 | Maximum system CPU utilization (high water mark) during the measurement interval. |
| `errors-in-operations` | uint64 | Count of the number of detected errors in operations, not due to a software error. |
| `flash-size-available` | uint64 | Minimum FLASH size available during the measurement interval. |
| `flash-utilization` | uint64 | Maximum FLASH size utilized during the measurement interval. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `ram-size-available` | uint64 | Minimum RAM size available during the measurement interval. |
| `ram-utilization` | uint64 | Maximum RAM size utilized during the measurement interval. |
| `software-errors` | uint64 | Count of the number of software errors detected. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `temperature-sensor-description` | uint64 | A table of temperature sensor descriptions that includes the physical location on the ONU or the component being measured. |
| `temperature-sensor-value` | uint64 | A table of temperature sensor values that specifies the average temperature of the ONU temperature sensor(s) during the measurement interval. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_PON`

- **Key:** `onu-name`
- **Description:** PON statistics reported by ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `rx-optical-level` | decimal64 (frac-digits 3; units dBm) | Receive Optical Level. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit Optical Level. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_RS232_RS485_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-id`
- **Description:** ME collects PM data for a RS232/RS485 interface.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this RS232/RS485 interface. |
| `incoming-bytes-from-chip` | uint64 | Counts the bytes received on the RS232/RS485 chipset. |
| `incoming-bytes-from-pon` | uint64 | Counts the bytes received on the PON port. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `outgoing-bytes-from-chip` | uint64 | Counts the bytes transmitted on the RS232/RS485 chipset. |
| `outgoing-bytes-from-pon` | uint64 | Counts the bytes transmitted on the PON port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_TCP_UDP_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-id`
- **Description:** ME collects PM data related to a TCP or UDP port.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this TCP or UDP port. |
| `accept-failed` | uint64 | Incremented when an attempt to accept a connection on a port fails. |
| `bind-failed` | uint64 | Incremented when an attempt by a service to bind to a port fails. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `listen-failed` | uint64 | Incremented when an attempt by a service to listen for a request on a port fails. |
| `select-failed` | uint64 | Incremented when an attempt to perform a select on a group of ports fails. |
| `socket-failed` | uint64 | Incremented when an attempt to create a socket associated with a port fails. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_DOWNSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with downstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `ploam-mic-error-count` | uint64 | Counts MIC errors detected in downstream PLOAM messages, either directed to this ONU or broadcast to all ONUs. |
| `downstream-ploam-message-count` | uint64 | Counts PLOAM messages received, either directed to this ONU or broadcast to all ONUs. |
| `profile-messages-received` | uint64 | Counts the number of profile messages received, either directed to this ONU or broadcast to all ONUs. |
| `ranging-time-messages-received` | uint64 | Counts the number of ranging_time messages received, either directed to this ONU or broadcast to all ONUs. |
| `deactivate-onu-id-messages-received` | uint64 | Counts the number of deactivate_ONU-ID messages received, either directed to this ONU or broadcast to all ONUs. |
| `disable-serial-number-messages-received` | uint64 | Counts the number of disable_serial_number messages received, whose serial number specified this ONU. |
| `request-registration-messages-received` | uint64 | Counts the number of request_registration messages received. |
| `assign-alloc-id-messages-received` | uint64 | Counts the number of assign_alloc-ID messages received. |
| `key-control-messages-received` | uint64 | Counts the number of key_control messages received. |
| `sleep-allow-messages-received` | uint64 | Counts the number of sleep_allow messages received. |
| `baseline-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the baseline message format. |
| `extended-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the extended message format. |
| `assign-onu-id-omci-messages-received` | uint64 | Counts the number of assign_ONU-ID messages received since the last reboot. |
| `omci-mic-error-count` | uint64 | Counts the number of MIC errors detected in OMCI messages directed to this ONU. |

### `PON_ONU_STATISTICS_ACCUMULATING_ONU_XG_PON_UPSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with upstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `upstream-ploam-message-count` | uint64 | Counts PLOAM messages transmitted upstream, excluding acknowledge messages. |
| `serial-number-message-count` | uint64 | Counts Serial_number_ONU PLOAM messages transmitted. |
| `registration-message-count` | uint64 | Counts registration PLOAM messages transmitted. |
| `key-report-message-count` | uint64 | Counts key_report PLOAM messages transmitted. |
| `acknowledge-message-count` | uint64 | Counts acknowledge PLOAM messages transmitted. It includes all forms of acknowledgement, including those transmitted in response to a PLOAMu grant when the ONU has nothing to send. |
| `sleep-request-message-count` | uint64 | Counts sleep_request PLOAM messages transmitted. |

### `PON_ONU_STATISTICS_BINNED`

- **Key:** `onu-name`, `onu-stats-id`
- **Description:** Realtime statistics for the ONU. These are the values of the statistics after a gather to the statistic file. The ONU statistics vary based on ONU configuration.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `olt-pon-rx-optical-level` | decimal64 (frac-digits 3; units dBm) | Receive optical level. |
| `olt-pon-tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit optical level. |
| `olt-pon-rx-deregistrations` | uint64 | Number of times the ONU has deregistered. |
| `olt-pon-rx-registrations` | uint64 | Number of times the ONU has completed registration. |
| `olt-pon-fiber-distance` | decimal64 (frac-digits 3; units kilometers) | Reports the ONU fiber distance in kilometers. |
| `olt-pon-equalization-delay` | uint64 (units upstream-slots(12.8ns)) | XGS-PON ONLY: Equalization delay assigned by the OLT to an ONU to ensure that the ONU's transmissions are aligned on a common upstream time reference. |
| `olt-pon-round-trip-time` | uint64 (units TQ(16ns)) | EPON ONLY: Calculated Route Trip Time (RTT) between the OLT and ONU. |
| `olt-pon-one-way-delay` | uint64 (units microseconds) | One way delay reported for an ONU. |
| `olt-pon-rx-acc-fec-bytes` | uint64 | Receive Accumulated FEC Bytes. |
| `olt-pon-rx-acc-fec-correct-bytes` | uint64 | Receive Accumulated FEC Corrected Bytes. |
| `olt-pon-rx-acc-fec-error-bytes` | uint64 | Receive Accumulated FEC Errored Bytes. |
| `olt-pon-rx-pre-fec-ber` | string | Receive Pre-FEC Bit Error Rate represented in scientific notation. |
| `olt-pon-rx-post-fec-ber` | string | Receive Post-FEC Bit Error Rate represented in scientific notation. |
| `onu-stats-id` *(key)* | date-and-time | Timestamp identifying the statistics collection period. |
| `timestamp` | date-and-time | Timestamp when the statistics were collected. |

### `PON_ONU_STATISTICS_BINNED_OLT_PON`

- **Key:** `onu-name`, `onu-stats-id`
- **Description:** PON statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `rx-optical-level` | decimal64 (frac-digits 3; units dBm) | Receive optical level. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit optical level. |
| `rx-deregistrations` | uint64 | Number of times the ONU has deregistered. |
| `rx-registrations` | uint64 | Number of times the ONU has completed registration. |
| `fiber-distance` | decimal64 (frac-digits 3; units kilometers) | Reports the ONU fiber distance in kilometers. |
| `equalization-delay` | uint64 (units upstream-slots(12.8ns)) | XGS-PON ONLY: Equalization delay assigned by the OLT to an ONU to ensure that the ONU's transmissions are aligned on a common upstream time reference. |
| `round-trip-time` | uint64 (units TQ(16ns)) | EPON ONLY: Calculated Route Trip Time (RTT) between the OLT and ONU. |
| `one-way-delay` | uint64 (units microseconds) | One way delay reported for an ONU. |

### `PON_ONU_STATISTICS_BINNED_OLT_PON_OMCC`

- **Key:** `onu-name`, `onu-stats-id`
- **Description:** GPON: OMCI channel statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `bad-key-exchanges` | uint64 | Bad Key Exchanges. |
| `good-key-exchanges` | uint64 | Good Key Exchanges. |
| `omci-oam-requests` | uint64 | OMCI/OAM Requests. |
| `omci-oam-resp-time-avg` | uint64 (units microseconds) | OMCI/OAM Resp Time Avg. |
| `omci-oam-resp-time-max` | uint64 (units microseconds) | OMCI/OAM Resp Time Max. |
| `omci-oam-resp-time-min` | uint64 (units microseconds) | OMCI/OAM Resp Time Min. |
| `omci-oam-responses` | uint64 | OMCI/OAM Responses. |
| `omci-oam-time-to-send-avg` | uint64 (units microseconds) | OMCI/OAM Time to Send Avg. |
| `omci-oam-time-to-send-max` | uint64 (units microseconds) | OMCI/OAM Time to Send Max. |
| `omci-oam-time-to-send-min` | uint64 (units microseconds) | OMCI/OAM Time to Send Min. |
| `omci-oam-timeouts` | uint64 | OMCI/OAM Timeouts. |
| `ploam-timeouts` | uint64 | PLOAM Timeouts. |
| `rx-all-bandwidth-reqs` | uint64 | Receive All Bandwidth Reqs. |
| `rx-bad-icv-drops` | uint64 | Receive Bad ICV Drops. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-control-octets` | uint64 | Receive Control Octets. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-key-mismatch-octets` | uint64 | Receive Key Mismatch Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-oam` | uint64 | Receive OAM. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-rate-bps` | uint64 | Receive Rate bps. |
| `rx-security-drop-octets` | uint64 | Receive Security Drop Octets. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-control-octets` | uint64 | Transmit Control Octets. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-grant-ups-tq` | uint64 | Transmit Grant UPS Tq. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-oam` | uint64 | Transmit OAM. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-ploam-ds-ranging-time` | uint64 | Transmit PLOAM DS Ranging Time. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `tx-upstream-slots` | uint64 | Transmit Upstream Slots. |

### `PON_ONU_STATISTICS_BINNED_OLT_PON_SERVICE`

- **Key:** `onu-name`, `onu-stats-id`, `service-port-id`
- **Description:** OLT-Service Port statistics for this ONU as represented on the OLT.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `service-port-id` *(key)* | uint8 | OLT-Service Port number. |
| `bad-key-exchanges` | uint64 | Bad Key Exchanges. |
| `enable-count` | uint64 | Number of times the OLT-Service was activated. |
| `good-key-exchanges` | uint64 | Good Key Exchanges. |
| `omci-oam-requests` | uint64 | OMCI/OAM Requests. |
| `omci-oam-resp-time-avg` | uint64 (units microseconds) | OMCI/OAM Resp Time Avg. |
| `omci-oam-resp-time-max` | uint64 (units microseconds) | OMCI/OAM Resp Time Max. |
| `omci-oam-resp-time-min` | uint64 (units microseconds) | OMCI/OAM Resp Time Min. |
| `omci-oam-responses` | uint64 | OMCI/OAM Responses. |
| `omci-oam-time-to-send-avg` | uint64 (units microseconds) | OMCI/OAM Time to Send Avg. |
| `omci-oam-time-to-send-max` | uint64 (units microseconds) | OMCI/OAM Time to Send Max. |
| `omci-oam-time-to-send-min` | uint64 (units microseconds) | OMCI/OAM Time to Send Min. |
| `omci-oam-timeouts` | uint64 | OMCI/OAM Timeouts. |
| `ploam-timeouts` | uint64 | PLOAM Timeouts. |
| `rx-all-bandwidth-reqs` | uint64 | Receive All Bandwidth Reqs. |
| `rx-bw-best-effort-sla-util` | uint64 | Receive BW Best Effort SLA Util. |
| `rx-bw-best-effort-sla-bps` | uint64 | Receive BW Best Effort SLA bps. |
| `rx-bw-fixed-sla-util` | uint64 | Receive BW Fixed SLA Util. |
| `rx-bw-fixed-sla-bps` | uint64 | Receive BW Fixed SLA bps. |
| `rx-bw-guaranteed-sla-util` | uint64 | Receive BW Guaranteed SLA Util. |
| `rx-bw-guaranteed-sla-bps` | uint64 | Receive BW Guaranteed SLA bps. |
| `rx-bw-total-sla-util` | uint64 | Receive BW Total SLA Util. |
| `rx-bw-total-sla-bps` | uint64 | Receive BW Total SLA bps. |
| `rx-bad-icv-drops` | uint64 | Receive Bad ICV Drops. |
| `rx-bandwidth-reqs` | uint64 | Receive Bandwidth Reqs. |
| `rx-crc32-drops` | uint64 | Receive CRC32 Drops. |
| `rx-crc8-errors` | uint64 | Receive CRC8 Errors. |
| `rx-control-octets` | uint64 | Receive Control Octets. |
| `rx-empty-slots` | uint64 | Receive Empty Slots. |
| `rx-encrypted-frames` | uint64 | Receive Encrypted Frames. |
| `rx-encrypted-octets` | uint64 | Receive Encrypted Octets. |
| `rx-encrypted-segments` | uint64 | Receive Encrypted Segments. |
| `rx-errored-bip-bits` | uint64 | Receive Errored BIP Bits. |
| `rx-errored-bip-blocks` | uint64 | Receive Errored BIP Blocks. |
| `rx-fec-corrected-blocks` | uint64 | Receive FEC Corrected Blocks. |
| `rx-fec-corrections` | uint64 | Receive FEC Corrections. |
| `rx-fec-good-blocks` | uint64 | Receive FEC Good Blocks. |
| `rx-fec-uncorrectable-blocks` | uint64 | Receive FEC Uncorrectable Blocks. |
| `rx-filtered-frames` | uint64 | Receive Filtered Frames. |
| `rx-frames-1024_1518` | uint64 | Receive Frames 1024-1518. |
| `rx-frames-128_255` | uint64 | Receive Frames 128-255. |
| `rx-frames-1519_plus` | uint64 | Receive Frames 1519-Plus. |
| `rx-frames-256_511` | uint64 | Receive Frames 256-511. |
| `rx-frames-512_1023` | uint64 | Receive Frames 512-1023. |
| `rx-frames-64` | uint64 | Receive Frames 64. |
| `rx-frames-65_127` | uint64 | Receive Frames 65-127. |
| `rx-frames-green` | uint64 | Receive Frames Green. |
| `rx-good-bip-blocks` | uint64 | Receive Good BIP Blocks. |
| `rx-hec-errors` | uint64 | Receive HEC Errors. |
| `rx-idle-octets` | uint64 | Receive Idle Octets. |
| `rx-key-mismatch-octets` | uint64 | Receive Key Mismatch Octets. |
| `rx-mpcp-ploam` | uint64 | Receive MPCP/PLOAM. |
| `rx-multi-broadcast-octets` | uint64 | Receive Multi/Broadcast Octets. |
| `rx-overflow-drops` | uint64 | Receive Overflow Drops. |
| `rx-overflow-octets` | uint64 | Receive Overflow Octets. |
| `rx-plain-frames` | uint64 | Receive Plain Frames. |
| `rx-plain-octets` | uint64 | Receive Plain Octets. |
| `rx-plain-segments` | uint64 | Receive Plain Segments. |
| `rx-ploam-mic-errors` | uint64 | Receive PLOAM MIC Errors. |
| `rx-rate-bps` | uint64 | Receive Rate bps. |
| `rx-security-drop-octets` | uint64 | Receive Security Drop Octets. |
| `rx-too-long-drops` | uint64 | Receive Too Long Drops. |
| `rx-too-short-drops` | uint64 | Receive Too Short Drops. |
| `rx-total-octets` | uint64 | Receive Total Octets. |
| `rx-unicast-octets` | uint64 | Receive Unicast Octets. |
| `tx-bw-best-effort-sla-util` | uint64 | Transmit BW Best Effort SLA Util. |
| `tx-bw-best-effort-sla-bps` | uint64 | Transmit BW Best Effort SLA bps. |
| `tx-bw-guaranteed-sla-util` | uint64 | Transmit BW Guaranteed SLA Util. |
| `tx-bw-guaranteed-sla-bps` | uint64 | Transmit BW Guaranteed SLA bps. |
| `tx-bw-total-sla-util` | uint64 | Transmit BW Total SLA Util. |
| `tx-bw-total-sla-bps` | uint64 | Transmit BW Total SLA bps. |
| `tx-bandwidth-reqs` | uint64 | Transmit Bandwidth Reqs. |
| `tx-control-octets` | uint64 | Transmit Control Octets. |
| `tx-encrypted-frames` | uint64 | Transmit Encrypted Frames. |
| `tx-encrypted-octets` | uint64 | Transmit Encrypted Octets. |
| `tx-encrypted-segments` | uint64 | Transmit Encrypted Segments. |
| `tx-frames-1024_1518` | uint64 | Transmit Frames 1024-1518. |
| `tx-frames-128_255` | uint64 | Transmit Frames 128-255. |
| `tx-frames-1519_plus` | uint64 | Transmit Frames 1519-Plus. |
| `tx-frames-256_511` | uint64 | Transmit Frames 256-511. |
| `tx-frames-512_1023` | uint64 | Transmit Frames 512-1023. |
| `tx-frames-64` | uint64 | Transmit Frames 64. |
| `tx-frames-65_127` | uint64 | Transmit Frames 65-127. |
| `tx-frames-broadcast` | uint64 | Transmit Frames Broadcast. |
| `tx-frames-green` | uint64 | Transmit Frames Green. |
| `tx-frames-multicast` | uint64 | Transmit Frames Multicast. |
| `tx-frames-unicast` | uint64 | Transmit Frames Unicast. |
| `tx-mpcp-ploam` | uint64 | Transmit MPCP/PLOAM. |
| `tx-multi-broadcast-octets` | uint64 | Transmit Multi/Broadcast Octets. |
| `tx-plain-frames` | uint64 | Transmit Plain Frames. |
| `tx-plain-octets` | uint64 | Transmit Plain Octets. |
| `tx-plain-segments` | uint64 | Transmit Plain Segments. |
| `tx-ploam-ds-ranging-time` | uint64 | Transmit PLOAM DS Ranging Time. |
| `tx-rate-bps` | uint64 | Transmit Rate bps. |
| `tx-total-octets` | uint64 | Transmit Total Octets. |
| `tx-unicast-octets` | uint64 | Transmit Unicast Octets. |
| `tx-upstream-slots` | uint64 | Transmit Upstream Slots. |

### `PON_ONU_STATISTICS_BINNED_ONU_ENHANCED_TC_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Enhanced TC statistics reported by ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | ME Identifier for this TC. |
| `lods-event-count` | uint64 | Counts the number of state transitions from O5.1 to O6. |
| `lods-event-restored-count` | uint64 | Counts the number of LODS cleared events. |
| `fragment-xgem-frames` | uint64 | Counts the number of XGEM frames that represent fragmented SDUs, as indicated by the LF bit = 0. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `onu-reactivation-by-lods-events` | uint64 | Counts the number of LODS events resulting in ONU reactivation without synchronization being reacquired. |
| `psbd-hec-error-count` | uint64 | Counts HEC errors in any of the fields of the downstream physical sync block. |
| `received-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of received bytes in non-idle XGEM frames. |
| `transmitted-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of transmitted bytes in non-idle XGEM frames. |
| `transmitted-xgem-frames` | uint64 | Counts the number of non-idle XGEM frames transmitted. If an SDU is fragmented, each fragment is an XGEM frame and is counted as such. |
| `unknown-profile-count` | uint64 | Counts the number of grants received whose specified profile was not known to the ONU. |
| `xgem-hec-lost-words-count` | uint64 | Counts the number of 4 byte words lost because of an XGEM frame HEC error. In general, all XGTC payload following the error is lost, until the next PSBd event. |
| `xgem-key-errors` | uint64 | Counts the number of downstream XGEM frames received with an invalid key specification. |
| `xgem-hec-error-count` | uint64 | Counts the number of instances of an XGEM frame HEC error. |
| `xgtc-hec-error-count` | uint64 | Counts HEC errors detected in the XGTC header. |
| `threshold-data-64-bit-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: MAC Bridge Port statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `direction` | enumeration (enum: downstream, upstream) | Direction of the traffic flow for this statistics entry. |
| `broadcast-frames` | uint64 | broadcast frames. |
| `crc-errored-frames` | uint64 | crc errored frames. |
| `drop-events` | uint64 | drop events. |
| `frames` | uint64 | frames. |
| `frames-1024-to-1518-octets` | uint64 | frames 1024 to 1518 octets. |
| `frames-128-to-255-octets` | uint64 | frames 128 to 255 octets. |
| `frames-256-to-511-octets` | uint64 | frames 256 to 511 octets. |
| `frames-512-to-1023-octets` | uint64 | frames 512 to 1023 octets. |
| `frames-64-octets` | uint64 | frames 64 octets. |
| `frames-65-to-127-octets` | uint64 | frames 65 to 127 octets. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-frames` | uint64 | multicast frames. |
| `octets` | uint64 | octets. |
| `oversize-frames` | uint64 | oversize frames. |
| `undersize-frames` | uint64 | undersize frames. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_EXTENDED_PM_64BIT`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: MAC Bridge Port 64-bit statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `direction` | enumeration (enum: downstream, upstream) | Direction of the traffic flow for this statistics entry. |
| `broadcast-frames` | uint64 | broadcast frames. |
| `crc-errored-frames` | uint64 | crc errored frames. |
| `drop-events` | uint64 | drop events. |
| `frames` | uint64 | frames. |
| `frames-1024-to-1518-octets` | uint64 | frames 1024 to 1518 octets. |
| `frames-128-to-255-octets` | uint64 | frames 128 to 255 octets. |
| `frames-256-to-511-octets` | uint64 | frames 256 to 511 octets. |
| `frames-512-to-1023-octets` | uint64 | frames 512 to 1023 octets. |
| `frames-64-octets` | uint64 | frames 64 octets. |
| `frames-65-to-127-octets` | uint64 | frames 65 to 127 octets. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-frames` | uint64 | multicast frames. |
| `octets` | uint64 | octets. |
| `oversize-frames` | uint64 | oversize frames. |
| `undersize-frames` | uint64 | undersize frames. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_FRAME_PM_UPSTREAM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Ethernet UNI port statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `alignment-error-counter` | uint64 | alignment error counter. |
| `buffer-overflows-on-receive` | uint64 | buffer overflows on receive. |
| `buffer-overflows-on-transmit` | uint64 | buffer overflows on transmit. |
| `carrier-sense-error-counter` | uint64 | carrier sense error counter. |
| `deferred-transmission-counter` | uint64 | deferred transmission counter. |
| `excessive-collision-counter` | uint64 | excessive collision counter. |
| `fcs-errors` | uint64 | fcs errors. |
| `frames-too-long` | uint64 | frames too long. |
| `internal-mac-receive-error-counter` | uint64 | internal mac receive error counter. |
| `internal-mac-transmit-error-counter` | uint64 | internal mac transmit error counter. |
| `interval-end-time` | uint64 | interval end time. |
| `late-collision-counter` | uint64 | late collision counter. |
| `multiple-collisions-frame-counter` | uint64 | multiple collisions frame counter. |
| `single-collision-frame-counter` | uint64 | single collision frame counter. |
| `sqe-counter` | uint64 | sqe counter. |
| `threshold-data-half-id` | uint64 | threshold data half id. |

### `PON_ONU_STATISTICS_BINNED_ONU_ETHERNET_PM3`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with ethernet messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | Total number of received good packets directed to the broadcast address. This does not include multicast packets. |
| `drop-events` | uint64 | Total number of events in which packets were dropped due to a lack of resources. |
| `fragments` | uint64 | Total number of packets received that were less than 64 octets long. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `jabbers` | uint64 | Total number of packets received that were longer than 1518 octets. |
| `multicast-packets` | uint64 | Total number of received good packets directed to a multicast address. This does not include broadcast packets. |
| `octets` | uint64 | Total number of octets received from the CPE, including those in bad packets. |
| `packets` | uint64 | Total number of packets received, including bad packets, broadcast packets and multicast packets. |
| `packets-64-octets` | uint64 | Total number of received packets (including bad packets) that were 64 octets long. |
| `packets-65-to-127-octets` | uint64 | Total number of received packets (including bad packets) that were 65 to 127 octets long. |
| `packets-128-to-255-octets` | uint64 | Total number of received packets (including bad packets) that were 128 to 255 octets long. |
| `packets-256-to-511-octets` | uint64 | Total number of received packets (including bad packets) that were 256 to 511 octets long. |
| `packets-512-to-1023-octets` | uint64 | Total number of received packets (including bad packets) that were 512 to 1023 octets long. |
| `packets-1024-to-1518-octets` | uint64 | Total number of received packets (including bad packets) that were 1024 to 1518 octets long. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `undersize-packets` | uint64 | Counts the number of frames discarded due to PPPoE filtering. |

### `PON_ONU_STATISTICS_BINNED_ONU_FEC_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: FEC statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `corrected-bytes` | uint64 | corrected bytes. |
| `corrected-code-words` | uint64 | corrected code words. |
| `fec-seconds` | uint64 | fec seconds. |
| `interval-end-time` | uint64 | interval end time. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `total-code-words` | uint64 | total code words. |
| `uncorrectable-code-words` | uint64 | uncorrectable code words. |

### `PON_ONU_STATISTICS_BINNED_ONU_GAL_ETHERNET_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with gal ethernet messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `discarded-downstream-frames` | uint64 | Counts the number of downstream GEM frames discarded for any reason. |
| `discarded-upstream-frames` | uint64 | Counts the number of upstream frames discarded prior to GEM encapsulation (due to congestion). |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_GEM_PORT_NETWORK_CTP_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with gem port network ctp messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `encryption-key-errors` | uint64 | Counts GEM frames with erroneous encryption key indexes. If the GEM port is not encrypted, this attribute counts any frame with a key index not equal to 0. If the GEM port is encrypted, this attribute counts any frame whose key index specifies a key that is not known to the ONU. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `received-gem-frames` | uint64 | Counts GEM frames received correctly on the monitored GEM port. A correctly received GEM frame is one that does not contain uncorrectable errors and has a valid header error check (HEC). |
| `received-payload-bytes` | uint64 | Counts user payload bytes received on the monitored GEM port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `transmitted-gem-frames` | uint64 | Counts GEM frames transmitted on the monitored GEM port. |
| `transmitted-payload-bytes` | uint64 | Counts user payload bytes transmitted on the monitored GEM port. |

### `PON_ONU_STATISTICS_BINNED_ONU_IP_HOST_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** ME collects PM data related to an IP host.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | ME Identifier for this IP host. |
| `dns-errors` | uint64 | Counts DNS errors received. |
| `dhcp-timeouts` | uint64 | Counts DHCP timeouts received. |
| `icmp-errors` | uint64 | Counts ICMP errors received. |
| `internal-error` | uint64 | Incremented whenever the ONU encounters an internal error condition such as a driver interface failure in the IP stack. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `ip-address-conflict` | uint64 | Incremented whenever the ONU detects a conflicting IP address on the network. A conflicting IP address is one that has the same value as the one curently assigned to the ONU. |
| `out-of-memory` | uint64 | Incremented whenever the ONU encounters an out of memory condition in the IP stack. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_MAC_BRIDGE_PORT_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: ME collects PM data related to a mac bridge port.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | ME Identifier for this mac bridge port. |
| `delay-exceeded-discard-counter` | uint64 | Counts frames discarded on this port because transmission was delayed. |
| `forwarded-frame-counter` | uint64 | Counts frames transmitted successfully on this port. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `mtu-exceeded-discard-counter` | uint64 | Counts frames discarded on this port because the MTU was exceeded. |
| `received-and-discarded-counter` | uint64 | Counts frames received on this port that were discarded due to errors. |
| `received-frame-counter` | uint64 | Counts frames received on this port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_OPERATIONAL_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with operational messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `cpu-percent-utilization` | uint64 | Maximum system CPU utilization (high water mark) during the measurement interval. |
| `errors-in-operations` | uint64 | Count of the number of detected errors in operations, not due to a software error. |
| `flash-size-available` | uint64 | Minimum FLASH size available during the measurement interval. |
| `flash-utilization` | uint64 | Maximum FLASH size utilized during the measurement interval. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `ram-size-available` | uint64 | Minimum RAM size available during the measurement interval. |
| `ram-utilization` | uint64 | Maximum RAM size utilized during the measurement interval. |
| `software-errors` | uint64 | Count of the number of software errors detected. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `temperature-sensor-description` | uint64 | A table of temperature sensor descriptions that includes the physical location on the ONU or the component being measured. |
| `temperature-sensor-value` | uint64 | A table of temperature sensor values that specifies the average temperature of the ONU temperature sensor(s) during the measurement interval. |

### `PON_ONU_STATISTICS_BINNED_ONU_PON`

- **Key:** `onu-name`, `onu-stats-id`
- **Description:** PON statistics reported by ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `rx-optical-level` | decimal64 (frac-digits 3; units dBm) | Receive Optical Level. |
| `tx-optical-level` | decimal64 (frac-digits 3; units dBm) | Transmit Optical Level. |

### `PON_ONU_STATISTICS_BINNED_ONU_RS232_RS485_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** ME collects PM data for a RS232/RS485 interface.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | ME Identifier for this RS232/RS485 interface. |
| `incoming-bytes-from-chip` | uint64 | Counts the bytes received on the RS232/RS485 chipset. |
| `incoming-bytes-from-pon` | uint64 | Counts the bytes received on the PON port. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `outgoing-bytes-from-chip` | uint64 | Counts the bytes transmitted on the RS232/RS485 chipset. |
| `outgoing-bytes-from-pon` | uint64 | Counts the bytes transmitted on the PON port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_TCP_UDP_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** ME collects PM data related to a TCP or UDP port.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | ME Identifier for this TCP or UDP port. |
| `accept-failed` | uint64 | Incremented when an attempt to accept a connection on a port fails. |
| `bind-failed` | uint64 | Incremented when an attempt by a service to bind to a port fails. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `listen-failed` | uint64 | Incremented when an attempt by a service to listen for a request on a port fails. |
| `select-failed` | uint64 | Incremented when an attempt to perform a select on a group of ports fails. |
| `socket-failed` | uint64 | Incremented when an attempt to create a socket associated with a port fails. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_BINNED_ONU_XG_PON_DOWNSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with downstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `ploam-mic-error-count` | uint64 | Counts MIC errors detected in downstream PLOAM messages, either directed to this ONU or broadcast to all ONUs. |
| `downstream-ploam-message-count` | uint64 | Counts PLOAM messages received, either directed to this ONU or broadcast to all ONUs. |
| `profile-messages-received` | uint64 | Counts the number of profile messages received, either directed to this ONU or broadcast to all ONUs. |
| `ranging-time-messages-received` | uint64 | Counts the number of ranging_time messages received, either directed to this ONU or broadcast to all ONUs. |
| `deactivate-onu-id-messages-received` | uint64 | Counts the number of deactivate_ONU-ID messages received, either directed to this ONU or broadcast to all ONUs. |
| `disable-serial-number-messages-received` | uint64 | Counts the number of disable_serial_number messages received, whose serial number specified this ONU. |
| `request-registration-messages-received` | uint64 | Counts the number of request_registration messages received. |
| `assign-alloc-id-messages-received` | uint64 | Counts the number of assign_alloc-ID messages received. |
| `key-control-messages-received` | uint64 | Counts the number of key_control messages received. |
| `sleep-allow-messages-received` | uint64 | Counts the number of sleep_allow messages received. |
| `baseline-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the baseline message format. |
| `extended-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the extended message format. |
| `assign-onu-id-omci-messages-received` | uint64 | Counts the number of assign_ONU-ID messages received since the last reboot. |
| `omci-mic-error-count` | uint64 | Counts the number of MIC errors detected in OMCI messages directed to this ONU. |

### `PON_ONU_STATISTICS_BINNED_ONU_XG_PON_UPSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-stats-id`, `me-id`
- **Description:** GPON: Counters associated with upstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-stats-id` *(key)* | leafref → onu-stats-id | References PON_ONU_STATISTICS_BINNED_LIST. |
| `me-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `upstream-ploam-message-count` | uint64 | Counts PLOAM messages transmitted upstream, excluding acknowledge messages. |
| `serial-number-message-count` | uint64 | Counts Serial_number_ONU PLOAM messages transmitted. |
| `registration-message-count` | uint64 | Counts registration PLOAM messages transmitted. |
| `key-report-message-count` | uint64 | Counts key_report PLOAM messages transmitted. |
| `acknowledge-message-count` | uint64 | Counts acknowledge PLOAM messages transmitted. It includes all forms of acknowledgement, including those transmitted in response to a PLOAMu grant when the ONU has nothing to send. |
| `sleep-request-message-count` | uint64 | Counts sleep_request PLOAM messages transmitted. |

### `PON_ONU_STATISTICS_STREAMING_ONU_ENHANCED_TC_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Enhanced TC statistics reported by ONU.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this TC. |
| `lods-event-count` | uint64 | Counts the number of state transitions from O5.1 to O6. |
| `lods-event-restored-count` | uint64 | Counts the number of LODS cleared events. |
| `fragment-xgem-frames` | uint64 | Counts the number of XGEM frames that represent fragmented SDUs, as indicated by the LF bit = 0. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `onu-reactivation-by-lods-events` | uint64 | Counts the number of LODS events resulting in ONU reactivation without synchronization being reacquired. |
| `psbd-hec-error-count` | uint64 | Counts HEC errors in any of the fields of the downstream physical sync block. |
| `received-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of received bytes in non-idle XGEM frames. |
| `transmitted-bytes-in-nonidle-xgem-frames` | uint64 | Counts the number of transmitted bytes in non-idle XGEM frames. |
| `transmitted-xgem-frames` | uint64 | Counts the number of non-idle XGEM frames transmitted. If an SDU is fragmented, each fragment is an XGEM frame and is counted as such. |
| `unknown-profile-count` | uint64 | Counts the number of grants received whose specified profile was not known to the ONU. |
| `xgem-hec-lost-words-count` | uint64 | Counts the number of 4 byte words lost because of an XGEM frame HEC error. In general, all XGTC payload following the error is lost, until the next PSBd event. |
| `xgem-key-errors` | uint64 | Counts the number of downstream XGEM frames received with an invalid key specification. |
| `xgem-hec-error-count` | uint64 | Counts the number of instances of an XGEM frame HEC error. |
| `xgtc-hec-error-count` | uint64 | Counts HEC errors detected in the XGTC header. |
| `threshold-data-64-bit-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_DOWNSTREAM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Downstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_FRAME_PM_UPSTREAM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Upstream MAC Bridge Service Profile statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `broadcast-packets` | uint64 | broadcast packets. |
| `crc-errored-packets` | uint64 | crc errored packets. |
| `drop-events` | uint64 | drop events. |
| `interval-end-time` | uint64 | interval end time. |
| `multicast-packets` | uint64 | multicast packets. |
| `octets` | uint64 | octets. |
| `oversize-packets` | uint64 | oversize packets. |
| `packets` | uint64 | packets. |
| `packets-1024-to-1518-octets` | uint64 | packets 1024 to 1518 octets. |
| `packets-128-to-255-octets` | uint64 | packets 128 to 255 octets. |
| `packets-256-to-511-octets` | uint64 | packets 256 to 511 octets. |
| `packets-512-to-1023-octets` | uint64 | packets 512 to 1023 octets. |
| `packets-64-octets` | uint64 | packets 64 octets. |
| `packets-65-to-127-octets` | uint64 | packets 65 to 127 octets. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `undersize-packets` | uint64 | undersize packets. |

### `PON_ONU_STATISTICS_STREAMING_ONU_ETHERNET_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Ethernet UNI port statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `alignment-error-counter` | uint64 | alignment error counter. |
| `buffer-overflows-on-receive` | uint64 | buffer overflows on receive. |
| `buffer-overflows-on-transmit` | uint64 | buffer overflows on transmit. |
| `carrier-sense-error-counter` | uint64 | carrier sense error counter. |
| `deferred-transmission-counter` | uint64 | deferred transmission counter. |
| `excessive-collision-counter` | uint64 | excessive collision counter. |
| `fcs-errors` | uint64 | fcs errors. |
| `frames-too-long` | uint64 | frames too long. |
| `internal-mac-receive-error-counter` | uint64 | internal mac receive error counter. |
| `internal-mac-transmit-error-counter` | uint64 | internal mac transmit error counter. |
| `interval-end-time` | uint64 | interval end time. |
| `late-collision-counter` | uint64 | late collision counter. |
| `multiple-collisions-frame-counter` | uint64 | multiple collisions frame counter. |
| `single-collision-frame-counter` | uint64 | single collision frame counter. |
| `sqe-counter` | uint64 | sqe counter. |
| `threshold-data-half-id` | uint64 | threshold data half id. |

### `PON_ONU_STATISTICS_STREAMING_ONU_FEC_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: FEC statistics reported by ONU through OMCI.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `corrected-bytes` | uint64 | corrected bytes. |
| `corrected-code-words` | uint64 | corrected code words. |
| `fec-seconds` | uint64 | fec seconds. |
| `interval-end-time` | uint64 | interval end time. |
| `threshold-data-half-id` | uint64 | threshold data half id. |
| `total-code-words` | uint64 | total code words. |
| `uncorrectable-code-words` | uint64 | uncorrectable code words. |

### `PON_ONU_STATISTICS_STREAMING_ONU_GAL_ETHERNET_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with gal ethernet messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `discarded-downstream-frames` | uint64 | Counts the number of downstream GEM frames discarded for any reason. |
| `discarded-upstream-frames` | uint64 | Counts the number of upstream frames discarded prior to GEM encapsulation (due to congestion). |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_STREAMING_ONU_GEM_PORT_NETWORK_CTP_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with gem port network ctp messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `encryption-key-errors` | uint64 | Counts GEM frames with erroneous encryption key indexes. If the GEM port is not encrypted, this attribute counts any frame with a key index not equal to 0. If the GEM port is encrypted, this attribute counts any frame whose key index specifies a key that is not known to the ONU. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `received-gem-frames` | uint64 | Counts GEM frames received correctly on the monitored GEM port. A correctly received GEM frame is one that does not contain uncorrectable errors and has a valid header error check (HEC). |
| `received-payload-bytes` | uint64 | Counts user payload bytes received on the monitored GEM port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `transmitted-gem-frames` | uint64 | Counts GEM frames transmitted on the monitored GEM port. |
| `transmitted-payload-bytes` | uint64 | Counts user payload bytes transmitted on the monitored GEM port. |

### `PON_ONU_STATISTICS_STREAMING_ONU_RS232_RS485_PERF_MON_HIST_DATA`

- **Key:** `onu-name`, `onu-id`
- **Description:** ME collects PM data for a RS232/RS485 interface.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | ME Identifier for this RS232/RS485 interface. |
| `incoming-bytes-from-chip` | uint64 | Counts the bytes received on the RS232/RS485 chipset. |
| `incoming-bytes-from-pon` | uint64 | Counts the bytes received on the PON port. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `outgoing-bytes-from-chip` | uint64 | Counts the bytes transmitted on the RS232/RS485 chipset. |
| `outgoing-bytes-from-pon` | uint64 | Counts the bytes transmitted on the PON port. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |

### `PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_DOWNSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with downstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `ploam-mic-error-count` | uint64 | Counts MIC errors detected in downstream PLOAM messages, either directed to this ONU or broadcast to all ONUs. |
| `downstream-ploam-message-count` | uint64 | Counts PLOAM messages received, either directed to this ONU or broadcast to all ONUs. |
| `profile-messages-received` | uint64 | Counts the number of profile messages received, either directed to this ONU or broadcast to all ONUs. |
| `ranging-time-messages-received` | uint64 | Counts the number of ranging_time messages received, either directed to this ONU or broadcast to all ONUs. |
| `deactivate-onu-id-messages-received` | uint64 | Counts the number of deactivate_ONU-ID messages received, either directed to this ONU or broadcast to all ONUs. |
| `disable-serial-number-messages-received` | uint64 | Counts the number of disable_serial_number messages received, whose serial number specified this ONU. |
| `request-registration-messages-received` | uint64 | Counts the number of request_registration messages received. |
| `assign-alloc-id-messages-received` | uint64 | Counts the number of assign_alloc-ID messages received. |
| `key-control-messages-received` | uint64 | Counts the number of key_control messages received. |
| `sleep-allow-messages-received` | uint64 | Counts the number of sleep_allow messages received. |
| `baseline-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the baseline message format. |
| `extended-omci-messages-received-count` | uint64 | Counts the number of OMCI messages received in the extended message format. |
| `assign-onu-id-omci-messages-received` | uint64 | Counts the number of assign_ONU-ID messages received since the last reboot. |
| `omci-mic-error-count` | uint64 | Counts the number of MIC errors detected in OMCI messages directed to this ONU. |

### `PON_ONU_STATISTICS_STREAMING_ONU_XG_PON_UPSTREAM_MGMT_PM`

- **Key:** `onu-name`, `onu-id`
- **Description:** GPON: Counters associated with upstream PLOAM and OMCI messages.

| Field | Type | Description |
| --- | --- | --- |
| `onu-name` *(key)* | leafref → onu-name | References PON_ONU_STATE_LIST. |
| `onu-id` *(key)* | uint16 | Performance management ME ID. |
| `interval-end-time` | uint64 | Identifies the most recently finished 15 min interval. |
| `threshold-data-half-id` | uint64 | Points to an instance of the threshold data 1 ME that contains PM threshold values. |
| `upstream-ploam-message-count` | uint64 | Counts PLOAM messages transmitted upstream, excluding acknowledge messages. |
| `serial-number-message-count` | uint64 | Counts Serial_number_ONU PLOAM messages transmitted. |
| `registration-message-count` | uint64 | Counts registration PLOAM messages transmitted. |
| `key-report-message-count` | uint64 | Counts key_report PLOAM messages transmitted. |
| `acknowledge-message-count` | uint64 | Counts acknowledge PLOAM messages transmitted. It includes all forms of acknowledgement, including those transmitted in response to a PLOAMu grant when the ONU has nothing to send. |
| `sleep-request-message-count` | uint64 | Counts sleep_request PLOAM messages transmitted. |

