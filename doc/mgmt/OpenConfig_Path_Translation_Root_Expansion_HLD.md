# OpenConfig Path Translation HLD #

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High Level Design](#high-level-design)
- [SAI API](#sai-api)
- [Configuration and Management](#configuration-and-management)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Memory Consumption](#memory-consumption)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
- [Open/Action items - if any](#openaction-items---if-any)

### Revision
| Rev  | Rev Date   | Author(s)          | Change Description |
|------|------------|--------------------|--------------------|
| v0.1 | 09/17/2024 | Neha Das (Google)   | Initial version |

### Scope

This document describes the high-level design to add a plugin-based path translation layer between the UMF gNMI server and external data clients to translate both requests and responses for interoperability between multiple clients and server implementations.

### Definitions/Abbreviations

- [gNMI](https://github.com/openconfig/gnmi) : gRPC Network Management Interface
- API : Application Programming Interface
- SONiC: Software for Open Networking in the Cloud
- UMF : Unified Management Framework
- FE: Frontend
- BE: Backend

### Overview

Unified Management Framework (UMF) is a SONIC management framework which provides gNMI and other common north bound interfaces to manage configuration and status of SONIC based switches.

The difference in paths and formats used by existing clients and multiple sever implementations, including UMF, can lead to interoperability issues. Some of the gaps that we have encountered include:
1. Support for gNMI requests for config and telemetry at the Single root path which is currently not supported in UMF. Single root means the xpath `/openconfig`. UMF supports gNMI requests modeled in OpenConfig subtrees such as `/openconfig/interfaces`, `/openconfig/qos`, etc but not at the `/openconfig` root level.
2. Difference in path format in UMF's gNMI implementation `Origin:<empty>, Elements: /openconfig-interfaces:interfaces/interface[name=<>]` versus OpenConfig standard path `Origin: openconfig, Elements: /interfaces/interface[name=<>]`. In general, UMF uses `openconfig-${module-name}:${root-container-name}` as the first element of its path, whereas Openconfig uses `openconfig` as the origin and `${root-container-name}` for the first path element without module name. Some legacy clients/tools use the following format as well: `Origin: <empty>, Elements: /openconfig/interfaces/interface[name=<>]`

The feature discussed in this HLD proposes to solve the gaps listed above with the addition of a translation layer for Openconfig paths in the UMF gNMI server. This path translation framework will be responsible for translating requests coming into the server and responses going out of the server. This framework can have different plugins which perform different types of translations. The plugin that we have added supports modification of OpenConfig paths to UMF complaint path formats, as well as adding support for expanding the single root path to multiple root container paths.
This new translation layer is inserted between the UMF gNMI server and data clients to translate both requests and responses.

### Requirements

- The Openconfig path format translation in UMF should be lightweight and expandable based on future model additions.
- Clean APIs with minimal changes to UMF for easier upstreaming/integration with future UMF code drops.

### Architecture Design

This design does not change the existing SONiC Architecture but leverages the existing gNMI/telemetry server interface design. This design adds a new path translation layer within UMF.

### High-Level Design

A new path translation layer will be added for OpenConfig paths in the UMF gNMI server which would be responsible for translating requests with Openconfig standard path before it is processed. The translation layer is also responsible for converting the response from UMF path format to Openconfig standard path before the response is sent.

The current implementation will translate only if the original request uses Openconfig Path format, and this can be extended in the future to perform other types of translations.

The new translation layer is also used to expand the single root path into multiple module subtrees such as `/interfaces`, `/qos`, etc.  The translation layer will identify the single root path, translate it to multiple supported subtree request paths (with Openconfig path format), then pass the modified requests to UMF Data Clients for further processing. It also translates the responses from UMF data clients to Openconfig single root path format, and passes back to UMF gNMI Server.

The translation layer will only translate when the request is using Openconfig path format. For other formats, it will pass through the original request without any modification. The translation of response will only happen if the request has been translated.

This new translation layer is inserted between the UMF gNMI server and data clients to translate both requests and responses as illustrated below.

![SupportOpenconfigCompliantPathInUMF](https://github.com/user-attachments/assets/43221de5-dac2-4ccd-97b6-b7e05cc99827)

#### Path Format Translation Layer API
There are two sets of interfaces defined in the translation layer:
- Translator interface
- Translation API.

##### Translator Interface
Translator interface defines the interface for path format translators. A translator implementing this interface can register itself by calling the register API.
Currently only the Openconfig path format translator is implemented.

(gnmi_server/pathtransl/pathTranslator.go, openconfigTransl.go)

```
type TranslatorCtx interface
type Translator interface {
	Name() string
	TranslGetRequest(req *gnmipb.GetRequest) (bool, TranslatorCtx)
	TranslGetResponse(resp *gnmipb.GetResponse, ctx TranslatorCtx)
	TranslSetRequest(req *gnmipb.SetRequest) (bool, TranslatorCtx)
	TranslSetResponse(resp *gnmipb.SetResponse, ctx TranslatorCtx)
	TranslSubscribeRequest(req *gnmipb.SubscribeRequest) (bool, TranslatorCtx)
	TranslSubscribeResponse(resp *gnmipb.SubscribeResponse, ctx TranslatorCtx)
}
func register(transl Translator) int
```

##### Translation APIs
Translation APIs are used by UMF gNMI Server to invoke the path format translation. The translation only happens if there is one registered translator that translates the request. Otherwise, an invalid TranslatorCtx (nil) will be returned to indicate no translation occured.

(gnmi_server/pathtransl/pathTranslator.go)

```
func TranslGetRequest(req *gnmipb.GetRequest) TranslatorCtx
func TranslGetResponse(resp *gnmipb.GetResponse, ctx TranslatorCtx)
func TranslSetRequest(req *gnmipb.SetRequest) TranslatorCtx
func TranslSetResponse(resp *gnmipb.SetResponse, ctx TranslatorCtx)
func TranslSubscribeRequest(req *gnmipb.SubscribeRequest) TranslatorCtx
func TranslSubscribeResponse(resp *gnmipb.SubscribeResponse, ctx TranslatorCtx)
```

#### Invocation for Translation
##### GetRequest & GetResponse
Translation of GetRequest/GetResponse happens inside gNMI Server’s Get process.

(gnmi_server/Server.go)
```
// Get implements the Get RPC in gNMI specification.
func (s *Server) Get(ctx context.Context, req *gnmipb.GetRequest) (*gnmipb.GetResponse, error) {
  ...
  translCtx := pathtransl.TranslGetRequest(req)
  ... // Data clients process req, and return GetResponse resp
  pathtransl.TranslGetResponse(resp, translCtx)
  return resp, err
}
```

##### SetRequest & SetResponse
Translation of SetRequest/SetResponse happens inside GNMI Server’s Set process. 

(gnmi_server/Server.go)
```
// Set implements the Set RPC in gNMI spec.
func (s *Server) Set(ctx context.Context, req *gnmipb.SetRequest) (*gnmipb.SetResponse, error) {
  ...
  translCtx := pathtransl.TranslSetRequest(req)
  ... // Data clients process req, and return SetResponse resp
  pathtransl.TranslSetResponse(resp, translCtx)
  return resp, err
}
```

##### SubscribeRequest
Translation of SubscribeRequest happens inside the Subscribe Client’s Run process before request is passed to transclient.

(gnmi_server/client_subscribe.go)
```
func (c *Client) Run(stream gnmipb.GNMI_SubscribeServer) (err error) {
  ...
  c.translCtx := pathtransl.TranslSubscribeRequest(req)
  ...
}
```

##### SubscribeResponse
Translation of SubscribeRequest happens inside the Subscribe Client’s Send process before notification response is sent.

(gnmi_server/client_subscribe.go)
```
func (c *Client) send(stream gnmipb.GNMI_SubscribeServer) error {
  ...
  pathtransl.TranslSubscribeResponse(resp, c.translCtx)
  ...
}
```

#### Single Root Translation
Single Root means xpath `/openconfig`, which UMF currently does not support. We can use this translation layer to support single root as well.

##### GetRequest
Single Root GetRequest is translated into a GetRequest with all the supported OpenConfig paths as below:

```
Original GetRequest (single root)
prefix:<origin:"openconfig">path:<>
```

```
Translated GetRequest
prefix:<>path:<elem:<name:"openconfig-interfaces:interfaces">>path:<elem:<name:"openconfig-lacp:lacp">>path:<elem:<name:"openconfig-platform:components">>path:<elem:<name:"openconfig-qos:qos">>path:<elem:<name:"openconfig-sampling:sampling">>path:<elem:<name:"openconfig-system:system">>
```

##### GetResponse
Since the single root GetRequest is translated into multiple top-container paths, the JSON_IETF response will receive multiple notifications (one for each translated path). These multiple notifications need to be combined into one single JSON_IETF value and sent back to the client.
Example:
```
Original GetResponse (with multiple notification)
notification:<timestamp:1234566 prefix:<> update:<path:<elem:<name:"openconfig-interfaces:interfaces">>val:<json_ietf_val:"{\"openconfig-interfaces:interfaces\":{...}}“>
update:<path:<elem:<name:"openconfig-platform:components">>val:<json_ietf_val:"{\"openconfig-platform:components\":{xxx}}">
>
```
```
Translated (combined) GetResponse
notification:<timestamp:1234566
prefix:<origin:"openconfig">
update:<path:<> val:<json_ietf_val:
"{
  \"openconfig-interfaces:interfaces:\": {...},
  \"openconfig-platform:components:\": {xxx}
}“
>>
```

##### SetRequest
For a Single root SetRequest with JSON_IETF encoding, the JSON value is in the same format as in the translated GetResponse above.
A mix of single root and non-single root SET is not supported. So for delete/update/replace, either there is only one root delete/update/replace, or non-single root ones.

To translate the SetRequest:

###### Single Root Delete
It will be translated into multiple delete paths as show below:
```
Original Delete
prefix:<origin:"openconfig">delete:<>
```
```
Translated Delete
prefix:<>delete:<elem:<name:"openconfig-interfaces:interfaces">>delete:<elem:<name:"openconfig-lacp:lacp">>delete:<elem:<name:"openconfig-platform:components">>delete:<elem:<name:"openconfig-qos:qos">>delete:<elem:<name:"openconfig-sampling:sampling">>delete:<elem:<name:"openconfig-system:system">>
```

###### Single Root Update/Replace
For update and replace, the JSON payload needs to be parsed and the payload has to be separated into multiple JSON payloads according to the top-container names, and then placed into individual updates/replaces.
```
Original Update
prefix:<origin:"openconfig">
update:<path:<> val:<json_ietf_val:
"{
  \"openconfig-interfaces:interfaces:\": {...},
  \"openconfig-platform:components:\": {xxx}
}“
>>
```
```
Translated Update
prefix:<>
update:<path:<elem:<name:"openconfig-interface:interfaces">> val:<json_ietf_val:
"{
  \"openconfig-interfaces:interfaces:\": {...},
}“>
update:<path:<elem:<name:"openconfig-platform:components">> val:<json_ietf_val:
"{
  \"openconfig-platform:components:\": {...},
}“>
>
```

##### SetResponse
Since we do not support the mix of single root set and non-single root set operations, we will only translate single root SetResponse if the original SetRequest is single root.
For the translation, we just need to use a single root UpdateResult to replace the Delete/Update/Replace.
For example:
```
Original SetResponse
prefix:<>
response:<timestamp:123456 path:<elem:<name:"openconfig-interfaces:interfaces">>op:Update>
response:<timestamp:123456 path:<elem:<name:"openconfig-platform:components">>op:Update>
response:<timestamp:123456 path:<elem:<name:"openconfig-qos:qos">>op:Replace>
response:<timestamp:123456 path:<elem:<name:"openconfig-lacp:lacp">>op:Replace>
```
```
Translated SetResponse
prefix:<origin:"openconfig">
response:<timestamp:123456 path:<>op:Update>
response:<timestamp:123456 path:<>op:Replace>
```

##### SubscribeRequest
For a single root SubscribeRequest, the translation is similar to a GetRequest. It will be translated into a SubscribeRequest with multiple top-container paths.

##### SubscribeResponse
Since SubscribeRespone is per update, there is nothing to change for single root translation on updates.


### SAI API

This HLD does not include any changes to the SAI API.

### Configuration and Management
The configuration is updated with the full set of OpenConfig models at the root, instead of individual subtrees.

#### CLI/YANG model Enhancements

This HLD does not include any enhancements to CLI or YANG models.

#### Config DB Enhancements

This HLD does not include any changes to the Config DB.

### Warmboot and Fastboot Design Impact

This HLD does not have any impact on Warmboot and Fastboot.

### Memory Consumption

### Restrictions/Limitations

### Testing Requirements/Design

In this section, we discuss both unit tests and end-to-end test cases for testing the root expansion feature.

#### Unit Test cases

- TestSplitRootPathGetRequest
    - Test that the single root path is split into multiple supported subtree paths.
    - Test the correctness of individual split paths in the new request.
- TestSplitRootPathGetResponse
    - Tests that the multiple supported subtree paths are combined into a single root path request.
    - Test the correctness of the combined paths in the new response.
- TestSplitRootPathSetDeleteRequest
    - Test that the single root path is split into multiple supported subtree paths.
    - Test the correctness of individual split paths in the new request.
- TestSplitRootPathSetDeleteResponse
    - Tests that the multiple supported subtree paths are combined into a single root path request.
    - Test the correctness of the combined paths in the new response.
- TestSplitRootPathSetUpdateRequest
    - Test that the single root path is split into multiple supported subtree paths.
    - Test the correctness of individual split paths in the new request.
- TestSplitRootPathSetUpdateResponse
    - Tests that the multiple supported subtree paths are combined into a single root path request.
    - Test the correctness of the combined paths in the new response.
- TestSplitRootPathSetReplaceRequest
    - Test that the single root path is split into multiple supported subtree paths.
    - Test the correctness of individual split paths in the new request.
- TestSplitRootPathSetReplaceResponse
    - Tests that the multiple supported subtree paths are combined into a single root path request.
    - Test the correctness of the combined paths in the new response.
- TestSplitRootPathSubscribeRequest
    - Test that the single root path is split into multiple supported subtree paths.
    - Test the correctness of individual split paths in the new request.
- TestSplitRootPathSubscribeResponse
    - No changes in the single root translation on SubscribeResponse updates.
- TestMixNotSupported
    - Test that a mix of single root and non-single root SET is not supported.

#### End-to-end Test cases
- Test that the Set at Root path is applied and config is converged.
- Test that the Get at Root path returns all supported paths.
- Test that the Subscribe at Root path returns expected subtree values.

### Open/Action items - if any
