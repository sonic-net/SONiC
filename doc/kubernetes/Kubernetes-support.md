# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The SONiC image has all the container images burned/embedded inside, with each container managing a feature, like swss, syncd, snmp, .... The systemd manages the features. The systemctl service commands calls service specific scripts for start/stop/wait. These scripts ensure all complex dependency rules are met and use `docker start/stop/wait` to manage the containers. This current mode is referred as '**Local mode**' in this doc.

# Vision
The vision here is to open up container management to external management infrastructure. There are few options here, like Kubernetes, DockerSwarm, OpenShift, ... As a first step/phase, this doc takes up with Kubernetes support. The reason for the pick is that
  * Widely adopted by many
  * World wide community support
  
The goal it to keep the design open for future integration with other technologies too. With a minimal build time change, one should be able to build SONiC image that supports the selected tool.

This proposal deals in depth with kubernetes-support. With this proposal, an image could be downloaded from external repositaries and kubernetes does the deployment. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode is referred as "**kubernetes mode**". For short word "kube" is used interchangeably to refer kubernetes.


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
          * Network
          * ...
        * Node selector labels
        * ...<br/>
      A sample manifest [here](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/snmp_pod_manifest.yaml)
      
   * Node selector labels<br/>
      A label is a `<key>=<value>` pair. A manifest may carry multiple labels. Each node that joined, can be described with multiple labels. A pod will be deployed only in nodes, where all the labels of the manifest are matched with the labels on the node. In short a full/subset of node labels should completely match with all labels on the manifest. This leads to the term "eligible nodes", where node labels matching is the requirement to meet, for deployment of a pod, in SONiC usage scenario.
      
      SONiC switch can add labels describing its version, platform, .... This can help create manifests for specific version and platform and ...
      
   * Daemonset<br/>
      A deamonset is a special kind of pod. A daemonset pod is deployed in every node that matches the requirments per manifest. In case of daemonset, there is only one instance per node. The kube manages pods on SONiC switches using the kind daemonset only.
           
## A high level overview on setup:
  1) Set up a master cluster
  2) Upload the container images to a container registry, like Azure Container Registry
  3) Create manifests for each feature.
     * The manifest describes the runtime options for the docker, like mounts, environment, args, ...
     * The manifest is assigned with node-selector labels possibly to select nodes by platform, OSVersion, ...
  4) Apply the manifests in master.
     * For a better control, manifests can be checked into a github repo.
     * A script running in master can watch for updates and apply manifest on each update or remove, if manifest is deleted.
  5) Configure SONiC switches with VIP of the cluster
     * The minigraph provides the VIP.
  6) Run a config command in switch to join the master manually or transparently.
  7) Now the master deploys pods in all eligible nodes that have joined.
  8) For any update, push new container image to registry; update manifest; propagate manifest to all masters.<br/>
     For each connected node,
     * On any manifest update, kube stops the current pod running in node and deploy the new one.
     * On any manifest removed, it stops tbe current pod
  
     

# Problem to solve:
Currently, all docker images are hard burned into installable SONiC image. For any code update in a container image, however minor, requires re-build of the entire SONiC image and the rest of the heavy weight process to qualify the image to run in a production switch followed by install of the image in controlled phases with a mandatory reboot required.

## Proposal:
Build the image as today. Install the image as today. In addition configure a subset of dockers as "*could be kube managed*", which could even be hardcoded in minigraph.py. Whenever the switch would join a master and if the master has a manifest for a feature marked as kube-managed for this node, master deploys the container per manifest.

For any code update for a container, update the container image, qualify the container image, upload to registry, update manifest, and the infrastructure would carry it to all masters, which would do a safe deployment in nodes. For services that do not affect dataplane or support warm restart, the impact could be as simple as service restart. If not, some additional safety process may need to be followed before service restart.

This could be extended to features that are ***not part of SONiC image***, but could be enabled to run in SONiC switches.

The above proposal has multiple challenges to brainstorm and solve<br/>

