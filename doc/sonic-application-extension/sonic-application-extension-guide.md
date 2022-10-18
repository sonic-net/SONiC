<!-- omit in toc -->
# SONiC Application Extension Guide

<!-- omit in toc -->
#### Rev 0.1

<!-- omit in toc -->
## Table of Content
- Revision
- Scope
- Porting an existing SONiC Docker image to be an Application Extension
- Developing a new SONiC Application Extension
- Adding 3rd party application to SONiC package database
- Building SONiC image with 3rd party application
- Manifest Reference

### Revision

| Rev |     Date    |       Author            | Change Description                   |
|:---:|:-----------:|:-----------------------:|--------------------------------------|
| 0.1 | 02/2021     | Stepan Blyshchak        | Initial Proposal                     |

### Scope

This document gives developers a quick guide through developing new application extensions or porting existing SONiC docker images into application extension compatible ones.

It is recommended to get acquainted with [HLD](sonic-application-extention-hld.md) document before reading this document.

### Porting an existing SONiC Docker image to be an Application Extension

It is possible to port existing SONiC docker image and make it an Application Extension.

An example of porting DHCP relay - https://github.com/sonic-net/sonic-buildimage/commit/b3b6938fda9244607fb00bfd36a74bccab0c38a9.

1. Add a new build time flag to SONiC build system to control whether to include new Docker Image *XXX*:

Makefile.work
```makefile
INCLUDE_XXX=$(INCLUDE_XXX)
```

2. Register this Docker image in SONIC_PACKAGES_LOCAL target group and remove from SONIC_INSTALL_DOCKER_IMAGES:


rules/docker-XXX.mk
```makefile
ifeq ($(INCLUDE_XXX), y)
ifeq ($(INSTALL_DEBUG_TOOLS), y)
SONIC_PACKAGES_LOCAL += $(DOCKER_XXX_DBG)
else
SONIC_PACKAGES_LOCAL += $(DOCKER_XXX)
endif
endif
```

3. Remove $(DOCKER_XXX)_RUN_OPT and replace with variables used to generate manifest for the docker:

rules/docker-XXX.mk
```makefile
$(DOCKER_XXX)_CONTAINER_PRIVILEGED = true
$(DOCKER_XXX)_CONTAINER_VOLUMES += /etc/sonic:/etc/sonic:ro
$(DOCKER_XXX)_CONTAINER_VOLUMES += /usr/share/sonic/scripts:/usr/share/sonic/scripts:ro
$(DOCKER_XXX)_CONTAINER_TMPFS += /tmp/
````

These variables are used to generate manifest for docker at build time (see generate_manifest function in https://github.com/sonic-net/sonic-buildimage/blob/master/rules/functions):

4. For extensions that provide CLI commands a CLI plugin is needed.

4.1. Remove extension CLI commands from sonic-utilities code.

4.2. Move the implementation as a separate file into sonic-buildimage under dockers/docker-xxx/cli folder.

This plugin has to implement ```register``` function needed to be loaded by sonic-utilities core:

dockers/docker-xxx/cli/show.py
```python
import click

@click.command()
def example()
    pass

def register(cli):
    cli.add_command(example)
