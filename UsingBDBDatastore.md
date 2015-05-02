# Using the Berkeley DB Datastore #

[BDBDatastore](http://arachnid.github.com/bdbdatastore) is an alternate datastore backend for App Engine, implemented using BDB JE. It requires JAVA installed in your machine.

Use apptool to enable BDBDatastore:

```
  $ bin/apptool --datastore=bdbdatastore parts/google_appengine/demos/guestbook/
```

Don't forget to create the index.yaml file:

```
  $ cat > parts/google_appengine/demos/guestbook/index.yaml
  indexes:

  - kind: Greeting
    properties:
    - name: date
      direction: desc
  <ctrl-c>
```

Then run the supervisor daemon by typing:

```
  $ bin/supervisord
```