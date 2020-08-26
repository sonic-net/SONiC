# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The SONiC image has all the container images burned/embedded inside, with each container managing a feature, like swss, syncd, snmp, .... The systemd manages the features. The systemctl service commands calls service specific scripts for start/stop/wait. These scripts ensure all complex dependency rules are met and use `docker start/stop/wait` to manage the containers. This current mode is referred as '**Local mode**' in this doc.

With this proposal, the management of container images is extended to kubernetes-support, where an image could be downloaded from external repositaries and kubernetes does the deployment. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode is referred as "**kubernetes mode**". For short word "kube" is used interchangeably to refer kubernetes.

# A Brief on Kubernetes
  
  ***Disclaimer**: This brief on kubernetes is only to give some basics on few terms, related to this doc. For full & official details, please refer to [kubernetes documentation](https://kubernetes.io/docs/home/)*
  
  This is a well known open source platform for managing containerized loads. To describe kubernetes in simple terms, it is a management engine, which can deploy applications in nodes, scale it, manage it, roll updates and customizable per app. 
  
  ## Key terms:
   * Kubernetes master/cluster<br/>
      This is the brain behind the kubernetes system. Comprised of many deamons, which includes API server, scheduler, controller, kubelet, proxy, etcd, ...<br/>
      To ensure high availability two or more masters could be installed as a cluster behind a VIP.<br/>
      A kubernetes cluster is externally installed to manage SONiC switches.
      This is outside the scope of this doc.
      
   * node<br/>
      A SONiC switch joins a kubernetes cluster as a node, to facilitate kube manage dockers in the switch.
      
   * pods<br/>
      This is the unit of kubernetes deployment. A manifest describes the pod. In SONiC switches, a pod runs a single container only. The master is configured with manifests that decides what containers/pods to deploy on SONiC switches. The SONiC switches keeps the control of when the deployment can happen.
      
   * manifest<br/>
      A manifest describes the pod as below. 
        * Assigns a name
        * List of containers
          * In case of sonic, only one container
        * Description of each container
          * Image URL
          * volume mounts
          * runtime args
          * environment variables
          * ...
        * Node selector labels
        * ...<br/>
      
   * Node selector labels<br/>
      A label is a `<key>=<value>` pair. A manifest may carry multiple labels. Each node that joined, can be described with multiple labels. A pod will be deployed only in nodes, where all the labels of the manifest are matched with the labels on the node. In short a full/subset of node labels should completely match with all labels on the manifest. This leads to the term "eligible nodes", where node labels matching is the requirement to meet, for deployment of a pod, in SONiC usage scenario.
      
      SONiC switch can add labels describing its version, platform, .... This can help create manifests for specific version and platform and ...
      
   * Daemonset<br/>
      A deamonset is a special kind of pod. A daemonset pod is deployed in every node that matches the requirments per manifest. In case of daemonset, there is only one instance per node. The kube manages pods on SONiC switches using the kind daemonset only.
           
## A high level overview on setup:
  1) Set up a master cluster
  2) The container images are stored in container registry, like Azure Container Registry
  3) The manifests are created for each feature.
     * The manifest describes the runtime options for the docker, like mounts, environment, args, ...
     * The manifest is assigned with node-selector labels possibly to select nodes by platform, OSVersion, ...
  4) The manifests are applied in master.
     * For a better control, manifests can be checked into a github repo.
     * A script running in master can watch for updates and apply manifest on each update or remove, if manifest is deleted.
  5) Configure SONiC switches with VIP of the cluster
     * The minigraph provides the VIP.
  6) Run a config command in switch to join the master manually or transparently.
  7) The master deploys pods in all eligible nodes that have joined.
     * On any manifest update, it stops the current pod running in node and deploy the new one.
     * On any manifest removed, it stops tbe current pod
  
     

