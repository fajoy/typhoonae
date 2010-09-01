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

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import appinfo
from google.appengine.ext import db
from google.appengine.ext import webapp
from wsgiref.simple_server import ServerHandler, WSGIRequestHandler, make_server

import cStringIO
import logging
import mimetools
import multifile
import optparse
import os
import signal
import supervisor.childutils
import sys
import re
import time
import typhoonae

APPLICATION_ID = 'appcfg'
DEFAULT_ADDRESS = 'localhost:9190'
DESCRIPTION = "HTTP service for deploying and managing GAE applications."
USAGE = "usage: %prog [options]"

SERVER_SOFTWARE = "TyphoonAE/0.1.6 AppConfigService/0.1.0"

LOG_FORMAT = '%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] %(message)s'

DEFAULT_SUPERVISOR_SERVER_URL = 'http://localhost:9001'

LIST_DELIMITER = '\n'
TUPLE_DELIMITER = '|'
MIME_FILE_HEADER = 'X-Appcfg-File'
MIME_HASH_HEADER = 'X-Appcfg-Hash'

STATE_INACTIVE = 0
STATE_UPDATING = 1
STATE_DEPLOYED = 2
VALID_STATES = frozenset([STATE_INACTIVE, STATE_UPDATING, STATE_DEPLOYED])

INDEX_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C //DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>TyphoonAE appcfg service</title>
  </head>
  <body>
    <h1>TyphoonAE appcfg service</h1>
    %(apps)s
  </body>
