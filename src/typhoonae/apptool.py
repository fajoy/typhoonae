# -*- coding: utf-8 -*-
#
# Copyright 2009 Tobias Rodäbel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Console script to perform common tasks on configuring an application."""

import google.appengine.api.croninfo
import google.appengine.cron
import getpass
import optparse
import os
import re
import socket
import subprocess
import sys
import tempfile
import typhoonae
import typhoonae.fcgiserver

DESCRIPTION = ("Console script to perform common tasks on configuring an "
               "application.")

USAGE = "usage: %prog [options] <application root>"

DEFAULT_EXPIRATION = '30d'

NGINX_HEADER = """
server {
    client_max_body_size 100m;
    listen      %(http_port)s;
    server_name %(server_name)s;

    access_log  %(var)s/log/httpd-access.log;
    error_log   %(var)s/log/httpd-error.log;
"""

NGINX_FOOTER = """
}
"""

NGINX_STATIC_LOCATION = """
location ~ ^/(%(path)s)/ {
    root %(root)s;%(rewrite)s
    expires %(expires)s;
}
"""

NGINX_REGEX_LOCATION = """
location ~* ^%(regex)s$ {
    root %(root)s;
    rewrite %(rewrite)s break;
    expires %(expires)s;
}
"""

FCGI_PARAMS = """\
    fastcgi_param CONTENT_LENGTH $content_length;
    fastcgi_param CONTENT_TYPE $content_type;
    fastcgi_param PATH_INFO $fastcgi_script_name;
    fastcgi_param QUERY_STRING $query_string;
    fastcgi_param REMOTE_ADDR $remote_addr;
    fastcgi_param REQUEST_METHOD $request_method;
    fastcgi_param REQUEST_URI $request_uri;
    fastcgi_param SERVER_NAME $server_name;
    fastcgi_param SERVER_PORT $server_port;
    fastcgi_param SERVER_PROTOCOL $server_protocol;
    %(add_params)s
    fastcgi_pass_header Authorization;
    fastcgi_intercept_errors off;\
"""

NGINX_SECURE_LOCATION = """
location ~ ^/(%(path)s) {
    auth_basic "%(app_id)s";
    auth_basic_user_file %(passwd_file)s;
    fastcgi_pass %(addr)s:%(port)s;
%(fcgi_params)s
}
"""

NGINX_FCGI_CONFIG = """
location / {
    fastcgi_pass %(addr)s:%(port)s;
%(fcgi_params)s
}
"""

NGINX_UPLOAD_CONFIG = """
location /%(upload_url)s {
    # Pass altered request body to this location
    upload_pass @%(app_id)s;

    # Store files to this directory
    # The directory is hashed, subdirectories 0 1 2 3 4 5 6 7 8 9
    # should exist
    upload_store %(blobstore_path)s 1;

    # Allow uploaded files to be read only by user
    upload_store_access user:r;

    # Set specified fields in request body
    upload_set_form_field $upload_field_name.name "$upload_file_name";
    upload_set_form_field $upload_field_name.content_type "$upload_content_type";
    upload_set_form_field $upload_field_name.path "$upload_tmp_path";

    # Inform backend about hash and size of a file
    upload_aggregate_form_field "$upload_field_name.md5" "$upload_file_md5";
    upload_aggregate_form_field "$upload_field_name.size" "$upload_file_size";

    upload_pass_form_field ".*";

    upload_cleanup 400 404 499 500-505;
}

location @%(app_id)s {
    fastcgi_pass %(addr)s:%(port)s;
%(fcgi_params)s
}
"""

NGINX_DOWNLOAD_CONFIG = """
location ~ ^/_ah/blobstore/%(app_id)s/(.*) {
    root %(blobstore_path)s;
    rewrite ^/_ah/blobstore/%(app_id)s/(.*) /$1 break;
    internal;
}
"""

