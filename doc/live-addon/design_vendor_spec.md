# Live-Addon Vendor Integration Specification

## 1. Purpose and Scope

This document defines how vendors integrate diagnostic software into live-addon.
It specifies the required inputs, supported options, package restrictions,
process configuration, health commands, and release metadata.
The integration is proposed, not implemented upstream. Paths and examples refer
to the planned `sonic-buildimage` integration.

The [framework and build design](./design_review.md) explains how SONiC builds,
validates, packages, and runs these inputs. Release and runtime deployment
settings are outside the vendor profile.

The vendor may supply source or prebuilt binary artifacts, along with scripts
and configuration files. Vendors supplying prebuilt binaries do not need to
provide proprietary source code. The vendor does not supply the production
Dockerfile or a prebuilt production image. A vendor may use its own Dockerfile
for development and testing, but the SONiC build does not use it.
The framework selects the base image and defines the installation policy.
It supplies the main Supervisor configuration, entrypoint, and generic HTTP
health server.

## 2. Integration Inputs and Platform Configuration

Each vendor integration is selected by
`platform/<vendor_name>-<platform>.ini` under `dockers/docker-live-addon`.
Replace the angle-bracket placeholders in the examples with the vendor name
and platform name. The default example uses `platform/example.ini`.
The profile declares:

| Section | Vendor input |
|---|---|
| `[source]` | Directory in `sonic-buildimage`, or external Git repository and revision |
| `[vendor-build]` | Working directory and deterministic artifact preparation script (build or copy) |
| `[artifact]` | Bundle format, filename pattern (`glob`), approved installation root, and archive options |
| `[supervisor]` | Explicit list of process configuration fragments; may be empty |
| `[addon]` | Optional approved OS packages required by the integration |
| `[manifest]` | Addon name, release version, and Feature Manager service/container settings |
| `[health]` | Startup, liveness, and readiness commands and execution limits |

The selected input directory must contain the declared script, Supervisor
fragments, and either buildable source or a prebuilt bundle. These inputs must
also provide the health commands installed in the image.
The vendor does not supply a separate runtime `health.ini`, main
`supervisord.conf`, raw manifest JSON, or container entrypoint.

Example platform profile:

```ini
[source]
repo=git@github.com:<vendor_name>/<vendor_name>-<platform>.git
ref=202411.1.0.15

[vendor-build]
working-directory=docker-<vendor_name>-<platform>-utility
build-script=./build-live-addon-artifact.sh

[artifact]
format=deb
glob=*.deb
install-root=/opt/<vendor_name>/live-addon

[supervisor]
conf-files =
    docker-<vendor_name>-<platform>-utility/supervisor/<vendor_name>-<platform>-agent.conf
    docker-<vendor_name>-<platform>-utility/supervisor/<vendor_name>-<platform>-support.conf

[addon]
optional-packages=rsyslog,supervisord-dependent-startup

[manifest]
package-name=live-addon-<vendor_name>-<platform>
package-version=202411.1.0.15
host-service=true
asic-service=false
after=syncd
privileged=true

[health]
startup-command=/opt/<vendor_name>/live-addon/bin/check-startup
liveness-command=/opt/<vendor_name>/live-addon/bin/check-liveness
readiness-command=/opt/<vendor_name>/live-addon/bin/check-readiness
command-timeout-seconds=8
max-output-bytes=4096
```

The privilege and service values above describe this example integration, not
defaults or an automatic grant of runtime privileges.

## 3. Source Selection

