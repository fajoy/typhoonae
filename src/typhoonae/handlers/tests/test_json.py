# -*- coding: utf-8 -*-
#
# Copyright 2010 Florian Glanzner 
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
"""Unit tests for the json-rpc request handles and helper functions."""
 
import google.appengine.ext.webapp
import unittest
import webob
import typhoonae.handlers.json_rpc as jrpc
from google.appengine.ext.webapp import Request, Response
 
 

class JSONRPCHandlerTestCase(unittest.TestCase):
    class MyTestHandler(jrpc.JSONRPCHandler):
        @jrpc.ServiceMethod
        def myMethod(self, a, b):
            return a + b
        def noServiceMethod():
            pass

    def setUp(self):
        """
        Set up the test with a simple TestHandler
        """
        h = self.MyTestHandler()
        h.request = Request.blank('/rpc/')
        h.response = Response()
        self.handler = h
    
    def getHandler(self):
        self.handler.response.clear()
        return self.handler

    def testJsonParsing(self):
        """
        The request body must contain valid json.
        An empty body should result in a ParseError.
        """
        h = self.getHandler()
        h.request.body = ''         
        self.assertRaises(jrpc.ParseError, h.post)


    def testRPCParsing(self):
        """
        Valid json but not valid json-rpc should result 
        in a InvalidRequestError. 
        """
        h = self.getHandler()
        # For JSON-RPC 2.0 the body must contain a member "jsonrpc".
        h.request.body = '''{"method":"myMethod"}'''
        self.assertRaises(jrpc.InvalidRequestError, h.post)
        h.response.clear()

        # A member "method must exist"
        h.request.body = '''{"jsonrpc":"2.0"}'''
        self.assertRaises(jrpc.InvalidRequestError, h.post)
        h.response.clear()
        
        # only "method", "jsonrpc", "id" and "params" members allowed
        h.request.body = '''{"jsonrpc":"2.0", "method":"myMethod", "BAD":"."}'''
        self.assertRaises(jrpc.InvalidRequestError, h.post)
        h.response.clear()

        #params member must be object or tuple
        h.request.body = '''{"jsonrpc":"2.0", "method":"myMethod",\
                "params":"BAD"}'''
        self.assertRaises(jrpc.InvalidRequestError, h.post)
        h.response.clear()

    def testParams(self):
        """
        Test Wrong parameters for the given 'method'
        """
        h = self.getHandler()
        h.request.body  = '''{"jsonrpc":"2.0", "method":"myMethod", \
                "params":["A","B", "BAD"], "id":"1"}'''
        self.assertRaises(jrpc.InvalidParamsError, h.post)
        h.response.clear()

        #test a params object
        h.request.body  = '''{"jsonrpc":"2.0", "method":"myMethod", \
                "params":{"a":"A","b":"B"}, "id":"1"}'''
        h.post()
        self.assertEqual(h.response._Response__status, (200, 'OK'))

    def testServiceMethod(self):
        """
        Tests the 'ServiceMethod' Annotation for methods
        exposted by the handler
        """
        h = self.getHandler()
        # See MyTestHandler. 'myMethod' is exposed as serviceMethod.
        b = '''{"jsonrpc":"2.0", "method":"myMethod", \
                "params":["A","B"], "id":"1"}'''
        h.request.body = b
        h.post()       
        self.assertEqual(h.response.out.getvalue(),
                '''{"jsonrpc": "2.0", "result": "AB", "id": "1"}''')
        h.response.clear()

        # 'noServiceMethod' is not a ServiceMethod
        b = '''{"jsonrpc":"2.0", "method":"noServiceMethod", \
                "params":["A","B"], "id":"1"}'''
        h.request.body = b
        self.assertRaises(jrpc.MethodNotFoundError, h.post)
        
    def testNotification(self):
        """
        Notification do not contain a member "id" in the body.
        There is no reply for a notification.
        HTTP-Status is 204 (No Content)
        """
        
        h = self.getHandler()
        # Valid Request with no ID
        h.request.body = '''{"jsonrpc":"2.0", "method":"myMethod", \
                "params":["A","B"]}'''
        h.post()
        self.assertEqual(h.response._Response__status, (204, 'No Content'))
        self.assertEqual(h.response.out.getvalue(), '')
        h.response.clear()

        #TODO Test that there is a 204 in case of an error 