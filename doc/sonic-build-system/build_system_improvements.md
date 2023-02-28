# Build system improvements

This document describes few options to improve SONiC build time.
To split the work we will consider that SONiC has two stages:

    1. debian/python packages compilation <- relatively fast
    2. docker images build <- slower espessially when several users are building in parallel

So we will first focus on second stage as it is the most time consuming stage

## Improving Dockerfile instructions

Each build instruction in Dockerfile involves creating a new layer, which is time consuming for docker daemon.

As long as we are using ```--no-cache --squash``` to build docker images there is no real use of building in layers.

e.g. SNMP docker image:

```Dockerfile
{\% if docker_snmp_sv2_debs.strip() -\%}
# Copy locally-built Debian package dependencies
{\%- for deb in docker_snmp_sv2_debs.split(' ') \%}
COPY debs/{{ deb }} /debs/
{\%- endfor \%}

```
Renders to:
```Dockerfile
# Copy locally-built Debian package dependencies
COPY debs/libnl-3-200_3.2.27-2_amd64.deb /debs/
COPY debs/libsnmp-base_5.7.3+dfsg-1.5_all.deb /debs/
COPY debs/libsnmp30_5.7.3+dfsg-1.5_amd64.deb /debs/
COPY debs/libpython3.6-minimal_3.6.0-1_amd64.deb /debs/
COPY debs/libmpdec2_2.4.2-1_amd64.deb /debs/
COPY debs/libpython3.6-stdlib_3.6.0-1_amd64.deb /debs/
COPY debs/python3.6-minimal_3.6.0-1_amd64.deb /debs/
COPY debs/libpython3.6_3.6.0-1_amd64.deb /debs/
COPY debs/snmp_5.7.3+dfsg-1.5_amd64.deb /debs/
COPY debs/snmpd_5.7.3+dfsg-1.5_amd64.deb /debs/
COPY debs/python3.6_3.6.0-1_amd64.deb /debs/
COPY debs/libpython3.6-dev_3.6.0-1_amd64.deb /debs/
```

Same goes for instructions to install built packages:

```Dockerfile
RUN dpkg_apt() { [ -f $1 ] && { dpkg -i $1 || apt-get -y install -f; } || return 1; }; dpkg_apt /debs/libnl-3-200_3.2.27-2_amd64.deb
RUN dpkg_apt() { [ -f $1 ] && { dpkg -i $1 || apt-get -y install -f; } || return 1; }; dpkg_apt /debs/libsnmp-base_5.7.3+dfsg-1.5_all.deb
RUN dpkg_apt() { [ -f $1 ] && { dpkg -i $1 || apt-get -y install -f; } || return 1; }; dpkg_apt /debs/libsnmp30_5.7.3+dfsg-1.5_amd64.deb
...
```

### Suggestion to improve:

```Dockerfile
{\% if docker_snmp_sv2_debs.strip() -\%}
# Copy locally-built Debian package dependencies
COPY
{\%- for deb in docker_snmp_sv2_debs.split(' ') \%}
debs/{{ deb }} \
{\%- endfor \%}
/debs/
```

This will generate single COPY instruction:
```Dockerfile
# Copy locally-built Debian package dependencies
COPY debs/libnl-3-200_3.2.27-2_amd64.deb \
     debs/libsnmp-base_5.7.3+dfsg-1.5_all.deb \
     debs/libsnmp30_5.7.3+dfsg-1.5_amd64.deb \
     debs/libpython3.6-minimal_3.6.0-1_amd64.deb \
     debs/libmpdec2_2.4.2-1_amd64.deb \
     debs/libpython3.6-stdlib_3.6.0-1_amd64.deb \
     debs/python3.6-minimal_3.6.0-1_amd64.deb \
     debs/libpython3.6_3.6.0-1_amd64.deb \
     debs/snmp_5.7.3+dfsg-1.5_amd64.deb \
     debs/snmpd_5.7.3+dfsg-1.5_amd64.deb \
     debs/python3.6_3.6.0-1_amd64.deb \
     debs/libpython3.6-dev_3.6.0-1_amd64.deb \
     /debs/
```

