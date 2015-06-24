import asyncore
import asynchat
import socket


class TestClient(asynchat.async_chat):
    def __init__(self, host, port):
        asynchat.async_chat.__init__(self)
        self.message = 'hello'
        self.received_data = []
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_terminator('\n')
        self.connect((host, port))

    def handle_connect(self):
        self.send('REQUESTING ID\n')

    def collect_incoming_data(self, data):
        print data

    def found_terminator(self):
        self.close()

# TestClient('localhost', 1115)
# asyncore.loop(timeout=0.1)
