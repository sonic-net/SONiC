# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Local mode**' has all container images burned in the image and the systemd manages the features. Under the hood, the systemctl service calls feature specific scripts for start/stop/wait. These scripts ensure all complex dependency rules are met and use `docker start/stop/wait` to manage the containers.

With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode, we term as "**kubernetes mode**"

# Requirements
The following are the high level requirements to meet.
1. Kubernetes mode is optional.
    * Switch could run completely in local mode, if desired.
    * The SONiC image could be built with no Kubernetes packages, to save on image size cost.
    * Current set of commands continue to work as before.
    
2. A feature could be managed using local container image (*Local mode*) or kubernetes-provided image (*kubernetes-mode*).
    * A feature could be configured for local or kubernetes mode, with local being default
    * A feature could be switched between two modes.
    * A feature could default to local image, until first kube deployment.
    
3. A feature's rules for start/stop stays the same, in either mode (local/kubernetes)
    * A set of rules are currently executed through systemd config, and bash scripts.
    * These rules will stay the same, for both modes.
    * As these rules stay the same, this new mode will transparently support warm/fast/cold reboots.
    
4. A feature could be configured as kubernetes-mode only.
    * The switch image will not have this container image as embedded (in other words no local copy).
    * The switch image must have systemctl service file and any associated bash scripts for this feature.
      - This is required to set the inter-dependency and other rules to meet to start/stop this feature, which includes support to warm/fast/cold reboots.
    * The service/scripts must ensure all dependencies across other features are met.
    * The feature is still controlled by switch as start/stop/enable/disable.
   
5. A kubernetes deployed container image must comply with guidelines set by SONiC.
   * Required to under go nightly tests to qualify.
   * Kubernetes masters are required to deploy only qualified images.
    
5. A new set of "system service ..." commands are provided to manage the features.
    * The commands would work transparenly on features, irrespective of their current mode as local/kubernetes.
    * This would cover all basic requirements, like start/stop/status/enable/disable/<more as deemed as necessary>.
    
6. The monit service would monitor the processes transparently across both modes.


# Non requirements
The following are required, but not addressed in this design doc. This would be addressed in one or more separate docs.

1. The feature deployed by kubernetes must have passed nightly tests.
2. The manifest for the feature must honor controls laid by switch as enable/disable/start/stop.
3. The kube managed container image be built with same base OS & tools docker-layers as switch version, to save disk/memory size.
4. The container image deployed must have cleared standard security checks laid for any SONiC images
5. The secured access to master kubernetes nodes and image registry.
6. The switch should be able to reach container registry through secured channel.

    
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
   
* The systemd would continue to manage features running in both local & kubernetes mode.
  
* The current set of systemctl commands for SONiC features are replaced with a new set of "system service ..." commands
   * systemctl start --> system service start
   * systemctl stop --> system service stop
   * systemctl status --> system service status
   
  These new commands would do required diligence as needed and fallback to corresponding systemctl commmands under the hood.
   
* Replace a subset of docker commands with a new set of "system container" commands

   At present, when systemd intends to start/stop/wait-for a service, it calls a feature specific bash script (e.g. /usr/bin/snmp.sh). This script ensures all the rules are met and eventually calls corresponding docker commands to start/stop/wait. With this proposal, for features configured as managed by kubernetes, instead of docker start/stop, it would need to create/remove a label for start/stop  and in case of docker wait, use container-id instead of name. To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker wait  --> system container wait
   * docker inspect --> system container inspect
   * docker exec    --> system container exec
   
   The bash scripts called by systemd service would be updated to call these new commands in place of docker commands. 
   
   
* The new "system container ..." commands would
   * Do a docker start, if in local mode, else create a label that would let kubelet start.
   * Do a docker stop, if in local mode, else remove the label that would let kubelet stop.
   * For docker wait/inspect/exec, run that command on docker-id instead of name.
      * There is no control on names of the dockers started by kubernetes
      * All the coniners are updated to record their docker-id in State-DB
      * Use the docker-id from STATE-DB, to run the docker commands.
 
