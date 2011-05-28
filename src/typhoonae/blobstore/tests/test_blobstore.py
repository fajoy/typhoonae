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
"""Unit tests for TyphoonAE's Blobstore implementation."""

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore
from google.appengine.api import datastore_file_stub
from google.appengine.api import datastore_types
from google.appengine.ext import blobstore
from typhoonae.blobstore import handlers
from typhoonae.blobstore import blobstore_stub
from typhoonae.blobstore import file_blob_storage

import cStringIO
import logging
import os
import tempfile
import unittest


class BlobstoreTestCase(unittest.TestCase):
    """Testing Blobstore."""

    def setUp(self):
        """Setup TyphoonAE's Blobstore API proxy stub and test data."""

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

        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', datastore_stub)

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

    def testCreateUploadSession(self):
        """Creates an upload session entity."""

        stub = apiproxy_stub_map.apiproxy.GetStub('blobstore')
        session = stub._CreateSession('foo', 'bar')
        self.assertNotEqual(None, session)

    def testGetEnviron(self):
        """Tests internal helper method to obtain environment variables."""

        stub = apiproxy_stub_map.apiproxy.GetStub('blobstore')
        os.environ['TEST_ENV_VAR'] = 'blobstore-test'
        self.assertEqual('blobstore-test', stub._GetEnviron('TEST_ENV_VAR'))
        self.assertRaises(
            blobstore_stub.ConfigurationError,
            stub._GetEnviron,
            'UNKNOWN_ENV_VAR')

    def testCreateUploadURL(self):
        """Creates an upload URL."""

        import google.appengine.api.blobstore

        upload_url = google.appengine.api.blobstore.create_upload_url('foo')
        self.assertTrue(upload_url.startswith('http://server:9876/upload/'))

    def testBlobInfo(self):
        """Tests retreiving a BlobInfo entity."""

        result = blobstore.BlobInfo.all().fetch(1)
        self.assertEqual(blobstore.BlobInfo,
                         type(result.pop()))

    def testBlobKey(self):
        """Tests whether a valid BlobKey can be stored in the datastore."""

        from google.appengine.ext import db

        class MyModel(db.Model):
            my_file = blobstore.BlobReferenceProperty()

        entity = MyModel()
        result = blobstore.BlobInfo.all().fetch(1)
        entity.my_file = result.pop()
        entity.put()

        fetched_entity = MyModel.all().fetch(1).pop()
        self.assertEqual(3943L, fetched_entity.my_file.size)
        self.assertEqual(
            datastore_types.BlobKey, type(fetched_entity.my_file.key()))

    def testOpenBlob(self):
        """Opens a blob file for streaming."""

        query = blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        self.storage.OpenBlob(key)

    def testImage(self):
        """Creates an image object from blob data."""

        from google.appengine.api.images import Image
        query = blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        img = Image(blob_key=key)
        img.resize(width=200)
        data = img.execute_transforms()
        thumbnail = Image(data)
        self.assertEqual(200, thumbnail.width)

    def testFetchData(self):
        """Fetches data for blob."""

        query = blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        data = blobstore.fetch_data(key, 0, 5)
        self.assertEqual('\x89PNG\r\n', data)

    def testBlobReader(self):
        """Tests the BlobReader API."""

        query = blobstore.BlobInfo.all()
        blob_info = query.fetch(1).pop()
        blob_key = str(blob_info.key())

        reader = blobstore.BlobReader(blob_key)
        self.assertEqual(blob_info.filename, reader.blob_info.filename)
        self.assertEqual(blob_info.size, reader.blob_info.size)

        data = blobstore.fetch_data(blob_key, 0, 5)
        self.assertEqual(data, reader.read()[:6])
        reader.close()
        self.assertTrue(reader.closed)
