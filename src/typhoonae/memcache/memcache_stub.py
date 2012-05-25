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
"""Memcache integration."""

from google.appengine.api import apiproxy_stub
from google.appengine.api import memcache
from google.appengine.api.memcache import memcache_service_pb
from google.appengine.runtime import apiproxy_errors

import base64
import cPickle
import logging
import os
import pylibmc
import threading
import time

DEFAULT_ADDR = '127.0.0.1'
DEFAULT_PORT = 11211

MemcacheSetResponse       = memcache_service_pb.MemcacheSetResponse
MemcacheSetRequest        = memcache_service_pb.MemcacheSetRequest
MemcacheIncrementRequest  = memcache_service_pb.MemcacheIncrementRequest
MemcacheIncrementResponse = memcache_service_pb.MemcacheIncrementResponse
MemcacheDeleteResponse    = memcache_service_pb.MemcacheDeleteResponse


def getKey(key, namespace=None):
    """Returns a key."""

    app_id = os.environ.get('APPLICATION_ID', '')
    if app_id: app_id += '.'

    if namespace:
        key = '%(namespace)s.%(key)s' % locals()
    key = '%(app_id)s%(key)s' % locals()
    return base64.b64encode(key)


class MemcacheServiceStub(apiproxy_stub.APIProxyStub):
    """Memcache service stub.

    This stub uses memcached to store data.
    """

    def __init__(self, config=None, service_name='memcache'):
        """Initializes memcache service stub.

        Args:
            config: Dictionary containing configuration parameters.
            service_name: Service name expected for all calls.
        """
        super(MemcacheServiceStub, self).__init__(service_name)
        if not config:
            config = ["%(addr)s:%(port)i" % dict(addr=DEFAULT_ADDR, port=DEFAULT_PORT)]

        self._cache = pylibmc.Client(config)

    def _GetMemcacheBehavior(self):
        behaviors = self._cache.behaviors
        keys = sorted(k for k in behaviors if not k.startswith('_'))
        sorted_behaviors = [(k, behaviors[k]) for k in keys]
        logging.debug("Memcache behavior: %s" % sorted_behaviors)
        return sorted_behaviors

    def _Dynamic_Get(self, request, response):
        """Implementation of MemcacheService::Get().

        Args:
            request: A MemcacheGetRequest.
            response: A MemcacheGetResponse.
        """
        for key in set(request.key_list()):
            value = self._cache.get(getKey(key, request.name_space()))
            if value is None:
                continue
            flags = 0
            stored_flags, cas_id, stored_value = cPickle.loads(value)
            flags |= stored_flags
            item = response.add_item()
            item.set_key(key)
            item.set_value(stored_value)
            item.set_flags(flags)
            if request.for_cas():
                item.set_cas_id(cas_id)

    def _Dynamic_Set(self, request, response):
        """Implementation of MemcacheService::Set().

        Args:
            request: A MemcacheSetRequest.
            response: A MemcacheSetResponse.
        """
        for item in request.item_list():
            key = getKey(item.key(), request.name_space())
            set_policy = item.set_policy()
            old_entry = self._cache.get(key)
            cas_id = 0
            if old_entry:
                stored_flags, cas_id, stored_value = cPickle.loads(old_entry)
            set_status = MemcacheSetResponse.NOT_STORED

            if ((set_policy == MemcacheSetRequest.SET) or
                (set_policy == MemcacheSetRequest.ADD and old_entry is None) or
                (set_policy == MemcacheSetRequest.REPLACE and
                 old_entry is not None)):

                if (old_entry is None or set_policy == MemcacheSetRequest.SET):
                    set_status = MemcacheSetResponse.STORED

            elif (set_policy == MemcacheSetRequest.CAS and item.for_cas() and
                item.has_cas_id()):
                if old_entry is None:
                    set_status = MemcacheSetResponse.NOT_STORED
                elif cas_id != item.cas_id():
                    set_status = MemcacheSetResponse.EXISTS
                else:
                    set_status = MemcacheSetResponse.STORED

            if (set_status == MemcacheSetResponse.STORED
                or set_policy == MemcacheSetRequest.REPLACE):

                set_value = cPickle.dumps(
                    [item.flags(), cas_id+1, item.value()])
                if set_policy == MemcacheSetRequest.REPLACE:
                    self._cache.replace(key, set_value)
                else:
                    self._cache.set(key, set_value, item.expiration_time())

            response.add_set_status(set_status)

    def _Dynamic_Delete(self, request, response):
        """Implementation of MemcacheService::Delete().

        Args:
            request: A MemcacheDeleteRequest.
            response: A MemcacheDeleteResponse.
        """
        for item in request.item_list():
            key = getKey(item.key(), request.name_space())
            entry = self._cache.get(key)
            delete_status = MemcacheDeleteResponse.DELETED

            if entry is None:
                delete_status = MemcacheDeleteResponse.NOT_FOUND
            else:
                self._cache.delete(key)

            response.add_delete_status(delete_status)

    def _Increment(self, namespace, request):
        """Internal function for incrementing from a MemcacheIncrementRequest.

        Args:
            namespace: A string containing the namespace for the request,
                if any. Pass an empty string if there is no namespace.
            request: A MemcacheIncrementRequest instance.

        Returns:
            An integer or long if the offset was successful, None on error.
        """
        if not request.delta():
            return None

        cas_id = 0

        key = getKey(request.key(), namespace)
        value = self._cache.get(key)
        if value is None:
            if not request.has_initial_value():
                return None
            flags, cas_id, stored_value = (
                memcache.TYPE_INT, cas_id, str(request.initial_value()))
        else:
            flags, cas_id, stored_value = cPickle.loads(value)

        if flags == memcache.TYPE_INT:
            new_value = int(stored_value)
        elif flags == memcache.TYPE_LONG:
            new_value = long(stored_value)
        if request.direction() == MemcacheIncrementRequest.INCREMENT:
            new_value += request.delta()
        elif request.direction() == MemcacheIncrementRequest.DECREMENT:
            new_value -= request.delta()

        new_stored_value = cPickle.dumps([flags, cas_id+1, str(new_value)])
        try:
            self._cache.set(key, new_stored_value)
        except:
            return None

        return new_value

    def _Dynamic_Increment(self, request, response):
        """Implementation of MemcacheService::Increment().

        Args:
            request: A MemcacheIncrementRequest.
            response: A MemcacheIncrementResponse.
        """
        new_value = self._Increment(request.name_space(), request)
        if new_value is None:
            raise apiproxy_errors.ApplicationError(
                memcache_service_pb.MemcacheServiceError.UNSPECIFIED_ERROR)
        response.set_new_value(new_value)

    def _Dynamic_BatchIncrement(self, request, response):
        """Implementation of MemcacheService::BatchIncrement().

        Args:
            request: A MemcacheBatchIncrementRequest.
            response: A MemcacheBatchIncrementResponse.
        """
        namespace = request.name_space()
        for request_item in request.item_list():
            new_value = self._Increment(namespace, request_item)
            item = response.add_item()
            if new_value is None:
                item.set_increment_status(MemcacheIncrementResponse.NOT_CHANGED)
            else:
                item.set_increment_status(MemcacheIncrementResponse.OK)
                item.set_new_value(new_value)

    def _Dynamic_FlushAll(self, request, response):
        """Implementation of MemcacheService::FlushAll().

        Args:
            request: A MemcacheFlushRequest.
            response: A MemcacheFlushResponse.
        """

        self._cache.flush_all()

    def _Dynamic_Stats(self, request, response):
        """Implementation of MemcacheService::Stats().

        Args:
            request: A MemcacheStatsRequest.
            response: A MemcacheStatsResponse.
        """
        stats = response.mutable_stats()

        num_servers = 0
        hits_total = 0
        misses_total = 0
        byte_hits_total = 0
        items_total = 0
        bytes_total = 0
        time_total = 0

        def get_stats_value(stats_dict, key, _type=int):
            if key not in stats_dict:
                logging.warn("No stats for key '%s'." % key) 
            return _type(stats_dict.get(key, '0'))

        for server, server_stats in self._cache.get_stats():
            num_servers += 1
            hits_total += get_stats_value(server_stats, 'get_hits')
            misses_total += get_stats_value(server_stats, 'get_misses')
            byte_hits_total += get_stats_value(server_stats, 'bytes_read') 
            items_total += get_stats_value(server_stats, 'curr_items') 
            bytes_total += get_stats_value(server_stats, 'bytes') 
            time_total += get_stats_value(server_stats, 'time', float) 

        stats.set_hits(hits_total)
        stats.set_misses(misses_total)
        stats.set_byte_hits(byte_hits_total)
        stats.set_items(items_total)
        stats.set_bytes(bytes_total)

        stats.set_oldest_item_age(time.time() - time_total / num_servers)
