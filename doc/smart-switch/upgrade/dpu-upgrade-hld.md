# Independent DPU Upgrade #

## Table of Content

### 1. Revision

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 01/23/2025 | Dawei Huang | Initial version    |

### 2. Scope

This document describes the high-level design of the sequence to independently upgrade a SmartSwitch DPU with minimal impact to other DPUs and the NPU, through GNOI API.

#### 2.1 Depenedencies
The individual DPU upgrade process depends on the following components:
* Healthy DPU and NPU SONiC Host Services: The system service running on DPU that interact with the OS to execute the upgrade process.
* Healthy DPU and NPU SONiC GNMI: The GNOI service running on the DPU, which is responsible for handling GNOI requests for upgrades.

In other words, the DPU upgrade process cannot be used to recover a DPU or NPU that is in a nonresponsive state. The DPU upgrade process assumes that the DPU and NPU are healthy and running. Manual intervention or other recovery process may be required to recover a DPU or NPU that is in a nonresponsive state.

### 3. Definitions/Abbreviations

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| DPU   | Data Processing Unit                      |
| gNMI  | gRPC Network Management Interface         |
| gNOI  | gRPC Network Operations Interface         |
| NPU   | Network Processing Unit                   |
| ASIC  | Application Specific Integrated Circuit   |
| HA	| High Availability                         |

### 4. Overview
Smart Switch offers comprehensive network functionality similar to traditional devices, combined with the flexibility and scalability of cloud services. It includes one switch ASIC (NPU) and multiple DPUs, with DPU ASICs connected only to the NPU, and all front panel ports linked to the NPU. DPUs are mostly independent SONiC devices, with their own SONiC image, and are connected to the NPU through a high-speed interface. Due to resource constraint on the DPU, some SONiC services are offloaded to the NPU, such as Database, GNMI and HA.

One use case for the DPUs is to provide additional capacity for invidividual customers. As such, SONiC should supports the ability to independently manage each DPU, with minimal impact to the network, the NPU and other DPUs. This document describes the high-level design of the sequence to independently upgrade a SmartSwitch DPU with minimal impact to other DPUs and the NPU, through GNOI API.

<img src="https://www.mermaidchart.com/raw/4fa5921d-23e4-4956-8fe6-bf8db7869943?theme=light&version=v0.1&format=svg" alt="Smart Switch Architecture" width="80%">

### 5. Goals and Requirements

The main goals and requirements of the DPU upgrade process are:
1. The upgrade process should have minimal impact on the network, the NPU and other DPUs.
2. External client should be able to drive the DPU upgrade process through the gNOI API.
3. The upgrade process should be able to upgrade the offloaded containers on the DPU.

Non-goals:
1. DPU fatal error recovery: This feature does not address the recovery of the DPU from fatal errors, say the DPU is in a nonresponsive state and requires a new image be loaded from BIOS. Such a recovery should be address in a different process.
2. Bootstrapping GNMI: The upgrade process relies on the GNMI service running on the DPU and NPU. The bootstrapping of the GNMI service is out of scope of this document.
3. DPU and NPU image compatibility: The upgrade process assumes that the DPU and NPU images are compatible with each other. It is up to the client to ensure the compatibility of the images.
4. Eliminating human intervention: The upgrade process may require human intervention to resolve issues that cannot be handled automatically, in particular, when both the upgrade process fails and the rollback process fails, the system may be left in an inconsistent state that requires manual intervention.

### 6. Architecture

The key components involved in the DPU upgrade process are:
* External Client: The client that drives the DPU upgrade process through the gNOI API.
* DPU: The Data Processing Unit that needs to be upgraded.
  * DPU Host Services: The system service running on DPU that interact with the OS to execute the upgrade process.
  * DPU GNMI Server: Running inside the GNMI container, it is responsible for handling GNOI requests for upgrades.
  * Offloader: Running a GNOI Client, it is responsible for upgrading and monitoring the offloaded containers on the NPU.
* NPU: The Network Processing Unit that is connected to the DPU.
  * Offloaded Containers: The containers that are offloaded from the DPU to the NPU, e.g. Database, GNMI and HA.
  * NPU GNMI Server: Running inside the GNMI container, it is responsible for handling GNOI requests for managing the offloaded containers.
  * GNMI/GNOI Splitter: Running inside the GNMI container, it is responsible for splitting the GNMI and GNOI requests and forwarding them to the corresponding GNMI/GNOI servers, i.e. GNOI requests to DPU GNMI Server and GNMI requests to NPU GNMI Server.

<img src="https://www.mermaidchart.com/raw/bb62a98d-3505-4722-92a2-81113b1040cf?theme=light&version=v0.1&format=svg" alt="DPU Upgrade Architecture" width="80%">

### 7. High-Level Design

#### 7.1. Upgrade Sequence

Here are the detailed steps of the DPU upgrade process. The upgrade process is initiated by the external client through the gNOI API.

