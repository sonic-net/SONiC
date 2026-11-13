# Rust supervisord for SONiC containers #

## Table of Content
- [Rust supervisord for SONiC containers](#rust-supervisord-for-sonic-containers)
	- [Table of Content](#table-of-content)
	- [List of Tables](#list-of-tables)
	- [Revision](#revision)
	- [Scope](#scope)
	- [Definitions/Abbreviations](#definitionsabbreviations)
	- [1. Overview](#1-overview)
	- [2. Requirements](#2-requirements)
		- [2.1 Functional requirements](#21-functional-requirements)
		- [2.2 Non-functional requirements](#22-non-functional-requirements)
		- [2.3 Out of scope](#23-out-of-scope)
	- [3. Architecture Design](#3-architecture-design)
		- [3.1 Where supervisord sits today](#31-where-supervisord-sits-today)
		- [3.2 What changes](#32-what-changes)
	- [4. High-Level Design](#4-high-level-design)
		- [4.1 Package and installation](#41-package-and-installation)
		- [4.2 Module structure](#42-module-structure)
		- [4.3 Configuration parsing](#43-configuration-parsing)
		- [4.4 Process supervision](#44-process-supervision)
		- [4.5 XML-RPC server](#45-xml-rpc-server)
		- [4.6 Event listener protocol](#46-event-listener-protocol)
		- [4.7 Native dependent-startup ordering](#47-native-dependent-startup-ordering)
		- [4.8 Shutdown ordering](#48-shutdown-ordering)
		- [4.9 Third-party dependencies](#49-third-party-dependencies)
		- [4.10 Build integration](#410-build-integration)
		- [4.11 Runtime implementation switch](#411-runtime-implementation-switch)
	- [5. SAI API](#5-sai-api)
	- [6. Configuration and management](#6-configuration-and-management)
		- [6.1. Manifest (if the feature is an Application Extension)](#61-manifest-if-the-feature-is-an-application-extension)
		- [6.2. CLI/YANG model Enhancements](#62-cliyang-model-enhancements)
		- [6.3. Config DB Enhancements](#63-config-db-enhancements)
	- [7. Warmboot and Fastboot Design Impact](#7-warmboot-and-fastboot-design-impact)
	- [8. Memory Consumption](#8-memory-consumption)
	- [9. Restrictions/Limitations](#9-restrictionslimitations)
	- [10. Testing Requirements/Design](#10-testing-requirementsdesign)
		- [10.1 Unit Test cases](#101-unit-test-cases)
		- [10.2 System Test cases](#102-system-test-cases)
		- [10.3 System test plan](#103-system-test-plan)
	- [11. Open/Action items](#11-openaction-items)
	- [Appendix A: Measured data](#appendix-a-measured-data)

## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: Abbreviations](#table-2-abbreviations)
* [Table 3: Modules](#table-3-modules)
* [Table 4: Third-party dependencies](#table-4-third-party-dependencies)
* [Table 5: Containers adopted](#table-5-containers-adopted)
* [Table 6: Memory measurement](#table-6-memory-measurement)
* [Table 7: Test layers](#table-7-test-layers)

## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 2026-10-23  | Yakiv Huryk        | Initial version                   |

## Scope

This document describes a drop-in replacement for the Python `supervisor`
package's `supervisord`, which runs in every SONiC container - as PID 1, except
in the two containers that share the host's PID namespace. The
replacement is written in Rust and would be installed at the same path under
the same process name, so no container entrypoint, configuration file, or
consumer of `supervisorctl` changes.

The goal is a reduction in per-container resident memory. The design constraint
is bug-for-bug behavioural compatibility with Python supervisor 4.3.0, which is
the version SONiC pins.

A runtime switch is included so that the Python implementation can be restored
on a running switch without rebuilding or reinstalling an image
([section 4.11](#411-runtime-implementation-switch)).

This document does **not** cover replacing `supervisorctl`, which continues to
come from the pip `supervisor` package.

## Definitions/Abbreviations
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                            |
|--------------------------|--------------------------------------------------------|
| PID 1                    | The init process of a container's PID namespace         |
| PSS                      | Proportional Set Size - resident pages divided by the number of processes sharing them |
| RSS                      | Resident Set Size - resident pages counted in full, regardless of sharing |
| RPC                      | Remote Procedure Call                                   |
| XML-RPC                  | The RPC protocol supervisor serves on its unix socket   |
| HLD                      | High Level Design                                       |
| SAI                      | Switch Abstraction Interface                            |

## 1. Overview

Every SONiC container runs Python `supervisord` as PID 1. It starts the
container's daemons, restarts them under policy, reaps orphans, and serves an
XML-RPC interface on `/var/run/supervisor.sock` that the host uses to drive the
container.

Measured on a switch, that process costs **19.3 MB PSS per container**, across
15-17 containers - a few hundred megabytes of a switch's RAM spent on process
supervision. The work being done does not justify the cost: after startup,
supervisord is largely idle.

This design replaces that process with a Rust implementation of about
**0.9 MB PSS**, a **17-22x** reduction. Measured on three switches, the saving
is **~219-253 MB** across 12 to 14 containers
([section 8](#8-memory-consumption)).

The engineering difficulty is not process supervision. It is compatibility.
Three contracts cannot move:

| Contract                          | Consumer                                  |
|-----------------------------------|-------------------------------------------|
| supervisor configuration format   | every `.conf` file and `.j2` template in `sonic-buildimage` that declares supervisor sections |
| XML-RPC over the unix socket      | stock `supervisorctl`, 230 call sites     |
| event listener protocol v3.0      | `supervisor-proc-exit-listener(-rs)`      |

In addition, six components parse `supervisorctl status` output positionally.
Python's observable behaviour is therefore the specification, including
behaviour that is arguably accidental.

## 2. Requirements

### 2.1 Functional requirements

1. Parse the existing `/etc/supervisor/supervisord.conf` and
   `/etc/supervisor/conf.d/*.conf` files unmodified, including `[program:]`,
   `[eventlistener:]`, `[group:]`, `[include]`, `[unix_http_server]`,
   `[supervisord]`, `[supervisorctl]` and `[rpcinterface:]` sections.
2. Serve the supervisor XML-RPC interface on the configured unix socket such
   that the unmodified pip `supervisorctl` works for every subcommand SONiC
   invokes.
3. Implement the event listener protocol v3.0 (`READY`, `RESULT n`, `OK`/`FAIL`)
   including event buffering, rejection and redelivery, so that
   `supervisor-proc-exit-listener` operates unchanged.
4. Implement the startup ordering currently provided by the
   `supervisord-dependent-startup` plugin, honouring `dependent_startup` and
   `dependent_startup_wait_for` directives.
5. Reap orphaned children as PID 1.
6. Handle `SIGTERM`/`SIGINT` by performing supervisor's shutdown sequence, so
   that `systemctl stop <feature>` completes within the 10 s `docker stop`
   window.
7. Preserve the process name `supervisord`, because `docker_image_ctl.j2` gates
   container startup on `pgrep -x -c supervisord` in an unbounded `until` loop.

### 2.2 Non-functional requirements

1. No change to any container entrypoint, `supervisord.conf.j2` template, or
   `critical_processes` file.
2. Selected by a build flag; a build with the feature disabled must be
   byte-for-byte the current behaviour, including the files and mounts that
   only the runtime switch needs ([section 4.10](#410-build-integration)).
3. Minimal dependency surface. This is PID 1 compiled with `panic = "abort"`; a
   panic restarts the container.
4. Behavioural equivalence must be demonstrable by measurement, not by
   assertion.

### 2.3 Out of scope

* Replacing `supervisorctl`. The pip `supervisor` package remains installed in
  every container image.
* `supervisord` features unused in SONiC. Measured at zero uses in-tree and
  therefore not implemented: `stderr_capture_maxbytes`, RPC basic
  authentication, `[supervisord]`-section `environment=` feeding
  `%(ENV_x)s` expansion, `stopasgroup`/`killasgroup`, and per-program `umask`.

## 3. Architecture Design

### 3.1 Where supervisord sits today

supervisord is not a leaf component. It sits between the host's service model
and every daemon inside the container, and five distinct mechanisms depend on
its behaviour.

```
                         HOST
  +-------------------------------------------------------------+
  |  <feature>.service                                          |
  |        | start                    ^ unit exits when the     |
  |        v                          | container does          |
  |  docker_image_ctl.j2 --------> docker-wait-any-rs           |
  |        |                                                    |
  |        | (1) readiness gate:  pgrep -x -c supervisord       |
  |        |     (unbounded until-loop)                         |
  |        |                                                    |
  |        | (2) docker exec .. supervisorctl start|stop|status |
  +--------+----------------------------------------------------+
           |                                    230 call sites
  +--------v----------------------------------------------------+
  |  CONTAINER                                                  |
  |                                                             |
  |   CONFIG_DB --(3) sonic-cfggen--> supervisord.conf          |
  |                   (at start)      critical_processes        |
  |                                   watchdog_processes        |
  |                                                             |
  |   +------------  supervisord   (PID 1)  ----------------+   |
  |   |  unix socket <-- XML-RPC                            |   |
  |   |  fork/exec . reap orphans . restart policy          |   |
  |   +--+-------------+--------------+-----------^---------+   |
  |      | spawn       | stdout       | (4) events |(5) SIGTERM |
  |      v             v              v            |            |
  |   daemons   +--> rsyslogd    proc-exit-listener+            |
  |   barriers  |    (priority 1)      |                        |
  |      |      |        |             | reads CONFIG_DB        |
  |      +------+        v             v   FEATURE.auto_restart |
  |       stdout    /dev/log      eventd (ZMQ)                  |
  +-------------------------------------------------------------+
```

Mechanism (5) deserves emphasis because it is unusual: when a *critical* process
exits unexpectedly, `supervisor-proc-exit-listener` sends `SIGTERM` to
`getppid()`, deliberately killing PID 1. supervisord exits, the container exits,
and systemd restarts the unit. Killing the init process is the container restart
path.

The listener exists in two implementations. 42 of the 48 configurations that
declare it run the Rust `supervisor-proc-exit-listener-rs` from
`src/sonic-supervisord-utilities-rs`; the Python `supervisor-proc-exit-listener`
remains only in the vpp, virtual-switch `syncd` and `redfish` containers. Both
act on `PROCESS_STATE_EXITED` with `expected:0` and speak the same protocol, so
this document refers to them together as `supervisor-proc-exit-listener`.

### 3.2 What changes

Only the implementation of the box labelled `supervisord (PID 1)`. Every arrow
into and out of it keeps its current protocol and semantics.

One process disappears: the `supervisord-dependent-startup` plugin, an
event listener that Python supervisord spawns to perform startup ordering, is
implemented natively (see [section 4.7](#47-native-dependent-startup-ordering)).
The `[eventlistener:dependent-startup]` section remains in the configuration
files and is recognised and skipped at load time, so the same rendered
configuration works under either implementation.

## 4. High-Level Design

This is a **built-in SONiC feature**, not an Application Extension.

Repository changed: `sonic-buildimage` only. No changes to `sonic-swss`,
`sonic-utilities`, `sonic-swss-common`, or SAI.

New source directory: `src/sonic-supervisord-rs`.

### 4.1 Package and installation

A new Debian package `sonic-supervisord-rs` installs a single binary at
`/usr/local/bin/supervisord` - the path at which the pip-installed Python
`supervisord` lives today, and the path ~20 container entrypoints already
`exec`.

The pip-installed `supervisord` at that path is not owned by any Debian
package, so dpkg has nothing to arbitrate. `debian/preinst` moves it aside with
`dpkg-divert --rename` to `/usr/local/lib/supervisord-python/supervisord`,
where it serves as the fallback of the runtime switch
([section 4.11](#411-runtime-implementation-switch)), and `debian/postrm`
reverses the diversion, so removing the package puts the Python supervisord
back.

Two pip packages must stay installed in every container image:
`supervisord-dependent-startup` (`docker-base-trixie/Dockerfile.j2`), and
`supervisor` 4.3.0, which only arrives as its dependency. `supervisor` provides
`supervisorctl` and the Python fallback; the plugin is what the fallback runs
for startup ordering.

A `sonic-supervisord-rs-dbgsym` package is produced via `add_derived_package`.

**Cross-compilation.** `slave.mk` exports `RUST_CROSS_COMPILE_TARGET` for armhf
and arm64 when `CROSS_BUILD_ENVIRON=y`. `debian/rules` passes it to `cargo` and
installs from the target-specific output directory, so an ARM package contains
an ARM binary; the variable is empty for a native build and both paths collapse
to `target/release`. The unit tests are skipped on a cross build, because the
test binaries are built for the target and cannot execute on the build host -
they still gate every native build.

### 4.2 Module structure

###### Table 3: Modules
| Module        | Responsibility                                                         |
|---------------|------------------------------------------------------------------------|
| `main.rs`     | Daemon lifecycle, poll loop, RPC dispatch, dependency engine, shutdown  |
| `config.rs`   | INI parsing, section expansion, variable expansion, validation          |
| `process.rs`  | fork/exec, pipes, state machine, listener framing                       |
| `rpc.rs`      | HTTP framing and XML-RPC encode/decode                                  |
| `syslog.rs`   | `/dev/log` output in supervisor's message format                        |
| `events.rs`   | Event payload construction, serials, type fan-out                       |

The daemon is single-threaded and event-driven, built on `poll(2)` over the
listening socket, connected RPC clients, and every child's stdout/stderr pipes.
Signals are delivered to the loop through a self-pipe.

### 4.3 Configuration parsing

The parser reproduces supervisor's `UnhosedConfigParser` semantics, including
several behaviours that a conventional INI parser gets wrong:

* Inline comments (`;`, `#`) start a comment **only when preceded by
  whitespace**. `command=foo;bar` retains the `;`.
* `[program:x]` with `numprocs=N` defines a *group* `x` containing N processes
  named by `process_name`, with `%(process_num)0Nd` expansion.
* `priority` in an `[eventlistener:]` section sets **both** the process priority
  (default 999) and the group priority (default **-1**).
* Four `[eventlistener:]` conditions are hard configuration errors, matching
  `options.py`: `buffer_size < 1`, a missing `events=` line, an unknown event
  type, and `redirect_stderr=true`.
* Sections with the same name merge, later keys winning, because supervisor
  builds its parser with `strict=False`. This holds across `[include]`d files.
* An `[include]` entry that cannot be opened is skipped with a warning, as
  `RawConfigParser.read` skips it; content that cannot be decoded is still fatal.
  Relative patterns resolve against the including file's directory.
* `[supervisord] loglevel`, `childlogdir` and `nocleanup` are honoured.

A test-only `--dump-config` flag prints the parsed program table in a stable
format, used by the corpus differential in
[section 10](#10-testing-requirementsdesign).

### 4.4 Process supervision

Spawning is built on `std::process::Command` with `pre_exec` for `setsid(2)` and
credential changes, rather than a hand-rolled `fork`/`exec`. Command lines are
split with a reimplementation of Python's `shlex.split(posix=True)`; a split
failure produces supervisor's `can't parse command %r` spawn error rather than a
best-effort split.

The command is resolved before forking exactly as `get_execv_args` does: a bare
name such as `command=fpmsyncd` is searched along the program's `PATH` (its
`environment=` `PATH`, else supervisord's), and a missing, directory or
non-executable file is a spawn error worded as Python words it. Over RPC the
same check is `startProcess`'s pre-flight, so `supervisorctl start` answers
`NO_FILE`/`NOT_EXECUTABLE` without spawning anything.

A channel with no `*_logfile` setting gets an **Automatic** log, as in Python:
`<childlogdir>/<name>-<channel>---<identifier>-XXXXXX.log`, created when the
program's group is added, with the previous run's files cleared at startup
unless `nocleanup` is set. SONiC points `childlogdir` at `/var/log/supervisor`;
twelve containers leave `supervisor-proc-exit-listener`'s logs unset, and its
stderr - where a failure of the critical-process watchdog is reported - lands
there.

Children start in the state a CPython parent leaves them in, because that is
what every SONiC daemon has always inherited: `SIGPIPE` and `SIGXFSZ` ignored
(a write to a vanished peer is `EPIPE`, not death), and - when supervisord's own
environment names no locale, as in every SONiC container - `LC_CTYPE=C.UTF-8`
from PEP 538's coercion.

A child's exit does not wake the main loop: as in Python, whose `SIGCHLD`
handler only records the signal while PEP 475 restarts the interrupted `poll`,
it is noticed through the child's pipes or the poll timeout, and a program
reaped in one pass is restarted in a later one. The poll timeout is at most
1 s, as in Python's `runforever`: an idle container wakes once a second, and a
crash-on-start `autorestart` program with `startsecs=0` is re-forked about once
a second rather than as fast as it can die. It is shorter when a `startsecs`,
backoff or `stopwaitsecs` deadline falls due sooner, so each step of a
`dependent_startup` chain proceeds as soon as its predecessor's `startsecs`
has passed instead of on the loop's next idle wake-up. Output, including an
event listener's, is read at most 128 KiB per pass, as Python's dispatcher
reads it, so a child flooding its pipe cannot hold the loop.

supervisord.log carries Python's lines at Python's levels (`spawned:`,
`success:`, `exited: x (terminated by SIGTERM; not expected)`, `stopped:`,
`gave up:`, `killing 'x' (pid) with SIGKILL`), filtered by `loglevel`. rsyslog
forwards this file to syslog, so its wording is an interface.

The process state machine implements supervisor's states (`STOPPED`, `STARTING`,
`RUNNING`, `BACKOFF`, `STOPPING`, `EXITED`, `FATAL`, `UNKNOWN`) with
`startsecs`, `startretries`, `exitcodes`, `autorestart`, `stopsignal` and
`stopwaitsecs` semantics.

Signals follow `supervisord.py`'s `handle_signal`, with its log wording:
`SIGTERM`, `SIGINT` and `SIGQUIT` request an exit, `SIGHUP` a restart
([section 4.5](#45-xml-rpc-server)), and `SIGUSR2` reopens supervisord's own
log and the programs' log files.

### 4.5 XML-RPC server

The socket, HTTP framing and XML-RPC dialect are those of Python supervisor.
Requests are parsed with `httparse` (HTTP) and `roxmltree` (XML) rather than
hand-rolled parsers, because this is untrusted input reaching PID 1.

Bounds enforced on the request path:

* `Content-Length` is parsed with checked arithmetic; a body length that would
  overflow is rejected rather than producing an out-of-range slice.
* Request bodies are capped at 1 MiB.
* `roxmltree` is configured with `nodes_limit: 8192` and rejects DTDs, bounding
  entity-expansion attacks.

The served methods are exactly these, all in the `supervisor.*` namespace:
`getAPIVersion`, `getVersion` (which `supervisorctl` calls before every
command), `getSupervisorVersion`, `getIdentification`, `getPID`, `getState`,
`getAllProcessInfo`, `getProcessInfo`, `startProcess`, `startProcessGroup`,
`startAllProcesses`, `stopProcess`, `stopProcessGroup`, `stopAllProcesses`,
`signalProcess`, `signalProcessGroup`, `signalAllProcesses`, `reloadConfig`,
`addProcessGroup`, `removeProcessGroup`, `getAllConfigInfo`, `shutdown` and
`restart`. Any other name, including one without the `supervisor.` prefix, is
`UNKNOWN_METHOD`, and a call with the wrong number of arguments is
`INCORRECT_PARAMETERS`, as Python's dispatcher answers. Parameters keep their
positions whatever their XML-RPC type.

`restart` is what `supervisorctl reload` calls; sonic-mgmt runs it in the gnmi
container after changing its configuration. As in Python it replies `True` at
once, stops every program in shutdown order
([section 4.8](#48-shutdown-ordering)), and starts afresh: the binary re-execs
itself with its original arguments, so the process keeps its PID, re-reads the
configuration and the runtime switch, clears the Automatic logs, re-binds the
socket and redoes the startup ordering. `SIGHUP` does the same.

If another supervisord already answers on the configured socket, a second one
refuses to start, as Python does, rather than taking the socket over.

Process names resolve as `_getGroupAndProcess` resolves them - `group:name`,
`name` only where the group is the program's own, and `group:*` for the whole
group. Once shutdown begins every `supervisor.*` method faults
`SHUTDOWN_STATE`. A request for any path other than `/RPC2` - including the
`/logtail` stream behind `supervisorctl tail -f` - is answered 404, and an
unparseable body 400, rather than left unanswered. The connection closes after
the reply for HTTP/1.0 and for `Connection: close`, as medusa does, including
when the reply was deferred.

`startProcess` and `stopProcess` reproduce supervisor's deferred-reply
semantics: the call is resolved as soon as the process leaves `STARTING` for any
state, so a crash-looping program faults immediately rather than blocking the
caller for its whole `startretries` budget.

### 4.6 Event listener protocol

Event listeners are children whose stdin/stdout carry the v3.0 protocol. The
implementation covers:

* Header and payload construction with supervisor's field order, so that
  listeners parsing positionally are unaffected.
* Per-pool FIFO queues bounded by `buffer_size`.
* `RESULT n` with `OK` or `FAIL`; a `FAIL` returns the event to the head of the
  pool queue for redelivery.
* Two independent serial numbers per event: a global `serial` and a per-pool
  `poolserial`. The pool serial is assigned when the event **enters** the pool
  and is retained across redelivery.
* Group event types (`PROCESS_STATE`) fan out to the concrete event names.
* A pool of `numprocs > 1` listeners delivers each event exactly once.
* The listener state machine of `dispatchers.py`: a listener starts
  ACKNOWLEDGED; anything but `READY` there, spurious data while READY, or
  `READY` while BUSY is a protocol violation that moves it to UNKNOWN, which is
  terminal until it restarts, and its in-flight event is re-queued.
* A listener that closes its stdout is reported, not polled forever, and one
  that closes its stdin (EPIPE on write) is quarantined with its event
  re-queued rather than stalling the pool.

### 4.7 Native dependent-startup ordering

supervisor has no startup ordering: `priority` orders the initial autostart
sweep but does not wait for a program to reach a state before starting the next.
SONiC fills this gap with the third-party
`supervisord-dependent-startup` pip package (version 1.4.0), an event listener
that watches `PROCESS_STATE` events and issues `startProcess` calls over
XML-RPC. In-tree, 70 configuration files declare it, 318 programs set
`dependent_startup=true`, and there are 247 `dependent_startup_wait_for` edges.

This implementation performs the same ordering internally. A program with
`dependent_startup=true` becomes eligible once every
`dependent_startup_wait_for=<program>:<state>` edge is satisfied; eligible
programs start in `priority` order, then by name.

An edge naming a program that does not exist is treated as **satisfied**. This
matches the plugin (`supervisord_dependent_startup.py:572-584` warns and deletes
the edge unless `error_action=exit`, which nothing in SONiC sets) and is
load-bearing: `docker-sysmgr`'s `rebootbackend` waits for `start:exited` and
that container has no `[program:start]`. Failing closed leaves its only critical
process `STOPPED` indefinitely.

At load time, a section that is an event listener whose `command` contains
`supervisord_dependent_startup` is dropped, and an informational message is
logged. Running both would race to start the same programs.

The engine runs only when that section is present. `dependent_startup` keys
mean nothing to supervisord itself, so a container without the plugin never had
those programs started automatically: `docker-sonic-vpp`'s `start.sh` starts
`vppcfgd`, `bgpcfgd` and `bgpmon` itself, at the point it is ready for them.

The plugin also requires `autostart=false` beside `dependent_startup=true`; with
its default `--error-action=skip` it stops handling a service that leaves
autostart on, and supervisord autostarts it. Five containers' `[program:start]`
do this, and are treated the same way here.

The engine finishes as the plugin does: once every `dependent_startup`
program has reached `RUNNING` or `FATAL`. Until then it starts again any of
them that is `STOPPED` or `EXITED` without having got there - one stopped while
still `STARTING`, for example. After that it is inert, and a group added later
by `supervisorctl update` is never started by it. Unknown dependencies are
dropped once, at startup; an edge whose program is removed later by `update`
is not satisfied.

### 4.8 Shutdown ordering

supervisor does not signal all processes at once, nor a whole priority tier. It
maintains a priority-sorted queue of groups and repeatedly stops the last
element, popping a group only once all of its processes have stopped
(`supervisord.py:156-172`). Groups therefore stop **one at a time**, highest
group priority first, equal priorities in reverse **name** order: the group
configurations are sorted by (priority, name) (`options.py:1827-1831`) and
declaration order plays no part. Startup uses the same order forwards.

At most one group is stopped per loop pass, and the listener pools are served
in between, as Python's phase 1 / `transition()` / phase 2 sequence does, so the
state-change event of a group that settles at once reaches the event listeners
before their own group is stopped. A process in `BACKOFF` at shutdown gives up -
`FATAL` - rather than being stopped (`process.py:813-828`).

The practical consequence, verified against Python 4.3.0: three equal-priority
programs each with a 2 s stop handler take **6 s** to shut down, not 2 s. Since
event listener groups default to priority -1 they stop last, and a program with
`priority=1` such as `rsyslogd` has its implicit group stop last among programs,
which is why logging survives most of shutdown.

### 4.9 Third-party dependencies

###### Table 4: Third-party dependencies
| Crate         | Version | Purpose                                | Transitive deps |
|---------------|---------|----------------------------------------|-----------------|
| `libc`        | 0.2     | syscall bindings                       | none            |
| `roxmltree`   | 0.21    | XML parsing of RPC requests            | `memchr`        |
| `httparse`    | 1.10    | HTTP request framing                   | none            |
| `signal-hook` | 0.4     | `sigaction`-based signal registration  | small           |

Four direct dependencies, 10 crates in the lock file. For comparison, other Rust
packages in `sonic-buildimage` carry between 51 and 333 lock file entries.

The dependency choice is deliberate. Input on the RPC socket is untrusted, and
with `panic = "abort"` a panic in PID 1 restarts the container, so HTTP framing
and XML parsing use maintained parsers rather than hand-rolled ones.
`roxmltree` carries an explicit "must not panic" guarantee, forbids `unsafe`,
and bounds entity expansion. Together the two parsers add about 65 KB, under
a tenth of the binary.

### 4.10 Build integration

A single build flag in `rules/config`:

```make
# ENABLE_SUPERVISORD_RS - replace the Python supervisord running as PID 1 in
# each container with the Rust one from src/sonic-supervisord-rs.
ENABLE_SUPERVISORD_RS ?= y
```

Containers do not reference the package directly. They reference a variable that
`rules/sonic-supervisord-rs.mk` defines only when the flag is set:

```make
ifeq ($(ENABLE_SUPERVISORD_RS),y)
SONIC_SUPERVISORD_RS_ENABLED = $(SONIC_SUPERVISORD_RS)
SONIC_DPKG_DEBS += $(SONIC_SUPERVISORD_RS)
$(eval $(call add_derived_package,$(SONIC_SUPERVISORD_RS),$(SONIC_SUPERVISORD_RS_DBG)))
endif
```

so each container's rule reads:

```make
$(DOCKER_ORCHAGENT)_DEPENDS += $(SONIC_SUPERVISORD_RS_ENABLED)
```

With the flag unset the variable expands to nothing, the package is never
registered, and every container keeps the pip `supervisord`. The flag is
honoured in one place rather than in 26 `_DEPENDS` lines.

The same flag gates the two pieces that exist only for the runtime switch
([section 4.11](#411-runtime-implementation-switch)): `build_debian.sh` ships
`/etc/sonic/supervisord_python`, and `docker_image_ctl.j2` bind-mounts it, only
when it is `y`. They are gated together because docker creates a directory at a
missing mount source. The flag is part of the root filesystem's cache key, and
with it unset the generated container scripts are byte-for-byte those of a
build without this feature.

###### Table 5: Containers adopted
| Category | Containers |
|---|---|
| Common | `database`, `orchagent` (swss), `teamd`, `lldp`, `snmp`, `dhcp-relay`, `router-advertiser`, `platform-monitor` (pmon), `sysmgr`, `eventd`, `gnmi`, `otel`, `fpm-frr` (bgp), `sonic-mgmt-framework`, `restapi` |
| Optional features | `nat`, `sflow`, `macsec`, `iccpd`, `mux`, `stp`, `p4rt`, `bmp`, `dhcp-server`, `dash-ha` |
| Platform | `docker-syncd-mlnx` |

26 containers. Adopting it for a further container is a one-line change: add
`$(SONIC_SUPERVISORD_RS_ENABLED)` to that image's `_DEPENDS`.

### 4.11 Runtime implementation switch

Replacing PID 1 in every container is a large blast radius, so the change is
reversible on a running switch without rebuilding or reinstalling an image.

`/etc/sonic/supervisord_python` selects the implementation. `0`, the shipped
default, uses this one; `1` falls back to the Python `supervisord`:

```
admin@sonic:~$ echo 1 | sudo tee /etc/sonic/supervisord_python
admin@sonic:~$ sudo config reload -y
```

`config reload` restarts every container except `database`, which keeps the
implementation it started with until the next reboot. A reboot after the edit
is therefore the complete revert; `config reload` is the one that needs no
reboot and covers everything else. The setting does not carry over an image
upgrade: a new image ships `0`, and `config-setup` does not migrate the file.

The mechanism follows `/etc/fips/fips_enable`, which already exists for exactly
this purpose and is read the same way by `orchagent.sh`:

* `build_debian.sh` ships the file containing `0`.
* `docker_image_ctl.j2` bind-mounts it read-only into every container, on the
  line after the `fips_enable` mount, so it is present in all of them including
  `database`.
* Both only when `ENABLE_SUPERVISORD_RS=y`
  ([section 4.10](#410-build-integration)).
* `main()` reads it before parsing configuration or binding the RPC socket, and
  hands over with `execv`, so PID 1 remains PID 1 and no supervisor-of-the-
  supervisor appears in the process table. If the fallback is missing, or is
  not a `#!` script - which would be this binary, re-reading the flag and
  exec'ing itself forever - it logs and continues as the Rust implementation,
  because a malformed switch must not leave a container with no init. A value
  other than `0` or `1`, or a file that exists but cannot be read, is reported
  on stderr - which `docker logs` shows - and selects this implementation.

Three design constraints follow:

1. **The fallback must be a file named `supervisord`.** The host readiness gate
   is `pgrep -x -c supervisord`, which matches `/proc/PID/comm`, and for a `#!`
   script the kernel takes `comm` from the *script's* basename. Measured: the
   same script named `supervisord-py` reports `comm=supervisord-py`, and
   `python3 -m supervisor.supervisord` reports `comm=python3`. Both fail the
   gate and every container then appears unready. Only the directory may
   change, so `debian/preinst` diverts pip's console script to
   `/usr/local/lib/supervisord-python/supervisord` with `dpkg-divert --rename`
   before dpkg unpacks this package over `/usr/local/bin/supervisord`, and
   `debian/postrm` reverses the diversion, so removing the package puts the
   Python supervisord back rather than leaving a container with no init.
2. **It must be a mounted file, not an environment variable.** `config reload`
   restarts containers but does not recreate them, so arguments fixed at
   `docker create` time cannot change, while the entrypoint does re-run.
3. **It must exist before any container starts.** Docker creates a directory
   at a missing `-v` mount source. The flag can then no longer be written,
   and every container stays on this implementation, reporting the unreadable
   flag on stderr. Recovery is to remove that directory, recreate the file with
   `0` or `1`, and restart the containers. Replacing the file, by contrast, is
   harmless when the change is applied by `config reload` or a reboot, because
   the bind mount is resolved again at every container start.
   `supervisorctl reload` re-reads the flag through the container's existing
   mount, so it still sees a replaced file's old contents. It is not a
   supported way to apply the switch.

The fallback is exactly the Python behaviour rather than a hybrid: the
configuration files declare `[eventlistener:dependent-startup]`, and only this
implementation drops that section at runtime, so under Python the plugin is
spawned and performs the ordering.

## 5. SAI API

No SAI API changes. This feature does not interact with SAI.

## 6. Configuration and management

### 6.1. Manifest (if the feature is an Application Extension)

Not applicable. This is a built-in feature, not an Application Extension.

### 6.2. CLI/YANG model Enhancements

No CLI changes and no YANG model changes.

`supervisorctl` remains the pip-provided client and its behaviour is unchanged.
`show` commands are unaffected.

One optional, non-breaking change is proposed for serviceability:
`getSupervisorVersion` may report `4.3.0-rs` instead of `4.3.0`, so that an
operator can distinguish the implementations. No in-tree consumer parses this
value.

### 6.3. Config DB Enhancements

No CONFIG_DB schema changes, no new tables, and no new fields.

Which implementation runs is selected by a file,
`/etc/sonic/supervisord_python` ([section 4.11](#411-runtime-implementation-switch)),
not by CONFIG_DB. supervisord reads it first thing at container start, and the
`database` container, which hosts CONFIG_DB, runs a supervisord of its own; a
key in CONFIG_DB could not select the implementation of the container that
serves it.

`FEATURE|<container>.auto_restart` continues to be consumed by
`supervisor-proc-exit-listener`, unchanged.

## 7. Warmboot and Fastboot Design Impact

There is no functional impact on warm reboot or fast reboot. supervisord holds
no forwarding state and participates in neither the warm-boot data path nor the
state restoration sequence.

Addressing the specific questions in the HLD template:

* **Does this feature add stalls, sleeps or I/O to the boot critical chain?**
  No. It removes work rather than adding it: the
  `supervisord-dependent-startup` plugin process is no longer spawned, so each
  container starts one fewer Python interpreter during startup and the
  `PROCESS_STATE` -> XML-RPC -> `startProcess` round trip per state transition
  is replaced by an in-process check.
* **Does it add CPU-heavy processing in the boot path?** No. Configuration
  parsing is performed once at startup, as today, by a compiled parser instead
  of a Python one.
* **Does it update a third-party dependency with boot-time impact?** No
  third-party runtime dependency is changed. The pip `supervisor` package
  remains installed at the same version.
* **Can the feature be delayed?** Not applicable; it is PID 1.
* **Behaviour when disabled:** with `ENABLE_SUPERVISORD_RS=n` the package is not
  built and no container depends on it, so boot behaviour is identical to
  today's.

Container startup time is expected to improve, for three reasons:

* interpreter start-up is removed from the critical path, for supervisord
  itself and for the dependent-startup plugin;
* stock supervisor 4.3.0 blocks for up to 1 s in its first `poll()` before
  starting anything. `src/supervisor.patch/0001-First-poll-is-non-blocking.patch`
  fixes that, but only in the wheel built for `docker-base-bookworm`; every
  adopted container is trixie-based and installs the unpatched PyPI 4.3.0.
  This implementation starts the autostart programs before its first poll;
* each `dependent_startup` step proceeds as soon as its predecessor's
  `startsecs` has passed ([section 4.4](#44-process-supervision)).

The improvement has not been quantified.

## 8. Memory Consumption

This is the motivating requirement, so it is stated with the measurement
methodology.

Measurements were taken on a single switch running **one** image, toggling
`/etc/sonic/supervisord_python` between `1` and `0` and reloading in between.
Hardware, platform, image, container set and boot are therefore identical on
both sides, and the only difference is which `supervisord` binary PID 1 execs.

Memory is reported as **PSS** (`/proc/PID/smaps_rollup`), not RSS, in the kB
units `smaps_rollup` reports; 1 MB here is 1000 of them. RSS counts a shared
page once per process, so summing RSS across 15 processes that share an
interpreter's pages over-counts physical memory. PSS divides each page by the
number of processes mapping it, so the sum is meaningful. It slightly
overstates what is returned: the interpreter pages a supervisord shares with
Python daemons that keep running stay resident. Most of each supervisord's PSS
is its own heap, so the effect on the totals is small.

###### Table 6: Memory measurement
| | Switch 1, 12 containers | Switch 2, 14 containers | Switch 3, 14 containers |
|---|---|---|---|
| Python supervisor 4.3.0, per container | 19.3 MB PSS | 19.05 MB PSS | 16.6 MB PSS |
| `sonic-supervisord-rs`, per container  | 862 kB PSS  | 946 kB PSS   | 960 kB PSS  |
| Python supervisor 4.3.0, total         | 232,170 kB  | 266,728 kB   | 232,206 kB  |
| `sonic-supervisord-rs`, total          | 10,348 kB   | 13,244 kB    | 13,437 kB   |
| **Saving**                             | **~222 MB (22.4x)** | **~253 MB (20.1x)** | **~219 MB (17.3x)** |

The three switches run different image builds with different container sets,
which accounts for the different container counts and for the lower Python
figure on the third. On the third, the binary was placed in the containers of
an image built without this feature, with pip's script moved to the fallback
path as the package does, and the host's `/etc/sonic` mount carried the flag. Each comparison counts
fewer containers than run on the switch. Containers that do not adopt the
package stay on Python, and `database` is not restarted by `config reload`
([section 9](#9-restrictionslimitations)), so it does not toggle. `gnmi` and
`otel` do switch, but are not in the first two totals: they share the host's
PID namespace, so `/proc/1` inside them is the host's init, and those
measurements, which read each container's PID 1, did not find their
supervisord. The third measurement locates each container's supervisord from
the host instead and includes both - about 31 MB of its saving - but not
`restapi`, which has no `/etc/sonic` mount on that image and so cannot be
switched there.

Per-container figures are tightly grouped. On the first switch: 830 to 964 kB
for this implementation against 19,019 to 19,262 kB for Python, with `sysmgr`
the only outlier at 21,977 kB because it runs more programs. On the second, 904
to 1,045 kB against 18,975 to 19,145 kB; on the third, 888 to 1,089 kB against
16,174 to 17,105 kB. `swss` is the largest on both sides throughout.

RSS would report a substantially larger saving. PSS is the smaller and correct
figure.

Static footprint: the stripped binary is approximately 760 KB.

**When the feature is disabled at build time:** the package is not built and not
installed, so memory consumption is exactly today's.

**When the runtime switch selects Python:** the Rust binary is still installed,
but `execv` replaces it before it allocates anything beyond argument parsing, so
the running footprint is Python's alone. The cost of the switch is the ~760 KB
binary on disk, not in memory.

## 9. Restrictions/Limitations

1. **`supervisorctl` is unchanged.** This package ships only `supervisord`. The
   pip `supervisor` package must remain installed in every container image,
   because 230 call sites depend on the client. The disk footprint of that
   package is therefore not recovered - only the running process.
2. **The runtime switch is applied by restarting containers.**
   `/etc/sonic/supervisord_python` is read when supervisord starts: at
   container start, and again on `supervisorctl reload`, which re-execs it
   inside the running container but through the existing mount. The supported
   way to apply a change is `config reload`. That does not restart `database`,
   which keeps the value it booted with until the next reboot. The file must
   exist before containers start
   ([section 4.11](#411-runtime-implementation-switch)).
3. **Unimplemented supervisor features.** `stderr_capture_maxbytes`, RPC basic
   authentication, `[supervisord]`-section `environment=` feeding `%(ENV_x)s`
   expansion, `stopasgroup`/`killasgroup` and per-program `umask` are not
   implemented; each was measured at zero uses in `sonic-buildimage`. Neither
   are the log-reading RPCs (`readLog`, `read/tailProcessStdoutLog`,
   `read/tailProcessStderrLog`, `clearLog`, `clear(All)ProcessLogs`), the
   `/logtail` HTTP stream behind `supervisorctl tail -f`, `sendProcessStdin`
   or `sendRemoteCommEvent`. None of these is used against a SONiC container
   in sonic-buildimage, sonic-utilities, sonic-host-services, sonic-gnmi or
   sonic-mgmt. The log files themselves are written where Python writes
   them.
4. **The binary must be named `supervisord`.** `docker_image_ctl.j2` gates
   container startup on `pgrep -x -c supervisord` in an unbounded loop, and
   `pgrep -x` matches `/proc/PID/comm`, not `argv[0]`.
5. **No `dependent-startup` line in `supervisorctl status`.** The ordering is
   native, so the plugin process does not exist; stock shows it `EXITED` once
   startup completes. Its warnings, which Python writes to the plugin's
   Automatic stderr log, are not produced.
6. **No empty syslog line per orchagent heartbeat.** Python keeps the newline
   that follows `<!--XSUPERVISOR:END-->` in its output buffer and logs it with
   the next chunk, so with `stdout_syslog=true` every heartbeat also produces
   an empty `swss#supervisord: orchagent ` line - about 8,600 a day at the
   default 10 s interval. This implementation splits output into lines and does
   not log an empty remainder. Observed on hardware under both implementations
   on the same image. Nothing in the tree matches on that line.

## 10. Testing Requirements/Design

Compatibility is treated as a measurement rather than an assertion. Every layer
below feeds identical input to stock Python supervisor 4.3.0 and to this
implementation and compares the results; Python is the oracle.

###### Table 7: Test layers
| Layer | Scale | Runs in build? |
|---|---|---|
| Unit tests | 201 | **Yes** |
| Integration tests | 23 | **Yes** |
| Configuration corpus differential | 118/118 configs, templates rendered | No |
| Command-line corpus differential | 195/195 command lines | No |
| Behavioural differential harnesses | 10 scripts | No |
| System tests ([section 10.3](#103-system-test-plan)) | sonic-mgmt suites | No |

### 10.1 Unit Test cases

201 in-source `#[test]` functions plus 23 integration tests, covering
configuration and value parsing, the process state machine, the event listener
wire protocol, XSUPERVISOR output capture, HTTP framing and argument checking
of the RPC socket, the `supervisorctl status` strings, the `getProcessInfo`
members, the dependency and shutdown engines, `restart` and the signals, and
the runtime switch.

Many are ports of the reference suite in `src/supervisor/supervisor/tests/`,
each citing the file and line it was derived from. Where the reference tests are
white-box over a `Subprocess` - which has no analogue here, because constructing
a `Supervisor` requires a bound RPC socket - the logic is split into a decision
function and the effect that applies it, and the decision is tested. Every such
function takes its clock as a parameter, so no test sleeps and the whole suite
completes in about ten milliseconds.

Each test is checked by mutation: breaking the code it covers makes it fail.

The integration tests cover what unit tests structurally cannot: that the reap
and tick paths actually call those decision functions in the right order, and
behaviour that only exists in a running daemon - CPU use under a half-closed RPC
peer or a listener that closed its pipes, Automatic logs, the log wording and
levels, deferred replies, signal inheritance, shutdown ordering, restart, a
second instance refusing a live socket, and how fast a startup chain advances.
They run the
built binary against configurations whose programs are `/bin/false` and
`/bin/sh`, with event listeners written in POSIX shell, so they need neither a
container image nor Python, and take about ten seconds.

These run during the package build. `debian/rules` defines:

```make
override_dh_auto_test:
ifeq ($(RUST_CROSS_COMPILE_TARGET),)
	cargo test --release --no-run --offline || cargo fetch
	cargo test --release --offline
else
	@echo "cross build for $(RUST_CROSS_COMPILE_TARGET): skipping cargo test (cannot execute target binaries)"
endif
```

so a failing test fails the `.deb`. The tests run once, with no retry, so a
flaky test cannot pass. Most other Rust packages in `sonic-buildimage` override
`dh_auto_test` to a no-op; this package deliberately does not.

### 10.2 System Test cases

**Configuration corpus differential.** The corpus is every configuration that
declares supervisor sections:

* every plain `.conf` file in the tree;
* every supervisor `.j2` template, rendered with an empty CONFIG_DB. That
  yields the unconditional programs of each container - database, swss, bgp,
  lldp, pmon, snmp, radv, dhcp-relay, syncd, gbsyncd and others - with their
  literal command lines and options. The database template is given its
  default single redis instance, which carries the tree's only per-program
  `user=`. One fragment, `dhcp-relay.monitors.j2`, needs sonic-cfggen's own
  filters to render;
* sonic-config-engine's rendered test outputs, which cover dhcp-relay with
  VLANs configured, including `dhcrelay ... -a %%h:%%p %%P`.

Each file is wrapped in a minimal base config with an `[include]`, exactly as
SONiC assembles configuration at container start, then parsed both by Python's
own `supervisor.options.realize()` and by `supervisord --dump-config`. 19 fields
per program are compared, including the process and group priorities
separately and the user. Result: 118 of 118 identical. One further file is a
fragment that Python rejects on its own - its `[group:]` names a program
defined in a sibling file - and is not compared.

**Command-line corpus differential.** Every distinct `command=` line in the
same corpus (174) plus 21 hand-written edge cases are split by Python's
`shlex.split(posix=True)` and by the implementation, comparing both the
resulting tokens and the failure cases. Result: 195 of 195 identical. `%%`
collapsing, which happens before the split, is covered by a unit test.

**Behavioural differential harnesses.** 10 scripts, run inside a real SONiC
container image. The same configuration file - including the
`[eventlistener:dependent-startup]` section - is run under stock Python
supervisord with the plugin, and under this implementation, and the output of an
unmodified `supervisorctl` and the event stream received by an unmodified
listener are compared. Coverage includes `supervisorctl` subcommands
including `reload`, `reread` and `update`, deferred start replies, `numprocs`,
listener pools, event
rejection and redelivery, heartbeat capture, shutdown ordering, unknown
dependencies, and malformed RPC input. A soak script exercises process churn and
RPC traffic under load.

### 10.3 System test plan

The sonic-mgmt suites below exercise every path between the host and
supervisord. Each is run twice on the same image, with
`/etc/sonic/supervisord_python` at `0` and at `1`, and the results compared:

* `process_monitoring/test_critical_process_monitoring.py` - a killed critical
  process restarts its container through `supervisor-proc-exit-listener`.
* `autorestart/test_container_autorestart.py` - the same, per feature, with
  `auto_restart` on and off.
* `container_checker/test_container_checker.py` - container and program health
  as monit and system-health see it.
* `system_health/test_watchdog.py` - a stopped orchagent is reported stuck
  through the XSUPERVISOR heartbeat.
* `ip/test_mgmt_ipv6_only.py` - `supervisorctl reload` in the gnmi container.
* `platform_tests/test_reload_config.py` - `config reload`, which is also how
  the runtime switch takes effect.
* `platform_tests/test_advanced_reboot.py` - warm and fast reboot, with
  control-plane and data-plane downtime compared between the two runs.

A toggle test completes the plan: flip the flag in both directions, apply it
with `config reload` and with a reboot, and confirm which implementation each
container runs - from the host, via `docker inspect -f '{{.State.Pid}}'` and
`/proc/<pid>/exe`, since two containers share the host's PID namespace.

## 11. Open/Action items

None.

## Appendix A: Measured data

Each measurement is from a single switch running one image, toggling
`/etc/sonic/supervisord_python` between `1` and `0` with a `config reload`
between measurements. Hardware, image, container set and boot are identical on
both sides.

| Figure | Value |
|---|---|
| Switch 1: Rust / Python supervisord PSS | 830-964 kB / 19,019-19,262 kB (`sysmgr` 21,977 kB) |
| Switch 1: PSS total, 12 containers | 10,348 kB vs 232,170 kB, ~222 MB saved, 22.4x |
| Switch 2: Rust / Python supervisord PSS | 904-1,045 kB / 18,975-19,145 kB |
| Switch 2: PSS total, 14 containers | 13,244 kB vs 266,728 kB, ~253 MB saved, 20.1x |
| Switch 3: Rust / Python supervisord PSS | 888-1,089 kB / 16,174-17,105 kB |
| Switch 3: PSS total, 14 containers incl. `gnmi`, `otel` | 13,437 kB vs 232,206 kB, ~219 MB saved, 17.3x |
| Binary size, stripped | ~760 KB |
| Direct dependencies / lock file crates | 4 / 10 |
| Source modules | 6 |
| Containers adopted | 26 |
| Unit tests / integration tests | 201 / 23 |

Containers excluded from the comparison and why: containers that do not adopt
the package stay on Python; `database` is not restarted by `config reload`;
on switches 1 and 2, `gnmi` and `otel`, which switch but share the host's PID
namespace, so reading each container's PID 1 did not find their supervisord;
on switch 3, `restapi`, which has no `/etc/sonic` mount on that image.
