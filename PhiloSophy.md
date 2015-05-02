# The Philosophy behind TyphoonAE #

The [Google App Engine SDK](http://code.google.com/appengine/downloads.html)
delivers a development web server that mirrors the production environment near
flawlessly. But you certainly can't use that in a real production environment.
That's where TyphoonAE comes in. It is the missing link to build a
full-featured and productive serving environment to run Google App Engine
(Python) applications.

We started TyphoonAE to understand and apply the techniques and philosophy
behind GAE using high-performance and high-scalable open source software on
commodity hardware. In the beginning it was a proof of concept, and to be
honest, for fun.

One of our goals is to allow a developer to run applications with TyphoonAE as
well as on Google's App Engine without modification. Since it is still beta, we
only provide a development buildout, which installs most of the required
libraries and components into an isolated environment. It is planned to release
images for VMWare and various EC2 appliances in the near future.

The main principles in the design of TyphoonAE are decoupling and statelessness
to provide concurrency, better caching, horizontal scalability and
fault-tolerance. It integrates various open source products where each one is a
superhero and scales independently.

We took advantage of the SDK's API proxy stub architecture as a non-intrusive approach and [dependency injection](http://en.wikipedia.org/wiki/Dependency_injection) from the very first line of code. So, patching the SDK is totally unnecessary. This allows us to follow [changes](ReleaseNotes.md) and updates very quickly.

## Components ##

TyphoonAE uses [NGINX](http://www.nginx.org) or [Apache](http://httpd.apache.org/) as HTTP server which passes incoming requests via [FastCGI](http://en.wikipedia.org/wiki/Fastcgi) to multiple instances of one application. The number of independent appserver processes can easily be adjusted to the workload. This seems to be very much a similar approach Google uses for GAE.

A [Supervisor](http://supervisord.org) manages our appserver processes.

> A supervisor daemon can manage groups of FastCGI processes that all listen on
> the same socket. Shared sockets allow for graceful restarts because the socket
> remains bound by the parent process while any of the child processes are being
> restarted. Finally, shared sockets are more fault tolerant because if a given
> process fails, other processes can continue to serve inbound connections.

> (Taken from the [Supervisor manual](http://supervisord.org/configuration.html#fcgi-programx).)

TyphoonAE supports a number of alternative datastore backends:
[MongoDB](http://www.mongodb.org), [MySQL](http://www.mysql.com)
and Nick Johnsonʼs BDBDatastore. MongoDB is fast and scalable, but
unfortunately, lacks support for transactions.

The Memcache service is backed by the well-known [memcached](http://memcached.org), and for the Task Queue and XMPP messaging we chose [RabbitMQ](http://www.rabbitmq.com) and [ejabberd](http://www.process-one.net/en/ejabberd).

As of this writing, TyphoonAE implements [almost all](http://code.google.com/p/typhoonae/wiki/RoadMap) services of Google App Engine except the High Performace Image Serving API. We added an experimental [Web Socket API and Service](http://code.google.com/p/typhoonae/wiki/WebSockets), which is exclusive to TyphoonAE.