1. **Prepare Relevant Images**: The external client downloads the new SONiC image and the offloaded container images from the image repository. The images are then transferred to the DPU and NPU respectively.
   * Description:
     * Deploy the new SONiC image to the DPU.
	 * Activate the new SONiC image on the DPU.
	 * (Offloader) Deploy the new offloaded container images to the NPU.
   * GNOI API:
     * 'System.SetPackage'
	 * 'OS.Activate'
	 * 'Containerz.Deploy'
   * Rollback:
     * Rollback the new SONiC image on the DPU. Client issues 'OS.Activate' with the old SONiC image.
	   * (optional) Rollback the new offloaded container images on the NPU. Client issues 'Containerz.RemoveImage' with the old container images.

2. **Upgrade DPU**: The external client triggers the DPU upgrade process.
   * Description:
	 * Reboot the DPU to apply the new SONiC image.
       * Check the reboot status of the DPU.
	 * Update the offloaded containers on the NPU.
	   * Confirm the new container images on the NPU.
	   * Stop the old offloaded containers.
	   * Start the new offloaded containers.
   * GNOI API:
	 * 'System.Reboot'
	 * 'System.RebootStatus'
	 * 'Containerz.ListImage'
	 * 'Containerz.StopContainer'
	 * 'Containerz.StartContainer'
   * Rollback:
	 * Rollback the new SONiC image on the DPU.
	   * Client issues 'OS.Activate' with the old SONiC image.
       * If the DPU does not have the old SONiC image, the client should use 'System.SetPackage' to deploy the old SONiC image.
	   * Client issues 'System.Reboot' to reboot the DPU.
	   * Client issues 'System.RebootStatus' to check the reboot status of the DPU.
	 * Rollback the new offloaded container images on the NPU.
	   * Client issues 'Containerz.ListImage' to confirm the old container images on the NPU.
	     * If not, client issues 'Containerz.Deploy' with the old container images.
	   * Client issues 'Containerz.StopContainer' to stop the current offloaded containers.
	   * Client issues 'Containerz.StartContainer' to start the old offloaded containers.
     * (optional) Rollback the new offloaded container images on the NPU. Client issues 'Containerz.RemoveImage' with the old container images.

The upgrade sequence is shown in the following diagram:

<img src="https://www.mermaidchart.com/raw/7797d125-08e3-4f00-9bfc-8e3cfa5757a0?theme=light&version=v0.1&format=svg" alt="DPU Upgrade Sequence" width="100%">

3. **Verify the upgrade result**
   * Description:
	 * Check the DPU SONiC version.
	 * Check the offloaded container versions on the NPU.
   * GNOI API:
	 * 'OS.Verify'
	 * 'Containerz.ListContainer'
   * Rollback:
	 * Rollback the new SONiC image on the DPU.
	   * Client issues 'OS.Activate' with the old SONiC image.
	   * Client issues 'System.Reboot' to reboot the DPU.
	   * Client issues 'System.RebootStatus' to check the reboot status of the DPU.
	 * Rollback the new offloaded container images on the NPU.
	   * Client issues 'Containerz.ListImage' to confirm the old container images on the NPU.
	     * If not, client issues 'Containerz.Deploy' with the old container images.
	   * Client issues 'Containerz.StopContainer' to stop the current offloaded containers.
	   * Client issues 'Containerz.StartContainer' to start the old offloaded containers.
     * (optional) Rollback the new offloaded container images on the NPU. Client issues 'Containerz.RemoveImage' with the old container images.

#### 7.2. GNMI/GNOI Splitter

Per smartswitch architecture, the GNMI service is offloaded to the NPU due to DPU resource constraints. But the GNOI service is still running on the DPU. The GNMI/GNOI Splitter is responsible for splitting the GNMI and GNOI requests and forwarding them to the corresponding GNMI/GNOI servers, i.e. GNOI requests to DPU GNMI Server and GNMI requests to NPU GNMI Server.

<img src="https://www.mermaidchart.com/raw/3e126a79-0049-4051-ba30-a18251829504?theme=light&version=v0.1&format=svg" alt="Mermaid Chart" width="80%">

#### 7.3. Offloader

One major challenge of the DPU upgrade is that several DPU containers, such as Database, GNMI and HA are offloaded to the NPU. The offloader is a service on the DPU that provides *local* management access to the offloaded containers on NPU. For example, the offloader can start, stop, deploy and list the offloaded containers on the NPU.

##### 7.3.1. Offloader Architecture.

The offloader consists of a single GNOI client connected to the GNOI server on NPU, through which it manages the offloaded containers on the NPU. To facilitate remote management of offloaded containers, we will also implement the containerz module in GNOI service.

<img src="https://www.mermaidchart.com/raw/eed55057-8dda-4f1b-8bf9-3046e2910497?theme=light&version=v0.1&format=svg" alt="Offloader Architecture" width="80%">

##### 7.3.2. Offloader Services.

The offloader can perform the following management operations to the offloaded containers on the NPU:
* Start a container on the NPU.
* Stop a container on the NPU.
* List the containers on the NPU.
* List the container images on the NPU.
* Deploy a container image to the NPU.
* Remove a container image from the NPU.

The offloader provides a command line interface to interact with the offloaded containers on the NPU.
* Get the status of the offloaded container.
* Start the offloaded container.
* Stop the offloaded container.
* List the offloaded containers.
* List the container images on the NPU.
* Deploy a container image to the NPU.