`[source]` selects the directory containing the integration files. Use exactly
one of the following forms.

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
repo=git@github.com:<vendor_name>/<vendor_name>-<platform>.git
ref=202411.1.0.15
```

`ref` is required. The framework records the exact Git commit before running
the artifact preparation script. The framework uses private repository
credentials only when fetching the integration files. These credentials are
not available to the artifact preparation script or included in the final
Docker context.

Both source options must meet the same artifact, Supervisor, health, and
manifest requirements. The framework does not copy repository-local source
directly into the image. Building the public example must not require private
vendor integrations.

## 4. Artifact Build Script

Provide one artifact preparation script through `build-script`. It must run
without user input and produce the same bundle from the same inputs. It may
build from supplied source or copy a prebuilt package or archive into the output
directory. The script prepares the bundle; the framework installs it later.
The framework runs the script from the configured working directory and passes
an absolute output directory:

```text
./build-live-addon-artifact.sh --output /workspace/vendor-artifacts
```

The script must:

- Exit with a non-zero status on failure.
- Produce exactly one declared artifact bundle in the supplied output directory.
- Not build or publish a Docker image or require publishing credentials.
- Not write outside its source and output directories.
- Record the bundle's version.

Set `working-directory` relative to the selected source directory. The framework
runs `build-script` from that working directory; both must exist. The framework
creates a fresh output directory for each run. It matches the artifact `glob`
against files in that directory, not the source tree. The pattern must match
exactly one file.

The script must use documented build dependencies with fixed versions. It may
download these dependencies over the network. It must not modify unrelated
build-system resources, access unrelated credentials, or require privileges to
control the build host.

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

Declare `install-root=/opt/<vendor_name>/live-addon` for every bundle format.
`<vendor_name>` must be a single SONiC-approved vendor directory name. All vendor
files must be installed beneath this root, including executables, private
libraries, Python modules, configuration files, and documentation.
Configure each process to find its libraries and Python modules using explicit
paths or settings that apply only to that process. Do not change global library
loader or Python startup settings. These restrictions do not apply to
SONiC-approved OS dependencies or package-manager state managed by the framework.

Payloads must not contain parent-directory references (`..`), device nodes,
set-user-ID or set-group-ID files, or symbolic or hard links that escape
`install-root`.
Installation must not start services, modify the main Supervisor configuration,
overwrite SONiC-owned framework files, fetch additional vendor payloads, or
require credentials.

### 5.2 Restricted Debian profile

Initially, Debian packages must meet these restrictions.

The package metadata archive, called the control archive, may contain only
`control`, `md5sums`, `shlibs`, and `symbols`. Executable or interactive package
hooks, including `preinst`, `postinst`, `prerm`, `postrm`, and Debconf `config`
scripts, are prohibited.
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

`Depends` entries must name specific SONiC-approved packages. Alternative or
virtual-package dependencies are not accepted initially. Dependencies must be
available from the approved repository snapshot whose contents cannot change.
The framework fixes each dependency's version and architecture and installs it
using `--no-install-recommends`. It rejects dependency installation if it removes,
downgrades, replaces, or deconfigures an installed package, or changes a protected
SONiC framework package.

Files in a `.deb` must already have destination paths beneath `install-root`.
Installation does not relocate them. A vendor file cannot use a path outside
that root even if no installed package owns the path. Parent-directory entries
may describe only the path leading to `install-root`; they must not modify
existing parent directories or their metadata.

Links must not escape `install-root`, including through existing filesystem
links. The package must not replace a non-directory filesystem entry owned by
the approved base image or a locked dependency. Existing directories may be
shared, but the package must not change their type or weaken their permissions.
Vendor programs must find their private libraries without changing the global
runtime linker configuration or cache.

### 5.3 TAR and ZIP profiles

Package the archive so that extracting it into `install-root` puts every file in
its final location. The framework does not run an installer from the archive.
Archive entry paths must not be absolute and must follow section 5.1's path and
file-type restrictions.

Set `strip-components` to remove leading directories from archive paths before
extraction. It defaults to `0`, which keeps the original paths. For example:

```ini
[artifact]
format=tar
glob=*.tar.gz
install-root=/opt/<vendor_name>/live-addon
strip-components=1
```

### 5.4 Optional OS packages

Declare additional OS packages through `[addon] optional-packages`, as shown
in section 2. They must use SONiC's approved package sources, fixed versions,
and installation policy. Do not supply package-manager commands or a Dockerfile
to bypass these controls.

## 6. Supervisor Program Fragments

List each Supervisor configuration file (fragment) in the multiline `conf-files`
setting:

```ini
[supervisor]
conf-files =
    docker-<vendor_name>-<platform>-utility/supervisor/<vendor_name>-<platform>-agent.conf
    docker-<vendor_name>-<platform>-utility/supervisor/<vendor_name>-<platform>-support.conf
```

Paths are relative to the selected source directory. Globs are not accepted.
The framework uses only the filename when installing each file, for example:

```text
docker-<vendor_name>-<platform>-utility/supervisor/<vendor_name>-<platform>-agent.conf
    -> /etc/supervisor/conf.d/<vendor_name>-<platform>-agent.conf
```

The `conf-files` setting is required but may be empty when there are no
long-running addon programs, as in the default example:

```ini
[supervisor]
conf-files =
```

Health commands remain required. Every listed file must exist and be valid.

Each fragment must satisfy these rules:

- Resolve to a regular `.conf` file inside the selected source directory,
  without absolute paths, parent traversal, or symlink escapes.
- Have a unique filename matching `<vendor_name>-<platform>-*.conf`.
- Contain only `[program:*]` and `[group:*]` sections. Global sections such as
  `[supervisord]`, `[include]`, `[unix_http_server]`, `[supervisorctl]`, and
  `[rpcinterface:*]` are prohibited.
- Include the platform in program and group names. Names must be unique across
  all declared fragments and must not match the framework health-server program.
- Include a definition for every program named in a `[group:*]` section in one
  of the declared fragments.
- Refer to vendor commands installed from the validated artifact.
- Run programs in the foreground and route standard output and error to
  container logs.
- Ensure programs handle `SIGTERM` and exit within the Kubernetes shutdown
  grace period.

Supervisor must be able to parse the combined configuration. Do not install
undeclared fragments through the artifact or replace the main configuration or
container entrypoint.

For example:

```ini
[program:<vendor_name>-<platform>-agent]
command=/opt/<vendor_name>/live-addon/bin/<vendor_name>-<platform>-agent
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

You may put multiple programs in one file or split them across files. You can
change vendor binaries and their arguments without changing the framework's
build rules, provided the fragments still meet these requirements.

## 7. Health Commands

Provide the three `[health]` commands shown in section 2:

