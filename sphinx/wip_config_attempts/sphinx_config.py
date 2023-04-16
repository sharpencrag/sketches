"""
Configuration file for the Sphinx documentation builder.

More information
----------------
https://www.sphinx-doc.org/en/master/usage/configuration.html

Usage
-----
This module defines base values for tools we want to document with Sphinx.
In order to do so, the sphinx `conf.py` for your module-under-documentation
should use a star-import to bring the values defined here into the module
namespace.

Example:
    in conf.py for a module we wish to document::
        from sphinx_config import *
        author = "Dev McCoder"
        exclude_patterns.append("test_")

"""

import os
import sys

# -- Third-Party Extensions --------------------------------------------------
import sphinx_rtd_theme


# -- Project information -----------------------------------------------------
project = "Project Name"
copyright = "Organization Name"
author = "Author Name"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.coverage",
    "sphinx.ext.githubpages",
    "sphinx.ext.ifconfig",
    "sphinx.ext.imgconverter",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.imgmath",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme"
]


# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# autosummary settings
autosummary_generate = True

# Mock out non-importable modules.
autodoc_mock_imports = []

# autodoc_default_options: {
#     'special-members': '__init__'
# }

autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates", os.environ["SPHINX_BASE_TEMPLATE_PATH"]]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static", os.environ["SPHINX_BASE_STATIC_PATH"]]

# Style type for any code snippets
pygments_style = "tango"
