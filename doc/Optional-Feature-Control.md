# SONiC Optional Feature Control Enhancement#

## Revision ##

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 10/10/19 | Pradnya Mohite | Initial version    |

## Scope ##
1.Add feature table in config db.  
   -Modify sonic-cfggen tool to add table and enable the telemetry feature by default.  
   -For each feature, key is FEATURE|feature name, status :on/off.  
2.Add "config feature enable|disable [feature name]" command line.  
   -Add support for show and config commands.  
3.Add feature watch in hostcfgd to watch config db entry, and start & enable or stop & disable the service.  
   -When hostcfgd first start, it reads all entries in the FEATURE table and compare with current service status, if there is mismatch, hostcfgd will start/stop the service.  
   -hostcfgd also dynamically listen to the FEATURE table and change the service status based on the config db change.  
