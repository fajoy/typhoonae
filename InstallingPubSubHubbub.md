# PubSubHubbub with TyphoonAE #

Since TyphoonAE implements scheduled tasks and the task queue service you can
easily set up a [PubSubHubbub](http://pubsubhubbub.googlecode.com) hub.
This how-to follows mostly Mariano Guerra's excellent guide which you can find
[here](http://code.google.com/p/pubsubhubbub/wiki/DeveloperGettingStartedGuide).
One of the main differences is that you don't have to run tasks _manually_.

## Requirements ##

Before you can start you will need a complete TyphoonAE [buildout](http://code.google.com/p/typhoonae/downloads/list), the
[pubsubhubbub](http://code.google.com/p/pubsubhubbub/source/checkout) and the
[tubes](http://github.com/marianoguerra/tubes) sources. Keep in mind that tubes
requires version 2.6.x of the Python interpreter due to class decorators.

## Configuring the hub ##

There's just a single step to configure the hub application. Change into the
root directory of your TyphoonAE buildout and enter the following command:

```
  $ ./bin/apptool --fcgi_port=8888 --crontab /ABSOLUTE/PATH/TO/pubsubhubbub/hub/
```

Start the services:

```
  $ ./bin/supervisord
```

We use cron for scheduled tasks. When all services are up and running acitvate the crontab by typing:

```
  $ crontab -e
```

Check on http://localhost:8080 that the hub started and go on by following the steps of Mariano Guerra's
[guide](http://code.google.com/p/pubsubhubbub/wiki/DeveloperGettingStartedGuide).
As mentioned above, you don't have to process the tasks manually.

Happy publishing!