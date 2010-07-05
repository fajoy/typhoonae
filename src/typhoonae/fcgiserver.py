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
"""FastCGI script to serve a CGI application."""

import base64
import cStringIO
import fcgiapp
import google.appengine.api.users
import google.appengine.tools.dev_appserver
import imp
import logging
import optparse
import os
import re
import sys
import typhoonae
import typhoonae.blobstore.handlers
import typhoonae.handlers.login

BASIC_AUTH_PATTERN = re.compile(r'Basic (.*)$')
DESCRIPTION = ("FastCGI application server.")
USAGE = "usage: %prog [options] <application root>"
SERVER_SOFTWARE = "TyphoonAE/0.1.5"


class CGIHandlerChain(object):
    """CGI handler chain."""

    def __init__(self, *handlers):
        """Constructor."""

        self.handlers = handlers

    def __call__(self, fp, environ):
        """Executes CGI handlers."""

        for handler in self.handlers:
            fp = handler(fp, environ)

        return fp


class CGIInAdapter:
    """Adapter for FastCGI input stream objects."""

    def __init__(self, i):
        self.i = i

    def close(self):
        self.i.close()

    def read(self, *args):
        return self.i.read(*args)

    def readline(self, *args):
        return self.i.readline()

    def seek(self, *args):
        return self.i.seek(*args)


class CGIOutAdapter:
    """Adapter for FastCGI output stream objects."""

    def __init__(self, o):
        self.o = o
        self.fp = cStringIO.StringIO()

    def __del__(self):
        del self.fp

    def flush(self):
        rewriter_chain = CGIHandlerChain(
            typhoonae.blobstore.handlers.CGIResponseRewriter())
        fp = rewriter_chain(self.fp, os.environ)
        try:
            self.o.write(fp.getvalue())
            self.o.flush()
        except IOError:
            logging.error("Invalid CGI output stream (IOError)")
        except fcgiapp.error:
            logging.error("Invalid CGI output stream (FastCGI)")
        finally:
            self.fp.flush()

    def write(self, s):
        self.fp.write(s)


def load_module(handler_path, cgi_path, module_dict=sys.modules):
    module_fullname = google.appengine.tools.dev_appserver.GetScriptModuleName(
        handler_path)
    script_module = module_dict.get(module_fullname)
    module_code = None
    has_main = google.appengine.tools.dev_appserver.ModuleHasValidMainFunction(
        script_module)
    if script_module is not None and has_main:
        logging.debug('Reusing main() function of module "%s"', module_fullname)
    else:
        if script_module is None:
            script_module = imp.new_module(module_fullname)

        missing_inits = (google.appengine.tools.dev_appserver.
                         FindMissingInitFiles(cgi_path, module_fullname))
        if missing_inits:
            logging.warning(
                'Missing package initialization files: %s',
                ', '.join(missing_inits))

        independent_load_successful = True

        if not os.path.isfile(cgi_path):
            independent_load_successful = False
        else:
            try:
                source_file = open(cgi_path)
                try:
                    module_code = compile(source_file.read(), cgi_path, 'exec')
                    script_module.__file__ = cgi_path
                finally:
                    source_file.close()

            except OSError:
                independent_load_successful = False

        if not independent_load_successful:
            raise RuntimeError('Failed to load module "%s"', cgi_path)

    module_dict[module_fullname] = script_module

    return module_fullname, script_module, module_code


def run_module(handler_path, cgi_path):
    """Executes a CGI script by importing it as a new module.

    Args:
        handler_path: CGI path stored in the application configuration
            (as a path like 'foo/bar/baz.py'). Should not have $PYTHON_LIB
            references.
        cgi_path: Absolute path to the CGI script file on disk.
    """
    module_fullname, script_module, module_code = load_module(
        handler_path, cgi_path)

    script_module.__name__ = '__main__'
    sys.modules['__main__'] = script_module

    if module_code:
        exec module_code in script_module.__dict__
    else:
        script_module.main()


