from log import root_log
from TestServer import TestServer
from TestClient import TestClient


server = TestServer('localhost', 1115)
ip, port = server.address
TestClient(ip, port)
try:
    server.run()
except KeyboardInterrupt:
    print "Ended via keyboard interrupt"
except Exception as e:
    print root_log.debug('Faulted during execution.')
    raise e
finally:
    server.end()
