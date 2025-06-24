
# Migrating Image-Managed Docker Containers to Kubernetes with Resource Control

## Background

In current SONiC architecture, Many containers are image-managed, which means it's packed into build image and managed by NDM Golden config. And commonly deployed and managed using `systemd` and monitored using tools like `monit`. But after KubeSonic comes into picture, this deolpyment lacks advanced orchestration and native resource management features offered by Kubernetes.

This document outlines a generic approach to migrate any Image-managed Docker container to Kubernetes, providing CPU and memory resource controls, while maintaining backward compatibility with the existing `systemd` workflows. The BMP container (`docker-sonic-bmp`) is used as a concrete example.

## Objective

- Standardize container deployment using Kubernetes, including the image native container which is controlled via NDM golden config FEATURE table.
- Enforce CPU and memory resource constraints natively.
- Maintain `systemd` interface for backward compatibility.
- Optionally integrate existing monitoring systems during transition.

---

## Standardize Kubernetes-Based container Deployment

### image native container migration

Since we need migration from a image-managed container to a Kubernetes-managed container, while preserving compatibility and avoiding dual-running instances.

There are some potential options as below:

### One-Time Migration Step
Define a Kubernetes pre-deployment job, which is to detect and stop/remove the native container (e.g., via systemd, Docker, etc.), before enabling the Kubernetes deployment.
Disable any native auto-restart logic (e.g., systemctl disable, docker rm -f && docker rm, etc.). But this may break some existing feature like CriticalProcessHealthChecker, featured, systemHealth, etc.

### Mirror the Real State into the Config Flag
This means we can keep updating the FEATURE table to reflect Kubernetes’ Real state

-When the K8s bmp Deployment enabled → set FEATURE|bmp "state = enabled"
-When the k8s Deployment is rollbacked → set FEATURE|bmp "state = disabled"

We can Implement this as Kubernetes-based CronJob as below:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sync-bmp-status
  namespace: sonic
spec:
  schedule: "*/1 * * * *" # every 1 minute
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: redis-updater
            image: redis:latest
            command: ["/bin/sh", "-c"]
            args:
              - |
                replicas=$(kubectl get deploy bmp -n sonic -o jsonpath='{.spec.replicas}')
                if [ "$replicas" -gt 0 ]; then
                  redis-cli HMSET FEATURE|bmp state enabled
                else
                  redis-cli HMSET FEATURE|bmp state disabled
                fi
            env:
              - name: REDIS_HOST
                value: my.redis.host
          restartPolicy: OnFailure

```

### Enforce CPU and memory resource constraints natively.

Kubernetes provides native resource management through the `resources` spec, allowing you to define minimum (`requests`) and maximum (`limits`) values for CPU and memory.

### Example Deployment YAML (Generic)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <container-name>
  namespace: <namespace>
spec:
  replicas: 1
  selector:
    matchLabels:
      app: <container-name>
  template:
    metadata:
      labels:
        app: <container-name>
    spec:
      containers:
      - name: <container-name>
        image: <container-image>
        command: ["<startup-command>"]
        resources:
          requests:
            memory: "100Mi"
            cpu: "100m"
          limits:
            memory: "800Mi"
            cpu: "500m"
        ports:
        - containerPort: <port>
        livenessProbe:
          exec:
            command: ["/usr/bin/pgrep", "<main-process>"]
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          exec:
            command: ["/usr/bin/pgrep", "<main-process>"]
          initialDelaySeconds: 30
          periodSeconds: 15
```

### Example: BMP Container

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bmp
  namespace: sonic
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bmp
  template:
    metadata:
      labels:
        app: bmp
    spec:
      containers:
      - name: bmp
        image: ksdatatest.azurecr.io/docker-sonic-bmp:latest
        command: ["/usr/local/bin/supervisord"]
        resources:
          requests:
            memory: "100Mi"
            cpu: "100m"
          limits:
            memory: "800Mi"
            cpu: "500m"
        ports:
        - containerPort: 5000
        livenessProbe:
          exec:
            command: ["/usr/bin/pgrep", "openbmpd"]
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          exec:
            command: ["/usr/bin/pgrep", "openbmpd"]
          initialDelaySeconds: 30
          periodSeconds: 15
