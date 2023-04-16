import argparse
import os

from rez_dev_context import py_dev_context


def write_py_requires(pkg_root, filename):
    pkg = os.path.join(pkg_root, "package.py")
    pkg = pkg_root
    tmp_file = os.path.join(pkg_root, filename)

    reqs = py_dev_context.RequirementsList.from_path(pkg)

    with open(tmp_file, "w") as file_:
        file_.write(" ".join(reqs.base))


if __name__ == "__main__":

    import sys

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    write_py_parser = subparsers.add_parser("write-py-reqs")
    write_py_parser.add_argument("pkg_root")
    write_py_parser.add_argument("filename")

    args = parser.parse_args(sys.argv[1:])

    # RUN ------------------------------------------------------------------- #

    if args.command == "write-py-reqs":
        write_py_requires(args.pkg_root, args.filename)
