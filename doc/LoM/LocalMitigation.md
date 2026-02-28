SONiC Local Mitigations (LoM) Service
=====================================

# Objective
1. To bring device-health monitoring's TTD & TTM drastically down from minutes to seconds
2. To enhance device health monitoring & mitigation via
   - Increasing its reliability & efficiency
   - Extend its device data accessibility to more than what is exported.
   
# Goals
1. Run a containerized service inside the switch that monitors the switch constantly, reports any anomalies and mitigate as needed.
2. Provide a system based off of multiple independent worker units called **actions**.
3. Provide a way to add/update an action that does one of the following.
   - Run a anomaly detection.
   - Run a safety check that might be required for mitigation.
   - Run mitigation for detected anomaly.
   - Run any cleanup required as needed.
4. Provide a unified way to describe each action in schema.
5. Provide a unified way to configure the actions.
6. Provide a way to run a set of actions sequentially to mitigate a detected action.
7. Report run of any action to external clients via export to Event-Hub.

# Problem to solve
Today all detections & mitigations are performed by external services. The problems or short falls we have are 
1. As any detection is based on exported data, the latency involved delays the alerting. This latency could be in minutes.
2. Any detecton algorithm is restricted to exported data only.
   - Any ask for additional data can only be available as part of next OS release and its rollout, which is in the order of months and years to cover entire fleet
3. Any problem/failure in exporting will result in alerts not being created.
   - There have been cases of missing data exports hence missed alerts.
   - It is not easy to alert for gaps in missed exports
   - Exports channels are not reliable inherently
4. Finding anomaly in the heavy volume of exported data, is like finding a needle in Haystack and cost heavily on resources.
5. Any inability to access the switch, will block a mitigation action.
6. The evolving OS updates often conflicts and invalidates external service's ability to detect/mitigate, silently.
   - e.g., A remove/re-write of a log message could affect the service that is detecting based on that log.
   - We don't have process to sync/test evolving OS with external services
7. An external service has scaling issues in managing thousands of switches.
8. A **single** service code is expected to handle multiple vendors, platforms & OS versions which is a very complex ask that translates to increased probabilities for gaps/failures. 


# Proposal
1. Run a dedicated service that can run all detection & mitigation actions locally within the switch.
   - The detection actions can watch forever until anomaly is detected
   - When detected, run configured mitigation actions, which are often preceded by safety-check actions
   - The entire set of actions to run upon a detection is pre-configured and explicitly ordered, called binding-sequence. 
   - The mitigation actions hence the safety checks are not mandatory. In other words there can be an empty binding sequence.. 
2. An action can be a detection for an anomaly, a mitigation action for an anomaly, a safety-check to precede mitigation and a cleanup, ... 
3. Actions can vary widely by logic and/or config.
4. Actions are vetted by nightly tests hence verfied to work on the hosting OS.
5. Actions are implemented as plugins.
6. Actions are defined by Schema and schema specifies configurable knobs.
7. Service is built with static config, which can be updated during runtime.
8. The LoM system is versioned.
9. LoM provides a CLI to show running config, status and stats.
10. LoM publishes all counters to Geneva Metrics
11. Results of all actions are published to Event-Hub.

# Benefits
1. Running locally, hence monitoring the switch constantly will give the **BEST** possible TTD (_Time to Detect_).
2. Running locally provides access to all data in the switch, whereas an external service strictly relies on exported data _only_.
3. Local mitigation is triggered right upon an anomaly detection, hence it will give the **BEST** possible TTM (_Time To Mitigate_).
   - Local mitigations can have TTM in seconds
4. Running locally improves the performance, availability & efficiency.
   - Even an inaccessible device could get mitigated
5. Running locally enables heartbeats that explicitly indicate Device health.
   - A healthy system may report no anomaly but still sends heartbeats to indicate its good health.
6. Running locally enables actions/service to be vetted in nightly tests.
7. The actions can be customized for this OS version and platform.
   - Build/run time can pick the right version.
