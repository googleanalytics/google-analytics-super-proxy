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

"""Handles all Admin requests to the Google Analytics Proxy.

These handlers are only available for actions performed by administrators. This
is configured in app.yaml. Addtional logic is provided by utility functions.

  AddUserHandler: Allows admins to view and grant users access to the app.
  QueryTaskWorker: Executes API Query tasks from the task queue
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.util import co
from controllers.util import query_helper
from controllers.util import users_helper
import webapp2


class AddUserHandler(base.BaseHandler):
  """Handles viewing and adding users of the to the service."""

  def get(self):
    template_values = {
        'users': users_helper.ListUsers(),
        'invitations': users_helper.ListInvitations(),
        'activate_link': self.request.host_url + co.LINKS['owner_activate'],
        'LINKS': co.LINKS
    }
    self.RenderHtmlTemplate('users.html', template_values)

  def post(self):
    """Handles HTTP POSTS requests to add a user.

    Users can be added by email address only.
    """
    email = self.request.get('email')
    users_helper.AddInvitation(email)
    self.redirect(co.LINKS['admin_users'])


class QueryTaskWorker(base.BaseHandler):
  """Handles API Query requests and responses from the task queue."""

  def post(self):
    query_id = self.request.get('query_id')
    api_query = query_helper.GetApiQuery(query_id)
    query_helper.ExecuteApiQueryTask(api_query)


app = webapp2.WSGIApplication(
    [(co.LINKS['admin_users'], AddUserHandler),
     (co.LINKS['admin_runtask'], QueryTaskWorker)],
    debug=True)
