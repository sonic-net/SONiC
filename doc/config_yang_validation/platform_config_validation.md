# SONiC Platform Specific Config Validation via YANG Models

## Table of Contents

- [1 Revision](#revision)
- [2 Project Overview](#project-overview)
- [3 Example: Buffer-Profile](#example-buffer-profile)
- [4 Design](#design)
    - [4.1 Design Summary](#design-summary)
    - [4.2 Framework](#framework)
    - [4.3 Expected behavior] (#expected-behavior)
- [5 Extending to new features](#extending-to-new-features)



### Revision

|  Rev  |  Date   |      Author      | Change Description |
| :---: | :-----: | :--------------: | ------------------ |
|  v0.1 | 2025-11-18 |     Rajath V     | Initial version of platform specific config validation HLD 

## Project Overview  

### Problem Statement
This document describes the broad guidelines to support platform specific config validation on SoNiC for YANG models. The goal of this framework is to provide an easy way to have simple validation checks for new features based on ASIC or platform constraints. 

### Goal
Enable platform level config validation on SoNiC using YANG models that are platform-specific and hold constraints that could vary between vendors/platforms.

### Scope
The scope of this project is to support platform specific config validation for all config fields that are defined in YANG models. This includes config fields updated via config CLI and gNMI/RESTCONF, as well as changes from config load / reload cases.

## Example: Buffer-Profile

```bash
#!/bin/bash

# Generate platform-specific YANG models from templates
TEMPLATE_DIR="/usr/local/platform-yang-templates"
OUTPUT_DIR="/usr/local/platform-yang-models"
# Dynamically determine platform name from the script name.
SCRIPT_NAME=$(basename "$0")
PLATFORM_SUFFIX=$(echo "$SCRIPT_NAME" | sed 's/^sonic-platform-//' | sed 's/\.postinst$//')
PLATFORM_NAME="x86_64-${PLATFORM_SUFFIX}"
PLATFORM_NAME=$(echo "$PLATFORM_NAME" | sed 's/nexthop-/nexthop_/')
FEATURE_CAPABILITIES_JSON="/usr/share/sonic/device/${PLATFORM_NAME}/feature_capabilities.json"

# Check if all required components exist
if [ -d "$TEMPLATE_DIR" ] && [ -f "$FEATURE_CAPABILITIES_JSON" ] && command -v j2 >/dev/null 2>&1; then
    mkdir -p "$OUTPUT_DIR"

    # Generate YANG files from templates
    for template in "$TEMPLATE_DIR"/*.yang.j2; do
        [ -e "$template" ] || continue
        filename=$(basename "$template" .j2)
        output_file="$OUTPUT_DIR/$filename"

        if j2 "$template" "$FEATURE_CAPABILITIES_JSON" > "$output_file" 2>/dev/null; thenExpand commentComment on line R23ResolvedCode has comments. Press enter to view.
            echo "Generated: $output_file"
        else
            echo "Warning: Failed to generate $output_file" >&2
        fi
    done
fi
```

Note: The above snippet is just an example and may need to be modified based on the specific platform and requirements. It uses `PLATFORM_SUFFIX`, `PLATFORM_NAME` to dynamically determine the platform name from the postinst script name. This assumes that the postinst script name follows a specific naming convention (e.g., `sonic-platform-nexthop-4010-r0.postinst`). The `FEATURE_CAPABILITIES_JSON` path is constructed based on the platform name. This is to override any symlinks made in the repository for multiple platforms to point to a single `postinst` file, since each platform may have different `feature_capabilities.json` files.


An example for feature_capabilities.json is shown below:
```json
{
    "mmu_capabilities": {
            "bpf_dynamic_th_low": -7,
            "bpf_dynamic_th_high": 3
    }
}
```

An example for the template is shown below:
```jinja2
module sonic-buffer-profile-capability {
    yang-version 1.1;
    namespace "http://github.com/sonic-net/sonic-buffer-profile-capability";
    prefix bpf-capability;

    import sonic-buffer-profile {
        prefix bpf;
    }

    description "SONIC buffer profile platform-specific YANG model - generated from feature_capabilities.json";

    revision 2025-11-12 {
        description "Initial revision Generated from feature_capabilities.json at installation time";
    }

    {% if mmu_capabilities is defined %}
    {% set bpf_dynamic_th_low = mmu_capabilities.bpf_dynamic_th_low %}
    {% set bpf_dynamic_th_high = mmu_capabilities.bpf_dynamic_th_high %}

    // Platform-specific deviations - BUFFER_PROFILE uses bpf_dynamic_th range from mmu_capabilities
    deviation "/bpf:sonic-buffer-profile/bpf:BUFFER_PROFILE/bpf:BUFFER_PROFILE_LIST/bpf:dynamic_th" {
        deviate replace {
            type int32 {
                range "{{ bpf_dynamic_th_low }}..{{ bpf_dynamic_th_high }}" {
                    error-message "Invalid dynamic_th for this platform. dynamic_th should be in the range [{{ bpf_dynamic_th_low }}, {{ bpf_dynamic_th_high }}]";
                }
            }
        }
        description "Platform-specific deviation for dynamic_th";
    }
    {% else %}
    // No buffer profile capability data - skip validation.
    {% endif %}
}
```

Apart from this, there's two other changes that are required to implement the framework:

1. Ensure that the new jinja2 templates are packaged by `sonic-yang-models` wheel. This can be done by adding the following line to `setup.py`:
```python
    data_files=[
        ('platform-yang-templates', glob.glob('./platform-yang-templates/*.yang.j2')),
    ],
```
2. Modify the `sonic_yang.py` and `sonic_yang_ext.py` files to load the generated YANG files from `/usr/local/platform-yang-models/`. This can be done by adding the following lines to the `_load_schema_modules` function in both files:
```python
    generated_yang_dir = "/usr/local/platform-yang-models"
    if os.path.exists(generated_yang_dir):
        generated_yang = glob.glob(generated_yang_dir + "/*.yang")
        py.extend(generated_yang)
```

## Design

### Design Summary
The framework is based broadly on two things - leveraging feature_capabilities.json files specific to each platform and using jinja2 templates to generate custom yang checks at runtime. Combining these two things allows for checks to be added only on those platforms that need them, eliminating unnecessary overhead for other platforms who can resort to default values.

This is especially important for features like ARS where limits are specified per platform, and currently there is no concrete implementation for injecting non-default values in the validation flow. Without this, config_db accepts all the data, but functionality fails and there is no other way to check this except from show logging.

This is cumbersome, especially for range checks for multiple objects per feature. Hence a better way is to guardrail it at the YANG validation level, which doesn’t write into config_db if there are out-of-bound values. 


### Framework

The design follows the current yang validation flow, and appends additional checks into it. Along with this, we also implement a postinst hook that is platform-specific, and checks whether there is a feature_capabilities.json file to generate the yang file using jinja2 templates to add to the yang validation flow.

The flow can be shortened to this:

feature_capabilities.json + YANG template → Generated YANG → Runtime validation

The directory structure can be broadly classified as follows:


```bash
src/sonic-yang-models/
├── yang-models/                    # Static YANG files
│   ├── sonic-buffer-profile.yang
│   ├── sonic-vlan.yang
│   └── ...
├── yang-templates/                 # Build-time templates (existing)
│   ├── sonic-acl.yang.j2          # Rendered during build for py/cvl variants
│   ├── sonic-extension.yang.j2
│   └── ...
├── platform-yang-templates/        # NEW: Runtime templates
│   ├── sonic-buffer-profile-capabilities.yang.j2
│ 
└── setup.py                        # Modified to package platform-yang-templates/
```
 
We’ll take the example of sonic-buffer-profile.yang as our baseline.

With this flow, after the postinstall hook, new files will be generated and installed on the box. The locations for these are depicted below:


```bash
/usr/local/
├── yang-models/                      # Base YANG models (from wheel)
│   ├── sonic-ars.yang
│   ├── sonic-port.yang
│   └── ...
├── platform-yang-templates/          # Platform-specific templates (from wheel)
│   ├── sonic-buffer-profile-capabilities.yang.j2
└── platform-yang-models/            # Generated YANG (created at install time)
    ├── sonic-buffer-profile-capabilities.yang
   

/usr/share/sonic/device/x86_64-nexthop_4010-r0/
├── feature_capabilities.json                     # Input data for templates
├── hwsku.json
└── ...
```

The changes required in postinst files are mainly:

1. Check if feature_capabilities.json exists
2. Check if platform-yang-templates directory exists
3. If both exist, render all templates in platform-yang-templates and save the output to platform-yang-models

### Expected behavior

Generally, config changes come from config load / reload, config CLI and gNMI. For config load / reload -y cases, YANG validation is hit and therefore platform-specific validation should kick in. For config CLI and gNMI cases, since we already have the YANG validation in place, the platform-specific validation should kick in as well.

However, manually writing config_db.json or running config will not trigger the YANG validation, and therefore the platform-specific validation will not kick in. This is expected behavior, as the user is bypassing the validation layer by directly modifying the config_db.json, without doing a config reload -y. Loading a different json file via config load / reload should still work as expected.

## Extending to new features

Since the infrastructure to add and extend yang parsing and also generate the new platform yang template files are all present, any new feature owner can simply extend the `feature_capabilities.json` if it exists, or add a new `feature capabilities.json` file to the platform of their choice. This should be coupled with a `jinja2` template for a yang file in the directory `src/sonic-yang-models/platform-yang-templates/`,
where the actual checks according to the capabilities are defined and current yang models are extended / deviations made. And to add to this, a platform-specific `postinst` file must be created / leveraged to add the jinja2 creation at runtime code.


In summary, a new feature owner has to:

1. Check if the nexthop postinst file already has the code for checking and generating platform-specific YANG files. If not, add this code.
2. Create a new `feature_capabilities.json` file or add into the current file if it exists. Add a key - <feature>_capabilities: With values being the custom ranges / any non default values that might be necessary for that platform.
3. Create a `sonic-<feature>-capability.yang.j2` file in `sonic-buildimage/src/sonic-yang-models/platform-yang-templates/` directory. This will be used to generate the new `<feature>-capability.yang` in the `/usr/local/platform-yang-models` directory on the box.	
