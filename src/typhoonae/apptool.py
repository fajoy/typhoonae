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
command = %(bin)s/appserver --log=%(var)s/log/appserver.log %(app_root)s
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
            sys.stderr.write('Warning: handler for url %s of type static_files '
                             'in app.yaml getting ignored. Use static_dir '
                             'instead.\n' % (handler.url))
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

    supervisor_conf_stub = open(options.supervisor, 'w')
    supervisor_conf_stub.write(
        "# Automatically generated supervisor configuration file: don't edit!\n"
        "# Use apptool to modify.\n")

    supervisor_conf_stub.write(SUPERVISOR_APPSERVER_CONFIG % locals())
    supervisor_conf_stub.close()


def main():
    """Runs the apptool console script."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

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
