# DLDD Pydantic Validation Implementation Plan

## Status

Proposed implementation plan. This document does not change the currently implemented validation path by itself.

## Objective

Replace DLDD's runtime Draft-7 and `fastjsonschema` rule checks with exact-version Pydantic v2 models while preserving:

- Bounded, duplicate-safe YAML and JSON ingestion.
- Exact `schema_version` dispatch with no version-range fallback.
- File-level envelope failures versus independently isolated rule failures.
- Partial activation as `DEGRADED` when at least one rule remains usable.
- Rejection and lifecycle fallback when zero rules are usable.
- Trusted vendor and DSE extension hooks without dynamic imports from rule content.
- Stable DLDD-owned diagnostics, paths, source lines, rule IDs, and rule names.
- Immutable runtime and materialized rule objects.
- Side-effect-free activation validation.

The target device currently runs CPython 3.13.5. Pydantic v2 supports this interpreter, so the remaining dependency work is SONiC wheel, architecture, lockfile, and image qualification rather than Python-language compatibility.

## Planning Decisions

| Topic | Decision |
|---|---|
| Runtime structural authority | Exact-version Pydantic v2 models |
| Runtime JSON Schema validation | Removed |
| Published JSON Schema | Generated from Pydantic for vendor tooling; not consumed at runtime |
| Schema version selection | Exact static registry lookup only |
| Validation granularity | Shallow file envelope followed by independent per-signature validation |
| Parser controls | Retained before Pydantic |
| Semantic and materialization checks | Retained, simplified where Pydantic makes structural checks redundant |
| Runtime object representation | Existing recursively frozen domain dataclasses |
| Vendor extensions | Trusted installed registry; Pydantic validates extension envelopes and optional vendor adapters validate payloads |
| Unknown core fields | Rejected; allowed and preserved only at documented vendor extension points |
| `0.0.1` handling | Updated in place because it has not been released |
| Event sampling | Optional event-level `sampling_interval`; omission inherits the current per-monitor CONFIG_DB effective default |
| DLDD restart timing | No cadence persistence; every eligible work item is due on startup, then resumes its normal interval |

Once schema `0.0.1` is released, its accepted input and runtime meaning are frozen. Subsequent contract changes must follow the versioning rules in `vendor-rules-schema-hld.md`.

## Repository Scope

### `sonic-host-services`

Primary implementation repository.

Planned changes:

- Add Pydantic validation models, exact-version registry, error normalization, and generated-schema tooling.
- Refactor rule validation to consume Pydantic DTOs.
- Preserve parser safety, semantic checks, DSE/vendor resolution, immutable domain models, materialization, lifecycle fallback, and telemetry.
- Add event-level sampling interval to validated and runtime models.
- Refactor monitor plans from one interval per monitor to per-work-item due scheduling.
- Replace schema-registry tests with Pydantic contract, strictness, security, and generated-schema tests.
- Remove the `fastjsonschema` runtime dependency after equivalence and regression gates pass.

### `sonic-buildimage`

Dependency and image integration repository.

Planned changes:

- Add exact Pydantic and compatible transitive dependency versions to the build-slave and host-image manifests.
- Remove the DLDD-introduced `fastjsonschema` pins only after confirming no other image consumer requires them.
- Verify CPython 3.13 and every target architecture use prebuilt compatible `pydantic-core` wheels.
- Run `pip check`, wheel build, host image build, import smoke test, and native linkage inspection.

### `SONiC` documentation

Documentation repository.

Planned changes:

- Make versioned Pydantic models the normative runtime rule contract.
- Describe generated JSON Schema as a derived publication artifact.
- Replace Draft-7, `$ref`, and `fastjsonschema` runtime language.
- Preserve the two-pass validation and failure-scope contract.
- Add event-level sampling and per-monitor fallback semantics.
- Update validation and timing test requirements.

### Vendor/platform repositories

No mandatory core change is expected unless a platform registers a vendor-specific source, evaluator, action, or query type. Such platforms may optionally provide a Pydantic model or `TypeAdapter` for their extension payload through the existing trusted hook boundary.

## Implementation Sequence

### Phase 0: Freeze the intended `0.0.1` contract

Tasks:

