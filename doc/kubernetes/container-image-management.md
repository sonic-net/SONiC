# Why container image management

After we support container upgrade via k8s, for the container image, we have two problem to be fixed.
- After we upgrade one container to a higher version via k8s, if k8s control plane is down and worker reboot, container need to go back to local mode, local mode container should run the newest version other than the original version.
- Upgrade will bring a new version image to sonic device, after upgrade many times, the disk will be full, need to avoid this.

So we need to manage the container image to fix these two problems

# Existing designs need to know first
### 1. local mode and kube mode
The container has two modes. Kube mode means that the contianer is deployed by k8s, the container image version is defined in daemonset like below. The image need to be downloaded from ACR, so it's with ACR prefix.
```
sonick8scue.azurecr.io/docker-sonic-telemetry:v1
```
 Local mode means that the container is created and started by systemd service, and systemd service will always use local latest image like below to create container.
 ```
 docker-sonic-telemetry:latest
 ```

### 2. Kube container will not replace the local container when their image versions are the same.
##### why this design
when the kube container and local container are in the same version, local container should be more stable, becasue it has run for some time. And when device first join k8s cluster as worker, k8s will try to deploy a same version container with local, if we choose replace, the container will has a down time, actually no upgrade happens, down time is not necessary.
##### one note
The kube container will dry-run, no main supervisord services start inside the container. But it still downloads the sonick8scue.azurecr.io/docker-sonic-telemetry:v1 image on device.
# How to handle Tag-Latest and Clean-Up
## How to Tag-Latest
For the first problem, since the systemd service will alway use image with latest tag, we can tag the newest version image as latest version. 
- When: If the new version of container has been running for more than 10 minutes, it means it's stable, and we will tag it as latest.
- Our customized k8s controller will complete the upgrade process within 10 minutes, if fallback happens or something wrong, it's impossible that the container run for more than 10 minutes, for this case, we can't tag the new version image to latest
- After we tag latest, we need to remove the previous stopped local container, otherwise when go back to local, systemd service will not create new local container with new version image and will start the stopped container which running with a previous version image.
## How to Clean-Up
For the second problem, we need to remove the old version images in time.
- Why we don't leverage k8s image clean up function for worker. Kubelet will try to remove all docker images which is not used, our upgrade only support telemetry now, we don't want k8s touch other container's image.
- When: Tag latest will trigger Clean-Up, once the tag latest successfully finished, we will do Clean-Up
- Besides the current running container image version and last stable version(last tagged latest version), Clean-Up will clean up all other version images (for fallback preparation)
- For image removal, we have three cases to handle:
    - Case 1: after device(v1) joined k8s cluster, k8s will deploy v1 container to device, kube v1 container  will dry-run. Due to no local to kube replacement happens, Tag-Latest and Clean-Up will not happen. Then we upgrade container to v2 via k8s, kube v2 container will run and replace the local one. Then the images on device after Tag-Latest should be like below:
        ```
        docker-sonic-telemetry:latest(v2)  image_id: kube_v2
        docker-sonic-telemetry:v1  image_id: local_v1
        sonick8scue.azurecr.io/docker-sonic-telemetry:v1  image_id: kube_v1
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        ```
        This case we need to remove kube v1 image, because it only dry-run before, then we tag local v1 image to kube v1 image for fallback prepared, then remove local v1 tag. Then the images after Clean-Up should be like below:
        ```
        docker-sonic-telemetry:latest(v2)  image_id: kube_v2
        sonick8scue.azurecr.io/docker-sonic-telemetry:v1  image_id: local_v1
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        ```
    - Case 2: proceed from the case-1, we have upgrade all devices in one device group container to kube v2 via k8s, then one device get re-imageed, the device is v3, after the device rejoin to k8s cluster, k8s will deploy kube v2 container, kube v2 container will run and replace the local v3 container. Then the images on device after Tag-Latest should be like below:
        ```
        docker-sonic-telemetry:latest(v2)  image_id: kube_v2
        docker-sonic-telemetry:v3  image_id: local_v3
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        ```
        This case we only need to remove local v3 image, becase it's not last latest version for the k8s daemonset. Then the images after Clean-Up should be like below:
        ```
        docker-sonic-telemetry:latest(v2)  image_id: kube_v2
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        ```
        
    - Case-3, proceed from the case-1, we upgrade container to v3 via k8s, kube v3 container will run and replace the last kube v2 container. Then the images on device after Tag-Latest should be like below:
        ```
        docker-sonic-telemetry:latest(v3)  image_id: kube_v3
        sonick8scue.azurecr.io/docker-sonic-telemetry:v1  image_id: local_v1
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        sonick8scue.azurecr.io/docker-sonic-telemetry:v3  image_id: kube_v3
        ```
        This case we only need to remove local v1 image which is with kube tag. Then the images after Clean-Up should be like below:
        ```
        docker-sonic-telemetry:latest(v3)  image_id: kube_v3
        sonick8scue.azurecr.io/docker-sonic-telemetry:v2  image_id: kube_v2
        sonick8scue.azurecr.io/docker-sonic-telemetry:v3  image_id: kube_v3
        ```
        This case is most ofen happened

- one note is that kube v1 image and local v1 image's image id maybe not same.

