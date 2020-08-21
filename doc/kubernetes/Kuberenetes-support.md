# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Local mode**' has all container images burned in the image and the systemd manages the features. Under the hood, the systemctl service calls feature specific scripts for start/stop/wait. These scripts ensure all complex dependency rules are met and use `docker start/stop/wait` to manage the containers.

With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode, we term as "**kubernetes mode**". For short we use the word "kube" interchangeably.

# A Brief on Kubernetes
  
  ***Disclaimer**: This brief on kubernetes is only to give some basics on these terms, so as to help with  reading this doc. For full & official details, please refer to [kubernetes documentation](https://kubernetes.io/docs/home/)
  
  This is a well known open source platform for managing containerized loads. To describe kubernetes in simple terms, it is a management engine, which can deploy applications in nodes, scale it, manage it, roll updates that is customizable per app. The common use case, is to deploy applications in a desired scale among the available nodes, that takes into account the needs of app and deploy at nodes where the needs can be met. If a node would crash or the environment changes or app requires an update, and many more, the engine manages it all transparently.
  
  ## Key terms:
  The key terms are described very briefly in simple terms, so as to familiarize the reader with these terms, as they are used in this doc. For in-depth details, please look up in 
   * Kubernetes master<br/>
      This is the brain behind the kubernetes system. Comprised of many deamons, which includes API server, scheduler, controller, kubelet, proxy, etcd, ...
      
   * HA kubernetes-master / kubernetes master cluster:<br/>
      Being the brain behind, the availability become highly critical. Hence often, multiple instances of the master are run as single entity. This cluster is configured behind a VIP (Virtual IP), which is often serviced by a Load Balancer. The access to VIP would direct to any of the masters in the cluster, that are active.
      
   * etcd<br/>
      This is the DB used by master for all its data. In a cluster, it is clustered across as replicated with a master/slaver relationship, managed by kubernetes as a multi-node etcd cluster.
      
   * node<br/>
      The nodes that can run apps, join the master. The master deploys apps in nodes, such that app's needs are met. A node may run single/none/multiple copies of same app. Master watch the health of the apps and take action on failure.
      
   * pods<br/>
      This is the unit of kubernetes deploymenet. A pod could run one or more containers. A manifest describes a pod.
      
   * manifest<br/>
      A manifest describes the pod as below. 
        * Assigns a name
        * The kind of object
        * count of replicas
        * List of containers
        * Description of each container
          * Image URL
          * mounts
          * runtime args
          * environment variables
          ...
        * Node selector labels
        ...

   * Node selector labels<br/>
      A label is a `<key>=<value>` pair. A manifest may carry multiple labels. Each node that joined, can be described with multiple labels. A pod will be deployed only in nodes, where all the labels of the manifest are matched with the labels on the node. A node may have more labels. In short of full/subset of node labels should completely match with all labels on the manifest. This leads to the term "eligible nodes", where node labels matching is one of the many requirements to meet, for deployment of a pod.
      
   * Daemonset<br/>
      A deamonset is a special kind of pod. Normally a pod is deployed in one or more nodes to meet the count of replicas required as per manifest. But deamonset is different, that a daemonset is deployed as only one replica per node in all nodes that matches all labels and more.
           
## Basic on `how` for a daemonset:
  1) Set up a master cluster
  2) Configure nodes with VIP of the cluster
  3) Nodes join the master, whenever they are ready
  4) The container images are stored in container registry, like Azure Container Registry
  5) Manifests are applied in master.
     For a better control, manifests can be checked into a github repo.
     A tool can watch for updates and apply manifest.
  6) For any new manifest, the master applies to all eligible nodes.
      * The node downloads the container image from URL in the manifest
      * The container is started in the node with runtime setup as described in manifest
  7) For any manifest update, the master does the following on all eligible nodes
      * Stop the currently running pod
      * Follow the same steps as above for the new manifest.
     
  
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
    * The feature is still controlled by systemd as start/stop/enable/disable.
   
5. A kubernetes deployed container image must comply with guidelines set by SONiC.
   * Required to under go nightly tests to qualify.
   * Kubernetes masters are required to deploy only qualified images.
   * Switch must have a control over a known label that let switch control, when a manifest can be deployed.
   * Masters control what manifests to deploy and switches/nodes control when to deploy.
   * Containers are expected to call a script at host, on post-start & pre-exit, that record their state.
       
6. The monit service would monitor the processes transparently across both modes.


# Mandates on deployed images
The following are required, but external to then node/switch, hence not addressed in this design doc. 
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
   
