# SONiC Management Framework Developer Guide

## Rev 0.9

## Table of Contents

* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definition/Abbreviation](#definitionabbreviation)
* [References](#references)
* [Prerequisites](#prerequisite)
* [1 Architecture](#1-architecture)
    * [1.1 Overview](#11-overview)
    * [1.2 Repositories](#12-repositories)
    * [1.3 Containers](#13-containers)
* [2 Developer Workflow](#2-developer-workflow)
    * [2.1 ABNF Schema](#21-abnf-schema)
    * [2.2 SONiC YANGs](#22-sonic-yang)
    * [2.3 OpenConfig YANGs](#23-openconfig-yang)
        * [2.3.1 Directory structure](#231-directory-structure)
        * [2.3.2 Extension YANGs](#232-extension-yangs)
        * [2.3.3 Extension YANG Style Guide](#233-extension-yang-style-guide)
        * [2.3.4 Backward Compatibility](#234-backward-compatibility)
        * [2.3.5 Versioning](#235-versioning)
        * [2.3.6 Tools](#236-tools)
    * [2.4 Config Translation App](#24-config-translation-app)
        * [2.4.1 Translation Approaches](#241-translation-approaches)
        * [2.4.2 YGOT](#242-ygot)
        * [2.4.3 DB Access APIs](#243-db-access-apis)
        * [2.4.4 Logging](#244-logging)
        * [2.4.5 Error Response](#245-error-response)
        * [2.4.6 D-Bus messaging](#246-d-bus-messaging)
    * [2.5 Transformer](#25-transformer)
        * [2.5.1 Annotation File](#251-annotation-file)
        * [2.5.2 Annotations](#252-annotate-yang-paths)
            * [2.5.2.1 sonic-ext:table-name](#2521-sonic-exttable-name-table_name)
            * [2.5.2.2 sonic-ext:field-name](#2522-sonic-extfield-name-field_name)
            * [2.5.2.3 sonic-ext:key-delimiter](#2523-sonic-extkey-delimiter-delim)
            * [2.5.2.4 sonic-ext:key-name](#2524-sonic-extkey-name-value)
            * [2.5.2.5 sonic-ext:key-transformer](#2525-sonic-extkey-transformer-function)
            * [2.5.2.6 sonic-ext:field-transformer](#2526-sonic-extfield-transformer-function)
            * [2.5.2.7 sonic-ext:table-transformer](#2527-sonic-exttable-transformer-function)
            * [2.5.2.8 sonic-ext:subtree-transformer](#2528-sonic-extsubtree-transformer-function)
            * [2.5.2.9 sonic-ext:db-name](#2529-sonic-extdb-name-name)
            * [2.5.2.10 sonic-ext:post-transformer](#25210-sonic-extpost-transformer-function)
            * [2.5.2.11 sonic-ext:get-validate](#25211-sonic-extget-validate-function)
            * [2.5.2.12 sonic-ext:rpc-callback](#25212-sonic-extrpc-callback-function)
        * [2.5.3 Guidelines for Choosing Annotation Type](#253-guidelines-for-choosing-annotation-type)
        * [2.5.4 Manifest file](#254-manifest-file)
        * [2.5.5 Callback functions](#255-callback-functions)
        * [2.5.6 Usage Examples](#256-usage-examples)
    * [2.6 App Module](#26-app-module)
    * [2.7 Config Validation Library](#27-config-validation-library)
        * [2.7.1 CVL Schema](#271-cvl-schema)
        * [2.7.2 Custom Validation](#272-custom-validation)
        * [2.7.3 Platform Validation](#273-platform-validation)
        * [2.7.4 CVL Debug Logs](#274-cvl-debug-logs)
    * [2.8 Non-DB Data](#28-non-db-data)
        * [2.8.1 Host Modules](#281-host-modules)
        * [2.8.2 FRR Integration](#282-frr-integration)
    * [2.9 KLISH CLI](#29-klish-cli)
        * [2.9.1 CLI components](#291-cli-components)
        * [2.9.2 CLI development steps](#292-cli-development-steps)
        * [2.9.3 Enhancements to Klish](#293-enhancements-to-klish)
        * [2.9.4 Preprocess XML files](#294-preprocess-xml-files)
        * [2.9.5 CLI directory structure](#295-cli-directory-structure)
        * [2.9.6 Generic REST Client](#296-generic-rest-client-for-actioner-scripts)
        * [2.9.7 Tool for JSON navigation in jinja templates](#297-tool-for-json-navigation-in-jinja-templates)        
    * [2.10 REST Server](#210-rest-server)
    * [2.11 gNMI](#211-gnmi)
    * [2.12 Compilation](#212-compilation)
        * [2.12.1 sonic-mgmt-common](#2121-sonic-mgmt-common)
        * [2.12.2 sonic-mgmt-framework](#2122-sonic-mgmt-framework)
        * [2.12.2 sonic-telemetry](#2122-sonic-telemetry)
    * [2.13 Unit Testing](#213-unit-testing)
        * [2.13.1 REST API testing](#2131-rest-api-testing)
        * [2.13.2 Local REST Server and CLI](#2132-local-rest-server-and-cli)
        * [2.13.3 gNMI Unit Testing](#2133-gnmi-unit-testing)
        * [2.13.3 Spytest](#2133-spytest)
* [3 Appendix](#3-appendix)
    * [3.1 Code Generators](#31-code-generators)

## List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

## Revision

| Rev |     Date    |       Author            | Change Description                                                   |
|:---:|:-----------:|:-----------------------:|----------------------------------------------------------------------|
| 0.1 | 09/12/2019  | Anand Kumar Subramanian | Initial version                                                      |
| 0.2 | 09/16/2019  | Prabhu Sreenivasan      | Added references, prerequisites and updated section 2.1.2 SONiC YANG |
| 0.3 | 09/16/2019  | Partha Dutta            | Updated SONiC YANG Guideline link                                    |
| 0.4 | 09/18/2019  | Anand Kumar Subramanian | Updated transformer section                                          |
| 0.5 | 09/20/2019  | Mohammed Faraaz C       | Updated REST Unit testing                                            |
| 0.6 | 09/20/2019  | Prabhu Sreenivasan      | Updated reference links and yang path                                |
| 0.7 | 09/23/2019  | Partha Dutta            | Updated SONiC YANG, CVL, gNMI section                                |
| 0.8 | 06/18/2019  | Kwangsuk Kim            | Updated CLI section                                                  |
| 0.9 | 06/22/2020  | Sachin Hola             | Incorporated Phase-II changes, with new repo structure.  |

## About this Manual

This document provides developer guidelines for Management framework feature development in SONiC.

## Scope

This document describes the steps the feature developers need to follow to develop a CLI, REST and gNMI for a given feature using the Management framework.

## Definition/Abbreviation

### Table 1: Abbreviations

| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| CVL                      | Config Validation Library           |
| NBI                      | North Bound Interface               |
| ABNF                     | Augmented Backus-Naur Form          |
| YANG                     | Yet Another Next Generation         |
| JSON                     | Java Script Object Notation         |
| XML                      | eXtensible Markup Language          |
| gNMI                     | gRPC Network Management Interface   |
| YGOT                     | YANG Go Tools                       |
| SONiC YANG               | YANG file which describes Redis DB schema for a given feature |
| RPC                      |  Remote Procedure Call              |

## References

| Document |  Link  |
|:--------:|:-------|
| SONiC YANG model guideline |  https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md |
| SONiC Management Framework HLD | https://github.com/Azure/SONiC/pull/436 |
| RFC 7950                  | August 2016         | https://tools.ietf.org/html/rfc7950 |

## Prerequisite

* Knowledge of YANG syntax
* GO Programming language
* SONiC Management Framework Architecture

## 1 Architecture

### 1.1 Overview

![Management Framework Architecture diagram](https://github.com/Azure/SONiC/blob/34cac1aabdc865fc41cbe064a2ab2442645524b1/doc/mgmt/images/Mgmt_Frmk_Arch.jpg)

In the above architecture diagram developer needs to write all the elements in green. Following are blocks that the developer has to write in order to get CLI, REST and gNMI support for the new feature being developed.

1) YANG Models

2) ABNF schema and SONiC YANG

3) Transformer - includes YANG annotations and custom translation

4) KLISH XML including Actioner and Renderer scripts

### 1.2 Repositories

Management framework and application code are distributed across 3 repositories.

1) **sonic-mgmt-common**

    - Translib, CVL and transformer infrastructure code
    - SONiC YANGs
    - OpenConfig, IETF YANGs and their extension YANGs
    - Trabsformer annotations and custom transformer functions
    - CVL custom validation functions
    - Host modules (application logic that runs on switch host)

2) **sonic-mgmt-framework**

    - YANG to OpenAPI converter and OpenAPI codegen tools
    - REST Server
    - KLISH CLI core and SONiC specific patches
    - CLI models (KLISH XML)
    - CLI actioner scripts
    - CLI renderer templates

3) **sonic-telemetry**

    - Telemetry server

All YANG data models and their translation logic goes into sonic-mgmt-common repository.
sonic-mgmt-framework adds REST and CLI interfaces for these YANG data models.
sonic-telemetry adds gNMI interface.

### 1.3 Containers

There will be 2 docker containers providing management services.

1) **mgmt-framework** -- provides REST Server and CLI
2) **telemetry** -- Telemetry service

## 2 Developer Workflow

Following are the steps to be followed by the application developer.

### 2.1 ABNF Schema

First step is to define the redis DB schema for the application/feature.
Usual SONiC practice is to express the database schema in ABNF.
An existing DB table can be modified or new tables may be introduced.

If you are defining new tables, try to keep it in line with the OpenConfig YANG model
for the feature (explained in next steps). Usually a redis table maps to YANG 'list' node.
Try to avoid mapping one redis table to multiple YANG lists.
This will make translation logic complex and requires custom translation code.

### 2.2 SONiC YANG

SONiC YANGs express the redis db schema in YANG format.
These YANGs should strictly adhere to the [SONiC YANG Model Guidelines](https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md) published by SONiC Community.

SONiC YANG models **MUST** be defined for every DB schema consumed by the management applications.
CVL, transformer and other framework components use these YANGs to understand the DB schema.

SONiC YANGs are maintained in `sonic-mgmt-common/models/yang/sonic` directory.

### 2.3 OpenConfig YANG

Every feature should support corresponding OpenConfig YANG model.
An OpenConfig compliant YANG model should be defined if there was no standard OpenConfig YANG.
Extension YANGs should be written to add additional data nodes over standard YANG and
to remove unsupported nodes.

Few existing features implemented IETF YANGs. However going forward only OpenConfig YANGs
and OpenConfig compliant extension YANGs should be used.

#### 2.3.1 Directory structure

All YANGs are maintained under `sonic-mgmt-common/models/yang` directory.

```
models
└── yang             : Standard OpenConfig and IETF YANGs
    ├── annotations  : Transformer annotations (section 2.5.2)
    ├── common       : Dependencies for standard YANGs
    ├── extensions   : Extensions YANGs
    ├── sonic        : SONiC YANGs (section 2.2)
    ├── testdata     : Test YANGs - ignored
    └── version.xml  : YANG bundle version configuration file
```

Unmodified OpenConfig and IETF YANGs should be kept in `yang` directory.
Framework will automatically enable REST and gNMI interfaces for these YANGs.

These YANGs refer few common YANG models, like ietf-interfaces.yang, for which we dont want
north bound interfaces. Such dependent YANGs must be kept in `yang/common` directory.
Framework will use these YANGs only to resolve compilation dependencies but not enable
REST and gNMI interaces for them.

All custom YANGs should be kept in `yang/extensions` directory.

#### 2.3.2 Extension YANGs

**Standard OpenConfig and IETF YANGs must not be modified directly**.
All customizations must be applied through extension YANGs.
Even new OpenConfig compliant YANGs (when there is no standard YANG) will also
be treated as an extension to OpenConfig.

Extension YANG should use YANG [augment](https://tools.ietf.org/html/rfc6020#section-4.2.8)
statements to add new data nodes to standard OpenConfig or IETF YANG data tree.

YANG [deviation](https://tools.ietf.org/html/rfc6020#section-7.18.3) statement should
be used to mark an existing data node as "not-supported" or to modify it.

Example:

```yang
module openconfig-acl-ext {
    namespace "http://github.com/Azure/oc-acl-ext";
    prefix oc-acl-ext;

    import openconfig-acl { prefix oc-acl; }

    /* Add an alt-name config to ACL */
    augment "/oc-acl:acl/acl-sets/acl-set/config" {
        leaf alt-name {
            type string;
        }
    }

    /* Mark ACL description not supported */
    deviation "/oc-acl:acl/acl-sets/acl-set/config/description" {
        deviate not-supported;
    }   

    /* Restrict ACL name to max 127 characters */
    deviation "/oc-acl:acl/acl-sets/acl-set/config/name" {
        deviate replace {
            type string {
                length "1..127";
            }
        }
    }
}
```

#### 2.3.3 Extension YANG Style Guide

OpenConfig extension YANGs should adhere to [OpenConfig style guidelines](https://github.com/openconfig/public/blob/master/doc/openconfig_style_guide.md).

Please review [current model hierarchy](http://www.openconfig.net/projects/models)
and IETF draft [draft-openconfig-netmod-opstate-01](https://tools.ietf.org/html/draft-openconfig-netmod-opstate-01) 
on overall OpenConfig modeling approach.

General guidelines for extension YANGs:

- All extension YANGs should be named as **openconfig-{function}-ext.yang**.

- **namespace** should be "http://openconfig.net/yang/{function}-ext" or "http://openconfig.net/yang/{function}/extension"

- Namespace **prefix** should be "oc-{function}-ext".

- Specify **organization**, **contact** and **oc-ext:origin** as "SONiC".

- Add module **description** statement with new features covered in the extension yang;
like [this](https://github.com/openconfig/public/blob/master/release/models/policy/openconfig-routing-policy.yang#L24)

- Include **revision** and **oc-ext:openconfig-version** statements.
    - oc-ext:openconfig-version should be "0.1.0" for the initial version (when a new extension YANG is defined)
    - Update the oc-ext:openconfig-version and add a revision statement for every enhancement to the mode.
    An enhancement may be split into multiple commits within a release.
    But all such related commits (within a release) should be grouped as one version change.
    - Version updates should follow [sematic versioning](https://semver.org/#semantic-versioning-specification-semver)
    guidelines. More details are at [section 2.3.5](#235-versioning)
    - Revision statements should be reverse chronological order (latest should be at the top).

- Do not use tab characters. Always expand tabs into 4 spaces.

- Try to maintain 72 column width through-out the file (like RFC document)

Naming conventions:

- Use **lower case with dash separated words** for all YANG node names (container, list, leaf-list, leaf,  grouping etc).
    Example: "ip-address"

    Do not use upper case, underscores, camel case; like "IP_Address" or "ipaddress" or "ipAddress".

- Use **upper case with underscore separated words** for enum and identity names.
Example: "IF_ETHERNET".

- Try to avoid cryptic and abbreviated words, unless they are widely used feature names.

    Example: "arp", "mpls", "fbs" are okay. But avoid names like "addr", "ip-addr", "neigh".

- Grouping names should make it easy to quickly understand the nature of the data within.
A suggested convention is ***xxx-yyy[-config|state|top]***, where xxx is the top-level module name 
(without the openconfig prefix), yyy is a string which indicates the contents of the groupings.

    Example: "interface-common-state", "subinterfaces-config".

- Use standard typedefs as much as possible.
Most of the common data types are already defined in one of these YANGs.
    - openconfig-types.yang
    - openconfig-inet-types.yang
    - openconfig-yang-types.yang
    - ietf-inet-types.yang
    - ietf-yang-types.yang

    Also look for openconfig-{feature}-types.yang for the feature specific typedefs.

Data tree guidelines:

- TODO

#### 2.3.4 Backward Compatibility

All extensions to standard OpenConfig/IETF YANGs or incremental changes to the extension
YANGs can affect REST and gNMI clients. Strict adherence to 
[YANG module update guidelines](https://tools.ietf.org/html/rfc6020#section-10) is a must.

#### 2.3.5 Versioning

Individual YANG models should be versioned through **revision** and **oc-ext:openconfig-version** statements.
In addition, a YANG bundle version (collective version number for all supported YANG modules)
is managed via `models/yang/version.xml` file.
YANG bundle version is used for API versioning feature (in future release).

YANG bundle version uses sematic versioning format -- ie, **{major}.{minor}.{patch}** format.
It should be updated for every YANG update or once in a release.

**Major version** should be incremented if YANG model is changed in a non backward compatible manner.
Such changes should be avoided.

- Delete, rename or relocate data node
- Change list key attributes
- Change data type of a node to an incompatible type
- Change leafref target

**Minor version** should be incremented if the YANG change modifies the API in a backward
compatible way. Patch version should be reset to 0.
Candidate YANG changes for this category are:

- Add new YANG module
- Add new YANG data nodes
- Mark a YANG data node as deprecated
- Change data type of a node to a compatible type
- Add new enum or identity

**Patch version** should incremented for cosmetic fixes that do not change YANG API.
Candidate YANG changes for this category are:

- Change description, beautification.
- Expand pattern or range of a node to wider set.
- Change must expression to accept more cases.
- Error message or error tag changes.

#### 2.3.6 Tools

Framework provides multiple tools and code generators to work with the YANGs.
Details of each code generators is in [section 3.1](#31-code-generators).
All the tools are automatically run during sonic-mgmt-common build.
They can also be triggered manually to validate YANG changes.

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-common
make models
```

It validates all the YANGs under `yang` directory using [pyang tool](http://www.yang-central.org/twiki/pub/Main/YangTools/pyang.1.html) and generates human readable reports.

##### 2.3.6.1 YANG Text Tree

This is the standard pyang text tree output generated through "-f tree" option.
Two files are generated:

1) `sonic-mgmt-common/models/yang/allyangs.tree` --
Combined tree for the OpenConfig and IETF YANGs and their extension YANGs

2) `sonic-mgmt-common/models/yang/sonic/allyangs.tree` --
Combined tree for all SONiC YANGs

Sample:

```text
module: openconfig-lldp
  +--rw lldp
     +--rw config
     |  +--rw enabled?                      boolean
     |  +--rw hello-timer?                  uint64
     |  +--rw suppress-tlv-advertisement*   identityref
     |  +--rw system-name?                  string
     |  +--rw system-description?           string
     |  +--rw oc-lldp-ext:multiplier?       uint8
     |  +--rw oc-lldp-ext:mode?             lldp-ext-mode-type
```

##### 2.3.6.2 YANG HTML Tree

This is also a standard pyang tree output generated through "-f jstree" option.
It is equivalent to the text tree but provides expand/collapse controls at each node. 

Two files are generated:
1) `sonic-mgmt-common/models/yang/allyangs_tree.html`
2) `sonic-mgmt-common/models/yang/sonic/allyangs_tree.html`

##### 2.3.6.3 YANG Markdown Tree

Markdown tree is similar to text tree but contains markdown annotations to highlight
the nodes added and removed though extension YANGs.
Newly added nodes (through augment statements) are highlighted in green colour.
Removed nodes (through "not-supported" deviation) are highlighted in red color.
This is equivalent of diff between standard YANG data tree and the final YANG tree
after applying all extension YANGs.

Markdown tree file path: `sonic-mgmt-common/models/yang/yang_tree.md`

Sample:

```diff
 module: openconfig-lldp
  +--rw lldp
     +--rw config
     |  +--rw enabled?                      boolean
     |  +--rw hello-timer?                  uint64
     |  +--rw suppress-tlv-advertisement*   identityref
     |  +--rw system-name?                  string
     |  +--rw system-description?           string
+    |  +--rw oc-lldp-ext:multiplier?       uint8
+    |  +--rw oc-lldp-ext:mode?             lldp-ext-mode-type
-    |  +--rw chassis-id?                   string
-    |  +--rw chassis-id-type?              oc-lldp-types:chassis-id-type
```

##### 2.3.6.3 OpenConfig Style Checker

TODO


### 2.4 Config Translation App

Config Translation App translates data from northbound API schema to native
[ABNF schema](#21-abnf-schema) and vice versa.
Northbound API schema are defined by OpenConfig or IETF YANGs and ther extensions.

#### 2.4.1 Translation Approaches

There are two approaches to develop the translation app.

1. [Transformer](#25-transformer)
2. [App Module](#26-app-module)

Transformer is the preferred approach for develpoing the translation app.
It reduces the coding and maintenance effort by hiding the most of the YANG
hierarchy tranversal in the framework itself.
New features can be introduced into Translib without affecting existing translation apps.

An App Module would receive the raw inputs passed by the clients and shloud code for every possible scenario.

Type of translation app can be selected per YANG module.
New additions to an existing YANG module should use the current translation approach used by that YANG.
It is not possible to support part of the YANG tree through App Modules and part through Transformer.

All new YANG modules should use transformer.

#### 2.4.2 YGOT

TODO

#### 2.4.3 DB Access APIs

TODO

#### 2.4.4 Logging

Translation apps should use Go "github.com/golang/glog" library for logging.

Guidelines:
- Use `glog.Infof()` for logging info messges. Info is enabled by default.
- Use `glog.Errorf()` for logging error messages.
- Use `glog.V(1).Infof()` for debug messages.
Typically, payloads or DB data should be logged this way.
This style of logging is called verbose logging and they are not enabled by default.
Program should be started with a command line argument "-v" to enable verbosity levels.
- Use `glog.V(2).Infof()` for more verbose developer traces.
- Avoid using higer verbosity levels, fatal logs, `fmt.Printf()` and other logging libraries.

Examples:

```go
import (
    "github.com/golang/glog"
)

// INFO log
glog.Infof("Processing ACL %s, %v", aclName, aclType)

// ERROR log
glog.Errorf("GetEntry returned error %v", err)

// DEBUG log
glog.V(1).Infof("Payload received = %v", data)

// DEBUG log which requires lot of formatting.
if glog.V(1) {
    s := doNiceFormatting(bigdata)
    glog.Infof("data = %s", s)
}
```

Log verbosity level for REST and gNMI servers can be changed via CONFIG_DB entries.
Details are in [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/master/doc/mgmt/Management%20Framework.md#322414-db-schema).

#### 2.4.5 Error Response

Translation apps should return Go error objects defined in
`sonic-mgmt-common/translib/tlerr/app_errors.go` file to report errors.
Translib infrastructure stops further processing of the request and returns the error
back to the service (REST or gNMI) which invoked the Translib APIs.
Protocol specific error response will be prepared by individual service.

Application error types:

| Error object       | Error condition                      | Constructor function      |
|--------------------|--------------------------------------|---------------------------|
| InvalidArgsError   | Bad request, constraint error        | `tlerr.InvalidArgs()`     |
| NotFoundError      | Target resource not found            | `tlerr.NotFound()`        |
| AlreadyExistsError | Dupicate create                      | `tlerr.AlreadyExists()`   |
| NotSupportedError  | Unspported operation                 | `tlerr.NotSupported()`    |
| InternalError      | Generic error during app execution   | `tlerr.New()`             |
| AuthorizationError | User is not authorized for the operation |                       |

Exampels:

```go
import (
    "github.com/Azure/sonic-mgmt-common/translib/tlerr"
)

// InvalidArgsError
return tlerr.InvalidArgs("Priority value %d is out of range[1-65535]", priority)

// NotFoundError
return tlerr.NotFound("ACL %s/%v not found", aclName, aclType)

// AlreadyExistsError
return tlerr.AlreadyExists("Duplicate ACL %s/%v", aclName, aclType)

// NotSupportedError
return tlerr.NotSupported("Cannot delete Ethernet interface")

// NotSupportedError
return tlerr.New("FRR returned %d", status)
```

Avoid returning other error objects created through `errors.New()` or `fmt.Errorf()`.
Translib will propagate such errors but REST/gNMI service cannot map them to correct protocol error codes.

Error types defined in `sonic-mgmt-common/translib/tlerr/tlerr.go` are reserved for Translib's internal use.

#### 2.4.6 D-Bus messaging

TODO

### 2.5 Transformer

Transformer provides a generic infrastructure for Translib to programmatically translate YANG to ABNF/Redis schema and vice versa, using YANG extensions to define translation hints along the YANG paths. At run time, the translation hints are mapped to an in-memory Transformer Spec that provides two-way mapping between YANG and ABNF/Redis schema for Transformer to perform data translation.

In case that SONiC YANG modules are used by NBI applications, the Transformer performs 1:1 mapping between a YANG object and a SONiC DB object without a need to write special translation codes or any translation hints.

If you use the openconfig YANGs for NBI applications, you need special handling to translate the data between YANG and ABNF schema. In such case, you have to annotate YANG extensions and write callbacks to perform translations where required.

In either case, the default application [common-app.go](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/translib/common_app.go) generically handles both set and get requests with the returned data from Transformer.  

Basic worklflow for developing a Translation App using transformer:

1) Create an annotation file template (for new YANGs)
2) Fill transformer annotations for YANG paths in the annotation file.
3) Register YANG and annotation file names in the manifest file (for new YANGs)
4) Implement the transformer callback functions if any.

#### 2.5.1 Annotation File

Annotation file contains translation hints in YANG format.
It uses YANG deviation statements to attach transformer annotation to specific YANG paths.
However these deviations do not affect the data model.
It only attaches additional metdata to YANG paths for Transformer's use.

All annotation files should be kept in `sonic-mgmt-common/models/yang/annotations` directory.

A template annotation file can be generated using `sonic-mgmt-common/tools/xfmr/annotate.sh` script.
It takes one or more YANG file names and writes the annotation template file contents to stdout.
Output can be redirected to specific annotation file under `yang/annotations` directory.
Template file contains empty "deviate add" statements for all YANG paths from the specified YANG files.

```bash
$ cd /sonic/sonic-buildimage/src/sonic-mgmt-common
$ tools/xfmr/annotate.sh
usage: tools/xfmr/annotate.sh YANG_FILE_NAME...

$ tools/xfmr/annotate.sh openconfig-lldp.yang
module openconfig-lldp-annot {

    yang-version "1";

    namespace "http://openconfig.net/yang/annotation/oc-lldp-annot";
    prefix "oc-lldp-annot";

    import openconfig-extensions { prefix oc-ext; }
    import openconfig-lldp-types { prefix oc-lldp-types; }
    import openconfig-interfaces { prefix oc-if; }
    import ietf-yang-types { prefix yang; }
    import openconfig-lldp { prefix oc-lldp; }

    deviation /oc-lldp:lldp {
      deviate add {
      }
    }

    deviation /oc-lldp:lldp/oc-lldp:state {
      deviate add {
      }
    }

    deviation /oc-lldp:lldp/oc-lldp:state/oc-lldp:system-description {
      deviate add {
      }
    }
    .....
```

#### 2.5.2 Annotate YANG Paths

Transformer provides custom YANG statements to specify translation hints.
They are defined in `sonic-mgmt-common/models/yang/annotations/sonic-extensions.yang` file.
These custom YANG statements should be used to annotate specific paths in the annotation file.

Example:

```yang
import sonic-extensions { prefix sonic-ext; }

deviation /oc-lldp:lldp/oc-lldp:config {
    deviate add {
        sonic-ext:table-name "LLDP";
        sonic-ext:key-transformer "lldp_global_key_xfmr";
    }
}

deviation /oc-lldp:lldp/oc-lldp:config/oc-lldp:hello-timer {
    deviate add {
        sonic-ext:field-name "hello_time";
    }
}
```

Following annotation statements are supported.

##### 2.5.2.1 sonic-ext:table-name {TABLE_NAME}

Maps a YANG container or list to redis table name.

The table-name is **inherited** to all descendant nodes unless another one is defined.

##### 2.5.2.2 sonic-ext:field-name {FIELD_NAME}

Maps a YANG leaf or leaf-list node to redis hash field name.

##### 2.5.2.3 sonic-ext:key-delimiter {DELIM}

Override the default delimiter "|" with a custom delimiter.
This is used to derive the redis table key by concatenating the table name and key components.

##### 2.5.2.4 sonic-ext:key-name {VALUE}

Specify the fixed redis key value for singleton tables.
Useful when top level YANG container is mapped to a redis table.

Example: below annotation results is  redis key "UDLD|GLOBAL".

```
deviate add {
    sonic-ext:table-name "UDLD";
    sonic-ext:key-name "GLOBAL";
}
```

##### 2.5.2.5 sonic-ext:key-transformer {FUNCTION}

Overloads the default method to generate DB key(s).
Used when the key values in a YANG list are different from ones in DB table.

A pair of Go callbacks should be implemented to support 2 way translation - YangToDB_xxx, DbToYang_xxx.
Function signatures:

```go
/**
 * KeyXfmrYangToDb type is defined to use for conversion of Yang key to DB Key 
 * 
 * Param: XfmrParams structure having Database info, YgotRoot, operation, Xpath
 * Return: Database keys to access db entry, error
 **/
type KeyXfmrYangToDb func (inParams XfmrParams) (string, error)

/**
 * KeyXfmrDbToYang type is defined to use for conversion of DB key to Yang key
 * 
 * Param: XfmrParams structure having Database info, operation, Database keys to access db entry
 * Return: multi dimensional map to hold the yang key attributes of complete xpath, error
 **/
type KeyXfmrDbToYang func (inParams XfmrParams) (map[string]interface{}, error)
```

##### 2.5.2.6 sonic-ext:field-transformer {FUNCTION}

Overloads default method for generating DB field value.
Used when the leaf/leaf-list values defined in a YANG list are different from the field values in DB.

A pair of callbacks should be implemented to support 2 way translation - YangToDB_xxx, DbToYang_xxx.
Function signatures:

```go
/**
 * FieldXfmrYangToDb type is defined to use for conversion of yang Field to DB field
 * 
 * Param: Database info, YgotRoot, operation, Xpath
 * Return: multi dimensional map to hold the DB data, error
 **/
type FieldXfmrYangToDb func (inParams XfmrParams) (map[string]string, error)

/**
 * FieldXfmrDbtoYang type is defined to use for conversion of DB field to Yang field
 * 
 * Param: XfmrParams structure having Database info, operation, 
 *        DB data in multidimensional map, output param YgotRoot
 * Return: error
 **/
type FieldXfmrDbtoYang func (inParams XfmrParams)  (map[string]interface{}, error)
```

##### 2.5.2.7 sonic-ext:table-transformer {FUNCTION}

Map a YANG container/list to TABLE name(s).
Used to dynamically map a YANG list/container to table names based on URI and payload.

The table-transformer is **inherited** to all descendant nodes until another one is defined
or table-name “NONE” is defined.

Table transformer function signature:

```go
/**
 * TableXfmrFunc type is defined to use for table transformer function for
 * dynamic derviation of redis table.
 *
 * Param: XfmrParams structure having database pointers, current db, operation,
 *        DB data in multidimensional map, YgotRoot, uri
 * Return: List of table names, error
 **/
type TableXfmrFunc func (inParams XfmrParams) ([]string, error)
```

##### 2.5.2.8 sonic-ext:subtree-transformer {FUNCTION}

Overloading default translation method for the current subtree.
Allows the callback function to take **full control of translation**.
Note that, if any other extensions are annotated to the nodes on the subtree, they are not effective.

The subtree-transformer is **inherited** to all descendant nodes unless another one is defined.
i.e. the scope of subtree-transformer callback is limited to the current and descendant nodes
along the YANG path until a new subtree transformer is annotated.

A pair of callbacks should be implemented to support 2 way translation - YangToDB_xxx, DbToYang_xxx.
Function signatures:

```go
/**
 * SubTreeXfmrYangToDb type is defined to use for handling the yang subtree to DB
 * 
 * Param: XfmrParams structure having Database info, YgotRoot, operation, Xpath
 * Return: multi dimensional map to hold the DB data, error
 **/
type SubTreeXfmrYangToDb func (inParams XfmrParams) (map[string]map[string]db.Value, error)

/**
 * SubTreeXfmrDbToYang type is defined to use for handling the DB to Yang subtree
 * 
 * Param : XfmrParams structure having Database pointers, current db, operation,
 *         DB data in multidimensional map, output param YgotRoot, uri
 * Return :  error
 **/
type SubTreeXfmrDbToYang func (inParams XfmrParams) (error)
```

##### 2.5.2.9 sonic-ext:db-name {NAME}

Specify DB name to access data from.
Valid values are:
- CONFIG_DB (default value)
- APPL_DB
- ASIC_DB
- COUNTERS_DB
- FLEX_COUNTER_DB
- STATE_DB

Used for GET operation to non CONFIG_DB, applicable only to SONiC YANG
 
The db-name is **inherited** to all descendant nodes unless another one.
It must be defined with the **table-name** annotation.

##### 2.5.2.10 sonic-ext:post-transformer {FUNCTION}

A special hook to update the mapped DB data after all translation is done, but before writing to DB.
Analogous to the postponed YangToDB subtree callback that is invoked at the very end by the Transformer.

This will be useful to add or update additional data to to be written to DB.
Example: adding the default ACL rule during ACL creation.

Post-transformer can be annotated only to the top-level container(s) within each YANG module.

Port-transformer callback function signature:

```go
/**
 * PostXfmrFunc type is defined to use for handling any default handling operations
 * required as part of the CREATE.
 * 
 * Param: XfmrParams structure having database pointers, current db, operation,
 *        DB data in multidimensional map, YgotRoot, uri
 * Return: Multi dimensional map to hold the DB data Map (tblName, key and Fields), error
 **/
type PostXfmrFunc func (inParams XfmrParams) (map[string]map[string]db.Value, error)
```

##### 2.5.2.11 sonic-ext:get-validate {FUNCTION}

A special hook to validate YANG nodes, to populate data read from database.

Allows developers to instruct the Transformer to choose a YANG node among multiple nodes
while constructing the response payload.
Typically used to check the "when" condition.

Callback function signature:

```go
/**
 * ValidateCallpoint is used to validate a YANG node during data translation
 * back to YANG as a response to GET.
 * 
 * Param : XfmrParams structure having Database pointers, current db, operation,
 *         DB data in multidimensional map, output param YgotRoot, uri
 * Return :  bool
 **/
type ValidateCallpoint func (inParams XfmrParams) (bool)
```

##### 2.5.2.12 sonic-ext:rpc-callback {FUNCTION}

Handler function for YANG custom RPCs and actions.
Transformer does not process input or output payloads.

Function signature:

```go
/**
 * RpcCallpoint is used to invoke a callback for action
 * 
 * Param : []byte input payload, dbi indices
 * Return :  []byte output payload, error
 **/
type RpcCallpoint func (body []byte, dbs [db.MaxDB]*db.DB) ([]byte, error)
```

#### 2.5.3 Guidelines for Choosing Annotation Type

1) If the translation is simple mapping between YANG container/list and TABLE, consider using the extensions - table-name, field-name, optionally key-delimiter 

2) If the translation requires a complex translation with your codes, consider the following transformer extensions - key-transformer, field-transformer, subtree-transformer to take a control during translation. Note that multiple subtree-transformers can be annotated along YANG path to divide the scope

3) If multiple tables are mapped to a YANG list, e.g. openconfig-interface.yang, use the table-transformer to dynamically choose tables based on URI/payload 

4) In Get operation access to non CONFIG_DB, you can use the db-name extension

5) In Get operation, you can annotate the subtree-transformer on the node to implement your own data access and translation with DbToYang_xxx function

6) In case of mapping a container to TABLE/KEY you can use the key-name/key-transfomer along with the table-name/table-transformer extension 

#### 2.5.4 Manifest file

Manifest file `sonic-mgmt-common/config/transformer/models_list` contains all the YANG
file names that require transformer based translation.

Each line is treated as one file name; lines stating with `#` are ignored.
Add all the standard OpenConfig, IETF YANG names along with their extension YANGs and annotation file here.
SONiC YANG file names should not be added here.

Example:

```
openconfig-lldp.yang
openconfig-lldp-ext.yang
openconfig-lldp-annot.yang
openconfig-interfaces.yang
openconfig-if-ip.yang
openconfig-if-ethernet.yang
openconfig-if-ethernet-ext.yang
openconfig-if-ethernet-ext2.yang
openconfig-interfaces-annot.yang
```

#### 2.5.5 Callback functions

Transformer callback functions should be implemented in Go source files in
`sonic-mgmt-common/translib/transformer` directory.
It is suggested to have feature and sub-feature specific source files for easy browsing.

Go function for each of the callback names (defined of annotation file) should be registered
throigh `XlateFuncBind` API call during transformer module initialization.
This can be done in the `init()` function of every Go source file where the callback functions are implemented.

Example:

```go
func init () {
    XlateFuncBind("intf_table_xfmr", intf_table_xfmr)
    XlateFuncBind("YangToDb_intf_name_xfmr", YangToDb_intf_name_xfmr)
    XlateFuncBind("DbToYang_intf_name_xfmr", DbToYang_intf_name_xfmr)
}
```

Note that [key-transformer](#2525-sonic-extkey-transformer-function),
[field-transformer](#2526-sonic-extfield-transformer-function) and
[subtree-transformer](#2528-sonic-extsubtree-transformer-function)
requires a pair of callbacks - with `YangToDb_` and `DbToYang_` prefix added to
the function name specified in annotation file.

Only one callback is required for
[table-transformer](#2527-sonic-exttable-transformer-function),
[post-transformer](#25210-sonic-extpost-transformer-function), 
[get-validate](#25211-sonic-extget-validate-function) and
[rpc-callback](#25212-sonic-extrpc-callback-function).

All the callback functions, except rpc-callback, receive context information
through a `XfmrParams` object.
The rpc-callback callback function receives raw bytes sent by the client.

```go
// RedisDbMap is map[DB_NUM]map[TABLE]map[KEY]db.Value
type RedisDbMap = map[db.DBNum]map[string]map[string]db.Value

// XfmrParams contains context, data passed to the callback functions.
type XfmrParams struct {
    d *db.DB
    dbs [db.MaxDB]*db.DB
    curDb db.DBNum

    // requestUri holds the resource URI specified in client app.
    // It can be pointing to parent or child node of the node at which
    // this callback is registered. -- (RO)
    requestUri string

    // uri contains path to the node where a callback gets invoked.
    // Functions should use this value to identify target resource. -- (RO)
    uri string

    // ygRoot is the ygot struct initialized by translib for the requestUri. -- (RW)
    ygRoot *ygot.GoStruct

    // oper indicates the current operation requested by translib. -- (RO)
    // 1=GET, 2=CREATE, 3=REPLACE, 4=UPDATE, 5=DELETE
    oper int

    // key contains the DB key of current node. -- (RO)
    key string

    // dbDataMap is the internal map referenced by callback. -- (RO)
    dbDataMap *map[db.DBNum]map[string]map[string]db.Value

    // subOpDataMap is a map[OPCODE]map[DB_NUM]map[TABLE]map[KEY]db.Value -- (RW)
    // It should be filled by YangToDb_xxx callbacks to record sub-operations.
    subOpDataMap map[int]*RedisDbMap

    // param is the ygot GoStruct initialized for payload -- (RO)
    param interface{}

    // txCache is a cache to pass data/state between callbacks. -- (RW)
    // Scope of this limited to one translib transaction.
    txCache *sync.Map

    skipOrdTblChk *bool
}
```

These structures and callback function templates are defined in
`sonic-mgmt-common/translib/transformer/xfmr_interface.go` file.

#### 2.5.6 Usage Examples

TBD

### 2.6 App Module

Instead of using the transformer, developers can write the complete App module that aids in the conversion of the incoming request to the SONiC ABNF format and vice versa. Following are the steps to be performed.  

1. Define a structure to hold all the incoming information as well as the translation information

Example:

    type AclApp struct {
        pathInfo   *PathInfo
        ygotRoot   *ygot.GoStruct
        ygotTarget *interface{}

        aclTs  *db.TableSpec
        ruleTs *db.TableSpec
    
        aclTableMap  map[string]db.Value
        ruleTableMap map[string]map[string]db.Value
    }

2. App modules will implement an init function which registers itself with the translib. In addition it should also add the YANG models it supports here to serve the capabilities API of gNMI.
    Example:
    func init () {
        log.Info("Init called for ACL module")
        err := register("/openconfig-acl:acl",
                &appInfo{appType: reflect.TypeOf(AclApp{}),
                ygotRootType:  reflect.TypeOf(ocbinds.OpenconfigAcl_Acl{}),
                isNative:      false,
                tablesToWatch: []*db.TableSpec{&db.TableSpec{Name: ACL_TABLE}, &db.TableSpec{Name: RULE_TABLE}}})

        if err != nil {
            log.Fatal("Register ACL App module with App Interface failed with error=", err)
        }

        err = appinterface.AddModel(&gnmi.ModelData{Name:"openconfig-acl",
                                                    Organization:"OpenConfig working group",
                                                    Version:"1.0.2"})
        if err != nil {
            log.Fatal("Adding model data to appinterface failed with error=", err)
        }
    }

App Modules will implement the following interface functions that will enable conversion from YGOT struct to ABNF format.

    initialize(data appData)
    translateCreate(d *db.DB) ([]db.WatchKeys, error)
    translateUpdate(d *db.DB) ([]db.WatchKeys, error)
    translateReplace(d *db.DB) ([]db.WatchKeys, error)
    translateDelete(d *db.DB) ([]db.WatchKeys, error)
    translateGet(dbs [db.MaxDB]*db.DB) error
    translateSubscribe(dbs [db.MaxDB]*db.DB, path string) (*notificationOpts, *notificationInfo, error)
    processCreate(d *db.DB) (SetResponse, error)
    processUpdate(d *db.DB) (SetResponse, error)
    processReplace(d *db.DB) (SetResponse, error)
    processDelete(d *db.DB) (SetResponse, error)
    processGet(dbs [db.MaxDB]*db.DB) (GetResponse, error)

initialize – Populate the app structure that we created in step 1 with the incoming appData which contains path, payload, YGOT root structure, YGOT target structure.

translate(CRUD) – Convert the information in the YGOT root and target structure to the corresponding ABNF key value pair and store it in the structure created in step 1

translateGet – Convert the incoming path to corresponding ABNF keys to be got from the redis DB using the DB access layer APIs similar to the python SWSSSDK.

translateSubscribe – Convert the incoming path in the argument to corresponding ABNF keys as part of the notificationInfo structure. In addition to this subscribe parameters like type of subscription supported, SAMPLE interval can also be specified as part of the notificationOpts structure.

process(CRUD) – Write the converted data from translate(CRUD) function into the Redis DB using the DB access layer APIs


### 2.7 Config Validation Library

Config Validation Library (CVL) performs the automatic syntactic and semantic validation
of DB writes based on the YANG constraints defined in SONiC YANG.
These constraints include data type, ranges, patterns, "leafref", "must" and "when" statements.
Constraints written for read-only state nodes (non CONFIG_DB tables), RPC and notification nodes are ignored.
Complex validations that cannot be expressed via YANG constraints can be implemented via
custom validation functions written in Go.

All DB writes performed via Translib DB Acceess APIs would automatically trigger CVL validations.

#### 2.7.1 CVL Schema

CVL uses YIN schema derived from SONiC YANGs for validation.
CVL schema is automatically generated during sonic-mgmt-common build.
Any changes to SONiC YANG requires sonic-mgmt-common compilation for it to reflect in CVL.
Details of the schema generator are in [Appendix 3.1.3](#313-cvl-schema-generator).

#### 2.7.2 Custom Validation

When to use custom validation?
* Complext validations, which can't be defined using YANG must/when expression.
* YANG based must/when consraints are taking lot of time

Custom validation functions can be registered to a DB table or field definition in SONiC YANGs.
CVL provides a YANG extension statement **sonic-ext:custom-validation** for this.

```yang
import sonic-extension { prefix sonic-ext; }

....
list ACL_RULE_LIST {
  leaf IP_TYPE {
    sonic-ext:custom-validation ValidateAclRuleIPAddress;
    ...
  }
....
```

A Go function with same name should be defined in a Go source file under `sonic-mgmt-common/cvl/custom_validation` directory.
Use feature specific source file for better code organization - like "custom_validation_{feature}.go".
Function name should be unique across all SONiC YANGs.
So it is suggested to include table name and field name in the function name.

Signature for custom validation handler function:

```go
func (t *CustomValidation) <ValidationFunction>(vc *CustValidationCtxt) CVLErrorInfo 

// CustValidationCtxt is the validation context passed to custom validation function
type CustValidationCtxt struct {
	ReqData []CVLEditConfigData //All request data
	CurCfg *CVLEditConfigData //Current request data for which validation should be done
	YNodeName string //YANG node name
	YNodeVal string  //YANG node value, leaf-list will have "," separated value
	YCur *xmlquery.Node //YANG data tree
	SessCache *CustValidationCache //Session cache, can be used for storing data, persistent in session
	RClient *redis.Client //Redis client
}
```

#### 2.7.3 Platform Validation

CVL allows platform specific validation in following ways:

* Add YANG 'deviation' files (e.g. sonic-acl-deviation.yang for ACL YANG) per platform and place it in 'models/yang/sonic/platform' folder for static platform validation. These files are automatically picked up during build time, processed and applied at run time.

```
models/yang/sonic/platform/
├── accton_as5712
│   └── sonic-acl-deviation.yang
└── quanta_ix8
    └── sonic-acl-deviation.yang
```

Note : All platform specific deviation files are packaged in a single image file. At runtime, based on detected platform from provisioned  “DEVICE_METADATA:platform” field, deviation files are applied. 

* Implement platform specific custom validation through CVL custom validation support for dynamic platform validation.

#### 2.7.4 CVL Debug Logs

For enabling CVL debug log please refer to "Debugging Info" section in `sonic-mgmt-common/cvl/README.md`.


### 2.8 Non-DB Data

#### 2.8.1 Host Modules

TODO

#### 2.8.2 FRR Integration

TODO


### 2.9 KLISH CLI

Open source Klish is integrated to sonic-mgmt-framework to provide the command line interface tool to perform network operations more efficiently in SONiC. Klish will provide the core functionality of command parsing, syntax validation, command help and command auto-completion.

Open Source [klish](http://libcode.org/projects/klish/.) is used here.

#### 2.9.1 CLI components

1. CLI Parser engine: Open source Klish

2. XML files:
XML files, defined by developer, that describe the CLI command structure.
Klish uses XML based command tree inputs to build the parser command tree.
All CLI commands to be supported are specified in XML format in module specific XML file.
XML files can be defined with macros and entity references, preprocessed by scripts to generate the expanded XML files.

3. Actioner: Script that will transform CLI commands to form the corresponding REST requests and invoke the REST client API.

4. Renderer: Script that will receive the JSON response from REST client API and use the jinja2 template file to render(display) the CLI output in the desired format.

#### 2.9.2 CLI development steps

Following are the steps to add a new CLI command. Please refer to https://github.com/sipwise/klish/blob/master/doc/klish.md for detail.

1. Create a CLI XML .xml file that defines the CLI command structure. This file defines the following
    * CLI command format
    * Parameters that the command requires
    * Help string to be displayed for the command and parameters
    * Datatype of the parameters.
    * View name for which the command needs to be available. Eg: configure-view(config mode) or enable-view(exec mode)

Example:

```xml
    <VIEW name="enable-view">
    <!--show ip access-lists -->
    <COMMAND
            name="show ip access-lists"
            help="Show IPv4 access-list information"
            >
            <PARAM
            name="access-list-name"
            help="Name of access-list (Max size 140)"
            ptype="STRING"
            optional="true"
            >
        </PARAM>
        <ACTION>
        if test "${access-list-name}" = ""; then&#xA;
            python $SONIC_CLI_ROOT/sonic-cli.py get_acl_acl_sets show_access_list.j2&#xA;
        else&#xA;
            python $SONIC_CLI_ROOT/sonic-cli.py get_acl_set_acl_entries ${access-list-name} ACL_IPV4 show_access_list.j2&#xA;
        fi&#xA;
        </ACTION>
    </COMMAND>
```

2. Write/Update an actioner script: The actioner script prepares the message body having the JSON request and invokes the REST client API. The actioner script is invoked by the klish and the input parameters are passed to it from the XML file.
Actioner can be defined with the <ACTION> tag in the XML file. 

   There are three different methods available to implement the Actioner: sub-shell, clish_restcl and clish_pyobj. Sub-shell is spawned by Klish to run the script defined in <ACTION> tag. Both clish_pyobj and clish_restcl methods are part of Klish built-in fucntions and invoked by Klish. The built-in fucntions can be used for commands that would reduce time taken to execute a command by eliminating the sub-shell interpreter overhead.

  * Spawn a sub-shell to run the scripts defined in a command's <ACTION> tag. The shebang can be specified for the script execution. By default the "/bin/sh" is used. To customize shebang the 'shebang' field of the ACTION tag is used.

    The sub-shell runs the Python script sonic_cli_<module_name>.py

    sonic_cli_<module_name>.py <OpenAPI client method> [parameters . . .]
    The sonic_cli_<module_name>.py has a dispatch function to call a REST client method with parameters passed from user input.

    **Example**:
    Refer the <ACTION> tag in the above example command.
    The actioner scripts are placed in the following location:
    sonic-mgmt-framework/CLI/actioner/
    One actioner script will be written per module.
    Eg: sonic_cli_if.py can be used to handle the interface cases.

  * Invoke the built-in function, clish_restcl, to use libcurl to make REST client call
    This builtin uses libcurl to connect to the REST server Format of ACTION tag argument: 

    oper= url=</restconf/data/...> body={..} 
    where oper can be PUT/POST/PATCH/DELETE and body is optional. Note that oper GET is not supported as we currently don't handle rendering using jinja templates.

    **Example**:

    <ACTION builtin="clish_restcl">oper=PATCH url=/restconf/data/openconfig-interfaces:interfaces/interface=Vlan${vlan-id}/config body={"openconfig-interfaces:config": {"name": "Vlan${vlan-id}"}}</ACTION>

  * Invoke the built-in function, clish_pyobj, to use the embedding Python to make REST client call
    This builtin uses embedded python library.
    Format of ACTION tag argument is similar to the one of sub-shell. 
    For 'show' commands, the jinja2 template is passed to the Python script to apply template to redender CLI output.
    The ${__full_line} variable is also required to support Pipe, e.g sonic# show vlan | no-more. 
    Note that the "if-else" statement defined in the sub-shell can be moved to Python script.

    **Example**:
    <ACTION builtin="clish_pyobj">sonic_cli_vlan get_sonic_vlan_sonic_vlan Vlan${id} show_vlan.j2 ${__full_line}</ACTION>

    **Example**:

    Below example shows that the clish_pyobj can be used to set a dynamic variable "supported_breakout_modes" to check the breakout capability for a given port.
    Once the result is returned from the Python fucntion, the variable keeps the result and pass to <PARAM> like below.
```
    <VAR dynamic="true" name="supported_breakout_modes">        
       <ACTION builtin="clish_pyobj">sonic_cli_breakout.py capability</ACTION>
    </VAR>

    <PARAM 
     name="100g-1x"
     help="breakout to 1 100G interface"
     mode="subcommand" ptype="SUBCOMMAND"
     test='${supported_breakout_modes} -ct ETHERNET:BREAKOUT_1x1:100GIGE'
    />
```
3. Write/Update Renderer scripts and templates. 
The JSON response from the swagger client API is received by the actioner and passes the response to the renderer script. 
The renderer script will invoke the jinja2 template with the JSON response. The template will parse the JSON response and generate the CLI output.
Please use [JSON tool](#297-tool-for-json-navigation-in-jinja-templates) to efficiently access the JSON data.
Refer files in the below path for an example of usage 

    **Renderer path**:
    sonic-mgmt-framework/CLI/renderer
    **Renderer script**:
    scripts/render_cli.py
    **Renderer template**:
    templates/show_access_list.j2

    Every show command response can have a separate template file.

#### 2.9.3 Enhancements to Klish

Additional enhancements can be done to open source klish as below. Enhancements may include defining a new data types for CLI command parameters, define new macros that can be referenced for CLI commands structure that have repetitive definitions and defining platform specific entity values.

1. PTYPES
    New parameter types (PTYPES) can be defined and used in the CLI XML files.
    * PTYPE represents a parameter type, a syntactical template which parameters reference.
    * sonic-clish.xsd defines the tag and the attributes associated with the PTYPE tag.
    * Whenever a new attribute or tag introduced the xsd rules should also be updated.
    * sonic-clish.xsd is avilable at sonic-mgmt-framework/CLI/clitree/scripts/
    * The klish source supports certain primitive PTYPEs.
    * New user defined PTYPEs can be added to the SONIC project and can be defined in sonic_types.xml file.
    * sonic_types.xml is available in sonic-mgmt-framework/CLI/clitree/cli-xml/sonic_types.xml

    **Example**:  STRING_32

    ```xml
    <PTYPE
        name="STRING_32"
        pattern="(^([a-zA-Z0-9_-]){1,32})$"
        help="String"
    />
    ```

2. MACROS
    * Macros can be introduced by defining them in <module>_macro.xml 
    * Macros are used where repetitive command snippets (or command parameter snippets) with minor variations are needed in XML files. 
    * It is possible to create a macro definition in a <module>_macro.xml file and use the macro in the <module>.xml file.
    * For cases where variations in the values of these macro options are needed, the XML attributes can be passed as arguments to macro and substituted as values inside the macro definition. 
    * As part of parser tree preprocessing during Make, the referenced macro is expanded with the macro definitions and then the parser file is exported to the target XML files in CLI/target/command-tree to be consumed by Klish parser.
    * One macro file can be written per module.
    * The macro files are placed at sonic-mgmt-framework/CLI/clitree/macro/
    * Macros can also be nested with reference to another macro definition.

    **Example**:

    ```xml
    <MACRODEF name="IPV4-SRC-OPTIONS">
        <PARAM
            name="src-options-switch"
            help=""
            ptype="SUBCOMMAND"
            mode="switch"
            >
            <PARAM
                name="src-prefix"
                help="Source Prefix"
                ptype="IP_ADDR_MASK"
                >
            </PARAM>
        </PARAM>
    </MACRODEF>
    ```

    * The previous macro “IPV4-SRC-OPTIONS“ is used by the macro below "IPV4-ACL".

    ```xml
    <MACRODEF name="IPV4-ACL">
            <!-- permit tcp -->
            <PARAM
                name="tcp"
                help="TCP packets"
                ptype="SUBCOMMAND"
                mode="subcommand"
                >
                <MACRO name="IPV4-SRC-OPTIONS" arg="" ></MACRO>
                <MACRO name="TCP-PORT-OPTIONS" arg="source"> </MACRO>
                <MACRO name="IPV4-DEST-OPTIONS" arg="" ></MACRO>
                <MACRO name="TCP-PORT-OPTIONS" arg="destination" > </MACRO>
            </PARAM>
        <!-- permit udp -->
        <PARAM
                name="udp"
                help="UDP packets"
                ptype="SUBCOMMAND"
                mode="subcommand"
                >
                <MACRO name="IPV4-SRC-OPTIONS" arg="" ></MACRO>
            <MACRO name="TCP-PORT-OPTIONS" arg="source"> </MACRO>
            <MACRO name="IPV4-DEST-OPTIONS" arg="" ></MACRO>
            <MACRO name="TCP-PORT-OPTIONS" arg="destination" > </MACRO>
        </PARAM>
    </MACRODEF>
    ```

3. Entities

    * Entities can be defined and referenced in the XML files.
    * One common use case for entities is to specify platform specific parameters and parameter value limits in XML files.
    * To define an entity based parameter value range limit, three tasks must be done:

    1. Define the feature value as entity in mgmt_clish_feature_master.xsd
    **Example**:

    ```xsl
        <xs:simpleType name="featurename_t">
            <xs:annotation>
            <xs:documentation>This contains the allowed feature names for any platform specific customizable feature names.
				If you are adding a new platform customizable feature, add a record in the enumerated list here.
			</xs:documentation>
            </xs:annotation>
            <xs:restriction base="xs:string">
            <xs:enumeration value="FEATURE_A"/>
            </xs:restriction>
        </xs:simpleType>

        <xs:simpleType name="entityname_t">
        <xs:annotation>
                <xs:documentation>This contains the allowed feature-value names for any platform specific customizable feature-value
					strings. If you are adding a new platform customizable entity, add a record in the enumerated list here.
				</xs:documentation>
            </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="MAX_MTU"/>
        </xs:restriction>
        </xs:simpleType>
    ```

    2. Set the attribute 'value' to the right limit on respective platform configuration file that can be defined statically (used at build time).
    Refer to a dummy platform (platform_dummy.xml) configuration file.
    The platform_dummy.xml file can be located at sonic-mgmt-framework/CLI/clitree/scripts/.

    **Example**:

    <ENTITYNAME value="9276">MAX_MTU</ENTITYNAME>

    3. Use the ENTITY just like any other XML ENTITY in the CLI parser XML file.
  
4. Extended support with ext_help and regexp_select  
   The ext_help is similar to the pattern used in select method and used with regexp_select method. The value of the ext_pattern attribute is used for auto completion in regexp_select method.

   **Example**:
   Interfaces can be defined with regexp_select method and ext_pattern to support abbreviated interface naming, i.e eth20, e20, Ether20 etc. Here, we are left the help part as empty, and define the help string in the place where we use this PTYPE.
```
   <!ENTITY ETH_PHY_NUM     "([0-9]|[1-9]([0-9])*)">
   <!ENTITY ETH_ALL_INTF    "(^[eE]([t]|(th)|(thernet))?\s*((&amp;ETH_PHY_NUM;$)))">
   <PTYPE
      name="PHY_INTERFACE"
      method="regexp_select"
      ext_pattern="Ethernet(port)"
      pattern="&ETH_ALL_INTF;"
      help=""
   />
```

#### 2.9.4 Preprocess XML files

* The preprocessing scripts are invoked at compile time and no action is required to add a new CLI command.

* This section gives information about what is done during preprocessing stage.

    * The preprocessing scripts preprocess the raw CLI XML files and generate a target XML file that can be consumed by the klish open source parser.
    * The inputs to the preprocessing scripts are the raw CLI XML files, macro files and other utility files like platform specifics.
    * The cli-xml files are validated as part of compilation.
    * The 'xmllint' binary is used to validate all the processed XML files (i.e. after macro substitution and pipe processing) against the detailed schema kept at sonic-clish.xsd
    * The following preprocessing scripts are introduced:

        * **klish_ins_def_cmd.py**: This script is used to append the "exit" and "end" commands to the views of the Klish XML files
        * **klish_insert_pipe.py**: This script extends every show and get COMMAND with pipe option
        * **klish_platform_features_process.sh**: Validate all platform XML files. Generate the entity.xml files.
        * **klish_replace_macro.py**: This script does macro replacement on the XML files which are used by klish to define CLI structure.

#### 2.9.5 CLI directory structure

All CLI infrastructure, CLI definitions and their handlers are maintained
under `sonic-mgmt-framework/CLI` directory.

```
CLI
├── actioner      /* CLI actioner scripts */
├── clicfg        /* Entity substitution  */
├── clitree
│   ├── cli-xml   /* CLI model XMLs       */
│   ├── macro     /* Macro definitions    */
│   └── scripts   /* Preprocessor scripts */
├── klish         /* KLISH patches and launcher scripts */
│   └── patches
└── renderer
    ├── scripts   /* Renderer scripts         */
    └── templates /* Renderer jinja templates */
```

Below directories are used to collect XML files and utility scripts to generate the target XML files for CLI command tree build-out.  

**clitree/cli-xml**  - contains unprocessed/raw CLI XML files defined by developer

**clitree/macro**    - contains macro definitions used/referenced in CLI XML files defined by developer

**clitree/scripts**  - contains utility scripts to process raw CLI XML files defined by developer into processed CLI XMLs to be consumed by Klish Parser.

**clitree/Makefile** - rules to preprocess the raw CLI XMLs and validate the processed output against the DTD in sonic-clish.xsd

**clicfg**           - files for platform specific entity substitution.

**renderer**         - templates and scripts to  be used in rendering the show commands output.

After compilation the processed CLI XMLs can be found in sonic-mgmt-framework/build/cli/command-tree

#### 2.9.6 Generic REST Client for Actioner Scripts

Actioner scripts should use the generic REST client for makeing to communicate to REST Server.
Generic client code is avalable at `sonic-mgmt-framework/CLI/actioner/cli_client.py`.
This is tailor made to connect REST Server on local switch and handle the CLI actioner usecases.

Typical usage:

Create a CLI client object.
Client object can be created as a global variable in every actioner script.
Server sonnection and session are managed internally.

```python
import cli_client as cc

api = cc.ApiClient()
```

Create a path object. It accepts parameterized path template and parameter values.
Path template is similar to the template used by Swagger UI.
Parameter values will be URL-encoded and substituted in the path template.

```python
path = cc.Path('/restconf/data/openconfig-acl:acl/acl-sets/acl-set={name},{type}/acl-entries',
            name='MyNewAccessList', type='ACL_IPV4')
```

Invoke REST API.. `ApiClient` object supports get, post, put, patch and delete operations.
All these operations send a REST request and return a response object wrapping the REST response data.

```python
response = api.get(path, response_type=None)
```

An optional argument known as response_type is applicable only for GET and POST operations. 
It instructs the REST Client infrastructure to return the response from REST server in the form of 
JSON string instead of JSON (python dictionary).
If the API does not specify value for response_type, the default is JSON. 
The supported values for response_type are string and json.

**The use case for using response_type**

If the response from the rest server contains a non-hierarchical JSON string and if it's quite big enough, 
then the recommendation is to operate on the JSON string itself instead of converting it to python dictionary.
This will help the actioner consume less memory. It was observed that loading into dictionary takes considerably
large memory.

Check API status through `response.ok()` function, which returns true if API was success (HTTP 2xx status).
`ok()` function returns false if server returned an error.
Use `response.error_message()` function to get the displayable error message.

```python
if response.ok() {
    respJson = response.content
    # invoke renderer to display respJson
} else {
    print response.error_message()
    return -1
}
```

Examples of other REST API calls.

```python
# construct your request data json
jsonDict = {}
jsonDict["acl-set"]=[{ "name":the_acl_name, .... }]

# POST request with default response_type i.e. JSON
response = api.post(path, data=jsonDict)

# POST request with string as response_type
response = api.post(path, data=jsonDict, response_type='string')

# PUT reuest
reponse = api.put(path, data=jsonDict)

# PATCH request
response = api.patch(path, data=jsonDict)

# GET request with default response_type i.e. JSON
response = api.get(path)

# GET request with string as response_type
response = api.get(path, response_type='string')

# DELETE request
response = api.delete(path)
```

Above example used `response.error_message()` function to get ser displayable error message from the REST response.
REST server always returns error information in standard RESTCONF error format.
The `error_message()` function looks for the **error-message** attribute to get user displayable message.
If there was no **error-message** attribute, a generic message will be returned based on **error-tag** value.
Actioners can override this logic through customiz error message formatter function.
The custom formtter function receives HTTP state code and RESTCONF error json; and should return a string.
However default error formatter is sufficient for most of the cases.

```python
if not response.ok():
     print response.error_message(formatter_func=my_new_error_message_formatter)

# .....

def my_new_error_message_formatter(status_code, error_entry):
    if err_entry['error-type'] == 'protocol':
        return "System error.. Please reboot!!"
    return "Application error.. Please retry."
```

#### 2.9.7 Tool for JSON navigation in jinja templates

Developers can use this tool to retrieve the JSON data efficiently and check for the existence of nodes. 
The tool uses the path in the GNMI style for querying and checking the nodes. 
Following are the APIs exposed by the tool

#### get(json_data, path)
    params
        json_data: JSON data in the form of dictionary
        path: The GNMI style path, examples below
    return value
        On success returns the queried nodes (format/type will be as present in JSON data)
        on Failure returns None

##### Example:

```code
(Pdb) get(data, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/")
{'name': 'MyACL1', 'type': 'ACL_IPV4', 'description': 'Description for MyACL1'}

```

#### get_str(json_data, path)
    params
        json_data: JSON data in the form of dictionary
        path: The GNMI style path, examples below
    return value
        On success returns the queried nodes (format/type will be strigified)
        on Failure returns None

##### Example:

```code
(Pdb) get_str(data, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/")
"{'name': 'MyACL1', 'type': 'ACL_IPV4', 'description': 'Description for MyACL1'}"

```

#### contains(json_data, path)
    params
        json_data: JSON data in the form of dictionary
        path: The GNMI style path, examples below
    return value
        On success returns True
        on Failure returns False
        
##### Example:

```code
(Pdb) contains(data, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/")
True
(Pdb) contains(data, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/not_present")
False

```

#### Sample usage in the renderer

```text
{{json_tools.get(json_output, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]")}}
{{json_tools.get(json_output, "/acl-sets/acl-set[name=MyACL1]")}}
{{json_tools.get(json_output, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/type")}}
{{json_tools.get_str(json_output, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/type")}}
{{json_tools.contains(json_output, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/type_not")}}
{{json_tools.contains(json_output, "/acl-sets/acl-set[name=MyACL1][type=ACL_IPV4]/config/type")}}

```


### 2.10 REST Server

sonic-mgmt-framework repository contains REST Server infrastructure code.
It provides [RESTCONF](https://tools.ietf.org/html/rfc8040) APIs for the YANGs defined in sonic-mgmt-common.
These APIs are serviced by Translib; see [HLD](https://github.com/Azure/SONiC/blob/master/doc/mgmt/Management%20Framework.md#3224-REST-server) for details.

YANGs are automatically plugged into REST Server infrastructure during sonic-mgmt-framework compilation.
Details are in [section 3.1.5](#315-swagger-server-generator).

### 2.11 gNMI

gNMI interfaces are automatically supported for all YANGs definied under `sonic-mgmt-common/models/yang` directiry.
This includes OpenConfig & IETF YANGs with their extensions and SONiC YANGs.

gNMI and telemetry infrastructure code is maintained in **sonic-telemetry** repository.

### 2.12 Compilation

#### 2.12.1 sonic-mgmt-common

sonic-mgmt-common repository compiles into **sonic-mgmt-common_1.0.0_{arch}.deb** and
**sonic-mgmt-common-codegen_1.0.0_{arch}.deb** packages.

The sonic-mgmt-common_1.0.0_{arch}.deb contains YANGs, YANG derivatives and configuration files
required by Translib, transformer and CVL. 
These are installed in **mgmt-framework** and **telemetry** containers.

sonic-mgmt-common-codegen_1.0.0_{arch}.deb contains YGOT bindings and other generated source files
which are required for sonic-mgmt-framework and sonic-telemetry compilation.
When package cache mode is enabled, the build infrastructure will not compile sonic-mgmt-common
files if there are no changes in it since last compilation.
Generated source files are restored by installing sonic-mgmt-common-codegen_1.0.0_{arch}.deb in
the build container.

#### 2.12.2 sonic-mgmt-framework

Code from sonic-mgmt-framework repository compiles into **sonic-mgmt-framework_1.0-01_{arch}.deb**
and a docker image **docker-sonic-mgmt-framework.gz**.
REST Server and CLI code are packaged in sonic-mgmt-framework_1.0-01_xyz.deb.
This and sonic-mgmt-common_1.0.0_{arch}.deb are included in the docker image.

To rebuld the docker image both these debs should be cleaned.

```bash
# Only if you have changed something in sonic-mgmt-common
find target -name "sonic-mgmt-common*" -delete -print

# Always do it - for both mgmt-common and mgmt-framework changes
find target -name "*sonic-mgmt-framework*" -delete -print

make target/docker-sonic-mgmt-framework.gz
```

To load new docker image on the switch:

```bash
admin@sonic:~$ sudo sonic_installer upgrade_docker mgmt-framework docker-sonic-mgmt-framework.gz
```

#### 2.12.2 sonic-telemetry

TODO

### 2.13 Unit Testing

#### 2.13.1 REST API testing

REST server provides a test UI (Swagger UI) will display the operations defined in OpenAPI spec along with options to test it inline. To launch the Swagger UI, open “https://SWITCH_IP/ui” from the browser. Browser may complain that the certificate is not trusted. This is expected since the REST Server uses a temporary self signed certificate by default. Ignore the warning and proceed, this loads a home page as shown below, which contains links for OpenAPIs both derived from yang models and also manually written OpenAPI specs.

![Swagger UI Home Page](images/homepage.jpeg)
Upon clicking of any one of the link, The Swagger UI correspoding to that openAPI spec will be opened as shown below.

![OpenAPI Page](images/openapis.jpeg)

Expand any section to view description, parameters and schema/sample data..

Use “Try it out” button test the API from the Swagger UI itself. It opens a form to enter URI parameters and body data. Enter values and hit “Execute” button. REST API will be invoked and results are shown.

#### 2.13.2 Local REST Server and CLI

TODO

#### 2.13.3 gNMI Unit Testing

gNMI unit testing can be performed using open-source gNMI tools. 'telemetry' docker already contains such tools e.g. gnmi_get, gnmi_set, gnmi_cli etc. You can directly invoke these tools from linux shell of a switch as below :

```
docker exec -it telemetry gnmi_get -xpath /openconfig-interfaces:interfaces/interface[name=Ethernet0] -target_addr 127.0.0.1:8080 -insecure

```

* Use 'gnmi_get' tool to perform a get request against the gNMI target in switch. For sample get request and response, refer to https://github.com/project-arlo/sonic-telemetry/blob/master/test/acl_get.test and https://github.com/project-arlo/sonic-telemetry/blob/master/test/acl_get.result respectively.
* Use 'gnmi_set' tool to perform a set request against the gNMI target in switch. For sample set request and response, refer to https://github.com/project-arlo/sonic-telemetry/blob/master/test/acl_set.test and https://github.com/project-arlo/sonic-telemetry/blob/master/test/acl_set.result respectively.
* Use 'gnmi_cli' to get the capabilities of gNMI target. For example :

```	
docker exec -it telemetry gnmi_cli -capabilities -insecure -logtostderr -address 127.0.0.1:8080
```		 
* Use 'gnmi_cli' to perform subscription request. For sample subscribe request and response, refer to https://github.com/project-arlo/sonic-telemetry/blob/master/test/ethernet_oper_status_subscribe.test and https://github.com/project-arlo/sonic-telemetry/blob/master/test/ethernet_oper_status_subscribe.result respectively. 

#### 2.13.3 Spytest

TODO


## 3 Appendix

### 3.1 Code Generators

#### 3.1.1 YANG Tree Generator

YANG tree generators are run during compilation of `sonic-mgmt-common/models/yang` directory.

Following trees are generated:
1) Standard [Text tree](#2361-yang-text-tree) using `pyang -f tree` option.
2) Standard [HTML tree](#2362-yang-html-tree) using `pyang -f jstree` option.
3) Custom [Markdown tree](#2363-yang-markdown-tree) which highlights nodes added/removed by extension YANGs.
Uses a custom pyang plugin `sonic-mgmt-common/tools/pyang/pyang_plugins/doctree.py`.

All tree generators are automatically run during sonic-mgmt-common compilation.
It can be manually trigged through following commands:

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-common/models/yang
make                    # generates all trees
make allyangs.tree      # generates only text tree
make allyangs_tree.html # generates only html tree
make yang_tree.md       # generates only md tree
```

Requires:
- Pyang 2.1.1
- Python 2.7.14 or later (or Python 3)

#### 3.1.2 YGOT Binding Generator

This tool generates YGOT binding code for YANG files under `sonic-mgmt-common/models/yang` directory.
YGOT bindings are written to `sonic-mgmt-common/translib/ocbinds/ocbinds.go` file.

It is run automatically during compilation of sonic-mgmt-common repository.
It can be manually triggered to test YANG changes through following steps.

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-common
make go-deps
cd -C translib ocbinds/ocbinds.go
```

Requires:
- Go 1.13.8 or later
- customized ygot (patched during sonic-mgmt-common compilation)

#### 3.1.3 CVL Schema Generator

This tool generates CVL YIN schema from the SONiC YANGs.
It removes all read-only state nodes, RPC and notification nodes using a
pyang plugin `sonic-mgmt-common/tools/pyang/pyang_plugins/yin_cvl.py`.

Schema files will be generated under `sonic-mgmt-common/build/cvl/schema` directory.

CVL Schema generator is automatically run during sonic-mgmt-common compilation.
It can be manually trigged through following commands:

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-common/cvl
make schema
```

Requires:
- Pyang 2.1.1
- Python 2.7.14 or later (or Python 3)

#### 3.1.4 OpenAPI Generator

This tool generates OpenAPI specs (aka swagger spec) from YANGs.
It is implemented as a pyang plugin `sonic-mgmt-framework/tools/pyang/pyang_plugins/openapi.py`.

YANG file to YAML file mapping is not one to one; i.e, there will not be a `.yaml` for every `.yang` file.
OpenAPI generator first constructs a normalized YANG tree using all the YANG files defined under
`sonic-mgmt-common/models/yang`, `sonic-mgmt-common/models/yang/extensions` 
and `sonic-mgmt-common/models/yang/sonic` directories.
YANGs from `sonic-mgmt-common/models/yang/common` are used to resolve compilation dependencies only.
YAML files will be generated for each top level YANG module in normalized tree.

Eg, below 3 YANG files will result in only one OpenAPI spec - main.yaml.

```text
+---------------------------+-------------------------------+-------------------------------+
|  yang/main.yang           |  yang/common/sub1.yang        |  yang/extensions/sub2.yang    |
+---------------------------+-------------------------------+-------------------------------+
|  module main {            |  module sub1 {                |  module sub2 {                |
|    container feature1 {   |    grouping newstuffs {...}   |    grouping morestuffs {...}  |
|    }                      |    augment /main:feature1 {   |    augment /main:feature1 {   |
|  }                        |      uses newstuffs;          |      uses morestuffs;         |
|                           |    }                          |    }                          |
|                           |  }                            |  }                            |
+---------------------------+-------------------------------+-------------------------------+
```

Generated OpenAPI specs will be written to `sonic-mgmt-framework/build/yaml` directory.

Note that transformer annotations YANGs are not considered - they are not data models.

OpenAPI Generator is automatically run during sonic-mgmt-framework compilation.
It can be manually trigged through following commands:

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-framework/models
make -f yang_to_openapi.mk
```

Requires:
- Pyang 2.1.1
- mmh3 2.5.1 (python library)
- Python 2.7.14 or later (or Python 3)

#### 3.1.5 Swagger Server Generator

This tool generates Swagger Go server handler code from the OpenAPIs specs.
It consumes YANG generated OpenAPI specs from `sonic-mgmt-framework/build/yaml` directory
and manually written OpenAPI specs from `sonic-mgmt-framework/models/openapi` directory, if any.

Generated Go source files will be available in `sonic-mgmt-framework/build/rest_server/dist/openapi` directory.
No manual edits are required in the generated server handler functions.
Customized mustache templates are used to generate the server handlers with REST Server specific logic.
Mustache templates are in `sonic-mgmt-framework/tools/swagger_codegen/go-server` directory.

Swagger server generator is automatically run during sonic-mgmt-framework compilation.
It can be manually trigged through following commands (assumes OpenAPI generator is already run):

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-framework/models
make -f openapi_codegen.mk go-server
```

Requires:
- Java 1.8
- Python 3
- jinja2 2.10.3

#### 3.1.6 Swagger Client SDK Generator

This tool generates swagger client SDK code in python from the OpenAPI specs.
Python client SDK was originally intended to be used by KLISH CLI actioners,
but now CLI actioners are using a generic REST client.
Hence this code generator is disabled by default.
It can be enabled for specific OpenAPIs specs by listing them in `sonic-mgmt-framework/models/codegen.config` file.

```makefile
# Generated OpenAPI specs from sonic-mgmt-framework/build/yaml directory
PY_YANGAPI_CLIENTS += openconfig-interfaces
PY_YANGAPI_CLIENTS += openconfig-platform
PY_YANGAPI_CLIENTS += openconfig-system

# OpenAPI specs from sonic-mgmt-framework/models/openapi directory
PY_OPENAPI_CLIENTS += my-new-apis
```

Generated client SDK code will be available in `sonic-mgmt-framework/build/openapi_client_py` directory.

Note: Swagger generates lot of client SDK code but only fraction of it will be exercised by KISH CLI.
Framework provides a generic REST client for CLI use which is more lighter and faster than swagger client SDK.
**Recommendation for CLIs is to use this generic REST client and not Swagger Client SDK**.

Swagger client SDK generator is automatically run during sonic-mgmt-framework compilation
if some OpenAPI specs are whitelisted in `sonic-mgmt-framework/models/codegen.config`.
It can be manually run through following commands (assumes OpenAPI generator is already run):

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-framework/models
make -f openapi_codegen.mk py-client  # generates for all whitelited specs

# To force generation for a specific spec
PY_YANGAPI_CLIENTS=openconfig-interfaces make -f openapi_codegen.mk py-client 
```

Requires:
- Java 1.8

#### 3.1.7 Swagger UI Generator

This tool generates Sweagger UI for the REST Server as expaned in [section 2.13.1](#2131-rest-api-testing).
It is automatically run along with [Swagger Server Generator](#315-swagger-server-generator).

#### 3.1.8 RESTCONF Documentation Generator

RESTCONF documentation is generated automatically as part of build during the phase when OpenAPIs(YAML) for YANG modules are generated.
No extra step is needed from developers. RESTCONF document generator is a submodule in OpenAPI Generator and it relies on YANG's description
statements for documentation text. 

Developers are requested to have a description statements in YANG models for all Data nodes such as container/list/leaf/leaf-list/rpc.
For any data node which does not have description statement, the generated document will have blank text i.e. empty sections

The generated document will be in a github complaint markdown format (.md)
The document will be generated for each top level YANG module in normalized tree. For more information on how generator works please refer [section 3.1.4](#314-OpenAPI-Generator)

The generated documents will be written to `sonic-mgmt-framework/build/restconf_md` directory.

#### 3.1.9 CLI Documentation Generator

CLI Document generator tool will generate the documentation using KLISH CLI model XMLs. 
Command name, mode, syntax and parameter description are already available in model XML. 
Additional tags will be introduced for developers to specify command description, usage info and examples for each COMMAND.

- DOCGEN tag to group all document generation related tags - it can include one DESCRIPTION, one USAGE and one or more EXAMPLE, ALTCMD and FEATURE tags.
- DESCRIPTION tag to provide a detailed description of the command.
- USAGE tag to specify usage guidelines - when to use, preconditions, suggested next actions, etc.
- EXAMPLE tags to specify examples and sample output.
- ALTCMD tags to specify alternative commands in other CLI framework such as VTYSH, CLICK and in fact other alternate commands in KLISH itself (if available).

All these documentation tags will be optional. They are used only for document generation and not to render the commands.

Document generator tool will consume all model XMLs from src/CLI/clitree/cli-xml directory to generate CLI document in markdown syntax. 
Below table summarizes how each section of document template will be derived from above defined XML tags.

```text
+----------------+-----------------+-------------------+---------------------------------------------------------------------------+
|  Section.      |    XML TAG      |  Attribute        |  Comments                                                                 |
+----------------+-----------------+-------------------+---------------------------------------------------------------------------+
| Command name   |  COMMAND        |                   |                                                                           |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------+
| Description    |  DESCRIPTION    |                   | Use “help” value of COMMAND tag if DESCRIPTION tag is not specified.      |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Syntax         |  PARAM          | name              | Lists all possible combinations of parameters                             |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Parameters     |  PARAM          | name, help, ptype |                                                                           |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Modes          |  VIEW           | name              | Parent command name will be shown here. The VIEW “name” attribute provides| 
|                |                 |                   | internal name of the mode. Tool will lookup the parent command by matching| 
|                |                 |                   | the VIEW “name” value with other COMMAND tag’s “view” attribute value     |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Usage          |                 |                   |                                                                           |
| guidelines     |  USAGE          |                   | Will be skipped if developer did not specify USAGE tag                    |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Examples       |  EXAMPLE        |                   | Will be skipped if developer did not specify EXAMPLE tags                 |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| Features       |  FEATURE        |                   | Will be skipped if developer did not specify FEATURE tags                 |
|----------------|-----------------|-------------------|---------------------------------------------------------------------------|
| ALTCMDS        |  ALTCMD         | type              | Will be skipped if developer did not specify ALTCMD tags                  |
+----------------+-----------------|-------------------|---------------------------------------------------------------------------|

```
CLI document generator is automatically run during sonic-mgmt-framework compilation.
It can be manually trigged through following commands:

```bash
cd /sonic/sonic-buildimage/src/sonic-mgmt-framework
make clidocgen (to generate the document)
make clidocgen-clean (to clean the document)
```
The document will be written to `sonic-mgmt-framework/build/cli/command-tree/industry_standard_cli_reference_guide.md` directory.

#### 3.1.9.1 Sample CLI Model

```text

<VIEW name="view-name">

<COMMAND
   name="command-tokens"
   help="CLI help string"
   >
   <PARAM
       name="param1"
       help="Help string for param1"
       ptype="UINT"
       />
   <PARAM
       name="param2"
       help="Help string for param2"
       ptype="STRING"
       />
   <ACTION>...</ACTION>
   <DOCGEN>
       <DESCRIPTION>
           Detailed command description
       </DESCRIPTION>
       <USAGE>
           Usage information
       </USAGE>
       <EXAMPLE summary="Example1 description">
           Example1 body
       </EXAMPLE>
       <EXAMPLE summary="Example2 description">
           Example2 body
       </EXAMPLE>

       <FEATURE> ZTP </FEATURE>
       <FEATURE> ZTP-cli </FEATURE>                         
       <ALTCMD type="click">
         config ztp -y enable
        </ALTCMD>
        <ALTCMD type="vtysh">
          ....
        </ALTCMD> 

   </DOCGEN>
</COMMAND>

</VIEW>

```

#### 3.1.9.2 Sample Generated Document

```text
### command-tokens

Detailed command description

#### Syntax

command-tokens param1
command-tokens param2

#### Parameters

Name   | Description            | Data type
-------|------------------------|--------
Param1 | Help string for param1 | UINT
Param2 | Help string for param2 | STRING

#### Mode

Parent command - derived from view-name

#### Usage Guidelines

Usage information

#### Examples

Example1 description

Example1 body

Example2 description

Example2 body

### Alternate Commands

#### click
config ztp -y enable

#### vtysh
...

### Features this CLI belongs to
* ZTP
* ZTP-cli

```
