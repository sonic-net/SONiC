# Event Producer via rsyslog

## Goals
1. Ability to stream syslog messages from apps as structured data via streaming telemetry
2. Adapt III party applications to Events/alarm framework

## Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes, oftent 10+.

## Possible solutions
1. Parse the log messages as app emits it.
2. Push the parsed data as JSON struct of {name: val[, ...]} to a redis DB table.
3. Now any tool can subscribe to that table for events
4. The container image provides the regex to parse the log messages. The app can update the log and update regex to be in sync

