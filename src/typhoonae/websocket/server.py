"""Web Socket server implementation which uses tornado."""

import base64
import logging
import mimetools
import optparse
import threading
import tornado.httpserver
import tornado.ioloop
import tornado.web
import typhoonae.handlers.login
import typhoonae.websocket
import typhoonae.websocket.tornado_handler
import urllib2


ADDRESS = 'host:port'
DESCRIPTION = "Web Socket Service."
USAGE = "usage: %prog [options]"
WEB_SOCKETS = {}


def post_multipart(url, credentials, fields):
    """Posts multipart form data fields.

    Args:
        url: Post multipart form data to this URL.
        credentials: Authentication credentials to be used when posting.
        fields: A list of tuples of the form [(fieldname, value), ...].
    """

    content_type, body = encode_multipart_formdata(fields)

    body = body.encode('utf-8')

    headers = {'Content-Type': content_type,
               typhoonae.websocket.WEBSOCKET_HEADER: '',
               'Content-Length': str(len(body))}

    if credentials:
        headers['Authorization'] = 'Basic %s' % base64.b64encode(credentials)

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
                del WEB_SOCKET


class Poster(threading.Thread):
    """Poster thread for non-blocking message delivery."""

    def __init__(self, body, socket):
        """Constructor.

        Args:
            body: The message body.
            socket: String which represents the socket id.
        """
        super(Poster, self).__init__()
        self.__body = body
        self.__socket = socket

    def run(self):
        """Post message."""

        post_multipart(
            'http://%s/_ah/websocket/message/' % ADDRESS,
            None,
            [(u'body', self.__body), (u'from', self.__socket)])


class WebSocketHandler(typhoonae.websocket.tornado_handler.WebSocketHandler):
    """Dispatcher for incoming web socket requests."""

    def __init__(self, *args, **kw):
        super(WebSocketHandler, self).__init__(*args, **kw)
        logging.info('initializing %s' % self)

    def open(self):
        self.receive_message(self.on_message)
        WEB_SOCKETS[self.stream.socket.fileno()] = self

    def on_message(self, message):
        poster = Poster(message, str(self.stream.socket.fileno()))
        poster.start()
        self.receive_message(self.on_message)


def main(app_id='demo', port=8888):
    """The main function.

    Args:
        port: The port to listen on.
    """
    global ADDRESS

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address", metavar="HOST:PORT",
                  help="the application host and port",
                  default="localhost:8080")

    (options, args) = op.parse_args()

    ADDRESS = options.address

    typhoonae.handlers.login.authenticate('websocket@typhoonae', admin=True)

    application = tornado.web.Application([
        (r"/broadcast", BroadcastHandler),
        (r"/message", MessageHandler),
        (r"/%s/?" % app_id, WebSocketHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
