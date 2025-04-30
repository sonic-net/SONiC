# SSH Login HLD

## Table of contents

# Revision

| Rev | Date       | Author          | Description     |
|:---:|:----------:|:---------------:|:--------------- |
| 0.1 | 29/04/2025 | Aidan Gallagher | Initial version |

# Scope

The scope of this document is to cover definition, design and implementation of SONiC SSH feature.

## Abbreviations

| Term    | Meaning                                   |
|:------- |:----------------------------------------- |
| SONiC   | Software for Open Networking in the Cloud |
| DB      | Redis Database                            |
| CLI     | Сommand-line Interface                    |
| YANG    | Yet Another Next Generation               |

# 1 Introduction

## 1.1 Feature Overview

Currently SSH access for SONiC switches is controlled by editing the ssh authorized keys file (usually `~/.ssh/authorized_keys`). This information is not stored in `/etc/sonic/config_db.json`.

When a SONiC device is upgraded any Linux configuration which is not stored in `/etc/sonic/config_db.json` will be removed.
This means after an operator upgrades a SONiC device the ssh login credentials will be lost. The operater will have to reconfigure the login credentials; this additional step is often done manually which increases the chances of misconfiguration and wastes time. 

This feature aims to solve the problem by storing a list of users and their associated ssh public keys in the redis database. 

## 1.2. Existing SSH Config Feature 
A feature already exists for configuring SSH with SONiC (See [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/ssh_config/ssh_config.md)). This feature allows configuring some options in`/etc/ssh/sshd_config` (currently the CLI is limied to `inactivity-timeout` and `max-sessions`).

Configuring SONiC to allow a user to login with their public key will require more than just modifying `/etc/ssh/sshd_config`. A list of public keys (`/etc/ssh/authorized_keys`) will need to be maintained too.

This feature will be implemented similarly to the local login feature.

## 1.3 Requirements

This feature will support saving a list of users and their public keys in the configuration file.

This feature will introduce CLI commands to:

* Configure users and their keys.
* Delete a user's keys.
* Show the configured users and their keys.

The CLI commands will store the state in the redis database. The operator can then run `config save` to write the state to `/etc/sonic/config_db.json`.

All users specified in the authorized_keys will have valid user accounts created using `adduser`.

When a SONiC switch is upgraded to a new image the SSH credentials stored in the configuration file will be applied.

# 2 Design

## 2.1 Overview

**SSHD Config**   
The sshd config will be updated to set the following
```
AuthorizedKeysFile "/etc/ssh/authorized_keys/%u .ssh/authorized_keys
```

**Authorized Keys**  
The daemon will write each users authorized keys to `/etc/ssh/authorized_keys/<username>`, for example bob's keys will be written to `/etc/ssh/authorized_keys/<username>`.


## 2.5 Security Concerns
Typically, each user's authorized SSH keys are stored in their own home directory under ~/.ssh/authorized_keys, with directory permissions such as:
```
drwx------   2 aidan aidan 4.0K Apr 25 14:20 .ssh
```
This restricts access so that only the user (or root) can view their keys. However, in this feature, all users and their public keys will be stored centrally in the SONiC configuration file.

We will not make efforts to restrict non-sudo users from viewing users and their keys because
* There aren't any untrusted users on the switch.
* From a technical stand point the public key is safe to be exposed.


## 2.6 CLI

Add a user or change the password for an existing user
```
$ config ssh login setuser <username> <keyname> <ssh-public-key> 
```

Delete an existing user's key
```
$ config ssh login deluserkey <username> <keyname>
```

Delete all of users key's
```
$ config ssh login deluser <username>
```

Show all configured users and their public keys
```
$ show ssh login
+------------+------------+------------------------------------------------------------------------------------------------+
| Username   | Key Name   | SSH Public Key                                                                                 |
+============+============+================================================================================================+
| admin      | key1       | ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJI/JgSaasddh5C9BrScyeJ9asd9cXWSqj/lwWAAS+QC main@C1D2M111 |
+------------+------------+------------------------------------------------------------------------------------------------+
```

## 2.7 YANG Model
```
module sonic-ssh-login {
    yang-version 1.1;
    namespace "http://github.com/sonic-net/sonic-ssh-login";
    prefix ssh-login;
    revision 2025-05-14 {
        description "Initial version";
    }

    container sonic-ssh-login {
        container SSH_LOGIN {
            list SSH_LOGIN_LIST {
                key "username keyname";

                leaf username {
                    type string;
                    description "The name of the local user";
                }

                leaf keyname {
                    type string;
                    description "A unique name or label for the SSH key (e.g. devmachine)";
                }

                leaf ssh-public-key {
                    type string;
                    description "The public SSH key";
                }
            }
        }
    }
}
```

# 3 Test Plan

## 3.1 System Testing
Todo