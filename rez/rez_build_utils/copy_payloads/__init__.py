"""
Copies payloads from source locations to build locations.
"""

import os

import console_utils

__all__ = ["copy_payloads"]

# --------------------------------------------------------------------------- #

def copy(source_path, build_path, payload_dirs):
    """Copies package payloads to a temporary build location.

    Args:
        source_path (str): path to a source build directory
        build_path (str): path to build to, typically in the source directory
        payload_dirs (list[str]): sub-directories in the source that we want
            to copy into the build_path
    """
    for payload_dir in payload_dirs:
        origin = os.path.join(source_path, payload_dir)
        destination = os.path.join(build_path, payload_dir)
        if not os.path.isdir(origin):
            continue
        console_utils.copytree(origin, destination, label=payload_dir)
