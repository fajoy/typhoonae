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
"""Unit tests for the FastCGI server module."""

import StringIO
import os
import sys
import tempfile
import typhoonae.fcgiserver
import unittest


class TestCase(unittest.TestCase):
    """Tests our FastCGI server module."""

    def setUp(self):
        """Loads the sample application."""

        app_root = os.path.join(os.path.dirname(__file__), 'sample')
        os.chdir(app_root)
        sys.path.insert(0, os.getcwd())

    def testServer(self):
        """Tests the main FastCGI server loop."""

        import fcgiapp

        class Options():
            debug_mode = False
            login_url = '/_ah/login'
            logout_url = '/_ah/logout'

        self.assertRaises(
            fcgiapp.error,
            typhoonae.fcgiserver.serve,
            typhoonae.getAppConfig(), Options())

    def testRunModule(self):
        """Tries to load and run a python module."""

        def request(uri, method='GET'):
            """Fakes a get request."""

            buffer = StringIO.StringIO()
            sys.stdout = buffer
            os.environ['PATH_INFO'] = uri
            os.environ['REQUEST_METHOD'] = method
            typhoonae.fcgiserver.run_module('app', run_name='__main__')
            sys.stdout = sys.__stdout__
            del os.environ['PATH_INFO']
            del os.environ['REQUEST_METHOD']
            return buffer

        buffer = request('/')
        assert buffer.getvalue().startswith('Status: 200 OK')

        buffer = request('/unknown')
        assert buffer.getvalue().startswith('Status: 404 Not Found')

    def testCGIHandlerChain(self):
        """Tests if our CGI handler chain works."""

        chain = typhoonae.fcgiserver.CGIHandlerChain((lambda x,y:True))
        fp = StringIO.StringIO()
        chain(fp, {})
        fp.close()

    def testCGIInAdapter(self):
        """Tests the FastCGI input strem adapter."""

        stdin = StringIO.StringIO('sample data\nfoobar')
        adapted_stdin = typhoonae.fcgiserver.CGIInAdapter(stdin) 
        self.assertEqual('sample data\nfoobar', adapted_stdin.read())
        adapted_stdin.seek(0)
        self.assertEqual('sample data\n', adapted_stdin.readline())
        adapted_stdin.close()

    def testCGIOutAdapter(self):
        """Tests the FastCGI output strem adapter."""

        stdout = StringIO.StringIO()
        adapted_stdout = typhoonae.fcgiserver.CGIOutAdapter(stdout)
        adapted_stdout.write('foobar')
        adapted_stdout.flush()

        class BrokenFastCGIOutStream:
            def write(self, data):
                raise IOError

        stdout = BrokenFastCGIOutStream()
        adapted_stdout = typhoonae.fcgiserver.CGIOutAdapter(stdout)
        adapted_stdout.write('foobar')
        adapted_stdout.flush()
