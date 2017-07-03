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

from qui.models.qubes import Domain, DomainManager

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip

gi.require_version('AppIndicator3', '0.1')  # isort:skip
from gi.repository import AppIndicator3 as appindicator  # isort:skip

DOMAIN_MANAGER_INTERFACE = "org.qubes.DomainManager1"
DOMAIN_MANAGER_PATH = "/org/qubes/DomainManager1"
DBusSignalMatch = dbus.connection.SignalMatch


def vm_label(vm):
    decorator = qui.decorators.DomainDecorator(vm)
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack_start(decorator.state(), False, True, 0)
    hbox.pack_start(decorator.icon(), False, True, 0)
    hbox.pack_start(decorator.name(), True, True, 0)
    hbox.pack_start(decorator.memory(), False, True, 0)
    return hbox

def sub_menu_hbox(name, image_name = None) -> Gtk.Widget:
    icon = Gtk.IconTheme.get_default().load_icon(image_name, 22, 0)
    image = Gtk.Image.new_from_pixbuf(icon)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack_start(image, False, False, 0)
    hbox.pack_start(Gtk.Label(name), True, False, 0)
    return hbox


class ShutdownItem(Gtk.MenuItem):
    ''' Shutdown menu Item. When activated shutdowns the domain. '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        hbox = sub_menu_hbox("Shutdown", image_name = "media-playback-stop")
        self.add(hbox)

        self.connect('activate', self.vm.Shutdown)


class KillItem(Gtk.MenuItem):
    ''' Kill domain menu Item. When activated kills the domain. '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        hbox = sub_menu_hbox("Kill", image_name = "media-record")
        self.add(hbox)

        self.connect('activate', self.vm.Kill)


class PreferencesItem(Gtk.MenuItem):
    ''' TODO: Preferences menu Item. When activated shows preferences dialog '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        hbox = sub_menu_hbox("preferences", image_name = "preferences-system")
        self.add(hbox)


class LogItem(Gtk.MenuItem):
    def __init__(self, vm, name, callback = None):
        super().__init__()
        image = Gtk.Image.new_from_file("/usr/share/icons/HighContrast/22x22/apps/logviewer.png")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(image, False, False, 0)
        hbox.pack_start(Gtk.Label(name), False, False, 0)
        if callback:
            self.connect('activate', callback)
        self.add(hbox)


class StartedMenu(Gtk.Menu):
    ''' The sub-menu for a started domain'''

    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        preferences = PreferencesItem(self.vm)
        shutdown_item = ShutdownItem(self.vm)

        self.add(preferences)
        self.add(shutdown_item)


class StartedMenuItem(Gtk.MenuItem):
    ''' Represents a menu item containing the sub-menu for a started domain '''

    # pylint: disable=too-few-public-methods

    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        submenu = StartedMenu(vm)
        self.set_submenu(submenu)
        hbox = vm_label(vm)
        self.add(hbox)


class DebugMenu(Gtk.Menu):
    ''' Sub-menu providing multiple MenuItem for domain logs. '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        console = LogItem(self.vm, "Console Log")
        guid = LogItem(self.vm, "GUI Daemon Log")
        qrexec = LogItem(self.vm, "Qrexec Log")
        kill = KillItem(self.vm)
        preferences = PreferencesItem(self.vm)

        self.add(console)
        self.add(qrexec)
        self.add(guid)
        self.add(preferences)
        self.add(kill)


class DebugMenuItem(Gtk.MenuItem):
    ''' MenuItem providing different logs for a domain. '''

    # pylint: disable=too-few-public-methods

    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        submenu = DebugMenu(vm)
        self.set_submenu(submenu)

        hbox = vm_label(vm)
        self.add(hbox)


class FailureMenuItem(Gtk.MenuItem):
    ''' Represents a menu item containing information about a vm. '''

    # pylint: disable=too-few-public-methods

    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        self.submenu = DebugMenu(vm)
        kill_item = KillItem(vm)
        self.submenu.add(kill_item)
        self.set_submenu(self.submenu)

        hbox = vm_label(vm)
        self.add(hbox)


