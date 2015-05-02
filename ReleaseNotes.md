You can download the latest version of TyphoonAE [here](http://code.google.com/p/typhoonae/downloads/list).

We also provide a preconfigured VMware image. See [this page](VMware.md) for
further information.

## Version 0.2.0 (2010-12-12) ##

  * Supports Google App Engine SDK 1.4.0.
  * Implements Channel API backed by the NGINX push module.
    * http://code.google.com/p/typhoonae/issues/detail?id=57
  * Adds experimental support for the appcfg.py update command.
    * http://code.google.com/p/typhoonae/issues/detail?id=49
  * Incoming Mail Service through a configurable IMAP listener and HTTP dispatcher.
    * http://code.google.com/p/typhoonae/issues/detail?id=73
  * Adds process monitor for automatically restarting appserver processes consuming more than a given amount of memory that is held in RAM (RSS).
  * Using Celery as alternative Task Queue backend.
  * Appserver imports and initializes API proxy stubs for various service backends only when needed.
  * Updated Web Socket Service to provide the latest Web Socket protocol.
    * http://code.google.com/p/typhoonae/issues/detail?id=52
  * Removed obsolete service for sequential integer ids and so eliminated a typical 'Single Point Of Failure'.
  * Fixes an issue where spaces in application paths caused failures on startup.
    * http://code.google.com/p/typhoonae/issues/detail?id=62
  * Fixes issues where develop mode didn't work.
    * http://code.google.com/p/typhoonae/issues/detail?id=63
    * http://code.google.com/p/typhoonae/issues/detail?id=64
  * Fixes an issue where the Capability API did not work with remote Datastore configuration.
    * http://code.google.com/p/typhoonae/issues/detail?id=65
  * Fixes a critical issue where an application hangs if the connection to the MySQL database server is temporarily lost.
    * http://code.google.com/p/typhoonae/issues/detail?id=67
  * Fixes a compatibility issue with Memcache.
    * http://code.google.com/p/typhoonae/issues/detail?id=70
  * Fixes compatibility issues with adding new tasks.
    * http://code.google.com/p/typhoonae/issues/detail?id=71
    * http://code.google.com/p/typhoonae/issues/detail?id=75

## Version 0.1.5 (2010-07-09) ##

  * Supports Google App Engine SDK 1.3.5.
  * Introducing MySQL backed Datastore.
  * Added support for configuring and running multiple applications.
  * The apptool takes new options for configuring SSL support.
  * The apptool takes a new option to specify a root directory for HTML error pages.
  * Fixes an issue where Blobstore creates invalid upload URLs.
    * http://code.google.com/p/typhoonae/issues/detail?id=26
  * Fixes an issue where the appserver crashes due to absolute script paths in the app.yaml file.
    * http://code.google.com/p/typhoonae/issues/detail?id=48
  * Fixes an issue where some users experiencing strange behaviours with module imports.
    * http://code.google.com/p/typhoonae/issues/detail?id=56
  * Fixes an issue where request handlers get executed, even though they require login.
    * http://code.google.com/p/typhoonae/issues/detail?id=59
  * Fixes an issue where script handlers referring to a package path don't work.
    * http://code.google.com/p/typhoonae/issues/detail?id=60

## Version 0.1.4 (2010-04-26) ##

  * Supports Google App Engine SDK 1.3.3.
  * Implements new features of Google App Engine SDK 1.3.2.
    * Blobstore API to read the contents of uploaded Blobs.
    * Task Queue API for adding multiple tasks in a single call.
  * Fixes an issue where it was nearly impossible to use a custom login/logout handler.
    * http://code.google.com/p/typhoonae/issues/detail?id=13
  * Fixes an issue where bulkloader.py didn't fetch any results from our MongoDB backed datastore.
    * http://code.google.com/p/typhoonae/issues/detail?id=38
  * Fixes a compatibility issue with crontab on Fedora.
    * http://code.google.com/p/typhoonae/issues/detail?id=42
  * Updated memcached, MongoDB, ejabberd and various Python packages.
  * Adds experimental JSON/RPC handler.

## Version 0.1.3 (2010-03-12) ##

  * Supports Google App Engine SDK 1.3.1.
  * Adds support for Datastore Query Cursors.
  * The apptool takes a new option to configure an application for development.
  * Fixes an issue where memcache batch support wasn't implemented.
    * http://code.google.com/p/typhoonae/issues/detail?id=34

## Version 0.1.2 (2010-02-08) ##

  * Adds experimental Web Socket service API.
  * Adds support for remote datastore.
  * Adds command line options to configure the HTTP port and SMTP host.
  * Fixes two issues where some static\_dir and static\_files handler options where misinterpreted.
    * http://code.google.com/p/typhoonae/issues/detail?id=23
    * http://code.google.com/p/typhoonae/issues/detail?id=24
  * Fixes an issue where an incomplete cron.yaml file caused apptool to fail.
    * http://code.google.com/p/typhoonae/issues/detail?id=25
  * Fixes an issue where BlobKey types can't be stored in the mongoDB datastore.
    * http://code.google.com/p/typhoonae/issues/detail?id=28
  * Fixes an issue where the Blobstore API wasn't fully implemented.
    * http://code.google.com/p/typhoonae/issues/detail?id=29

## Version 0.1.1 (2009-12-28) ##

  * Supports Google App Engine SDK 1.3.0.
  * Adds support for the new Blobstore API.
  * Adds optional HTTP basic authentication.
  * Fixes an issue where the XMPP/HTTP dispatcher didn't handle unicode.
    * http://code.google.com/p/typhoonae/issues/detail?id=15
  * Fixes an issue where memcache.get\_multi(keys) raises a KeyError.
    * http://code.google.com/p/typhoonae/issues/detail?id=16
  * Fixes an issue where the SCRIPT\_NAME variable is missing in the CGI environment.
    * http://code.google.com/p/typhoonae/issues/detail?id=18
  * Fixes an issue where the login parameter of URL handler definitions in the app.yaml configuration file got ignored.
    * http://code.google.com/p/typhoonae/issues/detail?id=20
  * Adds several new command line options to the apptool and fcgiserver.

## Version 0.1.0b2 (2009-12-04) ##

  * Using Google App Engine SDK 1.2.8.
  * Added BDBDatastore support.
  * Fixes an issue where the CURRENT\_VERSION\_ID variable is missing in the CGI environment.
    * http://code.google.com/p/typhoonae/issues/detail?id=8
  * Deferred API works now.
    * http://code.google.com/p/typhoonae/issues/detail?id=9
  * Fixes an issue where memcache.put() raises a UnicodeDecodeError when trying to store an encoded protocol buffer.
    * http://code.google.com/p/typhoonae/issues/detail?id=10
  * Added support for datastore queries with the keys\_only keyword argument.
    * http://code.google.com/p/typhoonae/issues/detail?id=11
  * Fixes an issue where writing unicode strings to the FastCGI output stream raises a TypeError.
    * http://code.google.com/p/typhoonae/issues/detail?id=12

## Version 0.1.0b1 (2009-11-20) ##

  * Added support for scheduled tasks.
    * http://code.google.com/p/typhoonae/issues/detail?id=5
  * Fixes an issue where the params keyword argument gets ignored when adding a task.
    * http://code.google.com/p/typhoonae/issues/detail?id=7
  * Minor refactoring.

## Version 0.1.0a3 (2009-10-22) ##

  * Added support for sending XMPP invitations.
  * Fixes an issue where static file pattern handlers got ignored.
    * http://code.google.com/p/typhoonae/issues/detail?id=3
  * Fixed unit tests.

## Version 0.1.0a2 (2009-10-17) ##

  * Added XMPP support.
  * Fixed an issue where an incorrect module path within a handler definition can cause the fcgiserver to crash on startup.
    * http://code.google.com/p/typhoonae/issues/detail?id=1
  * Refactored integer ID client API out of datastore stub.

## Version 0.1.0a1 (2009-10-05) ##

  * First alpha release.