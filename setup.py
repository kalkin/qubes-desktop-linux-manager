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
      packages=setuptools.find_packages())
