#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' A menu listing domains '''

import os.path
import signal
import sys
from enum import Enum

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

# pylint: disable=wrong-import-position
import qubesadmin
import qui.decorators

from qui.models.qubes import Domain, DomainManager

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import GObject, Gtk  # isort:skip

gi.require_version('AppIndicator3', '0.1')  # isort:skip
from gi.repository import AppIndicator3 as appindicator  # isort:skip

DOMAIN_MANAGER_INTERFACE = "org.qubes.DomainManager1"
DOMAIN_MANAGER_PATH = "/org/qubes/DomainManager1"
DBusSignalMatch = dbus.connection.SignalMatch


class STATE(Enum):
    FAILED = 1
    TRANSIENT = 2
    RUNNING = 3


def vm_label(decorator):
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack_start(decorator.icon(), False, True, 0)
    hbox.pack_start(decorator.name(), True, True, 0)
    hbox.pack_start(decorator.memory(), False, True, 0)
    return hbox

def sub_menu_hbox(name, image_name = None) -> Gtk.Widget:
    icon = Gtk.IconTheme.get_default().load_icon(image_name, 16, 0)
    image = Gtk.Image.new_from_pixbuf(icon)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack_start(image, False, False, 0)
    hbox.pack_start(Gtk.Label(name), True, False, 0)
    return hbox


class ShutdownItem(Gtk.ImageMenuItem):
    ''' Shutdown menu Item. When activated shutdowns the domain. '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        icon = Gtk.IconTheme.get_default().load_icon('media-playback-stop', 16, 0)
        image = Gtk.Image.new_from_pixbuf(icon)

        self.set_image(image)
        self.set_label('Shutdown')

        self.connect('activate', self.vm.Shutdown)


class KillItem(Gtk.ImageMenuItem):
    ''' Kill domain menu Item. When activated kills the domain. '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        icon = Gtk.IconTheme.get_default().load_icon('media-record', 16, 0)
        image = Gtk.Image.new_from_pixbuf(icon)

        self.set_image(image)
        self.set_label('Kill')

        self.connect('activate', self.vm.Kill)


class PreferencesItem(Gtk.ImageMenuItem):
    ''' TODO: Preferences menu Item. When activated shows preferences dialog '''
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        icon = Gtk.IconTheme.get_default().load_icon('preferences-system', 16, 0)
        image = Gtk.Image.new_from_pixbuf(icon)

        self.set_image(image)
        self.set_label('Preferences')


class LogItem(Gtk.ImageMenuItem):
    def __init__(self, vm, name, callback = None):
        super().__init__()
        image = Gtk.Image.new_from_file("/usr/share/icons/HighContrast/16x16/apps/logviewer.png")

        decorator = qui.decorators.DomainDecorator(vm)
        self.set_image(image)
        self.set_label(name)
        if callback:
            self.connect('activate', callback)


class StartedMenu(Gtk.Menu):
    ''' The sub-menu for a started domain'''

    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        preferences = PreferencesItem(self.vm)
        shutdown_item = ShutdownItem(self.vm)

        self.add(preferences)
        self.add(shutdown_item)


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


class FailureMenuItem(Gtk.ImageMenuItem):
    ''' Represents a menu item containing information about a vm. '''

    # pylint: disable=too-few-public-methods

    def __init__(self, vm):
        super().__init__()
        self.vm = vm

        self.submenu = DebugMenu(vm)
        kill_item = KillItem(vm)
        self.submenu.add(kill_item)
        self.set_submenu(self.submenu)

        decorator = qui.decorators.DomainDecorator(vm)
        pixbuf = Gtk.IconTheme.get_default().load_icon('media-record', 16, 0)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        self.set_image(icon)
        hbox = vm_label(decorator)
        self.add(hbox)


class DomainMenuItem(Gtk.ImageMenuItem):
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        self.started_menu = StartedMenu(vm)
        self.debug_menu = DebugMenu(vm)

        self.failed_menu = DebugMenu(vm)
        remove = Gtk.MenuItem("Remove")
        remove.connect('activate', lambda: self.hide)
        self.failed_menu.add(remove)

        self.progress_visible = False

        self.decorator = qui.decorators.DomainDecorator(vm)

        self.progressbar = Gtk.ProgressBar()

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.pack_start(self._domain_label(), True, True, 0)
        self.add(self.vbox)
        state = self._state()
        if state in [STATE.RUNNING, STATE.FAILED]:
            self._hide_progress()
        else:
            self._show_progress()

        self._update_submenu(state)
        self._update_image(state)
        GObject.timeout_add(150, self.pulse)

    def _domain_label(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.decorator.name(), True, True, 0)
        hbox.pack_start(self.decorator.memory(), False, True, 0)
        return hbox

    def _state(self):
        if self.vm['state'] == 'Started':
            return STATE.RUNNING
        elif self.vm['state'] == 'Failed':
            return STATE.FAILED

        return STATE.TRANSIENT

    def _show_progress(self):
        if not self.progress_visible:
            self.vbox.pack_start(self.progressbar, False, True, 0)
            self.progress_visible = True

    def pulse(self):
        if self.progress_visible:
            self.progressbar.pulse()
        return True

    def _hide_progress(self):
        if self.progress_visible:
            self.vbox.remove(self.progressbar)
            self.progress_visible = False

    def _update_image(self, state):
        if state == STATE.RUNNING:
            self.set_image(self.decorator.icon())
        elif state == STATE.FAILED:
            failed_pixbuf = Gtk.IconTheme.get_default().load_icon(
                'media-record', 16, 0)
            failed_image = Gtk.Image.new_from_pixbuf(failed_pixbuf)
            self.set_image(failed_image)
        else:
            self.set_image(self.decorator.icon(22))

    def _update_submenu(self, state):
        if state == STATE.RUNNING:
            self.set_submenu(self.started_menu)
        elif state == STATE.FAILED:
            self.set_submenu(self.failed_menu)
        else:
            self.set_submenu(self.debug_menu)


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
            'Starting': self.update_domain_item,
            'Started': self.update_domain_item,
            'Failed': self.show_failure_menu,
            'Halting': self.update_domain_item,
            'Halted': self.remove_menu,
            'Unknown': self.update_domain_item,
        }

    def remove_menu(self, _, vm_path):
        ''' Remove the menu item for the specified domain from the tray'''
        vm_widget = self.menu_items[vm_path]
        self.tray_menu.remove(vm_widget)
        del self.menu_items[vm_path]

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

    def update_domain_item(self, _, vm_path):
        ''' Add/Replace the menu item with the started menu for the specified vm in the tray'''
        if vm_path in self.menu_items:
            self.remove_menu(None, vm_path)

        vm = self.domain_manager.children[vm_path]
        domain_item = DomainMenuItem(vm)
        self.tray_menu.add(domain_item)
        self.menu_items[vm_path] = domain_item
        self.tray_menu.show_all()

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
            else:
                self.update_domain_item(DOMAIN_MANAGER_INTERFACE, vm_path)

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
