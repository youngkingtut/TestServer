import asyncore
import asynchat
import socket
import Queue
import sqlite3
import os
import time
from Config import Config
from log import root_log


class ClientAPI(asynchat.async_chat):
    def __init__(self, sock, client_id, test_queue, db_cursor):
        asynchat.async_chat.__init__(self, sock=sock)
        self.set_terminator(Config.TERMINATOR)
        self.client_id = str(client_id)
        self.client_name = 'Client ' + self.client_id
        self.client_header = None
        self.client_message = None
        self.test = None
        self.test_status = 'NOT RUN'
        self.start_time = ''
        self.end_time = ''
        self.test_queue = test_queue
        self.db_cursor = db_cursor
        self.message_handler = {Config.API_CLIENT_START: self.log_client_start,
                                Config.API_ID_REQUEST: self.send_client_id,
                                Config.API_TEST_REQUEST: self.send_client_test,
                                Config.API_CLIENT_END: self.log_client_end,
                                Config.API_HEARTBEAT: self.log_heartbeat,
                                Config.API_TEST_STATS: self.log_test_stats,
                                Config.API_TEST_INFO: self.log_test_info,
                                Config.API_BAD_TIMEOUT: self.log_bad_timeout}

    def handle_close(self):
        root_log.debug(self.client_name + ': stop (abort)')
        self.test_status = 'ABORTED'
        self.end_time = time.strftime('%Y-%m-%d_%H:%M:%S')
        self.write_to_db()
        self.close()

    def collect_incoming_data(self, data):
        message = data.split(Config.API_DELIMITER)
        self.client_header = message[0]
        if len(message) > 1:
            self.client_message = message[1]
        else:
            self.client_message = None

    def found_terminator(self):
        self.message_handler.get(self.client_header, self.log_unknown)()

    def send_client_id(self):
        root_log.debug(self.client_name + ': sending id')
        self.send(Config.API_ID_REQUEST + Config.API_DELIMITER +
                  self.client_id + Config.TERMINATOR)

    def send_client_test(self):
        if not self.test_queue.empty():
            self.test = self.test_queue.get()
            test_string = self.test.test_name + Config.API_DELIMITER + str(self.test.test_kwargs)
            root_log.debug('Client ' + self.client_id + ': Sending test-' + test_string)
            self.send(Config.API_TEST_REQUEST + Config.API_DELIMITER + test_string + Config.TERMINATOR)
        else:
            root_log.debug('Client ' + self.client_id + ': test queue is empty, no test sent')
            self.send(Config.API_TEST_REQUEST + Config.TERMINATOR)

    def log_client_start(self):
        root_log.debug(self.client_name + ': start')
        self.start_time = time.strftime('%Y-%m-%d_%H:%M:%S')

    def log_client_end(self):
        root_log.debug(self.client_name + ': stopped successfully')
        self.test_status = 'COMPLETED'
        self.end_time = time.strftime('%Y-%m-%d_%H:%M:%S')
        self.write_to_db()
        self.close()

    def log_heartbeat(self):
        root_log.debug(self.client_name + ': heartbeat')

    def log_test_stats(self):
        root_log.debug(self.client_name + ': ' + self.client_message)

    def log_test_info(self):
        root_log.debug(self.client_name + ': file roll over')

    def log_bad_timeout(self):
        root_log.debug(self.client_name + ': timeout too low, timeout set to ' + self.client_message)

    def log_unknown(self):
        root_log.debug(self.client_name + ': Unknown command from client')

    def write_to_db(self):
        if self.test:
            entries = (self.test.test_name, str(self.test.test_kwargs),
                       self.start_time, self.end_time, self.test_status)
            self.db_cursor.execute('INSERT INTO Tests VALUES (?,?,?,?,?);', entries)

class TestServer(asyncore.dispatcher):
    def __init__(self, host, port, test_queue):
        asyncore.dispatcher.__init__(self)
        self.db = None
        self.db_cursor = None
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.test_queue = test_queue
        self.address = self.socket.getsockname()
        self.client_id = 0
        self.listen(5)
        self.connection_made = False

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, address = pair
            root_log.debug('Incoming connection from %s' % repr(address))
            ClientAPI(sock, self.get_client_id(), self.test_queue, self.db_cursor)
            self.connection_made = True

    def check_for_exit(self):
        if len(asyncore.socket_map) > 1:
            return True
        elif not self.connection_made:
            return True
        else:
            root_log.debug('No Clients Remain')
            return False

    def get_client_id(self):
        self.client_id += 1
        return self.client_id

    def initialize_database(self):
        if not os.path.isfile(Config.DB_NAME):
            self.db = sqlite3.connect(Config.DB_NAME)
            self.db_cursor = self.db.cursor()
            self.db_cursor.execute('''CREATE TABLE tests
                                    (test_name text,
                                     test_params text,
                                     start_time text,
                                     end_time text,
                                     status text);''')
        else:
            self.db = sqlite3.connect(Config.DB_NAME)
            self.db_cursor = self.db.cursor()

    def run(self):
        self.initialize_database()
        root_log.debug('Starting session')
        while self.check_for_exit():
            asyncore.loop(timeout=Config.LOOP_TIMEOUT, count=Config.LOOP_COUNT)

    def end(self):
        root_log.debug('Ending the session, print out metrics here')
        self.db.commit()
        self.db.close()
        self.close()

class Test(object):
    def __init__(self, test_name, **kwargs):
        self.test_name = test_name
        self.test_kwargs = kwargs

if __name__ == '__main__':
    tests = Queue.Queue()
    tests.put(Test(Config.TEST_FILE_WRITE, timeout=10, file_size=10))
    server = TestServer(Config.HOST, Config.PORT, tests)
    try:
        server.run()
    except KeyboardInterrupt:
        print "Ended via keyboard interrupt"
    except Exception as e:
        print root_log.debug('Faulted during execution.')
        raise e
    finally:
        server.end()