def serve(conf, options):
    """Implements the server loop.

    Args:
        conf: The application configuration.
        options: Command line options.
    """

    cache_disabled = False

    if options.debug_mode:
        cache_disabled = True

    # Inititalize URL mapping
    url_mapping = typhoonae.initURLMapping(conf, options)

    while True:
        (inp, out, unused_err, env) = fcgiapp.Accept()

        # Initialize application environment
        os_env = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        os.environ['APPLICATION_ID'] = conf.application
        os.environ['CURRENT_VERSION_ID'] = conf.version + ".1"
        os.environ['AUTH_DOMAIN'] = options.auth_domain
        os.environ['SERVER_SOFTWARE'] = options.server_software
        os.environ['SCRIPT_NAME'] = ''
        os.environ['TZ'] = 'UTC'
        os.environ['USER'] = 'apphosting'

        # Get user info and set the user environment variables
        email, admin, user_id = typhoonae.handlers.login.getUserInfo(
            os.environ.get('HTTP_COOKIE', None))
        os.environ['USER_EMAIL'] = email
        os.environ['USER_ID'] = user_id
        if admin:
            os.environ['USER_IS_ADMIN'] = '1'
        else:
            os.environ['USER_IS_ADMIN'] = '0'
        nickname = None
        if email:
            nickname = email.split('@')[0]
        os.environ['USER_NICKNAME'] = nickname or ''
        os.environ['USER_ORGANIZATION'] = ''

        # CGI handler chain
        cgi_handler_chain = CGIHandlerChain(
            typhoonae.blobstore.handlers.UploadCGIHandler(
                upload_url=options.upload_url))

        # Redirect standard input and output streams
        sys.stdin = cgi_handler_chain(CGIInAdapter(inp), os.environ)
        sys.stdout = CGIOutAdapter(out)

        # Compute script path and set PATH_TRANSLATED environment variable
        path_info = os.environ['PATH_INFO']
        for pattern, handler_path, script, login_required, admin_only in url_mapping:
            if re.match(pattern, path_info) is not None:
                os.environ['PATH_TRANSLATED'] = script
                break

        http_auth = os.environ.get('HTTP_AUTHORIZATION', False)

        internal = os.environ.get('X-TyphoonAE-Secret') == 'secret'

        try:
            if http_auth and not email and not internal:
                match = re.match(BASIC_AUTH_PATTERN, http_auth)
                if match:
                    user, pw = base64.b64decode(match.group(1)).split(':')
                    print('Status: 301 Permanently Moved')
                    print('Set-Cookie: ' + typhoonae.handlers.login.
                          getSetCookieHeaderValue(user, admin=True))
                    print('Location: %s\r\n' % os.environ['REQUEST_URI'])
            elif (login_required or admin_only) and not email and not internal:
                print('Status: 302 Requires login')
                print('Location: %s\r\n' %
                      google.appengine.api.users.create_login_url(path_info))
            else:
                # Load and run the application module
                run_module(handler_path, script)
        finally:
            # Flush buffers
            sys.stdout.flush()
            del sys.stdout
            del sys.stdin
            # Re-redirect standard input and output streams
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__

            # Restore original environment
            os.environ.clear()
            os.environ.update(os_env)

            # Finish request
            fcgiapp.Finish()

            if typhoonae.end_request_hook:
                typhoonae.end_request_hook()


def main():
    """Initializes the server."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--auth_domain", dest="auth_domain", metavar="STRING",
                  help="use this value for the AUTH_DOMAIN environment "
                  "variable", default='localhost')

    op.add_option("--blobstore_path", dest="blobstore_path", metavar="PATH",
                  help="path to use for storing Blobstore file stub data",
                  default=os.path.join('var', 'blobstore'))

    op.add_option("--datastore", dest="datastore", metavar="NAME",
                  help="use this Datastore backend (%s)"
                      % '/'.join(sorted(typhoonae.SUPPORTED_DATASTORES)),
                  default='mongodb')

    op.add_option("--debug", dest="debug_mode", action="store_true",
                  help="enables debug mode", default=False)

    op.add_option("--email", dest="email", metavar="EMAIL",
                  help="the username to use", default='')

    op.add_option("--internal_address", dest="internal_address",
                  metavar="HOST:PORT",
                  help="the internal application host and port",
                  default='localhost:8770')

    op.add_option("--log", dest="logfile", metavar="FILE",
                  help="write logging output to this file",
                  default=os.path.join(os.environ['TMPDIR'], 'fcgi.log'))

    op.add_option("--login_url", dest="login_url", metavar="STRING",
                  help="login URL", default='/_ah/login')

    op.add_option("--logout_url", dest="logout_url", metavar="STRING",
                  help="logout URL", default='/_ah/logout')

    op.add_option("--password", dest="password", metavar="PASSWORD",
                  help="the password to use", default='')

    op.add_option("--server_software", dest="server_software", metavar="STRING",
                  help="use this server software identifier",
                  default=SERVER_SOFTWARE)

    op.add_option("--smtp_host", dest="smtp_host", metavar="ADDR",
                  help="use this SMTP host", default='localhost')

    op.add_option("--smtp_port", dest="smtp_port", metavar="PORT",
                  help="use this SMTP port", default=25)

    op.add_option("--smtp_user", dest="smtp_user", metavar="STRING",
                  help="use this SMTP user", default='')

    op.add_option("--smtp_password", dest="smtp_password", metavar="STRING",
                  help="use this SMTP password", default='')

    op.add_option("--upload_url", dest="upload_url", metavar="URI",
                  help="use this upload URL for the Blobstore configuration "
                       "(no leading '/')",
                  default='upload/')

    op.add_option("--xmpp_host", dest="xmpp_host", metavar="ADDR",
                  help="use this XMPP/Jabber host", default='localhost')

    (options, args) = op.parse_args()

    if sys.argv[-1].startswith('-') or sys.argv[-1] == sys.argv[0]:
        op.print_usage()
        sys.exit(2)

    app_root = sys.argv[-1]

    logging.basicConfig(
        format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] '
               '%(message)s',
        level=logging.INFO, filename=options.logfile)

    # Change the current working directory to the application root and load
    # the application configuration
    os.chdir(app_root)
    sys.path.insert(0, app_root)
    conf = typhoonae.getAppConfig()

    # Inititalize API proxy stubs
    typhoonae.setupStubs(conf, options)

    # Serve the application
    serve(conf, options)


if __name__ == "__main__":
    main()
