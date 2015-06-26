from __future__ import division
import asyncore
import asynchat
import socket
import multiprocessing
import psutil
import time
import datetime
import argparse
import sys
import os
from Config import Config
from log import root_log


class TestClient(asynchat.async_chat):
    def __init__(self, host, port, timeout, chunk_size_megabytes):
        asynchat.async_chat.__init__(self)
        self.set_terminator(Config.TERMINATOR)
        self.timeout = timeout
        self.chunk_size = chunk_size_megabytes
        self.end_of_test = multiprocessing.Event()
        self.message_queue = multiprocessing.Queue()
        self.block_size = os.statvfs('/').f_bsize
        self.timeout_reset = False
        self.timeout_check()
        self.data = None
        self.client_id = None
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))

    def handle_connect(self):
        self.send(Config.API_CLIENT_START + Config.TERMINATOR)
        if self.timeout_reset:
            self.send(Config.API_BAD_TIMEOUT + Config.API_DELIMITER + str(self.timeout) + Config.TERMINATOR)
        self.send(Config.API_ID_REQUEST + Config.TERMINATOR)

    def handle_error(self):
        typ, val, traceback = sys.exc_info()
        root_log.debug('Connection closed: ' + str(val))
        self.close()

    def handle_close(self):
        self.end_of_test.set()

    def collect_incoming_data(self, data):
        self.data = data

    def found_terminator(self):
        server_message = self.data.split(Config.API_DELIMITER)
        if server_message[0] == Config.API_ID_REQUEST:
            self.client_id = server_message[1]
            self.run()

    def run(self):
        test = multiprocessing.Process(target=self.chunk_test)
        test.start()
        test_pid = test.pid
        multiprocessing.Process(target=self.send_heartbeat).start()
        multiprocessing.Process(target=self.gather_stats, args=(test_pid,)).start()

        end_time = time.time() + self.timeout
        while time.time() < end_time:
            if not self.message_queue.empty():
                self.send(self.message_queue.get())

        self.end()

    def end(self):
        self.send(Config.API_CLIENT_END + Config.TERMINATOR)
        self.end_of_test.set()
        self.close()

    def timeout_check(self):
        file_name = Config.TEST_FILE + str(os.getpid())
        buf = b'\xab' * self.block_size

        start = datetime.datetime.now()
        with open(file_name, 'wb') as f:
            f.write(buf)
        total_time = (datetime.datetime.now() - start).microseconds / Config.MICRO_SECONDS_PER_SECOND

        os.remove(file_name)
        min_time = ((self.chunk_size * Config.BYTES_PER_MEGABYTE) / self.block_size) * total_time * Config.NEEDED_CHUNKS
        if min_time > self.timeout:
            self.timeout = min_time
            self.timeout_reset = True
            root_log.debug('Timeout too low for chunk size. Timeout set to %d' % self.timeout)

    def send_heartbeat(self):
        while not self.end_of_test.is_set():
            time.sleep(Config.HEARTBEAT_TIME)
            self.message_queue.put(Config.API_HEARTBEAT + Config.TERMINATOR)

    def gather_stats(self, test_pid):
        try:
            process = psutil.Process(test_pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            root_log.log('Stats was unable to connect to test PID with psutil module')
            raise exc

        process.cpu_percent()
        while not self.end_of_test.is_set():
            time.sleep(Config.STATS_TIME)
            if process.is_running():
                cpu = process.cpu_percent()
                mem = process.memory_percent()
                io = process.io_counters()
                self.message_queue.put(Config.API_TEST_STATS + Config.API_DELIMITER +
                                       'CPU %f%% MEM %f%% Bytes Written %d' % (cpu, mem, io.write_bytes)
                                       + Config.TERMINATOR)

    def chunk_test(self):
        test_dir = Config.TEST_DIR + self.client_id + time.strftime('/%Y%m%d_%H%M%S')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

        file_number = 0
        buf = b'\xab' * self.block_size
        num_of_blocks = int((self.chunk_size * 1024 * 1024) / self.block_size)
        while not self.end_of_test.is_set():
            time.sleep(3)
            test_file = test_dir + '/' + str(file_number)
            file_number += 1
            with open(test_file, 'wb') as f:
                for _ in range(num_of_blocks):
                    f.write(buf)
            root_log.debug('file roll over')
            self.message_queue.put(Config.API_TEST_INFO + Config.TERMINATOR)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--timeout', dest='timeout', default=10, type=int,
                        help='runtime for client')
    parser.add_argument('-c', '--chunk_size', dest='chunk_size', default=10, type=int,
                        help='chunk size of test files')
    cmd_input = parser.parse_args()

    client = TestClient(Config.HOST, Config.PORT, cmd_input.timeout, cmd_input.chunk_size)
    try:
        asyncore.loop(timeout=Config.LOOP_TIMEOUT)
    except KeyboardInterrupt:
        root_log.debug('Ended via keyboard interrupt')
    except Exception as e:
        root_log.debug('Faulted during execution.')
        raise e
    finally:
        client.close()
