#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

import sphinx_rtd_theme

# Get the project root dir, which is the parent dir of this
cwd = os.getcwd()
project_root = os.path.dirname(cwd)

# Insert the project root dir as the first element in the PYTHONPATH.
# This lets us ensure that the source package is imported, and that its
# version is used.
sys.path.insert(0, project_root)

import coalaip_bigchaindb


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'pycoalaip-bigchaindb'
copyright = u"2016, BigchainDB"

# The version info for the project you're documenting, acts as replacement
# for |version| and |release|, also used in various other places throughout
# the built documents.
#
# The short X.Y version.
version = coalaip_bigchaindb.__version__
# The full version, including alpha/beta/rc tags.
release = coalaip_bigchaindb.__version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

pygments_style = 'sphinx'
todo_include_todos = True
suppress_warnings = ['image.nonlocal_uri']


html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Output file base name for HTML help builder.
htmlhelp_basename = 'pycoalaip-bigchaindbdoc'

latex_elements = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index', 'pycoalaip-bigchaindb.tex',
     u'pycoalaip-bigchaindb Documentation',
     u'BigchainDB', 'manual'),
]

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pycoalaip-bigchaindb',
     u'pycoalaip-bigchaindb Documentation',
     [u'BigchainDB'], 1)
]

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'pycoalaip-bigchaindb',
     u'pycoalaip-bigchaindb Documentation',
     u'BigchainDB',
     'pycoalaip-bigchaindb',
     'One line description of project.',
     'Miscellaneous'),
]

intersphinx_mapping = {'https://docs.python.org/3': None}
