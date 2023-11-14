# Container Addition Steps
This technical note presents a quick reference to the audience who intend to add a new feature or functionality within SONiC NOS in a new docker container service.
## Steps

For better understanding, the process of SONiC Container addition is explained taking an example. In which, “Feature AAA is intended to be supported in SONiC architecture by adding it’s support within a new container named ‘docker-AAA’”.

* Step1: 
```
Create a new directory containing AAA feature specific configuration files and its docker service-related configuration files.
These files will later become part of AAA container OS, when deployed. This docker directory file should be specified at the
following source path of SONiC NOS code ‘~/sonic-buildimage/dockers/docker-AAA/’.
•	start.sh        : This file contains the list of commands to be executed/performed every time the container starts like,
                    - Running any init scripts & configuration data population
                    - Also, if any specific config generation required for the container those operations shall be performed using this script.

•	supervisord.conf: This file contains the list of processes/services that the container would like to start every time container is (re)started.
                    Also, user can configure the actions of sub-processes of the container i.e. 
                    - Expected action on every (re)start.
                    - Should the sub-processes auto start or manually be started?
                    - Dependency on other sub-process etc.
                    Example configuration,
                      [program:start]
                      command=sh /usr/bin/start.sh
                      priority=1
                      autostart=true
                      autorestart=false
                      startsecs=0
                      stdout_logfile=syslog
                      stderr_logfile=syslog
                      dependent_startup=true
                      dependent_startup_wait_for=rsyslogd:running
                      [program:AAA_Service]
                      command=/usr/bin/python3 /usr/bin/AAA_Service &
                      priority=2
                      autostart=true
                      autorestart=true
                      stdout_logfile=syslog
                      stderr_logfile=syslog
                      dependent_startup=true
                      dependent_startup_wait_for=start:exited

•	manifest.json : This file contains the control information specific to the container like,
                    - Privileges to be assigned to the container (if any)
                    -  Configuration detailing any container specific CLI auto-generation
                    -  Inter container dependency information specification etc.,

•	Dockerfile.j2	: This file contains Docker build instructions in a Jinja2 template format. It contains a collection of instructions
                  and commands that will be automatically executed in sequence in the docker environment for building a new docker image.
                  It constitutes the list of libraries, packages, utility commands, OS services and also the file structure of container OS or docker image.

•	Dockerfile-dbg.j2 : Same as Dockerfile.j2 but captures information specific to Debug version of the image.

•	critical_processes: This file contains the list of processes nominated as critical within the container.
                      E.g.: In docker-AAA container, the process ‘AAA_Service’ marked as critical.

•	Other container specific functional source files, configuration files & directories.
```
