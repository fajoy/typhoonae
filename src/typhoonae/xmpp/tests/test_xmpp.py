# -*- coding: utf-8 -*-
#
# Copyright 2009 Tobias Rodäbel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for the XMPP service."""

import BaseHTTPServer
import SimpleHTTPServer
import cgi
import httplib
import os
import threading
import typhoonae.xmpp.xmpp_http_dispatch
import unittest


class StoppableHttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """HTTP request handler with QUIT stopping the server."""

    def do_POST(self):
        length = int(self.headers.getheader('content-length'))
        qs = self.rfile.read(length)
        params = cgi.parse_qs(qs, keep_blank_values=1)

        self.server.buffer.append(params)

        self.send_response(200)
        self.end_headers()

    def do_QUIT(self):
        """Sends 200 OK response, and sets server.stop to True."""

        self.send_response(200)
        self.end_headers()
        self.server.stop = True


class StoppableHttpServer(BaseHTTPServer.HTTPServer):
    """HTTP server that reacts to self.stop flag."""

    buffer = []

    def serve_forever(self):
        """Handles one request at a time until stopped."""

        self.stop = False
        while not self.stop:
            self.handle_request()


def stop_server(port):
    """Send QUIT request to HTTP server running on localhost:<port>."""

    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()


class MockMessage(object):
    """A fake message class."""

    def getBody(self):
        return 'foo'

    def getFrom(self):
        return 'test@nowhere.net'

    def getTo(self):
        return 'recipient@nowhere.net'


class XmppHttpDispatcherTestCase(unittest.TestCase):
    """Testing the XMPP/HTTP dispatcher."""

    def setUp(self):
        """Sets up a test HTTP server."""

        self.server = StoppableHttpServer(('localhost', 9876),
                                          StoppableHttpRequestHandler)
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()

    def tearDown(self):
        """Tears the test HTTP server down."""

        stop_server(9876)

    def testDispatcher(self):
        """Makes a call to our dispatcher."""

        dispatcher = typhoonae.xmpp.xmpp_http_dispatch.Dispatcher(
            'localhost:9876')

        message = MockMessage()
        dispatcher(None, message)
        assert 'test@nowhere.net' in str(self.server.buffer)
