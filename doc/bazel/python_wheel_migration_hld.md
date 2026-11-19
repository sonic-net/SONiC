# SONiC Python Wheel Migration

## Table of Contents

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
  - [3.a Prior Art](#3a-prior-art)
- [4. Overview](#4-overview)
  - [4.a Motivation](#4a-motivation)
  - [4.b Migration](#4b-migration)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.a Hermetic Python toolchain](#7a-hermetic-python-toolchain)
  - [7.b Component migration](#7b-component-migration)
  - [7.c Artifact equivalence verification](#7c-artifact-equivalence-verification)
  - [7.d Unit Test migration](#7d-unit-test-migration)
  - [7.e Runfiles resolution for tests](#7e-runfiles-resolution-for-tests)
  - [7.f Affected systems](#7f-affected-systems)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
- [14. Open/Action items](#14-openaction-items---if-any)

### 1. Revision

### 2. Scope

This document covers the migration of SONiC wheel components to Bazel. It covers the migration of the `.whl` artifact, the migration of the component's unit tests, and some of the problems encountered during that migration.

Please note that this design covers only the migration of individual components (defined in the next section). Migrating the full image assembly process is out of the scope of this document.

### 3. Definitions/Abbreviations

| Term | Definition |
|---|---|
| Component | An individually buildable unit of the SONiC build, declared in `rules/*.mk`. This document is concerned with components of type `SONIC_PYTHON_WHEELS`, whose artifact is a Python wheel. |
| `SONIC_PYTHON_WHEELS` | The component type whose build recipe, defined in `slave.mk`, produces a Python wheel and optionally runs its test suite as a gate. |
| Wheel (`.whl`) | The Python distribution format: a zip archive holding the package sources plus a `.dist-info` metadata directory. For a pure-Python package it contains no ELF objects. [PEP 427](https://peps.python.org/pep-0427/) |
| Hermetic | A build that depends only on explicitly declared inputs, and in particular not on tools or libraries installed on the host. |
| Bazel target / label | The unit of a Bazel build, and its unique identifier `@<repository>//<package>:<name>`. [Documentation](https://bazel.build/concepts/labels) |
| Module | A Bazel dependency unit, declared by a `MODULE.bazel` file. Each migrated component is its own module, which is why its targets are addressed as `@<component>//:<target>`. [Documentation](https://bazel.build/external/module) |
| runfiles | The directory tree Bazel materializes next to an executable target, containing everything that target declared it needs at run time. [Documentation](https://bazel.build/extending/rules#runfiles) |
| Sandbox | The per-action directory tree in which Bazel executes an action. Only declared inputs are materialized in it. [Documentation](https://bazel.build/docs/sandboxing) |
| `py_library` / `py_wheel` / `py_venv_test` | Bazel rules for, respectively, a Python source library, a wheel artifact, and a test executed inside a generated virtual environment. |
| venv | A Python virtual environment, generated per test target, with its own `site-packages`. |
| `.pth` file | A file in `site-packages` whose lines CPython's `site` module appends to `sys.path` at interpreter startup. [Documentation](https://docs.python.org/3/library/site.html) |
| Lockfile | A file pinning the exact resolved version and hash of every third-party Python dependency, making resolution reproducible. |
| Shim | A small program interposed between the test runner and the test. Here, the single Python entry point shared by all migrated pytest suites. |
| `mtree` | A textual description of a file tree — path, owner, mode, content source — used to declare the contents of a tar archive explicitly. |

#### 3.a Prior Art

Most of the wheel components have already been migrated, and a proof of concept covering `sonic-frr-mgmt-framework` has been submitted as [sonic-net/sonic-buildimage#29162](https://github.com/sonic-net/sonic-buildimage/pull/29162).

Every code excerpt quoted in Section 7 is taken from that PR at commit [`c5654a8`](https://github.com/oikox/sonic-buildimage/tree/c5654a82056b968c612af017ffa5e1126cd6b08e), whose two files are [`src/sonic-frr-mgmt-framework/BUILD.bazel`](https://github.com/oikox/sonic-buildimage/blob/c5654a82056b968c612af017ffa5e1126cd6b08e/src/sonic-frr-mgmt-framework/BUILD.bazel) and [`src/sonic-frr-mgmt-framework/MODULE.bazel`](https://github.com/oikox/sonic-buildimage/blob/c5654a82056b968c612af017ffa5e1126cd6b08e/src/sonic-frr-mgmt-framework/MODULE.bazel).

### 4. Overview

A full example of migrating a wheel component can be found in [sonic-net/sonic-buildimage#29162](https://github.com/sonic-net/sonic-buildimage/pull/29162). We will explore the different moving pieces in that PR in Section 7.

#### 4.a Motivation

Why Bazel at all is not argued here. The case for moving the SONiC build to Bazel — inputs that are declared rather than assumed, builds that are reproducible, incrementality that is correct rather than approximate, and a cache that can be reused across machines and CI runs, in place of a build whose correctness depends on the state of a slave container — has already been made in Borja Lorente's *SONiC Build System Migration* HLD ([`bazel_migration_hld.md`](./bazel_migration_hld.md), merged as sonic-net/SONiC#2396). This design takes that conclusion as given and addresses one layer of it: the Python wheel components.

What that layer costs is specific. On the Make side, both the wheel build and its test run inside the slave container — an environment where dependencies are already installed. Under Bazel, only declared inputs exist. Migration is therefore fundamentally about turning implicit, container-provided dependencies into explicit declarations.

#### 4.b Migration

Migration is per-component and purely additive: adding Bazel targets to a component does not remove or alter its Make-based build. Both paths remain functional, and each component can be migrated independently.

We propose the following order, easiest-to-verify first:

1. Pure-Python wheels with no cross-module dependencies. These contain no ELF artifacts, so equivalence can be established at the strongest level (see 7.c), which makes them the cheapest way to build confidence.
2. Wheels depending on other first-party Python packages.
3. Wheels depending on native (SWIG) bindings from other components.

A component is considered migrated when all of the following hold:

- Its `.whl` is verified equivalent to the Make-produced one (7.c).
- Its test suite collects and passes the same set of cases as the Make-side pytest run (13.1).
- No source under test, and no `setup.py`, has been modified.

Migrated targets are invoked directly through Bazel:

- `bazel build @sonic-frr-mgmt-framework//:wheel`
- `bazel test @sonic-frr-mgmt-framework//:all`

This design does not add or modify any makefile. The existing `make target/python-wheels/...` flow is untouched and continues to work exactly as before. Integration with the Make entry points, so that a migrated component can be built through `make` as it is today, is left out of the scope of this document and tracked in Section 14.

Rollout policy — whether the Bazel path becomes the default for these components, and whether it gates CI — is out of scope of this document.

### 5. Requirements

1. The `.whl` produced by Bazel MUST be equivalent to the Make-produced one, verified per 7.c.
2. The migrated suite MUST collect and pass the same set of test cases as the Make-side pytest run.
3. Migration MUST NOT modify the sources under test, nor setup.py.
4. The build MUST NOT depend on any host-installed pip, setuptools, or Python interpreter.
5. Both build systems MUST coexist; the Make path stays functional.

### 6. Architecture Design

There are no expected changes to the SONiC component architecture.

Each migrated component gains a `MODULE.bazel` and a `BUILD.bazel` declaring its sources, artifacts and dependencies.

The behavior that is common to every migrated test suite is not repeated per component. It is provided by the existing shared build-infrastructure module, `sonic-build-infra`, which each component takes as a `bazel_dep`, and consists of exactly two pieces:

- a macro, `sonic_py_pytest_test`, which declares one test target per test file (7.d.2);
- a shared Python entry point, `pytest_shim.py`, used as the `main` of every such target (7.e.2).

Defining these once means the run-time behavior every suite depends on is fixed in one place rather than copied into each component.

### 7. High-Level Design

This section specifies how different parts of the build will work under Bazel. Everything explained here has already been implemented in a proof of concept migrating `sonic-frr-mgmt-framework`, in [sonic-net/sonic-buildimage#29162](https://github.com/sonic-net/sonic-buildimage/pull/29162). The following sections will explain different parts of that PR.

> [!WARNING]
> Most wheel components have been migrated, but their unit tests do not all pass yet. Test migration has met considerably more resistance than artifact migration — `sonic-utilities`, for instance, still has a significant number of failing cases. The classes of resistance encountered are discussed in 7.d.4, and the ones still unresolved are listed in Sections 12 and 14.

#### 7.a Hermetic Python toolchain

The interpreter is fetched by the Python ruleset and pinned by version, so that no host `python3` participates in the build:

```python
python = use_extension("@rules_python//python/extensions:python.bzl", "python")
python.toolchain(
    is_default = True,
    python_version = "3.13.4",
)
```

The toolchain downloads a prebuilt standalone CPython distribution rather than consulting `/usr/bin/python3`, which is what makes the result identical from machine to machine. The pinned version MUST match the `python3` provided by the target Debian release's apt packages, because modules installed by this build share `/usr/lib/python3/dist-packages` with dpkg-managed ones.

#### 7.b Component migration

##### 7.b.1 The three Make-side steps, made explicit

The Make-side recipe for a wheel component performs three steps inside the slave container:

```
python3 setup.py bdist_wheel           # produce the .whl
pip3 install ".[testing]" && pytest    # test gate
pip3 install <wheel>                   # install into rootfs / a downstream image layer
```

Each is opaque: what it will write is known only after it has run, and it runs against whatever the container happens to provide. Under Bazel none of the three is executed. Instead their **outputs** are declared as targets, and `setup.py` is kept as the reference specification that those declarations must match:

| Make-side step | Bazel equivalent |
|---|---|
| `setup.py bdist_wheel` | `py_wheel` assembles the wheel from a declared description of its contents and metadata |
| `pytest` gate | one test target per test file (7.d) |
| `pip3 install <wheel>` | a tar archive declaring the file tree that install would lay down |

This is what makes the build hermetic — no host `pip` or `setuptools` participates. It also creates an obligation: anything `pip` used to do as a side effect must now be written down explicitly, which is the subject of 7.b.3.

##### 7.b.2 The three targets

Every migrated component exposes the same three targets, each serving a different downstream consumer.

| Target | Purpose | Downstream consumer |
|---|---|---|
| source library | The importable package sources | Other components; the component's own tests; `:wheel` and `:install` |
| `:wheel` | The distribution artifact | Equivalence verification; image layers that install a wheel |
| `:install` | The file tree `pip install` would lay down, as a tar | OCI image layers; deb packaging |

**The source library** — `:frrcfgd_lib` in this component — exposes the package so that other Bazel targets can import it:

```python
load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "frrcfgd_lib",
    srcs = glob(["frrcfgd/**/*.py"]),
    imports = ["."],
    visibility = ["//visibility:public"],
)
```

The target name is the component's own choice; what matters is the role. This component declares a second library for the same reason, because `setup.py` runs `find_packages()` and `tests/` carries an `__init__.py`, so the test sources are part of the distribution as well:

```python
py_library(
    name = "tests_lib",
    srcs = glob(["tests/*.py"]),
    imports = ["."],
)
```

`imports = ["."]` declares an **import root**: a runfiles-relative path recorded in the library's provider. The library does not apply it itself — the consuming executable does. For a venv-based test, it is applied by writing the path as a line in a `.pth` file inside the venv's `site-packages`, which CPython's `site` module appends to `sys.path` at interpreter startup. This detail matters, because it is the mechanism that breaks inside the sandbox; see 7.e.

**`:wheel`** produces the artifact. Each attribute corresponds to a field of `setup.py`, which is what makes the target reviewable against it:

```python
load("@rules_python//python:packaging.bzl", "py_wheel")

py_wheel(
    name = "wheel",
    # setup.py `name`. py_wheel normalises this to sonic_frr_mgmt_framework
    # for the .whl filename, but writes it verbatim into METADATA's Name
    # field, so it has to carry the dashes to match the Make wheel.
    distribution = "sonic-frr-mgmt-framework",
    version = "1.0",
    # setup.py `description` / `url`.
    summary = "Utility to dynamically configuration FRR based on config DB data update event",
    homepage = "https://github.com/Azure/sonic-buildimage",
    # setup.py install_requires
    requires = [
        "jinja2>=2.10",
        "netaddr==0.8.0",
        "pyyaml>=6.0.1",
    ],
    # setup.py entry_points.console_scripts
    entry_points = {
        "console_scripts": [
            "frrcfgd = frrcfgd.frrcfgd:main",
        ],
    },
    # setup.py data_files — see 7.b.3
    data_files = _DATA_FILES,
    # dist-info extras that bdist_wheel emits — see 7.b.3
    extra_distinfo_files = {
        ":top_level_txt": "top_level.txt",
    },
    deps = [
        ":frrcfgd_lib",
        ":tests_lib",
    ],
    visibility = ["//visibility:public"],
)
```

| `setup.py` | `py_wheel` attribute |
|---|---|
| `name` | `distribution` |
| `version` | `version` |
| `description` | `summary` |
| `url` | `homepage` |
| `install_requires` | `requires` |
| `classifiers` | `classifiers` |
| `entry_points.console_scripts` | `entry_points["console_scripts"]` |
| `data_files` | `data_files` |
| `packages=[...]` | collected from the `py_library` targets in `deps` |

**`:install`** declares the file tree that `pip3 install <wheel>` would produce, as a tar archive in the Debian layout. The `mtree` description gives explicit control of path, owner, mode and content source for every entry:

```python
tar(
    name = "install",
    srcs = [
        "frrcfgd/__init__.py",
        "frrcfgd/frrcfgd.py",
        ":frrcfgd_console_script",
    ] + _TEMPLATE_FILES,
    mtree = [
        "./usr/lib/python3/dist-packages/frrcfgd/__init__.py uid=0 gid=0 mode=0644 type=file content=$(location frrcfgd/__init__.py)",
        "./usr/lib/python3/dist-packages/frrcfgd/frrcfgd.py uid=0 gid=0 mode=0644 type=file content=$(location frrcfgd/frrcfgd.py)",
        "./usr/local/bin/frrcfgd uid=0 gid=0 mode=0755 type=file content=$(location :frrcfgd_console_script)",
    ] + [
        # setup.py `data_files=[('sonic/frrcfgd', [...])]` is a RELATIVE path, so
        # `pip3 install` lays it under the install prefix (/usr/local on Debian)
        # => /usr/local/sonic/frrcfgd/. docker-fpm-frr/docker_init.sh consumes it
        # via `sonic-cfggen -T /usr/local/sonic/frrcfgd`, so the templates MUST
        # land there (NOT /usr/share/sonic/frrcfgd).
        "./usr/local/sonic/frrcfgd/" + src.split("/")[-1] +
        " uid=0 gid=0 mode=0644 type=file content=$(location " + src + ")"
        for src in _TEMPLATE_FILES
    ],
    visibility = ["//visibility:public"],
)
```

Declaring the layout instead of running `pip` is what keeps this step reproducible, and it also makes the layout reviewable: the target path and mode of every installed file is visible in the BUILD file.

##### 7.b.3 Replicating pip's implicit behavior

Because `pip install` is no longer executed, the side effects it used to perform must be produced explicitly. Which ones apply is per component; for `sonic-frr-mgmt-framework` there are three.

**Console-script entry points.** When `setup.py` declares `entry_points.console_scripts`, it is `pip install` — not `bdist_wheel` — that generates the executable under `/usr/local/bin/`:

```python
#!/usr/bin/python3
import re, sys
from frrcfgd.frrcfgd import main
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
```

`py_wheel(entry_points = ...)` records the declaration in the wheel's metadata, but does not generate the script. It is therefore written out explicitly, so `:install` can place it in `/usr/local/bin/`:

```python
load("@bazel_skylib//rules:write_file.bzl", "write_file")

write_file(
    name = "frrcfgd_console_script",
    out = "frrcfgd_bin",
    content = [
        "#!/usr/bin/python3",
        "# -*- coding: utf-8 -*-",
        "import re",
        "import sys",
        "from frrcfgd.frrcfgd import main",
        "if __name__ == '__main__':",
        "    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])",
        "    sys.exit(main())",
    ],
)
```

The generated file is named `frrcfgd_bin` rather than `frrcfgd`, because the package directory of that name already occupies the label. The installed name is set by the `:install` mtree, which is where the path belongs anyway.

**`top_level.txt`.** `bdist_wheel` writes the top-level import names into `<pkg>.dist-info/top_level.txt`. This one file has to be supplied explicitly and attached through `extra_distinfo_files`:

```python
write_file(
    name = "top_level_txt",
    out = "top_level.txt",
    content = [
        "frrcfgd",
        "tests",
        "",
    ],
)
```

The content is whatever `find_packages()` returns, which for this component is two names rather than one: `tests/` carries an `__init__.py`, so setuptools treats it as a package and `bdist_wheel` lists it. Writing only `frrcfgd` here would have produced a wheel that installs correctly and still differs from the Make one. The value has to be read off the Make artifact rather than inferred from what the component appears to export.

The remaining `.dist-info` contents — `METADATA`, `WHEEL`, `RECORD`, `entry_points.txt` — are produced by `py_wheel` itself.

**`data_files`.** `setup.py` names one target directory for twenty-one template files that live in five source subdirectories:

```python
data_files = [('sonic/frrcfgd', ['templates/bgpd/bgpd.conf.j2',
                                 'templates/bfdd/bfdd.conf.j2',
                                 ...
                                 'templates/frr/frr.conf.j2'])]
```

setuptools splits this across both steps, so the migration has to as well. `bdist_wheel` copies the files into the wheel's `.data/data/` tree, flattening the nested source layout; that part is declared as `py_wheel(data_files = ...)`:

```python
_DATA_FILES = {
    src: "data/sonic/frrcfgd/" + src.split("/")[-1]
    for src in _TEMPLATE_FILES
}
```

`pip install` then unpacks that tree relative to the **install prefix**. Because the target path in `setup.py` is relative, the files land under `/usr/local/sonic/frrcfgd/` on Debian — and `docker-fpm-frr/docker_init.sh` reads them from exactly there, via `sonic-cfggen -T /usr/local/sonic/frrcfgd`. The prefix is recorded nowhere in the wheel, so it cannot be derived from the artifact; it is spelled out in the `:install` mtree instead (the `tar` excerpt in 7.b.2). A plausible-looking `/usr/share/sonic/frrcfgd/` would build, install, and pass every test, while breaking FRR configuration at runtime.

Which of these three apply to any further component is determined by reading its `setup.py`.

##### 7.b.4 Third-party dependencies

Third-party Python dependencies are resolved from a lockfile pinning version and hash, declared in the component's own `MODULE.bazel`:

```python
uv = use_extension("@aspect_rules_py//uv/unstable:extension.bzl", "uv")
uv.declare_hub(hub_name = "sonic_frr_mgmt_pip")
uv.project(
    hub_name = "sonic_frr_mgmt_pip",
    pyproject = "//bazel:pyproject.toml",
    lock = "//bazel:uv.lock",
)
use_repo(uv, "sonic_frr_mgmt_pip")
```

The `pyproject.toml` referenced here exists solely to feed dependency resolution. It does not replace `setup.py`, which remains the reference specification for the wheel's own metadata; keeping them separate means the migration adds a file rather than editing one, satisfying requirement 3.

A target is generated for each locked top-level package, consumed as `@<hub>//<dep>`:

```python
py_library(
    name = "pytest_lib",
    testonly = True,
    deps = [
        ":frrcfgd_lib",
        ":tests_lib",
        # frrcfgd.py imports netaddr at module level (setup.py install_requires).
        "@sonic_frr_mgmt_pip//netaddr",
        "@sonic_frr_mgmt_pip//pytest",
    ],
)
```

Note that this declares third-party dependencies **per component**. Whether resolution should instead be centralized for the whole repository is an open question, and the same question applies to the apt extension used by native components; both are raised in Section 14.

#### 7.c Artifact equivalence verification

The migration is only credible if the Bazel-built wheel can be shown to be equivalent to the Make-built one. For wheels a stronger claim is available than for binary packages:

> A pure-Python wheel contains no ELF objects. The usual sources of build-time non-determinism — embedded absolute paths, timestamps, build IDs, toolchain identifiers — are properties of compiled objects and therefore do not arise. Wheels can consequently be held to a content-level bar rather than a filename-level one.

The check has three parts, performed against the Make artifact under `target/python-wheels/<release>/`:

1. **Tree structure.** `unzip -l` on both wheels; compare the full entry list, including the `.dist-info` directory, and the recorded permissions.
2. **Content.** Every text file must be byte-identical. This covers the package sources, the generated console-script shims, and `top_level.txt`.
3. **Metadata.** `METADATA` and `entry_points.txt` must agree field by field with the values declared in `setup.py`.

Part 2 is what would not be available for a component containing compiled objects, and it is the reason pure-Python wheels are proposed as the first migration step in 4.b.

#### 7.d Unit Test migration

##### 7.d.1 What the Make side does

In the wheel recipe, the test is a gate in front of the wheel build:

```makefile
if [ ! "$($*_TEST)" = "n" ] && [ ! "$(BUILD_SKIP_TEST)" = "y" ]; then \
    pip$($*_PYTHON_VERSION) install ".[testing]" && \
    pip$($*_PYTHON_VERSION) uninstall --yes "$$NAME" && \
    timeout ... python$($*_PYTHON_VERSION) -m pytest; \
fi
```

Three actions, each with a meaning the Bazel side must preserve:

- `pip install ".[testing]"` installs the package, its runtime dependencies and its test dependencies.
- `pip uninstall <self>` removes only the package body while keeping the dependencies, so pytest exercises the **source tree** rather than an installed copy.
- `python3 -m pytest` decides, by its exit code, whether the wheel build proceeds.

The environment those actions operate on is the slave container, and nothing about it is declared.

##### 7.d.2 One target per test file

Rather than one target running the whole suite, each test file becomes its own test target. The suite itself is unchanged — the same files, collected the same way — but Bazel can then run them concurrently, cache the ones whose inputs have not changed, and attribute a failure to a single target.

The per-target boilerplate is factored into one macro, so a component declares only what differs per file:

```python
_SHIM = Label("//python:pytest_shim.py")

def sonic_py_pytest_test(name, test_file, venv, deps,
                         pytest_args = [], size = "small", data = [], **kwargs):
    py_venv_test(
        name = name,
        size = size,                      # replaces Make's timeout $(BUILD_PROCESS_TIMEOUT)
        srcs = [_SHIM],
        main = _SHIM,
        # argv[1]: the test file's runfiles-relative path, resolved by the shim
        args = ["$(rlocationpath %s)" % test_file] + pytest_args,
        data = [test_file] + data,
        venv = venv,
        deps = deps,
        **kwargs
    )
```

A component then declares its suite as a list comprehension:

```python
[sonic_py_pytest_test(
    name = f[:-len(".py")],
    test_file = "tests/" + f,
    # venv name from bazel/pyproject.toml [project].name.
    venv = "sonic-frr-mgmt-framework",
    deps = [":pytest_lib"],
) for f in _TEST_FILES]
```

Note that `srcs` and `main` are always the same shared shim, with the test file passed as data plus an argument. The shim is discussed in 7.e.

##### 7.d.3 Making the environment explicit

This is the substance of the migration: everything the slave container provided implicitly becomes a declared dependency of the test library.

| Make-side provider | Mechanism on the Make side | Bazel declaration |
|---|---|---|
| `$(PKG)_DEPENDS` | dependency wheels `pip install`ed in the container | `@<module>//:<library>` |
| `$(PKG)_DEBS_DEPENDS` | dependency debs `dpkg -i`ed in the container, including SWIG bindings | `@<module>//<package>:<name>` |
| `install_requires` / `tests_require` | `pip install ".[testing]"` | locked third-party targets, `@<hub>//<dep>` |
| the package under test | left in place by `pip uninstall <self>` | `:frrcfgd_lib` |

The last row is worth calling out: depending on the source library rather than `:wheel` is what reproduces the intent of `pip uninstall <self>` — the tests exercise the sources, not a built and installed copy.

This table is the mechanical part of migrating any further component: read its `rules/<component>.mk` and its `setup.py`, and translate each entry.

##### 7.d.4 Classes of resistance encountered

Artifact migration is largely mechanical; test migration is not. The resistance falls into a small number of classes, and it is worth naming them because they determine how much work a given component's suite will be.

1. **Run-time dependency lookup.** A dependency can be correctly declared and physically present in runfiles and still not be found, because the mechanism that locates it at run time does not know about the runfiles tree. This affects every suite with a cross-module dependency and is the subject of 7.e.
2. **Working-directory assumptions.** Make runs pytest from the component directory, so suites commonly open fixtures by a path relative to it. A Bazel test starts at the runfiles root instead, so the working directory has to be established before collection.
3. **External services.** Suites that require a live service such as Redis are excluded from this design entirely.
4. **State shared across files.** Splitting one pytest process into one process per file removes any state a suite implicitly shared between files.

Classes 1 and 2 are addressed by the shared shim and are therefore solved once for all components. Classes 3 and 4 are per-component and are the reason some suites — `sonic-utilities` most notably — do not pass yet. The remaining work is tracked in Sections 12 and 14.

#### 7.e Runfiles resolution for tests

##### 7.e.1 The constraint

A Bazel test does not run in the source tree. It runs with its working directory inside its **runfiles** tree, which Bazel materializes from exactly what the target declared. The tree is one flat top-level directory per repository, named by that repository's canonical name:

```
test_config.runfiles/
├── MANIFEST
├── _main/                                              ← files contributed by the main repo
├── sonic-frr-mgmt-framework+/                          ← the package under test, and its tests
│   ├── frrcfgd/
│   ├── tests/
│   └── .test_config -> <output tree>/.test_config      ← the venv, symlinked out of the tree
├── sonic-build-infra+/                                 ← the shared pytest shim
├── rules_python++python+python_3_13_4_.../             ← the hermetic interpreter
└── aspect_rules_py++uv+whl_install__...__pytest__9_1_1/  ← third-party packages, one each
```

The layout exists so that run-time lookup has one uniform rule: whatever a program looks for, the path is `<repository>/<path-within-package>`.

The consequence is that **any mechanism which locates dependencies at run time must be taught about this tree**. A dependency being correctly declared is not sufficient; something has to translate that declaration into the form the lookup mechanism understands. For Python, that mechanism is `sys.path`.

##### 7.e.2 Why a shared shim

Two independent reasons converge on a single shared entry point for every migrated suite:

- The Make-side entry is a shell command, `python3 -m pytest`. A Bazel Python test rule requires a `main` `.py` instead, so an entry point must exist regardless.
- The repair described below has to happen before pytest imports anything. Putting it in one shared file defines it once for the whole repository rather than copying it into every component.

The shim's essential structure is an ordering constraint:

```python
if __name__ == "__main__":
    runfiles_root = _runfiles_root()      # from the test runner's environment
    _replay_aspect_pth(runfiles_root)     # must run before `import pytest`

    import pytest
    rc = pytest.main([..., test_path] + sys.argv[2:])
    ...
```

The repair must precede `import pytest`, because pytest's plugin discovery walks `sys.path` as it stands at import time.

##### 7.e.3 How first-party dependencies reach `sys.path`

A venv-based test resolves its two classes of dependency differently:

| Dependency class | How it enters the environment |
|---|---|
| third-party packages | materialized into the venv's `site-packages` |
| first-party `py_library`, including cross-module | **not copied**; one line per import root written into a `.pth` file in `site-packages` |

The `.pth` mechanism has one property that matters here: `site` appends each line to `sys.path`, resolving relative paths against the `.pth` file's own directory, and **silently skips any line naming a directory that does not exist** — no warning, no log.

##### 7.e.4 The failure

The generated `.pth` file states in its own header that its entries are relative paths within the runfiles tree:

```
# Generated by Aspect py_binary
# Contains relative import paths to non site-package trees within the .runfiles
../../../../../../../sonic-frr-mgmt-framework+/
../../../../../../../_main/
../../../../../../../aspect_rules_py++uv+project__sonic_frr_mgmt_framework/
```

But the venv's `site-packages` sits five levels below the runfiles root, while every entry ascends seven:

```
<runfiles>/ sonic-frr-mgmt-framework+ / .test_config / lib / python3.13 / site-packages
            └────────── 1 ────────┘ └───── 2 ────┘ └ 3 ┘ └── 4 ──┘ └──── 5 ────┘

5 × ..  ->  <runfiles>                  ← the anchor the header declares
7 × ..  ->  <config>/bin/external/      ← where the entries actually resolve
```

The significant point is not the two extra levels but the destination: the entries land in the **output tree**, a different tree with a different layout. It contains only repositories that have produced build outputs, and inside the sandbox only the test's own outputs. Meanwhile each of those three directories is present, correctly, under the runfiles root.

Combined with the silent-skip property, `site` contributes nothing at all: every import root the component declared is dropped, with no diagnostic.

##### 7.e.5 When the breakage is fatal

The dropped entries are not always missed, and the distinction is worth stating precisely, because it decides which components this blocks.

pytest supplies one import root of its own. Under its default `prepend` import mode it walks up from the test file past every directory holding an `__init__.py` and inserts the first one that does not. For this component that is `<runfiles>/sonic-frr-mgmt-framework+/` — `tests/` carries an `__init__.py`, so the walk does not stop there — which is exactly the first of the dropped `.pth` entries. The component's own sources therefore stay importable, and this suite passes with the repair below disabled: verified by removing the call and re-running, 17 cases across 2 targets, still green.

What pytest cannot supply is any *other* module's import root. A component whose tests import a `py_library` from a different Bazel module has that root only in the `.pth` file — `sonic-py-common`, whose tests reach the `swsscommon` binding built by another module, is one. When `site` drops that line nothing puts it back, and the test fails with `ModuleNotFoundError` for a dependency that is both correctly declared and physically present in its own runfiles.

The condition is therefore: **silent for a component whose tests import only its own sources, fatal for one that depends on another module.** It is a property of the venv layout rather than of any component, which is why it is repaired once in the shared shim instead of being waited for.

##### 7.e.6 The repair

By the time the test's own code runs, `site` has already discarded those lines, so the file is re-read in the shim and each line re-anchored before being appended to `sys.path`:

```python
rel = line.lstrip("./")                    # drop the entire ../ prefix chain
cand = os.path.join(runfiles_root, rel)    # re-anchor at the runfiles root
if os.path.isdir(cand) and cand not in sys.path:
    sys.path.append(cand)
```

The prefix chain is discarded entirely rather than corrected from seven levels to five. Correcting the count would only hold at the current venv depth and would need revisiting whenever that layout changed. Discarding it reduces each line to a repository-relative identity — `sonic-frr-mgmt-framework+` — which is then resolved against the authoritative runfiles root. That is exactly the lookup contract the runfiles tree is designed around (7.e.1).

Two properties make this safe to carry:

- It appends only directories that exist, so it cannot mask a genuinely missing dependency.
- It is additive. Where the dropped entries were going to be recovered anyway it changes nothing, which is what the disabled-repair run in 7.e.5 demonstrates. If the upstream anchor calculation is corrected, every entry will already be on `sys.path` and this code becomes a no-op for every component, at which point it can be removed (Section 14).

The same class of breakage — a declared dependency the run-time lookup mechanism cannot find inside runfiles — also affects native test suites, where the mechanism is the OS dynamic loader rather than `sys.path`. That case is out of scope here and noted in Section 14.

#### 7.f Affected systems

`sonic-buildimage`: new `BUILD.bazel` / `MODULE.bazel` files under `src/<component>`. No makefile, no source under test, and no `setup.py` is modified. No runtime component, container, or image is affected by this design.

### 8. SAI API

There are no changes to the SAI API.

### 9. Configuration and management

There are no changes to the configuration.

### 10. Warmboot and Fastboot Design Impact

This design doesn't impact warmboot.

### 11. Memory Consumption

There is no impact on memory consumption. This design changes how artifacts are built and tested, not what they contain or how they execute at run time.

### 12. Restrictions/Limitations

Because no makefile is modified, the Bazel-built artifacts and the migrated test suites are not reachable from the existing make targets. Consequently they are not exercised by the current CI jobs, and the equivalence checks described in 7.c MUST be run explicitly.

The following limitations also apply:

- **Not all migrated suites pass yet.** Artifact migration is complete for most wheel components, but test migration is not; `sonic-utilities` is the most significant outstanding case. The classes of cause are enumerated in 7.d.4.
- **Per-file test targets do not share process state.** A suite relying on ordering across files, or on state established by an earlier file, will not behave as it does under a single pytest invocation.
- **The `.pth` re-anchoring in 7.e.6 is a workaround** for an anchor calculation in an upstream ruleset. It is additive and degrades to a no-op once that is corrected, but until then it is a dependency on behavior this design does not own.

### 13. Testing Requirements/Design

The subject of this design is the build and test path itself, so what is required is a demonstration of equivalence with the Make-based path rather than new functional tests. No new SONiC functional, system or warmboot/fastboot test is required, and no existing one is affected.

#### 13.1. Unit Test cases

The migrated suite is the existing suite: the same test files, unmodified, run by pytest. Equivalence is established per component against the Make baseline:

1. Capture the Make-side result for the component from its wheel build log.
2. Run `bazel test @<component>//:all`.
3. Compare the set of collected test cases and the number that pass. Both must agree.

For `sonic-frr-mgmt-framework` the two sides agree: the Make-side wheel build log reports `collected 17 items` and `17 passed`, and `bazel test @sonic-frr-mgmt-framework//...` reports the same 17 cases, split across the two test targets, all passing.

#### 13.2. System Test cases

Equivalence between the Bazel-built and Make-built wheel is verified per 7.c. At present this is run manually per component.

### 14. Open/Action items - if any

1. **Centralized or per-component third-party dependency declaration.** Each component currently declares its own Python dependencies through a uv extension with its own lockfile. The alternative is a single repository-wide resolution. Per-component locking isolates version conflicts between components and keeps each lockfile auditable against that component's `setup.py`; centralized resolution gives one source of truth and one place to update. The same question applies to the apt extension used by native components, and it is worth settling both together, since the answer affects every component migrated hereafter.
2. **CI integration.** Migrated targets are invoked directly via `bazel build` / `bazel test`, so they are invisible to the existing CI jobs and the unit tests have to be run manually. Two levels of integration are possible: a dedicated CI job running `bazel test` for the migrated components, which requires no makefile change and would give signal immediately; or wiring Bazel targets behind the existing `make target/...` entry points so the user-facing interface is unchanged. We lean towards the first as an immediate step, and propose that the second be aligned with whatever Make/Bazel interoperability mechanism the project adopts rather than solved per component here.
3. **Remaining test suites.** The suites that do not pass yet (7.d.4, Section 12) need to be worked through per component. The per-component causes should be enumerated so that the remaining effort can be estimated.
4. **Upstream `.pth` anchor calculation.** The repair in 7.e.6 compensates for behavior in an upstream ruleset. It should be reported upstream, tracked, and removed once fixed; the condition for removal is unambiguous, namely that the repair appends nothing because every entry already resolves.
5. **Native test suites.** The same class of run-time lookup breakage affects gtest suites, where the mechanism is the OS dynamic loader rather than `sys.path`. It requires a different bridge and is proposed as a follow-up document.
