from __future__ import division
import os
import datetime
import time
import utilities
import multiprocessing
from utilities import root_log
from config import Config
""" File Write Test

Test writes file_size files for timeout seconds. The test writes all
information to message_queue. A timeout check is performed to guarantee
that the test will write at least two files within the timeout time.

To run test, call the run method.

Example:
    test = FileWriteTest(10, 10)
    test.run()
    while not test.message_queue.empty():
        print test.message_queue.get()
"""


class FileWriteTest(object):
    """ Initializes test.

        Args:
            timeout (int): test timeout time in seconds.
            file_size (int): size of files to write in MB.
    """

    def __init__(self, timeout=Config.TEST_DEFAULT_TIMEOUT_SEC, file_size=Config.TEST_DEFAULT_FILE_SIZE_MB):
        self.test_timeout_sec = timeout
        self.file_size_mb = file_size
        self.message_queue = multiprocessing.Queue()
        self.end_of_test = multiprocessing.Event()
        self.block_size = os.statvfs('/').f_bsize
        self.processes = []
        self.timeout_check()

    @staticmethod
    def get_test_name():
        return Config.TEST_FILE_WRITE_NAME

    def get_test_args(self):
        return str(dict([('timeout', self.test_timeout_sec), ('file_size', self.file_size_mb)]))

    def timeout_check(self):
        """ Writes one block out to file and times it. Checks time against test_timeout_sec.
            If timeout is too short for file_size, sets test_timeout_sec to calculated time.
        """
        root_log.debug('Checking timeout')
        utilities.verify_dir_exists(Config.TEST_LOG_DIR)
        file_name = Config.TEST_LOG_DIR + str(os.getpid())
        buf = b'\x50' * self.block_size
        num_of_blocks = Config.TEST_TIMEOUT_NUM_OF_BLOCKS

        file_descriptor = os.open(file_name, os.O_WRONLY | os.O_APPEND | os.O_DSYNC | os.O_CREAT)
        try:
            start = datetime.datetime.now()
            for _ in xrange(num_of_blocks):
                os.write(file_descriptor, buf)
            total_time = (datetime.datetime.now() - start)
        except Exception as e:
            root_log.debug('failed to write temp file {}'.format(file_name))
            raise e
        finally:
            os.close(file_descriptor)
            os.remove(file_name)

        total_time = total_time.seconds + (total_time.microseconds / Config.MICRO_SECONDS_PER_SECOND)
        min_time = ((self.file_size_mb * Config.BYTES_PER_MEGABYTE) /
                    (num_of_blocks * self.block_size)) * total_time * Config.TEST_MIN_FILE_WRITES
        if min_time > self.test_timeout_sec:
            self.test_timeout_sec = min_time
            self.message_queue.put(Config.API_BAD_TIMEOUT + Config.API_DELIMITER)
            root_log.debug('Timeout too low for file size. Timeout set to {}'.format(self.test_timeout_sec))

    def run(self):
        """ Spawns three processes and then waits for test time to end.
            Upon ending, sets the end_of_test Event to signal that the
            three processes should end.
        """
        root_log.debug('Creating processes')
        test = multiprocessing.Process(target=self.file_write_test)
        test.start()
        test_pid = test.pid
        multiprocessing.Process(target=self.send_heartbeat).start()
        multiprocessing.Process(target=self.gather_stats, args=(test_pid,)).start()

        root_log.debug('Beginning test loop')
        end_time = time.time() + self.test_timeout_sec
        while time.time() < end_time:
            time.sleep(Config.TEST_TIMEOUT_CHECK)
        root_log.debug('Test ended')
        self.end_of_test.set()

    def send_heartbeat(self):
        """ Continues writing out message event until end_of_test is set """
        while not self.end_of_test.is_set():
            time.sleep(Config.TEST_HEARTBEAT_TIME)
            self.message_queue.put(Config.API_HEARTBEAT + Config.TERMINATOR)
            root_log.debug('Heartbeat')

    def gather_stats(self, test_pid):
        """ Continues writing out cpu/mem info for input pid until end_of-test is set
            Args:
                test_pid (int): pid of process to monitor.
        """
        cpu, cpu_total_new, cpu_pid_new = 0, 0, 0
        while not self.end_of_test.is_set():
            time.sleep(Config.TEST_STATS_TIME)
            try:
                cpu_pid_old = cpu_pid_new
                cpu_total_old = cpu_total_new
                cpu_pid_new = utilities.get_cpu_clock_cycles_of_pid(test_pid)
                cpu_total_new = utilities.get_total_cpu_clock_cycles()
                mem_total = utilities.get_total_memory()
                if mem_total:
                    mem = utilities.get_memory_of_pid(test_pid) / mem_total
                if cpu_total_new and cpu_pid_new:
                    cpu = (cpu_pid_new - cpu_pid_old) / (cpu_total_new - cpu_total_old)
            except IOError:
                if not self.end_of_test.is_set():
                    root_log('file write test process data could not be gathered from Linux proc files')
                return
            self.message_queue.put(Config.API_TEST_STATS + Config.API_DELIMITER + 'CPU {} MEM {}'.format(cpu, mem)
                                   + Config.TERMINATOR)
            root_log.debug('Stats: CPU {:3.5f}%% MEM {:3.5f}%%'.format(cpu, mem))

    def file_write_test(self):
        """ Write file of given file_size. When finished, write out a new file
            with the same size. Continues until end_of_test is set. Writes out
            every time file rollover occurs.
        """
        utilities.verify_dir_exists(Config.TEST_LOG_DIR)

        file_number = 0
        buf = b'\xab' * self.block_size
        num_of_blocks = int((self.file_size_mb * Config.BYTES_PER_MEGABYTE) / self.block_size)
        while not self.end_of_test.is_set():
            test_file = Config.TEST_LOG_DIR + str(os.getpid()) + str(file_number)
            file_number += 1
            file_descriptor = os.open(test_file,  os.O_WRONLY | os.O_APPEND | os.O_DSYNC | os.O_CREAT)
            try:
                for _ in xrange(num_of_blocks):
                    os.write(file_descriptor, buf)
            except Exception as e:
                root_log.debug('failed to write temp file {}'.format(test_file))
                raise e
            finally:
                os.close(file_descriptor)
                os.remove(test_file)
                self.message_queue.put(Config.API_TEST_FILE_WRITE + Config.TERMINATOR)
                root_log.debug('file roll over')
