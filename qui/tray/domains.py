#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' A menu listing domains '''

import os.path
import signal
import sys

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

# pylint: disable=wrong-import-position
import qubesadmin
import qui.decorators

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip

gi.require_version('AppIndicator3', '0.1')  # isort:skip
from gi.repository import AppIndicator3 as appindicator  # isort:skip

DOMAIN_MANAGER_INTERFACE = "org.qubes.DomainManager1"
DOMAIN_MANAGER_PATH = "/org/qubes/DomainManager1"
DOMAINS = qubesadmin.Qubes().domains
VM_MENU = Gtk.Menu()


class DomainMenuItem(Gtk.MenuItem):
    ''' Represents a menu item containing information about a vm. '''

    # pylint: disable=too-few-public-methods

    def __init__(self, vm):
        super(DomainMenuItem, self).__init__()
        self.vm = vm
        decorator = qui.decorators.DomainDecorator(vm)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(decorator.icon(), False, True, 0)
        hbox.pack_start(decorator.name(), True, True, 0)
        hbox.pack_start(decorator.memory(), False, True, 0)
        self.add(hbox)
        self.connect('activate', self.stop_vm)

    def start_spinning(self):
        # TODO
        pass

    def stop_spinning(self):
        # TODO
        pass

    def stop_vm(self, _):
        self.vm.shutdown()


class MyApp(Gtk.Application):
    ''' Implements the Freedesktop “System Tray Protocol Specification” '''

    def __init__(self, app_name):
        super(MyApp, self).__init__()
        self.name = app_name
        self.ind = appindicator.Indicator.new(
            'Qubes Widget', "qubes-logo-icon",
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.bus = dbus.SessionBus()

        for vm in DOMAINS:
            if vm.name == 'dom0':
                continue

            obj = self._dbus_object(vm)
            obj.connect_to_signal("Started", lambda: self._menu_add(vm),
                                  dbus_interface="org.qubes.Domain")

            if vm.is_running():
                self._menu_add(vm)

        self.ind.set_menu(VM_MENU)

    def _dbus_object(self, vm: qubesadmin.vm.QubesVM):
        path = "%s/domains/%s" % (DOMAIN_MANAGER_PATH, vm.qid)
        print(path)
        return self.bus.get_object(DOMAIN_MANAGER_INTERFACE, path)

    def _menu_add(self, vm: qubesadmin.vm.QubesVM):
        widget = DomainMenuItem(vm)
        obj = self._dbus_object(vm)
        obj.connect_to_signal("Halted", lambda: VM_MENU.remove(widget),
                              dbus_interface="org.qubes.Domain")

        VM_MENU.add(widget)
        VM_MENU.show_all()

    def run(self):  # pylint: disable=arguments-differ
        Gtk.main()


def main():
    ''' main function '''
    app = MyApp('Scaffold')
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
