#!/usr/bin/env python3

from setuptools import setup
import sys
import io
import os

# load version variables from manatools/version.py
_version_file = os.path.join(os.path.dirname(__file__), "manatools", "version.py")
with io.open(_version_file, "r", encoding="utf-8") as vf:
    exec(vf.read())

# Read long description if README.md exists
_long_description = ""
_readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(_readme_path):
    with io.open(_readme_path, "r", encoding="utf-8") as rf:
        _long_description = rf.read()

setup(
    name=__project_name__,
    version=__project_version__,
    author='Angelo Naselli',
    author_email='anaselli@linux.it',
    packages=[
        'manatools',
        'manatools.aui',
        'manatools.aui.backends',
        'manatools.aui.backends.qt',
        'manatools.aui.backends.gtk',
        'manatools.aui.backends.curses',
        'manatools.ui'
    ],
    include_package_data=True,
    license='LGPLv2+',
    description='Python ManaTools framework.',
    long_description=_long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "dbus-python",
        "python-gettext",
        "PyYAML",
    ],
)
