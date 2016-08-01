import cps_object
import cps
# Create CPS Object
cps_obj = cps_object.CPSObject('dell-base-if-cmn/if/interfaces/interface')

# Populate the attributes for the CPS Object
cps_obj.add_attr("base-if-vlan/if/interfaces/interface/id",100)
cps_obj.add_attr('if/interfaces/interface/type','ianaift:l2vlan')

# Associate a CPS Operation with the CPS Object
cps_update = {'change':cps_obj.get(),'operation': 'create'}

# Add the CPS Operation,Obj pair to a new CPS Transaction
transaction = cps.transaction([cps_update])

# Check for failure
if not transaction: 
    raise RuntimeError ("Error creating Vlan")
print "Successfully created"
