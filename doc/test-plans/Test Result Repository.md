# **Administration of Public SONiC Test Result Repository** 

## **Introduction** 

There has been strong support in the SONiC community for creating a publicly accessible repository of sonic-mgmt test results from tests run against the master SONiC branch. This document describes the requirements for organizing such a repository and is intended to be the basis for setting up the governance and administrative structure to manage this repository. 

## **Organizational Framework** 

The repository is organized around a set of testbeds each of which represents a specific test topology of interest. Each of these testbeds independently runs sonic-mgmt tests aligned with the configured topology. Each testbed is owned by an organization, which is responsible for executing tests on the testbed, and uploading results. The results are stored in the repository, aggregated and made visible to all participants through visual dashboards and programmatic access. 

## **Constraints** 

Given the public nature of the repository and the information sensitivity concerns around organizations that contribute test results, there are several constraints that need to be considered in order to operate this repository. 

● Each testbed is assigned to and owned by a specific participating organization. 

● An organization can only run and upload test results for the testbeds that it owns

## **Administration**

The test result repository is hosted and maintained by UNH-IOL, who will be responsible for

● Onboarding organizations 

● Provision testbeds associated with the onboarded organizations 

● Operate and maintain the data repository 

● Operate and maintain the user interface and API service 

The members of the administrative structure by definition require full knowledge of the organizations and their associations with the testbeds present in the system in order to be able to provision them. However, the administrators do *not* require: 

● Physical or administrative access to the testbeds themselves 

● Access to physically identifiable information regarding the testbeds 

● Visibility into test or device logs 

### **Data Repository Schema**

The repository schema is based on the format already supported for test result repositories at the UNH-IOL. The existing schema may be extended to support additional sonic-mgmt related aspects such as

**Global Metadata**

- SONiC software version string (Mandatory)  
- Commit hash of sonic-buildimage used in the test run (Mandatory)  
- Commit hash of sonic-mgmt instance used in the test run (Mandatory)  
- Topology name: (Such as t1, m0) (Mandatory)  
- Data plane family (Optional) which describes the forwarding architecture used on the testbed DUT  
- TestBatchID   
- ASIC   
- HWSKU string (such as \<Vendor\>-\<Model\>-\<Variant\>-\<PortConfig\>)  
- Platform string (Such as: \<Arch\>-\<Machine\>-\<Machine-Revision\>)   
- DUT Hostname   
- Testbed ID

**Global Metadata Visibility Table**

| Metadata | Logged Out (Public) / Public API | Logged in and part of the organization that owns the results. | Logged in and part of the lab that uploaded the results.  |
| :---- | ----- | ----- | ----- |
| TestBatchID  | ✓ | ✓ | ✓ |
| SONiC software version string  | ✓ | ✓ | ✓ |
| Commit hash of sonic-buildimage used in the test run | ✓ | ✓ | ✓ |
| Commit hash of sonic-mgmt instance used in the test run | ✓ | ✓ | ✓ |
| Topology name | ✓ | ✓ | ✓ |
| Data plane family (optional)  | ✓ | ✓ | ✓ |
| Testbed ID | ✓ | ✓ | ✓ |
| DUT Hostname  |  | ✓ | ✓ |
| ASIC |  | ✓ | ✓ |
| HWSKU string  |  | ✓ | ✓ |
| Platform string  |  | ✓ | ✓ |

Each global metadata has the following sub-fields

- Mandatory: Manufacturer name, Model.   
- It is mandatory to have at least one of these: Software version, Hardware version, Firmware version  
- Optional: Serial number, Inventory id, Description

**Per test data**

- Result: PASS/FAIL/XFAIL/ERROR/SKIP  
- Error signature: The “message” field from the XML schema that is emitted for all unsuccessful tests. (Note that this error field can carry device identifying information, so it  will not be visible with the public test result API)

**Per test data visibility table** 

| Metadata | Logged Out (Public) / Public API | Logged in and part of the organization that owns the results. | Logged in and part of the lab that uploaded the results.  |
| :---- | ----- | ----- | ----- |
| Result | ✓ | ✓ | ✓ |
| Error signature |  | ✓ | ✓ |

# **Public Test Result API**

As shown in the visibility table above, repository access is available through unauthenticated web browsing and a public API offering anonymized test data. While this API enables programmatic integration with external CI/CD pipelines, token generation is restricted to registered users to protect the platform from unwanted automated traffic.

The public API will support the following query operations:

1. Get all available testbed IDs in the repository  
2. For each testbed ID, query public testbed attributes which returns  
   1. Topology name  
   2. Optional attributes such data plane family  
3. Get all available topologies in the repository  
4. For a given topology, get all the available testbeds that use that topology  
5. Get all available test run batches which returns a list of BatchIDs  
6. Get available test run batches in date range which returns a list of BatchIDs  
7. Query information regarding a specific test run batch ID, which returns  
   1. Testbed ID  
   2. Sonic-buildimage commit hash  
   3. Sonic-mgmt build hash  
   4. Software version string  
8. Get all test run IDs for a given Batch ID  
9. Get run data for a run ID, which returns  
   1. Fully qualified name of the test (test name, module name)  
   2. Test result  
      

## **Guidelines for Repository Contributions**

The contribution of test results to the repository are considered to be “data contributions”.  Data contributions may originate from three sources.

Data Sources:

1) UNH Interoperability Lab conducts independent testing and uploads results to the repository.  
2) Vendors self-test and upload the results to the repository.  
3) Virtual testing done in a fully simulated environment may be conducted without hardware and the results uploaded to the repository.

The public repository only exposes results submitted from testbeds running unmodified device and test software. This is ensured by auditing the version and commit hash strings against public SONiC builds.

### **Licensing**

All data contributions made to the repository are subject to the [Community Data License Agreement Permissive 2.0 (CDLA-Permissive-2.0)](https://spdx.org/licenses/CDLA-Permissive-2.0.html). 
