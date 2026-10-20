import argparse
import time
from ipaddress import IPv6Address, IPv6Network
from swsscommon import swsscommon

ROUTE_TABLE_NAME = "ROUTE_TABLE"
appdb = swsscommon.DBConnector("APPL_DB", 0)
pipeline = swsscommon.RedisPipeline(appdb, 50000)
route_table = swsscommon.ProducerStateTable(pipeline, ROUTE_TABLE_NAME, True, True)

def generate_route_fvs(num, nhg_idx, subnet, pic):
    """
    Generate a list of route data to be injected.
    Each entry contains (Key, FieldValuePairs)
    """

    base_network = IPv6Network(subnet)
    routes_to_inject = []

    start_addr = IPv6Address(base_network.network_address) + 1
    for i in range(num):
        ip_addr = start_addr + i
        key = f"{ip_addr}/32"
        pairs = {"blackhole": "false"}
        pairs["nexthop_group"] = f"{nhg_idx}"
        if pic:
            pairs["pic_context_id"] = f"{pic}"
        fvs = swsscommon.FieldValuePairs(list(pairs.items()))
        routes_to_inject.append((key, fvs))
    return routes_to_inject

def inject_routes_appdb(num_routes, nhg_idx, subnet, pic=None):
    _key_fvs_list = generate_route_fvs(num_routes, nhg_idx=nhg_idx, subnet=subnet, pic=pic)

    start_time = time.time()

    for key, fvs in _key_fvs_list:
        route_table.set(key, fvs)
    route_table.flush()

    end_time = time.time()
    duration = end_time - start_time

    print(f"Injecting {num_routes} into appdb takes: {duration:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject routes into APPL_DB for testing.")

    parser.add_argument(
        '--num',
        type=int,
        default=50000,
        help='Number of routes to inject (e.g., 50000).'
    )
    parser.add_argument(
        '--nhg',
        type=int,
        default=1,
        help='Nexthop Group index to use for the routes (e.g., 1).'
    )
    parser.add_argument(
        '--subnet',
        type=str,
        default="2001:db1:1::",
        help='Base subnet for route generation (e.g., 2001:db1:1::).'
    )

    args = parser.parse_args()
    # persisting bad routes with nexthop group not existing
    inject_routes_appdb(
        num_routes=args.num,
        nhg_idx=args.nhg,
        subnet=args.subnet
    )
