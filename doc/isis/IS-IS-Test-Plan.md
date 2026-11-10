# IS-IS integration test plan

## Scope and prerequisites

Validate the implemented five-table ConfigDB → recovery worker → existing FRR
path, explicit interface binding, per-level configuration and operational CLI.
This plan updates the prior binding/response cases to the new contract. New cases
cover the agreed overload, SPF, redistribution and recovery capabilities; they
are not a separate expansion into SRv6 or changes to FRR.

- Install matching utilities, YANG models and framework packages. Set
  `DEVICE_METADATA|localhost.frr_mgmt_framework_config=true`, restart the affected
  bgp container, and confirm isisd and frrcfgd are running.
- Prepare `default`, `VrfA`, `VrfB` and routed interfaces. Use the existing SONiC
  interface workflow to change VRF; changing only the IS-IS row is not a VRF move.
- Use distinct instance names `CORE` and `EDGE`. NETs in the same VRF must share
  a system ID; different VRFs may use different system IDs.
- Exercise Ethernet, PortChannel, VLAN, loopback and VLAN subinterfaces where
  available. Reject member ports in place of routed aggregates.
- Use the Force10 seven-node topology for passive-loopback IPv4/IPv6 forwarding.
  Record actual interfaces, peer addresses and loopback prefixes from its profiles.
- Select the same ASIC namespace for configuration and observation. Confirm the
  other ASIC remains unchanged. Run disruptive recovery cases on a dedicated lab.

### Seven-node forwarding prerequisites

Use P1–P4 and PE1–PE3 with the twelve links in `topo_force10-7nodes.yml`.
The existing profiles number the fabric links with IPv6; enabling the IPv4 IS-IS
AF alone does not provide a verified IPv4 next-hop setup. The integration fixture
adds consecutive /31s from `198.19.0.0/27` to the same twelve links, preflights
all seven nodes for collisions before writing, preserves exact pre-existing
addresses, and removes only addresses it added, including after setup failure.
Original IPv6 addressing and BGP configuration remain the baseline.

The profiles also redistribute connected IPv6 prefixes into BGP. During the
P1↔PE3 forwarding case, temporarily suppress that redistribution on P1 and PE3,
without stopping their BGP sessions, then restore the original values even on
failure. Require exact-prefix native routes with protocol IS-IS, selected and
installed state, and active FIB next hops in both directions before pinging.
A route merely present in the IS-IS RIB or a ping forwarded by BGP is not a pass.
The BGP coexistence case runs after restoring the baseline advertisements.

For an official-image-only local lab, retain those seven roles, twelve fabric
links, IPv6 interface/Loopback0 addresses and direct BGP peer relationships. The
community SRv6 profiles additionally contain VPN/SRv6 fields that the pinned
official image does not model. Generate a separate IS-IS acceptance configuration
rather than changing the shared profiles or disabling config validation. Use
supported BGP network entries for dedicated Loopback100 prefixes so the BGP
coexistence check has real learned routes without competing for IS-IS Loopback0
forwarding. Document this baseline explicitly; it is not SRv6/VPN acceptance.
Validate every generated configuration with the same full YANG entry point used
by `config reload` before deploying any role.

## Test setup and observations

### Local VS image with incremental packages

When a Linux builder or hardware DUT is unavailable, use an official SONiC VS
image with the same FRR/libyang revisions and install the changed Python wheels
and routing-container templates. Keep the base disk read-only and use a separate
qcow2 overlay for each node. Build utilities inside the guest against its actual
SONiC dependencies. Build a derived BGP image containing both the shared YANG/model
package and frrcfgd, docker_init.sh, gen_frr.conf.j2 and supervisor templates;
recreating the container must retain the changes.

The local reference run uses VS master build `1267969` (`df8f211dd8`), FRR 10.7.1,
libyang 3.12.2, and two QEMU x86-64 guests on an ARM64 Mac using TCG. Each guest
has 6 GiB RAM and four virtual CPUs. Use distinct device MACs, NET system IDs and
loopback addresses. Loopback TCP socket backends connect the two data interfaces;
the attempted macOS UDP multicast backend transmitted frames but delivered none
to the peer, so it was not used for protocol acceptance.

Check native swsscommon as well as legacy redis-py: current ConfigDBConnector
returns a native DBConnector without an eval method. Run the isolated Redis
regression in `src/sonic-yang-models/tests/test_isis_atomic_sdk.py` with
`ISIS_TEST_REDIS_SOCKET` pointing to a dedicated disposable Redis server, never
the DUT's ConfigDB server. Verify list/empty-row round trips and rejection of
concurrent inserts and field changes without partial writes.

Record cold-start failure separately from recovery after explicit retry. In this
TCG environment, service initialization exceeded the 30-second attempt deadline;
`supervisorctl signal HUP frrcfgd` restored convergence after services were ready.
That result does not qualify automatic cold-start timing or hardware forwarding.
The reduced two-node topology supplements, rather than replaces, the seven-node
Force10 and multi-ASIC cases below.

