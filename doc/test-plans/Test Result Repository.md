# **Administration of Public SONiC Test Result Repository**

## **Introduction**

There has been strong support in the SONiC community for creating a publicly accessible repository of sonic-mgmt test results from tests run against the master SONiC branch.  This document describes the requirements for organizing such a repository and is intended to be the basis for setting up the governance and administrative structure to manage it.

## **Organizational Framework**

The repository is organized around a set of testbeds, each of which represents a specific test topology of interest.  Each of these testbeds independently runs sonic-mgmt tests aligned with the configured topology.  Each testbed is owned by an organization, which is responsible for executing tests on it and uploading the results.  Test results are stored in the repository, aggregated, and made visible to all participants through visual dashboards and programmatic access.

## **Constraints**

Given the public nature of the repository and contributing organizations' concerns regarding information sensitivity, there are several constraints which need to be considered in order to operate this repository:

- each testbed is assigned to and owned by a specific participating organization;
- an organization may only run and upload test results for testbeds which it owns.

## **Administration**

The test result repository is hosted and maintained by the University of New Hampshire Interoperability Laboratory (UNH-IOL).  The UNH-IOL will be responsible for:

- onboarding organizations;
- provisioning testbeds associated with each onboarded organization;
- operating and maintaining the data repository;
- operating and maintaining the user interface and API service.

The members of the administrative structure by definition require full knowledge of the organizations and their associations with the testbeds present in the system.  This is required in order for testbeds to be fully provisioned.  However, the administrators do *not* require:

- physical or administrative access to the testbeds themselves;
- access to physically identifiable information regarding the testbeds;
- visibility into test or device logs.

### **Data Repository Schema**

The repository schema is based on the format already supported by the UNH-IOL for test result repositories.  The existing schema may be extended to support additional sonic-mgmt related aspects, such as:

**Global Metadata**

- SONiC software version string (Mandatory)
- Commit hash of sonic-buildimage used in the test run (Mandatory)
- Commit hash of sonic-mgmt instance used in the test run (Mandatory)
- Topology name: (Such as t1, m0) (Mandatory)
- Data plane family (Optional) which describes the forwarding architecture used on the testbed DUT
- Test batch ID
- ASIC
- HWSKU string (such as \<Vendor\>-\<Model\>-\<Variant\>-\<PortConfig\>)
- Platform string (Such as: \<Arch\>-\<Machine\>-\<Machine-Revision\>)
- DUT Hostname
- Testbed ID

**Global Metadata Visibility Table**

| Metadata | Logged Out (Public) / Public API | Logged in and part of the organization that owns the results. | Logged in and part of the lab that uploaded the results.  |
| :---- | ----- | ----- | ----- |
| Test batch ID | ✓ | ✓ | ✓ |
| SONiC software version string | ✓ | ✓ | ✓ |
| Commit hash of sonic-buildimage used in the test run | ✓ | ✓ | ✓ |
| Commit hash of sonic-mgmt instance used in the test run | ✓ | ✓ | ✓ |
| Topology name | ✓ | ✓ | ✓ |
| Data plane family (optional)  | ✓ | ✓ | ✓ |
| Testbed ID | ✓ | ✓ | ✓ |
| DUT Hostname  |  | ✓ | ✓ |
| ASIC |  | ✓ | ✓ |
| HWSKU string  |  | ✓ | ✓ |
| Platform string  |  | ✓ | ✓ |

Each DUT described in the testbed metadata *must* have the following attributes:

- Manufacturer name
- Manufacturer model
- At least one of the following attributes:
  - Software version
  - Hardware version
  - Firmware version

Each DUT *may* also have the following attributes:

- Device serial number
- Device inventory ID
- Device description

**Per-Test Data**

Per-test results data will include the following attributes:

- a result, such as PASS, FAIL, XFAIL, ERROR, or SKIP;
- an error signature, such as the “message” field from the XML schema that is emitted for all unsuccessful tests.

The error signature may carry device-identifying information and must not be exposed through public web views or the public test result API.

**Per-Test Data Visibility Table**

| Metadata | Public web views / Public API | Members of the organization that owns the results | Members of the lab that uploaded the results |
| :---- | ----- | ----- | ----- |
| Result | ✓ | ✓ | ✓ |
| Error signature |  | ✓ | ✓ |

## **Public Test Result API**

Public web views are available without authentication.  Public API queries require a token, which only registered users may generate.  The public API offers anonymized test data, with the same field visibility as the public web views shown in the tables above.  It enables programmatic integration with external CI/CD pipelines, while the token requirement helps protect the platform from unwanted automated traffic.

The public API will support the following query operations:

- Get all available testbed IDs in the repository
- Get public attributes for a given testbed ID, including:
  - Topology name
  - Optional attributes such as data plane family
- Get all available topologies in the repository
- Get all available testbeds that use a given topology
- Get all available test run batches (returns a list of batch IDs)
- Get available test run batches within a date range (returns a list of batch IDs)
- Get information for a specific test run batch ID, including:
  - Testbed ID
  - sonic-buildimage commit hash
  - sonic-mgmt commit hash
  - Software version string
- Get all test run IDs for a given batch ID
- Get data for a test run ID, including:
  - Fully qualified test name (test name and module name)
  - Test result

## **Guidelines for Repository Contributions**

Contributions of test results to the repository are considered to be “data contributions”.  Data contributions may originate from three sources:

- the UNH-IOL, which conducts independent testing and uploads test results to the repository;
- vendors, who may self-test and upload test results to the repository;
- test results uploaded as a result of virtual testing conducted in a fully simulated environment without the use of hardware devices.

Only results from testbeds running unmodified device and test software are eligible for public display.  Submitted version strings and commit hashes are checked against public SONiC builds and sonic-mgmt revisions.  These checks verify that the reported identifiers match public versions; they do not by themselves establish that the software used for the test run was unmodified.

### **Licensing**

All data contributions made to the repository are subject to the [Community Data License Agreement Permissive 2.0 (CDLA-Permissive-2.0)](https://spdx.org/licenses/CDLA-Permissive-2.0.html).
