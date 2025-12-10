# SONiC Optional Feature Control Enhancement #

## Revision ##

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 10/10/19 | Pradnya Mohite | Initial version    |

## Scope ##
Add support to enable/disable features in sonic. Features like telemetry agent can be optional and this enhancement will provide a way to control that. 

### Implementation Details ###
* Add feature table in config db.  
  * Modify sonic-cfggen tool to add table and enable the telemetry feature by default.  
  * For each feature, key is FEATURE|feature name, status :enabled/disabled.  
* Add "config feature enable|disable [feature name]" command line.  
  * Add support for show and config commands.  
* Add feature in hostcfgd to listen for Config DB FEATURE table entry changes, and enable & start or stop & disable the respective service as appropriate.  
  * When hostcfgd first starts, it reads all entries in the FEATURE table and compares with current status of each service. If there is mismatch, hostcfgd will enable & start or stop & disable as appropriate.  