1. Inventory every positive and negative fixture, sample rule, and deployed vendor rule available in the workspace and target image.
2. Record the intentional `0.0.1` behavior for every field:
   - Required versus omitted.
   - Nullable versus non-nullable.
   - Defaults.
   - Numeric bounds.
   - Allowed enums.
   - Unknown-field behavior.
   - File-level versus rule-level failure scope.
3. Confirm that closed core objects and explicit vendor extension points are the intended first-release contract.
4. Add `event.sampling_interval` to the intended contract as an optional positive integer in seconds.
5. Define omission as inheritance from the materialized source's monitor default and reject explicit `null`.

Exit criteria:

- A reviewed contract matrix exists.
- Every existing field and extension point has a deliberate extra-field policy.
- Every intentional difference from the current permissive Draft-7 artifact is documented.

### Phase 1: Qualify and pin Pydantic

As of 2026-07-06, Pydantic 2.13.4 is the latest stable release and is the initial qualification candidate. The final pins must be taken from a successful SONiC dependency resolution rather than copied blindly from this plan.

Tasks:

1. Resolve and pin `pydantic`, its exact compatible `pydantic-core`, and all transitive packages.
2. Update `sonic-host-services` package metadata from Python `>=3.8` to at least Python `>=3.9`, matching current Pydantic v2 requirements, unless the SONiC branch intentionally declares a stricter Python 3.13 baseline.
3. Confirm wheel availability for:
   - CPython 3.13 on the deployed target.
   - CPython versions used by supported SONiC build variants.
   - Every supported SONiC CPU architecture.
4. Prohibit an unplanned source build of `pydantic-core`; image construction must fail if an approved wheel is unavailable.
5. Add dependency versions to the Trixie build slave, Bookworm build slave when still built, and host image manifests.
6. Run license, SBOM, vulnerability, hash, ABI, and native linkage checks.

Exit criteria:

- Reproducible dependency resolution succeeds for every supported build target.
- `python3 -c 'import pydantic, pydantic_core'` succeeds in the final image.
- `pip check` reports no conflicts.

### Phase 2: Add versioned Pydantic contracts without changing activation

Add the following package structure:

```text
dldd/rule_schema/
  __init__.py
  base.py
  errors.py
  registry.py
  v0_0_1.py
  generate.py
```

Tasks:

1. Define a strict shared base model and bounded JSON-compatible vendor payload type.
2. Define the shallow `EnvelopeV001` and `SignatureEnvelopeV001` models.
3. Define version-specific metadata, condition, event, path, evaluation, action, query, and wrapper models.
4. Use discriminated unions for built-in typed objects.
5. Define controlled vendor extension envelopes that cannot accept malformed built-in types.
6. Define `RuleContract` and an immutable exact-version registry.
7. Add startup integrity checks that confirm the registry key and envelope `Literal` version agree.
8. Add Pydantic-to-DLDD diagnostic normalization.
9. Add explicit conversion from validation DTOs to existing immutable domain dataclasses.

Exit criteria:

- All positive fixtures construct equivalent domain objects.
- All negative fixtures fail at the intended scope with stable DLDD issue metadata.
- The existing runtime activation path is still available for differential testing.

### Phase 3: Differential and security validation

Temporarily run the old and new validators in tests, never as a production double-validation path.

Tasks:

1. Compare accept/reject results for the complete fixture corpus.
2. Compare file-level versus per-rule scope.
3. Compare constructed domain objects and explicitly approved defaults.
4. Review intentional differences, particularly:
   - Unknown fields formerly accepted through broad `additionalProperties: true`.
   - Pydantic omitted-versus-null behavior.
   - Strict integer behavior for booleans, floats, and numeric strings.
   - Union selection and discriminator failures.
5. Retain all parser limit and hostile-input tests unchanged.
6. Add error-volume and validation-time bounds.

Exit criteria:

- No unexplained acceptance or scope differences remain.
- Every deliberate behavior change is represented in tests and the HLD.
- The strictness, extra-field, discriminator, omitted/null, and vendor-extension matrices pass.

### Phase 4: Switch runtime validation to Pydantic

Tasks:

