#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
''' This is the graphical equivalent of `qvm-ls(1)` based on `Gtk.TreeView`'''

from __future__ import print_function

import signal

import qubesadmin
import qubesadmin.tools.qvm_ls as qvm_ls

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gio, Gtk  # isort:skip pylint: disable=C0413

# pylint:disable=missing-docstring


class DomainsListStore(Gtk.ListStore):
    def __init__(self, app, columns, **kwargs):
        params = [
            str,
        ] * len(columns)
        super(DomainsListStore, self).__init__(*params, **kwargs)
        for vm in app.domains:
            if vm.name == 'dom0':
                continue
            self.append([col.cell(vm) for col in columns])


class ListBoxWindow(Gtk.Window):
    def __init__(self, app, col_names):
        super().__init__(title="Domain List")
        self.app = app
        self.filter = ["Halted"]
        self.col_names = col_names
        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.add(self._button_bar())
        hbox.pack_start(self._tree_view(), True, True, 5)
        self.add(hbox)
        self.show_all()

    def _button_bar(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        states = ["Halted", "Transient", "Running"]
        for state in states:
            button = Gtk.ToggleButton(state)
            if state not in self.filter:
                button.set_active(True)
            button.connect('toggled', self._toggle_filter, state)
            vbox.add(button)
        vbox.set_halign(Gtk.Align.CENTER)
        return vbox

    def _toggle_filter(self, widget, state):
        if widget.get_active():
            self.filter.remove(state)
        else:
            self.filter.append(state)

        self.filter_store.refilter()
        self.show_all()

    def _tree_view(self):
        columns = []
        for col in self.col_names:
            col = col.strip().upper()
            if col in qvm_ls.Column.columns:
                columns += [qvm_ls.Column.columns[col]]

        self.set_border_width(10)

        # self.grid = Gtk.Grid()
        # self.grid.set_column_homogeneous(True)
        store = DomainsListStore(self.app, columns)
        self.filter_store = store.filter_new()
        self.filter_store.set_visible_func(self._filter_func)
        treeview = Gtk.TreeView.new_with_model(self.filter_store)
        for index in range(0, len(columns)):
            col = columns[index]
            title = str(col.ls_head)
            if col.ls_head == 'LABEL':
                renderer = Gtk.CellRendererPixbuf()
                kwargs = {'icon-name': index}
            else:
                renderer = Gtk.CellRendererText()
                kwargs = {'text': index}

            view_column = Gtk.TreeViewColumn(title, renderer, **kwargs)
            treeview.append_column(view_column)
        return treeview

    def _filter_func(self, model, iter, data):
        state = model[iter][1]
        if state in self.filter:
            return False
        return True

    def reload(self):
        print("drin")


qvm_ls.Column('LABEL', attr=(lambda vm: vm.label.icon), doc="Label icon")

#: Available formats. Feel free to plug your own one.
formats = {
    'simple': ('state', 'label', 'name', 'class', 'template', 'netvm'),
    'network': ('state', 'label', 'name', 'netvm', 'ip', 'ipback', 'gateway'),
    'full': ('state', 'label', 'name', 'class', 'qid', 'xid', 'uuid'),
    #  'perf': ('name', 'state', 'cpu', 'memory'),
    'disk': ('state', 'label', 'name', 'disk', 'priv-curr', 'priv-max',
             'priv-used', 'root-curr', 'root-max', 'root-used'),
}


def main(args=None):  # pylint:disable=unused-argument
    parser = qvm_ls.get_parser()
    try:
        args = parser.parse_args()
    except qubesadmin.exc.QubesException as e:
        parser.print_error(e.message)
        return 1

    if args.fields:
        columns = [col.strip() for col in args.fields.split(',')]
    else:
        columns = formats[args.format]

    # assume unknown columns are VM properties
    for col in columns:
        if col.upper() not in qvm_ls.Column.columns:
            qvm_ls.PropertyColumn(col.lower())

    window = ListBoxWindow(args.app, columns)
    window.connect("delete-event", Gtk.main_quit)
    w_file = Gio.File.new_for_path("/var/lib/qubes/qubes.xml")
    monitor = w_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
    monitor.connect("changed", window.reload)
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    # next line is for behaving well with Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
