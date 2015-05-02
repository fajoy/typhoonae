# TyphoonAE on VMware/VirtualBox #

For the ones who don't want to build their own TyphoonAE environment, we supply
a preconfigured VMware/VirtualBox appliance. You can run multiple versions of
different GAE Python applications on this TyphoonAE _box_. To upload
application files, run the original appcfg.py command from the SDK with the
update action and the name of your application's root directory.

![http://wiki.typhoonae.googlecode.com/hg/multiple_apps.png](http://wiki.typhoonae.googlecode.com/hg/multiple_apps.png)

See [this page](UsingAppcfg.md) for a brief introduction of TyphoonAE's Appcfg
Service.

Since TyphoonAE is still _beta_, it is not guaranteed that all GAE Python applications will run. See [these notes](http://code.google.com/p/typhoonae/wiki/RoadMap#Known_Incompatibilities) to get some information on what to expect. However, any [bug reports](http://code.google.com/p/typhoonae/issues) are highly welcome.

## Getting the Image ##

Download and unpack the archive.

```
  $ curl -O http://www.typhoonae.org/TyphoonAE_Ubuntu_10.10_64bit.vmwarevm.tar.gz
  $ tar xvzf TyphoonAE_Ubuntu_10.10.64bit.vmwarevm.tar.gz
```

A VirtualBox appliance is also available.

```
  $ curl -O http://www.typhoonae.org/TyphoonAE_Ubuntu_10.10_64bit.vbox.tar.gz
  $ tar xvzf TyphoonAE_Ubuntu_10.10.64bit.vbox.tar.gz
```

## Installed and Preconfigured Services ##

Since the virtual machine image is a _all-in-one_ installation, it has a whole
bunch of software installed. The following list shows only the more important
components.

  * Ubuntu 10.10 64bit
  * Google App Engine SDK 1.4.0 (Python)
  * Python 2.6
  * TyphoonAE 0.2.0
  * MongoDB 1.6.3
  * RabbitMQ 1.8.0
  * Ejabberd 2.1.5
  * Memcached 1.4.5
  * Nginx 0.7.67

## Running and Configuring the Engine ##

Run VMware/VirtualBox and import the appliance. Once the guest system is up and
running, login by using `typhoonae` as user and password.

Now it is very important to obtain the correct IP address of your guest. You
can use the following command:

```
  $ ifconfig eth0
```

On the VMware/VirtualBox host add the following lines to your local hosts table
(`/etc/hosts` on Linux/OS X) and don't forget to replace 10.0.1.42 with the
correct IP address of the guest.

```
  # TyphoonAE VM beta
  10.0.1.42       typhoonae.local    typhoonae

  # My application
  10.0.1.42       myapp.typhoonae.local
  10.0.1.42       1.latest.myapp.typhoonae.local
```

For each application you plan to deploy to TyphoonAE make the appropriate
entries as shown above. Since TyphoonAE supports multiple versions, add another
line for each version.

## Uploading the App ##

Now deploy the 'myapp' GAE Python application by typing:

```
  $ appcfg.py --insecure -s typhoonae.local:8080 update path/to/myapp/
```

Visit your application by opening http://myapp.typhoonae.local in your web
browser.

To see what applications are installed enter http://typhoonae.local:8080 into
your web browser.

![http://wiki.typhoonae.googlecode.com/hg/appcfg_overview.png](http://wiki.typhoonae.googlecode.com/hg/appcfg_overview.png)

In order to cleanly shutdown the virtual machine, login to the guest system ...

```
  $ ssh typhoonae@typhoonae.local
```

... and enter the following commands:

```
  $ sudo supervisorctl shutdown
  $ sudo shutdown -h now
```

Please bear in mind that TyphoonAE and the above configuration is beta.
However, you're invited to help improving all this. Contact the TyphoonAE
discussion group.