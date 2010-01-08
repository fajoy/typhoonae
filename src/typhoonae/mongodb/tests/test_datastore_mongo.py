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
"""Unit tests for the datastore mongo stub."""

import datetime
import google.appengine.api.apiproxy_stub
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.datastore_types
import google.appengine.ext.db
import os
import time
import typhoonae.mongodb.datastore_mongo_stub
import unittest

 
class LowerCaseProperty(google.appengine.ext.db.Property):
    """A convenience class for generating lower-cased fields for filtering."""

    def __init__(self, property, *args, **kwargs):
        """Constructor.
 
        Args:
            property: The property to lower-case.
        """
        super(LowerCaseProperty, self).__init__(*args, **kwargs)
        self.property = property

    def __get__(self, model_instance, model_class):
        return self.property.__get__(model_instance, model_class).lower()
 
    def __set__(self, model_instance, value):
        raise google.appengine.ext.db.DerivedPropertyError(
            "Cannot assign to a DerivedProperty")


class TestModel(google.appengine.ext.db.Model):
    """Some test model."""

    contents = google.appengine.ext.db.StringProperty(required=True)
    lowered_contents = LowerCaseProperty(contents)
    number = google.appengine.ext.db.IntegerProperty()
    more = google.appengine.ext.db.ListProperty(int, required=True)


class TestIntidClient(object):
    """Pretends to be an intid server client."""

    def __init__(self, host=None, port=None):
        self.value = 0

    def get(self):
        self.value += 1
        return self.value

    def close(self):
        pass


class DatastoreMongoTestCase(unittest.TestCase):
    """Testing the typhoonae datastore mongo."""

    def setUp(self):
        """Register typhoonae's datastore API proxy stub."""

        os.environ['APPLICATION_ID'] = 'test'

        google.appengine.api.apiproxy_stub_map.apiproxy = \
                    google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        datastore = typhoonae.mongodb.datastore_mongo_stub.DatastoreMongoStub(
            'test', '', '', require_indexes=False,
            intid_client=TestIntidClient())

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        self.stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'datastore_v3')

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel LIMIT 1000")

        for entity in query:
            entity.delete()

    def testPuttingAndGettingEntity(self):
        """Writes an entity to and gets an entity from the datastore."""

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel LIMIT 1000")

        for entity in query:
            entity.delete()

        entity = TestModel(contents='foo')
        entity.put()
        assert TestModel.all().fetch(1)[0].contents == 'foo'
        query = google.appengine.ext.db.GqlQuery("SELECT * FROM TestModel")
        self.assertEqual(query.count(), 1)

    def testUnicode(self):
        """Writes an entity with unicode contents."""

        entity = TestModel(contents=u'Äquator')
        entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE contents=:1", u'Äquator')
        assert query.count() == 1
        result = query.fetch(1)
        assert type(result[0].contents) == unicode

    def testAllocatingIDs(self):
        """Allocates a number of IDs."""

        for i in xrange(0, 1000):
            test_key = TestModel(contents='some string').put()

        query = google.appengine.ext.db.GqlQuery("SELECT * FROM TestModel")
        assert query.count() == 1000

        start, end = google.appengine.ext.db.allocate_ids(test_key, 2000)
        self.assertEqual(start, 1001)
        self.assertEqual(end, 3001)

    def testBatching(self):
        """Counts in batches with __key__ as offset."""

        for i in xrange(0, 1000):
            TestModel(contents='some string').put()
        for i in xrange(0, 1000):
            TestModel(contents='some string').put()

        keys = []
        # Maybe we have a compatibility problem here, because order by
        # __key__ should be the default.
        query = google.appengine.ext.db.GqlQuery(
            "SELECT __key__ FROM TestModel ORDER BY __key__")
        cursor = query.fetch(1000)
        while len(cursor) == 1000:
            keys.extend(cursor)
            query = google.appengine.ext.db.GqlQuery(
                "SELECT __key__ FROM TestModel "
                "WHERE __key__ > :1 ORDER BY __key__", cursor[-1])
            cursor = query.fetch(1000)
        keys.extend(cursor)
 
        self.assertEqual(2000, len(keys))

    def testFilter(self):
        """Filters queries."""

        data = 'foo'
        entity = TestModel(contents=data)
        entity.put()
        q = TestModel.all()
        q.filter("contents =", data)
        result = q.get()
        assert result.contents == data

    def testKeysOnly(self):
        """Fetches keys only."""

        entity = TestModel(contents='Some contents')
        entity.put()
        query = TestModel.all(keys_only=True)
        cursor = query.fetch(1)
        assert type(cursor[0]) == google.appengine.api.datastore_types.Key

    def testDerivedProperty(self):
        """Query by derived property."""

        entity = TestModel(contents='Foo Bar')
        entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE lowered_contents = :1", 'foo bar')
        cursor = query.fetch(1)
        assert cursor[0].contents == 'Foo Bar'

    def testSorting(self):
        """Sort query."""

        values = ['Spain', 'England', 'america']
        for value in values:
            entity = TestModel(contents=value)
            entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel ORDER BY lowered_contents ASC")
        cursor = query.fetch(3)
        self.assertEqual([u'america', u'England', u'Spain'],
                         [e.contents for e in cursor])

    def testInQueries(self):
        """Does some IN queries."""

        entity = TestModel(contents=u'some contents', number=1, more=[1, 4])
        entity.put()
        count = (TestModel.all()
                 .filter('number IN', [1, 3])
        ).count()
        self.assertEqual(1, count)

        count = (TestModel.all()
                 .filter('number IN', [0, 4])
        ).count()
        self.assertEqual(0, count)

        count = (TestModel.all()
                 .filter('number IN', [1, 3])
                 .filter('number IN', [1, 4])
        ).count()
        self.assertEqual(1, count)

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 LIMIT 10", [3])
        cursor = query.fetch(10)
        self.assertEqual(0, len(cursor))

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 LIMIT 10", [4])
        cursor = query.fetch(10)
        self.assertEqual(0, len(cursor))

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 "
            "AND number IN :2 ORDER BY number DESC",
            [1, 2], [1])
        cursor = query.fetch(10)
        self.assertEqual(1, len(cursor))

        # This test seems to fail due to a GAE Python bug.
        # See http://code.google.com/p/googleappengine/issues/detail?id=2611
        # for further details.
        #
        # To be commented in after the bug is fixed.
        #
        #count = (TestModel.all()
        #         .filter('more =', 1)
        #         .filter('more IN', [1, 2])
        #         .filter('more IN', [0, 1])
        #).count()
        #self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main() 
