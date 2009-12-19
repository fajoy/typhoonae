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
"""Blobstore handlers."""

import google.appengine.ext.blobstore
import google.appengine.ext.webapp
import google.appengine.ext.webapp.blobstore_handlers
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
import logging
import urllib


class MainHandler(google.appengine.ext.webapp.RequestHandler):
    """Provides the file upload form."""

    def get(self):
        """Handles get."""

        upload_url = google.appengine.ext.blobstore.create_upload_url('/upload')
        output = google.appengine.ext.webapp.template.render(
            'upload.html', {'upload_url': upload_url})
        self.response.out.write(output)


class UploadHandler(
    google.appengine.ext.webapp.blobstore_handlers.BlobstoreUploadHandler):
    """Handles upload of blobs."""

    def post(self):
        """Handles post."""

        logging.info(self.request)
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        self.redirect('/serve/%s' % blob_info.key())


class ServeHandler(
    google.appengine.ext.webapp.blobstore_handlers.BlobstoreDownloadHandler):
    """Serves blobs."""

    def get(self, resource):
        """Handles get."""

        resource = str(urllib.unquote(resource))
        blob_info = google.appengine.ext.blobstore.BlobInfo.get(resource)
        logging.info(blob_info)
        self.send_blob(blob_info)

 
app = google.appengine.ext.webapp.WSGIApplication([
    ('/blobstore', MainHandler),
    ('/upload', UploadHandler),
    ('/serve/([^/]+)?', ServeHandler),
], debug=True)


def main():
    """The main function."""

    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
