# -*- coding: utf-8 -*-
#
# Copyright 2009, 2010, 2011 Tobias Rodäbel
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
"""Unit tests for the Memcache Service."""

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import memcache
from google.appengine.ext import db
from typhoonae.memcache import memcache_stub

import os
import time
import unittest


class MemcacheTestCase(unittest.TestCase):
    """Testing the TyphoonAE's memcache."""

    def setUp(self):
        """Register TyphoonAE's memcache API proxy stub."""

        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

        apiproxy_stub_map.apiproxy.RegisterStub('memcache',
            memcache_stub.MemcacheServiceStub())

        self.stub = apiproxy_stub_map.apiproxy.GetStub('memcache')

    def tearDown(self):
        """Flush memcache."""

        memcache.flush_all()

    def testBehaviors(self):
        """Gets memcache behavior."""

        behaviour = dict(self.stub._GetMemcacheBehavior())
        self.assertTrue('hash' in behaviour)

    def testAddingItem(self):
        """Adds items of different types."""

        foo = "bar"
        memcache.add('foo', foo)
        assert memcache.get('foo') == foo

        tres_bien = u"Très bien".encode('utf-8')
        memcache.add('tres_bien', tres_bien)
        assert memcache.get('tres_bien') == tres_bien

        items = [u'foo', 'bar', tres_bien, {1: 'one'}, 42L]
        memcache.add('items', items)
        assert memcache.get('items') == items

        number = 10
        memcache.add('number', number)
        assert memcache.get('number') == number

        long_number = long(20)
        memcache.add('long', long_number)
        assert memcache.get('long') == long_number

        yes = True
        memcache.add('yes', yes)
        assert memcache.get('yes') == yes

        greeting = 'Hello'
        memcache.set('greeting', greeting, namespace='me')
        assert memcache.get('greeting') is None
        assert memcache.get('greeting', namespace='me') == greeting
        assert memcache.get('greeting', namespace='no') is None

        unicode_data = ['Äquator'.decode('utf-8'),]
        memcache.set('unicode', unicode_data)
        self.assertEqual(unicode_data, memcache.get('unicode'))
        assert type(memcache.get('unicode')) == list

    def testDeletingItem(self):
        """Tries to set and delete a key and its value."""

        data = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        memcache.set('data', data)
        assert memcache.get('data') == data
        memcache.delete('data')
        assert memcache.get('data') == None

    def testDeletingUnknownKey(self):
        """Tries to delete an unknown key."""

        memcache.delete('unknown')

    def testExpirationTime(self):
        """Adds an expireing item."""

        bye = "Good bye!"
        memcache.add('bye', bye, 1)
        assert memcache.get('bye') == bye
        time.sleep(2)
        assert memcache.get('bye') == None

    def testGetKey(self):
        """Tries to obtain a key."""

        os.environ['APPLICATION_ID'] = ''
        assert memcache_stub.getKey('bar') == 'YmFy'
        assert (memcache_stub.getKey('b', namespace='a') == 'YS5i')
        os.environ['APPLICATION_ID'] = 'app'
        assert (memcache_stub.getKey('b', namespace='a') == 'YXBwLmEuYg==')
        del os.environ['APPLICATION_ID']
        memcache.set('counter', 0, namespace='me')
        assert memcache.get('counter', namespace='me') == 0

    def testIncrementDecrement(self):
        """Testing automatically incrementing and decrementing."""

        memcache.incr('unknown_key')
        assert memcache.get('unknown_key') == None
        memcache.set('counter', 0)
        assert memcache.get('counter') == 0
        memcache.incr('counter')
        assert memcache.get('counter') == 1
        memcache.incr('counter', delta=2)
        assert memcache.get('counter') == 3
        memcache.decr('counter')
        assert memcache.get('counter') == 2
        memcache.decr('counter', 2)
        assert memcache.get('counter') == 0
        memcache.incr('second_counter', initial_value=10)
        assert memcache.get('second_counter') == 11
        memcache.decr('third_counter', initial_value=10)
        assert memcache.get('third_counter') == 9

        # This should cause an error message, because zero deltas are not
        # allowed.
        memcache.incr('counter', delta=0)

        memcache.set('lcounter', long(20))
        assert memcache.get('lcounter') == long(20)
        memcache.incr('lcounter')
        assert memcache.get('lcounter') == long(21)

    def testUnsuccessfulIncrement(self):
        """Tests incrementing values in a broken chache."""

        cache = self.stub._cache
        self.stub._cache = {}

        memcache.incr('somekey')

        self.stub._cache = cache

    def testBatchIncrement(self):
        """Tests incrementing multiple keys with integer values."""

        memcache.set('low', 0)
        memcache.set('high', 100)

        memcache.offset_multi({'low': 1, 'high': -50})

        self.assertEqual(1, memcache.get('low'))
        self.assertEqual(50, memcache.get('high'))

        memcache.offset_multi({'low': 9, 'high': 0})

        self.assertEqual(10, memcache.get('low'))
        self.assertEqual(50, memcache.get('high'))

        memcache.offset_multi(
            {'max': 5, 'min': -5}, initial_value=10)

        self.assertEqual(15, memcache.get('max'))
        self.assertEqual(5, memcache.get('min'))

    def testFlushAll(self):
        """Flushes the whole cache."""

        spam = "Hello, World!"
        memcache.set('spam', spam)
        assert memcache.get('spam') == spam
        memcache.flush_all()
        assert memcache.get('spam') == None

    def testReplaceItem(self):
        """Adds and replaces a cached item."""

        first = "Little pig, little pig, let me come in!"
        second = "Not by the hair on my chinny-chin-chin!"
        memcache.set('first', first)
        assert memcache.get('first') == first
        memcache.replace('first', second)
        assert memcache.get('first') == second

    def testClient(self):
        """Tests the class-based Memcache interface."""

        client = memcache.Client()
        client.set('foobar', 'some value')
        assert client.get('foobar') == 'some value'

    def testComapareAndSet(self):
        """Tests the Compare-And-Set method."""

        client = memcache.Client()
        client.set('mycounter', 0)

        def bump_counter(key):
            retries = 0
            while retries < 10: # Retry loop
                counter = client.gets(key)
                assert counter is not None, 'Uninitialized counter'
                if client.cas(key, counter+1):
                    break
                retries += 1

        bump_counter('mycounter')
        assert client.get('mycounter') == 1

    def testNamespaces(self):
        """Tests namespace support."""

        from google.appengine.api import namespace_manager

        namespace = namespace_manager.get_namespace()

        try:
            namespace_manager.set_namespace('testing')
            memcache.set('foobar', 1)
        finally:
            namespace_manager.set_namespace(namespace)

        self.assertEqual(memcache.get('foobar'), None)

    def testCacheProtobuf(self):
        """Tries to cache an encoded protocol buffer."""

        from google.appengine.ext import db

        class MyModel(db.Model):
            name = db.StringProperty()

        entity = MyModel(name="foobar")

        os.environ['APPLICATION_ID'] = 'app'
        memcache.set('protobuf', db.model_to_protobuf(entity).Encode())

        encoded_entity = memcache.get('protobuf')
        cached_entity = db.model_from_protobuf(encoded_entity)
        assert cached_entity.name == 'foobar'

    def testMulti(self):
        """Stores multiple keys' values at once."""

        memcache.set_multi({'map_key_one': 1, 'map_key_two': u'some value'})
        values = memcache.get_multi(['map_key_one', 'map_key_two'])
        assert {'map_key_one': 1, 'map_key_two': u'some value'} == values

        memcache.add_multi(
            {'map_key_one': 'one', 'map_key_two': 2, 'three': u'trois'})
        values = memcache.get_multi(['map_key_two', 'three'])
        assert {'map_key_two': u'some value', 'three': u'trois'} == values

    def testStats(self):
        """Tries to get memcache stats."""

        stats = memcache.get_stats()
        self.assertEqual(
            set(['hits', 'items', 'bytes', 'oldest_item_age', 'misses',
                 'byte_hits']),
            set(stats.keys()))
