# SONiC Build System Migration #

## Table of Content 

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions/Abbreviations](#3-definitionsabbreviations)
   - [3.a Prior Art](#3a-prior-art)
4. [Overview](#4-overview)
   - [4.a Motivation](#4a-motivation)
   - [4.b Migration](#4b-migration)
     - [Phase 1: Opt-in trial period](#phase-1-opt-in-trial-period)
     - [Phase 2: Opt-out migration period](#phase-2-opt-out-migration-period)
     - [Phase 3: Bazel-only](#phase-3-bazel-only)
     - [CI considerations](#ci-considerations)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
   - [7.a Changes to Existing Build System (Bazel/make Interoperability)](#7a-changes-to-existing-build-system-bazelmake-interoperability)
   - [7.b Bazel Build](#7b-bazel-build)
     - [7.b.1 Groundwork](#7b1-groundwork)
     - [7.b.2 Managing Patched External Dependencies](#7b2-managing-patched-external-dependencies)
     - [7.b.3 Building Component Containers](#7b3-building-component-containers)
     - [7.b.4 Platform & Device Support](#7b4-platform--device-support)
     - [7.b.5 Debuggability](#7b5-debuggability)
   - [7.c Affected Systems](#7c-affected-systems)
     - [Dependency Changes](#dependency-changes)
     - [Changed Repositories](#changed-repositories)
   - [7.d Performance Summary](#7d-performance-summary)
8. [SAI API](#8-sai-api)
9. [Configuration and management](#9-configuration-and-management)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
    - [Warmboot and Fastboot Performance Impact](#warmboot-and-fastboot-performance-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions/Limitations](#12-restrictionslimitations)
13. [Testing Requirements/Design](#13-testing-requirementsdesign)
    - [13.1. Unit Test cases](#131-unit-test-cases)
    - [13.2. System Test cases](#132-system-test-cases)
14. [Open/Action items - if any](#14-openaction-items---if-any)

### 1. Revision  

### 2. Scope  

This document covers the migration of the SONiC build system into a modern, Bazel-based system. It proposes an end state of the build system, as well as a migration path to get us there.

Please note that this design covers only the migration of individual components. Migrating the full image assembly process is out of the scope of this document.

### 3. Definitions/Abbreviations 

- Bazel: A build system open-sourced by Google. It specializes in polyglot builds, and promises fast, reproducible builds through hermeticity. [Documentation](https://bazel.build/docs)
- Bazel rules, also called rulesets: Extensions to Bazel to provide additional capabilities, usually to integrate Bazel with a new programming language. Usually named `rules_<lang>`. For instance, `rules_go` extends Bazel to be able to build and test Go sources. [Documentation](https://bazel-docs-staging.netlify.app/versions/master/skylark/rules.html)
- BUILD files: Files where the Bazel build is defined. Usually named `BUILD.bazel`, and written by hand in [Starlark](https://bazel.build/rules/language). [Documentation](https://bazel.build/concepts/build-files)
- Bazel registry: A specially-shaped directory that hosts bazel rules and their versions. [Documentation](https://bazel.build/external/registry)
- Bazel Central Registry, or BCR: The canonical, Google-maintained Bazel registry. Most rulesets live here, and most Bazel projects pull their rulesets from here. [Documentation](https://registry.bazel.build/)
- bzlmod: Bazel's dependency resolution tool, which takes care of resolving ruleset dependencies. Automatically works with the BCR by default, but can be configured to resolve dependencies from other Bazel registries. [Documentation](https://bazel.build/external/overview)
- Bazel target: The unit of a build. A target represents one or more inputs and produces one or more outputs. For instance, "the docker image for syncd" is a target, but so is "the shared library of sonic_swss_common". [Documentation](https://bazel.build/concepts/build-ref)
- Label: The unique identifier of a target. It follows the syntax `@<repository name>//path/to/target:<target name>` . For instance, `@sonic_buildimage//dockers/docker-base-bookworm:docker-base-bookworm` refers to [this target](https://github.com/thesayyn/sonic-buildimage/blob/04f2d3bf54650b1ceecb663a11f53be6810856f1/dockers/docker-base-bookworm/BUILD.bazel#L123-L139). [Documentation](https://bazel.build/concepts/labels)

Non-Bazel Definitions
- debhelper, or `dh`: A suite of Debian tools to rebuild and repack Debian packages. In SONiC, they are used to apply patches to external dependencies. [Documentation](https://man7.org/linux/man-pages/man1/dh.1.html)
- Open Container Initiative (OCI): An industry standard to specify container formats and runtimes. [Documentation](https://opencontainers.org/).

#### 3.a Prior Art

We have already implemented large parts of this document as proofs of concept.

Please see these publications about our work:
- Talk from OCP EMEA Summit 2026: https://www.youtube.com/watch?v=uSKCNDWuXjc
- Blog article about our work:  https://aspect.build/blog/bazel-for-sonic

### 4. Overview 

> [!tip]
> A full example of migrating a container can be found in [sonic-buildimage#28005](https://github.com/sonic-net/sonic-buildimage/pull/28005).
> We will explore the different moving pieces in that PR in [Section 7](#7-high-level-design).

#### 4.a Motivation

The current SONiC build system, while being ergonomic and accommodating the vast matrix of platforms and vendors that are required, has some shortcomings, that the community has been feeling for some time.

After two decades of SONiC development, we now have a fuller picture of what SONiC needs in a build. With this information, we believe we can build a faster, more reliable build system on top of Bazel.

Early results demonstrate that we can produce cold builds similar to those in the current system, but **sub-minute builds** for some classes of incremental changes, all while keeping hermeticity and reproducibility, so that the same build on the same commit will produce the same results a year from now.

#### 4.b Migration

Bazel migrations are expensive, and famously disruptive. To alleviate this issue as much as possible, we propose a gradual, non-mandatory rollout.

We will extend the existing build system with a new target type that can build docker containers in Bazel.
The mechanics of this new target are discussed in [7.a](#7a-changes-to-existing-build-system-bazelmake-interoperability).

Users can control whether they want to build with Bazel or GNU make with a command line flag:

```
$ make target/docker-sysmgr.gz
# Builds make-based target as usual

$ BUILD_WITH_BAZEL_WHEN_AVAILABLE=y make target/docker-sysmgr.gz
# make runs Bazel to build the target
```

This flag will start off disabled by default. The implementation of this flag's semantics is defined in [section 7.a](#7a-changes-to-existing-build-system-bazelmake-interoperability).

To minimize disruption, we propose the following phases to the migration:

##### Phase 1: Opt-in trial period

Phase 1 will introduce Bazel as an optional build system for some components. For this phase, `BUILD_WITH_BAZEL_WHEN_AVAILABLE` will be turned off by default.
We will start with small components such as `sflow`, `teamd`, and `database`, and continue onto progressively larger leaf components until we have sufficient coverage to be representative of the Bazel build.
We expect this phase to last until the November release.

The community can use this period to experiment with Bazel, adopt it into their own builds, and generally gather information on whether this is a net benefit.

After the November release, the community will face a decision point: Should we adopt Bazel fully?

If we decide to move forward, we will continue onto Phase 2.

##### Phase 2: Opt-out migration period

At the start of this phase, we will flip `BUILD_WITH_BAZEL_WHEN_AVAILABLE` to be on by default.
This will signal to the community that we do intend to adopt Bazel, and that they should start adopting it into their internal forks if they haven't already.

We expect to massively increase coverage of targets that build with Bazel, specifically extending to building the base layers (`docker-base-*`, `docker-config-engine-*`, and `docker-swss-layer-*`) with Bazel by default.

By the end of this phase, we expect most users to be able to build their components entirely in Bazel, without the need of a slave container.

##### Phase 3: Bazel-only

When every component can be built with Bazel, and most users have had a reasonable opportunity to migrate, we expect to be able to remove the current build system, and transition to using exclusively Bazel.

We cannot give estimations of when this will be, as it will depend on community support and involvement.

##### CI considerations

One open question is when we will establish a blocking CI pipeline for Bazel builds.
We propose doing this early, as part of Phase 1.

After the first container build merges, we will stand up a non-blocking CI pipeline that will test the Bazel build.
That pipeline will run on every build, but failures in it won't block contributors from merging code.

When that pipeline has been proven to be stable for a reasonable period, we propose to make it blocking, so that contributions that would break the Bazel build cannot be merged.
This will avoid code drift between the two builds, helping tremendously with migration speed.

### 5. Requirements

The migration must satisfy the following requirements:

1. Faster builds
    * Cold builds comparable to those of the current system
    * Sub-minute incremental builds for common classes of changes
    * Aggressive caching, so that unchanged components are never rebuilt
2. Hermetic and reproducible builds
    * No dependency on the host system (e.g. host-installed `gcc`, `python`, or `docker`)
    * The same build on the same commit produces the same artifacts
3. Equivalent build output
    * Resulting containers are comparable to those of the current system in size, runtime performance, and memory footprint
    * No regression in functionality of the produced images
4. Gradual migration
    * Bazel and GNU make coexist, with per-component opt-in and opt-out controlled by a single flag
    * Components are migrated one at a time, starting from the least depended-on
    * A CI pipeline that validates the Bazel build to prevent drift between the two systems
5. Platform and device coverage
    * Present patterns to migrate the existing matrix of vendors, platforms, devices, and ASIC manufacturers
    * Allow users to select the target platform and SAI implementation at build time from the command line
6. Maintained developer experience
    * Automatic generation of debug containers, mirroring the current system

### 6. Architecture Design 

There are no expected changes to the SONiC architecture.

### 7. High-Level Design 

This section specifies how different parts of the build will work under Bazel.
Everything explained here has already been implemented in a proof of concept migrating `docker-sysmgr`, in [sonic-buildimage#28005](https://github.com/sonic-net/sonic-buildimage/pull/28005).
The following sections will explain different parts of that PR.

#### 7.a Changes to Existing Build System (Bazel/make Interoperability)

During the migration, Bazel and make will have to interoperate. This section explains the changes needed in the current build system to make that happen.

We propose to **extend the existing build system to add the ability to build some targets with Bazel**. For example, with [docker-sysmgr](https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/rules/docker-sysmgr.mk#L21-L30):

```make
# From sonic-buildimage#28005/rules/docker-sysmgr.mk

...
ifeq ($(BUILD_WITH_BAZEL_WHEN_AVAILABLE),n)

SONIC_DOCKER_IMAGES += $(DOCKER_SYSMGR)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_SYSMGR)

else

# When BUILD_WITH_BAZEL_WHEN_AVAILABLE is enabled, build this docker with Bazel.
# Bazel only supports bookworm today, which is enforced at the root Makefile.
$(DOCKER_SYSMGR)_BAZEL_BASE += $(DOCKER_CONFIG_ENGINE_BOOKWORM)
SONIC_BAZEL_DOCKER_IMAGES += $(DOCKER_SYSMGR)
SONIC_BOOKWORM_DOCKERS += $(DOCKER_SYSMGR)

endif
...
```

As shown in the example, the `BUILD_WITH_BAZEL_WHEN_AVAILABLE` configuration flag will toggle the entire Bazel behaviour. When switched off, the system will use the regular make-based build:

```make
# From sonic-buildimage#28005/rules/config

...
# Build eligible dockers (those registered in SONIC_BAZEL_DOCKER_IMAGES) with
# Bazel instead of the legacy `docker build` flow.
# When disabled, fall back to the normal Make docker build.
BUILD_WITH_BAZEL_WHEN_AVAILABLE ?= n
```

This flag is defined in [rules/config](https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/rules/config#L164-L177), along with another flag to control where the Bazel cache directory goes, `SONIC_BAZEL_CACHE_SOURCE`.

We modify the rules execution engine to create targets for this new target type. In [`slave.mk`](https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/slave.mk#L1413-L1420):

```make
# From sonic-buildimage#28005/slave.mk

...
# Targets for building docker images with Bazel.
$(addprefix $(TARGET_PATH)/, $(SONIC_BAZEL_DOCKER_IMAGES)) : $(TARGET_PATH)/%.gz : .platform \
		$$(addprefix $(TARGET_PATH)/,$$($$*.gz_BAZEL_BASE))
	$(HEADER)
	bazel run --config=slave //dockers/$*:write_$*.gz $(LOG)
	$(FOOTER)

SONIC_TARGET_LIST += $(addprefix $(TARGET_PATH)/, $(SONIC_BAZEL_DOCKER_IMAGES))
```

Please note that these new targets depend on make-built base images, through the `$*_BAZEL_BASE` condition.
We have written [some tooling to import make-built base images into Bazel](https://github.com/sonic-net/sonic-buildimage/tree/e09be005b19c3521c674e4415d08a25648fc15f4/tools/bazel/oci), but they are out of scope of this section.

This ensures that Bazel-built dockers are built exactly like any other Docker, in the slave container, while maintaining Bazel's benefits like hermeticity and a more granular cache.
It also ensures that **there should be no change to the workflow of someone using Bazel**. The way they call make is the same, and the produced artifacts should be interchangeable.

Our goal is that a contributor could switch to Bazel without even realizing it.

#### 7.b Bazel Build

This section describes how individual components are built with Bazel, focusing on the Bazel build itself rather than its interoperability with the existing make-based system.

##### 7.b.1 Groundwork

The Bazel ethos is that **every input to a build must be known, down to the checksum, before the build starts**. The current build system has a few instances where we cannot deterministically predict these inputs.

- Define a hermetic gcc toolchain, so that we always use the same version for every build. [Source](https://github.com/blorente/sonic-build-infra/tree/master/toolchains/gcc).
- Fetch Debian packages deterministically, instead of relying on `apt install`. We do that by using `rules_distroless` to fetch from a Debian snapshot. [Source](https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/MODULE.bazel#L23-L56).

##### 7.b.2 Managing Patched External Dependencies

The SONiC build relies on patching several third party dependencies (e.g. [libnl3](https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/src/libnl3/BUILD.bazel)). Furthermore, it relies on the Debian suite of tools ([debhelper](https://man7.org/linux/man-pages/man1/dh.1.html) and associated tools), which is not compatible with Bazel. Hence, another solution is required.

We propose four approaches to tackle this problem. They are detailed in [this documentation](https://github.com/thesayyn/sonic-buildimage/blob/master/tools/bazel/docs/import-external-projects.md), but we will list their summaries here for ease of reference.

In order of most preferred to least preferred, they are:

1. Find the module we want to patch in the BCR. Please see the PR for instructions on how to patch it.
2. Pull the dependency as a Debian package with `rules_distroless`. This method does not allow patching.
3. Migrate said dependency to Bazel. The specific method will depend on the dependency, but tips and tricks have been listed in the document above.
4. Patch and build the dependency out of band, and then import the built artifacts into the Bazel build.

An early draft of documentation explaining these can be found [here](https://github.com/thesayyn/sonic-buildimage/blob/master/tools/bazel/docs/import-external-projects.md).

##### 7.b.3 Building Component Containers

Currently, most components in SONiC are bundled into `.deb` archives before being installed in the containers to be deployed.

We propose a similar model except, instead of `.deb` archives, we will bundle the components into tar archives for ease of consumption. Using `tar.bzl` and `mtree`, we can replicate the rootfs structure of `.deb` packages:

```starlark
# Example from: https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/src/sonic-sysmgr/BUILD.bazel#L4-L11
# Note how we're able to place a file in `/debian/sysmgr/rebootbackend`.
tar(
    name = "sysmgr_pkg",
    srcs = ["//rebootbackend"],
    mtree = [
        "./debian/sysmgr/rebootbackend type=file content=$(location //rebootbackend:rebootbackend)",
    ],
    visibility = ["//visibility:public"],
)
```

Then, we can skip the `apt install` step of building containers and just treat each tar as an OCI container layer with `rules_oci`:

```starlark
# Example from: https://github.com/sonic-net/sonic-buildimage/blob/e09be005b19c3521c674e4415d08a25648fc15f4/dockers/docker-sysmgr/BUILD.bazel#L59-L72
oci_image(
    name = "docker-sysmgr",
    base = ":config_engine_base_layout",
    entrypoint = ["/usr/local/bin/supervisord"],
    env = {
        "DEBIAN_FRONTEND": "noninteractive",
    },
    tars = [
        ":apt_deps",
        ":rdeps",
        ":source_files",
    ],
    visibility = ["//visibility:public"],
)
```

##### 7.b.4 Platform & Device Support

The current SONiC build supports a rich matrix of vendors, platforms, and devices. This can be replicated with Bazel's expressive configuration language.

We define command line flags to allow users to specify which device and ASIC manufacturer they're targeting ([link](https://github.com/blorente/sonic-build-infra/blob/master/config/BUILD.bazel)):

```starlark
# SONiC platform, which maps to ASIC manufacturers
string_flag(
    name = "asic_manufacturer",
    build_setting_default = "_incompatible",
    values = [
	    "broadcom",
	    "marvell-prestera",
	    ... # Other manufacturers
	],
)
```

Then, we can use these values to parameterize the build. For instance, we can define an alias at `@sonic_buildimage//dockers/docker-syncd` that will point to the right `@sonic_buildimage//platform` subdirectory:

```starlark
# Will resolve to the right docker image based on platform, or fail if no platform is specified or if the specified platform is not supported.

alias(
    name = "docker-syncd",
    actual = select({
        "@sonic_build_infra//config:platform_vs": "//platform/vs/docker-syncd-vs",
        "@sonic_build_infra//config:platform_broadcom": "//platform/broadcom/docker-syncd-brcm",
        "//conditions:default": ":empty",
    }),
)
```

Once the build is defined like that, a user that wants to build for Broadcom can specify this from the command line:

```shell
$ bazel build //dockers/docker-syncd:docker-syncd --@sonic_build_infra//asic_manufacturer=broadcom
```

We can similarly parameterize every aspect of the build, including which SAI implementation to use:

```shell
$ bazel build <target> \
   --@sonic_build_infra//asic_manufacturer=broadcom
   --@sonic_build_infra//sai=<your custom SAI implementation>
```

For ease of use, we propose bundling default configurations for well-known combinations:

```shell
$ bazel build <target> --config=broadcom # Equivalent to the above.
```

##### 7.b.5 Debuggability

We will implement automatic debug container generation, mirroring the current system.

We will write a Bazel rule that will crawl the dependency tree of an image, capture the debug symbols of its binaries, and bundle them with well-known debugging tools such as `gdb` to create debug containers.

For instance, following the example in [7.b.4](#7b4-platform--device-support):

```starlark
oci_image(
    name = "docker-base-bookworm",
    ...
)

debug_container(
	name = "docker-base-bookworm_dbg",
    base = ":docker-base-bookworm" # reference the container above
)
```

Users will then be able to load these containers into switches normally for debugging.

#### 7.c Affected Systems

##### Dependency Changes

Once components build entirely in Bazel, we lose a few dependencies:
- We no longer need a sonic-slave container. Note that, during the migration, Bazel still runs inside the slave container (see [7.a](#7a-changes-to-existing-build-system-bazelmake-interoperability)); this dependency only goes away once a component builds entirely in Bazel.
- We no longer depend on developer tools such as `gcc` and `python` being installed in the build machine.
- We no longer depend on Docker at build time.

And we gain a few dependencies:
- We depend on Google servers to download and install Bazel at build time.
- We gain a dependency on the Bazel Central Registry.

##### Changed Repositories

Every component repository will need to be migrated to Bazel. `sonic-buildimage` will also need to change, but it will be migrated piecemeal.

#### 7.d Performance Summary

We expect the resulting containers to be comparable (if not equal) to those produced by the old build system, both in terms of size and runtime performance and memory footprint.

We aim for build times to be reduced dramatically, especially for incremental builds. We expect noticeable second-order effects on developer ergonomics, as a more reliable build means fewer cold builds overall. We expect on-disk build caches to be significantly larger than those of the old build system.

### 8. SAI API 

There are no changes to the SAI API.

### 9. Configuration and management 

There are no changes to the configuration.

### 10. Warmboot and Fastboot Design Impact  

TODO BL: I probably need help from Brian for this

### Warmboot and Fastboot Performance Impact
This sub-section must cover the impact of the functionality on warmboot and fastboot performance, that is control plane and data plane downtime.
As part of the analysis cover the following:

- Does this feature add any stalls/sleeps/IO operations to the boot critical chain? Does it change when this feature is disabled/unused? 
- Does this feature add any additional CPU heavy processing (e.g. rendering Jinja templates) in the boot path (process, library or utility used during boot up)? Does it change when this feature is disabled/unused?
- In case this feature updates a third party dependency does it cause any impact on boot time performance?
- Can the feature (service or docker) be delayed?
- What are the possible optimizations and what is the expected boot time degradation if, by the nature of the feature, additional CPU/IO costs can't be avoided?

### 11. Memory Consumption

We expect the resulting containers to be comparable (if not equal) to those produced by the old build system, both in terms of size and runtime performance and memory footprint.

### 12. Restrictions/Limitations  

We should not depend on the host system at all. This means that we must find hermetic alternatives to historically unhermetic software, such as gcc. For instance, we should never rely on gcc being installed on the system.

This means that, sometimes, we'll need to migrated dependencies to Bazel, which incurs a non-trivial cost. A large portion of these dependencies have already been migrated, and the maintenance cost is estimated to be low.

### 13. Testing Requirements/Design  

// TODO BL: I probably need Brian's help for this, since his team has been donig the validation

#### 13.1. Unit Test cases  

#### 13.2. System Test cases

### 14. Open/Action items - if any 

 // TODO BL:
