"""
Tools for making new Rez recipes (aka source packages, aka developer packages)
"""

from __future__ import annotations
from typing import Callable
from typing import Union

import os
import stat
import enum
import inspect
import uuid
import re
from pathlib import Path

from rez import packages
from rez import developer_package
from rez import package_maker
from rez import serialise
from rez import package_serialise
from rez import resolved_context
from rez.utils import filesystem

from tqdm import tqdm

import isort
import isort.stdlibs.all

import console_utils

# typing
PathLike = Union[str, os.PathLike, Path]

# aliases
PackageMaker = package_maker.PackageMaker
DeveloperPackage = developer_package.DeveloperPackage

__all__ = ["Rezifier", "PyPackageRezifier", "UtilityRezifier", "make_package"]

# ----------------------------------------------------------------- CONSTANTS #

ADD_BIN_CMD = 'env.PATH.append("{root}/bin")'
ADD_PY_CMD = 'env.PYTHONPATH.append("{root}/python")'

#: (str) batch script to pause execution if an error has occurred
BAT_ERR_CHECK = (
    'if NOT ["%errorlevel%"]==["0"] (\n'
    '  pause\n'
    '  exit /b %errorlevel%\n'
    ')\n'
)

#: (str) batch script to delete the temporary build directory
BAT_CLEAN_BUILD = "rd /s /q .\\build\n"


#: (re.Pattern) matches either path/to/tests/ or path/to/test/
TEST_DIR_PATTERN = re.compile(f"\\{os.path.sep}(tests?)\\{os.path.sep}")


# The source code of this function is used to create a base build.py file for
# utility packages.  See UtilityRezifier.make_build_py

#: (callable) a function defining the base source code for a new build.py file
def _buildpy_source():
    """build the {pkg_name} package"""

    import os

    from pkg_payload_utils import payload_mover

    def build(source_path, build_path):
        pass

    if __name__ == "__main__":
        source_path = os.environ["REZ_BUILD_SOURCE_PATH"]

        is_install = int(os.environ["REZ_BUILD_INSTALL"])

        if is_install:
            build_path = os.environ["REZ_BUILD_INSTALL_PATH"]
        else:
            build_path = os.environ["REZ_BUILD_PATH"]

        build(source_path, build_path)


# ------------------------------------------------------------- REZIFICATIONS #

class Rezifier:
    """Utility for building Rez packages from scratch.

    This tool was designed to make rez package recipes, but with some minor
    changes, can be used to generate directly-installed or directly-released
    packages as well (like how rez-pip works).

    This class can be customized through the use of dependency injection.
    """
    def __init__(self, *,
                 pkg_name: str,
                 pkg_dir: PathLike,
                 data: dict=None,
                 git_initialize: bool=False,
                 repo_name: str=None):
        """
        Args:
            pkg_name (str): Name of the package to be created.

            pkg_dir (PathLike): Directory where the package will be created

            data (dict, optional): Dictionary of package attributes. If not
                None, a default package will be generated. Defaults to None.

            git_initialize (bool, optional): True if the new package should be
                initialized as a git repository. Defaults to False.

            repo_name (str, optional): Name of the new git repository. Ignored
                if the `git_initialize` argument is False.
        """
        self.pkg_name = pkg_name
        self.pkg_dir = pkg_dir
        self.pkg_sub_dir = os.path.join(self.pkg_dir, self.pkg_name)
        self.data = data or dict()
        self.git_initialize = git_initialize
        self.repo_name = repo_name

        # This should always be "package.py" unless you have configured Rez
        # to look for a different package name.
        #: (str) the name of the developer package py file.
        self.pkg_file_name = "package.py"

        # These attributes will be populated when the rezifier is run
        self.pkg_maker = None
        self.pkg_path: PathLike = None
        self.pkg_obj: DeveloperPackage = None

    def make_package(self):
        """Makes the package.py for the rez developer package."""

        data = self.get_data()
        data.update(self.data)
        self.pkg_maker = package_maker.PackageMaker(self.pkg_name, data=data)

        self.pkg_path = os.path.join(self.pkg_sub_dir, "package.py")

        make_package(self.pkg_path, self.pkg_maker)

    def get_data(self) -> dict:
        """Returns a dict of package attributes and their values."""
        return {
            "version": "1.0.0",
            "uuid": str(uuid.uuid4())
        }

    def collect_requirements(self):
        """Child classes can use this method to generate a requirements list.

        Returns:
            list[str]: A list of package requirements as strings.
        """
        return False

    def make_payloads(self):
        """Makes the payload files, if any.

        Not implemented by default.
        """
        pass

    def make_accessories(self):
        """Makes accessory files for the package, if any.

        These might include shell scripts or other utilities.
        """
        self.make_standard_bats()

    def make_standard_bats(self):
        """Makes batch scripts for building, installing, and releasing packages.

        Args:
            target_dir (PathLike): The base directory for the package.  This is
                where the bat files will be created.
        """
        self.make_build_bat()
        self.make_install_bat()
        self.make_release_bat()

    def make_build_bat(self):
        """Make a standard bat file for building a Rez package."""
        self.make_bat(
            "rez_build.bat",
            "rez-build\n"
            + BAT_ERR_CHECK
        )

    def make_install_bat(self):
        """Make a standard bat file for installing a Rez package."""
        self.make_bat(
            "rez_install.bat",
            "rez-build --install --clean\n"
            + BAT_ERR_CHECK
            + BAT_CLEAN_BUILD
        )

    def make_release_bat(self):
        """Make a standard bat file for releasing a Rez package."""
        self.make_bat(
            "rez_release.bat",
            "rez-release\n"
            + BAT_ERR_CHECK
            + BAT_CLEAN_BUILD
        )

    def make_bat(self, name: str, contents: str):
        """Make a `.bat` file with the given contents.

        Args:
            name (str): The name of the batch file (including extension).
            contents (str): The contents of the batch file.
        """
        with open(os.path.join(self.pkg_sub_dir, name), "w") as release_bat:
            release_bat.write(contents)

    def initialize(self):
        """A hook for initializing the package as a git repository.

        Not implemented by default.
        """
        pass

    def run(self):
        """Makes package files and payload directories for the new package."""
        self.make_package()
        self.make_payloads()
        self.make_accessories()
        if self.git_initialize:
            self.initialize()


