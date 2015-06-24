import logging

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(module)ls(%(asctime)s)- %(message)s', datefmt='%H:%M:%S'))

root_log = logging.getLogger("Root_log")
root_log.setLevel(logging.DEBUG)
root_log.addHandler(console)
