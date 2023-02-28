# Egress ACL Bug Fix Description

In current implementation most of the egress ACL flow are covered, but still have two issues related to the egress ACL support as I observed. To have a integrated ACL feature support, suggest to fix them, detailed described as below.


### 1. Remove the restriction of only support L4 port ACL range in ingress table 

In function `AclTable::create()` there is code preventing support of `SAI_ACL_RANGE_TYPE_L4_DST_PORT_RANGE` and `SAI_ACL_RANGE_TYPE_L4_SRC_PORT_RANGE` in egress ACL table:

    if (stage == ACL_STAGE_INGRESS)
    {
        int32_t range_types_list[] = { SAI_ACL_RANGE_TYPE_L4_DST_PORT_RANGE, SAI_ACL_RANGE_TYPE_L4_SRC_PORT_RANGE };
        attr.id = SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE;
        attr.value.s32list.count = (uint32_t)(sizeof(range_types_list) / sizeof(range_types_list[0]));
        attr.value.s32list.list = range_types_list;
        table_attrs.push_back(attr);
    }

This restriction shall be removed so L4 port ACL range can be both supported on both direction. 
 
### 2. Have AclRuleMirror to support both ingress and egress mirror action

#### this part need to be revised due to insufficient design consideration

SAI defined two different action for ingress mirror and egress mirror. 

For ingress mirror it's `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS`, for egress it's `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS`

In current code when create an Acl mirror rule, there is no way to tell it's a ingress rule or egress rule, so only ingress mirror action will be assigned.

To have both mirror action supported, we need to extend AclRuleMirror and the creation flow of it.

 -  Add a new member to AclRuleMirror class to indicate the stage
 
		class AclRuleMirror: public AclRule
		{
			public:	public:
		-       AclRuleMirror(AclOrch *m_pAclOrch, MirrorOrch *m_pMirrorOrch, string rule, string table, acl_table_type_t type);	
		+       AclRuleMirror(AclOrch *m_pAclOrch, acl_stage_type_t stage, MirrorOrch *m_pMirrorOrch, string rule, string table, acl_table_type_t type);
			bool validateAddAction(string attr_name, string attr_value);
			bool validateAddMatch(string attr_name, string attr_value);
			bool validate();
			@@ -263,6 +263,7 @@ class AclRuleMirror: public AclRule
			protected:
			bool m_state;
			string m_sessionName;
		+       acl_stage_type_t m_tableStage;
			AclRuleCounters counters;
			MirrorOrch *m_pMirrorOrch;
		};

 -  Revise the flow of mirror Acl creation to have proper mirror action assigned.
 
		-  m_actions[SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS] = value;
		+  if (m_tableStage == ACL_STAGE_INGRESS)
		+  {   
		+      m_actions[SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS] = value;
		+  }
		+  else if (m_tableStage == ACL_STAGE_EGRESS)
		+  {
		+      m_actions[SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS] = value;
		+  }
		+  else
		+  {
		+      SWSS_LOG_ERROR("Unknown ACL table stage: %d", m_tableStage);
		+      return false;
		+  }
 
- flow chart after add the new flow

   ![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/acl_mirror_rule_flow.svg)

### 3. New SWSS virtual test Added to cover the egress ACL support

 - Dedicated test cases for egress ACL table creation/deletion and various egress ACL rule verification
 - Dedicated test case for egress ACL mirror verification.


 
