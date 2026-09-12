#!/usr/bin/env python3
"""
oci-lock: Manage and pin OCI container images to immutable cryptographic hashes in oci.lock.
Similar to flake.lock, maps 'image:latest' to 'image@sha256:<digest>'.
"""

import sys
from pathlib import Path

# Ensure local package directory is on sys.path if running in source tree
_pkg_dir = Path(__file__).parent.resolve()
if (_pkg_dir / "oci_lock").is_dir():
    sys.path.insert(0, str(_pkg_dir))

from oci_lock.cli import main

if __name__ == "__main__":
    main()