SUPERVISOR_MONGODB_CONFIG = """
[program:mongod]
command = %(bin)s/mongod --dbpath=%(var)s
process_name = mongod
directory = %(bin)s
priority = 10
redirect_stderr = true
stdout_logfile = %(var)s/log/mongod.log

[program:intid]
command = %(bin)s/intid
process_name = intid
directory = %(root)s
priority = 20
redirect_stderr = true
stdout_logfile = %(var)s/log/intid.log
stopsignal = INT
"""

SUPERVISOR_BDBDATASTORE_CONFIG = """
[program:bdbdatastore]
command = java -jar %(root)s/parts/bdbdatastore/bdbdatastore-0.2.2.jar %(var)s
process_name = bdbdatastore
directory = %(app_root)s
priority = 10
redirect_stderr = true
stdout_logfile = %(var)s/log/bdbdatastore.log
"""

SUPERVISOR_APPSERVER_CONFIG = """
[fcgi-program:%(app_id)s]
command = %(bin)s/appserver --auth_domain=%(auth_domain)s --log=%(var)s/log/%(app_id)s.log --datastore=%(datastore)s --xmpp_host=%(xmpp_host)s --server_software=%(server_software)s --blobstore_path=%(blobstore_path)s --upload_url=%(upload_url)s --smtp_host=%(smtp_host)s --smtp_port=%(smtp_port)s --smtp_user=%(smtp_user)s --smtp_password=%(smtp_password)s --email=%(email)s --password=%(password)s %(add_opts)s%(app_root)s
socket = tcp://%(addr)s:%(port)s
process_name = %%(program_name)s_%%(process_num)02d
numprocs = 2
priority = 999
redirect_stderr = true
stdout_logfile = %(var)s/log/%(app_id)s.log
stdout_logfile_maxbytes = 1MB
stdout_logfile_backups = 10
stderr_logfile = %(var)s/log/%(app_id)s-error.log
stderr_logfile_maxbytes = 1MB
"""

SUPERVISOR_AMQP_CONFIG = """
[program:taskworker]
command = %(bin)s/taskworker --amqp_host=%(amqp_host)s
process_name = taskworker
directory = %(root)s
priority = 20
redirect_stderr = true
stdout_logfile = %(var)s/log/taskworker.log

[program:deferred_taskworker]
command = %(bin)s/deferred_taskworker --amqp_host=%(amqp_host)s
process_name = deferred_taskworker
directory = %(root)s
priority = 20
redirect_stderr = true
stdout_logfile = %(var)s/log/deferred_taskworker.log
"""

SUPERVISOR_XMPP_HTTP_DISPATCH_CONFIG = """
[program:xmpp_http_dispatch]
command = %(bin)s/xmpp_http_dispatch --address=%(internal_server_name)s:%(internal_http_port)s --jid=%(jid)s --password=%(password)s
process_name = xmpp_http_dispatch
priority = 999
redirect_stderr = true
stdout_logfile = %(var)s/log/xmpp_http_dispatch.log
"""

SUPERVISOR_WEBSOCKET_CONFIG = """
[program:websocket]
command = %(bin)s/websocket --address=%(internal_server_name)s:%(internal_http_port)s --app_id=%(app_id)s
process_name = websocket
priority = 999
redirect_stderr = true
stdout_logfile = %(var)s/log/websocket.log
"""

