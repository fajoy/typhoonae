# TyphoonAE Blobstore #

Google introduced the [Blobstore](http://code.google.com/appengine/docs/python/blobstore/overview.html) service by releasing App Engine 1.3.0. It is currently in an experimental state and allows apps to serve data objects up to 50 MB. The following document describes how TyphoonAE makes the Blobstore API accessible to developers.

## Under the hood ##

TyphoonAE takes advantage of the well-proved NGINX upload [module](http://www.grid.net.ru/nginx/upload.en.html). It stores all files being uploaded to a specified directory in the file system, strips their contents from the request body and passes an altered request to the backend, thus allowing arbitrary handling of uploaded files. Stored files will be served directly through NGINX. In this way no FastCGI process will be blocked with handling large amounts of data either in one or another direction.

## Configuration ##

TyphoonAE's default configuration lets you use the Blobstore API right out of
the box.

Similar to the dev\_appserver.py TyphoonAE's apptool provides the
--blobstore\_path command line option for specifying an alternate directory to
store the uploaded files.

The maximum file size for uploaded data in TyphoonAE is only limited by the
bandwidth, operating system and your hardware. The NGINX upload
[module](http://www.grid.net.ru/nginx/upload.en.html) takes a number of
directives to configure a "soft" and "hard" limit or set the upload buffer
size.