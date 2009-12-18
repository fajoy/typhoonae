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
"""Demo application."""

import datetime
import django.utils.simplejson
import google.appengine.api.capabilities
import google.appengine.api.labs.taskqueue
import google.appengine.api.memcache
import google.appengine.api.users
import google.appengine.api.xmpp
import google.appengine.ext.db
import google.appengine.ext.webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
import logging
import os
import random
import urllib

NUM_SHARDS = 20


class SimpleCounterShard(google.appengine.ext.db.Model):
    """Shards for the counter"""

    count = google.appengine.ext.db.IntegerProperty(required=True, default=0)   


class LogEntry(google.appengine.ext.db.Model):
    """Log entry model."""

    ip = google.appengine.ext.db.StringProperty()   


class Note(google.appengine.ext.db.Model):
    """Very simple note model."""

    body = google.appengine.ext.db.StringProperty()
    date = google.appengine.ext.db.DateTimeProperty(auto_now=True)


def increment():
    """Increments the value for a given sharded counter."""

    def transaction():
        index = random.randint(0, NUM_SHARDS - 1)
        shard_name = "shard" + str(index)
        counter = SimpleCounterShard.get_by_key_name(shard_name)
        if counter is None:
            counter = SimpleCounterShard(key_name=shard_name)
        counter.count += 1
        counter.put()

    google.appengine.ext.db.run_in_transaction(transaction)


def get_count():
    """Retrieves the value for a given sharded counter."""

    total = 0
    for counter in SimpleCounterShard.all():
        total += counter.count
    return total


def get_notes():
    """Returns a list of notes."""

    memcache_enabled = (google.appengine.api.capabilities.
                        CapabilitySet('memcache').is_enabled())

    if memcache_enabled:
        notes = google.appengine.api.memcache.get("notes")
        if notes is not None:
            return notes

    query = google.appengine.ext.db.GqlQuery(
        "SELECT * FROM Note ORDER BY date DESC LIMIT 500")

    notes = ['(%s) %s - %s' %
             (note.key().id(), note.date, note.body) for note in query]

    if memcache_enabled:
        if not google.appengine.api.memcache.add("notes", notes, 10):
            logging.error("Writing to memcache failed")

    return notes


def get_login_or_logout(user):
    """Returns either login or logout button."""

    form = ('<form action="%(action)s" method="GET">'
            '<input type="submit" value="%(label)s">'
            '</form>')

    if user:
        vars = dict(action=google.appengine.api.users.create_logout_url('/'),
                    label='Logout')
    else:
        vars = dict(action=google.appengine.api.users.create_login_url('/'),
                    label='Login')

    return form % vars 


class DemoRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Simple request handler."""

    def get(self):
        """Handles get."""

        user = google.appengine.api.users.get_current_user()
        login_or_logout = get_login_or_logout(user)

        increment()
        count = get_count()
        notes = get_notes()
        now = datetime.datetime.now()
        eta = now + datetime.timedelta(seconds=5)
        google.appengine.api.labs.taskqueue.add(url='/makenote',
                                                eta=eta,
                                                payload="%i delayed" % count)
        vars = dict(
            count=count,
            env=os.environ,
            login_or_logout=login_or_logout,
            notes=notes,
            user=user)
        output = google.appengine.ext.webapp.template.render('index.html', vars)
        self.response.out.write(output)


class CountRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Request handler for counting log entries."""

    def get(self):
        """Returns just the current counter value."""

        query = LogEntry.all()
        count = query.count()
        self.response.headers.add_header("Content-Type", "text/plain")
        self.response.out.write('Count: %i' % count)


class LogRequestHandler(google.appengine.ext.webapp.RequestHandler):
    """Request handler for making a log entry."""

    def get(self):
        """Makes a log entry."""

        entry = LogEntry(ip='0')
        entry.put()
        self.response.headers.add_header("Content-Type", "text/plain")
        self.response.out.write('ok')


class NoteWorker(google.appengine.ext.webapp.RequestHandler):
    """Stores notes."""

    def post(self):
        """Handles post."""

        note = Note(body=self.request.body)
        note.put()

    def get(self):
        """Handles get."""

        last_key = self.request.get('last_key')

        query = google.appengine.ext.db.GqlQuery(
            "SELECT * FROM Note ORDER BY date DESC LIMIT 1")

        result = query.get()

        if result != None:
            key = str(result.key().id_or_name())
        else:
            key = None

        if key == None or key == last_key:
            self.response.set_status(304)
            return

        self.response.headers.add_header(
            "Content-Type", "'application/javascript; charset=utf8'")

        data = {'key': key, 'message': result.body}

        self.response.out.write(django.utils.simplejson.dumps(data))


class InviteHandler(google.appengine.ext.webapp.RequestHandler):
    """Invites recipient to a XMPP chat."""

    def post(self):
        """Handles post."""

        recipient = self.request.get('recipient')
        if google.appengine.api.xmpp.get_presence(recipient):
            google.appengine.api.xmpp.send_invite(recipient)

        self.redirect('/')


class XMPPHandler(google.appengine.ext.webapp.RequestHandler):
    """Handles XMPP messages."""

    def post(self):
        """Handles post."""

        message = google.appengine.api.xmpp.Message(self.request.POST)

        logging.info("Received XMPP message: %s" % message.body)

        if message.body[0:5].lower() == 'hello':
             message.reply("Hi, %s!" % message.sender)

        note = Note()
        note.body = message.body
        note.put()


app = google.appengine.ext.webapp.WSGIApplication([
    ('/', DemoRequestHandler),
    ('/count', CountRequestHandler),
    ('/log', LogRequestHandler),
    ('/makenote', NoteWorker),
    ('/getnote', NoteWorker),
    ('/invite', InviteHandler),
    ('/_ah/xmpp/message/chat/', XMPPHandler),
], debug=True)


def main():
    """The main function."""

    google.appengine.ext.webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
