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
from typing import Any  # pylint: disable=unused-import

import dbus

from qui.models.dbus import ObjectManager, Properties, _DictKey


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
        bus = dbus.SessionBus()  # pylint: disable=no-member
        proxy = bus.get_object('org.qubes.Labels1', '/org/qubes/Labels1',
                               follow_name_owner_changes=True)
        super(LabelsModel, self).__init__(proxy, cls=Label)
        for key, value in self.children.items():
            name = key.split('/')[-1].upper()
            setattr(self, name, value)

    def _setup_signals(self):
        pass


LABELS = LabelsModel()


class Domain(Properties):
    ''' Wrapper around `org.qubes.Domain` Interface '''

    def __init__(self, proxy: dbus.proxies.ProxyObject,  # pylint: disable=no-member
                 data: dbus.Dictionary=None) -> None:  # pylint: disable=no-member
        super().__init__(proxy)

    def __getitem__(self, key: _DictKey):
        value = super().__getitem__(key)
        if value == '':
            return None
        return value

    def __setitem__(self, key: _DictKey, value: Any) -> None:
        pass

    def _setup_signals(self):
        pass


class DomainManager(Properties,ObjectManager):
    ''' Wraper around `org.qubes.DomainManager1` '''
    _metaclass__ = _Singleton

    def __init__(self):
        self.bus = dbus.SessionBus()  # pylint: disable=no-member
        proxy = self.bus.get_object('org.qubes.DomainManager1',
                                    '/org/qubes/DomainManager1',
                                    follow_name_owner_changes=True)
        super().__init__(proxy, cls=Domain)
        self._setup_signals()

    def connect_to_signal(self, signal_name, handler_function):
        ''' Handy wrapper around self.proxy.connect_to_signal'''
        return self.proxy.connect_to_signal(
                signal_name, handler_function,
                dbus_interface='org.qubes.DomainManager1')

    def disconnect_signal(self, signal_matcher):
        ''' Handy wrapper around self.bus.remove_signal_receiver '''
        return self.bus.remove_signal_receiver(signal_matcher)

    def _setup_signals(self):
        pass

