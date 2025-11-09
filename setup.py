#!/usr/bin/env python3

from setuptools import setup
exec(open('manatools/version.py').read())

try:
  import yui
except ImportError:
  import sys
  print('Please install python3-yui in order to install this package',
        file=sys.stderr)
  sys.exit(1)


setup(
  name=__project_name__,
  version=__project_version__,
  author='Angelo Naselli',
  author_email='anaselli@linux.it',
  packages=['manatools', 'manatools.aui', 'manatools.ui'],
  #scripts=['scripts/'],
  license='LGPLv2+',
  description='Python ManaTools framework.',
  long_description=open('README.md').read(),
  #data_files=[('conf/manatools', ['XXX.yy',]), ],
  install_requires=[
    "dbus-python",
    "python-gettext",
    "PyYAML",
  ],
)
