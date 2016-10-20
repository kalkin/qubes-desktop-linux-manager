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


import collections
import functools
import xml.dom.minidom

import dbus
from dbus.mainloop.glib import DBusGMainLoop

from typing import Callable, Dict, Union, Any

DBusGMainLoop(set_as_default=True)

ObjectPath = Union[dbus.ObjectPath, str]  # pylint: disable=invalid-name

OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
PROPERTIES_CHANGED = 'PropertiesChanged'


class InterfaceWrapper(object):
    ''' Represents a D-Bus Interface '''

    # pylint: disable=too-few-public-methods
    def __init__(self, node: xml.dom.minidom.Element) -> None:
        super(InterfaceWrapper, self).__init__()
        self.name = _name(node)
        self.signals = {
            _attr(signal_node, 'name'): Signal(signal_node)
            for signal_node in _children(node, 'signal')
        }
        self.methods = {
            _attr(method_node, 'name'): Method(method_node)
            for method_node in _children(node, 'method')
        }


class Method(list):
    ''' Represents a D-Bus Method '''

    # pylint: disable=too-few-public-methods
    def __init__(self, method: xml.dom.minidom.Element, *args,
                 **kwargs) -> None:
        super(Method, self).__init__(*args, **kwargs)
        self.name = _name(method)
        for arg in _children(method, 'arg'):
            if _attr(arg, 'direction') == 'in':
                self.append(_attr(arg, 'type'))


class Signal(dict):
    ''' Represents a D-Bus Signal '''

    # pylint: disable=too-few-public-methods
    def __init__(self, signal: xml.dom.minidom.Element, *args,
                 **kwargs) -> None:
        super(Signal, self).__init__(*args, **kwargs)
        self.name = _name(signal)
        for arg in _children(signal, 'arg'):
            key = _name(arg)
            self[key] = _attr(arg, 'type')


class Model():
    ''' Wrapper around the `dbus.proxies.ProxyObject`.  '''

    # pylint: disable=too-few-public-methods

    def __init__(self, proxy: dbus.proxies.ProxyObject) -> None:
        super(Model, self).__init__()
        self.proxy = proxy
        self.interfaces = self._init_interfaces()
        for iface_name, iface in self.interfaces.items():
            for method in iface.methods.keys():
                func = self._wrap_dbus_method(iface_name, method)
                partial_function = functools.partial(func, proxy)
                setattr(self, method, partial_function)

    def _init_interfaces(self) -> Dict[str, InterfaceWrapper]:
        ''' Initialize the `InterfaceWrapper` objects '''
        xml_str = str(self.proxy.Introspect())
        doc = xml.dom.minidom.parseString(xml_str)

        root = doc.childNodes[1]  # skip doctype
        assert root.nodeName == 'node'

        return {
            _name(iface): InterfaceWrapper(iface)
            for iface in root.getElementsByTagName('interface')
        }

    def _wrap_dbus_method(self, iface_name: str, func_name: str) -> Callable:
        ''' Wrapper around a lambda calling
            `dbus.proxies.ProxyObject.get_dbus_method()` with the right
            interface and executing it.
        '''
        return lambda obj, *args, **kwargs: \
            self.proxy.get_dbus_method(func_name, dbus_interface=iface_name)(*args, **kwargs)


_DictKey = Union[str, dbus.String]  # pylint: disable=invalid-name


class PropertiesModel(Model, collections.MutableMapping):
    ''' Provides dictionary access to a `org.freedesktop.DBus.Properties` object
    '''

    def __init__(self, proxy: dbus.proxies.ProxyObject,
                 data: dbus.Dictionary=None, *args, **kwargs) -> None:
        super(PropertiesModel, self).__init__(proxy, *args, **kwargs)
        assert PROPERTIES_INTERFACE in self.interfaces
        if data is None:
            # pylint: disable=no-member
            self._data = self.GetAll('')  # type: ignore
        else:
            self._data = data

        def _update(interface, changed_properties, invalidated):
            ''' Update the internal dictionary when a property changes '''
            # pylint: disable=unused-argument
            for key, value in changed_properties.items():
                self._data[key] = value

        proxy.connect_to_signal(PROPERTIES_CHANGED, _update,
                                dbus_interface=PROPERTIES_INTERFACE)

    def __getitem__(self, key: _DictKey):
        return self._data[key]

    def __setitem__(self, key: _DictKey, value: Any) -> None:
        self.proxy.Set('', key, value)  # type: ignore

    def __delitem__(self, key: _DictKey):
        msg = 'It is not possible to delete D-Bus properties'
        raise NotImplementedError(msg)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class ObjectManagerModel(Model):
    ''' A Model which has child models. '''

    # pylint: disable=too-few-public-methods
    def __init__(self, proxy: dbus.proxies.ProxyObject,
                 cls: type=PropertiesModel) -> None:
        super(ObjectManagerModel, self).__init__(proxy)
        assert OBJECT_MANAGER_INTERFACE in self.interfaces
        child_data = self.GetManagedObjects()
        self.children = {}  # type: Dict[dbus.ObjectPath, PropertiesModel]
        bus = dbus.SessionBus()
        for child_path, _kwargs in child_data.items():
            _data = list(_kwargs.values())[0]
            child_proxy = bus.get_object(bus_name=proxy.bus_name,
                                         object_path=child_path)
            self.children[child_proxy.object_path] = cls(child_proxy, _data)

    def GetManagedObjects(self):
        ''' Wrapper arround
            'org.freedesktop.DBus.ObjectManager.GetManagedObjects'. This wrapper
            is used to keep mypy and pylint happy.
        '''
        # type:ignore pylint: disable=no-member,invalid-name
        return super(ObjectManagerModel, self).GetManagedObjects()


def _name(elem: xml.dom.minidom.Element) -> str:
    ''' Returns the name attribute from a `xml.dom.minidom.Element`. '''
    return str(elem.getAttribute('name'))


def _children(elem: xml.dom.minidom.Element,
              name: str) -> xml.dom.minidom.NodeList:
    ''' Returns children with specified name elements of a
        `xml.dom.minidom.Element`.
    '''
    return elem.getElementsByTagName(name)


def _attr(elem: xml.dom.minidom.Element, name: str) -> str:
    ''' Shorthand for `str(elem.getAttribute(name))`. '''
    return str(elem.getAttribute(name))
