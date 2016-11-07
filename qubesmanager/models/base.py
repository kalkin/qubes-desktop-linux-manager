#!/usr/bin/env python3
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2016 Bahtiar `kalkin-` Gadimov <bahtiar@gadimov.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
''' Base model api '''

import abc

import dbus

from typing import Dict, List

# pylint: disable=too-few-public-methods


class NamedMixin():
    ''' Sets the `name` property of a class '''

    def __init__(self, name: str, *args, **kwargs):
        super(NamedMixin, self).__init__(*args, **kwargs)
        self.name = name


class Method(NamedMixin, list):
    ''' Encapsulates a method and it's arguments '''

    def __init__(self, name: str, *args: str) -> None:
        super(Method, self).__init__(name=name)
        self.extend(args)


class Signal(NamedMixin, dict):
    ''' Encapsulates a Signals and it's key/value arguments '''

    def __init__(self, name: str, **kwargs) -> None:
        super(Signal, self).__init__(name=name)
        self.update(kwargs)


class Interface(object):
    ''' Contains information about signals and methods '''

    def __init__(self, name: str, methods: List[Signal],
                 signals: List[Method]) -> None:
        super(Interface, self).__init__()
        self.name = name
        self.methods = methods
        self.signals = signals


class Model(metaclass=abc.ABCMeta):
    ''' A gathering of signals and events for multiple interfaces.  '''

    def __init__(self, interfaces: List[Interface]) -> None:
        self.interfaces = interfaces
        self._setup_methods()
        self._setup_signals()

    @abc.abstractmethod
    def _setup_methods(self) -> Dict[str, Interface]:
        ''' Add methods wrappers to the `Model` '''
        return

    @abc.abstractmethod
    def _setup_signals(self) -> Dict[str, Interface]:
        ''' Add signals wrappers to the `Model` '''
        return
