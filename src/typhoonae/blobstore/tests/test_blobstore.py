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
"""Unit tests for TyphoonAE's Blobstore implementation."""

import cStringIO
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.datastore
import google.appengine.api.datastore_types
import google.appengine.ext.blobstore
import google.appengine.ext.db
import logging
import os
import typhoonae.blobstore.handlers
import typhoonae.blobstore.blobstore_stub
import typhoonae.blobstore.file_blob_storage
import typhoonae.mongodb.datastore_mongo_stub
import unittest


class TestIntidClient(object):
    """Pretends to be an intid server client."""

    def __init__(self, host=None, port=None):
        self.value = 0

    def get(self):
        self.value += 1
        return self.value

    def close(self):
        pass


class BlobstoreTestCase(unittest.TestCase):
    """Testing Blobstore."""

    def setUp(self):
        """Register typhoonae's memcache API proxy stub."""

        os.environ['APPLICATION_ID'] = 'test'
        os.environ['AUTH_DOMAIN'] = 'yourdomain.net'
        os.environ['SERVER_NAME'] = 'server'
        os.environ['SERVER_PORT'] = '9876'
        os.environ['USER_EMAIL'] = 'test@yourdomain.net'

        google.appengine.api.apiproxy_stub_map.apiproxy = \
                    google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

        datastore = typhoonae.mongodb.datastore_mongo_stub.DatastoreMongoStub(
            'test', '', require_indexes=False, intid_client=TestIntidClient())

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        try:
            from google.appengine.api.images import images_stub
            google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
                'images',
                images_stub.ImagesServiceStub())
        except ImportError, e:
            logging.warning(
                'Could not initialize images API; you are likely '
                'missing the Python "PIL" module. ImportError: %s', e)
            from google.appengine.api.images import images_not_implemented_stub
            google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
                'images',
                images_not_implemented_stub.ImagesNotImplementedServiceStub())

        storage = typhoonae.blobstore.file_blob_storage.FileBlobStorage(
            os.path.dirname(__file__), 'test')

        self.storage = storage

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'blobstore',
            typhoonae.blobstore.blobstore_stub.BlobstoreServiceStub(storage))

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

/test.png
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

        handler = typhoonae.blobstore.handlers.UploadCGIHandler()
        fp = handler(fp, environ)

    def tearDown(self):
        """Clean up."""

        query = google.appengine.ext.blobstore.BlobInfo.all()
        cursor = query.fetch(10)

        for b in cursor:
            key = google.appengine.api.datastore_types.Key.from_path(
                '__BlobInfo__', str(b.key()))
            google.appengine.api.datastore.Delete(key)

    def testCreateUploadSession(self):
        """Creates an upload session entity."""

        stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'blobstore')
        session = stub._CreateSession('foo', 'bar')
        self.assertNotEqual(None, session)

    def testGetEnviron(self):
        """Tests internal helper method to obtain environment variables."""

        from google.appengine.api.blobstore import blobstore_stub
        stub = google.appengine.api.apiproxy_stub_map.apiproxy.GetStub(
            'blobstore')
        os.environ['TEST_ENV_VAR'] = 'blobstore-test'
        self.assertEqual('blobstore-test', stub._GetEnviron('TEST_ENV_VAR'))
        self.assertRaises(
            blobstore_stub.ConfigurationError,
            stub._GetEnviron,
            'UNKNOWN_ENV_VAR')

    def testCreateUploadURL(self):
        """Creates an upload URL."""

        upload_url = google.appengine.api.blobstore.create_upload_url('foo')
        self.assertTrue(upload_url.startswith('http://server:9876/upload/'))

    def testBlobInfo(self):
        """Tests retreiving a BlobInfo entity."""

        result = google.appengine.ext.blobstore.BlobInfo.all().fetch(1)
        self.assertEqual(google.appengine.ext.blobstore.BlobInfo,
                         type(result.pop()))

    def testBlobKey(self):
        """Tests whether a valid BlobKey can be stored in the datastore."""

        class MyModel(google.appengine.ext.db.Model):
            file = google.appengine.ext.blobstore.BlobReferenceProperty()

        entity = MyModel()
        result = google.appengine.ext.blobstore.BlobInfo.all().fetch(1)
        entity.file = result.pop()
        entity.put()

        fetched_entity = MyModel.all().fetch(1).pop()
        self.assertEqual(3943L, fetched_entity.file.size)
        self.assertEqual(google.appengine.api.datastore_types.BlobKey,
                         type(fetched_entity.file.key()))

    def testOpenBlob(self):
        """Opens a blob file for streaming."""

        query = google.appengine.ext.blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        self.storage.OpenBlob(key)

    def testImage(self):
        """Creates an image object from blob data."""

        from google.appengine.api.images import Image
        query = google.appengine.ext.blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        img = Image(blob_key=key)
        img.resize(width=200)
        data = img.execute_transforms()
        thumbnail = Image(data)
        self.assertEqual(200, thumbnail.width)

    def testFetchData(self):
        """Fetches data for blob."""

        query = google.appengine.ext.blobstore.BlobInfo.all()
        key = str(query.fetch(1).pop().key())
        data = google.appengine.ext.blobstore.fetch_data(key, 0, 5)
        self.assertEqual('\x89PNG\r\n', data)


if __name__ == "__main__":
    unittest.main()