```

---

## Maintaining `systemd` Compatibility

In environments where existing operational workflows depend on managing containers via systemd, we can preserve compatibility by implementing a proxy systemd unit that interacts with Kubernetes behind the scenes. This allows existing automation tools and scripts that call systemctl to continue functioning without modification, even though the container is now orchestrated by Kubernetes.

### Rationale


Many production systems have monitoring, automation, or recovery mechanisms that depend on:
- `systemctl start <service>`
- `systemctl stop <service>`
- `systemctl status <service>`

To prevent breaking these expectations during the migration, a `systemd` service stub can be provided.


### Step-by-Step Setup

#### 1. Create Wrapper Script

Create a script `/usr/local/bin/k8s-wrapper.sh` that translates `systemd`-style commands to Kubernetes `kubectl` actions:

```bash
#!/bin/bash
set -e

NAME="$1"
ACTION="$2"
NAMESPACE="default"

if [[ -z "$NAME" || -z "$ACTION" ]]; then
  echo "Usage: $0 <container-name> {start|stop|restart|status}"
  exit 1
fi

case "$ACTION" in
  start)
    echo "[INFO] Scaling $NAME deployment to 1"
    kubectl scale deployment "$NAME" --replicas=1 -n "$NAMESPACE"
    ;;
  stop)
    echo "[INFO] Scaling $NAME deployment to 0"
    kubectl scale deployment "$NAME" --replicas=0 -n "$NAMESPACE"
    ;;
  restart)
    echo "[INFO] Restarting $NAME deployment"
    kubectl rollout restart deployment "$NAME" -n "$NAMESPACE"
    ;;
  status)
    echo "[INFO] Getting pod status for $NAME"
    kubectl get pods -l app="$NAME" -n "$NAMESPACE" -o wide
    ;;
  *)
    echo "Usage: $0 <container-name> {start|stop|restart|status}"
    exit 1
esac
```

Make the script executable:

```bash
chmod +x /usr/local/bin/k8s-wrapper.sh
```


#### 2. Create systemd Unit File

Example unit file: /etc/systemd/system/bmp.service

```
[Unit]
Description=Kubernetes managed container bmp
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/k8s-wrapper.sh bmp start
ExecStop=/usr/local/bin/k8s-wrapper.sh bmp stop
ExecReload=/usr/local/bin/k8s-wrapper.sh bmp restart
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

#### 3. Reload systemd and Enable the Stub Service
```

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable bmp.service
```

```

sudo systemctl start bmp.service
sudo systemctl status bmp.service
sudo systemctl stop bmp.service
```

### Limitations


systemctl status does not show process PID or exit codes—it proxies Kubernetes pod status.

Restart policies (e.g., Restart=on-failure) defined in systemd will not work—Kubernetes handles restarts via livenessProbe and restartPolicy.

This assumes kubectl is installed and configured to access the correct Kubernetes cluster and namespace.

### Benefits

No disruption to automation or legacy tooling using systemctl.

Operators familiar with systemd can continue using the same commands.

Allows gradual migration to a fully Kubernetes-native setup.

---

## Monitoring and Alerting

Kubernetes supports integrated monitoring using:
- `kubectl top pod` for resource snapshots
- Prometheus and AlertManager for alerting
- Fluentd, Loki, or EFK stack for logging

If legacy tools like `monit` must be retained temporarily, rewrite checks to use Kubernetes data (e.g., via `kubectl top`) instead of Docker or CGroup files.

---

## Migration Strategy

1. **Deploy container in Kubernetes** in a test environment.
2. **Verify application health, logs, and performance.**
3. **Create `systemd` wrapper service** to mimic old interface.
4. **Transition monitoring (if applicable).**
5. **Gradually phase out Monit or Docker-native tools.**
6. **Monitor and document stability in production.**

---

## Conclusion

This document provides a generic, reusable pattern for migrating Docker containers from `systemd` + `monit` to Kubernetes. It ensures modern resource control, while preserving backward compatibility during transition. The BMP container serves as a concrete example of this process.
