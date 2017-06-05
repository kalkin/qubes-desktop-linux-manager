#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' A menu listing domains '''

import signal
import sys

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
        self.menu = Gtk.Menu()
        domains = qubesadmin.Qubes().domains
        active_vms = [vm for vm in domains if vm.is_running()]
        for vm in active_vms:
            if vm.name == 'dom0':
                continue
            else:
                self.menu.add(DomainMenuItem(vm))
        self.menu.show_all()
        self.ind.set_menu(self.menu)

    def run(self):  # pylint: disable=arguments-differ
        Gtk.main()


def main():
    ''' main function '''
    app = MyApp('Scaffold')
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
