# SNMP Migration from snmp.yml to ConfigDB
# High Level Design Document
### Rev 0.1

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Travis Van Duyn    | Initial version                   |
| 0.2 |             | Travis Van Duyn    | Updated to add --json output      |

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

admin@switch1:~$ redis-cli -n 4 hgetall "SNMP|LOCATION"
1) "Location"
2) "Emerald City"

admin@switch1:~$ redis-cli -n 4 hgetall "SNMP|CONTACT"
1) "joe"
2) "joe@contoso.com"
```

# SNMP_COMMUNITY Table
```
SNMP_COMMUNITY|<community>

admin@switch1:~$ redis-cli -n 4 hgetall "SNMP_COMMUNITY|Jack"
1) "TYPE"
2) "RW"

```

# SNMP_USER Table
```
SNMP_USER|<user>

admin@switch1:~$ redis-cli -n 4 hgetall "SNMP_USER|Travis"
 1) "SNMP_USER_TYPE"
 2) "Priv"
 3) "SNMP_USER_PERMISSION"
 4) "RO"
 5) "SNMP_USER_AUTH_TYPE"
 6) "SHA"
 7) "SNMP_USER_AUTH_PASSWORD"
 8) "TravisAuthPass"
 9) "SNMP_USER_ENCRYPTION_TYPE"
10) "AES"
11) "SNMP_USER_ENCRYPTION_PASSWORD"
12) "TravisEncryptPass"
```



# New SNMP CLI Commands
# Show commands
```
admin@switch1:~$ show run snmp -h
admin@str-s6000-acs-11:~$ show run snmp -h
Usage: show run snmp [OPTIONS] COMMAND [ARGS]...

  Show SNMP running configuration

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  community  show SNMP running configuration community
  contact    show SNMP running configuration contact
  location   show SNMP running configuration location
  user       show SNMP running configuration user
admin@switch1:~$
```

show run snmp community
```
admin@switch1:~$ show run snmp community -h
Usage: show run snmp community [OPTIONS]

  show SNMP running configuration community

Options:
  --json          Display the output in JSON format
  -h, -?, --help  Show this message and exit.
admin@switch1:~$

admin@switch1:~$ show run snmp community
Community String    Community Type
------------------  ----------------
Jack                RW
admin@switch1:~$ 
admin@switch1:~$ show run snmp community --json
{'Jack': {'TYPE': 'RW'}}
admin@switch1:~$ 

```

show run snmp contact
```
admin@switch1:~$ show run snmp contact -h
Usage: show run snmp contact [OPTIONS]

  show SNMP running configuration contact

Options:
  --json          Display the output in JSON format
  -?, -h, --help  Show this message and exit.
admin@switch1:~$

admin@switch1:~$ show run snmp contact
Contact    Contact Email
---------  -----------------
Joe        joe@contoso.com
admin@switch1:~$
admin@switch1:~$ show run snmp contact --json
{'joe': 'joe@contoso.com'}
admin@switch1:~$
```

show run snmp location
```
admin@switch1:~$ show run snmp location -h
Usage: show run snmp location [OPTIONS]

  show SNMP running configuration location

Options:
  --json          Display the output in JSON format
  -h, -?, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ show run snmp location
Location
----------
Emerald City
admin@switch1:~$
admin@switch1:~$ show run snmp location --json
{'Location': 'Emerald City'}
admin@switch1:~$ 
```

show run snmp users
```
admin@switch1:~$ show run snmp user -h
Usage: show run snmp user [OPTIONS]

  show SNMP running configuration user

Options:
  --json          Display the output in JSON format
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ show run snmp user
User    Permission Type    Type    Auth Type    Auth Password    Encryption Type    Encryption Password
------  -----------------  ------  -----------  ---------------  -----------------  ---------------------
Travis  RO                 Priv    SHA          TravisAuthPass   AES                TravisEncryptPass
admin@switch1:~$
admin@switch1:~$ show run snmp user --json
{'Travis': {'SNMP_USER_TYPE': 'Priv', 'SNMP_USER_PERMISSION': 'RO', 'SNMP_USER_AUTH_TYPE': 'SHA', 'SNMP_USER_AUTH_PASSWORD': 'TravisAuthPass', 'SNMP_USER_ENCRYPTION_TYPE': 'AES', 'SNMP_USER_ENCRYPTION_PASSWORD': 'TravisEncryptPass'}}
admin@switch1:~$
```


# Config Commands
```
admin@switch1:~$ sudo config snmp -h
Usage: config snmp [OPTIONS] COMMAND [ARGS]...

  SNMP configuration tasks

