# Live-Addon Framework and Build Design

This document describes the proposed SONiC-owned framework, image build, and
runtime implementation in `sonic-buildimage`. The
[vendor integration specification](./design_vendor_spec.md)
defines how vendors integrate their software into the live-addon component.
Release and rollout orchestration are outside the image build.

| Revision | Date | Description |
|---|---|---|
| 0.1 | 2026-11-09 | Initial community proposal |

## 1. Executive Summary

Live-addon is a proposed container framework for running vendor- or
platform-specific diagnostic programs on SONiC switches. It provides a consistent
way to build, validate, package, supervise, and health-check those programs while
keeping the production image and runtime policy under SONiC community ownership.

The framework separates diagnostic functionality from container infrastructure.
Vendors define their diagnostic programs and semantic health checks; the SONiC
live-addon design defines how those inputs are incorporated into an image and
managed at runtime. The proposed model is:

- The SONiC community owns the final Dockerfile and image policy.
- The vendor supplies source code or prebuilt binary artifacts, a deterministic
  script to build or copy the artifact, and declarative installation metadata.
  Binary-only integrations do not require disclosure of proprietary source code.
- The vendor supplies an explicit set of platform-specific Supervisor program
  fragments.
- The SONiC framework supplies the main Supervisor configuration and fixed
  entrypoint.
- The vendor supplies startup, liveness, and readiness health commands. A
  vendor may use the same executable for all three checks.
- The SONiC framework supplies the on-demand HTTP health server and Kubernetes
  probe integration.
- SONiC builds a checked-in example by default, without external vendor inputs.
  Build owners can enable vendor profiles to produce additional, separate
  images. Vendor integrations may be contributed through normal upstream PRs.

The vendor may maintain its own Dockerfile for independent
development and testing, but that Dockerfile should not define the production
image published by the SONiC build pipeline.

---

## 2. Scope

This proposal covers image construction and runtime support for vendor- or
platform-specific diagnostics: source acquisition, artifact validation and
installation, process supervision, health interfaces, and image metadata.
The implementation target is `sonic-buildimage`.

Live-addon-specific files, profiles, and commands in these documents describe
the proposed implementation layout, not files already available upstream.
Repository-relative build paths refer to `sonic-buildimage`, not this
documentation repository. Vendor-specific examples illustrate the contract;
they do not establish a dependency on a particular vendor or claim that its
integration already implements the proposal.

Live-addon is an optional diagnostic and troubleshooting mechanism, not an
always-on part of normal SONiC operation. The operator responsible for a SONiC
deployment decides which addon image to use and when, where, and for how long
to deploy it, based on the issue being investigated. The example image is built
by default; vendor images are built only when enabled. Neither is included in
normal SONiC installer images by default. Building an image does not install or
enable the addon. Deployment and release orchestration remain separate operator
responsibilities.

