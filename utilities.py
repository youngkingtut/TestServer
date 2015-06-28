__author__ = 'Tristan Storz'
import logging
import os
import subprocess


LINUX_STAT_LOCATION = '/proc/stat'
LINUX_PROCESS_STAT_LOCATION = '/proc/%d/stat'

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(module)ls(%(asctime)s)- %(message)s', datefmt='%H:%M:%S'))

file_formatter = logging.Formatter('%(asctime)s- %(message)s', datefmt='%Y%m%d(%H:%M:%S)')

root_log = logging.getLogger("Root_log")
root_log.setLevel(logging.DEBUG)
root_log.addHandler(console)


def get_total_cpu_clock_cycles():
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
    try:
        cpu_info = subprocess.check_output('lscpu')
        return cpu_info
    except OSError:
        return None


def verify_dir_exists(directory):
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except os.error as e:
            print 'could not create directory {}'.format(directory)
            raise e
