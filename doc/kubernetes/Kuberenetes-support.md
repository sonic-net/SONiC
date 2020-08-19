# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Local mode**' has all container images burned in the image and the systemd manages the features. Under the hood, the systemctl service calls feature specific scripts for start/stop/wait. These scripts ensure all complex dependency rules are met and use `docker start/stop/wait` to manage the containers.

With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode, we term as "**kubernetes mode**". FOr short we use the word "kube" interchangeably.

# Requirements
The following are the high level requirements to meet.
1. Kubernetes mode is optional.
    * Switch could run completely in local mode.
    * The SONiC image could be built with no Kubernetes packages, to save on image size cost.
    * Current set of commands continue to work as before.
    
2. A feature could be managed using local container image (*Local mode*) or kubernetes-provided image (*kubernetes-mode*).
    * A feature could be configured for local or kubernetes mode, with local being default
    * A feature could be switched between two modes.
    * A feature could default to local image, until first kube deployment or upon kube deployment failure.
    
3. A feature's rules for start/stop stays the same, in either mode (local/kubernetes)
    * A set of rules are currently executed through systemd config, and bash scripts.
    * These rules will stay the same, for both modes.
    
4. A feature could be configured as kubernetes-mode only.
    * The switch image need not have this container image as embedded (in other words no local copy).
    * The switch must have systemctl service file and any associated bash scripts for this feature.
    * The service/scripts must ensure all dependencies across other features are met.
    * The feature is still controlled by switch as start/stop/enable/disable.
   
5. A kubernetes deployed container image must comply with guidelines set by SONiC.
   * Required to under go nightly tests to qualify.
   * Kubernetes masters are required to deploy only qualified images.
   * Switch must have a control over a knownlabel that let switch decide, when a manifest can be deployed.
   * Masters control what manifests to deploy and switches/nodes control when to deploy.
   * Containers are expected to call a script at host, on post-start & pre-exit.
       
6. The monit service would monitor the processes transparently across both modes.


# Non requirements
The following are required, but not addressed in this design doc. This would be addressed in one or more separate docs.

1. The feature deployed by kubernetes must have passed nightly tests.
2. The manifest for the feature must honor controls laid by switch as start/stop.
3. The kube managed container image be built with same base OS & tools docker-layers as switch version, to save disk/memory size.
4. The container image deployed must have cleared standard security checks laid for any SONiC images
5. The secured access to master kubernetes nodes and the container registries is ensured.
6. The secrets requied to access container registry is provided by master through secured objects.

    
# Design proposal

## Current behavior
* A feature is managed by systemd.
* A feature has a systemd service file and one or more bash scripts that honor the complex dependency rules set for the feature.
* A feature's change of state could affect the state of other features.
* All the complex dependencies across features are met through systemd service management.

## Proposed behavior at high level
* Maintain the current behavior (*as given above*) in new mode with exception of few updates as explained below.
   * There would not be any changes required in the .service or bash scripts associated with the service, except for few minor updates described below.
   * systemctl gets used in the same way as now.
   
* The systemd would continue to manage features running in both local & kubernetes mode. 
   *  The current set of systemctl commands would continue to manage as before in both modes.
   
* For kubernetes controlled features, master decides on *what to deploy* and node controls the *when to deploy*.
   * The kubernetes manifests are ***required*** to honor `<feature name>_enabled=true` as one of the node-selector labels.
   * The switch/node would create/remove a label to control the start/stop of container deployment by kubernetes.
   * The manifest could add more labels to select the eligible nodes, based on OS version, platform, HWSKU, device-mode, ...
   * The node upon joining the master would create labels for OS version, platform, HWSKU, device-mode, ..., as self description
   * Master would deploy on nodes that match all labels.

*  Replace a subset of docker commands with a new set of "system container" commands

   Currently when systemd intends to start/stop/wait-for a service, it calls a feature specific bash script (e.g. /usr/bin/snmp.sh). This script ensures all the rules are met and eventually calls corresponding docker commands to start/stop/wait to start/stop or wait on the container.
   
   With this proposal, for features configured as managed by kubernetes, start/stop would add/remove label `<feature name>_enabled=true` and, use docker start/stop for locally managed containers. In case of container wait, use container-id instead of name.
   
   To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker kill  --> system container kill
   * docker wait  --> system container wait
   * docker inspect --> system container inspect
   * docker exec    --> system container exec
   
   The bash scripts called by systemd service would be updated to call these new commands in place of docker commands. In addition, any script that call docker commands will be switched to these new commands. A sample could be the reboot scripts, which call `docker kill ...`.
   
   