***This doc addresses the SONiC node side changes only to adopt to the above proposal in phases.***

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
   * Meet the set Test requirements to qualify.
   * Switch must have a control over a known node-selector label that let switch control, when a manifest can be deployed.
   * Masters control what manifests to deploy and switches/nodes control when to deploy.
   * Containers are expected to call a script at host, on post-start & pre-exit, that record their state.
       
    
# Design proposal

## Current behavior
* A feature is managed by systemd.
* A feature has a systemd service file and one or more bash scripts that honor the complex dependency rules set for the feature.
* A feature's change of state could affect the state of other features.
* All the complex dependencies across features are met through systemd service management.

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/local_mode.png)

## Proposed behavior at high level

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/kube_mode.png)

![](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/transition.png)

* Maintain the current behavior (*as given above*) in new mode with exception of few updates as explained below.
   * There would not be any changes required in the .service or bash scripts associated with the service, except for few minor updates described below.
   
* The systemd would continue to manage features running in both local & kubernetes mode. 
   *  The current set of systemctl commands would continue to manage as before in both modes.
   
* For kubernetes controlled features, master decides on *what to deploy* through manifests and node controls the *when to deploy* through labels.
   * The kubernetes manifests are ***required*** to honor the following as node-selector labels.
      * `<feature name>_enabled=true`  -- This would be used to control start/stop deploy by kube
      * `<feature name>_<version>_enabled=true` -- This would be used to disable a version, which is already available locally or a higher version is running.
   * The manifest could add more labels to select the eligible nodes, based on OS version, platform, HWSKU, device-mode, ...
   * The node upon joining the master would create labels for OS version, platform, HWSKU, device-mode, ..., as self description
   * Master would deploy on nodes that match *all* labels.

*  Replace a subset of docker commands with a new set of "system container" commands

   In this hybrid mode of local & kube managing dockers, the docker start/stop/kill involves create/remove of kubernetes labels, additionally. The containers started by kubernetes do not use feature name as container name. Hence all docker commands that need docker name, would need to use docker-ID instead. 
   
   To accomplish this, the docker commands are replaced as listed below.

   * docker start --> system container start
   * docker stop  --> system container stop
   * docker kill  --> system container kill
   * docker wait  --> system container wait
   * Use `system container id` command to get container ID to use with docker commands that require name or ID like, docker exec/inspect/...
   
   
   The bash scripts called by systemd service would be updated to call these new commands in place of docker commands. In addition, any script that call docker commands will be switched to these new commands. A sample could be the reboot scripts, which call `docker kill/stop ...`.
   
   
* The new "system container ..." commands in brief<br/>
   * Container start<br/>
     Do a docker start, if in local mode, else create a label that would let kubelet start.
     
   * Container stop<br/>
      Do a docker stop and in addition remove the label that would let kubelet stop deploying. 
      
   * Container kill<br/>
      Do a docker kill and remove the label to disable kube deploy.<br/> 
     
   * container wait<br/>
      Do a docker wait on container ID, if it is started. If not, wait until kube deploys, which would set `remote_state=pending`, switch the state as `remote_state=ready` and then proceed to wait on the container ID
      
   * Container id<br/>
      This returns the container ID of the feature. This can be used for docker commands that demand name or ID. All running dockers are required to record their container ID in the STATE-DB and this command fetch the ID from there.
      Note: There is no control on names of the dockers started by kubernetes
 
