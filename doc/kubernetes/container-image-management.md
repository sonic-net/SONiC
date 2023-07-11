# Why container image management

- After we support container upgrade via k8s, for the container image, we have two problem to be fixed.
    - After we upgrade one container to a higher version via k8s, in this time, k8s is down or something wrong, container need to go back to local mode, local mode container should be the higher version other than the original version.
    - Upgrade will bring a new version container image to sonic, after many times upgrade, the disk will be full, need to avoid this.
- So we need to manage the container image to fix these two problems


# How to handle the two problems
- Tag latest
    - Each time we do upgrade, after we think the new version is good, we tag the image version to latest. When need to go back to local, local mode will use the latest version image
    - How to "think the new version is good", after the new version container is running, we will check the container is still running or not in ten minutes, still running mean the new version is good so that we can do  tag latest. Not running means fallback happens or something wrong, we can't tag the new version image to latest
    - After we tag latest, we need to remove the previous stopped local container, otherwise when go back to local, systemd service will not create new local container with new version image and will start the stopped container which running on a previous version image.
- Image Clean-Up
    - Tag latest will trigger Clean-Up, once the tag latest successfully finished, we will do Clean-Up
    - Clean-Up will clean up all old version images beside the last latest version image(for fallback usage)
    - How to handle one special case
        - After we upgrade one container from local mode(v1) to kube mode(v2) and we tag the v2 version image to latest, before we do Clean-Up we will find there is two cases for container image versions
            - Case 1:
                ```
                docker-sonic-telemetry:latest(v2)
                docker-sonic-telemetry:v1
                sonick8scue.azurecr.io/docker-sonic-telemetry:v1
                sonick8scue.azurecr.io/docker-sonic-telemetry:v2
                ```
            - Case 2:
                ```
                docker-sonic-telemetry:latest(v2)
                docker-sonic-telemetry:v1
                sonick8scue.azurecr.io/docker-sonic-telemetry:v2
                ```
        - For case-1, we remove sonick8scue.azurecr.io/docker-sonic-telemetry:v1 and tag docker-sonic-telemetry:v1 to sonick8scue.azurecr.io/docker-sonic-telemetry:v1 and remove docker-sonic-telemetry:v1.
        - For case-2, we remove docker-sonic-telemetry:v1 directly.
        - Why are there these two cases, find answer in next section.

# Kube container will not replace the local container when their image version are the same.(Suppose the versions are both v1)
- Why: when they are in the same version, local container should be more stable and no need to restart the container so no down time; when we rollout, we will enable k8s on many devices, we don't want the containers restart at the same time.
- The kube container will dry-run, no real services start inside the container. But it will still download the sonick8scue.azurecr.io/docker-sonic-telemetry:v1 image.
- Actually docker-sonic-telemetry:v1 and sonick8scue.azurecr.io/docker-sonic-telemetry:v1 have the defferent image id, but docker-sonic-telemetry:v1 really runs before and the latter not. So for the Clean-Up case-1, we will remove latter, because it never really run before, and tag the docker-sonic-telemetry:v1 to sonick8scue.azurecr.io/docker-sonic-telemetry:v1 and remove docker-sonic-telemetry:v1 to get last latest image prepared for fallback
- How Clean-Up case-2 comes? Suppose we have a device group, all devices' containers running on v2 version in kube mode, now one device reimaged, it's sonic version is v3, once the device rejoin to k8s cluster, k8s scheduled v2 container will replace the local v3 container. V3 image can't be the last latest image version, so clean up the v3 image directly.
