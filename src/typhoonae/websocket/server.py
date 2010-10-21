"""Web Socket server implementation which uses tornado."""

import logging
import mimetools
import optparse
import re
import threading
import tornado.httpserver
import tornado.ioloop
import tornado.web
import typhoonae.websocket
import typhoonae.websocket.tornado_handler
import urllib
import urllib2


DESCRIPTION = "Web Socket Service."
USAGE       = "usage: %prog [options]"
WEB_SOCKETS = {}

HANDSHAKE = 1 << 0
MESSAGE   = 1 << 1

HANDSHAKE_URL = 'http://%s/_ah/websocket/handshake/%s'
MESSAGE_URL   = 'http://%s/_ah/websocket/message/%s'


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
        logging.error(reason)
        return

    return res.read()


def encode_multipart_formdata(fields):
    """Encodes multipart form data.

    Returns content type and body.
    """

    BOUNDARY = mimetools.choose_boundary()
    CRLF = u'\r\n'
    buffer = []

    for (key, value) in fields:
        buffer.append(u'--%s' % BOUNDARY)
        buffer.append(u'Content-Disposition: form-data; name="%s"' % key)
        buffer.append(u'')
        buffer.append(value)

    buffer.append(u'--%s--' % BOUNDARY)
    buffer.append(u'')
    body = CRLF.join(buffer)
    content_type = u'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body


class BroadcastHandler(tornado.web.RequestHandler):
    """The broadcaster."""

    def post(self):
        for id in WEB_SOCKETS.keys():
            try:
                WEB_SOCKETS[id].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[id]


class MessageHandler(tornado.web.RequestHandler):
    """Receives messages and passes them to web sockets."""

    def post(self):
        id = self.request.headers.get('X-Typhoonae-Websocket')
        if id:
            try:
                WEB_SOCKETS[int(id)].write_message(self.request.body)
            except IOError:
                del WEB_SOCKETS[int(id)]


class Dispatcher(threading.Thread):
    """Dispatcher thread for non-blocking message delivery."""

    def __init__(self, socket, request_type, param_path, body=''):
        """Constructor.

        Args:
            socket: String which represents the socket id.
            request_type: The request type.
            param_path: Parameter path.
            body: The message body.
        """
        super(Dispatcher, self).__init__()
        self._socket = socket
        self._type = request_type
        self._path = param_path
        self._body = body

    def run(self):
        """Post message."""

        if self._type == HANDSHAKE:
            url = HANDSHAKE_URL % (ADDRESS, self._path)
        elif self._type == MESSAGE:
            url = MESSAGE_URL % (ADDRESS, self._path)
        post_multipart(url, [(u'body', self._body), (u'from', self._socket)])


class WebSocketHandler(typhoonae.websocket.tornado_handler.WebSocketHandler):
    """Dispatcher for incoming web socket requests."""

    def __init__(self, *args, **kw):
        super(WebSocketHandler, self).__init__(*args, **kw)

    def open(self, param_path):
        sock_id = self.stream.socket.fileno()
        WEB_SOCKETS[sock_id] = self
        dispatcher = Dispatcher(str(sock_id), HANDSHAKE, param_path)
        dispatcher.start()
        self.receive_message(self.on_message)

    def on_message(self, message):
        param_path = re.match(r'/%s/(.*)' % APP_ID, self.request.uri).group(1)
        sock_id = self.stream.socket.fileno()
        dispatcher = Dispatcher(
            str(sock_id),
            MESSAGE,
            param_path,
            body=message)
        dispatcher.start()
        self.receive_message(self.on_message)


def main():
    """The main function."""

    global ADDRESS, APP_ID

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address", metavar="HOST:PORT",
                  help="the application host and port",
                  default="localhost:8080")

    op.add_option("--app_id", dest="app_id", metavar="STRING",
                  help="the application id", default="")

    (options, args) = op.parse_args()

    ADDRESS = options.address
    APP_ID = options.app_id

    application = tornado.web.Application([
        (r"/broadcast", BroadcastHandler),
        (r"/message", MessageHandler),
        (r"/%s/(.*)" % urllib.quote(APP_ID), WebSocketHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
