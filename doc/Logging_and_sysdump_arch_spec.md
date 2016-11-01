# SONiC Logging & System Dumps Arch Spec

## Requirements

### Logs

 1. Log files manipulation  
    1.1. Upload (Current or specific ID)  
  	1.2. Rotate  
  	1.3. Delete  
 2. Setting severity level  
    2.1. General  
    2.2. Per daemon/component  
    2.3. Logs generated inside docker containers should be available and transparent to general logging mechanism  
 3. Logging to console *(Useful for debugging purposes)*  
    3.1. Specific severity type used by application to print to console  
    3.2. Log monitor events to mirror selected messages to all terminals  
 4. Daemon crashes should be monitored and reported along with system dumps generated after crash occures.  

### System Dumps

System dumps should capture as much of a system state at the moment of querying as possible.
Dump can be divided into 3 parts:

1. General - provides all general (non platform related) information of a system. This includes output from all available `show` commands, configuration files, databases snapshots, standard command like `ifconfig` or `ip` or `lsmod`, along with all log files on the system
2. Per daemon - all stateteful daemons that under SONiC project development should have a possibility to dump their state. It requires a registration mechanism that allows to trigger dump generation for each daemon.
3. Per platform - each platform should be able to dump its inner state, SDK configuration etc. It requires a registration mechanism that allows to trigger dump generation.  

End goal of system dump is a collection of configuration files, logs, states of system components that will allow to reproduce any configuration in local development environment.

System should provide an interface to generate such dump on demand and upload it to a remote server.

## Scale/Performance

In order to not use all available space on disk, log files should be rotated automaticcaly and their size should be limited.  
Log files should be limitatied in their overall size.  
Spamming log messages should be limited in frequency of their occurence.  
Sysdump archive should have a limitation in size

## Interaction with other modules

All modules should use the same common API for logging and dumps (provided by libswss-common).

## Configuration flow

Following list of parameters should be configurable:  
1. Maximum number of files for rotation  
2. Rotation period  
3. Maximum log file size  
4. Compress type for rotated log files  
5. Post rotation actions  
Those parameters in configuration files are deployed via sonic-mgmt.  
It is done during deployment stage.  

## UI types to support

User can change logging configuration via sonic-mgmt, which takes care of deploying configs.  
Sysdump should be available through sonic-mgmt.  
