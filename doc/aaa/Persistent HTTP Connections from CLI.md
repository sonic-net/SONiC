Persistent HTTP connections from CLI
====================================

The SONiC CLI provided by the management framework container runs an instance of
klish, which provides a fixed set of commands. The CLI is simply a front-end to
the REST server, and each command is mapped to a corresponding REST endpoint.

# Command Flow

When the user enters a specific command on the CLI, the corresponding `ACTION`
tag in the CLI XML specification shells out to a Python script with any
arguments and an optional template to format the returned values. This script
connects to the REST server on the local machine over HTTPS, retrieves and
formats the JSON response. The Python script then exits, terminating any HTTP
connection that had been set up.

This is the current behavior, even without RBAC support, which means that every
command will need to set up a new HTTPS connection. However, when RBAC is
enabled, it is not likely to cause a noticeable performance impact, since the
system is already incurring the TLS overhead.

As can be seen from the flow above, it is not possible to set up a persistent
HTTP connection, since every command spawns a new connection.

# Alternative Designs

This section describes some alternative designs that will enable the CLI to
create a persistent connection.

## Proxy service

As part of the management framework, we can add a "proxy" service that is
spawned with the CLI. This service will set up a secure HTTP connection for the
authenticated user, and create a local unix socket that is accessible only by
that user. The CLI XML will remain unchanged, but the Python ApiClient class
will be changed to connect to the local socket.

This will still create independent HTTP connections, but they can be insecure
connections, while the proxy service will transfer the connections from the
insecure unix socket to the secure tunnel, which will reduce the TLS connection
time.

**Note:** The security considerations have not been completely mapped out, and
this may open the system up to security holes.

## Klish modification

This approach considers modifying the Klish executable.  When Klish is spawned,
it will set up the HTTPS connection and keep it alive as long as the CLI is
active. Each `ACTION` tag will call into klish functions that will connect to
the existing HTTPS connection.

This approach is the most secure option, however, it needs heavy modification to
klish, and there are several unknowns at this time.

## No modification - Buzznik

This approach leaves the design as is for the Buzznik release. Every command
will continue to create a new HTTPS connection, as it does today, and will tear
down the connection on completion of the request.
