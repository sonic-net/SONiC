# SONiC SNMP TABLE schema proposal #

## Scope of the change ##

Currently SNMP configuration is managed from a mix of yaml files and DB based ACLs, we propose to integrate the SNMP configs into an SNMP table in the DB.  
The following document proposes the database Schema in Json format and the list of required changes to the code.

## Current configurtions for SNMP ##
sonic-buidimage and sonic-snmpagent depend on the following files:
* */etc/sonic/snmp.yaml*
    defines 2 keys:  
  * *snmp_rocommunity:*  
  * *snmp_location:*  
   this file is consumed in the snmp docker container by */usr/share/sonic/templates/snmpd.conf.j2* and */usr/bin/snmpd-config-updater*.  
* */etc/sonic/config_db.json* or */etc/sonic/minigraph.xml* for ACL definitions 'SNMP_ACL'
  this file is consumed by */usr/bin/snmpd-config-updater*, */usr/share/sonic/templates/alias_map.j2*, */usr/share/sonic/templates/sysDescription.j2*.

In the end this is used to produce */etc/snmp/snmpd.conf*.

## Limits and incentives to change ##
* This goes against the principle of having the config DB be the central repository of configuration data.
* Imposes the provisioning of multiple static files.
* the snmpContact is hardcoded in the */usr/share/sonic/templates/snmpd.conf.j2* file.

## Proposal: integrate the SNMP configuration into config DB ##
### Proposed Schema ###

* SNMP Global values
```
{
   "SNMP":{
      "LOCATION":{
         "LOCATION":"<SNMP_LOCATION_STRING>"
      },
      "CONTACT":{
         "<CONTACT_NAME>":"<SNMP_CONTACT_STRING>"
      }
   }
}
```

* SNMP Community values
```
{
   "SNMP_COMMUNITY":{
      "<SNMP_COMM>":{
         "TYPE":"RO|RW"
      },
      "<SNMP_COMM>":{
         "TYPE":"RO|RW"
      },
      "<SNMP_COMM>":{
         "TYPE":"RO|RW"
      }
   }
}
```

* SNMP User values 
```
{
   "SNMP_USER":{
      "<SNMP_USER>":{
         "SNMP_USER_TYPE":"noAuthNoPriv|AuthNoPriv|Priv",
         "SNMP_USER_AUTH_TYPE":"MD5|SHA|HMAC-SHA-2",
         "SNMP_USER_ENCRYPTION_TYPE":"DES|AES",
         "SNMP_USER_AUTH_PASSWORD":"<AUTH_PASSWORD_STRING>",
         "SNMP_USER_ENCRYPTION_PASSWORD":"<ENCRYPTION_PASSWORD_STRING>",
         "SNMP_USER_PERMISSION": "RO|RW"
      },
      "<SNMP_USER>":{
         "SNMP_USER_TYPE":"noAuthNoPriv|AuthNoPriv|Priv",
         "SNMP_USER_AUTH_TYPE":"MD5|SHA|HMAC-SHA-2",
         "SNMP_USER_ENCRYPTION_TYPE":"DES|AES",
         "SNMP_USER_AUTH_PASSWORD":"<AUTH_PASSWORD_STRING>",
         "SNMP_USER_ENCRYPTION_PASSWORD":"<ENCRYPTION_PASSWORD_STRING>",
         "SNMP_USER_PERMISSION": "RO|RW"
      },
      "<SNMP_USER>":{
         "SNMP_USER_TYPE":"noAuthNoPriv|AuthNoPriv|Priv",
         "SNMP_USER_AUTH_TYPE":"MD5|SHA|HMAC-SHA-2",
         "SNMP_USER_ENCRYPTION_TYPE":"DES|AES",
         "SNMP_USER_AUTH_PASSWORD":"<AUTH_PASSWORD_STRING>",
         "SNMP_USER_ENCRYPTION_PASSWORD":"<ENCRYPTION_PASSWORD_STRING>",
         "SNMP_USER_PERMISSION": "RO|RW"
      }
   }
}
```

Where:
- LOCATION_STRING:  String, defines the snmpLocation, default: "".  
- CONTACT_STRING:   String, defines the snmpContact, default: "" or the current hardcoded value for backwards compatibility.  
- COMMUNITY_STRING: String, defines the community string.
- TYPE: String, defines the community string permissions of either read-only RO or read-write RW.
- SNMP_USER: String, defines the SNMP user.
- SNMP_USER_TYPE: String, defines which authentication and encryption methods will be used for that SNMP user.  The options are noAuthNoPriv or AuthNoPriv or Priv.
- SNMP_USER_AUTH_TYPE: String, defines which authentication type will be used for that SNMP user MD5 or SHA or MHAC-SHA-2.
- SNMP_USER_ENCRYPTION_TYPE: String, defines which encryption type will be used for that SNMP user DES or AES. 
- SNMP_USER_AUTH_PASSWORD: String, defines which authentication password will be used for that SNMP user.
- SNMP_USER_ENCRYPTION_PASSWORD: String, defines which encryption password will be used for that SNMP user. 
- SNMP_USER_PERMISSION: String, RO (Read-Only) or RW (Read-Write) defines what will be used for that SNMP user.


New keys:
* "TYPE":  Optional, if ommited defaults to 'RO', there are 2 possible values:  
  * "RO": read-only, the only implemented method at this time.  
  * "RW": well you never know - here for completeness but unused in the code.  

### Files needing modification for implementation ###

The changes we propose are only additive to remain compatible with the current install base and the current way of doing things.

In repo *sonic-buildimage*:

* *dockers/docker-snmp-v2/snmpd.conf.j2*:  
  * verify the existence of the SNMP table in the datatbase and fork behavior if present, if not continue using old method.

* *dockers/docker-snmp-v2/snmpd-config-updater*:  
  * this file will be deprecated soon by caclmgrd so no updates will be done


In repo *sonic-swss-common*: 

* *common/schema.h*:  
  * #define CFG_SNMP_TABLE_NAME           "SNMP"

In repo *sonic-swss*:

* *doc/swss-schema.md*:
  * add the definition of this schema