1. Replace the current static schema registry with the exact-version Pydantic contract registry.
2. Change `validate_document()` to:
   - Enforce document limits.
   - Probe and select an exact version.
   - Validate the shallow envelope.
   - Validate each signature independently.
   - Normalize Pydantic and custom semantic errors.
   - Convert successful DTOs to immutable domain objects.
   - Run materialization as it does today.
3. Keep the public validation tiers and CLI behavior stable.
4. Keep `static-schema` as a compatibility name, but redefine it as bounded parsing plus versioned Pydantic structural and semantic validation.
5. Preserve unexpected model-validator exceptions as package failures rather than misclassifying them as bad rules.

Exit criteria:

- Mixed valid/invalid candidates activate `DEGRADED` exactly as specified.
- Zero usable rules rejects the candidate and retains or restores a usable generation.
- No adapter read, CLI, I2C, action, query, or network operation occurs during activation validation.

### Phase 5: Implement event-specific sampling cadence

This is a runtime scheduling feature in addition to the validation refactor.

Tasks:

1. Add optional `sampling_interval` to the Pydantic event model and immutable `Event` domain model.
2. Add effective sampling metadata to each materialized `MonitorWorkItem`.
3. Resolve an omitted interval after monitor assignment:
   - Redis work item → `redis_monitor_polling_interval`.
   - File work item → `file_monitor_polling_interval`.
   - Common or vendor work item → `common_monitor_polling_interval`.
4. Track `next_sample_due` per correlation key using monotonic time.
5. On startup, initialize every eligible key as immediately due; do not restore old schedule timestamps.
6. After a normal attempt, set the next due time to the attempt time plus the effective interval.
7. Coalesce missed intervals instead of issuing catch-up bursts.
8. Preserve `IN_FLIGHT`, hold, suspension, and one-shot recheck precedence.
9. Apply dynamic CONFIG_DB interval updates only to work items that inherit the monitor default. Explicit event intervals remain unchanged.

Exit criteria:

- Two events in the same monitor can run at different intervals.
- Omitted intervals follow their current monitor default.
- Restart causes a fresh normal sample and then normal cadence.
- Dynamic CONFIG_DB changes affect inherited work only.

### Phase 6: Generate and publish JSON Schema

Tasks:

1. Generate Draft 2020-12 JSON Schema from each exact-version Pydantic contract.
2. Assign a stable `$id`, title, schema version, and generated-file warning.
3. Keep the generated artifact in package data for vendor editors and offline tooling.
4. Do not load or execute the generated artifact at runtime.
5. Retain layout files only for version-neutral external extraction consumers.
6. Add a deterministic generation command and CI comparison test.
7. Require review when generated output changes; after first release, require a schema-version decision for behavioral changes.

Exit criteria:

- Regeneration is deterministic with the pinned Pydantic version.
- The installed wheel contains the expected generated artifact and layout.
- Runtime validation succeeds if the generated artifact is absent, proving it is not a hidden runtime dependency.

### Phase 7: Remove the old validation implementation

Tasks:

1. Remove Draft-7 schema compilation, `$id`/`$ref` security traversal, derived envelope schemas, and `StaticSchemaIssue` conversion.
2. Replace calls into the old Draft-7 `StaticSchemaContract` with the new
   `contract.validate_envelope()` and `contract.validate_signature()` Pydantic
   adapter entry points.
3. Remove structural helper code made redundant by Pydantic after verifying no semantic behavior is lost.
4. Remove or repurpose tests that exist only for installed Draft-7 compiler behavior.
5. Remove `fastjsonschema` from `sonic-host-services` and the DLDD-specific build-image pins.
6. Keep `regex` and its runtime timeout controls for event evaluation.

Exit criteria:

- `rg fastjsonschema` finds no DLDD runtime or test dependency.
- All parser, validation, activation, lifecycle, monitor, telemetry, and action tests pass.
- Generated JSON Schema is the only remaining schema artifact and is clearly marked derived.

### Phase 8: Update HLDs and operator documentation

Update at least these areas:

- `vendor-rules-schema-hld.md`:
  - Validation authority and exact-version model registry.
  - Strict and extra-field behavior.
  - Generated Draft 2020-12 artifact status.
  - Vendor extension contract.
  - Event-level `sampling_interval` and omission semantics.
- `device-local-diagnosis-daemon.md`:
  - Validation pipeline and implementation notes.
  - Pydantic dependency and package-integrity behavior.
  - Per-work-item scheduling.
  - Removal of the no-per-rule-polling limitation.
  - Updated test matrix.

