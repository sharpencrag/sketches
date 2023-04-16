"""
Tools for working with Rez contexts in developer packages.

These tools are useful when you need the environment that a developer package
will use when released, but the package has not yet been released.

"""

import os
from pathlib import Path
from typing import Union

from rez.packages import get_developer_package
from rez.resolved_context import ResolvedContext
from rez.developer_package import DeveloperPackage

PathLike = Union[str, os.PathLike, Path]


class RequirementsList:
    """Convenience object for working with lists of package requirements."""

    def __init__(self):
        """
        Attributes:
            base (list[str]): Base requirements for the package.
            build (list[str]): All build requirements (including private).
            variants (list[list[str]]): Requirements for all variants.
            tests (dict[str, list[str]]): Requirements for each type of test
                provided in the package.
        """
        self.base = list()
        self.build = list()
        self.variants = list()
        self.tests = dict()

    @property
    def all_variant_indexes(self):
        return list(range(len(self.variants)))

    @classmethod
    def from_package(cls, pkg: DeveloperPackage):

        def _to_str(reqs):
            return [str(req) for req in reqs]

        inst = cls()
        base_requires = getattr(pkg, "requires") or list()
        inst.base = _to_str(base_requires)

        build_requires = list()
        build_requires.extend(getattr(pkg, "build_requires") or list())
        build_requires.extend(getattr(pkg, "private_build_requires") or list())
        inst.build = _to_str(build_requires)

        variant_requires = getattr(pkg, "variants") or list()
        inst.variant = _to_str(variant_requires)

        tests = getattr(pkg, "tests") or dict()
        for test_name in tests:
            requires = tests.get("requires", False)
            if requires:
                inst.tests[test_name] = _to_str(requires)
        return inst

    def to_context(self, base=True, variants=False, variant_indexes=0,
                   build=False, tests=False, test_names=None
                   ) -> ResolvedContext:
        """Construct a context from requirements.

        Args:
            base (bool, optional): Use requirements from the base "requires"
                package. Defaults to True.
            variants (bool, optional): Use requirements from one or more
                package variants. Defaults to False.
            variant_indexes (list[int], optional): A list of indexes associated
                with individual variants. Ignored if "variants" is False.
            build (bool, optional): Use requirements from the "build_requires"
                package attribute. Defaults to False.
            tests (bool, optional): Use requirements from the "tests" package
                attribute. Defaults to False.
            test_names (list[str], optional): Names of the tests to pull
                requirements from. Defaults to None. Ignored if "tests" is
                False.
        """
        all_requirements = list()
        all_requirements += self.base if base else list()
        all_requirements += self.build if build else list()

        if variants:
            for index in variant_indexes:
                all_requirements += self.variants[index]

        if tests:
            for test_name in test_names:
                all_requirements += self.tests[test_name]

        return all_requirements

    @classmethod
    def from_path(cls, path: PathLike):
        package = get_developer_package(path)
        return cls.from_package(package)