Options:
  -h, -?, --help  Show this message and exit.

Commands:
  community
  contact
  location
  user
admin@switch1:~$
```

sudo config snmp community
```
admin@switch1:~$ sudo config snmp community -h
Usage: config snmp community [OPTIONS] COMMAND [ARGS]...

Options:
  -h, -?, --help  Show this message and exit.

Commands:
  add      Add snmp community string
  del      Delete snmp community string
  replace  Replace snmp community string
admin@switch1:~$
admin@switch1:~$ sudo config snmp community add -h
Usage: config snmp community add [OPTIONS] <snmp_community> <RO|RW>

  Add snmp community string

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$ 
admin@switch1:~$ sudo config snmp community del -h
Usage: config snmp community del [OPTIONS] <snmp_community>

  Delete snmp community string

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp community replace -h
Usage: config snmp community replace [OPTIONS] <current_community_string>
                                     <new_community_string>

  Replace snmp community string

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
```

sudo config snmp contact
```
admin@switch1:~$ sudo config snmp contact -h
Usage: config snmp contact [OPTIONS] COMMAND [ARGS]...

Options:
  -h, -?, --help  Show this message and exit.

Commands:
  add     Add snmp contact name and email
  del     Delete snmp contact name and email
  modify  Modify snmp contact
admin@switch1:~$
admin@switch1:~$ sudo config snmp contact add -h
Usage: config snmp contact add [OPTIONS] <contact_name> <contact_email>

  Add snmp contact name and email

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp contact del -h
Usage: config snmp contact del [OPTIONS] <contact_name>

  Delete snmp contact name and email

Options:
  -h, -?, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp contact modify -h
Usage: config snmp contact modify [OPTIONS] <contact> <contact email>

  Modify snmp contact

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
```

sudo config snmp location
```
admin@switch1:~$ sudo config snmp location -h
Usage: config snmp location [OPTIONS] COMMAND [ARGS]...

Options:
  -h, -?, --help  Show this message and exit.

Commands:
  add     Add snmp location
  del     Delete snmp location
  modify  Modify snmp location
admin@switch1:~$
admin@switch1:~$ sudo config snmp location add -h
Usage: config snmp location add [OPTIONS] <location>

  Add snmp location

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp location del -h
Usage: config snmp location del [OPTIONS] <location>

  Delete snmp location

Options:
  -h, -?, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp location modify -h
Usage: config snmp location modify [OPTIONS] <location>

  Modify snmp location

Options:
  -h, -?, --help  Show this message and exit.
admin@switch1:~$
```

sudo config snmp user
```
admin@switch1:~$ sudo config snmp user -h
Usage: config snmp user [OPTIONS] COMMAND [ARGS]...

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  add  Add snmp user
  del  Delete snmp user
admin@switch1:~$
admin@switch1:~$ sudo config snmp user add -h
Usage: config snmp user add [OPTIONS] <snmp_user>
                            <noAuthNoPriv|AuthNoPriv|Priv> <RO|RW>
                            <MD5|SHA|HMAC-SHA-2> <auth_password> <DES|AES>
                            <encrypt_password>

  Add snmp user

Options:
  -?, -h, --help  Show this message and exit.
admin@switch1:~$
admin@switch1:~$ sudo config snmp user del -h
Usage: config snmp user del [OPTIONS] <snmp_user>

  Delete snmp user

Options:
  -h, -?, --help  Show this message and exit.
admin@switch1:~$ 
```

# Migration Plan
In order to move from using the snmp.yml file to using the Redis ConfigDB here are the things the need to be done to move this in a way that is backward compatible.
1. Create a python conversion script to parse the data in snmp.yml file and store it in ConfigDB using the above schema.
2. Update Dockerfile.j2 in docker-snmp container to add a line to copy over new python conversion script to "/usr/bin/"
3. Update the snmpd.conf.j2 jinja template to pull SNMP information from only the Redis ConfigDB
4. Update start.sh in docker-snmp container as follows:
    - Add a line above the `sonic-cfggen` call to run the python conversion script from step 1 (which will run every time this docker container starts)
    - Remove the `-y /etc/sonic/snmp.yml` argument from the existing call to sonic-cfggen as it will no longer needed because the python conversion script above will have already loaded that data into Config DB


# Notes:
A new docker-snmp container with all the above updates will be created so that we will eventually be able to remove the snmp.yml file and only use the Redis ConfigDB after we socalize the update.

If we do the migration in this way then when we rollout a new docker-snmp container to the existing devices we will still support the information in the snmp.yml file but we'll also be able to get the information from the Redis ConfigDB for all the new show and config commands.