* The new "system container ..." commands in brief<br/>
   * Container start<br/>
     Do a docker start, if in local mode, else create a label that would let kubelet start.
     
   * Container stop<br/>
      Do a docker stop, if in local mode, else remove the label that would let kubelet stop. If remove label would fail, do an explicit docker stop using the ID.<br/>
      ***Note***: For a kubelet managed containers, an explicit docker stop will not work, as kubelet would restart. That is the reason, we remove the label instead, which instruct kubelet to stop it. But if label remove failed (*mostly because of kubernetes master unreachable*), the command/script that failed to remove, will auto disable kubelet transparently. Hence if label-remove would fail, the explicit docker-stop would be effective.
      
   * Container kill<br/>
      Do a docker kill, if in local mode, else remove the label, then do docker kill on the docker-id.<br/> 
      Please note, in either mode, docker kill will *not* give an opportunity for graceful stop. Hence explicitly call `/etc/sonic/scripts/container_state <name> down` to update the container state.
      
   * Container wait/inspect/exec<br/>
      * For docker wait/inspect/exec, run that command on docker-id instead of name.
      * There is no control on names of the dockers started by kubernetes
      * All the coniners are updated to record their docker-id in State-DB
      * Use the docker-id from STATE-DB, to run the docker commands.
 
* The containers started in either mode, are required to record their start & end as follows in STATE-DB.
  This informtion would be helpful to learn/show the current status and as well the actions to take for start/stop/wait/...
   * On post-start
      * `current_owner = local/kube` 
      * `docker_id = <ID of the container>`
      * `current_owner_update_ts = <Time stamp of change>`
    
     The start.sh of the container (*called from supervisord*) is updated to call `system container state <name> up <kube/local>`, which in turn would do the above update.
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      * `current_owner_update_ts = <Time stamp of change>`
      
     A local monit script is added to supervisord. This script is started by start.sh inside the container under supervisord control. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
     
   The containers that could be managed by kube, ***must*** call the `system container state ...` commands. It would be handy, if all containers follow this irrespective of whether kube may or may not manage it, as that way STATE-DB/FEATURE table could be one place to get the status of all active services. The code that gets i/p fron this table has to be aware of the possibility of not all containers may call it, but it can be assured that all kube manageable containers would have an entry.
   
*  Any auto container-start by kubernetes, is ensured to have been preceeded with service start calls.
   This is accomplished with tracking the container sate in state-DB by hostcfgd (details below).
   
*  When a container exits, the docker-wait command run by systemd would return. This is the same in either mode. Hence, container exit is handled transparently across, both local & kubernetes modes.

*  The hostcfgd helps ensure kube managed containers are started through `systemctl start` only.
   
   When kube managed container starts, there are three possible scenarios.
      1. A local image is running. Hence switching from local to kuberenetes mode is required.
      2. Kube container is running, a manifest update occurred and kubernetes is trying to stop & start.
      3. Kube container is starting when switch is expecting/waiting for kube to start, upon corresponding service start.
      
   In scenario 1 & 2, assistance is required to stop currently running container(s) for this feature, go through service stop and then kick off service start, which would result in scenario 3 above. In scenario 3, the kube container starts & run smoothly
   
     
* The monit could help switch from kubernetes managed to local image, on any failure scenario.

  If a manifest for a feature for a device is removed or corrupted, this would make kubernetes un-deploy its container image. The monit could watch for failures, if configured. When monit notices the kubernetes-managed container being down for a configured period or more, it could make the necessary updates and restart the service, which would transparently start the local container image, if fallback to local image is enabled.
  
*  Systemd service install for new kubernetes features.

   The features that are not part of SONiC image would not have service files in the image and hence not in the switch too. The service files and an entry in FEATURE table are ***required*** to enable a feature run in a switch.
   
   There are multiple ways of accomplishing this requirement. This is analyzed in an independent section below.
   

*  The scripts are provided to join-to/reset-from master.
   *  kube_join
      *  Fetches admin.conf from master through https GET and use that to join
      *  It could be enhanced to help install service files for kubernetes only features.
            
   * kube_reset
      *  Helps reset connection from master.
      *  This could be enhanced to remove the service files for kubernetes-only features.

  
