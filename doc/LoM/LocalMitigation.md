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
7. Report run of any action to external clients via SONiC events channel.

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
5. Actions are implemented as plugins, so an update/add can be done via small file copy of that plugin.
6. Actions are defined by Schema and schema specifies configurable knobs.
7. Service is built with static config, which can be overrriden via config-DB
8. The plugins are versioned. 
9. The running configuration & state/status are reflected in STATE-DB.
10. The CLI extends dynamically to any action using YANG schema.
11. An action add/update/re-config will not impact control/data plane

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
9. The plugins as versioned and switches report the running versions. Rollback to any older version can be done via small config update.
10. The actions are defined in YANG schema, hence the published reports are structured 
11. Actions' runs have full visibility via gNMI & STATE-DB.
12. For any new SONiC bug in released OS, it could be well managed via small/simple detection/mitigation actions that can be rolled out in hours across the fleet.
    - Create detection & mitigation action & update automated tests
    - Identify target releases
    - Kick off auto tests runs on target releases.
    - Deploy the actions to target devices.
13. FUSE may continue to deploy this OS version with known issue, as it would transparently *also* install the actions that detect/mitigate.   
15. Supports enable/disable of actions via config update.
    

# A Use case:
## Link flap / CRC / Discards
For a link the common issues are flaps, CRC-errors & discards. Here we need a way to watch for it with appropriate algorithm to identify anomalies. When an anomaly is detected, the mitigation is bring link down. But this demands basic safety checks. A detection-action can be configured with appropriate mitigation actions to run upon detection, along with approriate safety checks to precede the mitigation action. This is called action sequence or binding sequence.

### Link anomaly Detection action:
An action for link flap may be written for flap by observing STATE-DB changes. An action for CRC-errors/discards may watch counters. These actions are run forever, often cache data at different time points and run an algorithm on the cached data to detect an anomaly. Upon detection, the detected anomaly is published via SONiC events channel that reaches EventHub via low latency channel in couple of seconds. Every published action is logged too as a fallback. Data published & logged are as per schema.

### Safety check action:
The mitigation action for a failing link, is to bring the link down. But this demands a safety check to assess the capacity of not just this device, but more of a global scope. One may write a local safety check action, that could succeed if device has the link availability > 75% (_this magic number is configurable_). When this local check fails, the action can reach out to an external SCS service for a global chjeck. This action returns success, if mitigation can happen, else return failure. In either case, its result is published & logged. A success/green-flag will allow mitigation to run.

### Mitigation action:
This action can set the admin down for the link. This action is published.

### Sequence completion:
-   The original detected anomaly is now re-published with final result as success or not.
     - The success implies a successful mitgation of the detected anomaly.
     - A failure implies that the anomaly is not locally mitigated. The failure gives appropriate error code that indicates the reason for failure. 
-   The completon is expected within seconds of detection.
-   Every action run as part of sequence has a set timeout, and must end by then along with overall timeout for entire sequence to complete.
-   A failing action will abort the sequence at that point which would skip subsequently ordered actions unless marked as mandatory.
-   During a sequnce run upon detection, the heartbeats are published more frequently. The HB would carry info on current running action.
-   If LoM fails, the external service can take over mitigation as is today.
-   In scenario where we mitigate successfully, the TTM is in couple of seconds. For any failure, we still get TTD in seconds.</br>
NOTE: An ICM is fired for every detected anomaly. If mitigation is done by LoM, the ICM will be marked "_mitigated_".

### Sequencing & config
Every detection action is tied to corresponding safety check & mitigation actions. This is called sequencing, by adding them in ordered sequence. A sequence progresses only if last executed action succeeds. Any failure aborts the sequence and causes the detected anomaly to be re-published with failure code indicating "_mitigation attempt failed_". This is called binding sequence. The Service comes with built-in actions and associated seqeunces.
Every action could be fine tuned via some configurable knobs. A SONiC CLI or configlet could do.

## Memory utilization
This is a complex probem as memory used by a daemon could vary based on its load (_e.g. count of peers, routes, route-maps configured_). This demands an custom detection per daemon with dynamically computed threshold. The detection needs to distinguish between "_is memory consumption growing constantly_" vs "_transient blips_". This algorithm might need few tweaks & updates as we observe its reports. Hence will takje some time to get tune it. Hence hard coding this into image will not fit. But actions are small plugins/minions that can be easily updated w/o impact to control/data plane, hence allows for frequent updates,.

### Detection
The action does the monitoring. We can have variations per platform, target OS version and even cluster type. This is vetted in nightly tests for  all  target platform & OS version. It constantly monitors. It can cache usage in various time points as required by algorithm to do a proper analysis. This detection action is kicked off at the start and run until detected or disabled.

