"""
General-purpose utilities for different Rez build operations.
"""

import os
from collections import namedtuple

BuildInfo = namedtuple("BuildInfo", ["source_dir", "build_dir", "is_install", "is_release"])


def get_build_info():
    """Returns information about the current build.

    This is purely a matter of convenience to avoid having to dig up rez env
    variables every time you need to use them.

    Returns:
        BuildInfo: namedtuple with information about source and build paths, as
            well as whether the current build is an install or a release.
    """
    source_path = os.environ["REZ_BUILD_SOURCE_PATH"]

    is_install = int(os.environ["REZ_BUILD_INSTALL"])
    if is_install:
        build_path = os.environ["REZ_BUILD_INSTALL_PATH"]
    else:
        build_path = os.environ["REZ_BUILD_PATH"]

    release_type = os.environ["REZ_BUILD_TYPE"]

    if release_type == "central":
        is_release = True
    else:
        is_release = False

    return BuildInfo(source_path, build_path, is_install, is_release)