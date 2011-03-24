# -*- coding: utf-8 -*-
#
# Copyright 2011 Tobias Rodäbel.
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
"""TyphoonAE's Files API proxy stub implementation."""

from google.appengine.api.files import file_service_pb
from google.appengine.api.files import file_service_stub
from google.appengine.tools import dev_appserver_upload


class BlobstoreFile(file_service_stub.BlobstoreFile):
    """File object for generic '/blobstore/' file."""

    def finalize(self):
        """Finalize a file."""

        raise NotImplementedError


class FileServiceStub(file_service_stub.FileServiceStub):
    """Python stub for file service."""

    def _Dynamic_Open(self, request, response):
        """Handler for Open RPC call."""

        filename = request.filename()
        content_type = request.content_type()
        open_mode = request.open_mode()

        if filename.startswith('/blobstore/'):
            self.open_files[filename] = BlobstoreFile(
                request, self.file_storage)
        else:
            raise_error(file_service_pb.FileServiceErrors.INVALID_FILE_NAME)
