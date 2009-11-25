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
"""Helper functions for registering App Engine API proxy stubs."""

import capability_stub
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.appinfo
import google.appengine.api.mail_stub
import google.appengine.api.urlfetch_stub
import google.appengine.api.user_service_stub
import google.appengine.ext.webapp
import intid
import logging
import memcache.memcache_stub
import mongodb.datastore_mongo_stub
import os
import re
import taskqueue.taskqueue_stub
import xmpp.xmpp_service_stub


def getAppConfig(directory='.'):
    """Returns a configuration object."""

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

    # Configure script with login handler
    login = google.appengine.api.appinfo.URLMap(
        url='/login',
        script='$PYTHON_LIB/typhoonae/handlers/login.py',
        login='required'
    )

    # Configure script with logout handler
    logout = google.appengine.api.appinfo.URLMap(
        url='/logout',
        script='$PYTHON_LIB/typhoonae/handlers/login.py'
    )

    # Generate URL mapping
    for handler in [login, logout] + conf.handlers:
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
            url_mapping.append((compiled, module, path))
 
    return url_mapping


def setupCapability():
    """Sets up cabability service."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'capability_service', capability_stub.CapabilityServiceStub())


def setupDatastore(app_id, datastore, history, require_indexes, trusted):
    """Sets up datastore."""

    tmp_dir = os.environ['TMPDIR']
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    datastore_path = os.path.join(tmp_dir, datastore)
    history_path = os.path.join(tmp_dir, history)

    datastore = mongodb.datastore_mongo_stub.DatastoreMongoStub(
        app_id, datastore_path, history_path, require_indexes=require_indexes,
        intid_client=intid.IntidClient())

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub(
        'datastore_v3', datastore)


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
        memcache.memcache_stub.MemcacheServiceStub())


def setupTaskQueue(root_path='.'):
    """Sets up task queue."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('taskqueue',
        taskqueue.taskqueue_stub.TaskQueueServiceStub(root_path=root_path))


def setupURLFetchService():
    """Sets up urlfetch."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('urlfetch',
        google.appengine.api.urlfetch_stub.URLFetchServiceStub())


def setupUserService():
    """Sets up user service."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('user',
        google.appengine.api.user_service_stub.UserServiceStub(
            login_url='/login?=%s', logout_url='/logout?=%s'))


def setupXMPP(host):
    """Sets up XMPP."""

    google.appengine.api.apiproxy_stub_map.apiproxy.RegisterStub('xmpp',
        xmpp.xmpp_service_stub.XmppServiceStub(host=host))


def setupStubs(conf, options):
    """Sets up api proxy stubs."""

    google.appengine.api.apiproxy_stub_map.apiproxy = \
        google.appengine.api.apiproxy_stub_map.APIProxyStubMap()

    setupCapability()

    setupDatastore(conf.application,
                   'dev_appserver.datastore',
                   'dev_appserver.datastore.history',
                   False, False)

    setupMail('localhost', 25, '', '')

    setupMemcache()

    setupTaskQueue()

    setupURLFetchService()

    setupUserService()

    setupXMPP(options.xmpp_host)

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
