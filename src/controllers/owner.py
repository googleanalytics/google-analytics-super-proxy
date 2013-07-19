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

"""Handles all Owner requests to the Google Analytics superProxy.

  These handlers are available for actions performed by owners that can manage
  API Queries. This is configured in app.yaml. Additional logic is provided by
  utility functions.

  ActivateUserHandler: Activates new users.
  AdminHandler: Handles the admin home page for owners.
  AuthHandler: Handles OAuth 2.0 flow and storing auth tokens for the owner.
  ChangeQueryStatusHandler: Disables/enables public endpoints for queries.
  CreateQueryHandler: Handles creating new API Queries.
  DeleteQueryHandler: Deletes an API Query and related entities.
  DeleteQueryErrorsHandler: Deletes API query error responses.
  EditQueryHandler: Handles requests to edit an API Query.
  ManageQueryHandler: Provides the status and management operations for an
                      API Query.
  RunQueryHandler: Handles adhoc refresh requests from owners.
  ScheduleQueryHandler: Handles API Query scheduling.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.util import access_control
from controllers.util import analytics_auth_helper
from controllers.util import co
from controllers.util import query_helper
from controllers.util import schedule_helper
from controllers.util import template_helper
from controllers.util import users_helper
import webapp2

from google.appengine.api import users


class ActivateUserHandler(base.BaseHandler):
  """Handles the activation of a new user."""

  def get(self):
    """Handles user activations."""
    user = users.get_current_user()

    if users_helper.GetGaSuperProxyUser(user.user_id()):
      self.redirect(co.LINKS['owner_index'])
      return

    if not users_helper.GetInvitation(user.email().lower()):
      self.redirect(co.LINKS['public_index'])

    template_values = {
        'xsrf_token': access_control.GetXsrfToken()
    }
    self.RenderHtmlTemplate('activate.html', template_values)

  @access_control.ValidXsrfTokenRequired
  def post(self):
    """Activates and adds a user to the service."""
    users_helper.ActivateUser()
    self.redirect(co.LINKS['owner_index'])


class AdminHandler(base.BaseHandler):
  """Handler for the Admin panel to list all API Queries."""

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Displays a list of API Queries.

    Only the user's API Queries are shown unless the user is an administrator.
    Administrators can also filter the list to only show queries they own.
    """
    query_filter = self.request.get('filter')

    if users.is_current_user_admin() and query_filter != 'owner':
      user = None
    else:
      user = users_helper.GetGaSuperProxyUser(
          users.get_current_user().user_id())

    api_queries = query_helper.ListApiQueries(user)
    hostname = self.request.host_url
    template_values = {
        'api_queries': template_helper.GetTemplateValuesForAdmin(api_queries,
                                                                 hostname),
        'query_error_limit': co.QUERY_ERROR_LIMIT,
        'revoke_token_url': '%s?revoke=true' % co.LINKS['owner_auth'],
        'oauth_url': analytics_auth_helper.OAUTH_URL
    }
    self.RenderHtmlTemplate('admin.html', template_values)


class AuthHandler(base.BaseHandler):
  """Handles OAuth 2.0 responses and requests."""

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    template_values = analytics_auth_helper.OAuthHandler(self.request)
    self.RenderHtmlTemplate('auth.html', template_values)


class ChangeQueryStatusHandler(base.BaseHandler):
  """Handles requests to change the endpoint status of an API Query."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Change the public endpoint status of an API Query."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])

    api_query = query_helper.GetApiQuery(query_id)
    query_helper.SetPublicEndpointStatus(api_query)
    self.redirect(redirect)


class CreateQueryHandler(base.BaseHandler):
  """Handles the creation of API Queries.

    This handles 3 cases, testing a query, saving a new query, and saving and
    automatically scheduling a new query.
  """

  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Displays the create query form."""
    template_values = {
        'timezone': co.TIMEZONE,
        'xsrf_token': access_control.GetXsrfToken()
    }
    self.RenderHtmlTemplate('create.html', template_values)

  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Validates and tests/saves the API Query to the datastore.

    The owner can do any of the following from the create form:
    testing: It will render the create form and show test results.
    save: It will save the query to the datastore.
    save and schedule: It will save the query to the datastore and enable
                       scheduling for the query.
    """
    query_form_input = {
        'name': self.request.get('name'),
        'request': self.request.get('request'),
        'refresh_interval': self.request.get('refresh_interval')
    }

    query_form_input = query_helper.ValidateApiQuery(query_form_input)

    if not query_form_input:
      self.redirect(co.LINKS['owner_index'])

    api_query = query_helper.BuildApiQuery(**query_form_input)

    if self.request.get('test_query'):
      test_response = query_helper.FetchApiQueryResponse(api_query)

      template_values = {
          'test_response': test_response,
          'name': api_query.name,
          'request': api_query.request,
          'refresh_interval': api_query.refresh_interval,
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }

      self.RenderHtmlTemplate('create.html', template_values)
      return

    elif self.request.get('create_query'):
      query_helper.SaveApiQuery(api_query)

    elif self.request.get('create_run_query'):
      query_helper.ScheduleAndSaveApiQuery(api_query)

    api_query_links = template_helper.GetLinksForTemplate(
        api_query, self.request.host_url)
    self.redirect(api_query_links.get('manage_link', '/'))


class DeleteQueryHandler(base.BaseHandler):
  """Handles requests to delete an API Query."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Delete an API Query and any child API Query (Error) Responses."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])
    api_query = query_helper.GetApiQuery(query_id)

    query_helper.DeleteApiQuery(api_query)

    self.redirect(redirect)


