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
"""Simple Channel API demo."""

from google.appengine.api import channel
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
import cgi
import logging


class MainHandler(webapp.RequestHandler):
    """Provides the main page of this Channel API demo."""

    def get(self):
        channel_id = channel.create_channel('demochannel')
        output = template.render('channel.html', {'channel_id': channel_id})
        self.response.out.write(output)


class ChannelHandler(webapp.RequestHandler):
    """Endpoint for receiving and sending Channel messages."""

    def post(self):
        channel_id = self.request.get('channel_id')
        if channel_id:
            message = cgi.escape(self.request.body)
            logging.info("Received: '%s'" % message)
            channel.send_message(channel_id, message)
        else:
            self.response.set_status(401)


app = webapp.WSGIApplication([
    ('/channel', MainHandler),
    ('/channel_message', ChannelHandler),
], debug=True)


def main():
    """The main function."""

    util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
