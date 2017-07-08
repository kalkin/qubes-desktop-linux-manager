#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
''' This is the graphical equivalent of `qvm-ls(1)` based on `Gtk.TreeView`'''

from __future__ import print_function

import signal

import qubesadmin
import qubesadmin.tools.qvm_ls

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
            self.append([col.cell(vm) for col in columns])


class ListBoxWindow(Gtk.Window):
    def __init__(self, args):

        if args.fields:
            col_names = args.fields
        else:
            col_names = qubesadmin.tools.qvm_ls.formats[args.format]

        columns = []
        for col in col_names:
            col = col.strip().upper()
            if col in qubesadmin.tools.qvm_ls.Column.columns:
                columns += [qubesadmin.tools.qvm_ls.Column.columns[col]]

        Gtk.Window.__init__(self, title="TreeView Demo")
        self.set_border_width(10)

        # self.grid = Gtk.Grid()
        # self.grid.set_column_homogeneous(True)
        self.store = DomainsListStore(args.app, columns)
        self.treeview = Gtk.TreeView.new_with_model(self.store)
        self.treeview.append_column(
            Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=0))
        i = 0
        for col in columns:
            self.treeview.append_column(
                Gtk.TreeViewColumn(
                    str(col.ls_head), Gtk.CellRendererText(), text=i))
            i += 1
        self.add(self.treeview)
        self.show_all()

    def reload(self):
        print("drin")


def main(args=None):  # pylint:disable=unused-argument
    parser = qubesadmin.tools.qvm_ls.get_parser()
    try:
        args = parser.parse_args()
    except qubesadmin.exc.QubesException as e:
        parser.print_error(e.message)
        return 1
    window = ListBoxWindow(args)
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