## CONFIG-DB

   ### Kubernetes Server config:
```
   key: "KUBERNETES_MASTER|SERVER"
   IP       = <IP of the kubernetes master cluster> 
   insecure = <https access mode as secured or not; default=False>
   disable  = <False - Enabled to connect to master; True - Disconnects, if already connected; defaults to False>
```

   ### Feature configuration:
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
   ### Kubernetes Server Status:
```
   key: "KUBERNETES_MASTER|SERVER"
   connected      = True/False
   last_update_ts = <seconds since epoch>
```

   ### Feature Status
```
   Key: "FEATURE|<name>"
   current_owner           = local/kube/none/"";   
                                              Empty or none implies that this container is not running
   current_owner_update_ts = <second since epoch>
                                              The timestamp of last current owner update
   docker-id               = ""/"<container ID>";
                                              Set to ID of the container, when running, else empty string or missing field.
   transition_mode = ""/"none"/"kube_pending"/"kube_ready"/"kube_stopped";
                                              Helps dynamic transition to kube deployment and ensure start-service to precede container start.
                                              Details below.
```

   ### Transient info:
   
   The kubernetes label creation requests are directed to API server running in kubernetes master and they are synchronous. These requests would timeout, if the server is unreachable. In this case, these failed requests are persisted in this Transient-info entry. The monitor program would watch and push, at the next time point the server is reachable. The action of explicit disconnect from master, will purge this entry. 
  
   The pending labels are appended into this list in the same order as they arrive. A label to add will look like `<key>=<val>` and label to remove will look like `<key>-`.
   
   The labels push from transient-info being asynchronous, if kubelet service reaches the server before the labels are synced to the master, there could be some unexpected behaviors. Hence anytime, a label can't be added/removed, the kubelet service is disabled. This would not affect the dockers started by kubelet. Later whenever, the monit could push all labels update to master, it would enable the kubelet service. Kubelet now could carry out the updates per labels update.
   
   Any `sudo config kubernetes label ...` command to add/remove a label, would first drain the transient-info, before executing this command. At the end of succesful completion, it ensures that the kubelet service is enabled.
   
   
   
   ```
   key: "KUBE_SERVER|PENDING_LABELS"
   @labels: [<list of labels>]
   ```
   
## State diagram
The following diagram depicts various states and the transitions. 
A state is described as combination of "current_owner" and "transition_mode" in STATE-DB.
A transition happens through an action, influenced by the configuration settings as "set_owner" & "fallback" along with failure-mode-detection enabled or not.

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/state_diagram.png)

Some common scenarios are described below, to help understand the transition in detail.

### Basic info:
   *  At a high level, a feature could switch between local & kube-managed or a feature could be kube managed only.
   *  In either mode, a container start is preceded by systemctl start.
   *  The transition mode
      *  none  - No initiative from kube on this feature
      *  kube_pending - Kube is ready to deploy and waiting for approval from local system.
      *  kube_ready - The local system has approved the deployment and kube can proceed to deploy
      *  kube_running - The kube is currently running the container
      *  kube_stopped - The kube started container has stopped/exited
   *  The kube could run the container only upon approval from the local system
      
### State descriptions
#### state INIT
***Stable*** state<br/>
current_owner = none<br/>
Transition_mode = none

In this state, no container is running. There is not any initiative from kube on this feature.

The current_owner = none implies that the feature's container is *not* running. The transition_mode = none, implies that there is not initiative from kube either.<br/>
This is the initial state upon boot, and it could be reached from other states too. 

The feature remains in this state until `systemctl start`. <br/>
Upon `systemctl start`, the destination state is LOCAL, if set_owner == LOCAL or KUBE with fallback enabled, else KUBE_READY.

The ways to reach this state:
* From any state, the action `systemctl stop` would transition back to this state with set_owner = local
* From state KUBE_READY, if `systemctl stop` is called, it returns back to INIT


####  state LOCAL
***Stable*** state<br/><br/>
current_owner = local<br/>
Transition_mode = none

The container is running using local image, started by docker command.<br/>

This state is reachable only from state INIT,  with either set_owner = local or set_owner = kube && fallback enabled. <br/>

The feature remains in this state until either `systemctl stop` or kube deploys in the case of set_owner = kube or docker exits.<br/>

This state transition back to INIT, upon `systemctl stop` or docker exit.<br/>
This state transition to LOCAL_TO_KUBE, whenever kube deploys (set_owner == Kube).
 

