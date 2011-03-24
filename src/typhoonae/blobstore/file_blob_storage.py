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
"""TyphoonAE's implementation of Blobstore stub storage.

Reuses code from Google App Engine SDK.
"""

from google.appengine.api import blobstore
from google.appengine.api import datastore_types
from typhoonae.blobstore import handlers

import errno
import os


__all__ = ['FileBlobStorage']


class FileBlobStorage(blobstore.blobstore_stub.BlobStorage):
    """Handles blob files stored on disk."""

    def __init__(self, storage_directory, app_id):
        """Constructor.

        Args:
            storage_directory: Directory within which to store blobs.
            app_id: App id to store blobs on behalf of.
        """
        self._storage_directory = storage_directory
        self._app_id = app_id

    @classmethod
    def _BlobKey(cls, blob_key):
        """Normalize to instance of BlobKey."""

        if not isinstance(blob_key, blobstore.BlobKey):
            return blobstore.BlobKey(unicode(blob_key))

        return blob_key

    def _DirectoryForBlob(self, blob_key):
        """Determine which directory where a blob is stored.

        Args:
            blob_key: Blob key to determine directory for.

        Returns:
            Directory relative to this objects storage directory to where
            blob is stored or should be stored.
        """
        blob_path = handlers.DecodeBlobKey(blob_key)

        d = os.path.join(self._storage_directory, self._app_id, blob_path[-1])

        return d

    def _FileForBlob(self, blob_key):
        """Calculate full filename to store blob contents in.

        This method does not check to see if the file actually exists.

        Args:
            blob_key: Blob key of blob to calculate file for.

        Returns:
            Complete path for file used for storing blob.
        """
        blob_path = handlers.DecodeBlobKey(blob_key)

        f = os.path.join(self._storage_directory, self._app_id,
                         blob_path[-1], blob_path)
        return f

    def StoreBlob(self, blob_key, blob_stream):
        """Store blob stream to disk.

        Args:
            blob_key: Blob key of blob to store.
            blob_stream: Stream or stream-like object that will generate blob
                content.
        """
        blob_key = self._BlobKey(blob_key)
        blob_directory = self._DirectoryForBlob(blob_key)
        if not os.path.exists(blob_directory):
            os.makedirs(blob_directory)
        blob_file = self._FileForBlob(blob_key)
        output = _local_open(blob_file, 'wb')

        try:
            while True:
                block = blob_stream.read(1 << 20)
                if not block:
                    break
                output.write(block)
        finally:
            output.close()

    def OpenBlob(self, blob_key):
        """Open blob file for streaming.

        Args:
            blob_key: Blob-key of existing blob to open for reading.

        Returns:
            Open file stream for reading blob from disk.
        """
        if isinstance(blob_key, basestring):
            blob_key = datastore_types.Key.from_path('__BlobInfo__', blob_key)
 
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
