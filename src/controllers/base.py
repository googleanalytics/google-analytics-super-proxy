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

"""The base handlers used by public, owner, and admin handler scripts.

  BaseHandler: The base class for all other handlers to render content.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import json
import os
import urllib

from controllers.util import co
from controllers.util import users_helper
import jinja2
import webapp2

from google.appengine.api import users

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), '..', 'templates')),
    autoescape=True)


class BaseHandler(webapp2.RequestHandler):
  """Base handler for generating responses for most types of requests."""

  def RenderHtmlTemplate(self, template_name, template_values=None):
    """Renders HTML using a template.

    Values that are common across most templates are automatically added and
    sent to the template.

    Args:
      template_name: The name of the template to render (e.g. 'admin.html')
      template_values: A dict of values to pass to the template.
    """
    if template_values is None:
      template_values = {}

    current_user = users.get_current_user()
    user_settings = None
    user_email = ''
    if current_user:
      user_settings = users_helper.GetGaSuperProxyUser(current_user.user_id())
      user_email = current_user.email()

    template_values.update({
        'user_settings': user_settings,
        'current_user_email': user_email,
        'is_admin': users.is_current_user_admin(),
        'logout_url': users.create_logout_url(co.LINKS['owner_index']),
        'LINKS': co.LINKS
    })
    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    template = jinja_environment.get_template(template_name)
    self.response.write(template.render(template_values))

  def RenderCsv(self, csv_content, status=200):
    """Renders CSV content.

    Args:
      csv_content: The CSV content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/csv; charset=UTF-8'
    self.response.headers['Content-Disposition'] = (
        'attachment; filename=query_response.csv')
    self.response.set_status(status)
    self.response.write(csv_content)

  def RenderHtml(self, html_content, status=200):
    """Renders HTML content.

    Args:
      html_content: The HTML content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.set_status(status)
    self.response.write(html_content)

  def RenderJson(self, json_response, status=200):
    """Renders JSON/Javascript content.

    If a callback parameter is included as part of the request then a
    Javascript function is output (JSONP support).

    Args:
      json_response: The JSON content to output.
      status: The HTTP status code to send.
    """
    self.response.set_status(status)
    self.response.headers['Content-Disposition'] = 'inline'
    if self.request.get('callback'):  # JSONP Support
      self.response.headers['Content-Type'] = (
          'application/javascript; charset=UTF-8')
      self.response.out.write('(%s)(%s);' %
                              (urllib.unquote(self.request.get('callback')),
                               json.dumps(json_response)))
    else:
      self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
      self.response.write(json.dumps(json_response))

  def RenderText(self, text, status=200):
    """Renders plain text content.

    Args:
      text: The plain text to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
    self.response.headers['Content-Disposition'] = 'inline'
    self.response.set_status(status)
    self.response.write(text)

  def RenderTsv(self, tsv_content, status=200):
    """Renders TSV for Excel content.

    Args:
      tsv_content: The TSV for Excel content to output.
      status: The HTTP status code to send.
    """
    self.response.headers['Content-Type'] = ('application/vnd.ms-excel; '
                                             'charset=UTF-16LE')
    self.response.headers['Content-Disposition'] = (
        'attachment; filename=query_response.tsv')
    self.response.set_status(status)
    self.response.write(tsv_content)
