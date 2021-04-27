#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 14:42:39 2021

code copied from here: 
    https://www.thepythoncode.com/article/get-hardware-system-information-python


@author: nlourie
"""

import psutil
import platform
from datetime import datetime
import json
import numpy as np

def get_size(Bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    
    scale = dict({0 : "",
                  3 : "K",
                  6 : "M",
                  9 : "G",
                  12 : "T",
                  15 : "P"
                  })
    
    for unit in scale.keys():
        if Bytes < factor:
            letter_unit = scale[unit]
            label = f'{letter_unit}{suffix}'
            size = np.round(Bytes,2)
            #return f"{Bytes:.2f} {units}"
            return size, unit, label
        Bytes /= factor
"""
# let's print CPU information
print("="*40, "CPU Info", "="*40)
# number of cores
print("Physical cores:", psutil.cpu_count(logical=False))
print("Total cores:", psutil.cpu_count(logical=True))
# CPU frequencies
cpufreq = psutil.cpu_freq()
print(f"Max Frequency: {cpufreq.max:.2f}Mhz")
print(f"Min Frequency: {cpufreq.min:.2f}Mhz")
print(f"Current Frequency: {cpufreq.current:.2f}Mhz")
# CPU usage
print("CPU Usage Per Core:")
for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
    print(f"Core {i}: {percentage}%")
print(f"Total CPU Usage: {psutil.cpu_percent()}%")


# Memory Information
print("="*40, "Memory Information", "="*40)
# get the memory details
svmem = psutil.virtual_memory()
print(f"Total: {get_size(svmem.total)}")
print(f"Available: {get_size(svmem.available)}")
print(f"Used: {get_size(svmem.used)}")
print(f"Percentage: {svmem.percent}%")
print("="*20, "SWAP", "="*20)
# get the swap memory details (if exists)
swap = psutil.swap_memory()
print(f"Total: {get_size(swap.total)}")
print(f"Free: {get_size(swap.free)}")
print(f"Used: {get_size(swap.used)}")
print(f"Percentage: {swap.percent}%")


# Disk Information
print("="*40, "Disk Information", "="*40)
print("Partitions and Usage:")
# get all disk partitions
partitions = psutil.disk_partitions()
for partition in partitions:
    print(f"=== Device: {partition.device} ===")
    print(f"  Mountpoint: {partition.mountpoint}")
    print(f"  File system type: {partition.fstype}")
    try:
        partition_usage = psutil.disk_usage(partition.mountpoint)
    except PermissionError:
        # this can be catched due to the disk that
        # isn't ready
        continue
    print(f"  Total Size: {get_size(partition_usage.total)}")
    print(f"  Used: {get_size(partition_usage.used)}")
    print(f"  Free: {get_size(partition_usage.free)}")
    print(f"  Percentage: {partition_usage.percent}%")
# get IO statistics since boot
disk_io = psutil.disk_io_counters()
print(f"Total read: {get_size(disk_io.read_bytes)}")
print(f"Total write: {get_size(disk_io.write_bytes)}")
"""
stats = dict()
#%%
# RAM
svmem = psutil.virtual_memory()
ram_total, ram_total_scale, ram_total_label = get_size(svmem.total)
ram_avail, ram_avail_scale, ram_avail_label = get_size(svmem.available)
ram_used, ram_used_scale, ram_used_label = get_size(svmem.used)
ram_pct_used = svmem.percent
stats.update({'ram_total' : ram_total})
stats.update({'ram_total_scale' : ram_total_scale})
stats.update({'ram_avail' : ram_avail})
stats.update({'ram_avail_scale' : ram_avail_scale})
stats.update({'ram_used' : ram_used})
stats.update({'ram_used_scale' : ram_used_scale})
stats.update({'ram_pct_used' : ram_pct_used})
#%%
# CPU
cpu_n_phys_cores = psutil.cpu_count(logical=False)
cpu_n_total_cores = psutil.cpu_count(logical=True)
stats.update({'cpu_n_phys_cores' : cpu_n_phys_cores})
stats.update({'cpu_n_total_cores' : cpu_n_total_cores})
#%%
for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval = 0)):
    #print(f"Core {i}: {percentage}%")
    stats.update({f'cpu_core_{i}' : percentage})







print(json.dumps(stats, indent = 2))



