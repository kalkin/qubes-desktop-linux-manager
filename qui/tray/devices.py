# pylint: disable=missing-docstring
import os.path
import signal
import subprocess
import sys

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True) # isort:skip

import qubesadmin
from qubesadmin.vm import AdminVM
from qubesadmin.devices import DeviceAssignment
from qui.models.qubes import DomainManager


import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip pylint:

gi.require_version('AppIndicator3', '0.1')  # isort:skip
from gi.repository import AppIndicator3 as appindicator  # isort:skip

QUBES_APP = qubesadmin.Qubes()
DBUS = dbus.SessionBus()
DOMAIN_MANAGER = DomainManager()


def find_vm(vm_path):
    qid = int(os.path.basename(vm_path))
    for vm in QUBES_APP.domains:
        if vm.qid == qid:
            return vm


class DeviceData():
    ''' Wraps all the data needed to display information about a device '''

    def __init__(self, data: DeviceAssignment):
        self.dev_type = data.devclass
        self.assignment = data
        self.vm_icon = self.assignment.backend_domain.label.icon
        self.name = "%s:%s" % (self.assignment.backend_domain.name,
                               self.assignment.ident)
        self.dbus_path = os.path.join('/org/qubes/DomainManager1',
                                      str(self.assignment.backend_domain.qid),
                                      self.dev_type, self.assignment.ident)

        if self.dev_type == 'block':
            self.icon = 'drive-removable-media'
        else:
            self.icon = 'network-wired-symbolic'

    def attach(self, vm):
        if self.assignment.frontend_domain:
            self.detach()

        self.assignment.frontend_domain = vm
        dev_col = self.assignment.backend_domain.devices[self.dev_type]
        try:
            dev_col.attach(self.assignment)
        except Exception as e:
            print(e)

    def detach(self):
        if self.assignment.frontend_domain:
            dev_col = self.assignment.frontend_domain.devices[self.dev_type]
            try:
                dev_col.detach(self.assignment)
            except Exception as e:
                print(e)
            self.assignment.frontend_domain = None


