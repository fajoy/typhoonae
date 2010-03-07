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
"""Simple intid server implementation."""

import logging
import os
import shelve
import socket
import threading

logging.basicConfig(
    format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] %(message)s',
    level=logging.INFO)

lock = threading.Lock()


class IntidClient(object):
    """Client for the integer ID server."""

    def __init__(self, host='localhost', port=9009):
        self.s = None
        for res in socket.getaddrinfo(
            host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):

            af, socktype, proto, canonname, sa = res
            try:
                self.s = socket.socket(af, socktype, proto)
            except socket.error, msg:
                self.s = None
                continue
            try:
                self.s.connect(sa)
            except socket.error, msg:
                self.s.close()
                self.s = None
                continue
            break

        if self.s is None:
            logging.error('no connection to intid server')
            raise RuntimeError

        self.s.send('con')
        r = self.s.recv(3)
        if r == 'ack':
            logging.info('connected to intid server')

    def get(self):
        self.s.send('int')
        data = self.s.recv(64)
        return int(data)

    def close(self):
        self.s.close()


class Worker(threading.Thread):
    """The worker thread."""

    def __init__(self, sock, db, num):
        super(Worker, self).__init__()
        self.socket = sock
        self.db = db
        self.num = num

    def run(self):
        while 1:
            data = self.socket.recv(3)
            if data == 'int':
                lock.acquire()
                i = self.db['int'] = self.db['int'] + 1
                self.db.sync()
                lock.release()
                self.socket.send(str(i))
            elif data == 'con':
                self.socket.send('ack')
            else:
                self.socket.close()
                logging.info("client %i disconnected" % self.num)
                break


def main():
    """The main function."""

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 9009))
    server_socket.listen(10)

    db = shelve.open(
        os.path.join(os.environ['TMPDIR'], 'intid'), writeback=True)

    if not 'int' in db:
        db['int'] = 0

    logging.info("server starting")

    client_num = 0

    try:
        while 1:
            socketfd, address = server_socket.accept()
            client_num += 1
            logging.info("client %i %s connected" % (client_num, address))
            t = Worker(socketfd, db, client_num)
            t.start()
    except KeyboardInterrupt:
        db.close()
        server_socket.close()
        logging.info("server stopping")
