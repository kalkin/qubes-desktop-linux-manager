#!/usr/bin/env python3
''' Decorators wrap a `qui.models.PropertiesModel` in a class
containing helpful representation methods.
'''

import gi  # isort:skip
import dbus
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk, Pango  # isort:skip

import qubesadmin
import qui.models.qubes
from qui.models.qubes import Device, Domain

LABELS = qui.models.qubes.LabelsManager()


class PropertiesDecorator():
    ''' Base class for all decorators '''

    # pylint: disable=too-few-public-methods

    def __init__(self, obj, margins=(5, 5)) -> None:
        self.obj = obj
        self.margin_left = margins[0]
        self.margin_right = margins[1]
        super(PropertiesDecorator, self).__init__()

    def set_margins(self, widget):
        ''' Helper for setting the default margins on a widget '''
        widget.set_margin_left(self.margin_left)
        widget.set_margin_right(self.margin_right)


class DomainDecorator(PropertiesDecorator):
    ''' Useful methods for domain data representation '''

    # pylint: disable=missing-docstring
    def __init__(self, vm: qubesadmin.vm.QubesVM, margins=(5, 5)) -> None:
        super(DomainDecorator, self).__init__(vm, margins)

    def name(self):
        label = Gtk.Label(self.obj['name'], xalign=0)
        self.set_margins(label)
        return label

    def memory(self) -> Gtk.Label:
        label = Gtk.Label(
            str(int(self.obj['memory_usage'] / 1024)) + ' MB', xalign=0)
        self.set_margins(label)
        label.set_sensitive(False)
        return label

    def icon(self) -> Gtk.Image:
        ''' Returns a `Gtk.Image` containing the colored lock icon '''
        label_path = self.obj['label']
        assert label_path in LABELS.children
        label = LABELS.children[label_path]
        if label is None:
            label = LABELS.BLACK  # pylint: disable=no-member
        icon_vm = Gtk.IconTheme.get_default().load_icon(label['icon'], 16, 0)
        icon_img = Gtk.Image.new_from_pixbuf(icon_vm)
        return icon_img

    def netvm(self) -> Gtk.Label:
        netvm = self.obj['netvm']
        if netvm is None:
            label = Gtk.Label('No', xalign=0)
        else:
            label = Gtk.Label(netvm['name'], xalign=0)

        self.set_margins(label)
        return label


def device_hbox(dev: Device) -> Gtk.Box:
    ''' Returns a :class:`Gtk.Box` containing the device name & icon.. '''
    if dev['dev_class'] == 'block':
        icon = 'drive-removable-media'
    elif dev['dev_class'] == 'mic':
        icon = 'audio-input-microphone'
    elif dev['dev_class'] == 'usb':
        icon = 'generic-usb'
    else:
        icon = 'emblem-important'
    dev_icon = create_icon(icon)

    name_label = Gtk.Label(dev.name, xalign=0)
    name_label.set_max_width_chars(64)
    name_label.set_ellipsize(Pango.EllipsizeMode.END)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    hbox.pack_start(name_label, True, True, 0)
    hbox.pack_start(dev_icon, False, True, 0)
    return hbox

def device_domain_hbox(vm: Domain, attached: bool) -> Gtk.Box:
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

    # hbox.pack_start(label, True, True, 5)

    if attached:
        eject_icon = create_icon('media-eject')
        hbox.pack_start(eject_icon, False, False, 5)
    else:
        add_icon = create_icon('list-add')
        hbox.pack_start(add_icon, False, False, 5)

    name = Gtk.Label(vm['name'], xalign=0)
    hbox.pack_start(name, True, True, 5)
    return hbox


def create_icon(name: dbus.String) -> Gtk.Image:
    ''' Create an icon from string '''
    icon_dev = Gtk.IconTheme.get_default().load_icon(name, 16, 0)
    return Gtk.Image.new_from_pixbuf(icon_dev)