```

```register``` may throw an exception, in this case main CLI will still work but a warning will be printed to the user.


4.3 UT for CLI:

In case CLI has unit tests, they need to be moved from sonic-utilities into sonic-buildimage repository and placed under dockers/docker-xxx/cli-plugins-tests/.

In case this folder exists tests are executed at docker image build time and test log is recorder in target/docker-xxx.gz.log.

The command line to execute tests is:

```
pytest-3 -v
```

### Developing a new SONiC Application Extension

To develop a new SONiC Application Extension use the following example extension as a template:
https://github.com/stepanblyschak/sonic-example-extension.

Prerequisites, build instructions and installation instructions are present in repository README.md file.

### Adding 3rd party application to SONiC package database

Modify files/build_templates/packages.json.j2 to include new package. Example for the previous sonic-example-extension - *cpu-report*:

```json
{
    "cpu-report": {
        "repository": "stepanblyschak/cpu-report",
        "description": "CPU report example",
        "default-reference": "1.0.0"
    }
}
```

### Building SONiC image with 3rd party application

To build SONiC image with 3rd party application pre-installed use SONIC_PACKAGES target group.
See https://github.com/sonic-net/sonic-buildimage/blob/master/rules/sonic-packages.mk.

Create a file under rules/ called rules/cpu-report.mk with the following content:
```makefile
CPU_REPORT = cpu-report
$(CPU_REPORT)_REPOSITORY = stepanblyschak/cpu-report
$(CPU_REPORT)_VERSION = 1.0.0
SONIC_PACKAGES += $(CPU_REPORT)
```

Additional options:

```
$(CPU_REPORT)_DEFAULT_FEATURE_STATE_ENABLED # "y" or "n" - whether feature is enabled by default at system start. Sets enabled in the FEATURE table. Disabled by default.
$(CPU_REPORT)_DEFAULT_FEATURE_OWNER # "local" or "kube". Default is "local".
```

### Manifest Reference

Label name the manifest content should be written to:
```
com.azure.sonic.manifest
```

The value should contain a JSON serialized as a string.

| Path       | Type   | Mandatory | Description                                                                                      |
| ---------- | ------ | --------- | ------------------------------------------------------------------------------------------------ |
| /version   | string | no        | Version of manifest schema definition. Defaults to 1.0.0.                                        |
| /package   | object | no        | Package related metadata information.                                                            |
| /package/version                    | string | yes       | Version of the package.                                                        |
| /package/name                       | string | yes       | Name of the package.                                                           |
| /package/description                | string | no        | Description of the package.                                                    |
| /package/depends                    | list   | no        | List of SONiC packages the service depends on. Defaults to []                  |
| /package/depends[index]/name        | string | yes       | Name of SONiC Package                                                          |
| /package/depends[index]/version     | string | no        | Version constraint expression string                                           |
| /package/depends/[index]/components | object | no        | Per component version                                                          |
| /package/breaks                     | list   | no        | List of SONiC package the service breaks with. Defaults to []                  |
| /package/breaks[index]/name         | string | yes       | Name of SONiC Package                                                          |
| /package/breaks[index]/version      | string | no        | Version constraint expression string                                           |
| /package/breaks/[index]/components  | object | no        | Per component version                                                          |
| /package/base-os/                 | object    | no        | Base OS versions constraints  |
| /package/base-os/[index]/name     | strnig    | yes       | Base OS component name        |
| /package/base-os/[index]/version  | string    | yes       | Base OS component version     |
| /package/changelog                     | dict            | no        | Changelog dictionary.                   |
| /package/changelog/\<version\>         | dict            | yes       | Package version.                        |
| /package/changelog/\<version\>/changes | list of strings | yes       | Changelog messages for a given version. |
| /package/changelog/\<version\>/author  | string          | yes       | Author name.                            |
| /package/changelog/\<version\>/email   | string          | yes       | Author's email address.                 |
| /package/changelog/\<version\>/date    | string          | yes       | Date and time in RFC 2822 format.       |
| /package/init-cfg | dict | no        | Default package configuration in CONFIG DB format. Defaults to {} |
| /package/debug-dump | string | No        | A command to be executed during system dump |
| /service   | object | yes       | Service management related properties.                                                           |
| /service/name      | string          | yes       | Name of the service. There could be two packages e.g: fpm-quagga, fpm-frr but the service name is the same "bgp". For such cases each one have to declare the other service in "conflicts". |
| /service/requires  | list of strings | no        | List of SONiC services the application requires.<p>The option maps to systemd's unit "Requires=".                                                                                           |
| /service/requisite | list of strings | no        | List of SONiC services that are requisite for this package.<p>The option maps to systemd's unit "Requisite=".                                                                               |
| /service/wanted-by | list of strings | no        | List of SONiC services that wants for this package.<p>The option maps to systemd's unit "WantedBy=".                                                                                        |
| /service/after     | list of strings | no        | Boot order dependency. List of SONiC services the application is set to start after on system boot.                                                                                         |
| /service/before    | list of strings | no        | Boot order dependency. List of SONiC services the application is set to start before on system boot.                                                                                        |                                                                                                                   |
| /service/delayed   | boolean         | no        | Wether to generate a timer to delay the service on boot. Defaults to false.                                                                                                                 |
| /service/dependent-of        | lits of strnigs | no        | List of SONiC services this application is dependent of.<p>Specifying in this option a service X, will regenerate the /usr/local/bin/X.sh script and upgrade the "DEPENDENT" list with this package service.<p>This option is warm-restart related, a warm-restart of service X will not trigger this package service restart.<p>On the other hand, this service package will be started, stopped, restarted togather with service X.<p>Example:<p>For "dhcp-relay", "radv", "teamd" this field will have "swss" service in the list. |
| /service/post-start-action   | string          | no        | Path to an executable inside Docker image filesystem to be executed after container start.<p>A package may use this field in case a systemd service should not reach started state before some condition. E.g.: A database service should not reach started state before redis process is not ready. Since, there is no control, when the redis process will start a "post-start-action" script may execute "redis-cli ping" till the ping is succeessful.                                                                            |
| /service/pre-shutdown-action | string          | no        | Path to an executable inside Docker image filesystem to be executed before container stops.<p>A uses case is to execute a warm-shutdown preparation script.<p>A script that sends SIGUSR1 to teamd to initiate warm shutdown is one of such examples.                                                                                                                                                                                                                                                                                 |
| /service/host-service | boolean | no        | Multi-ASIC field. Wether a service should run in host namespace. Default is True.   |
| /service/asic-service | boolean | no        | Multi-ASIC field. Wether a service should run per ASIC namespace. Default is False. |
| /service/warm-shutdown/       | object          | no        | Warm reboot related properties. Used to generate the warm-reboot script.                                                                                                                                                                                                                                                                                                                  |
| /service/warm-shutdown/after  | lits of strings | no        | Warm shutdown order dependency. List of SONiC services the application is set to stop after on warm shutdown.<p>Example: a "bgp" may specify "radv" in this field in order to avoid radv to announce departure and cause hosts to lose default gateway.<p>*NOTE*: Putting "radv" here, does not mean the "radv" should be installed as there is no such dependency for the "bgp" package. |
| /service/warm-shutdown/before | lits of strings | no        | Warm shutdown order dependency. List of SONiC services the application is set to stop before on warm shutdown.<p>Example: a "teamd" service has to stop before "syncd", but after "swss" to be able to send the last LACP PDU though CPU port right before CPU port becomes unavailable.                                                                                                  |
| /service/fast-shutdown/       | object          | no        | Fast reboot related properties. Used to generate the fast-reboot script.                                                                                                                                                                                                                                                                                                                  |
| /service/fast-shutdown/after  | lits of strings | no        | Same as for warm-shutdown.                                                                                                                                                                                                                                                                                                                                                                |
| /service/fast-shutdown/before | lits of strings | no        | Same as for warm-shutdown.                                                                                                                                                                                                                                                                                                                                                                |
| /processes                    | object          | no        | Processes infromation                                                                                                                                                                                                                                                                                                                                                                     |
| /processes/[name]/reconciles  | boolean         | no        | Wether process performs warm-boot reconciliation, the warmboot-finalizer service has to wait for. Defaults to False.                                                                                                                                                                                                                                                                      |
| /container | object | no        | Container related properties.                                                                    |
| /container/privileged         | string          | no        | Start the container in privileged mode. Later versions of manifest might extend container properties to include docker capabilities instead of privileged mode. Defaults to False. |
| /container/volumes            | list of strings | no        | List of mounts for a container. The same syntax used for '-v' parameter for "docker run".<p>Example: "\<src\>:\<dest\>:\<options\>". Defaults to [].                               |
| /container/mounts             | list of objects | no        | List of mounts for a container. Defaults to [].                                                                                                                                    |
| /container/mounts/[id]/source | string          | yes       | Source for mount                                                                                                                                                                   |
| /container/mounts/[id]/target | string          | yes       | Target for mount                                                                                                                                                                   |
| /container/mounts/[id]/type   | string          | yes       | Type for mount. See docker mount types.                                                                                                                                            |
| /container/tmpfs              | list of strings | no        | Tmpfs mounts. Defaults to []                                                                                                                                                       |
| /container/environment        | dict            | no        | Environment variables for Docker container (key=value). Defaults to {}.                                                                                                            |
| /processes | list   | no        | A list defining processes running inside the container.                                          |
| /cli       | object | no        | CLI plugin information. *NOTE*: Later will deprecated and replaced with a YANG module file path. |
| /cli/mandatory         | boolean| no        | Wether CLI is a mandatory functionality for the package. Default: False. |
| /cli/show-cli-plugin   | string | no        | A path to a plugin for sonic-utilities show CLI command.        |
| /cli/config-cli-plugin | string | no        | A path to a plugin for sonic-utilities config CLI command.      |
| /cli/clear-cli-plugin  | string | no        | A path to a plugin for sonic-utilities sonic-clear CLI command. |


