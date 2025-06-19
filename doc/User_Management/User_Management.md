# Declarative Local User Management

## Revision

| Rev | Date           | Author      | Change Description                                                                                                                                   |
|:---:|:--------------:|:-----------:|:----------------------------------------------------------------------------------------------------------------------------------------------------:|
| 1.0 | June 16, 2025  | Manoharan Sundaramoorthy   | Initial HLD                                                                                                                                          |


## 1. Scope
This document describes the high-level design for a new feature that provides a declarative and persistent method for managing local user accounts on a SONiC device. This feature allows administrators to define local users, including their roles, password hashes, SSH keys, and **security policies** including **login attempt limits**.

This ensures that local user accounts are consistently applied with robust security postures and persist across reboots and upgrades.

## 2. Definitions/Abbreviations

| Abbreviation | Definition                                                                |
|:------------:|:--------------------------------------------------------------------------|
| **`userd`** | The new User Daemon proposed in this design.                              |
| **PAM** | Pluggable Authentication Modules                                          |


## 3. Overview
This feature introduces a new dedicated daemon, **`userd`**, which manages the full lifecycle of local users based on definitions in `CONFIG_DB`. It simplifies management by providing a user-friendly CLI, mapping abstract roles (`administrator`, `operator`) to specific Linux groups, and enforcing security policies. This provides a solution for managing secure, persistent local user accounts.

## 4. Requirements
### 4.1 Functional Requirements
1.  The system must allow an administrator to define a local user account declaratively.
2.  The user definition must support:
    * Username and a pre-hashed password.
    * A role, limited to either **`administrator`** or **`operator`**.
    * Authorized SSH keys (statically defined).
3.  The system will **auto-generate** a unique UID for each new user.
4.  **Default Admin User:**
    * The **`admin`** user (or the user specified during compilation) must be included in the `golden_config_db.json` with default settings.
    * This ensures the admin user is always present in CONFIG_DB by default and can be managed like any other user.
    * The admin user can be modified or disabled through standard CONFIG_DB operations.
5.  **Security Policy Requirements:**
    * **Login Attempts:** The system must support configuring a global maximum number of failed login attempts per role before accounts are temporarily locked.
6.  The system must map roles to underlying Linux groups:
    * `administrator`: members of `sudo`, `docker`, `redis` and `admin` groups.
    * `operator`: members of a standard, non-privileged and would belong to `users` group.
7.  User accounts and their configurations must persist across system reboots and upgrades.
8.  **System Consistency:** On startup, the system must perform a consistency check to ensure Linux users match CONFIG_DB definitions and automatically remove any users that were added directly to Linux (bypassing CONFIG_DB).

## 5. Architecture Design
The architecture centers on the new `userd` daemon. This daemon will now interact with several core Linux subsystems to enforce the configured security policies.

**`userd`'s Points of Interaction:**
1.  **CONFIG_DB:** Single source of truth for user configuration and global security policies.
2.  **Core User Files:** `/etc/passwd`, `/etc/shadow`, `/etc/group` for basic user identity.
3.  **PAM Configuration (`/etc/security/faillock.conf`):** To manage global failed login attempt policies per role via `pam_faillock`.

## 6. High-Level Design

### 6.1 `userd` Daemon
The `userd` daemon's logic will be expanded to manage security configurations idempotently.

**Startup Consistency Check:**
* **System Reconciliation:** On startup, `userd` will perform a consistency check to ensure that all local users in the Linux system (`/etc/passwd`, `/etc/shadow`, `/etc/group`) match the definitions in CONFIG_DB.
* **Cleanup of Unmanaged Users:** Any users found in the Linux system that are not defined in CONFIG_DB (except for system users like `root`, `admin`, `daemon`, etc.) will be automatically removed to maintain consistency.
* **CONFIG_DB as Source of Truth:** This ensures that CONFIG_DB remains the single source of truth for user management and prevents configuration drift.

**Default Admin User:**
* **Golden Config Integration:** The `admin` user (or the user specified during compilation) is included in `golden_config_db.json` with default settings, ensuring it's always present in CONFIG_DB.
* **Standard Management:** The admin user is managed through the same CONFIG_DB interface as other users, with no special exception handling required.
* **Default Configuration:** The admin user in `golden_config_db.json` will have the default password `YourPaSsWoRd` and administrator role.

**User Account Management:**
* **Account Status Control:** `userd` will monitor the `enabled` attribute for each user. When `enabled` is `false`, it will prepend `!` to the password hash in `/etc/shadow` to disable password-based login. When `enabled` is `true`, it will restore the original password hash.
* **Password Hash Preservation:** When disabling a user, `userd` will store the original password hash and restore it when the user is re-enabled, ensuring seamless account management.

**New Logic for Security Policies:**

* **To enforce Login Attempts:**
    * `userd` will manage the PAM configuration file at `/etc/security/faillock.conf`.
    * For global role-based limits (e.g., administrators with limit of 5), it will ensure appropriate configuration in the global section.
    * `userd` will configure PAM to apply different limits based on user group membership (administrator vs operator roles).
    * `userd` will be responsible for ensuring the PAM stack is configured to use `pam_faillock` with role-based policies.

