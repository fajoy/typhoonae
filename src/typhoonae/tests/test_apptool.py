# -*- coding: utf-8 -*-
#
# Copyright 2009, 2010 Tobias Rodäbel
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
"""Unit tests for the apptool console script."""

import os
import re
import shutil
import sys
import tempfile
import typhoonae
import typhoonae.apptool
import unittest


class ApptoolTestCase(unittest.TestCase):
    """Tests apptoll functions."""

    def setUp(self):
        """Loads the sample application."""

        self.app_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'sample'))
        self.curr_dir = os.getcwd()
        os.chdir(os.path.abspath(self.app_root))
        sys.path.insert(0, os.getcwd())
        self.conf = typhoonae.getAppConfig()
        assert self.conf.application == 'sample'

        class OptionsMock:
            amqp_host = "localhost"
            auth_domain = "example.com"
            blobstore_path = "/tmp/blobstore"
            datastore = "mongodb"
            develop_mode = False
            fcgi_host = "localhost"
            fcgi_port = 8081
            email = "test@example.com"
            environment = ""
            html_error_pages_root = "/tmp/html"
            http_base_auth_enabled = False
            http_port = 8080
            imap_host = "localhost"
            imap_port = 143
            imap_ssl = False
            imap_user = ""
            imap_password = ""
            imap_mailbox = "INBOX"
            internal_address = "localhost:8770"
            login_url = None
            logout_url = None
            multiple = False
            password = ""
            server_name = "host.local"
            server_software = "TyphoonAE"
            set_crontab = False
            smtp_host = "localhost"
            smtp_port = 25
            smtp_user = ""
            smtp_password = ""
            ssl_enabled = False
            ssl_certificate = None
            ssl_certificate_key = None
            upload_url = "upload/"
            use_celery = False
            var = "/tmp/var"
            xmpp_host = "localhost"

        self.options = OptionsMock()

    def tearDown(self):
        """Clean up the test environment."""

        try:
            shutil.rmtree(os.path.join(os.getcwd(), 'etc'))
        except OSError:
            pass
        os.chdir(self.curr_dir)

    def testScheduledTasksConfig(self):
        """Tests the configuration for scheduled tasks."""

        typhoonae.apptool.read_crontab(self.options)
        tab = typhoonae.apptool.write_crontab(self.options, self.app_root)
        self.assertEqual([
                ('*/1', '*', '*', '*', '*', os.path.join(
                    os.getcwd(), 'bin', 'runtask') +
                    ' http://localhost:8770/a',
                 ' # Test A (every 1 minutes)', 'Test A (every 1 minutes)')],
                 tab)

    def testNGINXConfig(self):
        """Writes a NGINX configuration file."""

        os.mkdir(os.path.join(os.getcwd(), 'etc'))
        paths = typhoonae.apptool.write_nginx_conf(
            self.options, self.conf, self.app_root)

        try:
            f = open(paths[0], 'r')
            config = f.read()
            self.assertTrue("""location ~* ^/(.*\.(gif|jpg|png))$ {
    root "%(app_root)s";
    rewrite ^/(.*\.(gif|jpg|png))$ /static/$1 break;
    expires 5h;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~* ^/favicon.ico$ {
    root "%(app_root)s";
    rewrite ^/favicon.ico$ /static/favicon.ico break;
    expires 30d;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~ ^/(static)/ {
    root "%(app_root)s";
    expires 30d;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~ ^/(foo)/ {
    root "%(app_root)s";
    rewrite ^/(foo)/(.*)$ /bar/$2 break;
    expires 30d;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~ ^/(images)/ {
    root "%(app_root)s";
    rewrite ^/(images)/(.*)$ /static/images/$2 break;
    expires 30d;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~* ^/(index.html)$ {
    root "%(app_root)s";
    rewrite ^/(index.html)$ /$1 break;
    expires 30d;
}""" % {'app_root': os.getcwd()} in config)

            self.assertTrue("""location ~* /upload/ {
    # Pass altered request body to this location
    upload_pass @sample;

    # Store files to this directory
    # The directory is hashed, subdirectories 0 1 2 3 4 5 6 7 8 9
    # should exist
    upload_store /tmp/blobstore/sample 1;

    # Set permissions for uploaded files
    upload_store_access user:rw group:rw;

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

location @sample {
    fastcgi_pass localhost:8081;
    set $stripped_http_host $http_host;
    if ($http_host ~ ^(.*):([0-9]+)$) {
      set $stripped_http_host $1;
    }
    fastcgi_param CONTENT_LENGTH $content_length;
    fastcgi_param CONTENT_TYPE $content_type;
    fastcgi_param PATH_INFO $fastcgi_script_name;
    fastcgi_param QUERY_STRING $query_string;
    fastcgi_param REMOTE_ADDR $remote_addr;
    fastcgi_param REQUEST_METHOD $request_method;
    fastcgi_param REQUEST_URI $request_uri;
    fastcgi_param SERVER_NAME $stripped_http_host;
    fastcgi_param SERVER_PORT $server_port;
    fastcgi_param SERVER_PROTOCOL $server_protocol;
    
    fastcgi_pass_header Authorization;

    # Increase the allowed size of the response.
    fastcgi_buffer_size 128k;
    fastcgi_buffers 4 256k;
    fastcgi_busy_buffers_size 256k;
    fastcgi_temp_file_write_size 256k;

    fastcgi_intercept_errors off;
}

location ~ ^/_ah/blobstore/sample/(.*) {
    root "/tmp/blobstore/sample";
    rewrite ^/_ah/blobstore/sample/(.*) /$1 break;
    expires 5d;
    internal;
}

location ~ ^/_ah/subscribe {
    push_subscriber long-poll;
    push_subscriber_concurrency broadcast;
    set $push_channel_id $arg_id;
    default_type text/plain;
}

location ~ {
    fastcgi_pass localhost:8081;
    set $stripped_http_host $http_host;
    if ($http_host ~ ^(.*):([0-9]+)$) {
      set $stripped_http_host $1;
    }
    fastcgi_param CONTENT_LENGTH $content_length;
    fastcgi_param CONTENT_TYPE $content_type;
    fastcgi_param PATH_INFO $fastcgi_script_name;
    fastcgi_param QUERY_STRING $query_string;
    fastcgi_param REMOTE_ADDR $remote_addr;
    fastcgi_param REQUEST_METHOD $request_method;
    fastcgi_param REQUEST_URI $request_uri;
    fastcgi_param SERVER_NAME $stripped_http_host;
    fastcgi_param SERVER_PORT $server_port;
    fastcgi_param SERVER_PROTOCOL $server_protocol;
    
    fastcgi_pass_header Authorization;

    # Increase the allowed size of the response.
    fastcgi_buffer_size 128k;
    fastcgi_buffers 4 256k;
    fastcgi_busy_buffers_size 256k;
    fastcgi_temp_file_write_size 256k;

    fastcgi_intercept_errors off;
}

error_page   500 502 503 504  /50x.html;
location = /50x.html {
    root "/tmp/html";
}

}
""" % {'app_root': os.getcwd()} in config)
            f.close()
        except Exception, e:
            print config
            raise e

    def testSupervisorConfig(self):
        """Writes a supervisord configuration file."""

        os.mkdir(os.path.join(os.getcwd(), 'etc'))
        paths = typhoonae.apptool.write_supervisor_conf(
            self.options, self.conf, self.app_root)
