

# Developing Google App Engine Applications with Buildout #

From the first line of code the TyphoonAE project made heavy usage of the great
[Buildout project](http://www.buildout.org/) by Jim Fulton. This article shows
you how to leverage Buildout functionalities in your App Engine project.

## The Blessings of Buildout ##

[Buildout](http://www.buildout.org/) provides a very convenient way for
developing applications because of its core feature to create and reproduce
complex software systems by configuration. A software project is typically a
collection of source code, depending libraries, testing facilities,
documentation and more. However, it can take some time to set up the
appropriate environment, especially when you want to enable co-workers to
easily participate and contribute.

There are many bad habits when developing software, for instance, it's not
uncommon to also commit external libraries to the same source repository. This
can really mess up a project and ties it to a fixed set of dependencies.
Replacing or updating libraries can become a nightmare. There are many tasks
like that a developer really doesn't want to care about. And that's where
Buildout comes in.

## Getting Started ##

It is not necessary but recommended to take a look at the comprehensive
[Buildout documentation](http://www.buildout.org/docs/) for further reading.

Let's begin with a small project which uses the external libraries
[bobo](http://bobo.digicool.com), a light-weight framework for creating WSGI
applications, and [Chameleon](http://chameleon.repoze.org) as template engine.
Our _development buildout_ contains the source code of our project and the
buildout configuration. See the
[complete sample](http://github.com/rodaebel/boboongae) to get an overview of
the directory structure. Since we use
[distribute](http://pypi.python.org/pypi/distribute) on top of Python's
distutils, we add a `setup.py` file. It contains all dependencies and
information to help people find or learn about our project. The following is a
minimal working example:

```
  from setuptools import setup, find_packages
  import os

  setup(
    name='boboongae',
    version='1.0',
    author="Peter Parker",
    author_email="peter@web.org",
    description="Bobo on Google App Engine.",
    packages=find_packages(),
    package_dir={'': os.sep.join(['src', 'boboongae'])},
    include_package_data=True,
    install_requires=[
      'bobo',
      'chameleon',
      'distribute',
    ],
  )
```

See the [distutils](http://docs.python.org/release/2.5.4/lib/module-distutils.html) and [setuptools](http://peak.telecommunity.com/DevCenter/setuptools)
documentation for further details on how to write `setup.py` scripts.

The syntax of a `buildout.cfg` file follows the typical configuration syntax
with sections, keys and values. The example below has only two sections, a more
general _buildout specific_ one and another section which describes a single
_part_. All parts must be listed in the `[buildout]` section separated by
blanks in the exact order they ought to be processed.

```
  [buildout]
  develop = .
  parts = boboongae

  [boboongae]
  recipe = rod.recipe.appengine
  url = http://googleappengine.googlecode.com/files/google_appengine_1.5.1.zip
  server-script = dev_appserver
  packages =
      bobo
      chameleon
      ordereddict
  exclude = tests
```

The following sections are describing the parts in detail where every part
needs a _recipe_ to know how to be built.

_Recipes_ are another clever feature of Buildout. They can be seen as plugins
to add new functionalities to a project's buildout. They are automatically
installed as Python eggs while processing a part. You can find hundreds of
Recipes on the [Python Package Index](http://pypi.python.org/pypi) for nearly
any purpose around creating and deploying software systems from small to
large-scale. For our boboongae project we use
[rod.recipe.appengine](http://pypi.python.org/pypi/rod.recipe.appengine). It
handles a number of important tasks for us:

  1. Fetches the Google App Engine SDK.
  1. Copies application code and depending libraries into its corresponding part directory ready to deploy.
  1. Installs the development appserver and appcfg script in PROJECT/bin.

The recipe takes a number of options. A complete list can be found on the
recipe's [PyPI page](http://pypi.python.org/pypi/rod.recipe.appengine). In our
sample above the `packages` option defines the packages bobo and chameleon to
be installed into `parts/boboongae/`. The recipe provides all depending
libraries as one zipped file `packages.zip`. So, you no longer have to worry
about whether all external stuff is correctly installed within your project
when deploying.

In order to make those external libraries accessible, you need to add the
following lines to the Python file which imports one or more packages from the
zip file.

```
  import sys
  sys.path.insert(0, 'packages.zip')
```

This mechanism comes from the old days where the maximum file limit on Google
App Engine was 1000 files. For compatibility reasons it's still enabled by
default, but you can easily disable it by setting the `zip-packages` flag to
False.

With `exclude` we define a list of basenames to be excluded when copying the
application files, in our case the whole "tests" directory, because it is not
needed for deployment.

_We believe in tests!_ Anyway, how to get the appropriate testing facilities
into our project? We choose
[nose](http://somethingaboutorange.com/mrl/projects/nose), an extension of
Python's unittest module, for testing our application. As you may imagine, we
just have to add another part `[nosetests]` to our buildout configuration.
**Don't forget to add nosetests to the parts at the top of the configuration
file.**

```
  [buildout]
  develop = .
  parts = boboongae nosetests
  
  ...

  [nosetests]
  recipe = zc.recipe.egg
  eggs =
      NoseGAE
      WebTest
      boboongae
      nose
  extra-paths =
      ${buildout:directory}/etc
      ${buildout:directory}/parts/google_appengine
      ${buildout:directory}/parts/google_appengine/lib/antlr3
      ${buildout:directory}/parts/google_appengine/lib/django_0_96
      ${buildout:directory}/parts/google_appengine/lib/fancy_urllib
      ${buildout:directory}/parts/google_appengine/lib/ipaddr
      ${buildout:directory}/parts/google_appengine/lib/webob
      ${buildout:directory}/parts/google_appengine/lib/yaml/lib
      ${buildout:directory}/parts/google_appengine/lib/simplejson
      ${buildout:directory}/parts/google_appengine/lib/graphy
  interpreter = python
```

Buildout now takes care of the rest and fetches all required packages and
installs them for you.
See this [documentation](http://somethingaboutorange.com/mrl/projects/nose/0.11.3/) on how to write tests.

## A Sample Project ##

This [sample project](http://github.com/rodaebel/boboongae) shows how to apply
the things we've learned above to a small Google App Engine Python project.
The build instructions in
[README](http://github.com/rodaebel/boboongae/blob/master/README.rst) follow the
typical pattern for buildouts.

Bootstrapping and running buildout:

```
  $ python bootstrap.py --distribute
  $ ./bin/buildout
```

Running the application:

```
  $ ./bin/dev_appserver parts/<APP>
```

Accessing the application using a web browser:

```
  http://localhost:8080
```

Uploading to the appspot:

```
   ./bin/appcfg update parts/<APP>
```

In order to change the functionality of your project or add new files, make all
changes in the source tree of the project and **never touch the parts**. They're
volatile and can be deleted or replaced each time you run Buildout again. On
Linux or OS X rod.recipe.appengine symlinks the source files into the
corresponding app directory under parts. Unfortunately, this does not work on
Windows. As a workaround execute buildout anytime you want to see your changes
take effect. This layout may change in a newer version of the recipe.

## Google App Engine, Buildout and virtualenv ##

Especially on Max OS X using virtualenv with Google App Engine can cause
enormous headache. This is due to the fact that the development appserver
messes around with sys.path which leads to annoying import errors within your
virtualenv.

This [patch](https://github.com/rodaebel/boboongae/blob/master/src/virtualenv_dev_appserver.patch) solves that issue. Fortunately, the [rod.recipe appengine package](http://pypi.python.org/pypi/rod.recipe.appengine) comes with a patch option. See this [buildout.cfg](http://github.com/rodaebel/boboongae/blob/master/buildout.cfg) file for further details and try the following sample:

```
  $ virtualenv gaebobo
  $ cd gaebobo
```

After changing into the newly created gaebobo directory, continue with:

```
  $ git clone https://github.com/rodaebel/boboongae.git
  $ cd boboongae
  $ ../bin/python bootstrap.py
  $ bin/buildout
```

And you're done. Run the development appserver by typing:

```
  $ bin/dev_appserver parts/boboongae
```


## App Engine Projects already using Buildout ##

Additionally, here is a certainly incomplete list of App Engine Projects which
are already using Buildout for development. Feel free to add more in your
comments.

  * [Tweet-Engine](http://www.tweetengine.net)
  * [Tipfy](http://code.google.com/p/tipfy)
  * [Lovely-GAE](http://code.google.com/p/lovely-gae/)
  * [repoze.bfg on GAE](http://code.google.com/p/bfg-gae-buildout)

  * [Good-Py](http://good-py.appspot.com) doesn't really use zc.buildout but is made for it by Martin Aspeli. See his [blog post](http://www.martinaspeli.net/articles/hello-good-py-a-known-good-versions-manager) for a deeper insight.