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
"""Using the Files API."""

from google.appengine.api import files
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

import urllib


class MainHandler(webapp.RequestHandler):
    """Provides a tiny UI for reading or creating a file."""

    def get(self, key):
        """Reads a stored file."""

        key = urllib.unquote(key or "foobar")

        try:
            f = files.open("/blobstore/%s" % key, "r")
            text = f.read(100)
            f.close()
        except (files.InvalidFileNameError, files.FinalizationError):
            text = "Not found"

        output = webapp.template.render('files.html', {'text': text})

        self.response.out.write(output)

    def post(self, unused_key):
        """Creates a file from the posted data."""

        filename = files.blobstore.create()

        f = files.open(filename, "a")
        f.write(self.request.get('text'))
        f.close()

        files.finalize(filename)

        self.redirect('/')


app = webapp.WSGIApplication([
    ('/files/([^/]+)?', MainHandler),
], debug=True)


def main():
    """The main function."""

    webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
