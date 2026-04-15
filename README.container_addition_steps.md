# Guidelines for new Container addition in SONiC Architecture
This technical note presents a quick reference to the audience who intend to add a new feature or functionality within SONiC NOS in a new docker container service.
## Steps

For better understanding, the process of SONiC Container addition is explained taking an example. In which, “Feature AAA is intended to be supported in SONiC architecture by adding it’s support within a new container named ‘docker-AAA’”.

* **Step 1:**
Create a new directory containing AAA feature specific functional source, configuration files and its docker service-related files. These files  will be deployed into 'AAA container OS'. This directory should be created at following path of the SONiC NOS code structure ‘~/sonic-buildimage/dockers/**docker-AAA/**’.
```
    •	start.sh        : This file contains the list of commands to be executed, every time container starts.
                            - Running any init scripts of the container
                            - Also, if any specific config generation is required for the container, then those steps need to be triggered 
                              using this script.

    •	supervisord.conf: This file contains the list of processes/services that the container would like to start every time container is
                            (re)started. Also, user can configure the actions of sub-processes of the container by updating in this
                            configuration file which include,  
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
                        - Configuration detailing any container specific CLI auto-generation
                        - Inter container dependency information specification etc.,

    •	Dockerfile.j2	: This file contains Docker build instructions in a Jinja2 template format.
                        It contains a collection of instructions and commands that will be automatically executed in sequence in the docker
                        environment for building a new docker image.
                        It constitutes the list of libraries, packages, utility commands, OS services and also the file structure of container OS
                        or docker image.

    •	Dockerfile-dbg.j2 : Same as Dockerfile.j2 but captures information specific to Debug version of the image.
    
    •	critical_processes: This file contains the list of processes nominated as critical within the container.
                          E.g.: In docker-AAA container, the process ‘AAA_Service’ marked as critical.
    
    •	Other container specific functional source files, configuration files & directories.
```

* **Step 2:**
Add an option for inclusion of the AAA feature dynamically in SONIC NOS using a macro (i.e., like INCLUDE_AAA) by specifying a config setting at file ‘~/sonic-buildimage/rules/config’.
```
    # INCLUDE_AAA - build docker-AAA for AAA feature support
    INCLUDE_AAA = y
```

* **Step 3:**
Add a build instruction to compile the new (AAA) feature source and include it into SONiC build process by updating the following make file ‘~/sonic-buildimage/slave.mk’
```
  SONIC_BUILD_INSTRUCTION:=  make INCLUDE_AAA=$(INCLUDE_AAA) 
```

* **Step 4:**
Create a make file & dependency file for the new container and related dependent packages by creating new .mk and .dep files at path “~/sonic-buildimage/rules/”. 
For docker AAA container following make files can be created,
    - docker-AAA.mk  : Docker container Makefile
    - docker-AAA.dep : Docker container package dependency file
    - AAA-SubService.mk  : Container’s Intermediate package Makefile 
    - AAA-SubService.dep  : Container’s Intermediate package dependencies 

* **Step 5:**
Specify the source files of the docker and its dependent packages by creating new directories at path ‘sonic-buildimage/src/’.
```
    ./sonic-buildimage/src/**AAA-SubService**/
```

* **Step 6:**
Initialize new (AAA) feature specific default configuration settings (if any) by specifying them at path ‘~/files/build_templates/init_cfg.json.j2’. This will be used whenever SONiC NOS boots up & feature AAA is included in the NOS.
```
    {%- if include_AAA == "y" %}{% do features.append(("AAA", "enabled", false, "enabled")) %}{% endif %}
```

* **Step 7:**
Define the sequence, indicating at which stage the new docker container AAA should start by specifying the details in following jinja file ‘- ~/files/build_templates/AAA.service.j2'

```
      [Unit]
      Description=AAA container
      Requires=swss.service
      After=swss.service syncd.service
      BindsTo=sonic.target
      After=sonic.target
      [Service]
      ExecStartPre=/usr/bin/{{docker_container_name}}.sh start
      ExecStart=/usr/bin/{{docker_container_name}}.sh wait
      ExecStop=/usr/bin/{{docker_container_name}}.sh stop
      RestartSec=30
```
