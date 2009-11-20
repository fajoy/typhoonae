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
"""Unit tests for the datastore PostgreSQL stub."""

import google.appengine.api.apiproxy_stub
import google.appengine.api.apiproxy_stub_map
import google.appengine.ext.db
import os
import typhoonae.postgresql.datastore_postgresql_stub
import unittest


class DatastorePostgreSQLTestCase(unittest.TestCase):
    """Testing the datastore API stub implementation."""

    def setUp(self):
        """Registers typhoonae's datastore API proxy stub."""

        os.environ['APPLICATION_ID'] = 'test'

        google.appengine.api.apiproxy_stub_map.apiproxy = \
                    google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        datastore = (typhoonae.postgresql.datastore_postgresql_stub.
                     DatastorePostgreSQLStub(
                        'test', '', '', require_indexes=False))

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        self.stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'datastore_v3')

    def testPuttingAndGettingEntity(self):
        """Writes an entity to and gets an entity from the datastore."""

        class TestModel(google.appengine.ext.db.Model):
            """Some test model."""

            data   = google.appengine.ext.db.StringProperty()
            point  = google.appengine.ext.db.GeoPtProperty()
            number = google.appengine.ext.db.IntegerProperty()

        entity = TestModel()
        entity.data   = 'foobar'        # str or unicode
        entity.number = 6               # int or long
        entity.point  = "45.256,-71.92" # GeoPt
        entity.put()


if __name__ == "__main__":
    unittest.main()
