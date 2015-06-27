import os
import datetime
import time
import psutil
import multiprocessing
from log import root_log
from Config import Config


class FileWriteTest(object):
    def __init__(self, timeout=Config.TEST_DEFAULT_TIMEOUT_SEC, file_size=Config.TEST_DEFAULT_FILE_SIZE_MB):
        self.test_timeout_sec = timeout
        self.file_size_mb = file_size
        self.message_queue = multiprocessing.Queue()
        self.end_of_test = multiprocessing.Event()
        self.block_size = os.statvfs('/').f_bsize
        self.processes = []
        # self.timeout_check()

    def timeout_check(self):
        root_log.debug('Checking timeout')
        file_name = Config.TEST_FILE + str(os.getpid())
        buf = b'\xab' * self.block_size

        start = datetime.datetime.now()
        with open(file_name, 'wb') as f:
            f.write(buf)
        total_time = (datetime.datetime.now() - start).microseconds / Config.MICRO_SECONDS_PER_SECOND

        os.remove(file_name)
        min_time = ((self.file_size_mb * Config.BYTES_PER_MEGABYTE) / self.block_size) * total_time * Config.TEST_MIN_FILE_WRITES
        if min_time > self.test_timeout_sec:
            self.test_timeout_sec = min_time
            self.message_queue.put(Config.API_BAD_TIMEOUT + Config.API_DELIMITER)
            root_log.debug('Timeout too low for file size. Timeout set to %d' % self.test_timeout_sec)
        else:
            root_log.debug('Timeout is a okay')

    def run(self):
        test = multiprocessing.Process(target=self.file_write_test)
        test.start()
        test_pid = test.pid
        multiprocessing.Process(target=self.send_heartbeat).start()
        multiprocessing.Process(target=self.gather_stats, args=(test_pid,)).start()

        end_time = time.time() + self.test_timeout_sec
        while time.time() < end_time:
            time.sleep(Config.TEST_TIMEOUT_CHECK)
        self.end_of_test.set()

    def send_heartbeat(self):
        while not self.end_of_test.is_set():
            time.sleep(Config.HEARTBEAT_TIME)
            self.message_queue.put(Config.API_HEARTBEAT + Config.TERMINATOR)

    def gather_stats(self, test_pid):
        try:
            process = psutil.Process(test_pid)
            process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            root_log.log('Stats was unable to connect to test PID with psutil module')
            raise exc
        while not self.end_of_test.is_set():
            time.sleep(Config.STATS_TIME)
            if process.is_running():
                cpu = process.cpu_percent()
                mem = process.memory_percent()
                io = process.io_counters()
                self.message_queue.put(Config.API_TEST_STATS + Config.API_DELIMITER +
                                       'CPU %f%% MEM %f%% Bytes Written %d' % (cpu, mem, io.write_bytes)
                                       + Config.TERMINATOR)

    def file_write_test(self):
        test_dir = Config.TEST_DIR + time.strftime('/%Y%m%d_%H:%M:%S')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

        # file_number = 0
        # buf = b'\xab' * self.block_size
        # num_of_blocks = int((self.file_size_mb * Config.BYTES_PER_MEGABYTE) / self.block_size)
        while not self.end_of_test.is_set():
            time.sleep(5)
            # test_file = test_dir + '/' + str(file_number)
            # file_number += 1
            # with open(test_file, 'wb') as f:
            #     for _ in range(num_of_blocks):
            #         f.write(buf)
            # os.remove(test_file)
            if not self.end_of_test.is_set():
                root_log.debug('file roll over')
                self.message_queue.put(Config.API_TEST_INFO + Config.TERMINATOR)
