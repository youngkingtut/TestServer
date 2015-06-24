import asyncore
import asynchat
import socket
from log import root_log


class ClientAPI(asynchat.async_chat):
    def __init__(self, sock, client_id=None):
        asynchat.async_chat.__init__(self, sock=sock)
        self.set_terminator('\n')
        self.client_id = client_id

    def collect_incoming_data(self, data):
        print data

    def found_terminator(self):
        self.send('oh infinite loop\n')

    def handle_close(self):
        root_log.debug('Client has left')
        self.close()


class TestServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.address = self.socket.getsockname()
        self.listen(5)
        self.connection_made = False

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, address = pair
            root_log.debug('Incoming connection from %s' % repr(address))
            ClientAPI(sock)
            self.connection_made = True

    def check_for_exit(self):
        if len(asyncore.socket_map) > 1:
            return True
        elif not self.connection_made:
            return True
        else:
            return False

    def run(self):
        root_log.debug('Starting session')
        while self.check_for_exit():
            asyncore.loop(timeout=0.1, count=1)

    def end(self):
        root_log.debug('Ending the session, print out metrics here')
        self.close()
