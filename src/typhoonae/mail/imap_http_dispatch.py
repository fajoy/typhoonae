# -*- coding: utf-8 -*-
#
# Copyright 2010 Ivan Vovnenko
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
"""Simple IMAP/HTTP dispatcher implementation."""

from imaplib2 import IMAP4, IMAP4_SSL
import datetime
import email
import logging
import optparse
import urllib2
import time

DESCRIPTION = ("IMAP/HTTP dispatcher.")
USAGE = "usage: %prog [options]"



def _create_imap_object(imap_host, imap_port, imap_ssl, imap_username, imap_password, imap_mailbox):
    cls = IMAP4
    if imap_ssl:
        cls = IMAP4_SSL
    imap = cls(imap_host, imap_port, debug=True)
    imap.login(imap_username, imap_password)
    imap.select(imap_mailbox, readonly=True)
    logging.debug("Created %s" % imap)
    return imap

def _release_imap_object(imap):
    try:
        imap.close()
    except Exception, e:
        logging.warn(e)
    try:
        imap.logout()
    except Exception, e:
        logging.warn(e)
    logging.debug("Released %s" % imap)

class Listener(object):
    
    def __init__(self, imap_host, imap_username, imap_password, callback, imap_port=None, imap_ssl=False, imap_mailbox='INBOX', idle_timeout=10):
        """Listener
        @param imap_host: hostname of the imap server
        @param: imap_username: imap username
        @param: imap_password: imap password
        @param callback: function, to be called when the message received
        @param imap_port: optional: imap server port. If omitted, default port is used, 143 or 994 id imap_ssl is True
        @param imap_ssl: optional, default - False.
        @param imap_mailbox: optional, default - 'INBOX'. Name of the imap mailbox to listen to new messages on 
        @param idle_timeout: optional: idle operation timeout, default value is 10 seconds
        """
        
        if imap_port == None:
            if imap_ssl:
                imap_port = 993
            else:
                imap_port = 143
        
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._imap_username = imap_username
        self._imap_password = imap_password
        self._imap_ssl = imap_ssl
        self._imap_mailbox = imap_mailbox
        
        self._callback = callback
        self._idle_timeout = idle_timeout
        
        logging.debug("Connecting to %s://%s:%d" % (("imaps" if self._imap_ssl else "imap"), self._imap_host, self._imap_port))
        
        self._imap = _create_imap_object(self._imap_host, self._imap_port, self._imap_ssl, self._imap_username, self._imap_password, self._imap_mailbox)
        
        self._seen_ids = set()
                
        # We going to check all the unseen messages since yesterday (worse case - server time zone is less then local) 
        self._search_criterion = '(UNSEEN SENTSINCE %s)' % (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        
        # reading messages that are already in the mailbox since yesterday (worth case time zone)
        try:
            status, response = self._imap.search(None, self._search_criterion)
            if status == 'OK':
                for id in response[0].split():
                    self._seen_ids.add(id)
                logging.info("Got %d old unseen messages" % len(self._seen_ids))
            else:
                logging.error("Could not perform initial search, exiting")
                raise "SEARCH returned %s != 'OK'" % status
        except:
            _release_imap_object(self._imap)
            raise
        
        
    def _wait_handle(self, timeout=None):
        try:
            status, response = self._imap.idle(timeout or self._idle_timeout);
            if status == 'OK':
                status, response = self._imap.search(None, self._search_criterion)
                if status == 'OK':
                    for id in response[0].split():
                        if id not in self._seen_ids:
                            logging.info("New mail arrived, %s" % id)
                            
                            def fetch_callback((response, id, error)):
                                status, response = response
                                if status == 'OK':
                                    logging.debug("Fetched message %s", id)
                                    
                                    eml = email.message_from_string(response[0][1])
                                            
                                    self._callback(eml)
                                else:
                                    logging.error('Error fetching message %s, will try later' % id)
                                    self._seen_ids.remove(id)
                                pass
                            
                            self._imap.fetch(id, '(RFC822)', callback=fetch_callback, cb_arg=id)                                
                            self._seen_ids.add(id)
                else:
                    logging.warn("SEARCH returned status=%s" % status)
            else:
                logging.warn("IDLE returned status=%s" % status)
        
        except (IMAP4.abort, IMAP4_SSL.abort), e:
            # On abort, won't try to fix, will just recreate imap
            logging.info("Got abort exception (%s), recreating imap object" % e)
            _release_imap_object(self._imap)
            self._imap = _create_imap_object(self._imap_host, self._imap_port, self._imap_ssl, self._imap_username, self._imap_password, self._imap_mailbox)
            
        except (IMAP4.error, IMAP4_SSL.error), e:
            logging.warn("imaplib2 error: %s" % e)    
            
            
    def _cleanup(self):
        logging.info("Releasing resources")        
        _release_imap_object(self._imap)   

        
    def serve_forever(self):
        logging.info("Starting IMAP Listener thread")
        try:
            while True: self._wait_handle()
        finally:
            self._cleanup()
            
                

def post_email_http(url, eml):
    """ This function posts email message to the url, the way Google App Engine would do it
    @param url: url to post message to
    @param eml: instance of email.message.Message
    """      

    email.message.Message
    string_eml = eml.as_string()
    req = urllib2.Request(url, string_eml, {"Content-Type" :"message/rfc822", "Content-Length":str(len(string_eml))})
    try:
        logging.debug("Posting email to %s" % url)
        res = urllib2.urlopen(req)
    except urllib2.URLError, err_obj:
        reason = getattr(err_obj, 'reason', err_obj)
        logging.error("Error posting message %s" % reason)
        return
    return res.read()      

class Dispatcher(object):
    
    def __init__(self, url):
        self._url = url
        
    def __call__(self, eml):
        _, email_address = email.utils.parseaddr(eml.get('to'))
        post_email_http("%s%s" % (self._url, email_address), eml)
                        
def main():
    """The main function."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("-a", "--address", dest="address", metavar="HOST:PORT",
                  help="the application host and port",
                  default="localhost:8770")

    op.add_option("--imap_host", dest="imap_host", metavar="IMAPHOST",
                  help="IMAP Server hostname", default="localhost")

    op.add_option("--imap_port", dest="imap_port", metavar="IMAPPORT",
                  help="IMAP Server port", type="int", default=143)
    
    op.add_option("--imap_ssl", dest="imap_ssl", metavar="IMAPSSL", action="store_true",
                  help="If it's IMAP SSL", default=False)
    
    op.add_option("-u", "--imap_user", dest="imap_user", metavar="IMAPUSER",
                  help="IMAP Server username", default="username@example.com")
    
    op.add_option("-p", "--imap_password", dest="imap_password", metavar="IMAPPASS",
                  help="IMAP Server password", default="secret")
    
    op.add_option("--imap_mailbox", dest="imap_mailbox", metavar="IMAPMBOX",
                  help="IMAP Server Mailbox", default="INBOX")
    

    (options, args) = op.parse_args()

    logging.basicConfig(
        format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] '
               '%(message)s',
        level=logging.DEBUG)
    dispatcher = Dispatcher("http://%s/_ah/mail/" % options.address)
    
    listener = Listener(options.imap_host, options.imap_user, options.imap_password, imap_port=int(options.imap_port), imap_ssl=options.imap_ssl, callback=dispatcher)
    
    try:            
        listener.serve_forever()
    except KeyboardInterrupt:
        # Don't make extra noise in logs
        pass
                          

if __name__ == "__main__":
    main()
