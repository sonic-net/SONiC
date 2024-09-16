# Local Login HLD

## Table of contents
- [Local Login HLD](#local-login-hld)
  - [Table of contents](#table-of-contents)
- [Revision](#revision)
- [Scope](#scope)
  - [Abbreviations](#abbreviations)
- [1 Introduction](#1-introduction)
  - [1.1 Feature Overview](#11-feature-overview)
  - [1.2 Requirements](#12-requirements)
- [2 Design](#2-design)
  - [2.1 Overview](#21-overview)
  - [2.2 Sequence Diagrams](#22-sequence-diagrams)
    - [2.2.1 Backend Flow](#221-backend-flow)
    - [2.2.2 CLI Flow](#222-cli-flow)
  - [2.3 Linux Commands](#23-linux-commands)
  - [2.4 Integration With Password Hardening](#24-integration-with-password-hardening)
  - [2.5 Security Concerns](#25-security-concerns)
  - [2.5.1 Config File](#251-config-file)
    - [2.5.2 Show Running Config](#252-show-running-config)
  - [2.6 CLI](#26-cli)
  - [2.7 YANG Model](#27-yang-model)
- [3 Test Plan](#3-test-plan)
  - [3.1 System Testing](#31-system-testing)
    - [Configure User For First Time](#configure-user-for-first-time)
    - [Add New User](#add-new-user)
    - [Delete User](#delete-user)
    - [Upgrade Image](#upgrade-image)
    - [Apply Patch](#apply-patch)
    - [Password Hardening Integration](#password-hardening-integration)
- [4 Disregarded Ideas](#4-disregarded-ideas)
  - [Modify Linux Commands](#modify-linux-commands)

# Revision

| Rev | Date       | Author          | Description     |
|:---:|:----------:|:---------------:|:--------------- |
| 0.1 | 13/09/2024 | Aidan Gallagher | Initial version |

# Scope

The scope of this document is to cover definition, design and implementation of SONiC logal login feature.

## Abbreviations

| Term    | Meaning                                   |
|:------- |:----------------------------------------- |
| SONiC   | Software for Open Networking in the Cloud |
| DB      | Redis Database                            |
| CLI     | Сommand-line Interface                    |
| YANG    | Yet Another Next Generation               |

# 1 Introduction

## 1.1 Feature Overview

Currently local user management for SONiC switches is controlled by linux commands (e.g. `adduser`, `passwd`, etc). These command update the linux files (e.g. `/etc/shadow`, `/etc/passwd`, etc) however they do not store any of this information in `/etc/sonic/config_db.json`.

When a new SONiC image is installed, any Linux configuration which is not also stored in `/etc/sonic/config_db.json` will be removed.
This means after an operator upgrades a SONiC device the login credentials will be reset to the default username and password. The operater will have to reconfigure the login credentials; this additional step is often done manually which increases the chances of misconfiguration and wastes time. 

This feature aims to solve the problem by storing a list of users and encrypted passwords into the redis database. 

## 1.2 Requirements

This feature will support saving a list of users and their encrypted passwords in the configuration file.

This feature will introduce CLI commands to:

* Configure users and their passwords.
* Configure users and use a preprepared encrypted password.
* Delete a user.
* Show the user names of configured users.

The CLI commands will store the state in the redis database. The operator can then run `config save` to write the state to  `/etc/sonic/config_db.json`.

When a SONiC switch is upgraded to a new image the local login credentials stored in the configuration file will be applied.

If no user information is stored in the database then no action will be taken. This ensures this features maintains backwards compatibility. 

# 2 Design

## 2.1 Overview

When an operator uses the CLI to add a user they will be prompted for a password with a masked input field.

The users password will be encrypted before it is pushed to the redis database.

## 2.2 Sequence Diagrams


### 2.2.1 Backend Flow

![Local login backend sequence diagram](images/local-login-backend-sequence.drawio.svg "Figure 1: Local login init sequence diagram")

### 2.2.2 CLI Flow

![Local login config sequence diagram](images/local-login-cli-sequence.drawio.svg "Figure 2: Local login config sequence diagram")


## 2.3 Linux Commands

When the local-login feature is not used the current behaviour of Linux commands such as  `adduser`, `psswd`, etc will not be changed. Changes made using these commands will persist until a new image wipes them.

When the local-login feature is used the configuration database is the single source of truth. This means any changes made using `adduser`, `psswd`, `etc` will be overwritten by the local-login service. The changes will be overwritten on system boot and whenever the local login database changes.


## 2.4 Integration With Password Hardening

The [password hardening feature](../passw_hardening/hld_password_hardening.md) imposes restrictions on what passwords can be used (e.g. min character length, numbers must be used, etc). This will not bypass any constraints impossed by password hardening.

There is no way to check a password meets the hardening constraints without actually attempting to modify the password. In other words there is no `passwd --dry-run` command. This means rather than the CLI script simply encrypting the password and writing the encrypted password to ConfigDB, the CLI will attempt to change the password and if successful it will read the encrypted password from `/etc/shadow` and write that value in the ConfigDB.
> **Note:** Please let me know if this is incorrect and you know of way to do the equivalent of `passwd --dry-run`

>  **Note**: The password hardening feature and this feature are both related to local login. It would make sense to move the password hardening feature under local-login in the CLI and yang. This will break backwards compatibility.

## 2.5 Security Concerns

### 2.5.1 Config File
On Linux systems encrypted passwords for every user are stored in `/etc/shadow`. This file is only readable by sudo users. This feature introduces storing the encrypted passwords in redisDB and `/etc/sonic/config_db.json`.  
RedisDB is only viewable to users in the redis group (1001) - therefore it is secure to store the passwords there.  
`config_db.json` is readable by non-sudo users therefore it reduces the security to store the passwords there. Below are the existing file permissions.

```
admin@sonic:~$ ls -lah /etc/shadow
-rw------- 1 root shadow 731 Sep 16 14:25 /etc/shadow
admin@sonic:~$ ls -lah /etc/sonic/config_db.json 
-rw-r--r-- 1 root root 17K Sep 23 09:07 /etc/sonic/config_db.json
```

This feature will change the config_db.json file permission to
```
-rw--r---- 1 root redis 731 Sep 16 14:25 /etc/sonic/config_db.json
```

### 2.5.2 Show Running Config

The command `show runningconfiguration all` is currently used to show the full configuration. This is no longer viable because it would allow non-sudo users to see the configured encrypted passwords.

This feature will modify `show runningconfiguration all` to remove the encrypted password when it is run without sudo. When it is run with sudo the full configuration will be outputed.


## 2.6 CLI

Add a user or change the password for an existing user
```
$ config local-login setuser <USERNAME>
New password:
Retype new password:
```

Add a user or change the password for an existing user - however this time use a existing pre-encrypted password. Note: The single quotes around the encrypted password are essential.
```
$ config local-login setuser <USERNAME> --encrypted-password '$y$j9T$b11VwUbTIB3mz4vlv/r2j/$BHx0RS4y56H.2ybeiCZTtuwWBsprCD6FOxsc5AoTO3/'
```

Delete an existing user
```
$ config local-login deluser <USERNAME>
```

Show all configured users 
```
$ show local-login
+------------+
| Username   |
+============+
| admin      |
+------------+
| aidan      |
+------------+
```

Show all configured users and their encrypted passwords
```
$ sudo show local-login
+------------+---------------------------------------------------------------------------+
| Username   | Password Hash                                                             |
+============+===========================================================================+
| admin      | $y$j9T$NtunjoczrFjJILXbKVQ/0.$YDM7E6dfbD/OlKUlo4qoRBs2kCd6.OusrkYMQNs38g3 |
+------------+---------------------------------------------------------------------------+
| aidan      | $y$j9T$WHVZxD7z2gvHHLNfFZuXH0$8frMVuUfFH.WXAp0ldKhN/YUPctCgf3aB1UkyfF5/j5 |
+------------+---------------------------------------------------------------------------+
```

>  Alternatively should the local-login CLI and yang live under AAA? something like this `config aaa authentication local setuser <USERNAME>`. If so shouldn't passwd-hardening live there too?

## 2.7 YANG Model

A new YANG model `sonic-local-login.yang` will be added to provide support for configuring local login credentials.

```
module sonic-local-login {

    yang-version 1.1;

    namespace  "http://github.com/sonic-net/sonic-local-login";

    prefix local-login;

    revision 2022-09-23 {
        description "Initial version";
    }

    typedef crypt-password-type {
        type string;
        description
          "A password that is hashed based on the hash algorithm
          indicated by the prefix in the string.  The string
          takes the following form, based on the Unix crypt function:

          $<id>[$<param>=<value>(,<param>=<value>)*][$<salt>[$<hash>]]

          Common hash functions include:

          id  | hash function
           ---+---------------
            1 | MD5
            2a| Blowfish
            2y| Blowfish (correct handling of 8-bit chars)
            5 | SHA-256
            6 | SHA-512

          These may not all be supported by a target device.";
    }

    container sonic-local-login
    {
        container LOCAL_LOGIN 
        {
                list LOCAL_LOGIN_LIST 
                {
                    key username;
                    leaf username 
                    {
                        type string;
                    }
                    leaf password 
                    {
                        type crypt-password-type;
                    }
                }
        } 
    } 
}
```

# 3 Test Plan

## 3.1 System Testing

These test steps are expected to be run in order.

### Configure User For First Time
1. Login as default admin user.
```
sshpass -p YourPaSsWoRd ssh admin@192.168.122.131
```
2. Set admin password to `newpassword`.
```
sudo config local-login setuser admin
```
4. Logout and login to `admin` using `newpassword`.
```
exit
sshpass -p newpassword ssh admin@192.168.122.131
```

### Add New User
  
1. Create new user `testuser` with password `testpassword`.
```
sudo config local-login setuser testuser
```
2. Logout and login to `testuser` using `testpassword`.
```
exit
sshpass -p testpassword ssh testuser@192.168.122.131
```

### Delete User

1. Attempt to delete `fakeuser` who doesn't exist and ensure error is reported.
```
sudo config local-login deluser fakeuser
```
2. Attempt to delete `testuser` and see error saying it's not possible because they are logged in.
```
sudo config local-login deluser testuser
```
3. Logout and login to `admin`.
```
exit
sshpass -p newpassword ssh admin@192.168.122.131
```
4. Delete `testuser`.
```
sudo config local-login deluser testuser
```
5. Ensure `testuser` has been removed.
```
sudo cat /etc/shadow | grep testuser
```

### Upgrade Image

1. Save the existing configuration to `/etc/sonic/config_db.json`.
```
sudo config save
```
2. Copy a new image with the password feature enabled.
```
sshpass -p newpassword sonic-new-img.bin admin@192.168.122.131:~
```
3. Upgrade the image.
```
sudo sonic-installer install ./sonic-new-img.bin
```
4. Login to `admin` using `testpasword`.
```
sshpass -p newpassword ssh admin@192.168.122.131
```

### Apply Patch
1. Create a file with a patch to configure user `admin:password1` and `fred:password2`.
```
$ cat set_fred_and_admin.patch
[
    {
        "op": "add",
        "path": "/LOCAL_LOGIN",
        "value": {
            "admin": {
                "password": "$6$e4AvxMffqgPNuTiC$As6SoXroNQtdG.mfPWCvyrK2rHV.SzKP9B2fxeCEM/It4djpksXP8OUK54fGHGPNzk8qeIlRGP9stuKsqAKOL1"
            },
            "fred": {
                "password": "$6$SEo3n/AJyNyvdjGy$cBtbfcr8j/k8Rqdrj4EkQrtfoYP8W.HQgngd58oNoM9NXGlAzZ4zpJYtc2FFJuO2/X.drZagq.fWHp43FzTTu0"
            }
        }
    }
]
```
2. Apply the patch.
```
sudo config apply-patch set_fred_and_admin.patch
```
3. Login to fred.
```
sshpass -p password2  ssh fred@192.168.122.131
```
4. Create a file with a patch to configure `admin:new_password1`, `bob:new_password2`, and remove fred.
```
$ cat remove_fred_replace_admin_add_bob.patch 
[
    {
        "op": "remove",
        "path": "/LOCAL_LOGIN/fred"
    },
    {
        "op": "replace",
        "path": "/LOCAL_LOGIN/admin/password",
        "value": "$6$mP2hwOINM/PKiqLZ$vgxZKjbNBqV9AanJiVDtqN.M9jjAT8DfQnLDA1.CPRnlr9.tEF6aW3T5SjDhe7Svir9yauoSQM9uhiEmhLehy."
    },
    {
        "op": "add",
        "path": "/LOCAL_LOGIN/bob",
        "value": {
            "password": "$6$eGO95RB0kxNb/jcn$QUzgZVqk3u42IvXHrFeiY7IQD6pBX4c5v7ELvqWzzVtv5jxFjw5Hz.GbOHOsIvJV1qwr6E9vd8Zj3YmSAKcPU."
        }
    }
]
```
5. Apply the patch.
```
sudo config apply-patch remove_fred_replace_admin_add_bob.patch
```
6.  Login to admin.
```
sshpass -p new_password1  ssh admin@192.168.122.131
```

### Password Hardening Integration
1. Configure password hardening.
```
sudo config passw-hardening policies state enabled
```
2. Attempt to set a weak password (`hello`) that doesn't meet the requirements and ensure it fails.
```
sudo config local-login setuser admin
```
3. Configure a strong password (`StrongerPassword1!`) that meets the criteria and ensure it works.
```
sudo config local-login setuser admin
```

# 4 Disregarded Ideas

## 4.1 Modify Linux Commands

A wrapper command could be created around `useradd` and `userdel` and have the same name; the wrapper command would handle updating the database before invoking the underlying command.  
The benefit of this approach is the user doesn't have to learn a new command and the existing Linux approach just works.  
This approach doesn't align with the existing SONiC design of adding adding new commands via sonic-utilities.
