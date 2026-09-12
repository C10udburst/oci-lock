import argparse
from pathlib import Path

from oci_lock.commands import cmd_add, cmd_remove, cmd_update
from oci_lock.lockfile import LOCK_FILENAME


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oci-lock",
        description="Pin and update OCI container images to immutable cryptographic hashes in oci.lock (similar to flake.lock).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    parser_add = subparsers.add_parser("add", help="Add an image to oci.lock pinned to its hash")
    parser_add.add_argument(
        "name",
        help="Image name to add, e.g. 'alpine' or 'busybox:latest'",
    )

    # remove
    parser_remove = subparsers.add_parser(
        "remove",
        aliases=["rm"],
        help="Remove an image from oci.lock",
    )
    parser_remove.add_argument(
        "name",
        help="Image name to remove, e.g. 'alpine' or 'busybox:latest'",
    )

    # update
    parser_update = subparsers.add_parser("update", help="Update image hashes in oci.lock")
    parser_update.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Optional specific image to update, e.g. 'alpine' or 'busybox:latest'",
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    lock_path = Path.cwd() / LOCK_FILENAME

    if args.command == "add":
        cmd_add(args, lock_path)
    elif args.command in ("remove", "rm"):
        cmd_remove(args, lock_path)
    elif args.command == "update":
        cmd_update(args, lock_path)
