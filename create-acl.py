#!/usr/bin/python
"""Simple   Base   ACL  CPS   config   using   the   generic   CPS   Python   module   and utilities. 
Create   ACL  Table
Create   ACL  Entry   to   Drop   all   packets   received   on  specific   port   from   specific   Src   MAC 
"""

import   cps_utils
import   nas_os_utils

#  Yang   Enum   name   to   number   map
e_stg   =  {'INGRESS':   1,   'EGRESS':   2}
e_ftype   =  {'SRC_MAC':   3,   'DST_MAC':   4,   'SRC_IP':   5,   'DST_IP':   6, 'IN_PORT':   9,   'DSCP':   21}
e_atype   =  {'PACKET_ACTION':   3,   'SET_TC':   10}
e_ptype   =  {'DROP':   1}


#  Tell   CPS   utility   about   the   type   of   each attribute
type_map   =  {
  'base-acl/entry/SRC_MAC_VALUE/addr':   'mac',
  'base-acl/entry/SRC_MAC_VALUE/mask':   'mac',
}
for   key,val   in   type_map.items():
    cps_utils.cps_attr_types_map.add_type(key,   val)



#  Create   ACL  Table
#
#  Create   CPS   Object   and fill leaf   attributes
cps_obj   =  cps_utils.CPSObject(module='base-acl/table')
cps_obj.add_attr   ('stage',   e_stg['INGRESS'])
cps_obj.add_attr   ('priority',   99)

#  Populate   the   leaf-list   attribute
cps_obj.add_list   ('allowed-match-fields',   [e_ftype['SRC_MAC'], e_ftype['DST_IP'], e_ftype['DSCP'], e_ftype['IN_PORT']])

#  Associate   the   CPS   Object   with   a CPS   operation cps_update   =  ('create',   cps_obj.get())
#  Add   the   CPS   object   to   a new   CPS   Transaction cps_trans   =  cps_utils.CPSTransaction([cps_update])

#  Commit   the   CPS   transaction r =  cps_trans.commit()
if not   r:
    raise   RuntimeError   ("Error   creating   ACL  Table")

ret   =  cps_utils.CPSObject   (module='base-acl/table',   obj=r[0]['change'])
tbl_id   =  ret.get_attr_data   ('id')
print   "Successfully   created   ACL  Table   " +  str(tbl_id) 

