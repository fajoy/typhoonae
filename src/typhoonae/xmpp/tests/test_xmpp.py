# -*- coding: utf-8 -*-
#
# Copyright 2010 Tobias Rodäbel
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
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.urlfetch_stub
import google.appengine.api
import cgi
import httplib
import os
import threading
import typhoonae.xmpp.xmpp_http_dispatch
import typhoonae.xmpp.xmpp_service_stub
import unittest
import xmpp


class XmppServiceTestCase(unittest.TestCase):
    """Testing the XMPP service API proxy stub."""

    def setUp(self):
        """Register TyphoonAE's XMPP service API proxy stub."""

        # Set up API proxy stubs.
        google.appengine.api.apiproxy_stub_map.apiproxy = \
            google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'xmpp',
            typhoonae.xmpp.xmpp_service_stub.XmppServiceStub())

        os.environ['APPLICATION_ID'] = 'testapp'

    def test_stub(self):
        """Tests whether the stub is correctly registered."""

        stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub('xmpp')

        self.assertEqual(
            typhoonae.typhoonae.xmpp.xmpp_service_stub.XmppServiceStub,
            stub.__class__)

    def testGetPresence(self):
        """Tests getting presence for a JID."""

        self.assertTrue(
            google.appengine.api.xmpp.get_presence('you@net', 'me@net'))

    def testSendMessage(self):
        """Sends a message."""

        # TODO: We need a proper XMPP server configuration to test whether
        # sending messages works correctly.
        self.assertRaises(
            xmpp.HostUnknown,
            google.appengine.api.xmpp.send_message,
            ['foo@bar'], 'Hello, World!')

    def testSendInvite(self):
        """Sends an invite."""

        self.assertRaises(
            xmpp.HostUnknown,
            google.appengine.api.xmpp.send_invite,
            ['foo@bar'], 'Hello, World!')


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

    def log_request(self, *args):
        """Suppress any log messages for testing."""


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
    conn.close()


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

    def testDispatcher(self):
        """Makes a call to our dispatcher."""

        server = StoppableHttpServer(
            ('localhost', 9876), StoppableHttpRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()

        dispatcher = typhoonae.xmpp.xmpp_http_dispatch.Dispatcher(
            'localhost:9876')

        message = MockMessage()
        dispatcher(None, message)
        assert 'test@nowhere.net' in str(server.buffer)

        typhoonae.xmpp.xmpp_http_dispatch.post_multipart(
            'http://localhost:9876',
            [(u'body', u'Some body contents.'),])

        stop_server(9876)

    def testPostMultipart(self):
        """Tries to post multipart form data."""

        typhoonae.xmpp.xmpp_http_dispatch.post_multipart(
            'http://localhost:8765',
            [(u'body', u'Some body contents.'),])

    def testLoop(self):
        """Tests the main loop."""

        class MockConnection(object):
            _counter = 0
            @classmethod
            def Process(cls, i):
                if cls._counter > 0:
                    raise KeyboardInterrupt
                cls._counter += 1

        typhoonae.xmpp.xmpp_http_dispatch.loop(MockConnection())
