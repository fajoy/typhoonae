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
"""Failure request handlers."""

import google.appengine.ext.webapp
import logging
import os


class FailureRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Simple request handler."""

    def get(self):
        """Handles get."""

        logging.error(self.request)
        self.response.set_status(404)
        self.response.out.write("<html><body>Not found!")
        self.response.out.write("<ul>")
        for k in os.environ:
            self.response.out.write("<li>%s: %s</li>" % (k, os.environ[k]))
        self.response.out.write("</ul>")
        self.response.out.write("</body></html>")


app = google.appengine.ext.webapp.WSGIApplication([
    ('.*', FailureRequestHandler),
], debug=True)


def main():
    """The main function."""

    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
