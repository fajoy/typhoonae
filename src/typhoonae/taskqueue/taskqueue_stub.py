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
"""Task queue API proxy stub."""

from amqplib import client_0_8 as amqp
import base64
import google.appengine.api.apiproxy_stub
import google.appengine.api.labs.taskqueue.taskqueue_service_pb
import google.appengine.api.labs.taskqueue.taskqueue_stub
import google.appengine.api.urlfetch
import google.appengine.runtime.apiproxy_errors
import logging
import os
import simplejson
import socket
import typhoonae.taskqueue


MAX_CONNECTION_RETRIES = 1

INTERNAL_SERVER_NAME = 'localhost'
INTERNAL_PORT = '8770'


class TaskQueueServiceStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """Task queue service stub."""

    pyaml = google.appengine.api.labs.taskqueue.taskqueue_stub._ParseQueueYaml

    def __init__(self, service_name='taskqueue', root_path=None):
        super(TaskQueueServiceStub, self).__init__(service_name)
        self.next_task_id = 1
        self.root_path = root_path
        self.conn = None
        self.channel = None

    def __del__(self):
        if self.channel is not None:
            self.channel.close()
        if self.conn is not None:
            self.conn.close()

    def connect(self):
        self.conn = amqp.Connection(
            host="localhost:5672",
            userid="guest",
            password="guest",
            virtual_host="/",
            insist=False)
        self.channel = self.conn.channel()

    def _ValidQueue(self, queue_name):
        if queue_name == 'default':
            return True
        queue_info = self.pyaml(self.root_path)
        if queue_info and queue_info.queue:
            for entry in queue_info.queue:
                if entry.name == queue_name:
                    return True
        return False

    def _Dynamic_Add(self, request, response):
        bulk_request = taskqueue_service_pb.TaskQueueBulkAddRequest()
        bulk_response = taskqueue_service_pb.TaskQueueBulkAddResponse()

        bulk_request.add_add_request().CopyFrom(request)
        self._Dynamic_BulkAdd(bulk_request, bulk_response)

        assert bulk_response.taskresult_size() == 1
        result = bulk_response.taskresult(0).result()

        if result != taskqueue_service_pb.TaskQueueServiceError.OK:
            raise apiproxy_errors.ApplicationError(result)
        elif bulk_response.taskresult(0).has_chosen_task_name():
            response.set_chosen_task_name(
                bulk_response.taskresult(0).chosen_task_name())

    def _PublishMessage(self, msg, eta):
        """Publish message.

        Args:
            msg: An amqp.Message instance.
            eta: Estimated time of task execution (UNIX time).
        """

        conn_retries = 0
        while conn_retries <= MAX_CONNECTION_RETRIES:
            try:
                if typhoonae.taskqueue.is_deferred_eta(eta):
                    self.channel.basic_publish(
                        msg, exchange="deferred", routing_key="deferred_worker")
                else:
                    self.channel.basic_publish(
                        msg, exchange="immediate", routing_key="normal_worker")
                break
            except Exception, err_obj:
                conn_retries += 1
                if conn_retries > MAX_CONNECTION_RETRIES:
                    raise Exception, err_obj
                if isinstance(err_obj, socket.error):
                    logging.error("queue server not reachable. retrying...")
                self.connect()

    def _Dynamic_BulkAdd(self, request, response):
        """Add many tasks to a queue using a single request.

        Args:
            request: The taskqueue_service_pb.TaskQueueBulkAddRequest. See
                taskqueue_service.proto.
            response: The taskqueue_service_pb.TaskQueueBulkAddResponse. See
                taskqueue_service.proto.
        """

        assert request.add_request_size(), 'empty requests not allowed'

        if not self._ValidQueue(request.add_request(0).queue_name()):
            raise google.appengine.runtime.apiproxy_errors.ApplicationError(
                google.appengine.api.labs.taskqueue.taskqueue_service_pb.
                TaskQueueServiceError.UNKNOWN_QUEUE)

        for add_request in request.add_request_list():

            content_type = 'text/plain'
            for h in add_request.header_list():
                if h.key() == 'content-type':
                    content_type = h.value()

            task_dict = dict(
                content_type=content_type,
                eta=add_request.eta_usec()/1000000,
                host=INTERNAL_SERVER_NAME,
                method=add_request.method(),
                name=add_request.task_name(),
                payload=base64.b64encode(add_request.body()),
                port=INTERNAL_PORT,
                queue=add_request.queue_name(),
                try_count=0,
                url=add_request.url(),
            )

            msg = amqp.Message(simplejson.dumps(task_dict))
            msg.properties["delivery_mode"] = 2
            msg.properties["task_name"] = add_request.task_name()

            self._PublishMessage(msg, task_dict['eta'])

            task_result = response.add_taskresult()

    def GetQueues(self):
        """Gets all the applications's queues.

        Returns:
            A list of dictionaries, where each dictionary contains one queue's
            attributes.
        """
        queues = []

        return queues
