# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Legacy mode**' has all container images burned in the image. The systemd manages the features and use docker to start/stop the approprite containers. With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests.

# Requirements
The following are the high level requirements to meet.
1. Kubernetes support is optional.
    * Switch could run completely in legacy mode, if desired.
    * Image could be built with no Kubernetes packages, to save image size cost.
    * Current set of commands continue to work as before.
    
2. A feature could be managed using local container image or kubernetes-provided image
    * A feature could be marked for legacy or kubernetes mode, with legacy being default
    * A feature could be switched between two modes.
    * A feature could default to local image, when/where kubernetes image is not available.
    
3. A feature's rules for start/stop stays the same, in either mode (legacy/kubernetes)
    * Set of rules are currently executed through systemd config, start/stop/wait scripts.
    * These rules will stay the same, for both modes
    * As these rules stay the same, this new feature will transparently support warm/fast/cold reboots.
    
4. A feature could be completely kubernetes managed only.
    * The switch image will not have this container image as embedded.
    * The feature is completely controlled by switch as start/stop/enable/disable
    
5. A set of "system service ..." commands will manage the features in both modes.
    * The same set of commands would work transparenly on features, irrespective of their current mode as legacy/kubernetes.
    * This would cover all basic requirements, like start/stop/status/enable/disable/<more as deemed as necessary>
    
6. The monit service would monitor the processes transparently across both modes.



# Non requirements
The following are required, but not addressed in this design doc. This would be addressed in one or more separate docs.

1. The feature deployed by kubernetes must have passed nightly tests.
2. The manifest for the feature must honor controls laid by switch as enable/disable/start/stop.
3. The kube managed container image be built with same base OS & tools docker-layers as switch version.
4. The container image deployed must have cleared standard security checks laid for any SONiC images

    
# Design proposal

## Current behavior
* A feature is managed by systemd.
* A feature has a systemd service file and one or more bash scripts that ensures the complex dependency rules set for the feature.
* A feature's change of state could affect the state of other features.
* All the complex dependencies are met through systemd service management of features.

## Proposed behavior at high level
* Maintain the current behavior given above as the same.
   * There would not be any change required in the .service or bash scripts associated with the service
   * systemctl could be used in the same way as now.
   
* The systemd would continue to manage features running in both lehacy & kubernetes mode.
  
* Replace the current set of systemctl commands for SONiC features, with a new set of "system service ..." commands
   * systemctl start --> system service start
   * systemctl stop --> system service stop
   * systemctl status --> system service status
   
  These new commands would do required diligence as needed and fallback to corresponding systemctl commmands under the hood.
   
* Replace a subset of docker commands with a new set of "system container" commands

   When systemd intends to start/stop/wait for a service, it calls a feature specific bash script (e.g. /usr/bin/snmp.sh). This script ensures all the rules are met and eventually calls corresponding docker commands to start/stop/wait. For features managed by kubernetes, instead, it would need to create/remove a label for start/stop and use docker-id for wait, instead of name. To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker wait  --> system container wait
   * docker inspect --> system container inspect
   * docker exec    --> system container exec 
   The bash scripts would be updatd to call these new commands.
   
   
* The new "system container ..." commands would
   * Do a docker start, if in legacy mode, else create a label that would let kubelet start.
   * Do a docker stop, if in legacy mode, else remove the label that would let kubelet stop.
   * For docker wait/inspect/exec, run that command on docker-id instead of name.
      * There is no control on names of the dockers started by kubernetes
      * Update all dockers to record their docker-id in State-DB
      * Obtain the docker-id for the given name and execute the docker command on that ID.
      
* Switches running completely in legacy mode may use the old systemctl or these new "system container ..." commands, or both.

* Switches running in new mode (*one or more features are marked for kubernetes management*), are required to use only the new set of commands
   * The systemctl commands would still work, but this control on complete switch over would help do a clean design and handle any possible tweaks required.
   
* Each container would mark its state at the start & end of its lifetime, in STATE-DB
   
   * On post-start
      * `current_owner = docker/kube` 
      * `docker_id = <ID of the container>`
      * `current_owner_update_ts = <Time stamp of change>`
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      * `current_owner_update_ts = <Time stamp of change>`
        
      
* The hostcfgd helps switch run time mode from legacy to kubernetes.
    A feature with local container image, but marked for Kubernetes-managed, can run in legacy mode until kubernetes could deploy its image. To be able run by kubernetes, there are few pre-requirements to meet, as listed below. 
      * kubernetes server is configured and enabled.
      * kubernetes master is available and reachable
      * kubernetes manifest for this feature & device is available
      * The corresponding container image could be successfully pulled down.
   The container's start.sh would indicates its availability and blocks. The hostcfgd notices the request and call for a service restart. This would transparently stop the container running local image and restart the kubernetes's downwloaded image.
   
* The monit could help switch from kubernetes managed to local image, on any failure scenario.
      If a manifest for a feature for a device is removed or corrupted, this would make kubernetes un-deploy its container image. If configured so, the monit upon noticing the kubernetes-managed container being down for <N> minutes, could make the necessary marks and restart the service, which would transparently start the local container image.
    
*  container life-cycle updates
      * post-star
   
   
