import argparse
from pathlib import Path
import sys

from oci_lock.commands import cmd_add, cmd_completion, cmd_remove, cmd_update
from oci_lock.completion import handle_completion, lockfile_completer
from oci_lock.lockfile import LOCK_FILENAME, resolve_lock_path

try:
    import argcomplete
except ImportError:
    argcomplete = None


def create_parser() -> argparse.ArgumentParser:
    file_parent = argparse.ArgumentParser(add_help=False)
    file_parent.add_argument(
        "-f",
        "--file",
        "--lockfile",
        "-l",
        dest="lockfile",
        default=argparse.SUPPRESS,
        help="Path to lockfile (default: oci.lock)",
    )

    parser = argparse.ArgumentParser(
        prog="oci-lock",
        description="Pin and update OCI container images to immutable cryptographic hashes in oci.lock (similar to flake.lock).",
        parents=[file_parent],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    parser_add = subparsers.add_parser(
        "add",
        parents=[file_parent],
        help="Add an image to oci.lock pinned to its hash",
    )
    parser_add.add_argument(
        "name",
        help="Image name to add, e.g. 'alpine' or 'busybox:latest'",
    )

    # remove
    parser_remove = subparsers.add_parser(
        "remove",
        aliases=["rm"],
        parents=[file_parent],
        help="Remove an image from oci.lock",
    )
    rm_arg = parser_remove.add_argument(
        "name",
        help="Image name to remove, e.g. 'alpine' or 'busybox:latest'",
    )
    setattr(rm_arg, "completer", lockfile_completer)

    # update
    parser_update = subparsers.add_parser(
        "update",
        parents=[file_parent],
        help="Update image hashes in oci.lock",
    )
    up_arg = parser_update.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Optional specific image to update, e.g. 'alpine' or 'busybox:latest'",
    )
    setattr(up_arg, "completer", lockfile_completer)

    # completion
    parser_completion = subparsers.add_parser(
        "completion",
        help="Generate shell tab completion script",
    )
    parser_completion.add_argument(
        "shell",
        nargs="?",
        choices=["bash", "zsh", "fish"],
        default=None,
        help="Target shell (bash, zsh, fish). Auto-detects if omitted.",
    )

    return parser


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "_complete":
        handle_completion(sys.argv[2:])

    parser = create_parser()
    if argcomplete:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command == "completion":
        cmd_completion(args)
        return

    lock_path = resolve_lock_path(getattr(args, "lockfile", None))

    if args.command == "add":
        cmd_add(args, lock_path)
    elif args.command in ("remove", "rm"):
        cmd_remove(args, lock_path)
    elif args.command == "update":
        cmd_update(args, lock_path)