### Pinned FRR multi-area lifecycle regression

With two active same-VRF areas, attempt to disable and delete one through CLI
and GCU. Require rejection before any ConfigDB write or native mutation. Include
a native planner case with a surviving foreign area. Do not use sequential area
deletion as test cleanup: explicitly shut down all active areas atomically, or
discard the disposable guest. An inactive area's removal and retirement of a
VRF's sole active area remain valid. Different VRFs are independent.

Replace disjoint NET lists sharing the same system ID, including three-to-three
replacement. Verify every intermediate native operation retains one to three
NETs. Verify the operational system ID, learned routes and sustained IPv4/IPv6
traffic after reconvergence; immediate ping can succeed using cached routes and
does not establish correctness. A missing system ID in runtime summary must
fail confirmation even when running-config still matches desired configuration.

### CLI setup

Use commands from the [HLD](IS-IS-CLI-Configuration.md). Minimal setup:

```shell
sudo config isis instance add CORE
sudo config isis net add CORE 49.0001.0000.0000.0001.00
sudo config interface isis bind Ethernet0 CORE
sudo config interface isis set Ethernet0 network-type point-to-point
sudo config interface isis af Ethernet0 ipv4 enable
sudo config interface isis af Ethernet0 ipv6 enable
sudo config interface isis enable Ethernet0
sudo config isis instance enable CORE
```

Capture all five `ISIS_*` tables, routed-interface base rows, FRR running config,
`show isis summary`, neighbors, interfaces, IPv4/IPv6 routes, traffic results and
frrcfgd logs before/after each operation. Record recovery journal status from
`/etc/frr/isis-owned.json` in the relevant bgp container. A zero CLI exit status
only proves ConfigDB acceptance. A recovery `applied` status requires matching
native readback; adjacency and forwarding must be checked independently.

## Binding transition matrix

| Case | Action | Required result |
| --- | --- | --- |
| B1: explicit binding | Try enabling an unbound interface; then bind, select AFs and enable | First operation rejects without writes. Explicit setup applies default circuit values without a later metric edit. Both AFs absent defaults to no native circuit. |
| B2: A → B | Configure metric 30, passive, point-to-point and both AFs in VrfA; move routed interface to VrfB | Old native binding is removed. Desired attributes and explicit VrfA reference remain; no automatic VrfB binding. `bind INTERFACE CORE --vrf VrfB` applies retained values to the selected parent. |
| B3: default ↔ VRF | Move default → VrfA → default, explicitly rebinding after each move | Each old binding is removed; neither default nor the sole available instance is guessed. |
| B4: disabled target | Explicitly bind to an existing disabled VrfB instance after a move; enable parent later | No circuit until parent enabled. Parent enable alone restores eligible retained interfaces. Missing parent binding rejects. |
| B5: delete ordering | Remove routed-interface row then unbind; repeat unbind then routed-interface removal | Native binding is removed in either order. Cleanup of a stale binding succeeds; no default binding is recreated. Repeated unbind/delete is harmless. |
| B6: prefix-only events | Add/remove IPv4/IPv6 prefix rows | Base VRF/binding does not change. Native routing reacts to addressing without an invented rebind. |
| B7: independent AFs | Exercise all four combinations and transitions, with passive/metric overrides | Only selected AFs are bound. Removing the last AF removes the circuit; enabling an AF recreates it with retained values. AF reset restores false, not true. |
| B8: parent lifecycle | With no surviving same-VRF sibling, disable then enable parent without replaying interfaces; attempt deletion with active and disabled bindings | Disable retains all desired values and removes native circuits before parent. Enable restores settings. Parent deletion refuses all remaining binding references without partial mutation. |
| B9: partial failure | Inject timeout/nonzero native reply before and after part of a rebind | No false confirmation. Durable pending ownership covers potentially applied objects. Bounded retries use fresh readback, preserving unrelated native configuration. |
| B10: failure then delete | Remove desired binding after B9 partial application | Reconciliation removes owned stale/partial state, does not recreate it and never deletes foreign objects. |
| B11: startup/offline changes | Save/restart bgp; separately stop frrcfgd, change/delete desired rows, restart frrcfgd | Startup/runtime defaults agree. Durable ownership permits cleanup of offline deletions; changed desired state is not mistaken for previously applied state. |
| B12: namespace isolation | Repeat moves, disabled parent and AF transitions on one ASIC | Other ASIC tables, native bindings, neighbors and traffic remain unchanged. |

Repeat B2–B7 for supported routed-interface types. Verify old-VRF advertisements
withdraw and new-VRF routes/traffic appear only after explicit rebind. Log measured
convergence; this plan does not assert unmeasured timing or scale limits.

## Configuration and operational regression cases

