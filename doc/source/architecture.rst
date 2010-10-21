.. TyphoonAE architecture.

Architecture Overview
=====================

Google App Engine delivers an easy-to-use and well-defined programming
interface which allows developers to build highly scalable web applications
whereby enabling them to rather concentrate on functionality than reliability
and robustness of the underlaying services.

Let's have a look at our stack. At this point, it is negligible whether the
software components are distributed in a cluster or installed on a single
machine.

.. figure:: architecture.*
   :alt: TyphoonAE's archtecture

   This is an architecture overview of TyphoonAE.

The diagram above shows how the Google App Engine API and the underlying
services are coupled together while TyphoonAE provides the glue code and a set
of workers and dispatchers for asynchronous data transfer. The grey rounded
boxes in the center are our Python runtime processes, each representing one
parallel process of an application.

You can easily guess that the inter-process communication takes place via
TCP/IP socket connections. Keep that in mind when discussing optimization
strategies, because it's all about I/O throughput. TyphoonAE uses various
standard protocols like HTTP, XMPP, Web Sockets, Protocol Buffers or AMQP to
name a few, whereas the latter two are solely for internal communication.

In short words, the described architecture is designed for horizontal
sclability and fault-tolerance while most parts work in a strictly stateless
paradigm, because this creates the simplest sort of reliable system.
