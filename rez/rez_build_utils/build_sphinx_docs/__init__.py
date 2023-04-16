"""
Builds sphinx documentation for a project.
"""

import os
import sys
import console_utils
import sphinx.cmd.build

# --------------------------------------------------------------------------- #


def build(source_docs_path, build_path, py_paths=None, target="html"):
    """Builds Sphinx documentation

    Args:
        docs_path (str): Path to a source docs directory
        build_path (str): Path to build documentation into
        py_sources (list[str]): Additional python source locations that are
           needed for generating documentation stubs
        target (str): A valid target for Sphinx's build systems
    """
    prepend_paths = py_paths or list()

    for path in prepend_paths:
        sys.path.insert(0, path)

    docs_build_path = os.path.join(build_path, "sources")
    docs_error_log_path = os.path.join(build_path, "sphinx_build_warnings.txt")

    console_utils.copytree(source_docs_path, docs_build_path)

    sphinx_build_result = sphinx.cmd.build.main(
        argv=["-M", target, docs_build_path, build_path, "-w", docs_error_log_path]
    )

    if sphinx_build_result != 0:
        raise SphinxBuildError()


class SphinxBuildError(Exception):
    """Raised when the sphinx build process encounters an issue"""