class PyPackageRezifier(Rezifier):
    """Rezifier object for packages containing Python modules."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source: PathLike = None
        self.test_dir = None

    def get_data(self):
        """Package attributes for python packages.

        Returns:
            dict: A data dictionary suitable for use in a `PackageMaker` object.
                The keys on this dict are directly translatable to rez package
                attributes.
        """
        data = super().get_data()
        data.update({
            "commands": ADD_PY_CMD,
            "requires": ["python"],
            "private_build_requires": ["rez_payload_utils", "console_utils"],
            "build_command": "copy_payloads",
            "release_type": "rt",
        })

        requires, test_requires, test_dirs = self.collect_requirements()
        if not test_dirs:
            return data

        tests_path = os.path.join("{root}", "python", self.pkg_name)
        test_cmd = f'python -m unittest discover -s {tests_path} -p"test_*.py"'
        data.update({
            "tests": {
                "unit": {
                    "command": test_cmd,
                    "run_on": ["default", "pre_release"],
                    "requires": ["python"] + test_requires,
                }
            }
        })
        data["requires"] += requires
        return data

    def _valid_requirement(self, require_name: str) -> bool:
        """Returns True if the given requirement is valid."""
        return (
            not require_name.startswith("_")
            and require_name not in isort.stdlibs.all.stdlib
            and require_name != self.pkg_name
        )

    def collect_requirements(self) -> tuple[list[str]]:
        """Collects the requirements for test and non-test modules.

        Returns:
            tuple[list[str]]: 3-tuple in the form of
                (reqs for tests, reqs for non-tests, test directories)
        """
        if not self.source:
            return (None, None, None)

        py_files, test_files, test_dirs = self.collect_python_files()

        non_test_requirements = self.collect_imports(
            py_files,
            validator=self._valid_requirement
        )

        test_requirements = self.collect_imports(
            test_files,
            validator=self._valid_requirement
        )
        return non_test_requirements, test_requirements, test_dirs

    def collect_python_files(self) -> list[str]:
        """Collects all python source files recursively in the directory.

        Returns:
            list[str]: Full paths to each non-test python file in the directory
            and all descendant directories.
        """
        py_files = []
        test_files = []
        test_dirs = []
        valid_test_names = ("test", "tests")
        for root, dirs, files in os.walk(self.source):
            full_files = [os.path.join(root, f) for f in files if f.endswith(".py")]
            if os.path.split(root)[1] in valid_test_names:
                test_files.extend(full_files)
            else:
                py_files.extend(full_files)
            test_dirs.extend(
                [os.path.join(root, dir_) for dir_ in dirs if dir_ in valid_test_names]
            )
        return py_files, test_files, test_dirs

    @staticmethod
    def collect_imports(py_files: list[str],
                        validator: Callable=None) -> list[str]:
        """Parses a set of python files for package-level imports.

        These imports are filtered to only include modules that aren't in the
        standard library. This should yield a list of python modules that
        might (or might not) be rez dependencies as well.

        Note that this list is often meant to be a starting place when
        building a new package. Some dependencies will not be appropriate to
        build into rez, and others may be artifacts of a python package's
        import mechanisms. Caveat emptor.

        Args:
            py_files (list[str]): A list of paths to python source files (not pyc).
            validator (Callable): Function that takes a str and returns a boolean.

        Returns:
            list[str]: A list of all detected dependencies.
        """
        requires = set()
        for py_file in tqdm(py_files, "Parsing Dependencies"):
            imports = isort.api.find_imports_in_file(py_file)
            dependencies = set()
            for import_ in imports:
                mod_name = import_.module.split(".")[0]
                if mod_name and validator and validator(mod_name):
                    dependencies.add(mod_name)
                elif mod_name and not validator:
                    dependencies.add(mod_name)
            requires = set.union(requires, dependencies)
        return list(requires)

    def make_payloads(self):
        """Copy the payload from the original source into the package."""
        payload_path = os.path.join(self.pkg_sub_dir, "python", self.pkg_name)
        os.makedirs(payload_path, exist_ok=True)
        if self.source is not None:
            console_utils.copytree(self.source, payload_path)
        else:
            init_path = os.path.join(payload_path, "__init__.py")
            with open(init_path, "w"):
                pass

    @classmethod
    def from_existing(cls, source: PathLike, *args, **kwargs) -> PyPackageRezifier:
        """Alternate Constructor: Make a new package from an existing py module

        Args:
            source (PathLike): The python package directory

        Returns:
            PyPackageRezifier: An instance of this class
        """
        instance = cls(*args, **kwargs)
        instance.source = source
        return instance


class UtilityRezifier(Rezifier):
    """Rezifier for utility packages (such as standalone tools)"""

    def make_payloads(self):
        """Makes a "bin" payload path"""
        payload_path = os.path.join(self.pkg_sub_dir, "bin")
        os.makedirs(payload_path, exist_ok=True)

    def get_data(self) -> dict:
        """Package attributes for utility packages.

        Returns:
            dict: A data dictionary suitable for use in a `PackageMaker` object.
                The keys on this dict are directly translatable to rez package
                attributes.
        """
        data = super().get_data()
        data.update({
            "commands": ADD_BIN_CMD,
            "variants": self._get_implicit_variant(),
            "release_type": "vendor",
            "private_build_requires": ["pkg_payload_utils", "console_utils"],
            "build_command": "python {root}/build.py"
        })
        return data

    def make_accessories(self):
        super().make_accessories()
        self.make_build_py()

    def make_build_py(self):
        """Makes a generic starting build.py file for a custom utility package.

        This function will typically be used as an "accessory maker" callback
        when using a Rezifier object.
        """
        build_py_path = os.path.join(self.pkg_sub_dir, "build.py")
        py_str = inspect.getsource(_buildpy_source)
        py_lines = py_str.split("\n")[1:]

        # strip the indent from the source code
        revised_py_str = "\n".join(
            [line[4:] for line in py_lines]
        )

        # add pkg-specific values
        revised_py_str = revised_py_str.format(pkg_name=self.pkg_name)

        with open(build_py_path, mode="w") as py_build_file:
            py_build_file.write(revised_py_str)

    @staticmethod
    def _get_implicit_variant():
        empty_ctx = resolved_context.ResolvedContext(
            package_requests=["arch", "platform"]
        )
        platform = empty_ctx.get_resolved_package("platform")
        arch = empty_ctx.get_resolved_package("arch")
        return [[platform.qualified_package_name, arch.qualified_package_name]]


def make_package(pkg_path: PathLike, pkg: PackageMaker) -> str:
    """Makes a new package file with the given data.

    Args:
        pkg_path (PathLike): Path to the new package file, including filename
            and extension.
        pkg (PackageMaker): An object that can be used to store and verify
            the new package's data.

    Returns:
        str: The path to the new package file
    """
    package_file_mode = (
        None if os.name == "nt" else
        # These aren't supported on Windows
        # https://docs.python.org/2/library/os.html#os.chmod
        (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    )
    package_obj = pkg.get_package()
    package_obj.validate_data()
    package_data = package_obj.data
    package_format = serialise.FileFormat.py
    base_path = os.path.dirname(pkg_path)
    os.makedirs(base_path, exist_ok=True)

    with filesystem.make_path_writable(base_path):
        open_pkg = serialise.open_file_for_write(
            pkg_path, mode=package_file_mode
        )
        with open_pkg as package_file:
            package_serialise.dump_package_data(
                package_data, buf=package_file, format_=package_format
            )
