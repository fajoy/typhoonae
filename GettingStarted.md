

# Before You Install #

Read the following instructions carefully if you want to build your own
TyphoonAE environment. In order to get a preconfigured **all-in-one** VMware
image, just go to [this page](VMware.md).

## Python Interpreter ##

It is possible to run TyphoonAE's Python parts with Python 2.5.x and 2.6.x, but
it is recommended to use a version which is supported by the Google App Engine
SDK. See http://code.google.com/intl/de/appengine/docs/python/overview.html for
further information.

We sometimes recommend to install TyphoonAE into a
[virtualenv](http://pypi.python.org/pypi/virtualenv) in order to obtain
isolation from any 'system' packages you've got installed in your Python
version.
If you are using OS X it is not recommended to use the system's Python. Read [this guide](BuildingPythonOnSnowLeopard.md) if you want to build your own suitable Python.

## Google App Engine SDK ##

You don't have to install the Google App Engine SDK, because
[zc.buildout](http://pypi.python.org/pypi/zc.buildout) will install it for you.

## Other requirements ##

Most of the required libraries and programs will be installed by zc.buildout.
See the [buildout.cfg](http://code.google.com/p/typhoonae/source/browse/buildout.cfg?repo=buildout) file.

The buildout needs Python and the tools contained in /bin and /usr/bin of a
standard installation of the Linux operating environment. You should ensure
that these directories are on your PATH and following programs can be found:

  * Python 2.5.2+ (3.x is not supported!)
  * gcc and g++
  * make
  * JAVA
  * locally installed sendmail (if you want to send emails)
  * erl (the Erlang/OTP runtime environment R14B01)
  * MySQL 5.1 (if you want to use it as alternate Datastore backend)
  * xsltproc
  * patch

On Ubuntu or Debian you will need to have the following packages installed:

  * build-essential
  * erlang-nox, erlang-dev and erlang-src
  * gettext
  * libexpat-dev (libexpat1-dev)
  * libmysql++-dev
  * libncurses5-dev
  * libsqlite3-dev
  * libssl-dev
  * python-dev
  * python-setuptools

Keep in mind that the Erlang packages provided by Debian Lenny are somewhat
outdated. As mentioned above, TyphoonAE (ejabberd, RabbitMQ) requires [R14+](http://erlang.org).

The Images API uses the [Python Imaging Library](http://www.pythonware.com/products/pil/) to transform images. TyphoonAE's buildout does not set up PIL for you. You'll need to download the PIL module and install it. For instance, on Debian use apt-get to install the python-imaging package.

# Installation #

We strongly recommend to install TyphoonAE as normal user, because, for
instance, memcached won't run as root.

  * Download and unpack the [buildout archive](http://typhoonae.googlecode.com/files/typhoonae-buildout-0.2.0.tar.gz) to get a starting point:
```
  $ tar xvzf typhoonae-buildout-0.2.0.tar.gz
  $ cd typhoonae-buildout-0.2.0
```

  * Build the stack:
```
  $ python bootstrap.py
  $ ./bin/buildout
```

  * Configure the helloworld application:
```
  $ ./bin/apptool parts/helloworld/
```

  * Run the services:
```
  $ ./bin/supervisord
```

  * Access the application using a web browser with the following URL: http://localhost:8080/

  * Run the supervisor console:
```
  $ ./bin/supervisorctl
```

When all services are up and running, the supervisor console shows something
like this:
```
  appcfg_service                   RUNNING    pid 17923, uptime 0:00:03
  ejabberd                         RUNNING    pid 17894, uptime 0:00:03
  helloworld.1:helloworld.1_00     RUNNING    pid 17931, uptime 0:00:02
  helloworld.1:helloworld.1_01     RUNNING    pid 17928, uptime 0:00:02
  helloworld.1_monitor             RUNNING    pid 17890, uptime 0:00:03
  helloworld_deferred_taskworker   RUNNING    pid 17908, uptime 0:00:03
  helloworld_taskworker            RUNNING    pid 17899, uptime 0:00:03
  helloworld_xmpp_http_dispatch    RUNNING    pid 17937, uptime 0:00:02
  memcached                        RUNNING    pid 17897, uptime 0:00:03
  mongod                           RUNNING    pid 17891, uptime 0:00:03
  nginx                            RUNNING    pid 17913, uptime 0:00:03
  rabbitmq                         RUNNING    pid 17892, uptime 0:00:03
  websocket                        RUNNING    pid 17934, uptime 0:00:02
```

In order to shut down all services just enter:

```
  $ ./bin/supervisorctl shutdown
```

## Troubleshooting ##

Sometimes zc.buildout fails due to a refused connection when a download location is temporarily down.

In such a case the output looks like this:

```
Installing libmemcached.
libmemcached: Downloading http://download.tangent.org/libmemcached-0.31.tar.gz
While:
  Installing libmemcached.

An internal error occured due to a bug in either zc.buildout or in a
recipe being used:
Traceback (most recent call last):
 ...
IOError: [Errno socket error] [Errno 111] Connection refused
```

To resolve this issue simply change the download location of libmemcached-0.31.tar.gz in the buildout.cfg file to a mirror site like this http://ftp.aarnet.edu.au/debian/pool/main/libm/libmemcached/libmemcached_0.31.orig.tar.gz and rerun the buildout.