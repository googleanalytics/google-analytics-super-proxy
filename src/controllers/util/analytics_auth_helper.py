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

"""Utility functions to handle authentication for Google Analytics API.

  AuthorizeApiQuery: Decorating function to add an access token to request URL.
  FetchAccessToken: Gets a new access token using a refresh token.
  FetchCredentials: Makes requests to Google Accounts API.
  GetAccessTokenForApiQuery: Requests an access token for a given refresh token.
  GetOAuthCredentials: Exchanges a auth code for tokens.
  OAuthHandler: Handles incoming requests from the Google Accounts API.
  RevokeAuthTokensForUser: Revokes and deletes a user's auth tokens.
  RevokeOAuthCredentials: Revokes a refresh token.
  SaveAuthTokensForUser: Obtains and saves auth tokens for a user.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import copy
from datetime import datetime
import json
import urllib

import config
from controllers.util import users_helper

from google.appengine.api import urlfetch
from google.appengine.api import users


# Configure with your APIs Console Project
OAUTH_CLIENT_ID = config.AUTH_CONFIG['OAUTH_CLIENT_ID']
OAUTH_CLIENT_SECRET = config.AUTH_CONFIG['OAUTH_CLIENT_SECRET']
OAUTH_REDIRECT_URI = config.AUTH_CONFIG['OAUTH_REDIRECT_URI']

OAUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
OAUTH_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
OAUTH_REVOKE_ENDPOINT = 'https://accounts.google.com/o/oauth2/revoke?token='
OAUTH_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
OAUTH_ACCESS_TYPE = 'offline'
ISSUED_AUTH_TOKENS_WEB_URL = (
    'https://www.google.com/accounts/IssuedAuthSubTokens')

OAUTH_PARAMS = urllib.urlencode({
    'response_type': 'code',
    'client_id': OAUTH_CLIENT_ID,
    'redirect_uri': OAUTH_REDIRECT_URI,
    'scope': OAUTH_SCOPE,
    'access_type': OAUTH_ACCESS_TYPE
})

OAUTH_URL = '%s?%s' % (OAUTH_ENDPOINT, OAUTH_PARAMS)

AUTH_MESSAGES = {
    'codeError': ('Unable to obtain credentials. Visit %s to revoke any '
                  'existing tokens for this App and retry.' %
                  ISSUED_AUTH_TOKENS_WEB_URL),
    'codeSuccess': 'Successfully connected to Google Analytics.',
    'revokeError': ('There was an error while attempting to disconnect from '
                    'Google Analytics. Visit <a href="%s">My Account</a> to '
                    'revoke any existing tokens for this App and retry.' %
                    ISSUED_AUTH_TOKENS_WEB_URL),
    'revokeSuccess': 'Successfully disconnected from Google Analytics.',
    'badRequest': ('Unable to obtain credentials for Google Analytics '
                   'connection visit <a href="%s">My Account</a> to revoke any '
                   'existing tokens for this App and retry.' %
                   ISSUED_AUTH_TOKENS_WEB_URL)
}


def AuthorizeApiQuery(fn):
  """Decorator to retrieve an access token and append it to an API Query URL.

  Args:
    fn: The original function being wrapped.

  Returns:
    An API Query entity with an access token appended to request URL.
  """
  def Wrapper(api_query):
    """Returns the original function with an authorized API Query."""
    access_token = GetAccessTokenForApiQuery(api_query)
    query = api_query.request
    if access_token:
      query = ('%s&access_token=%s&gasp=1' % (
          urllib.unquote(api_query.request), access_token))

    # Leave original API Query untouched by returning a copy with
    # a valid access_token appended to the API request URL.
    new_api_query = copy.copy(api_query)
    new_api_query.request = query

    return fn(new_api_query)
  return Wrapper


def FetchAccessToken(refresh_token):
  """Gets a new access token using a refresh token.

  Args:
    refresh_token: The refresh token to use.

  Returns:
    A valid access token or None if query was unsuccessful.
  """
  auth_params = {
      'refresh_token': refresh_token,
      'client_id': OAUTH_CLIENT_ID,
      'client_secret': OAUTH_CLIENT_SECRET,
      'grant_type': 'refresh_token'
  }

  return FetchCredentials(auth_params)


def FetchCredentials(auth_params):
  """General utility to make fetch requests to OAuth Service.

  Args:
    auth_params: The OAuth parameters to use for the request.

  Returns:
    A dict with the response status code and content.
  """
  auth_status = {
      'status_code': 400
  }

  auth_payload = urllib.urlencode(auth_params)

  try:
    response = urlfetch.fetch(url=OAUTH_TOKEN_ENDPOINT,
                              payload=auth_payload,
                              method=urlfetch.POST,
                              headers={
                                  'Content-Type':
                                  'application/x-www-form-urlencoded'
                              })

    response_content = json.loads(response.content)

    if response.status_code == 200:
      auth_status['status_code'] = 200

    auth_status['content'] = response_content

  except (ValueError, TypeError, AttributeError, urlfetch.Error), e:
    auth_status['content'] = str(e)

  return auth_status


def GetAccessTokenForApiQuery(api_query):
  """Attempts to retrieve a valid access token for an API Query.

  First retrieves the stored access token for the owner of the API Query, if
  available. Checks if token has expired and refreshes token if required (and
  saves it) before returning the token.

  Args:
    api_query: The API Query for which to retrieve an access token.

  Returns:
    A valid access token if available or None.
  """
  user_settings = users_helper.GetGaSuperProxyUser(api_query.user.key().name())
  if user_settings.ga_refresh_token and user_settings.ga_access_token:

    access_token = user_settings.ga_access_token

    # Check for expired access_token
    if datetime.utcnow() > user_settings.ga_token_expiry:
      response = FetchAccessToken(user_settings.ga_refresh_token)
      if (response.get('status_code') == 200 and response.get('content')
          and response.get('content').get('access_token')):
        access_token = response.get('content').get('access_token')
        expires_in = int(response.get('content').get('expires_in', 0))

        users_helper.SetUserCredentials(api_query.user.key().name(),
                                        user_settings.ga_refresh_token,
                                        access_token,
                                        expires_in)
    return access_token
  return None


def GetOAuthCredentials(code):
  """Retrieves credentials from OAuth 2.0 service.

  Args:
    code: The authorization code from the auth server

  Returns:
    A dict indicating whether auth flow was a success and the auth
    server response.
  """
  auth_params = {
      'code': code,
      'client_id': OAUTH_CLIENT_ID,
      'client_secret': OAUTH_CLIENT_SECRET,
      'redirect_uri': OAUTH_REDIRECT_URI,
      'grant_type': 'authorization_code'
  }

  return FetchCredentials(auth_params)


def OAuthHandler(request):
  """Handles OAuth Responses from Google Accounts.

  The function can handle code, revoke, and error requests.

  Args:
    request: The request object for the incoming request from Google Accounts.

  Returns:
    A dict containing messages that can be used to display to a user to indicate
    the outcome of the auth task.
  """

  # Request to exchange auth code for refresh/access token
  if request.get('code'):
    code_response = SaveAuthTokensForUser(request.get('code'))
    if code_response.get('success'):
      auth_values = {
          'status': 'success',
          'message': AUTH_MESSAGES['codeSuccess'],
      }
    else:
      auth_values = {
          'status': 'error',
          'message': AUTH_MESSAGES['codeError'],
          'message_detail': code_response.get('message')
      }

  # Request to revoke an issued refresh/access token
  elif request.get('revoke'):
    revoked = RevokeAuthTokensForUser()
    if revoked:
      auth_values = {
          'status': 'success',
          'message': AUTH_MESSAGES['revokeSuccess']
      }
    else:
      auth_values = {
          'status': 'error',
          'message': AUTH_MESSAGES['revokeError']
      }

  # Error returned from OAuth service
  elif request.get('error'):
    auth_values = {
        'status': 'error',
        'message': AUTH_MESSAGES['badRequest'],
        'message_detail': request.get('error')
    }
  else:
    auth_values = {
        'status': 'error',
        'message': 'There was an error connecting to Google Analytics.',
        'message_detail': AUTH_MESSAGES['badRequest']
    }

  return auth_values


def RevokeAuthTokensForUser():
  """Revokes a user's auth tokens and removes them from the datastore.

  Returns:
    A boolean indicating whether the revoke was successfully.
  """
  user = users_helper.GetGaSuperProxyUser(users.get_current_user().user_id())

  if user and user.ga_refresh_token:
    RevokeOAuthCredentials(user.ga_refresh_token)
    users_helper.SetUserCredentials(users.get_current_user().user_id())
    return True
  return False


def RevokeOAuthCredentials(token):
  """Revokes an OAuth token.

  Args:
    token: A refresh or access token

  Returns:
    True if token successfully revoked, False otherwise
  """
  if token:
    revoke_url = OAUTH_REVOKE_ENDPOINT + token

    try:
      response = urlfetch.fetch(url=revoke_url)

      if response.status_code == 200:
        return True
    except urlfetch.Error:
      return False
  return False


def SaveAuthTokensForUser(code):
  """Exchanges an auth code for tokens and saves it to the datastore for a user.

  Args:
    code: The auth code from Google Accounts to exchange for tokens.

  Returns:
    A dict indicating whether the user's auth settings were successfully
    saved to the datastore and any messages returned from the service.
  """
  response = {
      'success': False
  }
  auth_response = GetOAuthCredentials(code)
  response_content = auth_response.get('content')

  if (auth_response.get('status_code') == 200
      and response_content
      and response_content.get('refresh_token')):

    refresh_token = response_content.get('refresh_token')
    access_token = response_content.get('access_token')

    users_helper.SetUserCredentials(
        users.get_current_user().user_id(),
        refresh_token, access_token)
    response['success'] = True
  else:
    response['message'] = response_content

  return response
