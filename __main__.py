__author__ = 'Tristan Storz'
import os
import subprocess
import Queue
from testserver import TestServer
from config import Config
import dbserver


def spawn_client(wait_time, test_timeout=None, test_file_size=None):
    """ Spins up clients after wait time using a subprocess shell.

        Args:
            wait_time (int): time until client starts.
            test_timeout (int); timeout for file write test.
            test_file_size (int): file size for file write test.

        Return:
            int: pid of subprocess shell
    """
    directory = os.path.dirname(os.path.realpath(__file__))
    command = 'sleep {} && python {}/testclient.py'.format(wait_time, directory)
    if test_timeout:
        command += ' -t {}'.format(test_timeout)
    if test_file_size:
        command += ' -f {}'.format(test_file_size)

    subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)

if __name__ == '__main__':
    # Populate the test queue with some different file write test
    tests = Queue.Queue()
    tests.put(Config.TEST_FILE_WRITE(5, 1))
    tests.put(Config.TEST_FILE_WRITE(30, 5))
    tests.put(Config.TEST_FILE_WRITE(10, 2))
    server = TestServer(Config.HOST, Config.PORT, tests)

    # One client comes with a test, the other two will request tests from the server
    spawn_client(1, 9, 2)
    spawn_client(7)
    spawn_client(10)

    # Start the server
    try:
        server.run()
    except KeyboardInterrupt:
        print 'Ended by user (Keyboard Interrupt)'
    except Exception as e:
        print 'Faulted during run'
        raise e
    finally:
        server.end()

    # After server completes, serve the database at localhost:8000
    try:
        tests = dbserver.get_test_data_from_db(os.getcwd() + '/' + Config.DB_NAME)
        dbserver.render_tests_to_template(tests)
        dbserver.http_server_at_local_host(Config.HTTP_PORT)
    except Exception as exc:
        print 'Faulted during execution'
        raise exc
