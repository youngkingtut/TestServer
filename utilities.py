__author__ = 'Tristan Storz'
import os
import subprocess
from config import Config

LINUX_MEM_INFO_LOCATION = '/proc/meminfo'
LINUX_STAT_LOCATION = '/proc/stat'
LINUX_PROCESS_STAT_LOCATION = '/proc/%d/stat'


def get_total_cpu_clock_cycles():
    """ Returns the total cpu cycles from /proc/stat """
    try:
        with open(LINUX_STAT_LOCATION, 'r') as f:
            cpu_entries = f.readline().split(' ')
    except IOError:
        return None

    cpu_cycles = 0
    for entry in cpu_entries:
        try:
            cpu_cycles += int(entry)
        except ValueError:
            pass
    return cpu_cycles


def get_cpu_clock_cycles_of_pid(pid):
    """ Returns the total cpu cycles for pid from /proc/[pid]/stat """
    try:
        with open(LINUX_PROCESS_STAT_LOCATION % pid, 'r') as f:
            pid_entries = f.read().split(' ')
    except IOError:
        return None

    pid_cycles = 0
    if len(pid_entries) > 14:
        pid_cycles = int(pid_entries[13]) + int(pid_entries[14])
    return pid_cycles


def get_cpu_info():
    """ Returns all cpu from lscpu command as a string """
    try:
        cpu_info = subprocess.check_output('lscpu')
        return cpu_info
    except OSError:
        return None


def get_total_memory():
    """ Returns the total memory for system from /proc/meminfo """
    try:
        with open(LINUX_MEM_INFO_LOCATION, 'r') as f:
            mem_entries = f.readline().split(' ')
    except IOError:
        return None

    memory = 0
    for entry in mem_entries:
        try:
            memory += int(entry)
        except ValueError:
            pass
    return memory * Config.BYTES_PER_KILOBYTE


def get_memory_of_pid(pid):
    """ Returns the total virtual memory for pid from /proc/[pid]/stat """
    try:
        with open(LINUX_PROCESS_STAT_LOCATION % pid, 'r') as f:
            pid_entries = f.read().split(' ')
    except IOError:
        return None

    pid_mem = 0
    if len(pid_entries) > 23:
        pid_mem = int(pid_entries[22])
    return pid_mem


def verify_dir_exists(directory):
    """ Creates directory if path does not exist """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except os.error as e:
            print 'could not create directory {}'.format(directory)
            raise e
