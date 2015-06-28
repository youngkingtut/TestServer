__author__ = 'Tristan Storz'
from ast import literal_eval
import asyncore
import asynchat
import socket
import Queue
import sqlite3
import os
import time
import uuid
from config import Config
from utilities import root_log
""" Test Server for logging information from concurrent clients running tests.

The TestServer class utilizes asyncore to monitor a host:port and
then spawns ClientAPI instances when a connection is made. TestServer
logs information from clients to a sqlite3 db in the same directory
(test_server.db). Information about the session is also logged to
server_logs/[datetime].log, where datetime is in YearMonthDay_Time
format

Additionally, TestServer can be initialized with a TestQueue to serve
tests to clients as they connect. This is only for the case where the
TestClient does not have a test to run and will then request one from
TestServer.

Example:
    # Start server on localhost port 1123:
        server = TestServer('localhost', 1123)
        try:
            server.run()
        finally:
            server.end()

    # Start server with test queue:
        import Queue

        tests = Queue.Queue()
        tests.put(Test(Config.TEST_FILE_WRITE, timeout=10, file_size=10))
        server = TestServer('localhost', 1123, tests)
        try:
            server.run()
        finally:
            server.end()

Note: the only supported test is 'file write' Adding more tests will
      require interfacing with TestClient and adding the appropriate
      information to config.py.
"""


class TestServer(asyncore.dispatcher):
    """ Initializes and runs server with asyncore loop via run method

        Args:
            host (str): address to host test server on.
            port (int): address port.
            test_queue (optional[Queue]): tests to run when client
                connects to server.
    """
    def __init__(self, host, port, test_queue=Queue.Queue()):
        asyncore.dispatcher.__init__(self)
        self.host = host
        self.port = port
        self.test_queue = test_queue
        self.db = None
        self.db_cursor = None
        self.connection_made = False

    def handle_accept(self):
        """ Spawn TestClient instance with unique id to handle connected client. """
        pair = self.accept()
        if pair is not None:
            sock, address = pair
            root_log.debug('Connection from %s' % repr(address))
            ClientAPI(sock, uuid.uuid4(), self.test_queue, self.db_cursor)
            self.connection_made = True

    def check_for_exit(self):
        """ Called in run() after every loop of asyncore.

            Return:
                bool: True if clients are present or no client has connected,
                      False otherwise.
         """
        if len(asyncore.socket_map) > 1:
            return True
        elif not self.connection_made:
            return True
        else:
            root_log.debug('No Clients Remain')
            return False

    def initialize_database(self):
        """ Create db with tests table if no db is present """
        if not os.path.isfile(Config.DB_NAME):
            self.db = sqlite3.connect(Config.DB_NAME)
            self.db_cursor = self.db.cursor()
            self.db_cursor.execute('''CREATE TABLE tests
                                    (test_name text,
                                     test_params text,
                                     start_time text,
                                     end_time text,
                                     cpu_info text,
                                     status text);''')
        else:
            self.db = sqlite3.connect(Config.DB_NAME)
            self.db_cursor = self.db.cursor()

    def setup(self):
        """ Create/bind socket and initialize sqlite database.

            Return:
                bool: True if no errors occur with sockets or db.
        """
        root_log.debug('Setting up server')
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((self.host, self.port))
        self.set_reuse_addr()
        self.listen(5)
        self.initialize_database()
        root_log.debug('Setup successful')
        return True

    def run(self):
        """ If setup succeeds, continue asyncore loop until exit status is reached. """
        root_log.debug('Starting session')
        if self.setup():
            while self.check_for_exit():
                asyncore.loop(timeout=Config.LOOP_TIMEOUT, count=Config.LOOP_COUNT)

    def end(self):
        """ Commit statements to database and then close the connection """
        root_log.debug('Ending the session, print out metrics here')
        self.db.commit()
        self.db.close()
        self.close()


