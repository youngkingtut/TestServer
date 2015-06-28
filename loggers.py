__author__ = 'tristan'
import logging

# Global logging handlers
console_formatter = logging.Formatter('%(module)ls(%(asctime)s)- %(message)s', datefmt='%H:%M:%S')
file_formatter = logging.Formatter('%(asctime)s- %(message)s', datefmt='%Y%m%d(%H:%M:%S)')

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(console_formatter)

server_log = logging.getLogger('Server_Log')
server_log.setLevel(logging.DEBUG)
server_log.addHandler(console)

test_log = logging.getLogger('Test_log')
test_log.setLevel(logging.DEBUG)
test_log.addHandler(console)


