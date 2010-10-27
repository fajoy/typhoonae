# -*- coding: utf-8 -*-
#
# Copyright 2009, 2010 Tobias Rodäbel
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
"""Unit tests for TyphoonAE's Task Queue implementation backed by Celery."""

from typhoonae.taskqueue import taskqueue_celery_stub
from typhoonae.taskqueue.tests import test_taskqueue

import google.appengine.api.apiproxy_stub
import google.appengine.api.apiproxy_stub_map
import os
import time


class TaskQueueTestCase(test_taskqueue.TaskQueueTestCase):
    """Testing the typhoonae task queue."""

    def setUp(self):
        """Register typhoonae's task queue API proxy stub."""

        google.appengine.api.apiproxy_stub_map.apiproxy = \
                    google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        taskqueue = taskqueue_celery_stub.TaskQueueServiceStub(
            internal_address='127.0.0.1:8770',
            root_path=os.path.dirname(__file__))
        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'taskqueue', taskqueue)

        self.stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'taskqueue')

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'urlfetch', test_taskqueue.DummyURLFetchServiceStub())

        # Setup environment
        self._os_environ = dict(os.environ)
        os.environ.clear()
        os.environ['SERVER_NAME'] = 'localhost'
        os.environ['SERVER_PORT'] = '8080'
        os.environ['TZ'] = 'UTC'
        time.tzset()
