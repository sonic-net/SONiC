<!-- omit in toc -->
# SONiC OS & SONiC Docker Images Versioning

<!-- omit in toc -->
#### Rev 0.1

<!-- omit in toc -->
## Table of Content
- [SONiC Package API](#sonic-package-api)
- [SONiC Package Releases](#sonic-package-releases)
- [Conventional Commits](#conventional-commits)
- [SONiC Package Versioning Rules](#sonic-package-versioning-rules)
- [SONiC Packages Versioning](#sonic-packages-versioning)
- [Base OS versioning](#base-os-versioning)
- [Base OS API that a package uses](#base-os-api-that-a-package-uses)
- [Open Questions](#open-questions)

<!-- omit in toc -->
## List of Figures

### Revision

| Rev |     Date    |       Author            | Change Description                   |
|:---:|:-----------:|:-----------------------:|--------------------------------------|
| 0.1 | 02/2021     | Stepan Blyshchak        | Initial Proposal                     |

### Overview

This document provides guidelines on how to do versioning for SONiC Docker Images using to semantic versioning strategy.

<!-- omit in toc -->
#### Motivation

With new SONiC Application Extension Infrastructure SONiC Dockers and SONiC Base OS can be seperated and distributed individually.
SONiC Dockers (aka SONiC Packages) can be installed, upgraded invididually from other. This creates a new problem which needs to be
solved - compatibility between dependend Dockers and host OS. SONiC Application Extension Infrastructure provides a way to specify
the package version dependency using semantic versioning (https://semver.org). This document provides a guideline on how to increment
version numbers correctly on releases.

## SONiC Package API

First of all, a clear definition of what is package API needs to be provided:

SONiC package API is Redis DB interface including:
  - CONFIG DB, APPL DB, STATE DB tables schema provided by this package

If any other kind of API is exposed by the SONiC Package it should be accounted as package API.

## SONiC Package Releases

As of today (202012 release), all SONiC Docker Images are released together with SONiC OS. With SONiC Application Extension
Infrastructure SONiC Dockers are released independently. On every release an increment in package version number is required.
The exact number in version that needs to be incremented depends on the type of changes comparing to previously released
package.

Types of changes:
  - Breaking change: backwards incompatible change; reflects in ***major*** version number
  - New functionality: backward compatible change; reflects in ***minor*** version number
  - Bug fixes or enhancement; reflects in ***patch*** version number

## Conventional Commits

In order to help ***package maintainers*** to understand whether a breaking change was introduced
comparing to previous release or a new functionality was included all SONiC repositories *can*
follow conventional commits (https://www.conventionalcommits.org/en/v1.0.0/):

e.g:

```
feat: Introduce new methods in ConsumerTable

BREAKING CHANGE: this feature breaks the Consumer/Producer based IPC
```

## SONiC Package Versioning Rules

- A package is published with a bug fix or enhancement whenever ***package maintainer decides*** to do so.
- Manual version update ***is required*** when SONiC Package releases
- On package release ***package maintainer must*** check package API compatibility comparing to previously released package
- In case API changed comparing to previous release ***package maintainer must*** must increment major version
- In case new backwards compatible changes were made comparing to previous release ***package maintainer must*** must increment minor version
- *Patch* version is updated on changes which do not introduce any changes to the API
- On package release ***package maintainer can*** update package dependencies

**NOTE**: SONiC package version has no correlation to a SONiC release. While keeping API of dependencies compatible a package can work across different SONiC releases.

Package maintainer may choose to maintain a single repository and have there packages that can work accross different releases or maintain a repository per SONiC release.

***package maintainer can*** update *default-reference* in package.json in SONiC buildimage to point to a default version which will be used when user installs a package.

## Base OS versioning

## Base OS API that a package uses

- SONiC utilities
    - This is a ***sonic-utilities contributor responsibility***
- Dependence on a new kernel functionality must be recorded in minor version
    - This is a ***package maintainer responsibility***
    E.g.: a patch in kernel to support 3-tuple conntrack entries that NAT docker depends on.
- SONiC host service (D-Bus based communication)
- etc.


# Examples

1. Changed the API and optionally introduced new API or other changes not related to API:

```
major.minor.patch => (major + 1).minor.patch
```

2. Introduced new API and optionally other changes:

```
major.minor.patch => major.(minor + 1).patch
```

3. Enhancements and bug fixes, SONiC SDK update, manifest update, etc.:

```
major.minor.patch => major.minor.(patch + 1)
```

*NOTE*: It is possible to maintain same version in two repositories, e.g. for two different SONiC releases:

azure/sonic-foo-202106:1.2.3
azure/sonic-foo-202112:1.2.3

4. Dependency changes

Considering the following package foo:

```json
{
  "package": {
    "name": "foo",
    "version": "1.2.3",
    "depends": [
      {
        "name": "swss",
        "version": "^1.0.0"
      }
    ]
  }
}
```

4.1 Package foo depends on swss API ^1.0.0. Now if swss upgrades to 2.0.0, but foo uses only few tables from swss APPL DB that didn't change a new package of foo has to be released, updating package dependencies:

foo's manifest:

```json
{
  "package": {
    "name": "foo",
    "version": "1.2.4",
    "depends": [
      {
        "name": "swss",
        "version": "^1.0.0,^2.0.0"
      }
    ]
  }
}
```

4.2 In case swss tables used by foo have changed, foo has to change by releasing a new package with updated dependency:

```json
{
  "package": {
    "name": "foo",
    "version": "1.2.4",
    "depends": [
      {
        "name": "swss",
        "version": "^2.0.0"
      }
    ]
  }
}
```

4.3 In case swss tables used by foo have changed, foo's developer might still want to support swss 1.0.0. In that case infrastructure can pass dependencies versions in environment variables when starting the container, foo's application can read the environment "SWSS_VERSION" knowing which exactly API to choose. This case is similar to 4.1 as new foo package will support both ^1.0.0 & ^2.0.0

5. Dependencies SDK changes

An infrastructure can detect wether package foo is using SDK componenet major version same as foo's dependencies. This automatic check does not require package maintainer additional manifest configuration.

For more control foo developer can specify more exact rules.

For example, foo is only using swss::Table, while a breaking change appeared in swss::ProducerStateTable/swss::ConsumerStateTable. foo's developer can update package to work with new SDK in swss as well:

```json
{
  "package": {
    "name": "foo",
    "version": "1.2.4",
    "depends": [
      {
        "name": "swss",
        "version": "^1.0.0",
        "components": {
          "libswsscommon": "^1.0.0,^2.0.0"
        }
      }
    ]
  }
}
```

## Open Questions
