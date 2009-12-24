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
"""Worker implementation for deferred tasks."""

from amqplib import client_0_8 as amqp
import logging
import optparse
import os
import simplejson
import socket
import sys
import threading
import typhoonae.taskqueue
import urllib2

DESCRIPTION = ("AMQP client deferred tasks.")
USAGE = "usage: %prog [options]"


class RecoverLoop(threading.Thread):
    """Provides a recover loop/timer."""

    def __init__(self, interval, callback, args=[], kwargs={}):
        """Initializes recover loop."""

        threading.Thread.__init__(self)
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.finished = threading.Event()
        self.event = threading.Event()

    def stop(self):
        """Stops the loop."""

        self.finished.set()

    def run(self):
        """Implements a simple callback loop."""

        while not self.finished.isSet():
            self.event.wait(self.interval)
            if not self.finished.isSet() and not self.event.isSet():
                self.callback(*self.args, **self.kwargs)


def main(
    queue="deferred_tasks", exchange="deferred", routing_key="deferred_worker"):
    """The main function."""

    op = optparse.OptionParser(description=DESCRIPTION, usage=USAGE)

    op.add_option("--amqp_host", dest="amqp_host", metavar="ADDR",
                  help="use this AMQP host", default='localhost')

    (options, args) = op.parse_args()

    logging.basicConfig(
        format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] '
               '%(message)s',
        level=logging.DEBUG)

    try:
        conn = amqp.Connection(
            host="%s:5672" % options.amqp_host,
            userid="guest",
            password="guest",
            virtual_host="/",
            insist=False)
    except socket.error, err_obj:
        logging.error("queue server not reachable (reason: %s)" % err_obj)
        sys.exit(1)

    chan = conn.channel()

    chan.queue_declare(
        queue=queue, durable=True, exclusive=False, auto_delete=False)
    chan.exchange_declare(
        exchange=exchange, type="direct", durable=True, auto_delete=False)
    chan.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)

    def recv_callback(msg):
        task = simplejson.loads(msg.body)
        if not typhoonae.taskqueue.is_deferred_eta(task['eta']):
            # Move back to 'immediate' queue

            task_dict = dict(task)

            new_msg = amqp.Message(simplejson.dumps(task_dict))
            new_msg.properties["delivery_mode"] = 2
            new_msg.properties["task_name"] = task['name']

            chan.basic_publish(
                new_msg, exchange="immediate", routing_key="normal_worker")

            chan.basic_ack(msg.delivery_tag)

        return

    _consumer_tag = "consumer.%i" % os.getpid()

    chan.basic_consume(
        queue=queue,
        no_ack=False,
        callback=recv_callback,
        consumer_tag=_consumer_tag)

    loop = RecoverLoop(5, chan.basic_recover, [False])
    loop.start()

    try:
        while True:
            chan.wait()
    finally:
        chan.basic_cancel(_consumer_tag)
        loop.stop()
        chan.close()
        conn.close()


if __name__ == "__main__":
    main()