* The containers started in either mode, are required to record their start & end as follows in STATE-DB.
  This informtion would be helpful to learn/show the current status and as well the actions to take for start/stop/wait/...
   * On post-start
      * `current_owner = local/kube` 
      * `docker_id = <ID of the container>`
    
     The start.sh of the container (*called from supervisord*) is updated to call `system container state <name> up <kube/local>`, which in turn would do the above update. The application process is started after the call to container_state script.
      
   * On pre-stop
      * `current_owner = none` 
      * `docker_id = ""`
      
     A local monitor script is added to supervisord. This script is started by start.sh inside the container under supervisord control. This script sleeps until SIGTERM. Upon SIGTERM, call `system container state <name> down`, which in turn would do the above update.
     
      Please note, in either mode, docker kill will *not* give an opportunity for graceful stop. Hence explicitly call `/etc/sonic/scripts/container_state <name> down` to update the container state.
     
   The containers that could be managed by kube, ***must*** call the `system container state ...` commands. It would be handy, if all containers follow this irrespective of whether kube may or may not manage it, as that way STATE-DB/FEATURE table could be one place to get the status of all active features. The code that gets i/p from this table has to be aware of the possibility of not all containers may call it, but it can be assured that all kube manageable containers would have an entry.
   
*  The hostcfgd & a daemon watching STATE-DB, helps switch between local and kube modes and from kube to kube.
   
   This is accomplished by service restart or add/remove of kubernetes label.
 
     
* A daemon could help switch from kubernetes to local if deploy would not happen for a period.

  When a feature remain pending for kube deployment, with no local conatainer running, a daemon could watch and switch over to local, if configured so. 
  
*  Systemd service install for new kubernetes features.

   The features that are not part of SONiC image would not have service files in the image and hence not in the switch too. The service files and an entry in FEATURE table are ***required*** to enable a feature run in a switch.
   
   There are multiple ways of accomplishing this requirement. This proposal would include a CLI command for a feature with simple requirements only. This command would accept list of other features, this feature depends on and create the required .service & bash scripts.
   
* Reboot support
  
  Meet the requirements for warm, fast & cold reboots. Details below.
  
* Image management
  
  Each deployment by kube, is likely to download a new image.This implies the need for image manaagement/garbage collection of unused images.
  This proposal includes a simple image management solution. The base idea would be to set some rules to qualify the last downloaded image as good.
  
  Once deemed good:
    * The older images *could* be purged
    * This new image *could* be tagged as local
    * The original local container image (part of SONiC image) *could* be purged<br/>
    
  All the "*could be*" are tunable with configuration.
  This would be a phase-1 solution, which would be further deep dived into, in future updates.

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
   
   no_fallback_to_local = true/false;           When set_owner == kube, it could fallback to local image, when/where kube deployment
                                                is not active.
                                                Set to True, to disable any fallback.
                                                Default: false.
   
   kube_failure_detection = <N>;                When set_owner == kube and if container is not running for N minutes, it is 
                                                considered as "failed". The alert logs will be raised.
                                                A value of 0 implies infinity, implying no failure monitoring.
                                                Default: 0
                                                                                                  
```
 ### Image management configuration:
```
   Key: "IMAGE_MGMT|GLOBAL"                     Provides the global image management settings for all features.
                                                A feature could override with its own settings.

   Disable = <true/false>;                      Disable image management. Default: False
                                                                  
   active_time_to_mark_good = <N>[s/m/h/d];     When the feature remains active >= N,  it is deemed good.
                                                STATE-DB tracks the state of a feature.
                                                A value of 0 implies, no check.
                                                Defaults to 0.
   
   purge_older_image = <true/false>;            Upon finding new image as good, purge the older ones
                                                Default: False

   tag_new_as_local = <true/false>;             Upon finding new image as good, tag it as local image.
                                                With this update, upon set_owner=local or fallback, this new image
                                                will run as local.
                                                Default: False

   purge_local_copy = <true/false>;             Upon tagging new one as local, purge the original local image from the disk.
                                                The original local copy is part of SONiC image.
                                                NOTE: This would block from restoring back to factory default setting
                                                Default: False


   Key: "IMAGE_MGMT|<feature>"                  Provides a way to override the global image management settings.
                                                for this feature only. One/subset/all the above could be re-configured.
                                                The global settings would act as default, if absent.

   
```
## STATE-DB
   ### Kubernetes Server Status:
```
   key: "KUBERNETES_MASTER|SERVER"
   connected           = True/False             This switch has joined the master as a node
   server_ip           = <IP address of server> The IP of the server
   server_reachability = True/False             The server reachability. 
   last_update_ts =    = <Timestamp of last update>  