# Problem to solve:
Currently, all docker images are hard burned into installable SONiC image. For any code update in a container image, however minor, requires re-build of the entire SONiC image and the rest of the heavy weight process to qualify the image to run in a production switch followed by install of the image in controlled phases with a mandatory reboot required.

## Proposal:
Build the image as today. Install the image as today. In addition configure a subset of dockers as "*could be kube managed*", which could even be hardcoded in minigraph.py. Whenever the switch would join a master and if the master has a manifest for a feature marked as kube-managed for this node, master deploys the container per manifest.<br/>
For any code update for a container, just build the container only, qualify *only* the container image through tests, upload the image to container registry and update the manifest in master. The master now deploys the updated container to all connected & eligible nodes, transparently, with the only cost of restarting that updated service. For containers that does not affect data plane, the restart can be transparent. For containers that do affect, it can be restarted in warm-reboot mode, so it could be updated with no traffic disruption.

This could be extended to features that are ***not part of SONiC image***, but could be enabled to run in SONiC switches.

# Goal:
1) Enable to deploy containers that are not part of SONiC image to run in a switch running SONiC
2) Enable containers that are part of SONiC image to become controllable by kubernetes as needed, with an ability to revert back to local.

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
    * The switch must have systemctl service file and any associated bash scripts for this feature, as required by systemd.
    * The service/scripts must ensure all dependencies across other features are met.
    * The feature is still controlled by systemd as start/stop/enable/disable.
   
5. A kubernetes deployed container image must comply with guidelines set by SONiC.
   * Required to under go nightly tests to qualify.
   * Kubernetes masters are required to deploy only qualified images.
   * Switch must have a control over a known node-selector label that let switch control, when a manifest can be deployed.
   * Masters control what manifests to deploy and switches/nodes control when to deploy.
   * Containers are expected to call a script at host, on post-start & pre-exit, that record their state.
       

# Mandates on deployed images
The following are required, but external to the node/switch, hence not addressed in this design doc. 
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
   
   But start/stop of a kube deployed containers are done through add/remove of `<feature name>_enabled=true` label and use `docker start/stop` only for local containers.
   In case of container wait, use container-id instead of name.
   
   To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker kill  --> system container kill
   * docker wait  --> system container wait
   * docker inspect --> system container inspect
   * docker exec    --> system container exec
   
   The bash scripts called by systemd service would be updated to call these new commands in place of docker commands. In addition, any script that call docker commands will be switched to these new commands. A sample could be the reboot scripts, which call `docker kill/stop ...`.
   
   
* The new "system container ..." commands in brief<br/>
   * Container start<br/>
     Do a docker start, if in local mode, else create a label that would let kubelet start.
     
   * Container stop<br/>
      Do a docker stop, if in local mode, else remove the label that would let kubelet stop. If remove label would fail, do an explicit docker stop using the ID.<br/>
      ***Note***: For a kubelet managed containers, an explicit docker stop will not work, as kubelet would restart. That is the reason, the label is removed instead, which instruct kubelet to stop it. But if label remove failed (*mostly because of kubernetes master unreachable*), it would auto disable kubelet transparently. Hence if label-remove would fail, the explicit docker-stop would be effective.
      
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
    
     The start.sh of the container (*called from supervisord*) is updated to call `system container state <name> up <kube/local>`, which in turn would do the above update. The application process is started after the call to container_state script.
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      * `current_owner_update_ts = <Time stamp of change>`
      
     A local monitor script is added to supervisord. This script is started by start.sh inside the container under supervisord control. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
     
   The containers that could be managed by kube, ***must*** call the `system container state ...` commands. It would be handy, if all containers follow this irrespective of whether kube may or may not manage it, as that way STATE-DB/FEATURE table could be one place to get the status of all active features. The code that gets i/p from this table has to be aware of the possibility of not all containers may call it, but it can be assured that all kube manageable containers would have an entry.
   
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
   required_services = <list of names>;         Optional entry. A kube only feature may provide this info to enable auto-create
                                                required .service & .bash scripts to enable systemd manage it as service.
  

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
   kube_mode = ""/"none"/"kube_pending"/"kube_ready";
                                              Helps dynamic transition to kube deployment.
                                              Details below.
