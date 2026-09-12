#!/usr/bin/env python3
"""
oci-lock: Manage and pin OCI container images in oci.lock.
Similar to flake.lock, maps 'image:latest' to 'image:<actual tag>'.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LOCK_FILENAME = "oci.lock"
CRANE_BIN = os.environ.get("CRANE_BIN") or shutil.which("crane") or "crane"

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def col(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def green(text: str) -> str:
    return col(text, "32")


def yellow(text: str) -> str:
    return col(text, "33")


def cyan(text: str) -> str:
    return col(text, "36")


def bold(text: str) -> str:
    return col(text, "1")


def dim(text: str) -> str:
    return col(text, "2")


def red(text: str) -> str:
    return col(text, "31")


def check_crane():
    if not shutil.which(CRANE_BIN):
        sys.exit(
            red(f"Error: '{CRANE_BIN}' executable not found in PATH. Please install crane.")
        )


def run_cmd(cmd: list[str]) -> str:
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() or str(e)
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {err}") from e


def normalize_key(spec: str) -> str:
    """Normalize image specifier so that if no tag is provided, :latest is appended."""
    parts = spec.rsplit(":", 1)
    if len(parts) == 1 or "/" in parts[1]:
        return f"{spec}:latest"
    return spec


def parse_image_spec(spec: str) -> tuple[str, str]:
    """Extract (repo, tag) from an image specifier."""
    parts = spec.rsplit(":", 1)
    if len(parts) == 1 or "/" in parts[1]:
        return spec, "latest"
    return parts[0], parts[1]


def parse_version(tag: str):
    """
    Parse a tag into a sortable tuple.
    Returns: (major, minor, patch, -is_prerelease, num_components, has_v) or None.
    """
    clean = tag.lstrip("v")
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[.-]?([a-zA-Z0-9.-]+))?$", clean)
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) is not None else 0
    patch = int(m.group(3)) if m.group(3) is not None else 0
    prerelease = m.group(4) or ""
    is_prerelease = 1 if prerelease else 0
    num_components = sum(
        1 for g in [m.group(1), m.group(2), m.group(3)] if g is not None
    )
    has_v = 1 if tag.startswith("v") else 0
    return (major, minor, patch, -is_prerelease, num_components, has_v)


def resolve_actual_tag(repo: str, target_tag: str = "latest") -> str:
    """Find the actual version tag matching target_tag's digest."""
    full_target = f"{repo}:{target_tag}"
    print(f"Resolving tag for {cyan(full_target)}...", flush=True)

    try:
        target_digest = run_cmd([CRANE_BIN, "digest", full_target])
    except Exception as e:
        raise RuntimeError(f"Failed to fetch digest for {full_target}: {e}") from e

    try:
        raw_tags = run_cmd([CRANE_BIN, "ls", repo]).splitlines()
    except Exception as e:
        raise RuntimeError(f"Failed to list tags for {repo}: {e}") from e

    candidates = []
    for t in raw_tags:
        t = t.strip()
        if not t or t == target_tag:
            continue
        # Skip git sha tags, PR tags, and non-version tags
        if (
            t.startswith("sha-")
            or t.startswith("pr-")
            or t.startswith("sha256-")
            or re.match(r"^[0-9a-f]{32,64}$", t)
        ):
            continue
        v = parse_version(t)
        if v is not None and v[3] == 0:  # Non-prereleases
            candidates.append((v, t))

    # Sort with highest version first
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Check top candidates for matching digest
    for _, t in candidates[:25]:
        try:
            d = run_cmd([CRANE_BIN, "digest", f"{repo}:{t}"])
            if d == target_digest:
                return f"{repo}:{t}"
        except Exception:
            continue

    # If no exact digest match was found among stable releases, check top candidate or fallback
    if candidates:
        top_tag = candidates[0][1]
        print(
            yellow(
                f"  Warning: No release tag directly matching digest of {full_target}. Using highest semver tag '{top_tag}'."
            ),
            file=sys.stderr,
        )
        return f"{repo}:{top_tag}"

    print(
        yellow(f"  Warning: No semver tag found for {repo}. Keeping '{target_tag}'."),
        file=sys.stderr,
    )
    return full_target


