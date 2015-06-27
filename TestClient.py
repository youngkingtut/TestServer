from __future__ import division
from ast import literal_eval
import asyncore
import asynchat
import socket
import multiprocessing
import time
import argparse
import sys
import threading
from Config import Config
from log import root_log
from FileWriteTest import FileWriteTest


class TestClient(asynchat.async_chat):
    def __init__(self, host, port, run_test=None):
        asynchat.async_chat.__init__(self)
        self.set_terminator(Config.TERMINATOR)
        self.server_header = None
        self.server_message = []
        self.client_id = None
        self.run_test = run_test
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.message_handler = {Config.API_TEST_REQUEST: self.set_run_test,
                                Config.API_ID_REQUEST: self.set_client_id}
        self.test_handler = {Config.TEST_FILE_WRITE: FileWriteTest}

    def handle_connect(self):
        self.send(Config.API_CLIENT_START + Config.TERMINATOR)
        self.send(Config.API_ID_REQUEST + Config.TERMINATOR)
        if not self.run_test:
            self.send(Config.API_TEST_REQUEST + Config.TERMINATOR)
        else:
            self.run()

    def handle_error(self):
        typ, val, traceback = sys.exc_info()
        root_log.debug('Connection closed: ' + str(val))
        self.close()

    def handle_close(self):
        root_log.debug('Socket closed')
        self.close()

    def collect_incoming_data(self, data):
        del self.server_message[:]
        message = data.split(Config.API_DELIMITER)
        self.server_header = message[0]
        for msg in message[1:]:
            self.server_message.append(msg)

    def found_terminator(self):
        self.message_handler.get(self.server_header, self.log_unknown_server_command)()

    def set_client_id(self):
        if len(self.server_message):
            self.client_id = self.server_message[0]
        else:
            root_log.debug('Id request returned no information')
            self.close()

    def set_run_test(self):
        if len(self.server_message):
            self.run_test = self.test_handler[self.server_message[0]](**literal_eval(self.server_message[1]))
            self.run()
        else:
            root_log.debug('no test found, ending session')
            self.close()

    def log_unknown_server_command(self):
        root_log.debug('Unknown command, ending session' + self.server_header)
        self.close()

    def run(self):
        root_log.debug('Starting test')
        message_queue = self.run_test.message_queue
        test_process = threading.Thread(target=self.run_test.run)
        test_process.start()

        while test_process.is_alive():
            if not message_queue.empty():
                self.send(message_queue.get())

        root_log.debug('Test ended')
        self.end()

    def end(self):
        root_log.debug('Ending session')
        self.send(Config.API_CLIENT_END + Config.TERMINATOR)
        self.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', dest='timeout', default=10, type=int,
                        help='runtime for client')
    parser.add_argument('-c', '--chunk_size', dest='chunk_size', default=10, type=int,
                        help='chunk size of test files')
    cmd_input = parser.parse_args()

    client = TestClient(Config.HOST, Config.PORT)
    try:
        asyncore.loop(timeout=Config.LOOP_TIMEOUT)
    except KeyboardInterrupt:
        root_log.debug('Ended via keyboard interrupt')
    except Exception as e:
        root_log.debug('Faulted during execution.')
        raise e
    finally:
        client.close()
