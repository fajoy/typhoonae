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
"""Unit tests for the Channel API and TyphoonAE's service stub."""

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import channel
from google.appengine.runtime import apiproxy_errors
from typhoonae.channel import channel_service_stub
import BaseHTTPServer
import SimpleHTTPServer
import cgi
import httplib
import os
import threading
import unittest


class StoppableHttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """HTTP request handler with QUIT stopping the server."""

    def do_POST(self):
        length = int(self.headers.getheader('content-length'))
        qs = self.rfile.read(length)
        params = cgi.parse_qs(qs, keep_blank_values=1)

        self.server.buf.append(params)

    def do_QUIT(self):
        """Sends 200 OK response, and sets server.stop to True."""

        self.send_response(200)
        self.end_headers()
        self.server.stop = True

    def log_request(self, *args):
        """Suppress any log messages for testing."""


class StoppableHttpServer(BaseHTTPServer.HTTPServer):
    """HTTP server that reacts to self.stop flag."""

    buf = []

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


class ChannelTestCase(unittest.TestCase):
    """Testing the Channel API."""

    def setUp(self):
        """Register TyphoonAE's Channel API proxy stub."""

        os.environ['SERVER_SOFTWARE'] = 'Development'

        # Set up API proxy stubs.
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

        apiproxy_stub_map.apiproxy.RegisterStub(
            'channel',
            channel_service_stub.ChannelServiceStub('localhost:9876'))

    def test_stub(self):
        """Tests whether the stub is correctly registered."""

        stub = apiproxy_stub_map.apiproxy.GetStub('channel')

        self.assertEqual(
            channel_service_stub.ChannelServiceStub, stub.__class__)

    def test_create_channel(self):
        """Creates a channel."""

        self.assertEqual('testchannel', channel.create_channel('testchannel'))

        self.assertRaises(
            channel.InvalidChannelKeyError, channel.create_channel, '')

    def test_send_message(self):
        """Sends a channel message."""

        # Set up a simple HTTP server for testing.
        server = StoppableHttpServer(
            ('localhost', 9876), StoppableHttpRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()

        # Send our message.
        channel.send_message('testchannel', 'Hello, World!')

        self.assertRaises(
            channel.InvalidMessageError,
            channel.send_message, 'testchannel', '')

        # Stop server.
        stop_server(9876)

        buf = server.buf
        self.assertEqual("[{'Hello, World!': ['']}]", str(buf))
