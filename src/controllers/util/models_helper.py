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

"""Utility functions for DB Models.

  FormatTimedelta: Converts a time delta to nicely formatted string.
  GetApiQueryLastRequest: Get timestamp of last request for an API Query.
  GetApiQueryRequestCount: Get request count of API Query.
  GetLastRequestTimedelta: Get the time since last request for query.
  GetModifiedTimedelta: Get the time since last refresh of API Query.
  IsApiQueryAbandoned: Checks if an API Query is abandoned.
  IsErrorLimitReached: Checks if the API Query has reached the error limit.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime

from controllers.util import co
from controllers.util import request_counter_shard
from controllers.util import request_timestamp_shard

from google.appengine.api import memcache


def FormatTimedelta(time_delta):
  """Formats a time delta into a sentence.

  Args:
    time_delta: A Timedelta object to format.

  Returns:
    A string containing a nicely formatted time delta in the form of
    "HH hours, MM minutes, ss seconds ago".
  """
  seconds = int(time_delta.total_seconds())
  days, time_left = divmod(seconds, 86400)  # 86400: seconds in a day = 24*60*60
  hours, time_left = divmod(time_left, 3600)  # 3600: seconds in an hour = 60*60
  minutes, seconds = divmod(time_left, 60)  # 60: seconds in a minute

  pretty_label = '%ss ago' % seconds
  if days > 0:
    pretty_label = '%sd, %sh, %sm ago' % (days, hours, minutes)
  elif hours > 0:
    pretty_label = '%sh, %sm ago' % (hours, minutes)
  elif minutes > 0:
    pretty_label = '%sm, %ss ago' % (minutes, seconds)
  return pretty_label


def GetApiQueryLastRequest(query_id):
  """Returns the timestamp of the last request.

  Args:
    query_id: The ID of the Query for which to retrieve the last request time.

  Returns:
    A DateTime object specifying the time when the API Query was last
    requested using the external public endpoint.
  """
  if query_id:
    request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
    request_timestamp = memcache.get(request_timestamp_key)
    if not request_timestamp:
      request_timestamp = request_timestamp_shard.GetTimestamp(
          request_timestamp_key)
    return request_timestamp
  return None


def GetApiQueryRequestCount(query_id):
  """Returns the request count for an API Query.

  Args:
    query_id: The ID of the Query from which to retrieve the request count.

  Returns:
    An integer representing the number of times the API Query has been
    requested using the external public endpoint.
  """
  request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
  request_count = memcache.get(request_counter_key)
  if not request_count:
    request_count = request_counter_shard.GetCount(request_counter_key)
  return request_count


def GetLastRequestTimedelta(api_query, from_time=None):
  """Returns how long since the API Query response was last requested.

  Args:
    api_query: The API Query from which to retrieve the last request timedelta.
    from_time: A DateTime object representing the start time to calculate the
               timedelta from.

  Returns:
    A string that describes how long since the API Query response was last
    requested in the form of "HH hours, MM minutes, ss seconds ago" or None
    if the API Query response has never been requested.
  """
  if not from_time:
    from_time = datetime.utcnow()

  if api_query.last_request:
    time_delta = from_time - api_query.last_request
    return FormatTimedelta(time_delta)
  return None


def GetModifiedTimedelta(api_query, from_time=None):
  """Returns how long since the API Query was updated.

  Args:
    api_query: The API Query from which to retrieve the modified timedelta.
    from_time: A DateTime object representing the start time to calculate the
               timedelta from.

  Returns:
    A string that describes how long since the API Query has been updated in
    the form of "HH hours, MM minutes, ss seconds ago" or None if the API Query
    has never been updated.
  """
  if not from_time:
    from_time = datetime.utcnow()

  api_query_response = api_query.api_query_responses.get()
  if api_query_response:
    time_delta = from_time - api_query_response.modified
    return FormatTimedelta(time_delta)
  return None


def IsApiQueryAbandoned(api_query):
  """Determines whether the API Query is considered abandoned.

  When an API Query response has not been requested for a period
  of time (configurable) then it is considered abandoned.

  If a query has never been requested then the modified date of the query
  will be used if it exists. If there is no modified date the the API query
  then the if an API Query Response exists then
  it wil be considered abandoned. This is to prevent the case where a query
  that is never requested continues to get scheduled.

  Args:
    api_query: THe API Query to check if abandonded.

  Returns:
    A boolean indicating if the query is considered abandoned.
  """
  if api_query.last_request:
    last_request_age = int(
        (datetime.utcnow() - api_query.last_request).total_seconds())
    max_timedelta = co.ABANDONED_INTERVAL_MULTIPLE * api_query.refresh_interval
    return last_request_age > max_timedelta
  elif api_query.modified:
    last_modified_age = int(
        (datetime.utcnow() - api_query.modified).total_seconds())
    max_timedelta = co.ABANDONED_INTERVAL_MULTIPLE * api_query.refresh_interval
    return last_modified_age > max_timedelta
  else:
    # If query has been refreshed but never requested, mark as abandoned.
    api_query_response = api_query.api_query_responses.get()
    if api_query_response:
      return True

  return False


def IsErrorLimitReached(api_query):
  """Returns a boolean to indicate if the API Query reached the error limit."""
  return (api_query.api_query_errors.count(
      limit=co.QUERY_ERROR_LIMIT) == co.QUERY_ERROR_LIMIT)
