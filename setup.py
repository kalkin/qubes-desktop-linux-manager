#!/usr/bin/env python3
''' Setup.py file '''
from distutils.core import setup
import setuptools

setup(name='qubesmanager',
      version='0.1',
      author='Invisible Things Lab',
      author_email='bahtiar@gadimov.de',
      description='Qubes core package',
      license='GPL2+',
      url='https://www.qubes-os.org/',
      package='qubesmanager',
      entry_points={
          'console_scripts': ['domains_table = qubesmanager.domains_table:main',
          'domains_indicators = qubesmanager.domains_indicator:main',
          'device_indicator = qubesmanager.device_indicator:main']
      },
      packages=setuptools.find_packages())
