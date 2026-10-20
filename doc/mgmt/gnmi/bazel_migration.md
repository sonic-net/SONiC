# Bazel Migration HLD #

_Rev v0.1_

## Table of Contents

### Revision

| Rev  | Rev Date   | Author(s)          | Change Description      |
|------|------------|--------------------|-------------------------|
| v0.1 | 1/15/2025  | Ryan Lucus (Google)|  Initial version        |
| v0.2 | 2/13/2025  | Ryan Lucus (Google)|  Make sonic-gnmi only   |

### Scope

Migrate the build system for sonic-gnmi and to Bazel.

### Definitions/Abbreviations

- [Bazel](https://bazel.build/) Open Source Multilanguage Build Tool
- [Gazelle](https://github.com/bazel-contrib/bazel-gazelle) Bazel build file manager for Golang

### Overview

Bazel is a modern build system that provides efficient and hermetic builds. They are easier to troubleshoot and maintain. Bazel uses Build files to define rules for compiling every binary and library used and a Workspace file defining the overall project. The Bazel configuration files are written in Starlark which is based on Python.

### Architecture Design

This feature does not change the SONiC Architecture.

### High Level Design

The primary Make file in each repository will be modified to point to new Bazel build targets and a build file added to each package.

Gazelle is used to keep build files and dependencies up to date with commands like `gazelle fix` and `gazelle update-repos`

As part of this migration we will also provide a number of documents for setting up a developer environment and basic tasks with Bazel such as adding new components, maintaining dependencies, or debugging build issues.

#### Improvements

- Speed
  - We saw a 30% improvement in our CI/CD environment without any caching.
  - Local builds went from 20 minutes to 5 minutes on average.

- Consistency
  - We found less issues when setting up new workstations for developers.

- Maintainability
  - Automated tooling with Gazelle for dependency updates.
  - Powerful tools like Bazel query for debugging build issues.
  - Protobuf files built from source instead of precompiled.

### Examples

#### Workflow

Update build files and dependencies with the following commands instead of manually editing.

```sh
go mod tidy && gazelle fix && bazel run :gazelle-update-repos
```

#### Change to Makefile

Significantly reduced complexity in the build chain from Sonic-Buildimage. The Make file now simply points to the appropiate target to be included.

Small sample before migration:

```make
INSTALL := /usr/bin/install
DBDIR := /var/run/redis/sonic-db/
GO ?= /usr/local/go/bin/go
TOP_DIR := $(abspath ..)
MGMT_COMMON_DIR := $(TOP_DIR)/sonic-mgmt-common
BUILD_DIR := build/bin
export CVL_SCHEMA_PATH := $(MGMT_COMMON_DIR)/build/cvl/schema
export GOBIN := $(abspath $(BUILD_DIR))
export PATH := $(PATH):$(GOBIN):$(shell dirname $(GO))
export CGO_LDFLAGS := -lswsscommon -lhiredis
export CGO_CXXFLAGS := -I/usr/include/swss -w -Wall -fpermissive
export MEMCHECK_CGO_LDFLAGS := $(CGO_LDFLAGS) -fsanitize=address
export MEMCHECK_CGO_CXXFLAGS := $(CGO_CXXFLAGS) -fsanitize=leak

ifeq ($(ENABLE_TRANSLIB_WRITE),y)
BLD_TAGS := gnmi_translib_write
endif
ifeq ($(ENABLE_NATIVE_WRITE),y)
BLD_TAGS := $(BLD_TAGS) gnmi_native_write
endif

ifneq ($(BLD_TAGS),)
BLD_FLAGS := -tags "$(strip $(BLD_TAGS))"
endif

MEMCHECK_TAGS := $(BLD_TAGS) gnmi_memcheck
ifneq ($(MEMCHECK_TAGS),)
MEMCHECK_FLAGS := -tags "$(strip $(MEMCHECK_TAGS))"
endif

ENABLE_DIALOUT_VALUE := 1
ifeq ($(ENABLE_DIALOUT),n)
ENABLE_DIALOUT_VALUE = 0
endif

GO_DEPS := vendor/.done
PATCHES := $(wildcard patches/*.patch)
PATCHES += $(shell find $(MGMT_COMMON_DIR)/patches -type f)

all: sonic-gnmi

sonic-gnmi: $(GO_DEPS)
# advancetls 1.0.0 release need following patch to build by go-1.19
 patch -d vendor -p0 < patches/0002-Fix-advance-tls-build-with-go-119.patch
# build service first which depends on advancetls
ifeq ($(CROSS_BUILD_ENVIRON),y)
 $(GO) build -o ${GOBIN}/telemetry -mod=vendor $(BLD_FLAGS) github.com/sonic-net/sonic-gnmi/telemetry
ifneq ($(ENABLE_DIALOUT_VALUE),0)
 $(GO) build -o ${GOBIN}/dialout_client_cli -mod=vendor $(BLD_FLAGS) github.com/sonic-net/sonic-gnmi/dialout/dialout_client_cli
endif
 $(GO) build -o ${GOBIN}/gnoi_client -mod=vendor github.com/sonic-net/sonic-gnmi/gnoi_client
 $(GO) build -o ${GOBIN}/gnmi_dump -mod=vendor github.com/sonic-net/sonic-gnmi/gnmi_dump
else
 $(GO) install -mod=vendor $(BLD_FLAGS) github.com/sonic-net/sonic-gnmi/telemetry
ifneq ($(ENABLE_DIALOUT_VALUE),0)
 $(GO) install -mod=vendor $(BLD_FLAGS) github.com/sonic-net/sonic-gnmi/dialout/dialout_client_cli
endif
 $(GO) install -mod=vendor github.com/sonic-net/sonic-gnmi/gnoi_client
 $(GO) install -mod=vendor github.com/sonic-net/sonic-gnmi/gnmi_dump
endif

# download and apply patch for gnmi client, which will break advancetls
# backup crypto and gnxi
 mkdir backup_crypto
 cp -r vendor/golang.org/x/crypto/* backup_crypto/

# download and patch crypto and gnxi
 $(GO) mod download golang.org/x/crypto@v0.0.0-20191206172530-e9b2fee46413
 cp -r $(GOPATH)/pkg/mod/golang.org/x/crypto@v0.0.0-20191206172530-e9b2fee46413/* vendor/golang.org/x/crypto/
 chmod -R u+w vendor
 patch -d vendor -p0 < patches/gnmi_cli.all.patch
 patch -d vendor -p0 < patches/gnmi_set.patch
 patch -d vendor -p0 < patches/gnmi_get.patch
 git apply patches/0001-Updated-to-filter-and-write-to-file.patch

ifeq ($(CROSS_BUILD_ENVIRON),y)
 $(GO) build -o ${GOBIN}/gnmi_get -mod=vendor github.com/jipanyang/gnxi/gnmi_get
 $(GO) build -o ${GOBIN}/gnmi_set -mod=vendor github.com/jipanyang/gnxi/gnmi_set
 $(GO) build -o ${GOBIN}/gnmi_cli -mod=vendor github.com/openconfig/gnmi/cmd/gnmi_cli
else
 $(GO) install -mod=vendor github.com/jipanyang/gnxi/gnmi_get
 $(GO) install -mod=vendor github.com/jipanyang/gnxi/gnmi_set
 $(GO) install -mod=vendor github.com/openconfig/gnmi/cmd/gnmi_cli
endif

# restore old version
 rm -rf vendor/golang.org/x/crypto/
 mv backup_crypto/ vendor/golang.org/x/crypto/
```

Entire file after migration:

```make
INSTALL := /usr/bin/install
BUILD_DIR := build/bin
BAZEL_OPTS := --verbose_failures

all: init sonic-gnmi clients

sonic-gnmi: $(MAKEFILE_LIST) $(GO_DEPS)
 bazel build $(BAZEL_OPTS) telemetry:telemetry --verbose_failures

clients:
 bazel build $(BAZEL_OPTS) dialout/dialout_client_cli:dialout_client_cli
 bazel build $(BAZEL_OPTS) gnoi_client:gnoi_client
 bazel build $(BAZEL_OPTS) third_party:gnmi_cli

clean:
 $(RM) -r build

install:
 install -D bazel-bin/telemetry/telemetry_/telemetry $(DESTDIR)/usr/sbin/telemetry
 install -D bazel-bin/dialout/dialout_client_cli/dialout_client_cli_/dialout_client_cli $(DESTDIR)/usr/sbin/dialout_client_cli
 install -D bazel-bin/gnoi_client/gnoi_client_/gnoi_client $(DESTDIR)/usr/sbin/gnoi_client
 install -D bazel-bin/external/com_github_openconfig_gnmi/cmd/gnmi_cli/gnmi_cli_/gnmi_cli $(DESTDIR)/usr/sbin/gnmi_cli
 mkdir -p $(DESTDIR)/usr/bin/

uninstall:
 rm $(DESTDIR)/usr/sbin/telemetry
 rm $(DESTDIR)/usr/sbin/dialout_client_cli
 rm $(DESTDIR)/usr/sbin/gnoi_client
 rm $(DESTDIR)/usr/sbin/gnmi_cli
```

### Testing Requirements/Design

All Currently supported tests shall be covered when migration is complete.
