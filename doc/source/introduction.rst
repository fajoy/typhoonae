.. TyphoonAE introduction.

============
Introduction
============

Who should read this manual?
============================

If you've already written a `Google App Engine
<http://code.google.com/appengine>`_ application and deployed it successfully
to the appspot you're probably asking how cool it'd be to get all that stuff
running on your own hardware `at home`. Or you plan to build your own scalable
App Engine with high-performance, distributed services powered by one hundred
percent open source.

The basic idea of this book is to give a brief explanation on the principles
and design decisions behind TyphoonAE. You can learn how to install your own
App Engine running your GAE applications.

If you are interested in developing TyphoonAE itself, this book contains a
reference guide. You'll get an architecture overview and an introduction to the
software under the hood of TyphoonAE.

The Philosophy behind TyphoonAE
===============================

The Google App Engine SDK delivers a development web server that mirrors the
production environment near flawlessly. But you obviously can't use that in a
real production environment. That's where TyphoonAE comes in. It is the missing
link to build a full-featured and productive serving environment to run Google
App Engine (Python) applications. The main principles in the design of
TyphoonAE are decoupling and statelessness to provide concurrency, better
caching, horizontal scalability and fault-tolerance. It integrates various open
source products where each one scales independently and runs on commodity
hardware.

Furthermore, TyphoonAE aims at staying as modular as possible. We took
advantage of the SDK's API proxy stub architecture as a non-intrusive approach
from the very first line of code. So, patching the SDK is totally unnecessary.
So, it has an astonishing small code base with good test coverage. This allows
us to follow changes and updates of the original Google App Engine very
quickly.
