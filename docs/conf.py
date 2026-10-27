"""Sphinx configuration for the CentrifugalPump documentation.

API reference is generated from the NumPy-style docstrings via autodoc + napoleon;
the hand-written guides are Markdown, rendered through myst-parser. PySide6 is
mocked so the ``pumpflow`` package documents without a Qt install on Read the Docs.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
project = "CentrifugalPump"
author = "Cristofer Antoni Souza Costa"
copyright = "2026, Cristofer Antoni Souza Costa"
release = "0.1.0"
version = "0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "myst_parser",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
# docs/README.md is the human doc hub; index.rst is the Sphinx landing page, so
# keep the hub out of the rendered site to avoid a duplicate, orphaned page.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- autodoc / napoleon ------------------------------------------------------
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
# Qt is a heavy GUI dependency and is not installed on the docs builder.
autodoc_mock_imports = ["PySide6"]

napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_use_rtype = False

always_document_param_types = False

# -- MyST (Markdown) ---------------------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3
# Render the existing ```mermaid fenced blocks via sphinxcontrib-mermaid.
myst_fence_as_directive = ["mermaid"]
# The hand-written guides link to source files with ../.. relative paths; those
# are not docs pages, so don't treat them as cross-reference targets.
suppress_warnings = ["myst.xref_missing"]

# -- intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "furo"
html_title = "CentrifugalPump"
html_static_path = ["_static"]
