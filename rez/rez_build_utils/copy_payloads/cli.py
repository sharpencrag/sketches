
"""
Command-line frontend for basic payload copying from source to build locations.
"""
import argparse
import sys

from rez_build_utils import copy_payloads
from rez_build_utils import utils

# These are the two most common payload paths we'll deal with.  Custom build
# scripts can provide their own, or any package can append a subdirectory to
# the env variable PAYLOAD_DIRS in its pre_build_commands
STANDARD_PAYLOADS = ("python", "bin")

PAYLOADS_ARG_HELP = (
    "Payload directories that you want to copy into the build location. "
    "Directories must be relative to the package root."
)

if __name__ == "__main__":
    # When used as a script, this module will automatically build and install
    # a module according to the parameters of the package and rez

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--payloads", nargs="*", default=STANDARD_PAYLOADS,
        help=("Payload directories that you want to copy into the build location. "
              "Directories must be relative to the package root.")
    )

    args = parser.parse_args(sys.argv[1:])
    payload_dirs = args.payloads

    source_path, build_path, *_ = utils.get_build_info()

    copy_payloads.copy(source_path, build_path, payload_dirs)