* The containers started in either mode, are required to record their start & end as follows in STATE-DB.
  This informtion would be helpful to learn/show the current status and as well the actions to take for start/stop/wait.
   * On post-start
      * `current_owner = local/kube` 
      * `docker_id = <ID of the container>`
      * `current_owner_update_ts = <Time stamp of change>`
    
     The start.sh of the container (*called from supervisord*) is updated to call `system container state <name> up <kube/local>`, which in turn would do the above update.
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      * `current_owner_update_ts = <Time stamp of change>`
      
     A local monit script is added to supervisord. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
  
* Switches running completely in local mode may use the current systemctl commands or these new "system sevice/container ..." commands, or both.

* Switches running in new mode (*one or more features are marked for kubernetes management*), are required to use only the new set of commands
   * The systemctl commands would still work, but this mandate on complete switch over would help do a clean design and handle any possible tweaks required.
   
* The hostcfgd helps switch current runtime mode from local to kubernetes.

  There are few requirements to meet for a successful kubernetes deployment for features marked as kube-managed. Hence until the point of deployment, which could be hours/days/months away or never, the feature could run in local mode. At the timepoint of successful deployment, the hostcfgd could help switch over from local to kubernetes mode, transparently.
  
    Requirements to meet for successful deployment:
    
     * kubernetes server is configured and enabled.
     * kubernetes master is available and reachable.
     * kubernetes manifest for this feature & device is available.
     * The corresponding container image could be successfully pulled down.
      
   When the container starts, it calls `system container state <name> up kube`. This script makes a request to get activated, if started by kubernetes for the first time. The hostcfgd watch for this request and upon request, do the necessary update and call for service restart. This would transparently stop the container running local image and restart the kubernetes's downwloaded image. From here on this feature runs on kubernetes deployed image.
   
* The monit could help switch from kubernetes managed to local image, on any failure scenario.

  If a manifest for a feature for a device is removed or corrupted, this would make kubernetes un-deploy its container image. The monit could watch for failures. When monit notices the kubernetes-managed container being down for a configured period or more, it could make the necessary updates and restart the service, which would transparently start the local container image.

  
## CONFIG-DB

   Kubernetes Server config:
```
   key: "KUBERNETES_MASTER|SERVER"
   IP       = <IP of the kubernetes master cluster> 
   insecure = <https access mode as secured or not; default=False>
   disable  = <False - Enabled to connect to master; True - Disconnects, if already connected>
```

   Feature configuration:
```
   Key: "FEATURE|<name>"
   set_owner   = local/kube;                    Defaults to local, if this field/key is absent or empty string.
   
   fallback_to_local = true/false;              When set_owner == kube and kube does not deploy or failed, run local image.
                                                Default: false.
   
   kube_failure_detection = <N>;                When set_owner == kube and if container is not running for N minutes, it is 
                                                considered as "failed". When "failed", if fall_back_to_local == true, the local 
                                                image would be started and alert logs will be raised. 
                                                A value of 0 implies infinity, implying no failure monitoring.
                                                Default: 0


```
  
## STATE-DB
   Kubernetes Server Status:
```
   key: "KUBERNETES_MASTER|SERVER"
   connected      = True/False
   last_update_ts = <seconds since epoch>
```

   Feature Status
