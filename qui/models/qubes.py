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


class LabelsManager(ObjectManager):
    ''' Wraper around `org.qubes.Labels1` '''
    __metaclass__ = _Singleton

    def __init__(self):
        bus = dbus.SessionBus()  # pylint: disable=no-member
        proxy = bus.get_object('org.qubes.Labels1', '/org/qubes/Labels1',
                               follow_name_owner_changes=True)
        super().__init__(proxy, cls=Label)
        for key, value in self.children.items():
            name = key.split('/')[-1].upper()
            setattr(self, name, value)
        self._setup_signals()

    def __getitem__(self, key: dbus.ObjectPath) -> Label:
        return self.children[key]

    def _setup_signals(self):
        pass


class Device(Properties):
    ''' Wrapper around `org.qubes.Device` Interface '''

    def connect_to_signal(self, signal_name, handler_function):
        ''' Handy wrapper around self.proxy.connect_to_signal'''
        return self.proxy.connect_to_signal(
                signal_name, handler_function,
                dbus_interface='org.qubes.Device')

    @property
    def frontend_domain(self):
        try:
            vm_obj_path = self['frontend_domain']
            return DomainManager().children[vm_obj_path]
        except KeyError:
            return None

    @property
    def backend_domain(self):
        vm_obj_path = self['backend_domain']
        return DomainManager().children[vm_obj_path]

    @property
    def name(self):
        name = self.backend_domain['name'] + ":" + self['ident']
        if self["description"] != " ()":
            name += " - " + self["description"]
        return name

    def __getitem__(self, key: _DictKey):
        value = super().__getitem__(key)
        if value == '':
            return None
        return value

    def _setup_signals(self):
        pass


class DevicesManager(ObjectManager):
    ''' Wraper around `org.qubes.Devices1` '''
    __metaclass__ = _Singleton

    def __init__(self):
        self.bus = dbus.SessionBus()  # pylint: disable=no-member
        proxy = self.bus.get_object('org.qubes.Devices1', '/org/qubes/Devices1',
                               follow_name_owner_changes=True)
        super().__init__(proxy, cls=Device)
        self.connect_to_signal("Added", self._add)
        self.connect_to_signal("Removed", self._remove)
        self._setup_signals()

    def _add(self, obj_path: dbus.ObjectPath):
        proxy = self.bus.get_object('org.qubes.Devices1', obj_path)
        self.children[obj_path] = Device(proxy)

    def _remove(self, obj_path: dbus.ObjectPath):
        proxy = self.bus.get_object('org.qubes.Devices1', obj_path)
        del self.children[obj_path]

    def __getitem__(self, key: dbus.ObjectPath) -> Label:
        return self.children[key]

    def _setup_signals(self):
        pass

    def connect_to_signal(self, signal_name, handler_function):
        ''' Handy wrapper around self.proxy.connect_to_signal'''
        return self.proxy.connect_to_signal(
                signal_name, handler_function,
                dbus_interface='org.qubes.Devices1')

    def disconnect_signal(self, signal_matcher):
        ''' Handy wrapper around self.bus.remove_signal_receiver '''
        return self.bus.remove_signal_receiver(signal_matcher)


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

