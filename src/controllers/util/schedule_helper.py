#!/usr/bin/python2.7
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to handle API Query scheduling.

  SetApiQueryScheduleStatus: Start and stop scheduling for an API Query.
  ScheduleApiQuery: Attempt to add an API Query to the task queue.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import logging
import random

from controllers.util import co

from google.appengine.api import taskqueue


def SetApiQueryScheduleStatus(api_query, status=None):
  """Change the scheduling status of an API Query.

  Args:
    api_query: The API Query to change the scheduling status for.
    status: The status to change the API Query to. If status=None then the
            scheduling status of the API Query will be toggled.

  Returns:
    True if status change was successful, False otherwise.
  """
  if api_query:
    if status is None:
      api_query.is_scheduled = not api_query.is_scheduled
    elif status:
      api_query.is_scheduled = True
    else:
      api_query.is_scheduled = False

    api_query.put()
    return True
  return False


def ScheduleApiQuery(api_query, randomize=False, countdown=None):
  """Adds a task to refresh an API Query response.

  Args:
    api_query: the API Query entity to update
    randomize: A boolean to indicate whether to add a random amount of time to
               task countdown. Helpful to minimze occurrence of all tasks
               starting at the same time.
    countdown: How long to wait until executing the query
  """
  if (not api_query.in_queue
      and (api_query.is_scheduled and not api_query.is_abandoned
           and not api_query.is_error_limit_reached)):

    random_seconds = 0
    if randomize:
      random_seconds = random.randint(0, co.MAX_RANDOM_COUNTDOWN)

    if countdown is None:
      countdown = api_query.refresh_interval

    try:
      taskqueue.add(
          url=co.LINKS['admin_runtask'],
          countdown=countdown + random_seconds,
          params={
              'query_id': api_query.key(),
          })
      api_query.in_queue = True
      api_query.put()
    except taskqueue.Error as e:
      logging.error(
          'Error adding task to queue. API Query ID: {}. Error: {}'.format(
              api_query.key(), e))