```
   Key: "FEATURE|<name>"
   current_owner           = local/kube/none/"";   
                                              Empty or none implies that this container is not running
   current_owner_update_ts = <second since epoch>
                                              The timestamp of last current owner update
   docker-id               = ""/"<container ID>";
                                              Set to ID of the container, when running, else empty string or missing field.
   transition_mode = ""/"none"/"to_kube"/"kube_ready";
                                              Helps dynamic transition from local to kube.
                                              absent/""/"none", until first kube deployment.
                                              First kube deployment sets to "to_kube" and sleep (does not proceeed).
                                              The hostcfgd stops local, sets to "kube_ready" and restart kube.
                                              On the next start by kube deployed containere, with mode == kube_ready,
                                              it proceeds to run.
```

   Transient info:
   
   The kubernetes label creation requests are directed to API server running in kubernetes master and they are synchronous. These requests would timeout, if the server is unreachable. In this case, these failed requests are persisted in this Transient-DB, which a monitor program could watch and push, at the next time point the server is reachable. The action of explicit disconnect from master, will purge this entry. 
  
   The pending labels are appended into this list in the same order as they arrive. A label to add will look like `<key>=<val>` and label to remove will look like `<key>-`.
   
   ```
   key: "KUBE_SERVER|PENDING_LABELS"
   @labels: [<list of labels>]
   ```
   
## State diagram

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/state_diagram.png)


## Internal commands

### Container start/stop/wait:
   The container start/stop/wait replace the corresponding docker commands. The logic is explained in the flow chart below. 
     
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_start_stop_wait.png)
   


### container state up/down
   Each container calls this upon start and upon termination. This helps gets the current mode as local/kubernetes, docker-id and the status as running or not.
   Ths following chart depicts the flow.
   
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_state.png)
   
 
### hostcfgd update
   The hostcfgd watches the first time kube deployment, by looking for `kube_request == pending` and set it to `ready` followed by system service restart. The restart brings down the docker started container and as well remove the label, which tears down the kubernetes initiated docker, which is currently sleeping upon setting `kube_request=pending`. The subsequent system service start, would add the label, that allows kubernetes deployment, which would proceed w/o blocking as `kube_request==ready`.
   
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/hostcfgd.png)
   

### monit watches for kubernetes failure
   When a kube managed container stops running for <N> minutes or more, it resets the `kube_request = none` and call for `system service restart`, which enables starting in local mode using local container image.
   
  ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/monit.png)
  
### service system start/stop/wait/status/restart

   For features that meets the following criteria, it calls systemctl start/stop/wait. 
   * Features that have local container image
   * Features that don't have local container image, but `kube_request == ready`.
   
   For a kubernetes-only feature, that has not deployed yet, would simulate as follows
   * the start service, will create the label to enable deploymnet
   * the stop service would remove label, that stop any current deployment and block further deployments
   * the wait would block on kube_request to go ready.
   * the status call would print a message that would indicate `pending deployment`
   
   
## CLI commands
  
### config kube server
  
#### IP 
   `sudo config kube server IP <address>`
   
   Sets IP address of the kubernetes master or cluster.
   
#### insecure 
   `sudo config kube server insecure on/off`
   
   This helps allow insecure https access. It is off by default.
   
#### disable 
   `sudo config kube disable on/off`
   
   This helps disable connecting to master. It is off by default.
   
### config kube label
 
#### add
   `config kube label add <key> <value>`
   
   This adds the label `<key>=<value>` to this node. In case of kubernetes master unreachability, it caches it into the transient-DB. Vice versa, when server is reachable, it drains any existing data in transient-DB before adding this new val.
   
#### drop
   `config kube label drop <key>`
   
   This follows same logic as in drop, just that label will be formatted as `<key>-` which is in kubernetes term, remove the label.
   
   
### config kube join/reset

   #### join:
   `config kube join [-f]`
   
   It initiates a connection to master, if the following are true.
   
   * not already connected or forced
   * server IP is configured
   * server is not disabled
      
   #### reset:
   `config kube resert`
      
   It resets connection to master.


### show kubernetes 

#### server
   `show kubernetes server`
   Lists all the configured entries for the server.
   
#### nodes
   `show kubernetes nodes`
   Lists all nodes in the current cluster. This command would work, only when kubernets master is reachable.

#### pods
   `show kubernetes pods`
   Lists all nodes in the current cluster. This command would work, only when kubernets master is reachable.

#### status
   `show kubernetes status`
   It describes the kubernetes status of the node.