EJABBERD_CONFIG = """
override_local.

override_acls.

{loglevel, 4}.

{hosts, ["%(xmpp_host)s"]}.

{listen,
 [

  {5222, ejabberd_c2s, [

                        {access, c2s},
                        {shaper, c2s_shaper},
                        {max_stanza_size, 65536}
                       ]},

  {5269, ejabberd_s2s_in, [
                           {shaper, s2s_shaper},
                           {max_stanza_size, 131072}
                          ]},

  {5280, ejabberd_http, [
                         captcha,
                         http_bind,
                         http_poll,
                         web_admin
                        ]}

 ]}.

{auth_method, [external]}.

{extauth_program, "%(bin)s/ejabberdauth"}.

{shaper, normal, {maxrate, 1000}}.

{shaper, fast, {maxrate, 50000}}.

{acl, local, {user_regexp, ""}}.

{access, max_user_sessions, [{10, all}]}.

{access, max_user_offline_messages, [{5000, admin}, {100, all}]}.

{access, local, [{allow, local}]}.

{access, c2s, [{deny, blocked},
               {allow, all}]}.

{access, c2s_shaper, [{none, admin},
                      {normal, all}]}.

{access, s2s_shaper, [{fast, all}]}.

{access, announce, [{allow, admin}]}.

{access, configure, [{allow, admin}]}.

{access, muc_admin, [{allow, admin}]}.

{access, muc, [{allow, all}]}.

{access, pubsub_createnode, [{allow, all}]}.

{access, register, [{allow, all}]}.

{language, "en"}.

{modules,
 [
  {mod_adhoc,    []},
  {mod_announce, [{access, announce}]},
  {mod_caps,     []},
  {mod_configure,[]},
  {mod_disco,    []},
  {mod_irc,      []},
  {mod_http_bind, []},
  {mod_last,     []},
  {mod_muc,      [
                  {access, muc},
                  {access_create, muc},
                  {access_persistent, muc},
                  {access_admin, muc_admin}
                 ]},
  {mod_offline,  [{access_max_user_messages, max_user_offline_messages}]},
  {mod_ping,     []},
  {mod_privacy,  []},
  {mod_private,  []},
  {mod_pubsub,   [
                  {access_createnode, pubsub_createnode},
                  {pep_sendlast_offline, false},
                  {last_item_cache, false},
                  {plugins, ["flat", "hometree", "pep"]}
                 ]},
  {mod_register, [
                  {welcome_message, {"Welcome!",
                                     "Hi.\\nWelcome to this Jabber server."}},
                  {access, register}
                 ]},
  {mod_roster,   []},
  {mod_shared_roster,[]},
  {mod_stats,    []},
  {mod_time,     []},
  {mod_vcard,    []},
  {mod_version,  []}
 ]}.
"""


def write_nginx_conf(options, conf, app_root, internal=False, mode='w'):
    """Writes nginx server configuration stub."""

    addr = options.addr
    add_params = []
    app_id = conf.application
    blobstore_path = os.path.abspath(
        os.path.join(options.blobstore_path, app_id))
    http_port = options.http_port
    port = options.port
    server_name = options.server_name
    upload_url = options.upload_url
    var = os.path.abspath(options.var)

    if internal:
        http_port = '8770'
        server_name = 'localhost'
        add_params = ['fastcgi_param X-TyphoonAE-Secret "secret";']

    for i in range(10):
        p = os.path.join(blobstore_path, str(i))
        if not os.path.isdir(p):
            os.makedirs(p)

    httpd_conf_stub = open(options.nginx, mode)

    if not internal:
        httpd_conf_stub.write(
            "# Automatically generated NGINX configuration file: don't edit!\n"
            "# Use apptool to modify.\n")
    elif internal:
        httpd_conf_stub.write(
            "# Internal configuration.\n")

    httpd_conf_stub.write(NGINX_HEADER % locals())

    urls_require_login = []

    for handler in conf.handlers:
        ltrunc_url = re.sub('^/', '', handler.url)
        if handler.GetHandlerType() == 'static_dir':
            if ltrunc_url != handler.static_dir:
                rewrite = '^/(%s)/(.*)$ /%s/$2 break;' % (ltrunc_url,
                                                          handler.static_dir)
                rewrite = '\n    rewrite ' + rewrite
            else:
                rewrite = ''
            l = handler.static_dir.split('/')
            httpd_conf_stub.write(NGINX_STATIC_LOCATION % dict(
                expires=(handler.expiration or
                         conf.default_expiration or
                         DEFAULT_EXPIRATION),
                path=ltrunc_url,
                rewrite=rewrite,
                root=app_root
                )
            )
        if handler.GetHandlerType() == 'static_files':
            if handler.url == '/':
                url = '/(%s)' % handler.upload.split('/')[-1]
                files = handler.static_files.replace(handler.upload, '$1')
            else:
                url = handler.url
                files = handler.static_files.replace('\\', '$')
                
            rewrite = '^%s$ /%s' % (url, files)
            httpd_conf_stub.write(NGINX_REGEX_LOCATION % dict(
                expires=(handler.expiration or
                         conf.default_expiration or
                         DEFAULT_EXPIRATION),
                regex=url,
                rewrite=rewrite,
                root=app_root
                )
            )
        if handler.login in ('admin', 'required'):
            if ltrunc_url not in urls_require_login:
                urls_require_login.append(ltrunc_url)

    if urls_require_login and options.http_base_auth_enabled and not internal:
        httpd_conf_stub.write(NGINX_SECURE_LOCATION % dict(
            addr=addr,
            app_id=conf.application,
            fcgi_params=FCGI_PARAMS % {'add_params': '\n'.join(add_params)},
            passwd_file=os.path.join(app_root, 'htpasswd'),
            path='|'.join(urls_require_login),
            port=port
            )
        )

    vars = locals()
    vars.update(
        dict(fcgi_params=FCGI_PARAMS % {'add_params': '\n'.join(add_params)}))
    httpd_conf_stub.write(NGINX_UPLOAD_CONFIG % vars)
    httpd_conf_stub.write(NGINX_DOWNLOAD_CONFIG % vars)
    httpd_conf_stub.write(NGINX_FCGI_CONFIG % vars)
    httpd_conf_stub.write(NGINX_FOOTER)
    httpd_conf_stub.close()


