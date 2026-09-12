import json
from pathlib import Path

LOCK_FILENAME = "oci.lock"


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
