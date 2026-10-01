"""Read-only, deterministic inspection of work-order JSON files."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .work_orders import STATUSES, WorkOrder

SUMMARY_FIELDS = ('id', 'title', 'status', 'assigned_worker', 'updated_at')


def list_work_orders(directory: Path, *, status: str | None = None) -> list[dict]:
    """Load immediate .json files in filename order without saving any data."""
    if status is not None and (not isinstance(status, str) or status not in STATUSES):
        raise ValueError('Invalid work order status')
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f'Not a work-order directory: {directory}')
    result = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.suffix != '.json' or not path.is_file():
            continue
        try:
            order = WorkOrder.load(path)
        except (OSError, ValueError) as exc:
            raise ValueError(f'Cannot read work order {path}: {exc}') from exc
        if status is not None and order.status != status:
            continue
        result.append({name: getattr(order, name) for name in SUMMARY_FIELDS})
    return result


def work_order_summary(directory: Path) -> dict:
    """Count validated directory entries using the existing listing conventions."""
    orders = list_work_orders(directory)
    counts = {status: 0 for status in sorted(STATUSES)}
    for order in orders:
        counts[order['status']] += 1
    return {'total': len(orders), 'by_status': counts}


def work_order_detail(path: Path) -> dict:
    """Return the full validated model without saving or resolving references."""
    try:
        return asdict(WorkOrder.load(path))
    except (OSError, ValueError) as exc:
        raise ValueError(f'Cannot read work order {path}: {exc}') from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description='Inspect work orders as read-only JSON.')
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('directory', nargs='?', type=Path,
                           help='Directory containing work-order .json files (not recursive)')
    selection.add_argument('--summary', type=Path, metavar='DIRECTORY',
                           help='Report total and counts for every work-order status (read-only)')
    selection.add_argument('--detail', type=Path, metavar='PATH',
                           help='Show the full contents of one work-order JSON file')
    parser.add_argument('--status', choices=sorted(STATUSES),
                        help='List only orders with this status (listing only)')
    args = parser.parse_args(argv)
    if args.status is not None and args.detail is not None:
        parser.error('--status cannot be combined with --detail')
    if args.summary is not None and args.status is not None:
        parser.error('--status cannot be combined with --summary')
    try:
        if args.summary is not None:
            result = work_order_summary(args.summary)
        elif args.detail is not None:
            result = work_order_detail(args.detail)
        else:
            result = list_work_orders(args.directory, status=args.status)
    except (OSError, ValueError) as exc:
        print(f'work-box-orders: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
