import json
from pathlib import Path

LOCK_FILENAME = "oci.lock"


def resolve_lock_path(custom_path: str | Path | None = None) -> Path:
    if custom_path:
        return Path(custom_path)
    default_lock = Path.cwd() / LOCK_FILENAME
    if not default_lock.exists():
        log_fallback = Path.cwd() / "oci.log"
        if log_fallback.exists():
            return log_fallback
    return default_lock


def load_lockfile(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            pass

    entries = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        entries[k.strip()] = v.strip()
                    elif ":" in line and not line.startswith("{"):
                        entries[line] = line
    except Exception:
        pass
    return entries


def save_lockfile(path: Path, data: dict[str, str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_data = dict(sorted(data.items()))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, indent=2)
        f.write("\n")
