
# High-Level Design (HLD) for Health Diagnostic Module in SONiC gNMI Server

## Overview
The purpose of this design is to add a health diagnostic module to the SONiC gNMI server, which supports health status reporting both for KubeSonic HTTP probes and gNMI-based diagnostics. The module will provide container health metrics such as CPU utilization, memory usage, disk occupation, and certificate expiration. The health status will be reported in **Dial-in** mode using the gNMI interface, and health proofs will be logged to syslog.

## Requirements

- **Health status report**
  - Within a KubeSonic HTTP request, if the container is healthy, return `http status code = 200` as a normal probe response; otherwise, indicate the container is unhealthy.
  - Return a result based on factors such as CPU utilization, memory usage, disk occupation, and certificate expiration.
  - Record all proofs (logs, metrics) to syslog for further investigation into why the container was deemed healthy or unhealthy.

- **gNMI Integration**
  - The health data must be available as part of the gNMI `Get` RPC for **Dial-in** mode, which will return container health metrics.

- **Performance Considerations**
  - The health checks should be lightweight and should not negatively impact gNMI server performance.

## Design Components

### 1. Health Diagnostic Module
The health diagnostic module is responsible for gathering container-specific metrics related to system resource usage, certificate expiration, and the health of network interfaces and containers.

#### Responsibilities:
- Report the health state when a KubeSonic probe requests it via an HTTP call.
- Gather container metrics (CPU, memory, disk occupation, certificate expiration).
- Return `http status code 200` if the container is healthy, otherwise report as unhealthy.
- Log all proofs to syslog for further analysis and troubleshooting.
- Support gNMI integration to return health data for **Dial-in** mode.

#### Module Structure
- `GetHealthInfo()`: A function to gather container-level health metrics including CPU utilization, memory usage, disk usage, and certificate expiration.
- `ReportHealthToKubeSonic()`: A function that responds to KubeSonic HTTP probes with the health state based on the gathered metrics.
- `LogHealthProofs()`: A function that logs health check data (proofs) to syslog for investigation.

```go
package health

import (
    "log/syslog"
    "net/http"
)

type ContainerHealthInfo struct {
    ContainerID      string
    CPUUtilization   float64
    MemoryUsage      float64
    DiskOccupation   float64
    CertExpiration   int64 // days until expiration
    Status           string
}

func GetHealthInfo() ([]ContainerHealthInfo, error) {
    // Example logic to gather container health metrics (using Docker or containerd APIs)
}

func ReportHealthToKubeSonic(w http.ResponseWriter, r *http.Request) {
    healthInfo, err := GetHealthInfo()
    if err != nil {
        http.Error(w, "Failed to gather health metrics", http.StatusInternalServerError)
        return
    }
    // Evaluate the health info, return HTTP status code 200 for healthy, else non-200
    for _, container := range healthInfo {
        if container.CPUUtilization < 80.0 && container.MemoryUsage < 80.0 && container.DiskOccupation < 90.0 && container.CertExpiration > 30 {
            w.WriteHeader(http.StatusOK)
        } else {
            w.WriteHeader(http.StatusServiceUnavailable)
        }
        LogHealthProofs(container)
    }
}

func LogHealthProofs(container ContainerHealthInfo) {
    logwriter, err := syslog.New(syslog.LOG_NOTICE, "container_health")
    if err == nil {
        logwriter.Info("Health check for container " + container.ContainerID + ": " +
            "CPU=" + fmt.Sprintf("%.2f", container.CPUUtilization) +
            ", Memory=" + fmt.Sprintf("%.2f", container.MemoryUsage) +
            ", Disk=" + fmt.Sprintf("%.2f", container.DiskOccupation) +
            ", CertExpiryDays=" + fmt.Sprintf("%d", container.CertExpiration))
    }
}
```

### 2. YANG Model Extension
The YANG model is extended to provide paths for reporting container health metrics in **Dial-in** mode using gNMI.

```yang
module sonic-health {
    namespace "http://github.com/sonic-net/sonic-gnmi/health";
    prefix "sh";

    container container-health-status {
        list container {
            key "container-id";

            leaf container-id {
                type string;
                description "ID of the container";
            }

            leaf cpu-utilization {
                type decimal64 { fraction-digits 2; }
                description "Percentage of CPU utilization for the container";
            }

            leaf memory-usage {
                type decimal64 { fraction-digits 2; }
                description "Memory usage for the container";
            }

            leaf disk-occupation {
                type decimal64 { fraction-digits 2; }
                description "Percentage of disk occupation for the container";
            }

            leaf cert-expiration {
                type int64;
                description "Days remaining before the certificate expires";
            }

            leaf status {
                type string;
                description "Container status (running, stopped, etc.)";
            }
        }
    }
}
```

### 3. gNMI Server Integration
The `Get` RPC will support paths to retrieve container health diagnostics based on the extended YANG model.

```go
func (s *Server) Get(ctx context.Context, req *gnmi.GetRequest) (*gnmi.GetResponse, error) {
    for _, path := range req.Path {
        if path == "/container-health-status" {
            containerHealthInfo, err := health.GetHealthInfo()
            if err != nil {
                return nil, err
            }
            // Construct the GetResponse for container health data
        }
    }

    return &gnmi.GetResponse{}, nil
}
```

### 4. Testing and Validation
The extended testing will include:
- Validation of both system and container health data for KubeSonic HTTP probes and gNMI diagnostics.
- Simulated container crashes, resource exhaustion, and certificate expiration to verify health diagnostics behavior.
- Testing syslog output for proper recording of health proofs.

## Conclusion
This high-level design extends the gNMI health diagnostic module to cover both system and container health diagnostics, with KubeSonic HTTP probe support and syslog-based logging. The design ensures comprehensive health monitoring and supports **Dial-in** mode using gNMI, providing real-time health information to clients and remote collectors.
