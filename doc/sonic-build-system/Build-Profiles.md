## SONiC Build Profiles

### Revision History

| Rev | Author                 | Change Description          |
|:---:|:----------------------:|-----------------------------|
| 0.1 | Justin Sherman (Cisco) | Initial version             |

### Overview

This adds a build profile feature, which allows developers to easily build SONiC with sets of pre-defined build flags, rather than manually specifiying all flags in the `make` invocation. 

For example:

```
make ENABLE_ZTP=y SECURE_UPGRADE_SIGNING_CERT=/some/cert SECURE_UPGRADE_PROD_SIGNING_TOOL=/some/script.sh SECURE_UPGRADE_MODE=prod USERNAME=ztp PASSWORD=ztp CHANGE_DEFAULT_PASSWORD=y all
```

becomes...

```
make PROFILE=ztp.signed all
```

The build infra will then automatically include the contents of `rules/profiles/ztp.signed.mk`:

```make
ENABLE_ZTP=y
SECURE_UPGRADE_SIGNING_CERT=/some/cert
SECURE_UPGRADE_PROD_SIGNING_TOOL=/some/script.sh
SECURE_UPGRADE_MODE=prod
USERNAME=ztp
PASSWORD=ztp
CHANGE_DEFAULT_PASSWORD=y # Force a password change on first login
```

### Details

The power of this feature comes from having multiple different build profiles present. This enables developers to easily build with multiple different sets of coherent build flags.

Unlike `rules/config.user`, the contents of the `rules/profiles/` directory will be committed, to enable consistent builds across users.
Common default build flags will remain in `rules/config`. Developers can still create the optional, temporary `rules/config.user` file in their workspace, if needed.

Order of precedence will be:

1. `rules/config`
2. `rules/config.user` - only if it exists
3. `rules/profiles/$(PROFILE).mk` - only if `$(PROFILE)` is defined

The changes required to implement this are very simple and completely backwards compatible: if the new `PROFILE` build flag is not provided, build behavior is identical to baseline.

### Questions and Answers

#### Why not just use `rules/config.user` or `rules/config`?

There are two advantages to the build profile approach over the existing files: the profiles are commited, enabling easy, consistent use by the whole team, and multiple profiles can co-exist, enabling easy use of multiple different sets of build flags.

#### Can't this just be handled by CI/CD?

Yes, but that approach only works for CI/CD builds. Builds done outside of CI/CD, like manual development builds, don't get any benefit. By committing the build profiles as includable makefiles, all builds can make use of this feature. Sources shared with customers no longer need to be accompanied by build instruction README files. The build process becomes portable, self-contained, and requires no extra infra besides that required by SONiC build itself.

#### Will this break my existing build/CI flow?

No. This feature is completely backwards compatible. No behavior change occurs unless the feature is explicitly used.