## 7. SAI API
No SAI API changes are required.

## 8. Configuration and Management
### 8.1 Config DB Enhancements
The `USER` table schema is defined for individual user accounts, and a new `USER_SECURITY_POLICY` table is added for global role-based security policies.

**Schema:**
```json
// Example for CONFIG_DB
{
    "USER": {
        "admin": {
            "role": "administrator",
            "password_hash": "$6$salt$hash_of_YourPaSsWoRd",
            "ssh_keys": ["ssh-rsa AAA..."],
            "enabled": true
        },
        "newadmin": {
            "role": "administrator",
            "password_hash": "hashed_password",
            "ssh_keys": ["ssh-rsa BBB..."],
            "enabled": true
        },
        "showuser": {
            "role": "operator",
            "password_hash": "hashed_password",
            "ssh_keys": ["ssh-rsa CCC..."],
            "enabled": false
        }
    },
    "USER_SECURITY_POLICY": {
        "administrator": {
            "max_login_attempts": 5
        },
        "operator": {
            "max_login_attempts": 3
        }
    }
}
```

**USER Table:**
* `role` (string, required): `administrator` or `operator`.
* `password_hash` (string, required): The hashed password.
* `ssh_keys` (optional): List of SSH public keys for the user.
* `enabled` (boolean, optional): Whether the user account is enabled. Defaults to `true` if not specified.

**USER_SECURITY_POLICY Table:**
* **`max_login_attempts`** (integer, optional): Number of failed login attempts before accounts with this role are locked.

**Notes:**
* Session timeouts are managed by the system's default timeout policy and are not configurable per user.
* Password hashes can be generated using `mkpasswd` command-line utility or programmatically using libraries like `passlib` in Python for NETCONF/RESTCONF implementations.
* The CLI provides both `--password-hash` (for pre-hashed passwords) and `--password-prompt` (for interactive secure password entry) options for improved security and usability.
* **CONFIG_DB as Source of Truth:** On startup, `userd` performs a consistency check and removes any users that were added directly to Linux (bypassing CONFIG_DB) to ensure CONFIG_DB remains the authoritative source for user management.
* **User Account Status:** When `enabled` is set to `false`, `userd` will prepend `!` to the password hash in `/etc/shadow` to disable password-based login while preserving SSH key access. When `enabled` is `true` (default), the original password hash is restored.
* **Password Hash Format:** Password hashes in CONFIG_DB cannot start with `!` as this is managed automatically by the `enabled` attribute. Use `enabled: false` instead of manually prepending `!` to disable accounts.
* **Administrator Availability:** At least one administrator user must remain enabled at all times to prevent complete loss of administrative access. This constraint is enforced by the Yang model.
* **Default Admin User:** The `admin` user (or the user specified during compilation) is included in `golden_config_db.json` with default settings, ensuring it's always available and manageable through standard CONFIG_DB operations.

### 8.2 Yang Model Enhancements
```
module sonic-user {
    yang-version 1.1;
    namespace "http://sonicproject.com/sonic-user";
    prefix "sonic-user";

    import sonic-ext {
        prefix "sonic-ext";
    }

    // Common typedef for user roles
    typedef user-role {
        type enumeration {
            enum "administrator" {
                description "Grants administrative privileges (e.g., member of sudo, docker groups).";
            }
            enum "operator" {
                description "Grants operator-level (read-only or limited) privileges.";
            }
        }
        description "User role that determines group memberships, privileges, and applicable security policies.";
    }

    // Top-level container for the User feature
    container sonic-user {
        description "Top-level container for local user management configuration";

        list USER_LIST {
            key "username";
            description "List of declaratively managed local users.";

            must "count(../USER_LIST[role='administrator' and (not(enabled) or enabled='true')]) >= 1" {
                error-message "At least one administrator user must remain enabled.";
            }

            leaf username {
                type string {
                    pattern '[a-z_][a-z0-9_-]*[$]?' {
                        error-message "Invalid username. Must start with a lowercase letter or underscore, followed by lowercase letters, numbers, underscores, or hyphens.";
                    }
                    must ". != 'root'" {
                        error-message "Username cannot be 'root'.";
                    };
                    length 1..32;
                }
                description "The username for the local account.";
            }

            leaf role {
                type user-role;
                mandatory true;
                description "The role assigned to the user, which determines their group memberships and privileges.";
            }

            leaf password_hash {
                type string;
                mandatory true;
                must "not(starts-with(., '!'))" {
                    error-message "Password hash cannot start with '!'. Use the 'enabled' attribute to disable user accounts.";
                }
                description "The hashed password string for the user, as found in /etc/shadow. Password hashes can be generated using 'mkpasswd' utility or programmatically using libraries like 'passlib'. To disable an account, use the 'enabled' attribute instead of prepending '!' to the password hash.";
            }

            leaf-list ssh_keys {
                type string;
                description "A list of full public SSH key strings.";
            }

            leaf enabled {
                type boolean;
                default true;
                description "Whether the user account is enabled. When false, the password is disabled by prepending '!' to prevent password-based login while preserving SSH key access.";
            }
        }

        list USER_SECURITY_POLICY_LIST {
            key "role";
            description "Global security policies applied to users based on their role.";

            leaf role {
                type user-role;
                description "The role for which this security policy applies.";
            }

            leaf max_login_attempts {
                type uint32 {
                    range "1..1000";
                }
                description "Maximum number of failed login attempts before accounts with this role are locked. If not set, system defaults apply.";
            }
        }
    }
}
```

