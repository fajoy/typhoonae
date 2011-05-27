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
"""TyphoonAE's WebSocket service stub."""

from typhoonae import websocket
from typhoonae.websocket import websocket_service_pb2

import google.appengine.api.apiproxy_stub
import httplib
import os
import re


__all__ = [
    'Error',
    'ConfigurationError',
    'WebSocketServiceStub'
]


class Error(Exception):
  """Base websocket error type."""


class ConfigurationError(Error):
  """Raised when environment is not correctly configured."""


class WebSocketServiceStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """TyphoonAE's WebSocket service stub."""

    def __init__(self, host, port=8888, service_name='websocket'):
        """Constructor.

        Args:
            service_name: Service name expected for all calls.
            port: Port number of the Web Socket service.
        """
        super(WebSocketServiceStub, self).__init__(service_name)
        self._host = host
        self._port = port

    def _GetAddress(self):
        """Returns service address."""

        return "%s:%s" % (self._host, self._port)

    @staticmethod
    def _GetEnviron(name):
        """Helper method ensures environment configured as expected.

        Args:
            name: Name of environment variable to get.

        Returns:
            Environment variable associated with name.

        Raises:
            ConfigurationError if required environment variable is not found.
        """
        try:
            return os.environ[name]
        except KeyError:
            raise ConfigurationError('%s is not set in environment.' % name)

    def _Dynamic_CreateWebSocketURL(self, request, response):
        """Implementation of WebSocketService::create_websocket_url().

        Args:
            request: A fully initialized CreateWebSocketURLRequest instance.
            response: A CreateWebSocketURLResponse instance.
        """

        url_parts = dict(
            protocol='ws',
            host=self._GetEnviron('SERVER_NAME'),
            port=self._port,
            success_path=re.sub('^/', '', request.success_path))

        response.url = websocket.WEBSOCKET_HANDLER_URL % url_parts

    def _SendMessage(self, body, socket, broadcast=False):
        """Sends a Web Socket message.

        Args:
            body: The message body.
            socket: A socket.
            broadcast: This flag determines whether a message should be sent to
                all active sockets but the sender.
        """
        if broadcast: path = 'broadcast'
        else: path = 'message'

        conn = httplib.HTTPConnection(self._GetAddress())

        headers = {websocket.WEBSOCKET_HEADER: str(socket),
                   'X-TyphoonAE-ServerName': self._GetEnviron('SERVER_NAME'),
                   'Content-Type': 'text/plain'}

        try:
            conn.request("POST", '/'+path, body.encode('utf-8'), headers)
        except:
            status = websocket_service_pb2.WebSocketMessageResponse.OTHER_ERROR
        finally:
            conn.close()

        status = websocket_service_pb2.WebSocketMessageResponse.NO_ERROR

        return status

    def _Dynamic_SendMessage(self, request, response):
        """Implementation of WebSocketService::send_message().

        Args:
            request: A WebSocketMessageRequest instance.
            response: A WebSocketMessageResponse instance.
        """

        status = self._SendMessage(
            request.message.body, request.message.socket)

        response.status.code = status

    def _Dynamic_BroadcastMessage(self, request, response):
        """Implementation of WebSocketService::broadcast_message().

        Args:
            request: A WebSocketMessageRequest instance.
            response: A WebSocketMessageResponse instance.
        """

        status = self._SendMessage(
            request.message.body, None, broadcast=True)

        response.status.code = status
