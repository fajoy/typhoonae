# Introduction #

We recommend very much _not_ to use the system Python when installing TyphoonAE
on an OS X machine but to install an own Python build.  The problem is that the
system Python has bindings to a Mac OS X SDK that is not available by default.
This pops up when building Python extensions.

Since it is a little bit tricky to build a Python on Snow Leopard here is how
to do it:

# Building and using an own Python #

Compile Python 2.6.4 with the following configure options:

```
$ ./configure MACOSX_DEPLOYMENT_TARGET=10.6 --prefix=/SOME/PREFIX/PATH/ --disable-tk
```

TyphoonAE works with Python 2.6.4 (in-officially) ;)

After installing Python, change into the typhoonae root directory and enter following commands:

```
$ /PATH/TO/YOUR/PYTHON/bin/python2.6 bootstrap.py
$ ./bin/buildout
```

You can now start the services and continue as described in [GettingStarted](GettingStarted.md)