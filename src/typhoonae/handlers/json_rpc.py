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
"""
JSONRPCHandler.
A webapp.RequestHandler for TyphoonAE and Google App Engine
See specs:
http://groups.google.com/group/json-rpc/web/json-rpc-2-0
http://groups.google.com/group/json-rpc/web/json-rpc-over-http

This version does not support:
  - *args, **kwargs and default-values are not supported for Service Methods
  - Batching not implemented
  - type hinting not implemented
  - Handle only HTTP POST
  - json-rpc Version < 2.0 (same as 1.2) not handled

TODO:
 - Tests
 - more Comments
 - Examples (doctest?)
 - Logging dependant on debug mode
 - ...
"""
from django.utils.simplejson import dumps, loads
from google.appengine.ext import webapp
from inspect import getargspec

def ServiceMethod(fn):
    fn.IsServiceMethod = True
    return fn

class JsonRpcError(Exception):
    """
    Baseclass for all JSON-RPC Errors.
    Errors are described in the JSON-RPC 2.0 specs, related HTTP Status
    Codes are described in the json-rpc-over-http proposal.
    """
    code = 0
    message = None
    data = None
    status = 500

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __str__(self):
        return(self.message)

    def __repr__(self):
        return '%s("%s")' % (str(self.__class__.__name__), self.message)

    def getJsonData(self):
        error = {
            'code' : self.code ,
            'message' : '%s: %s' %
                (str(self.__class__.__name__),
                str(self.message)),
            'data' : self.data}
        # TODO More / less info depending on DEBUG mode
        return error
        
class ParseError(JsonRpcError):
    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """
    code = -32700
    message = 'Parse error.'

class InvalidRequestError(JsonRpcError):
    """
    The JSON sent is not a valid Request object.
    """
    code = -32600
    message = 'Invalid Request.'
    status = 400

class MethodNotFoundError(JsonRpcError):
    """
    The method does not exist / is not available.
    """
    code = -32601
    message = 'Method not found.'
    status = 404

class InvalidParamsError(JsonRpcError):
    """
    Invalid method parameter(s).
    """
    code = -32602
    message = 'Invalid params'

class InternalError(JsonRpcError):
    """
    Internal JSON-RPC error.
    """
    code = -32603
    message = 'Internal error.'

class ServerError(JsonRpcError):
    """
    Base Class for implementation-defined Server Errors.
    The Error Code must be between -32099..-32000
    """
    code = -32000
    message = 'Server Error'

class JSONRPCHandler(webapp.RequestHandler):
    """
    TODO
    """
    
    def __init__(self):
        webapp.RequestHandler.__init__(self)

        # Will set to True when the request is a notification.
        self.notification = False
        self.message_id = None
        self.params = ()
        self.method_name = None

    def post(self):
        self.handle_post()

    def handle_post(self):
        """
        post
        """
        try:
            self.parse_jsonrpc()    # raises InvalidRequestError, ParseError
            method = self.getServiceMethod()    # raises MethodNotFoundError
            result = self.executeMethod(method, self.params) # raises InvalidParamsError
            
            if self.notification:
                self.error(204)
            else:
                self.response.headers['Content-Type'] = 'application/json-rpc'
                http_body = self.encodeResponse(result, self.message_id)
                self.response.out.write(http_body)
        except (ParseError,
                InvalidRequestError,
                MethodNotFoundError,
                InvalidParamsError,
                ServerError),ex:
            self.error(ex.status)
            body = self.encodeResponse(ex.getJsonData(),
                self.message_id,
                error = True)
            if not self.notification:   #even no error return on notifications
                self.response.out.write(body)
        except Exception, ex:
            #TODO Handle all other exceptions. -> InternalError. Logging.
            raise

    def parse_jsonrpc(self):
        try:
            json = loads(self.request.body)
        except ValueError:
            raise ParseError()
            
        #TODO raise error when batch processing requested

        if not isinstance(json, dict):
            raise InvalidRequestError('No valid JSON-RPC Message. Must be an object')

        if not set(json.keys()) <= frozenset(['method','jsonrpc','params','id']):
            raise InvalidRequestError('Invalid members in request object')

        if not ('jsonrpc' in json and json['jsonrpc'] == '2.0'):
            raise InvalidRequestError('Server support JSON-RPC Ver. 2.0 only')

        if 'method' not in json:
            raise InvalidRequestError('No method specified')
        if not isinstance(json['method'], basestring):
            raise InvalidRequestError('"method" must be a string')
        self.method_name = json['method']

        if 'id' not in json:
            self.notification = True
        else:
            self.message_id = json['id']

        if 'params' in json:
            params = json['params']
            if not isinstance(params, (dict, list, tuple)):
                raise InvalidRequestError('"params" must be an array or object.')
            self.params = params

    def getServiceMethod(self):
        # TODO use inspect.getmembers()?
        method = getattr(self, self.method_name, None)
        if not method or not self.hasServiceMethodAnnotation(method):
            raise MethodNotFoundError('Method %s not found'%self.method_name)
        return method

    def executeMethod(self, method, params):
            args = set(getargspec(method)[0][1:])
            if isinstance(params, (list, tuple)):
                if not len(args) == len(params):
                    raise InvalidParamsError("Wrong number of parameters. "+
                        "Expected %i got %i."%(len(args),len(params)))
                return method(*params)
            if isinstance(params, dict):
                paramset = set(params)
                if not args == paramset:
                    raise InvalidParamsError("Named parameters do not "+
                        "match method. Expected %s."%(str(args)))
                params = self.dictKeysToAscii(params)
                return method(**params)

    def encodeResponse(self, data, mid, error=False):
        key = 'result'
        if error: key = 'error'
        body = {'jsonrpc':'2.0', key:data, 'id':mid}
        return dumps(body)

    def hasServiceMethodAnnotation(self, f):
        """
        Test if a function was annotated @ServiceMethod
        """
        return hasattr(f, 'IsServiceMethod') and \
            getattr(f, 'IsServiceMethod') == True

    def dictKeysToAscii(self, d):
        """
        Convert all keys to str.
        Maybe Unicode in JSON but no Unicode as keys in python allowed
        """
        try:
            r = {}
            for (k, v) in d.iteritems():
                r[str(k)] = v
            return r
        except UnicodeEncodeError:
            # unsure which error is the correct to raise here
            raise InvalidRequestError("Parameter-names must be ASCII")

###########################
# Test only
    @ServiceMethod
    def aServiceMethod(self, a):
        return 'is A service method: ' +a

    def notAServiceMethod(self):
        return 'noo'