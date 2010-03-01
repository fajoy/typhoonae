# -*- coding: utf-8 -*-
#
# Copyright 2009, 2010 Tobias Rodäbel
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
"""Helper functions for registering App Engine API proxy stubs."""

import google.appengine.api.apiproxy_stub_map
import google.appengine.api.appinfo
import google.appengine.api.mail_stub
import google.appengine.api.urlfetch_stub
import google.appengine.api.user_service_stub
import google.appengine.api.validation
import logging
import os
import re
import typhoonae.blobstore.blobstore_stub
import typhoonae.blobstore.file_blob_storage
import typhoonae.capability_stub
import typhoonae.intid
import typhoonae.memcache.memcache_stub
import typhoonae.mongodb.datastore_mongo_stub
import typhoonae.taskqueue.taskqueue_stub
import typhoonae.websocket.websocket_stub
import typhoonae.xmpp.xmpp_service_stub


SUPPORTED_DATASTORES = frozenset(['mongodb', 'bdbdatastore'])

end_request_hook = None


def getAppConfig(directory='.'):
    """Returns a configuration object."""

    attrs = google.appengine.api.appinfo.AppInfoExternal.ATTRIBUTES

    attrs[google.appengine.api.appinfo.SERVICES] = (
        google.appengine.api.validation.Optional(
            google.appengine.api.validation.Repeated(
                google.appengine.api.validation.Regex(
                    r'(mail|xmpp_message|websocket_message)'))))

    path = os.path.join(directory, 'app.yaml')
    conf_file = open(path, 'r')

    try:
        conf = google.appengine.api.appinfo.LoadSingleAppInfo(conf_file)
    except IOError:
        raise RuntimeError
    finally:
        conf_file.close()

    return conf


def initURLMapping(conf):
    """Returns a list with mappings URL to module name and script."""

    url_mapping = []

    add_handlers = [
        google.appengine.api.appinfo.URLMap(url=url, script=script)
        for url, script in [
            # Configure script with login handler
            ('/_ah/login', '$PYTHON_LIB/typhoonae/handlers/login.py'),
            # Configure script with logout handler
            ('/_ah/logout', '$PYTHON_LIB/typhoonae/handlers/login.py')
        ]
    ]

    # Generate URL mapping
    for handler in add_handlers + conf.handlers:
        script = handler.script
        regexp = handler.url
        if script != None:
            if script.startswith('$PYTHON_LIB'):
                module = script.replace(os.sep, '.')[12:-3]
                try:
                    m = __import__(module)
                except Exception, err_obj:
                    logging.error(
                        "Could not initialize script '%s'. %s: %s" %
                        (script, err_obj.__class__.__name__, err_obj)
                    )
                    continue
                p = os.path.dirname(m.__file__).split(os.sep)
                path = os.path.join(os.sep.join(p[:len(p)-1]), script[12:])
            else:
                module_path, unused_ext = os.path.splitext(script)
                module = module_path.replace(os.sep, '.')
                path = os.path.join(os.getcwd(), script)

            if not regexp.startswith('^'):
                regexp = '^' + regexp
            if not regexp.endswith('$'):
                regexp += '$'
            compiled = re.compile(regexp)
            login_required = handler.login in ('required', 'admin')
            admin_only = handler.login in ('admin',)
            url_mapping.append(
                (compiled, module, path, login_required, admin_only))

    return url_mapping


