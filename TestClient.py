import asyncore
import asynchat
import socket
import thread
import time
from Config import Config


class TestClient(asynchat.async_chat):
    def __init__(self, host, port, timeout=20, chuck_size=10):
        asynchat.async_chat.__init__(self)
        self.set_terminator(Config.TERMINATOR)
        self.data = None
        self.timeout = timeout
        self.chuck_size = 10
        self.client_id = None
        self.threads = []

    def connect(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))

    def handle_connect(self):
        self.send(Config.API_CLIENT_START + Config.TERMINATOR)
        self.send(Config.API_ID_REQUEST + Config.TERMINATOR)

    def handle_close(self):
        self.send(Config.API_CLOSE + Config.TERMINATOR)
        self.close_threads()
        self.close()

    def handle_error(self):
        root_log.debug('uncaught exception')

    def collect_incoming_data(self, data):
        self.data = data

    def found_terminator(self):
        server_message = self.data.split(Config.API_DELIMETER)
        if server_message[0] == Config.API_ID_REQUEST:
            self.client_id = int(server_message[1])
            self.run()

    def run(self):
        try:
            heartbeat = thread.start_new_thread(self.send_heartbeat, ())
            self.threads.append(heartbeat)
        except (KeyboardInterrupt, SystemExit):
            self.close_threads()

    def send_heartbeat(self):
        while True:
            self.send(Config.API_HEARTBEAT + Config.TERMINATOR)
            time.sleep(5)
            self.handle_close()
