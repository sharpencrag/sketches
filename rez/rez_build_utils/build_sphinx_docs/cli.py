"""
Command-line frontend for building Sphinx documentation.

"""

import argparse
import sys
import os

from rez_build_utils import build_sphinx_docs
from rez_build_utils import utils

STANDARD_PY_DIR = "python"
STANDARD_DOCS_DIR = "docs"

PY_SOURCES_ARG_HELP = (
    "Any python source directories that should be accessible while building "
    "documentation.  Path must be relative to the package root directory."
)

DOCS_ROOT_ARG_HELP = (
    "Documentation root directory.  Typically, this is where your index.rst "
    "lives.  Path must be relative to the package root directory."
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--py-sources", nargs="*", default=[STANDARD_PY_DIR], help=PY_SOURCES_ARG_HELP
    )

    parser.add_argument(
        "--docs-root", default=STANDARD_DOCS_DIR, help=DOCS_ROOT_ARG_HELP
    )

    args = parser.parse_args(sys.argv[1:])
    source_path, build_path, *_ = utils.get_build_info()

    docs_root = os.path.join(source_path, args.docs_root)
    build_path = os.path.join(build_path, args.docs_root)
    py_dirs = [os.path.join(source_path, dir_) for dir_ in args.py_sources]

    print("PY_DIRS", py_dirs)

    build_sphinx_docs.build(docs_root, build_path, py_dirs)
