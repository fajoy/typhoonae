# Product Roadmap #

The following provides a quick overview of the features that are actively under development or already implemented.

## Google App Engine Services ##

TyphoonAE 0.2.0 currently uses the Google App Engine SDK 1.4.0. Here is a quick overview which services are supported:

| **Service** | **Supported** | **Backend(s)** |
|:------------|:--------------|:---------------|
| Datastore | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | MongoDB, MySQL, BDBDatastore |
| Memcache | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | memcached |
| Task Queue | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | RabbitMQ |
| Blobstore | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | NGINX Upload Module/Filesystem |
| Scheduled Tasks | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | cron |
| XMPP | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | ejabberd |
| Channel API | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | NGINX Push Module |
| URL Fetch | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | SDK |
| Mail | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | sendmail |
| Incoming Email | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | IMAP |
| Images | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) | PIL |
| High Performance Image Serving |  |  |
| Remote API | ![http://wiki.typhoonae.googlecode.com/hg/check.jpg](http://wiki.typhoonae.googlecode.com/hg/check.jpg) |  |

### Non-GAE Services (experimental) ###

| **Service** | **Status** | **Documentation** |
|:------------|:-----------|:------------------|
| Web Sockets | working | [wiki page](WebSockets.md) |

## Known Incompatibilities ##

  * Datastore MongoDB backend does not support transactions, Expandos and kindless ancestor queries.
  * The Blobstore backend uses local disk.
  * The default value of the CGI environment variable SERVER\_SOFTWARE is TyphoonAE/X.Y.Z. Many people derive a DEBUG flag depending of the value of SERVER\_SOFTWARE. For this purpose, `apptool` provides a `--server_software` option to specify a custom value.
  * Bucket size in the Task Queue is not supported.
  * Rate limit in the Task Queue is only supported in the celery backend.
  * The backoff behaviour of the Task Queue is not the same as the GAE Task Queue.
  * Scheduled Tasks (cron) in Google App Engine never overlap (a new task is only executed at the right time if the previous execution has finished), but they can overlap in TyphoonAE.

## Planned Features ##

  * Alternative datastore backends (Cassandra, HBase, Hypertable)
  * Easy distribution of the TyphoonAE backend services over multiple machines
  * Admin console