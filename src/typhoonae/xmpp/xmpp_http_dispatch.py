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
"""Simple XMPP/HTTP dispatcher implementation."""

import cookielib
import logging
import mimetools
import optparse
import sys
import time
import urllib2
import xmpp

DESCRIPTION = ("XMPP/HTTP dispatcher.")
USAGE = "usage: %prog [options]"

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
urllib2.install_opener(opener)


def post_multipart(url, fields):
    """Posts multipart form data fields.

    Args:
        url: Post multipart form data to this URL.
        fields: A list of tuples of the form [(fieldname, value), ...].
    """

    content_type, body = encode_multipart_formdata(fields)

    headers = {'Content-Type': content_type,
               'Content-Length': str(len(body))}

    r = urllib2.Request(url, body, headers)

    return urllib2.urlopen(r).read()


def encode_multipart_formdata(fields):
    """Encodes multipart form data.

    Returns content type and body.
    """

    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    buffer = []

    for (key, value) in fields:
        buffer.append('--%s' % BOUNDARY)
        buffer.append('Content-Disposition: form-data; name="%s"' % key)
        buffer.append('')
        buffer.append(value)

    buffer.append('--%s--' % BOUNDARY)
    buffer.append('')
    logging.debug(str(buffer))
    body = CRLF.join(buffer)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body


class Dispatcher(object):
    """The XMPP/HTTP dispatcher class."""

    def __init__(self, address):
        """Initializes the dispatcher."""

        self.address = address

    def __call__(self, conn, message):
        """The dispatcher function."""

        logging.debug(str(message))
        post_multipart('http://%s/_ah/xmpp/message/chat/' % self.address,
                       [('body', message.getBody()),
                        ('from', str(message.getFrom())),
                        ('stanza', str(message)),
                        ('to', str(message.getTo()))])


def loop(conn):
    """The main loop."""

    def process():
        try:
            conn.Process(1)
        except KeyboardInterrupt:
            return 0
        return 1

    while process():
        pass


def main():
    """The main function."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address", metavar="HOST:PORT",
                  help="the application host and port",
                  default="localhost:8080")

    op.add_option("-j", "--jid", dest="jid", metavar="JID",
                  help="use this Jabber ID", default="demo@localhost")

    op.add_option("-p", "--password", dest="password", metavar="PASSWORD",
                  help="use this password", default="demo")

    (options, args) = op.parse_args()

    logging.basicConfig(
        format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] '
               '%(message)s',
        level=logging.DEBUG)

    jid = xmpp.JID(options.jid)
    user, server, password = jid.getNode(), jid.getDomain(), options.password

    client = xmpp.Client(server, debug=[])

    for i in range(5):
        conn = client.connect()
        if conn:
            break
        logging.warning("Retrying to connect to server '%s'" % server)
        # Retrying after 5 seconds
        time.sleep(5)

    if not conn:
        logging.error("Unable to connect to server '%s'" % server)
        sys.exit(2)

    if conn <> 'tls':
        logging.warning("Unable to estabilish secure connection - TLS failed")

    auth = client.auth(user, password)

    if not auth:
        logging.error("Authentication on %s failed" % server)
        sys.exit(1)

    if auth <> 'sasl':
        logging.warning("SASL authentication on %s failed" % server)

    client.RegisterHandler('message', Dispatcher(options.address))
    client.sendInitPresence()

    loop(client)


if __name__ == "__main__":
    main()
