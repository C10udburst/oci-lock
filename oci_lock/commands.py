from pathlib import Path
import sys

from oci_lock.crane import check_crane, normalize_key, resolve_digest
from oci_lock.lockfile import load_lockfile, save_lockfile
from oci_lock.ui import bold, cyan, dim, green, red, yellow


def cmd_add(args, lock_path: Path):
    check_crane()
    key = normalize_key(args.name)
    pinned, digest = resolve_digest(key)

    data = load_lockfile(lock_path)
    old_target = data.get(key)

    data[key] = pinned
    save_lockfile(lock_path, data)

    if old_target and old_target != pinned:
        print(
            green(f"Updated {bold(key)}: {dim(old_target)} -> {bold(pinned)} in {lock_path.name}")
        )
    else:
        print(green(f"Added {bold(key)} -> {bold(pinned)} to {lock_path.name}"))


def cmd_remove(args, lock_path: Path):
    if not lock_path.exists():
        sys.exit(
            red(f"Error: '{lock_path.name}' not found in current directory.")
        )

    data = load_lockfile(lock_path)
    if not data:
        sys.exit(yellow(f"'{lock_path.name}' is empty."))

    key = normalize_key(args.name)
    if key in data:
        target_key = key
    else:
        matches = [k for k in data if k == args.name or k == key or k.startswith(f"{args.name}:")]
        if not matches:
            sys.exit(
                red(
                    f"Error: '{args.name}' not found in {lock_path.name}.\nKnown entries:\n"
                    + "\n".join(f"  - {k}" for k in data.keys())
                )
            )
        if len(matches) > 1:
            sys.exit(
                red(
                    f"Error: Multiple entries match '{args.name}':\n"
                    + "\n".join(f"  - {k}" for k in matches)
                    + "\nPlease specify the full tag."
                )
            )
        target_key = matches[0]

    del data[target_key]
    save_lockfile(lock_path, data)
    print(green(f"Removed {bold(target_key)} from {lock_path.name}"))


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
        try:
            new_val, _ = resolve_digest(key)
        except Exception as e:
            print(red(f"Failed to fetch digest for {key}: {e}"), file=sys.stderr)
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
