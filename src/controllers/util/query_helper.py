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

"""Utility functions to help ineteract with API Queries.

  ResolveDates: Converts placeholders to actual dates.
  BuildApiQuery: Creates an API Query for the user.
  DeleteApiQuery: Deletes an API Query and related entities.
  DeleteApiQueryErrors: Deletes API Query Errors.
  DeleteApiQueryResponses: Deletes API Query saved Responses.
  ExecuteApiQueryTask: Runs a task from the task queue.
  FetchApiQueryResponse: Makes a request to an API.
  GetApiQuery: Retrieves an API Query from the datastore.
  GetApiQueryResponseFromDb: Returns the response content from the datastore..
  GetApiQueryResponseFromMemcache: Retrieves an API query from memcache.
  GetPublicEndpointResponse: Returns public response for an API Query request.
  InsertApiQueryError: Saves an API Query Error response.
  ListApiQueries: Returns a list of API Queries.
  RefreshApiQueryResponse: Fetched and saves an updated response for a query
  SaveApiQuery: Saves an API Query for a user.
  SaveApiQueryResponse: Saves an API Query response for an API Query.
  ScheduleAndSaveApiQuery: Saves and API Query and schedules it.
  SetPublicEndpointStatus: Enables/Disables the public endpoint.
  UpdateApiQueryCounter: Increments the request counter for an API Query.
  UpdateApiQueryTimestamp: Updates the last request time for an API Query.
  ValidateApiQuery: Validates form input for creating an API Query.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import copy
from datetime import datetime
from datetime import timedelta
import json
import re
import urllib

from controllers.transform import transformers
from controllers.util import analytics_auth_helper
from controllers.util import co
from controllers.util import date_helper
from controllers.util import errors
from controllers.util import request_counter_shard
from controllers.util import request_timestamp_shard
from controllers.util import schedule_helper
from controllers.util import users_helper

from models import db_models

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db


def ResolveDates(fn):
  """A decorator to resolve placeholder dates of an API Query request URL.

  Supports {today} and {Ndaysago} date formats.

  Args:
    fn: The original function being wrapped.

  Returns:
    An API Query entity with a new request URL where placeholder dates
    have been resolved to actual dates.
  """
  def Wrapper(api_query):
    """Returns an API Query with resolved placeholder dates in request URL."""
    query = urllib.unquote(api_query.request)
    start_search = re.search(r'start-date={(\d+)daysago}', query)
    end_search = re.search(r'end-date={(\d+)daysago}', query)

    if start_search:
      resolved_date = (datetime.utcnow() - timedelta(
          days=int(start_search.group(1))))
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace(start_search.group(),
                            'start-date=%s' % resolved_date)

    if end_search:
      resolved_date = (datetime.utcnow() - timedelta(days=int(
          end_search.group(1))))
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace(end_search.group(),
                            'end-date=%s' % resolved_date)

    if '{today}' in query:
      resolved_date = datetime.utcnow()
      resolved_date = FormatResolvedDate(resolved_date)
      query = query.replace('{today}', resolved_date)

    # Leave original API Query untouched by returning a copy w/resolved dates
    new_api_query = copy.copy(api_query)
    new_api_query.request = query

    return fn(new_api_query)
  return Wrapper


def FormatResolvedDate(date_to_format, timezone=co.TIMEZONE):
  """Formats a UTC date for the Google Analytics superProxy.

  Args:
    date_to_format: datetime The UTC date to format.
    timezone: string The timezone to use when formatting the date.
              E.g. 'pst', 'Eastern', 'cdt'.

  Returns:
    A string representing the resolved date for the specified timezone. The
    date format returned is yyyy-mm-dd. If the timezone specified does not
    exist then the original date will be used.
  """
  if timezone.lower() != 'utc':
    timezone_date = date_helper.ConvertDatetimeTimezone(
        date_to_format, timezone)
    if timezone_date:
      date_to_format = timezone_date

  return date_to_format.strftime('%Y-%m-%d')


def BuildApiQuery(name, request, refresh_interval, **kwargs):
  """Builds an API Query object for the current user.

  Args:
    name: The name of the API Query.
    request: The requet URL for the API Query.
    refresh_interval: An integer that specifies how often, in seconds, to
                      refresh the API Query when it is scheduled.
    **kwargs: Additional properties to set when building the query.

  Returns:
    An API Query object configured using the passed in parameters.
  """
  current_user = users_helper.GetGaSuperProxyUser(
      users.get_current_user().user_id())
  modified = datetime.utcnow()
  api_query = db_models.ApiQuery(name=name,
                                 request=request,
                                 refresh_interval=refresh_interval,
                                 user=current_user,
                                 modified=modified)

  for key in kwargs:
    if hasattr(api_query, key):
      setattr(api_query, key, kwargs[key])

  return api_query


def DeleteApiQuery(api_query):
  """Deletes an API Query including any related entities.

  Args:
    api_query: The API Query to delete.
  """
  if api_query:
    query_id = str(api_query.key())
    DeleteApiQueryErrors(api_query)
    DeleteApiQueryResponses(api_query)
    api_query.delete()
    memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                          key_prefix=query_id)

    request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
    request_counter_shard.DeleteCounter(request_counter_key)

    request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
    request_timestamp_shard.DeleteTimestamp(request_timestamp_key)


def DeleteApiQueryErrors(api_query):
  """Deletes API Query Errors.

  Args:
    api_query: The API Query to delete errors for.
  """
  if api_query and api_query.api_query_errors:
    db.delete(api_query.api_query_errors)


def DeleteApiQueryResponses(api_query):
  """Deletes an API Query saved response.

  Args:
    api_query: The API Query for which to delete the response.
  """
  if api_query and api_query.api_query_responses:
    db.delete(api_query.api_query_responses)


def ExecuteApiQueryTask(api_query):
  """Executes a refresh of an API Query from the task queue.

    Attempts to fetch and update an API Query and will also log any errors.
    Schedules the API Query for next execution.

  Args:
    api_query: The API Query to refresh.

  Returns:
    A boolean. True if the API refresh was a success and False if the API
    Query is not valid or an error was logged.
  """
  if api_query:
    query_id = str(api_query.key())
    api_query.in_queue = False

    api_response_content = FetchApiQueryResponse(api_query)

    if not api_response_content or api_response_content.get('error'):
      InsertApiQueryError(api_query, api_response_content)

      if api_query.is_error_limit_reached:
        api_query.is_scheduled = False

      SaveApiQuery(api_query)

      # Since it failed, execute the query again unless the refresh interval of
      # query is less than the random countdown, then schedule it normally.
      if api_query.refresh_interval < co.MAX_RANDOM_COUNTDOWN:
        schedule_helper.ScheduleApiQuery(api_query)  # Run at normal interval.
      else:
        schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      return False

    else:
      SaveApiQueryResponse(api_query, api_response_content)

      # Check that public  endpoint wasn't disabled after task added to queue.
      if api_query.is_active:
        memcache.set_multi({'api_query': api_query,
                            co.DEFAULT_FORMAT: api_response_content},
                           key_prefix=query_id,
                           time=api_query.refresh_interval)
        # Delete the transformed content in memcache since it will be updated
        # at the next request.
        delete_keys = set(co.SUPPORTED_FORMATS) - set([co.DEFAULT_FORMAT])
        memcache.delete_multi(list(delete_keys), key_prefix=query_id)

        SaveApiQuery(api_query)
        schedule_helper.ScheduleApiQuery(api_query)
        return True

      # Save the query state just in case the user disabled it
      # while it was in the task queue.
      SaveApiQuery(api_query)
  return False


@ResolveDates
@analytics_auth_helper.AuthorizeApiQuery
def FetchApiQueryResponse(api_query):
  try:
    response = urlfetch.fetch(url=api_query.request, deadline=60)
    response_content = json.loads(response.content)
  except (ValueError, TypeError, AttributeError, urlfetch.Error), e:
    return {'error': str(e)}

  return response_content


def GetApiQuery(query_id):
  """Retrieves an API Query entity.

  Args:
    query_id: the id of the entity

  Returns:
    The requested API Query entity or None if it doesn't exist.
  """
  try:
    return db_models.ApiQuery.get(query_id)
  except db.BadKeyError:
    return None


def GetApiQueryResponseFromDb(api_query):
  """Attempts to return an API Query response from the datastore.

  Args:
    api_query: The API Query for which the response is being requested.

  Returns:
    A dict with the HTTP status code and content for a public response.
    e.g. Valid Response: {'status': 200, 'content': A_JSON_RESPONSE}
    e.g. Error: {'status': 400, 'content': {'error': 'badRequest',
                                            'code': 400,
                                            'message': This is a bad request'}}
  """
  status = 400
  content = co.DEFAULT_ERROR_MESSAGE

  if api_query and api_query.is_active:
    try:
      query_response = api_query.api_query_responses.get()

      if query_response:
        status = 200
        content = query_response.content
      else:
        status = 400
        content = {
            'error': co.ERROR_INACTIVE_QUERY,
            'code': status,
            'message': co.ERROR_MESSAGES[co.ERROR_INACTIVE_QUERY]}
    except db.BadKeyError:
      status = 400
      content = {
          'error': co.ERROR_INVALID_QUERY_ID,
          'code': status,
          'message': co.ERROR_MESSAGES[co.ERROR_INVALID_QUERY_ID]}

  response = {
      'status': status,
      'content': content
  }

  return response


def GetApiQueryResponseFromMemcache(query_id, requested_format):
  """Attempts to return an API Query response from memcache.

  Args:
    query_id: The query id of the API Query to retrieve from memcache.
    requested_format: The format type requested for the response.

  Returns:
    A dict contatining the API Query, the response in the default format
    and requested format if available. None if there was no query found.
  """
  query_in_memcache = memcache.get_multi(
      ['api_query', co.DEFAULT_FORMAT, requested_format],
      key_prefix=query_id)

  if query_in_memcache:
    query = {
        'api_query': query_in_memcache.get('api_query'),
        'content': query_in_memcache.get(co.DEFAULT_FORMAT),
        'transformed_content': query_in_memcache.get(requested_format)
    }
    return query
  return None


def GetPublicEndpointResponse(
    query_id=None, requested_format=None, transform=None):
  """Returns the public response for an external user request.

  This handles all the steps required to get the latest successful API
  response for an API Query.
    1) Check Memcache, if found skip to #4.
    2) If not in memcache, check if the stored response is abandoned and needs
       to be refreshed.
    3) Retrieve response from datastore.
    4) Perform any transforms and return the formatted response to the user.

  Args:
    query_id: The query id to retrieve the response for.
    requested_format: The format type requested for the response.
    transform: The transform instance to use to transform the content to the
               requested format, if required.

  Returns:
    A tuple contatining the response content, and status code to
    render. e.g. (CONTENT, 200)
  """
  transformed_response_content = None
  schedule_query = False

  if not requested_format or requested_format not in co.SUPPORTED_FORMATS:
    requested_format = co.DEFAULT_FORMAT

  response = GetApiQueryResponseFromMemcache(query_id, requested_format)

  # 1. Check Memcache
  if response and response.get('api_query') and response.get('content'):
    api_query = response.get('api_query')
    response_content = response.get('content')
    transformed_response_content = response.get('transformed_content')
    response_status = 200
  else:
    api_query = GetApiQuery(query_id)

    # 2. Check if this is an abandoned query
    if (api_query is not None and api_query.is_active
        and not api_query.is_error_limit_reached
        and api_query.is_abandoned):
      RefreshApiQueryResponse(api_query)

    # 3. Retrieve response from datastore
    response = GetApiQueryResponseFromDb(api_query)
    response_content = response.get('content')
    response_status = response.get('status')

    # Flag to schedule query later on if there is a successful response.
    if api_query:
      schedule_query = not api_query.in_queue

  # 4. Return the formatted response.
  if response_status == 200:
    UpdateApiQueryCounter(query_id)
    UpdateApiQueryTimestamp(query_id)

    if co.ANONYMIZE_RESPONSES:
      response_content = transformers.RemoveKeys(response_content)

    if not transformed_response_content:
      try:
        transformed_response_content = transform.Transform(response_content)
      except (KeyError, TypeError, AttributeError):
        # If the transformation fails then return the original content.
        transformed_response_content = response_content

    memcache_keys = {
        'api_query': api_query,
        co.DEFAULT_FORMAT: response_content,
        requested_format: transformed_response_content
    }

    memcache.add_multi(memcache_keys,
                       key_prefix=query_id,
                       time=api_query.refresh_interval)

    # Attempt to schedule query if required.
    if schedule_query:
      schedule_helper.ScheduleApiQuery(api_query)

    response_content = transformed_response_content
  else:
    raise errors.GaSuperProxyHttpError(response_content, response_status)

  return (response_content, response_status)


def InsertApiQueryError(api_query, error):
  """Stores an API Error Response entity for an API Query.

  Args:
    api_query: The API Query for which the error occurred.
    error: The error that occurred.
  """
  if co.LOG_ERRORS:
    error = db_models.ApiErrorResponse(
        api_query=api_query,
        content=error,
        timestamp=datetime.utcnow())
    error.put()


def ListApiQueries(user=None, limit=1000):
  """Returns all queries that have been created.

  Args:
    user: The user to list API Queries for. None returns all queries.
    limit: The maximum number of queries to return.

  Returns:
    A list of queries.
  """
  if user:
    try:
      db_query = user.api_queries
      db_query.order('name')
      return db_query.run(limit=limit)
    except db.ReferencePropertyResolveError:
      return None
  else:
    api_query = db_models.ApiQuery.all()
    api_query.order('name')
    return api_query.run(limit=limit)
  return None


def RefreshApiQueryResponse(api_query):
  """Executes the API request and refreshes the response for an API Query.

  Args:
    api_query: The API Query to refresh the respone for.
  """
  if api_query:
    api_response = FetchApiQueryResponse(api_query)
    if not api_response or api_response.get('error'):
      InsertApiQueryError(api_query, api_response)
    else:
      SaveApiQueryResponse(api_query, api_response)

      # Clear memcache since this query response has changed.
      memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                            key_prefix=str(api_query.key()))


def SaveApiQuery(api_query, **kwargs):
  """Saves an API Query to the datastore.

  Args:
    api_query: The API Query to save.
    **kwargs: Additional properties to set for the API Query before saving.

  Returns:
    If successful the API Query that was saved or None if the save was
    unsuccessful.
  """

  if api_query:
    for key in kwargs:
      modified = datetime.utcnow()
      api_query.modified = modified
      if hasattr(api_query, key):
        setattr(api_query, key, kwargs[key])

    try:
      api_query.put()
      return api_query
    except db.TransactionFailedError:
      return None
  return None


def SaveApiQueryResponse(api_query, content):
  """Updates or creates a new API Query Response for an API Query.

  Args:
    api_query: The API Query for which the response will be added to
    content: The content of the API respone to add to the API Query.
  """
  db_response = api_query.api_query_responses.get()
  modified = datetime.utcnow()

  if db_response:
    db_response.content = content
    db_response.modified = modified
  else:
    db_response = db_models.ApiQueryResponse(api_query=api_query,
                                             content=content,
                                             modified=modified)
  db_response.put()


def ScheduleAndSaveApiQuery(api_query, **kwargs):
  """Schedules and saves an API Query.

  Args:
    api_query: The API Query to save and schedule.
    **kwargs: Additional properties to set for the API Query before saving.

  Returns:
    If successful the API Query that was saved or None if the save was
    unsuccessful.
  """
  if api_query:
    api_query.is_active = True
    api_query.is_scheduled = True
    saved = SaveApiQuery(api_query, **kwargs)
    if saved:
      schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      return api_query

  return None


def SetPublicEndpointStatus(api_query, status=None):
  """Change the public endpoint status of an API Query.

  Args:
    api_query: The API Query to change
    status: The status to change the API Query to. If status=None then the
            status of the API Query will be toggled.

  Returns:
    True if status change was successful, False otherwise.
  """
  if api_query and status in (None, True, False):
    if not status:
      api_query.is_active = not api_query.is_active
    else:
      api_query.is_active = status

    if api_query.is_active is False:
      api_query.is_scheduled = False

    try:
      api_query.put()
      memcache.delete_multi(['api_query'] + co.SUPPORTED_FORMATS.keys(),
                            key_prefix=str(api_query.key()))
      return True
    except db.TransactionFailedError:
      return False
  return False


def UpdateApiQueryCounter(query_id):
  """Increment the request counter for the API Query."""
  request_counter_key = co.REQUEST_COUNTER_KEY_TEMPLATE.format(query_id)
  request_counter_shard.Increment(request_counter_key)


def UpdateApiQueryTimestamp(query_id):
  """Update the last request timestamp for an API Query."""
  request_timestamp_key = co.REQUEST_TIMESTAMP_KEY_TEMPLATE.format(query_id)
  request_timestamp_shard.Refresh(request_timestamp_key)


def ValidateApiQuery(request_input):
  """Validates API Query settings.

  Args:
    request_input: The incoming request object containing form input value.

  Returns:
    A dict containing the validated API Query values or None if the input
    was invalid.
    e.g. {'name': 'Query Name',
          'request': 'http://apirequest',
          'refresh_interval': 15
         }
  """
  if request_input:
    name = request_input.get('name')
    request = request_input.get('request')
    refresh_interval = request_input.get('refresh_interval')
    validated_request = None
    try:
      if not name or not request or not refresh_interval:
        return None

      if len(name) > co.MAX_NAME_LENGTH or len(name) <= 0:
        return None
      validated_request = {
          'name': name
      }

      if len(request) > co.MAX_URL_LENGTH or len(request) <= 0:
        return None
      validated_request['request'] = request

      if int(refresh_interval) not in range(co.MIN_INTERVAL, co.MAX_INTERVAL):
        return None
      validated_request['refresh_interval'] = int(refresh_interval)
    except (ValueError, TypeError):
      return None
    return validated_request

  return None
