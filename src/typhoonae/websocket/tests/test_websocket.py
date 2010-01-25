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
"""Unit tests for TyphoonAE's WebSocket API and service stub."""

import google.appengine.api.apiproxy_stub_map
import os
import typhoonae.websocket
import typhoonae.websocket.websocket_stub
import unittest


class WebSocketTestCase(unittest.TestCase):
    """Testing the WebSocket API."""

    def setUp(self):
        """Register TyphoonAE's WebSocket API proxy stub."""

        # Test environment.
        os.environ.update({
            'SERVER_NAME':'host',
            'SERVER_PORT':'8080',
            'SERVER_PROTOCOL':'http',
            'APPLICATION_ID':'app'
        })

        # Set up API proxy stub.
        google.appengine.api.apiproxy_stub_map.apiproxy = \
            google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'websocket',
            typhoonae.websocket.websocket_stub.WebSocketServiceStub())

    def test_get_stub(self):
        """Tests whether the stub is correctly registered."""

        stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'websocket')
        self.assertEqual(
            typhoonae.websocket.websocket_stub.WebSocketServiceStub,
            stub.__class__)

    def test_create_websocket_url(self):
        """Tries to obtain a valid Web Socket URL."""

        self.assertEqual(
            'http://host:8080/',
            typhoonae.websocket.create_websocket_url())

        self.assertEqual(
            'http://host:8080/foo',
            typhoonae.websocket.create_websocket_url('/foo'))

    def test_send_message(self):
        """Sends a message to a Web Socket."""

        typhoonae.websocket.send_message('1', 'My first message.')

        self.assertRaises(
            typhoonae.websocket.BadArgumentError,
            typhoonae.websocket.send_message, 1, 'My second message.')
