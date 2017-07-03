#!/usr/bin/env python3
''' Setup.py file '''
from distutils.core import setup
import setuptools

setup(name='qui',
      version='0.1',
      author='Invisible Things Lab',
      author_email='bahtiar@gadimov.de',
      description='Qubes User Interface Package',
      license='GPL2+',
      url='https://www.qubes-os.org/',
      packages=("qui", "qui.tray", "qui.models"),
      entry_points={
          'gui_scripts': [
              'qui-ls = qui.domains_table:main',
              'qui-domains = qui.tray.domains:main',
              'qui-devices = qui.tray.devices:main'
          ]
      })
