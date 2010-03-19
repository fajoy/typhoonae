# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc., 2009, 2010 Tobias Rodäbel
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
"""TyphoonAE's Blobstore API stub."""

from google.appengine.api import apiproxy_stub
from google.appengine.api import blobstore
from google.appengine.api import datastore
from google.appengine.api import datastore_errors
from google.appengine.api import datastore_types
from google.appengine.api import users
from google.appengine.api.blobstore import blobstore_service_pb
from google.appengine.api.blobstore import blobstore_stub
from google.appengine.runtime import apiproxy_errors

import os
import time


__all__ = [
    'BlobstoreServiceStub',
    'CreateUploadSession',
]


_UPLOAD_SESSION_KIND = '__BlobUploadSession__'


def CreateUploadSession(creation, success_path, user):
    """Create upload session in datastore.

    Creates an upload session and puts it in Datastore to be referenced by
    upload handler later.

    Args:
        creation: Creation timestamp.
        success_path: Path in users application to call upon success.
        user: User that initiated this upload, if any.

    Returns:
        String encoded key of new Datastore entity.
    """
    entity = datastore.Entity(_UPLOAD_SESSION_KIND)
    entity.update({
        'creation': creation,
        'success_path': success_path,
        'user': user,
        'state': 'init'
    })
    datastore.Put(entity)
    return str(entity.key())


class BlobstoreServiceStub(apiproxy_stub.APIProxyStub):
    """TyphoonAE's blobstore service stub."""

    def __init__(self,
                 blob_storage,
                 time_function=time.time,
                 service_name='blobstore',
                 uploader_path='upload/'):
        """Constructor.

        Args:
            blob_storage: BlobStorage class instance used for blob storage.
            time_function: Used for dependency injection in tests.
            service_name: Service name expected for all calls.
            uploader_path: Path to upload handler pointed to by URLs generated
                by this service stub.
        """
        super(BlobstoreServiceStub, self).__init__(service_name)
        self.__storage = blob_storage
        self.__time_function = time_function
        self.__uploader_path = uploader_path

    @property
    def storage(self):
        """Access BlobStorage used by service stub.

        Returns:
            BlobStorage instance used by blobstore service stub.
        """
        return self.__storage

    def _GetEnviron(self, name):
        """Helper method ensures environment configured as expected.

        Args:
            name: Name of environment variable to get.

        Returns:
            Environment variable associated with name.

        Raises:
            ConfigurationError if required environment variable is not found.
        """
        try:
            return os.environ[name]
        except KeyError:
            raise blobstore_stub.ConfigurationError(
                '%s is not set in environment.' % name)

    def _CreateSession(self, success_path, user):
        """Create new upload session.

        Args:
            success_path: Application path to call upon successful POST.
            user: User that initiated the upload session.

        Returns:
            String encoded key of a new upload session created in the datastore.
        """
        return CreateUploadSession(self.__time_function(), success_path, user)

    def _Dynamic_CreateUploadURL(self, request, response):
        """Create upload URL implementation.

        Create a new upload session.  The upload session key is encoded in the
        resulting POST URL.  This URL is embedded in a POST form by the
        application which contacts the uploader when the user posts.

        Args:
            request: A fully initialized CreateUploadURLRequest instance.
            response: A CreateUploadURLResponse instance.
        """
        session = self._CreateSession(
            request.success_path(), users.get_current_user())

        response.set_url('http://%s:%s/%s%s' % (self._GetEnviron('SERVER_NAME'),
                                                self._GetEnviron('SERVER_PORT'),
                                                self.__uploader_path,
                                                session))

    def _Dynamic_DeleteBlob(self, request, response):
        """Delete a blob by its blob-key.

        Delete a blob from the blobstore using its blob-key.  Deleting blobs
        that do not exist is a no-op.

        Args:
            request: A fully initialized DeleteBlobRequest instance.
            response: Not used but should be a VoidProto.
        """
        for blob_key in request.blob_key_list():
            key = datastore_types.Key.from_path('__BlobInfo__', str(blob_key))
            self.__storage.DeleteBlob(key)
            datastore.Delete(key)

    def _Dynamic_FetchData(self, request, response):
        """Fetch a blob fragment from a blob by its blob-key.

        Fetches a blob fragment using its blob-key.  Start index is inclusive,
        end index is inclusive.  Valid requests for information outside of
        the range of the blob return a partial string or empty string if
        entirely out of range.

        Args:
            request: A fully initialized FetchDataRequest instance.
            response: A FetchDataResponse instance.

        Raises:
            ApplicationError when application has the following errors:
                INDEX_OUT_OF_RANGE: Index is negative or end > start.
                BLOB_FETCH_SIZE_TOO_LARGE: Request blob fragment is larger than
                  MAX_BLOB_FRAGMENT_SIZE.
                BLOB_NOT_FOUND: If invalid blob-key is provided or is not found.
        """
        start_index = request.start_index()
        if start_index < 0:
            raise apiproxy_errors.ApplicationError(
                blobstore_service_pb.BlobstoreServiceError.
                DATA_INDEX_OUT_OF_RANGE)

        end_index = request.end_index()
        if end_index < start_index:
            raise apiproxy_errors.ApplicationError(
                blobstore_service_pb.BlobstoreServiceError.
                DATA_INDEX_OUT_OF_RANGE)

        fetch_size = end_index - start_index + 1
        if fetch_size > blobstore.MAX_BLOB_FETCH_SIZE:
            raise apiproxy_errors.ApplicationError(
                blobstore_service_pb.BlobstoreServiceError.
                BLOB_FETCH_SIZE_TOO_LARGE)

        blob_key = request.blob_key()
        blob_info_key = datastore.Key.from_path(
            blobstore.BLOB_INFO_KIND, blob_key)
        try:
            datastore.Get(blob_info_key)
        except datastore_errors.EntityNotFoundError, err:
            raise apiproxy_errors.ApplicationError(
                blobstore_service_pb.BlobstoreServiceError.BLOB_NOT_FOUND)

        blob_file = self.__storage.OpenBlob(blob_key)
        blob_file.seek(start_index)
        response.set_data(blob_file.read(fetch_size))
