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

"""Handles all public requests to the Google Analytics superProxy.

These handlers are for actions performed by external users that may or may not
be signed in. This is configured in app.yaml. Additional logic is provided by
utility functions.

  PublicQueryResponseHandler: Outputs the API response for the requested query.
  NotAuthorizedHandler: Handles unauthorized requests.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from controllers import base
from controllers.transform import transformers
from controllers.util import co
from controllers.util import errors
from controllers.util import query_helper
import webapp2


class PublicQueryResponseHandler(base.BaseHandler):
  """Handles public requests for an API Query response.

  The handler retrieves the latest response for the requested API Query Id
  and format (if specified) and renders the response or an error message if
  a response was not found.
  """

  def get(self):
    """Renders the API Response in the format requested.

    Gets the public response and then uses the transformer to render the
    content. If there is an error then the error message will be rendered
    using the default response format.
    """
    query_id = self.request.get('id')
    response_format = str(self.request.get('format', co.DEFAULT_FORMAT))

    transform = transformers.GetTransform(response_format)

    try:
      (content, status) = query_helper.GetPublicEndpointResponse(
          query_id, response_format, transform)
    except errors.GaSuperProxyHttpError, proxy_error:
      # For error responses use the transform of the default format.
      transform = transformers.GetTransform(co.DEFAULT_FORMAT)
      content = proxy_error.content
      status = proxy_error.status

    transform.Render(self, content, status)


class NotAuthorizedHandler(base.BaseHandler):
  """Handles unauthorized public requests to owner/admin pages."""

  def get(self):
    self.RenderHtmlTemplate('public.html')


app = webapp2.WSGIApplication(
    [(co.LINKS['public_query'], PublicQueryResponseHandler),
     (co.LINKS['public_default'], NotAuthorizedHandler)],
    debug=True)
