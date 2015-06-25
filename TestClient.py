import asyncore
import asynchat
import socket
import threading
import time
import argparse
import sys
from Config import Config
from log import root_log


class TestClient(asynchat.async_chat):
    def __init__(self, host, port, timeout=15, chunk_size=10):
        asynchat.async_chat.__init__(self)
        self.set_terminator(Config.TERMINATOR)
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.data = None
        self.client_id = None
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))

    def handle_connect(self):
        self.send(Config.API_CLIENT_START + Config.TERMINATOR)
        self.send(Config.API_ID_REQUEST + Config.TERMINATOR)

    def handle_error(self):
        typ, val, traceback = sys.exc_info()
        root_log.debug('Connection closed: ' + str(val))
        self.handle_close()

    def handle_close(self):
        self.send(Config.API_CLOSE + Config.TERMINATOR)
        self.close()

    def collect_incoming_data(self, data):
        self.data = data

    def found_terminator(self):
        server_message = self.data.split(Config.API_DELIMITER)
        if server_message[0] == Config.API_ID_REQUEST:
            self.client_id = int(server_message[1])
            self.run()

    def run(self):
        heartbeat = threading.Thread(target=self.send_heartbeat, args=(self.timeout,))
        stats = threading.Thread(target=self.gather_stats)
        test = threading.Thread(target=self.chunk_test)
        heartbeat.start()
        stats.start()
        test.start()

        while heartbeat.is_alive():
            pass

        self.close()

    def send_heartbeat(self, timeout):
        end_time = time.time() + timeout
        while time.time() < end_time:
            time.sleep(Config.HEARTBEAT_TIME)
            self.send(Config.API_HEARTBEAT + Config.TERMINATOR)

    def gather_stats(self):
        pass

    def chunk_test(self):
        pass


if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument('-t', '--timeout', dest='timeout', default=15, type=int,
                            help='runtime for client')
        parser.add_argument('-c', '--chunk_size', dest='chunk_size', default=10, type=int,
                            help='chunk size of test files')
        args = parser.parse_args()

        client = TestClient(Config.HOST, Config.PORT, args.timeout, args.chunk_size)
        try:
            asyncore.loop(timeout=Config.LOOP_TIMEOUT)
        except KeyboardInterrupt:
            print 'Ended via keyboard interrupt'
        except Exception as e:
            root_log.debug('Faulted during execution.')
            raise e
        finally:
            client.close()