An operator-enabled live-addon deployment must recover after both cold and warm
system reboots on its qualified SONiC releases and platforms. Restarting services
does not imply uninterrupted execution or automatic resumption of an in-progress
diagnostic session. Vendor restart-safety, session-continuity, and qualification
requirements are defined in
[vendor specification section 9](./design_vendor_spec.md#9-submission-and-qualification).

---

## 3. Design Goals

The proposed integration should:

1. Keep the final production Dockerfile under SONiC community control.
2. Keep vendor integration simple.
3. Allow the vendor to control how its binaries are started without allowing
   it to replace the container's main Supervisor configuration.
4. Provide a common health interface for Kubernetes probes.
5. Support repository-local and external integration inputs, including
   proprietary binary-only packages, through one platform configuration.
6. Pin external input revisions and verify every artifact bundle.
7. Preserve a clear path for vendor-specific dependencies and initialization.
8. Build through normal SONiC Make targets, without a pipeline preparation
   step or a separate Python build orchestrator.
9. Support a public, vendor-free default and optional reviewed vendor
   integrations without requiring private repositories or credentials.

### Out of scope

Running vendor applications for purposes other than diagnostics is outside the
scope of this document.

---

## 4. Recommended Ownership Boundary

| Concern | SONiC framework | Vendor |
|---|---:|---:|
| Final production Dockerfile | Yes | No |
| Base image | Yes | No |
| OS package installation policy | Yes | Declares requirements |
| Artifact preparation | Runs and validates | Supplies source or prebuilt binaries |
| Artifact installation implementation | Owns and executes | Declares format and destination |
| Main `/etc/supervisor/supervisord.conf` | Yes | No |
| Supervisor program fragments | Validates and installs | Produces and declares |
| Container `ENTRYPOINT` | Yes | No |
| Program startup details | No | Yes |
| Generic on-demand health server | Yes | No |
| Semantic health check | Executes and reports | Defines |
| Kubernetes probes | Yes | Provides health semantics |
| Feature Manager manifest | Defines schema, validates, and generates label | Declares platform values |

This boundary lets the vendor retain control over its executable lifecycle
while the SONiC framework retains control over the container lifecycle.
The vendor-facing deliverables are defined in
[vendor specification section 2](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).

---

## 5. Source, Artifact Build, and Installation

The proposed framework has one platform model. Vendor profiles use
`platform/<vendor_name>-<platform>.ini`; the default uses `platform/example.ini`.
All profiles follow the same artifact, validation, Supervisor, health, and
image-generation path. Whether the source is stored in this repository or an
external repository affects only
how the framework resolves the source root.

`[source]` locates integration inputs, not necessarily program source code.
The artifact script may compile supplied source or simply copy a prebuilt binary
bundle into the clean output directory. Both use the same controlled build
environment, validation, and installation path; proprietary program source need
not be provided.

The profile schema and complete example are defined in
[vendor specification section 2](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).
Source selection, artifact production, and payload restrictions are defined in
[section 3](./design_vendor_spec.md#3-source-selection),
[section 4](./design_vendor_spec.md#4-artifact-build-script), and
[section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions).
The framework implements those requirements rather than maintaining a second
input contract.

### 5.1 Getting the integration files and building the image

For each selected profile, the framework:

1. Reads and validates the profile before running any code from the selected
   source directory.
2. Uses the configured directory in `sonic-buildimage` without a separate Git
   checkout, or fetches the external repository and records the exact Git commit
   selected by `ref`.
3. Runs the profile's artifact preparation script in the controlled build
   environment. The script builds a bundle from source or copies a prebuilt
   bundle. The framework passes an absolute path to its output directory.
4. Validates the bundle and the declared runtime configuration.
5. Prepares the approved files for the image build and uses the shared Dockerfile
   maintained by SONiC to install the validated bundle.

The framework gets the integration files before running the artifact preparation
script. It uses credentials for private repositories only when fetching those
files. These credentials are not available in the environment where the script
runs or included in the files sent to Docker for the image build. The framework
uses the same build steps and dependencies for local and external sources.
It does not copy either source directory directly into the image.

The framework creates a fresh, separate output directory before each run of the
artifact preparation script. After the script finishes, the framework finds the
bundle in that directory using the profile's `glob` file pattern. This prevents
it from using files left over from a previous build. Missing or invalid profiles
or inputs cause the build to fail with an explicit error; the framework does not
use the example image instead.

The default example follows these same steps; see section 9.2. The framework uses
the same Dockerfile and generates the runtime configuration in the same way,
regardless of where the integration files are stored.

### 5.2 Validation and layer-safe installation

The framework checks the vendor bundle's format, files, package metadata, and
required dependencies against the rules in
[vendor specification section 5](./design_vendor_spec.md#5-artifact-payload-and-dependency-restrictions).
It uses the appropriate checks and installation tools for the actual format:
Debian package tools, `tar`, or `unzip`. If the bundle's actual format does not
match the format declared by the vendor, the build fails.

Before building the image, the framework can check the package metadata and
files without installing the package or running vendor code. For Debian
packages, some checks also need to know which packages are already installed
and what the package manager would change. The framework runs these checks in
a SONiC-controlled build stage that uses the approved base image:

1. Identify all required packages, including their dependencies, using the
   approved repository snapshot whose contents cannot change.
2. Fix the exact version and target architecture of every package. Record its
   repository and content hash in the build record (provenance) and software
   bill of materials (SBOM).
3. Simulate the full installation before making changes. Reject any package
   changes forbidden by the
   [restricted Debian profile](./design_vendor_spec.md#52-restricted-debian-profile).
4. Install only after the package metadata, files, and simulated installation
   pass these checks. Use the same fixed package versions and architectures,
   with `--no-install-recommends`. Do not let the package manager choose a new,
   unchecked dependency set or install an unchecked bundle with
   `apt-get install -y ./vendor.deb`.

The framework places the checked bundle at a framework-reserved location in
the files supplied to Docker for the build (the Docker build context). This is
where the build reads the bundle, not where its files will be installed.

The generated Dockerfile must not use `COPY` or `ADD` to put the bundle into
the image. Docker saves filesystem changes in layers; deleting the bundle in
a later step would not remove its contents from the earlier layer.

Instead, a BuildKit read-only bind mount lets the installation `RUN` step read
the bundle from the build context without storing the bundle itself in an
image layer:

```dockerfile
RUN --mount=type=bind,source=vendor-artifacts/vendor-bundle.tar.gz,target=/tmp/vendor-bundle.tar.gz,readonly \
    mkdir -p '/opt/<vendor_name>/live-addon' && \
    tar -xzf /tmp/vendor-bundle.tar.gz \
        -C '/opt/<vendor_name>/live-addon' \
        --strip-components=1
```

The framework generates the bundle's source filename and installation command
from the checked artifact metadata. The installed files remain in the image,
but the package or archive itself does not.

For Debian, the generated package-manager commands install the checked local
package and the fixed dependency set. For TAR and ZIP, the generated commands
extract files using the checked installation root and archive options. They
never run an installer included in the archive. The vendor specification's
installation restrictions apply to every format.

Installation and package-manager cache cleanup must happen in the same `RUN`
step. A package-manager or extraction error fails the image build. This approach
requires BuildKit; the SONiC organization build already uses `docker buildx build`.

The final Docker build context contains only the newly built artifact, explicitly
declared and checked Supervisor configuration fragments, generated health
configuration, and approved framework files. These framework files include the
repository snapshot inputs and records of fixed package versions. Do not include
the entire vendor source tree. Any failed validation, content-integrity check,
artifact build, or installation stops the build.

---

## 6. Supervisor Runtime Design

### 6.1 Main configuration ownership

The SONiC community should maintain the main Supervisor configuration as a
framework file in the source repository:

```text
dockers/docker-live-addon/framework/supervisord.conf
```

The generated Dockerfile copies that file to:

```text
/etc/supervisor/supervisord.conf
```

The framework must not depend on the distribution package's default
configuration because its daemon and logging defaults are not the live-addon
container contract. The SONiC-owned configuration should contain:

```ini
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0
pidfile=/var/run/supervisord.pid
user=root

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[include]
files=/etc/supervisor/conf.d/*.conf
```

`nodaemon=true` keeps Supervisor running as the container's PID 1 instead of
forking into the background. Docker and Kubernetes track the lifetime and exit
status of PID 1 and send container termination signals to it. If Supervisor
daemonizes and its original PID 1 exits, the container is considered stopped
and its remaining processes are terminated. Foreground operation inside the
container does not make the Kubernetes workload interactive or prevent it
from running detached from an operator's terminal.

With `nodaemon=true`, Supervisor already writes its activity log to stdout.
`logfile=/dev/null` avoids duplicating those messages in the container log,
and `logfile_maxbytes=0` disables rotation. Vendor program logging follows
[vendor specification section 6](./design_vendor_spec.md#6-supervisor-program-fragments).

The production image should always use the fixed SONiC-owned entrypoint:

```dockerfile
ENTRYPOINT ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
```

The `-n` option enforces the same foreground invariant at the process
invocation boundary. Either `-n` or `nodaemon=true` is sufficient by itself;
using both keeps the repository configuration independently correct and
protects the container lifecycle if one setting is accidentally changed.

The Unix socket remains available for local debugging with `supervisorctl`.
For example, an operator may enter the running container with `docker exec` or
`kubectl exec` and run `supervisorctl status`; that interactive process is
separate from Supervisor's standard-output stream. No Supervisor TCP control
interface is exposed.

### 6.2 Fragment validation and installation

The framework validates the complete declared fragment set against
[vendor specification section 6](./design_vendor_spec.md#6-supervisor-program-fragments),
then copies only those files to `/etc/supervisor/conf.d/<basename>`. It must
validate names and group references across the set, not just each file in
isolation. The artifact cannot populate that directory or replace the main
configuration.

An explicitly empty list is accepted for profiles with no resident addon
programs. The framework health-server program is still installed independently.
The complete main configuration and copied fragment set must pass
`supervisord` configuration parsing during the image build.

### 6.3 Container lifecycle boundary

The fixed entrypoint starts Supervisor identically for every platform. Vendor
startup details remain inside the validated fragments rather than being
duplicated in framework build rules.

This provides a stable platform boundary:

```text
Kubernetes
    -> SONiC-owned ENTRYPOINT
        -> SONiC-owned main supervisord.conf
            -> validated vendor <vendor_name>-<platform>-*.conf fragments
                -> vendor binaries
```

---

## 7. Kubernetes Health Probe Design

### 7.1 Health cannot be inferred generically

There is no reliable universal test that can determine whether an arbitrary
vendor binary is semantically healthy. A running process may still be
deadlocked, disconnected from a required dependency, or unable to perform its
function.

The framework therefore defines how checks are invoked and interpreted, while
the vendor provides the platform-specific startup, liveness, and readiness
executables.

### 7.2 On-demand checks

Kubernetes already decides when to request health checks. The health server
runs the vendor checks when requested, avoiding a separate background monitor
and saved results that could be out of date.

### 7.3 On-demand health architecture

The SONiC framework should provide one common process:

| Component | File | Responsibility |
|---|---|---|
| Health HTTP server | `framework/health_server.py` | Invoke the command mapped to the requested endpoint and return its current result |

```text
Kubernetes kubelet
       |
       | GET /health/startup, /health/live, or /health/ready
       v
framework/health_server.py
       |
       | invokes the corresponding command with a strict timeout
       v
Vendor startup, liveness, or readiness executable
       |
       v
HTTP 200 or HTTP 503
```

When a health endpoint is called, the server runs the corresponding vendor
health-check command and returns its result. Results are not cached for later
checks. Calls that arrive while the same check is still running share its result.

The default example supplies small read-only health-check commands through
the same contract. The health server invokes them on demand: successful checks
produce HTTP 200 and failures produce HTTP 503. Missing health commands remain
a build error for every profile.

The server should start independently of the vendor processes. If Kubernetes
probes the container before the server is listening, the connection failure is
a failed probe and Kubernetes retries according to the probe configuration. If
the server is listening but the vendor is not initialized, the startup command
returns non-zero and the server returns HTTP 503.

The initial deployment contract requires `hostNetwork: true`. The health
server must listen only on `127.0.0.1:50200`, and every Kubernetes HTTP probe
must explicitly set `host: 127.0.0.1` and `port: 50200`. Because a
host-networked Pod shares the SONiC node's network namespace, the health server
and the host kubelet use the same loopback interface.

The proposed deployment reserves port `50200` for this health server.
Qualification must verify that no other host-network service on
the node uses that address and port. Binding the server to `0.0.0.0` is not
permitted because it would expose unauthenticated endpoints that execute vendor
commands through every applicable switch interface. The bind address and port
are framework-owned values and are not vendor-configurable.

### 7.4 Runtime health configuration

During the image build, the framework reads and validates the `[health]`
settings in the selected platform profile. It uses these settings to generate
`/etc/live-addon/health.ini` in the image, in the format expected by the health
server. The health server uses this file to run the configured checks.

The command syntax, meaning, timeout, and diagnostic limits are defined in
[vendor specification section 7](./design_vendor_spec.md#7-health-commands).

### 7.5 Request execution rules

The server maps endpoints directly:

| Endpoint | Command |
|---|---|
| `/health/startup` | `startup-command` |
| `/health/live` | `liveness-command` |
| `/health/ready` | `readiness-command` |

For every request, the server should:

1. Validate the endpoint and select its configured command.
2. Start the command without a shell in a new process group.
3. Capture size-limited standard output and error.
4. Wait up to `command-timeout-seconds`.
5. On timeout, terminate the process group, wait a short grace period, and
   force-kill any remaining processes.
6. Return HTTP 200 only for exit code `0`; otherwise return HTTP 503.
7. Log the endpoint, duration, exit code or timeout, and bounded diagnostics.

Checks are independent. The server does not require startup state to decide
whether a liveness or readiness command may run. Kubernetes provides the normal
ordering by withholding liveness and readiness probes until the startup probe
succeeds.

Vendor health commands may be closed-source binaries whose execution time and
resource use cannot be assumed. The framework therefore permits at most one
active invocation of each check type. Concurrent requests for the same
endpoint must use single-flight coalescing: the first request starts the
command, and later requests wait for that in-flight command and receive the
same result. They must not start another vendor process or fail solely because
another caller reached the endpoint first.

Different check types may run concurrently. The Python server should use
`ThreadingHTTPServer` and maintain synchronized in-flight state for each
endpoint. When a command completes, the server must publish its result, wake
all waiting requests, and clear the in-flight state before writing any HTTP
response. A slow or disconnected client must not prevent a later request from
starting the next command. Client disconnection must not cancel an invocation
that still has other waiting callers.

Waiting requests must not outlive the configured command timeout. The
`command-timeout-seconds` value must leave sufficient margin below the
Kubernetes probe `timeoutSeconds` for a waiting kubelet request to receive the
shared HTTP response.

### 7.6 Kubernetes probe semantics

The kubelet is the Kubernetes agent running on each node. For live-addon, it
sends HTTP requests to the health endpoints; the health server runs the
corresponding vendor commands.

Kubernetes uses the results as follows:

| Probe | Action when the configured failure threshold is reached |
|---|---|
| `startupProbe` | Restart the container if initialization has not completed within the allowed startup window |
| `livenessProbe` | Restart the container |
| `readinessProbe` | Mark the Pod not ready, without restarting the container |

The deployment owner supplies the Kubernetes deployment YAML and configures
how often probes run, their timeouts, and their failure thresholds. Use the
endpoint addresses described in section 7.3 and the timeout margin in section 7.5.

Allow enough time for vendor initialization and required SONiC services to
become ready before the startup probe's failure threshold is reached. This
does not control the order in which other containers start.

### 7.7 Supervisor integration

The SONiC framework should add only the generic health server independently of
the vendor fragments:

```ini
[program:live-addon-health-server]
command=/usr/bin/health_server.py --config /etc/live-addon/health.ini --bind 127.0.0.1 --port 50200
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

If the health server exits unexpectedly, Supervisor restarts it. Probe
connection failures during that interval are treated as health failures by
Kubernetes.

---

## 8. SONiC Feature Manager Image Manifest

A manifest is a JSON description of the addon image. It records the addon name
and release version, whether it runs as a host or ASIC service, the SONiC
services listed in `after`, and whether it requires a privileged container.
SONiC stores this JSON in an image label named `com.azure.sonic.manifest`.
A label is information attached to the Docker image; Feature Manager reads
it from the host without running the addon container.

The vendor supplies these values in the platform profile's `[manifest]`
section. [Vendor specification section 8](./design_vendor_spec.md#8-feature-manager-metadata)
defines the required settings and valid values. The framework checks them
before building the image and fails the build if they are invalid or a required
value is missing.

The vendor sets `package-name` in `[manifest]` in the selected
`platform/<vendor_name>-<platform>.ini` file. For example,
`package-name=live-addon-<vendor_name>-<platform>` names the addon and its
container; it is not the filename of the vendor's Debian package. See the
[platform profile example](./design_vendor_spec.md#2-integration-inputs-and-platform-configuration).

The framework reads that INI file and creates `live-addon.vars`, a build-time
file containing Make variable assignments for the addon name, release version
and other image settings. Make reads this generated file before using those
settings to build the image. The vendor does not supply `live-addon.vars`.

SONiC's existing `generate_manifest` routine creates most of the manifest from
these Make settings, including the package name, release version, `after`
service list and container privilege requirement.

For the two service flags, the proposed framework supplies
`dockers/docker-live-addon/manifest.part.json.j2`. This is a SONiC-owned
Jinja template; `.j2` identifies the template format. "Part" means it produces
only part of the final manifest, not a second complete manifest. The framework
passes the validated `host-service` and `asic-service` values from the INI
file to this template. For the vendor profile example, it produces:

```json
{
  "service": {
    "host-service": true,
    "asic-service": false
  }
}
```

The build renders this template to `manifest.part.json` and merges its two values
into the full `manifest.json`. This ensures the final service flags match the
vendor's declarations. The existing
[manifest-generation routine](https://github.com/sonic-net/sonic-buildimage/blob/master/rules/functions#L212-L241)
supports this partial-file merge.

SONiC's regular image build then stores the completed JSON in the
`com.azure.sonic.manifest` image label.

For example, the generated manifest contains:

```json
{
  "version": "1.0.0",
  "package": {
    "name": "live-addon-<vendor_name>-<platform>",
    "version": "202411.1.0.15"
  },
  "service": {
    "host-service": true,
    "asic-service": false,
    "after": ["syncd"]
  },
  "container": {
    "privileged": true
  }
}
```

There are two different versions in this JSON. The top-level `version`
(`1.0.0`) identifies the manifest format. The nested `package.version`
(`202411.1.0.15` in this example) identifies the addon release.
Qualification checks that select supported addon versions must read
`package.version`, not the Docker image tag, and must fail if the release
version is missing.

The checked-in example profile uses its own package name and release version.
It sets `host-service=false`, `asic-service=false`, and `privileged=false`,
and leaves `after` empty. It therefore does not register a working vendor
service.

To read the addon release version without starting the container:

```bash
sudo docker image inspect <image:tag> \
  --format '{{ index .Config.Labels "com.azure.sonic.manifest" }}' \
  | jq -r '.package.version'
```

The manifest only describes the image. It does not install Feature Manager
inside the container or grant Kubernetes privileges. The deployment owner must
configure the deployment to match the service and privilege values declared
in the manifest.

---

## 9. Proposed Build Flow

### 9.1 Building live-addon images and adding them to an installer

Add `rules/docker-live-addon.mk` to register the example and enabled vendor images
in `SONIC_DOCKER_IMAGES` and the supported builder-release list, such as
`SONIC_BOOKWORM_DOCKERS`. Use the SONiC-owned
`dockers/docker-live-addon/Dockerfile.j2` with the existing image build recipe
in `slave.mk`.

The live-addon Make rule must run the preparation steps before building the
image: obtain the selected inputs, build or copy the vendor artifact, validate
the inputs and artifact, and prepare the files needed by the Docker build.
Make tracks these steps as prerequisites of the image target. Small Python
helpers can perform validation; Make remains responsible for running the build.

Keep live-addon images out of the default installer image lists. Building
them does not install or enable diagnostics.

To include a vendor image in a particular SONiC installer, the build owner first
enables its profile through `LIVE_ADDON_VENDOR_PLATFORMS`. The platform's build
rules then add `docker-live-addon-<vendor_name>-<platform>.gz` to
`SONIC_INSTALL_DOCKER_IMAGES` only when that installer build explicitly requests
it. The platform's installer rule must retain the archive in
`<installer>_DOCKERS`, the final list of Docker images selected for that
installer. Enabling a vendor build alone must not select it for inclusion.

During installer construction, SONiC loads the selected archive's Docker image
into the filesystem that will be installed on the switch. The vendor image is
then available locally after SONiC installation. Including it does not deploy
or start its diagnostics; the deployment owner still controls whether and how
they run.

### 9.2 Default example, vendor build controls, and system tests

The normal SONiC image build must build the checked-in example from
`platform/example.ini`
with `[source] path=dockers/docker-live-addon/platform/example`. This path is
relative to the `sonic-buildimage` repository root. The example is a reference
implementation of the framework, not a vendor diagnostic service. It uses the
same artifact build, validation, installation, and health interfaces as vendor
integrations, with its payload confined to `/opt/example/live-addon`.
Its Docker image is named `docker-live-addon`, and its saved archive is
`target/docker-live-addon.gz`.

The build owner controls vendor builds through the Make setting
`LIVE_ADDON_VENDOR_PLATFORMS`, a space-separated list of profile names.
Define this setting in `rules/config` with an empty default. The build owner
sets the list in that file; leaving it empty builds no vendor images. Add a name
to enable that vendor's build; remove it to disable the build. Merely adding a vendor INI file
to the branch does not enable it. This setting does not change SONiC's
ASIC/build `PLATFORM`, and it does not disable the default example.

Vendor profile names use `<vendor_name>-<platform>`. For example,
`LIVE_ADDON_VENDOR_PLATFORMS="<vendor_name>-<platform>"` enables
`platform/<vendor_name>-<platform>.ini`. List multiple names to build multiple
vendor images. The build produces:

| Profile | Docker image name | Saved archive |
|---|---|---|
| `example` | `docker-live-addon` | `target/docker-live-addon.gz` |
| `<vendor_name>-<platform>` | `docker-live-addon-<vendor_name>-<platform>` | `target/docker-live-addon-<vendor_name>-<platform>.gz` |

Each enabled vendor profile produces its own image and
`target/docker-live-addon-<vendor_name>-<platform>.gz` archive; it does not replace
the example or another vendor's output. Each image's manifest comes from that profile's
`[manifest]` values, including its package name, release version, service flags,
and privilege requirement. The build keeps artifacts, generated configuration,
and image metadata separate for each profile. Unknown profiles and unsupported
release/architecture combinations fail the build rather than producing a
different image.

The example image contains the approved OS dependencies, main Supervisor
configuration, fixed entrypoint, framework health server, sample health-check
payload and example manifest. The sample explicitly declares `[supervisor]`
with an empty `conf-files` value: only the framework health server runs under
Supervisor, and sample checks execute only when requested. It needs no
privileged operation, host PID namespace or host-filesystem mounts.

Public CI must build the example and run `sonic-mgmt` system tests against it
on a Linux testbed, without vendor hardware or private inputs. The tests must
exercise startup, liveness, and readiness endpoints, including successful and
failed checks, command timeouts, and concurrent requests sharing one check.
This provides a common test of the health server independent of vendor programs.

### 9.3 Dependency and cache handling

```text
Default example + enabled vendor profiles
              |
              v
For each profile, Make resolves and validates its inputs
              |
              +--> example/local vendor: resolve the checked-in source path
              |
              +--> external vendor: fetch the declared repo and pinned ref
              |
              +--> build or copy the selected artifact in a controlled environment
              +--> validate one bundle and declared runtime configuration
              +--> stage approved snapshot sources, locks and metadata
              |
              v
Shared regular-image recipe renders Dockerfile.j2, generates the manifest,
injects hooks in place, builds Dockerfile and saves the image
              |
              v
Separate image archive + version records + final SBOM for each profile
```

---

## 10. References

- [Live-Addon Vendor Integration Specification](./design_vendor_spec.md)
- [SONiC buildimage repository](https://github.com/sonic-net/sonic-buildimage):
  shared image recipes, build hooks, and manifest generation.
- [Kubernetes startup, liveness, and readiness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/):
  deployment-side probe behavior.
- [Supervisor configuration](https://supervisord.org/configuration.html):
  process supervision and configuration semantics.
