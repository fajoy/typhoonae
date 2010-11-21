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
"""Task queue API proxy stub."""

from amqplib import client_0_8 as amqp
import base64
import google.appengine.api.api_base_pb
import google.appengine.api.apiproxy_stub
import google.appengine.api.apiproxy_stub_map
import google.appengine.api.taskqueue.taskqueue_service_pb
import google.appengine.api.taskqueue.taskqueue_stub
import google.appengine.api.urlfetch
import google.appengine.runtime.apiproxy_errors
import logging
import os
import simplejson
import socket
import typhoonae.taskqueue


MAX_CONNECTION_RETRIES = 1


class TaskQueueServiceStub(google.appengine.api.apiproxy_stub.APIProxyStub):
    """Task queue service stub."""

    pyaml = google.appengine.api.taskqueue.taskqueue_stub._ParseQueueYaml

    def __init__(
            self,
            internal_address,
            service_name='taskqueue',
            root_path=None):
        """Initialize the Task Queue API proxy stub.

        Args:
            internal_address: The internal host and port of where the
                appserver lives.
            service_name: Service name expected for all calls.
            root_path: The app's root directory.
        """
        super(TaskQueueServiceStub, self).__init__(service_name)

        (self._internal_host, self._internal_port) = internal_address.split(':')

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
        bulk_request = (google.appengine.api.taskqueue.
                        taskqueue_service_pb.TaskQueueBulkAddRequest())
        bulk_response = (google.appengine.api.taskqueue.
                         taskqueue_service_pb.TaskQueueBulkAddResponse())

        bulk_request.add_add_request().CopyFrom(request)
        self._Dynamic_BulkAdd(bulk_request, bulk_response)

        assert bulk_response.taskresult_size() == 1
        result = bulk_response.taskresult(0).result()

        OK = (google.appengine.api.taskqueue.
              taskqueue_service_pb.TaskQueueServiceError.OK)
        if result != OK:
            raise google.appengine.runtime.apiproxy_errors.ApplicationError(
                result)
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
                google.appengine.api.taskqueue.taskqueue_service_pb.
                TaskQueueServiceError.UNKNOWN_QUEUE)

        if request.add_request(0).has_transaction():
            self._TransactionalBulkAdd(request)

        for add_request in request.add_request_list():
            if not request.add_request(0).has_transaction():
                content_type = 'text/plain'
                for h in add_request.header_list():
                    if h.key() == 'content-type':
                        content_type = h.value()

                task_dict = dict(
                    content_type=content_type,
                    eta=add_request.eta_usec()/1000000,
                    host=self._internal_host,
                    method=add_request.method(),
                    name=add_request.task_name(),
                    payload=base64.b64encode(add_request.body()),
                    port=self._internal_port,
                    queue=add_request.queue_name(),
                    try_count=0,
                    url=add_request.url(),
                )

                msg = amqp.Message(simplejson.dumps(task_dict))
                msg.properties["delivery_mode"] = 2
                msg.properties["task_name"] = add_request.task_name()

                self._PublishMessage(msg, task_dict['eta'])

            task_result = response.add_taskresult()

    def _TransactionalBulkAdd(self, request):
        """Uses datastore.AddActions to associate tasks with a transaction.

        Args:
            request: The taskqueue_service_pb.TaskQueueBulkAddRequest
                containing the tasks to add. N.B. all tasks in the request
                have been validated and assigned unique names.
        """
        try:
            google.appengine.api.apiproxy_stub_map.MakeSyncCall(
                'datastore_v3', 'AddActions', request,
                google.appengine.api.api_base_pb.VoidProto())
        except google.appengine.runtime.apiproxy_errors.ApplicationError, e:
            raise google.appengine.runtime.apiproxy_errors.ApplicationError(
                e.application_error +
                google.appengine.api.taskqueue.taskqueue_service_pb.
                TaskQueueServiceError.DATASTORE_ERROR,
                e.error_detail)

    def GetQueues(self):
        """Gets all the applications's queues.

        Returns:
            A list of dictionaries, where each dictionary contains one queue's
            attributes.
        """
        queues = []

        return queues