</html>
"""

FILE_FILTER_PATTERNS = [
    '\.git.*',
    '.*/\.git.*',
]


class AppConfigServiceError(Exception):
    """Exception to be raised on errors during appversion deployment."""


class WSGIServerHandler(ServerHandler):

    server_software = SERVER_SOFTWARE


class RequestHandler(WSGIRequestHandler):
    """Extends the WSGI request handler class to implement custom logging."""

    def handle(self):
        """Handles a single HTTP request."""

        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        handler = WSGIServerHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ()
        )
        handler.request_handler = self
        handler.run(self.server.get_app())

    def log_message(self, format, *args):
        logging.info(format, *args)


class Appversion(db.Model):
    """Represents appversions."""

    app_id = db.StringProperty(required=True)
    version = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now=True)
    app_yaml = db.BlobProperty(required=True)
    state = db.IntegerProperty(choices=VALID_STATES, default=STATE_UPDATING)

    @property
    def current_version_id(self):
        version_id = "%s.%i" % (
            self.version, int(time.mktime(self.created.timetuple())) << 28)
        return version_id

    @property
    def config(self):
        return appinfo.LoadSingleAppInfo(cStringIO.StringIO(self.app_yaml))


class IndexPage(webapp.RequestHandler):
    """Provides a simple index page."""

    def get(self):
        apps = u'<ul>'
        apps += u''.join([
            u'<li>%s (%s)</li>' % (app.app_id, app.current_version_id)
            for app in Appversion.all().fetch(10)
        ])
        apps += u'</ul>'

        self.response.out.write(INDEX_TEMPLATE % locals())


class UpdatecheckHandler(webapp.RequestHandler):
    """Informs a client about available updates.

    This implementation always pretends to be in sync with the client.
    """

    def post(self):
        response = ""
        # We pretend always to be up-to-date
        for key in self.request.params.keys():
            response += "%s: %s\n" % (key, self.request.params.get(key))
        self.response.out.write(response)


class AppversionHandler(webapp.RequestHandler):
    """Implements web-hooks for uploading a new appversion.

    Handles all POST requests for /api/appversion.
    """

    def post(self, func_name):
        app_id = self.request.params.get('app_id')
        version = self.request.params.get('version')
        path = self.request.params.get('path')

        func = getattr(self, func_name, None)
        if func:
            try:
                func(app_id, version, path, self.request.body)
            except AppConfigServiceError, e:
                self.response.out.write(e)
                self.response.set_status(403)

    @staticmethod
    def _extractMimeParts(stream):
        msg = mimetools.Message(stream)
        msgtype = msg.gettype()
        params = msg.getplist()

        files = []

        raw_data = cStringIO.StringIO()
        if msgtype[:10] == "multipart/":
            f = multifile.MultiFile(stream)
            f.push(msg.getparam("boundary"))
            while f.next():
                submsg = mimetools.Message(f)
                filename = submsg.getheader(MIME_FILE_HEADER)
                content_hash = submsg.getheader(MIME_HASH_HEADER)
                try:
                    raw_data = cStringIO.StringIO()
                    mimetools.decode(f, raw_data, submsg.getencoding())
                except ValueError:
                    continue
                files.append((filename, content_hash, raw_data.getvalue()))
            f.pop()
        return files

    @staticmethod
    def _extractFileTuples(data):
        tuples = [tuple(f.split(TUPLE_DELIMITER))
                  for f in data.split(LIST_DELIMITER)]
        for pattern in FILE_FILTER_PATTERNS:
            tuples = filter(lambda t:not re.match(pattern, t[0]), tuples)
        return tuples

    @staticmethod
    def _createFile(app_dir, file_path, data):
        path, name = os.path.split(file_path)
        dst = os.path.join(app_dir, path)
        if not os.path.isdir(dst):
            os.makedirs(dst)
        f = file(os.path.join(dst, name), 'wb')
        f.write(data)
        f.close()

    @staticmethod
    def getAppversionDirectory(appversion):
        """Get appversion directory.

        Args:
            appversion: An Appversion instance.

        Returns an absolute directory path.
        """
        app_dir = os.path.join(
            os.path.abspath(os.environ['APPS_ROOT']),
            appversion.app_id,
            appversion.current_version_id)
        return app_dir

    @classmethod
    def createAppversionDirectory(cls, appversion):
        """Create appversion directory.

        Args:
            appversion: An Appversion instance.

        Raises AppConfigServiceError when appversion directory exits.
        Returns an absolute directory path.
        """
        app_dir = cls.getAppversionDirectory(appversion)
        if os.path.isdir(app_dir):
            raise AppConfigServiceError(
                u"Application exists (app_id=u'%s')." % appversion.app_id)
        os.makedirs(app_dir)
        return app_dir

    @classmethod
    def extractFiles(cls, data, app_dir):
        """Extracts files from multipart into the appversion directory.

        Args:
            data: Multipart form data.
            app_dir: String containing the absolute appversion directory.
        """
        files = cls._extractMimeParts(cStringIO.StringIO(data))
        for file_path, content_hash, contents in files:
            cls._createFile(app_dir, file_path, contents)

    @staticmethod
    def getAppversion(app_id, version, state):
        """Get appversion key.

        Args:
            app_id: The application id.
            version: The application version.
            state: Integer representing the appversion state.

        Returns datastore_types.Key instance.
        """
        query = db.GqlQuery(
            "SELECT * FROM Appversion WHERE app_id = :1 "
            "AND version = :2 AND state = :3", app_id, version, state)
        return query.get()

    # API methods

    def create(self, app_id, version, path, data):
        if self.getAppversion(app_id, version, STATE_UPDATING):
            raise AppConfigServiceError(
                u"Already updating application (app_id=u'%s')." % app_id)
        def tx():
            appversion = Appversion(
                app_id=app_id,
                version=version,
                app_yaml=self.request.body)
            appversion.put()

            app_dir = self.createAppversionDirectory(appversion)

            conf = file(os.path.join(app_dir, 'app.yaml'), 'wb')
            conf.write(self.request.body)
            conf.close()

            logging.debug('Appversion directory: %s', app_dir)

        db.run_in_transaction(tx)

    def clonefiles(self, app_id, version, path, data):
        files = self._extractFileTuples(data)
        self.response.out.write(
            LIST_DELIMITER.join([filename for filename, _ in files]))

    def cloneblobs(self, app_id, version, path, data):
        files = self._extractFileTuples(data)
        self.response.out.write(
            LIST_DELIMITER.join([filename for filename, _, mimetype in files]))

    def addfile(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self._createFile(app_dir, path, data)

    def addfiles(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self.extractFiles(data, app_dir)

    def addblobs(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self.extractFiles(data, app_dir)

    def deploy(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        appversion.state = STATE_DEPLOYED
        appversion.put()

    def isready(self, app_id, version, path, data):
        self.response.out.write('1')


class DatastoreHandler(webapp.RequestHandler):
    """Implements web-hooks for actions on the datastore.

    Handles all POST requests for /api/datastore.
    """

    def post(self, resource, func_name):
        pass


class CronHandler(webapp.RequestHandler):
    """Implements web-hooks for configuring the cron service.

    Handles all POST requests for /api/cron.
    """

    def post(self, func_name):
        pass


app = webapp.WSGIApplication([
    ('/', IndexPage),
    ('/api/updatecheck', UpdatecheckHandler),
    ('/api/appversion/(.*)', AppversionHandler),
    ('/api/datastore/(.*)/(.*)', DatastoreHandler),
    ('/api/cron/(.*)', CronHandler),
], debug=True)


class AppConfigService(object):
    """Uses a simple single-threaded WSGI server and signal handling."""

    def __init__(self, addr, app, apps_root, verbose=False):
        """Initialize the WSGI server.

        Args:
            app: A webapp.WSGIApplication.
            addr: Use this address to initialize the HTTP server.
            apps_root: Applications root directory.
            verbose: Boolean, default False. If True, enable verbose mode.
        """
        assert isinstance(app, webapp.WSGIApplication)
        self.app = app
        host, port = addr.split(':')
        self.host = host
        self.port = int(port)
        self.apps_root = apps_root

        # Setup signals
        signal.signal(signal.SIGHUP, self._handleSignal)
        signal.signal(signal.SIGQUIT, self._handleSignal)
        signal.signal(signal.SIGABRT, self._handleSignal)
        signal.signal(signal.SIGTERM, self._handleSignal)

        # Setup environment
        os.environ['APPLICATION_ID'] = APPLICATION_ID

        # Setup Datastore
        # We use the SQLite Datastore stub for development. Later, we take
        # the production Datastore.
        from google.appengine.datastore import datastore_sqlite_stub
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()

        datastore_path = os.path.join(
            os.environ['TMPDIR'], APPLICATION_ID+'.sqlite')

        datastore = datastore_sqlite_stub.DatastoreSqliteStub(
            APPLICATION_ID, datastore_path)

        apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        logging.debug('Using datastore: %s', datastore_path)

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

        logging.info('Starting (pid:%i)', os.getpid())
        try:
            logging.debug('HTTP server listening on %s:%i',
                          self.host, self.port)
            server = make_server(
                self.host, self.port, app, handler_class=RequestHandler)
            server.serve_forever()
        except KeyboardInterrupt:
            logging.warn('Interrupted')


def main():
    """The main method."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address",
                  metavar="ADDR", help="use this address",
                  default=DEFAULT_ADDRESS)

    op.add_option("-d", "--debug", dest="debug_mode", action="store_true",
                  help="enables debug mode", default=False)

    op.add_option("--apps_root", dest="apps_root", metavar="PATH",
                  help="the root directory of all application directories",
                  default=os.environ.get("TMPDIR", "/tmp"))

    (options, args) = op.parse_args()

    os.environ['APPS_ROOT'] = options.apps_root

    logging.basicConfig(format=LOG_FORMAT)

    if options.debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    service = AppConfigService(
        options.address, app, options.apps_root, options.debug_mode)
    service.serve_forever()
