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

import google.appengine.api.files
import google.appengine.ext.webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
import urllib


class MainHandler(google.appengine.ext.webapp.RequestHandler):
    """Provides a tiny UI for creating a file."""

    def get(self, key):
        """Handles get."""

        key = urllib.unquote(key or "foobar")

        try:
            f = google.appengine.api.files.open("/blobstore/%s" % key, "r")
            text = f.read(100)
            f.close()
        except (google.appengine.api.files.InvalidFileNameError,
                google.appengine.api.files.FinalizationError):
            text = "Not found"

        output = google.appengine.ext.webapp.template.render(
            'files.html', {'text': text})

        self.response.out.write(output)

    def post(self, unused_key):
        """Handles post."""

        text = self.request.get('text')

        filename = google.appengine.api.files.blobstore.create()

        try:
            f = google.appengine.api.files.open(filename, "a")
            f.write(text)
            f.close()
            google.appengine.api.files.finalize(filename)
        except (google.appengine.api.files.InvalidFileNameError,
                google.appengine.api.files.ExistenceError), e:
            import cgi
            text = cgi.escape(repr(e))

        self.redirect('/')


app = google.appengine.ext.webapp.WSGIApplication([
    ('/files/([^/]+)?', MainHandler),
], debug=True)


def main():
    """The main function."""

    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