* The systemd would continue to manage features running in both local & kubernetes mode. 
   *  The current set of systemctl commands would continue to manage as before in both modes.
   
* For kubernetes controlled features, master decides on *what to deploy* and node controls the *when to deploy*.
   * The kubernetes manifests are ***required*** to honor `<feature name>_enabled=true` as one of the node-selector labels.
   * The switch/node would create/remove a label to control the start/stop of container deployment by kubernetes.
   * The manifest could add more labels to select the eligible nodes, based on OS version, platform, HWSKU, device-mode, ...
   * The node upon joining the master would create labels for OS version, platform, HWSKU, device-mode, ..., as self description
   * Master would deploy on nodes that match *all* labels.

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
      * All the containers are required to record their docker-id in State-DB
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
      
     A local monitor script is added to supervisord. This script is started by start.sh inside the container under supervisord control. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
     
   The containers that could be managed by kube, ***must*** call the `system container state ...` commands. It would be handy, if all containers follow this irrespective of whether kube may or may not manage it, as that way STATE-DB/FEATURE table could be one place to get the status of all active services. The code that gets i/p fron this table has to be aware of the possibility of not all containers may call it, but it can be assured that all kube manageable containers would have an entry.
   
*  The hostcfgd helps switch between local and kube modes.
   
   When set_owner is switched to kube while running in local mode, it creates the label to enable kube-deploy and whenever kube deploys asynchronously, it stops the local container, so as to help kube deployed container take over. Vice versa, when switching to local, while running in kube mode, it calls `system container stop`, which stops the running kube deployed container, followed by call to `system container start` which starts the local container. The entire switching from kube to local is synchronous.
 
     
* A daemon could help switch from kubernetes to local if deploy would not happen for a period.

  When a feature remain pending for kube deployment, with no local conatainer running, a daemon could watch and switch over to local, if configured so. 
  
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
   
   fallback_to_local = true/false;              When set_owner == kube, it could fallback to local image, when/where kube deployment is not active.
                                                Default: false.
   
   kube_failure_detection = <N>;                When set_owner == kube and if container is not running for N minutes, it is 
                                                considered as "failed". The alert logs will be raised.
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
   transition_mode = ""/"none"/"kube_pending"/"kube_ready";
                                              Helps dynamic transition to kube deployment.
                                              Details below.
