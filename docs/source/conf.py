# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Task dispenser'
copyright = '2024, -'
author = '-'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    'sphinx.ext.autosummary',
    'sphinx.ext.autodoc.typehints',
    # "sphinx_autodoc_typehints",
    "sphinxarg.ext",
    "myst_parser",
    'sphinx.ext.viewcode',
]
autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = ['.*']

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

autodoc_typehints = 'both'

html_favicon = 'favicon_purple.png'
