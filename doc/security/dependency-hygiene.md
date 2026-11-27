# Automated Dependency Hygiene #

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Installation scope](#71-installation-scope)
  - [7.2 Native managers](#72-native-managers)
  - [7.3 Hand-pinned versions](#73-hand-pinned-versions)
  - [7.4 Pull request grouping](#74-pull-request-grouping)
  - [7.5 Branch policy](#75-branch-policy)
  - [7.6 Approval and merge](#76-approval-and-merge)
  - [7.7 Reviewers](#77-reviewers)
  - [7.8 Existing automation](#78-existing-automation)
  - [7.9 Gaps outside both](#79-gaps-outside-both)
  - [7.10 Rollout](#710-rollout)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1 Manifest](#91-manifest)
  - [9.2 CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3 Config DB Enhancements](#93-config-db-enhancements)
  - [9.4 Renovate configuration](#94-renovate-configuration)
  - [9.5 Setup steps](#95-setup-steps)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1 Unit Test cases](#131-unit-test-cases)
  - [13.2 System Test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items)

### 1. Revision

| Rev | Date | Author | Change |
|-----|------|--------|--------|
| 0.1 | 2026-08-31 | Brad House (Nexthop) | First draft. Security WG. |
| 0.2 | 2026-10-14 | Brad House (Nexthop) | Restructured as a design and implementation plan. Review corrections. |
| 0.3 | 2026-10-22 | Brad House (Nexthop) | Go repositories first. Security update grouping, patched modules, local `replace` directives, the `go` directive, DCO, and the setup steps. Release branches by pattern, release age in the preset, the robot commit check, copies into `vendor/` that follow `go.mod`, no unattended merge for patched modules, branch protection on Renovate branches, no fixup that undoes the update, the fixup as an edit Renovate leaves alone, the `go` directive and held-module checks, and rebasing only on a conflict outside the `automerge` rule. |
| 0.4 | 2026-11-04 | Brad House (Nexthop) | The freeze pipelines and what they keep current that Renovate does not, and the gaps outside both. |
| 0.5 | 2026-11-07 | Brad House (Nexthop) | The `go.sum` fixup's pull request runs wait for approval, and its dispatched checks are not part of the pull request's checks, so the robot reads a required check the pull request lacks from the head commit. |
| 0.6 | 2026-11-12 | Brad House (Nexthop) | Branch protection does not count dispatched runs, so the robot approves the fixup's pull request runs instead, and evaluates only the pull request's checks. No dispatch step and no loop backstop in the `go.sum` workflow. The robot accepts a `github-actions[bot]` commit only as a fixup a run started by Renovate recorded. |
| 0.7 | 2026-11-13 | Brad House (Nexthop) | GitHub Actions pinned to a digest. Dependabot security updates stay on where Python packages are. The ruleset that replaces a rule matching every branch leaves out branches with their own rules. Branch builds skip Renovate branches. The merge queue. |
| 0.8 | 2026-11-17 | Brad House (Nexthop) | Renovate merges labeled security updates itself, with the `renovate-approve` app's approval, in every repository without the `go.sum` workflow. The merge robot stays for those with it. The FIPS Go custom manager reads only trixie's pin, and `sonic-buildimage` turns off the `dockerfile` manager. The OpenTelemetry Collector has no custom manager, since its downloads are checked against pinned SHA256s a version bump does not update. A ruleset that targets all branches excludes `renovate/**`, since its force-push and deletion rules block rebases and branch cleanup. A repository keeping classic protection narrows its wildcard rule to `[0-9]*` instead of moving it to a ruleset. |
| 0.9 | 2026-11-20 | Brad House (Nexthop) | FIPS Go takes patch releases only, since a new Go minor needs `FIPS_GOLANG_MAIN_VERSION` and a new FIPS package line. A read-only check that steps 1 to 7 are in place before a repository's `renovate.json` merges. |
| 0.10 | 2026-11-20 | Brad House (Nexthop) | `go.mod` requires a published `sonic-mgmt-common` and the build adds the `replace`, so Renovate updates `go.sum` itself. No `go.sum` fixup workflow, and no merge robot path: Renovate merges every unattended update with `renovate-approve`'s approval. The pin moves weekly, and is the one update outside security updates that merges unattended. Release branches rely on OSV, and those that restrict pushes allow the Renovate app. Tested by building `sonic-mgmt-framework` and `sonic-gnmi` both ways. |
| 0.11 | 2026-11-22 | Brad House (Nexthop) | Renovate takes Python: the pip build hook releases the frozen pins an install's own requirements rule out, and retries a failed install releasing only the pins `pip` names, instead of all of them. Dependabot security updates are off everywhere. `sonic-buildimage` clones `sonic-swss-common`, which its crates depend on by path. An onboarding pull request merged by mistake is replaced by the repository's own `renovate.json`. |

### 2. Scope

[Renovate](https://docs.renovatebot.com/) runs across the `sonic-net` GitHub organization and updates third party dependencies.

In scope:

- Dependencies declared in a checked-in manifest: `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py`, GitHub Actions workflows, Dockerfiles.
- Versions SONiC pins by hand in its own build scripts, such as Docker and containerd.
- Modules a repository patches at build time. Their ordinary updates wait for approval on the Dependency Dashboard. See [7.3](#73-hand-pinned-versions).
- Which updates open a pull request, how those pull requests are grouped, and which ones merge without a person.

Out of scope:

| Item | Reason |
|------|--------|
| The Linux kernel | Each bump needs a config refresh and out-of-tree module rebuilds on every platform |
| Stock Debian packages | The nightly version freeze pipeline moves them. See [7.8](#78-existing-automation) |
| Debian packages SONiC rebuilds from pinned sources | Re-pinning a git commit or a FIPS build is a judgment call. SBOM-driven triage covers them |
| Components SONiC builds from source with a local patch series | A version bump conflicts with the patch series |
| The Go version | The build container sets it. See [7.2](#72-native-managers) |
| Removing unused dependencies | Owned by the [202611 EOL and deprecation plan](../eol-planning/202611-eol-and-deprecation.md) |

The design changes no runtime code.

### 3. Definitions/Abbreviations

| Term | Meaning |
|------|---------|
| Renovate | An open source bot that reads dependency files, finds newer versions, and opens pull requests |
| Manifest | A file that names a dependency and its version, such as `go.mod` |
| Manager | The part of Renovate that reads one manifest format |
| Custom manager | A regular expression that tells Renovate where a version sits in a file it does not otherwise read |
| Datasource | Where Renovate looks up the newest version of a dependency |
| Automerge | Merging a pull request without a person |
| Security update | An update that fixes a published vulnerability, as classified by GitHub advisories or OSV |
| Merge robot | `azure-pipelines/automation-pr-scan.yml` in `sonic-pipelines`, which merges labeled bot pull requests |
| `renovate-approve` | A GitHub App from Renovate's maintainers that approves Renovate pull requests, so Renovate can merge them where a review is required |
| SBOM | Software Bill of Materials, the list of everything in a build |
| WG | Working group |

### 4. Overview

Most third party versions in SONiC move only when another change forces them. Renovate opens a pull request when upstream publishes a release, and the existing test suite decides whether it is safe.

Each source of third party code has one owner:

| Source | Where the version is set | Kept current by |
|--------|--------------------------|-----------------|
| Go, Rust and Python modules | `go.mod`, `Cargo.toml`, `requirements*.txt`, `setup.py`, `pyproject.toml` | Renovate, native managers |
| GitHub Actions and Dockerfile base images | Workflow files, Dockerfiles | Renovate, native managers |
| Versions pinned by hand | `build_debian.sh`, Dockerfile templates, `rules/*.mk` | Renovate, custom managers |
| Stock Debian packages | The Debian snapshot and `files/build/versions*` | Version freeze pipeline |
| Submodule commits | `sonic-buildimage` submodule pointers | Submodule update pipeline |
| Debian packages SONiC rebuilds | `rules/*.mk`, `src/` | SBOM-driven triage |
| The Linux kernel | `sonic-linux-kernel` | People |
| The Go version | The build container, and the `go` directive in each `go.mod` | The build container's owners |

Hand-pinned versions sit in no file Renovate reads by default. Each one has a custom manager (R9).

### 5. Requirements

| # | Requirement |
|---|-------------|
| R1 | Renovate acts only in the `sonic-net` repositories that adopt it, each through one reviewed configuration file |
| R2 | A security update opens a pull request without anyone asking |
| R3 | A security update that is not a major version bump, and that passes every check, merges without a person |
| R4 | A major version bump never merges without a person, including a security update |
| R5 | Release branches receive security updates, and patch and minor updates to hand-pinned versions. Nothing else |
| R6 | Development branches receive every update. `master` is the development branch |
| R7 | One pull request per ecosystem per update type |
| R8 | One pull request per dependency for a major version bump |
| R9 | Every hand-pinned version has a custom manager |
| R10 | Reviewers are assigned automatically: the Security Working Group, plus the release branch owner on a release branch |
| R11 | The reproducible build version files keep working |

R1 to R10 do not apply to the exclusions in [section 2](#2-scope).

### 6. Architecture Design

Nothing changes in the SONiC image, its containers, or anything that runs on a switch. The change is to the development workflow:

```
upstream release ──▶ Renovate ──▶ pull request ──▶ checks ──┬─▶ automerge label, all checks pass ──▶ renovate-approve approves, Renovate merges
                                                            └─▶ otherwise ──▶ reviewer
```

Renovate runs as the hosted GitHub App. Nothing is installed on build machines. Each repository controls its behavior through a `renovate.json` at its root.

### 7. High-Level Design

#### 7.1 Installation scope

| Repository | Renovate configuration |
|------------|------------------------|
| `sonic-buildimage` | Yes |
| Submodules owned by `sonic-net` | Yes |
| Third party submodules (FRR, scapy, supervisor, vendor platform repositories) | No. Their dependencies arrive through the pinned submodule commit |

A repository adopts Renovate through a change that adds its `renovate.json`, reviewed like any other. Renovate's own onboarding pull request ("Configure Renovate") is never merged: it carries `config:recommended` alone, without the shared preset, the reviewers or the patched-module rules, and it leaves Dependabot running. One merged by mistake, as `sonic-buildimage`'s was, is replaced by the change that adds the repository's own `renovate.json`, which edits the file instead of adding it. Until then, Renovate runs with `config:recommended` alone; once the preset applies, it closes the pull requests the preset does not allow.

The app is installed on all repositories, and opens an onboarding pull request in each one without a `renovate.json`. Each onboarding pull request is closed without merging. Renovate does not reopen one that was closed unmerged, and picks a repository up on its next run once the repository's own `renovate.json` merges. A repository created later gets its own onboarding pull request, closed the same way.

The repositories that are mostly Go come first: `sonic-mgmt-common` and `sonic-gnmi`. Renovate takes every manager in [7.2](#72-native-managers) in them, not only `gomod`.

#### 7.2 Native managers

| Manager | Reads | Enabled |
|---------|-------|---------|
| `gomod` | `go.mod` | Yes |
| `cargo` | `Cargo.toml` | Yes |
| `github-actions` | `.github/workflows/*.yml` | Yes |
| `dockerfile` | `Dockerfile` | Yes |
| `pip_requirements`, `pip_setup`, `pep621` | `requirements*.txt`, `setup.py`, `pyproject.toml` | Yes. The pip build hook lets a requirement an install states win over the frozen pin. See the pip seam in [7.8](#78-existing-automation) |
| `git-submodules` | `.gitmodules` | No. The submodule update pipeline owns submodule pointers |

`gomod` runs `go mod tidy` after each update, and rewrites import paths on a major bump.

A Python lower bound (`>=`) that already allows the newest release is left as it is. Exact pins (`==`) and upper bounds are raised.

**Submodules a manifest reads.** Renovate does not clone submodules, and a manifest that depends on a path inside one cannot be resolved without it. In `sonic-buildimage`, five crates depend on `src/sonic-swss-common/crates/swss-common` by path, so `cargo` fails to load them and every lock file update in those workspaces reports an artifact error. `sonic-buildimage`'s `renovate.json` sets `cloneSubmodules` with `cloneSubmodulesFilter` naming `src/sonic-swss-common` only. The `git-submodules` manager stays off: cloning a submodule does not update its pointer.

**GitHub Actions are pinned to a digest.** Semgrep's blocking `github-actions-mutable-action-tag` rule fails every changed `uses:` line that names a tag, so an update from one tag to another would fail the required Semgrep check. The preset pins each action to a commit digest, with its version as a comment. In a repository that still uses tags, Renovate first opens one pull request that pins them all.

**The `go` directive.** Each Go repository lists `go` in `ignoreDeps`. A standard library vulnerability makes Renovate propose raising the `go` directive, and a security update overrides every package rule, so only `ignoreDeps` stops it. The directive cannot move ahead of the Go in the build container, and a standard library fix reaches SONiC through that toolchain.

`ignoreDeps` does not stop `go get` from raising the directive. Renovate runs `go get` with the newest Go the directive allows, and raises the directive when an update needs a newer Go. Each Go repository's CI therefore builds only with the build container's Go. Every job that runs Go runs in the `sonic-slave` container for the pull request's base branch, the pipeline sets `GOTOOLCHAIN=local` so Go never downloads a toolchain, and no pipeline names a Go version. A directive newer than the container's Go then fails CI, and the pull request does not merge unattended; a raise the container's Go supports passes. A GitHub Actions workflow that runs Go to change the repository runs it in the same container with `GOTOOLCHAIN=local`. When the build container moves to a newer Go, no repository changes.

**Local `replace` directives.** To update `go.sum`, Renovate runs `go get` in a checkout of the one repository. `sonic-gnmi` and `sonic-mgmt-framework` required `sonic-mgmt-common` at the zero pseudo-version, `v0.0.0-00010101000000-000000000000`, and replaced it with `../sonic-mgmt-common`, so `go get` failed without that checkout beside them, and `go.sum` was left behind. Renovate's `gomodMassage` option comments out the whole `replace` block, which also drops the pins that patched modules depend on, so it is not used.

Such a repository's `go.mod` instead requires `sonic-mgmt-common` at the pseudo-version of a commit on its default branch, such as `v0.0.0-20261106021544-c49a9496f49b`, which the Go module proxy serves, and carries no `replace` for it. The build adds the `replace` when the checkout is there, before the `go mod tidy` it already runs:

```make
@if [ -d $(MGMT_COMMON_DIR) ]; then \
   $(GO) mod edit -replace github.com/Azure/sonic-mgmt-common=$(MGMT_COMMON_DIR); \
 fi
```

With a directory `replace`, Go reads `sonic-mgmt-common`'s requirements from the checkout, so the build compiles against the same `sonic-mgmt-common` as before. A workflow that points Go at a checkout of its own, such as `sonic-gnmi`'s CodeQL analysis, adds the `replace` with `go mod edit` the same way. Go selects the highest version that any `go.mod` in the build requires, and the repository's own `go.mod` is one of them, so the committed `go.mod` is a lower bound on what the build uses: the build can raise a module above it, never lower it. A security update Renovate makes therefore always reaches the build. Built both ways in `sonic-buildimage`, with the pin at the commit the build checks out, `sonic-mgmt-framework` and `sonic-gnmi` ship the same files, and every binary embeds the same module versions. Only the label on `sonic-mgmt-common` and the spelling of its `replace` path differ.

Renovate then owns its branches. Nothing else commits to them, so Renovate rebases them itself, rewrites import paths on a major update, and merges what is labeled `automerge` ([7.6](#76-approval-and-merge)). A `go.sum` fixup workflow, which committed `go mod tidy` to each Renovate branch, did not work: see the alternatives in [7.6](#76-approval-and-merge).

**The pin.** Renovate treats the pseudo-version as a digest of `sonic-mgmt-common`'s default branch. Only Renovate's own `go get` and `go mod tidy` read the commit it names, and when they tidy, Go copies that commit's requirements into the repository's `go.mod`. A stale pin therefore leaves `go.mod` and `go.sum` below what the build resolves: a scanner reading them sees older versions than the binary carries, and the build's own tidy fetches more of the dependency set than `go.sum` records. A stale pin fails outright only when the repository imports a package added to `sonic-mgmt-common` after the pinned commit. Renovate's tidy cannot find the package, and every Renovate pull request reports an artifact error until the pin moves. Each such repository moves the pin weekly:

```json
{
  "matchManagers": ["gomod"],
  "matchPackageNames": ["github.com/Azure/sonic-mgmt-common"],
  "matchUpdateTypes": ["digest"],
  "minimumReleaseAge": "7 days",
  "schedule": ["before 6am on monday"],
  "rebaseWhen": "behind-base-branch",
  "automerge": true,
  "automergeType": "pr",
  "platformAutomerge": false
}
```

A pin update raises the versions `sonic-mgmt-common` requires in the build, so it is a real change. Those versions are already reviewed in `sonic-mgmt-common`, and Renovate merges the update only once every check, the full build included, has passed. It is the one update that is not a security update and still merges unattended: `automerge: true` makes Renovate write `**Automerge**: Enabled` in its body, so `renovate-approve` approves it ([7.6](#76-approval-and-merge)). A person reviewing a weekly update whose versions were reviewed upstream would add noise, not scrutiny. It carries no `automerge` label, so it sets `rebaseWhen` itself: the preset rebases only labeled updates when they fall behind ([7.5](#75-branch-policy)), and a base branch that requires branches to be up to date would otherwise hold it open for good. Semgrep's `renovate-missing-minimum-release-age` rule accepts only `"7 days"` or `false`, and Renovate's validator accepts only a string, so the rule waits 7 days. A digest update only ever offers the head of `sonic-mgmt-common`'s default branch, so the pin moves once that head is 7 days old, after a week with no commits there. Over its recent history that is every one to three weeks. Until then the update shows under Pending Status Checks on the Dependency Dashboard, and ticking it there opens the pull request early; it still merges only once the head is 7 days old.

On a release branch the preset turns ordinary `gomod` updates off ([7.5](#75-branch-policy)), so the pin stays where it was at the branch cut. The build is unaffected, since it compiles against the release branch's checkout. A backport that makes the repository import a package newer than the pin shows as an artifact error on the branch's security updates, which then wait for a reviewer, and the branch's pin is moved by hand to the head of `sonic-mgmt-common`'s release branch.

**Generated packages.** `go mod tidy` loads every package the repository imports, so a package that exists only after a build step fails it, wherever the `replace` points. `sonic-mgmt-framework`'s `rest/main` imported `build/rest_server/dist/openapi`, which codegen creates. Its committed `routes.go` moved to `rest/openapi`, codegen generates the server code beside it, `.gitignore` covers the generated files, and the `gofmt` check covers only committed code. A package with at least one committed file resolves, so `translib/ocbinds`, whose `ocbinds.go` `sonic-mgmt-common` generates, needs nothing.

**Branch protection on Renovate branches.** This applies to every repository that adopts Renovate. Renovate adds commits to an existing Renovate branch whenever it rebases it or moves it to a newer version. A branch protection rule that matches every branch, rather than only the default and release branches, rejects those commits when it requires a pull request or status checks: the commit is not a pull request, and a new commit cannot have passed the required checks. Such a rule does not block branch creation, so Renovate's own branches still appear, but nothing can be added to them afterwards, and a rebase someone asks for does nothing. Exempting the bots from the pull request requirement is not enough, because the required checks still apply. The protection is moved to a branch ruleset with the same rules, and the wildcard rule is deleted ([9.5](#95-setup-steps)). A classic rule gives way to a more specific one, such as the default branch's, a release branch's or `commit-validation`'s, but a ruleset applies on top of every classic rule. The ruleset therefore includes all branches and excludes `renovate/**`, the default branch, and every branch with a classic rule of its own, so it covers only what the wildcard rule covered. A ruleset that already targets all branches blocks Renovate on its own, with no classic rule involved: a restrict-force-pushes rule refuses every rebase, which Renovate pushes as a force-push, and a restrict-deletions rule keeps Renovate from deleting the branches it no longer needs. Such a ruleset excludes `renovate/**` as well. Its bypass list has the repository admin role where the wildcard rule did not apply to administrators.

A repository that keeps classic protection narrows the wildcard rule's pattern instead. A classic rule has a single pattern and no exclusions, and GitHub matches it with `File.fnmatch` and `File::FNM_PATHNAME`, so `*` does not cross a `/`. The wildcard rule becomes `[0-9]*`, which matches release branches such as `202611` and no `renovate/` or `dependabot/` branch, with its settings unchanged. The default branch and any other branch that has to stay protected, such as `release` or `commit-validation`, keep or get a rule of their own naming them. Other branches, such as a person's working branch, are no longer protected. A more permissive `renovate/**` rule beside the wildcard rule does not work: of two wildcard rules matching a branch, GitHub applies the one created first, so the existing wildcard rule still governs Renovate's branches.

**Branch builds.** An Azure pipeline whose CI trigger includes every branch also builds each push to a Renovate branch. Such a build takes the build container's tag from the branch name, which has no container, fails, and reports under the pull request build's check name on the same commit, so the pull request does not merge unattended. The change that adds `renovate.json` excludes `renovate/*` from that trigger.

GitHub refuses such a commit with "Repository rule violations found", followed by the rules it broke, such as "Cannot force-push to this branch", "Changes must be made through a pull request" and "2 of 2 required status checks are expected". A refused deletion leaves the branch in place. Renovate records that only in its job log, at debug level, and reports the run as having no errors or warnings, so neither the pull request nor the Dependency Dashboard shows it. A Renovate pull request that never takes a requested rebase or a newer version points to this rule. Write access to `renovate/**` opens no merge path. Renovate does not merge a branch someone else pushed to, `renovate-approve` approves again only after a push by Renovate ([7.6](#76-approval-and-merge)), and the default branch keeps its own protection.

**Lock files.** A Rust repository commits its `Cargo.lock`, a library included, as Cargo recommends. Without one, every build resolves crates.io afresh, so a new release reaches the build without review, and Renovate has only the ranges in `Cargo.toml` to update. A library's lock file does not affect the repositories that depend on it, which resolve it in their own. The change that adds a repository's `renovate.json` also adds a missing `Cargo.lock`, and CI builds with `--locked`, so a lock file out of step with `Cargo.toml` fails. As with Go, CI builds with the build container's Rust toolchain and installs none, so a lock file that needs a newer Rust fails.

Renovate updates the crates a `Cargo.toml` names, and their entries in `Cargo.lock`. A crate the lock file holds only as another crate's dependency gets no pull request of its own, a vulnerable one included. The preset therefore enables lock file maintenance: once a week Renovate runs `cargo update`, and opens one pull request per repository that moves every crate in its lock files to the newest compatible release. A crate SONiC takes from a git branch, such as `swss-common` from `master`, moves to that branch's head in the same pull request. `gomod` has no lock file maintenance, and needs none: `go.mod` lists every module the build uses, and Renovate updates each one there.

`cargo update` takes the newest releases as they stand, without the 7-day hold in [7.5](#75-branch-policy), so the lock file maintenance pull request is never labeled `automerge`, and a reviewer reads its lock file changes. It runs on `master` only: the release branch rule that disables every manager but `custom.regex` disables it too.

#### 7.3 Hand-pinned versions

A version a person pins in a build script has a custom manager entry beside it.

`sonic-buildimage` turns the `dockerfile` manager off. Its Dockerfiles are Jinja templates whose base images are SONiC containers, or Debian images the version freeze owns ([7.8](#78-existing-automation)), and the one plain `Dockerfile` starts from a local image.

| Variable | File | Datasource | Merge |
|----------|------|------------|-------|
| `DOCKER_VERSION` (`docker-ce`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| `CONTAINERD_IO_VERSION` (`containerd.io`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| Rust toolchain | `sonic-slave-trixie/Dockerfile.j2` | `github-releases` | Reviewer |
| `FIPS_GOLANG_VERSION` | `rules/sonic-fips.mk` | `golang-version` | Dashboard only |

**Docker and containerd.** Each package has its own entry, because each is a separate package in the apt repository. The pin omits the distribution suffix, and the build appends `~$IMAGE_DISTRO`. The apt index carries the suffix, so `extractVersionTemplate` strips it before comparison and before the new value is written:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/^build_debian\\.sh$/"],
      "matchStrings": ["DOCKER_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO"],
      "depNameTemplate": "docker-ce",
      "datasourceTemplate": "deb",
      "registryUrlTemplate": "https://download.docker.com/linux/debian?suite=trixie&components=stable&binaryArch=amd64",
      "extractVersionTemplate": "^(?<version>.+)~trixie$"
    },
    {
      "customType": "regex",
      "managerFilePatterns": ["/^build_debian\\.sh$/"],
      "matchStrings": ["CONTAINERD_IO_VERSION=(?<currentValue>\\S+?)~\\$IMAGE_DISTRO"],
      "depNameTemplate": "containerd.io",
      "datasourceTemplate": "deb",
      "registryUrlTemplate": "https://download.docker.com/linux/debian?suite=trixie&components=stable&binaryArch=amd64",
      "extractVersionTemplate": "^(?<version>.+)~trixie$"
    }
  ]
}
```

The `suite` parameter and the stripped suffix both name the image distribution, and change together when it does.

**OpenTelemetry Collector.** `OTEL_VERSION` in `dockers/docker-sonic-otel/Dockerfile.j2` has no custom manager. Each of the three architecture packages it downloads is checked against a SHA256 pinned beside it, and a regex manager changes only the version. Every pull request it opened would fail all three checksums. Recomputing them needs `postUpgradeTasks`, which the hosted Renovate app does not run, so the collector stays a manual update.

**Rust toolchain.** The `rustup` invocation carries a plain version string:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^sonic-slave-trixie/Dockerfile\\.j2$/"],
  "matchStrings": ["--default-toolchain (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "rust-lang/rust",
  "datasourceTemplate": "github-releases"
}
```

**FIPS Go toolchain.** `FIPS_GOLANG_VERSION` names a FIPS package SONiC publishes to its own mirror, which exists only after SONiC builds it. Renovate lists the upstream Go release on the Dependency Dashboard and opens a pull request only when someone approves it there. The file sets the version once per distribution, and only trixie's is tracked:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^rules/sonic-fips\\.mk$/"],
  "matchStrings": ["ifeq \\(\\$\\(BLDENV\\), trixie\\)[\\s\\S]*?FIPS_GOLANG_VERSION = (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "go",
  "datasourceTemplate": "golang-version"
}
```

```json
{
  "packageRules": [
    {
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "dependencyDashboardApproval": true
    },
    {
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "matchUpdateTypes": ["minor", "major"],
      "enabled": false
    }
  ]
}
```

Only patch releases are proposed. The custom manager captures `1.26.7` in `FIPS_GOLANG_VERSION = 1.26.7-1+fips` and keeps the Debian revision, but `FIPS_GOLANG_MAIN_VERSION = 1.26` beside it names the package (`golang-1.26_...`), and the regex cannot change it. A minor bump would leave the two disagreeing, and the build would look for a package that does not exist. A new Go minor is a new FIPS package line, which `@sonic-net/sonic-build` starts by hand, changing both values together.

The FIPS Go entry names its dependency `go`, so `ignoreDeps` for the `go` directive ([7.2](#72-native-managers)) is set in each Go repository rather than in the shared preset.

**Go module copies into `vendor/`.** `go mod vendor` leaves out packages nothing imports, so some builds copy files from a module into `vendor/` themselves, such as the `sonic-gnmi` `Makefile` and the `sonic-mgmt-common` `patches/apply.sh`. A copy never names a module version. It takes the module's directory from `go list -m`, which follows `go.mod` and its `replace` directives:

```make
MOD_DIR = $$($(GO) list -mod=mod -m -f '{{.Dir}}' $(1))
```

A version named in the build instead stays behind when `go.mod` moves: the build passes, and ships the old code. A version that follows `go.mod` needs no custom manager, and moves in the same pull request as `go.mod`.

**Patched modules.** Some repositories patch the vendored source of a module at build time. A bump usually needs the patch refreshed by hand, so an ordinary update to such a module opens only on Dependency Dashboard approval, in a pull request of its own:

```json
{
  "matchManagers": ["gomod"],
  "matchPackageNames": ["github.com/openconfig/ygot", "github.com/openconfig/goyang"],
  "groupName": null,
  "minimumReleaseAge": "7 days",
  "dependencyDashboardApproval": true,
  "addLabels": ["patched-module"],
  "prBodyNotes": ["`patches/apply.sh` patches this module in `vendor/`. A patch that still applies may no longer be correct for the new version, so check each one against it. This update is never labeled `automerge`."]
}
```

`minimumReleaseAge` repeats the preset's: Semgrep's `renovate-missing-minimum-release-age` rule asks it of every rule that names packages.

`groupName: null` matters. Renovate holds a whole group for approval when any one update in it needs approval, so a patched module left in the ecosystem group would hold back every ordinary update in that ecosystem.

A security update to a patched module still opens, because `vulnerabilityAlerts` overrides `dependencyDashboardApproval`. It never merges unattended. The build shows whether a patch still applies, but not whether it is still correct against the new version. The `patched-module` label marks these modules. The preset's `automerge` rule ([7.5](#75-branch-policy)) skips an update carrying it, and the note in the pull request body asks the reviewer to check each patch. Each one opens on its own, so a patch that needs work holds back only that fix. The repository's `vulnerabilityAlerts.groupName` names the same modules:

```json
{
  "vulnerabilityAlerts": {
    "groupName": "{{{datasource}}} security updates{{#if (or isMajor (includes (split 'github.com/openconfig/ygot github.com/openconfig/goyang' ' ') depName))}} for {{{depName}}}{{/if}}"
  }
}
```

The two lists sit in the same file and change together.

A patched module's version can also move without its own update. `go get` raises any module the update needs a newer version of, so a module whose newer releases require newer patched modules is held for approval too, even when it is not patched itself. `sonic-mgmt-common` holds `openconfig/gnmi` because its newer versions require newer `goyang` and `ygot`. A check on each Renovate pull request fails it when a held module changes version and the pull request is not that module's own update; the module's own pull request names it in its title. The check reads the held modules from the rule that adds the `patched-module` label, so it never needs its own list.

#### 7.4 Pull request grouping

| Base branch | Update type | Grouping |
|-------------|-------------|----------|
| Any | Security, patch or minor | One pull request per ecosystem per update type |
| Any | Security, major | One pull request per dependency |
| `master` | Patch | One pull request per ecosystem |
| `master` | Minor | One pull request per ecosystem |
| `master` | Major | One pull request per dependency |

A major bump is the update most likely to break, and an isolated failure names its cause.

An ecosystem is a datasource. Grouping by datasource rather than by manager puts a custom manager that reads `go` in the same pull request as `gomod`.

`vulnerabilityAlerts` overrides every package rule, including `groupName`, and its default `groupName` is `null`. Left alone, every security update would get its own pull request. The grouping is therefore set inside `vulnerabilityAlerts`, and names a major update by its dependency:

```json
{
  "vulnerabilityAlerts": {
    "groupName": "{{{datasource}}} security updates{{#if isMajor}} for {{{depName}}}{{/if}}"
  }
}
```

With `separateMajorMinor` and `separateMinorPatch`, Renovate also splits each group by update type, so a major update never shares a pull request, or its labels, with a patch or minor one.

`prConcurrentLimit` and `prHourlyLimit` bound the volume of ordinary updates. Security updates ignore both. `vulnerabilityAlerts.prConcurrentLimit` bounds them separately. The first run clears the accumulated backlog and is the largest.

#### 7.5 Branch policy

Release branches from `202611` on are in scope. One pattern matches them, so a new release branch needs no change to the preset. Older release branches carry no Renovate rules. When a release branch reaches end of life, the pattern's lower bound moves past it.

| Update | `master` | Release branch |
|--------|----------|----------------|
| Security, patch or minor | `automerge` label | `automerge` label |
| Security, major | Reviewer | Reviewer |
| Hand-pinned version, patch or minor | Reviewer | Reviewer |
| Hand-pinned version, major | Reviewer | Not opened |
| Any other patch or minor | Grouped, reviewer | Not opened |
| Any other major | One per dependency, reviewer | Not opened |
| Lock file maintenance | Weekly, reviewer | Not opened |

**Security classification.** Renovate classifies a security update from GitHub vulnerability alerts and OSV, both keyed by ecosystem:

| Lane | Datasource | Classified as security |
|------|------------|------------------------|
| `gomod`, `cargo`, `pip` | Ecosystem registry | Yes |
| A custom manager on an ecosystem datasource | Ecosystem registry | Yes |
| Docker, containerd | `deb` | No |
| Rust | `github-releases` | No |
| FIPS Go | `golang-version` | No |

A custom manager on any other datasource has no advisory feed behind it. A release branch therefore enables hand-pinned updates by name, and a reviewer decides whether each one is needed.

A release branch depends on OSV. GitHub computes Dependabot alerts for the default branch only, and closes an alert once the default branch has the fix, even while a release branch still pins the vulnerable version. `osvVulnerabilityAlerts` has Renovate check each base branch's own versions against OSV, which carries the Go vulnerability database. A Go standard library fix reaches a release branch through its build container's Go, which follows the FIPS Go pin: the preset allows hand-pinned patch updates there, so the new Go patch appears on that branch's Dependency Dashboard for approval ([7.3](#73-hand-pinned-versions)).

**The `automerge` label.** Renovate applies the `vulnerabilityAlerts` object to every security update with precedence over all package rules. That object sets the `security` label and the grouping in [7.4](#74-pull-request-grouping), and never `automerge`. A package rule adds `automerge` to security updates that are patch or minor:

```json
{
  "vulnerabilityAlerts": { "enabled": true, "labels": ["security"] },
  "packageRules": [
    {
      "description": "Security updates below a major version merge unattended, unless a repository marks the module patched-module. They are kept up to date with the base branch so Renovate can merge them; every other update is rebased only on a conflict, or when someone asks for it on the pull request or the dependency dashboard",
      "matchJsonata": ["isVulnerabilityAlert = true and $not('patched-module' in addLabels)"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"],
      "rebaseWhen": "behind-base-branch"
    }
  ]
}
```

Besides these, only the weekly `sonic-mgmt-common` pin update merges unattended ([7.2](#72-native-managers)). A security update that needs a major version opens with the `security` label alone and waits for a reviewer. So does one to a module a repository marks `patched-module` ([7.3](#73-hand-pinned-versions)). Renovate adds the vulnerability rules after the preset's own. Its first pass over the rules sets the security flag, and a later pass, which starts from that result, matches the `automerge` rule on the flag and the update type.

**Rebasing.** A base branch that requires branches to be up to date before merging makes Renovate's default, `rebaseWhen: auto`, rebase every open pull request each time the base branch moves. Each rebase is a new push, with its own build, review requests and notifications. The preset sets `rebaseWhen: conflicted`, so an update is rebased only when it conflicts with the base branch, or when a reviewer ticks the rebase box on the pull request or the Dependency Dashboard before merging it. The `automerge` rule sets `behind-base-branch`, so an update that merges unattended is always current when it is evaluated.

Renovate truncates a pull request body that would be too long, which a long security advisory can cause, and the rebase box at its end goes with it. The Dependency Dashboard's rebase box for that branch does the same thing.

**Release branch rules.** Before a lookup, Renovate does not yet know the update type, and a rule that disables a dependency at that stage removes it before any later rule can re-enable it. The release branch rules therefore disable every manager except `custom.regex` up front, and then disable `custom.regex` majors once the update type is known. A security update overrides both.

**Release age.** The preset holds every update until its release is 7 days old, so a release that is withdrawn or compromised soon after publication is not proposed. A security update is not held, because `vulnerabilityAlerts` resets `minimumReleaseAge`.

#### 7.6 Approval and merge

Renovate cannot approve its own pull requests. Which ones merge unattended is decided in `renovate.json` ([7.5](#75-branch-policy)), and Renovate merges them itself, with the approval of the [`renovate-approve`](https://github.com/apps/renovate-approve) app.

**Renovate merges.** Each repository adds a rule that matches exactly what the preset labels `automerge`:

```json
{
  "matchJsonata": ["isVulnerabilityAlert = true and $not('patched-module' in addLabels)"],
  "matchUpdateTypes": ["patch", "minor"],
  "automerge": true,
  "automergeType": "pr",
  "platformAutomerge": false,
  "assignAutomerge": true
}
```

| Setting | Reason |
|---------|--------|
| `automergeType: pr` | The merge goes through the pull request, which keeps a review record |
| `platformAutomerge: false` | GitHub's native auto-merge waits only for the base branch's required checks, and many branches require little more than `EasyCLA`. With it off, Renovate merges on a later run, and only once every check on the head commit has passed. A check still running, or none at all, holds the merge |
| `assignAutomerge: true` | Renovate otherwise requests no reviewers on a pull request it intends to merge, and one that fails would reach nobody |

The `renovate-approve` app approves the pull request, which satisfies a branch's review requirement. It approves only a pull request the Renovate bot opened whose body says `**Automerge**: Enabled`, and it does so when the pull request opens. It is therefore installed on the whole organization: a Renovate pull request a reviewer has to merge says `Disabled` and is never approved. A pull request opened before its repository's rule merged gets no approval, and waits for a reviewer, or for Renovate to open it again. When a push dismisses its approval, the app approves again only if the Renovate bot made the push.

Nothing bypasses branch protection, so GitHub enforces every required check and every ruleset as for any other pull request. Renovate does not merge a branch someone else has pushed to, and such a push dismisses the approval where the branch dismisses stale reviews. The rule repeats the preset's condition rather than matching the label, and the two change together.

**Release branches that restrict pushes.** A classic rule that restricts who can push to a branch applies to merging a pull request into it. `sonic-mgmt-framework`'s `20[0-9]*` rule allows only `sonic-automation` and `sonic-release-managers`, so GitHub would refuse Renovate's merge even after `renovate-approve` approved it. Each such rule adds the Renovate app to the actors allowed to push ([9.5](#95-setup-steps)). That gives Renovate merge rights on the branch, which its configuration limits to security patch and minor updates (R3, R5), and each branch's release manager agrees to it before the app is added ([14](#14-openaction-items)).

`EasyCLA` is a required check, and is a commit status. A pull request from the Renovate bot clears it the same way one from `mssonicbld` does.

Repositories that require DCO sign-off reject unsigned commits, so the preset sets `commitBody` to a `Signed-off-by` line for the Renovate bot.

**The merge robot.** The merge robot (`automation-pr-scan.yml`) also lists the Renovate pull requests labeled `automerge` and `security` in the repositories it scans, evaluates every check and commit itself, approves runs a fixup commit left waiting, and merges with `gh pr merge --admin` as `mssonicbld`. It existed for repositories that ran a `go.sum` fixup workflow, where Renovate treated the fixed-up branch as edited and never merged it. With the pin in [7.2](#72-native-managers), no repository runs one, so that support is removed from the robot ([14](#14-openaction-items)), and no branch needs a review bypass for `mssonicbld` on Renovate's account. Until it is removed, whichever of the two acts first merges a labeled pull request, and both wait for every check to pass.

Alternatives considered:

| Option | Not chosen because |
|--------|--------------------|
| A `go.sum` fixup workflow, with the merge robot | The workflow committed `go mod tidy` to each Renovate branch as `github-actions[bot]`. Renovate then treated the branch as edited: it no longer rebased it, so each base branch change it conflicted with waited for a person to tick the rebase box, and each rebase repeated the fixup, a robot approval of its waiting runs and the build. Letting Renovate own the fixed-up branch instead, by ignoring the fixup's author, made it rebuild the branch on every run once tidy moved a line in `go.mod`, in a loop. Renovate never merged an edited branch, so the robot merged with `--admin`, whose `mssonicbld` bypass also skips the branch's required checks and rulesets, so the robot had to evaluate every check and commit itself |
| A `go.work` file naming the checkout | Go never vendors a workspace module, and the builds vendor `sonic-mgmt-common` and read it from `vendor/` |
| Self-hosted Renovate, tidying in `postUpgradeTasks` | Renovate makes the tidy commit itself, but SONiC would run and upgrade Renovate, its schedule and its tokens. The pin removes the need |
| `platformAutomerge: true` | GitHub merges once the required checks pass, ignoring any other check that fails |
| Ruleset bypass for Renovate | Applies to every Renovate pull request, and cannot be limited to security updates |
| `automergeType: branch` | Commits without a pull request, which leaves no review record on a release branch |

#### 7.7 Reviewers

Renovate assigns reviewers from an explicit list. `CODEOWNERS` is not used, because most paths Renovate edits fall through to a single catch-all owner.

```json
{
  "reviewers": ["team:sonic-security-wg"]
}
```

| Rule | Reason |
|------|--------|
| The reviewer is the `@sonic-net/sonic-security-wg` team | One place to edit when membership changes |
| The team holds the public Working Group membership | It is a new team, created for this |
| The team is visible, and has no parent team | A secret team's name would show on public review requests while its membership stayed hidden. A child team inherits its parent's access |
| The team has Read on each repository Renovate runs in | A review can only be requested from a team with access to the repository |
| `sonic-private-security-group` is never a reviewer, or a parent of the team | It handles embargoed vulnerabilities. These pull requests are public and carry fixes that are already published |
| A release branch adds its release manager team through `additionalReviewers` | Each release branch already has a `release-manager-<branch>` team |

The release manager rule is added to the preset with the branch, once its `release-manager-<branch>` team exists:

```json
{
  "matchBaseBranches": ["/^202611$/"],
  "additionalReviewers": ["team:release-manager-202611"]
}
```

Renovate sets reviewers when it opens a pull request and does not revisit them.

#### 7.8 Existing automation

Five pipelines already keep parts of the tree current, all acting as `mssonicbld`. Renovate is added beside them.

| Pipeline | Owns | Where it lives |
|----------|------|----------------|
| Version freeze | What the image build resolves: `apt` and `pip` versions per platform, architecture and container, Docker base image digests, and the Debian snapshot timestamp. Writes `files/build/versions-public/`, which `files/build/versions` links to | `sonic-buildimage`, `.azure-pipelines/azure-pipelines-UpgrateVersion.yml` |
| `docker-ptf` version freeze | The same for the `docker-ptf` test image. Writes `dockers/docker-ptf/files/` | `sonic-buildimage`, `.azure-pipelines/docker-ptf.yml` |
| `docker-sonic-mgmt` version freeze | The same for the `docker-sonic-mgmt` test image. Writes `dockers/docker-sonic-mgmt/files/` | `sonic-buildimage`, `.azure-pipelines/docker-sonic-mgmt.yml` |
| Submodule update | Which commit of each submodule `sonic-buildimage` builds | `sonic-pipelines`, `azure-pipelines/submodule-update.yml` |
| Merge robot | Merging labeled bot pull requests | `sonic-pipelines`, `azure-pipelines/automation-pr-scan.yml` |
| Renovate | What manifests declare, and hand-pinned versions | Each repository's `renovate.json` |

**The freeze pipelines.** Each one builds with nothing pinned, records what the build installed, and opens a pull request with the difference:

| Step | Work |
|------|------|
| 1 | Read the newest Debian and Debian security snapshot timestamps from `packages.trafficmanager.net` |
| 2 | Build with `SONIC_VERSION_CONTROL_COMPONENTS=` empty, against those snapshots. The version freeze builds `vs`, `vpp`, `alpinevs`, `broadcom`, `marvell-prestera` (`armhf`, `arm64`), `mellanox`, `nvidia-bluefield` and `aspeed-arm64` |
| 3 | The build hooks record each container's result: `dpkg-query` for `versions-deb-*`, `pip3 freeze --all` for `versions-py3`, and the images, downloads and clones it used for `versions-docker`, `versions-web` and `versions-git` (`src/sonic-build-hooks/scripts/collect_version_files`) |
| 4 | `make freeze` (`scripts/versions_manager.py freeze`) merges the results into the version files. A scheduled run of the version freeze also drops the files of containers no build produced |
| 5 | Push `repd/versions/<branch>` (or `repd/docker-ptf-versions/<branch>`) and open a pull request labeled `automerge`, which the merge robot merges |

The version freeze runs daily. Its YAML schedule names the `20*` release branches, and it also opens the `master` pull requests, such as #30435. `docker-sonic-mgmt` runs daily on `master`. `docker-ptf` names no schedule in its YAML. A build with `deb` in `SONIC_VERSION_CONTROL_COMPONENTS` sets `MIRROR_SNAPSHOT=y` and installs only what the files name, so a Debian security fix reaches a build only through the next freeze.

What the freeze pipelines keep current, and Renovate does not:

| Item | Version file | Why not Renovate |
|------|--------------|------------------|
| Stock Debian packages, including Debian security and LTS fixes | `versions-mirror`, `versions-deb-*` | No manifest names them, and Renovate has no Debian advisory feed |
| Python packages Debian installs, such as `python3-brotli` | `versions-py3`, through `pip3 freeze` | They are Debian packages. `pip` reports their upstream version |
| Python packages a build installs with `pip` | `versions-py3` | Renovate updates the requirements a manifest states. The packages those resolve to, and every transitive one, are pinned by the freeze. See the pip seam below |
| Docker base images named in Dockerfile templates, such as `debian:trixie` | `versions-docker`, by digest | The `dockerfile` manager does not read a `.j2` template such as `FROM {{ prefix }}debian:trixie` ([7.3](#73-hand-pinned-versions)) |
| What a pinned download or clone fetched | `versions-web`, `versions-git` | These record what a build fetched. A hand-pinned version in the URL is Renovate's ([7.3](#73-hand-pinned-versions)) |

**Dependabot.** Dependabot has three parts, and each is handled when a repository adopts Renovate:

| Part | With Renovate | Reason |
|------|---------------|--------|
| Dependabot alerts | On | Renovate reads them for GitHub's vulnerability data |
| Dependabot security updates | Off | Each vulnerability would get a pull request from both bots. Renovate takes every ecosystem Dependabot covered here, Python included |
| Dependabot version updates (`.github/dependabot.yml`) | Removed in the change that adds `renovate.json` | Renovate does the same work. The preset's `minimumReleaseAge` replaces a cooldown it set |

Open Dependabot pull requests are closed once Renovate runs; Renovate opens its own.

**The pip seam.** The pip build hook in `src/sonic-build-hooks/scripts/buildinfo_base.sh` passes the frozen `versions-py3` file to every `pip install` as a constraint file. It used to release a package from the constraint only when an exact version appeared on the command line. A requirement in a `requirements.txt`, or in a wheel's `Requires-Dist` from a `setup.py`, that the frozen version did not satisfy made `pip` fail, and the hook then retried the install with no constraints at all: every package in it took its newest version, and the build passed without being reproducible. A Renovate bump to a pin would have done exactly that.

| Resolution | Effect |
|------------|--------|
| Exclude `pip_requirements` and `pip_setup` | Python stays with the freeze pipeline, and Dependabot stays on for it. Chosen for the first phases |
| Teach the build hook to read the requirements an install states | Removes the seam. Chosen |
| Order the Renovate pull request behind a re-freeze | Keeps both, with a dependency between them |

Before each install, `src/sonic-build-hooks/scripts/pip_release_constraints.py`, run by the wrapped `pip`'s own interpreter with `pip`'s vendored `packaging`, reads the requirements the install states: on the command line, in requirements files (nested `-r` included), and in local wheels' `Requires-Dist`, with markers and extras evaluated. It drops the pin of each package a stated requirement excludes, and of each local wheel's own package; every other pin stays, and each dropped pin is logged. The unconstrained retry becomes a targeted one: when the resolver still fails, as when an unfrozen package's newest release needs a newer transitive package, or a frozen version has no wheel for the architecture, `pip` names each blocking pin, and the hook releases only those and tries again. An install that fails with no pin named fails the build. The next freeze records what the build installed. A Renovate change to a `setup.py` in a submodule reaches the hook through the submodule update, the same way. The preset enables the Python managers only after the hook change merges (sonic-net/sonic-buildimage#30963, sonic-net/sonic-pipelines#262).

The frozen `versions-py3` files are not given to Renovate. About half their entries are Python packages Debian installs (G5 in [7.9](#79-gaps-outside-both)): raising such a pin changes nothing the build installs, the next freeze writes Debian's version back, and Renovate would open the same pull request again. On `master`, the nightly freeze moves the rest.

#### 7.9 Gaps outside both

Neither the freeze pipelines nor Renovate closes these. CVE-2026-111497, a Brotli decoder overflow fixed by Debian on 2026-10-23, shows most of them: `master` picked up the fix when freeze pull request #30435 merged on 2026-10-29, and only because the freeze runs nightly.

| # | Gap | Example | Suggested fix |
|---|-----|---------|---------------|
| G1 | The freeze runs on a clock, not on an advisory. Nothing starts it when Debian publishes a fix, or speeds the merge of its pull request | The Brotli fix took six days to reach `master` | A daily job that compares each branch's `versions-deb-*` against the Debian security tracker's JSON, and starts that branch's freeze or opens an issue when a pinned version is older than a fix |
| G2 | A stalled freeze is silent. A failing pipeline or an unmerged pull request leaves the pins where they are | `202505`'s last freeze merged on 2026-06-28. It still pins `libbrotli1` `1.0.9-2+b6` | An alert when a branch's `versions-mirror` snapshot is older than a set age |
| G3 | Version files no freeze build produces go stale. The scheduled clean-up drops a container's files only when no build produces the container at all | `files/build/versions-public/dockers/docker-ptf/versions-deb-bookworm` kept `+b6` after the freeze moved the rest of `master`, until a hand-written pull request (#30454) | Build every pinned container and distribution in the freeze, or drop the files of each one it does not build |
| G4 | `docker-ptf` has two version trees, and the published image follows neither for Debian packages | `files/build/versions-public/dockers/docker-ptf/` and `dockers/docker-ptf/files/` disagree. The `docker-ptf` Dockerfile ends by removing the `apt` pins and running `apt-get upgrade` | Keep one tree per image, and record what the image ships after the upgrade |
| G5 | `versions-py3` cannot tell a Debian package from a PyPI one | `brotli==1.1.0` is Debian's patched `python3-brotli`, and also the name of the vulnerable PyPI release. A scanner reading `versions-py3` reports it, and a `pip install` would satisfy the constraint with the vulnerable wheel | Mark or leave out the packages under `dist-packages` in `pip3 freeze`, and have scanners read `versions-deb-*` for them |
| G6 | The SBOM sees a library built into another package only when an advisory names that package | The SBOM records Debian's `python3-brotli` under its source package `brotli`, so a scan matches Debian's advisory. A PyPI `Brotli` wheel, which also compiles the decoder into `_brotli.so`, matches only if the GitHub advisory lists the PyPI package. `README.sbom.md` lists statically linked vendored libraries as undetectable | A list of known bundled copies, mapped to the library each carries, read by SBOM triage |
| G7 | Build and test images have no SBOM | `README.sbom.md` puts `sonic-slave-*` out of scope, and `docker-ptf`'s Trivy scan is optional | Scan them, or record that they are accepted unscanned |
| G8 | An image built on a base that is not Debian gets no fix from the Debian snapshot or the freeze. Only the base image digest is pinned, and its version files list only what the build installs or upgrades, so a base package the build leaves alone appears in none of them | `docker-dash-engine`, which the `vs` image ships, builds `FROM p4lang/behavioral-model:latest`, an Ubuntu 24.04 image. It upgrades only curl, so it ships `libbrotli1` `1.1.0-2build2` while Ubuntu's fix is `1.1.0-2ubuntu0.1`. Only the SBOM scan reports it. The pinned base also carries six other Ubuntu security updates it does not apply | Apply the distribution's security updates in each such image, as `docker-ptf` does with `apt-get upgrade`, so the next freeze records the result |

Shipped images are covered. Each official image's SBOM is published beside it and sent to OpenPSIRT for its branch (`.azure-pipelines/upload-sbom-openpsirt.yml`), and an old SBOM can be scanned again against current advisories, which finds the shipped images a new fix applies to. Rebuilding them is the release process's.

#### 7.10 Rollout

| Phase | Work |
|-------|------|
| 1 | The shared preset and `renovate-approve`. `sonic-mgmt-common`, `sonic-gnmi` and `sonic-mgmt-framework` on `master`, with the pin in [7.2](#72-native-managers), including unattended merges of security updates |
| 2 | Docker and containerd custom managers in `sonic-buildimage`, on `master` |
| 3 | Native managers on `master` in `sonic-buildimage` and the remaining owned repositories holding `go.mod` or `Cargo.toml` |
| 4 | Rust and FIPS Go custom managers |
| 5 | Remaining owned repositories, and the `202611` branch |
| 6 | Python managers, after the pip build hook releases the pins an install's requirements rule out |

The Go repositories come first because they need no custom manager. Each repository adds the rule that lets Renovate merge ([7.6](#76-approval-and-merge)) once `renovate-approve` is installed, in its own change or in the one that adds its `renovate.json`.

### 8. SAI API

No change.

### 9. Configuration and management

#### 9.1 Manifest

Not applicable. This is not a SONiC Application Extension.

#### 9.2 CLI/YANG model Enhancements

No change.

#### 9.3 Config DB Enhancements

No change.

#### 9.4 Renovate configuration

Shared settings live in one preset at `renovate/default.json` in `sonic-net/sonic-pipelines`, beside the merge robot and the submodule updater. Each repository extends it:

```json
{
  "extends": ["local>sonic-net/sonic-pipelines//renovate/default"]
}
```

Repository-specific settings, such as custom managers, sit beside the `extends` line. The double slash selects a file in a subdirectory.

The preset:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "description": "Shared Renovate preset for sonic-net repositories. See doc/security/dependency-hygiene.md in sonic-net/SONiC.",
  "extends": ["config:recommended"],
  "baseBranchPatterns": ["master", "/^(20261[12]|20(2[7-9]|[3-9][0-9])(0[1-9]|1[0-2]))$/"],
  "reviewers": ["team:sonic-security-wg"],
  "dependencyDashboard": true,
  "osvVulnerabilityAlerts": true,
  "separateMajorMinor": true,
  "separateMinorPatch": true,
  "rebaseWhen": "conflicted",
  "commitBody": "Signed-off-by: {{{gitAuthor}}}",
  "enabledManagers": ["gomod", "cargo", "pip_requirements", "pip_setup", "pep621", "github-actions", "dockerfile", "custom.regex"],
  "postUpdateOptions": ["gomodTidy", "gomodUpdateImportPaths"],
  "lockFileMaintenance": { "enabled": true },
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "groupName": "{{{datasource}}} security updates{{#if isMajor}} for {{{depName}}}{{/if}}"
  },
  "packageRules": [
    {
      "description": "Wait 7 days after a release before proposing it. Security updates are not delayed",
      "matchPackageNames": ["*"],
      "minimumReleaseAge": "7 days"
    },
    {
      "description": "Pin GitHub Actions to a commit digest. Semgrep's blocking github-actions-mutable-action-tag rule fails every changed uses: line that names a tag",
      "matchManagers": ["github-actions"],
      "matchDepTypes": ["action"],
      "pinDigests": true
    },
    {
      "description": "Group patch and minor updates per ecosystem on master",
      "matchBaseBranches": ["master"],
      "matchUpdateTypes": ["patch", "minor"],
      "groupName": "{{{datasource}}} {{{updateType}}} updates"
    },
    {
      "description": "Major updates get their own pull request",
      "matchBaseBranches": ["master"],
      "matchUpdateTypes": ["major"],
      "groupName": null
    },
    {
      "description": "Release branches take security updates, and hand-pinned versions, only",
      "matchBaseBranches": ["/^(20261[12]|20(2[7-9]|[3-9][0-9])(0[1-9]|1[0-2]))$/"],
      "matchManagers": ["!custom.regex"],
      "enabled": false
    },
    {
      "description": "A hand-pinned major update is not opened on a release branch",
      "matchBaseBranches": ["/^(20261[12]|20(2[7-9]|[3-9][0-9])(0[1-9]|1[0-2]))$/"],
      "matchManagers": ["custom.regex"],
      "matchUpdateTypes": ["major"],
      "enabled": false
    },
    {
      "description": "Security updates below a major version merge unattended, unless a repository marks the module patched-module. They are kept up to date with the base branch so Renovate can merge them; every other update is rebased only on a conflict, or when someone asks for it on the pull request or the dependency dashboard",
      "matchJsonata": ["isVulnerabilityAlert = true and $not('patched-module' in addLabels)"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"],
      "rebaseWhen": "behind-base-branch"
    },
    {
      "description": "FIPS Go is published by SONiC; open only on dashboard approval",
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "dependencyDashboardApproval": true
    },
    {
      "description": "FIPS Go takes patch releases only. A new Go minor also changes FIPS_GOLANG_MAIN_VERSION, which the custom manager cannot",
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "matchUpdateTypes": ["minor", "major"],
      "enabled": false
    }
  ]
}
```

This is the file committed to `sonic-pipelines`. Its `description` names this document. Each Go repository adds `ignoreDeps` for the `go` directive, and a rule and a `vulnerabilityAlerts.groupName` for its patched modules ([7.3](#73-hand-pinned-versions)). A repository that builds against a `sonic-mgmt-common` checkout requires the published module, adds the `replace` in its build, and moves the pin weekly ([7.2](#72-native-managers)). Each Go repository adds the held-module check in [7.3](#73-hand-pinned-versions). Every repository adds the rule that lets Renovate merge ([7.6](#76-approval-and-merge)). Each Go repository's CI builds with the build container's Go only ([7.2](#72-native-managers)).

#### 9.5 Setup steps

| Step | Who | Work |
|------|-----|------|
| 1 | SONiC Foundation EasyCLA administrators | Add `renovate[bot]` to the EasyCLA approved list, as `mssonicbld` is |
| 2 | Organization administrator, Security WG | Create the `sonic-security-wg` team as set out in [7.7](#77-reviewers): visible, no parent team, the public Working Group membership with at least one member as team maintainer, and Read on each repository Renovate runs in |
| 3 | Each repository's administrators | Leave Dependabot alerts on, and turn Dependabot security updates off. See [7.8](#78-existing-automation) |
| 4 | `sonic-pipelines` maintainers | Merge `renovate/default.json`, and remove the merge robot's Renovate support from `automation-pr-scan.yml` ([7.6](#76-approval-and-merge)) |
| 5 | Organization administrator | On each branch Renovate targets whose protection restricts who can push, add the Renovate app to the actors allowed to push, once the branch's release manager agrees ([7.6](#76-approval-and-merge)) |
| 6 | Each repository's administrators | Where a branch protection rule matches every branch, replace that rule with a branch ruleset that includes all branches, excludes `renovate/**`, the default branch and every branch with a classic rule of its own, keeps the same rules, and lets the repository admin role bypass where the wildcard rule did not apply to administrators, so Renovate can add commits to Renovate branches. A repository that keeps classic protection instead changes the wildcard rule's pattern to `[0-9]*`, and adds a rule naming each other branch that has to stay protected ([7.2](#72-native-managers)). Every existing ruleset that targets all branches also excludes `renovate/**` |
| 7 | Organization administrator | Install the app at <https://github.com/apps/renovate> on all repositories, accepting the requested permissions, which include read access to Dependabot alerts, and close the onboarding pull requests without merging ([7.1](#71-installation-scope)). Install <https://github.com/apps/renovate-approve> on all repositories too ([7.6](#76-approval-and-merge)) |
| 8 | Each repository's owners | Merge a `renovate.json` extending the preset, with the rule that lets Renovate merge, and the removal of `.github/dependabot.yml`. Where the build uses a `sonic-mgmt-common` checkout, the change requires the published module, adds the `replace` in the build and the weekly pin rule, and commits any package the repository imports that only a build step generated ([7.2](#72-native-managers)). In a Go repository, CI builds with the build container's Go only. In a Rust repository, the change commits any missing `Cargo.lock`, and CI builds with `--locked` and the build container's Rust ([7.2](#72-native-managers)). An Azure CI trigger that includes every branch excludes `renovate/*` ([7.2](#72-native-managers)) |
| 9 | Each repository's owners | Close the open Dependabot pull requests once Renovate's Dependency Dashboard issue appears |

Renovate opens nothing in a repository but its onboarding pull request until step 8. Steps 1 to 7 come first, so the first Renovate pull requests clear `EasyCLA`, reach their reviewers, and are approved when they open. A pull request Renovate opened before step 1 keeps its failed `EasyCLA` status until someone comments `/easycla` on it.

A missed step shows only indirectly. A push of Renovate's own that the branch rules refuse appears only in its debug log ([7.2](#72-native-managers)), and a merge GitHub refuses leaves the pull request open with no comment. The change that adds a repository's `renovate.json` therefore records, in its description, the output of a read-only check run by someone with admin access to the repository:

| Check | Pass |
|-------|------|
| `gh api repos/{repo}/rules/branches/renovate%2Fcheck` | `[]`: no ruleset applies to a Renovate branch |
| `gh api graphql` for the repository's `branchProtectionRules` and their `matchingRefs` | No classic rule matches `renovate/check` |
| `gh api repos/{repo}/branches/{branch}/protection` for each branch Renovate targets | Where `restrictions` is set, its `apps` include `renovate` |
| `gh api orgs/sonic-net/installations`, as an organization owner | `renovate` and `renovate-approve` are installed with access to the repository |
| `go mod tidy -diff` in a copy of the repository alone, with nothing beside it and no build step run | Exits 0, so Renovate can update `go.sum` there ([7.2](#72-native-managers)) |

`sonic-mgmt-framework` adopted Renovate before this check existed. Its wildcard rule refused every `go.sum` fixup for five days, failing the workflow with "2 of 2 required status checks are expected", and `master` required a review `mssonicbld` could not bypass and branches up to date, so no security update merged. The pull requests showed only as blocked, and the Dependency Dashboard showed nothing. It moved to the pin in [7.2](#72-native-managers) in sonic-net/sonic-mgmt-framework#192.

A later repository repeats steps 2 (the team's Read access), 3, 5, 6, 8 and 9, and closes its onboarding pull request if one is open.

| Action | Effect |
|--------|--------|
| Remove the `automerge` rule from the preset | The robot merges nothing. Renovate still merges where a repository's own rule allows it |
| Remove a repository's Renovate merge rule, or uninstall `renovate-approve` | Renovate merges nothing in that repository, or anywhere |
| Remove a repository's `renovate.json`, or remove the repository from the installation | Renovate ignores that repository |
| Uninstall the app | Renovate stops everywhere |

### 10. Warmboot and Fastboot Design Impact

No direct impact. Renovate changes no code that runs at boot. A dependency bump passes the same warmboot and fastboot tests as any other pull request.

| Question | Answer |
|----------|--------|
| Added to the boot critical chain | Nothing |
| New CPU work on the boot path | None |
| Third party updates | Each is gated by the same pipeline as any other pull request |
| New service or container | None |

### 11. Memory Consumption

No change. Nothing is added to the image.

### 12. Restrictions/Limitations

| Limitation | Effect |
|------------|--------|
| Hand-pinned versions outside an ecosystem datasource are never classified as security updates | No advisory feed sits behind them. They are enabled by name and merged by a reviewer. See [7.5](#75-branch-policy) |
| `go.mod` understates what a build against a `sonic-mgmt-common` checkout uses | Renovate tidies against the pin, which trails `sonic-mgmt-common`'s default branch by one to three weeks, and the build can only raise a module above `go.mod`. A scanner reading `go.mod` sees older versions than the binary carries. See [7.2](#72-native-managers) |
| A release branch's `sonic-mgmt-common` pin stays at the branch cut | A backport that imports a newer package shows as an artifact error on the branch's security updates, and the pin is moved by hand. See [7.2](#72-native-managers) |
| The `go` directive is not updated | A standard library fix reaches SONiC through the build container's toolchain |
| Renovate merges only on its next run | A security update merges some time after its last check passes, not at once |
| `renovate-approve` approves a pull request only when it opens | One opened before its repository's merge rule waits for a reviewer, or for Renovate to open it again. See [7.6](#76-approval-and-merge) |
| A security fix to a v0 Go module can change its API | Go treats a v0 minor bump as compatible, and labels it accordingly. Security updates take the lowest fixed version, and the build and tests gate the merge |
| The FIPS Go pin depends on a SONiC FIPS build | Renovate lists the upstream patch release on the dashboard. The bump lands after SONiC publishes the package. A new Go minor is moved by hand, with `FIPS_GOLANG_MAIN_VERSION`. See [7.3](#73-hand-pinned-versions) |
| A vulnerable crate held only in a `Cargo.lock` gets no security pull request | Renovate raises security updates only for the crates a `Cargo.toml` names. Lock file maintenance moves the crate on `master` within a week, after review. On a release branch it is updated by hand. See [7.2](#72-native-managers) |
| Renovate reads only what a manifest declares | Versions resolved at build time belong to the version freeze pipeline |
| npm lockfiles inside Debian's Go and Ruby packages are not reached | They are part of Debian's packages and are not SONiC dependencies |
| Findings with no published fix are not addressed | Nothing can update to a fix that does not exist. Shipping less is the [EOL plan](../eol-planning/202611-eol-and-deprecation.md)'s remit |
| SONiC's Debian rebuilds are not covered | SBOM-driven triage covers them |
| A bump can conflict with a local patch | Components built from source with a patch series are out of scope. Ordinary updates to patched modules wait for dashboard approval. A security update to one opens on its own, with the `patched-module` label and no `automerge`, so a reviewer checks each patch. See [7.3](#73-hand-pinned-versions) |
| Renovate does not read the frozen `versions-py3` files | Half their entries are Debian's packages, which a pin cannot move (G5). The nightly freeze moves the rest on `master`. See the pip seam in [7.8](#78-existing-automation) |

### 13. Testing Requirements/Design

#### 13.1 Unit Test cases

Renovate ships no code into SONiC. The configuration is tested:

| Test | Method |
|------|--------|
| Configuration is valid | `npx --yes --package renovate -- renovate-config-validator` in CI on every change to a `renovate.json` or the preset |
| Custom managers match the right lines | A Renovate run against a fork finds `DOCKER_VERSION`, `CONTAINERD_IO_VERSION`, `FIPS_GOLANG_VERSION` and the `rustup` toolchain, and nothing else |
| Custom managers write the right value | In that run, each pushed branch's diff keeps the `~$IMAGE_DISTRO` suffix, `containerd.io` tracks its own package, and the new version exists in the apt index |
| FIPS Go takes patch releases only | With a newer Go patch and a newer Go minor both released, the Dependency Dashboard lists the patch for approval and not the minor, and the approved branch's diff keeps `-1+fips` and changes nothing else |
| The setup check catches a missed step | Run against a repository with a wildcard rule, a release branch that restricts pushes without the Renovate app, and an import of a package only a build step generates, the check in [9.5](#95-setup-steps) fails each row. After steps 5, 6 and 8, it passes |
| Release branch rules hold | A run against a release branch from `202611` on proposes security updates and hand-pinned patch and minor updates only |
| Grouping is correct | A run against `master` proposes one pull request per ecosystem per update type, and majors one per dependency |
| A major security update is not labeled `automerge` | A run against a fork pinned to a vulnerable version whose fix needs a major bump opens a pull request with the `security` label alone |
| A copy into `vendor/` moves with `go.mod` | Vendoring before and after the change gives an identical tree. After a `go.mod` bump to a module the build copies, the copied files match the new version |
| Patched modules wait for approval | The Dependency Dashboard lists each patched module under pending approval, and no pull request opens for it |
| The pin resolves without a checkout | In a copy of the repository alone, with no build step run, `go mod tidy -diff` exits 0. A Renovate update there leaves a `go.sum` the build accepts, with no artifact error |
| The pin leaves the build unchanged | With the pin at the commit `sonic-buildimage` checks out, the package built with the committed `replace` and with the build-time one holds the same files, and `go version -m` lists the same module versions in every binary |
| The pin moves weekly | Renovate opens one digest update for `sonic-mgmt-common` on a Monday, which `renovate-approve` approves and Renovate merges once its checks pass, and opens none on a release branch. On a base branch that requires branches to be up to date, the update is rebased when it falls behind, and still merges |
| Renovate merges a labeled update | A labeled security update is approved by `renovate-approve` when it opens, and Renovate merges it on a run after its last check passes. With a check the branch does not require left failing, or still running, it does not |
| `renovate-approve` approves only automerge pull requests | A major security update and an ordinary update get no approval |
| Renovate leaves a pushed branch alone | After someone else pushes to a labeled Renovate branch, Renovate does not merge it, and `renovate-approve` does not approve it again |
| Renovate merges on a release branch | On a release branch whose protection restricts pushes, with the Renovate app allowed, Renovate merges a labeled security update. Without the app on the list, GitHub refuses the merge |
| Release age | An ordinary update younger than 7 days is not proposed. A security update of the same age is |
| Lock file maintenance | A run against `master` in a Rust repository opens one lock file maintenance pull request, without `automerge`, whose CI builds with `--locked`. A run against a release branch opens none, and a Go repository gets none |
| Patched modules stay separate | A run with an ordinary update to a patched module and to an unpatched one in the same ecosystem opens the unpatched one in the ecosystem group, and lists the patched one alone for approval. A security update to a patched module opens in its own pull request, labeled `security` and `patched-module`, without `automerge` |
| Rebasing is limited to `automerge` updates | After a merge to `master`, a run rebases only the pull requests labeled `automerge` that are behind it, and any pull request that conflicts |
| Renovate can update its own branches | In each Renovate repository, a requested rebase pushes a new commit to the branch, and a branch whose pull request is closed or merged is deleted |
| The `go` directive stays within the build container's Go | A Renovate pull request that raises the directive past the container's Go fails CI, which downloads no toolchain. One that raises it within the container's Go passes |

#### 13.2 System Test cases

Every Renovate pull request runs the existing SONiC pipeline. No new test infrastructure is required.

| Test | Method |
|------|--------|
| A bumped image builds | `Azure.sonic-buildimage` on the pull request |
| A bumped image works | The existing regression suite |
| Warm and fast reboot are unaffected | The existing warmboot and fastboot tests |
| Fixable findings go down | An SBOM scan of each release branch build, compared run to run |

The scan and the comparison:

```bash
make ENABLE_SBOM=y target/sonic-broadcom.bin
python3 scripts/sbom_vuln_scan.py --vex vex/ target/sonic-broadcom.bin.cdx.json
python3 scripts/sbom_vuln_diff.py <previous>.vuln.json target/sonic-broadcom.bin.vuln.json
```

### 14. Open/Action items

Owners come from `CODEOWNERS` where a repository has one, and from the organization or Foundation for an account or policy setting. `sonic-pipelines` has no `CODEOWNERS`, so its items go to its maintainers. A suggested owner has not agreed to the work.

| # | Item | Touches | Suggested owner |
|---|------|---------|-----------------|
| 1 | Install the Renovate app on all `sonic-net` repositories, and close its onboarding pull requests unmerged | Organization settings | Organization administrators |
| 2 | Create the `sonic-security-wg` team, as set out in [7.7](#77-reviewers) | Organization settings | Organization administrators, Security WG |
| 3 | Give `renovate[bot]` the EasyCLA treatment `mssonicbld` has | EasyCLA configuration | SONiC Foundation EasyCLA administrators |
| 4 | Remove the merge robot's Renovate support from `automation-pr-scan.yml`: the author filter, the check and commit evaluation, and the approval of waiting runs ([7.6](#76-approval-and-merge)) | `sonic-pipelines` | `sonic-pipelines` maintainers, Security WG |
| 5 | Update the description of the preset's `automerge` rule, which still names the merge robot ([9.4](#94-renovate-configuration)) | `renovate/default.json` | `sonic-pipelines` maintainers |
| 6 | Land the shared preset at `renovate/default.json` | `sonic-pipelines` | `sonic-pipelines` maintainers |
| 7 | Add the release manager reviewer rule in [7.7](#77-reviewers) once the `release-manager-202611` team exists | `renovate/default.json` | Security WG, 202611 release manager |
| 8 | Merge the pip build hook change, then the preset's Python managers (sonic-net/sonic-buildimage#30963, sonic-net/sonic-pipelines#262) | `src/sonic-build-hooks/`, `renovate/default.json` | `@sonic-net/sonic-build`, `sonic-pipelines` maintainers |
| 9 | Confirm the FIPS Go release cadence, so the toolchain pin has something to track | `src/sonic-fips/`, `rules/sonic-fips.mk` | `@sonic-net/sonic-build` |
| 10 | Stand up SBOM-driven triage for the Debian packages SONiC rebuilds | — | Security WG |
| 11 | Confirm the release branch policy in [7.5](#75-branch-policy) | `renovate.json` | Security WG |
| 12 | Add the Renovate app to the push allowances of each release branch that restricts pushes, once its release manager agrees to Renovate merging security patch and minor updates ([7.6](#76-approval-and-merge), [9.5](#95-setup-steps) step 5) | Repository settings | Organization administrators, each release manager |
| 13 | Start a branch's freeze when the Debian security tracker shows a fix newer than a pinned version (G1 in [7.9](#79-gaps-outside-both)) | `sonic-buildimage` `.azure-pipelines/` | `@sonic-net/sonic-build`, Security WG |
| 14 | Alert when a branch's Debian snapshot is older than a set age (G2) | `sonic-buildimage` `.azure-pipelines/` | `@sonic-net/sonic-build` |
| 15 | Build or drop every pinned container and distribution the freeze does not build (G3) | `scripts/versions_manager.py`, `.azure-pipelines/` | `@sonic-net/sonic-build` |
| 16 | One version tree for `docker-ptf`, recording what it ships after its `apt-get upgrade` (G4) | `dockers/docker-ptf/`, `.azure-pipelines/docker-ptf.yml` | `docker-ptf` owners |
| 17 | Keep Debian-installed Python packages apart from PyPI ones in `versions-py3` (G5) | `src/sonic-build-hooks/` | `@sonic-net/sonic-build` |
| 18 | Keep a list of known bundled library copies for SBOM triage (G6), with item 10 | — | Security WG |
| 19 | Scan the build and test images, or record that they are accepted unscanned (G7) | `.azure-pipelines/` | `@sonic-net/sonic-build`, Security WG |
| 20 | Apply the distribution's security updates in every image built on a base that is not Debian, starting with `docker-dash-engine` (G8) | `platform/vs/docker-dash-engine/Dockerfile.j2` | `@sonic-net/DASH-maintainer` |
| 21 | Install the `renovate-approve` app on all `sonic-net` repositories ([7.6](#76-approval-and-merge)) | Organization settings | Organization administrators |
| 22 | Add the Renovate merge rule to each repository ([7.6](#76-approval-and-merge)) | `renovate.json` | Each repository's owners |
| 23 | Move `sonic-gnmi` and `sonic-mgmt-framework` to the published `sonic-mgmt-common` pin and remove their `go.sum` workflows ([7.2](#72-native-managers)): sonic-net/sonic-gnmi#906, sonic-net/sonic-mgmt-framework#192. Then drop the `sonic-automation` review bypass on `sonic-mgmt-framework` `master`, and require branches there to be up to date again | `go.mod`, `Makefile`, `renovate.json`, repository settings | Each repository's owners |
