import os
import shutil
import subprocess
import sys

from oci_lock.ui import cyan, red

CRANE_BIN = os.environ.get("CRANE_BIN") or shutil.which("crane") or "crane"


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


def parse_repo(key: str) -> str:
    """Extract repository name without tag or digest."""
    if "@" in key:
        return key.split("@", 1)[0]
    parts = key.rsplit(":", 1)
    if len(parts) == 1 or "/" in parts[1]:
        return key
    return parts[0]


def resolve_digest(image_spec: str) -> tuple[str, str]:
    """
    Given an image spec (e.g. repo:latest or repo), return (pinned_spec, digest).
    pinned_spec will be 'repo@sha256:...'.
    """
    key = normalize_key(image_spec)
    repo = parse_repo(key)
    print(f"Fetching digest for {cyan(key)}...", flush=True)
    digest = run_cmd([CRANE_BIN, "digest", key])
    pinned = f"{repo}@{digest}"
    return pinned, digest
