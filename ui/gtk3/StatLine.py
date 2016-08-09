import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

class StatLine(Gtk.Grid):
    __gtype_name__ = 'StatLine'

    class Statistics(object):
        def __init__(self, title='Stat', value='no data', *args, **kwargs):
            self._title = title
            self._value = value
            self.title_label = Gtk.Label()
            self.title_label.set_text(title)
            self.value_label = Gtk.Label()
            self.value_label.set_text(value)
            self.value_label.modify_font(Pango.FontDescription('monospace'))

        @property
        def title(self):
            return self._title

        @title.setter
        def title(self, value):
            self._title = value
            self.title_label.set_text(value)

        @property
        def value(self):
            return self._title

        @value.setter
        def value(self, nvalue):
            self._value = nvalue
            self.value_label.set_text(nvalue)
            
    def __init__(self, title='Statistics Line', count=None, *args, **kwargs):
        super(StatLine, self).__init__(*args, **kwargs)
        self.set_vexpand(False)
        self.set_column_homogeneous(True)
        self.get_style_context().add_class('transparencible')
        self.title = Gtk.Label(label=title)
        self.title.get_style_context().add_class('title')
        self.title.set_hexpand(True)
        self.statistics = list()
        self.separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        if count is not None:
            self.set_statistics_count(count)

    def set_statistics_count(self, count):
        if count > len(self.statistics):
            for i in range(len(self.statistics), count):
                self.insert_column(i)
                stat = self.Statistics(value='n/a')
                self.statistics.append(stat)
                self.attach(stat.title_label, i, 1, 1, 1)
                self.attach(stat.value_label, i, 2, 1, 1)
            self.attach(self.title, 0, 0, count, 1)
            self.attach(self.separator, 0, 3, count, 1)
        elif count < len(self.statistics):
            for i in range(len(self.statistics)-1, count-1, -1):
                self.remove_column(i)
                del self.statistics[i] 
