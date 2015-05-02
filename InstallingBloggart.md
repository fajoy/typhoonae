# Running Bloggart on TyphoonAE #

[Bloggart](http://github.com/Arachnid/bloggart) is a useful and versatile blogging system for Google App Engine developed by Nick Johnson as a demonstration app for a [series of blog posts](http://blog.notdot.net/2009/10/Writing-a-blog-system-on-App-Engine).

The following steps describe how to install Bloggart on TyphoonAE. If you haven't already installed TyphoonAE follow the steps described in the [Getting Started Guide](http://code.google.com/p/typhoonae/wiki/GettingStarted).

## Installation ##

Use [git](http://git-scm.com) to fetch the current source tree by typing:

```
  $ git clone http://github.com/Arachnid/bloggart.git
```

Change into the newly created bloggart directory and get the sources of
aetycoon by typing:

```
  $ git clone http://github.com/Arachnid/aetycoon.git
```

Bloggart provides a `config.py` file to customize the name of your blog, add
you as the author, set up host and theme and so on. **Hint:** If you don't want
to ping Google Sitemap when your sitemep is generated, noramally after
publishing your first post, change `google_sitemap_ping` to `False`.

If you want to use TyphoonAE's [HTTP basic authentication](HTTPBasicAuth.md), don't
forget to create a htpasswd file in the root directory of Bloggart.

```
  $ htpasswd -c htpasswd bloggart
```

Now it's time to configure Bloggart for TyphoonAE. Change to your TyphoonAE
root directory and type:

```
  $ bin/apptool --http_base_auth /absolute/path/to/bloggart
```

Run all services with:

```
  $ bin/supervisord
```

That's all. Now access your blog using a web browser with the following URL:

> http://localhost:8080

To shutdown all services enter following command:

```
  $ bin/supervisorctl -c etc/supervisord.conf -u admin -p admin shutdown
```

Happy blogging!