class DeleteQueryErrorsHandler(base.BaseHandler):
  """Handles requests to delete API Query Error Responses."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Delete API query error responses."""
    query_id = self.request.get('query_id')
    redirect = self.request.get('redirect', co.LINKS['owner_index'])
    api_query = query_helper.GetApiQuery(query_id)

    query_helper.DeleteApiQueryErrors(api_query)
    schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
    self.redirect(redirect)


class EditQueryHandler(base.BaseHandler):
  """Handles requests to edit an API Query."""

  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Validates and tests/saves the API Query to the datastore.

    The owner can do any of the following from the edit form:
    testing: It will render the create form and show test results.
    save: It will save the query to the datastore.
    save and refresh: It will save the query, fetch the lastest data and then
      save both to the datastore.
    """
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if not api_query:
      self.redirect(co.LINKS['owner_index'])

    query_form_input = {
        'name': self.request.get('name'),
        'request': self.request.get('request'),
        'refresh_interval': self.request.get('refresh_interval')
    }
    query_form_input = query_helper.ValidateApiQuery(query_form_input)

    hostname = self.request.host_url
    api_query_links = template_helper.GetLinksForTemplate(api_query, hostname)

    if not query_form_input:
      self.redirect(api_query_links.get('manage_link', '/'))

    api_query.name = query_form_input.get('name')
    api_query.request = query_form_input.get('request')
    api_query.refresh_interval = query_form_input.get('refresh_interval')

    if self.request.get('test_query'):
      test_response = query_helper.FetchApiQueryResponse(api_query)

      template_values = {
          'test_response': test_response,
          'api_query': template_helper.GetTemplateValuesForManage(api_query,
                                                                  hostname),
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }
      self.RenderHtmlTemplate('edit.html', template_values)
      return

    elif self.request.get('save_query'):
      query_helper.SaveApiQuery(api_query)
    elif self.request.get('save_query_refresh'):
      query_helper.SaveApiQuery(api_query)
      query_helper.RefreshApiQueryResponse(api_query)

    self.redirect(api_query_links.get('manage_link', '/'))


class ManageQueryHandler(base.BaseHandler):
  """Handles requests to view and manage API Queries."""

  @access_control.OwnerRestricted
  @access_control.ActiveGaSuperProxyUser
  def get(self):
    """Retrieves a query to be managed by the user."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      hostname = self.request.host_url
      template_values = {
          'api_query': template_helper.GetTemplateValuesForManage(api_query,
                                                                  hostname),
          'timezone': co.TIMEZONE,
          'xsrf_token': access_control.GetXsrfToken()
      }

      if self.request.get('action') == 'edit':
        self.RenderHtmlTemplate('edit.html', template_values)
        return

      self.RenderHtmlTemplate('view.html', template_values)
      return

    self.redirect(co.LINKS['owner_index'])


class RunQueryHandler(base.BaseHandler):
  """Handles a single query execution request.

  This handles adhoc requests by owners to Refresh an API Query.
  """

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Refreshes the API Query Response."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      query_helper.RefreshApiQueryResponse(api_query)
      api_query_links = template_helper.GetLinksForTemplate(
          api_query, self.request.host_url)
      self.redirect(api_query_links.get('manage_link', '/'))
      return

    self.redirect(co.LINKS['owner_index'])


class ScheduleQueryHandler(base.BaseHandler):
  """Handles the scheduling of API Queries. Starting and stopping."""

  @access_control.OwnerRestricted
  @access_control.ValidXsrfTokenRequired
  @access_control.ActiveGaSuperProxyUser
  def post(self):
    """Starts/Stops API Query Scheduling."""
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)

    if api_query:
      schedule_helper.SetApiQueryScheduleStatus(api_query)
      schedule_helper.ScheduleApiQuery(api_query, randomize=True, countdown=0)
      api_query_links = template_helper.GetLinksForTemplate(
          api_query, self.request.host_url)
      self.redirect(api_query_links.get('manage_link', '/'))
      return

    self.redirect(co.LINKS['owner_index'])


app = webapp2.WSGIApplication(
    [(co.LINKS['owner_index'], AdminHandler),
     (co.LINKS['query_manage'], ManageQueryHandler),
     (co.LINKS['query_edit'], EditQueryHandler),
     (co.LINKS['query_delete'], DeleteQueryHandler),
     (co.LINKS['query_delete_errors'], DeleteQueryErrorsHandler),
     (co.LINKS['query_create'], CreateQueryHandler),
     (co.LINKS['query_status_change'], ChangeQueryStatusHandler),
     (co.LINKS['query_run'], RunQueryHandler),
     (co.LINKS['query_schedule'], ScheduleQueryHandler),
     (co.LINKS['owner_auth'], AuthHandler),
     (co.LINKS['owner_activate'], ActivateUserHandler),
     (co.LINKS['owner_default'], AdminHandler)],
    debug=True)