Exit criteria:

- Neither HLD claims that Draft-7 or `fastjsonschema` is the runtime authority.
- Validation states, activation fallback, and side-effect boundaries remain consistent across both HLDs.

### Phase 9: Target and lifecycle qualification

Tasks:

1. Install the resulting image or packages on a Python 3.13 target.
2. Repeat the four live rule-validation scenarios:
   - Unsupported exact schema version.
   - One good rule and one broken rule.
   - Two broken rules.
   - Two good rules.
3. Verify CLI output, exit status, `DLDD_STATUS`, active generation, broken-rule telemetry, and fallback selection.
4. Exercise built-in and advertised vendor operation types.
5. Exercise explicit and inherited event sampling intervals.
6. Restart DLDD and confirm every eligible rule is sampled again without persisted cadence state.
7. Change monitor defaults in CONFIG_DB and confirm only inherited work changes cadence.
8. Measure validation latency, daemon startup latency, and resident memory against the current implementation.

Exit criteria:

- Live behavior matches the HLD and acceptance matrix.
- No regression appears in fault publication, action lifecycle, Healthz artifacts, or restart reconciliation.

## Commit and Review Boundaries

Keep reviews small and independently understandable:

1. Add dependency locks and import qualification.
2. Add Pydantic model package and unit tests without runtime cutover.
3. Add exact registry, error normalization, and DTO-to-domain conversion.
4. Add differential/security tests and generated-schema tooling.
5. Cut runtime validation over to Pydantic.
6. Add event-level cadence and monitor scheduler changes.
7. Remove old Draft-7 validator and dependency.
8. Update HLD and operator documentation.

Do not combine dependency qualification, runtime cutover, scheduling changes, and old-code removal into one opaque commit.

## Mandatory Test Matrix

| Area | Minimum coverage |
|---|---|
| Parsing | Duplicate JSON/YAML keys, aliases, unsafe tags, malformed UTF-8, multiple documents, non-finite numbers, every size/depth/node boundary |
| Strictness | Strings, integers, floats, booleans, bytes, tuples/lists, YAML dates, and custom mappings against every relevant field family |
| Presence | Omitted, explicit `null`, zero, false, empty string, and empty list for every optional/defaulted field |
| Extras | Unknown field at every core object and lossless vendor payload preservation at each extension point |
| Unions | Every built-in discriminator, missing/invalid tag, malformed built-in, advertised vendor type, and unadvertised vendor type |
| Versioning | Exact supported version, unsupported patch/minor/major, missing handler, and registry/model mismatch |
| Isolation | One good/one bad, two bad, two good, duplicate identity, zero usable rules, and fallback retention |
| Diagnostics | Stable code, scope, path, line, rule identity, deterministic ordering, redacted input, and bounded error volume |
| Vendor/DSE | No dynamic imports, side-effect-free validation, strict hook output models, unresolved references, and missing hooks |
| Timing | Explicit interval, inherited interval per monitor, mixed intervals, restart behavior, dynamic CONFIG_DB updates, holds, and one-shot rechecks |
| Packaging | Python 3.13 import, every architecture, `pip check`, wheel contents, native linkage, full host-services tests, and full image build |

## Rollback Strategy

Before the old validator is removed, the Pydantic cutover commit can be reverted while retaining the model and differential-test work. After removal, rollback is by reverting the cutover and removal commits together and restoring the prior dependency pins.

Runtime fallback between validator engines must not be selectable from uploaded rule content or CONFIG_DB. A dual-validator runtime flag would create two authorities and is intentionally excluded.

## Completion Criteria

The migration is complete only when:

- Pydantic models are the sole runtime structural authority.
- The old Draft-7 runtime validator and DLDD-specific dependency are removed.
- Parser and security protections remain intact.
- Exact version selection and per-rule isolation pass all tests.
- Generated schema and layouts are packaged for external consumers.
- Vendor extension hooks remain supported without dynamic imports.
- Event sampling inheritance and restart behavior match the agreed contract.
- Python 3.13 and all supported SONiC image/architecture builds pass.
- Both HLDs describe the implemented behavior without contradictory legacy text.
