import   cps_utils


#Create   the   CPS   Object   and fill the   table-id   and entry-id   key values
cps_obj   =  cps_utils.CPSObject(module='base-acl/entry', data={'table-id':   2, 'id':   1})

#Associate   the   CPS   Object   with   a CPS   operation
cps_update   =  ('delete',   cps_obj.get())

#Add   the   CPS   object   to   a new   CPS   Transaction
cps_trans   =  cps_utils.CPSTransaction([cps_update])

#Commit   the   CPS   transaction
r =  cps_trans.commit()
if not   r:
    raise   RuntimeError   ("Error   deleting   ACL  Entry")