### 8.3 CLI Enhancements
The CLI is enhanced with user management and global security policy commands.

**User Add Command:**
```
config user add <username> --role <role>
                          [--password-hash <hash> | --password-prompt]
                          [--ssh-key <key>]
                          [--disabled]
```
* Multiple `--ssh-key` flags can be provided to build a list.
* Use `--password-hash` to provide a pre-hashed password directly.
* Use `--password-prompt` to enter the password securely through an interactive prompt (password will be hashed automatically).
* Use `--disabled` to create the account in disabled state. Accounts are enabled by default.
* If neither password option is provided, the user account will be created with password login disabled (password set to `!`).

**User Delete Command:**
```
config user del <username>
```

**User Modify Command:**
```
config user modify <username> [--password-hash <hash> | --password-prompt]
                              [--ssh-key <key>]
                              [--enabled | --disabled]
```

* Use `--password-hash` to provide a pre-hashed password directly.
* Use `--password-prompt` to enter the password securely through an interactive prompt (password will be hashed automatically).
* Use `--enabled` or `--disabled` to change the account status.

**Security Policy Commands:**
```
config user security-policy <role> --max-login-attempts <count>
```
* Configure global login attempt limits for a specific role (`administrator` or `operator`).

```
show user security-policy [<role>]
```
* Display current security policies for all roles or a specific role.

**Password Prompt Implementation:**
When `--password-prompt` is used, the CLI will:
1. Display a secure password prompt (e.g., "Enter password for user <username>:")
2. Hide password input (no echo to terminal)
3. Prompt for password confirmation (e.g., "Confirm password:")
4. Validate that both entries match
5. Hash the password using the same algorithm as `mkpasswd` (e.g., SHA-512)
6. Store only the hashed password in CONFIG_DB
7. Clear the plaintext password from memory immediately after hashing

**Other commands (e.g., `show user`) remain as previously defined.**

## 9. Testing Requirements
### New System Test cases
* **Global Login Attempts Policy:**
  * Configure `administrator` role with `max_login_attempts` of 5 and `operator` role with 3.
  * Create users with both roles and verify that login attempt limits are enforced according to their role.
  * Attempt to log in with incorrect passwords and verify accounts are locked based on their role's policy.
  * Verify `faillock --user <username>` shows the correct state for users of different roles.

* **Password Management:**
  * Test user creation with `--password-hash` option and verify the hash is stored correctly.
  * Test user creation with `--password-prompt` option and verify the password is hashed and stored securely.
  * Verify that passwords entered via prompt are not logged in command history.
  * Test password modification using both hash and prompt methods.
  * Attempt to create a user with a password hash starting with `!` and verify it fails with an appropriate error message.

* **Account Status Management:**
  * Create a user with `--disabled` and verify the password hash is prepended with `!` in `/etc/shadow`.
  * Enable a disabled user and verify the original password hash is restored.
  * Test that disabled users cannot login with password but can still use SSH keys.
  * Verify that the `enabled` attribute defaults to `true` when not specified.

* **Administrator Availability Constraint:**
  * Attempt to disable the last remaining enabled administrator user and verify it fails with an appropriate error.
  * Verify that at least one administrator user can always be enabled when multiple administrators exist.
  * Test that the constraint is enforced during user deletion of administrator accounts.

* **Default Admin User:**
  * Verify the `admin` user exists by default in `golden_config_db.json` and is present in CONFIG_DB after system initialization.
  * Verify the `admin` user can be modified, disabled, or deleted through standard CONFIG_DB operations.
  * Test that the `admin` user has the default password `YourPaSsWoRd` and administrator role when first created from golden config.

* **Startup Consistency Check:**
  * Create a user directly in Linux using `useradd` (bypassing CONFIG_DB).
  * Restart the `userd` daemon and verify the manually created user is automatically removed.
  * Verify that users defined in CONFIG_DB are preserved and properly configured.
  * Ensure system users (root, daemon, etc.) are not affected by the cleanup process.

* **User Management:** Create users with different roles and verify all security policies are enforced correctly based on role-based policies.

## 10. Future Enhancements

### 10.1 Remote SSH Key Management
Support for dynamically fetching SSH keys from remote URLs could be added in future versions to enable centralized SSH key management.

## 11. Open/Resolved Issues

None