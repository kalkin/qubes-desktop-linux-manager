#!/usr/bin/env python3
''' Decorators wrap a `qui.models.PropertiesModel` in a class
containing helpful representation methods.
'''

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip

import qubesadmin
import qui.models.qubes

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
        label = Gtk.Label(str(int(self.obj['memory_usage']/1024)) + ' MB', xalign=0)
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
