import asyncore
import asynchat
import socket
from Config import Config
from log import root_log


class ClientAPI(asynchat.async_chat):
    def __init__(self, sock, client_id):
        asynchat.async_chat.__init__(self, sock=sock)
        self.set_terminator(Config.TERMINATOR)
        self.client_id = str(client_id)
        self.data = None
        self.data_handler = {Config.API_CLIENT_START: self.log_client_start,
                             Config.API_ID_REQUEST: self.send_client_id,
                             Config.API_CLIENT_END: self.handle_close,
                             Config.API_HEARTBEAT: self.log_heartbeat}

    def handle_close(self):
        root_log.debug('Client ' + self.client_id + ': stop')
        self.close()

    def handle_error(self):
        root_log.debug('uncaught exception')

    def collect_incoming_data(self, data):
        self.data = data

    def found_terminator(self):
        self.data_handler[self.data]()

    def send_client_id(self):
        root_log.debug('Client ' + self.client_id + ': sending unique id')
        self.send(Config.API_ID_REQUEST + Config.API_DELIMETER +
                  self.client_id + Config.TERMINATOR)

    def log_client_start(self):
        root_log.debug('Client ' + self.client_id + ': start')

    def log_heartbeat(self):
        root_log.debug('Client ' + self.client_id + ': heartbeat')


class TestServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.address = self.socket.getsockname()
        self.client_guid = 0
        self.listen(5)
        self.connection_made = False

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            root_log.debug('Incoming connection from %s' % repr(addr))
            ClientAPI(sock, self.get_guid())
            self.connection_made = True

    def check_for_exit(self):
        if len(asyncore.socket_map) > 1:
            return True
        elif not self.connection_made:
            return True
        else:
            root_log.debug('No Clients Remain')
            return False

    def get_guid(self):
        self.client_guid = self.client_guid + 1
        return self.client_guid

    def run(self):
        root_log.debug('Starting session')
        while self.check_for_exit():
            asyncore.loop(timeout=Config.LOOP_TIMEOUT,
                          count=Config.LOOP_COUNT)

    def end(self):
        root_log.debug('Ending the session, print out metrics here')
        self.close()