Reduced number of steps from 52 to 20 for SNMP docker.

### How much faster?

```bash
stepanb@51bc3c787be0:/sonic$ time BLDENV=stretch make -f slave.mk target/docker-snmp-sv2.gz
```

|Without optiomization|With optimizations|
|---------------------|------------------|
|27m48.289s           |10m50.024s        |

Gives 2.7 times build time improvement

**NOTE**: build time is linear to number of steps: 27/10 ~ 52/20

### How to force developers to use single step instruction for new Dockerfiles.j2?
Provide a set of macros defined in dockers/dockerfile-macros.j2 file:

```jinja
copy_files
install_debian_packages
install_python_wheels
```

## Upgrade docker in slave to 18.09 and use Docker Build Kit (optionally)

1. Upgrade docker in sonic-slave-stretch to 18.09 - already available in debian stretch repositories
2. Add environment variable ```DOCKER_BUILD_KIT=1``` to ```docker build``` command to use BuildKit instead of legacy docker build engine

|Without optiomization in #1 |With optimizations in #1|
|----------------------------|------------------------|
|11m2.483s                   |4m20.083s               |

Gives 2.5 times build time improvement
Max 6.5 times build time improvement

**NOTE**: (bug) squash generates image squashed with base image resulting in sonic image size (600 mb -> 1.5 gb)

Introduce option SONIC_USE_DOCKER_BUILDKIT and warn user about image size:
```
$ make SONIC_USE_DOCKER_BUILDKIT=y target/sonic-mellanox.bin
warning: using docker buildkit will produce increase image size (more details: https://github.com/moby/moby/issues/38903)
...
```

However, eventuly it will be fixed, so we can use SONIC_USE_DOCKER_BUILDKIT=y by default

### Avoid COPY debs/py-debs/python-wheels at all (for future)
https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/experimental.md#run---mounttypebind-the-default-mount-type

```Dockerfile
RUN --mount=type=bind,target=/debs/,source=debs/ dpkg_apt() deb1 debs2 deb3...
```

|With optimizations in #1|
|------------------------|
|3m56.957s               |

**NOTE**: requires enabling ```# syntax = docker/dockerfile:experimental``` in Dockerfile


## Enable swss, swss-common, sairedis parallel build

From ``` man dh build ```:
```
If your package can be built in parallel, please either use compat 10 or pass --parallel to dh. Then dpkg-buildpackage -j will work.
```

- swss (can be built in parallel, ~7m -> ~2m)
- swss-common (can be built in parallel)
- sairedis (~20m -> ~7m)

## Seperate sairedis RPC from non-RPC build

Some work is done on that but no PR (https://github.com/sonic-net/sonic-sairedis/issues/333)

sairedis is a dependency for a lot of targets (usually I see sairedis compilation takes a lot of time blocking other targets to start)

The idea of improvement is:

- No need to build libthrift, saithrift when 'ENABLE_SYNCD_RPC != y'
- The debian/rules in sairedis is written in a way that it will built sairedis from scratch twice - non-rpc and rpc version.

This improvement is achivable by specifying in rules/sairedis.mk:

```SAIREDIS_DPKG_TARGET = binary-syncd```

and conditionaly injecting libthrift depending on ENABLE_SYNCD_RPC.

The overal improvement ~10m.

sairedis target built time now is ~3m.

## Total improvement

It is hard to measure the total improvement, because since last time it was tested build system has changed (new packages were added and we finnaly moved to stretch for all dockers)

Few month ago on our build server with 12 CPUs sonic took around ~6h.
Right now on the same server it is around 2.5h. Enabling ```SONIC_USE_BUILD_KIT=y``` I was able to build the image in 1.5h.
The test included linux kernel built from scratch and not downloaded pre-built package.

