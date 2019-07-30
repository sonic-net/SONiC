gRPC Network Management Interface (gNMI)
========================================

gNMI Is a gRPC based protocol to manage netowork devices. Sonic provides the gNMI server, while the client must be provided by the user. Although the protocol allows for many encodings and models to be used, our usage is restricted to JSON encoding and openconfig based yang models. All paths and values come from the openconfig models.

Supported Openconfig Models:
-----------------
- Openconfig Interfaces
- Openconfig ACLs
- Openconfig System

Supported RPC Operations:
---------------------
- Get: Get one or more paths and have value(s) returned in a GetResponse.
- Set: Update, replace or delete objects
    + Update: List of one or more objects to update
    + Replace: List of one or objects to replace existing objects, any unspecified fields wil be defaulted.
    + Delete: List of one or more object paths to delete
- Capabilities: Return gNMI version and list of supported models
- Subscribe:
    + Subscribe to paths using either streaming or poll, or once based subscription, with either full current state or updated values only.
        * Once: Get single subscription message.
        * Poll: Get one subscription message for each poll request from the client.
        * Stream: Get one subscription message for each object update, or at each sample interval if using sample mode.
        

Example Client Operations:
--------------------------
Using opensource clients, these are example client operations. The .json test payload files are available here: https://github.com/project-arlo/sonic-mgmt-framework/tree/master/src/translib/test

Get:
----
`./gnmi_get -xpath /openconfig-acl:acl/interfaces -target_addr 127.0.0.1:8080 -alsologtostderr -insecure true -pretty`

Set:
----
-Replace
    `./gnmi_set -replace /openconfig-acl:acl/:@./test/01_create_MyACL1_MyACL2.json -target_addr 127.0.0.1:8080 -alsologtostderr -insecure true -pretty`
-Delete
    `./gnmi_set -delete /openconfig-acl:acl/ -target_addr 127.0.0.1:8080 -insecure`

Subscribe:
----------
-Streaming sample based
`./gnmi_cli -insecure -logtostderr -address 127.0.0.1:8080 -query_type s -streaming_sample_interval 3000000000 -streaming_type 2 -q /openconfig-acl:acl/ -v 0 -target TRANSLIB`
-Poll based
`./gnmi_cli -insecure -logtostderr -address 127.0.0.1:8080 -query_type p -polling_interval 1s -count 5 -q /openconfig-acl:acl/ -v 0 -target TRANSLIB`
-Once based
`./gnmi_cli -insecure -logtostderr -address 127.0.0.1:8080 -query_type o -q /openconfig-acl:acl/ -v 0 -target TRANSLIB`