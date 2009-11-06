.. TyphoonAE getting started guide.

===============
Getting started
===============

The following chapter will guide you through the initial steps required to
install TyphoonAE into a stand-alone directory tree on your development
machine.

Before you install
==================

First of all, TyphoonAE is tested on Mac OS X Leopard, Snow Leopard
[#SnowLeopard]_, Debian Lenny and Ubuntu 9.0.4/9.10. Since TyphoonAE integrates
an extensive number of open source products its installing process must cover
many dependencies. Hence, the group of platforms which can run TyphoonAE
shrinks slightly.

This is a very short overview of the *larger* parts. Later on, we will have a
closer look at these parts and what keeps them together.

 * `Google App Engine SDK <http://code.google.com/appengine>`_
 * `mongoDB <http://www.mongodb.org/>`_
 * `memcached <http://www.danga.com/memcached/>`_
 * `RabbitMQ <http://www.rabbitmq.com/>`_
 * `ejabberd <http://www.process-one.net/en/ejabberd>`_
 * `FastCGI <http://www.fastcgi.com/>`_
 * `nginx <http://nginx.net/>`_
 * `Supervisor <http://supervisord.org/>`_

.. [#SnowLeopard] To install TyphoonAE on Mac OS X Snow Leopard you must install a pure Python 2.5.4, because the system version raises incompatibility issues.

Python interpreter
------------------

It is possible to run TyphoonAE's Python parts with Python 2.5.x and 2.6.x, but
it is recommended to use a version which is supported by the Google App Engine
SDK [#SDK]_.

We recommend to install TyphoonAE into a `virtualenv
<http://pypi.python.org/pypi/virtualenv>`_ in order to obtain isolation from
any *system* packages you've got installed in your Python version.

.. [#SDK] See http://code.google.com/intl/de/appengine/docs/python/overview.html for further information.

Google App Engine SDK
---------------------

You don't have to install the Google App Engine SDK, because `zc.buildout
<http://pypi.python.org/pypi/zc.buildout>`_ will install it for you.

Other requirements
------------------

Most of the required libraries and programs will be installed by zc.buildout [#buildout]_.

The buildout needs Python and the tools contained in /bin and /usr/bin of a
standard installation of the Linux operating environment. You should ensure
that these directories are on your PATH and following programs can be found:

 * Python 2.5.2+ (3.x is not supported!)
 * gcc and g++
 * make

(Note: On Debian Lenny libncurses5-dev and libssl-dev are required.)

.. [#buildout] See the buildout.cfg file.

Installation
============

Download and unpack the `buildout archive
<http://typhoonae.googlecode.com/files/typhoonae-buildout-0.1.0a3.tar.gz>`_ to
get a starting point::

  $ tar xvzf typhoonae-buildout-0.1.0a3.tar.gz
  $ cd typhoonae-buildout-0.1.0a3

Build the stack::

  $ python bootstrap.py
  $ ./bin/buildout

Configure the helloworld application::

  $ ./bin/apptool parts/helloworld/

Let the cloud fly::

  $ ./bin/supervisord

Access the application using a web browser with the following URL::

  http://localhost:8080/

Run the supervisor console::

  $ ./bin/supervisorctl -c etc/supervisord.conf -u admin -p admin

When all services are up and running, the supervisor console shows something
like this::

  appserver:appserver_00           RUNNING    pid 40169, uptime 0:00:16
  appserver:appserver_01           RUNNING    pid 40168, uptime 0:00:16
  deferred_taskworker              RUNNING    pid 40194, uptime 0:00:09
  ejabberd                         RUNNING    pid 40159, uptime 0:00:16
  intid                            RUNNING    pid 40163, uptime 0:00:16
  memcached                        RUNNING    pid 40160, uptime 0:00:16
  mongod                           RUNNING    pid 40157, uptime 0:00:16
  nginx                            RUNNING    pid 40165, uptime 0:00:16
  rabbitmq                         RUNNING    pid 40158, uptime 0:00:16
  taskworker                       RUNNING    pid 40193, uptime 0:00:09
  xmpp_http_dispatch               RUNNING    pid 40167, uptime 0:00:16
