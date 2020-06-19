# SONiC Management Framework Developer Guide

## Rev 0.6

## Table of Contents

* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definition/Abbreviation](#definitionabbreviation)
* [Table 1: Abbreviations](#table-1-abbreviations)
* [1 Architecture](#1-Architecture)
    * [1.1 Requirements](#11-requirements)
    * [1.2 Design Overview](#12-design-overview)
        * [1.2.1 Basic Approach](#121-basic-approach)
        * [1.2.2 Container](#122-container)
* [2 Developer Workflow](#2-developer-workflow)
    * [2.1 ABNF Schema](#21-abnf-schema)
    * [2.2 YANG Identification](#22-yang-identification)
        * [2.2.1 Standard YANG](#221-standard-yang)
        * [2.2.2 SONiC YANG](#222-sonic-yang)
    * [2.3 Code Generation](#23-code-generation)
    * [2.4 Config Translation App](#24-config-translation-app)
        * [2.4.1 Transformer](#241-transformer)
            * [2.4.1.1 Annotation File](#2411-annotation-file)
            * [2.4.1.2 Annotate YANG extensions](#2412-annotate-YANG-extensions)
            * [2.4.1.3 Manifest file](#2413-manifest-file)
            * [2.4.1.4 Special handling](#2414-special-handling)
        * [2.4.2 App Module](#242-app-module)
    * [2.5 Config Validation Library](#25-config-validation-library)
    * [2.6 Industry Standard CLI](#26-Industry-Standard-cli)
        * [2.6.1 CLI components](#261-cli-components)
        * [2.6.2 CLI development steps](#262-cli-development-steps)
        * [2.6.3 Enhancements to Klish](#263-enhancements-to-klish)
        * [2.6.4 Preprocess XML files](#264-preprocess-xml-files)
        * [2.6.5 CLI directory structure](#265-cli-directory-structure)
    * [2.7 gNMI](#27-gnmi)
    * [2.8 Unit Testing](#28-unit-testing)

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

1) Knowledge of YANG syntax

2) GO Programming language

3) SONiC Management Framework Architecture

## 1 Architecture

![Management Framework Architecture diagram](https://github.com/project-arlo/SONiC/blob/master/doc/mgmt/images/Mgmt_Frmk_Arch.jpg)

In the above architecture diagram developer needs to write all the elements in green. Following are blocks that the developer has to write in order to get CLI, REST and gNMI support for the new feature being developed.

1) YANG Models

2) ABNF schema and SONiC YANG

3) Transformer - includes YANG annotations and custom translation

4) KLISH XML including Actioner and Renderer scripts

## 2 Developer Workflow

Following are the steps to be followed by the application developer.

### 2.1 ABNF Schema

For the existing feature ABNF schema must be used as a reference to develop the SONiC YANG.

Define the ABNF schema for the new feature. It is suggested to keep it in line with YANG model selected below. It is also suggested to keep the field names in the ABNF schema same as that of the leafs and leaf lists in the YANG model to help in easy translation. Ideally defining ABNF schema and configuration objects in SONiC YANG can go hand in hand to keep one definition in line with other.

### 2.2 YANG Identification

Identify the standard/SONiC YANG model to be used for northbound APIs.

#### 2.2.1 Standard YANG

OpenConfig model is preferred. IETF YANG model can be used if there is no OpenConfig model for the feature.

Feature implementation may have to support additional configuration/state knobs than the standard YANGs. In such cases, the developer will have to write a custom extension YANG. Extension YANGs will add custom configuration/state knobs on top of standard YANG tree using YANG deviation.

Below is a hypothetical example of extending openconfig ACL configuration by disabling description, limiting number of characters of ACL name and adding a new alt-name config.

    module openconfig-acl-deviations {
        namespace "http://github.com/Azure/sonic-oc-acl-deviations";
        prefix oc-acl-deviations;
        import openconfig-acl { prefix oc-acl; }

        /* Mark ACL description not supported */
        deviation /oc-acl:acl/acl-sets/acl-set/config/description {
            deviate not-supported;
        }
        
        /* Restrict ACL name to max 127 characters */
        deviation /oc-acl:acl/acl-sets/acl-set/config/name {
            deviate replace {
                type string {
                    length "1..127";
                }
            }
        }
        
        /* Add an alt-name config to ACL */
        augment /oc-acl:acl/acl-sets/acl-set/config {
            leaf alt-name {
                type string;
            }
        }
    }

Note: You should avoid deviations/extensions to standard YANG models as much as possible. Add them only if necessary for your feature. NSM apps that depend of standard modules may not be able to discover the SONiC switches if standard YANG models are modified too much.

#### 2.2.2 SONiC YANG

SONiC YANGs are custom YANGs developed for data (i.e. ABNF JSON) modeling in SONiC. SONiC YANGs captures the Redis DB schema associated with a given feature. This YANG helps SONiC validate syntax and semantics of a feature configuration. SONiC YANGs are mandatory for Management Framework to work and it needs to capture all supported configuration pertaining to a feature. SONiC YANG shall capture operational state data syntax, RPC, notification when used as Northbound Management Interface YANG.

Please refer to [SONiC YANG Model Guidelines](https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md) for detailed guidelines on writing SONiC YANG. Please refer to existing YANG models (in "models/yang/sonic/" folder in 'sonic-mgmt-framework' repository) already written for features like ACL etc. You can also refer to few test YANGs available in "src/cvl/testdata/schema" folder. Once you have written a SONiC YANG following the guideline, place it in "models/yang/sonic/" folder.

### 2.3 Code Generation

Generate the REST server stubs and REST Client SDKs for YANG based APIs by placing the main YANG modules under sonic-mgmt-framework/models/yang directory and compiling. By placing YANG module in this directory and compiling, YAML (swagger spec) is generated for the YANG. Also the YGOT GO structures for the YANG are also automatically generated during the build time. If there is YANG which is augmenting or adding deviations for the main YANG module, this augmenting/deviation YANG should also be placed in sonic-mgmt-framework/models/yang directory itself.

Place all dependent YANG modules such as submodules or YANGs which will define typedefs etc under sonic-mgmt-framework/models/yang/common directory. By placing YANG module in this directory, YAML (swagger spec)  is not generated for the YANG modules, but the YANGs placed under sonic-mgmt-framework/models/yang can utilize or refer to types, and other YANG constraints from the YANG modules present in this directory.
Example: ietf-inet-types.yang which mainly has typedefs used by other YANG models and generally we won't prefer having a YAML for this YANG, this type of YANG files can be placed under sonic-mgmt-framework/models/yang/common.

Generation of Rest-server stubs and client SDKs will automatically happen when make command is executed as part of the build.

### 2.4 Config Translation App

Developer writes the Config translation App. Config translation App translates the data in [Northbound API schema](#21-YANG-identification) to the native [ABNF schema](#22-abnf-schema) and vice versa. All Northbound API services like REST, GNMI, NETCONF will invoke this app to read and write data.

Config Translation can be done using

1. Transformer (Preferred) or
2. App module (Not preferred)

#### 2.4.1 Transformer

Transformer provides a generic infrastructure for Translib to programmatically translate YANG to ABNF/Redis schema and vice versa, using YANG extensions to define translation hints along the YANG paths. At run time, the translation hints are mapped to an in-memory Transformer Spec that provides two-way mapping between YANG and ABNF/Redis schema for Transformer to perform data translation.

In case that SONiC YANG modules are used by NBI applications, the Transformer performs 1:1 mapping between a YANG object and a SONiC DB object without a need to write special translation codes or any translation hints.

If you use the openconfig YANGs for NBI applications, you need special handling to translate the data between YANG and ABNF schema. In such case, you have to annotate YANG extensions and write callbacks to perform translations where required.

In either case, the default application [common-app.go](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/translib/common_app.go) generically handles both set and get requests with the returned data from Transformer.

##### 2.4.1.1 Annotation File

The goYANG package is extended to generate the template annotation file for any input YANG file. A new output format type "annotate" can be used to generate the template annotation file.

The goYANG usage is as below:

Usage: goYANG [-?] [--format FORMAT] [--ignore-circdep] [--path DIR[,DIR...]] [--trace TRACEFILE] [FORMAT OPTIONS] [SOURCE] [...]
 -?, --help  display help
     --format=FORMAT
             format to display: annotate, tree, types
     --ignore-circdep
             ignore circular dependencies between submodules
     --path=DIR[,DIR...]
             comma separated list of directories to add to search path
     --trace=TRACEFILE
             write trace into to TRACEFILE

Formats:
    annotate - generate template file for YANG annotations

    tree - display in a tree format
 
    types - display found types
        --types_debug  display debug information
        --types_verbose
                       include base information

Add $(SONIC_MGMT_FRAMEWORK)/gopkgs/bin to the PATH to run the goYANG binary.

e.g.

goYANG --format=annotate --path=/path/to/yang/models openconfig-acl.yang  > openconfig-acl-annot.yang

[Annotation file example](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/models/yang/annotations/openconfig-acl-annot.yang)

Sample output:

    module openconfig-acl-annot {

        YANG-version "1"
    
        namespace "http://openconfig.net/yang/annotation";
        prefix "oc-acl-annot"
    
        import openconfig-packet-match { prefix oc-pkt-match }
        import openconfig-interfaces { prefix oc-if }
        import openconfig-yang-types { prefix oc-yang }
        import openconfig-extensions { prefix oc-ext }
    
        deviation oc-acl:openconfig-acl {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:state {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:state/oc-acl:counter-capability {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:acl-sets {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set {
        deviate add {
        }
        }
    
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set/oc-acl:type {
        deviate add {
        }
        }
    ...
    ...
        deviation oc-acl:openconfig-acl/oc-acl:acl/oc-acl:config {
        deviate add {
        }
        }
    }

##### 2.4.1.2 Annotate YANG extensions

The translation hints can be defined as YANG extensions to support simple table/field name mapping or more complex data translation by overloading the default methods.

[Extensions](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/models/yang/common/sonic-extensions.yang)

|                       Extensions                      |                         Usage             |                   Note
|-------------------------------------------------------|-------------------------------------------|---------------------------------------------------------------------------------------|
| sonic-ext:table-name [string]                         | Map a YANG list to TABLE name             | Processed by the default transformer method.                                          |
|                                                       |                                           | Argument could be one or more table names mapped to the given YANG list node          |
|                                                       |                                           | The table-name is inherited to all descendant nodes unless another one is defined.    |
| sonic-ext:field-name [string]                         | Map a YANG leafy to FIELD name            | Processed by the default transformer method                                           |
| sonic-ext:key-delimiter [string]                      | Override the default delimiter, “|”       | Processed by the default transformer method                                           |
|                                                       |                                           | Used to concatenate multiple YANG keys into a single DB key                           |
| sonic-ext:key-transformer [function]                  | Overloading the default method to generate| Used when the key values in a YANG list are different from ones in DB TABLE           |
|                                                       | DB key(s)                                 | A pair of callbacks should be implemented to support 2 way translation - YangToDBxxx, |
|                                                       |                                           | Db2Yangxxx                                                                            |
| sonic-ext:field-transformer [function]                | Overloading default method for field      | Used when the leaf/leaf-list values defined in a YANG list are different from the     |
|                                                       | generation                                | field values in DB                                                                    |
|                                                       |                                           | A pair of callbacks should be implemented to support 2 way translation - YangToDBxxx, |
|                                                       |                                           | Db2Yangxxx                                                                            |
| sonic-ext:subtree-transformer [function]              | Overloading default method for the current| Allows the sub-tree transformer to take full control of translation. Note that, if any|
|                                                       | subtree                                   | other extensions are annotated to the nodes on the subtree, they are not effective.   |
|                                                       |                                           | The subtree-transformer is inherited to all descendant nodes unless another one is    |
|                                                       |                                           | defined, i.e. the scope of subtree-transformer callback is limited to the current and |
|                                                       |                                           | descendant nodes along the YANG path until a new subtree transformer is annotated     |
|                                                       |                                           | A pair of callbacks should be implemented to support 2 way translation - YangToDBxxx, |
|                                                       |                                           | DbToYangxxx                                                                           |
|(Coming soon)sonic-ext:db-access-transformer [function]| Overloading default (get) method to read  | Allows the readonly transformer to take full control of DB access and translation     |
|                                                       | db and populate to ygot structure         | from DB to Yang                                                                       |
|                                                       |                                           | Used for “GET” operation, applicable to both rw/ro YANG container/lists               |
|                                                       |                                           | Note that, unless annotated, the default transformer will read DB and populate to the |
|                                                       |                                           | YGOT optionally with the help of DbToYang subtree transformer.                        |
|                                                       |                                           | The readonly-transformer is inherited to all descendant nodes unless another one.     |
| sonic-ext:db-name [string]                            | DB name to access data – “APPL_DB”,       | Used for GET operation to non CONFIG_DB, applicable only to SONiC YANG                |
|                                                       | “ASIC_DB”, “COUNTERS_DB”, “CONFIG_DB”,    | Processed by Transformer core to traverse database                                    |
|                                                       | “FLEX_COUNTER_DB”, “STATE_DB”. The        | The db-name is inherited to all descendant nodes unless another one.                  |
|                                                       | default db-name is CONFIG_DB              | Must be defined with the table-name                                                   |
|(Coming soon) sonic-ext:post-transformer [function]    | A special hook to update the DB requests  | Analogous to the postponed YangToDB subtree callback that is invoked at the very end  |
|                                                       | right before passing to common-app        | by the Transformer.                                                                   |
|                                                       |                                           | Used to add/update additional data to the maps returned from Transformer before       |
|                                                       |                                           | passing to common-app, e.g. add a default acl rule                                    |
|                                                       |                                           | Note that the post-transformer can be annotated only to the top-level container(s)    |
|                                                       |                                           | within each module, and called once for the given node during translation             |
| sonic-ext:get-validate [function]                     | A special hook to validate YANG nodes,    | Allows developers to instruct Transformer to choose a YANG node among multiple nodes, |
|                                                       | to populate data read from database       | while constructing the response payload                                  |            |
|                                                       |                                           | Typically used to check the “when” condition to validate YANG node among multiple     |
|                                                       |                                           | nodes to choose only valid nodes from sibling nodes.                                  |

The template annotation file generated from section [2.4.1.1](#2411-annotation-file) can be used by the app developer to add extensions to the YANG paths as needed to transform data between YANG and ABNF format.

Following is the guide to find which extensions can be annotated in implementing the model.

    1. If the translation is simple mapping between YANG list and TABLE, consider using the extensions - table-name, field-name, optionally key-delimiter, key-transformer, field-transformer

    2. If the translation requires a complex translation with codes, use the extension, subtree-transformer, to take control during translation. Note that multiple subtree-transformers can be annotated along YANG path to divide the scope

    3. If multiple tables are mapped to a YANG list, e.g. openconfig-interface.yang, use the table-name extension with a set of table names, and annotate the subtree-transformer to dynamically choose tables based on URI/payload

    4. In GET operation, Transformer can read data by TABLE and optionally KEYs learned from URI. But, in case that you need to access database with your own method, annotate the db-access-transformer to take a control during data access, e.g. when you read interface counters, you need to get OID for the interface name, then subsequently read the counters by the OID.

##### 2.4.1.3 Manifest file

Add the list of YANG modules and annotation files to the transformer manifest file located at sonic-mgmt-framework/config/transformer/models_list

    e.g. for openconfig ACL
    openconfig-acl-annot.yang
    openconfig-acl.yang

##### 2.4.1.4 Special handling

Implement the overload methods if you need translate data with special handling. There are three types of transformer special handling functions: key-transformer, field-transformer and subtree-transformer. Argument of each transformer is used by the transformer core to dynamically lookup and invoke the function during data translation. A function name is formed by an argument string prefixed by a reserved literal – “YANGToDb_” or “DbToYANG_”, which distinguishes the direction in which the convertion happens.

Here is a data structures passed from Transformer to overloaded methods.

        type XfmrParams struct {
        d *db.DB
        dbs [db.MaxDB]*db.DB
        curDb db.DBNum
        ygRoot *ygot.GoStruct
        uri string
        oper int
        key string
        dbDataMap *map[db.DBNum]map[string]map[string]db.Value
        param interface{}
    }

e.g. for YANG extension defined in the annotation file
sonic-ext:subtree-transformer "acl_port_bindings_xfmr";
A pair of functions shall be implemented for two way translation:  YANGToDb_acl_port_bindings_xfmr() and  DbToYANG_acl_port_bindings_xfmr().

    e.g. xfmr_acl.go

    var YangToDb_acl_port_bindings_xfmr SubTreeXfmrYangToDb = func(inParams XfmrParams) (map[string]map[string]db.Value, error) {
        var err error
        res_map := make(map[string]map[string]db.Value)
        aclTableMap := make(map[string]db.Value)
        log.Info("YangToDb_acl_port_bindings_xfmr: ", inParams.ygRoot, inParams.uri)
    
        aclObj := getAclRoot(inParams.ygRoot)
        if aclObj.Interfaces == nil {
            return res_map, err
        }
    . . .
    }
    var DbToYang_acl_port_bindings_xfmr SubTreeXfmrDbToYang = func(inParams XfmrParams) error {
        var err error
        data := (*inParams.dbDataMap)[inParams.curDb]
        log.Info("DbToYang_acl_port_bindings_xfmr: ", data, inParams.ygRoot)
    . . .
    }

Mapping openconfig ENUM to Redis ABNF data is typically handled by field transformer. Below example shows how.
    e.g. E_OpenconfigAcl_FORWARDING_ACTION

    var ACL_FORWARDING_ACTION_MAP = map[string]string{
        strconv.FormatInt(int64(ocbinds.OpenconfigAcl_FORWARDING_ACTION_ACCEPT), 10): "FORWARD",
        strconv.FormatInt(int64(ocbinds.OpenconfigAcl_FORWARDING_ACTION_DROP), 10): "DROP",
        strconv.FormatInt(int64(ocbinds.OpenconfigAcl_FORWARDING_ACTION_REJECT), 10): "REDIRECT",
    }

    . . .
    
    var YangToDb_acl_forwarding_action_xfmr FieldXfmrYangToDb = func(inParams XfmrParams) (map[string]string, error) {
        res_map := make(map[string]string)
        var err error
        if inParams.param == nil {
            res_map["PACKET_ACTION"] = ""
            return res_map, err
        }
        action, _ := inParams.param.(ocbinds.E_OpenconfigAcl_FORWARDING_ACTION)
        log.Info("YangToDb_acl_forwarding_action_xfmr: ", inParams.ygRoot, " Xpath: ", inParams.uri, " forwarding_action: ", action)
        res_map["PACKET_ACTION"] = findInMap(ACL_FORWARDING_ACTION_MAP, strconv.FormatInt(int64(action), 10))
        return res_map, err
    }
    var DbToYang_acl_forwarding_action_xfmr FieldXfmrDbtoYang = func(inParams XfmrParams) (map[string]interface{}, error) {
        var err error
        result := make(map[string]interface{})
        data := (*inParams.dbDataMap)[inParams.curDb]
        log.Info("DbToYang_acl_forwarding_action_xfmr", data, inParams.ygRoot)
        oc_action := findInMap(ACL_FORWARDING_ACTION_MAP, data[RULE_TABLE][inParams.key].Field["PACKET_ACTION"])
        n, err := strconv.ParseInt(oc_action, 10, 64)
        result["forwarding-action"] = ocbinds.E_OpenconfigAcl_FORWARDING_ACTION(n).ΛMap()["E_OpenconfigAcl_FORWARDING_ACTION"][n].Name
        return result, err
    }

Overloaded transformer functions are grouped by YANG module, to have a separate GO file. At init(), the functions need to be bind for dynamic invocation.
    e.g. xfmr_acl.go

    func init () {
        XlateFuncBind("YANGToDb_acl_entry_key_xfmr", YANGToDb_acl_entry_key_xfmr)
        XlateFuncBind("DbToYANG_acl_entry_key_xfmr", DbToYANG_acl_entry_key_xfmr)
        XlateFuncBind("YANGToDb_acl_l2_ethertype_xfmr", YANGToDb_acl_l2_ethertype_xfmr)
        XlateFuncBind("DbToYANG_acl_l2_ethertype_xfmr", DbToYANG_acl_l2_ethertype_xfmr)
        XlateFuncBind("YANGToDb_acl_ip_protocol_xfmr", 
    . . .
    }

#### 2.4.2 App Module

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

### 2.5 Config Validation Library

Config Validation Library (CVL) performs the automatic syntactic and semantic validation based on the constraints defined in SONiC YANG. Note that CVL uses CVL YANG derived from SONiC YANG by stripping off read-only state objects, RPC and Notification objects. This happens during build time automatically with the help of pyang plugin and therefore no manual intervention is needed. 

If any specific validation can't be achieved through constraints, CVL provides options to develop custom validation code (this is WIP in 'buzznik' and more details would be updated soon) which is loaded as a plug-in in CVL. CVL generates stub function based on YANG extension and you need to implement functional validation code inside this stub function and place the file inside 'src/cvl/custom_validation' folder.   

CVL allows platform specific validation in following ways:

* Add YANG 'deviation' files (e.g. sonic-acl-deviation.yang for ACL YANG) per platform and place it in 'models/yang/sonic/deviation' folder for static platform validation. These files are automatically picked up during build time and processed.
* Implement platform specific custom validation through CVL plug-in for dynamic platform validation.

### 2.6 Industry Standard CLI

Open source Klish is integrated to sonic-mgmt-framework to provide the command line interface tool to perform network operations more efficiently in SONiC. Klish will provide the core functionality of command parsing, syntax validation, command help and command auto-completion.

Open Source [klish](http://libcode.org/projects/klish/.) is used here.

#### 2.6.1 CLI components

1. CLI Parser engine: Open source Klish

2. XML files:
XML files, defined by developer, that describe the CLI command structure.
Klish uses XML based command tree inputs to build the parser command tree.
All CLI commands to be supported are specified in XML format in module specific XML file.
XML files can be defined with macros and entity references, preprocessed by scripts to generate the expanded XML files.

3. Actioner: Script that will transform CLI commands to form the corresponding REST requests and invoke the REST client API.

4. Renderer: Script that will receive the JSON response from REST client API and use the jinja2 template file to render(display) the CLI output in the desired format.

#### 2.6.2 CLI development steps

Following are the steps to add a new CLI command. Please refer to https://github.com/sipwise/klish/blob/master/doc/klish.md for detail.

1. Create a CLI XML .xml file that defines the CLI command structure. This file defines the following
    * CLI command format
    * Parameters that the command requires
    * Help string to be displayed for the command and parameters
    * Datatype of the parameters.
    * View name for which the command needs to be available. Eg: configure-view(config mode) or enable-view(exec mode)

Example:

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

2. Write/Update an actioner script: The actioner script prepares the message body having the JSON request and invokes the REST client API. The actioner script is invoked by the klish and the input parameters are passed to it from the XML file.
Actioner can be defined with the <ACTION> tag in the XML file. There are three different methods available to implement the Actioner: sub-shell, clish_restcl and clish_pyobj. Sub-shell is spawned by Klish to run the script defined in <ACTION> tag. Both clish_pyobj and clish_restcl methods are part of Klish built-in fucntions and invoked by Klish. The built-in fucntions can be used for commands that would reduce time taken to execute a command by eliminating the sub-shell interpreter overhead.

  * Spawn a sub-shell to run the scripts defined in a command's <ACTION> tag. The shebang can be specified for the script execution. By default the "/bin/sh" is used. To customize shebang the 'shebang' field of the ACTION tag is used.

    The sub-shell runs the Python script sonic_cli_<module_name>.py
	sonic_cli_<module_name>.py <OpenAPI client method> [parameters . . .]
    The sonic_cli_<module_name>.py has a dispatch function to call a REST client method with parameters passed from user input.

    **Example**:
    Refer the <ACTION> tag in the above example command.
    The actioner scripts are placed in the following location:
    sonic-mgmt-framework/src/CLI/actioner/
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
    <VAR dynamic="true" name="supported_breakout_modes">        
       <ACTION builtin="clish_pyobj">sonic_cli_breakout.py capability</ACTION>
    </VAR>
    . . .
    <PARAM 
     name="100g-1x"
     help="breakout to 1 100G interface"
     mode="subcommand" ptype="SUBCOMMAND"
     test='${supported_breakout_modes} -ct ETHERNET:BREAKOUT_1x1:100GIGE'
    />

3. Write/Update Renderer scripts and templates. The JSON response from the swagger client API is received by the actioner and passes the response to the renderer script. The renderer script will invoke the jinja2 template with the JSON response. The template will parse the JSON response and generate the CLI output. Refer files in the below path for an example of usage 

    **Renderer path**:
    sonic-mgmt-framework/src/CLI/renderer
    **Renderer script**:
    scripts/render_cli.py
    **Renderer template**:
    templates/show_access_list.j2

    Every show command response can have a separate template file.

#### 2.6.3 Enhancements to Klish

Additional enhancements can be done to open source klish as below. Enhancements may include defining a new data types for CLI command parameters, define new macros that can be referenced for CLI commands structure that have repetitive definitions and defining platform specific entity values.

1. PTYPES
    New parameter types (PTYPES) can be defined and used in the CLI XML files.
    * PTYPE represents a parameter type, a syntactical template which parameters reference.
    * sonic-clish.xsd defines the tag and the attributes associated with the PTYPE tag.
    * Whenever a new attribute or tag introduced the xsd rules should also be updated.
    * sonic-clish.xsd is avilable at sonic-mgmt-framework/src/CLI/clitree/scripts/
    * The klish source supports certain primitive PTYPEs.
    * New user defined PTYPEs can be added to the SONIC project and can be defined in sonic_types.xml file.
    * sonic_types.xml is available in sonic-mgmt-framework/src/CLI/clitree/cli-xml/sonic_types.xml

    **Example**:  STRING_32

    <PTYPE
        name="STRING_32"
        pattern="(^([a-zA-Z0-9_-]){1,32})$"
        help="String"
    />

2. MACROS
    * Macros can be introduced by defining them in <module>_macro.xml 
    * Macros are used where repetitive command snippets (or command parameter snippets) with minor variations are needed in XML files. 
    * It is possible to create a macro definition in a <module>_macro.xml file and use the macro in the <module>.xml file.
    * For cases where variations in the values of these macro options are needed, the XML attributes can be passed as arguments to macro and substituted as values inside the macro definition. 
    * As part of parser tree preprocessing during Make, the referenced macro is expanded with the macro definitions and then the parser file is exported to the target XML files in CLI/target/command-tree to be consumed by Klish parser.
    * One macro file can be written per module.
    * The macro files are placed at sonic-mgmt-framework/src/CLI/clitree/macro/
    * Macros can also be nested with reference to another macro definition.

    **Example**:

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

    * The previous macro “IPV4-SRC-OPTIONS“ is used by the macro below "IPV4-ACL".

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

3. Entities

    * Entities can be defined and referenced in the XML files.
    * One common use case for entities is to specify platform specific parameters and parameter value limits in XML files.
    * To define an entity based parameter value range limit, three tasks must be done:

    1. Define the feature value as entity in mgmt_clish_feature_master.xsd
    **Example**:

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

    2. Set the attribute 'value' to the right limit on respective platform configuration file that can be defined statically (used at build time).
    Refer to a dummy platform (platform_dummy.xml) configuration file.
    The platform_dummy.xml file can be located at sonic-mgmt-framework/src/CLI/clitree/scripts/.

    **Example**:

    <ENTITYNAME value="9276">MAX_MTU</ENTITYNAME>

    3. Use the ENTITY just like any other XML ENTITY in the CLI parser XML file.

4. Extended support with ext_help and regexp_select  
   The ext_help is similar to the pattern used in select method and used with regexp_select method. The value of the ext_pattern attribute is used for auto completion in regexp_select method.

   **Example**:
   Interfaces can be defined with regexp_select method and ext_pattern to support abbreviated interface naming, i.e eth20, e20, Ether20 etc. Here, we are left the help part as empty, and define the help string in the place where we use this PTYPE.
   <!ENTITY ETH_PHY_NUM     "([0-9]|[1-9]([0-9])*)">
   <!ENTITY ETH_ALL_INTF    "(^[eE]([t]|(th)|(thernet))?\s*((&amp;ETH_PHY_NUM;$)))">
   <PTYPE
      name="PHY_INTERFACE"
      method="regexp_select"
      ext_pattern="Ethernet(port)"
      pattern="&ETH_ALL_INTF;"
      help=""
   />

#### 2.6.4 Preprocess XML files

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

#### 2.6.5 CLI directory structure

sonic-mgmt-framework/CLI

- actioner
- clicfg
- clitree
	- cli-xml
	- macro
	- scripts
- klish
	- patches
		- klish-2.1.4
		- scripts
- renderer
	- scripts
	- templates

Below directories are used to collect XML files and utility scripts to generate the target XML files for CLI command tree build-out.  

**clitree/cli-xml**  - contains unprocessed/raw CLI XML files defined by developer

**clitree/macro**    - contains macro definitions used/referenced in CLI XML files defined by developer

**clitree/scripts**  - contains utility scripts to process raw CLI XML files defined by developer into processed CLI XMLs to be consumed by Klish Parser.

**clitree/Makefile** - rules to preprocess the raw CLI XMLs and validate the processed output against the DTD in sonic-clish.xsd

**clicfg**           - files for platform specific entity substitution.

**renderer**         - templates and scripts to  be used in rendering the show commands output.

After compilation the processed CLI XMLs can be found in sonic-mgmt-framework/build/cli/command-tree

### 2.7 gNMI

There is no specific steps required for gNMI.

### 2.8 Unit Testing
#### 2.8.1 REST Server

REST server provides a test UI (Swagger UI) will display the operations defined in OpenAPI spec along with options to test it inline. To launch the Swagger UI, open “https://IP:80/ui” from the browser. Browser may complain that the certificate is not trusted. This is expected since the REST Server uses a temporary self signed certificate by default. Ignore the warning and proceed, this loads a home page as shown below, which contains links for OpenAPIs both derived from yang models and also manually written OpenAPI specs.

![Swagger UI Home Page](images/homepage.jpeg)
Upon clicking of any one of the link, The Swagger UI correspoding to that openAPI spec will be opened as shown below.

![OpenAPI Page](images/openapis.jpeg)

Expand any section to view description, parameters and schema/sample data..

Use “Try it out” button test the API from the Swagger UI itself. It opens a form to enter URI parameters and body data. Enter values and hit “Execute” button. REST API will be invoked and results are shown.

### 2.8.2 gNMI Unit Testing
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
	