class ClientAPI(asynchat.async_chat):
    """ Manage client connections. Log client information and send tests when requested.

        Args:
            sock (int): address to host test server on.
            client_id (uuid.uuid4): unique client identification.
            test_queue (optional[Queue]): tests to run when client requests a test.
            db_cursor (sqlite3.Cursor): object to write out sql commands to server db
    """
    def __init__(self, sock, client_id, test_queue, db_cursor):
        asynchat.async_chat.__init__(self, sock=sock)
        self.set_terminator(Config.TERMINATOR)
        self.client_id = str(client_id)
        self.client_header = None
        self.client_message = []
        self.test = None
        self.test_status = 'NOT RUN'
        self.test_completed = False
        self.start_time = ''
        self.end_time = ''
        self.client_cpu_info = None
        self.test_queue = test_queue
        self.db_cursor = db_cursor
        self.message_handler = {Config.API_CLIENT_START: self.log_client_start,
                                Config.API_ID_REQUEST: self.send_client_id,
                                Config.API_SYSTEM_INFO: self.log_client_system_info,
                                Config.API_RUNNING_TEST: self.log_run_test,
                                Config.API_TEST_REQUEST: self.send_client_test,
                                Config.API_CLIENT_END: self.log_client_end,
                                Config.API_HEARTBEAT: self.log_heartbeat,
                                Config.API_TEST_STATS: self.log_test_stats,
                                Config.API_TEST_INFO: self.log_test_info,
                                Config.API_BAD_TIMEOUT: self.log_bad_timeout}

    def handle_close(self):
        """ Records test status and shutdowns socket. """
        root_log.debug(self.client_id + ': stop')
        if self.test_completed:
            self.test_status = 'COMPLETED'
        else:
            self.test_status = 'ABORTED'
        self.end_time = time.strftime('%Y-%m-%d_%H:%M:%S')
        self.write_to_db()
        self.shutdown(socket.SHUT_RDWR)
        self.close()

    def collect_incoming_data(self, data):
        """ Saves data from client to client_header and client_message.
            Args:
                data (str): message from server.
        """
        del self.client_message[:]
        message = data.split(Config.API_DELIMITER)
        self.client_header = message[0]
        for msg in message[1:]:
            self.client_message.append(msg)

    def found_terminator(self):
        """ Calls api method from message_handler dict. """
        self.message_handler.get(self.client_header, self.log_unknown)()

    def send_client_id(self):
        """ Sends self.client_id. """
        root_log.debug(self.client_id + ': sending id')
        self.send(Config.API_ID_REQUEST + Config.API_DELIMITER +
                  self.client_id + Config.TERMINATOR)

    def send_client_test(self):
        """ Sends test from queue if non empty, otherwise sends None. """
        if not self.test_queue.empty():
            self.test = self.test_queue.get()
            test_string = self.test.test_name + Config.API_DELIMITER + str(self.test.test_kwargs)
            root_log.debug(self.client_id + ': Sending test-' + test_string)
            self.send(Config.API_TEST_REQUEST + Config.API_DELIMITER + test_string + Config.TERMINATOR)
        else:
            root_log.debug(self.client_id + ': test queue is empty, no test sent')
            self.send(Config.API_TEST_REQUEST + Config.TERMINATOR)

    def log_client_start(self):
        root_log.debug(self.client_id + ': start')
        self.start_time = time.strftime('%Y-%m-%d_%H:%M:%S')

    def log_client_end(self):
        root_log.debug(self.client_id + ': test finished')
        self.test_completed = True
        self.handle_close()

    def log_client_system_info(self):
        self.client_cpu_info = self.client_message[0]
        root_log.debug(self.client_id + ': system info gathered')

    def log_heartbeat(self):
        root_log.debug(self.client_id + ': heartbeat')

    def log_test_stats(self):
        root_log.debug(self.client_id + ': ' + self.client_message[0])

    def log_test_info(self):
        root_log.debug(self.client_id + ': file roll over')

    def log_run_test(self):
        self.test = Test(self.client_message[0], **literal_eval(self.client_message[1]))
        root_log.debug(self.client_id + ': Running {} {}'.format(self.test.test_name, self.test.test_kwargs))

    def log_bad_timeout(self):
        root_log.debug(self.client_id + ': timeout too low, timeout set to ' + self.client_message[0])

    def log_unknown(self):
        root_log.debug(self.client_id + ': Unknown command from client({})'.format(self.client_header))

    def write_to_db(self):
        """ Write out test information to database. """
        if self.test:
            entries = (self.test.test_name, str(self.test.test_kwargs),
                       self.start_time, self.end_time, self.client_cpu_info, self.test_status)
            self.db_cursor.execute('INSERT INTO tests VALUES (?,?,?,?,?,?);', entries)


class Test(object):
    """ Generic test object

        Args:
            test_name (str): name of test, supported tests = ['file write'].
            **kwargs: arguments for test.
                Example:
                    # 'file write' test requires timeout and file_size
                    Test('file write', timeout=1, file_size=2)

    """
    def __init__(self, test_name, **kwargs):
        self.test_name = test_name
        self.test_kwargs = kwargs


if __name__ == '__main__':
    server = TestServer(Config.HOST, Config.PORT)
    try:
        server.run()
    except KeyboardInterrupt:
        print "Ended via keyboard interrupt"
    except Exception as e:
        print root_log.debug('Faulted during execution.')
        raise e
    finally:
        server.end()
