Guido van Rossum recently released the [Appstats](https://sites.google.com/site/appengineappstats/) beta, an RPC Instrumentation for Google App Engine. The following describes the few preparations you have to make to get this awesome tool running on TyphoonAE.

As described in the [Appstats documentation](https://sites.google.com/site/appengineappstats/) just unzip the distribution into your application (toplevel directory) and follow the other steps of the documentation.

Make sure to configure your application with:

```
  $ ./bin/apptool --server_software=Dev-TyphoonAE/0.1.0 /path/to/your/app
```

["See the light!"](http://www.youtube.com/watch?v=d95YFdubGrU)

### Update ###

Since Appstats is included in the Google App Engine SDK, it is no longer
necessary to download and install Appstats.