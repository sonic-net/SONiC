# Why need health-check
- Current status
    - We can only check whether the k8s scheduled container is running or not, couldn't exactly know the real supervisor service inside container is healthy or not
- Problems should be resolved
    - Health-check should check whether the real supervisor service is healthy or not
    - If not healthy, there better be different error codes to help debug

# How do we Implement the health-check 
- Leverage k8s probe tool
    - K8s has three kinds of probe, liveness, readiness and startup probes which can help us probe state inside container. Configure Liveness, Readiness and Startup Probes | Kubernetes, we can use startup probe for our scenario.
    - Startup probe has four probe types, http|TCP|gRPC|command, command type should be good for our scenario.
    - Command type means that we could deploy one script inside container, k8s will call this script and get the exit code when start the container. If the script exit code is zero, k8s thinks it's healthy. If the script exit code is non-zero, k8s think it's not healthy. We can use different non-zero exit codes to recognize what the issue is if probe failed.
    - Start command probe example:
    - ![](startup_probe.jpg)

# How do we implement the script inside container
- Script path and name
    - /usr/bin/readiness_probe.sh
- Health-Check logic in the script(two steps for now)
    - Do common checks which are same for all containers
        - Currently, one common check is that if the supervisor start.sh exists, we need to ensure that it exits with code 0.
        - Will not check critical services, because these services should be managed by the exit-listener supervisor service.
    - Call container self-related specific executable script if exists
        - Executable script path and name
            - /usr/bin/readiness_probe_hook
        - Feature owner should implement the pythons script if needed
            - One note is that exit code should be 0 if all are good. If not, need to define the exit code clearly so that we can figure out the issue once happens.
