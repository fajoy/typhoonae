# -*- coding: utf-8 -*-
#
# Copyright 2010, 2011 Tobias Rodäbel
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
"""Web Socket server implementation which uses tornado."""

import base64
import logging
import mimetools
import optparse
import re
import threading
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import typhoonae.websocket
import urllib2
import urlparse


DESCRIPTION = "Web Socket Service."
USAGE = "usage: %prog [options]"
LOG_FORMAT = '%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] %(message)s'

WEB_SOCKETS = {}

HANDSHAKE = 1 << 0
MESSAGE = 1 << 1
SOCKET_CLOSED = 1 << 2

HANDSHAKE_URI = '_ah/websocket/handshake'
MESSAGE_URI = '_ah/websocket/message'
SOCKET_CLOSED_URI = '_ah/websocket/closed'


def post_multipart(url, fields):
    """Posts multipart form data fields.

    Args:
        url: Post multipart form data to this URL.
        fields: A list of tuples of the form [(fieldname, value), ...].
    """

    content_type, body = encode_multipart_formdata(fields)

    body = body.encode('utf-8')

    headers = {'Content-Type': content_type,
               typhoonae.websocket.WEBSOCKET_HEADER: '',
               'Content-Length': str(len(body))}

    req = urllib2.Request(url, body, headers)

    try:
        res = urllib2.urlopen(req)
    except urllib2.URLError, e:
        reason = getattr(e, 'reason', e)
        logging.error("%s (URL: %s)" % (reason, url))
        return

    return res.read()


def encode_multipart_formdata(fields):
    """Encodes multipart form data.

    Returns content type and body.
    """

    BOUNDARY = mimetools.choose_boundary()
    CRLF = u'\r\n'
    buf = []

    for (key, value) in fields:
        buf.append(u'--%s' % BOUNDARY)
        buf.append(u'Content-Disposition: form-data; name="%s"' % key)
        buf.append(u'')
        buf.append(value)

    buf.append(u'--%s--' % BOUNDARY)
    buf.append(u'')
    body = CRLF.join(buf)
    content_type = u'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body


class BroadcastHandler(tornado.web.RequestHandler):
    """The broadcaster."""

    def post(self):
        app_id = self.request.headers.get('X-TyphoonAE-AppId')
        for s in WEB_SOCKETS[app_id].keys():
            try:
                WEB_SOCKETS[app_id][s].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[app_id][s]


class MessageHandler(tornado.web.RequestHandler):
    """Receives messages and passes them to web sockets."""

    def post(self):
        s = self.request.headers.get(typhoonae.websocket.WEBSOCKET_HEADER)
        app_id = self.request.headers.get('X-TyphoonAE-AppId')
        if s:
            try:
                WEB_SOCKETS[app_id][int(s)].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[app_id][int(s)]


class Dispatcher(threading.Thread):
    """Dispatcher thread for non-blocking message delivery."""

    def __init__(self, address, socket, request_type, param_path, body=''):
        """Constructor.

        Args:
            address: The server address.
            socket: String which represents the socket id.
            request_type: The request type.
            param_path: Parameter path.
            body: The message body.
        """
        super(Dispatcher, self).__init__()

        self._address = address
        self._socket = socket or u''
        self._type = request_type
        self._path = param_path
        self._body = body or u''

    def run(self):
        """Post message."""

        uris = {
            HANDSHAKE: HANDSHAKE_URI,
            MESSAGE: MESSAGE_URI,
            SOCKET_CLOSED: SOCKET_CLOSED_URI
        }

        url = 'http://%s:%s/%s/%s' % (
            self._address, PORT, uris[self._type], self._path)

        post_multipart(url, [(u'body', self._body), (u'from', self._socket)])


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """Dispatcher for incoming web socket requests."""

    def __init__(self, *args, **kw):
        super(WebSocketHandler, self).__init__(*args, **kw)

    def open(self, param_path):
        sock_id = self.stream.socket.fileno()
        app_id = base64.b64decode(
            re.match(r'^/([a-zA-Z0-9=]+)/.*', self.request.uri).group(1))
        if app_id not in WEB_SOCKETS:
            WEB_SOCKETS[app_id] = {}
        WEB_SOCKETS[app_id][sock_id] = self
        address = urlparse.urlsplit(self.request.headers['Origin']).hostname
        dispatcher = Dispatcher(address, str(sock_id), HANDSHAKE, param_path)
        dispatcher.start()

    def _dispatch(self, request_type, message=None):
        param_path = re.match(r"^/[a-zA-Z0-9=]+/(.*)",
                              self.request.uri).group(1)
        if self.stream.socket:
            sock_id = str(self.stream.socket.fileno())
        else:
            sock_id = None
        address = urlparse.urlsplit(self.request.headers['Origin']).hostname
        dispatcher = Dispatcher(
            address, sock_id, request_type, param_path, body=message)
        dispatcher.start()

    def on_message(self, message):
        self._dispatch(request_type=MESSAGE, message=message)

    def on_close(self):
        self._dispatch(request_type=SOCKET_CLOSED)


def main():
    """The main function."""

    global PORT

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--internal_port", dest="internal_port", metavar="PORT",
                  help="the application internal port",
                  default=8770)

    op.add_option("--port", dest="port", metavar="PORT",
                  help="port for the Web Socket server to listen on",
                  default=8888)

    (options, args) = op.parse_args()

    PORT = options.internal_port

    logging.basicConfig(format=LOG_FORMAT, level=logging.ERROR)

    application = tornado.web.Application([
        (r"/broadcast", BroadcastHandler),
        (r"/message", MessageHandler),
        (r"/[a-zA-Z0-9=]+/(.*)", WebSocketHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
