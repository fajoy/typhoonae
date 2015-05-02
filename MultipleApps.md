# Running Multiple Applications on TyphoonAE #

[Google App Engine](http://code.google.com/appengine) delivers an easy-to-use
and well-defined programming interface which allows developers to build highly
scalable web applications whereby enabling them to rather concentrate on
functionality than reliability and robustness of the underlaying services.

Since TyphoonAE more and more becomes a real solution as an alternate serving
environment for GAE applications, we felt the need to provide a way to
configure the stack to run multiple apps at once. The following brief guide
will help you to understand how we run multiple applications and how to use the
`apptool` to configure them.

## Architecture Overview ##

Let's first have a look at our stack. At this point, it is negligible whether
the software components are distributed in a cluster or installed on a single
machine.

[![](http://typhoonae.googlecode.com/hg/doc/source/architecture.png)](http://typhoonae.googlecode.com/hg/doc/source/architecture.pdf)

(Click image for a PDF version.)

The diagram above shows how the <b><font color='#85d5fd'>Google App Engine<br>
API</font></b> and the underlying <b><font color='#90cb82'>services</font></b>
are coupled together while <b><font color='orange'>TyphoonAE</font></b>
provides the glue code and a set of workers and dispatchers for asynchronous
data transfer. The grey rounded boxes in the center are our Python runtime
processes, each representing one parallel process of an application.

You can easily guess that the inter-process communication takes place via
TCP/IP socket connections. Keep that in mind when discussing optimization
strategies, because it's all about I/O throughput. TyphoonAE uses various
standard protocols like HTTP, XMPP, Web Sockets, Protocol Buffers or AMQP to
name a few, whereas the latter two are solely for internal communication.

In short words, the described architecture is designed for horizontal
sclability and fault-tolerance while most parts work in a strictly stateless
paradigm, because this creates the simplest sort of reliable system.

## Introducing Multiple Application Support ##

TyphoonAE is developed from the ground up to run multiple applications, but we
haven't provided the tools in the past to configure them. This is due to the
fact that we focused on building the stack first.

The latest TyphoonAE release (0.1.5) introduces a first approach for installing
more than one application. The following steps show how to set up the
`helloworld` application and [Bloggart](http://github.com/Arachnid/bloggart), a
useful and versatile blogging system for App Engine.

[This Wiki page](InstallingBloggart.md) shows how to get Bloggart.

If you haven't already done so, it is highly recommended to read the
[Getting Started](GettingStarted.md) documentation and build the stack first.

Configure the TyphoonAE's `helloworld` application:

```
  $ ./bin/apptool --multiple --server_name=example.com parts/helloworld/
```

We need a few more command line options to configure Bloggart, because the
default parameters are already in use by the helloworld app now:

```
  $ ./bin/apptool --multiple --server_name=example.com --internal_address=localhost:8771
  --fcgi_host=localhost --fcgi_port=8082 /path/to/bloggart
```

Add following entries to your `/etc/hosts` file:

```
  127.0.0.1 helloworld.example.com
  127.0.0.1 bloggart-demo.example.com
```

Start all services by typing:

```
  $ ./bin/supervisord
```

Access the applications using a web browser with the following URLs:
http://helloworld.example.com:8080 and http://bloggart-demo.example.com:8080