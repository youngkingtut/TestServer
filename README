My solution to the SolidFire project is broken up into three main pieces.
- TestServer is used to log all data from clients.
- TestClient is used to manage tests.
- FileWriteTest is the test that was defined by the project spec.

TestServer and TestClient both use the asyncore module to communicate with each other. The server instance can be initiated with a test queue. As clients connect to the server, the clients can request a test from the queue. Also, the client can be initiated with a test to run. In that case, no test is requested and the client will begin running its test after resolving the connection with the server.

I built a sample test run in __main__.py. Fire it up with 'python TestServer' in terminal. After the clients have finished their tests, the database will be served and can be viewed at localhost:8000. Type ctrl+C to end the http server. Logs can be found in test_logs/ and server_logs/.

Final notes:
I believe I achieved all goals set by the project spec. However, if I was given more time to work on this system, I would spend it working on the following:
- Server stability, reconnecting clients with hosts if the host drops out.
- Cleaning up the calculated statistics on the server side.
- Adding more system data to what is sent over from the client.
- Making it easier to add more tests with unique statuses and results.
- Fleshing out the database. Right now it is one flat table.
- Cleaning up the logging system.


Thanks for taking time to check out my work!
Tristan Storz

