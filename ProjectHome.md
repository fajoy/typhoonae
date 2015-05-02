The TyphoonAE project aims at providing a full-featured and productive serving environment to run [Google App Engine](http://code.google.com/appengine) (Python) applications. It delivers the parts for building your own scalable App Engine while staying compatible with Google's API.

_Important note:_ The current development status is <font color='red'><b>beta</b></font>. At this point it is not guaranteed that any GAE application will run completely error-free on TyphoonAE. So, stay patient please!

See the [Release Notes](ReleaseNotes.md) for information on the current release and the [Product Roadmap](RoadMap.md) for further details on planned features.

## Demo <font color='red'><b>(currently unavailable)</b></font> ##

We have installed three demos on a single TyphoonAE instance running in a virtual XEN environment:

  * [Bloggart](http://blog.typhoonae.org)
  * [Web Socket Hybrid Demo](http://hybrid.typhoonae.org) (using [Web Socket API](WebSockets.md))
  * [Trivia Quiz I/O Demo](http://trivia-quiz.typhoonae.org:8080/) (using [Channel API](ChannelAPI.md))

Any feedback is appreciated! Feel free to join our [discussion group](http://groups.google.com/group/typhoonae) for TyphoonAE.

## Architecture Overview ##
Click the image below for a PDF version.

[![](http://typhoonae.googlecode.com/hg/doc/source/architecture.png)](http://typhoonae.googlecode.com/hg/doc/source/architecture.pdf)

## The Stack ##

  * Google App Engine SDK http://code.google.com/appengine

### Supported Datastore Backends ###

  * MongoDB http://www.mongodb.org
  * MySQL http://www.mysql.com
  * Berkeley DB JE - http://arachnid.github.com/bdbdatastore

It should be fairly achievable to implement an appropriate API proxy stub for [HBase](http://hbase.apache.org/) support. Don't hesitate to ask the TAE project members for details.

### HTTP Server via FastCGI ###

  * NGINX http://nginx.net/
  * Apache2 http://httpd.apache.org/
  * FastCGI http://www.fastcgi.com

### Memcache ###

  * memcached http://memcached.org

### Task Queue / Messaging ###

  * RabbitMQ - http://www.rabbitmq.com
  * ejabberd - http://www.process-one.net/en/ejabberd

### Web Sockets (TyphoonAE only) ###

  * Tornado - http://www.tornadoweb.org

### Supervisor ###

  * Supervisor http://supervisord.org

All these components will be automatically installed by [zc.buildout](http://www.buildout.org) into an isolated directory tree on your development machine. If you want to remove the TyphoonAE development environment you just have to delete this single directory.

For some good reasons why using zc.buildout you may want to read [this post](http://renesd.blogspot.com/2008/05/buildout-tutorial-buildout-howto.html) or watch [this talk](http://us.pycon.org/2009/conference/schedule/event/48/).

The configuration above is tested on OS X, Debian and Ubuntu Linux. Several parts can be replaced by editing the [buildout.cfg](http://code.google.com/p/typhoonae/source/browse/buildout.cfg?repo=buildout) file. _But you should really know what you're doing._

## PyPI ##

http://pypi.python.org/pypi/typhoonae

## Resources ##

  * David Rousseau shows on [Google App Engine as a Framework](http://sites.google.com/site/gaeasaframework/) how to install TyphoonAE on Ubuntu.

## Support TyphoonAE ##

<a href='https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KNKKR9UCQKPRY'><img src='https://www.paypal.com/en_US/i/btn/btn_donate_LG.gif' /></a>

[![](http://wiki.typhoonae.googlecode.com/hg/mongo_berlin.png)](http://www.10gen.com/conferences/mongoberlin2010)