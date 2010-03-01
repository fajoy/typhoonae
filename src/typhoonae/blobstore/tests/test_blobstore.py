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


if __name__ == "__main__":
    unittest.main()
