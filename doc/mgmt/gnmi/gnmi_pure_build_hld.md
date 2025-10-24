# gNMI Pure Build Infrastructure HLD

# High Level Design Document

#### Rev 0.1

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
- [Testing Requirements/Design](#testing-requirementsdesign)
- [Restrictions/Limitations](#restrictionslimitations)
- [Open/Action Items](#openaction-items)

## Revision

| Rev  | Rev Date   | Author(s)          | Change Description |
|------|------------|--------------------|--------------------|
| v0.1 | 10/17/2025 | Dawei Huang        | Initial version    |

## Scope

This document describes the high-level design for establishing a pure Go build infrastructure for the sonic-gnmi repository. It addresses the critical development velocity problems caused by lack of local testability, manual testing requirements, and inability for reviewers to verify pull requests without full SONiC environments.

## Definitions/Abbreviations

- **Pure Build**: Go code that compiles and tests without CGO or SONiC-specific dependencies (swsscommon, translib, Redis, ConfigDB)
- **Full Build**: Complete SONiC build with all CGO and platform dependencies
- **CGO**: Go's C interoperability mechanism, used for swsscommon C++ bindings
- **swsscommon**: SONiC Switch State Service Common library (C++)
- **translib**: SONiC management framework translation library
- **Dev Container**: Pre-built Docker container with all SONiC build dependencies

## Overview

The sonic-gnmi repository currently faces critical development velocity problems:

### Current Pain Points

1. **No Local Testability**: Developers cannot run tests locally without installing full SONiC dependencies (libswsscommon, Redis, translib), which requires:
   - Installing specific .deb packages
   - Configuring Redis with Unix sockets
   - Setting up sonic-mgmt-common
   - Building SWIG-generated bindings

2. **Manual Testing is Unverifiable**: Pull requests contain manual test instructions like:
   ```bash
   # Install .deb, restart gnmi, run grpcurl
   ```
   Reviewers cannot verify these were actually executed - instructions could be AI-generated or fabricated.

3. **Long PR Review Cycles**: Example PRs stuck for months:
   - PR #404: gNOI File Services - **137 days open**, 57 comments
   - PR #395: gNOI File Services - **153 days open**
   - Multiple gNOI.OS Install PRs - 115-133 days each

   Root cause: No standardized test environment → endless clarification questions

4. **Slow Iteration Cycles**:
   - Current: Code → Build .deb → Install → Restart service → Manual grpcurl → 10+ minutes
   - Each small change requires rebuilding and redeploying

5. **Azure CI as Only Verification**:
   - PR #524: **25 `/azp run` retries** in 11 days
   - Each CI run: 30-60 minutes
   - Developers waiting hours/days for feedback

### Proposed Solution

Establish two parallel build systems:

1. **pure.mk**: Fast, local testing without SONiC dependencies
   - Runs in 2 seconds on any machine with Go installed
   - Enables `go test` during development
   - Currently supports: `internal/diskspace`, `pkg/server/operational-handler`

2. **full.mk**: Complete SONiC build using pre-built dev container
   - Standardized, reproducible environment
   - Works on any machine with Docker
   - Eliminates manual setup instructions

## Requirements

### Functional Requirements

1. **Local Development**: Developers must be able to run tests on laptops without SONiC installation
2. **Fast Iteration**: Test execution in seconds, not minutes
3. **Automated Testing**: Replace manual test instructions with `go test`
4. **Reproducible Builds**: Same command produces same results on any machine
5. **Progressive Adoption**: Existing packages continue to work while new packages adopt pure build

### Non-Functional Requirements

1. **No Regression**: Existing SONiC builds must continue to work unchanged
2. **CI Integration**: Both pure and full builds run in Azure pipelines
3. **Documentation**: Clear guidelines for when to use pure vs full build

## Architecture Design

### Dependency Quarantine Strategy

The core architectural principle is **dependency quarantine using Go build tags**:

```
┌─────────────────────────────────────────────┐
│         Application/Business Logic           │
│              (pure Go code)                  │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼──────┐   ┌────────▼─────┐
│ Interface    │   │  Interface   │
│ (no tags)    │   │  (no tags)   │
└──────┬───────┘   └──────┬───────┘
       │                  │
   ┌───┴───┐          ┌───┴───┐
   │       │          │       │
┌──▼──┐ ┌─▼───┐   ┌──▼──┐ ┌─▼───┐
│sonic│ │mock │   │sonic│ │mock │
│ tag │ │ tag │   │ tag │ │ tag │
└─────┘ └─────┘   └─────┘ └─────┘
   │                  │
   └──CGO deps────────┘
```

### Example: sonic_db_config Quarantine

**Interface (always compiled):**
```go
// sonic_db_config/interface.go
package dbconfig

type SonicDBConfig interface {
    GetDbList(ns string) ([]string, error)
    GetDbId(db_name, ns string) (int, error)
    // ... other methods
}

var DB SonicDBConfig
```

**SONiC Implementation (requires CGO):**
```go
// sonic_db_config/db_config_sonic.go
//go:build sonic

package dbconfig

import "github.com/sonic-net/sonic-gnmi/swsscommon"

type sonicDB struct{}

func init() {
    DB = &sonicDB{}
}

func (s *sonicDB) GetDbList(ns string) ([]string, error) {
    // Calls SWIG-generated swsscommon bindings
    db_vec := swsscommon.SonicDBConfigGetDbList()
    defer swsscommon.DeleteVectorString(db_vec)
    // ... convert to []string
}
```

**Mock Implementation (pure Go):**
```go
// sonic_db_config/db_config_mock.go
//go:build !sonic

package dbconfig

type mockDB struct {
    data map[string][]string
}

func init() {
    DB = &mockDB{
        data: map[string][]string{
            "": {"APPL_DB", "CONFIG_DB", "STATE_DB"},
        },
    }
}

func (m *mockDB) GetDbList(ns string) ([]string, error) {
    return m.data[ns], nil
}
```

**Build Selection:**
```bash
# Pure build - uses mocks
go test ./sonic_db_config/...

# SONiC build - uses real swsscommon
go test -tags sonic ./sonic_db_config/...
```

### Build System Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Developer Machine                    │
│                                                       │
│  ┌─────────────┐              ┌──────────────┐      │
│  │  pure.mk    │              │  full.mk     │      │
│  │             │              │              │      │
│  │ - No deps   │              │ - Docker     │      │
│  │ - 2 seconds │              │ - Full env   │      │
│  │ - go test   │              │ - Containers │      │
│  └─────────────┘              └──────────────┘      │
│         │                            │               │
│         │                            │               │
│         ▼                            ▼               │
│  ┌─────────────┐              ┌──────────────┐      │
│  │Mock backend │              │Dev Container │      │
│  │(in-memory)  │              │(pre-built)   │      │
│  └─────────────┘              └──────────────┘      │
└──────────────────────────────────────────────────────┘
                       │
                       │ git push
                       ▼
┌──────────────────────────────────────────────────────┐
│              Azure Pipelines CI                       │
│                                                       │
│  ┌──────────────────────────────────────────┐        │
│  │ Step 1: Pure Build (fast)                │        │
│  │   make -f pure.mk ci                     │        │
│  │   Duration: ~10 seconds                  │        │
│  └──────────────────────────────────────────┘        │
│                       │                               │
│                       ▼                               │
│  ┌──────────────────────────────────────────┐        │
│  │ Step 2: Full Build (complete)            │        │
│  │   make -f full.mk ci                     │        │
│  │   Duration: ~30 minutes                  │        │
│  └──────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────┘
```

## High-Level Design

### Component 1: pure.mk - Fast Local Testing

**Purpose**: Enable developers to test business logic without SONiC dependencies.

**Implementation:**
```makefile
# pure.mk - Simple CI for pure packages without SONiC dependencies

GO ?= go
GOROOT ?= $(shell $(GO) env GOROOT)

# Pure packages (no CGO/SONiC dependencies)
PURE_PACKAGES := \
	internal/diskspace \
	pkg/server/operational-handler

# Future packages to migrate:
# TODO: gnoi_client/config
# TODO: common_utils (split pure vs CGO parts)

# Default target
.DEFAULT_GOAL := ci

# Full CI pipeline
.PHONY: ci
ci: clean lint build-test test
	@echo "✅ Pure CI completed successfully!"

# Format check
.PHONY: fmt-check
fmt-check:
	@for pkg in $(PACKAGES); do \
		files=$$($(GOROOT)/bin/gofmt -l $$pkg/*.go); \
		if [ -n "$$files" ]; then \
			echo "Files need formatting: $$files"; \
			exit 1; \
		fi; \
	done

# Static analysis
.PHONY: vet
vet:
	@for pkg in $(PACKAGES); do \
		cd $$pkg && $(GO) vet ./...; \
		cd - >/dev/null; \
	done

# Run tests with coverage
.PHONY: test
test:
	@for pkg in $(PACKAGES); do \
		cd $$pkg && $(GO) test -v -race -coverprofile=coverage.out ./...; \
		if [ -f coverage.out ]; then \
			$(GO) tool cover -func=coverage.out; \
		fi; \
		cd - >/dev/null; \
	done
```

**Usage:**
```bash
# Developer workflow
make -f pure.mk ci           # Run all checks
make -f pure.mk test         # Run tests only
make -f pure.mk fmt          # Auto-format code

# Per-package testing
make -f pure.mk PACKAGES=internal/diskspace test
```

**Benefits:**
- **Fast**: Completes in 2 seconds
- **No Setup**: Works on any machine with Go
- **Enables TDD**: Rapid test-driven development
- **Pre-commit Hook**: Can run before every commit

### Component 2: full.mk - Standardized Full Build

**Purpose**: Provide reproducible SONiC build environment via pre-built container.

**Implementation:**
```makefile
# full.mk - Full build using pre-built dev container

# Container configuration
DOCKER_IMAGE ?= sonicdev-microsoft.azurecr.io:443/sonic-slave-bookworm:latest
CONTAINER_WORKDIR := /workspace

# Docker run - container has all dependencies pre-installed
DOCKER_RUN := docker run --rm \
	-v $(PWD):$(CONTAINER_WORKDIR) \
	-w $(CONTAINER_WORKDIR) \
	$(DOCKER_IMAGE)

# Interactive shell
DOCKER_SHELL := docker run --rm -it \
	-v $(PWD):$(CONTAINER_WORKDIR) \
	-w $(CONTAINER_WORKDIR) \
	$(DOCKER_IMAGE) /bin/bash

.DEFAULT_GOAL := ci

# Full CI pipeline
.PHONY: ci
ci: fmt-check build test
	@echo "✅ Full SONiC CI completed successfully!"

# Build with SONiC dependencies
.PHONY: build
build:
	$(DOCKER_RUN) make -f Makefile all

# Test with SONiC dependencies
.PHONY: test
test:
	$(DOCKER_RUN) make -f Makefile check_gotest

# Interactive debugging
.PHONY: shell
shell:
	$(DOCKER_SHELL)
```

**Dev Container Contents** (pre-built elsewhere):
- libswsscommon, libhiredis
- Redis server (pre-configured)
- sonic-mgmt-common libraries
- protobuf compiler, SWIG
- Go 1.21 toolchain

**Usage:**
```bash
# One-time setup
make -f full.mk pull         # Pull pre-built container

# Development
make -f full.mk ci           # Run full build+test
make -f full.mk shell        # Debug interactively
```

**Benefits:**
- **Reproducible**: Same container = same results everywhere
- **No Manual Steps**: No 60-step setup from azure-pipelines.yml
- **Works Everywhere**: Mac, Windows, Linux - just needs Docker
- **Isolated**: Doesn't pollute host machine

### Component 3: Package Migration Strategy

**Criteria for Pure Package:**
A package is pure-eligible if:
1. Business logic can be tested independently of SONiC
2. Dependencies can be mocked via interfaces
3. No fundamental requirement for CGO (e.g., not SWIG bindings themselves)

**Migration Process:**

**Step 1: Extract Interface**
```go
// Before (tightly coupled)
func ProcessData() error {
    db_vec := swsscommon.SonicDBConfigGetDbList()
    // ... business logic
}

// After (interface-based)
func ProcessData(db DBConfig) error {
    list, _ := db.GetDbList()
    // ... business logic (testable!)
}
```

**Step 2: Create Build Tag Files**
- `package_sonic.go` - real implementation with `//go:build sonic`
- `package_mock.go` - mock implementation with `//go:build !sonic`

**Step 3: Add to pure.mk**
```makefile
PURE_PACKAGES := \
	internal/diskspace \
	pkg/server/operational-handler \
	new/pure/package  # <-- Add here
```

**Step 4: Add Tests**
```go
// package_test.go (no build tags - runs in both modes)
func TestBusinessLogic(t *testing.T) {
    // Uses mock in pure build, real impl in full build
    result := ProcessData(DefaultDB)
    assert.Equal(t, expected, result)
}
```

**Current Status:**
- **Pure**: `internal/diskspace`, `pkg/server/operational-handler`
- **In Progress**: File service handlers (PR #521 pattern)
- **TODO**: `gnoi_client/config`, `common_utils` (auth/context parts)

**Long-term Goal:**
Eventually quarantine translib itself, enabling entire gNMI server to be testable without SONiC.

### Component 4: CI/CD Integration

**Azure Pipeline Changes:**
```yaml
# azure-pipelines.yml (updated)
steps:
  - script: |
      # Step 1: Pure build (fast feedback)
      make -f pure.mk ci
    displayName: "Pure package tests (fast)"

  - script: |
      # Step 2: Full build (complete verification)
      make all && make check_gotest $(UNIT_TEST_FLAG)
    displayName: "Full SONiC build and test"
```

**Benefits:**
- Fast feedback from pure tests (10 seconds)
- Complete coverage from full tests (30 minutes)
- Developers get early signal before full build

### Component 5: Documentation and Contribution Guidelines

**New Contributor Guide:**
```markdown
## Testing Your Changes

### Quick Test (Recommended for most changes)
```bash
make -f pure.mk ci
```

### Full Test (When modifying SONiC integration)
```bash
make -f full.mk ci
```

### Pull Request Requirements
- [ ] `make -f pure.mk ci` passes (if pure package)
- [ ] `make -f full.mk ci` passes (if SONiC integration)
- [ ] Include automated `go test` instead of manual instructions
```

**Package Structure Guide:**
```
When to use pure build:
✅ Business logic (path parsing, validation, formatting)
✅ gRPC handlers (can mock backend)
✅ Utilities (checksum, download, parsing)

When full build is required:
❌ Direct swsscommon calls
❌ Direct translib calls
❌ SWIG binding generation
```

## Testing Requirements/Design

### Unit Testing Strategy

**Pure Packages:**
```go
// Example: internal/diskspace/diskspace_test.go
func TestGet(t *testing.T) {
    m := New()
    info, err := m.Get("/tmp")

    assert.NoError(t, err)
    assert.Greater(t, info.Total, uint64(0))
    assert.Greater(t, info.Available, uint64(0))
}

// Runs without SONiC: go test ./internal/diskspace
```

**SONiC Integration (with quarantine):**
```go
// Example: sonic_db_config/db_config_test.go
func TestGetDbList(t *testing.T) {
    // Works with both mock (pure) and real (sonic) backends
    list, err := DB.GetDbList("")

    assert.NoError(t, err)
    assert.Contains(t, list, "CONFIG_DB")
}

// Pure: go test ./sonic_db_config
// Full: go test -tags sonic ./sonic_db_config
```

### Test Coverage Requirements

**Pure packages must achieve:**
- Minimum 90% line coverage
- All error paths tested
- Edge cases covered

**Example from current codebase:**
- `internal/diskspace`: 95.5% coverage
- `pkg/server/operational-handler`: 92.8% coverage

### CI Test Matrix

| Build Type | Duration | When to Run | Coverage |
|------------|----------|-------------|----------|
| Pure       | ~10 sec  | Every commit, pre-merge | Pure packages only |
| Full       | ~30 min  | Pre-merge, post-merge | All packages |

### Manual Testing Elimination

**Before (PR #521 style - manual):**
```
#### How to verify it
1. Build debian package: dpkg-buildpackage...
2. Install: sudo dpkg -i sonic-gnmi_1.0_amd64.deb
3. Restart: sudo systemctl restart gnmi
4. Test: grpcurl -d '{"path":"/tmp/file"}' ...
5. Verify: ls -la /tmp/file
```

**After (automated):**
```go
// file_test.go
func TestTransferToRemote(t *testing.T) {
    handler := NewFileHandler()

    resp, err := handler.TransferToRemote(context.Background(), &gnoi.TransferToRemoteRequest{
        LocalPath:  "/tmp/testfile",
        RemotePath: "http://example.com/upload",
        Protocol:   gnoi.TransferProtocol_HTTP,
    })

    assert.NoError(t, err)
    assert.NotEmpty(t, resp.Hash)
}
```

**Pull Request Checklist:**
```markdown
- [ ] Added `go test` for new functionality
- [ ] `make -f pure.mk ci` passes (pure packages)
- [ ] `make -f full.mk ci` passes (SONiC integration)
- [ ] Coverage ≥90% for new code
```

## Restrictions/Limitations

### Current Limitations

1. **Not All Packages Can Be Pure**:
   - SWIG bindings (`swsscommon/`) must remain CGO-based
   - Core SONiC integration points require full environment

2. **Mock Behavior Drift Risk**:
   - Mock implementations may diverge from real SONiC behavior
   - Mitigation: Full build tests catch divergence

3. **Learning Curve**:
   - Contributors must understand pure vs full distinction
   - Mitigation: Clear documentation and examples

4. **Container Image Size**:
   - Dev container is ~2-3GB
   - Mitigation: One-time download, cached locally

### Known Issues

1. **go.mod Replace Directive**:
   - Current: `replace github.com/Azure/sonic-mgmt-common => ../sonic-mgmt-common`
   - Problem: Breaks `go mod verify`
   - TODO: Fix with proper versioning or go.work workspace

2. **Module Verification Disabled**:
   - `pure.mk` CI currently skips `mod-verify` due to above
   - Must be re-enabled once replace directive fixed

## Open/Action Items

### Immediate (v0.1)

- [ ] Document pure.mk usage in CONTRIBUTING.md
- [ ] Add full.mk implementation
- [ ] Update azure-pipelines.yml to run both builds
- [ ] Create dev container build pipeline

### Short-term (v0.2)

- [ ] Migrate `gnoi_client/config` to pure build
- [ ] Split `common_utils` into pure and SONiC parts
- [ ] Add pre-commit hook for `make -f pure.mk ci`

### Long-term (v1.0)

- [ ] Quarantine translib behind interface
- [ ] Make entire gNMI server testable without SONiC
- [ ] Achieve 100% of non-binding code pure-testable
- [ ] Fix go.mod replace directive issues

### Documentation

- [ ] Developer guide: When to use pure vs full
- [ ] Migration guide: Converting existing package to pure
- [ ] Architecture decision record: Why build tags over other approaches

---

**Note**: This HLD represents a fundamental shift from environment-dependent manual testing to standardized, automated testing. The goal is to reduce PR review cycles from months to days by establishing clear testing contracts that both contributors and reviewers can trust.
