# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc., 2011 Tobias Rodäbel.
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
"""TyphoonAE's Files API proxy stub implementation.

Substantial portions of the following code are copied from the original Files
API proxy stub of the Google App Engine SDK.
"""

from google.appengine.api import apiproxy_stub
from google.appengine.api.files import blobstore as files_blobstore
from google.appengine.api.files import file_service_pb
from google.appengine.api.files import file_service_stub
from google.appengine.runtime import apiproxy_errors
from google.appengine.tools import dev_appserver_upload
import base64
import random
import string


class FileStorage(file_service_stub.FileStorage):
    """Virtual file storage to be used by file api.

    Abstracts away all aspects of logical and physical file organization of
    the API.
    """


class BlobstoreFile(file_service_stub.BlobstoreFile):
    """File object for generic '/blobstore/' file."""


class FileServiceStub(apiproxy_stub.APIProxyStub):
    """Python stub for file service."""

    def __init__(self, blob_storage):
        """Constructor."""
        super(FileServiceStub, self).__init__('file')
        self.open_files = {}
        self.file_storage = FileStorage(blob_storage)

    def _Dynamic_Create(self, request, response):
        filesystem = request.filesystem()

        if filesystem != files_blobstore._BLOBSTORE_FILESYSTEM:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.UNSUPPORTED_FILE_SYSTEM)

        if request.has_filename():
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.FILE_NAME_SPECIFIED)

        mime_type = None
        blob_filename = ""
        for param in request.parameters_list():
            name = param.name()
            if name == files_blobstore._MIME_TYPE_PARAMETER:
                mime_type = param.value()
            elif name == files_blobstore._BLOBINFO_UPLOADED_FILENAME_PARAMETER:
                blob_filename = param.value()
            else:
                apiproxy_errors.ApplicationError(
                    file_service_pb.FileServiceErrors.INVALID_PARAMETER)
        if mime_type is None:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.INVALID_PARAMETER)

        random_str = ''.join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(64))

        filename = (files_blobstore._BLOBSTORE_DIRECTORY +
                    files_blobstore._CREATION_HANDLE_PREFIX +
                    base64.urlsafe_b64encode(random_str))
        self.file_storage.add_blobstore_file(filename, mime_type, blob_filename)
        response.set_filename(filename)

    def _Dynamic_Open(self, request, response):
        """Handler for Open RPC call."""

        filename = request.filename()
        content_type = request.content_type()
        open_mode = request.open_mode()

        if filename.startswith('/blobstore/'):
            if request.exclusive_lock() and filename in self.open_files:
                apiproxy_errors.ApplicationError(
                    file_service_pb.FileServiceErrors.EXCLUSIVE_LOCK_FAILED)
            self.open_files[filename] = BlobstoreFile(
                request, self.file_storage)
        else:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.INVALID_FILE_NAME)

    def _Dynamic_Close(self, request, response):
        """Handler for Close RPC call."""

        filename = request.filename()
        finalize = request.finalize()

        if not filename in self.open_files:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.FILE_NOT_OPENED)

        if finalize:
            self.open_files[filename].finalize()

        del self.open_files[filename]

    def _Dynamic_Read(self, request, response):
        """Handler for Read RPC call."""

        filename = request.filename()

        if not filename in self.open_files:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.FILE_NOT_OPENED)

        self.open_files[filename].read(request, response)

    def _Dynamic_Append(self, request, response):
        """Handler for Append RPC call."""

        filename = request.filename()

        if not filename in self.open_files:
            apiproxy_errors.ApplicationError(
                file_service_pb.FileServiceErrors.FILE_NOT_OPENED)

        self.open_files[filename].append(request, response)
