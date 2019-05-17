# Egress mirroring support and ACL action capability check

# Table of Contents

#### Revision
| Rev |  Date   |       Author       | Change Description |
|:---:|:-------:|:------------------:|:------------------:|
| 0.1 | 2019-05 |   Blyschak Stepan  | Initial Version    |

## Motivation
Not all ASICs support all actions on ingress, egress stages

E.g.: Egress mirror action on ingress stage or vice versa might be not supported

## Design

## 1. Egress mirroring support

The proposed new schema:

### ACL_RULE_TABLE
```
mirror_action = "ingress"/"egress":1*255VCHAR                 ; refer to the mirror session
```

e.g.:
```
{
  "ACL_RULE": {
        "EVERFLOW|RULE_1": {
            "MIRROR_ACTION": "EGRESS:everflow0",
            "PRIORITY": "9999",
            "SRC_IP": "20.0.0.10/32"
        }
}
```

mirror_action should be implicitly set to "ingress" by default to be backward compatible


### orchagent

- AclRuleMirror adds processing of new schema and convert to SAI_ACL_ACTION_TYPE_MIRROR_INGRESS/EGRESS based on "ingress"/"egress" value;
- By default mirror action is considered "ingress" to be backward compatible;

### acl-loader

- By default acl-loader with ```--session_name``` parameter will produce ingress mirror rule;
- A new parameter ```--mirror_stage=ingress|egress``` will be added;

e.g.:

```
admin@sonic:~$ acl-loader update incremental --session_name=everflow0 --mirror_stage=egress rules.json
```


## 2. ACL action capability check

### orchagent

AclOrch on initialization will query ACL stage capabilities and store them in internal map:

| SAI attribute                                         |  Comment                                        |
|:-----------------------------------------------------:|:-----------------------------------------------:|
|SAI_SWITCH_ATTR_MAX_ACL_ACTION_COUNT                   | max acl action count                            |
|SAI_SWITCH_ATTR_ACL_STAGE_INGRESS                      | list of action types supported on ingress stage |
|SAI_SWITCH_ATTR_ACL_STAGE_EGRESS                       | list of action types supported on egress stage  |


#### aclorch.cpp

```c++
class AclOrch
{
public:
  ...
  // return true if action in attr is supported at stage otherwise return false
  bool isActionSupported(acl_stage_type_t stage, sai_acl_entry_attr_t attr) const;
  ...
private:

   // query SAI_SWITCH_ATTR_ACL_STAGE_INGRESS/SAI_SWITCH_ATTR_STAGE_EGRESS
   // will be called from AclOrch::init();
   void queryAclCapabilities();

   std::map<sai_acl_stage_t, std::set<sai_acl_action_type_t>> m_aclStageCapabilities;
...
};
```

and in AclRule

```c++
class AclRule
{
public:
  ...
  // generic validation of ACL action based on m_aclStageCapabilities
  virtual bool validateAddAction(string attr_name, string attr_value);
  ...
};
```

AclRule derivatives will call base class method ```AclRule::validateAddAction```, e.g. AclRuleMirror:

```c++
AclRuleMirror::validateAddAction(string attr_name, string attr_value)
{
  ... //
  ... // validate

  ... // fill in m_actions map

  return AclRule::validateAddAction(attr_name, attr_value);
}
```

### VS test

Test case 1:

VS test cases update to check for differnt combinations ingress/egress table and ingress/egress mirror rule creation

### system level testing

TBD

### Switch ACL capability table

We will put ACL capabilities in state DB table:

```
SWITCH_CAPABILITY|switch
```

e.g:
```
127.0.0.1:6379[6]> hgetall "SWITCH_CAPABILITY|switch"
1) "ACL_ACTIONS|INGRESS|PACKET_ACTION"
2) "DROP,FORWARD,REDIRECT"
3) "ACL_ACTIONS|INGRESS|MIRROR_ACTION"
4) "INGRESS"
5) "ACL_ACTIONS|EGRESS|PACKET_ACTION"
6) "DROP,FORWARD"
7) "ACL_ACTIONS|EGRESS|MIRROR_ACTION"
8) "EGRESS"
...
```

### libsairedis

Implement SAI_ATTR_VALUE_TYPE_ACL_CAPABILITY deserialization as it is missing
**DONE**

### vslib

Add support for SAI_SWITCH_ATTR_ACL_STAGE_INGRESS, SAI_SWITCH_ATTR_ACL_STAGE_EGRESS to VS.

Two options:
1. Return all actions as supported
2. Return per VS simulating specific device. Currently there are MLNX and BRCM

Second options is harder to maintain:
1. every SAI (mlnx/brcm) update will require to check if list of supported actions were updated and update a VS library correspondingly and also update VS test.
2. VS tests need to check which acl test cases to run for which vs simulating device

So, we prefer to go with first option to make all actions returned as supported by VS.

### VS test

Check negative flow in case action is not supported.

For ingress and egress tables:
  - Set custom SAI_SWITCH_ATTR_ACL_STAGE_$STAGE attribute using setReadOnlyAttribute mechanism in VS test infrastructure and restart orchagent to make it reconstruct its capability map;
  - Create ACL rule wich is not supported and verify no entry in ASIC DB;

### system level testing

TBD