```

   ### Transient info:
   
   The kubernetes label creation requests are directed to API server running in kubernetes master and they are synchronous. These requests would timeout, if the server is unreachable. In this case, these failed requests are persisted in this Transient-info entry. A monitoring script would watch and push, at the next time point the server is reachable. The action of explicit disconnect from master, will purge this entry. 
  
   The pending labels are appended into this list in the same order as they arrive. A label to add will look like `<key>=<val>` and label to remove will look like `<key>-`.
   
   The labels control, what to deploy/un-deploy. This implies that the kubelet which does the job of deploy/un-deploy of containers, should be in sync with labels update. Hence in scenarios, where master become unreachable and so labels can't be pushed to master, the kubelet is disabled. The kubelet remains disabled until all labels are synced and at that point, it gets re-enabled. If kubelet is *not* disabled and if it reaches server before labels are synced, the kubelet's actions could be unexpected/undesired.
   
   *NOTE*: Disabling kubelet does not affect containers deployed by it. So if stop/kill is required, when kubelet is disabled, make explicit docker call.
    
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
   *  The [`systemctl stop` action is always performed](https://man7.org/linux/man-pages/man5/systemd.service.5.html) when the container exits.
      * The container exit may be due to an explicit call to `systemctl stop` or
      * The container may exit due to internal container process termination or kubelet removing the pod.
   *  A `systemctl start` always precedes the container start.
      * Whenever container exits, not due to `systemctl stop`, and if the feature is enabled for auto-restart, the start action is performed transparently.
      * This helps kubelet deploy a new updated pod,upon removing the running pod.
   *  The kube mode
      *  none  - No initiative from kube on this feature
      *  kube_pending - Kube is ready to deploy and waiting to proceed
      *  kube_ready - kube container can proceed to run 
   *  At anytime only one container from any mode can be running its application processes.
      
### State descriptions
#### state INIT
***Stable*** state<br/>
system state = down<br/>
current_owner = none<br/>
kube_mode = any or N/A

In this state, no container is running. This is the initial state upon boot and upon performing `systemctl stop` from any state.

The current_owner = none implies that the feature's container is *not* running in any mode.<br/>

The feature remains in this state until `systemctl start` action is performed. <br/>
Upon `systemctl start`, the destination state is LOCAL, if set_owner == local or kube with fallback enabled and kube_mode is none, else KUBE_READY.

The `systemctl stop` brings back to this state from any state.


####  state LOCAL
***Stable*** state<br/>
system state = up
current_owner = local<br/>
kube_mode = none

The container is running using local image, started by docker command.<br/>

This state is reached from INIT state, upon `systemctl start`, if set_owner = local or {set_owner = kube && fallback_to_local && kube_mode = none)
   
The feature remains in this state until `systemctl stop` action is performed, which transitions it back to INIT state.


####  state KUBE_READY
***Semi-stable*** state<br/>
system state = up<br/>
current_owner = none<br/>
kube_mode = kube_ready

There is no container running. The `systemctl status` would indicate 'waiting for kube deployment'.<br/>

This state is reached from INIT state, upon `systemctl start`, if set_owner = kube and either of the following is true
  * The fallback_to_local == false, so it transitons to KUBE_READY state <br/>
  OR
  * The kube_mode != none, implying kube is pending deployment. So even with fallback set, go to KUBE_READY.
   
The feature remains in this state until
  * kube deploys the container, which transitions it to KUBE_RUNNING state.<br/>
  OR
  * The `systemctl stop` action is performed, which transitions it back to INIT state.
   
####  state KUBE_RUNNING
***Stable*** state<br/>
system state = up<br/>
current_owner = kube<br/>
kube_mode = kube_ready

The kube  deployed container is running.

This state is reached from KUBE_READY state, upon kube deploying the image
   
The feature remains in this state until `systemctl stop` action is performed.<br/>
BTW, the kubelet stopping the container to deploy a new one, or an internal container crash would auto trigger this `systemctl stop` action.

   
#### state LOCAL_TO_KUBE
***Transient*** state<br/>
system state = up<br/>
current_owner = local<br/>
kube_mode = kube_pending

In this state, the local container is running. The kube has deployed its container, which sets the kube_mode to kube_pending and goes into a forever sleep mode. NOTE: The application processes inside the kube deployed container are not started yet.

This state reached only from LOCAL, upon deployment by kube.

The feature remains in this state until hostcfgd notices the kube_mode, invokes `systemctl stop`, which would transition it to INIT state. 


### Common set of scenarios
The common scenarios and the corresponding transition flows are descibed below on scenario basis.

### Default scenario:
None of the features are configured with set_owner = kube. Here it swings between states INIT and LOCAL. The action, `systemctl start` takes from state INIT to LOCAL and `systemctl stop` reverses it from state LOCAL to INIT.


### Kube managing feature with fallback enabled:
Upon system boot, the state is at INIT. The `systemctl start` takes it to state LOCAL and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, the deployed-container sets kube_mode to kube_pending and gets into a forever sleep mode. This action by kube transitions to the transient state LOCAL_TO_KUBE. The hostcfgd interferes, call for `systemctl stop`, which transitions it to INIT state. Now hostcfgd sets kube_mode = kube_ready and call for `systemctl start`, which would transition it to KUBE_READY state, waiting for re-deploy from kube. The re-deploy by kube would notice the mode to kube_ready, hence proceeds to start the application processes, transitioning to KUBE_RUNNING state. 

The feature stays in state-KUBE_RUNNING state, until container exits. In normal conditions, the exit is mostlikely because kube un-deployed to handle a manifest update. This action of container exit, triggers systemd to perform stop action, which would transition it to INIT state. As it is auto-container exit, if this feature is enabled for auto restart by systemd, the systemd would transparently perform start action. Ths start action would transition to state KUBE_READY, as kube_mode == kube_ready. The kubelet deploys the container per updated-manifest, which takes it back to state-KUBE_RUNNING. In case of any crash, the transitions are the same, just that kubelet would be restarting the container from the same image. In case the manifest is removed, the feature will remain in KUBE_READY state, until `systemctl stop` would transition to INIT state. 

In other words, once kube deploys, it would not go to LOCAL mode, even with fallback set, unless the kube_mode is explicitly set to none, followed by a `systemctl restart`, which would transition briefly to INIT state and ends in LOCAL state. If a feature is stuck in KUBE_READY for too long, this action could be executed to fallback to LOCAL state


### kube managing feature with fallback disable:
Upon system boot, the state is at INIT. The `systemctl start`, sets kube_mode to 'kube_ready' which takes it to state KUBE_READY and as well add a label that enables kube-deployment. Whenever kube deploys in future, asyhnchronously, it sets the current_owner to 'kube', which is state KUBE_RUNNING. 

When a manifest is re-deployed/un-deployed or container exits, the behavior is same as in case above, with the exceptiom of never fallback to LOCAL state.

### Switching from kube managed to local mode:
In kube-managed mode, the state is either "KUBE_READY" or "KUBE_RUNNING". When owner is switched to local, the hostcfgd notices it, call `system container stop` which would transition to INIT state and then call `system container start`, which takes it to LOCAL state.

### Switching from local to kube managed:
The feature is in LOCAL mode. When set_owner is changed to KUBE, the hostcfgd create a label to enable kube deployment. At a later point, whenever kube deploys, it follows the same steps as described in `Kube managing feature with fallback enabled` section above. 


## Internal commands

### Container start/stop/kill/wait:
   The container start/stop/kill/wait replace the corresponding docker commands. The logic is explained in the flow chart below. The waiting for docker-id will timeout, in case of local image, after N seconds. In case of kubernetes mode, it will wait for ever, as the image deployment depends on many external factors.
     
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_start_stop_wait.png)
   


### container state up/down
   Each container calls this upon start and upon termination. This helps gets the current mode as local/kubernetes, docker-id and the status as running or not.
   Ths following chart depicts the flow.
   
   ![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/container_state.png)
   
 
### hostcfgd update
   The hostcfgd watches for `kube_mode == kube_pending`. When set, stops the service, wait till service stops, set `kube_mode=kube_ready` and start the service. This ensures smooth transfer from local mode to kube mode and as well ensure service start precedes container start by kubernetes.
   
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

### config feature

#### config feature <name> [owner <local/kube>] [fallback <true/false>] [failmode < N seconds >] [required <list of required services> ] [-y]
   This command can be used to sets all properties of a FEATURE.<br/>
   The set_owner update has the potential to restart the service as required. If yes, a confirmation prompt would be provided.
   
### config feature install <name>
   Every feature requires .service & bash scripts to enable systemd to manage it. The features that are part of SONiC image has those files embedded. For new features that are added, this command could be used to create.
  
   This command would help create a .service file for systemd and other required bash scripts with required services, such that this service would only run as long as all the required services are running.<br/>
  
  If the required list is not provided, it would default to "swss" as the required service.
  
  On image upgrade, if that involves carrying config over, either these created files need to be carried along or run this command in the new image for all kube-only features.
   
#### config feature uninstall <name> 
   Removes the corresponding .service file, associated bash scripts. It does not affect the corresponding entries in FEATURE table from both CONFIG-DB & STATE-DB.
   
### show kubernetes 

#### server
   `show kubernetes server`
   Lists all the configured entries for the server and the status as connected or not, and when did the last state change happened.
   
   ```
   admin@str-s6000-acs-13:~$ show kube server
   KUBERNETES_MASTER SERVER IP 10.10.10.10
   KUBERNETES_MASTER SERVER insecure False
   KUBERNETES_MASTER SERVER disable False
   KUBERNETES_MASTER SERVER connected True
   KUBERNETES_MASTER SERVER last_update_ts 1000
   ```
   
#### nodes
   `show kubernetes nodes`
   Lists all nodes in the current cluster. This command requires kubernets master as reachable.
   
   ```
   admin@str-s6000-acs-13:~$ show kube nodes
   NAME               STATUS   ROLES    AGE   VERSION
   str-renuka-01      Ready    master   29d   v1.18.6
   str-s6000-acs-13   Ready    <none>   18d   v1.18.6
  ```

#### pods
   `show kubernetes pods`
   Lists all active pods in the current node. This command requires kubernets master as reachable.
   
   ```
   admin@str-s6000-acs-13:/usr/lib/python2.7/dist-packages/show$ show kube pods  
   NAME             READY   STATUS    RESTARTS   AGE
   snmp-sv2-577ff   1/1     Running   0          17h
   ```

#### status
   `show kubernetes status`
   It describes the kubernetes status of the node.<br/>
   Provides the output of `kubectl describe node <name of this node>`.<br/>
   This command requires kubernets master as reachable

#### show feature <name>
   This would list FEATURE table data from both CONFIG-DB & STATE-DB<br/>
   ```
   admin@str-s6000-acs-13:~$ show features 
   Feature    Status    set_owner    fallback    current_owner    current_owner_update    docker_id     kube_request
   ---------  --------  -----------  ----------  ---------------  ----------------------  ------------  --------------
   snmp       enabled   kube         true        kube             1598323562              4333d9d5004a  kube_ready
   ```
# Reboot support

## Warm-reboot support
   This [warm-reboot](https://github.com/Azure/SONiC/blob/master/doc/warm-reboot/SONiC_Warmboot.md) support is for updating/restarting with no data-plane disruption. The `/usr/bin/warm_reboot` script is a complex script that does many pre-requisites, kill the containers and eventually call a specific command for reboot. The individual service level support for warm-start lies within its code/implementation-logic. When configured for warm start, upon start-up, the service should be able to acquire its i/p data from all its channels as ever, but instead of pushing it in entirety to the consumer/DB, read the pre-boot data (which is made available in APP-DB), find the diffs as stale/new/update and only push the diffs. With every app doing it and, with some additional complex steps for critical processes like orchagent & syncd, the data plane traffic goes unaffected, except for the changes pushed into ASIC,  which is a normal runtime experience of consuming changes as it happens.
   
   In short if a service supports warmboot, it would continue to support in both local & kube modes transparently.</br>
   The warm_reboot script needs few updates as below.<br/>
      * Disable kubelet service (`systemctl disable kubelet`)
      * Replace all `docker kill` commands with corresponding `system container kill` commands, with an option to skip any updates. 
      * kubelet config/context, kube certs/keys and, /etc/sonic/kube_admin.conf  needs to be carried over to the new image.
      * Carry the .service & bash scripts created for kube only features to new image.
      * Ensure all kube managed features have local images.
         * If not, tag the currently downloaded image appropriately
      * Ensure all kube managed features are enabled to fallback to local image.
      
   
   Reason for the changea:
   * With kubelet running, it would restart any container that is manually stopped or killed. Hence disable it
   * Containers started by kube, can't be referred by name. The `system container kill` command would fetch the corresponding docker-id from STATE-DB  and use that to kill.
      * Pass the option to skip any updates to save time, as system is going for a reboot.
   * Carry over kubelet related context, to enable transparent join and interaction with master.
   * The .service & bash scripts for kube only features, may not be available in new image. To save the time of re-create, just take the files over to the new image.
   * Upon reboot, the switch could take some solid time to establish connection with kubernetes master. Until then, the containers that are marked as kube-managed with no fallback, can't start. Hence ensure availability of local image & fallback, so the containers can start immediately from local copy. The set_owner remaining as kube, will help kube to manage, whenever the switch successfully connects to the master.<br/>BTW, connecting to the master is done by kubelet transparently.
   
   For new features that are not known to warm-reboot script, some hooks could be allowed for registration of feature-custom scripts. This could help with some preparation steps before reboot, like caching some data, setting some DB values, ...
   
## Fast-reboot
   This [fast-reboot](https://github.com/Azure/SONiC/wiki/Fast-Reboot) support aims to help image-udpate and restart, with minimal data-plane traffic disruption. The implementation is similar to warm-reboot, that logic is embedded in the fast-boot script, additional utilities and some tweaks inside the code/logic of individual services that supports. Here again any service level support lies within the internal code/logic.
   
   In short, the summary and the required changes, including hooks for new features, are the same as in warm-reboot support, just that here use fast-reboot script.
  
   
## reboot
   Regular reboot is supported transparently, as it just restarts the entire system and  goes through systemd, as long as `system container ...` commands are used instead of corresponding `docker ...` commands.
   
# Multi-ASIC support:
In multi-asic platform,
  * Some features run in single instance like in other platforms. e.g. ACMS
  * Some features run in multiple instances as one per ASIC. e.g. syncd
  * Some features run in multiple instances as one per ASIC and one in host too. e.g. database
  
All these features single or multiple, share the same image with only runtime differences.
Multi-ASIC support would be a *best* effort approach. Any additional work required for multi-asic support would be outside the scope of this doc.

## Manifests
For kube managed dockers, the runtime is defined in manifests. Following are the differences observed across multiple instances of same feature.
  * Name of the container
    e.g. "bgp, bgp0, bgp1, bgp2, bgp3, bgp4, bgp5"
    This is well defined across ASICs, hence can be auto coined.
    
  * NAMESPACE_ID - the environment variable
    none for host instance and for each ASIC, it ranges from 0 to 5. This is well defined across ASICs.
  
  * Hostname
    The host instance carry the hostname. The ASIC instances carry an unique ID. All docker of running in that ASIC share that ID.
    ***TODO/Questions:***
      1) How is this identified per ASIC ?
      2) Can this be pre-identified and be common across switches of the same platform ?
    
  * Mounts differ
    Path mounts differ per ASIC. For example, each ASIC instance maps its own redis instance. This is well defined across ASICs.
    
In short, same image, but with different runtime parameters. This can be easily extended as multiple manifests as one manifest per ASIC.

### Summary:
* There will be a ***manifest per instance*** in switch, which could be one per ASIC and/or one per host.
* Manifest also controls, the URL of the image, hence theoretically, this could result in multiple ASICs running different images for the same feature.
  * There need to be an external control to ensure that all manifests across ASICs for a switch carry same URL, if that is a requirement.
  * This is outside scope of this doc
* Even when master is applied with manifests that all point to same URL, the point of switching one image to other, can be asynchronous across ASICs.
  * The hostcfgd is a single instance and it would need to circle through ASIC instances, when switching between kube to local and viceversa
  * Hopefully, this would be an acceptable delay between instances
  * If not, further investigation & customization would be required.
  * Any fine tuning, would be an RFE and not in the scope of this doc.

## FEATURE config:
The configuration of FEATURE is in CONFIG-DB. This controls set_owner, fallback, enabled,... parameters per FEATURE.

The config could be distributed per ASIC or it could be one shared instance that controls across all ASICs & host.

The proposal is to have ***FEATURE config in single host instance*** that serves all ASICs & host. 
The same instance, which carries system level config like TACACS, syslog, ...


## FEATURE status:
* The status has to be instance specific and hence would be ***distributed as per ASIC and one for host in STATE-DB***. 
* The hostcfgd would watch all instances of STATE-DB to make effect.
   
    
# Service install for kube managed features

Points to note:
   * The features managed by kube only (*no local image*), will not have a service file locally in the image, hence it needs to be explicitly created/installed.
   * The features that are in hybrid mode as local/kube managed, a service file would indeed be available locally. Yet, an updated image that could be brought in by kube, could demand a tweak in the service file or start/stop/wait scripts, which requires an explicit update.
   * Every kube-managed feature should have an entry in CONFIG-DB, FEATURE table.
   * Any utility that requires the list of all features would refer to this FEATURE table in CONFIG-DB.
   
 A couple of proposals are listed below. The poposal-1, the easiest option is provided as part of this doc. The rest are *only* suggestions for brainstorming for now. 
   
 ## Proposal - 1:
  Provide a config command that can create a .service and bash scripts for a feature with simple requirements like, 
    * This feature depends on zero or more features &&
    * No other feature depends on this feature &&
    * Transparent to wam-reboot & fast-reboot
      implying it does not affect data plane traffic directly or indirectly.
  The `config feature install <name> [<required services list>]` would create the necessary files.
  
  
  ## proposal - 2:
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
   *  The kubernetes master manages manifests. With a distributed system of multiple masters sharing the same set of manifests, there is likely a single input source for the manifests. The same source could be extended to provide service-file-packages too.
      *  A possible input source is a git repo, cloned locally in each master.
      *  A periodic pull & monitor can identify new/update/delete of manifests, which can be applied transparently.
   *  A single metadata file could be available in the same source that explains all the service packages and optionally additional filters to select elgible target nodes, per package.
   *  Master can make the metadata & service package files available through an https end-point for nodes.
   *  A node can watch for this meta-data file update at master through https end-point, pull the update, look for any new/updated/deleted packages that this node is eligible for, pull down those packages and, install/uninstall the same.
   *  The installation would include .service file, any associated scripts and update of FEATURE table in CONFIG-DB.
        
   

## Proposal - 4:
   Run an external service, to install required service files in each node, explicitly.

# Image management
  For a kube managed container, when updates happen, it downloads a new image, which can eventually result in multiple container images for a single feature.
  
  ***Note:*** This requirement is outside the scope of this doc. This doc, just touches the possibilities.
  
  ## Garbage collection:
  The kubelet's [garbage collection](https://kubernetes.io/docs/concepts/cluster-administration/kubelet-garbage-collection/) feature could be utilized.<br/>
  For a tighter control, a custom soultion might be required which could monitor & manage as configured.
  
  
  ## local image
  Every switch comes with locally available container images for all embedded services. When a kube downloads an image for an embedded service, potentially the local image for that feature could be removed and tag the downloaded image as the local copy, as it is with higher probability that downloaded image would be higher in quality and/or features, in relation to the locally burned container image.

# Failure mode detection & rollback
  With kubernetes managing features, it involves new code being pulled in dynamically, which has the potential to fail.<br/>
  This brings in two questions
  a)  How to detect the failure?
  b)  How to do rollback ?
  
  This requirement is outside the scope of this doc, but discuss some possibilities.
  
  ## Failure detection
  * A monitor script could be used both at host level and internally within the container to look for failure.
    * The monitoring could either report on error or touch heartbeat to show healthy
  * The CONFIG-DB could be used to provide some configurable parameters for the failure detection algorithm
  * The STATE-DB could be used as the place to save heartbeat or errors
   
  ## Self-mitigation:
  *  Switch comes by default with a local image, which can be considered ***Golden***.
  *  Any downloaded image, could be certified as ***Golden***, if it ran healthy for < N > seconds.
  *  Always keep one copy of one ***Golden*** image in the system for every feature.
     * Ensure that garbage collection does not touch the ***Golden*** image.
     * When you mark a new image as ***Golden***, unmark the previous ***Golden*** image as not ***Golden*** anymore
  *  Make sure starting a feature in local mode runs this ***Golden*** image.
  *  Whenever new downloaded image reports failure and the failure persists for more than < M > seconds,
     * mark the Feature's fallback to 'true'.
     * set kube_mode = "none"
     * restart the service, which would end up running from local ***Golden*** image.
  
  
  # Safety Check Service
  When a manifest is deployed in master, it gets instantly applied to all eligible nodes. In a production environment, this flooding of updates across all at the same time point, may not be acceptable, as this involves
    * restart of service, which could have data plane disruption
    * New code may not be good, causing failure across entire fleet of devices at the same time.<br/>

  ***Note:*** The Safety Check Service is a critical requirement, but outside the scope of this doc.
  
  A brief brainstorming is attempted, more to highlight the problem to solve.
  
  ## High level requirements:
    a) The master should not flood but make the updates in batches, where a single batch would have a subset of nodes.
    b) The selection of batches and its members had to be done diligently
    c) An update on a batch, may involve isolating devices from traffic, before marking the batch as ready for update.
    d) Rolling updates in batches be controlled based on results of deployment done so far.
    e) Have a way to rollback, when a batch fails
    
  
  ## A possibility:
  * Each manifest be assigned with an unique label as one of NodeSelector labels
  * When a manifest is applied, none of the nodes would be eligible, as none of the nodes would have this new label.
  * An external entity identifies the subset of nodes to update.
  * For each node in that set, add this unique label, that will make the selected subset of nodes as eligible for update
      * If this is a manifest update, make sure to remove the unique label that was added for the last update
      * This removal will make kube undeploy the old one.
      * Addition of the new label will enable deployment of the current update.
  * Wait for deployment to a batch complete. Give sometime to watch the health
  * Depending on the result, either
    * repeat the above steps from identifying next set of nodes to update<br/>
    OR
    * remove the new label and add the old label to rollback for each node.
     
    
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


   