### Safety-check
Asses the daemon that is in trouble to verify if its restart will impact Dataplane or not. If not, it returns success, else returns failure, which will abort sequence and no mitigation action is executed. This will also look at the service restart history to ensure that no more than N restarts is attempted in M seconds.

### Mitigation
This may be just service restart or more (_say remove/reset files/data_). The action is executed and its result is published

### Sequence completion:
- Anomaly is re-published with mitigation result. An external service may take over mitigation on any failure.

### conclusion
- The actions are anytime updatable as we see need for tuning.
- This type of detection is better equipped to run locally as it has wealth  of data, like daemon's current load level, history on restarts for last N seconds.
- The action can be fully customized for this OS version.
- Mitigation happens in seconds if it would not have data plane impact. The most common daemons that face issues are control plane daemons like SNMP.


# Design
![image](https://github.com/renukamanavalan/SONiC/assets/47282725/4255824b-8927-4c81-9962-5e04dc783743)


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
- The entire state of LoM is available in STATE-DB which is polled out by GWS

# SONiC i/f
LoM is another SONiC service and built as part of SONiC image. Its integration is provided below.

## LoM Service
LoM is a systemd maintained containerized service. Like Telemetry, this service is predominantly written in Go with a vision of supporting mult-language plugins in future. It is built as docker image with all required systemd's service related files and an entry in FEATURE table as enabled. The code resides in a dedicated sub module.

## CONFIG
LoM service comes with static config created during build time off of schema. The LoM publishes the running config into STATE-DB. The CONFIG-DB updates are needed only when tweaks are needed over static config. 
The SONiC-CLI will be enhanced for LoM. This added module will be written as dynamically driven by YANG schema. It would browse YANG files for modules/objects to configure and within each, it refers schema for configurable attributes, their types & defaults. In other words add/remove a YANG file add/remove a LoM key. Add / remove a configurable attribute will transparently reflect in CLI tabbing.
In short LoM config commands will be indirectly driven by schema.
The sceham updates are always backward compatible, hence data created by older versions of scehma will remain valid.

### CONFIG-DB:
- The CLI can be used to GET/SET any attributes.
- The updates are only a diff to in-built static config
- To see the full config call "show LoM config" which will show the current running config

### STATE-DB :
The STATE-DB carries 3 categories of data
- Config -- The current running config == static built-in config + Config-DB
- Counters -- The stat counters
- Live-Cache -- The last N actions' & heartbeats published.

**Table**: LoM|Config<br>
**Keys**: "Global", "Procs", "binding", "actions" & "Red-button"

#### LoM|Config|Global
```
"MAX_SEQ_TIMEOUT_SECS": 20
"MIN_PERIODIC_LOG_PERIOD_SECS": 1,
... 
```

#### LoM|Config|Procs|< Proc ID >:
```
"actions": [
   '{ "action-name":  "<..>", "plugin-version": "<...>", "plugin-filename": <...?> }',
   '{ "action-name":  "<..>", "plugin-version": "<...>", "plugin-filename": <...?> }',
   ...
]

```

#### LoM|Config|Binding|< sequence name >:
```
"priority": 1,
"timeout:: 20,
"actions": [
  '{"name": < action name >", "sequence": < Index within sequence>, "timeout": 5}',
   ...
]
```

#### LoM|Config|Actions|< action name >
```
"Description": "..."
"Disable": "True",
"HB_Freq": < seconds > 
"Mimic": "False",
< action specific attrs per schema >
```
#### LoM|Counters
Stats are maintained as below to cover all actions
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
```
"Actions": [ <Last N published non-heartbeat strings are saved here.>]
"Heartbeats": [ <last M heartbeats are saved here >]
```

#### LoM|RedButton
- This is used to disable one/subset/all actions.
- Unlike other configurations, this RedButton config has a ***SLA*** to reach the target device as this could be disabling an action, which is critical that it is disabled within set SLA
- Red Button config is versioned.
- Update is via CONFIG-DB and LoM updates its running value for the same in STATE-DB.
```
{
   "CreateTimestamp": < Timestamp of the create/udpate by external user >
   "updateTiemstamp": < update timestamp in DUT >
   "DisableAll": True/False  # Disable all actions
   "DisableMitigations": True/False # Disables all mitigations
   "ActionsDisabled": [ < list of action disabled action names > ]
}
```

## LoM Visibility / State / Status
### SONiC events
Results of all actions are published w/o any constraints to Events Hub via SONiC gNMI. Even a stale response (_one that arrives after timeout_) is also published. The publish use SONic Events channel. As per Event's channel usage agreement, all publish o/p are per defined schema with backward compatibility.

### State-DB
Reports current running config of LoM, LoM maintained counters and last set of N actions published and M heartbeats published.

#### syslog
All published events are also logged by default by SONiC event module.
LoM reports all events/info.err messages via syslog.
For persistent errors, it reports periodically, to manage the unreliable syslog transport.

# Actions Update:
One of the core values of LoM is its management of diverse independent actions yet work in unison with single context during mitigation of detected anomaly. The actions are implemented as plugins to provide the flexibility and adaptability to take updates at run time w/o impacting control or data plane.

LoM is not built as one monolithic piece but as a collaborative union of plugins bind by config. Each plugin is an **independent** worker item for one specific purpose and this enables an update of a Plugin transparent to rest of the system. The plugins are versioned and use config to update to new version or easy rollback to previous.

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
- Add this plugin to a test switch, update config needed to add new action and test it out as plugin.
- Run the updated test suite to ensure the updated system is good in its current updated state.
   - Nightly tests run the updated test suite
- An update to existing plugin may follow subset of above steps based on extent of change.
- Create an self installable archive that has this plugin and configlet to apply with metadata to filter out target devices.
  - Running this archive as script copies the plugin to destination and updates the config with built-in configlet.
  - The archive may have metadata for target matching, like "OSVersion <= .... && PLATFORM == .... If present install proceeds on match only.
- Save this archive in a local repo.
 
## Update vetting
- Identify the target OS versions & Platform for this update.
- Auto create test pipelines for all target scenarios.
- The test pipeline will download the archive from a local repo onto DUT and run the script associated to install.
- The nightly tests run the test suite that vets all available actions.
  
## Fleet upgrade
- Take help from FUSE
- FUSE need not do any device isolation for update as these updates are transparent to both control & data planes
- An explicit FUSE policy is created with following info
   - Device metadata to match (e.g. `OSVersion >= 20221131.80`) by specifying few filters.
       - This includes current plugin version <= this update's or not present
   - URL of the self-installable Plugin archive.
- FUSE identifies the matching devices in current scope, download the archive and run the script associated with the archive.

## Fleet update status
- The switch has current running versions in STATE-DB.
- FUSE is used for Action(s)/Plugin(s) update.
  - It updates plugin files & CONFIG-DB.
  - LoM takes in the update transparently by watching CONFIG-DB, load new plugins and reflect the new values in STATE-DB.
  - On any failure, it sets version to an reserved error string and provide detailed error message in logs repeatedly until fixed.
  - FUSE watch for STATE-DB change with timeout to validate the success of the update.

   
# LoM config update
- As mentioned above the service comes with built-in config. Need config updates only when an update is needed. 
- The SONiC DB schema is provided above.
- YANG schema is provided for config/configlet validation
- NDM will be required to do the updates. NOTE: We need config updates, only when/where a tweak is needed.

# Other teams Ask/Support

## SONiC - Core team
1. Help review LoM HLD
2. Help with review of all SONiC image changes
3. Help with review SONiC nightly tests
4. Help with Pipeline updae with action-update added and auto-pipeline creation for all target scenarios.
5. Help with internal repo creation for LoM

## FUSE
1. Help with LoM actions update as described above
2. On any SONiC image upgrade, look for possible plugin updates and apply as part of image update
3. Help with Policy creation & management.
4. Help with internal repo where update archive canbe held

## NDM
1. Add a new schema for LoM objects
2. The rest should be transparent as all validations are run inside SONiC

## GWS
### Red Button:
1. Watch for Red Button changes in NDM config.
2. A GWS instance is associated with a set of devices
3. For each matching device  in that set, it pushes the RedButton config.
4. RedButton config has a timestamp of update. This can be compared with red-button config in switch as reflected in STATE-DB. If NDM has later update push it, else all good.
5. GWS helps ensure SLA to update the switch upon any Red Button config changes.

### Heartbeat watcher:
1. Listens for heartbeats for all systems running LoM
2. Raise alert on missing heartbeat
3. Analyze heartbeat contents with its config. If expected actions are missing, raise alert.

## Build/Test pipelines
- As acttions update are intended for all released images, we would need to create Test Run pipeline for any release, run the install script (_as FUSE would do_) and run the entire test suite.
- As the target OS & platforms would be few many, we need a way to automate these pipelines creation

## LoM Dashboard
- Shows all devices running LoM
- Shows by plugin
- A view on counters reported by all devices.
