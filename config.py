__author__ = 'Tristan Storz'
class Config(object):
    """ Config information for everything in the TestServer module """
    DB_NAME = 'test_server.db'

    HTTP_PORT = 8000
    PORT = 1115
    HOST = 'localhost'

    BYTES_PER_MEGABYTE = 1024 * 1024
    MICRO_SECONDS_PER_SECOND = 1000000

    LOOP_TIMEOUT = 0.1
    LOOP_COUNT = 1

    TERMINATOR = '||'

    HEARTBEAT_TIME = 2
    STATS_TIME = 3

    API_CLOSE = 'end connection'
    API_CLIENT_START = 'start'
    API_CLIENT_INFO = 'info'
    API_CLIENT_END = 'end'

    API_DELIMITER = '::'
    API_ID_REQUEST = 'id request'
    API_TEST_REQUEST = 'test request'
    API_SYSTEM_INFO = 'system info'

    API_HEARTBEAT = 'heartbeat'
    API_BAD_TIMEOUT = 'bad timeout'
    API_RUNNING_TEST = 'test start'
    API_TEST_STATS = 'stats'
    API_TEST_INFO = 'test info'

    TEST_FILE_WRITE = 'file write'
    TEST_DEFAULT_TIMEOUT_SEC = 10
    TEST_DEFAULT_FILE_SIZE_MB = 10
    TEST_TIMEOUT_CHECK = 0.1
    TEST_DIR = './test_logs/Client'
    TEST_FILE = 'test'
    TEST_MIN_FILE_WRITES = 2

    SERVER_DIR = './server_logs/'
