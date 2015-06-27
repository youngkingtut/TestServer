import SimpleHTTPServer
import SocketServer
import os
import sqlite3
import jinja2
from Config import Config


if __name__ == '__main__':

    db = sqlite3.connect('test_server.db')
    cursor = db.execute('SELECT * FROM tests;')
    tests = []
    for row in cursor:
        test = dict(test_name=row[0], test_params=row[1], start_time=row[2], end_time=row[3], test_status=row[4])
        tests.append(test)
    db.close()

    environment = jinja2.Environment(loader=jinja2.PackageLoader('TestServer', 'templates'))
    template = environment.get_template('index_template.html')
    index_file = 'index.html'
    with open(index_file, 'wb') as f:
        f.write(template.render(tests=tests))

    http_server = SocketServer.TCPServer(('', Config.HTTP_PORT), SimpleHTTPServer.SimpleHTTPRequestHandler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt as e:
        print 'keyboard'
        raise e
    finally:
        http_server.shutdown()
        os.remove(index_file)
