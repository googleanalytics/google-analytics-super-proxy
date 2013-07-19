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

"""Utility module to validate XSRF tokens."""

__author__ = 'nickski15@gmail.com (Nick Mihailovski)'
__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import hashlib
import hmac

import config
from controllers.util import query_helper
from controllers.util import users_helper

import co

from google.appengine.api import users


def OwnerRestricted(original_request):
  """Requires that the user owns the entity being accessed or is an admin.

    If the request isn't made by the owner of the API Query or an admin then
    they will be redirected to the owner index page.

  Args:
    original_request: The restricted request being made.

  Returns:
    The wrapped request.
  """
  def Wrapper(self, *args, **kwargs):
    query_id = self.request.get('query_id')
    owner_has_access = UserOwnsApiQuery(query_id)
    if owner_has_access or users.is_current_user_admin():
      return original_request(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['owner_index'])
      return

  return Wrapper


def ActiveGaSuperProxyUser(original_request):
  """Requires that this is a valid user of the app.

    If the request isn't made by an active Google Analytics superProxy user then
    they will be redirected to the public index page.

  Args:
    original_request: The restricted request being made.

  Returns:
    The wrapped request.
  """
  def Wrapper(self, *args, **kwargs):
    user = users_helper.GetGaSuperProxyUser(users.get_current_user().user_id())
    if user or users.is_current_user_admin():
      return original_request(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['public_index'])
      return

  return Wrapper


def GetXsrfToken():
  """Generate a signed token unique to this user.

  Returns:
    An XSRF token unique to the user.
  """
  token = None
  user = users.get_current_user()
  if user:
    mac = hmac.new(config.XSRF_KEY, user.user_id(), hashlib.sha256)
    token = mac.hexdigest()
  return token


def ValidXsrfTokenRequired(original_handler):
  """Require a valid XSRF token in the environment, or error.

    If the request doesn't include a valid XSRF token then they will be
    redirected to the public index page.

  Args:
    original_handler: The handler that requires XSRF validation.

  Returns:
    The wrapped handler.
  """
  def Handler(self, *args, **kwargs):
    if self.request.get('xsrf_token') == GetXsrfToken():
      return original_handler(self, *args, **kwargs)
    else:
      self.redirect(co.LINKS['public_index'])
      return

  Handler.__name__ = original_handler.__name__
  return Handler


def UserOwnsApiQuery(query_id):
  """Check if the currently logged in user owns the API Query.

  Args:
    query_id: The id of the API query.

  Returns:
    A boolean to indicate whether the logged in user owns the API Query.
  """
  user = users.get_current_user()
  api_query = query_helper.GetApiQuery(query_id)

  if user and user.user_id() and api_query:
    return user.user_id() == api_query.user.key().name()
  return False
