__author__ = 'Tristan Storz'
import SimpleHTTPServer
import SocketServer
import os
import sqlite3
import jinja2
from config import Config
# Wrote this script to display the tests db in browser.
# Uses jinja2 to template db info and simpleHttpServer
# to host it at localhost 8000
if __name__ == '__main__':

    db = sqlite3.connect(Config.DB_NAME)
    try:
        cursor = db.execute('SELECT * FROM tests;')
        tests = []
        for row in cursor:
            test = dict(test_name=row[0], test_params=row[1], start_time=row[2], end_time=row[3], test_status=row[4],
                        cpu_info=row[5])
            tests.append(test)
    except sqlite3.OperationalError as e:
        print 'test_server.db has not been created by TestServer or cannot be found by dbserver.py'
        raise e
    finally:
        db.close()

    try:
        environment = jinja2.Environment(loader=jinja2.PackageLoader('testserver', 'templates'))
        template = environment.get_template('index_template.html')
        index_file = 'index.html'
        with open(index_file, 'wb') as f:
            f.write(template.render(tests=tests))
    except ImportError as e:
        print 'template not found'
        raise e

    http_server = SocketServer.TCPServer(('', Config.HTTP_PORT), SimpleHTTPServer.SimpleHTTPRequestHandler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print 'keyboard interrupt'
    except Exception as e:
        raise e
    finally:
        http_server.shutdown()
        os.remove(index_file)
