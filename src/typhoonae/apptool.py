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

import optparse
import os
import re
import socket
import sys
import typhoonae 

DESCRIPTION = ("Console script to perform common tasks on configuring an "
               "application.")

USAGE = "usage: %prog [options] <application root>"

NGINX_HEADER = """
server {
    listen      8080;
    server_name localhost;

    access_log  %(var)s/log/httpd-access.log;
    error_log   %(var)s/log/httpd-error.log;
"""

NGINX_FOOTER = """
}
"""

NGINX_STATIC_LOCATION = """
location ~ ^/(%(path)s)/ {
    root %(root)s;
    expires 30d;
}
"""

NGINX_REGEX_LOCATION = """
location ~* ^%(regex)s$ {
    root %(root)s;
    rewrite %(rewrite)s break;
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

SUPERVISOR_APPSERVER_CONFIG = """
[fcgi-program:appserver]
command = %(bin)s/appserver --log=%(var)s/log/appserver.log --xmpp_host=%(xmpp_host)s %(app_root)s
socket = tcp://%(addr)s:%(port)s
process_name = %%(program_name)s_%%(process_num)02d
numprocs = 2
priority = 999
redirect_stderr = true
stdout_logfile = %(var)s/log/appserver.log
stdout_logfile_maxbytes = 1MB
stdout_logfile_backups = 10
stderr_logfile = %(var)s/log/appserver-error.log
stderr_logfile_maxbytes = 1MB
"""

SUPERVISOR_XMPP_HTTP_DISPATCH_CONFIG = """
[program:xmpp_http_dispatch]
command = %(bin)s/xmpp_http_dispatch --jid=%(jid)s --password=%(password)s
process_name = xmpp_http_dispatch
priority = 999
redirect_stderr = true
stdout_logfile = %(var)s/log/xmpp_http_dispatch.log
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


def write_nginx_conf(options, conf, app_root):
    """Writes nginx server configuration stub."""

    var = os.path.abspath(options.var)
    addr = options.addr
    port = options.port

    httpd_conf_stub = open(options.nginx, 'w')
    httpd_conf_stub.write("# Automatically generated NGINX configuration file: "
                          "don't edit!\n"
                          "# Use apptool to modify.\n")

    httpd_conf_stub.write(NGINX_HEADER % locals())

    static_dirs = {}
    secure_urls = []

    for handler in conf.handlers:
        ltrunc_url = re.sub('^/', '', handler.url)
        if handler.GetHandlerType() == 'static_dir':
            if handler.static_dir in static_dirs:
                static_dirs[handler.static_dir].append(ltrunc_url)
            else:
                static_dirs[handler.static_dir] = [ltrunc_url]
        if handler.GetHandlerType() == 'static_files':
            rewrite = '^%s$ /%s' % (handler.url,
                                    handler.static_files.replace('\\', '$'))
            httpd_conf_stub.write(NGINX_REGEX_LOCATION % dict(
                regex=handler.url,
                root=app_root,
                rewrite=rewrite
            ))
        if handler.secure == 'always':
            if ltrunc_url not in secure_urls:
                secure_urls.append(ltrunc_url)

    for s in static_dirs:
        if len(s.split('/')) > 1:
            root = app_root + '/' + '/'.join(s.split('/')[1:])
        else:
            root = app_root
        httpd_conf_stub.write(NGINX_STATIC_LOCATION % dict(
            root=root,
            path='|'.join(static_dirs[s]),
            )
        )

    if secure_urls:
        httpd_conf_stub.write(NGINX_SECURE_LOCATION % dict(
            addr=addr,
            app_id=conf.application,
            fcgi_params=FCGI_PARAMS,
            passwd_file=os.path.abspath(options.passwd_file),
            path='|'.join(secure_urls),
            port=port
            )
        )

    vars = locals()
    vars.update(dict(fcgi_params=FCGI_PARAMS))
    httpd_conf_stub.write(NGINX_FCGI_CONFIG % vars)
    httpd_conf_stub.write(NGINX_FOOTER)
    httpd_conf_stub.close()


def write_supervisor_conf(options, conf, app_root):
    """Writes supercisord configuration stub."""

    bin = os.path.abspath(os.path.dirname(sys.argv[0]))
    var = os.path.abspath(options.var)
    addr = options.addr
    port = options.port
    xmpp_host = options.xmpp_host

    supervisor_conf_stub = open(options.supervisor, 'w')
    supervisor_conf_stub.write(
        "# Automatically generated supervisor configuration file: don't edit!\n"
        "# Use apptool to modify.\n")

    supervisor_conf_stub.write(SUPERVISOR_APPSERVER_CONFIG % locals())

    jid = conf.application + '@' + xmpp_host
    password = conf.application

    if conf.inbound_services is not None:
        for service in conf.inbound_services:
            if service == 'xmpp_message':
                supervisor_conf_stub.write(
                    SUPERVISOR_XMPP_HTTP_DISPATCH_CONFIG % locals())

    supervisor_conf_stub.close()


def write_ejabberd_conf(options):
    """Writes ejabberd configuration file."""

    bin = os.path.abspath(os.path.dirname(sys.argv[0]))
    xmpp_host = options.xmpp_host

    ejabberd_conf = open(options.ejabberd, 'w')
    ejabberd_conf.write(EJABBERD_CONFIG % locals())
    ejabberd_conf.close()


def main():
    """Runs the apptool console script."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--ejabberd", dest="ejabberd", metavar="FILE",
                  help="write ejabberd configuration to this file",
                  default=os.path.join('etc', 'ejabberd.cfg'))

    op.add_option("--fcgi_host", dest="addr", metavar="ADDR",
                  help="use this FastCGI host",
                  default='localhost')

    op.add_option("--fcgi_port", dest="port", metavar="PORT",
                  help="use this port of the FastCGI host",
                  default='8081')

    op.add_option("-n", "--nginx", dest="nginx", metavar="FILE",
                  help="write nginx configuration to this file",
                  default=os.path.join('etc', 'server.conf'))

    op.add_option("-p", "--passwd", dest="passwd_file", metavar="FILE",
                  help="use this passwd file for authentication",
                  default=os.path.join('etc', 'htpasswd'))

    op.add_option("-s", "--supervisor", dest="supervisor", metavar="FILE",
                  help="write supervisor configuration to this file",
                  default=os.path.join('etc', 'appserver.conf'))

    op.add_option("--var", dest="var", metavar="PATH",
                  help="use this directory for platform independent data",
                  default=os.environ.get('TMPDIR', '/var'))

    op.add_option("--xmpp_host", dest="xmpp_host", metavar="HOST",
                  help="use this XMPP host", default=socket.gethostname())

    (options, args) = op.parse_args()

    if sys.argv[-1].startswith('-') or sys.argv[-1] == sys.argv[0]:
        op.print_usage()
        sys.exit(2)

    app_root = sys.argv[-1]

    if not os.path.isabs(app_root):
        app_root = os.path.normpath(os.path.join(os.getcwd(), app_root))

    conf = typhoonae.getAppConfig(app_root)

    write_nginx_conf(options, conf, app_root)
    write_supervisor_conf(options, conf, app_root)
    write_ejabberd_conf(options)
