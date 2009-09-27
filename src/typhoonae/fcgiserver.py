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
import time
import traceback
import typhoonae
import typhoonae.handlers.login

DESCRIPTION = ("FastCGI application server.")
USAGE = "usage: %prog [options] <application root>"


def get_traceback():
    """Returns traceback."""

    output = StringIO.StringIO()
    traceback.print_exc(file=output)
    value = output.getvalue()
    output.close()

    return value


def serve(conf):
    """Implements the server loop.

    Args:
        conf: The application configuration.
    """

    # Inititalize URL mapping
    url_mapping = typhoonae.initURLMapping(conf)

    module_cache = dict()

    while True:
        (inp, out, err, env) = fcgiapp.Accept()

        # Redirect standard input, output and error streams
        sys.stdin = inp
        sys.stdout = out
        sys.stderr = err

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
        for pattern, name, script in url_mapping:
            if re.match(pattern, os.environ['PATH_INFO']) is not None:
                os.environ['PATH_TRANSLATED'] = script
                break

        try:
            # Lookup module in cache
            if name in module_cache:
                module_cache[name]['main']()
            else:
                # Load and run the application module
                mod = runpy.run_module(name, run_name='__main__')
                # Store module in the cache
                module_cache[name] = mod
        except:
            try:
                tb = get_traceback()
                logging.error(tb)
                print 'Content-Type: text/plain\n'
                print tb
            except IOError:
                # TODO: Check whether it occurs due to a broken FastCGI
                # pipe or if we have some kind of leak
                pass
        finally:
            # Re-redirect standard input, output and error streams
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

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
    typhoonae.setupStubs(conf)

    # Serve the application
    try:
        serve(conf)
    except:
        logging.error(get_traceback())


if __name__ == "__main__":
    main()