def write_supervisor_conf(options, conf, app_root):
    """Writes supercisord configuration stub."""

    addr = options.addr
    amqp_host = options.amqp_host
    app_id = conf.application
    auth_domain = options.auth_domain
    bin = os.path.abspath(os.path.dirname(sys.argv[0]))
    blobstore_path = os.path.abspath(options.blobstore_path)
    datastore = options.datastore.lower()
    develop_mode = options.develop_mode
    email = options.email
    http_port = options.http_port
    internal_http_port = 8770
    internal_server_name = 'localhost'
    password = options.password
    port = options.port
    root = os.getcwd()
    server_name = options.server_name
    server_software = options.server_software
    upload_url = options.upload_url
    var = os.path.abspath(options.var)
    xmpp_host = options.xmpp_host
    smtp_host = options.smtp_host
    smtp_port = options.smtp_port
    smtp_user = options.smtp_user
    smtp_password = options.smtp_password

    additional_options = []

    if develop_mode:
        additional_options.append(('debug', None))

    add_opts = ' '.join(
        ['--%s' % opt for opt, arg in additional_options if arg is None])

    add_opts += ' '.join(
        ['--%s=%s' % (opt, arg) for opt, arg in additional_options if arg])

    if add_opts:
        add_opts += ' '

    supervisor_conf_stub = open(
        os.path.join(root, 'etc', conf.application+'-supervisor.conf'), 'w')
    supervisor_conf_stub.write(
        "# Automatically generated supervisor configuration file: don't edit!\n"
        "# Use apptool to modify.\n")

    if datastore == 'mongodb':
        supervisor_conf_stub.write(SUPERVISOR_MONGODB_CONFIG % locals())
    elif datastore == 'bdbdatastore':
        supervisor_conf_stub.write(SUPERVISOR_BDBDATASTORE_CONFIG % locals())
    elif datastore == 'remote':
        pass
    else:
        raise RuntimeError, "unknown datastore"

    supervisor_conf_stub.write(SUPERVISOR_APPSERVER_CONFIG % locals())
    supervisor_conf_stub.write(SUPERVISOR_AMQP_CONFIG % locals())

    jid = conf.application + '@' + xmpp_host
    password = conf.application

    if conf.inbound_services is not None:
        for service in conf.inbound_services:
            if service == 'xmpp_message':
                supervisor_conf_stub.write(
                    SUPERVISOR_XMPP_HTTP_DISPATCH_CONFIG % locals())
            elif service == 'websocket_message':
                supervisor_conf_stub.write(
                    SUPERVISOR_WEBSOCKET_CONFIG % locals())

    supervisor_conf_stub.close()