def load_lockfile(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_lockfile(path: Path, data: dict[str, str]):
    sorted_data = dict(sorted(data.items()))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, indent=2)
        f.write("\n")


def cmd_add(args, lock_path: Path):
    check_crane()
    key = normalize_key(args.name)
    repo, tag = parse_image_spec(key)

    actual_target = resolve_actual_tag(repo, tag)
    data = load_lockfile(lock_path)
    old_target = data.get(key)

    data[key] = actual_target
    save_lockfile(lock_path, data)

    if old_target and old_target != actual_target:
        print(
            green(f"Updated {bold(key)}: {dim(old_target)} -> {bold(actual_target)} in {lock_path.name}")
        )
    else:
        print(green(f"Added {bold(key)} -> {bold(actual_target)} to {lock_path.name}"))


def cmd_update(args, lock_path: Path):
    check_crane()
    if not lock_path.exists():
        sys.exit(
            red(f"Error: '{lock_path.name}' not found in current directory. Use 'oci-lock add <image>' first.")
        )

    data = load_lockfile(lock_path)
    if not data:
        sys.exit(yellow(f"'{lock_path.name}' is empty."))

    target_keys = []
    if args.image:
        normalized = normalize_key(args.image)
        if normalized not in data:
            matches = [k for k in data if k == normalized or k.startswith(f"{args.image}:")]
            if not matches:
                sys.exit(
                    red(
                        f"Error: '{args.image}' not found in {lock_path.name}.\nKnown entries:\n"
                        + "\n".join(f"  - {k}" for k in data.keys())
                    )
                )
            target_keys.extend(matches)
        else:
            target_keys.append(normalized)
    else:
        target_keys = list(data.keys())

    updated: list[tuple[str, str, str]] = []
    unchanged: list[tuple[str, str]] = []

    for key in target_keys:
        old_val = data[key]
        repo, tag = parse_image_spec(key)
        try:
            new_val = resolve_actual_tag(repo, tag)
        except Exception as e:
            print(red(f"Failed to update {key}: {e}"), file=sys.stderr)
            unchanged.append((key, old_val))
            continue

        if new_val != old_val:
            data[key] = new_val
            updated.append((key, old_val, new_val))
        else:
            unchanged.append((key, old_val))

    save_lockfile(lock_path, data)

    print("\n" + bold("Summary of OCI image locks:"))
    print(bold("─────────────────────────────"))
    if updated:
        print(green(bold(f"Updated ({len(updated)}):")))
        for key, old_v, new_v in updated:
            print(f"  • {bold(key)}")
            print(f"    {dim(old_v)} -> {green(bold(new_v))}")
    else:
        print(dim("Updated: (none)"))

    if unchanged:
        print("\n" + cyan(bold(f"Unchanged ({len(unchanged)}):")))
        for key, val in unchanged:
            print(f"  • {key}: {dim(val)}")
    else:
        print(dim("Unchanged: (none)"))


def main():
    parser = argparse.ArgumentParser(
        description="Pin and update OCI container image versions in oci.lock (similar to flake.lock)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    parser_add = subparsers.add_parser("add", help="Add an image to oci.lock")
    parser_add.add_argument(
        "name",
        help="Image name to add, e.g. 'ghcr.io/homarr-labs/homarr' or 'ghcr.io/homarr-labs/homarr:latest'",
    )

    # update
    parser_update = subparsers.add_parser("update", help="Update image tags in oci.lock")
    parser_update.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Optional specific image to update, e.g. 'b3log/siyuan' or 'b3log/siyuan:latest'",
    )

    args = parser.parse_args()
    lock_path = Path.cwd() / LOCK_FILENAME

    if args.command == "add":
        cmd_add(args, lock_path)
    elif args.command == "update":
        cmd_update(args, lock_path)


if __name__ == "__main__":
    main()
