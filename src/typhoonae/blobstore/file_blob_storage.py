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
"""TyphoonAE's implementation of Blobstore stub storage."""

import errno
import google.appengine.api.blobstore
import google.appengine.api.blobstore.blobstore_stub
import google.appengine.api.datastore
import google.appengine.api.datastore_types
import os


__all__ = ['FileBlobStorage']


class FileBlobStorage(
        google.appengine.api.blobstore.blobstore_stub.BlobStorage):
    """Handles blob files stored on disk."""

    def __init__(self, storage_directory, app_id):
        """Constructor.

        Args:
            storage_directory: Directory within which to store blobs.
            app_id: App id to store blobs on behalf of.
        """
        self._storage_directory = storage_directory
        self._app_id = app_id

    def _FileForBlob(self, blob_key):
        """Calculate full filename to store blob contents in.

        This method does not check to see if the file actually exists.

        Args:
            blob_key: Blob key of blob to calculate file for.

        Returns:
            Complete path for file used for storing blob.
        """
        try:
            blob_info = google.appengine.api.datastore.Get(blob_key)
        except google.appengine.api.datastore_errors.EntityNotFoundError:
            return ''

        blob_path = blob_info['path']

        f = os.path.join(self._storage_directory, self._app_id,
                         blob_path[-1], blob_path)
        return f

    def OpenBlob(self, blob_key):
        """Open blob file for streaming.

        Args:
            blob_key: Blob-key of existing blob to open for reading.

        Returns:
            Open file stream for reading blob from disk.
        """
        if isinstance(blob_key, basestring):
            blob_key = google.appengine.api.datastore_types.Key.from_path(
                '__BlobInfo__', blob_key)
 
        return open(self._FileForBlob(blob_key), 'rb')

    def DeleteBlob(self, blob_key):
        """Delete blob data from disk.

        Deleting an unknown blob will not raise an error.

        Args:
            blob_key: Blob-key of existing blob to delete.
        """
        try:
            os.remove(self._FileForBlob(blob_key))
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise e
