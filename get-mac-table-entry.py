import   cps_utils import   cps

cps_utils.add_attr_type("base-mac/query/mac-address",   "mac")


d  =     {"mac-address":   "00:0a:0b:cc:0d:0e","request-type":"2"}
obj   =  cps_utils.CPSObject('base-mac/query', data=   d)

filter_list   =  [] filter_list.append(obj.get()) l =  []

if cps.get(filter_list,l):
    if l:
        for   ret_obj   in   l:
            cps_utils.print_obj(ret_obj) 
    else:
        print   "No   objects   found"         
else:
    print   "No   objects   found" 
    raise   RuntimeError   ("Error   Getting   MAC   Table   Entries")

