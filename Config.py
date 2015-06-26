class Config(object):
    PORT = 1115
    HOST = 'localhost'

    BYTES_PER_MEGABYTE = 1024 * 1024
    MICRO_SECONDS_PER_SECOND = 1000000

    LOOP_TIMEOUT = 0.1
    LOOP_COUNT = 1

    TERMINATOR = '\n'

    HEARTBEAT_TIME = 5
    STATS_TIME = 9

    API_CLOSE = 'end connection'
    API_CLIENT_START = 'start'
    API_CLIENT_END = 'end'
    API_DELIMITER = ':'
    API_ID_REQUEST = 'id request'
    API_HEARTBEAT = 'heartbeat'
    API_BAD_TIMEOUT = 'bad timeout'
    API_TEST_STATS = 'stats'
    API_TEST_INFO = 'test info'

    TEST_DIR = './test_logs/Client'
    TEST_FILE = 'test'
    NEEDED_CHUNKS = 2

    SERVER_DIR = './server_logs/'
