__author__ = 'Tristan Storz'
import asyncore
import asynchat
import socket
import multiprocessing
import argparse
import sys
import utilities
import logging
import time
from config import Config
from loggers import test_log, file_formatter
from filewritetest import FileWriteTest
""" Test Client for running tests and sending test information to server

The TestClient uses asynchat to connect with a TestServer on a host:port.
When a connection is successful, TestClient will proceed to send system
information and request a system id and test from the server. The TestClient
will then proceed to run and send test information to the server.

Optionally, TestClient can be initialized with a test. In that case, no
test will be requested from the server.

Example:
    # Start TestClient on localhost:1123
        client = TestClient('localhost', 1123)
        try:
            client.connect_to_host()
        finally:
            client.close()

    # Start client with FileWriteTest
        from filewritetest import FileWriteTest

        client = TestClient('localhost', 1123 FileWriteTest(1, 2))
        try:
            client.connect_to_host()
        finally:
            client.close()

Note: The only supported test is 'file write' Adding more tests requires
      adding the test class to TestClient.test_handler. Additional tests
      must be classes with the following methods, run(), get_test_name(),
      and get_test_args(). Also, the following parameters, message_queue
      (multiprocessing.Queue()) and end_of_test (multiprocessing.Event()).
"""


class TestClient(asynchat.async_chat):
    """ Init log and params, call connect_to_host() after creating instance to run.

        Args:
            host (str): test server address.
            port (int): test server port.
            run_test (Class): test to run when connected to the server.
    """
    def __init__(self, host, port, run_test=None):
        asynchat.async_chat.__init__(self)
        self.set_terminator(Config.TERMINATOR)
        self.host = host
        self.port = port
        self.run_test = run_test
        self.server_header = None
        self.server_message = []
        self.client_id = None
        self.message_handler = {Config.API_TEST_REQUEST: self.set_run_test,
                                Config.API_ID_REQUEST: self.set_client_id}
        self.test_handler = {Config.TEST_FILE_WRITE_NAME: FileWriteTest}
        self.setup_log_file()

    @staticmethod
    def setup_log_file():
        utilities.verify_dir_exists(Config.TEST_LOG_DIR)
        test_log_file = logging.FileHandler(Config.TEST_LOG_DIR + time.strftime('%Y%m%d_%H%M%S'), 'a')
        test_log_file.setLevel(logging.DEBUG)
        test_log_file.setFormatter(file_formatter)
        test_log.addHandler(test_log_file)

    def connect_to_host(self):
        """ Create/bind socket, start asyncore loop until connection ends """
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        asyncore.loop(timeout=Config.LOOP_TIMEOUT)

    def handle_connect(self):
        """ Sends start and system info. Requests id. Requests test if not
            initialized with test.
        """
        self.send(Config.API_CLIENT_START + Config.TERMINATOR)
        self.send_system_info()
        self.send(Config.API_ID_REQUEST + Config.TERMINATOR)
        if not self.run_test:
            self.send(Config.API_TEST_REQUEST + Config.TERMINATOR)
        else:
            self.run()

    def handle_error(self):
        typ, val, traceback = sys.exc_info()
        test_log.debug('Connection closed: ' + str(val))
        self.close()

    def handle_close(self):
        test_log.debug('Socket closed')
        self.shutdown(socket.SHUT_RDWR)
        self.close()

    def collect_incoming_data(self, data):
        """ Saves data to server_header and server_message.
            Args:
                data (str): information from server.
        """
        del self.server_message[:]
        message = data.split(Config.API_DELIMITER)
        self.server_header = message[0]
        for msg in message[1:]:
            self.server_message.append(msg)

    def found_terminator(self):
        """ Calls api method from message_handler dict. """
        self.message_handler.get(self.server_header, self.log_unknown_server_command)()

    def set_client_id(self):
        """ Sets client_id to the return packet from server if present. """
        if len(self.server_message):
            self.client_id = self.server_message[0]
            test_log.debug('id received: {}'.format(self.client_id))
        else:
            test_log.debug('Id request returned no information')
            self.handle_close()

    def set_run_test(self):
        """ Sets run_test to the return packet from server if present """
        if len(self.server_message):
            test_log.debug('running test from server: {} {}'.format(self.server_message[0], self.server_message[1]))
            function_args = [int(arg) for arg in self.server_message[1].split(',')]
            self.run_test = self.test_handler[self.server_message[0]](*function_args)
            self.run()
        else:
            test_log.debug('no test found, ending session')
            self.handle_close()

    def send_system_info(self):
        self.send(Config.API_SYSTEM_INFO + Config.API_DELIMITER + utilities.get_cpu_info() + Config.TERMINATOR)

    def log_unknown_server_command(self):
        test_log.debug('Unknown command, ending session' + self.server_header)
        self.handle_close()

    def run(self):
        """ Sends test information for run_test to server. Then forks to run test in child.
            Continues to log any information from run_test.message_queue until
            run_test.end_of_test is set by the test. Ends the connection gracefully.
        """
        if self.run_test:
            test_log.debug('Starting test')
            self.send(Config.API_RUNNING_TEST + Config.API_DELIMITER + self.run_test.get_test_name() +
                      Config.API_DELIMITER + self.run_test.get_test_args() + Config.TERMINATOR)
            test_process = multiprocessing.Process(target=self.run_test.run)
            test_process.start()

            while not self.run_test.end_of_test.is_set():
                if not self.run_test.message_queue.empty():
                    self.send(self.run_test.message_queue.get())

            test_log.debug('Test ended')
            self.end()
        else:
            test_log.debug('No running test')
            self.handle_close()

    def end(self):
        test_log.debug('Ending session')
        self.send(Config.API_CLIENT_END + Config.TERMINATOR)
        self.handle_close()


if __name__ == '__main__':
    # Spin up a client to connect to the test server. Input arguments are for the file write test,
    # more can be added to support additional tests.
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', dest='timeout', default=10, type=int,
                        help='runtime for client')
    parser.add_argument('-f', '--filesize', dest='file_size', default=10, type=int,
                        help='chunk size of test files')
    cmd_input = parser.parse_args()

    if len(sys.argv) > 1:
        test_log.debug('custom test {}'.format(cmd_input))
        client = TestClient(Config.HOST, Config.PORT, FileWriteTest(cmd_input.timeout, cmd_input.file_size))
    else:
        client = TestClient(Config.HOST, Config.PORT)

    try:
        client.connect_to_host()
    except KeyboardInterrupt:
        test_log.debug('Ended via keyboard interrupt')
    except Exception as e:
        test_log.debug('Faulted during execution.')
        raise e
    finally:
        client.close()