The offloader will also provide a mode to automatically manage the offloaded containers on the NPU:
* On services start, check the health of the offloaded containers on the NPU.
  * If the offloaded containers are not running, start them.
  * If the offloaded containers have different versions from the DPU SONiC, upgrade them.
* When the service is running, subscribe to lifetime events of the offloaded containers on the NPU.
  * If the offloaded containers are stopped, start them.
  * If the offloaded containers have different versions from the DPU SONiC, upgrade them.

### 8. GNOI Specific Features

#### 8.1. `System.SetPackage` RPC.

##### 8.1.1. Path Validation
The `System.SetPackage` RPC is used to deploy a new SONiC image to the DPU. This RPC allowed the client to transfer a new SONiC image to a client specific path on the DPU. Without proper validation, this can lead to a security risk that the client can transfer a malicious file to sensitive paths on the DPU. The `System.SetPackage` RPC should validate the path to ensure that the file is transferred to a client specific path on the DPU. Any path specified by the client should satisfy either of the following conditions:

1. The path is all writable directories, such as `/tmp`, `/var/tmp`, etc.
2. The path is under the `/lib/firmware` directory, which is a common location for firmware files.


### 9. Configuration

The main goal of the feature is to provide an API for external clients to drive the DPU upgrade process, which is currently driven manually or through host agent via command line interface `sonic-installer`. The feature does not require any new configuration change.

### 10. CLI

As mentioned above, the offloader provides a command line interface to interact with the offloaded containers on the NPU. The offloader CLI commands are:
* `offloadctl status <container>`: Get the status of the offloaded container.
* `offloadctl start <container>`: Start the offloaded container.
* `offloadctl stop <container>`: Stop the offloaded container.
* `offloadctl list`: List the offloaded containers.
* `offloadctl list-image`: List the container images on the NPU.
* `offloadctl deploy <image>`: Deploy a container image to the NPU.

### 11. Implementation Roadmap

The implementation consists of new features in different SONiC components.

#### 11.1. SONiC Host Services

The SONiC host services are responsible for interacting with the OS to execute the upgrade process, on behalf of the GNOI server inside the containerized environment. The host services should provides the following:
* Service for managing the DPU SONiC image.
  * Download the new SONiC image.
  * Install the new SONiC image.
  * Activate the new SONiC image.
  * List the SONiC images on the DPU.
* Service for managing the offloaded container images on the NPU.
  * Deploy the new container images.
  * List the container images on the NPU.
  * List the containers on the NPU.
  * Start a container on the NPU.
  * Stop a container on the NPU.

#### 11.2. SONiC GNMI
This is the GNOI service running on the DPU, which is responsible for handling GNOI requests for upgrades. The GNMI service should provide the following:
* `OS` module.
  * `Activate` RPC. (new)
  * `Verify` RPC (new)
* `System` module.
  * `SetPackage` RPC (new)
  * `Reboot` RPC. (implemented)
  * `RebootStatus` RPC. (implemented)
* `Containerz` module.
  * `Deploy` RPC. (new)
  * `ListImage` RPC. (new)
  * `ListContainer` RPC. (new)
  * `StartContainer` RPC. (new)
  * `StopContainer` RPC. (new)

#### 11.3. SONiC GNMI Splitter
The GNMI/GNOI Splitter is responsible for splitting the GNMI and GNOI requests and forwarding them to the corresponding GNMI/GNOI servers, i.e. GNOI requests to DPU GNMI Server and GNMI requests to NPU GNMI Server. The implementation will be in the NPU GNMI container.

#### 11.4. SONiC Offloader
This will create a new repository. The implementation will includes:
* GNOI Client interface.
* Command line interface for offloader.
* Redis interface for monitoring the offloaded containers on the NPU.

### 12. Testing Requirements/Design

#### 12.1. Unit Tests
Individual units test will be written for each feature added to `sonic-host-services`, `sonic-gnmi` and `sonic-offloader`.

#### 12.2. Integration Tests for GNOI API
For each GNOI API added, integration tests will be added to `sonic-mgmt` to test stress the API with different outputs.

#### 12.3. Integration tests for individual component.
Integration tests are also needed for the individual components.
* Generic switch upgrade test.
  * with `System.SetPackage`, `OS.Activate`, `System.Reboot`, `System.RebootStatus` and `OS.Verify` RPCs.
  * Test the upgrade process with different SONiC images.
* GNOI/GNMI Splitter test (smartswitch specific).
  * Test the splitter with different GNMI and GNOI requests.
* Offloader test (smartswitch specific).
  * with `Containerz.*` RPCs.
  * Test offloader can start, stops, deploy and list the offloaded containers on the NPU.

#### 12.4. Full Integration tests
Full integration tests will be added to `sonic-mgmt` to test the individual DPU upgrade process.

### 13. Open Items

#### 13.1. OS Image Cleanup
GNOI does not have a service for cleaning up non-current images. This is potentially a useful feature to clean up old images that are no longer needed.

#### 13.2. Post Upgrade Actions
Formally supports post-upgrade actions, such as running a script after the upgrade process is completed.