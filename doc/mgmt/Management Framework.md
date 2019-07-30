# SONiC Management Framework

## High level design document

### Rev 0.2

## Table of Contents

* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definition/Abbreviation](#definitionabbreviation)
* [Table 1: Abbreviations](#table-1-abbreviations)
* [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#1_1-requirements)
    * [1.2 Design Overview](#1_2-design-overview)
        * [1.2.1 Basic Approach](#1_2_1-basic-approach)
        * [1.2.2 Container](#1_2_2-container)
* [2 Functionality](#2-functionality)
    * [2.1 Target Deployment Use Cases](#2_1-target-deployment-use-cases)
    * [2.2 Functional Description](#2_2-functional-description)
* [3 Design](#3-design)
    * [3.1 Overview](#3_1-overview)
        * [3.1.1 Build time flow](#3_1_1-build-time-flow)
        * [3.1.2 Run time flow](#3_1_2-run-time-flow)
            * [3.1.2.1 CLI](#3_1_2_1-cli)
            * [3.1.2.2 REST](#3_1_2_2-rest)
            * [3.1.2.3 gNMI](#3_1_2_3-gnmi)
    * [3.2 SONiC Management Framework Components](#3_2-sonic-management-framework-components)
        * [3.2.1 Build time components](#3_2_1-build-time-components)
            * [3.2.1.1 Yang to OpenAPI converter](#3_2_1_1-yang-to-openapi-converter)
                * [3.1.1.1.1 Overview](#3_1_1_1_1-overview)
                * [3.1.1.1.2 Supported HTTP verbs](#3_1_1_1_2-supported-http-verbs)
                * [3.1.1.1.3 Supported Data Nodes](#3_1_1_1_3-supported-data-nodes)
                * [3.1.1.1.4 Data Type Mappings](#3_1_1_1_4-data-type-mappings)
                * [3.1.1.1.5 Notes](#3_1_1_1_5-notes)
                * [3.1.1.1.6 Future enhancements](#3_1_1_1_6-future-enhancements)
            * [3.2.1.2 swagger generator](#3_2_1_2-swagger-generator)
            * [3.2.1.3 YGOT generator](#3_2_1_3-ygot-generator)
            * [3.2.1.4 pyang compiler](#3_2_1_4-pyang-compiler)
        * [3.2.2 Run time components](#3_2_2-run-time-components)
            * [3.2.2.1 CLI](#3_2_2_1-cli)
            * [3.2.2.2 REST Client SDK](#3_2_2_2-rest-client-sdk)
            * [3.2.2.3 gNMI Client](#3_2_2_3-gnmi-client)
            * [3.2.2.4 REST Server](#3_2_2_4-rest-server)
                * [3.2.2.4.1 Transport options](#3_2_2_4_1-transport-options)
                * [3.2.2.4.2 TransLib linking](#3_2_2_4_2-translib-linking)
                * [3.2.2.4.3 Media Types](#3_2_2_4_3-media-types)
                * [3.2.2.4.4 Payload Validations](#3_2_2_4_4-payload-validations)
                * [3.2.2.4.5 Concurrency](#3_2_2_4_5-concurrency)
                * [3.2.2.4.6 API Versioning](#3_2_2_4_6-api-versioning)
                * [3.2.2.4.7 RESTCONF Entity-tag](#3_2_2_4_7-restconf-entity-tag)
                * [3.2.2.4.8 RESTCONF Discovery](#3_2_2_4_8-restconf-discovery)
                * [3.2.2.4.9 RESTCONF Query Parameters](#3_2_2_4_9-restconf-query-parameters)
                * [3.2.2.4.10 RESTCONF Operations](#3_2_2_4_10-restconf-operations)
                * [3.2.2.4.11 RESTCONF Notifications](#3_2_2_4_11-restconf-notifications)
                * [3.2.2.4.12 Authentication](#3_2_2_4_12-authentication)
                * [3.2.2.4.13 DB Schema](#3_2_2_4_13-db-schema)
            * [3.2.2.5 gNMI server](#3_2_2_5-gnmi-server)
			    * [3.2.2.5.1 Files changed/added](#3_2_2_5_1-files-changed/added)
				* [3.2.2.5.2 Sample Requests](#3_2_2_5_3-sample-requests)
            * [3.2.2.6 Translib](#3_2_2_6-translib)
                * [3.2.2.6.1 App Interface](#3_2_2_6_1-app-interface)
                * [3.2.2.6.2 Translib Request Handler](#3_2_2_6_2-translib-request-handler)
                * [3.2.2.6.3 YGOT request binder](#3_2_2_6_3-ygot-request-binder)
                * [3.2.2.6.4 DB access layer](#3_2_2_6_4-db-access-layer)
                * [3.2.2.6.5 App Modules](#3_2_2_6_5-app-modules)
            * [3.2.2.7 Config Validation Library (CVL)](#3_2_2_7-config-validation-library-cvl)
				* [3.2.2.7.1 Architecture](#3_2_2_7_1-architecture)
				* [3.2.2.7.2 Validation types](#3_2_2_7_2-validation-types)
				* [3.2.2.7.3 CVL APIs](#3_2_2_7_3-cvl-apis)
            * [3.2.2.8 Redis DB](#3_2_2_8-redis-db)
            * [3.2.2.9 Non DB data provider](#3_2_2_9-non-db-data-provider)
* [4 Flow Diagrams](#4-flow-diagrams)
    * [4.1 REST SET flow](#4_1-rest-set-flow)
    * [4.2 REST GET flow](#4_2-rest-get-flow)
	* [4.3 Translib Initialization flow](#4_3-translib-initialization-flow)
	* [4.4 gNMI flow](#4_4-gNMI-flow)
	* [4.5 CVL flow](#4_5-CVL-flow)
	
* [5 Error Handling](#5-error-handling)
* [6 Serviceability and Debug](#6-serviceability-and-debug)
* [7 Warm Boot Support](#7-warm-boot-support)
* [8 Scalability](#8-scalability)
* [9 Unit Test](#9-unit-test)
* [10 Internal Design Information](#10-internal-design-information)

## List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

## Revision

| Rev |     Date    |       Author            | Change Description                |
|:---:|:-----------:|:-----------------------:|-----------------------------------|
| 0.1 | 06/13/2019  | Anand Kumar Subramanian | Initial version                   |
| 0.2 | 07/05/2019  | Prabhu Sreenivasan      | Added gNMI, CLI content from DELL |

## About this Manual

This document provides general information about the Management framework feature implementation in SONiC.

## Scope

This document describes the high level design of Management framework feature.

## Definition/Abbreviation

### Table 1: Abbreviations

| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| CVL                      | Config Validation Library           |

## 1 Feature Overview

Management framework is a SONiC application which is responsible for providing various common North Bound Interfaces (NBIs) for the purposes of managing configuration on SONiC switches. The application manages coordination of NBI’s to provide a coherent way to validate, apply and show configuration.

### 1.1 Requirements

* Must provide support for:

    1. Standard [YANG](https://tools.ietf.org/html/rfc7950) models (e.g. OpenConfig, IETF, IEEE)
    2. Industry-standard CLI

* Must provide support for [OpenAPI spec](https://swagger.io/specification/) to generate REST server side code
* Must provide support for NBIs such as:

    1. CLI
    2. gNMI
    3. REST/RESTCONF

* Must support the following security features:

    1. Certificate-based authentication
    2. User/password based authentication

* Ease of use for developer workflow

    1. Specify data model and auto-generate as much as possible from there

* Must support Validation and Error Handling - data model, platform capability/scale, dynamic resources

### 1.2 Design Overview

Management framework makes use of the translation library (Translib) written in golang to convert the data models exposed to the management clients into the Redis ABNF schema format. Supported management servers can make use of the Translib to convert the incoming payload to SONiC ABNF schema and vice versa depending on the incoming request. Translib will cater to the needs of REST and gNMI servers. Later the Translib can be enhanced to support other management servers if needed. This framework will support both standard and custom YANG models for communication with the corresponding management servers. Management framework will also take care of maintaining data consistency, when writes are performed from two different management servers at the same time. Management framework will provide a mechanism to authenticate and authorize any incoming requests. Management framework will also take care of validating the requests before persisting them into the Redis DB.

#### 1.2.1 Basic Approach

#### 1.2.2 Container

The management framework is designed to run in a single container named “sonic-mgmt-framework”. The container includes the REST server linked with translib, and CLI process. The gNMI support requires the gNMI server which is provided as a part of sonic-telemetry container. Although it is possible to run gNMI server in a separate container, it would make more sense to move the gNMI server to the new management framework.

## 2 Functionality

### 2.1 Target Deployment Use Cases

1. KLISH based CLI which will use REST client to talk to the corresponding servers to send and receive data.
2. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
3. gNMI client with support for capabilities, get, set, and subscribe based on the supported YANG models.

### 2.2 Functional Description

## 3 Design

### 3.1 Overview

The SONiC management framework comprises two flows:

1. Build time flow
2. Run time flow

as show in the architecture diagram below.

![Management Framework Architecture diagram](images/Mgmt_Frmk_Arch.jpg)

#### 3.1.1 Build time flow

User can start with YANG or OpenAPI spec.

1. In case of YANG, the pyang compiler generates the corresponding OpenAPI spec which is in turn given to the Swagger generator to generate the REST client SDK and REST SERVER stubs in golang. The YANG data model is also provided to the [YGOT](https://github.com/openconfig/ygot) generator to generate the YGOT bindings which will be consumed by the APP module. The requests in this case will be converted into filled in YGOT structures and given to app module for conversion
2. In case of OpenAPI spec, it is directly given to the [Swagger](https://swagger.io) generator to generate the REST client SDK and REST SERVER stubs in golang. In this case the REST server takes care of validating the incoming request to be OpenAPI compliant before giving the same to the app module. In this case the Translib infra will invoke the App module functions with the path and the raw JSON for App modules for conversion.

#### 3.1.2 Run time flow

##### 3.1.2.1 CLI

1. CLI uses KLISH framework to provide CLI shell. The CLI request is converted to a corresponding REST client request using the Client SDK generated by the Swagger generator and given to the REST server.
2. The Swagger generated REST server in Go programming language, handles all the REST requests from the CLI and invokes a common handler for all the create, update, replace, delete and get operations along with path and payload. This common handler converts all the requests into Translib arguments and invokes the corresponding Translib provided APIs.
3. TransLib uses the value of the input (incoming) path/URI to determine the the identity of the appropriate App module.
4. App module uses the APIs provided by the DB access layer to read and write data into the Redis DB.
5. DB access layer will take care of calling the Configuration Validation Library (CVL) API to validate if the writes to the Redis DB are conforming to the ABNF schema.
6. App modules can directly talk to the Non-DB data providers like FRR, and write and read data from them.

##### 3.1.2.2 REST

1. REST client will use the Swagger generated client SDK to send the request to the REST server.
2. From then on the flow is similar to the one seen in the CLI.

##### 3.1.2.3 gNMI

1. gNMI Is a TCP/gRPC based server that has 4 RPCs defined: Get, Set, Capabilities and Subscribe.
2. gNMI Specification requires all connections to use mutual TLS.
3. Authentication on a per RPC is supported with username/password or token based authentication.
4. Communication happens using Protocol Buffers defined in the gNMI Specification for each request type. 
5. Errors are handled by returning the standard gRPC Error codes in the response, along with one or more user readable error strings.
6. Get requests provide a path to an object and the response provides the object in a specified encoding (Json, Xml, Yang, Protobuf)
7. Set Requests can have more than one operation defined. There are three operation types: Update, Replace and Delete. All operations in a Set Request are part of a transaction that will either succeed or fail as one operation. Update and replace operations provide a path along with a payload provided in a specified encoding. Delete operations only require a path.
8. Set and Get operations will send the request path and payload (if applicable) through to the Translib. Translib will then provide a response in the correct format to be returned to the gNMI client.
9. Capabilities request returns version information, list of supported models (ACL, Interface, System etc.) as well as supported encodings (Json, Xml, Yang, Protobuf etc.)
10. Subscribe request requires a path to an object as well as a operation type: Once, Poll or Stream. For Once, the gRPC connection remains open until a single update is sent, then it is closed. For Poll, the gRPC connection remains open, but the client is responsible for requesting updates to the object. For Stream, the gRPC remains open and the Server will send updates as soon as they are available from Translib.

### 3.2 SONiC Management Framework Components

Management framework components can be classified into

1. Build time components
2. Run time components

#### 3.2.1 Build time components

Following are the build time components of the management framework

1. YANG to OpenAPI converter
2. Swagger generator
3. YGOT generator
4. pyang compiler (for CVL YANG to YIN conversion)

##### 3.2.1.1 YANG to OpenAPI converter

##### 3.1.1.1.1 Overview

Open source Python-based YANG parser called pyang is used for YANG parsing and building a python object dictionary. A custom in-house plugin is developed to translate this python object dictionary into OpenAPI spec. As of now OpenAPI spec version, 2.0 is chosen considering the maturity of the toolset available in the open community.

URI format and payload will be RESTCONF complaint and is based on the [RFC8040](https://tools.ietf.org/html/rfc8040). The Request and Response body will only be in JSON format in this release.

##### 3.1.1.1.2 Supported HTTP verbs

Following are the HTTP methods supported in the version 1

POST, PUT, PATCH, GET and DELETE.

##### 3.1.1.1.3 Supported Data Nodes

For each of the below-listed Data keywords nodes in the YANG model, the OpenAPI (path) will be generated in version 1

* Container
* List
* Leaf
* Leaf-list

##### 3.1.1.1.4 Data Type Mappings

| YANG Type |     OpenAPI Type
|:---:|:-----------:|:-----------------------:|-----------------------------------|
| int8 | Integer
| int16 | Integer
| int32 | Integer
| int64 | Integer
| uint8 | Integer
| uint16 | Integer
| uint32 | Integer
| uint64 | Integer
| decimal64 | Number
| String | string
| Enum | Enum
| Identityref | String (Future can be Enum)
| long | Integer
| Boolean | Boolean
| Binary | String with Format as Binary (<https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md>)
| bits | integer

##### 3.1.1.1.5 Notes

* All list keys will be made mandatory in the payload and URI
* YANG mandatory statements will be mapped to the required statement in OpenAPI
* Default values, Enums are mapped to Default and Enums statements of OpenAPI
* Currently, Swagger/OpenAPI 2.0 Specification does NOT support JSON-schema a yOf and oneOfdirectives, which means that we cannot properly treat YANG choice/case statements during conversion. As a workaround, the current transform will simply serialize all configuration nodes from the choice/case sections into a flat list of properties.

##### 3.1.1.1.6 Future enhancements

* Support for additional Data nodes such as RPC, Actions, and notifications(if required).
* Support for RESTCONF query parameters such as depth, filter, etc 
* Support for other RESTCONF features such as capabilities.
* Support for HTTPS with X.509v3 Certificates.
* Support for a pattern in string, the range for integer types and other OpenAPI header objects defined in https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#header-object 
* Other misc OpenAPI related constraint will be added

##### 3.2.1.2 Swagger generator

Swagger-codegen tool (github.com/Swagger-api/Swagger-codegen) is used to generate REST server and client code from the OpenAPI definitions. It consumes the OpenAPI definitions generated from YANG files and any other manually written OpenAPI definition files.

REST Server is generated in GO language. Customized Swagger-codegen templates are used to make each server stub invoke a common request handler function. The common request handler will invoke Translib APIs to service the request.

REST client is generated in python language. Client applications can generate the REST client in any language using standard Swagger-codegen tool.

##### 3.2.1.3 YGOT generator

YGOT generator generates GO binding structures for the management YANG. The generated GO binding structures are consumed by the Translib to validate the incoming payload and help in conversion of Redis data to management YANG specific JSON output payload.

##### 3.2.1.4 pyang compiler

Open source pyang tool is used to compile CVL specific SONiC native YANG models and generate YIN schema.

#### 3.2.2 Run time components

Following are the run time components in the management framework

1. CLI
2. REST Client SDK
3. gNMI Client
4. REST Server
5. gNMI Server
6. Translib
7. Config Validation Library (CVL)
8. Redis DB
9. Non DB data provider

##### 3.2.2.1 CLI

Open source Klish is integrated to sonic-mgmt-framework to provide the command line interface tool to perform network operations more efficiently in SONiC.  Klish will provide the core functionality of command parsing, syntax validation, command help and command auto-completion. 

![CLI components Interaction Diagram](images/cli_interactions.jpg)

1. CLI command input from user
2. Klish invokes the actioner script
3. Actioner script invokes the swagger client API to make a REST API call.
4. Receive response from swagger client API and pass it to renderer scripts.
5. Renderer scripts processes the JSON response from Rest Client and parses the response.
6. CLI output is rendered to the console.


CLI consists of the following components.

1) CLI Parser engine

Open source Klish

2) XML files

XML files defined by developer that defines the CLI command structure. Klish uses XML based command tree inputs to build the parser command tree. Every CLI to be supported are specified in xml format in module/feature specific xml file. XML files can be defined with macros and entity references, preprocessed by scripts to generate the expanded XML files.

3) Actioner scripts

Script that will form the request body and invoke the swagger client API.

4) Renderer

Script that will receive the JSON response from Swagger CLI API and use the jinja2 template file to render the CLI output in the desired format.

###### Preprocess XML files

The preprocessing scripts preprocess the raw CLI xml files and generate a target XML file that can be consumed by the klish open source parser. The inputs to the preprocessing scripts are the raw CLI XML files, macro files and other utility files like platform specifics. 

The cli-xml files are validated as part of compilation. The 'xmllint' binary is used to validate all the processed XML files (i.e. after macro substitution and pipe processing) against the detailed schema kept at sonic-clish.xsd

The following preprocessing scripts are introduced:

*klish_ins_def_cmd.py*

This script is used to append the "exit" and "end" commands to the views of the Klish XML files


*klish_insert_pipe.py*

This script extends every show and get COMMAND with pipe option


*klish_platform_features_process.sh*

Validate all platform xml files. Generate the entity.xml files.


*klish_replace_macro.py*

This script does macro replacement on the xml files which are used by klish to define CLI structure.


###### Actioner scripts

The Actioner script is used to invoke the swagger client API. The script can be defined in the <ACTION> tag and run with bash conditional expressions.  

    Example:
    <VIEW name="configure-if-view">
        <!-- ip access-group -->
        <COMMAND
             name="ip access-group"
             help="Specify access control for packets"
             >
        <MACRO name="ACG-OPTIONS" arg=""></MACRO>
        <ACTION>
            if test "${direction-switch}" = "in"; then
                python $SONIC_CLI_ROOT/target/sonic-cli.py post_list_base_interfaces_interface ${access-list-name} ACL_IPV4 ${iface} ingress
            else
                python $SONIC_CLI_ROOT/target/sonic-cli.py post_list_base_interfaces_interface ${access-list-name} ACL_IPV4 ${iface} egress
            fi
        </ACTION>
        </COMMAND>

###### Renderer scripts.

The actioner script receives the JSON output from the swagger client API and invokes the renderer script. The renderer script will send the JSON response to the jinja2 template file to parse the response and generate the CLI output.


###### Workflow (to add a new CLI)

The following steps are to be followed when a new CLI is to be added.
1. Create a CLI XML file that defines the cli command structure.
2. Define the CLI command and the parameters that the command requires.
3. Define the CLI help string to be displayed and datatype for the parameters.
   New parameter types(PTYPES) can be defined and used in the CLI XML files.
   All xml tags should be defined in the sonic-clish.xsd schema file.
4. New macro can be introduced by defining them in <module>macro.xml 


##### 3.2.2.2 REST Client SDK

Framework provides swagger-codegen generated python client SDK. Developers can generate client SDK code in other programming languages from the OpenAPI definitions on need basis.

Client applications can use swagger generated client SDK or any other REST client tool to communicate with REST Server.

##### 3.2.2.3 gNMI Client

GNMI clients developed by JipanYANG.(github.com/jipanYANG/gnxi/gnmi_get, github.com/jipanYANG/gnxi/gnmi_set)
are used for testing. gnmi_get and gnmi_set code has been changed to handle module name.

##### 3.2.2.4 REST Server

The management REST Server will be implemented as a Go HTTP server. It supports below operations:

* RESTCONF APIs for YANG data
* REST APIs for manual OpenAPI definitions

###### 3.2.2.4.1 Transport options

REST Servers supports only HTTPS transport and listens on default port 443. Server port can be changed through a an entry in ConfigDB REST_SERVER table. Details are in [DB Schema](#322413-db-schema) section.

HTTPS certificates are managed similar to that of existing gNMI Telemetry program. Server key, certificate and CA certificate are maintained in ConfigDB DEVICE_METATDATA table. Same certificate will be used by both gNMI Telemetry and REST Server.

###### 3.2.2.4.2 Translib linking

REST Server will statically link with Translib. Each REST request will invoke Translib APIs which will invoke appropriate app module. Below is the mapping of HTTP operations to Translib APIs:

 HTTP Method | Translib API     | Request data  | Response data
-------------|------------------|---------------|---------------
 GET         | Translib.Get     | path          | status, payload
 POST        | Translib.Create  | path, payload | status
 PATCH       | Translib.Update  | path, payload | status
 PUT         | Translib.Replace | path, payload | status
 DELETE      | Translib.Delete  | path          | status

More details about Translib APIs are in section [3.2.2.6](#3226-Translib).

###### 3.2.2.4.3 Media Types

YANG defined RESTCONF APIs support **application/yang-data+json** media type. **application/yang-data+xml** is not supported in first release.

OpenAPI defined REST APIs can support any media type. REST Server or Translib will not process input or output data for such APIs. App module should process the data.

###### 3.2.2.4.4 Payload Validations

REST Server will not perform any payload validation for YANG defined RESTCONF APIs. Translib will validate the input and output payloads through YGOT bindings.

For OpenAPI defined REST APIs the REST Server will provide limited payload validation. Translib will not validate such payloads. JSON request payloads (content type **application/json**) will be validated against the schema defined in OpenAPI. Response data and non-JSON request data will not be validated.

###### 3.2.2.4.5 Concurrency

REST Server will accept concurrent requests. Translib provides appropriate locking mechanism - parallel reads and sequential writes.

###### 3.2.2.4.6 API Versioning

REST Server will allow clients to specify API version through a custom HTTP header "Accept-Version". However API versioning feature will be supported only in a future release. The server will ignore the version information in current release.

    Accept-Version: 2019-06-20
    Accept-Version: 1.0.3

REST Server will extract version text from the request header and pass it to the Translib API as metadata. App modules can inspect the version information and act accordingly.

For YANG defined RESTCONF APIs, the version will the latest YANG revision date. For manual OpenAPI definitions developer can define version text in any appropriate format.

###### 3.2.2.4.7 RESTCONF Entity-tag

REST Server supports entity-tag and last-modified timestamps only for top level datastore (/restconf/data). Per resource entity tags and timestamps will not be supported. Global entity tag and timestamp are used for all resources.

###### 3.2.2.4.8 RESTCONF Discovery

Server will support RESTCONF root resource discovery as described in [RFC8040, section 3.1](https://tools.ietf.org/html/rfc8040#page-18). RESTCONF root resource will be "/restconf".

YANG module library discovery as per [RFC7895](https://tools.ietf.org/html/rfc7895) will be supported in a future release.

###### 3.2.2.4.9 RESTCONF Query Parameters

RESTCONF Query Parameters will be supported in future release. All query parameters will be ignored by REST Server in this release.

###### 3.2.2.4.10 RESTCONF Operations

RESTCONF operations via YANG RPC are not supported in this release. They can be supported in future releases.

###### 3.2.2.4.11 RESTCONF Notifications

RESTCONF Notification are not supported by framework. Clients can use gNMI for monitoring and notifications.

###### 3.2.2.4.12 Authentication

REST Server will support below 3 authentication modes.

* No authentication
* TLS Certificate authentication
* Username/password authentication

Only one mode can be active at a time. Administrator can choose the authentication mode through ConfigDB REST_SERVER table entry. See [DB Schema](#322413-db-schema) section.

###### 3.2.2.4.12.1 No Authentication

This is the default mode. REST Server will not authenticate the client; all requests will be processed. It should not be used in production.

###### 3.2.2.4.12.2 Certificate Authentication

In this mode TLS public certificate of the client will be used to authenticate the client. Administrator will have to pre-provision the CA certificate in ConfigDB DEVICE_METADATA|x509 entry. REST Server will accept a connection only if the client TLS certificate is signed by that CA.

###### 3.2.2.4.12.3 User Authentication

In this mode REST Server expects the client to provide user credentials in every request. Server will support HTTP Basic Authentication method to accept user credentials.

REST Server will integrate with Linux PAM to authenticate and authorize the user. PAM may internally use native user database or TACACS+ server based on system configuration. REST write requests will be allowed only if the user has admin privileges. Only read operations will be allowed for other users.

Performing TACACS+ authentication for every REST request can slow down the APIs. This will be optimized through JSON Web Token (JWT) or a similar mechanism in future release.

###### 3.2.2.4.13 DB Schema

A new table "REST_SERVER" will be introduced in ConfigDB for maintaining REST Server configurations. Below is the schema for this table.

    key         = REST_SERVER:default   ; REST Server configurations.
    ;field      = value
    port        = 1*5DIGIT              ; Server port - defaults to 443
    client_auth = "none"/"user"/"cert"  ; Client authentication mode.
                                        ; none: No authentication, all clients
                                        ;       are allowed. Should be used only
                                        ;       for debugging. Default value.
                                        ; user: Username/password authentication
                                        ;       via PAM.
                                        ; cert: Certificate based authentication.
                                        ;       Client's public certificate should
                                        ;       be registered on this server.
    log_level   = DIGIT                 ; Verbosity for glog.V logs


##### 3.2.2.5 gNMI server

1. gNMI Server is part of the telemetry process that supports dialout telemtry as well as gNMI.
2. The gRPC server opens a TCP port and allows only valid mutually authenticated TLS connections, which requires valid Client, Server and CA Certificates be installed as well a properly configured DNS. Multiple simultaneous connections are allowed to gNMI server.
3. The gNMI Agent uses the db client, as well as the non-db client to access and modify data directly in the redis DB.
4. The Translib client is used to provide alternative models of access such as Openconfig models as opposed to the native redis schema, as long as the Translib supports these models. Translib offers bidirectional translation between the native redis model and the desired north bound model, as well as notifications/updates on these model objects to support telemetry and asynchronous updates, alarms and events. Translib should also provide information about what models it supports so that information can be returned in gNMI Capabilities response.
5. The gNMI Server defines the four RPC functions as required by the gNMI Specification: Get, Set, Capabilities and Subscribe.
6. Since the db, non-db and translib clients offer the functionality to support these functions, gNMI only has to translate the paths and object payloads into the correct parameters for the client calls and package the results back intro the response gNMI objects to return to the gNMI Client, which is a straightforward operation, since no additional processing of the data is expected to be done in the gNMI Server itself. When new models are added to Translib, no additional work should be required to support them in gNMI Server.
7. All operations in a Set request are processed in a single transaction that will either succeed or fail as one operation. The db, non-db and translib clients must support a Bulk operation in order to achieve the transactional behavior. gNMI Server then must use this Bulk operation for Set requests.
8. Subscribe operations: Once, Poll and Stream require that the gRPC connection remain open until the subscription is completed. This means many connections must be supported. Subscribe offers several options, such as only sending object updates (not the whole object) which requires support form the db clients. Subscribe also allows for periodic sampling defined by the client. This must be handled in the gNMI agent itself. This requires a timer for each subscribe connection of this type in order to periodically poll the db client and return the result in a Subscribe Response. These timers should be destroyed when the subscription gRPC connection is closed.

###### 3.2.2.5.1 Files changed/added:

    |-- gnmi_server
    |   |-- client_subscribe.go
    |   |-- server.go ------------------- MODIFIED (Handles creation of transl_data_client for GET/SET/CAPABILITY)
    |   |-- server_test.go
    |-- sonic_data_client
    |   |-- db_client.go ---------------- MODIFIED (Common interface Stub code for new functions as all data clients implement common interface functions)
    |   |-- non_db_client.go ------------ MODIFIED (Common interface Stub code for new functions as all data clients implement common interface functions)
    |   |-- transl_data_client.go ------- ADDED    (Specific processing for GET/SET/CAPABILITY for transl data clients)
    |   |-- trie.go
    |   |-- virtual_db.go
    |
    |-- transl_utils -------------------- ADDED
        |-- transl_utils.go ------------- ADDED    (Layer for invoking Translib API's)

###### 3.2.2.5.2 Sample Requests

go run gnmi_get.go  -xpath /openconfig-acl:acl/acl-sets/acl-set[name=MyACL4][type=ACL_IPV4]/acl-entries/acl-entry[sequence-id=1] -target_addr 10.130.84.34:8081 -alsologtostderr -insecure true -pretty

go run gnmi_set.go -replace  /openconfig-acl:acl/acl-sets/acl-set[name=MyACL4][type=ACL_IPV4]/acl-entries/acl-entry=2/actions/config:@openconfig.JSON -target_addr 10.130.84.34:8081 -alsologtostderr -insecure true -pretty

go run gnmi_capabilities.go -target_addr 10.130.84.34:8081 -alsologtostderr -insecure true -pretty 

##### 3.2.2.6 Translib

Translib is a library that will convert the management server requests to Redis ABNF format and vice versa. Translib exposes the following APIs for the management servers to consume. Translib also has the capability to communicate with non DB data providers and get and set data on them.

        func Create(req SetRequest) (SetResponse, error)
            This method is exposed to the management servers to perform a configuration create operation.
            Input parameters:
            SetRequest - Contains the path and payload of the create request
            Returns:
            error - error string
            SetResponse - contains fields like error source, error type etc
        func Update(req SetRequest) (SetResponse, error)
            This method is exposed to the management servers to perform a configuration update operation.
            Input parameters:
            SetRequest - Contains the path and payload of the update request
            Returns:
            error - error string
            SetResponse - contains fields like error source, error type etc
        func Replace(req SetRequest) (SetResponse, error)
            This method is exposed to the management servers to perform a configuration replace operation.
            Input parameters:
            SetRequest - Contains the path and payload of the replace request
            Returns:
            error - error string
            SetResponse - contains fields like error source, error type etc
        func Delete(req SetRequest) (SetResponse, error)
            This method is exposed to the management servers to perform a configuration delete operation.
            Input parameters:
            SetRequest - Contains the path and payload of the delete request
            Returns:
            error - error string
            SetResponse - contains fields like error source, error type etc
        func Get(req GetRequest) (GetResponse, error)
            This method is exposed to the management servers to perform a configuration/Operational get operation.
            Input parameters:
            GetRequest - Contains the path and payload of the get request
            Returns:
            error - error string
            GetResponse - contains fields like payload, error source, error type etc
        func Subscribe(paths []string, q *queue.PriorityQueue, stop chan struct{}) error
            This method is exposed to the management servers to perform a subscribe operation on the operational data.
            Input parameters:
            paths - paths of all the operational data that are being subscribed
            q - queue through which the operational data notifications will exchanged with the management servers
            stop - channel for stopping the subscribe request.
            Returns:
            error - error string
        func GetModels() ([]ModelData, error)
            This method is exposed to get all the supported models using which the user will be able to communicate
            Returns:
            error - error string
            []ModelData - array of ModelData structure containing name, version and organisation of the exposed models

        Translib Structures:
        type ErrSource int

        const(
            ProtoErr ErrSource = iota
            AppErr
        )

        type SetRequest struct{
            Path       string
            Payload    []byte
        }

        type SetResponse struct{
            ErrSrc     ErrSource
        }

        type GetRequest struct{
            Path       string
        }

        type GetResponse struct{
            Payload    []byte
            ErrSrc     ErrSource
        }

        type ModelData struct{
            Name      string
            Org       string
            Ver       string
        }

Translib has the following sub modules to help in the translation of data

1. App Interface
2. Translib Request Handlers
3. YGOT request binder
4. DB access layer
5. App Modules

###### 3.2.2.6.1 App Interface

App Interface helps in identifing the App module responsible for servicing the incoming request. It provides the following APIs for the App modules to register themselves with the App interface during the initialization of the app modules.

        func Register(path string, appInfo *AppInfo) error
            This method can be used by any app module to register itself with the Translib infra.
            Input Parameters:
            path - base path of the model that this app module services
            appInfo - This contains the reflect types of the App module structure that needs to be instantiated for each request, corresponding YGOT structure reflect type to instantiate the corresponding YGOT structure and boolean indicating if this is native app module to differentiate between OpenAPI spec servicing app module and the YANG serving app module.
            Returns:
            error - error string  
        func AddModel(model *gnmi.ModelData) error
            This method can be used to register the models that the app module supports with the Translib infra.
            Input Parameters:
            model - Filled ModelData structure containing the Name, Organisation and version of the model that is being supported.
            Returns:
            error - error string

        App Interface Structures:
        //Structure containing app module information
        type AppInfo struct {
            AppType      reflect.Type
            YGOTRootType reflect.Type
            IsNative     bool
        }

        Example Usages:
        func init () {
            log.Info("Init called for ACL module")
            err := appinterface.Register("/openconfig-acl:acl", 
                    &appinterface.AppInfo{AppType: reflect.TypeOf(AclApp{}),
                    YGOTRootType: reflect.TypeOf(ocbinds.OpenconfigAcl_Acl{}),
                    IsNative: false})
            if err != nil {
                log.Fatal("Register ACL app module with App Interface failed with error=", err)
            }

            err = appinterface.AddModel(&gnmi.ModelData{Name:"openconfig-acl",
                                                        Organization:"OpenConfig working group",
                                                        Version:"1.0.2"})
            if err != nil {
                log.Fatal("Adding model data to appinterface failed with error=", err)
            }
        }

        type AclApp struct {
            path string
            YGOTRoot *YGOT.GoStruct
            YGOTTarget *interface{}
        }

Translib request handlers use the App interface to get all the App module information depending on the incoming path as part of the requests.

###### 3.2.2.6.2 Translib Request Handler

These are the handlers for the APIs exposed by the Translib. Whenever a request lands in the request handler, the handler uses the App interface to get the App Module that can process the request based on the incoming path. It then uses the YGOT binder module, if needed, to convert the incoming path and payload from the request into YGOT structures. The filled YGOT structures are given to the App Modules for conversion to ABNF schema. The Translib also intercts with the DB access layer to start, commit and abort a transaction.

###### 3.2.2.6.3 YGOT request binder

The YGOT request binder module uses the YGOT tools to perform the un-marshalling and validation. YGOT (YANG Go Tools) is an open source tool and it has collection of Go utilities which are used to

  1. generate a set of Go structures for bindings for the given YANG modules at build time
  2. un-marshall the given request into the Go structure objects, and these objects follows the same hierarchical structure defined in the YANG model, and it's simply a data instance tree of the given request, but represented using the generated Go structures
  3. validate the contents of the Go structures against the YANG schema (e.g., validating range and regular expression constraints).
  4. render the Go structure objects to an output format - such as JSON.

This RequestBinder module exposes the below mentioned APIs which will be used to un-marshall the request into Go structure objects, and validate the request  

    func getRequestBinder(uri *string, payload *[]byte, opcode int, appRootNodeType *reflect.Type) *requestBinder
        This method is used to create the requestBinder object which keeps the given request information such as uri, payload, App module root type, and un-marshall the same into object bindings
        Input parameters:
            uri -  path of the target object in the request.
            payload - payload content of given the request and the type is byte array
            opcode - type of the operation (CREATE, DELETE, UPDATE, REPLACE) of the given request, and the type is enum
            appRootNodeType - pointer to the reflect.Type object of the App module root node's YGOT structure object
        Returns:
        requestBinder -  pointer to the requestBinder object instance

    func (binder *requestBinder) unMarshall() (*YGOT.GoStruct, *interface{}, error)
        This method is be used to un-marshall the request into Go structure objects, and validates the request against YANG model schema
        Returns:
        YGOT.GoStruct - root Go structure object of type Device.
        interface{} - pointer to the interface type of the Go structure object instance of the given target path
        error - error object to describe the error if the un-marshalling fails, otherwise nil 

Utilities methods:
These utilities methods provides below mentioned common operations on the YGOT structure which are needed by the App module

    func getParentNode(targetUri *string, deviceObj *ocbinds.Device) (*interface{}, *YANG.Entry, error)
        This method is used to get parent object of the given target object's uri path
        Input parameters:
        targetUri - path of the target URI
        deviceObj - pointer to the base root object Device
        Returns
        interface{} - pointer to the parent object of the given target object's URI path
        YANG.Entry - pointer to the YANG schema of the parent object
        error - error object to describe the error if this methods fails to return the parent object, otherwise nil

    func getNodeName(targetUri *string, deviceObj *ocbinds.Device) (string, error)
        This method is used to get the YANG node name of the given target object's uri path.
        Input parameters:
        targetUri - path of the target URI  
        deviceObj - pointer to the base root object Device
        Returns:
        string - YANG node name of the given target object
        error - error object to describe the error if this methods fails to return the parent object, otherwise nil

    func getObjectFieldName(targetUri *string, deviceObj *ocbinds.Device, YGOTTarget *interface{}) (string, error)
        This method is used to get the go structure object field name of the given target object.
        Input parameters:
            targetUri - path of the target URI
            deviceObj - pointer to the base root object Device
            YGOTTarget - pointer to the interface type of the target object.
        Returns:
        string - object field name of the given target object
        error - error object to describe the error if this methods fails to perform the desired operation, otherwise nil

###### 3.2.2.6.4 DB access layer

The DB access layer implements a wrapper over the go-Redis/Redis package
enhancing the  functionality in the following ways:

    * Provide a sonic-py-swsssdk like API in Go
    * Enable support for concurrent access via Redis CAS (Check-And-Set)
      transactions.
    * Invoke the CVL for validation before write operations to the Redis DB

The APIs are broadly classified into the following areas:

    * Initialization/Close: NewDB(), DeleteDB()
    * Read                : GetEntry(), GetKeys(), GetTable()
    * Write               : SetEntry(), CreateEntry(), ModEntry(), DeleteEntry()
    * Transactions        : StartTx(), CommitTx(), AbortTx()

Detail Method Signature:
    Please refer to the code for the detailed method signatures.

DB access layer, Redis, CVL Interaction:

    DB access       |  PySWSSSDK API   |  RedisDB Call at  | CVL Call at
                    |                  |  at CommitTx      | invocation
    ----------------|------------------|-------------------|--------------------
    SetEntry(k,v)   | set_entry(k,v)   | HMSET(fields in v)|If HGETALL=no entry
                    |                  | HDEL(fields !in v | Validate(OP_CREATE)
                    |                  |  but in           |
                    |                  |  previous HGETALL)|Else
                    |                  |                   | Validate(OP_UPDATE)
                    |                  |                   | Validate(
                    |                  |                   |   DEL_FIELDS) TBD
    ----------------|------------------|-------------------|--------------------
    CreateEntry(k,v)|    none          | HMSET(fields in v)| Validate(OP_CREATE)
    ----------------|------------------|-------------------|--------------------
    ModEntry(k,v)   | mod_entry(k,v)   | HMSET(fields in v)| Validate(OP_UPDATE)
    ----------------|------------------|-------------------|--------------------
    DeleteEntry(k,v)|set,mod_entry(k,0)| DEL               | Validate(OP_DELETE)
    ----------------|------------------|-------------------|--------------------
    DeleteEntryField|    none          | HDEL(fields)      | Validate(
    (k,v)           |                  |                   |   DEL_FIELDS) TBD

###### 3.2.2.6.5 App Modules

TBD

##### 3.2.2.7 Config Validation Library (CVL)

Config Validation Library (CVL) is an independent library to validate ABNF schema based SONiC (Redis) configuration. This library can be used by component like [Cfg-gen](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-config-engine/sonic-cfggen), Translib, [ZTP](https://github.com/Azure/SONiC/blob/master/doc/ztp/ztp.md) etc. to validate SONiC configuration data before it is written to Redis DB.

CVL uses SONiC native YANG models written based on ABNF schema along with various constraints. These native YANG models are simple and very close mapping of ABNF schema. Custom YANG extension (annotation) are used for custom validation purpose. Specific YANG extensions (rather metadata) are used  to translate ABNF data to YANG data. Opensource *libyang* library is used to perform YANG data validation.

###### 3.2.2.7.1 Architecture

![CVL architecture](images/CVL_Arch.jpg)

1. During build time, developer writes YANG schema based on ABNF schema and adds metadata and constraints as needed. Custom YANG extensions are defined for this purpose. 
2. The YANG models are compiled using Pyang compiler and generated YIN files packaged in the build
3. During boot up/initialization sequence YIN schemas generated from SONiC native YANG models are parsed and schema tree is build using libyang API.
4. Application calls CVL APIs to validate the configuration. 
5. ABNF JSON goes through a translator and YANG  data is generated. Metadata embedded in the YANG schema are used to help this translation process.
6. Then YANG data is fed to libyang for performing syntax validation first. If error occurs, CVL returns appropriate error code and details to application without proceeding further.
7. If syntax validation is successful, CVL uses dependent data from translated YANG data or if needed, fetches the dependent data from Redis DB.
8. Finally translated YANG data and dependent data are merged and fed to libyang for performing semantics validation. If error occurs, CVL returns appropriate error code and details to application, else success is returned.
9. Platform validation is specific syntax and semantics validation only performed with the help of dynamic platform data as input.

###### 3.2.2.7.2 Validation types

Config Validator does Syntactic, Semantic validation and Platform Validation as per native YANG schema.

###### 3.2.2.7.2.1 Syntactic Validation

Following are some of the syntactic validation supported by the config validation library

* Basic data type
* Enum
* Ranges
* Pattern matching
* Check for mandatory field
* Check for default field
* Check for number of keys are their types
* Check for table size etc.

###### 3.2.2.7.2.2 Semantic Validation

* Check for key reference existence  in other table
* Check any conditions between fields within same table
* Check any conditions between fields across different table

###### 3.2.2.7.2.3 Platform specific validation

There can be two types of platform constraint validation

###### 3.2.2.7.2.3.1 Static Platform Constraint Validation

* Platform constraints (range, enum, ‘must’/’when’ expression etc.) are expressed in YANG deviation model for each feature.
* Deviation models are compiled along with SONiC feature YANG model and new constraints are added or overwritten in the compiled schema.

###### 3.2.2.7.2.3.2  Dynamic Platform Constraint Validation

###### 3.2.2.7.2.3.2.1 Platform data is available in Redis DB table.

* SONiC YANG models can be developed based on platform specific data in Redis DB. Constraints like ‘must’ or ‘when’ are used in feature YANG by cross-referencing platform YANG models.

###### 3.2.2.7.2.3.2.2 Platform data is available through APIs

* If constraints cannot be expressed using YANG syntax or platform data is available through API, custom validation needs to be hooked up in feature YANG model through custom YANG extension.
* CVL will generate stub code for custom validation. Feature developer implements the stub code. The validation function should call platform API and fetch required parameter for checking constraints.
* Based on YANG extension syntax, CVL will call the appropriate custom validation function along with YANG instance data to be validated. 

###### 3.2.2.7.3 CVL APIs

        //Strcture for key and data in API
        type CVLEditConfigData struct {
                VType CVLValidateType //Validation type
                VOp CVLOperation      //Operation type
                Key string      //Key format : "PORT|Ethernet4"
                Data map[string]string //Value :  {"alias": "40GE0/28", "mtu" : 9100,  "admin_status":  down}
        }

        /* CVL Error Structure. */
        type CVLErrorInfo struct {
                TableName string      /* Table having error */
                ErrCode  CVLRetCode   /* Error Code describing type of error. */
                Keys    []string      /* Keys of the Table having error. */
                Value    string        /* Field Value throwing error */
                Field	 string        /* Field Name throwing error . */
                Msg     string        /* Detailed error message. */
                ConstraintErrMsg  string  /* Constraint error message. */
        }

        /* Error code */
        type CVLRetCode int
        const (
                CVL_SUCCESS CVLRetCode = iota
                CVL_SYNTAX_ERROR /* Generic syntax error */
                CVL_SEMANTIC_ERROR /* Generic semantic error */
                CVL_ERROR /* Generic error */
                CVL_SYNTAX_MISSING_FIELD /* Missing field */
                CVL_SYNTAX_INVALID_FIELD /* Invalid Field  */
                CVL_SYNTAX_INVALID_INPUT_DATA /*Invalid Input Data */
                CVL_SYNTAX_MULTIPLE_INSTANCE /* Multiple Field Instances */
                CVL_SYNTAX_DUPLICATE /* Duplicate Fields  */
                CVL_SYNTAX_ENUM_INVALID /* Invalid enum value */
                CVL_SYNTAX_ENUM_INVALID_NAME /* Invalid enum name  */
                CVL_SYNTAX_ENUM_WHITESPACE /* Enum name with leading/trailing whitespaces */
                CVL_SYNTAX_OUT_OF_RANGE /* Value out of range/length/pattern (data) */
                CVL_SYNTAX_MINIMUM_INVALID /* min-elements constraint not honored  */
                CVL_SYNTAX_MAXIMUM_INVALID /* max-elements constraint not honored */
                CVL_SEMANTIC_DEPENDENT_DATA_MISSING /* Dependent Data is missing */
                CVL_SEMANTIC_MANDATORY_DATA_MISSING /* Mandatory Data is missing */
                CVL_SEMANTIC_KEY_ALREADY_EXIST /* Key already existing. */
                CVL_SEMANTIC_KEY_NOT_EXIST /* Key is missing. */
                CVL_SEMANTIC_KEY_DUPLICATE /* Duplicate key. */
                CVL_SEMANTIC_KEY_INVALID /* Invaid key */
                CVL_NOT_IMPLEMENTED /* Not implemented */
                CVL_INTERNAL_UNKNOWN /*Internal unknown error */
                CVL_FAILURE          /* Generic failure */
        )

1. Initialize() - Initialize the library only once, subsequent calls does not affect once library is already initialized . This automatically called when if ‘cvl’ package is imported.
2. Finish()  - Clean up the library resources. This should ideally be called when no more validation is needed or process is about to exit.
3. ValidateConfig(jsonData string) - Just validates json buffer containing multiple row instances of the same table, data instance from different tables. All dependency are provided in the payload. This is useful for bulk data validation.
4. ValidateEditConfig(cfgData []CVLEditConfigData) - Validates the JSON data for create/update/delete operation. Syntax or Semantics Validation can be done separately or together. Related data should be given as depedent data for validation to be succesful.
5. ValidateKey(key string) - Just validates the key and checks if it exists in the DB. It checks whether the key value is following schema format. Key should have table name as prefix.
6. ValidateField(key, field, value string)  - Just validates the field:value pair in table. Key should have table name as prefix.

##### 3.2.2.8 Redis DB

Please see [3.2.2.6.4 DB access layer](#3_2_2_6_4-db-access-layer)

##### 3.2.2.9 Non DB data provider

Currently, it is up to each App Module to perform the proprietary access
mechanism for the app specific configuration.

## 4 Flow Diagrams

### 4.1 REST SET flow

![REST SET flow](images/write.jpg)

1. REST client can send any of the write commands such as POST, PUT, PATCH or DELETE and it will be handled by the REST Gateway.
2. All handlers in the REST gateway will invoke a command request handler.
3. Authentication and authorization of the commands are done here.
4. Request handler invokes one of the write APIs exposed by the translib.
5. Translib infra populates the ygot structure with the payload of the request and performs a syntactic validation
6. Translib acquires the write lock (mutex lock) to avoid another write happening from the same process at the same time.
7. Translib infra gets the app module corresponding to the incoming uri.
8. Translib infra calls the initialize function of the app module with the ygot structures, path and payload.
9. App module caches the incoming data into the app structure.
10. Translib infra calls appropriate translateWrite function which from the cached ygot structures translates the request into redis ABNF format. It also additionally get all the keys that will be affected as part of this request.
11. App modules returns the list of keys that it wants to keep a watch on along with the status.
12. Translib infra invokes the start transaction request exposed by the DB access layer.
13. DB access layer performs a WATCH of all the keys in the redis DB. If any of these keys are modified externally then the EXEC call in step 26 will fail.
14. Status being returned fram redis.
15. Status being returned from DB access layer.
16. Translib then invokes the processWrite API on the app module.
17. App modules perform writes of the translated data to the DB access layer.
18. DB access layer validates the writes using CVL and then caches them.
19. Status being returned from DB access layer.
20. Status being returned from App Module.
21. Translib infra invokes the commit transaction on the DB access layer.
22. DB access layer first invokes MULTI request on the redis DB indicating there are multiple writes coming in, so commit everything together. All writes succeed or nothing succeeds.
23. Status returned from redis.
24. pipline of all the cached writes are executed from the DB access layer.
25. Status retuned from redis.
26. EXEC call is made to the redis DB. Here if the call fails, it indicates that one of the keys that we watched has changed and none of the writes will go into the redis DB.
27. Status returned from redis DB.
28. Status retuned from DB access layer.
29. Write lock acquired in Step 6 is released.
30. Status returned from the translib infra.
31. REST Status returned from the Request handler.
32. REST response is sent by the rest gateway to the rest client.

### 4.2 REST GET flow

![REST GET flow](images/read.jpg)

1. REST GET request from the REST client is sent to the REST Gateway.
2. REST Gateway invokes a common request handler.
3. Authentication of the incoming request is performed.
4. Request handler calls the translib exposed GET API with the uri of the request.
5. Translib infra gets the app module corresponding to the incoming uri.
6. Translib infra calls the initialize function of the app module with the ygot structures and path. App module caches them.
7. Status retuned from app module.
8. Translib infra invokes translateGet function which translates the path to the Redis keys that needs to be queried.
9. Status returned from app module.
10. Translib infra calls the processGet function on the app module
11. App modules calls read APIs exposed by the DB access layer to read data from the redis DB.
12. Data is read from the Redis DB is returned to the app module
13. App module fills the YGOT structure with the data from the Redis DB and validated the filled YGOT structure for the syntax.
14. App module converts the YGOT structures to JSON format.
15. IETF JSON payload is returned to the Translib infra.
16. IETF JSON payload is returned to the request handler.
17. Response is returned to REST gateway.
18. REST response is returned to the REST client from the REST gateway.

### 4.3 Translib Initialization flow

![Translib Initialization flow](images/Init.jpg)

1. App Module 1 init is being invoked
2. App module 1 calls Register function exposed by Translib infra to register itself with the translib.
3. App Module 2 init is being invoked
4. App module 2 calls Register function exposed by Translib infra to register itself with the translib.
5. App Module N init is being invoked
6. App module N calls Register function exposed by Translib infra to register itself with the translib.

This way multiple app modules initialize with the translib infra during boot up.

### 4.4 gNMI flow

![GNMI flow](images/GNMI_flow.jpg)

1. GNMI requests land in their respective GET/SET handlers which then redirect the requests to corresponding data clients.
2. If user does not provide target field then by default the request lands to the transl_data_client. 
3. Next, the transl_data_client provides higher level abstraction along with collating the responses for multiple paths.
4. Transl Utils layer invokes Translib API's which in turn invoke App-Module API's and data is retrieved and modified in/from  Redis Db/non-DB as required.

### 4.5 CVL flow

![CVL flow](images/CVL_flow.jpg)

Above is the sequence diagram explaining the CVL steps. Note that interaction between DB Access layer and Redis including transactions is not shown here for brevity.

1. REST/GNMI invokes one of the write APIs exposed by the translib.
2. Translib infra populates the ygot structure with the payload of the request and performs a syntactic validation.
3. Translib acquires the write lock (mutex lock) to avoid another write happening from the same process at the same time.
4. Translib infra gets the app module corresponding to the incoming uri.
5. Translib infra calls the initialize function of the app module with the ygot structures, path and payload.
6. Translib infra calls appropriate translateWrite function which from the cached ygot structures translates the request into redis ABNF format. It also additionally get all the keys that will be affected as part of this request.
7. App modules returns the list of keys that it wants to keep a watch on along with the status.
8. Translib infra invokes the start transaction request exposed by the DB access layer.
9. Status being returned from DB access layer.
10. Translib then invokes the processWrite API on the app module.
11. App modules perform writes of the translated data to the DB access layer.
12. DB access layer calls validateWrite for CREATE/UPDATE/DELETE operation. It is called with keys and Redis/ABNF payload.
13. validateSyntax() feeds Redis data to translator internally which produces YANG XML. This is fed to libyang for validating the syntax.
14. If it is successful, control goes to next step, else error is returned to DB access layer. The next step is to ensure that keys are present in Redis DB for Update/Delete operation. But keys should not be present for Create operation.
15. Status is returned after checking keys.
16. CVL gets dependent data from  incoming Redis payload. For example if ACL_TABLE and ACL_RULE is getting created in a single request.
17. Otherwise dependent should be present in Redis DB, query is sent to Redis to fetch it.
18. Redis returns response to the query.
19. Finally request data and dependent is merged and validateSemantics() is called. 
20. If above step is successful, success is returned or else failure is returned with error details.
21. DB Access layer forwards the status response to App mpdule.
22. App module forwards the status response to Translib infra.
23. Translib infra invokes the commit transaction on the DB access layer.
24. Status is returned from DB access layer after performing commit operation.
25. Write lock acquired in Step 3 is released.
26. Final response is returned from the translib infra to REST/GNMI.

## 5 Error Handling

Validation is done at both north bound interface and against database schema. Appropriate error code is returned for invalid configuration.
All application errors are logged into syslog.

## 6 Serviceability and Debug

1. Detailed syslog messages to help trace a failure.
2. Debug commands will be added when debug framework becomes available.
3. CPU profiling enable/disable with SIGUR1 signal.

## 7 Warm Boot Support

Management Framework does not disrupt data plane traffic during warmboot. No special handling required for warmboot.

## 8 Scalability

Describe key scaling factor and considerations

## 9 Unit Test

#### GNMI
1.  Verify that gnmi_get is working at Toplevel module
2.  Verify thet gnmi_get is working for each ACL Table
3.  Verify gnmi_get working for each ACL Rule:
4.  Verify that gnmi_get is working for all ACL interfaces
5.  Verify that gnmi_get is working for each ACL interface name
6.  Verify that gnmi_get fails for non-existent ACL name and type
7.  Verify that TopLevel node can be deleted
8.  Verify that a particular ACL Table can be deleted
9.  Verify that ACL rule can be deleted
10. Verify that ACL table can be created
11. Verify that ACL rule can be created
12. Verify that ACL binding can be created
13. Verify that creating rule on non existent ACL gives error
14. Verify that giving invalid interface number is payload gives error.
15. Verify that  GNMI capabalities is returning correctly.

#### Request Binder (YGOT)
1.  create a ygot object binding for the uri ends with container
2.  create a ygot object binding for the uri ends with leaf
3.  create a ygot object binding for the uri ends with list
4.  create a ygot object binding for the uri ends with leaf-list
5.  create a ygot object binding for the uri which has keys
6.  create a ygot object binding for the uri which has keys and ends with list with keys
7.  validate the uri which has the correct number of keys
8.  validate the uri which has the invalid node name
9.  validate the uri which has the invalid key value
10. validate the uri which has the incorrect number of keys
11. validate the uri which has the invalid leaf value
12. validate the payload which has the incorrect number of keys
13. validate the payload which has the invalid node name
14. validate the payload which has the invalid leaf value
15. validate the uri and the payload with the "CREATE" operation
16. validate the uri and the payload with the "UPDATE" operation
17. validate the uri and the payload with the "DELETE" operation
18. validate the uri and the payload with the "REPLACE" operation
19. validate the getNodeName method for LIST node
20. validate the getNodeName method for leaf node
21. validate the getNodeName method for leaf-list node
22. validate the getParentNode method for LIST node
23. validate the getParentNode method for leaf node
24. validate the getParentNode method for leaf-list node
25. validate the getObjectFieldName method for LIST node
26. validate the getObjectFieldName method for leaf node
27. validate the getObjectFieldName method for leaf-list node

#### DB access layer
1.  Create, and close a DB connection. (NewDB(), DeleteDB())
2.  Get an entry (GetEntry())
3.  Set an entry without Transaction (SetEntry())
4.  Delete an entry without Transaction (DeleteEntry())
5.  Get a Table (GetTable())
6.  Set an entry with Transaction (StartTx(), SetEntry(), CommitTx())
7.  Delete an entry with Transaction (StartTx(), DeleteEntry(), CommitTx())
8.  Abort Transaction. (StartTx(), DeleteEntry(), AbortTx())
9.  Get multiple keys (GetKeys())
10. Delete multiple keys (DeleteKeys())
11. Delete Table (DeleteTable())
12. Set an entry with Transaction using WatchKeys Check-And-Set(CAS)
13. Set an entry with Transaction using Table CAS
14. Set an entry with Transaction using WatchKeys, and Table CAS
15. Set an entry with Transaction with empty WatchKeys, and Table CAS
16. Negative Test(NT): Fail a Transaction using WatchKeys CAS
17. NT: Fail a Transaction using Table CAS
18. NT: Abort an Transaction with empty WatchKeys/Table CAS
19. NT: Check V logs, Error logs
20. NT: GetEntry() EntryNotExist.

#### ACL app (via REST)
1.  Verify that if no ACL and Rules configured, top level GET request should return empty response
2.  Verify that bulk request for ACLs, multiple Rules within each ACLs and interface bindings are getting created with POST request at top level
3.  Verify that all ACLs and Rules and interface bindings are shown with top level GET request
4.  Verify that GET returns all Rules for single ACL
5.  Verify that GET returns all Rules for single ACL
6.  Verify that GET returns Rules details for single Rule
7.  Verify that GET returns all interfaces at top level ACL-interfaces
8.  Verify that GET returns one interface binding
9.  Verify that single or multiple new Rule(s) can be added to existing ACL using POST/PATCH request
10. Verify that single or mutiple new ACLs can be added using POST/PATCH request
11. Verify that single or multiple new interface bindings can be added to existing ACL using POST/PATCH request
12. Verify that single Rule is deleted from an ACL with DELETE request
13. Verify that single ACL along with all its Rules and bindings are deleted with DELETE request
14. Verify that single interface binding is deleted with DELETE request
15. Verify that all ACLs and Rules and interface bindings are deleted with top level DELETE request
16. Verify that CVL throws error is ACL is created with name and type same as existing ACL with POST request
17. Verify that CVL throws error is RULE is created with SeqId, ACL name and type same as existing Rule with POST request
18. Verify that GET returns error for non exising ACL or Rule
19. Verify that CVL returns errors on creating rule under non existent ACL using POST request
20. Verify that CVL returns error on giving invalid interface number in payload during binding creation

#### CVL
1.  Verify that CVL Failure is returned when non-existent key name is given
2.  Verify that CVL Failure is returned when non-existent depenedent configuration is given
3.  Verify that CVL Success is returned when Valid JSON data is provided
4.  Verify that CVL Failure is returned must expression is not satisified
5.  Verify that CVL Failure is returned when out of range values are present.
6.  Verify that CVL Failure is returned when invalid options are given
7.  Verify that CVL Failure is returned when invalid IP address is given
8.  Verify that CVL Failure is returned when extra invalid node is added.
9.  Verify that CVL failure is returned when mandatory node is not provided.
10. Verify that CVL Failure is returned when values exceed custom platform constraints
11. Verify that CVL failure is returned is incorrect number of keys are given
12. Verify that CVL Failure is returned when key value is invalid
13. ValidateCreate - CVL failure is returned if user tries to create list with existing key
14. ValidateCreate - CVL failure is returned if user tries to create list with invalid key
15. ValidateCreate - CVL failure is returned if user tries to create list without mandatory nodes not present
16. ValidateCreate - CVL failure is returned if user tries to create list with REDIS based dependent nodes not present
17. ValidateCreate - CVL failure is returned if user tries to create list with App-module based depedent not present
18. ValidateCreate - CVl failure is reurned if user tries to create list with missing key
19. ValidateCreate - CVL success is returned for valid ABNF json coming from ZTP
20. ValidateCreate - CVL success is returned for valid ABNF json coming from Translib
21. ValidateCreate - CVL success is returned for valid ABNF json coming from cfg-gen
22. ValidateCreate - CVL success is returned for valid ABNF json coming from any other applications
23. ValidateUpdate - CVL failure is returned if user tries to replace an entry with non-existing key
24. ValidateUpdate - CVL failure is returned if user tries to replace an entry without mandotory nodes present
25. ValidateUpdate - CVL failure is returned if user tries to replace an entry with REDIS based dependent nodes not present
26. ValidateUpdate - CVL failure is returned if user tries to replace an entry with App-Module based dependent nodes not present
27. ValidateUpdate - CVL success is returned if user tries to update with data coming from Click CLI
28. ValidateUpdate - CVL success is returned if user tries to update with data coming from Translib
29. ValidateUpdate - CVL success is returned if user tries to update with data coming from cfg-gen
30. ValidateUpdate - CVL success is returned if user tries to update with data coming from any other applications
31. ValidateUpdate - CVL failure is returned for any syntactic error is present in ABNF json
32. ValidateUpdate - CVL failure is returned for any semantic error is present in ABNF json
33. ValidateDelete - CVL failure is returned if user tries to delete node with non-existent key
34. ValidateDelete - CVL failure is returned if user tries to delete leaf that has been referred somewhere else and not found in list of delete keys
35. ValidateDelete - CVl deletes all the dependent nodes


## 10 Internal Design Information

Internal BRCM information to be removed before sharing with the community
