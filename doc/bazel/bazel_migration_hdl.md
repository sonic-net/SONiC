# SONiC Build System Migration #

## Table of Content 

### 1. Revision  

### 2. Scope  

This document covers the migration of the SONiC build system into a modern, Bazel-based system. It proposes an end state of the build system, as well as a migration path to get us there.

### 3. Definitions/Abbreviations 

- Bazel: A build system open-sourced by Google. It specializes in polyglot builds, and promises fast, reproducible builds through hermeticity. [Documentation](https://bazel.build/docs)
- Bazel rules, also called rulesets: Extensions to Bazel to provide additional capabilities, usually to integrate Bazel with a new programming language. Usually named `rules_<lang>`. For instance, `rules_go` extends Bazel to be able to build and test Go sources. [Documentation](https://bazel-docs-staging.netlify.app/versions/master/skylark/rules.html)
- BUILD files: Files where the Bazel build is defined. Usually named `BUILD.bazel`, and written by hand in [Starlark](TODO BL: link to docs). [Documentation](https://bazel.build/concepts/build-files)
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

#### 4.a Motivation

The current SONiC build system, while being ergonomic and accommodating the vast matrix of platforms and vendors that are required, has some shortcomings, that the community has been feeling for some time.

After two decades of SONiC development, we now have a fuller picture of what SONiC needs in a build. With this information, we believe we can build a faster, more reliable build system on top of Bazel.

Early results demonstrate that we can produce cold builds similar to those in the current system, but **sub-minute builds** for some classes of incremental changes, all while keeping hermeticity and reproducibility, so that the same build on the same commit will produce the same results a year from now.

// TODO BL: Should we include a table here?

#### 4.b Migration Overview

Bazel migrations are expensive, and famously disruptive. To alleviate this issue as much as possible, we propose a gradual rollout. We will migrate each component in turn, in a manner such that we:

- Keep compatibility with the old build system. A component built with Bazel can be depended on from a component built with Make.
- Can roll back if needed. The old build system will remain in place, even for migrated components, to ensure users can roll back quickly if there are issues.

### 5. Requirements

TODO BL: I need to read more what they expect here.

### 6. Architecture Design 

This section covers the changes that are required in the SONiC architecture. In general, it is expected that the current architecture is not changed.
This section should explain how the new feature/enhancement (module/sub-module) fits in the existing architecture. 

If this feature is a SONiC Application Extension mention which changes (if any) needed in the Application Extension infrastructure to support new feature.

### 7. High-Level Design 

This section specifies how different parts of the build will work under Bazel. Everything explained here has already been implemented in a proof of concept, in [thesayyn/sonic-buildimage](https://github.com/thesayyn/sonic-buildimage).

#### 7.a Groundwork

The Bazel ethos is that **every input to a build must be known, down to the checksum, before the build starts**. The current build system has a few instances where we cannot deterministically predict these inputs.

- Define a hermetic gcc toolchain, so that we always use the same version for every build. [Source](TODO LINK to sonic-build-infra/toolchain).
- Fetch Debian packages deterministically, instead of relying in `apt install`. We do that by using `rules_distroless` to fetch from a Debian snapshot. [Source](TODO BL: Source to code in sonic-buildimage that pulls this stuff).
- For components that have Python dependencies, we created `pyproject.toml` files to be able to generate deterministic `uv` lockfiles. [Example](TODO BL: Example for sonic-utilities).

#### 7.b Managing Patched External Dependencies

The SONiC build relies on patching several third party dependencies (e.g. [libnl3](TODO BL: link to buildimage/src/libnl3)). Furthermore, it relies on the Debian suite of tools ([debhelper](https://man7.org/linux/man-pages/man1/dh.1.html) and associated tools), which is not compatible with Bazel. Hence, another solution is required.

We propose four approaches to tackle this problem. They are detailed in [this PR to `thesayyn/sonic-buidimage`](https://github.com/thesayyn/sonic-buildimage/pull/15), but we will list their summaries here for ease of reference.

In order of most preferred to least preferred, they are:

1. Find the module we want to patch in the BCR. Please see the PR for instructions on how to patch it.
2. Pull the dependency as a Debian package with `rules_distroless`. This method does not allow patching.
3. Migrate said dependency to Bazel. The specific method will depend on the dependency, but tips and tricks have been listed in the document above.
4. Patch and build the dependency out of band, and then import the built artifacts into the Bazel build.

#### 7.c Building Component Containers

Currently, most components in SONiC are bundled into `.deb` archives before being installed in the containers to be deployed.

We propose a similar model except, instead of `.deb` archives, we will bundle the components into tar archives for ease of consumption. Using `tar.bzl` and `mtree`, we can replicate the rootfs structure of `.deb` packages:

```starlark
# Example from: https://github.com/thesayyn/sonic-buildimage/blob/master/src/sonic-sysmgr/BUILD.bazel#L4-L11
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
# Example from: https://github.com/thesayyn/sonic-buildimage/blob/master/dockers/docker-base-bookworm/BUILD.bazel#L123-L139
oci_image(
    name = "docker-base-bookworm",
    architecture = "amd64",
    entrypoint = ["/usr/bin/supervisord"],
    env = {
        "DEBIAN_FRONTEND": "noninteractive",
    },
    os = "linux",
    tars = [ # Each of these is a tar() target.
        ":rootfs",
        ":rootdirslinks",
        ":flat",
        ":site-packages",
        "@sonic_supervisord_utilities//:dist",
    ],
    visibility = ["//visibility:public"],
)
```

#### 7.d Platform & Device Support

The current SONiC build supports a rich matrix of vendors, platforms, and devices. This can be replicated with Bazel's expressive configuration language.

We define command line flags to allow users to specify which device and ASIC manufacturer they're targeting ([link](https://github.com/thesayyn/sonic-build-infra/blob/master/config/BUILD.bazel)):

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

#### 7.e Debuggability

We will implmement automatic debug container generation, mirroring the current system.

We will write a Bazel rule that will crawl the dependency tree of an image, capture the debug symbols of its binaries, and bundle them with well-known debugging tools such as `gdb` to create debug containers.

For instance, following the example in [7.d](TODO BL: LINK):

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

#### 7.f Affected Systems

##### Dependency Changes

We lose a few dependencies:
- We no longer need a sonic-slave container.
- We no longer depend on developer tools such as `gcc` and `python` being installed in the build machine.
- We no longer depend on Docker at build time.

And we gain a few dependencies:
- We depend on Google servers to download and install Bazel at build time.
- We gain a dependency on the Bazel Central Registry.

##### Changed Repositories

Every component repository will need to be migrated to Bazel. `sonic-buildimage` will also need to change, but it will be migrated piecemeal.

#### 7.g Performance Summary

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
As part of the analysis cover the flowing:

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
