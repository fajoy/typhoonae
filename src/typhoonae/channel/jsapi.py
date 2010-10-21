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
"""Implementation of a request handler providing the Channel JS API."""

import google.appengine.ext.webapp
import google.appengine.ext.webapp.util
import logging
import os


class ChannelJSAPIHandler(google.appengine.ext.webapp.RequestHandler):

    def get(self):
        js_file = open(
            os.path.join(os.path.dirname(__file__), 'tae-channel-js.js'), 'rb')
        js_data = js_file.read()
        js_file.close()
        self.response.headers['Content-Type'] = 'application/javascript'
        self.response.out.write(js_data)


app = google.appengine.ext.webapp.WSGIApplication([
    ('/_ah/channel/jsapi', ChannelJSAPIHandler),
], debug=True)


def main():
    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
