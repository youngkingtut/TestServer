from log import root_log
from TestServer import TestServer
from Config import Config


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
