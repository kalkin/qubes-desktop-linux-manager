# pylint: disable=missing-docstring
import os.path
import signal
import sys

import qubesadmin
import qubesadmin.vm

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip pylint:

gi.require_version('AppIndicator3', '0.1')  # isort:skip
from gi.repository import AppIndicator3 as appindicator  # isort:skip

QUBES_APP = qubesadmin.Qubes()


class RadioNone(Gtk.RadioMenuItem):
    def __init__(self, active_vm=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.name('None'), True, True, 0)
        hbox.set_margin_right(10)
        self.add(hbox)
        active = active_vm is None
        self.set_active(active)

    @staticmethod
    def name(s):
        label = Gtk.Label(str(s), xalign=0)
        label.set_margin_left(32)
        return label


class IconMenuItem(Gtk.MenuItem):
    def __init__(self, label, icon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.icon(icon), False, True, 0)
        hbox.pack_start(self.name(label), True, True, 0)
        hbox.set_margin_right(10)
        self.add(hbox)

    @staticmethod
    def name(s):
        label = Gtk.Label(str(s), xalign=0)
        set_margins(label)
        return label

    @staticmethod
    def icon(s):
        icon_vm = Gtk.IconTheme.get_default().load_icon(s, 22, 0)
        icon_img = Gtk.Image.new_from_pixbuf(icon_vm)
        set_margins(icon_img)
        return icon_img


class RadioIconMenuItem(Gtk.RadioMenuItem):
    def __init__(self, label, icon, active=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.icon(icon), False, True, 0)
        hbox.pack_start(self.name(label), True, True, 0)
        hbox.set_margin_right(10)
        self.add(hbox)
        self.set_active(active)

    @staticmethod
    def name(s):
        label = Gtk.Label(str(s), xalign=0)
        set_margins(label)
        return label

    @staticmethod
    def icon(s):
        icon_vm = Gtk.IconTheme.get_default().load_icon(s, 22, 0)
        icon_img = Gtk.Image.new_from_pixbuf(icon_vm)
        set_margins(icon_img)
        return icon_img


class RadioDomainItem(RadioIconMenuItem):
    def __init__(self, vm, active=False):
        label = str(vm)
        icon = vm.label.icon
        super(RadioDomainItem, self).__init__(label, icon, active)


def set_margins(widget):
    widget.set_margin_left(5)
    widget.set_margin_right(5)


class DomainMenu(Gtk.Menu):
    def __init__(self, device, *args, **kwargs):
        super(DomainMenu, self).__init__(*args, **kwargs)
        self.active_vm = device.frontend_domain
        self.known_domains = {}
        self.active_vm = device.frontend_domain
        self.append(RadioNone(self.active_vm))

        for vm in [v for v in QUBES_APP.domains if not v.is_halted()]:
            if not isinstance(vm, qubesadmin.vm.AdminVM):
                self.add_domain(vm)
                self.known_domains[vm.qid] = vm

    def add_domain(self, vm):
        if isinstance(vm, qubesadmin.vm.QubesVM):
            label = str(vm)
            icon = vm.label.icon
            b_act = (label == self.active_vm)
            row = RadioIconMenuItem(label, icon, b_act)
            super(DomainMenu, self).append(row)
        else:
            super(DomainMenu, self).add(vm)


class DeviceItem(Gtk.MenuItem):

    def __init__(self, device, *args, **kwargs):
        "docstring"
        super(DeviceItem, self).__init__(*args, **kwargs)

        vm_icon = create_icon(device.vm_icon)
        dev_icon = create_icon(device.icon)
        name = Gtk.Label(device.name, xalign=0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(vm_icon, True, True, 0)
        hbox.pack_start(name, True, True, 0)
        hbox.pack_start(dev_icon, True, True, 0)
        self.add(hbox)
        submenu = DomainMenu(device)
        self.set_submenu(submenu)


class DeviceData():
    ''' Wraps all the data needed to display information about a device '''

    def __init__(self, device, dev_type):
        self.backend_domain = device.backend_domain
        self.frontend_domain = None
        self.dev_type = dev_type
        self.vm_icon = self.backend_domain.label.icon
        self.name = "%s:%s" % (self.backend_domain.name, device.ident)
        self.dbus_path = os.path.join('/org/qubes/DomainManager1',
                                      str(self.backend_domain.qid), self.dev_type,
                                      device.ident)

        if self.dev_type == 'block':
            self.icon = 'drive-removable-media'
        else:
            self.icon = 'network-wired-symbolic'

        for vm in QUBES_APP.domains:
            try:
                if device in vm.devices[dev_type].attached():
                    self.frontend_domain = vm
            except qubesadmin.exc.QubesDaemonNoResponseError as exc:
                print(exc, file=sys.stderr)


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

    def run(self):  # pylint: disable=arguments-differ
        for vm in QUBES_APP.domains:
            for device in vm.devices[self.dev_type]:
                device_data = DeviceData(device, self.dev_type)
                menu_item = DeviceItem(device_data)
                self.tray_menu.add(menu_item)

        self.tray_menu.show_all()

        Gtk.main()


def create_icon(name):
    icon_dev = Gtk.IconTheme.get_default().load_icon(name, 22, 0)
    return Gtk.Image.new_from_pixbuf(icon_dev)


def main():
    app = DevicesTray()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run()


if __name__ == '__main__':
    sys.exit(main())
