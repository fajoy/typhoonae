# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc., 2011 Tobias Rodäbe
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
"""TyphoonAE's stub of the capability service API."""

import google.appengine.api.apiproxy_stub
import google.appengine.api.capabilities
import logging
import os
import supervisor.childutils

IsEnabledRequest = google.appengine.api.capabilities.IsEnabledRequest
IsEnabledResponse = google.appengine.api.capabilities.IsEnabledResponse
CapabilityConfig = google.appengine.api.capabilities.CapabilityConfig

DEFAULT_SUPERVISOR_SERVER_URL = 'http://localhost:9001'

MEMCACHE_SERVICE = 'memcache'


class CapabilityServiceStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """Capability service stub."""

    def __init__(self, service_name='capability_service'):
        """Constructor.

        Args:
            service_name: Service name expected for all calls.
        """
        super(CapabilityServiceStub, self).__init__(service_name)

        self.__supervisor_rpc = self._GetSupervisorRpcInterface()

        try:
            self.__supervisor_rpc.getState()
            self.__has_supervisor = True
        except socket.error, e:
            logging.critical("Connecting to supervsord failed %s.", e)
            self.__has_supervisor = False

    @staticmethod
    def _GetSupervisorRpcInterface(default_url=DEFAULT_SUPERVISOR_SERVER_URL):
        """Returns the supervisor RPC interface.

        Args:
            default_url: Specifies the default URL to the supervisor server.

        See http://supervisord.org/api.html for a detailed documentation.
        """
        env = {}
        env.update(os.environ)
        env.setdefault('SUPERVISOR_SERVER_URL', default_url)

        return supervisor.childutils.getRPCInterface(env).supervisor

    def _Dynamic_IsEnabled(self, request, response):
        """Implementation of CapabilityService::IsEnabled().

        Args:
            request: An IsEnabledRequest.
            response: An IsEnabledResponse.
        """
        if request.package() == MEMCACHE_SERVICE and self.__has_supervisor:
            proc_info = self.__supervisor_rpc.getProcessInfo('memcached')
            if proc_info.get('statename') != 'RUNNING':
                response.set_summary_status(IsEnabledResponse.DISABLED)
                config = response.add_config()
                config.set_package(MEMCACHE_SERVICE)
                config.set_status(CapabilityConfig.DISABLED)
                return

        response.set_summary_status(IsEnabledResponse.ENABLED)

        default_config = response.add_config()
        default_config.set_package('')
        default_config.set_capability('')
        default_config.set_status(CapabilityConfig.ENABLED)
