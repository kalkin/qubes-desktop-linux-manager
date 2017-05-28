#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' A menu listing domains '''

import signal
import sys

import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

# pylint: disable=wrong-import-position
import qui.decorators
from qui.models.qubes import DOMAINS

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
        decorator = qui.decorators.DomainDecorator(vm)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(decorator.icon(), False, True, 0)
        hbox.pack_start(decorator.name(), True, True, 0)
        hbox.pack_start(decorator.prefs_button(), False, True, 0)
        hbox.pack_start(decorator.stop_button(), False, True, 0)
        hbox.pack_start(decorator.memory(), False, True, 0)
        self.add(hbox)


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
        for domain in DOMAINS.children.values():
            self.menu.add(DomainMenuItem(domain))
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
