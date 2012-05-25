# -*- coding: utf-8 -*-
#
# Copyright 2010 Tobias Rodäbel
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
"""Images handler."""

import google.appengine.ext.webapp
import google.appengine.ext.webapp.util
import logging
import os


class ImagesHandler(google.appengine.ext.webapp.RequestHandler):
    """Images handler takes care of image resizing and cropping on blobs."""

    def get(self):
        image_file = open(
            os.path.join(os.path.dirname(__file__), 'dummy.png'), 'rb')
        image_data = image_file.read()
        image_file.close()
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(image_data)


app = google.appengine.ext.webapp.WSGIApplication([
    ('/_ah/img(?:/.*)?', ImagesHandler),
], debug=True)


def main():
    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
