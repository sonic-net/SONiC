# Live-Addon Vendor Integration Specification

## 1. Purpose and Scope

This document defines the proposed integration contract for vendors adding
diagnostic functionality to SONiC through live-addon: required inputs, supported
options, payload restrictions, process configuration, health commands, and
release metadata.
These requirements describe the proposed contract, not an implemented upstream
feature. Paths and examples refer to the planned `sonic-buildimage` integration.

The [framework and build design](./design_review.md) explains how SONiC builds,
validates, packages, and runs these inputs. It is not a second definition of the
vendor contract. Release and runtime deployment settings are outside the vendor
profile; [framework section 7.8](./design_review.md#78-kubernetes-deployment-boundary)
defines the image's deployment interface.

The vendor may supply source or prebuilt binary artifacts with declarative
integration inputs; proprietary program source is not required for binary-only
integrations. The vendor does not supply the production Dockerfile or a prebuilt
production image. A vendor may maintain a Dockerfile for its own
development and testing, but the SONiC build does not use it to define the final
image. SONiC owns the base image, installation policy, main Supervisor
configuration, entrypoint, and generic HTTP health server.

## 2. Integration Inputs and Platform Configuration

Each integration is selected by `platform/<platform>.ini` under
`dockers/docker-live-addon`. The profile declares:

| Section | Vendor input |
|---|---|
| `[source]` | A repository-local input path or an external input repository and revision |
| `[vendor-build]` | Working directory and deterministic artifact preparation script (build or copy) |
| `[artifact]` | Bundle format, output glob, approved installation root, and archive options |
| `[supervisor]` | Explicit list of process configuration fragments; may be empty |
| `[addon]` | Optional approved OS packages required by the integration |
| `[manifest]` | Addon release identity and Feature Manager service/container values |
| `[health]` | Startup, liveness, and readiness commands and execution limits |

The selected input directory must contain the declared script, Supervisor
fragments, and either buildable source or a prebuilt artifact bundle, including
the inputs needed to supply the installed health commands.
The vendor does not supply a separate runtime `health.ini`, main
`supervisord.conf`, raw manifest JSON, or container entrypoint.

The following vendor-specific example illustrates the proposed contract; it
does not imply an existing implementation or a dependency of the public build:

```ini
[source]
repo=git@github.com:Cisco-8000-sonic/platform-cisco-8000.git
ref=202411.1.0.15

[vendor-build]
working-directory=docker-cisco-utility
build-script=./build-live-addon-artifact.sh

[artifact]
format=deb
glob=*.deb
install-root=/opt/cisco/live-addon

[supervisor]
conf-files =
    docker-cisco-utility/supervisor/cisco-8000-agent.conf
    docker-cisco-utility/supervisor/cisco-8000-support.conf

[addon]
optional-packages=rsyslog,supervisord-dependent-startup

[manifest]
package-name=live-addon-cisco-8000
package-version=202411.1.0.15
host-service=true
asic-service=false
after=syncd
privileged=true

[health]
startup-command=/opt/cisco/live-addon/bin/check-startup
liveness-command=/opt/cisco/live-addon/bin/check-liveness
readiness-command=/opt/cisco/live-addon/bin/check-readiness
command-timeout-seconds=8
max-output-bytes=4096
```

The privilege and service values above describe this example integration, not
defaults or an automatic grant of runtime privileges.

## 3. Source Selection

`[source]` selects the integration input directory. It may contain source code
or prebuilt binary bundles with their copy script and declarative configuration;
it does not require access to proprietary program source.

Use exactly one of the following forms.

### 3.1 Repository-local source

Open-source integrations may contribute their source directly to
`sonic-buildimage` and select it through `path`. The proposed checked-in sample
uses:

```ini
[source]
path=dockers/docker-live-addon/platform/example
```

`path` is relative to the `sonic-buildimage` repository root and must resolve
inside that repository. No separate Git checkout is performed.

### 3.2 External source

Integrations that keep their inputs in a separate repository, including
proprietary source or prebuilt binary packages, use:

```ini
[source]
repo=git@github.com:Cisco-8000-sonic/platform-cisco-8000.git
ref=202411.1.0.15
```

`ref` is required. Source acquisition resolves and records the concrete commit
before the artifact build. Private-source credentials belong only to source
acquisition; they are not available to the artifact build or included in the
final Docker context.

The two forms are mutually exclusive. Both must satisfy the same artifact,
Supervisor, health, and manifest contract. Repository-local source is not copied
directly into the image.
A prebuilt binary bundle is permitted; a vendor-supplied production Docker image
is not. Optional private integrations must not become prerequisites of the
public example live-addon build.

## 4. Artifact Build Script

Provide one deterministic, non-interactive artifact preparation script through
`build-script`. It may build from supplied source or simply copy the vendor's
prebuilt package or archive into the output directory. A copy-only script does
not require proprietary program source and is not an installation hook.
The framework invokes it from the configured working directory and passes an
absolute output directory:

```text
./build-live-addon-artifact.sh --output /workspace/vendor-artifacts
```

The script must:

- Return non-zero on failure and require no interactive input.
- Produce exactly one declared artifact bundle in the supplied output directory.
- Not build or publish a Docker image or require publishing credentials.
- Not write outside its source and output directories.
- Record sufficient artifact version information for traceability.

`working-directory` is relative to the resolved source root; `build-script`
selects the script invoked from that directory. The working directory and script
must exist. The artifact `glob` is evaluated relative to a newly created output
directory, not the source tree, and must match exactly one file.

The build runs in a SONiC-approved sandbox with read-only source, an empty
writable output directory, and a documented, pinned toolchain. It has no access
to unrelated workspaces or host filesystems, the Docker daemon socket, or
repository, registry, signing, publishing, or deployment credentials. Resource
use and execution time are bounded. The profile cannot select or weaken the
sandbox.

Network access is disabled by default. Any required exception must be documented
and restricted to SONiC-approved, version-pinned sources. Toolchain and
artifact-build dependencies must be documented and pinned as part of the
integration.

## 5. Artifact, Payload, and Dependency Restrictions

### 5.1 Common payload rules

Produce a single bundle in one of these initial formats:

| `format` | Accepted suffixes |
|---|---|
| `deb` | `.deb` |
| `tar` | `.tar`, `.tar.gz`, `.tgz` |
| `zip` | `.zip` |

The declared format must match the detected format. Malformed or unsafe bundles
are rejected.

Every artifact must declare `install-root=/opt/<vendor>/live-addon`, where
`<vendor>` is a single SONiC-approved vendor directory name. This is the only
allowed vendor payload root for every format. Executables, private libraries,
Python modules, configuration files, and documentation must all reside there.
Use explicit paths or process-local lookup settings, not global loader or Python
startup configuration. This restriction does not apply to SONiC-approved OS
dependencies or framework-managed package-manager state.

Payloads must not contain parent traversal, device nodes, set-user-ID or
set-group-ID files, or symbolic or hard links that escape `install-root`.
Installation must not start services, modify the main Supervisor configuration,
overwrite SONiC-owned framework files, fetch additional vendor payloads, or
require credentials.

### 5.2 Restricted Debian profile

The initial contract supports a restricted Debian package, not every feature
accepted by `dpkg`.

The control archive may contain only `control`, `md5sums`, `shlibs`, and
`symbols`. Executable or interactive package hooks, including `preinst`,
`postinst`, `prerm`, `postrm`, and Debconf `config` scripts, are prohibited.
All vendor trigger declarations, including `activate-noawait ldconfig`, are
prohibited.

The allowed control fields are `Package`, `Version`, `Architecture`,
`Maintainer`, `Description`, `Section`, `Priority`, `Homepage`, `Source`,
`Installed-Size`, and `Depends`. Unknown installation-affecting fields are
rejected. In particular, do not declare `Pre-Depends`, `Recommends`, `Suggests`,
`Enhances`, `Breaks`, `Conflicts`, `Replaces`, `Provides`, `Essential`,
`Protected`, or `Multi-Arch`. The package name must not replace an installed
package or use a SONiC-reserved package name. Its architecture must match the
target image or be `all`.

`Depends` entries must name concrete SONiC-approved packages. Alternative or
virtual-package dependencies are not accepted initially. Dependencies must be
available from the approved immutable repository snapshot and are locked to
exact versions and architectures. Installation uses `--no-install-recommends`.
A dependency transaction that removes, downgrades, replaces, or deconfigures an
installed package, or changes a protected SONiC framework package, is rejected.
Declaring a requirement does not authorize an arbitrary package source or
unconstrained dependency resolution.

Every Debian payload destination must already be beneath `install-root`, even
if a destination outside it is unowned. Installing a `.deb` does not relocate
its contents beneath that root. Ancestor directory entries may only represent
the path to `install-root`; they must not modify existing ancestor directories
or their metadata.

Links must not escape `install-root`, including through existing filesystem
links. The package must not replace a non-directory filesystem entry owned by
the approved base image or locked dependency set. Existing directories may be
shared, but the package must not change their type or weaken their permissions.
Private libraries must resolve within the vendor process without changing the
global runtime linker configuration or cache.

### 5.3 TAR and ZIP profiles

Archives must already have their final runtime filesystem layout. Extraction
into `install-root` is the complete installation operation; the framework does
not execute an installer contained in the archive. Absolute member paths are
prohibited, in addition to the common path and file-type restrictions above.

`strip-components` optionally removes leading path components before extraction
and defaults to `0`. For example:

```ini
[artifact]
format=tar
glob=*.tar.gz
install-root=/opt/cisco/live-addon
strip-components=1
```

`install-root` must still be the approved `/opt/<vendor>/live-addon`, not an
arbitrary path beneath `/opt`.

### 5.4 Optional OS packages

Declare optional OS dependencies through `[addon] optional-packages`, as shown
in section 2. They are subject to SONiC's approved package sources, locked
versions, and installation policy; the vendor does not provide package-manager
commands or a Dockerfile to bypass those controls.

## 6. Supervisor Program Fragments

Declare every fragment explicitly through the multiline `conf-files` list:

```ini
[supervisor]
conf-files =
    docker-cisco-utility/supervisor/cisco-8000-agent.conf
    docker-cisco-utility/supervisor/cisco-8000-support.conf
```

Paths are relative to the resolved source root. Globs are not accepted. Each
file is installed using its basename, for example:

```text
docker-cisco-utility/supervisor/cisco-8000-agent.conf
    -> /etc/supervisor/conf.d/cisco-8000-agent.conf
```

The list must be declared but may be explicitly empty when there are no resident
addon programs, as in the default sample:

```ini
[supervisor]
conf-files =
```

Health commands remain required. An empty list does not excuse a missing or
invalid declared file.

Each fragment must satisfy these rules:

- Resolve to a regular `.conf` file inside the source root, without absolute
  paths, parent traversal, or symlink escapes.
- Have a unique basename matching `<platform>-*.conf`.
- Contain only `[program:*]` and `[group:*]` sections. Global sections such as
  `[supervisord]`, `[include]`, `[unix_http_server]`, `[supervisorctl]`, and
  `[rpcinterface:*]` are prohibited.
- Use platform-qualified program and group names that are unique across the
  fragment set and do not collide with the framework health-server program.
- Define every program referenced by a `[group:*]` section in the declared set.
- Refer to vendor commands installed from the validated artifact.
- Run programs in the foreground and route standard output and error to
  container logs.
- Allow Kubernetes `SIGTERM` handling and shutdown within its grace period.

The complete configuration must pass Supervisor configuration parsing. Do not
install undeclared fragments through the artifact or replace the main
configuration or container entrypoint.

For example:

```ini
[program:cisco-8000-agent]
command=/opt/cisco/live-addon/bin/cisco-agent
autostart=true
autorestart=true
startsecs=5
stopasgroup=true
killasgroup=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

Splitting programs across multiple files is optional. Vendor binaries and
arguments may change without corresponding framework build-rule changes as
long as the declared fragments continue to satisfy this contract.

## 7. Health Commands

Provide the three `[health]` commands shown in section 2:

| Setting | Meaning | Framework endpoint |
|---|---|---|
| `startup-command` | Has vendor initialization completed? | `/health/startup` |
| `liveness-command` | Does the running container require restart? | `/health/live` |
| `readiness-command` | Is the vendor function currently available? | `/health/ready` |

Commands must be absolute executable paths with optional explicit arguments.
They run without a shell and must be read-only checks that do not modify system
state. Exit code `0` maps to HTTP 200. Non-zero exit, timeout, spawn failure, or
an internal execution error maps to HTTP 503. Standard output and error are
diagnostic only and are truncated to `max-output-bytes`.

`command-timeout-seconds` must leave sufficient margin below the Kubernetes
probe `timeoutSeconds` for command termination and the HTTP response, including
requests waiting for an in-flight check.

Health commands must remain in the foreground and must not daemonize, create
detached sessions, or leave background descendants. Initial timeout cleanup
uses process groups, not cgroup containment.

A vendor may use the same executable for every probe type:

```ini
[health]
startup-command=/opt/cisco/live-addon/bin/health-check
liveness-command=/opt/cisco/live-addon/bin/health-check
readiness-command=/opt/cisco/live-addon/bin/health-check
command-timeout-seconds=8
max-output-bytes=4096
```

Checks run on demand, not through a periodic vendor monitor or a cached status
file. Concurrent requests for one endpoint share one in-flight invocation;
different check types may execute concurrently. The server does not maintain
startup state or gate liveness and readiness execution. Kubernetes handles
normal probe ordering, retries, and restart/readiness policy.

Startup checks must report success only after vendor initialization and required
SONiC dependencies are ready, including after reboot. Deployment owners must
allow a probe window long enough for expected initialization; see
[framework section 7.6](./design_review.md#76-kubernetes-probe-semantics).

The framework generates `/etc/live-addon/health.ini` from the profile and owns
the HTTP server. Its bind address `127.0.0.1` and port `50200` are not
vendor-configurable. The vendor does not need to implement an HTTP service or
supply a runtime health configuration file.

## 8. Feature Manager Metadata

Declare `[manifest]` values in the platform profile, not as raw JSON or an
arbitrary Docker `LABEL` instruction:

| Setting | Requirement |
|---|---|
| `package-name` | Valid, nonempty addon package identity; also the authoritative container name |
| `package-version` | Explicit, nonempty overall addon release version |
| `host-service` | Explicit Boolean |
| `asic-service` | Explicit Boolean |
| `after` | Comma-separated SONiC service names; may be empty |
| `privileged` | Explicit Boolean; no implicit grant of privileged operation |

All fields other than `after` are required. Whitespace-only release versions,
invalid Boolean values, and malformed service names are rejected.

`package-version` is not a dependency version, Docker tag, or manifest schema
version. The release owner sets it explicitly. It becomes the nested
`package.version` consumed by SONiC qualification checks; the top-level manifest
schema version remains `1.0.0`.

The manifest does not install Feature Manager inside the container or itself
grant Kubernetes privileges. Deployment configuration must be consistent with
the declared service and privilege values.

## 9. Submission and Qualification

A vendor integration PR supplies the reviewed platform profile, the location of
source or prebuilt binary inputs, a build-or-copy preparation script, declared
Supervisor fragments, health commands, and integration tests. Additional source
or toolchain prerequisites belong in normal reviewed Make rules and are
activated only for the selected integration.

After normal SONiC build setup, the proposed selection is:

```bash
make LIVE_ADDON_PLATFORM=cisco-8000 target/docker-live-addon.gz
```

`LIVE_ADDON_PLATFORM` selects the addon profile, not SONiC's ASIC/build
`PLATFORM`. For an explicitly requested live-addon build, omitting this
selection builds the checked-in example without external vendor inputs or
credentials. An invalid selection fails; it does not fall back to that example.

Before submission, verify that:

- Source, working directory, script, and declared fragments resolve correctly.
- The script succeeds non-interactively and produces exactly one valid bundle
  in the supplied clean output directory.
- Artifact metadata and payloads satisfy section 5, including the restricted
  Debian profile when applicable.
- Any configured checksum or signature can be verified.
- The declared programs start under Supervisor, log to container streams, and
  shut down within the Kubernetes grace period.
- Startup checks fail until initialization completes, and all checks report
  success and failure correctly within their timeout.
- With the deployment kept enabled, configured diagnostic services recover and
  become ready after both cold and warm system reboots on the qualified SONiC
  releases and platforms.
- Programs tolerate relevant SONiC service restarts and re-establish their
  dependencies without resetting or disturbing preserved ASIC forwarding state
  during warm recovery.
- Documentation declares whether interrupted diagnostic sessions restart from
  scratch or can resume, and whether results persist. Any claimed persistence or
  resumption is verified, including required checkpoints, persistent storage,
  and identification of collection gaps.
- The manifest identifies the intended release and runtime requirements.

Invalid source selections, missing inputs, build failures, unsafe artifacts,
invalid fragments or health configuration, failed integrity checks, and
installation failures fail the build. Container publication, qualification,
node selection, mounts, privileges, and rollout are coordinated by deployment
owners, not additional fields in the platform profile. The interface is defined
in [framework section 7.8](./design_review.md#78-kubernetes-deployment-boundary).
