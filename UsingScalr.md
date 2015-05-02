

# Using TyphoonAE With Scalr #

You can use [Scalr](http://scalr.net) to create and manage a scalable
infrastructure for TyphoonAE. The following steps will guide you through the
process of setting up and configuring your own App Engine.

## Prerequisites ##

In order to run TyphoonAE on Scalr you need to register at [Amazon Web Servces](http://aws.amazon.com) and [Scalr](http://scalr.net) which helps you to manage
and configure your instances on Amazon's platform. It is recommended to have a
basic understanding of how things work on AWS and which are the steps to get an
[EC2](http://aws.amazon.com/documentation/ec2/) instance up and running even if
Scalr will take completely care of it. The Scalr [wiki](http://wiki.scalr.net/)
is also a great resource and highly recommended.

Once you have successfully set up both accounts, it's just a few more steps to
run your Typhoon App Engine _farm_.

## Setting Up Your Farm ##

Let's now start by creating a [farm](http://wiki.scalr.net/What_is.../A_Farm).
Select 'Build new' from 'Server Farms' in the main menu.

![http://wiki.typhoonae.googlecode.com/hg/farms_build.jpg](http://wiki.typhoonae.googlecode.com/hg/farms_build.jpg)

After typing in the name and a description of your Farm, we change to the
'Roles' tab. A Role is an AMI or virtual machine image that serves as a
component of your infrastructure architecture, and is used to launch one or
more Instances.

![http://wiki.typhoonae.googlecode.com/hg/farms_build_roles.jpg](http://wiki.typhoonae.googlecode.com/hg/farms_build_roles.jpg)

We currently provide a single 'typhoonae-dev' Role. It is backed by an AWS
image with the ID **ami-b0bf48d9** in region US-East. 'Add' this role to your
Farm. If the 'typhoonae-dev' role does not exist, you need to manually launch
the AMI through the AWS console and import it by selecting 'Import non-scalr
server' from 'Servers' in the top menu.

Enter the server's public ip address, give it a Behavior, Role name, then click
'Next'. Scalr gives you a command to execute on the server. Now wait until all
running `scalarizr` processed terminated (~ 1 min) and execute the import
command in the shell. If everything goes well, you'll be redirected to the
snapshot status page. After up to half an hour, the snapshot will have
completed, and you can terminate or shutdown your server.

After saving you're ready to launch your Farm. It will take a few minutes to
start the attached Role. When the server first starts up, it will be running
NGINX, the App Config Service, RabbitMQ and the memcached.

Let's add a valid DNS zone now by selecting 'Add new' in the 'Websites' / 'DNS
Zones' menu. You can choose between an atomatically generated domain provided
by Scalr or a domain you own.

![http://wiki.typhoonae.googlecode.com/hg/dns_zone_add.jpg](http://wiki.typhoonae.googlecode.com/hg/dns_zone_add.jpg)

We're half way through setting up TyphoonAE in the cloud. The next steps are
very important, though. It is crucial for the services that they can safely
resolve our newly added domain. Therefore, we need to tweak the
`/etc/resolv.conf` file on the running server. Scalr provides a very convenient
way to get a command line shell within your web browser. Just navigate to the
server overview page by selecting 'Manage' from 'Servers' in the main menu.
Then click on the console icon of the running server. You'll be logged in as
the super user.

```
  $ vim /etc/resolv.conf
```

The following entries should be listed in the `/etc/resolv.conf` file.
Typically, you just have to add the first line:

```
  nameserver 127.0.0.1
  nameserver 172.16.0.23
  domain ec2.internal
  search ec2.internal
```

Now replace `localhost` in `/home/ubuntu/typhoonae/etc/default-nginx.conf` with
the domain of your DNS zone.

```
  server {
    listen      80;
    server_name yourdomain.scalr.ws;

    access_log  /home/ubuntu/typhoonae/var/log/httpd-access.log;
    error_log   /home/ubuntu/typhoonae/var/log/httpd-error.log;

    location / {
        root    /home/ubuntu/typhoonae/doc/www;
    }
  }
```

Two more configuration steps, and we're through. First add a wildcard record to
the DNS zone configuration pointing to the external IP of the TyphoonAE Role
(server). Why do we need this? The reason is pretty simple. Let's say you want
to deploy an app with the ID `myapp`. The wildcard subdomain ensures that your
app can be accessed with the following URL `http://myapp.yourdomain.com`.

![http://wiki.typhoonae.googlecode.com/hg/dns_zone_edit.jpg](http://wiki.typhoonae.googlecode.com/hg/dns_zone_edit.jpg)

In a final step modify the _Security group_ settings of the TyphoonAE Role.
Otherwise, we won't be able to either deploy nor access any application.

![http://wiki.typhoonae.googlecode.com/hg/sec_group_edit.jpg](http://wiki.typhoonae.googlecode.com/hg/sec_group_edit.jpg)

## Uploading Your Application ##

In order to deploy a Google App Engine Python application to your TyphoonAE
environment, simply use the original `appcfg.py` command from the SDK. See
[this page](UsingAppcfg.md) for an overview of Typhoon's _Appcfg Service_.

```
  $ python appcfg.py --insecure -s yourdomain.scalr.ws:8080 update myapp
```

If everything works well, we expect the output of `appcfg.py` to be as follows:

```
  Application: myapp; version: 1.
  Server: yourdomain.scalr.ws:8080.
  Scanning files on local disk.
  Initiating update.
  Cloning 38 static files.
  Cloning 384 application files.
  Cloned 100 files.
  Cloned 200 files.
  Cloned 300 files.
  Uploading 312 files and blobs.
  Uploaded 312 files and blobs
  Precompilation starting.
  Precompilation completed.
  Deploying new version.
  Checking if new version is ready to serve.
  Will check again in 1 seconds.
  Checking if new version is ready to serve.
  Will check again in 2 seconds.
  Checking if new version is ready to serve.
  Will check again in 4 seconds.
  Checking if new version is ready to serve.
  Closing update: new version is ready to start serving.
  Uploading index definitions.
```

Since the _Appcfg Service_ provides a simple overview of the installed apps,
your application ID and a version info should appera here:

> http://yourdomain.scalr.ws:8080

```
  myapp (1.345942587489648640)
```

Now access the application using a web browser with the follwing URL:

> http://myapp.yourdomain.scalr.ws (http://myapp.yourdomain.ws)