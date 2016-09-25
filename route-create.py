#Python   block   to   create   a route

import   cps_utils
import   socket
import   netaddr   as net

#Populate   the   attributes
version   =  'ipv4'
route_ip   =  '70.5.5.0'
obj   =  cps_utils.CPSObject('base-route/obj/entry')
obj.add_attr("vrf-id",   0)
if version   ==   'ipv4':
    obj.add_attr("af",   socket.AF_INET)
elif   version   ==   'ipv6':
    obj.add_attr("af",   socket.AF_INET6)
ip   =  net.IPNetwork(route_ip)
obj.add_attr_type("route-prefix",   version)
obj.add_attr("route-prefix",   str(ip.network))
obj.add_attr("prefix-len",   int(ip.prefixlen))

nh_addr   =  '1.1.1.2' 
lst =  ["nh-list",   "0",   "nh-addr"]
obj.add_embed_attr(lst,   nh_addr)
obj.add_attr("nh-count",   1)

print   obj.get()

# Create transaction
cps_update   =  ('create',   obj.get())
transaction   =  cps_utils.CPSTransaction([cps_update])

# Commit and verify result
ret   =  transaction.commit()
if not   ret:
    raise   RuntimeError   ("Error   creating   Route")


