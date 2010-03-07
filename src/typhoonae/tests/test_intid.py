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
"""Unit tests for the intid server."""

import threading
import time
import typhoonae.intid
import unittest


class TestClient(threading.Thread):
    """Simple test client implementation."""

    def __init__(self, accum):
        super(TestClient, self).__init__()
        self.client = typhoonae.intid.IntidClient()
        self.accum = accum

    def run(self):
        """Fetches integer IDs."""

        for i in range(100):
            self.accum.append(self.client.get())

    def close(self):
        self.client.close()


class IntidTestCase(unittest.TestCase):
    """Testing the typhoonae intid server."""

    def testGetIntIDs(self):
        """Get some integer IDs."""

        def issorted(L):
            """"Tests if a List is sorted."""

            for i in range(0, len(L)-1):
                if cmp(L[i],L[i+1]) == -1: continue
                else: return False
            return True

        client = typhoonae.intid.IntidClient()
        ids = []
        for i in range(10):
            ids.append(client.get())
        client.close()
        assert len(ids) == 10
        assert issorted(ids)

    def testConcurrentClients(self):
        """Sets up concurrent intid clients."""

        # These two lists are our accumulators
        ids1 = []
        ids2 = []

        # Set up two concurrent clients and start them
        c1 = TestClient(ids1)
        c2 = TestClient(ids2)
        c1.start()
        c2.start()

        # Wait for two seconds
        time.sleep(2)

        # Disconnect our test clients
        c1.close()
        c2.close()

        # Check whether we obtained the same id twice
        assert set(ids1).intersection(set(ids2)) == set([])

    def testSimpleClient(self):
        """Tries to set up a simple intid client."""

        client = typhoonae.intid.IntidClient()
        client.close()

        self.assertRaises(
            RuntimeError, typhoonae.intid.IntidClient, port=9876)


if __name__ == "__main__":
    unittest.main()