def write_ejabberd_conf(options):
    """Writes ejabberd configuration file."""

    bin = os.path.abspath(os.path.dirname(sys.argv[0]))
    xmpp_host = options.xmpp_host

    ejabberd_conf = open(options.ejabberd, 'w')
    ejabberd_conf.write(EJABBERD_CONFIG % locals())
    ejabberd_conf.close()


def print_error(msg):
    """Prints an error message to the standard error stream."""

    sys.stderr.write("%s: %s\n" % (os.path.basename(sys.argv[0]), msg))


CRONTAB_ROW = re.compile(r'^\s*([^@#\s]+)\s+([^@#\s]+)\s+([^@#\s]+)'
                         r'\s+([^@#\s]+)\s+([^@#\s]+)\s+([^#\n]*)'
                         r'(\s+#\s*([^\n]*)|$)')

EVERY_DAY_SET = set([0, 1, 2, 3, 4, 5, 6])
EVERY_MONTH_SET = set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])


def read_crontab(options):
    """Reads the user's crontab.

    Args:
        options: Dictionary of command line options.

    Returns crontab entries.
    """

    result = list()

    p = subprocess.Popen(
        ['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()

    for entry in stdout.split('\n'):
        m = re.match(CRONTAB_ROW, entry)
        if m:
            result.append(m.groups())

    return result


class CrontabRow(object):
    """Represents one crontab row."""

    def __init__(self):
        """Initialize crontab row instance."""

        self.minute = '*'
        self.hour = '*'
        self.dom = '*'
        self.month = '*'
        self.dow = '*'
        self.command = ''
        self.description = None

    def __repr__(self):
        return "%s %s %s %s %s %s # %s" % (
            self.minute, self.hour, self.dom, self.month, self.dow,
            self.command, self.description)


def write_crontab(options, app_root):
    """Writes crontab entries."""

    cron_path = os.path.join(app_root, 'cron.yaml')
    if not os.path.isfile(cron_path):
        return
 
    cron_file = open(cron_path, 'r')
    try:
        cron_info = google.appengine.api.croninfo.LoadSingleCron(cron_file)
    except Exception, err_obj:
        print_error(str(err_obj))
        return
    finally:
        cron_file.close()

    tab = read_crontab(options)

    if not cron_info.cron:
        return tab

    for entry in cron_info.cron:
        parser = google.appengine.cron.groc.CreateParser(entry.schedule)
        parser.timespec()

        row = CrontabRow()

        if parser.time_string:
            m, h = parser.time_string.split(':')
            if len(m) == 2 and m[0] == '0': m = m[1:]
            if len(h) == 2 and h[0] == '0': h = h[1:]
            row.minute = m
            row.hour = h

        if parser.period_string:
            if parser.period_string == 'hours':
                row.minute = '0'
                row.hour = '*/%i' % parser.interval_mins
            elif parser.period_string == 'minutes':
                row.minute = '*/%i' % parser.interval_mins

        if parser.month_set and parser.month_set != EVERY_MONTH_SET:
            row.month = ','.join(map(str, parser.month_set))

        if parser.weekday_set and parser.weekday_set != EVERY_DAY_SET:
            row.dow = ','.join(map(str, parser.weekday_set))

        row.command = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), 'runtask')
        row.command += ' http://%s:%s%s' % (
            options.server_name, options.http_port, entry.url)

        row.description = '%s (%s)' % (entry.description, entry.schedule)

        tab.append(re.match(CRONTAB_ROW, str(row)).groups())

    if options.set_crontab:
        _, path = tempfile.mkstemp()
        try:
            tmp = open(path, "w")
            tmp.write('\n'.join([' '.join(r) for r in tab]))
            tmp.close()
            subprocess.call(['crontab', path])
        finally:
            if os.path.isfile(path):
                os.remove(path)

    return tab


