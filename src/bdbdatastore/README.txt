============
BDBDatastore
============

An alternate datastore backend for App Engine, implemented using BDB JE.

BDBDatastore is an alternate datastore backend for App Engine apps. It's far
more robust and scalable than the one the development server uses, but not as
big and hard to install as HBase and HyperTable based backends. BDBDatastore is
intended primarially for use by people who want to host their own App Engine
apps, and don't expect datastore load for a single app to exceed what a single
server can handle. In the event your app gets too big for BDBDatastore, the
migration path to an alternate backend is smooth.

License
=======

Apache License 2.0

Authors
=======

Nick Johnson 

Contact
=======

Nick Johnson (arachnid@notdot.net) 
