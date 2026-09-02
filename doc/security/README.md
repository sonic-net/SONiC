# SONiC Security

This directory is the home for SONiC security-related design documents and initiatives.

## Documents in this directory

| Document | Description |
|----------|-------------|
| [Static Analysis CI Gates](static-analysis-ci-hld.md) | Fleet-wide static analysis (Python, C/C++, Rust, Go, shell) wired into the existing per-repository build pipelines as a merge gate, driven from a shared `sonic-net/sonic-ci` repository. |

## Related documents elsewhere in `doc/`

Predating this directory, several security-related HLDs live in their own feature
directories. They are listed here for discoverability; they have not been moved, because
existing links and references point at their current locations.

| Document | Location |
|----------|----------|
| Container Hardening | [`doc/Container Hardening/SONiC_container_hardening_HLD.md`](../Container%20Hardening/SONiC_container_hardening_HLD.md) |
| Password Hardening | [`doc/passw_hardening/hld_password_hardening.md`](../passw_hardening/hld_password_hardening.md) |
| Secure Boot | [`doc/secure_boot/hld_secure_boot.md`](../secure_boot/hld_secure_boot.md) |
| Secure Upgrade | [`doc/secure_upgrade/secure_upgrade.md`](../secure_upgrade/secure_upgrade.md) |

## Adding a document

New security-related design documents should be added to this directory and registered in
the table above. Follow the standard SONiC HLD template at
[`doc/guidelines/hld_template.md`](../guidelines/hld_template.md).
