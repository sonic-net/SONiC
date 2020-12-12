# SNMP Migration from snmp.yml to ConfigDB 
# High Level Design Document
### Rev 0.1

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Travis Van Duyn    | Initial version                   |

# About this Manual
This document provides general information about the migration of SNMP community information from snmp.yml file to the ConfigDB.
# Scope
Currently we are using the /etc/sonic/snmp.yml file to populate the SNMP communities in the /etc/snmp/snmpd.conf file.
The goal of this update is to move away from the snmp.yml file and move towards the ConfigDB for better supportibility and ease of use.


# Config DB
## SNMP SCHEMA
Some new "SNMP" tables should be added to ConfigDB in order to store SNMP related configuration. 
https://github.com/Azure/SONiC/blob/master/doc/snmp/snmp-schema-addition.md

The new SNMP tables are: 
SNMP
SNMP_COMMUNITY
SNMP_USER


# SNMP Table
```
SNMP|LOCATION
SNMP|CONTACT

admin@str-s6000-acs-11:~$ redis-cli -n 4 hgetall "SNMP|LOCATION"
1) "LOCATION"
2) "Redmond"

admin@str-s6000-acs-11:~$ redis-cli -n 4 hgetall "SNMP|CONTACT"
1) "joe"
2) "joe@microsoft.com"
```

# SNMP_COMMUNITY Table
```
SNMP_COMMUNITY|<community>

admin@str-s6000-acs-11:~$ redis-cli -n 4 hgetall "SNMP_COMMUNITY|Jack"
1) "TYPE"
2) "RW"

```

# SNMP_USER Table 
```
SNMP_USER|<user>

admin@str-s6000-acs-11:~$ redis-cli -n 4 hgetall "SNMP_USER|Travis"
 1) "SNMP_USER_ENCRYPTION_TYPE"
 2) "AES"
 3) "SNMP_USER_AUTH_TYPE"
 4) "SHA"
 5) "SNMP_USER_ENCRYPTION_PASSWORD"
 6) "TravisEncryptPass"
 7) "SNMP_USER_AUTH_PASSWORD"
 8) "TravisAuthPass"
 9) "SNMP_USER_TYPE"
10) "Priv"
11) "SNMP_USER_PERMISSION"
12) "RO"
```



# New SNMP CLI Commands
# Show commands
```
admin@str-s6000-acs-11:~$ show run snmp -h
Usage: show run snmp [OPTIONS] COMMAND [ARGS]...

  Show SNMP information

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  community  show runningconfiguration snmp community
  contact    show runningconfiguration snmp contact
  location   show runningconfiguration snmp location
  users      show runningconfiguration snmp users
admin@str-s6000-acs-11:~$ 
```

show run snmp community
```
admin@str-s6000-acs-11:~$ show run snmp community
Community String    Community Type
------------------  ----------------
Qi                  RO
Travis              RO
Bill                RO
Jack                RW
public              RO
Joker               RW
admin@str-s6000-acs-11:~$ 
```

show run snmp contact
```
admin@str-s6000-acs-11:~$ show run snmp contact
Contact    Contact Email
---------  -----------------
Joe        joe@microsoft.com
admin@str-s6000-acs-11:~$ 
```

show run snmp location
```
admin@str-s6000-acs-11:~$ show run snmp location 
Location
----------
Redmond
admin@str-s6000-acs-11:~$ 
```

show run snmp users
```
admin@str-s6000-acs-11:~$ show run snmp users
User    Type    Auth Type    Auth Password    Encryption Type    Encryption Password
------  ------  -----------  ---------------  -----------------  ---------------------
Travis  Priv    SHA          TravisAuthPass   AES                TravisEncryptPass
admin@str-s6000-acs-11:~$
```


# Config Commands
```
admin@str-s6000-acs-11:~$ sudo config snmp -h
Usage: config snmp [OPTIONS] COMMAND [ARGS]...

  SNMP configuration tasks

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  community
  contact
  location
  user
admin@str-s6000-acs-11:~$ 
```

sudo config snmp community 
```
admin@str-s6000-acs-11:~$ sudo config snmp community -h
Usage: config snmp community [OPTIONS] COMMAND [ARGS]...

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  add  Add snmp community
  del  Add snmp community
admin@str-s6000-acs-11:~$ 
```

sudo config snmp contact  
```
admin@str-s6000-acs-11:~$ sudo config snmp contact -h
Usage: config snmp contact [OPTIONS] COMMAND [ARGS]...

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  modify  Modify snmp contact
admin@str-s6000-acs-11:~$ 
```

sudo config snmp location 
```
admin@str-s6000-acs-11:~$ sudo config snmp location -h
Usage: config snmp location [OPTIONS] COMMAND [ARGS]...

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  modify  Modify snmp location
admin@str-s6000-acs-11:~$ 
```

sudo config snmp user 
```
admin@str-s6000-acs-11:~$ sudo config snmp user -h
Usage: config snmp user [OPTIONS] COMMAND [ARGS]...

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  add  Add snmp user
  del  Add snmp user
admin@str-s6000-acs-11:~$ 
```

# Migration Plan
In order to move from using the snmp.yml file to using the Redis ConfigDB here are the things the need to be done to move this in a way that is backward compatible. 
1. Create a python conversion script to take input from snmp.yml file and convert it to Redis ConfigDB format from above schema.
2. Update Dockerfile.j2 in docker-snmp container to add a line to copy over new python conversion script to "/usr/bin/"
3. Update the snmpd.conf.j2 jinja template to pull SNMP information from only the Redis ConfigDB
4. Update start.sh in docker-snmp container to add a line above sonic-cfggen to run python conversion script (which will run everytime this docker container starts) and then comment out the "-y /etc/sonic/snmp.yml" file as this is not needed since we grabbed the snmp.yml info in the python conversion script and have the information available in the Redis ConfigDB. 
5. Create new docker-snmp container with all these updates so that we will eventually be able to remove the snmp.yml file and only use the Redis ConfigDB after we socalize the update.

If we do the migration in this way then when we rollout a new docker-snmp container to the existing devices we will still support the information in the snmp.yml file but we'll also be able to get the information from the Redis ConfigDB for all the new show and config commands. 

After this update is rolled out to the fleet we will stablize for some time and work with the NDM and HWProxy teams to migration over to using ConfigDB for their configurations. 
