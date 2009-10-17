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
"""FastCGI script to serve a CGI application."""

import StringIO
import fcgiapp
import logging
import optparse
import os
import re
import runpy
import sys
import typhoonae
import typhoonae.handlers.login

DESCRIPTION = ("FastCGI application server.")
USAGE = "usage: %prog [options] <application root>"


_module_cache = dict()

def run_module(mod_name, init_globals=None, run_name=None):
    """Execute a module's code without importing it.

    Caches module loader and code and returns the resulting top level namespace
    dictionary.
    """
    global _module_cache

    if mod_name not in _module_cache:
        loader = runpy.get_loader(mod_name)
        if loader is None:
            raise ImportError("No module named " + mod_name)
        if loader.is_package(mod_name):
            raise ImportError(("%s is a package and cannot " +
                              "be directly executed") % mod_name)
        code = loader.get_code(mod_name)
        if code is None:
            raise ImportError("No code object available for " + mod_name)
        _module_cache[mod_name] = (loader, code)
    else:
        loader, code = _module_cache[mod_name]

    filename = loader.get_filename(mod_name)

    if run_name is None:
        run_name = mod_name
    if sys.hexversion > 33883376:
        pkg_name = mod_name.rpartition('.')[0]
        return runpy._run_module_code(code, init_globals, run_name,
                                      filename, loader, pkg_name)
    return runpy._run_module_code(code, init_globals, run_name,
                                  filename, loader, alter_sys=True)


def serve(conf):
    """Implements the server loop.

    Args:
        conf: The application configuration.
    """

    # Inititalize URL mapping
    url_mapping = typhoonae.initURLMapping(conf)

    back_ref_pattern = re.compile(r'\\([0-9]*)')

    class StdinAdapter:
        """Adapter for FastCGI input stream objects."""

        def __init__(self, i):
            self.i = i

        def read(self, *args):
            return self.i.read(*args)

        def readline(self, *args):
            return self.i.readline()

        def seek(self, *args):
            return self.i.seek(*args)

    while True:
        (inp, out, unused_err, env) = fcgiapp.Accept()

        # Redirect standard input and output streams
        sys.stdin = StdinAdapter(inp)
        sys.stdout = out

        # Initialize application environment
        os_env = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        os.environ['APPLICATION_ID'] = conf.application
        os.environ['AUTH_DOMAIN'] = 'localhost'
        os.environ['SERVER_SOFTWARE'] = 'TyphoonAE/0.1.0'
        os.environ['TZ'] = 'UTC'

        # Get user info and set the user environment variables
        email, admin, user_id = typhoonae.handlers.login.getUserInfo(
            os.environ.get('HTTP_COOKIE', None))
        os.environ['USER_EMAIL'] = email
        if admin:
            os.environ['USER_IS_ADMIN'] = '1'
        os.environ['USER_ID'] = user_id

        # Compute script path and set PATH_TRANSLATED environment variable
        path_info = os.environ['PATH_INFO']
        for pattern, name, script in url_mapping:
            # Check for back reference
            if re.match(pattern, path_info) is not None:
                m = back_ref_pattern.search(name)
                if m:
                    ind = int(m.group(1))
                    mod = path_info.split('/')[ind]
                    name = '.'.join(name.split('.')[0:-1]+[mod])
                os.environ['PATH_TRANSLATED'] = script
                os.chdir(os.path.dirname(script))
                break

        try:
            # Load and run the application module
            run_module(name, run_name='__main__')
        finally:
            # Re-redirect standard input and output streams
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__

            # Restore original environment
            os.environ.clear()
            os.environ.update(os_env)

            # Finish request
            fcgiapp.Finish()


def main():
    """Initializes the server."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--log", dest="logfile", metavar="FILE",
                  help="write logging output to this file",
                  default=os.path.join(os.environ['TMPDIR'], 'fcgi.log'))

    op.add_option("--xmpp_host", dest="xmpp_host", metavar="HOST",
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
    serve(conf)


if __name__ == "__main__":
    main()