def setupCapability():
    """Sets up cabability service."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'capability_service', typhoonae.capability_stub.CapabilityServiceStub())


def setupDatastore(name, app_id, datastore, history, require_indexes, trusted):
    """Sets up datastore."""

    if name == 'mongodb':
        tmp_dir = os.environ['TMPDIR']
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        datastore_path = os.path.join(tmp_dir, datastore)
        history_path = os.path.join(tmp_dir, history)

        datastore = typhoonae.mongodb.datastore_mongo_stub.DatastoreMongoStub(
            app_id, datastore_path,
            require_indexes=require_indexes,
            intid_client=typhoonae.intid.IntidClient())
    elif name == 'bdbdatastore':
        from notdot.bdbdatastore import socket_apiproxy_stub
        datastore = socket_apiproxy_stub.RecordingSocketApiProxyStub(
            ('localhost', 9123))
        global end_request_hook
        end_request_hook = datastore.closeSession
    else:
        raise RuntimeError, "unknown datastore"

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'datastore_v3', datastore)

    if name in ['bdbdatastore']:
        from google.appengine.tools import dev_appserver_index
        app_root = os.getcwd()
        logging.info("%s" % app_root)
        dev_appserver_index.SetupIndexes(app_id, app_root)
        dev_appserver_index.IndexYamlUpdater(app_root)


def setupMail(smtp_host, smtp_port, smtp_user, smtp_password,
              enable_sendmail=False, show_mail_body=False):
    """Sets up mail."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('mail',
        google.appengine.api.mail_stub.MailServiceStub(
            smtp_host, smtp_port, smtp_user, smtp_password,
            enable_sendmail=enable_sendmail, show_mail_body=show_mail_body))


def setupMemcache():
    """Sets up memcache."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('memcache',
        typhoonae.memcache.memcache_stub.MemcacheServiceStub())


def setupTaskQueue(root_path='.'):
    """Sets up task queue."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('taskqueue',
        typhoonae.taskqueue.taskqueue_stub.TaskQueueServiceStub(
            root_path=root_path))


def setupURLFetchService():
    """Sets up urlfetch."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('urlfetch',
        google.appengine.api.urlfetch_stub.URLFetchServiceStub())


def setupUserService():
    """Sets up user service."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('user',
        google.appengine.api.user_service_stub.UserServiceStub(
            login_url='/_ah/login?continue=%s',
            logout_url='/_ah/logout?continue=%s'))


def setupXMPP(host):
    """Sets up XMPP."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('xmpp',
        typhoonae.xmpp.xmpp_service_stub.XmppServiceStub(host=host))


def setupBlobstore(blobstore_path, app_id):
    """Sets up blobstore service."""

    storage = typhoonae.blobstore.file_blob_storage.FileBlobStorage(
        blobstore_path, app_id)
    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'blobstore',
        typhoonae.blobstore.blobstore_stub.BlobstoreServiceStub(storage))


def setupWebSocket():
    """Sets up Web Socket service."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'websocket', typhoonae.websocket.websocket_stub.WebSocketServiceStub())


def setupRemoteDatastore(app_id, email, password):
    """Enables remote API mode for all datastore operations."""

    from google.appengine.ext.remote_api import remote_api_stub
    remote_api_stub.ConfigureRemoteApi(
        app_id, '/remote_api', lambda:(email, password), secure=True,
        servername=app_id+'.appspot.com', services=['datastore_v3'])
    remote_api_stub.MaybeInvokeAuthentication()


def setupStubs(conf, options):
    """Sets up api proxy stubs."""

    google.appengine.api.apiproxy_stub_map.apiproxy = \
        google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

    if options.datastore == 'remote':
        setupRemoteDatastore(conf.application, options.email, options.password)

    setupCapability()

    if options.datastore in SUPPORTED_DATASTORES:
        setupDatastore(options.datastore.lower(),
                       conf.application,
                       'dev_appserver.datastore',
                       'dev_appserver.datastore.history',
                       False,
                       False)

    setupMail(options.smtp_host, options.smtp_port,
              options.smtp_user, options.smtp_password)

    setupMemcache()

    setupTaskQueue()

    setupURLFetchService()

    setupUserService()

    setupXMPP(options.xmpp_host)

    setupBlobstore(options.blobstore_path, conf.application)

    setupWebSocket()

    try:
        from google.appengine.api.images import images_stub
        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'images',
            images_stub.ImagesServiceStub())
    except ImportError, e:
        logging.warning('Could not initialize images API; you are likely '
                        'missing the Python "PIL" module. ImportError: %s', e)
        from google.appengine.api.images import images_not_implemented_stub
        google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
            'images',
            images_not_implemented_stub.ImagesNotImplementedServiceStub())