| Setting | Meaning | Framework endpoint |
|---|---|---|
| `startup-command` | Has vendor initialization completed? | `/health/startup` |
| `liveness-command` | Does the running container require restart? | `/health/live` |
| `readiness-command` | Is the vendor function currently available? | `/health/ready` |

Specify each command as an absolute executable path, optionally followed by
arguments. The framework runs commands without a shell. Checks must not modify
system state. The framework returns HTTP 200 for exit code `0`. It returns
HTTP 503 if a command returns non-zero, times out, cannot be started, or if an
internal execution error occurs. Standard output and error are diagnostic only
and are truncated to `max-output-bytes`.

Set `command-timeout-seconds` low enough that command termination and the HTTP
response also fit within the Kubernetes probe's `timeoutSeconds`, even when a
request waits for a check that is already running.

Health commands must run in the foreground. They must not daemonize, create
detached sessions, or leave child processes running in the background. On
timeout, the framework terminates the process group; it does not use a cgroup
to contain the command's processes.

A vendor may use the same executable for every probe type:

```ini
[health]
startup-command=/opt/<vendor_name>/live-addon/bin/health-check
liveness-command=/opt/<vendor_name>/live-addon/bin/health-check
readiness-command=/opt/<vendor_name>/live-addon/bin/health-check
command-timeout-seconds=8
max-output-bytes=4096
```

Each health request runs the corresponding vendor command; requests to the same
endpoint share the command if it is already running. Different check types may
run at the same time. The health server does not cache results or run a periodic
monitor.
The server does not track whether startup has completed or wait for startup
success before running liveness and readiness checks. Kubernetes controls probe
ordering, retries, restarts, and whether the container is ready.

Startup checks must report success only after vendor initialization and required
SONiC dependencies are ready, including after reboot. Deployment owners must
configure probes to allow enough time for expected initialization; see
[framework section 7.6](./design_review.md#76-kubernetes-probe-semantics).

The framework runs the HTTP server and generates `/etc/live-addon/health.ini`
from the profile. Vendors cannot change its bind address (`127.0.0.1`) or port
(`50200`) and do not need to implement an HTTP service or supply a runtime health
configuration file.

## 8. Feature Manager Metadata

Declare `[manifest]` values in the platform profile, not as raw JSON or an
arbitrary Docker `LABEL` instruction:

| Setting | Requirement |
|---|---|
| `package-name` | Valid, nonempty addon package name; also the container name |
| `package-version` | Explicit, nonempty overall addon release version |
| `host-service` | Explicit Boolean |
| `asic-service` | Explicit Boolean |
| `after` | Comma-separated SONiC service names; may be empty |
| `privileged` | Explicit Boolean; no implicit grant of privileged operation |

All fields other than `after` are required. Whitespace-only release versions,
invalid Boolean values, and malformed service names are rejected.

The release owner sets `package-version` to identify the addon release.
SONiC qualification checks read it from the manifest's nested `package.version`
field. This is separate from dependency versions, Docker tags, and the top-level
schema `version`, which remains `1.0.0`.

The manifest does not install Feature Manager inside the container or itself
grant Kubernetes privileges. Deployment configuration must be consistent with
the declared service and privilege values.

## 9. Submission and Qualification

Submit a PR with the platform profile, source or binary input location,
preparation script, declared Supervisor fragments, health commands, and
integration tests. Declare additional source or toolchain dependencies in the
normal Make rules, which must be reviewed. Enable these dependencies only when
the build owner enables the integration.

The default build produces the checked-in example without vendor inputs.
Vendor profiles produce additional, separate images with their own manifests;
adding a profile alone does not enable its build. The build controls and output
names are defined in
[framework section 9.2](./design_review.md#92-default-example-vendor-build-controls-and-system-tests).

Before submitting the PR, verify that:

- The source selection is valid, and the working directory, script, and declared
  fragments exist at the configured paths.
- The script succeeds non-interactively and produces exactly one valid bundle
  in the supplied clean output directory.
- Artifact metadata and payloads satisfy section 5, including the restricted
  Debian profile when applicable.
- Any configured checksum or signature can be verified.
- The declared programs start under Supervisor, send standard output and error
  to container logs, and shut down within the Kubernetes grace period.
- Startup checks fail until initialization completes, and all checks report
  success and failure correctly within their timeout.
- With the deployment kept enabled, configured diagnostic services recover and
  become ready after both cold and warm system reboots on each SONiC release
  and platform being qualified.
- Programs handle relevant SONiC service restarts and reconnect to their
  dependencies without resetting or disturbing preserved ASIC forwarding state
  during warm recovery.
- The documentation states whether interrupted diagnostic sessions restart from
  scratch or can resume, and whether results persist. Any claimed persistence
  or ability to resume is tested, including required checkpoints, persistent
  storage, and gaps in collected data.
- The manifest identifies the intended release and runtime requirements.

The build must fail for invalid source selections, missing inputs, unsafe
artifacts, invalid Supervisor or health configuration, failed integrity checks,
or errors during preparation or installation. Deployment owners coordinate
container publication, qualification, node selection, mounts, privileges, and
rollout. These are not additional platform profile settings.
