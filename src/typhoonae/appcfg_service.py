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
"""Service for deploying and managing GAE applications.

Provides service methods as web-hooks for the appcfg.py script.

This implementation uses a simple WSGI server while omitting any security.
It should only be used internally.
"""

from google.appengine.ext import webapp
from wsgiref.simple_server import make_server

import logging
import optparse
import signal
import sys
import time

DEFAULT_ADDRESS = 'localhost:9190'
DESCRIPTION = "HTTP service for deploying and managing GAE applications."
USAGE = "usage: %prog [options]"


class UpdatecheckRequestHandler(webapp.RequestHandler):
    """ """

    def post(self):
        response = ""
        # We pretend always to be up-to-date
        for key in self.request.params.keys():
            response += "%s: %s\n" % (key, self.request.params.get(key))
        self.response.headers['content-type'] = 'text/plain'
        self.response.out.write(response)


class AppversionRequestHandler(webapp.RequestHandler):
    """ """

    def post(self):
        app_id = self.request.params.get('app_id')
        version = self.request.params.get('version')
        version_dir = "%s.%i" % (version, int(time.time()) << 28)


app = webapp.WSGIApplication([
    ('/api/updatecheck', UpdatecheckRequestHandler),
    ('/api/appversion/create', AppversionRequestHandler),
], debug=True)


class WSGIServer(object):
    """Provides a simple single-threaded WSGI server with signal handling."""

    def __init__(self, addr, app):
        """Initialize the WSGI server.

        Args:
            app: A webapp.WSGIApplication.
            addr: Use this address to initialize the HTTP server.
        """
        assert isinstance(app, webapp.WSGIApplication)
        self.app = app
        host, port = addr.split(':')
        self.host = host
        self.port = int(port)

        # Setup signals
        signal.signal(signal.SIGHUP, self._handleSignal)
        signal.signal(signal.SIGQUIT, self._handleSignal)
        signal.signal(signal.SIGABRT, self._handleSignal)
        signal.signal(signal.SIGTERM, self._handleSignal)

    def _handleSignal(self, sig, frame):
        logging.debug('Caught signal %d' % sig)
        if sig in (3, 6, 15):
            self.shutdown()

    def shutdown(self):
        """Shut down the service."""

        logging.info('Shutting down')
        sys.exit(0)

    def serve_forever(self):
        """Start serving."""

        logging.info('Starting')
        try:
            logging.debug('HTTP server listening on %s:%i',
                          self.host, self.port)
            server = make_server(self.host, self.port, app)
            server.serve_forever()
        except KeyboardInterrupt:
            logging.warn('Interrupted')


def main():
    """The main method."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--address", dest="address",
                  metavar="ADDR", help="use this address",
                  default=DEFAULT_ADDRESS)

    op.add_option("-d", "--debug", dest="debug_mode", action="store_true",
                  help="enables debug mode", default=False)

    (options, args) = op.parse_args()

    if options.debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    server = WSGIServer(options.address, app)
    server.serve_forever()
