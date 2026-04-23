# YANG 1.1 Action Support in SONiC Management Framework

## High Level Design Document

#### Rev 0.1

## Table of Contents

- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
- [1 Feature Overview](#1-feature-overview)
  - [1.1 RPC vs Action](#11-rpc-vs-action)
  - [1.2 Design Overview](#12-design-overview)
- [2 Design](#2-design)
  - [2.1 Request Flow](#21-request-flow)
  - [2.2 YANG Model Changes](#22-yang-model-changes)
  - [2.3 Annotation and Callpoint Registration](#23-annotation-and-callpoint-registration)
  - [2.4 Callback Function Types](#24-callback-function-types)
  - [2.5 REST Framework Changes](#25-rest-framework-changes)
  - [2.6 TransLib Changes](#26-translib-changes)
  - [2.7 OpenAPI Generator Changes](#27-openapi-generator-changes)
  - [2.8 Go Handler Template Changes](#28-go-handler-template-changes)
  - [2.9 Sonic YANG Generator Changes](#29-sonic-yang-generator-changes)
  - [2.10 CLI Generator Changes](#210-cli-generator-changes)
- [3 What is NOT Changed](#3-what-is-not-changed)
- [4 Notes](#4-notes)

## Revision

| Rev | Date       | Author     | Change Description |
|:---:|:----------:|:----------:|:-------------------|
| 0.1 | 2026-04-23 | Jichen Dou | Initial version    |

## About this Manual

This document describes the design for supporting YANG 1.1 `action` statements (RFC 7950 §7.15) with correct RESTCONF invocation (RFC 8040 §3.6) in the SONiC Management Framework. Changes span YANG models, translib, the REST server, OpenAPI/code generators, and the CLI generator.

## Scope

This document covers the end-to-end design for introducing `action` support: how actions differ from RPCs at the YANG and RESTCONF layers, the new `ActionCallpoint` type and its registration, and all framework components that required modification.

## Definition/Abbreviation

| Term | Description |
|------|-------------|
| HLD | High Level Design |
| RPC | Remote Procedure Call (YANG top-level, RFC 7950 §7.14) |
| Action | YANG 1.1 operation defined inside a data node (RFC 7950 §7.15) |
| RESTCONF | REST-like protocol for YANG-modeled data (RFC 8040) |
| translib | SONiC Management Framework translation library |
| OCM | Optical Channel Monitor — an OTN network element that measures per-channel optical power across a wavelength spectrum. Used in this document as the concrete example of a list-scoped action. |

---

## 1 Feature Overview

### 1.1 RPC vs Action

YANG 1.1 (RFC 7950) introduces the `action` statement as a way to define operations that are *scoped to a specific data instance* rather than to the module as a whole. The table below summarises the key differences:

| Aspect | RPC (RFC 7950 §7.14) | Action (RFC 7950 §7.15) |
|--------|----------------------|------------------------|
| Defined at | Module top level | Inside a `container` or `list` node |
| RESTCONF path | `POST /restconf/operations/<module:rpc-name>` | `POST /restconf/data/<path-to-data-node>/<module:action-name>` |
| Instance context | None — global scope | The parent list/container instance (keys in URI) |
| Annotation extension | `sonic-ext:rpc-callback` | `sonic-ext:action-callback` |
| Go callback type | `RpcCallpoint` (2 params) | `ActionCallpoint` (3 params, includes `vars`) |

### 1.2 Design Overview

The OCM raw-data retrieval use case illustrates the motivation: the existing top-level `get-ocm-raw` RPC had no way to identify *which* channel-monitor instance to query without embedding the name in the input payload. Converting it to an `action` defined inside the `channel-monitor` list lets the instance key come directly from the URI, keeping the payload minimal.

**YANG definition (new module `sonic-oc-action-ext`):**

```yang
augment "/oc-chan-monitor:channel-monitors/oc-chan-monitor:channel-monitor" {
    action get-ocm-raw {
        output {
            leaf length { type uint32; }
            leaf data   { type binary; }
            uses action-response-status;
        }
    }
}
```

**RESTCONF invocation:**
```
POST /restconf/data/openconfig-channel-monitor:channel-monitors/channel-monitor=OCM0-0/sonic-oc-act-ext:get-ocm-raw
{"sonic-oc-act-ext:input": {}}
```

The channel-monitor key `OCM0-0` is part of the URI, not the payload.

---

## 2 Design

### 2.1 Request Flow

```
Client  POST /restconf/data/<data-path>/<action-name>
          |
          v
[1]  Generated Go handler  (controllers-api.j2)
         rc.IsAction = true
          |
          v
[2]  server.Process(w, r)
          |
          v
[3]  parseMethod()  →  isOperationsRequest()
         detects rc.IsAction == true  →  args.method = "ACTION"
          |
          v
[4]  trimRestconfPrefix()  strips "/restconf/data"
         translib path: /openconfig-channel-monitor:channel-monitors/channel-monitor=OCM0-0/sonic-oc-act-ext:get-ocm-raw
          |
          v
[5]  invokeTranslib()  case "ACTION"  →  translib.Action(req)
          |
          v
[6]  CommonApp.processAction()
         transformer.CallRpcMethod(path, pathInfo.Vars, body, dbs)
         registered callback  act_get_ocm_raw_cb
          |
          v
[7]  200 OK with output JSON  (or 204 No Content if action has no output)
```

### 2.2 YANG Model Changes

**`src/sonic-mgmt-common`**

| File | Change |
|------|--------|
| `models/yang/sonic-oc-action-ext.yang` | **New file.** YANG 1.1 module hosting OTN actions via `augment`. Contains the `get-ocm-raw` action inside `channel-monitor`, plus the shared `action-status` typedef and `action-response-status` grouping. |
| `models/yang/openconfig-channel-monitor.yang` | Upgraded to `yang-version "1.1"`. Removed top-level `get-ocm-raw` RPC (now replaced by the action). |
| `models/yang/annotations/sonic-extensions.yang` | Added `action-callback` extension (see §2.3). |
| `models/yang/annotations/openconfig-channel-monitor-annot.yang` | Upgraded to `yang-version "1.1"`. Replaced RPC deviation with action deviation using `sonic-ext:action-callback`. |
| `config/transformer/models_list` | Added `sonic-oc-action-ext.yang`. |

Any YANG module or annotation file that references an `action` node **must** declare `yang-version "1.1"` — this is a hard requirement of the YANG specification.

### 2.3 Annotation and Callpoint Registration

A new YANG extension `action-callback` is added to `sonic-extensions.yang`, mirroring the existing `rpc-callback`:

```yang
// sonic-extensions.yang

extension rpc-callback {
    argument "callback";
    description "RPC callback to be invoked for action";
}

extension action-callback {
    argument "callback";
    description "Action callback to be invoked for action within list or container";
}
```

The annotation file wires a specific action path to its Go callback:

```yang
// openconfig-channel-monitor-annot.yang

deviation "/oc-chan-monitor:channel-monitors/oc-chan-monitor:channel-monitor/sonic-oc-act-ext:get-ocm-raw" {
    deviate add {
        sonic-ext:action-callback "act_get_ocm_raw_cb";
    }
}
```

The callback is registered at init time with the same `XlateFuncBind` call used for RPC callbacks:

```go
// xfmr_otn_openconfig.go
func init() {
    XlateFuncBind("act_get_ocm_raw_cb", act_get_ocm_raw_cb)
}
```

### 2.4 Callback Function Types

`xfmr_interface.go` defines two callpoint signatures:

```go
// RpcCallpoint — top-level RPC; no URI instance context needed.
type RpcCallpoint func(body []byte, dbs [db.MaxDB]*db.DB) ([]byte, error)

// ActionCallpoint — YANG 1.1 action (or RPC needing URI path context).
// vars carries list keys extracted from URI predicates,
// e.g. {"name": "OCM0-0"} for channel-monitor=OCM0-0.
type ActionCallpoint func(vars map[string]string, body []byte, dbs [db.MaxDB]*db.DB) ([]byte, error)
```

| | `RpcCallpoint` | `ActionCallpoint` |
|---|---|---|
| Signature | `func(body, dbs)` | `func(vars, body, dbs)` |
| `vars` param | None | List keys from URI predicates |
| Use case | Top-level `rpc` | `action` inside list/container |
| YANG annotation | `sonic-ext:rpc-callback` | `sonic-ext:action-callback` |
| RESTCONF path | `POST /restconf/operations/…` | `POST /restconf/data/…` |

**`CallRpcMethod` auto-dispatch** (`xlate.go`) selects the calling convention by inspecting the registered function's parameter count at runtime — no type tag is required at registration:

```go
// xlate.go — CallRpcMethod
if fn, ok := XlateFuncs[rpcFunc]; ok && fn.Type().NumIn() == 3 {
    // ActionCallpoint: 3 params → (vars, body, dbs)
    data, err = XlateFuncCall(rpcFunc, vars, body, dbs)
} else {
    // RpcCallpoint: 2 params → (body, dbs)
    data, err = XlateFuncCall(rpcFunc, body, dbs)
}
```

**Example — RPC callback** (global, no instance context):

```go
// annotation: sonic-ext:rpc-callback "rpc_showtech_cb"
var rpc_showtech_cb RpcCallpoint = func(body []byte, dbs [db.MaxDB]*db.DB) ([]byte, error) {
    // body is the JSON input payload; no instance key needed
    ...
}
```

**Example — Action callback** (needs to know which instance to act on):

```go
// annotation: sonic-ext:action-callback "act_get_ocm_raw_cb"
var act_get_ocm_raw_cb ActionCallpoint = func(vars map[string]string, body []byte, dbs [db.MaxDB]*db.DB) ([]byte, error) {
    port := vars["name"]  // channel-monitor list key from the URI
    if port == "" {
        return nil, tlerr.New("missing channel-monitor name in URI")
    }
    // use port to address the correct OCM instance
    ...
}
```

### 2.5 REST Framework Changes

**`src/sonic-mgmt-framework`**

#### `rest/server/context.go`

`RequestContext` gains an `IsAction` boolean flag:

```go
// IsAction indicates this is a YANG 1.1 action request (RFC 7950 Section 7.15).
// Actions use POST on data paths rather than the /restconf/operations/ prefix used by RPCs.
IsAction bool
```

#### `rest/server/handler.go`

`isOperationsRequest()` now recognises action requests in addition to the `/restconf/operations/` prefix check:

```go
func isOperationsRequest(r *http.Request) bool {
    k := strings.Index(r.URL.Path, restconfOperPathPrefix)
    if k >= 0 {
        return true  // classic RPC path prefix
    }
    cv := r.Context().Value(requestContextKey)
    if cv != nil {
        if rc, ok := cv.(*RequestContext); ok && rc.IsAction {
            return true  // action flag set by generated handler
        }
    }
    return false
}
```

When `isOperationsRequest()` returns `true` for a `POST`, `parseMethod` sets `args.method = "ACTION"`. The `invokeTranslib` switch then calls `translib.Action()` and returns HTTP 200 with the response payload:

```go
case "ACTION":
    req := translib.ActionRequest{
        Path:          args.path,
        Payload:       args.data,
        ClientVersion: args.version,
    }
    res, err1 := translib.Action(req)
    if err1 == nil {
        status = 200
        content = res.Payload
    } else {
        err = err1
    }
```

### 2.6 TransLib Changes

**`src/sonic-mgmt-common`**

#### `translib/translib.go`

`ActionRequest` / `ActionResponse` structs define the action invocation interface (analogous to the existing `RpcRequest` / `RpcResponse`). `Action()` calls `translateAction()` then `processAction()`.

#### `translib/common_app.go`

`processAction()` passes `pathInfo.Vars` (the URI list-key map) to `CallRpcMethod` so the callback receives instance context:

```go
func (app *CommonApp) processAction(dbs [db.MaxDB]*db.DB) (ActionResponse, error) {
    var resp ActionResponse
    var err error

    resp.Payload, err = transformer.CallRpcMethod(
        app.pathInfo.Path, app.pathInfo.Vars, app.body, dbs)

    return resp, err
}
```

The `pathInfo.Vars` field is populated during path parsing and contains the decoded list predicates, e.g. `{"name": "OCM0-0"}` for `channel-monitor=OCM0-0`.

### 2.7 OpenAPI Generator Changes

**`src/sonic-mgmt-framework/tools/pyang/pyang_plugins/openapi.py`**

- `walk_child()` routes `action` keyword to a new `handle_action()` instead of `handle_rpc()`.
- `handle_action()` generates the path under `/restconf/data` (not `/restconf/operations`), sets `x-action: true` on the generated OpenAPI entry, generates path parameters for all parent list keys (e.g. `{name}`), and attaches the output schema to the `200 OK` response.
- `build_payload()` skips `action` nodes to avoid duplicating them as data fields.
- `verb_responses["action"]` is defined as `{200: with content, 204, 404, 403}`.

### 2.8 Go Handler Template Changes

**`src/sonic-mgmt-framework/tools/codegen/go-server/templates-yang/controllers-api.j2`**

For routes marked `x-action`, the template reads the output schema from `responses["200"]` (not `responses["204"]` as for RPCs) and sets `rc.IsAction = true` so the REST server routes the request as an action:

```go
// Generated handler for an x-action route
func ActionGetOcmRaw(w http.ResponseWriter, r *http.Request) {
    rc, r := server.GetContext(r)
    rc.IsAction = true
    server.Process(w, r)
}
```

The `rc.IsAction = true` line is the only generated difference from a plain data-POST handler.

### 2.9 Sonic YANG Generator Changes

**`platform/otn-kvm/sonic-yanggen/sonic_yanggen.py`**

- Parses `sonic-ext:action-callback` deviations alongside `rpc-callback`.
- `_find_actions_in_subtree()`: recursive libyang traversal to locate `ACTION` nodes.
- `gen_container()`: emits list-level actions **inside the `_LIST` container** using `_find_actions_in_subtree()`.
- Sets `yang-version "1.1"` in the generated Sonic YANG when actions are present.
- `gen_actions()` + `_walk_actions()`: emits remaining container-level actions.
- `_emit_rpc_or_action(node, keyword)`: unified emitter for both `rpc` and `action`.

### 2.10 CLI Generator Changes

**`src/sonic-utilities/sonic_cli_gen/yang_parser.py`**

- Added `on_action()`: parses an `action` node into `{name, description, input, output, has_input, has_output}`.
- Added `get_actions()`: retrieves `action` elements from a YANG entity and maps through `on_action()`. Called from both `on_table_container()` (container-level) and `on_object_entity()` (list-level).
- `has_actions` flag replaced with `has_rpc_or_action` (checks both top-level `rpcs` and per-table/object `actions`).

**`src/sonic-utilities/templates/sonic-cli-gen/config.py.j2`**

- Replaced `gen_cfg_rpc` / `gen_cfg_action` macros with a unified `gen_cfg_operation` + `gen_cfg_run` pair. RPCs and actions share a single `run` subgroup per table/object.
- `gen_cfg_operation` behaviour depends on the presence of list keys: non-empty keys (list-level action) turn list keys into positional arguments and input fields into `--options`; empty keys (RPC or container-level action) turn all input into `--options`.

---

## 3 What is NOT Changed

- **RPC handling** — existing top-level RPCs continue to use `/restconf/operations/`. The RPC path in the REST server and translib is untouched.
- **transformer core** — `CallRpcMethod()` already accepted a `vars` argument; only `common_app.go` was updated to forward `pathInfo.Vars` into it.

---

## 4 Notes

- Any YANG module or annotation file referencing an `action` node must declare `yang-version "1.1"`.
- Per RFC 8040 §4.4.2: if an action has no `output` section the server MUST return `204 No Content`; if output is present the server returns `200 OK` with the payload.