#### state LOCAL_TO_KUBE
***Transient*** state<br/><br/>
current_owner = local<br/>
Transition_mode = kube_pending

The container is running using local image, started by docker command and kube has a pending deployment.<br/>

This state is reachable only from state LOCAL.

The hostcfgd watches for this request, and stop the local service by calling `systemctl stop`. 
This state transitions to state KUBE_PENDING, in normal circumstances. But if set_owner has been reverted to local, it transitions back to INIT.

As hostcfgd initiates the action, this state is very short lived, only for the duration of hostcfgd to notice and local docker to stop.


#### state KUBE_PENDING
***Transient*** state<br/>
current_owner = none<br/>
Transition_mode = kube_pending

In this state no container is running and kube is requesting permission to run.<br/>

This state could be reached in two ways. One from state LOCAL_TO_KUBE, upon hostcfgd stopping the locally running container. Two, when a kube is re-deploying a container (from state KUBE_STOPPED). 

The hostcfgd transitions it into state-KUBE_READY, by ensuring `systemctl stop` is called, transition_mode is set to kube_ready, followed by `systemctl start`. All these steps taken by hostcfgd are synchronous hence this state is pretty short lived.

NOTE: Anytime a `systemctl stop` is issued, if set_owner is reverted to 'local', it would instead transiton back to INIT - a static rule.


#### state KUBE_READY
***Semi-Transient*** state<br/>
current_owner = none<br/>
Transition_mode = kube_ready

In this state, no container is running and local system has approved container deployment by kube.<br/>

This state happens in two ways.  One, from state INIT, when set_owner = kube with no fallback and `systemctl start` takes to this state, and kube is pre-approved to run.<br/>
Two, from state KUBE_PENDING, when hostcfgd intercepts the request by kube to deploy. The hostcfgd sets the transition_mode to kube_ready and call `systemctl start`.<br/>

This state remains until either kube deploys the container or `systemctl stop` is called. 

This state transitions to KUBE_RUNNING, upon successful deployment by kube or it transitions to state INIT, if `systemctl stiop` is called.

When transitioning from state KUBE_PENDING, this mostlikely a short lived state, as this transition is happening due to request from kube. This could be a long lived state, if transitioned from state INIT, as there is no initiative from kube yet. 


#### state KUBE_RUNNING
***Stable*** state<br/>
current_owner = kube<br/>
Transition_mode = kube_running

This is the state where a feature is running with a container deployed by kube, as described in manifest.<br/>
It remains in this state, until either `systemctl stop` or kube un-deploys the container or container exits due to failure.  Irrespective of the trigger, upon docker exit, it transitions to state 6.


#### state KUBE_STOPPED
***Semi-transient*** state<br/>
current_owner = none<br/>
Transition_mode = kube_stopped

The kube deployed container has exited. No container is running.
This is the immediate state, when the kube managed container exits. 
* If this transition is due to `systemctl stop` action
   *  If set_owner = local, it transtions synchronously to state 0
   *  If set_owner = kube, it remains in this state, until `systemctl start` and transitions to state 4.
* If this is due to container exit, which may be unexpected crash or kube un-deploy to handle manifest removed or updated
   * Stays in this state, until either kube deploy and transitions to state 3<br/>
      OR
   * If fallback is enabled and failure mode check is enabled, upon the failure period, the monit transitions it to state 0, from where it would initiate `systemctl start`, which will take it to state 1.

### Common set of scenarios
The common scenarios and the corresponding transition flows are descibed below on scenario basis.

### Default scenario:
None of the features are configured with set_owner = kube. Here it swings between states 0 and 1. The action, `systemctl start` takes from state 0 to 1 and `systemctl stop` reverses it from state 1 to 0.


### Kube managing feature with fallback enabled:
Upon system boot, the state is at 0. The `systemctl start` takes it to state 1 and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, the deployed-container sets transition_mode to kube_pending and gets into sleep-forever. This action by kube transitions to state 2. The hostcfgd interferes, stops both the local container and kube-deployed container, which transitions it to state 3. Upon state 3 reached, the hostcfgd sets mode=kube_ready and initiates `systemctl start`, that transitions to state 4, along with a label to enable kube-deployment. As kube is all ready to deploy, it re-deploys, which takes it to state 5. 

