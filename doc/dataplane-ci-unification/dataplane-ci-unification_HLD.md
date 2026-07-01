# Unifying CI infrastructure for sonic-swss, sonic-swss-common, sonic-sairedis

### Revision

| Rev | Rev Date | Author(s) | Change Description |
|:---:|:--------:|:---------:|--------------------|
| 1.0 | 2026/06/09 | Lawrence Lee | Initial version |


## Table of Contents

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [1. TL;DR](#1-tldr)
- [2. Background](#2-background)
  * [2.1 The three-repo group](#21-the-three-repo-group)
  * [2.2 How CI is structured today](#22-how-ci-is-structured-today)
  * [2.3 What the pipelines share today](#23-what-the-pipelines-share-today)
- [3. Problems](#3-problems)
- [4. Goals](#4-goals)
- [5. Proposed solution](#5-proposed-solution)
  * [5.1 Single source of truth for build steps](#51-single-source-of-truth-for-build-steps)
  * [5.2 Dependency inheritance](#52-dependency-inheritance)
- [6. Detailed design](#6-detailed-design)
  * [6.1 Per-repo `build-env/`](#61-per-repo-build-env)
  * [6.2 Per-repo `build-template.yaml`](#62-per-repo-build-templateyaml)
  * [6.3 Inherited dependency model](#63-inherited-dependency-model)
  * [6.4 `buildenv_setup` package hosted in sonic-dataplane-buildenv (NEW repo, narrow scope)](#64-buildenv_setup-package-hosted-in-sonic-dataplane-buildenv-new-repo-narrow-scope)
  * [6.5 Single setup mechanism — `buildenv_setup`](#65-single-setup-mechanism--buildenv_setup)
  * [6.6 Same-pipeline-run support](#66-same-pipeline-run-support)
  * [6.7 sonic-swss owns the entire VS test stack](#67-sonic-swss-owns-the-entire-vs-test-stack)
  * [6.8 Pre-merge CI for shared-infra changes](#68-pre-merge-ci-for-shared-infra-changes)
- [7. Migration plan](#7-migration-plan)
- [8. Risks](#8-risks)


### Definitions/Abbreviations

| Term | Definition |
|------|------------|
| AZP | Azure Pipelines - provider used to run CI checks for SONiC repos |
| CI | Continuous integration - checks/tests that are used to validate source code |
| Downstream repository | any repo which comes later in the dependency chain for a given repository, e.g. sonic-swss is downstream of sonic-sairedis, which is downstream of sonic-swss-common |
| DVS | Docker Virtual Switch - a containerized SONiC virtual switch (the `docker-sonic-vs` image) that VS tests run against |
| Upstream repository | Any repo which comes earlier in the dependency chain for a given repository, e.g. sonic-swss-common is upstream of sonic-sairedis, which is upstream of sonic-swss |
| VS test | Virtual switch test - tests which live in sonic-swss and are run against a DVS image |


### Scope

This proposal outlines CI infrastructure changes for sonic-swss, sonic-sairedis, and sonic-swss-common. It does not include any changes to the sonic-buildimage build system, production SONiC code, or existing test code.


## 1. TL;DR

The existing Azure DevOps CI pipelines for sonic-swss, sonic-swss-common, and sonic-sairedis contain several repo-specific copies of the same file (many of which have drifted apart over time). These three repos also manage their build dependencies separately, even though there is significant overlap/inheritance of dependencies. There is also no convenient way to setup a local development environment that matches the CI environment, making it harder to debug any build/test issue caught by CI. This document proposes consolidating shared CI infrastructure (with a new dedicated repository, `sonic-dataplane-buildenv`, hosting a shared environment-setup utility and sonic-swss owning the entire VS test stack) to remove redundancy and establish a single source of truth for building each component.


## 2. Background

### 2.1 The three-repo group

The SONiC core dataplane components comprise of sonic-swss, sonic-sairedis, and sonic-swss-common. sonic-swss-common is a foundational library used by many SONiC components. sonic-sairedis provides the mechanism to interact with the SAI API layer, and is dependent on sonic-swss-common. sonic-swss contains the orchestration layer which actually makes SAI API calls, and is dependent on both sonic-sairedis and sonic-swss-common. These three repositories are tightly coupled - a change in sonic-swss-common could potentially break sonic-sairedis or sonic-swss. As a result, CI checks for one repo need to verify that any proposed changes/PR are compatible with the other two repos.

### 2.2 How CI is structured today

Currently, each repo owns its entire CI pipeline end-to-end. This causes significant redundancy since each repo must also build all downstream repos, e.g. the CI pipeline for sonic-swss-common must first build sonic-swss-common, then build sonic-sairedis and sonic-swss on top and run VS tests. sonic-swss-common has its own set of steps/pipeline definitions to build sonic-sairedis and sonic-swss as well as to run the VS test suite. sonic-swss-common is also solely responsible for performing environment setup for all of these steps. Similarly, sonic-sairedis has its own pipeline definition/steps to build sonic-swss and run the VS tests, and also independently manages dependencies/setup for the CI environment.

### 2.3 What the pipelines share today

| Concern | # of copies | Notes |
|---------|:-----------:|-------|
| `docker-sonic-vs/Dockerfile` + `start.sh` (the integration-test image build context) | 3 | Drifted `dpkg --purge` lists (e.g., sonic-swss-common is missing `framework` from its purge list, leaving stale `framework` installed); drifted vpp install block; drifted debug-package install; sonic-sairedis has extra `cat /etc/apt/sources.list` debug instrumentation not in the others. |
| `build-docker-sonic-vs-template.yaml` (Azure Pipelines template that builds the docker-sonic-vs image) | 3 | ~180 LOC; drifted parameter names, drifted artifact-download invocations, drifted DEB install ordering. |
| `test-docker-sonic-vs-template.yaml` (Azure Pipelines template that runs VS tests against a docker-sonic-vs image) | 3 | ~220 LOC; drifted parallelism mechanisms (sonic-swss uses GNU `parallel`, the others use `xargs -P`); drifted retry counts; drifted env vars (sonic-swss-common is missing `DEFAULT_CONTAINER_REGISTRY=publicmirror.azurecr.io/`, which is set in the other two). |
| `build_and_install_module.sh` (team_handler kernel module install script, invoked during the Test stage) | 3 | sonic-swss's version handles multiple kernel source package layouts; sonic-sairedis's and sonic-swss-common's are behind on this. |
| Cross-repo build templates — `build-swss-template.yaml` (sonic-sairedis + sonic-swss-common), `build-sairedis-template.yaml` (sonic-swss-common) | 3 files total | Each is a forked re-implementation of the downstream repo's own `build-template.yaml`. ~160 LOC of drift across them; when sonic-swss adds a new dependency, sonic-swss-common's `BuildSwss` stage breaks because its forked template doesn't know about it. |
| Inline `apt-get install` blocks in each repo's `build-template.yaml` (host-side deps installed before invoking the build) | 3 sets | ~9 packages duplicated across all 3 (`libhiredis-dev`, `swig`, `libnl-*-dev`, `libzmq3-dev`, `redis-server`, etc.); a few more duplicated across 2 of the 3 (`dotnet-sdk-8.0`); package lists drift over time as deps are added/removed in only one repo. |
| Inline `pip3 install` invocations in each repo's `build-template.yaml` and `test-docker-sonic-vs-template.yaml` | spread across all 3 | Test framework packages (`pytest`, `flaky`, `exabgp`, `docker`) duplicated; sonic-swss has `lcov_cobertura`; sonic-swss-common has `Pympler`; libyang pip install workaround duplicated across all three test templates. |
| Inline upstream-DEB download blocks (`DownloadPipelineArtifact@2` + `dpkg -i`) for each repo's CI to pull in its upstream's just-built DEBs | spread across all 3 | Each repo independently hardcodes which upstream Azure DevOps pipelines / artifact names / DEB filename patterns to fetch; e.g., sonic-sairedis duplicates sonic-swss-common's common-libs download logic that sonic-swss-common itself also uses. |


## 3. Problems

1. Build/dependency changes do not automatically propagate - separate PRs are needed for each affected repo which are extra painful when speed is needed (e.g. when approaching branch cut deadlines). E.g. if the name of an artifact required by sonic-sairedis changes, separate PRs to update the artifact name are required for both sonic-sairedis and sonic-swss (since it's dependent on sonic-sairedis).
2. Multiple copies of the same step drift over time - changes made in one repo will remain isolated to that repo by default which can mask failures for downstream CI. E.g. a PR in sonic-swss-common may introduce a breaking dependency change, and will update the sonic-swss-common CI pipeline to account for this; however, sonic-sairedis and sonic-swss have separate CI pipeline definitions and will break once the swss-common change is merged.
3. No easy way to stand up a local dev environment that matches the CI environment. Increases friction for debugging build or test failures, discourages use of C++ unit tests which are faster and often less flaky than VS tests

## 4. Goals

1. Single source of truth per repo for "how to build me." This includes environment setup, dependencies, and build commands.
2. Zero duplication of shared CI concerns across the three repos.
3. Portable local build environment per repo that maintains parity to CI.


## 5. Proposed solution

### 5.1 Single source of truth for build steps
Each of sonic-swss-common, sonic-sairedis, and sonic-swss will maintain their own `build-template.yaml` file which serves as the canonical CI build recipe for that repo. When one repo needs to build another repo as part of its CI pipeline, it will use the `build-template.yaml` from the other repo rather than maintaing its own copy of build steps, e.g. when sonic-sairedis CI builds sonic-swss, it will directly use the build template from sonic-swss.

### 5.2 Dependency inheritance
A given repository should automatically inherit the build dependencies of all of its upstream repos, e.g. sonic-sairedis should automatically install all dependencies of sonic-swss-common; similarly, sonic-swss should automatically install all dependencies of sonic-sairedis (which includes sonic-swss-common dependencies):
- In each of sonic-swss-common, sonic-sairedis, and sonic-swss, create a new `build-env/` folder which will contain the following:
  - Required upstream repositories/artifacts
  - Dependencies that need to be installed from `apt` or `pip` which are not already acquired from upstream repositories
  - A script to run the build commands for the repo
  - Files to setup a local development environment 
- Create a new environment setup utility in a new repository `sonic-dataplane-buildenv`. This utility will recursively parse the dependencies listed in each repo's `build-env/` directory and install them as required. 

## 6. Detailed design

### 6.1 Per-repo `build-env/`

Layout:
```
<repo>/build-env/
├── README.md
├── build.sh
├── Dockerfile               # local dev only
├── compose.yaml             # local dev only
├── upstream-artifacts.yaml
└── packages/
    ├── base.yaml
    ├── tooling.yaml
    └── test.yaml            # ONLY in sonic-swss
```

Each repository will have a build-env/ directory which will hold information relevant to that repo's build process:
- `build.sh` will run the commands used by CI to build this repo
- `upstream-artifacts.yaml` contains information about artifacts that need to be downloaded from other AZP builds, e.g. in sonic-swss this file will indicate that artifacts from sonic-sairedis are needed.
- `packages/` contains information on dependencies that will be installed from a package manager (either `apt` or `pip`)
  - `base.yaml` contains build dependency information and will cascade to any downstream repos. E.g. since sonic-sairedis is dependent on sonic-swss-common, all dependencies in sonic-swss-common's `base.yaml` file will be inherited by sonic-sairedis
  - `tooling.yaml` contains dependencies that are specific to a repository and will NOT cascade.
  - `test.yaml` exists in sonic-swss only and contains dependencies needed for VS test runs

This directory also contains files to help setup a local development environment:
- `Dockerfile` will be a skeleton that is used to setup a local docker-based development environment and will invoke the shared dependency installation mechanism 
- `compose.yaml` will be used in conjuction with the Dockerfile for local environment setup

### 6.2 Per-repo `build-template.yaml`

Each repo will contain a single `build-template.yaml` which serves as the single source of truth for how to build that specific repo. When an upstream repo needs to build a downstream repo, it will refer to the downstream repo's `build-template.yaml` instead of needing to maintain its own copy of the build steps. 

### 6.3 Inherited dependency model

A major pain point of the existing CI model is that each repository's CI independently decides what dependencies are installed. To resolve this, each repo will have all of its dependencies inherited by downstream repos. Each repo can also declare additional dependencies that are specific to that repo. This means that the list of explicitly declared dependencies in each repo will be much shorter. The following files will be used for dependency management:

| File | Lives in | Cascades? | Purpose |
|------|----------|-----------|---------|
| `packages/base.yaml` | all 3 | yes | contains all `apt` and `pip` packages needed to setup the build environment for a repo, as well as any post-installation scripts that need to be run to properly configure the packages |
| `packages/tooling.yaml` | all 3 | no | non-build dependency packages needed only in a specific repo |
| `packages/test.yaml` | swss only | N/A | packages required for VS tests |
| `upstream-artifacts.yaml` | all 3 | yes | set of artifacts to download from other build pipelines; also the entrypoint for dependency cascading |

`upstream-artifacts.yaml` in each repo is used to declare which artifacts/pipelines need to be downloaded for the repo's build environment. This is also how the upstream/downstream relationship is declared. If an artifact listed in this file provides its own `build-env/` dependency files, those dependencies are inherited and that artifact's `upstream-artifacts.yaml` is recursively parsed.

As a concrete example, `upstream-artifact.yaml` in sonic-sairedis will list sonic-swss-common artifacts as a dependency. During the environment setup process, the swss-common artifacts are downloaded. As part of this proposal, these artifacts will now include a `build-env/` folder which declares dependencies for specific swss-common version that was used to build the artifact. The dependencies from the swss-common artifact's `base.yaml` will now be installed. Then the swss-common artifact's `upstream-artifacts.yaml` will be parsed, and those upstream artifacts will be downloaded and the entire process is repeated.


Example `packages/base.yaml`:
```yaml
packages:
  - libhiredis-dev
  - { name: libnl-3-dev, when: { arch: { not: amd64 } } }
  - { name: pyyaml, type: pip }
  - redis-server
post_install:                                # env-config commands run after package install
  - name: configure-redis-for-tests          # cascades from base.yaml to downstream repos
    source: configure-redis-for-tests.sh     # lives in same repo's build-env/ alongside base.yaml;
                                             # cascade picks it up via the upstream bundle's build-env/
    requires: [redis-server]                 # ordering: redis-server installed first
    scopes: [build, test]                    # apply during both Build setup AND Test setup
                                             # (default scopes if omitted: [build])
```

Example `upstream-artifacts.yaml`:
```yaml
upstream:
  # Build-scoped entry (default — scopes: [build] if omitted)
  - name: sonic-swss-common
    pipeline: Azure.sonic-swss-common
    artifact_name: sonic-swss-common-{debian_version}
    debs:
      - libswsscommon_1.0.0_{arch}.deb
      - { path: python3-swsscommon_1.0.0_{arch}.deb, scopes: [build, test] }  # per-DEB refinement

  # Test-scoped entry: same pipeline, different artifact (Ubuntu 22.04 build of sw-common)
  # — needed because the Test stage runs on a different host OS than the Build stage
  - name: sonic-swss-common-test-host
    pipeline: Azure.sonic-swss-common
    artifact_name: sonic-swss-common.amd64.ubuntu22_04
    scopes: [test]
    debs:
      - libswsscommon_*.deb
      - python3-swsscommon_*.deb

  # Test-only NEW upstream (no Build-stage equivalent)
  - name: sonic-buildimage-ubuntu22-04
    pipeline: sonic-net.sonic-buildimage-ubuntu22.04
    artifact_name: sonic-buildimage.amd64.ubuntu22_04
    scopes: [test]
    debs:
      - libprotobuf*.deb
```

### 6.4 `buildenv_setup` package hosted in sonic-dataplane-buildenv (NEW repo, narrow scope)

A new `buildenv_setup` package will be created and live in a new `sonic-dataplane-buildenv` repository. This package will be responsible for executing the actual build environment setup steps (including dependency inheritance). It will be responsible for calculating required dependencies based on explicitly declared + inherited dependencies for each repository, actually downloading and installing the dependencies, and performing any post-install actions that may be required.

This package lives in a new, dedicated repository rather than inside one of the existing repos for a few reasons: its scope is shared, generic infrastructure that does not belong to any single repo; a separate repo gives it an independent CI lifecycle (a change to `buildenv_setup` is validated by the comprehensive gate described in §6.8 instead of running inside a particular repo's pipeline); and it makes cross-team ownership and review explicit. Since the `buildenv_setup` package is meant to be shared/generic infrastructure, it will NOT have separate release branches — it lives only on `master`. All branch-specific concerns (e.g. a release branch pinning an older dependency version) are instead handled in each repo's `build-env/` files, which ARE branched.

### 6.5 Single setup mechanism — `buildenv_setup`

By moving all environment setup steps to the new `buildenv_setup` utility, we can easily setup local development environments. Sample invocations of the utility for both CI runs and local dev setup are shown below. Using `buildenv_setup` as a common entry point for both scenarios ensures parity between CI and local dev environments which will make it easier to debug and resolve any issues caught by the CI pipeline.

CI invocation (inside `container: sonic-slave-*`):
```bash
git clone --depth 1 https://github.com/sonic-net/sonic-dataplane-buildenv /tmp/dataplane-buildenv
cd /tmp/dataplane-buildenv && python3 -m buildenv_setup --repo-dir $(pwd) --scope build
```

Local-dev invocation (in `build-env/Dockerfile`):
```dockerfile
FROM sonic-slave-${DEBIAN_VERSION}:latest
RUN git clone --depth 1 https://github.com/sonic-net/sonic-dataplane-buildenv /tmp/dataplane-buildenv
COPY . /workspace
RUN cd /tmp/dataplane-buildenv && python3 -m buildenv_setup --repo-dir /workspace --scope build
```

### 6.6 Same-pipeline-run support

Some CI pipelines need to re-use artifacts from earlier stages in the run, e.g. for a PR made in sonic-sairedis, the sonic-sairedis pipeline must build the sairedis packages, then re-use the newly built sairedis when building swss. This is done to ensure that the changes made in the PR do not break downstream repos (e.g. ensure that sonic-sairedis changes do not cause issues in sonic-swss). By default, `buildenv_setup` downloads each upstream artifact from the latest successful AZP run. To support same-pipeline reuse, `buildenv_setup` accepts an `--upstream-staged-dir` flag pointing at a directory of artifacts that were already produced earlier in the current run; for any upstream found there it uses that staged copy, and for the rest it falls back to the default download. The shared build/test templates expose this through a `staged_upstreams` parameter — the calling stage lists which upstreams should come from the current run, and the template downloads them and points `buildenv_setup` at the staged directory. This keeps the staging logic inside the shared templates rather than scattered across each repo's pipeline.

### 6.7 sonic-swss owns the entire VS test stack

All three repos (sonic-swss-common, sonic-sairedis, and sonic-swss) rely on VS tests as part of their PR validation pipeline. However, since these VS tests live entirely within sonic-swss, all of the related infra/setup files will stay within sonic-swss rather than moving to the new repo. This includes the AZP templates to build the DVS image and run the tests, setup scripts that are run before the tests, and files related to the DVS image construction. sonic-sairedis and sonic-swss-common consume this stack by referencing the swss-owned templates directly (via `@sonic_swss` template references) from their own BuildDocker and Test stages, so the VS test stack has a single source of truth even though all three repos run it.

### 6.8 Pre-merge CI for shared-infra changes

Since the new `sonic-dataplane-buildenv` repo will be depended on by multiple repos, it's critical that we avoid breaking changes getting merged. To ensure this, the `sonic-dataplane-buildenv` PR checks will include building all three repos for all supported Debian version and architecture combinations, as well as running VS tests which should cover the entire CI pipeline for all three repos. Running all combinations will be expensive, but changes to `sonic-dataplane-buildenv` are expected infrequently and a breaking change slipping through would be quite costly/disruptive which justifies the added overhead.

## 7. Migration plan

The migration is **incremental and non-breaking**. Rather than a single large cutover, the changes land as a sequence of small PRs, each of which keeps every affected repo's CI green after merge and is revertable in isolation. Work proceeds **stage-by-stage in dependency order**: each repo's CI is a set of independent Azure Pipelines stages (Build, BuildDocker, Test, and the cross-repo build stages), so we can move one `(repo, stage)` combination at a time instead of rewriting a whole pipeline at once.

Guiding principles:
- **Always green:** every PR leaves the target repo's CI passing; nothing is half-migrated across a merge boundary.
- **Additive artifact changes only:** the published artifacts gain a new `build-env/` subdirectory but the existing DEBs stay exactly where they are to avoid breaking existing consumers.
- **Dependency-ordered cutover:** the build-dependency cascade (`sonic-swss-common` → `sonic-sairedis` → `sonic-swss`) dictates the order — an upstream repo must publish its `build-env/` bundle before a downstream repo can inherit from it.
- **Gate last:** the cross-repo pre-merge gate (§6.8) runs in informational (non-blocking) mode while the cutover is in progress, and is promoted to required-to-merge only once every stage is migrated.

| Phase | What | # of PRs |
|-------|------|:--------:|
| 1 | **Stand up the shared infra.** Create the `sonic-dataplane-buildenv` repo (the `buildenv_setup` package + tests) and add sonic-swss's shared VS-test templates + Docker image files. Add the cross-repo selfcheck pipeline in **informational** mode. Nothing in any repo's existing pipelines changes yet. | 9 |
| 2 | **Stage-by-stage cutover.** Migrate each `(repo, stage)` combination to the new infra. | 12 |
| 3 | **Lock the gate.** Promote the selfcheck pipelines from informational to required-to-merge, now that every stage runs on the new infra. | 2 |


## 8. Risks

| # | Risk | Mitigation |
|:-:|------|------------|
| 1 | **Wide blast radius of shared infra.** `buildenv_setup` and the shared VS-test templates are depended on by all three repos across every active branch, so a single bad change can break everyone at once. | The comprehensive pre-merge gate (§6.8) exercises all three repos' full pipelines against the change before it can merge; the shared paths are CODEOWNERS-gated for cross-team review; the buildenv repo is master-only, so there is a single place to apply a fix. |
| 2 | **CI now depends on the correctness of one Python package.** A bug in `buildenv_setup` that the old inline `apt-get` / artifact-download steps would have tolerated can now break every repo's environment setup. | The same package runs in both CI and local development, so defects surface quickly and visibly; it ships with a comprehensive unit-test suite; a `--dry-run` mode emits the resolved install plan for inspection and diffing against a known-good baseline. |
| 3 | **Cross-repo dependency coupling.** Because dependencies are inherited (§6.3), a bad change to an upstream repo's dependency files can break a downstream repo's build environment. | The pre-merge gate runs on PRs that touch the shared dependency files, catching downstream breakage before merge; `--dry-run` makes the resolved dependency set diffable so unexpected changes are caught in review. |
| 4 | **The comprehensive PR check for `sonic-dataplane-buildenv` is slow/expensive.** Building all three repos across every supported Debian/arch combination plus VS tests is costly. | Accepted by design (§6.8): buildenv changes are infrequent and the cost of a slipped breaking change is far higher. The comprehensive PR check only fires on PRs that touch the shared infra — not on routine PRs. |
| 5 | **Cross-repo template references couple repos to each other's interfaces.** A repo that references `build-template.yaml@<repo>` or the swss-owned VS-test templates (§6.2, §6.7) depends on the upstream's file paths and parameter contract. | Treat upstream template parameter changes as breaking changes requiring cross-team coordination; document the parameter contract in each template; the pre-merge gate exercises the repository-as-downstream path on every shared-infra PR. |