```

   ### Feature Status
```
   Key: "FEATURE|<name>"
   current_owner           = local/kube/none/"";   
                                              Empty or none implies that this container is not running
                                              
   last_update_ts = <second since epoch>      The timestamp of last owner update
   
   container-id            = ""/"<container ID>";
                                              Set to ID of the container, when running, else empty string.
                                              
   remote_state            = ""/"none"/"ready"/"pending"/"running"/"stopped";
                                              Helps with dynamic transition to kube deployment.
                                           
   container_version       = <version of running container image>;
                                              <Major>.<Minor>.<Patch>. Local container images may not have any, which
                                              would default to 0.0.0.
                                              
 ```

      
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

#### config feature <property name> <feature name>  <value>
   This command can be used to sets all properties of a FEATURE.<br/>
  
     ```
     admin@str-s6000-acs-13:~$ show  feature config lldp
     Feature    State    AutoRestart    Owner
     ---------  -------  -------------  -------
     lldp       enabled  enabled        kube
     admin@str-s6000-acs-13:~$ sudo config feature owner lldp local
     admin@str-s6000-acs-13:~$ show  feature config lldp
     Feature    State    AutoRestart    Owner
     ---------  -------  -------------  -------
     ```
   
#### config feature install <name> [<required services>]
   Every feature requires .service & bash scripts to enable systemd to manage it. The features that are part of SONiC image has those files embedded. This command can be used to create the .service & bash scripts.  
  
  If the required list is not provided, it would default to "swss" as the required service.
  
  On image upgrade, if that involves carrying config over, either these created files need to be carried along or run this command in the new image for all kube-only features.
   
   
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
   
#### show feature status <name>
   This would list FEATURE table data from both CONFIG-DB & STATE-DB<br/>
   ```
   admin@str-s6000-acs-13:~$ show feature status snmp
   Feature    State    AutoRestart    SystemState    UpdateTime           ContainerId    Version      SetOwner    CurrentOwner
   ---------  -------  -------------  -------------  -------------------  -------------  -----------  ----------  --------------
   snmp       enabled  enabled        up             2020-12-08 22:59:57  snmp           20201230.80  kube        local
   ```
 State - The configured state as enabled/disabled<br/>
 AutoRestart -- The configured value<br/>
 SystemState -- The current systemctl status of the feature<br/>
 UpdateTime -- The last update time to this entry<br/>
 Container ID -- ID of the container if the feature is running.<br/>
 Version -- The version of current running or last run container image<br/>
 SetOwner -- As configured<br/>
 CurrentOwner -- Current owner of the running container.<br/>
 <br/>
Note: SystemState == Up does not really mean the feature is running, as in case of remote management by Kube, the deployment could be delayed. A non-empty container-id implies that the feature is indeed running.<br/>
# Reboot support

## Warm-reboot support
   This [warm-reboot](https://github.com/Azure/SONiC/blob/master/doc/warm-reboot/SONiC_Warmboot.md) support is for updating/restarting with no data-plane disruption. The `/usr/bin/warm_reboot` script is a complex script that does many pre-requisites, kill the containers and eventually call a specific command for reboot. The individual service level support for warm-start lies within its code/implementation-logic. When configured for warm start, upon start-up, the service should be able to acquire its i/p data from all its channels as ever, but instead of pushing it in entirety to the consumer/DB, read the pre-boot data (which is made available in APP-DB), find the diffs as stale/new/update and only push the diffs. With every app doing it and, with some additional complex steps for critical processes like orchagent & syncd, the data plane traffic goes unaffected, except for the changes pushed into ASIC,  which is a normal runtime experience of consuming changes as it happens.
   
   In short if a service supports warmboot, it would continue to support in both local & kube modes transparently.</br>
   The warm_reboot script needs few updates as below.<br/>
   * Disable kubelet service (`systemctl disable kubelet`)
   * Replace all `docker stop/kill` commands with corresponding `system container stop/kill` commands, with an option to skip any updates. 
   * kubelet config/context, kube certs/keys and, /etc/sonic/kube_admin.conf  needs to be carried over to the new image.
   * Carry the .service & bash scripts created for kube only features to new image.
   * Ensure all kube managed features are enabled to fallback to local image.
 
   
   Reason for the changes:
   * With kubelet running, it would restart any container that is manually stopped or killed. Hence disable it
   * Containers started by kube, can't be referred by name. The `system container kill` command would fetch the corresponding docker-id from STATE-DB  and use that to kill.
      * Pass the option to skip any updates to save time, as system is going for a reboot.
   * Carry over kubelet related context, to enable transparent join and interaction with master.
   * The .service & bash scripts for kube only features, may not be available in new image. To save the time of re-create, just take the files over to the new image.
   * Upon reboot, the switch could take some solid time to establish connection with kubernetes master. Until then, the containers that are marked as kube-managed with no fallback, can't start. Hence ensure availability of local image & fallback, so the containers can start immediately from local copy. The set_owner remaining as kube, will help kube to manage, whenever the switch successfully connects to the master.<br/>BTW, connecting to the master is done by kubelet transparently.
   * If kube downloaded image is later then local image, it would cause a service restart, when kubelet connects upon warm-reboot. To avoid, if downloaded version is later then destination version, carry over the image of later version.
   
   For new features that are not known to warm-reboot script, some hooks could be allowed for registration of feature-custom scripts. This could help with some preparation steps before reboot, like caching some data, setting some DB values, ...
   
## Fast-reboot
   This [fast-reboot](https://github.com/Azure/SONiC/wiki/Fast-Reboot) support aims to help image-udpate and restart, with minimal data-plane traffic disruption. The implementation is similar to warm-reboot, that logic is embedded in the fast-boot script, additional utilities and some tweaks inside the code/logic of individual services that supports. Here again any service level support lies within the internal code/logic.
   
   In short, the summary and the required changes, including hooks for new features, are the same as in warm-reboot support, just that here use fast-reboot script.
  
   
## reboot
Upon reboot, all kube managed features would start from 'local' image, if fallback is set to True. The kube managed features with no fallback, would be started by kubelet, upon joining the master. If the kubernetes master is reachable, this would not add much overhead. 

NOTE: Features that are marked as kube owned with fallback and if last downloaded image is not tagged as local, there would be a local to kube transition, upon kubelet connecting to master and deploying the version that is higher.
   
# Multi-ASIC support:

***Note:*** The kubernetes management of Multi-ASIC platform would be a ***best*** effort approach. Any additional work required for multi-asic support would be outside the scope of this doc.

In multi-asic platform,
  * Some features run in single instance like in other platforms. e.g. ACMS
  * Some features run in multiple instances as one per ASIC. e.g. syncd
  * Some features run in multiple instances as one per ASIC and one in host too. e.g. database
  
All these features single or multiple, share the same image with only runtime differences.<br/>

## Manifests
All the different docker containers are created with ASIC specific runtime differences.
For a sample, it differs in
* docker name
* path mounts
  * socket path(s) for redis
  * feature specific socket paths
* Environment variables
  * NAMESPACE_ID
* Container network

All of the above can be expressed in manifests. There can be multiple manifests as one per ASIC and one for host.


## FEATURE config:
The configuration of FEATURE is in CONFIG-DB. This controls set_owner, fallback, enabled,... parameters per FEATURE.

The config could be distributed per ASIC or it could be one shared instance that controls across all ASICs & host.

The proposal is to have ***FEATURE config in single host instance*** that serves all ASICs & host. 
The same instance, which carries system level config like TACACS, syslog, ...


## FEATURE status:
* The status has to be instance specific and hence would be ***distributed as per ASIC and one for host in STATE-DB***. 
* The hostcfgd would watch all instances of STATE-DB to make effect.
   

# Kubernetes cluster unreachable impacts
The kubernetes deployment is initiated & managed by Kubernetes master, through kubelet agent running in switch. This signifies the need for High-avaialbility of master. To meet the requirement, the kubernetes is installed as a cluster of 3 or 5 masters, under a single VIP. Despite all this, there are always scenarios where a node may lose its connectivity to Kubernetes master. Here are some heads-up and expected reactions.

* kubelet will continue to retry until it is connected to master.
* kubelet will continue to work per last context received from master
  * Say master applied manifest for "feature-foo" version "1.0.0" and it is successfully deployed in node
  * Say, later master become unreachable
  * Say, user removes the feature-foo manifest at master.
  * But node will continue to run feature-foo and infact, if it would crash/restarted, kubelet will re-deploy, as kubelet is not aware of the manifest removal.
  * The feature-foo will be undeployed, only upon node reaching master (which is in future)
  
* SONiC impacts
  * When using new manifests for version upgrade, the older one may not get removed (as per master plan), but continue to run while higher version is already running.
  * kubelet could deploy a feature, when any of the following is true.
    * systemctl stopped the feature (systemct status down)
    * Ownership of the feature switched to "local"
    * A higher version of the same feature running
    * This version of the feature is expliciltly blocked locally by node.
    
* SONiC handling:

  Whenever a container comes up, the start.sh is expected to call "container_startup.py". This script would check the current status of the node and if this deployment is incorrect/unexpected, it puts this start script to sleep forever with periodic logs.
  
# Manifests generation:
***NOTE***: The discussion below on manifests generation is outside the scope of this doc.

*This discussion here is to record the challenge to solve and kick off the brainstorming with a proposal.*

The manifests set the runtime environment for a docker. This include, name, mounts, environment variables, and more.  A sample manifest is [here](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/snmp_pod_manifest.yaml) for reference.

In SONiC these runtime environment are hard coded in the systemd's start command as part of `docker create`, inside the bash script's (e.g. /usr/bin/snmp.sh) start() function.

These bash scripts are auto-created using templates, as part of image build.

## Proposal: Extend the auto-create code to create manifests too.
  * A separate template could be provided for manifest creation
  * A manifest per feature per ASIC is created.
    * Platform & HWSKU related paths can be simplified with pre-created softlinks that point to approrpriate dir for that platform/hardware sku.
    * This could avoid the need to go per platform per HWSKU granularity.
    * For multi-ASIC, as runtime parameters differs across multiple instances, there has to be multiple manifests as one per instance.
  * Use these generated manifests in nightly tests to help validate
    * preferably, it could be extended to VS tests that run as part of PR-builds, to help catch failure ahead.
    
  
# Service install for kube managed features

Points to note:
   * The features managed by kube only (*no local image*), will not have a service file locally in the image, hence it needs to be explicitly created/installed.
   * The features that are in hybrid mode as local/kube managed, a service file would indeed be available locally. Yet, an updated image that could be brought in by kube, could demand a tweak in the service file or start/stop/wait scripts, which requires an explicit update.
   * Every kube-managed feature should have an entry in CONFIG-DB, FEATURE table.
   * Any utility that requires the list of all features would refer to this FEATURE table in CONFIG-DB.
   
 A couple of proposals are listed below. The poposal-1, the easiest option is provided as part of this doc. The rest are *only* suggestions for brainstorming.
 
 ## Proposal - 1:
  Provide a way to create a .service and bash scripts for a feature with simple requirements like, 
  
  * This feature depends on zero or more features &&
  * No other feature depends on this feature &&
  * Transparent to warm-reboot & fast-reboot
    implying it does not affect data plane traffic directly or indirectly.
      
  The `sudo config feature install <name> [<list of reequired services>]` create/update the service files & bash scripts per configuration. In the absence of required services list, it would default to `swss`.
  
  
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
   
   
 ## Proposal - 3:
   *  For every new feature, make the .service & bash scripts as a package and available in a known location.
   *  Propagate to the switches in push or pull mode.
        
   
## Proposal - ...:
   The new upcoming feature Application-Extension is addressing this challenge in package driven format. Brainstorm that plan and make a unified way.


# Image management
  For a kube managed container, when updates happen, it downloads a new image, which can eventually result in multiple container images for a single feature.
  
  This doc addresses with one simple solution. This needs more deep-diving to understand all challenges and brainstorm the options, which is outside the scope of this doc.
  
  ## Garbage collection:
  The kubelet's [garbage collection](https://kubernetes.io/docs/concepts/cluster-administration/kubelet-garbage-collection/) feature could be utilized.<br/>
  For a tighter control, a custom soultion might be required which could monitor & manage as configured.
  
  
# Failure mode detection & rollback
  For kubernetes managed features, when the system is expecting kube to deploy, many external factors could block the deployment. The kube deployment could be unhealthy and may need to block kube from deploying this version. 
  
  This brings in two questions<br/>
  
  a)  How to detect the failure?<br/>
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
     * set remote_state = "none"
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
  * For each update, create a new manifest, instead of updating existing.
    In addition to helping with Safety check, using new manifest helps with quick transition from one to anoter in a switch with very low service down time.
  * The manifest would get an unique label as <feature name>_<version>_enabled=true as of NodeSelector labels
  * An external entity identifies the subset of nodes to update.
  * For each node in that set, add this unique label, that will make the selected subset of nodes as eligible for update
  * Wait for deployment to a batch complete. Give sometime to watch the health.
  * Remove the label used by older manifest for these nodes, to ensure kube would not attempt to deploy older instance
    Node may do this removal. This action would ensure the label is removed, if node has problem reaching kube master.
  * Depending on the result, either
    * repeat the above steps from identifying next set of nodes to update<br/>
    OR
    * remove the new label and add the old label to rollback for each node.
     
# Implementation phases:
The final goal for this work item would be to manage nearly all container images on SONiC switch. The proposal here is to take smaller steps towards this goal.

## Phase 1:
   Support services that meet ***all*** of the following criteria

   * A kube-only feature that is not available in SONiC image
   * A simple feature that has few *required* services and no service depends on this feature.
   * A feature that does not affect dataplane traffic
      * Transparent to warm-reboot & fast-reboot.
    
The config command could be used to create the FEATURE entry and the required systemd files.

## Phase 2:
  Extend support to features that meet ***all*** of the following criteria:
   * A locally available feature which can be switched between local & kube.
   * A feature that does not affect dataplane, like snmp, pmon, lldp, dhcp_relay,...
 
The service files are already available. The FEATURE table would need to be updated, with the minium of set_owner.


# RFE -- For brain storming
## Warm-restart 
During runtime, a FEATURE could auto restart  using warm-restart to minimize traffic disruptions. The possible restart scenarios are listed below.
  1. When kube is re-deploying per updated manifest
  2. When kube is deploying while in LOCAL mode -- local-to-kube transition
  3. When owner is set to `local` and kube-to-local transition occurs
  4. When container exits due to internal failure and systemd auto-restart.
  
With exception of the 'failure exit', the rest are initiated to do an expectes/explicit transition. In all these cases, one may do a warm restart, to minimize impact to an active switch.

## Tag downloaded as local image
The fallback to local is a very handy feature to be able to 
  * start a service quickly on reboot.
  * Run a service when kube master is unreachable or join not initiated.
  * run local when kube master has some issues w.r.t deploying.

The version of the local image is highly likely to be lower than the downloaded image. Falling back local image of lower version is *not* advisable for following reasons.
  * The lower version may have bugs, or not compatible with state left behind by later version.
  * When kube connects, the service restart is imminent, causing two starts in succession upon boot.
  
To avoid falling back to lower version, we could have a qualifying time to assess health of a FEATURE and when deemed healthy, remove the local image and tag the downloaded as local. This way we have the latest downloaded as local too. Upon boot, the FEATURE could start from local and when kube is ready to deploy, it could back off, when it notices the same version is already running.

