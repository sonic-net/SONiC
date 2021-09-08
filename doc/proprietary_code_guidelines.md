
# Guidelines for referencing proprietary code #

### Scope

This document contains guidelines for referencing proprietary code within SONiC repositories. This covers, for example, adding support for routing stacks other than FRR/Quagga, where the routing stack itself is not open source but requires changes to core SONiC code to allow it to be built and run. The same applies to platforms where the platform library is not open source.

### Requirements

The following are requirements that any references to proprietary code must meet in order to be included in core SONiC code.
- Functionality must be entirely unchanged for anyone not using the proprietary code.
- Making changes to core SONiC code must remain as easy as before the references are added. A developer must be able to make changes to SONiC without having to think about its impact on the proprietary code.

In particular this means that it is not a requirement for developers to test the references to proprietary code if they are not using it. Responsiblity for maintaining these references belongs to the owners of the proprietary code.

### Guidelines

The following are guidelines for how references to proprietary code should be included in the core SONiC code. These should be used when writing or reviewing such code.

- Code that only applies if certain proprietary code is available (e.g. a particular routing stack) must be protected by checks to ensure that this code does not run if the proprietary code is not present.
  - When applicable this should use existing variables (e.g. the configured routing stack) to allow easy extensibility and compatibility with existing checks in the code.
- Large blocks of code should be stored in separate files where possible, or functions if not, clearly marked as being related to the relevant e.g. routing stack/platform. The core code should then make a single call into the proprietary related code, reducing the impact on the readability of the core code.
- If certain core code must not be run when specific proprietary code is in use, this may be wrapped in checks. This should be done in as few places as possible, to reduce impact on the readability and maintainability of the core code.

### Worked examples

#### 1. Adding additional show commands specific to a given routing stack

If you have show commands that only apply to a given routing stack, here called "new_stack", this should be done similar to the following.

Define your show commands in files in a new subdirectory, sonic-utilities/show/new_stack. For example, add ```sonic-utilities/show/new_stack/__init__.py``` with the following contents:

```
import click

def add_commands(cli):
	@cli.group(cls=clicommon.AliasedGroup)
    def new_cli_group():
        """Show new CLI commands"""
        pass

    @new_cli_group.command()
    def new_command():
    	< Code for new show command >
```

Then in ```sonic-utilities/show/main.py``` include this code by adding to the existing routing stack check as follows:
```
if routing_stack == "quagga":
    from .bgp_quagga_v4 import bgp
    ip.add_command(bgp)
    from .bgp_quagga_v6 import bgp
    ipv6.add_command(bgp)
elif routing_stack == "frr":
    from .bgp_frr_v4 import bgp
    ip.add_command(bgp)
    from .bgp_frr_v6 import bgp
    ipv6.add_command(bgp)
elif routing_stack == "new_stack":
	from . include new_stack
	new_stack.add_commands(cli)
```
#### 2. Removing a container dependency for a given routing stack
If you do not run a given container when using a given routing stack, you will want to remove any dependency on that container conditional on the routing stack.

For example if you do not run teamd (e.g. your routing stack implements LAG support itself) then in ```files/scripts/swss.sh``` change from:
```
MULTI_INST_DEPENDENT="teamd"
```
to:
```
ROUTING_STACK="$(/usr/local/bin/sonic-cfggen -y /etc/sonic/sonic_version.yml -v routing_stack)"
if [[ "$ROUTING_STACK" != "new_stack" ]]; then
	MULTI_INST_DEPENDENT="teamd"
fi
```