def main():
    """Runs the apptool console script."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--auth_domain", dest="auth_domain", metavar="STRING",
                  help="use this value for the AUTH_DOMAIN environment "
                  "variable", default='localhost')

    op.add_option("--amqp_host", dest="amqp_host", metavar="ADDR",
                  help="use this AMQP host", default='localhost')

    op.add_option("--blobstore_path", dest="blobstore_path", metavar="PATH",
                  help="path to use for storing Blobstore file stub data",
                  default=os.path.join('var', 'blobstore'))

    op.add_option("--crontab", dest="set_crontab", action="store_true",
                  help="set crontab if cron.yaml exists", default=False)

    op.add_option("--datastore", dest="datastore", metavar="NAME",
                  help="use this datastore", default='mongodb')

    op.add_option("--develop", dest="develop_mode", action="store_true",
                  help="configure application for development", default=False)

    op.add_option("--ejabberd", dest="ejabberd", metavar="FILE",
                  help="write ejabberd configuration to this file",
                  default=os.path.join('etc', 'ejabberd.cfg'))

    op.add_option("--email", dest="email", metavar="EMAIL",
                  help="the username to use", default='')

    op.add_option("--fcgi_host", dest="addr", metavar="ADDR",
                  help="use this FastCGI host", default='localhost')

    op.add_option("--fcgi_port", dest="port", metavar="PORT",
                  help="use this port of the FastCGI host",
                  default='8081')

    op.add_option("--http_base_auth", dest="http_base_auth_enabled",
                  action="store_true",
                  help="enable HTTP base authentication",
                  default=False)

    op.add_option("--http_port", dest="http_port", metavar="PORT",
                  help="port for the HTTP server to listen on",
                  default=8080)

    op.add_option("--nginx", dest="nginx", metavar="FILE",
                  help="write nginx configuration to this file",
                  default=os.path.join('etc', 'server.conf'))

    op.add_option("--password", dest="password", metavar="PASSWORD",
                  help="the password to use", default='')

    op.add_option("--server_name", dest="server_name", metavar="STRING",
                  help="use this server name", default=socket.getfqdn())

    op.add_option("--server_software", dest="server_software", metavar="STRING",
                  help="use this server software identifier",
                  default=typhoonae.fcgiserver.SERVER_SOFTWARE)

    op.add_option("--smtp_host", dest="smtp_host", metavar="ADDR",
                  help="use this SMTP host", default='localhost')

    op.add_option("--smtp_port", dest="smtp_port", metavar="PORT",
                  help="use this SMTP port", default=25)

    op.add_option("--smtp_user", dest="smtp_user", metavar="STRING",
                  help="use this SMTP user", default='')

    op.add_option("--smtp_password", dest="smtp_password", metavar="STRING",
                  help="use this SMTP password", default='')
                  
    op.add_option("--upload_url", dest="upload_url", metavar="URI",
                  help="use this upload URL for the Blobstore configuration "
                       "(no leading '/')",
                  default='upload/')

    op.add_option("--var", dest="var", metavar="PATH",
                  help="use this directory for platform independent data",
                  default=os.environ.get('TMPDIR', '/var'))

    op.add_option("--xmpp_host", dest="xmpp_host", metavar="ADDR",
                  help="use this XMPP host", default=socket.getfqdn())

    (options, args) = op.parse_args()

    if sys.argv[-1].startswith('-') or sys.argv[-1] == sys.argv[0]:
        op.print_usage()
        sys.exit(2)

    app_root = sys.argv[-1]

    if not os.path.isabs(app_root):
        app_root = os.path.normpath(os.path.join(os.getcwd(), app_root))

    if options.datastore == 'remote':
        # Prompt for email and password when not set.
        if not options.email:
            options.email = raw_input('Email: ')
        if not options.password:
            options.password = getpass.getpass('Password: ')

    conf = typhoonae.getAppConfig(app_root)

    write_nginx_conf(options, conf, app_root)
    write_nginx_conf(options, conf, app_root, internal=True, mode='a')
    write_supervisor_conf(options, conf, app_root)
    write_ejabberd_conf(options)
    write_crontab(options, app_root)
