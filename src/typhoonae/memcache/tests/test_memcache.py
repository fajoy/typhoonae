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
"""Unit tests for memcache."""

import google.appengine.api.apiproxy_stub_map
import google.appengine.ext.db
import os
import time
import typhoonae.memcache.memcache_stub
import unittest


class MemcacheTestCase(unittest.TestCase):
    """Testing the TyphoonAE's memcache."""

    def setUp(self):
        """Register typhoonae's memcache API proxy stub."""

        google.appengine.api.apiproxy_stub_map.apiproxy = (
            google.appengine.api.apiproxy_stub_map.APIProxyStubMap())

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'memcache', typhoonae.memcache.memcache_stub.MemcacheServiceStub())

        self.stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'memcache')

    def testAddingItem(self):
        """Adds items of different types."""

        foo = "bar"
        google.appengine.api.memcache.add('foo', foo)
        assert google.appengine.api.memcache.get('foo') == foo

        tres_bien = u"Très bien".encode('utf-8')
        google.appengine.api.memcache.add('tres_bien', tres_bien)
        assert google.appengine.api.memcache.get('tres_bien') == tres_bien

        items = [u'foo', 'bar', tres_bien, {1: 'one'}, 42L]
        google.appengine.api.memcache.add('items', items)
        assert google.appengine.api.memcache.get('items') == items

        number = 10
        google.appengine.api.memcache.add('number', number)
        assert google.appengine.api.memcache.get('number') == number

        long_number = long(20)
        google.appengine.api.memcache.add('long', long_number)
        assert google.appengine.api.memcache.get('long') == long_number

        yes = True
        google.appengine.api.memcache.add('yes', yes)
        assert google.appengine.api.memcache.get('yes') == yes

        greeting = 'Hello'
        google.appengine.api.memcache.set('greeting', greeting, namespace='me')
        assert google.appengine.api.memcache.get('greeting') is None
        assert (google.appengine.api.memcache.get('greeting', namespace='me') ==
            greeting)
        assert (google.appengine.api.memcache.get('greeting', namespace='no') is
            None)

        unicode_data = ['Äquator'.decode('utf-8'),]
        google.appengine.api.memcache.set('unicode', unicode_data)
        self.assertEqual(
            unicode_data, google.appengine.api.memcache.get('unicode'))
        assert type(google.appengine.api.memcache.get('unicode')) == list

    def testDeletingItem(self):
        """Tries to set and delete a key and its value."""

        data = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        google.appengine.api.memcache.set('data', data)
        assert google.appengine.api.memcache.get('data') == data
        google.appengine.api.memcache.delete('data')
        assert google.appengine.api.memcache.get('data') == None

    def testDeletingUnknownKey(self):
        """Tries to delete an unknown key."""

        google.appengine.api.memcache.delete('unknown')

    def testExpirationTime(self):
        """Adds an expireing item."""

        bye = "Good bye!"
        google.appengine.api.memcache.add('bye', bye, 1)
        assert google.appengine.api.memcache.get('bye') == bye
        time.sleep(1.1)
        assert google.appengine.api.memcache.get('bye') == None

    def testGetKey(self):
        """Tries to obtain a key."""

        os.environ['APPLICATION_ID'] = ''
        assert typhoonae.memcache.memcache_stub.getKey('bar') == 'YmFy'
        assert (typhoonae.memcache.memcache_stub.getKey('b', namespace='a') ==
                'YS5i')
        os.environ['APPLICATION_ID'] = 'app'
        assert (typhoonae.memcache.memcache_stub.getKey('b', namespace='a') ==
                'YXBwLmEuYg==')
        del os.environ['APPLICATION_ID']
        google.appengine.api.memcache.set('counter', 0, namespace='me') 
        assert google.appengine.api.memcache.get('counter', namespace='me') == 0

    def testIncrementDecrement(self):
        """Testing automatically incrementing and decrementing."""

        google.appengine.api.memcache.incr('unknown_key')
        assert google.appengine.api.memcache.get('unknown_key') == 1
        google.appengine.api.memcache.set('counter', 0) 
        assert google.appengine.api.memcache.get('counter') == 0
        google.appengine.api.memcache.incr('counter')
        assert google.appengine.api.memcache.get('counter') == 1
        google.appengine.api.memcache.incr('counter', delta=2)
        assert google.appengine.api.memcache.get('counter') == 3
        google.appengine.api.memcache.decr('counter')
        assert google.appengine.api.memcache.get('counter') == 2

        # This should cause an error message, because zero deltas are not
        # allowed.
        google.appengine.api.memcache.incr('counter', delta=0)

        google.appengine.api.memcache.set('lcounter', long(20))
        assert google.appengine.api.memcache.get('lcounter') == long(20)
        google.appengine.api.memcache.incr('lcounter')
        assert google.appengine.api.memcache.get('lcounter') == long(21)

    def testUnsuccessfulIncrement(self):
        """Tests incrementing values in a broken chache."""

        cache = self.stub._cache
        self.stub._cache = {}

        google.appengine.api.memcache.incr('somekey')

        self.stub._cache = cache
        del cache

    def testBatchIncrement(self):
        """Tests incrementing multiple keys with integer values."""

        google.appengine.api.memcache.set('low', 0)
        google.appengine.api.memcache.set('high', 100)

        google.appengine.api.memcache.offset_multi({'low': 1, 'high': -50})

        self.assertEqual(1, google.appengine.api.memcache.get('low'))
        self.assertEqual(50, google.appengine.api.memcache.get('high'))

        google.appengine.api.memcache.offset_multi({'low': 9, 'high': 0})

        self.assertEqual(10, google.appengine.api.memcache.get('low'))
        self.assertEqual(50, google.appengine.api.memcache.get('high'))

    def testFlushAll(self):
        """Flushes the whole cache."""

        spam = "Hello, World!"
        google.appengine.api.memcache.set('spam', spam)
        assert google.appengine.api.memcache.get('spam') == spam
        google.appengine.api.memcache.flush_all()
        assert google.appengine.api.memcache.get('spam') == None

    def testReplaceItem(self):
        """Adds and replaces a cached item."""

        first = "Little pig, little pig, let me come in!"
        second = "Not by the hair on my chinny-chin-chin!"
        google.appengine.api.memcache.set('first', first)
        assert google.appengine.api.memcache.get('first') == first
        google.appengine.api.memcache.replace('first', second)
        assert google.appengine.api.memcache.get('first') == second

    def testCacheProtobuf(self):
        """Tries to cache an encoded protocol buffer."""

        class MyModel(google.appengine.ext.db.Model):
            name = google.appengine.ext.db.StringProperty()

        entity = MyModel(name="foobar")

        os.environ['APPLICATION_ID'] = 'app'
        google.appengine.api.memcache.set('protobuf',
            google.appengine.ext.db.model_to_protobuf(entity).Encode())

        encoded_entity = google.appengine.api.memcache.get('protobuf')
        cached_entity = google.appengine.ext.db.model_from_protobuf(
            encoded_entity)
        assert cached_entity.name == 'foobar'

    def testMulti(self):
        """Stores multiple keys' values at once."""

        google.appengine.api.memcache.set_multi(
            {'map_key_one': 1, 'map_key_two': u'some value'})
        values = google.appengine.api.memcache.get_multi(
            ['map_key_one', 'map_key_two'])
        assert {'map_key_one': 1, 'map_key_two': u'some value'} == values

        google.appengine.api.memcache.add_multi(
            {'map_key_one': 'one', 'map_key_two': 2, 'three': u'trois'})
        values = google.appengine.api.memcache.get_multi(
            ['map_key_two', 'three'])
        assert {'map_key_two': u'some value', 'three': u'trois'} == values

    def testStats(self):
        """Tries to get memcache stats.

        TODO: This is not implemented right now.
        """

        self.assertRaises(
            NotImplementedError,
            google.appengine.api.memcache.get_stats)
        

if __name__ == "__main__":
    unittest.main()
