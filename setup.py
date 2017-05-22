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
      entry_points={
          'console_scripts': ['qui-ls = qui.domains_table:main',
          'qui-domains = qui.tray.domains:main',
          'qui-devices = qui.tray.devices:main']
      },
      packages=setuptools.find_packages())
      packages=setuptools.find_packages(),
      )
