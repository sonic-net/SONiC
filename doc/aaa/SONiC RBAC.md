# Authentication and Role-Based Access Control
# High Level Design Document
#### Rev 0.1

# Table of Contents
- [Revision History](#revision-history)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [1 Feature Overview](#1-feature-overview)
  * [1.1 Requirements](#11-requirements)
    + [1.1.1 Functional Requirements](#111-functional-requirements)
      - [1.1.1.1 NBI Authentication](#1111-nbi-authentication)
      - [1.1.1.2 CLI Authentication to REST server](#1112-cli-authentication-to-rest-server)
      - [1.1.1.3 REST/gNMI server authentication methods CLIs](#1113-restgnmi-server-authentication-methods-clis)
      - [1.1.1.4 Linux Groups](#1114-linux-groups)
      - [1.1.1.5 Customizable roles](#1115-customizable-roles)
      - [1.1.1.6 Local User Management and UserDB Sync](#1116-local-user-management-and-userdb-sync)
    + [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
    + [1.1.3 Scalability Requirements](#113-scalability-requirements)
      - [1.1.3.1 Translib](#1131-translib)
    + [1.1.4 Warm Boot Requirements](#114-warm-boot-requirements)
  * [1.2 Design Overview](#12-design-overview)
    + [1.2.1 Basic Approach](#121-basic-approach)
    + [1.2.2 Container](#122-container)
    + [1.2.3 SAI Overview](#123-sai-overview)
- [2 Functionality](#2-functionality)
  * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [2.2 Functional Description](#22-functional-description)
- [3 Design](#3-design)
  * [3.1 Overview](#31-overview)
  * [3.2 DB Changes](#32-db-changes)
    + [3.2.1 CONFIG DB](#321-config-db)
    + [3.2.2 APP DB](#322-app-db)
    + [3.2.3 STATE DB](#323-state-db)
    + [3.2.4 ASIC DB](#324-asic-db)
    + [3.2.5 COUNTER DB](#325-counter-db)
  * [3.3 Switch State Service Design](#33-switch-state-service-design)
    + [3.3.1 Orchestration Agent](#331-orchestration-agent)
    + [3.3.2 Other Process](#332-other-process)
  * [3.4 SyncD](#34-syncd)
  * [3.5 SAI](#35-sai)
  * [3.6 User Interface](#36-user-interface)
    + [3.6.1 Data Models](#361-data-models)
    + [3.6.2 CLI](#362-cli)
      - [3.6.2.1 Configuration Commands for User Management](#3621-configuration-commands-for-user-management)
      - [3.6.2.2 Show Commands](#3622-show-commands)
      - [3.6.2.3 Debug Commands](#3623-debug-commands)
      - [3.6.2.4 IS-CLI Compliance](#3624-is-cli-compliance)
    + [3.6.3 REST API Support](#363-rest-api-support)
- [4 Flow Diagrams](#4-flow-diagrams)
- [5 Error Handling](#5-error-handling)
  * [5.1 REST Server](#51-rest-server)
  * [5.2 gNMI server](#52-gnmi-server)
  * [5.3 CLI](#53-cli)
  * [5.4 Translib](#54-translib)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Warm Boot Support](#7-warm-boot-support)
- [8 Scalability](#8-scalability)
- [9 Unit Test](#9-unit-test)

# Revision History
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 04/07/2020  | Nirenjan Krishnan  | Initial version                   |

# About this Manual
This document provides a high-level design approach for authentication and RBAC in the SONiC Management Framework.


# Scope

TBD

# Definitions/Abbreviations

| **Term**                 | **Meaning**                         |
|:--------------------------|:-------------------------------------|
| RBAC                      | Role-Based Access Control                   |
| AAA                       | Authentication, Authorization, Accounting |
| CLI   | Command-Line Interface |
| REST  | REpresentational State Transfer |
| gNMI  | gRPC Network Management Interface |
| NBI    | North-bound Interfaces (CLI, REST, gNMI) |
| HAM   | Host Account Manager |



# 1 Feature Overview

## 1.1 Requirements

- For RBAC, the roles will be defined in the configuration database. Initially,
  two roles will be supported; admin (with read/write privileges), and operator
  (with read-only privileges); however, it shall be possible for the users with
  admin role to define additional roles.
- HAM will become the single source of truth for user management on SONiC
  systems.
- Local user management: CLIs and APIs for creating and managing local users on
  the system -- their usernames, passwords, and roles.
- Authentication control: CLIs and APIs to modify the allowed authentication
  modes on the REST and gNMI interfaces.
- CLI authentication mechanisms to REST server.

### 1.1.1 Functional Requirements

#### 1.1.1.1 NBI Authentication
A variety of authentication methods must be supported:
* **CLI** authentication is handled via user detection on the Unix Socket.
  CLI shall also support communication to the REST server over a TCP connection,
  but this shall use Certificate-based authentication to ensure that the CLI
  user is an authorized user.
* **REST** authentication
  - Password-based Authentication
  - JWT token-based authentication
  - Certificate-based Authentication
* **gNMI** Authentication
  - Password-based Authentication with Token-based authentication
  - Certificate-based Authentication

#### 1.1.1.2 CLI Authentication to REST server
Given that the CLI module works by issuing REST transactions to the Management
Framework's REST server, the CLI module must also be able to authenticate with
the REST server when REST authentication is enabled. This can be accomplished
via the following steps:
1. KLISH must be launched as the corresponding user
    - This is performed by the `-u` argument to `docker exec`
2. REST will listen in on a Unix socket. Listener will detect the user at the
   remote end of the connection, and use that for authentication/authorization.
3. The REST server will authenticate the user and return a token with the
   username and role encoded in it. The KLISH CLI must cache this token and use
   it for all future requests from this KLISH session. The REST server will
   validate this token to username/role mapping with it so as to identify all
   future requests as well. This will also allow the REST server in creating
   audit logs for all the requests sent from KLISH, as well as pass the username
   and role to Translib for RBAC enforcement.
4. KLISH CLI session will store the authentication token, and from then on,
   KLISH CLI will send REST requests using the persistent connection with the
   authentication token in the HTTP header to the REST server for all the CLI
   commands.
5. The KLISH session must be able to cleanly handle ctrl-c breaks while it is
   busy waiting on a response from the REST server.
6. When the user exits the KLISH CLI session, the HTTP persistent connection is
   closed. The REST server will clean up the corresponding authentication token
   for its corresponding KLISH CLI Client.
7. In order to accomodate those CLI actioners that are generated by the Swagger
   code generator, the REST server will also listen on port 8443 with
   certificate based authentication to identify the user.
   - This is necessary since the Swagger code generator does not support
     connections over Unix sockets.


#### 1.1.1.3 REST/gNMI server authentication methods CLIs

The CLI shall provide commands to modify the authentication methods of both the
REST and gNMI interfaces.

#### 1.1.1.4 Linux Groups
Roles will not have a direct map to a primary Linux group, however,
supplementary groups are used to allow access to additional functionalities.
- `admin` users will be added to `sudo` and `docker` groups
- `operator` users will be added to `docker` group only.
- All non-admin users will be added to the `docker` group only.

The default shell for all users is set to a script. This script will determine
if the user is a member of the admin group, and if so, drop them into a Bash
shell, otherwise, it will spawn KLISH to drop them into the CLI. Non-admin users
will only have access to the CLI and not be able to access Bash. Users cannot
run `system` commands from KLISH.

#### 1.1.1.5 Customizable roles

Admin users shall be able to create customizable roles for further granularity beyond read-only and read-write. For instance, a `secadmin` role shall allow the users to configure security parameters on the switch. The custom role shall have a default deny policy. Custom roles shall map a set of features, and their access level to the feature. A feature is a set of YANG paths. The default policy is no access to a feature, if it is not specified in the role.

```
[
  {
    "name": "secadmin",
    "features": [
        {
            "feature": "aaa",
            "access": "rw"
        },
        {
            "feature": "net",
            "access": "ro"
        }
    ]
  }
]
```

Features map to a set of YANG paths. The features are saved in the
ResourceTable, but a default feature set is defined in the system to allow users
to start from a known state. Sample feature description is shown below.

```
[
    {
        "name": "aaa",
        "paths": [
            "openconfig-aaa:aaa/system/users/user={username}",
            "openconfig-aaa:aaa/system/users"
        ]
    },
    {
        "name": "net",
        "paths": [
            "openconfig-net:net/xyz"
        ]
    }
]
```


#### 1.1.1.6 Local User Management and UserDB Sync
An interface must be developed for local user management, so that administrators can add users and assign passwords and roles to them. Administrators with the appropriate role must be able to add/delete users, modify user passwords, and modify user roles. They must be able to do so through all of the NBIs, meaning that a YANG model and CLI tree must be developed.

Users must be added to the Linux database (`/etc/passwd`, `/etc/group`, and optionally `/etc/shadow`). That's where a user is mapped to a Linux [User Identifier](https://en.wikipedia.org/wiki/User_identifier) (UID) and primary [Group Identifier](https://en.wikipedia.org/wiki/Group_identifier) (GID). When users are created they also need to be assigned roles. Roles are simply defined as Linux groups (`/etc/group`) and assigned to users as [Supplementary GIDs](https://en.wikipedia.org/wiki/Group_identifier#Supplementary_groups).

When a user is created it also needs to be assigned certificates that will allow them to communicate with the REST server. Finally, all users need to be added to the REDIS database where additional information about each user can be stored.

Since these operations (i.e. creating Linux users, assigning certificates, etc.) are non-trivial, the process of creating users will be entrusted to the Host Account Management Daemon (**hamd**).

##### 1.1.1.6.1 Host Account Management Daemon (hamd)

The hamd process runs on the host. It is accessed via a DBus interface that provides the ability to access and/or modify the host's Linux database (`/etc/passwd`, `/etc/group`, and optionally `/etc/shadow`). Since DBus is a secured interface we can control which processes will be allowed to access hamd.

The hamd process will provide the following APIs to create/modify/delete user and group (role) accounts:

- **useradd**: To create new users (similar to GNU [useradd](http://man7.org/linux/man-pages/man8/useradd.8.html))
- **userdel**: To delete a user (similar to GNU [userdel](http://man7.org/linux/man-pages/man8/userdel.8.html))
- **passwd**: To change a user password (similar to GNU [passwd](http://man7.org/linux/man-pages/man1/passwd.1.html))
- **setroles**: To set a user's roles (similar to GNU [usermod](http://man7.org/linux/man-pages/man8/usermod.8.html))
- **groupadd**: To create new groups/roles (similar to GNU [groupadd](http://man7.org/linux/man-pages/man8/groupadd.8.html))
- **groupdel**: To delete groups/roles (similar to GNU [groupdel](http://man7.org/linux/man-pages/man8/groupdel.8.html))
- **usermod**: To create or modify users. This method will accept a username,
  hashed password, and a list of strings corresponding to the roles.

The hamd process will add the users to the User Table in the Config DB, however, only the username and roles will be saved in the DB. The password will not be saved due to security considerations.

##### 1.1.1.6.2 Name Service Switch

In addition to providing APIs to create/modify/delete user and group (role) accounts, hamd also provides APIs to simply read user and group (role) accounts. Here's the list:

- **getpwnam**: To retrieve user credentials (similar to POSIX [getpwnam](http://man7.org/linux/man-pages/man3/getpwnam.3.html))
- **getpwuid**: To retrieve user credentials (similar to POSIX [getpwuid](http://man7.org/linux/man-pages/man3/getpwnam.3.html))
- **getgrnam**: To retrieve group/role credentials (similar to POSIX [getgrnam](http://man7.org/linux/man-pages/man3/getgrnam.3.html))
- **getgrgid**: To retrieve group/role credentials (similar to POSIX [getgrgid](http://man7.org/linux/man-pages/man3/getgrnam.3.html))

These APIs, however, are meant to be invoked through [NSS](https://en.wikipedia.org/wiki/Name_Service_Switch) (name service switch).  That is, applications running in containers can simply continue invoking the standard POSIX APIs (`getpwnam()`, `getgrnam()`, etc) and a Host Account Management NSS module will ensure that the credentials get retrieved from hamd running on the host. The HAM NSS module (`libnss_ham.so.2`) need be installed and configured (`/etc/nsswitch.conf`) in the containers that require access to the host's Linux database.

### 1.1.2 Configuration and Management Requirements

Local users are managed via all the NBIs, i.e., CLI, REST and gNMI. The admin
users may also create or modify local users from the Bash shell. All requests
will be proxied to HAM to perform the actual user management.

### 1.1.3 Scalability Requirements

#### 1.1.3.1 Translib
- Translib will cache all the user information along with the privilege and resource information to avoid the overhead of querying them every time we receive a request.
- Will rely on notification to update any change in the user information, privilege or resource information

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach

The Translib code (also in sonic-mgmt-framework) will be modified to support RBAC via Roles, rather than Groups. It will receive username data from the REST/gNMI NBIs and perform the role lookup for a given user.

Translib shall cache the user table and role list to amortize the cost of a
database lookup over several transactions.

### 1.2.2 Container
SONiC Management Framework, gNMI Telemetry containers

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Enterprise networks that enforce authentication for their management interfaces.

## 2.2 Functional Description
This feature enables authentication and Role-Based Access Control (RBAC) on the REST and gNMI programmatic interfaces that are provided by the SONiC Management Framework and Telemetry containers. With respect to authentication, these programmatic interfaces will support password-based authentication with tokens, and certificate-based authentication.

Since the Klish CLI in the management framework communicates with the REST server in the back-end, the solution will also be extended to support REST authentication.

RBAC will be enforced centrally in the management framework, so that users accessing the system through varying interfaces will be limited to the same, consistent set of operations and objects depending on their role. Users' roles will be mapped using Linux Groups.

Users and their role (group) assignments may be managed via the NBIs. HAM shall
provide tools to allow administrators to manage the users and roles from the
shell (Click command? Shell script? TBD)

# 3 Design
## 3.1 Overview
(TODO/DELL: Draw a picture)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
* **UserTable**

  This table contains the username to role mapping needed for enforcing the authorization checks.  It has the following columns :
    * *user* : This is the username being authorized. This is a string.
    * *tenant* : This contains the tenant with which the user is associated. This is a string
    * *role* : This specifies the role associated with the username in the tenant. This is a comma separated list of strings.
      The UserTable is keyed on <***user, tenant***>.

  **Note**: The UserTable will _not_ store users' salted+hashed passwords due to security concerns surrounding access restrictions to the DB; instead, that information will be maintained in `/etc/shadow` as per Linux convention.

* **PrivilegeTable**

  This table provides the information about the type of operations that a particular role is authorized to perform. The authorization can be performed at the granularity of a feature, feature group, or the entire system. The table has the following columns :
    * *role* : The role associated with the user that is being authorized. This is a string.
    * *feature* : This is feature that the role is being authorized to access. The granularity of the feature can be :
        * *feature* - A logical grouping of multiple commands. If the user is authorized to access a particular feature, the column contains the tag associated with that feature.
        * *entire-system* - If the user is being granted access to the entire system, the column contains *all*
    * *permissions* : Defines the permissions associated with the role. This is a string.
        * *none* - This is the default permissions that a role is created with. A role associated with *none* permission cannot access any resources on the system to read, or to modify them.
        * *read-only* - The role only has read access to the resources associated with the *feature*.
        * *read-write* - The role has permissions to read and write (create, modify and delete) the resources associated with the *feature*.
  The PrivilegeTable is keyed on <***role, feature***>

* **ResourceTable**
  Though the resources are statically tagged with the features that they belong to, a ResourceTable is still needed so as to allow for future extensibility. It is possible that in the future, a customer wants a more granular control over the authorization and wants to either sub partition the features or override the default tagging associated with a feature. The ResourceTable will allow for this support in the future. In the Phase 2, this table will be create using the default tagging associated with the resources.
    * *resource* : The xpath associated with the resource being accessed. This is a string.
    * *feature-name* : The tag of the feature this resource belongs to.
  The ResourceTable is keyed on <***resource, feature***>

* **TenantTable**
  (To be implemented in Phase 3 or when Multi-tenancy is introduced)
  In most systems today, a single SONiC system will serve multiple tenants. A tenant is a group of users who have a different privileges for resource instances. As SONiC becomes multitenant, RBAC needs to account for this when authorizing users. The TenantTable is needed to enable this and has the following columns :
    * *resource* : The xpath associated with the resource being accessed. This is a string.
    * *tenant* : The tenant for which the resource partitioning is being done. This is a string.
    * *instances* : The instances of the *resource* allocated to this *tenant*. This is a list of instances.
  The TenantTable is keyed on <***resource, tenant***>

### 3.2.2 APP DB
N/A

### 3.2.3 STATE DB
N/A

### 3.2.4 ASIC DB
N/A

### 3.2.5 COUNTER DB
N/A

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
N/A

### 3.3.2 Other Process
N/A

## 3.4 SyncD

N/A. HAM is going to be the single source of truth, and it will take care of
synchronizing the User Table and /etc/passwd

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models

TBD from developer
(TODO/DELL)

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands for User Management
Users may be managed via Linux tools like `sonic-useradd`, `sonic-usermod`, `passwd`, etc. They may also be managed via configuration.

##### username
`username <name> password <password-string> role <role-string>` -- Configures a user on the system with a given name, password, and role.
* **name** is a text string of 1-32 alphanumeric characters
* **password-string** is a text string of 1-32 alphanumeric characters
* **role-string** is a text string consisting of a role name. In the initial release, the user is recommended to use "admin" and "operator" roles, as other roles will not be supported. A text string is desired instead of keywords so that in the future, more roles may be implemented and expanded.
* Configuring another a user with the same **name** should result in modification of the existing user.

`no username <name>` -- Deletes a user from the system.
* **name** is a text string of 1-32 alphanumeric characters

##### aaa authentication
```
aaa authentication {rest-server | gnmi-server} {[password] [token] [certificate]}
aaa authentication {rest-server | gnmi-server} certificate no-authorization
no aaa authentication {rest-server | gnmi-server}
```

The `certificate no-authorization` mode will force users to authenticate via
certificate, however, there will be no role lookup performed. All authenticated
users will be treated as having full administrator access.

The `no aaa ...` command will disable authentication altogether, and will allow
all users to execute admin level commands via the REST/gNMI interfaces. The CLI
however, will still require a valid password based login, due to it being
accessed via SSH.

##### userrole
`userrole <name>` - Creates a new custom role and enters userrole config to
enable/disable individual features.
`(config-userrole)# feature <feat-name> {read-only | read-write}` - Enable
feature `<feat-name>` with read-only or read-write access.
`(config-userrole)# no feature <feat-name>` - Disable access to feature
`<feat-name>`.

`no userrole <name>` - Deletes a user role from the system.

#### 3.6.2.2 Show Commands

##### show users

`show users`

This will display a list of configured users on the system.

##### show roles

`show roles`

This will display a list of configured roles on the system.
#### 3.6.2.3 Debug Commands
N/A

#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support
Ability to configure local users via REST API.

# 4 Flow Diagrams
N/A

# 5 Error Handling
## 5.1 REST Server
The REST server should return standard HTTP errors when authentication fails or if the user tries to access a forbidden resource or perform an unauthorized activity.

## 5.2 gNMI server
The gNMI server should return standard gRPC errors when authentication fails.

## 5.3 CLI
Authentication errors will be handled by user detection on Unix sockets. However, the CLI must gracefully handle authorization failures from the REST server. While the CLI will render all of the available commands to a user, the user will actually only be able to execute a subset of them. This limitation is a result of the design decision to centralize RBAC in Translib. Nevertheless, the CLI must inform the user when they attempt to execute an unauthorized command.


## 5.4 Translib
Translib will authorize the user and when the authorization fails will return appropriate error string to the REST/gNMI server. Translib will also log an audit message with the username and the command that was attempted.

If a user authenticates but is not part of one of the pre-defined roles, they will not be allowed to do anything at all on the system.

# 6 Serviceability and Debug
All operations performed by NBIs (CLI commands, REST/gNMI operations) should be logged/audited with usernames attached to the given operation(s) performed.

Initially, users who are remotely authenticated will share a common role-specific username, so there will be a limitation here.

# 7 Warm Boot Support
N/A

# 8 Scalability
See previous section 1.1.3: Scalability Requirements

# 9 Unit Test

### Table 3: Test Cases
| **Test Case**                 | **Description**                         |
|:--------------------------|:-------------------------------------|
| REST with password | Authenticate to REST server with username/password and perform some operations |
| REST with token | Perform subsequent operations with token, ensure username/password are not re-prompted |
| REST authorized RBAC | Perform authorized operations as both `Admin` and `Operator` via REST |
| REST unauthorized RBAC | Attempt unauthorized operations as both `Admin` and `Operator` via REST |
| CLI with password | SSH to the system with username/password and execute some commands |
| CLI with RSA | SSH to the system with pubkey and execute some commands |
| CLI authorized RBAC | SSH to the system and perform authorized commands |
| CLI unauthorized RBAC | SSH to the system and perform unauthorized commands |
| RBAC no-group | Create a user and assign them to a non-predefined group; make sure they can't perform any operations |
| gNMI authentication | Test the same authentication methods as REST, but for gNMI instead |
| gNMI authorization | Test the same authorization as REST, but for gNMI instead |
| Create custom role | Create a custom role on the system with individual features |
| Delete custom role | Delete custom role from system |
| REST with custom role authorized | Perform authorized operations with custom role user via REST |
| REST with custom role unauthorized | Perform unauthorized operations with custom role user via REST |
| gNMI with custom role authorized | Perform authorized operations with custom role user via gNMI |
| gNMI with custom role unauthorized | Perform unauthorized operations with custom role user via gNMI |
