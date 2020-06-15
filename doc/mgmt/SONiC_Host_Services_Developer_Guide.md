Developer Guide - SONiC Host Services
=====================================

# Introduction

The SONiC management infrastructure requires certain actions to be executed on
the host. Since the management plane runs inside a container, there is a
separate host service that runs on the host, and communicates with the container
over D-Bus.

# High-level architecture

The host services infrastructure is designed so that it easily communicates with
the management framework and telemetry containers. The host service is a Python
application, and consists of a number of "servlets". Each servlet serves a class
of functions, such as image management, ZTP, show tech-support, etc. The
container API is a part of the transformer library, and has a wrapper function
to allow the app module to communicate with its peer servlet on the host.

The design assumes that the individual app module developers do not know the
details of D-Bus, and in fact does not require them to. The wrapper function and
the servlets take care of hiding the details of the D-Bus implementation from
the developer, and the only D-Bus specific knowledge that the developer needs to
know is the function signature identifiers as described in the [python-dbus API
documentation][dbus].

## Servlets

Servlets are short Python snippets that reside on the host and provide the
application specific service. These must reside under `scripts/host_modules` in
the `sonic-mgmt-framework` repository.

The servlet must import the `host_service` module, and create a derived class
from `host_service.HostModule`. The class should have instance methods that
are decorated with the `@host_service.method` decorator. Each function may take
input parameters and return output parameters. The D-Bus API requires knowledge
of the parameter types for each function, therefore, these must be specified,
otherwise, the servlet will not be able to correctly process the user request.

The `host_service.method` decorator takes in several parameters, as defined by
the [python-dbus API documentation][dbus], however, we are only concerned with
the following parameters, as listed in the example below.

```python
@host_service.method(host_service.bus_name(MOD_NAME),
                     in_signature='...',
                     out_signature='...')
def func(self, in_param_1, in_param_2, ...):
    return out_param_1, out_param_2, ...
```

The key identifier is the `MOD_NAME` constant, which defines the namespace for
all functions within the servlet class. For example, the `showtech.py` servlet
sets `MOD_NAME` to be `showtech`, which when used with the `host_service.method`
decorator, causes the `info` function to be addressable using `showtech.info`.

`in_signature` and `out_signature` default to the empty strings, indicating no
input and return values respectively. However, if the function takes in
parameters, or returns any values, it is mandatory to specify them. The data
types are as declared [here][dbus].

## Transformer utility

Individual app modules may communicate with the host service using the
`hostQuery` or `hostQueryAsync` functions in the `transformer` package. These
functions perform very similar actions, with the difference being that the
`hostQuery` function returns a `hostResult` structure, while the
`hostQueryAsync` function returns a `hostResult` channel and an error. Both
functions take in the endpoint (e.g. `showtech.info`) and any arguments needed
by the corresponding function in the host.

The `hostResult` structure contains two parameters, a `Body`, which is of type
`[]interface{}`, and an `Err` which is an error type. If the host function
defined by the endpoint succeeds, the `Body` parameter will contain the return
values from the function.

The app module must prepare the input parameters according to the `in_signature`
declaration in the function decorator. E.g., if `in_signature='as'`, meaning an
array of strings, then the args passed to `hostQuery` must be of type
`[]string`. If the types of the parameters don't match, the request will fail,
and the `.Err` member will contain the corresponding error.

The `hostQueryAsync` function may be used if you want to "fire-and-forget" the
host request. This will return a channel which will contain the `hostResult`
structure when the function finishes executing. If you don't care about the
result, then make sure you clean up the channel by reading and discarding the
result in a separate gorouting. Eg.

```go
ch, err := hostQueryAsync("some_long_running.function")
if err != nil {
    go func() {
        <- ch
    }()
}
```

[dbus]: https://dbus.freedesktop.org/doc/dbus-python/tutorial.html#basic-types



