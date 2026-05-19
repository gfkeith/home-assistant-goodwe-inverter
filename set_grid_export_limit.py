"""
Set the grid export limit on a GoodWe inverter over TCP.

Usage:
    python set_grid_export_limit.py <host> <limit_watts> [--dry-run]

Arguments:
    host          Inverter IP address or hostname
    limit_watts   New grid export limit in watts (0 = no export)
    --dry-run     Read and print the current limit without writing

Example:
    python set_grid_export_limit.py 192.168.1.100 3000
    python set_grid_export_limit.py 192.168.1.100 0 --dry-run
"""

import argparse
import asyncio
import sys

import goodwe
from goodwe.const import GOODWE_TCP_PORT
from goodwe.exceptions import InverterError


TIMEOUT = 2
RETRIES = 5


async def run(host: str, limit_watts: int, dry_run: bool) -> None:
    print(f"Connecting to inverter at {host}:{GOODWE_TCP_PORT} (TCP)...")
    try:
        inverter = await goodwe.connect(
            host=host,
            port=GOODWE_TCP_PORT,
            timeout=TIMEOUT,
            retries=RETRIES,
        )
    except InverterError as exc:
        print(f"ERROR: Could not connect to inverter: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Connected: {inverter.model_name}  "
        f"S/N: {inverter.serial_number}  "
        f"Firmware: {inverter.firmware}"
    )

    # Read current values before making any change.
    try:
        current_enabled = await inverter.read_setting("grid_export")
        current_limit = await inverter.get_grid_export_limit()
    except InverterError as exc:
        print(f"ERROR: Could not read current grid export settings: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nCurrent grid export limit settings:"
        f"\n  grid_export (enabled): {current_enabled}"
        f"\n  grid_export_limit:     {current_limit} W"
    )

    if dry_run:
        print("\n--dry-run specified, no changes written.")
        return

    print(f"\nWriting grid_export_limit = {limit_watts} W ...")
    try:
        await inverter.set_grid_export_limit(limit_watts)
    except InverterError as exc:
        print(f"ERROR: Write failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Read back to confirm.
    try:
        confirmed = await inverter.get_grid_export_limit()
    except InverterError as exc:
        print(f"WARNING: Write sent but could not read back to confirm: {exc}", file=sys.stderr)
        return

    if confirmed == limit_watts:
        print(f"Confirmed: grid_export_limit is now {confirmed} W")
    else:
        print(
            f"WARNING: Read-back value ({confirmed} W) does not match "
            f"requested value ({limit_watts} W). Check inverter.",
            file=sys.stderr,
        )
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set the grid export limit on a GoodWe inverter over TCP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("host", help="Inverter IP address or hostname")
    parser.add_argument(
        "limit_watts",
        nargs="?",
        type=int,
        default=None,
        help="New export limit in watts (omit with --dry-run to just read the current value)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and print the current limit without writing",
    )
    args = parser.parse_args()

    if not args.dry_run and args.limit_watts is None:
        parser.error("limit_watts is required unless --dry-run is specified")
    if args.limit_watts is not None and args.limit_watts < 0:
        parser.error("limit_watts must be >= 0")

    return args


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = parse_args()
    asyncio.run(run(args.host, args.limit_watts, args.dry_run))
