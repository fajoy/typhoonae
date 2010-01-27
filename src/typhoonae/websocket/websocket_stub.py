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

import google.appengine.api.apiproxy_stub
import os
import re
import typhoonae.websocket


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

    def __init__(self, service_name='websocket', port=8888):
        """Constructor.

        Args:
            service_name: Service name expected for all calls.
        """
        super(WebSocketServiceStub, self).__init__(service_name)
        self._port = port

    def _GetPort(self):
        """Returns service port."""

        return self._port

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
        """Implementation of WebSocketService::CreateWebSocketURL().

        Args:
            request: A fully initialized CreateWebSocketURLRequest instance.
            response: A CreateWebSocketURLResponse instance.
        """

        url_parts = dict(
            protocol='ws',
            host=self._GetEnviron('SERVER_NAME'),
            port=self._GetPort(),
            app_id=self._GetEnviron('APPLICATION_ID'),
            success_path=re.sub('^/', '', request.success_path))

        response.url = typhoonae.websocket.WEBSOCKET_HANDLER_URL % url_parts

    def _Dynamic_SendMessage(self, request, response):
        """Implementation of WebSocketService::SendMessage().

        Args:
            request: A WebSocketMessageRequest instance.
            response: A WebSocketMessageResponse instance.
        """

        body = request.message.body

        # Implement send message here.

        response.status.code = (typhoonae.websocket.websocket_service_pb2.
                                WebSocketMessageResponse.NO_ERROR)
