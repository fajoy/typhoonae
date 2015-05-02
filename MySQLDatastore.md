# MySQL Datastore Backend #

TyphoonAE comes with support for MySQL 5.1 as alternate Datastore backend.

## Introduction ##

[MySQL](http://www.mysql.com) is a mature and widely-used relational database
management system (RDBMS). It is used in many high-profile, large-scale World
Wide Web products including [Wikipedia](http://www.wikipedia.org) and
[Facebook](http://www.facebook.com).

TyphoonAE's MySQL connector is designed to store Entities in a MySQL database
in a similar fashion to the production datastore. Substantial portions of this
design and code are taken from Nick Johnson's SQLite Datastore stub which is
part of the official Google App Engine SDK. Therefore, we warmly recommend this
[article](http://blog.notdot.net/2010/03/Announcing-the-SQLite-datastore-stub-for-the-Python-App-Engine-SDK) for further reading.

## Configuration ##

In order to use the MySQL Datastore configure your application by typing:

```
  $ bin/apptool --datastore=mysql parts/google_appengine/demos/guestbook/
```

**Important**: Make sure you have a MySQL server running on the same machine.

Then run the supervisor daemon by typing:

> $ bin/supervisord