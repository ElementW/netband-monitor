import threading, os, time
from collections import deque, namedtuple
from .constants import *

ByteCount = namedtuple('ByteCount', ['rx', 'tx'])
TimedByteCount = namedtuple('TimedByteCount', ['time', 'count'])

class NetworkStatisticsMonitorThread(threading.Thread):
    def __init__(self, monitoring_interfaces=[], *args, **kwargs):
        super(NetworkStatisticsMonitorThread, self).__init__(*args, **kwargs)
        self.monitor_interval = 0.1
        self.event = threading.Event()
        self.should_stop = False
        self.monitoring_interfaces = monitoring_interfaces
        self.interface_stats = {}
        self.interface_delta = {}
        self.interface_delta_per_sec = {}
        self.interface_delta_per_sec_records = {}
        self.interface_stats_delta_lock = threading.Lock()

    @staticmethod
    def _read_stat(path):
        with open(path, 'r') as f:
            return int(f.read())

    def run(self):
        last_update = time.time()
        while True:
            self.event.wait(self.monitor_interval)
            if self.event.is_set():
                self.event.clear()
                if self.should_stop:
                    break
            now = time.time()
            inverse_dtime = 1 / (now - last_update)
            for iface in self.monitoring_interfaces:
                iface = SYS_CLASS_NET + iface
                stats_dir = iface + '/statistics'
                rx = self._read_stat(stats_dir + '/rx_bytes')
                tx = self._read_stat(stats_dir + '/tx_bytes')
                if iface not in self.interface_stats:
                    self.interface_stats[iface] = ByteCount(rx, tx)
                if iface not in self.interface_delta:
                    self.interface_delta[iface] = deque()
                if iface not in self.interface_delta_per_sec:
                    self.interface_delta_per_sec[iface] = deque()
                if iface not in self.interface_delta_per_sec_records:
                    self.interface_delta_per_sec_records[iface] = ByteCount(0, 0)
                drx = rx - self.interface_stats[iface].rx
                dtx = tx - self.interface_stats[iface].tx
                (drxps, dtxps) = (drx * inverse_dtime, dtx * inverse_dtime)
                if drx != 0 or dtx != 0:
                    self.interface_stats_delta_lock.acquire()
                    self.interface_delta[iface].append(TimedByteCount(time.time(), ByteCount(drx, dtx)))
                    self.interface_delta_per_sec[iface].append(TimedByteCount(time.time(), ByteCount(drxps, dtxps)))
                    (rrx, rtx) = self.interface_delta_per_sec_records[iface]
                    if drxps > rrx:
                      rrx = drxps
                    if dtxps > rtx:
                      rtx = dtxps
                    self.interface_delta_per_sec_records[iface] = ByteCount(rrx, rtx)
                    self.interface_stats_delta_lock.release()
                self.interface_stats[iface] = ByteCount(rx, tx)
            last_update = now

    def stop(self):
        self.should_stop = True
        self.event.set()
