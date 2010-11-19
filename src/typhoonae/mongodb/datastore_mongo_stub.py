# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc., 2008-2009 10gen Inc., 2010 Tobias Rodäbel
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
#

"""MongoDB backed stub for the Python datastore API."""

from google.appengine.api import api_base_pb
from google.appengine.api import apiproxy_stub
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore
from google.appengine.api import datastore_types
from google.appengine.api import users
from google.appengine.datastore import datastore_pb
from google.appengine.datastore import datastore_index
from google.appengine.runtime import apiproxy_errors
from google.appengine.datastore import entity_pb
from pymongo.connection import Connection
from pymongo.binary import Binary

import logging
import pymongo
import re
import random
import sys
import threading
import types

try:
  __import__('google.appengine.api.labs.taskqueue.taskqueue_service_pb')
  taskqueue_service_pb = sys.modules.get(
      'google.appengine.api.labs.taskqueue.taskqueue_service_pb')
except ImportError:
  from google.appengine.api.taskqueue import taskqueue_service_pb

entity_pb.Reference.__hash__ = lambda self: hash(self.Encode())
datastore_pb.Query.__hash__ = lambda self: hash(self.Encode())

_MAX_QUERY_COMPONENTS = 100
_MAX_QUERY_OFFSET = 1000
_CURSOR_CONCAT_STR = '!CURSOR!'
_MAX_ACTIONS_PER_TXN = 5


