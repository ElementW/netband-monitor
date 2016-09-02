import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import cairo
from collections import deque

def clamp(n, smallest, largest): return max(smallest, min(n, largest))

class LineChart(Gtk.Misc):
    __gtype_name__ = 'LineChart'

    class Line(object):
        def __init__(self, color=None, width=None, *args, **kwargs):
            self.color = color
            self.width = width
            self.data = deque()

    def __init__(self, *args, **kwargs):
        super(LineChart, self).__init__(*args, **kwargs)
        self.set_size_request(40, 40)
        self.lines = []
        self.data_max = 1

    def do_draw(self, cr):
        allocation = self.get_allocation()
        for line in self.lines:
            fg_color = line.color if line.color is not None else \
                self.get_style_context().get_color(Gtk.StateFlags.NORMAL)
            cr.set_source_rgba(*list(fg_color))
            line_width = line.width if line.width is not None else 2
            cr.set_line_width(line_width)
            lw2 = line_width / 2
            h = allocation.height
            for i, data in enumerate(line.data):
                if i == 0:
                    cr.move_to(0, min(h - data/self.data_max*h, h - lw2))
                else:
                    cr.line_to(i*(float(allocation.width)/(len(line.data)-1)),
                        min(h - data/self.data_max*h, h - lw2))
            if len(line.data) > 0:
                cr.stroke() 
