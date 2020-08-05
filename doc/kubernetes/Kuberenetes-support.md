# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Legacy mode**' has all container images burned in the image and the systemd manages the features. Under the hood, the systemctl service calls feature specific scripts for start/stop/wait. These scripts use docker to start/stop/wait to manage the containers.

With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode, we term as "**kubernetes mode**"

# Requirements
The following are the high level requirements to meet.
1. Kubernetes mode is optional.
    * Switch could run completely in legacy mode, if desired.
    * The SONiC image could be built with no Kubernetes packages, to save on image size cost.
    * Current set of commands continue to work as before.
    
2. A feature could be managed using local container image (*legacy mode*) or kubernetes-provided image (*kubernetes-mode*).
    * A feature could be configured for legacy or kubernetes mode, with legacy being default
    * A feature could be switched between two modes.
    * A feature could default to local image, when/where kubernetes image is not available.
    
3. A feature's rules for start/stop stays the same, in either mode (legacy/kubernetes)
    * A set of rules are currently executed through systemd config, and bash scripts.
    * These rules will stay the same, for both modes
    * As these rules stay the same, this new feature will transparently support warm/fast/cold reboots.
    
4. A feature could be configured as kubernetes-mode only.
    * The switch image will not have this container image as embedded.
    * The feature is still controlled by switch as start/stop/enable/disable
   
5. A kubernetes deployed container image must comply with guidelines set by SONiC
   * Required to undergo nightly tests to qualify
   * Kubernetes masters are required to deploy only qualified images
    
5. A new set of "system service ..." commands are provided to manage the features.
    * The commands would work transparenly on features, irrespective of their current mode as legacy/kubernetes.
    * This would cover all basic requirements, like start/stop/status/enable/disable/<more as deemed as necessary>
    
6. The monit service would monitor the processes transparently across both modes.



# Non requirements
The following are required, but not addressed in this design doc. This would be addressed in one or more separate docs.

1. The feature deployed by kubernetes must have passed nightly tests.
2. The manifest for the feature must honor controls laid by switch as enable/disable/start/stop.
3. The kube managed container image be built with same base OS & tools docker-layers as switch version.
4. The container image deployed must have cleared standard security checks laid for any SONiC images
5. The secured access to master kubernetes nodes and image registry.

    
# Design proposal

## Current behavior
* A feature is managed by systemd.
* A feature has a systemd service file and one or more bash scripts that honor the complex dependency rules set for the feature.
* A feature's change of state could affect the state of other features.
* All the complex dependencies across features are met through systemd service management.

## Proposed behavior at high level
* Maintain the current behavior (*as given above*) in new mode with exception of few updates as explained below.
   * There would not be any changes required in the .service or bash scripts associated with the service, except for few minor updates described below.
   * systemctl gets used in the same way as now, but under new wrapper commands.
   
* The systemd would continue to manage features running in both legacy & kubernetes mode.
  
* The current set of systemctl commands for SONiC features are replaced with a new set of "system service ..." commands
   * systemctl start --> system service start
   * systemctl stop --> system service stop
   * systemctl status --> system service status
   
  These new commands would do required diligence as needed and fallback to corresponding systemctl commmands under the hood.
   
* Replace a subset of docker commands with a new set of "system container" commands

   When systemd intends to start/stop/wait-for a service, it calls a feature specific bash script (e.g. /usr/bin/snmp.sh). This script ensures all the rules are met and eventually calls corresponding docker commands to start/stop/wait. For features managed by kubernetes, it would need to create/remove a label for start/stop instead of docker start/stop and in case of docker wait, use container-id instead of name. To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker wait  --> system container wait
   * docker inspect --> system container inspect
   * docker exec    --> system container exec
   
   The bash scripts called by systemd service would be updated to call these new commands in place of docker commands. 
   
   
* The new "system container ..." commands would
   * Do a docker start, if in legacy mode, else create a label that would let kubelet start.
   * Do a docker stop, if in legacy mode, else remove the label that would let kubelet stop.
   * For docker wait/inspect/exec, run that command on docker-id instead of name.
      * There is no control on names of the dockers started by kubernetes
      * Update all dockers to record their docker-id in State-DB
      * Obtain the docker-id for the given name and execute the docker command on that ID.
 
* The container started in either mode, are required to record their start & end as follows in STATE-DB.
  This informtion would be helpful to learn/show the current status and as well the actions to take for start/stop/wait.
   * On post-start
      * `current_owner = docker/kube` 
      * `docker_id = <ID of the container>`
      * `current_owner_update_ts = <Time stamp of change>`
    
     The start.sh of the container (*called from supervisord*) is updated to call `system container state <name> up <kube/systemd>`, which in turn would do the above update.
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      * `current_owner_update_ts = <Time stamp of change>`
      
     A local monit script is added to supervisord. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
  
* Switches running completely in legacy mode may use the current systemctl commands or these new "system sevice/container ..." commands, or both.

* Switches running in new mode (*one or more features are marked for kubernetes management*), are required to use only the new set of commands
   * The systemctl commands would still work, but this mandate on complete switch over would help do a clean design and handle any possible tweaks required.
   
* The hostcfgd helps switch current runtime mode from legacy to kubernetes.

  There are few requirements to meet for a successful kubernetes deployment for features marked as kube-managed. Hence until the point of deployment, which could be hours/days/months away or never, the feature could run in legacy mode. At the timepoint of successful deployment, the hostcfgd could help switch over from legacy to kubernetes mode, transparently.
  
    Requirements to meet for successful deployment:
      * kubernetes server is configured and enabled.
      * kubernetes master is available and reachable.
      * kubernetes manifest for this feature & device is available.
      * The corresponding container image could be successfully pulled down.
      
   When the container starts, it calls `system container state <name> up kube`. This script makes a request to get activated, if started by kubernetes for the first time. The hostcfgd watch for this request and upon request, do the necessary update and call for service restart. This would transparently stop the container running local image and restart the kubernetes's downwloaded image. From here on this feature runs on kubernetes deployed image.
   
* The monit could help switch from kubernetes managed to local image, on any failure scenario.

  If a manifest for a feature for a device is removed or corrupted, this would make kubernetes un-deploy its container image. The monit could watch for failures. When monit notices the kubernetes-managed container being down for <N> minutes or more, could make the necessary marks and restart the service, which would transparently start the local container image.

  
## CONFIG-DB
   Key: "Feature|<name>"
   set_owner   = systemd/kube;   Defaults to systemd, if this field is absent or empty string
   
