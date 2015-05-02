# Uploading and Managing a Python App #

The Google App Engine SDK provides the `appcfg.py` command to upload and manage
applications. Since TyphoonAE aims at being compatible with Google App Engine,
it implements its own _experimental appcfg service_.

## Introducing the Appcfg Service ##

TyphoonAE's appcfg service is mainly a WebHook-based, RPC-like interface for
the `appcfg.py` command. It runs as a separate daemon process and listens on
port 9190 for HTTP requests. A typical update process consists of a sequence of
different _phases_: initiation, cloning static and application files, uploading
files and blobs, precompilation, deployment and a check whether the newly
uploaded version is ready to serve. As soon as the new version is ready,
`appcfg.py` uploads index definitions, cron, task queue and DOS entries, if
present. When a phase fails, the fault is reported back to the `appcfg.py`
client and shows up as error output.

At the time of this writing, the appcfg service also provides a very minimalistic overview of the installed applications.

![http://wiki.typhoonae.googlecode.com/hg/appcfg_overview.png](http://wiki.typhoonae.googlecode.com/hg/appcfg_overview.png)

**It is not possible to use the `appcfg.py` command and TyphoonAE's `apptool`
command within the same installation of TyphoonAE.** This is due to the fact
that our appcfg service stores all appversion data in a database to keep track
of used ports and other configuration details. However, the `apptool` is a pure
command line utility and has no access to any database.

## Uploading Applications ##

To upload a Python application, run the `appcfg.py` command with the `update`
action and the name of your application's root directory. Since we use the original `appcfg.py` of the SDK, we can follow this [documentation](http://code.google.com/appengine/docs/python/tools/uploadinganapp.html#Uploading_the_App).

The only difference is that we certainly need to connect to another server and
therefore use the `--server=SERVER` option. Furthermore, we must apply the
`--insecure` option, because our appcfg service does not support SSL by
default.

But it is also possible to use the `appcfg.py` command more securely through
SSL. The following sample configuration shows how to configure NGINX as HTTPS
Proxy in front of the appcfg service.

```
  upstream appcfg_service {
      server 127.0.0.1:9190;
  }

  server {
      listen      9191;
      server_name localhost;
      ssl on;
      ssl_certificate /path/to/certificate.crt;
      ssl_certificate_key /path/to/secret.key;
      access_log  /path/to/appcfg-httpd-access.log;
      error_log   /path/to/appcfg-httpd-error.log;

      location / {
          proxy_pass http://appcfg_service;
          proxy_read_timeout 500;
          proxy_send_timeout 500;
      }
  }
```

## Setting Up Your Domain Name ##

When using the Appcfg Service, TyphoonAE follows the same domain naming scheme
as the productive Google App Engine. After you have successfully uploaded your
application, it should be accessible at _yourapp.yourdomain.net_. This
requires editing the Domain Name entries or `/etc/hosts` if you're testing
locally.

Here is a sample entry for `/etc/hosts` for the guestbook application:

```
  127.0.0.1	guestbook.yourhost
  127.0.0.1	1.latest.guestbook.yourhost
```

TyphoonAE has a global configuration file `etc/typhoonae.cfg` which can be
used to set different parameters like `server_name`, `http_port` or the
preferred Datastore backend to name a few.