# -*- coding: utf-8 -*-
#
# Copyright 2011 Tobias Rodäbel
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
"""Unit tests for TyphoonAE's Files API implementation."""

from __future__ import with_statement

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore
from google.appengine.api import datastore_file_stub
from google.appengine.api import datastore_types
from google.appengine.api import files
from google.appengine.ext import blobstore
from typhoonae.blobstore import handlers
from typhoonae.blobstore import blobstore_stub
from typhoonae.blobstore import file_blob_storage
from typhoonae.files import file_service_stub

import cStringIO
import logging
import os
import tempfile
import unittest


class FilesTestCase(unittest.TestCase):
    """Testing the Files API."""

    def setUp(self):
        """Register API proxy stubs and add some test data."""

        os.environ['APPLICATION_ID'] = 'demo'
        os.environ['AUTH_DOMAIN'] = 'yourdomain.net'
        os.environ['SERVER_NAME'] = 'server'
        os.environ['SERVER_PORT'] = '9876'
        os.environ['USER_EMAIL'] = 'test@yourdomain.net'

        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

        self.datastore_path = tempfile.mktemp('db')

        datastore_stub = datastore_file_stub.DatastoreFileStub(
            'demo', self.datastore_path, require_indexes=False,
            trusted=False)

        apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore_stub)

        try:
            from google.appengine.api.images import images_stub
            apiproxy_stub_map.apiproxy.RegisterStub(
                'images',
                images_stub.ImagesServiceStub())
        except ImportError, e:
            logging.warning(
                'Could not initialize images API; you are likely '
                'missing the Python "PIL" module. ImportError: %s', e)
            from google.appengine.api.images import images_not_implemented_stub
            apiproxy_stub_map.apiproxy.RegisterStub(
                'images',
                images_not_implemented_stub.ImagesNotImplementedServiceStub())

        storage = file_blob_storage.FileBlobStorage(
            os.path.dirname(__file__), 'demo')

        self.storage = storage

        apiproxy_stub_map.apiproxy.RegisterStub(
            'blobstore', blobstore_stub.BlobstoreServiceStub(storage))

        apiproxy_stub_map.apiproxy.RegisterStub(
            'file', file_service_stub.FileServiceStub(storage))

        environ = dict()
        environ['REQUEST_URI'] = environ['PATH_INFO'] = \
            '/upload/agRkZW1vchsLEhVfX0Jsb2JVcGxvYWRTZXNzaW9uX18YAQw'
        environ['CONTENT_TYPE'] = (
            'multipart/form-data; '
            'boundary=----WebKitFormBoundarygS2PUgJ8Rnizqyb0')

        buf = """------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.name"

test.png
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.content_type"

image/png
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.path"

/0000000001
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.md5"

da945dc0237f4efeed952c249a0d3805
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.size"

3943
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="submit"

Submit
------WebKitFormBoundarygS2PUgJ8Rnizqyb0--
"""

        fp = cStringIO.StringIO(buf)

        handler = handlers.UploadCGIHandler()
        fp = handler(fp, environ)

    def tearDown(self):
        """Clean up."""

        query = blobstore.BlobInfo.all()
        cursor = query.fetch(10)

        for b in cursor:
            key = datastore_types.Key.from_path('__BlobInfo__', str(b.key()))
            datastore.Delete(key)

        os.unlink(self.datastore_path)

    def testOpenFile(self):
        """Tests opening a file."""

        # Get blob key
        query = blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
 
        # Open the file for reading
        f = files.open("/blobstore/%s" % key, "r")

        # Read data and close file
        data = f.read(10)
        f.close()

        self.assertEqual('\x89PNG\r\n\x1a\n\x00\x00', data)

    def testWriteFile(self):
        """Tests writing files."""

        # Create the file
        file_name = files.blobstore.create(mime_type='application/octet-stream')

        # Open the file and write to it
        with files.open(file_name, 'a') as f:
            f.write('data')

        # Finalize the file and get its blob key
        files.finalize(file_name)
        blob_key = files.blobstore.get_blob_key(file_name)

        # Check file contents
        f = files.open("/blobstore/%s" % blob_key, "r")
        self.assertEqual('data', f.read(10))
        f.close()

        # Clean up
        blobstore_stub = apiproxy_stub_map.apiproxy.GetStub('blobstore')
        blobstore_stub.storage.DeleteBlob(blob_key)
