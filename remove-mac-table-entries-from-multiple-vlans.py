import   cps_utils

vlan_list   =[1,2,3,4,5]

obj   =  cps_utils.CPSObject('base-mac/flush')

count   =  0
el   =  ["input/filter","0","vlan"]

for   vlan   in   vlan_list:
    obj.add_embed_attr(el,   vlan)
    count = count + 1

el[1]   =  str(count)

tr_obj   =  ('rpc',   obj.get())
transaction   =  cps_utils.CPSTransaction([tr_obj])
ret   =  transaction.commit()

if not   ret:
    raise   RuntimeError("Error   Flushing   entries   from   MAC   Table")


