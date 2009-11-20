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
"""PostgreSQL backed stub for the Google App Engine Python datastore API."""

import google.appengine.api
import google.appengine.datastore
import logging


class DatastorePostgreSQLStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """Datastore API stub using PostgreSQL to persist."""

    def __init__(self,
                 app_id,
                 datastore_file,
                 history_file,
                 require_indexes=False,
                 service_name='datastore_v3',
                 intid_client=None):
        """Constructor.

        Initializes the datastore stub.

        Args:
            app_id: string
            datastore_file: ignored
            history_file: ignored
            require_indexes: bool, default False. If True, composite indexes
                must exist in index.yaml for queries that need them.
            service_name: Service name expected for all calls.
        """
        super(DatastorePostgreSQLStub, self).__init__(service_name)

        assert isinstance(app_id, basestring) and app_id != ''

    def __ValidateKey(self, key):
        """Validate this key.

        Args:
            key: google.appengine.datastore.entity_pb.Reference

        Raises:
            datastore_errors.BadRequestError: if the key is invalid
        """
        assert isinstance(key, google.appengine.datastore.entity_pb.Reference)

    def MakeSyncCall(self, service, call, request, response):
        """The main RPC entry point.

        Service must be 'datastore_v3'. So far, the supported calls are 'Get',
        'Put', 'RunQuery', 'Next', and 'Count'.
        """
        self.assertPbIsInitialized(request)
        super(DatastorePostgreSQLStub, self).MakeSyncCall(service,
                                                          call,
                                                          request,
                                                          response)
        self.assertPbIsInitialized(response)

    def assertPbIsInitialized(self, pb):
        """Raises an exception if the given PB is not initialized and valid."""
        explanation = []
        assert pb.IsInitialized(explanation), explanation
        pb.Encode()

    def _AppIdNamespaceKindForKey(self, key):
        """Get (app, kind) tuple from given key.

        Args:
            key: google.appengine.datastore.entity_pb.Reference

        Returns:
            Tuple (app, kind), both are unicode strings.
        """
        last_path = key.path().element_list()[-1]
        return key.app(), last_path.type()

    def _Dynamic_Put(self, request, response):
        """Translates protobuf representation to SQL statement.

        Args:
            request: Datastore protocol buffer put request.
            response: Datastore protocol buffer put response.
        """
        for entity in request.entity_list():
            self.__ValidateKey(entity.key())

            assert entity.has_key()
            assert entity.key().path().element_size() > 0

            last_path = entity.key().path().element_list()[-1]
            if last_path.id() == 0 and not last_path.has_name():

                # We need to obtain a new integer id.
                last_path.set_id(1)

                assert entity.entity_group().element_size() == 0
                group = entity.mutable_entity_group()
                root = entity.key().path().element(0)
                group.add_element().CopyFrom(root)
            else:
                assert (entity.has_entity_group() and
                        entity.entity_group().element_size() > 0)

            # Let's get the app id an the kind.
            app_id, kind = self._AppIdNamespaceKindForKey(entity.key())

            # We assume that we always get the same order of properties, if the
            # model doesn't change. So, we can compute our columns.
            properties = entity.property_list()
            if properties:
                data = google.appengine.api.datastore.Entity._FromPb(entity)
                columns = [(p.name(), data[p.name()]) for p in properties]
            else:
                columns = []

            # Now, we should be able to create our table.

        response.key_list().extend([e.key() for e in request.entity_list()])