This stays in state-5, until container exits. In normal conditions, the exit is mostlikely because kube un-deployed to handle a manifest update. This takes it to state 6, where transition_mode = kube_stopped. The kubelet re-deploys the container per updated-manifest, which takes it to state-3, where kube container sets the transition_mode to kube_pending and goes to sleep. The hostcfgd notices it, stops the sleeping container, sets the transition_mode to kube_ready and call `systemctl start`, along with label to enable kube deployment and this takes to state 4. Kube re-reploys to reach the stable state-5.
 
Once kube deploys a container, the transition_mode never goes to none and flips between kube controlled modes as 'pending', 'ready', 'running' & 'stopped'. In two ways, it could get reset to none. One, set_owner = local, followed by `systemctl stop`. Two, the container  is not 'running' for a period more than set failmode period and it has fallback enabled, which takes it back to state-0, where mode=none, by monit.

### kube managing feature with fallback disable:
Upon system boot, the state is at 0. The `systemctl start`, sets transition_mode to 'kube_ready' which takes it to state 4 and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, it sets the transition_mode to 'kube-running' and current_owner to 'kube', which is state 5. 

In normal mode, when the corresponding manifest gets updated, kube un-deploys the current running container, this takes it to state 6. It stays in state-6, until kube re-deploys. This goes through the approval process. The deployed container sets transition_mode to 'kube_pending', which is noticed by hostcfgd. The hostcfgd stops the sleeping container, sets the transition_mode to kube_ready and call `systemctl start`, along with label to enable kube deployment and this takes to state 4. Kube re-reploys to reach the stable state-5.

### Switching from kube managed to local mode:
In normal mode, the feature would be in state-5, where kube deployed container is running. When user runs a config command to change the owner to local, it updates `set_owner=local`, call `systemctl stop`. This `systemctl stop` stops the container, which transitions to state-6 and upon reaching state-6, it sets transition_mode to none, which takes it to state=0. The config command, then issues `systemctl start`, which takes it to state-1

### Switching from local to kube managed:
In normal mode, the feature is in state-1. When user runs a config command to switch, it updates `set_owner=kube`, and then call `systemctl stop`. The service stop, will stop the local container, which would take it to state-0. The config command will then call `systemctl start` and that takes it to state-4 or state-1, depending on fallback enabled or not. Rest of the state transition is already explained above.

## Internal commands

### Container start/stop/kill/wait:
   The container start/stop/kill/wait replace the corresponding docker commands. The logic is explained in the flow chart below. The waiting for docker-id will timeout, in case of local image, after N seconds. In case of kubernetes mode, it will wait for ever, as the image deployment depends on many external factors.
     
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_start_stop_wait.png)
   


### container state up/down
   Each container calls this upon start and upon termination. This helps gets the current mode as local/kubernetes, docker-id and the status as running or not.
   Ths following chart depicts the flow.
   
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_state.png)
   
 
### hostcfgd update
   The hostcfgd watches for `kube_request == pending`. When set, stops the service, wait till service stops, set `kube_request=ready` and start the service. This ensures smooth transfer from local mode to kube mode and as well ensure service start precedes container start by kubernetes.
   
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/hostcfgd.png)
   

### monit watches for kubernetes failure
   When a kube managed container stops running for <N> minutes or more, it resets the `kube_request = none` and call for `system service restart`, which enables starting in local mode using local container image, if fallback to local image is enabled.
   
  ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/monit.png)
  
   
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

# Reboot support

