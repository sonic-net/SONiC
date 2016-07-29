import   cps
import   cps_utils

#  Example   GET  request cps_get_response   =  []
cps.get([cps.key_from_name('observed','base-pas/chassis')], cps_get_response) 

chassis_vendor_name   =  cps_attr_get(cps_get_response[0]['data'],'base-pas/chassis/vendor-name')
