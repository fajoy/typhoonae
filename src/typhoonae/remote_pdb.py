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
"""Simple Remote Python Debugger."""

import pdb
import socket
import sys


class RemoteDebugger(pdb.Pdb):
    """Provides a remote Python debugger.

    Sample Usage:
    >>> debugger = RemoteDebugger()
    >>> debugger.set_trace()

    And then connect via telnet <hostname> 10987.
    """

    def __init__(self, port=10987):
        """Constructor.

        Args:
        port: The port number to use.
        """
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((socket.gethostname(), port))
        self.sock.listen(1)

        (client, address) = self.sock.accept()

        fp = client.makefile('rw')

        pdb.Pdb.__init__(self, completekey='tab', stdin=fp, stdout=fp)

        sys.stdout = sys.stdin = fp

    def do_continue(self, unused_arg):
        sys.stdout = self.old_stdout
        sys.stdin = self.old_stdin
        self.sock.close()
        self.set_continue()
        return 1

    do_c = do_cont = do_continue
