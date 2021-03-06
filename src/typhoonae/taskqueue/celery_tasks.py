# -*- coding: utf-8 -*-
#
# Copyright 2010, 2011 Joaquin Cuenca Abela, Tobias Rodäbel
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
"""Inititalizes a task worker for the Task Queue Celery backend."""

from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_init
from celery.task.base import Task
from google.appengine.api import queueinfo

import base64
import datetime
import logging
import os
import re
import urllib2


def _ParseQueueYaml(root_path):
    """Loads the queue.yaml file and parses it.

    Args:
        root_path: Directory containing queue.yaml. Not used.

    Returns:
        None if queue.yaml doesn't exist, otherwise a queueinfo.QueueEntry
        object populated from the queue.yaml.
    """
    if root_path is None:
        return None
    for queueyaml in ('queue.yaml', 'queue.yml'):
        try:
            fh = open(os.path.join(root_path, queueyaml), 'r')
        except IOError:
            continue
        try:
            queue_info = queueinfo.LoadSingleQueue(fh)
            return queue_info
        finally:
            fh.close()
    return None


class RequestWithMethod(urllib2.Request):
    def __init__(self, method, *args, **kwargs):
        self._method = method
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method


def get_short_task_description(name=None, url=None, **kw):
    return "%s (%s)" % (name, url)


def handle_task(task, **task_args):
    """Decodes received message and processes task."""

    logger = task.get_logger()
    headers = {'Content-Type': task_args['content_type'],
               'X-AppEngine-TaskName': task_args['name'],
               'X-AppEngine-TaskRetryCount': str(task_args['try_count']),
               'X-AppEngine-QueueName': task_args['queue']}

    # TODO: We run this query as an HTTP request, which has a significant
    # overhead (the query needs to go to nginx, and from there to the python
    # server). It will be more efficient to run directly the associated code
    # here.
    # TODO: We are not checking if the HTTP request died with a retryable
    # exception.
    req = RequestWithMethod(
        method=task_args['method'],
        url='http://%(host)s:%(port)s%(url)s' % task_args,
        data=base64.b64decode(task_args['payload']),
        headers=headers
    )
    task_description = get_short_task_description(**task_args)
    try:
        res = urllib2.urlopen(req)
    except urllib2.URLError, err_obj:
        reason = getattr(err_obj, 'reason', err_obj)
        logger.error("failed task %s %s", task_description, reason)
        task.retry(kwargs=task_args, exc=err_obj)
    except SoftTimeLimitExceeded, err_obj:
        logger.error("failed task %s (time limit exceeded)" % task_description)
        task.retry(kwargs=task_args, exc=err_obj)
    finally:
        logger.info("finished with task %s" % task_description)


def get_task_class_name(gae_queue_name):
    return re.sub('[^a-zA-Z_]', '', gae_queue_name.replace('-', '_')) + '_Task'


def create_task_queue(queue_name, rate_qps, bucket_size=5):
    """Create a task queue.

    We create dynamically a new class inherited from celery Task and we setup
    the desired rate limit. Unfortunately the vocabulary is quite confusing,
    an AppEngine Queue becomes, in celery parlance, a Task class.

    Args:
        queue_name: The name of the queue that we want to create.
        rate_qps: The rate in queries per second for this queue. -1 for
            unbounded rate limit. 0 for stopping this queue.
        bucket_size: Ignored, it's still not supported by celery.
    """
    task_class_name = get_task_class_name(queue_name)
    if rate_qps < 999999:
        rate_limit = "%d/h" % int(rate_qps * 3600)
    else:
        rate_limit = None

    # TODO: We ignore the bucket_size parameter
    return type(task_class_name, (Task,), dict(
         routing_key=queue_name,
         name=task_class_name,
         rate_limit=rate_limit,
         run=handle_task,
         ignore_result=True,
         send_error_emails=False,
         __module__=create_task_queue.__module__))


def create_task_queues_from_yaml(app_root=None):
    if app_root:
        queue_info = _ParseQueueYaml(app_root)
    else:
        queue_info = None
    tasks = {}
    if queue_info and queue_info.queue:
        for entry in queue_info.queue:
            tasks[entry.name] = create_task_queue(
                entry.name, queueinfo.ParseRate(entry.rate),
                entry.bucket_size)
    else:
        tasks['default'] = create_task_queue('default', 5)
    return tasks


def load_queue_config(signal, sender=None, **kwargs):
    if 'APP_ROOT' not in os.environ:
        logging.error("application root unknown")
    create_task_queues_from_yaml(os.environ.get('APP_ROOT'))


worker_init.connect(load_queue_config)