8. The plugin model allows for granular update of actions to the affected devices ***only*** with a simple file copy & config update.
   - An action/plugin could be deployed in hours across fleet to check/mitigate a newly found bug in a released OS.
   - Plugin update does not affect control & Data planes
9. The actions are defined in YANG schema, hence the published reports are structured 
10. Actions' runs have full visibility via gNMI in EVENT-HUB.
11. For any new SONiC bug in released OS, it could be well managed via small/simple detection/mitigation actions that can be rolled out in hours across the fleet.
    - Create detection & mitigation action & update automated tests
    - Identify target releases
    - Kick off auto tests runs on target releases.
    - Deploy the updated LoM to target devices.
12. FUSE may continue to deploy this OS version with known issue, as it would transparently *also* install the actions that detect/mitigate.   
13. Supports enable/disable of actions via config update.
    

# A Use case:
## Link flap / CRC / Discards
For a link the common issues are flaps, CRC-errors & discards. Here we need a way to watch for it with appropriate algorithm to identify anomalies. When an anomaly is detected, the mitigation is bring link down. But this demands basic safety checks. A detection-action can be configured with appropriate mitigation actions to run upon detection, along with approriate safety checks to precede the mitigation action. This is called action sequence or binding sequence.

### Link anomaly Detection action:
An action for link flap may be written for flap by observing STATE-DB changes. An action for CRC-errors/discards may watch counters. These actions are run forever, often cache data at different time points and run an algorithm on the cached data to detect an anomaly. Upon detection, the detected anomaly is published via gNMI channel to EventHub in few seconds. Every published action is also logged as a fallback. Data published & logged are as per schema.

### Safety check action:
The mitigation action for a failing link, is to bring the link down. But this demands a safety check to assess the capacity of not just this device, but more of a global scope. One may write a local safety check action, that could succeed if device has the link availability > 75% (_this magic number is configurable_). When this local check fails, the action can reach out to an external SCS service for a global check. This action returns success, if mitigation can happen, else return failure. In either case, its result is published & logged. A success/green-flag will allow mitigation to run.

### Mitigation action:
This action can set the admin down for the link. This action is published.

### Sequence completion:
-   The original detected anomaly is now re-published with final result as success or not.
     - The success implies a successful mitgation of the detected anomaly.
     - A failure implies that the anomaly is not locally mitigated. The failure gives appropriate error code that indicates the reason for failure. 
-   The completon is expected within seconds of detection.
-   Every action that is invoked as part of sequence has a set timeout, and must end by then along with overall timeout for entire sequence to complete.
-   A failing action or timeout will abort the sequence at that point which would skip subsequently ordered actions unless marked as mandatory.
-   During a sequnce run upon detection, the heartbeats are published more frequently. The HB would carry info on current running action.
-   If the sequence fails to mitigate, the external service can take over mitigation as is today.
-   In scenario where we mitigate successfully, the TTM is in couple of seconds. For any failure, we still get TTD in seconds.</br>
NOTE: An ICM is fired for every detected anomaly. If mitigation is done by LoM, the ICM will be marked "_mitigated_".

### Sequencing & config
Every detection action is tied to corresponding safety check & mitigation actions. This is called sequencing, by adding them in ordered sequence. A sequence progresses only if last executed action succeeds. Any failure aborts the sequence and causes the detected anomaly to be re-published with failure code indicating "_mitigation attempt failed_". This is called binding sequence. The Service comes with built-in actions and associated seqeunces.
Every action could be fine tuned via some configurable knobs. A SONiC CLI or configlet could do.

## Memory utilization
This is a complex probem as memory used by a daemon could vary based on its load (_e.g. count of peers, routes, route-maps configured_). This demands an custom detection per daemon with dynamically computed threshold. The detection needs to distinguish between "_is memory consumption growing constantly_" vs "_transient blips_". This algorithm being complex, might need few tweaks & updates overtime before it become solid. Hence hard coding this into image will not fit. But actions are small plugins/minions that can be easily updated w/o impact to control/data plane, hence allows for frequent updates,.

