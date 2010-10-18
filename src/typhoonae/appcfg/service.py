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
from google.appengine.ext.webapp import template
from wsgiref.simple_server import ServerHandler, WSGIRequestHandler, make_server

import ConfigParser
import cStringIO
import datetime
import logging
import mimetools
import multifile
import optparse
import os
import shutil
import signal
import socket
import sys
import re
import threading
import time
import typhoonae.apptool
import typhoonae.fcgiserver

APPLICATION_ID = 'appcfg'
DEFAULT_ADDRESS = 'localhost:9190'
DESCRIPTION = "HTTP service for deploying and managing GAE applications."
USAGE = "usage: %prog [options]"

SERVER_SOFTWARE = "TyphoonAE/0.1.6 AppConfigService/0.1.0"

LOG_FORMAT = '%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] %(message)s'

DEFAULT_SUPERVISOR_SERVER_URL = 'http://localhost:9001'

CONFIG_FILE_KEY = "TYPHOONAE_CONFIG"
CONFIG_FILE_NAME = "typhoonae.cfg"

XMPP_INBOUND_SERVICE_NAME = "xmpp_message"

LIST_DELIMITER = '\n'
TUPLE_DELIMITER = '|'
MIME_FILE_HEADER = 'X-Appcfg-File'
MIME_HASH_HEADER = 'X-Appcfg-Hash'

STATE_INACTIVE = 0
STATE_UPDATING = 1
STATE_DEPLOYED = 2
VALID_STATES = frozenset([STATE_INACTIVE, STATE_UPDATING, STATE_DEPLOYED])

MAX_USED_PORTS = 10

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
        logging.debug(format, *args)


class PortConfig(db.Model):
    """Stores port configurations for a machine."""

    used_ports = db.ListProperty(int)


class Appversion(db.Model):
    """Represents appversions."""

    app_id = db.StringProperty()
    version = db.StringProperty()
    current_version_id = db.StringProperty()
    updated = db.DateTimeProperty()
    app_yaml = db.BlobProperty()
    fcgi_port = db.IntegerProperty()
    portconfig = db.ReferenceProperty(PortConfig)
    state = db.IntegerProperty(choices=VALID_STATES, default=STATE_UPDATING)

    @property
    def config(self):
        return appinfo.LoadSingleAppInfo(cStringIO.StringIO(self.app_yaml))


