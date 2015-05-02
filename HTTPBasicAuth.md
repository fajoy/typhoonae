## Configuring HTTP Basic Authentication ##

TyphoonAE allows optional HTTP Basic Authentication. The following notes are ment as a guide on how to enable this feature for you application.

  * Place a `htpasswd`-file into your application root directory. Don't forget to set up an initial user.

  * Run `apptool`:

```
  ./bin/apptool --http_base_auth /path/to/your/app
```