class DomainTray(Gtk.Application):
    ''' A tray icon application listing all but halted domains. ” '''

    def __init__(self, app_name):
        super().__init__()
        self.name = app_name
        self.tray_menu = Gtk.Menu()
        self.ind = indicator(self.tray_menu)
        self.domain_manager = DomainManager()
        self.signal_matches = {} # type: Dict[dbus.ObjectPath, List[DBusSignalMatch]]
        self.menu_items = {} # type: Dict[dbus.ObjectPath, Gtk.MenuItem]

        self.signal_callbacks = {
            'Starting': self.show_debug_menu,
            'Started' : self.show_started_menu,
            'Failed'  : self.show_failure_menu,
            'Halting' : self.show_debug_menu,
            'Halted'  : self.remove_menu,
            'Unknown' : self.show_debug_menu,
        }


    def remove_menu(self, _, vm_path):
        ''' Remove the menu item for the specified domain from the tray'''
        vm_widget = self.menu_items[vm_path]
        self.tray_menu.remove(vm_widget)
        del self.menu_items[vm_path]

    def show_debug_menu(self, _, vm_path):
        ''' Add/Replace the menu item with the debug menu for the specified vm in the tray'''
        if vm_path in self.menu_items:
            self.remove_menu(_, vm_path)
        vm = self.domain_manager.children[vm_path]
        widget = DebugMenuItem(vm)
        self.tray_menu.add(widget)
        self.tray_menu.show_all()
        self.menu_items[vm_path] = widget

    def show_failure_menu(self, _, vm_path):

        if vm_path in self.menu_items:
            self.remove_menu(_, vm_path)
        vm = self.domain_manager.children[vm_path]
        widget = FailureMenuItem(vm)

        remove = Gtk.MenuItem("Remove")
        remove.connect('activate', lambda: self.remove_menu(None, vm_path))
        widget.submenu.add(remove)

        self.tray_menu.add(widget)
        self.tray_menu.show_all()
        self.menu_items[vm_path] = widget

    def show_started_menu(self, _, vm_path):
        ''' Add/Replace the menu item with the started menu for the specified vm in the tray'''
        if vm_path in self.menu_items:
            self.remove_menu(_, vm_path)
        vm = self.domain_manager.children[vm_path]
        widget = StartedMenuItem(vm)
        self.tray_menu.add(widget)
        self.tray_menu.show_all()
        self.menu_items[vm_path] = widget

    def run(self):  # pylint: disable=arguments-differ
        for signal_name, handler_function in self.signal_callbacks.items():
            matcher = self.domain_manager.connect_to_signal(signal_name,
                                                            handler_function)

            if signal_name not in self.signal_matches:
                self.signal_matches[signal_name] = list()

            self.signal_matches[signal_name] += [matcher]


        for vm_path, vm in self.domain_manager.children.items():
            if vm['name'] == 'dom0' or vm['state'] == 'Halted':
                continue
            elif vm['state'] == 'Started':
                self.show_started_menu(DOMAIN_MANAGER_INTERFACE, vm_path)
            else:
                self.show_debug_menu(DOMAIN_MANAGER_INTERFACE, vm_path)

        self.connect('shutdown', self._disconnect_signals)
        Gtk.main()

    def _disconnect_signals(self, _):
        for matchers in self.signal_matches.values():
            for matcher in matchers:
                self.domain_manager.disconnect_signal(matcher)

def indicator(tray_menu: Gtk.Menu) -> appindicator.Indicator:
    '''Helper function to setup the indicator object'''
    ind = appindicator.Indicator.new(
        'Qubes Widget', "qubes-logo-icon",
        appindicator.IndicatorCategory.SYSTEM_SERVICES)
    ind.set_menu(tray_menu)
    ind.set_status(appindicator.IndicatorStatus.ACTIVE)
    return ind


def main():
    ''' main function '''
    app = DomainTray('org.qubes.ui.tray.Domains')
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
