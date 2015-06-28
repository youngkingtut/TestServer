__author__ = 'Tristan Storz'
import SimpleHTTPServer
import SocketServer
import sqlite3
import jinja2
from config import Config
# Wrote this module to display the tests db in browser.
# Uses jinja2 to template db info and simpleHttpServer
# to host it at localhost 8000


def get_test_data_from_db(database_location):
    """ Query db and return the tests table.
        Args:
            database_location (string): location of db.

        Return:
            (list[dict]): each test stored as dict in list.
    """
    db = sqlite3.connect(database_location)
    db_tests = []
    try:
        test_entries = db.execute('SELECT * FROM tests;')
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
            db_tests.append(test)
    except sqlite3.OperationalError as e:
        print 'test_server.db has not been created by TestServer or cannot be found by dbserver.py'
        raise e
    finally:
        db.close()
        return db_tests


def render_tests_to_template(db_tests):
    """ Render tests in index.html """
    try:
        environment = jinja2.Environment(loader=jinja2.PackageLoader('testserver', 'templates'))
        template = environment.get_template('index_template.html')
        index_file = 'index.html'
        with open(index_file, 'wb') as f:
            f.write(template.render(tests=db_tests))
    except ImportError as e:
        print 'template not found'
        raise e


def http_server_at_local_host(port):
    """ serve index.html at port """
    server = SocketServer.TCPServer(('', port), SimpleHTTPServer.SimpleHTTPRequestHandler)
    try:
        print 'now serving test data at localhost {}'.format(port)
        print 'press ctrl+C to end'
        server.serve_forever()
    except KeyboardInterrupt:
        print 'keyboard interrupt'
    except Exception as e:
        raise e
    finally:
        server.shutdown()


if __name__ == '__main__':
    try:
        tests = get_test_data_from_db(Config.DB_NAME)
        render_tests_to_template(tests)
        http_server_at_local_host(Config.HTTP_PORT)
    except Exception as exc:
        print 'Faulted during execution'
        raise exc
