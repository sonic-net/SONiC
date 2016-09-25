#Python   code block   to   Delete   ip   address
import   cps_utils
#  Populate   the   attributes   for   the   CPS   Object

idx=16
ip_addr="10.0.0.1"
pfix_len=16
ip_attributes   =  {"base-ip/ipv4/ifindex":   idx,"ip":ip_addr,"prefix-length":pfix_len}

#  Create   CPS   Object
cps_utils.add_attr_type('base-ip/ipv4/address/ip',"ipv4")
cps_obj=cps_utils.CPSObject('base-ip/ipv4/address',data=ip_attributes)

#  Create   the   CPS   Transaction   to delete   the   CPS   Object
cps_update   =  ('delete',   cps_obj.get())
transaction   =  cps_utils.CPSTransaction([cps_update])

#  Commit   the   transaction
ret   =  transaction.commit()

#  Check   for   failure
if not   ret:
    raise   RuntimeError   ("Error   ")