class DatastoreMongoStub(apiproxy_stub.APIProxyStub):
  """Persistent stub for the Python datastore API, using MongoDB to persist.

  A DatastoreMongoStub instance handles a single app's data.
  """

  def __init__(self,
               app_id,
               datastore_file=None,
               require_indexes=False,
               service_name='datastore_v3'):
    """Constructor.

    Initializes the datastore stub.

    Args:
      app_id: string
      datastore_file: ignored
      require_indexes: bool, default False.  If True, composite indexes must
          exist in index.yaml for queries that need them.
      service_name: Service name expected for all calls.
    """
    super(DatastoreMongoStub, self).__init__(service_name)

    assert isinstance(app_id, basestring) and app_id != ''
    self.__app_id = app_id
    self.__require_indexes = require_indexes
    self.__trusted = True

    # TODO should be a way to configure the connection
    self.__db = Connection()[app_id]

    # NOTE our query history gets reset each time the server restarts...
    # should this be fixed?
    self.__query_history = {}

    self.__next_index_id = 1
    self.__indexes = {}
    self.__index_lock = threading.Lock()

    self.__cursor_lock = threading.Lock()
    self.__next_cursor = 1
    self.__queries = {}

    self.__id_lock = threading.Lock()
    self.__id_map = {}

    # Transaction support
    self.__next_tx_handle = 1
    self.__tx_writes = {}
    self.__tx_deletes = set()
    self.__tx_actions = []
    self.__tx_lock = threading.Lock()

  def Clear(self):
    """Clears the datastore.

    This is mainly for testing purposes and the admin console.
    """
    for name in self.__db.collection_names():
      if not name.startswith('system.'):
        self.__db.drop_collection(name)
    self.__queries = {}
    self.__query_history = {}
    self.__indexes = {}
    self.__id_map = {}
    self.__next_tx_handle = 1
    self.__tx_writes = {}
    self.__tx_deletes = set()
    self.__tx_actions = []

    self.__db.datastore.drop()

  def MakeSyncCall(self, service, call, request, response):
    """ The main RPC entry point. service must be 'datastore_v3'.

    So far, the supported calls are 'Get', 'Put', 'Delete', 'RunQuery', 'Next',
    and 'AllocateIds'.
    """
    self.AssertPbIsInitialized(request)

    super(DatastoreMongoStub, self).MakeSyncCall(
        service, call, request, response)

    self.AssertPbIsInitialized(response)

  def AssertPbIsInitialized(self, pb):
    """Raises an exception if the given PB is not initialized and valid."""
    explanation = []
    assert pb.IsInitialized(explanation), explanation
    pb.Encode()

  def QueryHistory(self):
    """Returns a dict that maps Query PBs to times they've been run."""

    return dict((pb, times) for pb, times in self.__query_history.items()
                if pb.app() == self.__app_id)

  def __collection_for_key(self, key):
    return key.path().element(-1).type()

  def __id_for_key(self, key):
    db_path = []
    def add_element_to_db_path(elem):
      db_path.append(elem.type())
      if elem.has_name():
        db_path.append(elem.name())
      else:
        db_path.append("\t" + str(elem.id()).zfill(10))
    for elem in key.path().element_list():
      add_element_to_db_path(elem)
    return "\10".join(db_path)

  def __key_for_id(self, id):
    def from_db(value):
      if value.startswith("\t"):
        return int(value[1:])
      return value
    return datastore_types.Key.from_path(*[from_db(a) for a in id.split("\10")])

  def __create_mongo_value_for_value(self, value):
    if isinstance(value, datastore_types.Rating):
      return {
        'class': 'rating',
        'rating': int(value),
        }
    if isinstance(value, datastore_types.Category):
      return {
        'class': 'category',
        'category': str(value),
        }
    if isinstance(value, datastore_types.Key):
      return {
        'class': 'key',
        'path': self.__id_for_key(value._ToPb()),
        }
    if isinstance(value, types.ListType):
      list_for_db = [self.__create_mongo_value_for_value(v) for v in value]
      sorted_list = sorted(value)
      return {
        'class': 'list',
        'list': list_for_db,
        'ascending_sort_key': self.__create_mongo_value_for_value(
          sorted_list[0]),
        'descending_sort_key': self.__create_mongo_value_for_value(
          sorted_list[-1]),
        }
    if isinstance(value, users.User):
      return {
        'class': 'user',
        'email': value.email(),
        }
    if isinstance(value, datastore_types.Text):
      return {
        'class': 'text',
        'string': unicode(value),
        }
    if isinstance(value, datastore_types.Blob):
      return Binary(value)
    if isinstance(value, datastore_types.ByteString):
      return {
        'class': 'bytes',
        'value': Binary(value)
        }
    if isinstance(value, datastore_types.IM):
      return {
        'class': 'im',
        'protocol': value.protocol,
        'address': value.address,
        }
    if isinstance(value, datastore_types.GeoPt):
      return {
        'class': 'geopt',
        'lat': value.lat,
        'lon': value.lon,
        }
    if isinstance(value, datastore_types.Email):
      return {
        'class': 'email',
        'value': value,
        }
    if isinstance(value, datastore_types.BlobKey):
      return {
        'class': 'blobkey',
        'value': str(value),
        }
    return value

  def __create_value_for_mongo_value(self, mongo_value):
    if isinstance(mongo_value, Binary):
      return datastore_types.Blob(str(mongo_value))
    if isinstance(mongo_value, types.DictType):
      if mongo_value['class'] == 'rating':
        return datastore_types.Rating(int(mongo_value["rating"]))
      if mongo_value['class'] == 'category':
        return datastore_types.Category(mongo_value["category"])
      if mongo_value['class'] == 'key':
        return self.__key_for_id(mongo_value['path'])
      if mongo_value['class'] == 'list':
        return [self.__create_value_for_mongo_value(v)
                for v in mongo_value['list']]
      if mongo_value['class'] == 'user':
        return users.User(email=mongo_value["email"])
      if mongo_value['class'] == 'text':
        return datastore_types.Text(mongo_value['string'])
      if mongo_value['class'] == 'im':
        return datastore_types.IM(mongo_value['protocol'],
                                  mongo_value['address'])
      if mongo_value['class'] == 'geopt':
        return datastore_types.GeoPt(mongo_value['lat'], mongo_value['lon'])
      if mongo_value['class'] == 'email':
        return datastore_types.Email(mongo_value['value'])
      if mongo_value['class'] == 'bytes':
        return datastore_types.ByteString(mongo_value['value'])
      if mongo_value['class'] == 'blobkey':
        return datastore_types.BlobKey(mongo_value['value'])
    return mongo_value

  def __mongo_document_for_entity(self, entity):
    document = {}
    document["_id"] = self.__id_for_key(entity.key())

    entity = datastore.Entity._FromPb(entity)
    for (k, v) in entity.iteritems():
      v = self.__create_mongo_value_for_value(v)
      document[k] = v

    return document

  def __entity_for_mongo_document(self, document):
    key = self.__key_for_id(document.get('_id'))
    entity = datastore.Entity(
      kind=key.kind(), parent=key.parent(), name=key.name())

    for k in document.keys():
      if k != '_id':
        v = self.__create_value_for_mongo_value(document[k])
        entity[k] = v

    pb = entity._ToPb()
    # no decent way to initialize an Entity w/ an existing key...
    if not key.name():
      pb.key().path().element_list()[-1].set_id(key.id())

    return pb

  def __allocate_ids(self, kind, size=None, max=None):
    """Allocates IDs.

    Args:
      kind: A kind.
      size: Number of IDs to allocate.
      max: Upper bound of IDs to allocate.

    Returns:
      Integer as the beginning of a range of size IDs.
    """
    self.__id_lock.acquire()
    ret = None
    col = self.__db.datastore
    _id = 'IdSeq_%s' % kind
    if not col.find_one({'_id': _id}):
      col.insert({'_id': _id, 'next_id': 1})
    if size is not None:
      assert size > 0
      next_id, block_size = self.__id_map.get(kind, (0, 0))
      if not block_size:
        block_size = (size / 1000 + 1) * 1000
        result = self.__db.command(
          "findandmodify",
          "datastore",
          query={"_id": _id},
          update={"$inc": {"next_id": next_id+block_size}})
        next_id = int(result['value']['next_id'])
      if size > block_size:
        result = self.__db.command(
          "findandmodify",
          "datastore",
          query={"_id": _id},
          update={"$inc": {"next_id": size}})
        ret = int(result['value']['next_id'])
      else:
        ret = next_id;
        next_id += size
        block_size -= size
        self.__id_map[kind] = (next_id, block_size)
    else:
      ret = col.find_one({'_id': _id}).get('next_id')
      if max and max >= ret:
        col.update({'_id': _id}, {'$set': {'next_id': max+1}})
    self.__id_lock.release()
    return ret

  def __ValidateAppId(self, app_id):
    """Verify that this is the stub for app_id.

    Args:
      app_id: An application ID.

    Raises:
      datastore_errors.BadRequestError: if this is not the stub for app_id.
    """
    assert app_id
    if not self.__trusted and app_id != self.__app_id:
      raise datastore_errors.BadRequestError(
          'app %s cannot access app %s\'s data' % (self.__app_id, app_id))

  def __ValidateTransaction(self, tx):
    """Verify that this transaction exists and is valid.

    Args:
      tx: datastore_pb.Transaction

    Raises:
      datastore_errors.BadRequestError: if the tx is valid or doesn't exist.
    """
    assert isinstance(tx, datastore_pb.Transaction)
    self.__ValidateAppId(tx.app())

  def __ValidateKey(self, key):
    """Validate this key.

    Args:
      key: entity_pb.Reference

    Raises:
      datastore_errors.BadRequestError: if the key is invalid
    """
    assert isinstance(key, entity_pb.Reference)

    self.__ValidateAppId(key.app())

    for elem in key.path().element_list():
      if elem.has_id() == elem.has_name():
        raise datastore_errors.BadRequestError(
            'each key path element should have id or name but not both: %r'
            % key)

  def __PutEntities(self, entities):
    """Inserts or updates entities in the DB.

    Args:
      entities: A list of entities to store.
    """
    for entity in entities:
      collection = self.__collection_for_key(entity.key())
      document = self.__mongo_document_for_entity(entity)
      unused_id = self.__db[collection].save(document).decode('utf-8')

  def __DeleteEntities(self, keys):
    """Deletes entities from the DB.

    Args:
      keys: A list of keys to delete index entries for.
    Returns:
      The number of rows deleted.
    """
    for key in keys:
      collection = self.__collection_for_key(key)
      _id = self.__id_for_key(key)
      self.__db[collection].remove({"_id": _id})
    return len(keys)

  def _Dynamic_Put(self, put_request, put_response):
    entities = put_request.entity_list()

    for entity in entities:
      self.__ValidateKey(entity.key())

      assert entity.has_key()
      assert entity.key().path().element_size() > 0

      last_path = entity.key().path().element_list()[-1]
      if last_path.id() == 0 and not last_path.has_name():
        id_ = self.__allocate_ids(last_path.type(), 1)
        last_path.set_id(id_)

        assert entity.entity_group().element_size() == 0
        group = entity.mutable_entity_group()
        root = entity.key().path().element(0)
        group.add_element().CopyFrom(root)

      else:
        assert (entity.has_entity_group() and
                entity.entity_group().element_size() > 0)

      if put_request.transaction().handle():
        self.__tx_writes[entity.key()] = entity
        self.__tx_deletes.discard(entity.key())

    if not put_request.transaction().handle():
      self.__PutEntities(entities)
    put_response.key_list().extend([e.key() for e in entities])

  def _Dynamic_Get(self, get_request, get_response):
    for key in get_request.key_list():
      collection = self.__collection_for_key(key)
      _id = self.__id_for_key(key)

      group = get_response.add_entity()
      document = self.__db[collection].find_one({"_id": _id})
      if document is None:
        entity = None
      else:
        entity = self.__entity_for_mongo_document(document)

      if entity:
        group.mutable_entity().CopyFrom(entity)

  def _Dynamic_Delete(self, delete_request, delete_response):
    keys = delete_request.key_list()
    for key in keys:
      self.__ValidateAppId(key.app())
      if delete_request.transaction().handle():
        self.__tx_deletes.add(key)
        self.__tx_writes.pop(key, None)

    if not delete_request.transaction().handle():
      self.__DeleteEntities(delete_request.key_list())

  def __special_props(self, value, direction):
    if isinstance(value, datastore_types.Category):
      return ["category"]
    if isinstance(value, datastore_types.GeoPt):
      return ["lat", "lon"]
    if isinstance(value, list):
      if direction == pymongo.ASCENDING:
        return ["ascending_sort_key"]
      return ["descending_sort_key"]
    return None

  def __unorderable(self, value):
    if isinstance(value, datastore_types.Text):
      return True
    if isinstance(value, datastore_types.Blob):
      return True
    return False

  def __translate_order_for_mongo(self, order_list, prototype):
    mongo_ordering = []

    for o in order_list:
      key = o.property().decode('utf-8')
      value = pymongo.ASCENDING
      if o.direction() is datastore_pb.Query_Order.DESCENDING:
        value = pymongo.DESCENDING

      if key == "__key__":
        key = "_id"
        mongo_ordering.append((key, value))
        continue

      if key not in prototype or self.__unorderable(prototype[key]):
        return None

      props = self.__special_props(prototype[key], value)
      if props:
        for prop in props:
          mongo_ordering.append((key + "." + prop, value))
      else:
        mongo_ordering.append((key, value))
    return mongo_ordering

  def __filter_suffix(self, value):
    if isinstance(value, types.ListType):
      return ".list"
    return ""

  def __filter_binding(self, key, value, operation, prototype):
    if key in prototype:
      key += self.__filter_suffix(prototype[key])

    if key == "__key__":
      key = "_id"
      value = self.__id_for_key(value._ToPb())
    else:
      value = self.__create_mongo_value_for_value(value)

    if operation == "<":
      return (key, {'$lt': value})
    elif operation == '<=':
      return (key, {'$lte': value})
    elif operation == '>':
      return (key, {'$gt': value})
    elif operation == '>=':
      return (key, {'$gte': value})
    elif operation == '==':
      return (key, value)
    raise apiproxy_errors.ApplicationError(
      datastore_pb.Error.BAD_REQUEST, "Can't handle operation %r." % operation)

  def _MinimalQueryInfo(self, query):
    """Extract the minimal set of information for query matching.

    Args:
      query: datastore_pb.Query instance from which to extract info.

    Returns:
      datastore_pb.Query instance suitable for matching against when
      validating cursors.
    """
    query_info = datastore_pb.Query()
    query_info.set_app(query.app())

    for filter in query.filter_list():
      query_info.filter_list().append(filter)
    for order in query.order_list():
      query_info.order_list().append(order)

    if query.has_ancestor():
      query_info.mutable_ancestor().CopyFrom(query.ancestor())

    for attr in ('kind', 'name_space', 'search_query', 'offset', 'limit'):
      query_has_attr = getattr(query, 'has_%s' % attr)
      query_attr = getattr(query, attr)
      query_info_set_attr = getattr(query_info, 'set_%s' % attr)
      if query_has_attr():
        query_info_set_attr(query_attr())

    return query_info

  def _DecodeCompiledCursor(self, compiled_cursor):
    """Converts a compiled_cursor into a cursor_entity.

    Args:
      compiled_cursor: Cursor instance to decode.

    Returns:
      (offset, query_pb, cursor_entity, inclusive)
    """
    assert len(compiled_cursor.position_list()) == 1

    position = compiled_cursor.position(0)
    entity_pb = datastore_pb.EntityProto()
    (count, query_info_encoded, entity_encoded) = position.start_key().split(
      _CURSOR_CONCAT_STR)
    query_info_pb = datastore_pb.Query()
    query_info_pb.ParseFromString(query_info_encoded)
    entity_pb.ParseFromString(entity_encoded)
    offset = int(count) + query_info_pb.offset()
    return (offset,
            query_info_pb,
            datastore.Entity._FromPb(entity_pb, True),
            position.start_inclusive())

  def _Dynamic_RunQuery(self, query, query_result):
    if query.keys_only():
      query_result.set_keys_only(True)

    num_components = len(query.filter_list()) + len(query.order_list())
    if query.has_ancestor():
      num_components += 1
    if num_components > _MAX_QUERY_COMPONENTS:
      raise apiproxy_errors.ApplicationError(
          datastore_pb.Error.BAD_REQUEST,
          ('query is too large. may not have more than %s filters'
           ' + sort orders ancestor total' % _MAX_QUERY_COMPONENTS))

    app = query.app()

    query_result.mutable_cursor().set_cursor(0)
    query_result.set_more_results(False)

    if self.__require_indexes:
      (required, kind, ancestor, props, num_eq_filters) = (
        datastore_index.CompositeIndexForQuery(query))
      if required:
        index = entity_pb.CompositeIndex()
        index.mutable_definition().set_entity_type(kind)
        index.mutable_definition().set_ancestor(ancestor)
        for (k, v) in props:
          p = index.mutable_definition().add_property()
          p.set_name(k)
          p.set_direction(v)

        if props and not self.__has_index(index):
          raise apiproxy_errors.ApplicationError(
              datastore_pb.Error.NEED_INDEX,
              "This query requires a composite index that is not defined. "
              "You must update the index.yaml file in your application root.")

    collection = query.kind()

    clone = datastore_pb.Query()
    clone.CopyFrom(query)
    clone.clear_hint()
    if clone in self.__query_history:
      self.__query_history[clone] += 1
    else:
      self.__query_history[clone] = 1

    # HACK we need to get one Entity from this collection so we know what the
    # property types are (because we need to construct queries that depend on
    # the types of the properties)...
    prototype = self.__db[collection].find_one()
    if prototype is None:
      return
    prototype = datastore.Entity._FromPb(
      self.__entity_for_mongo_document(prototype))

    spec = {}

    if query.has_ancestor():
      spec["_id"] = re.compile("^%s.*$" % self.__id_for_key(query.ancestor()))

    operators = {datastore_pb.Query_Filter.LESS_THAN:             '<',
                 datastore_pb.Query_Filter.LESS_THAN_OR_EQUAL:    '<=',
                 datastore_pb.Query_Filter.GREATER_THAN:          '>',
                 datastore_pb.Query_Filter.GREATER_THAN_OR_EQUAL: '>=',
                 datastore_pb.Query_Filter.EQUAL:                 '==',
                 }

    for filt in query.filter_list():
      assert filt.op() != datastore_pb.Query_Filter.IN

      prop = filt.property(0).name().decode('utf-8')
      op = operators[filt.op()]

      filter_val_list = [datastore_types.FromPropertyPb(filter_prop)
                         for filter_prop in filt.property_list()]

      (key, value) = self.__filter_binding(prop,
                                           filter_val_list[0],
                                           op,
                                           prototype)

      if key in spec:
        if (not isinstance(spec[key], types.DictType)
            and not isinstance(value, types.DictType)):
          if spec[key] != value:
            return
        elif not isinstance(spec[key], types.DictType):
          value["$in"] = [spec[key]]
          spec[key] = value
        elif not isinstance(value, types.DictType):
          spec[key]["$in"] = [value]
        else:
          spec[key].update(value)
      else:
        spec[key] = value

    offset = 0
    # Cursor magic
    if query.has_compiled_cursor():
      offset, query_pb, unused_spec, incl = self._DecodeCompiledCursor(
        query.compiled_cursor())

    cursor = self.__db[collection].find(spec)

    order = self.__translate_order_for_mongo(query.order_list(), prototype)
    if order is None:
      return
    if order:
      cursor = cursor.sort(order)

    if query.offset() == datastore._MAX_INT_32:
      query.set_offset(0)
      query.set_limit(datastore._MAX_INT_32)

    if offset:
      cursor = cursor.skip(int(offset))
    elif query.has_offset() and query.offset() != _MAX_QUERY_OFFSET:
      cursor = cursor.skip(int(query.offset()))
    if query.has_limit():
      cursor = cursor.limit(int(query.limit()))

    self.__cursor_lock.acquire()
    cursor_index = self.__next_cursor
    self.__next_cursor += 1
    self.__cursor_lock.release()
    self.__queries[cursor_index] = cursor

    # Cursor magic
    compiled_cursor = query_result.mutable_compiled_cursor()
    position = compiled_cursor.add_position()
    query_info = self._MinimalQueryInfo(query)
    cloned_cursor = cursor.clone()
    results = list(cloned_cursor)
    if results:
      start_key = _CURSOR_CONCAT_STR.join((
        str(len(results) + offset),
        query_info.Encode(),
        self.__entity_for_mongo_document(results[-1]).Encode()
      ))
      # Populate query result
      result_list = query_result.result_list()
      for doc in results:
        result_list.append(self.__entity_for_mongo_document(doc))
      query_result.set_skipped_results(len(results))
      position.set_start_key(str(start_key))
      position.set_start_inclusive(False)
    del cloned_cursor

    query_result.mutable_cursor().set_cursor(cursor_index)
    query_result.set_more_results(False)

  def _Dynamic_Next(self, next_request, query_result):
    cursor = next_request.cursor().cursor()
    query_result.set_more_results(False)

    if cursor == 0: # we exited early from the query w/ no results...
      return

    try:
      cursor = self.__queries[cursor]
    except KeyError:
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'Cursor %d not found' % cursor)

    query_result.set_more_results(True)

  def _Dynamic_BeginTransaction(self, request, transaction):
    self.__ValidateAppId(request.app())

    self.__tx_lock.acquire()
    handle = self.__next_tx_handle
    self.__next_tx_handle += 1

    transaction.set_app(request.app())
    transaction.set_handle(handle)

    self.__tx_actions = []

  def _Dynamic_AddActions(self, request, _):
    """Associates the creation of one or more tasks with a transaction.

    Args:
      request: A taskqueue_service_pb.TaskQueueBulkAddRequest containing the
          tasks that should be created when the transaction is comitted.
    """
    if ((len(self.__tx_actions) + request.add_request_size()) >
        _MAX_ACTIONS_PER_TXN):
      raise apiproxy_errors.ApplicationError(
          datastore_pb.Error.BAD_REQUEST,
          'Too many messages, maximum allowed %s' % _MAX_ACTIONS_PER_TXN)

    new_actions = []
    for add_request in request.add_request_list():
      self.__ValidateTransaction(add_request.transaction())
      clone = taskqueue_service_pb.TaskQueueAddRequest()
      clone.CopyFrom(add_request)
      clone.clear_transaction()
      new_actions.append(clone)

    self.__tx_actions.extend(new_actions)

  def _Dynamic_Commit(self, transaction, transaction_response):
    self.__ValidateTransaction(transaction)

    try:
      self.__PutEntities(self.__tx_writes.values())
      self.__DeleteEntities(self.__tx_deletes)
      for action in self.__tx_actions:
        try:
          apiproxy_stub_map.MakeSyncCall(
              'taskqueue', 'Add', action, api_base_pb.VoidProto())
        except apiproxy_errors.ApplicationError, e:
          logging.warning('Transactional task %s has been dropped, %s',
                          action, e)
          pass
    finally:
      self.__tx_writes = {}
      self.__tx_deletes = set()
      self.__tx_actions = []
      self.__tx_lock.release()

  def _Dynamic_Rollback(self, transaction, transaction_response):
    self.__ValidateTransaction(transaction)

    self.__tx_writes = {}
    self.__tx_deletes = set()
    self.__tx_actions = []
    self.__tx_lock.release()

  def _Dynamic_GetSchema(self, app_str, schema):
    # TODO this is used for the admin viewer to introspect.
    pass

  def __collection_and_spec_for_index(self, index):
    def translate_name(ae_name):
      if ae_name == "__key__":
        return "_id"
      return ae_name

    def translate_direction(ae_dir):
      if ae_dir == 1:
        return pymongo.ASCENDING
      elif ae_dir == 2:
        return pymongo.DESCENDING
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'Weird direction.')

    collection = index.definition().entity_type()
    spec = []
    for prop in index.definition().property_list():
      spec.append(
        (translate_name(prop.name()), translate_direction(prop.direction())))

    return (collection, spec)

  def _Dynamic_AllocateIds(self, allocate_ids_request, allocate_ids_response):
    model_key = allocate_ids_request.model_key()
    kind = model_key.path().element(0).type()
    if allocate_ids_request.has_size() and allocate_ids_request.has_max():
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'Both size and max cannot be set.')

    if allocate_ids_request.has_size():
      if allocate_ids_request.size() < 1:
        raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                               'Size must be greater than 0.')
      first_id = self.__allocate_ids(kind, size=allocate_ids_request.size())
      allocate_ids_response.set_start(first_id)
      allocate_ids_response.set_end(first_id + allocate_ids_request.size() - 1)
    else:
      if allocate_ids_request.max() < 0:
        raise apiproxy_errors.ApplicationError(
            datastore_pb.Error.BAD_REQUEST,
            'Max must be greater than or equal to 0.')
      first_id = self.__allocate_ids(kind, max=allocate_ids_request.max())
      allocate_ids_response.set_start(first_id)
      allocate_ids_response.set_end(max(allocate_ids_request.max(),
                                        first_id - 1))

  def __gen_index_name(self, keys):
    """Generate an index name from the set of fields it is over."""

    return u"_".join([u"%s_%s" % item for item in keys])

  def __has_index(self, index):
    (collection, spec) = self.__collection_and_spec_for_index(index)
    if (self.__gen_index_name(spec)
        in self.__db[collection].index_information().keys()):
      return True
    return False

  def _Dynamic_CreateIndex(self, index, id_response):
    if index.id() != 0:
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'New index id must be 0.')
    elif self.__has_index(index):
      logging.getLogger().info(index)
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'Index already exists.')

    (collection, spec) = self.__collection_and_spec_for_index(index)

    if spec: # otherwise it's probably an index w/ just an ancestor specifier
      self.__db[collection].create_index(spec)
      if self.__db.error():
        raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                               'Error creating index. Maybe '
                                               'too many indexes?')

    # NOTE just give it a dummy id. we don't use these for anything...
    id_response.set_value(1)

  def _Dynamic_GetIndices(self, app_str, composite_indices):
    if app_str.value() != self.__db.name():
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             'Getting indexes for a different '
                                             'app unsupported.')

    def from_index_name(name):
      elements = name.split("_")
      index = []
      while len(elements):
        if not elements[0]:
          elements = elements[1:]
          elements[0] = "_" + elements[0]
        index.append((elements[0], int(elements[1])))
        elements = elements[2:]
      return index

    for collection in self.__db.collection_names():
      info = self.__db[collection].index_information()
      for index in info.keys():
        index_pb = entity_pb.CompositeIndex()
        index_pb.set_app_id(self.__db.name())
        index_pb.mutable_definition().set_entity_type(collection)
        index_pb.mutable_definition().set_ancestor(False)
        index_pb.set_state(2) # READ_WRITE
        index_pb.set_id(1) # bogus id
        for (k, v) in from_index_name(index):
          if k == "_id":
            k = "__key__"
          p = index_pb.mutable_definition().add_property()
          p.set_name(k)
          p.set_direction(v == pymongo.ASCENDING and 1 or 2)
        composite_indices.index_list().append(index_pb)

  def _Dynamic_UpdateIndex(self, index, void):
    logging.log(logging.WARN, 'update index unsupported')

  def _Dynamic_DeleteIndex(self, index, void):
    (collection, spec) = self.__collection_and_spec_for_index(index)
    if not spec:
      return

    if not self.__has_index(index):
      raise apiproxy_errors.ApplicationError(datastore_pb.Error.BAD_REQUEST,
                                             "Index doesn't exist.")
    self.__db[collection].drop_index(spec)
