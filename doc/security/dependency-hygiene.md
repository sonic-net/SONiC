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
  - [7.9 Rollout](#79-rollout)
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
| 0.3 | 2026-10-22 | Brad House (Nexthop) | Go repositories first. Security update grouping, patched modules, local `replace` directives, the `go` directive, DCO, and the setup steps. Release branches by pattern, release age in the preset, the robot commit check, copies into `vendor/` that follow `go.mod`, no unattended merge for patched modules, branch protection on Renovate branches, no fixup that undoes the update, and the `go` directive and held-module checks. |

### 2. Scope

[Renovate](https://docs.renovatebot.com/) runs across the `sonic-net` GitHub organization and updates third party dependencies.

In scope:

- Dependencies declared in a checked-in manifest: `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py`, GitHub Actions workflows, Dockerfiles.
- Versions SONiC pins by hand in its own build scripts, such as Docker and the OpenTelemetry Collector.
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
| SBOM | Software Bill of Materials, the list of everything in a build |
| WG | Working group |

### 4. Overview

Most third party versions in SONiC move only when another change forces them. Renovate opens a pull request when upstream publishes a release, and the existing test suite decides whether it is safe.

Each source of third party code has one owner:

| Source | Where the version is set | Kept current by |
|--------|--------------------------|-----------------|
| Go, Rust and Python modules | `go.mod`, `Cargo.toml`, `requirements.txt`, `setup.py` | Renovate, native managers |
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
upstream release ──▶ Renovate ──▶ pull request ──▶ checks ──┬─▶ automerge label, all checks pass ──▶ merge robot merges
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

A repository adopts Renovate through a change that adds its `renovate.json`, reviewed like any other. Renovate's own onboarding pull request ("Configure Renovate") is never merged: it carries `config:recommended` alone, without the shared preset, the reviewers or the patched-module rules, and it leaves Dependabot running.

The app is installed on all repositories, and opens an onboarding pull request in each one without a `renovate.json`. Each onboarding pull request is closed without merging. Renovate does not reopen one that was closed unmerged, and picks a repository up on its next run once the repository's own `renovate.json` merges. A repository created later gets its own onboarding pull request, closed the same way.

The repositories that are mostly Go come first: `sonic-mgmt-common` and `sonic-gnmi`. Renovate takes every manager in [7.2](#72-native-managers) in them, not only `gomod`.

#### 7.2 Native managers

| Manager | Reads | Enabled |
|---------|-------|---------|
| `gomod` | `go.mod` | Yes |
| `cargo` | `Cargo.toml` | Yes |
| `github-actions` | `.github/workflows/*.yml` | Yes |
| `dockerfile` | `Dockerfile` | Yes |
| `pip_requirements`, `setup-py` | `requirements.txt`, `setup.py` | No, until the pip constraint seam is resolved. See [7.8](#78-existing-automation) |
| `git-submodules` | `.gitmodules` | No. The submodule update pipeline owns submodule pointers |

`gomod` runs `go mod tidy` after each update, and rewrites import paths on a major bump.

**The `go` directive.** Each Go repository lists `go` in `ignoreDeps`. A standard library vulnerability makes Renovate propose raising the `go` directive, and a security update overrides every package rule, so only `ignoreDeps` stops it. The directive cannot move ahead of the Go in the build container, and a standard library fix reaches SONiC through that toolchain.

`ignoreDeps` does not stop `go get` from raising the directive. Renovate runs `go get` with the newest Go the directive allows, and raises the directive when an update needs a newer Go. CI downloads whatever toolchain `go.mod` names, so it passes. Each Go repository therefore checks its Renovate pull requests: where Renovate updates `go.sum` itself, a check fails a pull request whose `go` directive differs from the merge base; where the `go.sum` workflow runs, the workflow fails instead (see below).

**Local `replace` directives.** To update `go.sum`, Renovate runs `go get` in a checkout of the one repository. A `replace` that points outside that repository, such as `sonic-gnmi` replacing `sonic-mgmt-common` with `../sonic-mgmt-common`, makes `go get` fail, and `go.sum` is left behind. Renovate's `gomodMassage` option comments out the whole `replace` block, which also drops the pins that patched modules depend on, so it is not used.

Such a repository carries a workflow that runs on Renovate pull requests:

| Step | Work |
|------|------|
| 1 | Check out the repository, and the replaced repository beside it at the pull request's base branch, as its CI pipeline does |
| 2 | Run `go mod tidy`, and commit any change to `go.mod` and `go.sum` to the Renovate branch through the GitHub API, as `github-actions[bot]` |
| 3 | Dispatch the repository's GitHub Actions checks on the new commit |

A commit made through the API is signed by GitHub, which the merge robot requires of every commit on a Renovate pull request ([7.6](#76-approval-and-merge)); a `git push` would leave it unsigned. A commit made with `GITHUB_TOKEN` starts no workflow runs, and `workflow_dispatch` is the exception, so step 3 dispatches them. A check that also builds the replaced repository takes its branch as a dispatch input. The workflow needs no secret. `renovate.json` lists `github-actions[bot]` in `gitIgnoredAuthors`, so Renovate keeps rebasing the branch, and suppresses Renovate's artifact error comments, which every such pull request would otherwise carry.

`go mod tidy` raises the `go` directive when a dependency needs a newer Go. Step 2 runs with `GOTOOLCHAIN=local`, and fails instead of committing when the directive changes, so the pull request shows that the update needs a newer build container.

Renovate cannot rewrite import paths in such a repository either, so a major update that changes the module path only changes `go.mod`. `go mod tidy` then drops the new requirement, which nothing imports, and requires the old module again. Committing that would undo the update, and Renovate would push it again, in a loop. Step 2 therefore compares `go.mod` at the merge base, at the head and after tidy, and fails instead of committing when tidy removes a requirement the update changed or requires again a module the update removed. The pull request then shows that the code has to change with the update.

Step 3 also runs when the branch is already tidy and its head is a fixup commit, so rerunning a job that committed but failed before dispatching still starts the checks.

**Branch protection on Renovate branches.** Step 2 needs to add a commit to an existing Renovate branch. A branch protection rule that matches every branch, rather than only the default and release branches, rejects that commit when it requires a pull request or status checks: the commit is not a pull request, and a new commit cannot have passed the required checks. Such a rule does not block branch creation, so Renovate's own branches still appear, but nothing can be added to them afterwards. Exempting `github-actions[bot]` from the pull request requirement is not enough, because the required checks still apply. In such a repository the protection is moved to a branch ruleset that includes all branches and excludes `renovate/**`, with the same rules and the repository admin role as its bypass, and the wildcard rule is deleted ([9.5](#95-setup-steps)). Write access to `renovate/**` opens no merge path, because the merge robot requires every commit on a Renovate pull request to be signed and authored by `renovate[bot]` or `github-actions[bot]` ([7.6](#76-approval-and-merge)), and the default branch keeps its own protection.

Step 2 also brings in any drift between the two repositories' `go.mod` files. The CI pipeline's own `go mod tidy` applies the same change on every build.

#### 7.3 Hand-pinned versions

A version a person pins in a build script has a custom manager entry beside it.

| Variable | File | Datasource | Merge |
|----------|------|------------|-------|
| `DOCKER_VERSION` (`docker-ce`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| `CONTAINERD_IO_VERSION` (`containerd.io`) | `build_debian.sh` | `deb`, `download.docker.com` | Reviewer |
| `OTEL_VERSION` | `dockers/docker-sonic-otel/Dockerfile.j2` | `github-releases` | Reviewer |
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

**OpenTelemetry Collector.** The built-in `dockerfile` manager does not read a `.j2` file and has no datasource for a bare `ARG`:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^dockers/docker-sonic-otel/Dockerfile\\.j2$/"],
  "matchStrings": ["ARG OTEL_VERSION=(?<currentValue>\\S+)"],
  "depNameTemplate": "open-telemetry/opentelemetry-collector-releases",
  "datasourceTemplate": "github-releases",
  "extractVersionTemplate": "^v(?<version>.*)$"
}
```

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

**FIPS Go toolchain.** `FIPS_GOLANG_VERSION` names a FIPS package SONiC publishes to its own mirror, which exists only after SONiC builds it. Renovate lists the upstream Go release on the Dependency Dashboard and opens a pull request only when someone approves it there:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^rules/sonic-fips\\.mk$/"],
  "matchStrings": ["FIPS_GOLANG_VERSION = (?<currentValue>\\d+\\.\\d+\\.\\d+)"],
  "depNameTemplate": "go",
  "datasourceTemplate": "golang-version"
}
```

```json
{
  "matchManagers": ["custom.regex"],
  "matchDatasources": ["golang-version"],
  "dependencyDashboardApproval": true
}
```

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

A patched module's version can also move without its own update. `go get` raises any module the update needs a newer version of, so a module whose newer releases require newer patched modules is held for approval too, even when it is not patched itself. `sonic-mgmt-common` holds `openconfig/gnmi` because its newer versions require newer `goyang` and `ygot`. Where Renovate updates `go.sum` itself, a check on each Renovate pull request fails it when a held module changes version and the pull request is not that module's own update; the module's own pull request names it in its title. The check reads the held modules from the rule that adds the `patched-module` label, so it never needs its own list. Where the `go.sum` workflow in [7.2](#72-native-managers) runs instead, the build shows whether the patches still apply.

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

**Security classification.** Renovate classifies a security update from GitHub vulnerability alerts and OSV, both keyed by ecosystem:

| Lane | Datasource | Classified as security |
|------|------------|------------------------|
| `gomod`, `cargo`, `pip` | Ecosystem registry | Yes |
| A custom manager on an ecosystem datasource | Ecosystem registry | Yes |
| Docker, containerd | `deb` | No |
| OpenTelemetry Collector, Rust | `github-releases` | No |
| FIPS Go | `golang-version` | No |

A custom manager on any other datasource has no advisory feed behind it. A release branch therefore enables hand-pinned updates by name, and a reviewer decides whether each one is needed.

**The `automerge` label.** Renovate applies the `vulnerabilityAlerts` object to every security update with precedence over all package rules. That object sets the `security` label and the grouping in [7.4](#74-pull-request-grouping), and never `automerge`. A package rule adds `automerge` to security updates that are patch or minor:

```json
{
  "vulnerabilityAlerts": { "enabled": true, "labels": ["security"] },
  "packageRules": [
    {
      "description": "Security updates below a major version merge unattended, unless a repository marks the module patched-module",
      "matchJsonata": ["isVulnerabilityAlert = true and $not('patched-module' in addLabels)"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"]
    }
  ]
}
```

A security update that needs a major version opens with the `security` label alone and waits for a reviewer. So does one to a module a repository marks `patched-module` ([7.3](#73-hand-pinned-versions)). Renovate adds the vulnerability rules after the preset's own. Its first pass over the rules sets the security flag, and a later pass, which starts from that result, matches the `automerge` rule on the flag and the update type.

**Release branch rules.** Before a lookup, Renovate does not yet know the update type, and a rule that disables a dependency at that stage removes it before any later rule can re-enable it. The release branch rules therefore disable every manager except `custom.regex` up front, and then disable `custom.regex` majors once the update type is known. A security update overrides both.

**Release age.** The preset holds every update until its release is 7 days old, so a release that is withdrawn or compromised soon after publication is not proposed. A security update is not held, because `vulnerabilityAlerts` resets `minimumReleaseAge`.

#### 7.6 Approval and merge

Renovate cannot approve its own pull requests. The existing merge robot merges them.

| | |
|---|---|
| `renovate.json` | Applies the `automerge` label as set out in [7.5](#75-branch-policy). Renovate's own `automerge` setting stays off |
| Merge robot | Lists Renovate pull requests carrying both the `automerge` and `security` labels, evaluates their checks, and merges the ones that pass with `gh pr merge --admin`, pinned to the head commit it evaluated. One that fails is left for its reviewers, without the cherry-pick retry or escalation |
| Branch protection | Depends on whether the branch's protection applies to administrators. See below |

Which pull requests merge is decided in `renovate.json`, by the label. Whether a labeled pull request merges is decided by the robot, and by branch protection where it applies to administrators.

`--admin` bypasses what an administrator may bypass on that branch:

| Protection applies to administrators | Review requirement | Required status checks |
|--------------------------------------|--------------------|------------------------|
| No | Bypassed | Bypassed |
| Yes | Enforced, unless `mssonicbld` is allowed to bypass required pull requests | Enforced |

The robot therefore enforces the checks itself, whatever the branch setting. Where protection applies to administrators, `mssonicbld` needs the pull request bypass on that branch, or the robot cannot merge there.

Robot check evaluation is a prerequisite for the `automerge` label. For a Renovate pull request, the robot merges only when every check it reads has completed successfully:

| Case | Required behavior |
|------|-------------------|
| A check still in progress | Not merged |
| A check that timed out, needs action, or failed to start | Not merged |
| A check that succeeded, was skipped, or was neutral | Passes |
| A commit status (legacy status context) other than success | Not merged |
| An empty check list | Not merged |
| A commit not signed by GitHub, or authored by anyone but the Renovate bot or `github-actions[bot]` | Not merged |
| A required status check of the base branch that has not reported | Not merged |
| No SONiC build check (`Azure.sonic-*` or `sonic-net.sonic-*`) has reported | Not merged |
| The head commit moved after the checks were read | Not merged |
| A check named `vulnerability scan` | Evaluated |
| A check named `OPTIONAL` | Skipped |

The labels and the pull request author do not say who wrote the commits, and anyone with write access can push to a Renovate branch. The robot therefore reads every commit on the pull request. GitHub signs a commit the Renovate bot makes through its API, and a `go.sum` fixup made the same way. It does not sign a pushed commit, whatever author the commit names.

The robot reads the base branch's required status checks from the branch API, so a merge never waits on a check list kept in the robot. The build check covers a branch that requires only `EasyCLA`, where the build might not yet have registered when the robot runs. The robot's evaluation of every other pull request is unchanged. The strict evaluation lands in the same `sonic-pipelines` change as the preset, so no Renovate pull request carries the label before it. Both labels are required, so a stray `automerge` label on an ordinary Renovate pull request merges nothing.

`EasyCLA` is a required check, and is a commit status. A pull request from the Renovate bot clears it the same way one from `mssonicbld` does. So does a commit from `github-actions[bot]`, which authors the `go.sum` fixups in [7.2](#72-native-managers).

Repositories that require DCO sign-off reject unsigned commits, so the preset sets `commitBody` to a `Signed-off-by` line for the Renovate bot.

Alternatives considered:

| Option | Not chosen because |
|--------|--------------------|
| [`renovate-approve`](https://github.com/apps/renovate-approve) app | Adds a second app and an admin setting on every repository. It is the path back if the robot proves unsuitable |
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

Three pipelines already keep parts of the tree current, all acting as `mssonicbld`. Renovate is added beside them.

| Pipeline | Owns | Where it lives |
|----------|------|----------------|
| Version freeze | What the build resolves: `apt` and `pip` versions per platform, architecture and container, and the Debian snapshot timestamp | `sonic-buildimage`, `.azure-pipelines/azure-pipelines-UpgrateVersion.yml` |
| Submodule update | Which commit of each submodule `sonic-buildimage` builds | `sonic-pipelines`, `azure-pipelines/submodule-update.yml` |
| Merge robot | Merging labeled bot pull requests | `sonic-pipelines`, `azure-pipelines/automation-pr-scan.yml` |
| Renovate | What manifests declare, and hand-pinned versions | Each repository's `renovate.json` |

**Dependabot.** Dependabot has three parts, and each is handled when a repository adopts Renovate:

| Part | With Renovate | Reason |
|------|---------------|--------|
| Dependabot alerts | On | Renovate reads them for GitHub's vulnerability data |
| Dependabot security updates | Off | Each vulnerability would get a pull request from both bots |
| Dependabot version updates (`.github/dependabot.yml`) | Removed in the change that adds `renovate.json` | Renovate does the same work. The preset's `minimumReleaseAge` replaces a cooldown it set |

Open Dependabot pull requests are closed once Renovate runs; Renovate opens its own.

**The pip seam.** The pip build hook in `src/sonic-build-hooks/scripts/buildinfo_base.sh` passes the frozen `versions-py3` file to every `pip install` as a constraint file. It releases a package from the constraint only when an exact version appears on the command line, and it does not read `-r requirements.txt`. A Renovate bump to a `requirements.txt` therefore conflicts with the frozen constraint until the next freeze.

| Resolution | Effect |
|------------|--------|
| Exclude `pip_requirements` and `setup-py` | Python stays with the freeze pipeline. Chosen for the first phases |
| Teach the build hook to read requirements files | Removes the seam |
| Order the Renovate pull request behind a re-freeze | Keeps both, with a dependency between them |

#### 7.9 Rollout

| Phase | Work |
|-------|------|
| 1 | The shared preset and the robot check evaluation in [7.6](#76-approval-and-merge). `sonic-mgmt-common` and `sonic-gnmi` on `master`, including the `automerge` label on security updates |
| 2 | Docker, containerd and OpenTelemetry custom managers in `sonic-buildimage`, on `master` |
| 3 | Native managers on `master` in `sonic-buildimage` and the remaining owned repositories holding `go.mod` or `Cargo.toml` |
| 4 | Rust and FIPS Go custom managers |
| 5 | Remaining owned repositories, and the `202611` branch |
| 6 | A resolution for the pip seam |

The Go repositories come first because they need no custom manager, and because the robot check evaluation is a small, contained change to land beside them.

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
  "commitBody": "Signed-off-by: {{{gitAuthor}}}",
  "enabledManagers": ["gomod", "cargo", "github-actions", "dockerfile", "custom.regex"],
  "postUpdateOptions": ["gomodTidy", "gomodUpdateImportPaths"],
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
      "description": "Security updates below a major version merge unattended, unless a repository marks the module patched-module",
      "matchJsonata": ["isVulnerabilityAlert = true and $not('patched-module' in addLabels)"],
      "matchUpdateTypes": ["patch", "minor"],
      "addLabels": ["automerge"]
    },
    {
      "description": "FIPS Go is published by SONiC; open only on dashboard approval",
      "matchManagers": ["custom.regex"],
      "matchDatasources": ["golang-version"],
      "dependencyDashboardApproval": true
    }
  ]
}
```

This is the file committed to `sonic-pipelines`. Its `description` names this document. Each Go repository adds `ignoreDeps` for the `go` directive, and a rule and a `vulnerabilityAlerts.groupName` for its patched modules ([7.3](#73-hand-pinned-versions)). A repository with a local `replace` also adds `gitIgnoredAuthors`, `suppressNotifications` and the workflow in [7.2](#72-native-managers). Any other Go repository adds the `go.mod` check in [7.2](#72-native-managers) and [7.3](#73-hand-pinned-versions).

#### 9.5 Setup steps

| Step | Who | Work |
|------|-----|------|
| 1 | SONiC Foundation EasyCLA administrators | Add `renovate[bot]` and `github-actions[bot]` to the EasyCLA approved list, as `mssonicbld` is |
| 2 | Organization administrator, Security WG | Create the `sonic-security-wg` team as set out in [7.7](#77-reviewers): visible, no parent team, the public Working Group membership with at least one member as team maintainer, and Read on each repository Renovate runs in |
| 3 | Each repository's administrators | Leave Dependabot alerts on, and turn Dependabot security updates off. See [7.8](#78-existing-automation) |
| 4 | `sonic-pipelines` maintainers | Merge `renovate/default.json` and the `automation-pr-scan.yml` change: the Renovate author filter, and the check evaluation in [7.6](#76-approval-and-merge). Add each Renovate repository to the robot's `repos` parameter if it is not already listed |
| 5 | Organization administrator | Where branch protection applies to administrators, allow `mssonicbld` to bypass required pull requests on the branches Renovate targets ([7.6](#76-approval-and-merge)) |
| 6 | Each repository's administrators | Where a repository carries a workflow from [7.2](#72-native-managers) and a branch protection rule matches every branch, replace that rule with a branch ruleset that includes all branches, excludes `renovate/**`, keeps the same rules, and lets the repository admin role bypass, so the workflow can commit to Renovate branches |
| 7 | Organization administrator | Install the app at <https://github.com/apps/renovate> on all repositories, accepting the requested permissions, which include read access to Dependabot alerts, and close the onboarding pull requests without merging ([7.1](#71-installation-scope)) |
| 8 | Each repository's owners | Merge a `renovate.json` extending the preset, the removal of `.github/dependabot.yml`, and any workflow from [7.2](#72-native-managers) |
| 9 | Each repository's owners | Close the open Dependabot pull requests once Renovate's Dependency Dashboard issue appears |

Renovate opens nothing in a repository but its onboarding pull request until step 8. Steps 1 to 6 come first, so the first Renovate pull requests clear `EasyCLA`, reach their reviewers, and can be merged by the robot.

A later repository repeats steps 2 (the team's Read access), 3, 5, 6, 8 and 9, and closes its onboarding pull request if one is open.

| Action | Effect |
|--------|--------|
| Remove the `automerge` rule from the preset | Nothing merges unattended |
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
| Renovate cannot update `go.sum` past a `replace` that points outside the repository | A workflow in that repository tidies it and re-dispatches its checks. See [7.2](#72-native-managers) |
| The `go` directive is not updated | A standard library fix reaches SONiC through the build container's toolchain |
| The merge robot merges without a review | Where branch protection does not apply to administrators it also bypasses the required checks, so the robot evaluates them itself. See [7.6](#76-approval-and-merge) |
| A security fix to a v0 Go module can change its API | Go treats a v0 minor bump as compatible, and labels it accordingly. Security updates take the lowest fixed version, and the build and tests gate the merge |
| The FIPS Go pin depends on a SONiC FIPS build | Renovate lists the upstream release on the dashboard. The bump lands after SONiC publishes the package |
| Renovate reads only what a manifest declares | Versions resolved at build time belong to the version freeze pipeline |
| npm lockfiles inside Debian's Go and Ruby packages are not reached | They are part of Debian's packages and are not SONiC dependencies |
| Findings with no published fix are not addressed | Nothing can update to a fix that does not exist. Shipping less is the [EOL plan](../eol-planning/202611-eol-and-deprecation.md)'s remit |
| SONiC's Debian rebuilds are not covered | SBOM-driven triage covers them |
| A bump can conflict with a local patch | Components built from source with a patch series are out of scope. Ordinary updates to patched modules wait for dashboard approval. A security update to one opens on its own, with the `patched-module` label and no `automerge`, so a reviewer checks each patch. See [7.3](#73-hand-pinned-versions) |
| Python is excluded | See the pip seam in [7.8](#78-existing-automation) |

### 13. Testing Requirements/Design

#### 13.1 Unit Test cases

Renovate ships no code into SONiC. The configuration is tested:

| Test | Method |
|------|--------|
| Configuration is valid | `npx --yes --package renovate -- renovate-config-validator` in CI on every change to a `renovate.json` or the preset |
| Custom managers match the right lines | A Renovate run against a fork finds `DOCKER_VERSION`, `CONTAINERD_IO_VERSION`, `OTEL_VERSION`, `FIPS_GOLANG_VERSION` and the `rustup` toolchain, and nothing else |
| Custom managers write the right value | In that run, each pushed branch's diff keeps the `~$IMAGE_DISTRO` suffix, `containerd.io` tracks its own package, and the new version exists in the apt index |
| Release branch rules hold | A run against a release branch from `202611` on proposes security updates and hand-pinned patch and minor updates only |
| Grouping is correct | A run against `master` proposes one pull request per ecosystem per update type, and majors one per dependency |
| A major security update is not labeled `automerge` | A run against a fork pinned to a vulnerable version whose fix needs a major bump opens a pull request with the `security` label alone |
| A copy into `vendor/` moves with `go.mod` | Vendoring before and after the change gives an identical tree. After a `go.mod` bump to a module the build copies, the copied files match the new version |
| Patched modules wait for approval | The Dependency Dashboard lists each patched module under pending approval, and no pull request opens for it |
| The `go.sum` workflow produces a tidy module | With the replaced repository checked out beside it, `go mod tidy` after a Renovate bump leaves a `go.sum` the build accepts. On a Renovate pull request, the fixup commit is signed by GitHub, and is followed by dispatched runs of each GitHub Actions check |
| Robot check evaluation | The evaluation function, run against each case in [7.6](#76-approval-and-merge) and against the check list and required checks of a live bot pull request, passes only when every check has completed successfully, every required check has reported, and a build check is present. A list holding only `EasyCLA` does not pass |
| Robot commit check | The robot declines a Renovate pull request carrying a pushed commit, including one that names the Renovate bot as its author, and merges one whose commits are all GitHub-signed commits from the Renovate bot and `github-actions[bot]` |
| Release age | An ordinary update younger than 7 days is not proposed. A security update of the same age is |
| Patched modules stay separate | A run with an ordinary update to a patched module and to an unpatched one in the same ecosystem opens the unpatched one in the ecosystem group, and lists the patched one alone for approval. A security update to a patched module opens in its own pull request, labeled `security` and `patched-module`, without `automerge` |
| The `go` directive is never raised | A `go.sum` workflow run on a bump that needs a newer Go fails, and pushes nothing |

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
| 3 | Give `renovate[bot]` and `github-actions[bot]` the EasyCLA treatment `mssonicbld` has | EasyCLA configuration | SONiC Foundation EasyCLA administrators |
| 4 | Land the merge robot check evaluation in [7.6](#76-approval-and-merge). Prerequisite for the `automerge` label | `sonic-pipelines` | `sonic-pipelines` maintainers, Security WG |
| 5 | Land the Renovate author filter in the merge robot, and keep each Renovate repository in its `repos` parameter | `sonic-pipelines` | `sonic-pipelines` maintainers |
| 6 | Land the shared preset at `renovate/default.json` | `sonic-pipelines` | `sonic-pipelines` maintainers |
| 7 | Add the release manager reviewer rule in [7.7](#77-reviewers) once the `release-manager-202611` team exists | `renovate/default.json` | Security WG, 202611 release manager |
| 8 | Choose a resolution for the pip seam | `src/sonic-build-hooks/` | `@sonic-net/sonic-build` |
| 9 | Confirm the FIPS Go release cadence, so the toolchain pin has something to track | `src/sonic-fips/`, `rules/sonic-fips.mk` | `@sonic-net/sonic-build` |
| 10 | Stand up SBOM-driven triage for the Debian packages SONiC rebuilds | — | Security WG |
| 11 | Confirm the release branch policy in [7.5](#75-branch-policy) | `renovate.json` | Security WG |
