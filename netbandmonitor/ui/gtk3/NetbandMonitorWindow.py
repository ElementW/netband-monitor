import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk, GLib
import threading, time, math, cairo, inspect, os.path
from collections import deque

from . import LineChart, StatLine
from ...settings import Settings

class NetbandMonitorWindow(Gtk.Window):
    __gtype_name__ = 'NetbandMonitorWindow'

    class ChartUpdater(threading.Thread):
        def __init__(self, window, net_monitor, *args, **kwargs):
            super(NetbandMonitorWindow.ChartUpdater, self).__init__(*args, **kwargs)
            self.event = threading.Event()
            self.window = window
            self.max_up = -1
            self.max_down = -1
            self.total_up = 0
            self.total_down = 0
            self.averages_update_interval = 2
            self.last_averages_update = 0

        def set_interval(self, interval):
            self.interval = interval

        def format_value(self, bytes):
            mult = 8 if self.window.use_bits else 1
            unit = 'b' if self.window.use_bits else 'B'
            unit_prefix_base = 1024 if self.window.use_binary_prefix else 1000
            unit_prefix_names = ["", "Ki", "Mi", "Gi"] if self.window.use_binary_prefix else ["", "k", "m", "g"]
            n_fold = 0 if bytes == 0 else min(int(math.log(bytes * mult, unit_prefix_base)), 3)
            bytes_scaled = float(bytes) / (unit_prefix_base ** n_fold)
            return "{:4.1f}{}{}".format(bytes_scaled, unit_prefix_names[n_fold], unit)

        def run(self):
            self.running_since = time.time()
            self.last_update = self.running_since
            while True:
                self.event.wait(self.interval)
                if self.event.is_set():
                    self.event.clear()
                    break
                if len(self.window.chart.lines) != 2:
                    self.window.chart.lines.append(LineChart.Line([1, 0, 0, 1]))
                    self.window.chart.lines[0].data.extend([0 for x in range(10)])
                    self.window.chart.lines.append(LineChart.Line())
                    self.window.chart.lines[1].data.extend([0 for x in range(10)])
                now = time.time()
                delta_time = now - self.last_update
                (up, down, up_per_sec, down_per_sec, record_up_per_sec, record_down_per_sec) = (0, 0, 0, 0, 0, 0)
                self.window.net_monitor.interface_stats_delta_lock.acquire()
                for iface in self.window.net_monitor.interface_delta_per_sec:
                    ifacestats = self.window.net_monitor.interface_delta_per_sec[iface]
                    n = 0
                    for stat in ifacestats:
                        if stat.time > self.last_update:
                            up_per_sec += stat.count.tx
                            down_per_sec += stat.count.rx
                            n += 1
                    if n > 0:
                      up_per_sec /= n
                      down_per_sec /= n
                    ifacestats = self.window.net_monitor.interface_delta[iface]
                    for stat in ifacestats:
                        if stat.time > self.last_update:
                            up += stat.count.tx
                            down += stat.count.rx
                    record = self.window.net_monitor.interface_delta_per_sec_records[iface]
                    if record.rx > record_down_per_sec:
                        record_down_per_sec = record.rx
                    if record.tx > record_up_per_sec:
                        record_up_per_sec = record.tx
                self.window.net_monitor.interface_stats_delta_lock.release()
                # Total stats
                # - Download
                if down > 0:
                    self.total_down += down
                    self.window.stat_total.statistics[0].value = self.format_value(self.total_down)
                # - Upload
                if up > 0:
                    self.total_up = up
                    self.window.stat_total.statistics[1].value = self.format_value(self.total_up)

                # Instant stats
                # - Download
                down_formatted = self.format_value(down_per_sec) + "/s"
                # - - Max
                if down_per_sec > self.max_down:
                    self.max_down = down_per_sec
                    self.window.stat_download.statistics[2].value = down_formatted
                # - - Current
                self.window.stat_download.statistics[0].value = down_formatted
                # - Upload
                up_formatted = self.format_value(up_per_sec) + "/s"
                # - - Max
                if up_per_sec > self.max_up:
                    self.max_up = up_per_sec
                    self.window.stat_upload.statistics[2].value = up_formatted
                # - - Current
                self.window.stat_upload.statistics[0].value = up_formatted

                # Averages
                if now - self.last_averages_update > self.averages_update_interval:
                    self.last_averages_update = now
                    self.window.stat_download.statistics[1].value = \
                        self.format_value(self.total_down / (now - self.running_since)) + "/s"
                    self.window.stat_upload.statistics[1].value = \
                        self.format_value(self.total_up / (now - self.running_since)) + "/s"

                # Chart
                viz_maxdown = self.window.settings.status_icon_max_download_per_sec or \
                              self.window.settings.bandwidth_max_download_per_sec or \
                              record_down_per_sec or 1
                viz_maxup = self.window.settings.status_icon_max_upload_per_sec or \
                            self.window.settings.bandwidth_max_upload_per_sec or \
                            record_up_per_sec or 1
                viz_max = max(viz_maxup, viz_maxdown)
                self.window.chart.lines[0].data.append(down)
                self.window.chart.lines[1].data.append(up)
                self.window.chart.data_max = viz_max
                if len(self.window.chart.lines[0].data) > 10:
                    self.window.chart.lines[0].data.popleft()
                    self.window.chart.lines[1].data.popleft()
                self.window.chart.queue_draw()

                # Status icon (tray)
                if self.window.status_icon_surface is None:
                    self.window.status_icon_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 22, 22)
                if self.window.status_icon_context is None:
                    self.window.status_icon_context = cairo.Context(self.window.status_icon_surface)
                    self.window.status_icon_context.identity_matrix()
                    self.window.status_icon_context.set_line_width(0)
                ctx = self.window.status_icon_context
                ctx.set_source_rgb(*self.window.settings.status_icon_bgcolor)
                ctx.rectangle(0, 0, 22, 22)
                ctx.fill()
                ctx.set_source_rgb(*self.window.settings.status_icon_download_color)
                h = (down_per_sec / float(viz_max)) * 20
                ctx.rectangle(2, 1+(20-h), 9, h)
                ctx.fill()
                ctx.set_source_rgb(*self.window.settings.status_icon_upload_color)
                h = (up_per_sec / float(viz_max)) * 20
                ctx.rectangle(13, 1+(20-h), 9, h)
                ctx.fill()
                self.window.status_icon.set_from_pixbuf(Gdk.pixbuf_get_from_surface(
                    self.window.status_icon_surface, 0, 0, 22, 22))

                self.last_update = now
                

        def stop(self):
            self.event.set()

    def __init__(self, net_monitor, *args, **kwargs):
        super(NetbandMonitorWindow, self).__init__(*args, **kwargs)
        self.set_size_request(240, 40)
        self.settings = Settings()
        self.net_monitor = net_monitor
        self.screen = self.get_screen()
        self.display = self.screen.get_display()
        visual = self.screen.get_rgba_visual()
        self.transparency = False
        if visual and self.screen.is_composited():
            self.set_visual(visual)
            self.transparency = True
        else:
            sys.stderr.write('System doesn\'t support transparency\n')
            self.set_visual(self.screen.get_system_visual())
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b'''
        .transparencible-win decoration {
            transition: box-shadow .5s linear;
        }
        .transparencible-win.transparent decoration {
            box-shadow: 0 3px 9px 1px rgba(0, 0, 0, 0), 0 0 0 1px rgba(255, 0, 0, 0);
        }
        .transparencible-win .titlebar, .transparencible {
            transition: opacity .5s linear;
        }
        .transparencible-win.transparent .titlebar, .transparent .transparencible {
            opacity: 0;
        }
        .transparencible-win.background {
            transition: background .5s linear;
        }
        .transparencible-win.background.transparent {
            background: transparent;
        }
        .transparencible-win.transparent .titlebar {
            opacity: 0;
        }
        .window-frame {
        box-shadow: none;
        margin: 0;
        }
        decoration {  }
        ''')
        self.context = self.get_style_context()
        self.context.add_provider_for_screen(self.screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.context.add_class('transparencible-win')

        self.vbox = Gtk.VBox()

        self.stat_download = StatLine("Download", 3)
        self.vbox.pack_start(self.stat_download, False, False, 0)
        self.stat_upload = StatLine("Upload", 3)
        self.vbox.pack_start(self.stat_upload, False, False, 0)
        for s in [self.stat_download.statistics, self.stat_upload.statistics]:
            s[0].title = "Current"
            s[1].title = "Average"
            s[2].title = "Max"

        self.stat_today = StatLine("Today", 2)
        self.vbox.pack_start(self.stat_today, False, False, 0)
        self.stat_total = StatLine("Total", 2)
        self.vbox.pack_start(self.stat_total, False, False, 0)
        for s in [self.stat_today.statistics, self.stat_total.statistics]:
            s[0].title = "Download"
            s[1].title = "Upload"

        self.chart = LineChart()
        self.vbox.pack_start(self.chart, True, True, 0)

        self.add(self.vbox)

        icontheme = Gtk.IconTheme.get_default()
        icontheme.append_search_path(os.path.join(os.path.dirname(inspect.stack()[0][1]), 'icons'))

        self.bar = Gtk.HeaderBar(title="Netband Monitor")
        self.bar.set_has_subtitle(False)
        #self.bar.set_subtitle("Monitoring...")
        self.bar.set_show_close_button(True)

        menubutton = Gtk.ToggleButton()
        menubutton.set_image(Gtk.Image.new_from_icon_name('emblem-system-symbolic', Gtk.IconSize.SMALL_TOOLBAR))
        menubutton.connect('toggled', lambda btn: self.popover.show_all() if btn.get_active() else self.popover.hide())
        self.popover = Gtk.Popover()
        self.popover.connect('closed', lambda popover: menubutton.set_active(False))
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.popover.set_relative_to(menubutton)
        box = Gtk.VBox()
        box.set_spacing(5)
        unitbuttonbox = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
        unitbuttonbox.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        self.bytes_button = Gtk.ToggleButton(label='')
        self.bits_button = Gtk.ToggleButton(label='')
        def bits_toggle(btn):
            if btn.get_active():
                self.use_bits = (btn == self.bits_button)
        for b in [self.bytes_button, self.bits_button]:
            b.get_child().set_halign(Gtk.Align.FILL)
            b.get_child().set_justify(Gtk.Justification.CENTER)
            b.connect('toggled', bits_toggle)
            unitbuttonbox.add(b)
        unitbuttonbox.set_property('margin', 5)
        unitbuttonbox.set_property('margin-bottom', 0)
        box.add(unitbuttonbox)
        self.binaryprefix_checkbutton = Gtk.CheckButton('')
        def binary_toggle(btn):
            self.use_binary_prefix = btn.get_active()
        self.binaryprefix_checkbutton.connect('toggled', binary_toggle)
        self.use_binary_prefix = True
        self.use_bits = False
        box.add(self.binaryprefix_checkbutton)

        box.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        box.add(Gtk.Label("Refresh rate"))
        refresh_rate_grid = Gtk.Grid()
        self.refresh_rate_label = Gtk.Label()
        self.refresh_rate_label.set_label('5000ms')
        self.refresh_rate_label.set_size_request(self.refresh_rate_label.get_allocation().width, -1)
        self.refresh_rate_scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL,
            Gtk.Adjustment.new(100, 100, 5000, 50, 50, 0))
        self.refresh_rate_scale.set_draw_value(False)
        self.refresh_rate_scale.set_has_origin(False)
        self.refresh_rate_scale.set_round_digits(0)
        self.refresh_rate_scale.set_hexpand(True)
        self.refresh_rate_scale.connect('value-changed', lambda scale:
            self.refresh_rate_label.set_label(str(int(scale.get_value())) + "ms"))
        self.refresh_rate_scale.connect('value-changed', lambda scale:
            self.chart_updater.set_interval(float(int(scale.get_value()))/1000))
        refresh_rate_grid.attach(self.refresh_rate_scale, 0, 0, 1, 1)
        refresh_rate_grid.attach(self.refresh_rate_label, 1, 0, 1, 1)
        
        box.add(refresh_rate_grid)
        
        checkbutton = Gtk.CheckButton("cc")
        box.add(checkbutton)
        self.popover.add(box)
        #self.popover.set_size_request(40, 40)
        self.bar.pack_end(menubutton)

        pinbutton = Gtk.ToggleButton()
        pinbutton.set_image(Gtk.Image.new_from_icon_name('pin-window-symbolic', Gtk.IconSize.SMALL_TOOLBAR))
        self.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        pinbutton.connect('toggled', lambda btn: self.set_keep_above(btn.get_active()))
        self.bar.pack_end(pinbutton)

        self.set_titlebar(self.bar)

        self.status_icon = Gtk.StatusIcon()
        self.status_icon_surface = None
        self.status_icon_context = None

        self.chart_updater = self.ChartUpdater(self, self.net_monitor)
        self.chart_updater.set_interval(0.1)
        self.chart_updater.start()

        self.connect('delete-event', lambda x, y: self.chart_updater.stop())

    @property
    def use_binary_prefix(self):
        return self.binaryprefix_checkbutton.get_active()

    @use_binary_prefix.setter
    def use_binary_prefix(self, use):
        self.binaryprefix_checkbutton.set_active(use)
        self.bytes_button.get_child().set_label("KiB, MiB\n(bytes)" if use else "kB, MB\n(bytes)")
        self.bits_button.get_child().set_label("Kib, Mib\n(bits)" if use else "kb, Mb\n(bits)")

    @property
    def use_bits(self):
        return self.bits_button.get_active()

    @use_bits.setter
    def use_bits(self, use):
        self.bits_button.set_active(use)
        self.bytes_button.set_active(not use)
        self.binaryprefix_checkbutton.set_label("Binary prefix (" + ("Kib, Mib)" if use else "KiB, MiB)"))

    @property
    def transparent(self):
        return self.context.has_class('transparent')

    @transparent.setter
    def transparent(self, value):
        if value:
            self.context.add_class('transparent')
        else:
            self.context.remove_class('transparent')