### Detection
The action does the monitoring. We can have variations per platform, target OS version and even cluster type. This is vetted in nightly tests for  all  target platform & OS version. It constantly monitors. It can cache usage in various time points as required by algorithm to do a proper analysis. This detection action is kicked off at the start and run until detected or disabled.

### Safety-check
Asses the daemon that is in trouble to verify if its restart will impact Dataplane or not. If not, it returns success, else returns failure, which will abort sequence and no mitigation action is executed. This will also look at the service restart history to ensure that no more than N restarts is attempted in M seconds.

### Mitigation
This may be just service restart or more (_say remove/reset files/data_). The action is executed and its result is published

### Sequence completion:
- Anomaly is re-published with mitigation result. An external service may take over mitigation on any failure.

## conclusion
- The actions the real workers that do the detection, mitigation & checks.
- The actions have wealth of data to access - Literally any.
- They are anytime updatable as we see need for tuning.
- The actions are independent entities bound together by config
- Being independent helps accelerate them to evolve quickly with no impact to others.
- Being built-in they are OS & platform specific and forced to evolve with OS updates by nightly tests.
- Mitigation happens in seconds if it would not have data plane impact.


# Design
![image](https://github.com/renukamanavalan/SONiC/assets/47282725/14fcd472-d68d-4a55-8e85-85f7abd1f5c6)

![image](https://github.com/renukamanavalan/SONiC/assets/47282725/feca5cfd-5aa8-46cf-9383-d27b1b960987)



## Core components
### Engine
This is the core controller of the LoM system. The engine runs the system by raising requests to registered actions and manages binding/mitigation sequences.

All plugins register with engine. Engine sends requests to all detection actions right upon registration. Engine identifies first action of a binding-sequence as a detection-action.

The detection actions run forever until an anomaly is detected or it gets disabled. In a healthy system, a detection action may run for days/weeks/months w/o returning. As detection actions run forever, it periodically sends heartbeats to engine to inform that it is active & healthy.

The engine publishes its own heartbeats periodically using SONiC events channel via gNMI to external services. In each heartbeat published it list all the actions it received hteartbeats from, since its last heartbeat publish. An external alert service may compare the list of actions in heartbeat with list of expected actions from golden config. It could raise an alert for any difference.

When a detection-action returns with success, indicating that an anomaly is detected, the engine kicks off mitigation sequence. If Engine is already in the middle of another sequence, it put this newly detected anomaly in wait Q, until current sequence is complete. In other words the engine ensures only one mitgation sequence can be active at anytime.

During a mitigation sequence, it invokes actions sequentially as ordered in config. It sets timeout for each action and also sets a timeout for completion of the entire sequence. If an action returns failure or a timeout occurs, engine aborts the sequence by not calling rest of the actions in the sequence, unless marked as mandatory. On success, every action in the sequence is invoked in order until end. Each action's result is published irrespective of success/failure. Each action when invoked, is provided with data/response returned by all preceding actions in the sequence, This gives dynamic context of the sequence to the just invoked action. As data from each action is per its schema, the action receiving the  data knows the entire data type. An action that needs data from another sets a binding via schema. 

At the end of a sequence, which may be upon calling all actions or upon abort, the original detected anomaly is re-published with either the the result of last action or timeout. At the completion of a sequence, the request action is re-issued to the first action of the sequence, which is a detection action.

LoM ensure periodic re-publish of an active anomaly until fixed, with the configurable period.

For timedout actions, they are kept in cache as active so as to block engine from sending another request. The plugin's i/f is intentionally made to be simple. The agreement with plugin is that, only one active request will be raised anytime per plugin. Hence a timedout action must return before it can be called again. The timedout action's response is still published even though it is stale as corresponding sequence is already aborted. If a sequence demands an action which still has an outstanding request, then the sequence is put in pending state, until either this sequence timesout or the request returns, whichever happens earlier.


### Plugin Manager
The plugin Manager manages a set of plugins per config. It interfaces the plugins to the engine. It loads & inits the plugins with config. Registers successfully initialized plugins with engine. Any requests engine initiates for a plugin is received by Plugin Manager and route it to appropriate plugin and re-route the plugin's response to engine, including heartbeats raised by long running plugins.

The plugin manager defines a simple plugin i/f, where the plugin never calls out, with exception of periodic heartbeat notifications, but gets called in with just 4 simple blocking methods. On any disable/new/update do appropriate de/re-register the plugins with engine. For any mis-behavior by plugins, manager raises syslog periodically until fixed. The plugin manager also ensures the contract set by plugin i/f is strictly adhered to. It runs the set of plugins under a shared process space.

On the other hand, the plugins can be compiled into Plugin Manager statically. This can drastically bring down the built binary size, hence container image size. The plugin Manager can also load plugins from standalone binaries. For a quick plugin update, the new binary may be copied to a path accessible by Plugin Manager, update the plugin revision in procs's config. The config manager will send a SIGHUP to pluginMgr which will reload its config and for plugin updates, it will de-register current and load the new.

Based on plugins configuration in procs config, one or more instances of plugin manager could run anytime.

### Supervisord & rsyslogd
The supervisord to start & manage all processes and rsyslogd to send logs out to host.

### Plugins
The plugins are the core workers that runs an action. A plugin == An action. An action is a standalone entity for a *single* purpose, like CRC-detection/link-availability-check/link-down mitigation/... Each plugin is independent and standalone with no dependency or awareness of other workers. The only binding it may have is the i/p data it requires from preceding plugins. This it expresses via schema with leaf-ref to schemas of all possible plugins/actions that could precede. For example, a link safety check references all link detection actions. A plugin is not aware of other plugins and act pretty independently.

A plugin operates under the process space of PluginMgr that has loaded it. There can be multiple plugins loaded by a single Plugin Mgr proc, as per procs' config. When the plugins access a shared resource that does not support concurrent access, appropriate abstraction i/f be provided to manage. This interface accepts multiple clients on one side and let only on reach the resource at any time transparently. A sample could be SONiC redis-DB which does not support concurrent access across threads/go-routines. A redis-access i/f may be provided to manage multiple clients on one side and allow only one of them to reach DB at any time point for Get/Set. 

The plugins are the unit of actions with a simple i/f of 4 APIs only. All 4 APIs are synchronous even in the instances where a request may run for days/weeks/...</br>
This enables plugin writing to be easy and the dev may focus only on algorithm and LoM transparently handles the rest.

**init**  - Called with action's config only once at the startup. Here the plugin absorbs its config, do its initialization and as well may kick off some long running concurrent activities as needed. </br>
**GetId** - Ability to get ID & version of this plugin. The pluginMgr uses this to confirm the loaded plugin is the intended one. </br>
**Request** - Run the action's main job, which may be detection, safety-checks & mitigations. This will be invoked with or w/o timeout. This is raised multiple times as only one call at a time.</br>
**Shutdown** - Called upon disable of a plugin or system shutdown. This provides a way to close/de-init the plugin.</br>

Plugins may be compiled statically into Plugin Manager or it could be explicitly loaded from a standalone binary.

Plugins are versioned. The config sets the version to use. This allows for easy rollback via config update.

One may write variations of same plugin meant for different Platforms. The buildtime picks the right one.

## LoM Config
It has 4 sets of config and each is detailed in YANG schema.
### Globals.conf
As name signifies the global runtime settings, are system level settings like heartbeat interval. A sample set is below.
```
{
    "MAX_SEQ_TIMEOUT_SECS": 120,</br>
    "MIN_PERIODIC_LOG_PERIOD_SECS": 1,
    "ENGINE_HB_INTERVAL_SECS": 10,
    "INITIAL_DETECTION_REPORTING_FREQ_IN_MINS": 5,
    "SUBSEQUENT_DETECTION_REPORTING_FREQ_IN_MINS": 60,
    "INITIAL_DETECTION_REPORTING_MAX_COUNT": 12,
    "PLUGIN_MIN_ERR_CNT_TO_SKIP_HEARTBEAT" : 3
}
````

### Procs.conf
A plugin Mgr proc provides a shared process space and interfaces the plugins to the engine. This configuration provides the grouping of plugins under one or more shared process space. Each space is identified by a unique proc ID. A plugin Mgr proc instance is created per proc-id. The plugin mgr is provided with its proc ID, to enable the instance loads its set of plugins.

Each plugin instance is identified with name, ID & optionally path.. 

The build process builds pluginMgr with all the plugins integrated as one binary. This helps save binary size as all common base elemants used by every Go program gets shared. Hence the initial build generated config will have empty string for path. When path is empty, the pluginMgr expects a statically linked copy. In future, when a plugin is updated, it gets copied to a path accessible by pluginMgr and this path is saved in config. Here the Plugin Manager loads from given path.

```
{
        "procs": {
                "proc_0": {
                        "link_crc": {
                                "name": "link_crc",
                                "version": "1.0.0.0",
                                "path": ""
                        }
                }
        }
}
```


### bindings.conf
Any action to be executed is required to be part of a sequence, called binding sequence. The first action of a sequence is detection action. Hence the first actions of all sequences are expected to be unique.

If a sequence has only one action, it implies that this detection action is *not* configured with any mitigation actions. This is also called referred as empty-sequence.

When configured with mitigation action, there will be a minimum of 2 more actions in addition to the first, as first is "detection", second is "safety-check" and  third is "mitigation". There can be more. All are listed with sequence & timeout where needed. The info here should be unambiguous to help execute the actions in order.

A missing sequence defaults to 0. A missing timeout defaults to timeout from this action's config. A missing "mandatory" flag defaults to false. Note: Sequence across all actions have to be numerically unique and positive. The validation will help with these constraints.

```
{
    "bindings": [
        {
            "SequenceName": "link_crc_bind-0",
            "Priority": 0,
            "Timeout": 2,
            "Actions": [
                {
                    "name": "link_crc"
                },
                {
                    "name": "link_down_check",
                    "sequence": 1
                },
                {
                    "name": "link_down",
                    "timeout": 5,
                    "sequence": 2
                },
                {   
                    "name": "cleanup",
                    "timeout": 5,
                    "sequence": 3,
                    "mandatory": true
                }
            ]
        }
    ]
}
```


### Actions.conf
All actions have some shared config like disable, mimic, heartbeat frequency, .... Each action could have action specific configurable attributes. An example could be window size & thresholds for detections with rolling window, a minimum % of availability to succeed for a safety check and more. The shared configurable knobs are listed in base YANG schema shared by all actions' schema. Each action schema provides its proprietary configurable attributes. 

The actions config file is generated from YANG schema for all attributes that has "configure=true" with schema specified defaults.
The actions.confd dir will hold all the individual conf files.

```
{
        "link_crc": {
                "Name": "link_crc",
                "Type": "Detection",
                "Timeout": 0,
                "HeartbeatInt": 30,
                "Disable": false,
                "Mimic": false,
                "ActionKnobs": {
                        "DetectionFreqInSecs": 30,
                        "IfInErrorsDiffMinValue": 0,
                        "InUnicastPacketsMinValue": 100,
                        "OutUnicastPacketsMinValue": 100,
                        "OutlierRollingWindowSize": 5,
                        "MinCrcError": 0.000001,
                        "MinOutliersForDetection": 2,
                        "LookBackPeriodInSecs": 125
                }
        }
}
```

# Safety Traps
- The LoM code runs inside docker and hence restricted to the scope of docker.
- The docker is configured with limits on resources like CPU & memory. So a miscreant inside docker can't hijack the switch.
- First release will be done only with detection plugins. They only Get/subscribe to DB and publish their findings. No write is done on DB or host.
- Limit the max anomaly report frequence per anomaly key, so that LoM will not flood events channel with redundant alerts, yet repeatedly alert at a sane frequencey to ensure to get external service's attention.
- Any misbehaving plugin is disabled and error is periodically reported until plugin is re-registered. Re-register happens upon either plugin update or service restart. 
- Later when mitigation is enabled
   - Every action is reviewed with SMEs for approval.
   - Any action can be disabled via config, called Red button.
   - Red button management will be described in a differetnt HLD.
   - Red button updates will come with a SLA.
- Safety checks
  - Mitigation actions are *always* associated with safety checks
  - Safety checks may only be local, where it suffice.
  - Safety checks could reachout as needed.
- Mitigation sequence & individual actions are timed.
   - Every action is called with timeout.
   - Upon timeout the sequence  is aborted.
   - The overall sequence execution has its timeout too.
- Mitigation sequence publishes more frequent heartbeats
  - The heartbeat would indicate the current active action and it position in the sequence.
  - The hearbeat will also list completed actions 
  - The absence of two or more heartbeats could be taken for failure and external service will take over.
   - All mitigation actions being  idempotent, it would be benign if both LoM and external service act on a single anomaly,
- Mitigation actions are set with max frequency limit
  - A mitigation for a key can only happen once within last N seconds.
  - This avoids a or save from a rogue plugin.
- Controls are multi-layered.
  - Actions have their config to ensure sanity in their behavior.
     - A mis-behaving plugin may ignore/fail to honor config
  - At next level, Plugin Manager watches and disables mis-behaving plugins
  - Engine adds the final guard on plugins and disable miscreants
  - Any disable by PluginMgr and/or engine reflects out as periodic syslogs reporting the disable, until re-registration..
- Honor red button config which can disable one/many/all actions with SLA.
- Mitigation actions support mimic mode, where we can observe what could have happened w/o making any switch update.
  - A mimiced Link Down will report that it was about to bring link xyz down, but did not as it was in mimic mode.
  - These o/ps could be reviewed along with pre-cursor action results before we enable a mitigation.
- The engine Heartbeats will report the active detections currently running. During mitigation, the position in sequence is reported and heartbeats are more frequent during a sequence run.
   - Any diff between expected list of actions and actions listed in Heartbeats could raise an alert.
   - Absence of heartbeats indicate unhealthy LoM
  

# SONiC i/f
LoM is installed as SONiC service.

## LoM Service
LoM is a systemd maintained containerized service. Like Telemetry, this service is predominantly written in Go with a vision of supporting mult-language plugins in future. It is built as docker image with all required systemd's service related files and an entry in FEATURE table as enabled. The code resides in a dedicated sub module.

## CONFIG
LoM service comes with static config created during build time off of schema. The LoM publishes the status & stats to Geneva metrics. An updated config can be copied on to a path accessible by LoM container and it absorbs the update transparently. 
LoM comes with its own CLI for update/show of the config. All config entities are declared in schema.
The regular heartbeats will list all the active actions.


#### LoM|Counters
Stats are maintained as below to cover all actions. The stats are exported to Geneva metrics. A LoM-CLI command is available for show with support for streaming mode.
- Count of active actions
- Count of active detection actions
- Count of failed actions (enabled but failed to activate)
- Count of disabled actions
- count of mimiced actions
- Total count of anomaly detections made
- Total count of successful action runs
- Total count failed action runs ( Has non-zero result code )
- Total count of successful sequences
- Total count of failed sequences

#### LoM|liveCache:
LOM's CLI could be used to stream events as they are published by LoM to EventHub.


#### LoM|RedButton
- This is used to disable one/subset/all actions.
- Unlike other configurations, this RedButton config has a ***SLA*** to reach the target device as this could be disabling an action, which is critical that it is disabled within set SLA
- Red Button config is available in external DB, which could be Cosmos-DB.
- LoM-CLI could be used to read the current state


## LoM Visibility / State / Status
### SONiC events
Results of all actions are published w/o any constraints to Events Hub via SONiC gNMI. Even a stale response (_one that arrives after timeout_) is also published. The publish use LoM's gNMI channel. All publish o/p are per defined schema with backward compatibility.

### MDM Dashboard
Reports counters published over time.

#### syslog
All published events are also logged via syslog.
LoM reports all its internal info/error messages too via syslog.
For persistent errors, LoM reports periodically until fixed, to manage the unreliable syslog transport.

# Actions Update:
One of the core values of LoM is its management of diverse independent actions yet work in unison with single context during mitigation of detected anomaly. The actions are implemented as plugins to provide the flexibility and adaptability to take updates at run time w/o impacting control or data plane.

In the initial phases, the plugins may be cmpiled in and updates would be via entire LoM agent update. In future phases we support dynamic/runtime update of individual plugins.

## Update requirements
- To update/fix bugs in a published plugin
- To add a new plugin
- To update w/o requiring new SONiC image
- To update all affected versions in a fleet in short time.
- To update w/o impacting control/data plane

## Update creation
- Create a script (bash/Python/...) to vet your action logic.
- Create the plugin for the same using LoM Dev environment.
- Create test code for the same and integrate it with automated test suite.
- Update the config to include the plugin.
- Build the new LoM agent and deploy to SONiC switch in lab.
- Run the updated test suite to ensure the updated system is good in its current updated state.
   - Nightly tests run the updated test suite
- An update to existing plugin may follow subset of above steps based on extent of change.
- The built LoM agent is a self-installable archive.
 
## Update vetting
- Identify the target OS versions & Platform for this update.
- Auto create test pipelines for all target scenarios.
- The test pipeline will download the archive from a local repo onto DUT and run the downloaded archive to install.
- The nightly tests run the test suite that vets all available actions.
  
## Fleet upgrade
- Take help from FUSE
- FUSE need not do any device isolation for update as these updates are transparent to both control & data planes
- LoM-agent is versioned. The config as suggested by FUSE would help pick the right LoM version for each OS version.
- FUSE identifies the matching devices in current scope, download the archive and run the script associated with the archive.

## Fleet update status
- Configuration & current state would be visible in NSS.
- FUSE updae plan would be described in detail in a dedicated HLD.

   
# LoM config update
- As mentioned above the service comes with built-in config. Need config updates only when an update is needed. 
- Any update is checked into an internal repo upon review & tests
- Workflow will trigger auto udpate at switches

# Other teams Ask/Support

## SONiC - Core team
1. Help review LoM HLD
2. Help with review of all plugins design- especially the mitigation plugins
3. Help with review of Lom-tests integraion with SONiC nightly tests
4. Help with internal repo creation for LoM

## FUSE
1. Help with LoM deployment.
2. On any SONiC image upgrade/conversion, deploy appropriate LoM agent based on vendor & OS version.
3. Help with Policy creation & management.
4. Help with internal repo where update archive canbe held

## NDM
1. Add a new schema for LoM objects
2. The rest should be transparent as all validations are run inside SONiC

## GWS
### Red Button:
1. Watch for Red Button changes in external config.
2. A GWS instance is associated with a set of devices
3. For each matching device  in that set, it pushes the RedButton config.
4. RedButton config has a timestamp of update. 
5. GWS helps ensure SLA to update the switch upon any Red Button config changes.

### Heartbeat watcher:
1. Listens for heartbeats for all systems running LoM
2. Raise alert on missing heartbeat
3. Analyze heartbeat contents with its config. If expected actions are missing, raise alert.

## Build/Test pipelines
- As acttions update are intended for all released images, we would need to create Test Run pipeline for any release, run the install script (_as FUSE would do_) and run the entire test suite.
- As the target OS & platforms would be few many, we need a way to automate these pipelines creation

## LoM Dashboard in Geneva
- Shows all devices running LoM
- Shows by plugin
- A view on counters reported by all devices.
