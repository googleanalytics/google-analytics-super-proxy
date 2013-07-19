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

"""Utility functions to handle user operations.

  AddInvitation: Adds an email to the user invite table.
  ActivateUser: Activates a user account so they can use the application.
  GetGaSuperProxyUser: Returns a user from the datastore.
  GetInvitation: Gets a user's invitation from the datastore.
  ListInvitations: Lists all invitations saved in the datastore.
  ListUsers: Lists all users saved in the datastore.
  SetUserCredentials: Saves auth tokens for a user.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime
from datetime import timedelta

from models import db_models

from google.appengine.api import users
from google.appengine.ext import db


def AddInvitation(email):
  """Create an invite for a user so that they can login.

  Args:
    email: the email of the user to invite/add.

  Returns:
    A boolean indicating whether the user was added or not.
  """
  if not GetInvitation(email):
    invitation = db_models.GaSuperProxyUserInvitation(
        email=email.lower(),
        issued=datetime.utcnow())
    invitation.put()
    return True
  return False


def ActivateUser():
  """Activates the current user if they have an outstanding invite.

  Returns:
    The user object for the activated user.
  """
  current_user = users.get_current_user()
  if current_user:
    invite = GetInvitation(current_user.email().lower())
    if invite:
      user = db_models.GaSuperProxyUser.get_or_insert(
          key_name=current_user.user_id(),
          email=current_user.email(),
          nickname=current_user.nickname())
      invite.delete()
      return user
  return None


def GetGaSuperProxyUser(user_id):
  """Retrieves a GaSuperProxyUser entity.

  Args:
    user_id: the user id of the entity

  Returns:
    The requested GaSuperProxyUser entity or None if it does not exist.
  """
  try:
    return db_models.GaSuperProxyUser.get_by_key_name(user_id)
  except db.BadKeyError:
    return None


def GetInvitation(email):
  """Retrieves a user invitation.

  Args:
    email: the email of the user

  Returns:
    The requested user invitation or None if it does not exist.
  """
  invitation = db_models.GaSuperProxyUserInvitation.all()
  invitation.filter('email = ', email)
  return invitation.get()


def ListInvitations(limit=1000):
  """Returns all outstanding user invitations.

  Args:
    limit: The maximum number of invitations to return.

  Returns:
    A list of invitations.
  """
  invitation = db_models.GaSuperProxyUserInvitation.all()
  return invitation.run(limit=limit)


def ListUsers(limit=1000):
  """Returns all users that have been added to the service.

  Args:
    limit: The maximum number of queries to return.

  Returns:
    A list of users.
  """
  user = db_models.GaSuperProxyUser.all()
  return user.run(limit=limit)


def SetUserCredentials(
    user_id, refresh_token=None, access_token=None, expires_in=3600):
  """Saves OAuth credentials for a user. Creates user if it does not exist.

  If only a user id is provided then credentials for a user will be cleared.

  Args:
    user_id: The id of the user to store credentials for.
    refresh_token: The refresh token to save for the user.
    access_token: The access token to save for the user.
    expires_in: How long the access token is valid for (seconds).
  """
  user = GetGaSuperProxyUser(user_id)
  token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

  if user:
    user.ga_refresh_token = refresh_token
    user.ga_access_token = access_token
    user.ga_token_expiry = token_expiry
  else:
    user = db_models.GaSuperProxyUser(
        key_name=users.get_current_user().user_id(),
        email=users.get_current_user().email(),
        nickname=users.get_current_user().nickname(),
        ga_refresh_token=refresh_token,
        ga_access_token=access_token,
        ga_token_expiry=token_expiry)
  user.put()
