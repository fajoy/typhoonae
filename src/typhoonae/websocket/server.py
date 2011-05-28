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
"""TyphoonAE's Web Socket Service backet by Tornado web."""

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

HANDSHAKE = 0
MESSAGE = 1
SOCKET_CLOSED = 2

HANDSHAKE_URI = '_ah/websocket/handshake'
MESSAGE_URI = '_ah/websocket/message'
SOCKET_CLOSED_URI = '_ah/websocket/closed'

URIs = {HANDSHAKE: HANDSHAKE_URI,
        MESSAGE: MESSAGE_URI,
        SOCKET_CLOSED: SOCKET_CLOSED_URI}

WEBSOCKET_ORIGIN_HEADER = typhoonae.websocket.WEBSOCKET_ORIGIN_HEADER


def post_multipart(url, fields, add_headers={}):
    """Posts multipart form data fields.

    Args:
        url: Post multipart form data to this URL.
        fields: A list of tuples of the form [(fieldname, value), ...].
        add_headers: Dict of additional headers to be included into the request.
    """

    content_type, body = encode_multipart_formdata(fields)

    body = body.encode('utf-8')

    headers = {'Content-Type': content_type,
               typhoonae.websocket.WEBSOCKET_HEADER: '',
               'Content-Length': str(len(body))}

    headers.update(add_headers)

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
        key = self.request.headers.get('X-TyphoonAE-ServerName')
        for s in WEB_SOCKETS[key].keys():
            try:
                WEB_SOCKETS[key][s].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[key][s]


class MessageHandler(tornado.web.RequestHandler):
    """Receives messages and passes them to web sockets."""

    def post(self):
        s = self.request.headers.get(typhoonae.websocket.WEBSOCKET_HEADER)
        key = self.request.headers.get('X-TyphoonAE-ServerName')
        if s:
            try:
                WEB_SOCKETS[key][int(s)].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[key][int(s)]


class Dispatcher(threading.Thread):
    """Dispatcher thread for non-blocking message delivery."""

    def __init__(self, address, socket, request_type, param_path, headers={},
                 body=''):
        """Constructor.

        Args:
            address: The server address.
            socket: String which represents the socket id.
            request_type: The request type.
            param_path: Parameter path.
            headers: Dict of headers to be submitted to the request handler.
            body: The message body.
        """
        super(Dispatcher, self).__init__()

        self._address = address
        self._socket = socket or u''
        self._type = request_type
        self._path = param_path
        self._headers = headers
        self._body = body or u''

    def run(self):
        """Post message."""

        url = 'http://%s:%s/%s/%s' % (
            self._address, PORT, URIs[self._type], self._path)

        post_multipart(
            url,
            [(u'body', self._body), (u'from', self._socket)],
            self._headers)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """Dispatcher for incoming web socket requests."""

    def __init__(self, *args, **kw):
        super(WebSocketHandler, self).__init__(*args, **kw)

    def open(self, path):
        sock_id = self.stream.socket.fileno()
        addr = self.request.headers['Host'].split(':')[0]
        if addr not in WEB_SOCKETS:
            WEB_SOCKETS[addr] = {}
        WEB_SOCKETS[addr][sock_id] = self
        headers = {WEBSOCKET_ORIGIN_HEADER: self.request.headers['Origin']}
        dispatcher = Dispatcher(
            addr, str(sock_id), HANDSHAKE, path, headers=headers)
        dispatcher.start()

    def _dispatch(self, request_type, message=None):
        path = re.match(r"^/(.*)", self.request.uri).group(1)
        if self.stream.socket:
            sock_id = str(self.stream.socket.fileno())
        else:
            sock_id = None
        addr = self.request.headers['Host'].split(':')[0]
        headers = {WEBSOCKET_ORIGIN_HEADER: self.request.headers['Origin']}
        dispatcher = Dispatcher(
            addr, sock_id, request_type, path, headers=headers, body=message)
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

    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

    application = tornado.web.Application([
        (r"/broadcast", BroadcastHandler),
        (r"/message", MessageHandler),
        (r"/(.*)", WebSocketHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
