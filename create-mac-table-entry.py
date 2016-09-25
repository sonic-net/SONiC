### Configure MAC address table entry
import   cps_utils

cps_utils.add_attr_type("base-mac/table/mac-address",   "mac")

d  =     {"mac-address":   "00:0a:0b:cc:0d:0e", "ifindex":   18, "vlan":   "100"}
obj   =  cps_utils.CPSObject('base-mac/table',data=   d)
tr_obj   =  ('create',   obj.get())

transaction   =  cps_utils.CPSTransaction([tr_obj])
ret   =  transaction.commit()

if not   ret:
    raise   RuntimeError   ("Error   creating   MAC   Table   Entry") 


