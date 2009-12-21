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
"""TyphoonAE's handler library for Blobstore API."""

import base64
import cStringIO
import cgi
import datetime
import google.appengine.api.blobstore
import google.appengine.api.datastore
import google.appengine.api.datastore_errors
import logging
import md5
import random
import re
import time


UPLOAD_URL_PATTERN = '/%s(.*)'

CONTENT_PART = """Content-Type: message/external-body; blob-key="%(blob_key)s"; access-type="X-AppEngine-BlobKey"
MIME-Version: 1.0
Content-Disposition: form-data; name="file"; filename="%(filename)s"

Content-Type: %(content_type)s
MIME-Version: 1.0
Content-Length: %(content_length)s
content-type: %(content_type)s
content-disposition: form-data; name="file"; filename="%(filename)s"
X-AppEngine-Upload-Creation: %(timestamp)s

"""

SIMPLE_FIELD = """Content-Type: text/plain
MIME-Version: 1.0
Content-Disposition: form-data; name="%(name)s"

%(value)s"""


def generateBlobKey():
    """Generates a unique BlobKey.

    Returns:
        String version of BlobKey that is unique within the BlobInfo datastore.
        None if there are too many name conflicts.
    """
    timestamp = str(time.time())
    tries = 0
    while tries < 10:
        number = str(random.random())
        digester = md5.md5()
        digester.update(timestamp)
        digester.update(number)
        blob_key = base64.urlsafe_b64encode(digester.digest())
        datastore_key = google.appengine.api.datastore.Key.from_path(
            google.appengine.api.blobstore.BLOB_INFO_KIND, blob_key)
        try:
            google.appengine.api.datastore.Get(datastore_key)
            tries += 1
        except google.appengine.api.datastore_errors.EntityNotFoundError:
            return blob_key
    return None


class UploadCGIHandler(object):
    """Handles upload posts for the Blobstore API."""

    def __init__(self, upload_url='upload/'):
        """Constructor.

        Args:
            upload_url: URL which will be used for uploads.
        """

        self.upload_url = upload_url

    def __call__(self, fp, environ):
        """Executes the handler.

        Args:
            fp: A file pointer to the CGI input stream.
            environ: The CGI environment.

        Returns:
            File pointer to the CGI input stream.
        """

        match = re.match(UPLOAD_URL_PATTERN % self.upload_url,
                         environ['PATH_INFO'])
        if match == None:
            return fp

        upload_session_key = match.group(1)

        try:
            upload_session = google.appengine.api.datastore.Get(
                upload_session_key)
        except google.appengine.api.datastore_errors.EntityNotFoundError:
            logging.error('Upload session %s not found' % upload_session_key)
            upload_session = None

        if self.upload_url.endswith('/'):
            upload_url = self.upload_url[:-1]
        else:
            upload_url = self.upload_url
        environ['PATH_INFO'] = environ['REQUEST_URI'] = '/' + upload_url

        def splitContentType(content_type):
            parts = content_type.split(';')
            pairs = dict([(key.lower().strip(), value) for key, value
                          in [p.split('=', 1) for p in parts[1:]]])
            return parts[0].strip(), pairs
 
        main_type, key_values = splitContentType(environ['CONTENT_TYPE'])
        boundary = key_values.get('boundary')

        form_data = cgi.parse_multipart(fp, {'boundary': boundary})
        data = dict([(k, ''.join(form_data[k])) for k in form_data])

        fields = set([k.split('.')[0] for k in data.keys() if k != 'submit'])


        def format_timestamp(stamp):
            f = google.appengine.api.blobstore.BASE_CREATION_HEADER_FORMAT
            return '%s.%06d' % (stamp.strftime(f), stamp.microsecond)

        meta_data = {}

        for field in fields:
            meta_data[field+'.timestamp'] = format_timestamp(
                datetime.datetime.now())
            meta_data[field+'.blobkey'] = str(generateBlobKey())

        for field in fields:
            blob_entity = google.appengine.api.datastore.Entity(
                '__BlobInfo__', name=meta_data[field+'.blobkey'])
            blob_entity['content_type'] = data[field+'.content_type']
            blob_entity['creation'] = meta_data[field+'.timestamp']
            blob_entity['filename'] = data[field+'.name']
            blob_entity['size'] = int(data[field+'.size'])
            google.appengine.api.datastore.Put(blob_entity)

        message = []
        for field in fields:
            message.append('--' + boundary)
            values = dict(
                blob_key=meta_data[field+'.blobkey'],
                filename=data[field+'.name'],
                content_type=data[field+'.content_type'],
                content_length=data[field+'.size'],
                timestamp=meta_data[field+'.timestamp']
            )
            message.append(CONTENT_PART % values)

        if 'submit' in data.keys():
            message.append('--' + boundary)
            message.append(SIMPLE_FIELD %
                           {'name': 'submit', 'value': data['submit']})
                
        message += ['--' + boundary + '--']

        message = '\n'.join(message)

        if upload_session:
            google.appengine.api.datastore.Delete(upload_session)

        environ['HTTP_CONTENT_LENGTH'] = str(len(message))

        return cStringIO.StringIO(message)
