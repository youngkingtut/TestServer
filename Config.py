class Config(object):
    PORT = 1115
    HOST = 'localhost'

    LOOP_TIMEOUT = 0.1
    LOOP_COUNT = 1

    TERMINATOR = '\n'

    HEARTBEAT_TIME = 5
    STATS_TIME = 10

    API_CLOSE = 'end connection'
    API_CLIENT_START = 'start'
    API_CLIENT_END = 'end'
    API_DELIMITER = ':'
    API_ID_REQUEST = 'id request'
    API_HEARTBEAT = 'heartbeat'