## Warm-reboot support
   This [warm-reboot](https://github.com/Azure/SONiC/blob/master/doc/warm-reboot/SONiC_Warmboot.md) support is for updating/restarting with no data-plane disruption. The `/usr/bin/warm_reboot` script is a complex script that does many pre-requisites, kill the containers and eventually call a specific command for reboot. The individual service level support for warm-start lies within its code/implementation-logic. When configured for warm start, upon start-up, the service should be able to acquire its i/p data from all its channels as ever, but instead of pushing it in entirety to the consumer/DB, read the pre-boot data (which is made available in APP-DB), find the diffs as stale/new/update and only push the diffs. With every app doing it and, with some additional complex steps for critical processes like orchagent & syncd, the data plane traffic goes unaffected, except for the changes pushed into ASIC,  which is a normal runtime experience of consuming changes as it happens.
   
   In short if a service supports warmboot, it would continue to support in both local & kube modes transparently. The only updates required would be to replace `docker kill` command with corresponding `system container kill`.
   
   For new features that are not known to warm-reboot script, some hooks could be allowed for registration of feature-custom scripts. This could help with some preparation steps before reboot, like caching some data, setting some DB values, ...
   
## Fast-reboot
   This [fast-reboot](https://github.com/Azure/SONiC/wiki/Fast-Reboot) support aims to help image-udpate and restart, with minimal data-plane traffic disruption. The implementation is similar to warm-reboot, that logic is embedded in the fast-boot script, additional utilities and some tweaks inside the code/logic of individual services that supports. Here again any service level support lies within the internal code/logic.
   
   In short, the summary is as above, the support for fast-boot remains the same, irrespective of service mode as local/kube. The only updates required would be to replace `docker kill` command with corresponding `system container kill`.
   
   For new features that are not known to fast-reboot script, some hooks could be allowed for registration of feature-custom scripts. This could help with some preparation steps before reboot, like caching some data, setting some DB values, ...
   
## reboot
   Regular reboot is supported transparently, as it just restarts the entire system and  goes through systemd, as long as `system container ...` commands are used instead of corresponding `docker ...` commands.
   
   
# Service install for kube managed features

Points to note:
   * The features managed by kube only (*no local image*), will not have a service file locally in the image, hence it needs to be explicitly created/installed.
   * The features that are in hybrid mode as local/kube managed, a service file would indeed be available locally. Yet, an updated image that could be brought in by kube, could demand a tweak in the service file or start/stop/wait scripts, which requires an explicit update.
   * Every kube-managed feature should have an entry in CONFIG-DB, FEATURE table.
   * Any utility that requires the list of all features would refer to this FEATURE table in CONFIG-DB.
   
   
 ## Proposal - 1:
   *  The kubernetes master manages manifests. With a distributed system of multiple masters sharing the same set of manifests, there is likely a single input source for the manifests. The same source could be extended to provide service-file-packages too.
      *  A possible input source is a git repo, cloned locally in each master.
      *  A periodic pull & monitor can identify new/update/delete of manifests, which can be applied transparently.
   *  A single metadata file could be available in the same source that explains all the service packages and optionally additional filters to select elgible target nodes, per package.
   *  Master can make the metadata & service package files available through an https end-point for nodes.
   *  A node can watch for this meta-data file update at master through https end-point, pull the update, look for any new/updated/deleted packages that this node is eligible for, pull down those packages and, install/uninstall the same.
   *  The installation would include .service file, any associated scripts and update of FEATURE table in CONFIG-DB.
        
   
## Proposal - 2:
   Templatize the service file creation.
   
   Most common requirements for any service are,  
   *  This feature/service ***requires*** the presence of one or more other services/features. 
   * One or more other services ***depends*** on this feature
   * pre-start & post-start commands to run at host during service start.
   * pre-stop & post-stop commands to run at host during service stop.
   * warm-reboot prepare commands
      * Commands to run to get this container prepared for warm start
   * fast-reboot prepare commands
      * Commands to help prepare for fast-reboot, pre reboot.
      * ...
      
   These requirements could be provided as an input to a service-create utility, that will create the required  .service, bash scripts and entries in FEATURE table.  
   NOTE: The tools that wipe off & re-create CONFIG-DB, would need to persist this FEATURE table into a transient cache and restore upon re-populating DB. A sample could be `sudo config load_minigraph`.
   
## Proposal - 3:
   Run an external service, to install required service files in each node, explicitly. The scope of this proposal is outside this doc.

# Implementation phases:
The final goal for this work item would be to remove nearly all container images from SONiC switch image and manage all through kubernetes only. The proposal here is to take smaller steps towards this goal.

## Phase 1:
   Support services that meet the following criteria

   * A simple service that has few *required* other services and no service depends on this service.
   * A service that does not affect dataplane traffic
      * Transparent to warm-reboot & fast-reboot.
   * A service with no local image, hence to be managed by kube only
  
Run an config utility with input file that provides the list of required services, and this creates the service file along with bash scripts as required by the service and an update to FEATURE table in CONFIG-DB, with set_owner = kube and no fallback.

## Phase 2:
   Support the services that meet the above criteria, with one deviation as 
   
   * A service with one or more dependent services

## Phase 3:
   A deviation from phase 2.<br/>
   * Support a locally available image between local & kube.
   * Only for features that does not affect dataplane, like snmp, pmon, lldp, ...
   


   
