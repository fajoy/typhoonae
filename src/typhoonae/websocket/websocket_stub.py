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


__all__ = ['Error', 'ConfigurationError', 'WebSocketServiceStub']

WEBSOCKET_HANDLER_URL = "%(protocol)s://%(host)s:%(port)s/%(success_path)s"


class Error(Exception):
  """Base websocket error type."""


class ConfigurationError(Error):
  """Raised when environment is not correctly configured."""


class WebSocketServiceStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """TyphoonAE's WebSocket service stub."""

    def __init__(self, service_name='websocket'):
        """Constructor.

        Args:
            service_name: Service name expected for all calls.
        """
        super(WebSocketServiceStub, self).__init__(service_name)

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

    @classmethod
    def _Dynamic_CreateWebSocketURL(cls, request, response):
        """Implementation of WebSocketService::CreateWebSocketURL().

        Args:
            request: A fully initialized CreateWebSocketURLRequest instance.
            response: A CreateWebSocketURLResponse instance.
        """

        url_parts = dict(
            protocol=cls._GetEnviron('SERVER_PROTOCOL'),
            host=cls._GetEnviron('SERVER_NAME'),
            port=cls._GetEnviron('SERVER_PORT'),
            success_path=re.sub('^/', '', request.success_path))

        response.url = WEBSOCKET_HANDLER_URL % url_parts