class DomainMenuItem(Gtk.MenuItem):
    def __init__(self, data: DeviceData, vm, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.vm = vm
        self.data = data
        self.ejected = True
        self._hbox = self._create_hbox()

        self.add(self._hbox)

    def _create_hbox(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        label = Gtk.Label(self.vm.name, xalign=0)

        hbox.pack_start(create_icon(self.vm.label.icon), False, True, 5)
        hbox.pack_start(label, True, True, 5)

        if self.data.assignment.frontend_domain == self.vm:
            eject_icon = create_icon('media-eject')
            hbox.pack_start(eject_icon, False, False, 5)
            self.ejected = False
        else:
            add_icon = create_icon('list-add')
            hbox.pack_start(add_icon, False, False, 5)
        return hbox

    def attach(self):
        assert self.ejected
        self.ejected = False

        self.remove(self._hbox)
        self._hbox = self._create_hbox()
        self.add(self._hbox)
        self.show_all()

    def detach(self):
        assert not self.ejected
        self.ejected = True
        self.remove(self._hbox)
        self._hbox = self._create_hbox()
        self.add(self._hbox)
        self.show_all()


class DomainMenu(Gtk.Menu):
    def __init__(self, data: DeviceData, *args, **kwargs):
        super(DomainMenu, self).__init__(*args, **kwargs)
        self.data = data
        self.menu_items = {}

        domains = [
            v for v in QUBES_APP.domains
            if v.is_running() and not isinstance(v, AdminVM)
        ]

        for vm in domains:
            self._add_vm(vm)

        DOMAIN_MANAGER.connect_to_signal('Started', self.add_vm)
        DOMAIN_MANAGER.connect_to_signal('DomainAdded', self.add_vm)
        DOMAIN_MANAGER.connect_to_signal('DomainRemoved', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Halted', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Failed', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Unknown', self.remove_vm)

    def _add_vm(self, vm):
        menu_item = DomainMenuItem(self.data, vm)
        menu_item.connect('activate', self.toggle)
        self.menu_items[vm.name] = menu_item
        self.append(menu_item)

    def add_vm(self, _, vm_path):
        print("add_vm %s" % vm_path)
        vm = find_vm(vm_path)
        self._add_vm(vm)
        self.show_all()

    def remove_vm(self, _, vm_path):
        print("remove_vm %s" % vm_path)
        vm = find_vm(vm_path)
        menu_item = self.menu_items[vm.name]
        if not menu_item.ejected:
            self.detach()
        self.remove(menu_item)
        self.show_all()

    def toggle(self, menu_item):
        if menu_item.ejected:
            self.attach(menu_item.vm)
        else:
            self.detach()

    def attach(self, vm):
        vm_name = vm.name
        menu_item = self.menu_items[vm_name]

        if self.data.assignment.frontend_domain:
            self.detach()

        self.data.attach(vm)
        menu_item.attach()
        subprocess.call(['notify-send', "Simulating attachment on %s" % vm])

    def detach(self):
        vm_name = self.data.assignment.frontend_domain.name
        menu_item = self.menu_items[vm_name]
        self.data.detach()
        menu_item.detach()
        subprocess.call(['notify-send', "Simulating detachment"])


class DeviceItem(Gtk.MenuItem):
    def __init__(self, data: DeviceData, *args, **kwargs):
        "docstring"
        super().__init__(*args, **kwargs)

        vm_icon = create_icon(data.vm_icon)
        dev_icon = create_icon(data.icon)
        name = Gtk.Label(data.name, xalign=0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(vm_icon, True, True, 0)
        hbox.pack_start(name, True, True, 0)
        hbox.pack_start(dev_icon, True, True, 0)
        self.add(hbox)
        submenu = DomainMenu(data)
        self.set_submenu(submenu)


class DevicesTray(Gtk.Application):
    def __init__(self, app_name='Devices Tray', dev_type='block'):
        super(DevicesTray, self).__init__()
        self.name = app_name
        self.tray_menu = Gtk.Menu()
        self.dev_type = dev_type

        self.ind = appindicator.Indicator.new(
            'Devices Widget', "gtk-preferences",
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.ind.set_menu(self.tray_menu)
        self.menu_items = {}
        DOMAIN_MANAGER.connect_to_signal('Started', self.add_vm)
        DOMAIN_MANAGER.connect_to_signal('DomainAdded', self.add_vm)
        DOMAIN_MANAGER.connect_to_signal('DomainRemoved', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Halted', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Failed', self.remove_vm)
        DOMAIN_MANAGER.connect_to_signal('Unknown', self.remove_vm)

    def _add_device(self, device, vm):
        assignment = DeviceAssignment(vm, device.ident, {}, persistent=False,
                                      frontend_domain=None,
                                      devclass=self.dev_type)
        data = DeviceData(assignment)
        item = DeviceItem(data)
        self.menu_items[data.name] = item
        self.tray_menu.add(item)

    def _add_devices(self, vm):
        for device in vm.devices[self.dev_type].available():
            self._add_device(device, vm)

    def add_vm(self, _, vm_path):
        vm = find_vm(vm_path)
        self._add_devices(vm)

    def remove_vm(self, _, vm_path):
        vm = find_vm(vm_path)
        for device in vm.devices[self.dev_type]:
            name = "%s:%s" % (vm.name, device.ident)
            menu_item = self.menu_items[name]
            self.tray_menu.remove(menu_item)

        self.tray_menu.show_all()

    def run(self):  # pylint: disable=arguments-differ
        for vm in QUBES_APP.domains:
            self._add_devices(vm)
            # for assignment in vm.devices[self.dev_type].assignments(
            #         persistent=False):
            #     data = DeviceData(assignment, self.dev_type)
            #     item = DomainMenu(data)
            #     self.tray_menu.add(item)

        self.tray_menu.show_all()

        Gtk.main()


def create_icon(name):
    icon_dev = Gtk.IconTheme.get_default().load_icon(name, 22, 0)
    return Gtk.Image.new_from_pixbuf(icon_dev)


def main():
    if len(sys.argv) > 1:
        dev_type = sys.argv[1]
        app = DevicesTray(dev_type=dev_type)
    else:
        app = DevicesTray()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run()


if __name__ == '__main__':
    sys.exit(main())
