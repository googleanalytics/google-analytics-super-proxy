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

"""Utility functions to help prepare template values for API Queries.

  GetContentForTemplate: Template value for API Query response content.
  GetErrorsForTemplate: Template value for API Query errors responses.
  GetFormatLinksForTemplate: Template value for API Query transform links.
  GetLinksForTemplate: Template values for API Query links.
  GetPropertiesForTemplate: Template values for API Query properties.
  GetTemplateValuesForAdmin: All template values required for the Admin page.
  GetTemplateValuesForManage: All template values required for the Manage page.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers.util import co


def GetContentForTemplate(api_query):
  """Prepares and returns the template value for an API Query response.

  Args:
    api_query: The API Query for which to prepare the response content template
               value.
  Returns:
    A dict containing the template value to use for the Response content.
  """
  content = {}
  if api_query:
    api_query_response = api_query.api_query_responses.get()
    if api_query_response:
      content['response_content'] = api_query_response.content

  return content


def GetErrorsForTemplate(api_query):
  """Prepares and returns the template values for API Query error responses.

  Args:
    api_query: The API Query for which to prepare the errors template values.
  Returns:
    A dict containing a list of template values to use for each API Query
    error responses.
  """
  errors = {}
  if api_query and api_query.api_query_errors:
    error_list = []
    for error in api_query.api_query_errors:
      error_list.append({
          'timestamp': error.timestamp,
          'content': error.content
      })

    errors['errors'] = error_list

  return errors


def GetFormatLinksForTemplate(api_query, hostname):
  """Prepares and returns template values for API Query format links.

  Args:
    api_query: The API Query for which to prepare the format links template
               values.
    hostname: The hostname to use for the format links.

  Returns:
    A dict containing the template value to use for the API Query format links.
  """
  query_id = api_query.key()
  format_links = {}
  format_links_list = {}

  for transform, config in co.SUPPORTED_FORMATS.items():
    format_links_list.update({
        config.get('label'): '%s%s?id=%s&format=%s' % (
            hostname, co.LINKS['public_query'], query_id, transform)
    })

  format_links['format_links'] = format_links_list

  return format_links


def GetLinksForTemplate(api_query, hostname):
  """Prepares and returns the template values for API Query links.

  Args:
    api_query: The API Query for which to prepare the links template values.
    hostname: The hostname to use for the links.

  Returns:
    A dict containing the template values to use for API Query links.
  """
  query_id = api_query.key()
  public_link = '%s%s?id=%s' % (hostname, co.LINKS['public_query'], query_id)
  manage_link = '%s?query_id=%s' % (co.LINKS['query_manage'], query_id)
  edit_link = '%s?query_id=%s&action=edit' % (
      co.LINKS['query_manage'], query_id)
  edit_post_link = '%s?query_id=%s' % (co.LINKS['query_edit'], query_id)
  delete_link = '%s?query_id=%s' % (co.LINKS['query_delete'], query_id)
  delete_errors_link = '%s?query_id=%s' % (
      co.LINKS['query_delete_errors'], query_id)
  status_change_link = '%s?query_id=%s' % (
      co.LINKS['query_status_change'], query_id)

  links = {
      'public_link': public_link,
      'manage_link': manage_link,
      'edit_link': edit_link,
      'edit_post_link': edit_post_link,
      'delete_link': delete_link,
      'delete_errors_link': delete_errors_link,
      'status_change_link': status_change_link
  }

  return links


def GetPropertiesForTemplate(api_query):
  """Prepares and returns the template value for a set of API Query properties.

  Args:
    api_query: The API Query for which to prepare the properties template
               values.
  Returns:
    A dict containing the template values to use for the API Query properties.
  """
  properties = {}
  if api_query:
    properties = {
        'id': str(api_query.key()),
        'name': api_query.name,
        'request': api_query.request,
        'user_email': api_query.user.email,
        'is_active': api_query.is_active,
        'is_scheduled': api_query.is_scheduled,
        'is_error_limit_reached': api_query.is_error_limit_reached,
        'in_queue': api_query.in_queue,
        'refresh_interval': api_query.refresh_interval,
        'modified_timedelta': api_query.modified_timedelta,
        'last_request_timedelta': api_query.last_request_timedelta,
        'request_count': api_query.request_count,
        'error_count': api_query.api_query_errors.count(
            limit=co.QUERY_ERROR_LIMIT)
    }

  return properties


def GetTemplateValuesForAdmin(api_queries, hostname):
  """Prepares and returns all the template values required for the Admin page.

  Args:
    api_queries: The list of queries for which to prepare template values.
    hostname: The hostname to use for links.

  Returns:
    A list of dicts that contain all the template values needed for each API
    Query that is listed on the Admin page.
  """
  template_values = []
  if api_queries:
    for api_query in api_queries:
      query_values = {}
      query_values.update(GetPropertiesForTemplate(api_query))
      query_values.update(GetLinksForTemplate(api_query, hostname))
      template_values.append(query_values)
  return template_values


def GetTemplateValuesForManage(api_query, hostname):
  """Prepares and returns all the template values required for the Manage page.

  Args:
    api_query: The API Query for which to prepare template values.
    hostname: The hostname to use for links.

  Returns:
    A dict that contains all the template values needed the API
    Query that is listed on the Manage page.
  """
  template_values = {}
  template_values.update(GetPropertiesForTemplate(api_query))
  template_values.update(GetLinksForTemplate(api_query, hostname))
  template_values.update(GetErrorsForTemplate(api_query))
  template_values.update(GetContentForTemplate(api_query))
  template_values.update(GetFormatLinksForTemplate(api_query, hostname))
  return template_values