class IndexPage(webapp.RequestHandler):
    """Provides a simple index page."""

    def get(self):
        apps = Appversion.all().fetch(10)
        template_path = os.path.join(os.path.dirname(__file__), 'index.html')
        output = template.render(template_path, {'apps': apps})
        self.response.out.write(output)


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

    __deploy_lock = threading.Lock()

    def post(self, func_name):
        app_id = self.request.params.get('app_id')
        version = self.request.params.get('version')
        path = self.request.params.get('path')

        func = getattr(self, '_RpcMethod_'+func_name, None)
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
            "AND version = :2 AND state = :3 ORDER BY updated DESC", 
            app_id, version, state)
        return query.get()

    # API methods

    def _RpcMethod_create(self, app_id, version, path, data):
        if self.getAppversion(app_id, version, STATE_UPDATING):
            raise AppConfigServiceError(
                u"Already updating application (app_id=u'%s')." % app_id)

        def makeCurrentAppversionId(version, date):
            return "%s.%i" % (version, int(time.mktime(date.timetuple()))<<28)

        appversion = self.getAppversion(app_id, version, STATE_DEPLOYED)
        now = datetime.datetime.now()
        if not appversion:
            appversion = Appversion(app_id=app_id, version=version)
        else:
            appversion.state = STATE_UPDATING
        appversion.current_version_id = makeCurrentAppversionId(
            version, now)
        appversion.updated = now
        appversion.app_yaml = self.request.body
        appversion.put()

        app_dir = self.createAppversionDirectory(appversion)

        conf = file(os.path.join(app_dir, 'app.yaml'), 'wb')
        conf.write(self.request.body)
        conf.close()

        logging.debug('Appversion directory: %s', app_dir)

    def _RpcMethod_clonefiles(self, app_id, version, path, data):
        files = self._extractFileTuples(data)
        self.response.out.write(
            LIST_DELIMITER.join([filename for filename, _ in files]))

    def _RpcMethod_cloneblobs(self, app_id, version, path, data):
        files = self._extractFileTuples(data)
        self.response.out.write(
            LIST_DELIMITER.join([filename for filename, _, mimetype in files]))

    def _RpcMethod_addfile(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self._createFile(app_dir, path, data)

    def _RpcMethod_addfiles(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self.extractFiles(data, app_dir)

    def _RpcMethod_addblobs(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        self.extractFiles(data, app_dir)

    def _RpcMethod_deploy(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)

        deployment = DeploymentThread(appversion, app_dir)
        self.__deploy_lock.acquire()
        deployment.start()
        self.__deploy_lock.release()

    def _RpcMethod_isready(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_DEPLOYED)
        if appversion:
            self.response.out.write('1')
            return
        self.response.out.write('0')

    def _RpcMethod_rollback(self, app_id, version, path, data):
        appversion = self.getAppversion(app_id, version, STATE_UPDATING)
        app_dir = self.getAppversionDirectory(appversion)
        logging.info("Deleting application directory '%s'", app_dir)
        shutil.rmtree(app_dir)
        logging.info("Deleting appversion (app_id=u'%s')", app_id)
        appversion.delete()


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

    def __init__(self, addr, app, apps_root, var, verbose=False):
        """Initialize the WSGI server.

        Args:
            app: A webapp.WSGIApplication.
            addr: Use this address to initialize the HTTP server.
            apps_root: Applications root directory.
            var: Directory for platform independent data.
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

        datastore_path = os.path.join(var, APPLICATION_ID+'.sqlite')

        datastore = datastore_sqlite_stub.DatastoreSqliteStub(
            APPLICATION_ID, datastore_path)

        apiproxy_stub_map.apiproxy.RegisterStub(
            'datastore_v3', datastore)

        logging.debug('Using datastore: %s', datastore_path)

    def _handleSignal(self, sig, frame):
        logging.debug('Caught signal %d', sig)
        if sig in (signal.SIGQUIT, signal.SIGABRT, signal.SIGTERM):
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
                self.host, self.port, self.app, handler_class=RequestHandler)
            server.serve_forever()
        except KeyboardInterrupt:
            logging.warn('Interrupted')


def getSupervisorRpcInterface(default_url=DEFAULT_SUPERVISOR_SERVER_URL):
    """Returns the supervisor RPC interface.

    Args:
        default_url: Specifies the default URL to the supervisor server.

    See http://supervisord.org/api.html for a detailed documentation.
    """
    import supervisor.childutils

    env = {}
    env.update(os.environ)
    env.setdefault('SUPERVISOR_SERVER_URL', default_url)

    return supervisor.childutils.getRPCInterface(env).supervisor


class Options(object):
    """Provides options as attributes.

    Replaces variables with their values from the environment.
    """

    def __init__(self, options, environ):
        """Constructor."""
        self._options = {}
        for opt in options:
            val = options[opt]
            for key in environ:
                val = re.sub(r'\$%s' % key, environ[key], val)
            self._options[opt] = val 

    def __getattr__(self, key):
        try:
            val = self._options[key]
        except KeyError:
            raise AppConfigServiceError(u"Option key '%s' not found" % key)
        if re.match(r'^([0-9]+)$', val):
            val = int(val)
        elif re.match(r'^(False|True)$', val, re.M):
            val = eval(val)
        return val


def readDefaultOptions():
    """Reads default options from gloabal config file."""

    environ = {
        'HOSTNAME': os.environ.get('HOSTNAME', socket.getfqdn()),
        'SERVER_SOFTWARE': os.environ.get('SERVER_SOFTWARE',
                                          typhoonae.fcgiserver.SERVER_SOFTWARE),
    }

    p = ConfigParser.ConfigParser()
    p.read(os.environ[CONFIG_FILE_KEY])

    return Options(dict(p.items('typhoonae')), environ)


def configureAppversion(appversion, app_dir, options):
    """Writes configuration files for the given appversion.

    Args:
        appversion: An Appversion instance.
        app_dir: Absolute path to the root directory of our appversion.
        options: An Options instance.
    """
    conf = appversion.config

    options.internal_address = '%s.latest.%s.%s' % (
        appversion.version, appversion.app_id, options.internal_address)

    typhoonae.apptool.write_nginx_conf(options, conf, app_dir)
    typhoonae.apptool.write_nginx_conf(
        options, conf, app_dir, internal=True, mode='a')
    typhoonae.apptool.make_blobstore_dirs(
        os.path.abspath(os.path.join(options.blobstore_path, conf.application)))
    typhoonae.apptool.write_supervisor_conf(options, conf, app_dir)
    typhoonae.apptool.write_ejabberd_conf(options)
    typhoonae.apptool.write_crontab(options, app_dir)


class DeploymentThread(threading.Thread):
    """Asynchronously deploy a given appversion."""

    def __init__(self, appversion, app_dir):
        threading.Thread.__init__(self)
        self.appversion = appversion
        self.app_dir = app_dir

    def run(self):
        supervisor_rpc = getSupervisorRpcInterface()

        try:
            supervisor_rpc.getState()
        except socket.error, e:
            logging.critical("Connecting to supervsord failed %s.", e)
            raise AppConfigServiceError(
                u"Internal error when deploying application (app_id=u'%s')." %
                self.app_id)

        options = readDefaultOptions()

        portconfig = PortConfig.get_or_insert(
            'portconfig_%s' % options.server_name.replace('.', '_'))

        if self.appversion.fcgi_port and self.appversion.portconfig:
            port = self.appversion.fcgi_port
        else:
            port = options.fcgi_port

            if not portconfig.used_ports:
                portconfig.used_ports.append(port)
            else:
                if len(portconfig.used_ports) == MAX_USED_PORTS:
                    raise AppConfigServiceError(
                        u"Maximum number of installed applications reached.")
                for i, p in enumerate(range(port, port+MAX_USED_PORTS)):
                    if p not in portconfig.used_ports:
                        portconfig.used_ports.insert(i, p)
                        options.fcgi_port = p
                        break

        configureAppversion(self.appversion, self.app_dir, options)

        app_config = self.appversion.config

        if self.appversion.config.inbound_services:
            if XMPP_INBOUND_SERVICE_NAME in app_config.inbound_services:
                supervisor_rpc.stopProcess('ejabberd')
                supervisor_rpc.startProcess('ejabberd')
                logging.info("Restarted XMPP gateway")

        added, changed, removed = supervisor_rpc.reloadConfig()[0]

        for name in removed:
            results = supervisor_rpc.stopProcessGroup(name)
            logging.info("Stoppend %s", name)
            supervisor_rpc.removeProcessGroup(name)
            logging.info("Removed process group %s", name)

        for name in changed:
            results = supervisor_rpc.stopProcessGroup(name)
            logging.info("Stopped %s", name)
            supervisor_rpc.removeProcessGroup(name)
            supervisor_rpc.addProcessGroup(name)
            logging.info("Updated process group %s", name)

        for name in added:
            supervisor_rpc.addProcessGroup(name)
            logging.info("Added process group %s", name)

        time.sleep(2)

        supervisor_rpc.stopProcess('nginx')
        supervisor_rpc.startProcess('nginx')
        logging.info("Restarted HTTP frontend")

        # Update Appversion instance
        if not self.appversion.fcgi_port and not self.appversion.portconfig:
            self.appversion.fcgi_port = port
            self.appversion.portconfig = portconfig
            portconfig.put()

        self.appversion.state = STATE_DEPLOYED
        self.appversion.updated = datetime.datetime.now()
        self.appversion.put()


def main():
    """The main method."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address",
                  metavar="ADDR", help="use this address",
                  default=DEFAULT_ADDRESS)

    op.add_option("--apps_root", dest="apps_root", metavar="PATH",
                  help="the root directory of all application directories",
                  default=typhoonae.apptool.setdir(
                        os.path.abspath(os.path.join('.', 'var'))))

    op.add_option("-c", "--config", dest="config_file",
                  metavar="FILE", help="read configuration from this file")

    op.add_option("-d", "--debug", dest="debug_mode", action="store_true",
                  help="enables debug mode", default=False)

    op.add_option("--var", dest="var", metavar="PATH",
                  help="use this directory for platform independent data",
                  default=typhoonae.apptool.setdir(
                        os.path.abspath(os.path.join('.', 'var'))))

    (options, args) = op.parse_args()

    os.environ['APPS_ROOT'] = options.apps_root

    logging.basicConfig(format=LOG_FORMAT)

    if options.debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    if options.config_file:
        os.environ[CONFIG_FILE_KEY] = options.config_file

    if CONFIG_FILE_KEY not in os.environ:
        os.environ[CONFIG_FILE_KEY] = CONFIG_FILE_NAME

    if not os.path.isfile(os.environ[CONFIG_FILE_KEY]):
        logging.error('Configuration file "%s" not found',
                      os.environ[CONFIG_FILE_KEY])
        sys.exit(1)

    service = AppConfigService(
        options.address,
        app,
        options.apps_root,
        options.var,
        options.debug_mode)

    service.serve_forever()
