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

"""Models for the Google Analytics superProxy.

  JsonQueryProperty: Property to store API Responses.
  GaSuperProxyUser: Represents the users of the service.
  GaSuperProxyUserInvitation: Represents an user invited to the service.
  ApiQuery: Models the API Queries created by users.
  ApiQueryResponse: Represents a successful response from an API.
  ApiErrorResponse: Represents an error response from an API.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import json

from controllers.util import models_helper

from google.appengine.ext import db


class JsonQueryProperty(db.Property):
  """Property to store/retrieve queries and responses in JSON format."""
  data_type = db.BlobProperty()

  # pylint: disable-msg=C6409
  def get_value_for_datastore(self, model_instance):
    value = super(JsonQueryProperty, self).get_value_for_datastore(
        model_instance)
    return db.Blob(json.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return None
    value = json.loads(str(value))
    return super(JsonQueryProperty, self).make_value_from_datastore(value)


class GaSuperProxyUser(db.Model):
  """Models a GaSuperProxyUser and user settings."""
  email = db.StringProperty()
  nickname = db.StringProperty()
  ga_refresh_token = db.StringProperty()
  ga_access_token = db.StringProperty()
  ga_token_expiry = db.DateTimeProperty()


class GaSuperProxyUserInvitation(db.Model):
  """Models a user invited to use the service."""
  email = db.StringProperty()
  issued = db.DateTimeProperty()


class ApiQuery(db.Model):
  """Models an API Query."""
  user = db.ReferenceProperty(GaSuperProxyUser,
                              required=True,
                              collection_name='api_queries')
  name = db.StringProperty(required=True)
  request = JsonQueryProperty(required=True)
  refresh_interval = db.IntegerProperty(required=True, default=3600)
  in_queue = db.BooleanProperty(required=True, default=False)
  is_active = db.BooleanProperty(required=True, default=False)
  is_scheduled = db.BooleanProperty(required=True, default=False)
  modified = db.DateTimeProperty()

  @property
  def is_abandoned(self):
    """Determines whether the API Query is considered abandoned."""
    return models_helper.IsApiQueryAbandoned(self)

  @property
  def is_error_limit_reached(self):
    """Returns True if the API Query has hit error limits."""
    return models_helper.IsErrorLimitReached(self)

  @property
  def last_request(self):
    """Returns the timestamp of the last request."""
    return models_helper.GetApiQueryLastRequest(str(self.key()))

  @property
  def last_request_timedelta(self):
    """Returns how long since the API Query response was last requested."""
    return models_helper.GetLastRequestTimedelta(self)

  @property
  def modified_timedelta(self, from_time=None):
    """Returns how long since the API Query was updated."""
    return models_helper.GetModifiedTimedelta(self, from_time)

  @property
  def request_count(self):
    """Reuturns the request count for the API Query."""
    return models_helper.GetApiQueryRequestCount(str(self.key()))


class ApiQueryResponse(db.Model):
  """Models an API Response."""
  api_query = db.ReferenceProperty(ApiQuery,
                                   required=True,
                                   collection_name='api_query_responses')
  content = JsonQueryProperty(required=True)
  modified = db.DateTimeProperty(required=True)


class ApiErrorResponse(db.Model):
  """Models an API Query Error Response."""
  api_query = db.ReferenceProperty(ApiQuery,
                                   required=True,
                                   collection_name='api_query_errors')
  content = JsonQueryProperty(required=True)
  timestamp = db.DateTimeProperty(required=True)
