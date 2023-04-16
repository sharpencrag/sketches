"""
Command-line interface for common build operations in Rez
"""
import argparse
import sys
import os

from rez_build_utils import build_sphinx_docs
import rez_build_utils.build_sphinx_docs.cli as docs_cli
from rez_build_utils import copy_payloads
import rez_build_utils.copy_payloads.cli as payload_cli
from rez_build_utils import utils


if __name__ == "__main__":

    source_path, build_path, *_ = utils.get_build_info()

    parser = argparse.ArgumentParser(description="Build Operations for Rez Packages")

    parser.add_argument("--copy-payloads", action="store_true")
    parser.add_argument(
        "--payloads", nargs="*", help=payload_cli.PAYLOADS_ARG_HELP,
        default=payload_cli.STANDARD_PAYLOADS
    )

    parser.add_argument("--make-docs", action="store_true")
    parser.add_argument(
        "--docs-root", help=docs_cli.DOCS_ROOT_ARG_HELP,
        default=docs_cli.STANDARD_DOCS_DIR
    )

    parser.add_argument(
        "--docs-py-sources", nargs="*", help=docs_cli.PY_SOURCES_ARG_HELP,
        default=[docs_cli.STANDARD_PY_DIR]
    )

    parser.add_argument(
        "--skip-docs", action="store_true",
        help=("Skip generating docs, even if --make_docs is provided. This is "
             "useful when building for another purpose such as running tests.")
    )

    args = parser.parse_args(sys.argv[1:])
    do_copy_payloads = args.copy_payloads
    do_make_docs = args.make_docs and not args.skip_docs

    if do_copy_payloads:
        copy_payloads.copy(source_path, build_path, args.payloads)

    if do_make_docs:
        docs_root = os.path.join(source_path, args.docs_root)
        build_path = os.path.join(build_path, args.docs_root)
        py_dirs = [os.path.join(source_path, dir_) for dir_ in args.docs_py_sources]
        build_sphinx_docs.build(docs_root, build_path, py_dirs)
