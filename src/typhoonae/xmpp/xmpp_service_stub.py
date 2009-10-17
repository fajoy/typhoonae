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
"""XMPP service API stub using ejabberd."""

import logging
import os

from google.appengine.api import apiproxy_stub
from google.appengine.api import xmpp
from google.appengine.api.xmpp import xmpp_service_pb

import xmpp


class XmppServiceStub(apiproxy_stub.APIProxyStub):
  """Python only xmpp service stub.

  This stub does not use an XMPP network. It prints messages to the console
  instead of sending any stanzas.
  """

  def __init__(self, log=logging.info, host='localhost', service_name='xmpp'):
    """Initializer.

    Args:
      log: A logger, used for dependency injection.
      service_name: Service name expected for all calls.
    """
    super(XmppServiceStub, self).__init__(service_name)
    self.log = log
    self.host = host

  def _Dynamic_GetPresence(self, request, response):
    """Implementation of XmppService::GetPresence.

    Returns online if the first character of the JID comes before 'm' in the
    alphabet, otherwise returns offline.

    Args:
      request: A PresenceRequest.
      response: A PresenceResponse.
    """
    jid = request.jid()
    self._GetFrom(request.from_jid())
    if jid[0] < 'm':
      response.set_is_available(True)
    else:
      response.set_is_available(False)

  def _Dynamic_SendMessage(self, request, response):
    """Implementation of XmppService::SendMessage.

    Args:
      request: An XmppMessageRequest.
      response: An XmppMessageResponse .
    """

    jid = xmpp.protocol.JID(self._GetFrom(request.from_jid()))
    client = xmpp.Client(jid.getDomain(), debug=[])
    client.connect()
    client.auth(jid.getNode(), 'demo')

    for to_jid in request.jid_list():
        client.send(xmpp.protocol.Message(to_jid, request.body()))
        response.add_status(xmpp_service_pb.XmppMessageResponse.NO_ERROR)

    client.disconnect()

  def _Dynamic_SendInvite(self, request, response):
    """Implementation of XmppService::SendInvite.

    Args:
      request: An XmppInviteRequest.
      response: An XmppInviteResponse .
    """
    from_jid = self._GetFrom(request.from_jid())
    self.log('Sending an XMPP Invite:')
    self.log('    From:')
    self.log('       ' + from_jid)
    self.log('    To: ' + request.jid())

  def _GetFrom(self, requested):
    """Validates that the from JID is valid.

    Args:
      requested: The requested from JID.

    Returns:
      string, The from JID.

    Raises:
      xmpp.InvalidJidError if the requested JID is invalid.
    """

    appid = os.environ['APPLICATION_ID']

    return '%s@%s' % (appid, self.host)