| Area | Cases and acceptance criteria |
| --- | --- |
| Identity | Same name in different VRFs and different names in one VRF. Observe correct native area-tag/VRF. Reject inconsistent same-VRF system IDs, including disabled configurations. For a validated bulk system-ID replacement, detach bindings and remove all old areas before recreation; reject unowned area conflicts. |
| NET | Missing NET rejects enable. Up to three unique valid NETs; reject malformed system ID/nonzero NSEL/duplicates. Add/delete NETs while disabled; preserve list values on repeated enable. |
| Interface validation | Alias mode, absent interface, routed prerequisite, wrong explicit VRF, aggregate-member rejection, disabled edits, stale cleanup and orphan-parent cleanup. |
| Per-level values | Set different metrics/hello values in L1/L2; `both` writes both rows atomically. Reset L1 restores its own default and leaves L2 unchanged. Concurrent graph changes reject rather than overwrite. |
| LSP timers | MTU 128–4352, default 1497 and explicit 1492. Refresh 1–65235, lifetime 350–65535, generation 1–120 seconds, with lifetime ≥ refresh + 300 and generation < refresh. Reset validates effective defaults; no partial write if either level is invalid. Native coupled timer command must accept valid transitions. |
| AF and MT | Four AF combinations; IPv6 single-topology and multi-topology peers separately. MT reset restores false. Only wide metric style is exposed. Confirm routes/traffic, not only rendered commands. |
| Overload | Toggle overload and set/reset startup overload timer. Inspect overload flag, transit-path selection, local reachability and expiry. Confirm unrelated instance unaffected. |
| SPF | Per-level minimum interval 1–120 seconds; complete five-value IETF backoff tuple, each 0–60000 ms, hold-down > time-to-learn. Reject partial tuple and invalid relation. Verify native running configuration, scheduler behavior after topology changes and reset; no invented per-level backoff. |
| Redistribution | IPv4 connected/static/kernel/bgp/ospf/rip and IPv6 connected/static/kernel/bgp/ospf6/ripng. Verify source routes, level, metric and existing route-map filtering; delete withdraws selected policy. Reject AF mismatch, missing route-map and unsupported parent level. Withdraw old-level policy before reducing parent level. |
| Show | Summary, neighbor, database/detail, interface, route, topology, hostname and VRF inventory; namespace/VRF/text/JSON. Instance filtering only on supported scoped JSON. Reject lossy multi-area route/topology JSON and lossy all-VRF JSON; hostname is text only. Daemon errors must fail, not masquerade as empty successful state. |
| Bulk model | Run YANG positives/negatives and full validated ConfigDB/GCU candidate operations: compound parent references, NET/system-ID, ranges, timers, SPF tuple, redistribution and deletes. Distinguish valid transient routed-interface removal from an invalid configured parent. Direct unvalidated Redis is not a supported validation API. |
| Packaging | Verify shared Python model, YANG models, startup include, utilities commands and generated completion are packaged together. Confirm legacy unrelated BGP startup paths remain intact. |

## Recovery and coexistence

The Force10 integration test adapts gs1571's offline UPDATE/DELETE and BGP
continuity checks from sonic-mgmt #29119 to named instances. Record the native
results for each restart/reload and failure-injection case independently. The
SRv6 setup is not imported, and its custom-fixture results do not qualify this image.

1. Inject missed notifications, daemon downtime, native socket disconnects,
   partial native application and unresponsive snapshot subprocesses. Each
   attempt remains bounded; pending/applied/failed state is observable.
2. Corrupt/truncate journal or readback and introduce an unowned native area or
   circuit. Fail closed without adopting or deleting unknown ownership.
3. Restart frrcfgd with the same desired state, then with offline update/delete;
   exercise config reload and bgp container restart separately. Observe recovery
   after fault removal and explicit retry, without clearing ownership manually.
4. Keep a BGP session, BGP-learned routes and traffic active during runtime IS-IS
   changes/faults. Native IS-IS sessions and worker must not block BGP callbacks,
   remove BGP configuration or restart the container.
5. Verify startup ownership-registration failure logs an error while rendering
   other protocols from the same frozen snapshot. Do not silently claim IS-IS is
   applied. Measure restart disruption; cold recovery is not warmboot support.

## Cleanup and reporting

Unbind each test interface with `config interface isis unbind INTERFACE`, then
`config isis instance del INSTANCE --vrf VRF`. Delete cascades owned level and
policy rows. Restore addressing/VRFs, saved configuration and any failure
injection. Disable alone is not cleanup. Confirm no test native binding,
adjacency or advertisement remains; preserve unrelated configured objects.

Record image and commit identifiers, namespace, topology, individual case results,
configuration/readback, journal/log evidence and traffic observations. Source
framework/CLI tests and native libyang fixtures have run locally; Linux package,
native FRR lifecycle and DUT cases in this plan are **not run** on this workstation.
Mark missing cases explicitly. Do not infer full acceptance from unit tests.

#### Explicit recovery retry

After correcting a failed recovery condition, use
`sudo docker exec bgp supervisorctl signal HUP frrcfgd` (select the actual ASIC's
bgp container on multi-ASIC systems). SIGHUP requests a new bounded IS-IS attempt;
it does not restart frrcfgd/BGP or discard the ownership journal. If no valid
desired snapshot is available, the retry stays pending until one can be read.
