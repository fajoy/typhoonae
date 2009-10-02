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
"""Task worker implementation."""

from __future__ import with_statement
from amqplib import client_0_8 as amqp
import logging
import os
import signal
import simplejson
import socket
import sys
import typhoonae.taskqueue
import urllib2

MAX_TRY_COUNT = 10
MAX_TIME_LIMIT = 30


class TimeLimitExceededError(Exception):
    """Exception to be raised when a time limit is exceeded."""

    def __str__(self):
        return "Maximum time limit exceeded"


class ExecutionTimeLimit(object):
    """Context manager for limited code execution.

    Raises an exception when maximum execution time is reached.
    """

    def __init__(self, seconds=MAX_TIME_LIMIT):
        """Initializes the context manager.

        Args:
            seconds: integer number of seconds before sending an alarm.
        """

        self.seconds = seconds

    def __enter__(self):
        """Enters the runtime context."""

        signal.signal(signal.SIGALRM, self.handle)
        signal.alarm(self.seconds)

    def __exit__(self, typ, value, trbck):
        """Exits the runtime context."""

        signal.alarm(0)

    def handle(self, signum, frame):
        """Handles signal."""

        raise TimeLimitExceededError


def handle_task(msg):
    """Decodes received message and processes task."""

    task = simplejson.loads(msg.body)

    if typhoonae.taskqueue.is_deferred_eta(task['eta']):
        return False

    req = urllib2.Request(
        url='http://%(host)s:%(port)s%(url)s' % task,
        data=task['payload'],
        headers={'Content-Type': 'text/plain'}
    )

    try:
        with ExecutionTimeLimit():
            res = urllib2.urlopen(req)
    except urllib2.URLError, err_obj:
        reason = getattr(err_obj, 'reason', err_obj)
        logging.error("failed task %s %s" % (task, reason))
        return False
    except TimeLimitExceededError:
        logging.error("failed task %s (time limit exceeded)" % task)
        return False

    return True


def main(queue="tasks", exchange="immediate", routing_key="normal_worker"):
    """The main function."""

    logging.basicConfig(
        format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)s] '
               '%(message)s',
        level=logging.DEBUG)

    try:
        conn = amqp.Connection(
            host="localhost:5672",
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
        if not handle_task(msg):
            task = simplejson.loads(msg.body)
            task_dict = dict(task)

            if task_dict["try_count"] < MAX_TRY_COUNT:
                task_dict["try_count"] = task["try_count"] + 1
                task_dict["eta"] = typhoonae.taskqueue.get_new_eta_usec(
                    task_dict["try_count"])

                new_msg = amqp.Message(simplejson.dumps(task_dict))
                new_msg.properties["delivery_mode"] = 2
                new_msg.properties["task_name"] = task['name']

                chan.basic_publish(
                    new_msg, exchange="deferred", routing_key="deferred_worker")

        chan.basic_ack(msg.delivery_tag)

    _consumer_tag = "consumer.%i" % os.getpid()

    chan.basic_consume(
        queue=queue,
        no_ack=False,
        callback=recv_callback,
        consumer_tag=_consumer_tag)

    try:
        while True:
            chan.wait()
    finally:
        chan.basic_cancel(_consumer_tag)

        chan.close()
        conn.close()


if __name__ == "__main__":
    main()
