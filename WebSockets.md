# Web Socket API #

The [Web Socket protocol](http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76) enables web applications to maintain bidirectional communications with server-side processes. The typhoonae.websocket package provides a Web Socket Service API for GAE applications. It was introduced by the TyphoonAE 0.1.2 release and _does not run on the productive Google App Engine platform_.

However, in order to enable the Web Socket API for the Google App Engine SDK,
go through the following guide.

## Patching the Google App Engine SDK (Python) to enable TyphoonAE's Web Socket API ##

To get an idea how Web Sockets could work with GAE download the SDK 1.5.0 patch from this [location](http://typhoonae.googlecode.com/files/gae-websocket-4.0.tar.gz). It also includes a demo app and some basic instructions.

## Web Borwsers Supporting Web Sockets ##

  * [Chrome](http://www.google.com/chrome/)
  * [Safari](http://www.apple.com/safari/)
  * [Prototype IE8 IE9 implementation](http://html5labs.interoperabilitybridges.com/prototypes/websockets/websockets/info)
  * [Mozilla Firefox 4](http://www.mozilla-europe.org/en/firefox/) **Note**: Since Beta 8 Firefox has [disabled Web Sockets by default](http://www.0xdeadbeef.com/weblog/2010/12/disabling-websockets-for-firefox-4/)

## Overview ##

Since Bret Taylor [came up](http://bret.appspot.com/entry/web-sockets-in-tornado) with a neat implementation of a [Web Socket handler](https://github.com/facebook/tornado/blob/master/tornado/websocket.py) for the [Tornado](http://www.tornadoweb.org/) web server, it's no longer a hassle to get an experimental Web Socket service up and running. A client can establish a Web Socket connection to the service which solely utilizes web hooks to dispatch messages to and from an application.

![http://typhoonae.googlecode.com/hg/doc/source/websocket.png](http://typhoonae.googlecode.com/hg/doc/source/websocket.png)

A client requests (1) a web page containing the Java Script call to establish a
Web Socket connection (2) to a URL provided by the application. The application
and Web Socket service communicate over web hooks (3, 4).

## Sending and Receiving Web Socket Messages ##

We distinguish between two types of incoming Web Socket messages. A handshake
message is received once per Web Socket session when the client establishes the
connection. This type of message can be handled seperately by a request
handler. All other incoming messages can be handled by another request handler.
The API we use in our handshake handler as well as in the handler for all other
incoming Web Socket messages doesn't differ. However, in many cases it is very
useful to handle Web Socket handshake messages seperately from _normal_
messages.

In order to handle incoming Web Socket requests, add this script handler to
the handlers section of the app.yaml file.

```
  - url: /_ah/websocket/.*
    script: script.py
    login: admin
```

Define the correct URL mapping for your WSGI application:

```
  app = google.appengine.ext.webapp.WSGIApplication([
    ('/_ah/websocket/handshake/(.*)', HandshakeHandler),
    ('/_ah/websocket/message/(.*)', MessageHandler),
  ], debug=True)
```

Our Web Socket API provides a convenience function to obtain the appropriate
service URL. It has one argument for additional URI information:

```
  websocket_url = typhoonae.websocket.create_websocket_url('/foo/bar')
```

The following request handler receives and sends messages from and to a Web
Socket. The POST method is used to receive an incoming message where the first
non-self argument contains the additional URI information from above:

```
  class MessageHandler(google.appengine.ext.webapp.RequestHandler):
    """Handles Web Socket requests."""

    def post(self, path):
      message = typhoonae.websocket.Message(self.request.POST)
      typhoonae.websocket.send_message(
        [message.socket], 'Received: "%s"' % message.body)
```

A `message` object has the two attributes `socket` and `body`. The former is a
string containing the socket id. The latter contains our message body as a
unicode string.

The client, usually a Web Socket capable browser, establishes a Web Socket by
using Java Script:

```
  ws = new WebSocket("ws://example.com");
```

### Broadcast Messages ###

TyphoonAE adds another very useful function which enables an app to broadcast
messages to all currently open Web Sockets of an app. Without this convenient
method a developer has to implement a solution to _remember_ all open Web
Sockets. By using `broadcast_message` the Web Socket service takes care of it.

```
  class MessageHandler(google.appengine.ext.webapp.RequestHandler):
    """Handles Web Socket requests."""

    def post(self, path):
      message = typhoonae.websocket.Message(self.request.POST)
      typhoonae.websocket.broadcast_message(message.body)
```

### Handling Closed Sockets ###

Applications sometimes should be informed when a socket is closed. Therefore,
an app can implement a third request handler for the following URL pattern:

```
    '/_ah/websocket/closed/(.*)'
```

The success path can be utilized for keeping track of additional informations
such as encoded user IDs.

```
  class SocketClosedHandler(google.appengine.ext.webapp.RequestHandler):
    """Handler for socket closed events."""

    def post(self, path):
      user = decode_user_from_path(path)
      typhoonae.websocket.broadcast_message('%s has left the building' % user)
```


See http://dev.w3.org/html5/websockets/ for further information on Web Sockets.