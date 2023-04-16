import argparse
import os
import sys

import rezifier


def new(args):

    # maps a "--type" command-line argument to default package data.
    default_pkg_map = {
        "empty": rezifier.Rezifier,
        "py": rezifier.PyPackageRezifier,
        "util": rezifier.UtilityRezifier,
    }

    # MAKE PARSER ----------------------------------------------------------- #
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("-d", "--target-dir")
    parser.add_argument(
        "-t", "--type",
        choices=default_pkg_map.keys()
    )
    parser.add_argument("-i", "--initialize", action="store_true")

    # PARSE AND PROCESS ARGS ------------------------------------------------ #
    parsed = parser.parse_args(args)
    name = parsed.name
    target_dir = parsed.target_dir or os.getcwd()
    pkg_type = default_pkg_map[parsed.type]

    # MAKE NEW DEV PACKAGE -------------------------------------------------- #
    rezifier_ = pkg_type(pkg_name=name, pkg_dir=target_dir)
    rezifier_.run()


def convert(args):
    # MAKE PARSER ----------------------------------------------------------- #
    parser = argparse.ArgumentParser()
    parser.add_argument("py_package")
    parser.add_argument("-p", "--parent-dir")
    parser.add_argument("-d", "--target-dir")
    parser.add_argument("-i", "--initialize", action="store_true")

    # PARSE AND PROCESS ARGS ------------------------------------------------ #
    parsed = parser.parse_args(args)
    py_package_name = parsed.py_package
    parent_dir = parsed.parent_dir or os.getcwd()
    py_package_path = os.path.join(parent_dir, py_package_name)
    target_dir = parsed.target_dir or os.path.join(os.getcwd(), "rezified")

    # MAKE DEV PACKAGE ------------------------------------------------------ #
    rezifier_ = rezifier.PyPackageRezifier.from_existing(
        py_package_path, pkg_name=py_package_name, pkg_dir=target_dir
    )
    rezifier_.run()


if __name__ == "__main__":
    # GET SUB-COMMAND ------------------------------------------------------- #
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["convert", "new"])
    parsed = parser.parse_args(sys.argv[1:2])
    command = parsed.command

    # RUN ------------------------------------------------------------------- #
    locals()[command](sys.argv[2:])
