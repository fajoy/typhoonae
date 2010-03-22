# -*- coding: utf-8 -*-
#
# Copyright 2010 Tobias Rodäbel
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
"""Custom login/logout handler."""

import Cookie
import google.appengine.ext.webapp
import os
import re
import typhoonae.handlers.login
import wsgiref.handlers


class LoginRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Simple login handler."""

    def get(self):
        """Sets the authentication cookie."""

        next_url = self.request.get('continue', '/')

        if os.environ.get('HTTP_AUTHORIZATION', False):
            self.redirect(next_url)
            return

        self.response.headers.add_header(
            'Set-Cookie',
            typhoonae.handlers.login.getSetCookieHeaderValue(
                'admin@typhoonae', admin=True)
        )

        self.response.set_status(401)
        self.response.headers.add_header('Content-Type', 'text/html')
        self.response.out.write(
            '<html><body>You\'re now logged in as admin@typhoonae! '
            'This is a custom login handler.<br><a href="%s">Continue</a>'
            '</body></html>' % next_url)


class LogoutRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Simple logout handler."""

    def get(self):
        """Removes the authentication cookie."""

        cookie_name = typhoonae.handlers.login.getCookieName()
        c = Cookie.SimpleCookie()
        c[cookie_name] = ''
        c[cookie_name]['path'] = '/'
        c[cookie_name]['max-age'] = '0'
        h = re.compile('^Set-Cookie: ').sub('', c.output(), count=1)
        self.response.headers.add_header('Set-Cookie', str(h))
        self.redirect('/')


app = google.appengine.ext.webapp.WSGIApplication([
    ('/_ah/login', LoginRequestHandler),
    ('/_ah/logout', LogoutRequestHandler),
], debug=True)


def main():
    wsgiref.handlers.CGIHandler().run(app)


if __name__ == '__main__':
    main()
