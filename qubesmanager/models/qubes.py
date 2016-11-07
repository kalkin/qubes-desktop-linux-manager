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
''' Data Models '''
import dbus

from qubesmanager.models.dbus import ObjectManager, Properties, _DictKey
from typing import Any  # pylint: disable=unused-import

# pylint: disable=too-few-public-methods,too-many-ancestors


class Label(Properties):
    ''' Wrapper around `org.qubes.Label` Interface '''

    def _setup_signals(self):
        pass


class _Singleton(type):
    ''' A singleton metaclass '''
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args,
                                                                  **kwargs)
        return cls._instances[cls]


class LabelsModel(ObjectManager):
    ''' Wraper around `org.qubes.Labels1` '''
    __metaclass__ = _Singleton

    def __init__(self):
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.qubes.Labels1', '/org/qubes/Labels1')
        super(LabelsModel, self).__init__(proxy, cls=Label)
        for key, value in self.children.items():
            name = key.split('/')[-1].upper()
            setattr(self, name, value)

    def _setup_signals(self):
        pass


LABELS = LabelsModel()


class DomainModel(Properties):
    ''' Wrapper around `org.qubes.Domain` Interface '''

    def __init__(self, proxy: dbus.proxies.ProxyObject,
                 data: dbus.Dictionary=None) -> None:
        super(DomainModel, self).__init__(proxy)

    def __getitem__(self, key: _DictKey):
        value = super(DomainModel, self).__getitem__(key)
        if value == '':
            return None
        if isinstance(value, dbus.ObjectPath):
            if value.startswith('/org/qubes/Labels1/labels/'):
                value = LABELS.children[value]
            elif value.startswith('/org/qubes/DomainManager1/domains/'):
                value = DOMAINS.children[value]
        return value

    def __setitem__(self, key: _DictKey, value: Any) -> None:
        pass

    def _setup_signals(self):
        pass


class DomainManagerModel(Properties, ObjectManager):
    ''' Wraper around `org.qubes.DomainManager1` '''
    _metaclass__ = _Singleton

    def __init__(self):
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.qubes.DomainManager1',
                               '/org/qubes/DomainManager1')
        super(DomainManagerModel, self).__init__(proxy=proxy, cls=DomainModel)

    def _setup_signals(self):
        pass


DOMAINS = DomainManagerModel()
