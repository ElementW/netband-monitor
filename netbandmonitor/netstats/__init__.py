import os
from .NetworkStatisticsMonitorThread import NetworkStatisticsMonitorThread
from .constants import *

def list_network_interfaces():
    interfaces = []
    for iface in os.listdir(SYS_CLASS_NET):
        if os.path.isdir(SYS_CLASS_NET + iface + '/device'):
            interfaces.append(iface)
    return interfaces
