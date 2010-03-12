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
"""Unit tests for the datastore mongo stub."""

import datetime
import google.appengine.api.apiproxy_stub
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.datastore
import google.appengine.api.datastore_types
import google.appengine.api.labs.taskqueue
import google.appengine.api.users
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


class TaskQueueServiceStubMock(google.appengine.api.apiproxy_stub.APIProxyStub):
    """Task queue service stub for testing purposes."""

    def __init__(self, service_name='taskqueue', root_path=None):
        super(TaskQueueServiceStubMock, self).__init__(service_name)

    def _Dynamic_Add(self, request, unused_response):
        pass


class DatastoreMongoTestCase(unittest.TestCase):
    """Testing the typhoonae datastore mongo."""

    def setUp(self):
        """Register typhoonae's datastore API proxy stub."""

        os.environ['APPLICATION_ID'] = 'test'
        os.environ['AUTH_DOMAIN'] = 'bar.net'

        google.appengine.api.apiproxy_stub_map.apiproxy = \
                    google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        datastore = typhoonae.mongodb.datastore_mongo_stub.DatastoreMongoStub(
            'test', '', require_indexes=False, intid_client=TestIntidClient())

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        self.stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'datastore_v3')

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'taskqueue', TaskQueueServiceStubMock())

    def tearDown(self):
        """Removes test entities."""

        query = google.appengine.ext.db.GqlQuery("SELECT * FROM TestModel")

        for entity in query:
            entity.delete()

    def testDatastoreTypes(self):
        """Puts and gets different basic datastore types."""

        datastore_types = google.appengine.api.datastore_types

        entity = google.appengine.api.datastore.Entity('TestKind')

        entity.update({
            'rating': datastore_types.Rating(1),
            'category': datastore_types.Category('bugs'),
            'key': datastore_types.Key.from_path('foo', 'bar'),
            'user': google.appengine.api.users.User('foo@bar.net'),
            'text': datastore_types.Text('some text'),
            'blob': datastore_types.Blob('data'),
            'bytestring': datastore_types.ByteString('data'),
            'im': datastore_types.IM('http://example.com/', 'Larry97'),
            'geopt': datastore_types.GeoPt(1.1234, -1.1234),
            'email': datastore_types.Email('foo@bar.net'),
            'blobkey': datastore_types.BlobKey('27f5a7'),
        })

        google.appengine.api.datastore.Put(entity)
        e = google.appengine.api.datastore.Get(entity)
        google.appengine.api.datastore.Delete(entity)

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

    def testQueryHistory(self):
        """Tries to retreive query history information."""

        entity = TestModel(contents='some data')
        entity.put()
        query = TestModel.all()
        assert query.get().contents == u'some data'
        history = self.stub.QueryHistory()
        assert history.keys().pop().kind() == 'TestModel'

    def testUnicode(self):
        """Writes an entity with unicode contents."""

        entity = TestModel(contents=u'Äquator')
        entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE contents=:1", u'Äquator')
        assert query.count() == 1
        result = query.fetch(1)
        assert type(result[0].contents) == unicode

    def testReferenceProperties(self):
        """Tests reference properties."""

        class FirstModel(google.appengine.ext.db.Model):
            prop = google.appengine.ext.db.IntegerProperty()

        class SecondModel(google.appengine.ext.db.Model):
            ref = google.appengine.ext.db.ReferenceProperty(FirstModel)

        obj1 = FirstModel()
        obj1.prop = 42
        obj1.put()

        obj2 = SecondModel()

        # A reference value is the key of another entity.
        obj2.ref = obj1.key()

        # Assigning a model instance to a property uses the entity's key as
        # the value.
        obj2.ref = obj1
        obj2.put()

        obj2.ref.prop = 999
        obj2.ref.put()

        results = google.appengine.ext.db.GqlQuery("SELECT * FROM SecondModel")
        another_obj = results.fetch(1)[0]
        self.assertEqual(999, another_obj.ref.prop)

        # Clean up.
        query = google.appengine.ext.db.GqlQuery("SELECT * FROM FirstModel")
        for entity in query:
            entity.delete()        

        query = google.appengine.ext.db.GqlQuery("SELECT * FROM SecondModel")
        for entity in query:
            entity.delete()        

    def testAllocatingIDs(self):
        """Allocates a number of IDs."""

        for i in xrange(0, 1000):
            test_key = TestModel(contents='some string').put()

        query = google.appengine.ext.db.GqlQuery("SELECT * FROM TestModel")
        self.assertEqual(1000, query.count())

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
        result = query.fetch(1000)
        while len(result) == 1000:
            keys.extend(result)
            query = google.appengine.ext.db.GqlQuery(
                "SELECT __key__ FROM TestModel "
                "WHERE __key__ > :1 ORDER BY __key__", result[-1])
            result = query.fetch(1000)
        keys.extend(result)
 
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
        result = query.fetch(1)
        assert type(result[0]) == google.appengine.api.datastore_types.Key

    def testDerivedProperty(self):
        """Query by derived property."""

        entity = TestModel(contents='Foo Bar')
        entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE lowered_contents = :1", 'foo bar')
        result = query.fetch(1)
        assert result[0].contents == 'Foo Bar'

    def testSorting(self):
        """Sort query."""

        values = ['Spain', 'England', 'america']
        for value in values:
            entity = TestModel(contents=value)
            entity.put()
        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel ORDER BY lowered_contents ASC")

        self.assertEqual(3, query.count())

        result = query.fetch(3)
        self.assertEqual([u'america', u'England', u'Spain'],
                         [e.contents for e in result])

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

        count = (TestModel.all()
                 .filter('contents IN', [u'some contents', u'foo'])
        ).count()
        self.assertEqual(1, count)

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 LIMIT 10", [3])
        result = query.fetch(10)
        self.assertEqual(0, len(result))

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 LIMIT 10", [4])
        result = query.fetch(10)
        self.assertEqual(0, len(result))

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM TestModel WHERE number IN :1 "
            "AND number IN :2 ORDER BY number DESC",
            [1, 2], [1])
        result = query.fetch(10)
        self.assertEqual(1, len(result))

        # This test failed in earlier GAE Python releases.
        # See http://code.google.com/p/googleappengine/issues/detail?id=2611
        # for further details.
        count = (TestModel.all()
                 .filter('more =', 1)
                 .filter('more IN', [1, 2])
                 .filter('more IN', [0, 1])
        ).count()
        self.assertEqual(1, count)

    def testCursors(self):
        """Tests the cursor API."""

        for i in xrange(0, 1000):
            TestModel(contents='Foobar', number=i).put()

        # Set up a simple query
        query = TestModel.all()

        self.assertEqual(1000, query.count())
        self.assertEqual(500, query.count(limit=500))

        # Fetch some results
        a = query.fetch(500)
        b = query.fetch(500, offset=100)

        # Perform query with cursor
        cursor = query.cursor()
        query.with_cursor(cursor)
        c = query.fetch(300)

        query.with_cursor(query.cursor())
        d = query.fetch(200)

        self.assertEqual(0L, a[0].number)
        self.assertEqual(499L, a[-1].number)
        self.assertEqual(100L, b[0].number)
        self.assertEqual(599L, b[-1].number)
        self.assertEqual(600L, c[0].number)
        self.assertEqual(899L, c[-1].number)
        self.assertEqual(900L, d[0].number)
        self.assertEqual(999L, d[-1].number)

    def testCursorsWithSort(self):
        """Tests cursor on sorted results."""

        values = ['Spain', 'england', 'France', 'germany']

        for value in values:
            entity = TestModel(contents=value)
            entity.put()

        query = TestModel.all().order('lowered_contents')

        self.assertEqual(4, query.count())

        a = query.fetch(2)

        cursor = query.cursor()
        query.with_cursor(cursor)

        b = query.fetch(2)

        self.assertEqual([u'england', u'France'], [e.contents for e in a])
        self.assertEqual([u'germany', u'Spain'], [e.contents for e in b])

    def testTransactions(self):
        """Tests transactions.

        Transactions are not supported by mongoDB but shouldn't raise an
        exception.
        """

        def my_transaction():
            entity = TestModel(contents='Foobar', number=42)
            entity.put()

        google.appengine.ext.db.run_in_transaction(my_transaction)

        self.assertEqual(42, TestModel.all().get().number)

    def testTransactionalTasks(self):
        """Tests tasks within transactions."""

        def my_transaction():
            google.appengine.api.labs.taskqueue.add(
                url='/path/to/my/worker', transactional=True)

        google.appengine.ext.db.run_in_transaction(my_transaction)


if __name__ == "__main__":
    unittest.main() 
