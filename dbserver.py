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
        test_entries = db.execute('SELECT * FROM tests;')
        tests = []
        for entry in test_entries:
            test = dict(test=entry[0],
                        start_time=entry[1],
                        end_time=entry[2],
                        files_written=entry[3],
                        write_speed=entry[4],
                        avg_cpu=entry[5],
                        avg_mem=entry[6],
                        cpu_info=entry[7],
                        test_status=entry[8])
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
