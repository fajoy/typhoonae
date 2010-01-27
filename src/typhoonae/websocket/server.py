"""Web Socket server implementation which uses tornado."""

import logging
import tornado.httpserver
import tornado.ioloop
import tornado.web
import typhoonae.websocket.tornado_handler


WEB_SOCKETS = []


class BroadcastHandler(tornado.web.RequestHandler):
    """The broadcaster."""

    def post(self):
        for ws in list(WEB_SOCKETS):
            try:
                ws.write_message(self.request.body)
            except IOError:
                WEB_SOCKETS.remove(ws)


class WebSocketHandler(typhoonae.websocket.tornado_handler.WebSocketHandler):
    """Dispatcher for incoming web socket requests."""

    def __init__(self, *args, **kw):
        super(WebSocketHandler, self).__init__(*args, **kw)
        logging.info('initializing %s' % self)

    def open(self):
        self.receive_message(self.on_message)
        WEB_SOCKETS.append(self)

    def on_message(self, message):
        self.write_message(message)
        self.receive_message(self.on_message)



def main(app_id='demo', port=8888):
    """The main function.

    Args:
        port: The port to listen on.
    """
    application = tornado.web.Application([
        (r"/broadcast", BroadcastHandler),
        (r"/%s/?" % app_id, WebSocketHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
