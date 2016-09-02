#!/usr/bin/env python3
import signal, threading
signal.signal(signal.SIGINT, signal.SIG_DFL)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import netbandmonitor.netstats, netbandmonitor.ui.gtk3

if __name__ == '__main__':
    monitor = netbandmonitor.netstats.NetworkStatisticsMonitorThread(
      netbandmonitor.netstats.list_network_interfaces())
    monitor.start()
    win = netbandmonitor.ui.gtk3.NetbandMonitorWindow(monitor)
    win.connect('delete-event', Gtk.main_quit)
    win.connect('delete-event', lambda x, y: monitor.stop())
    #t = threading.Timer(6, lambda: win.context.add_class('transparent'))
    #t.start()
    
    win.show_all()
    Gtk.main()
