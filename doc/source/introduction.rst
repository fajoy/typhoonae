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
app engine with high-performance, distributed services powered by one hundred
percent open source.

The basic idea of this document is to give a brief explanation on the
principles and design descisions behind TyphoonAE. You can learn how to install
your own app engine runnig your GAE applications.

If you are interested in developing TyphoonAE itself, this book contains a
refrence guide. You'll get an architecture overview and an introduction to the
software under the hood of TyphoonAE.

The philosophy behind TyphoonAE
===============================

The Google App Engine SDK delivers a development web server that mirrors the
production environment near flawlessly. But you obviously can't use that in a
real production environment. That's where TyphoonAE comes in. It is the missing
link to build a full-featured and productive serving environment to run Google
App Engine (Python) applications. The main principles in the design of
TyphoonAE are decoupling and statelessness to provide concurrency, better
caching, horizontal scalability and fault-tolerance. It integrates various open
source products where each one is a superhero and scales independently.

Furthermore, TyphoonAE aims at staying as modular as possible. It goes without
patching the SDK and utilizes the same dependency injection `stub` pattern. So,
it has an astonishing small code base with good test coverage.
