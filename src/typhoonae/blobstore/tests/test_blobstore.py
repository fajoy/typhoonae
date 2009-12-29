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
import os
import typhoonae.blobstore.handlers
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
            'test', '', '', require_indexes=False,
            intid_client=TestIntidClient())

        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)


    def testUploadCGIHandler(self):
        environ = dict()
        environ['REQUEST_URI'] = environ['PATH_INFO'] = \
            '/upload/agRkZW1vchsLEhVfX0Jsb2JVcGxvYWRTZXNzaW9uX18YAQw'
        environ['CONTENT_TYPE'] = (
            'multipart/form-data; '
            'boundary=----WebKitFormBoundarygS2PUgJ8Rnizqyb0')

        buf = """------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.name"

myimage.jpg
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.content_type"

image/jpeg
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.path"

/some/path/to/blobstore/8/0000000018
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.md5"

5820acc74923923093dbe8d42963f37c
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="file.size"

1538106
------WebKitFormBoundarygS2PUgJ8Rnizqyb0
Content-Disposition: form-data; name="submit"

Submit
------WebKitFormBoundarygS2PUgJ8Rnizqyb0--
"""

        fp = cStringIO.StringIO(buf)

        handler = typhoonae.blobstore.handlers.UploadCGIHandler()
        fp = handler(fp, environ)


if __name__ == "__main__":
    unittest.main()
