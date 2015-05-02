# TyphoonAE Redis Datastore #

The TyphoonAE Redis Datastore aims at providing an alternate, scalable and
productive Datastore backend for TyphoonAE. It's designed for the current GAE
1.3.3 API and supports the bulkloader to restore downloaded data into your
locally running application.

It is implemented as an independent Python package and does not necessarily
depend on TyphoonAE. Thus, you can use it with the Google App Engine Python
SDK.

The current development status is <font color='red'><b>beta</b></font> and so
this package is not included in the current TyphoonAE 0.1.4 release. The layout
of the underlying database may change in future releases.

## Introduction ##

[Redis](http://code.google.com/p/redis) is an advanced in-memory key-value
store. In contrast to memcache, its dataset is not volatile, and values can be
strings, lists, sets, and ordered sets. Furthermore, it is an extremely fast
storage for data structures with a clean interface providing atomic operations to
push/pop/add/remove elements, different operations on sets, and so forth. And
Redis supports neat sorting abilities.

Since Redis delivers master-slave replication with very fast non-blocking first
synchronization and auto reconnection on net split, it is very suitable to be
used as Datastore backend for TyphoonAE.

## Building and Testing ##

Get a local copy of the TyphoonAE Redis repository with

```
  $ hg clone https://redis.typhoonae.googlecode.com/hg/ typhoonae-redis
```

or by downloading a complete buildout archive from
[this location](http://code.google.com/p/typhoonae/downloads/list).

Change into the typhoonae-redis directory and run the buildout process:

```
  $ python bootstrap.py
  $ bin/buildout
```

To run all unit tests start the Redis server and enter the following command:

```
  $ bin/nosetests
```

## Using the TyphoonAE Redis Datstore with the Google App Engine SDK ##

The buildout already downloads and patches the Google App Engine SDK for you.
In order to use the Redis Datastore just start the development appserver with
an additional option:

```
  $ bin/dev_appserver --use_redis parts/google_appengine/demos/guestbook/
```

**Important**: The Redis server must be listening on port 6379.

## Limitations and Further Improvements ##

As far as possible, indexes are implemented by using Redis' backend facilities
(e.g. sorting). In some cases queries with inequality filters can result in
relatively expensive operations for datasets of about 10,000+ entities of one
kind. As usual, this tends to be the harder part when implementing filter
capabilities and needs further improvements.

Redis handles persistence by asynchronously writing changes, which means that
if the Redis server goes down unexpectedly, it is possible to lose data.

## Implementation Notes ##

The following are brief notes on some implementation details of the TyphoonAE
Redis Datastore which may help to understand how it works and what the benefits
as well as the caveats of this approach are.

Entities are stored as encoded protocol buffers. They can be retrieved by
unique keys which contain the ID of the application that created them along
with the _path_. A typical entity key may look like:

> `app!Parent\bkeyname\aChild\b\t0000001001`

where the last of two path elements, separated by a _beep_ (\a), represents our
entity and the first an ancestor. At a later point we will see why it is
important to store this information in our Redis keys. For more on keys and
paths from the API's point of view, see the
[official GAE documentation](http://code.google.com/appengine/docs/python/datastore/keysandentitygroups.html#Entity_Groups_Ancestors_and_Paths).

When updating a property the whole entity protocol buffer is replaced with the
new version.

### Indexes ###

How can we search entities by the value of a distinct property? Well, we could
scan and decode all stored protocol buffers, lookup our property and collect
the results. That would obviously be very inefficient.

It's all about storing the same information in different ways to reduce cost.
Redis is extremely fast at accessing keys. The time complexity of a GET is
O(1). What we need is a set of entity keys for the value of a single property
of one kind:

> Person:name:Steve = SET(KEY\_001, KEY\_234, KEY\_047, KEY\_438)

`SELECT * FROM Person WHERE name = Steve` translated to a Redis command is `SORT Person:name:Steve BY * ALPHA` and returns KEY\_001, KEY\_047, KEY\_234, KEY\_438.
See [this documentation](http://code.google.com/p/redis/wiki/SortCommand) for
further details on the sort command. The BY option and additional indexes
enable us to do ordered queries. Unfortunately, this can result in a huge
number of extra keys in our Redis database. Therefore, a future release may
include the ability to build indexes _offline_.

### Transactions ###

We have to face a number of assumptions before we can implement a _Transaction
Layer_ on top of Redis.
[Transactions](http://code.google.com/appengine/docs/python/datastore/transactions.html) guarantee that a datastore operation or a set of datastore operations
either succeed completely, or fail completely. Inside a transaction only
operations on one entity group are allowed, and a transaction never leaves the
borders of one request.

Redis has a number of commands (SETNX, GETSET) which in combination allow to
implement **custom distributed locks**, ensuring at all times that only 1 client
at a time can execute the protected logic. We use these capabilities to [acquire](http://code.google.com/p/typhoonae/source/browse/src/typhoonae/redis/datastore_redis_stub.py?repo=redis#438) and release locks for entity groups.