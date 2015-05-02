# Channel API #

As [announced](http://code.google.com/events/io/2010/sessions/building-real-time-apps-app-engine-feed-api.html) at Google I-O 2010, the [Channel API](http://code.google.com/appengine/docs/python/channel/overview.html) enables developers to build applications that can push content directly to your user’s browser. The technique behind that is widely known as _Comet_. In fact, Comet subsumes multiple techniques and mainly allows a web application to push data to a browser via long-held HTTP requests, without the browser explicitly requesting it.

If you have followed the link above to the Google I-O presentation you should have noticed the neat [Trivia Quiz](http://www.youtube.com/watch?v=oMXe-xK0BWA&t=7m46s) application. If you're lucky [the original demo](http://io-trivia-quiz.appspot.com) is still online. However, [here](http://trivia-quiz.typhoonae.org:8080) is the same app running on TyphoonAE without any changes.

## How Things Work With TyphoonAE ##

TyphoonAE uses the [NGINX HTTP push module](http://pushmodule.slact.net) to
provide a powerful and scaleable server-side implementation. It can easily
handle thousands of open channels. For our more technically inclined readers,
Channels are stored in a [red-black tree](http://en.wikipedia.org/wiki/Red-black_tree), and have an O(log(N)) retrieval cost.
The module's [project page](http://pushmodule.slact.net) also tells that all
other operations are constant-time, so things should scale quite well.

A client, typically a web browser, uses Ajax with long polling to detect new
information on the server. TyphoonAE delivers the appropriate Javascript API
which is most possibly compatible with Google's Channel API. Due to the fact
that Google has not yet officially released the Channel API, our implementation
is _experimental_ and might be subject to change in future releases.

## Availability ##

The Channel API is available in the productive GAE environment since Google
[released](http://googleappengine.blogspot.com/2010/12/happy-holidays-from-app-engine-team-140.html) the App Engine SDK 1.4.0. TyphoonAE introduces its alternative Channel API backend with the 0.2.0 release.

## Creating Channels ##

An app can create channels by calling the Channel API `google.appengine.api.channel`. It requires only a few lines of code to be added to our request handler.

Here is an example handler script using the webapp framework:

```
  class MyRequestHandler(webapp.RequestHandler):

    def get(self):
      channel_id = channel.create_channel('mychannel')
      output = template.render('index.html', {'channel_id': channel_id})
      self.response.out.write(output)
```

The channel id is passed to our `index.html`.

```
  <html>
    <head>
      <title>My Channel Demo</title>
      <script type="text/javascript" src="/_ah/channel/jsapi"></script>
      <script type="text/javascript">

        var channel = new goog.appengine.Channel('{{ channel_id }}');
        var socket = channel.open()

        socket.onopen = function() {
          // Do stuff right after opening a channel
        }

        socket.onmessage = function(evt) {
          // Do more cool stuff when a channel message comes in
        }

      </script>
    </head>
    <body>
      ...
    </body>
  </html>
```

These samples don't reflect the complete Channel API, and as already noted
above, may be subject to change. Stay tuned for the API Reference.

## Receiving And Sending Messages ##

To handle incoming messages, you simply create a request handler that accepts
POST requests.

```
  class EchoHandler(webapp.RequestHandler):

    def post(self):
      channel_id = self.request.get('channel_id')
      if channel_id:
        message = cgi.escape(self.request.body)
        channel.send_message(channel_id, message)
      else:
        self.response.set_status(401)

  app = webapp.WSGIApplication([
    ('/echo', EchoHandler),
  ])
```

And this is the appropriate Javascript code to send a new message from our
client application to the server:

```
  sendMessage = function(msg) {
    if (msg) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/echo?channel_id={{ channel_id }}', true);
      xhr.send(msg);
    }
  }
```