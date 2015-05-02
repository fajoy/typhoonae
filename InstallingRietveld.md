# Code Review with Rietveld on TyphoonAE #

[Rietveld](http://code.google.com/appengine/articles/rietveld.html) is a web app for code review written by Guido van Rossum. This How-To guides you through a few steps that will help you to run Rietveld on TyphoonAE.

## Installation ##

Fetch the current source tree by typing:

```
  $ svn checkout http://rietveld.googlecode.com/svn/trunk/ rietveld
```

Download the proper Django version 1.0.2 by clicking this [link](http://www.djangoproject.com/download/1.0.2/tarball).

Unzip and untar the source archive and copy the `django` source directory into your previously created `rietveld` root directory.

Now it's time to configure Rietveld for TyphoonAE. Change to your TyphoonAE root directory and type:

```
  $ bin/apptool /PATH/TO/rietveld
```

Run the services with:

```
  $ bin/supervisord
```

Access Rietveld using a web browser with the following URL:

> http://localhost:8080

Happy reviewing!