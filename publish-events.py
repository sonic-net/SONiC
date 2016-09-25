import   cps
import   cps_utils


handle   =  cps.event_connect()


obj   =  cps_utils.CPSObject('base-port/interface',qual='observed', data=   {"ifindex":23})

cps.event_send(handle,   obj.get()) 

