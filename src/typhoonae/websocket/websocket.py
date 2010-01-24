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
"""This module contains TyphoonAE's WebSocket API.

This module allows App Engine apps to interact with Web Sockets held by a
decoupled Web Socket Service.
"""

from google.appengine.api import apiproxy_stub_map
from google.appengine.runtime import apiproxy_errors
from typhoonae.websocket import websocket_service_pb2


__all__ = [
    'create_websocket_url',
]


class Error(Exception):
    """Base error class for this module."""


def create_websocket_url(success_path='',
                         _make_sync_call=apiproxy_stub_map.MakeSyncCall):
    """Create a valid Web Socket URL.

    Args:
        success_path: Path within application to call when a new Web Socket
            request received.
        _make_sync_call: Used for dependency injection.

    Returns:
        String containing a valid Web Socket URL.
    """

    request = websocket_service_pb2.CreateWebSocketURLRequest()
    response = websocket_service_pb2.CreateWebSocketURLResponse()

    request.success_path = success_path

    try:
        _make_sync_call("websocket", "CreateWebSocketURL", request, response)
    except apiproxy_errors.ApplicationError, e:
        raise Error()

    return response.url
