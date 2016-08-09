#!/usr/bin/env python3
import signal, threading
signal.signal(signal.SIGINT, signal.SIG_DFL)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import ui.gtk3
import netstats

if __name__ == '__main__':
    monitor = netstats.NetworkStatisticsMonitorThread(['wlp3s0'])
    monitor.start()
    win = ui.gtk3.NetbandMonitorWindow(monitor)
    win.connect('delete-event', Gtk.main_quit)
    win.connect('delete-event', lambda x, y: monitor.stop())
    t = threading.Timer(6, lambda: win.context.add_class('transparent'))
    #t.start()
    
    win.show_all()
    Gtk.main()