```

   ### Transient info:
   
   The kubernetes label creation requests are directed to API server running in kubernetes master and they are synchronous. These requests would timeout, if the server is unreachable. In this case, these failed requests are persisted in this Transient-info entry. A monitoring script would watch and push, at the next time point the server is reachable. The action of explicit disconnect from master, will purge this entry. 
  
   The pending labels are appended into this list in the same order as they arrive. A label to add will look like `<key>=<val>` and label to remove will look like `<key>-`.
   
   The labels push from transient-info being asynchronous, if kubelet service reaches the server before the labels are synced to the master, there could be some unexpected behaviors. Hence anytime, a label can't be added/removed, the kubelet service is disabled. This would not affect the dockers started by kubelet. Later whenever, all the labels were synced to master, the kubelet service will be enabled. Kubelet now could carry out the updates per updated labels.
   
   Any `sudo config kubernetes label ...` command to add/remove a label, would first drain the transient-info, before executing this command. At the end of succesful completion, it ensures that the kubelet service is enabled.
   
   
   
   ```
   key: "KUBE_SERVER|PENDING_LABELS"
   @labels: [<list of labels>]
   ```
   
## State diagram
The following diagram depicts various states and the transitions. 

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/state_diagram.png)

Some common scenarios are described below, to help understand the transition in detail.

### Basic info:
   *  At a high level, a feature could switch between local & kube-managed or a feature could be kube managed only.
   *  In either mode, a container start is preceded by systemctl start.
   *  The kube mode
      *  none  - No initiative from kube on this feature
      *  kube_pending - Kube is ready to deploy and waiting to proceed
      *  kube_ready - kube container can proceed to run 
   *  At anytime only one container from any mode can be active
      
### State descriptions
#### state INIT
***Stable*** state<br/>
system state = down
current_owner = none<br/>
kube_mode = any or N/A

In this state, no container is running. The systemd has stopped the feature.

The current_owner = none implies that the feature's container is *not* running.<br/>
This is the initial state upon boot, and it could be reached from other states too. 

The feature remains in this state until `systemctl start`. <br/>
Upon `systemctl start`, the destination state is LOCAL, if set_owner == LOCAL or KUBE with fallback enabled, else KUBE_READY.

The `systemctl stop` brings back to this state from any state.


####  state LOCAL
***Stable*** state<br/><br/>
system state = up
current_owner = local<br/>
kube_mode = none

The container is running using local image, started by docker command.<br/>

This state is reachable in three ways:
   * From INIT state, upon `systemctl start`, if set_owner = local or {set_owner = local && fallback_to_local)
   * From KUBE_RUNNING, if set_owner is set to "local"
   * From KUBE_READY, if set_owner is set to "local"
   
The feature remains in this state until either of the  following occurs.
   * `systemctl stop` takes back to INIT state
   * The set_owner == kube and kube is deploying the image, which takes it to 'KUBE_RUNNING' state
   
####  state KUBE_READY
***Semi-stable*** state<br/><br/>
system state = up
current_owner = none<br/>
kube_mode = kube_ready

There is no container running. The `systemctl status` would indicate 'waiting for kube deployment'.<br/>

This state is reachable in two ways:
   * From INIT state, upon `systemctl start`, if  {set_owner = kube && not fallback_to_local)
   * From KUBE_RUNNING, when container exits (may be kube undeploy or crash)
   
The feature remains in this state until either of the  following occurs.
   * `systemctl stop` takes back to INIT state
   * The kube is deploying the image, which takes it to 'KUBE_RUNNING' state.
   * set_owner is set to local, which transitions to 'LOCAL' state
   
####  state KUBE_RUNNING
***Stable*** state<br/><br/>
system state = up
current_owner = kube<br/>
kube_mode = kube_ready

The kube  deployed container is running.<br/>

This state is reachable in two ways:
   * From KUBE_READY state, upon kube deploying the image
   * From LOCAL, when container exits (may be kube undeploy or crash)
   
The feature remains in this state until either of the  following occurs.
   * `systemctl stop` takes back to INIT state
   * The set_owner is changed to local, which transitions to LOCAL state.
   * The docker exited transitions it to KUBE_READY
     The docker exit might be due to
      * The manifest is updates, so it removes the current running container, to deploy the new
      * Any fatal faulure encountered
      * The manifest is removed at master, hence kube is un-deploying
      
   
### Transient State descriptions
When the feature is switching between 'local' & 'kube', it moves through one or two short lived transient states. 

#### state LOCAL_TO_KUBE
system state = up
current_owner = local<br/>
kube_mode = kube_pending

In this state, the local container is running. The kube has deployed its container, which sets the kube_mode to kube_pending and goes into waiting loop for local container to exit.

This state reachable only from LOCAL.

The feature remains in this state until hostcfgd notices the kube_mode change to pending and call `docker stop`. 

When the container running local image stops, it transitions to the next transient state "KUBE_PENDING". 


#### state KUBE_PENDING
system state = up
current_owner = none<br/>
kube_mode = kube_pending

In this state no container is running and kube has to notice that local container has exited and proceed<br/>

This state reachable only from LOCAL_TO_KUBE.

The feature remains in this state until the kube deployed container realizes that local container has stopped. 

When the container notices that local container stopped, it transitions to the next stable state "KUBE_RUNNING". 


#### state KUBE_STOPPED
system state = up
current_owner = none<br/>
kube_mode = kube_ready

In this state no container is running and awaiting hostcfgd to call `system container start`. <br/>

This state reachable only from KUBE_RUNNING and it is reached upon hostcfgd calling `system container stop`.

The feature will remains in this state, only until hostcfgd call `system container start` and the container starts from local image and transition to the stable state "LOCAL".


### Common set of scenarios
The common scenarios and the corresponding transition flows are descibed below on scenario basis.

### Default scenario:
None of the features are configured with set_owner = kube. Here it swings between states INIT and LOCAL. The action, `systemctl start` takes from state INIT to LOCAL and `systemctl stop` reverses it from state LOCAL to INIT.


### Kube managing feature with fallback enabled:
Upon system boot, the state is at INIT. The `systemctl start` takes it to state LOCAL and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, the deployed-container sets transition_mode to kube_pending and gets into waiting-mode for local container to exit. This action by kube transitions to state LOCAL_TO_KUBE. The hostcfgd interferes, stops the local container, which transitions it to state KUBE_PENDING. Upon state KUBE_PENDING reached, the kube deployed breaks from waiting mode and proceed to run and that transitions to state KUBE_RUNNING. 

This stays in state-KUBE_RUNNING, until container exits. In normal conditions, the exit is mostlikely because kube un-deployed to handle a manifest update. This takes it to state KUBE_READY. The kubelet re-deploys the container per updated-manifest, which takes it back to state-KUBE_RUNNING. In case of any crash, the transitions are the same, just that kubelet would be restarting the container from the same image. In case the manifest is removed, the feature will remain in KUBE_READY state, until `systemctl stop` or `kube deploy`.

### kube managing feature with fallback disable:
Upon system boot, the state is at INIT. The `systemctl start`, sets transition_mode to 'kube_ready' which takes it to state KUBE_READY and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, it sets the current_owner to 'kube', which is state KUBE_RUNNING. 

When a manifest is re-deployed/un-deployed or container exits, the behavior is same as in case above.

### Switching from kube managed to local mode:
In kube-managed mode, the state is either "KUBE_READY" or "KUBE_RUNNING". When owner is switched to local, the hostcfgd notices it, call `system container stop` if in KUBE_RUNNING mode and then call `system container start`, which takes it to LOCAL mode.

### Switching from local to kube managed:
The feature is in LOCAL mode. When set_owner is changed to KUBE, the hostcfgd create a label to enable kube deployment. At a later point, whenever kube deploys, the kube deployed container sets the kube_state to kube_pending, which transitions it to the transient state "LOCAL_TO_KUBE". The hostcfgd notices it, and call `docker stop` to stop the local container, which transitions it into next transient state "KUBE_PENDING". Here the kube deployed container realizes that local container exited, and proceeds to run which transitions it to the stable state of 'KUBE_RUNNING'.


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

### config FEATURE

#### config FEATURE <name> owner <local/kube> fallback <true/false> failmode <N> [-y]
   This command sets owner, fallback & failmode detection for a feature.<br/>
   This command has the potential to restart the service as required. So a confirmation prompt would be provided.
   
### config FEATURE install
   This command would help install a new FEATURE with simple requirements.
   
#### config FEATURE install <name> [required <list of services required>] 
   This command will create a .service file for systemd and other required bash scripts with required services listed here, such that this service would only run as long as all the required services are running.<br/>
   If the required list is not provided, it would default to "swss" as the required service.
   This would also create an entry in CONFIG-DB FEATURE table as kube-managed with no fallback or failmode check.
   This could be modified using, `CONFIG FEATURE ...` command.
   
#### config FEATURE uninstall <name> 
   Removes the corresponding .service file, associated bash scripts and corresponding entries in FEATURE table from both CONFIG-DB & STATE-DB.
   
### show kubernetes 

#### server
   `show kubernetes server`
   Lists all the configured entries for the server and the status as connected or not, and when did the last state change happened.
   
#### nodes
   `show kubernetes nodes`
   Lists all nodes in the current cluster. This command would work, only when kubernets master is reachable.

#### pods
   `show kubernetes pods`
   Lists all nodes in the current cluster. This command would work, only when kubernets master is reachable.

#### status
   `show kubernetes status`
   It describes the kubernetes status of the node.

#### show FEATURE <name>
   This would list FEATURE table data from both CONFIG-DB & STATE-DB
   
# Reboot support

## Warm-reboot support
   This [warm-reboot](https://github.com/Azure/SONiC/blob/master/doc/warm-reboot/SONiC_Warmboot.md) support is for updating/restarting with no data-plane disruption. The `/usr/bin/warm_reboot` script is a complex script that does many pre-requisites, kill the containers and eventually call a specific command for reboot. The individual service level support for warm-start lies within its code/implementation-logic. When configured for warm start, upon start-up, the service should be able to acquire its i/p data from all its channels as ever, but instead of pushing it in entirety to the consumer/DB, read the pre-boot data (which is made available in APP-DB), find the diffs as stale/new/update and only push the diffs. With every app doing it and, with some additional complex steps for critical processes like orchagent & syncd, the data plane traffic goes unaffected, except for the changes pushed into ASIC,  which is a normal runtime experience of consuming changes as it happens.
   
   In short if a service supports warmboot, it would continue to support in both local & kube modes transparently. 
   The warm_reboot script needs to be updated as 
      * Disable kubelet service (`systemctl disable kubelet`)
      * Replace all `docker kill` commands with corresponding `system container kill` commands, with an option not to check for kubelet service. 
      * kubelet config/context, kube certs/keys and, /etc/sonic/kube_admin.conf  needs to be carried over to the new image.
      * Ensure all kube managed features have local images.
         * If not, tag the currently downloaded image appropriately
      * Ensure all kube managed features are enabled to fallback to local image.
      
   
   Reason for the changea:
   * With kubelet running, it would restart any container that is manually stopped or killed. Hence disable it
   * Containers started by kube, can't be referred by name. The `system container kill` command would fetch the corresponding docker-id from STATE-DB  and use that to kill.
      * Pass the option not to check for kubelet service, to save time from redundant check.
   * Carry over kubelet related context, to enable transparent join and interaction with master.
   * Upon reboot, the switch could take some solid time to establish connection with kubernetes master. Until then, the containers that are marked as kube-managed with no fallback, can't start. Hence ensure availability of local image & fallback, so the containers can start immediately from local copy. The set_owner remaining as kube, will help kube to manage, whenever the switch successfully connects to the master. BTW, connecting to the master is done by kubelet transparently.
   
   For new features that are not known to warm-reboot script, some hooks could be allowed for registration of feature-custom scripts. This could help with some preparation steps before reboot, like caching some data, setting some DB values, ...
   
## Fast-reboot
   This [fast-reboot](https://github.com/Azure/SONiC/wiki/Fast-Reboot) support aims to help image-udpate and restart, with minimal data-plane traffic disruption. The implementation is similar to warm-reboot, that logic is embedded in the fast-boot script, additional utilities and some tweaks inside the code/logic of individual services that supports. Here again any service level support lies within the internal code/logic.
   
   In short, the summary and the required changes, including hooks for new features, are the same as in warm-reboot support, just that here use fast-reboot script.
  
   
## reboot
   Regular reboot is supported transparently, as it just restarts the entire system and  goes through systemd, as long as `system container ...` commands are used instead of corresponding `docker ...` commands.
   
   
# Service install for kube managed features

Points to note:
   * The features managed by kube only (*no local image*), will not have a service file locally in the image, hence it needs to be explicitly created/installed.
   * The features that are in hybrid mode as local/kube managed, a service file would indeed be available locally. Yet, an updated image that could be brought in by kube, could demand a tweak in the service file or start/stop/wait scripts, which requires an explicit update.
   * Every kube-managed feature should have an entry in CONFIG-DB, FEATURE table.
   * Any utility that requires the list of all features would refer to this FEATURE table in CONFIG-DB.
   
 A couple of proposals are listed below. The pick & implementation of the proposal is outside this doc. 
   
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

# Image management
  For a kube managed container, when updates happen, it downloads a new image, which can result in multiple container images for a single feature. This is a requirement, but not addressed in this doc. This doc, just touches the possibilities.
  
  ## Garbage collection:
  We could extend kubelet's garbage collection facility and configure it appropriately. 
  
  ## local image
  Every switch image comes with container images for all features. We may remove it and tag the downloaded image as local, so the switch can keep one copy for both kube & local modes.

# Failure mode detection & rollback
  With kubernetes managing features, it involves new code being pulled in dynamically, which has the potential to fail.<br/>
  This brings in two questions
  a)  How to detect the failure?
  b)  How do we rollback ?
  
  This requirement is outside this doc, but discuss some possibilities.
  
  ## Failure detection
   * We could use a monitor script both at host level and internally within the container. 
   * The CONFIG-DB FEATURE table entry could be used to configure failure mode detection parameters for either.
   * The STATE-DB FEATURE entry could be used by both monitoring facilitlies to report the error.
   * The CONFIG-DB FEATURE, could set the rollback policy as alert-only, switch-to-local, ...
   * The hostcfgd or another daemon could carry out the task, upon STATE-DB FEATURE table reporting failure.
   
# Implementation phases:
The final goal for this work item would be to remove nearly all container images from SONiC switch image and manage all through kubernetes only. The proposal here is to take smaller steps towards this goal.

## Phase 1:
   Support services that meet *all* of the following criteria

   * A simple service that has few *required* other services and no service depends on this service.
   * A service that does not affect dataplane traffic
      * Transparent to warm-reboot & fast-reboot.
   * A service with no local image, hence to be managed by kube only
  
Run an config utility with input file that provides the list of required services, and this creates the service file along with bash scripts as required by the service and an update to FEATURE table in CONFIG-DB, with set_owner = kube and no fallback.

## Phase 1:
   A deviation from phase 1.<br/>
   * Support a locally available image between local & kube.
   * Only for features that does not affect dataplane, like snmp, pmon, lldp, ...
 
The service files are already available. The FEATURE table would be auto created, when user runs the command to switch owner to kube.


   
