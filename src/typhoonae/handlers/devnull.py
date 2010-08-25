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
"""Dev null handler."""

import google.appengine.ext.webapp
import google.appengine.ext.webapp.util


class DevNullHandler(google.appengine.ext.webapp.RequestHandler):
    """ """

    def get(self):
        pass

    def post(self):
        pass


app = google.appengine.ext.webapp.WSGIApplication([
    ('/_ah/dev/null', DevNullHandler),
], debug=True)


def main():
    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
