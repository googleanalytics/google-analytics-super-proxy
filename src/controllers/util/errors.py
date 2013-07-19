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

"""Custom exceptions for the Google Analytics superProxy."""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'


class GaSuperProxyHttpError(Exception):
  """Exception for a proxy response with a non-200 HTTP status."""

  def __init__(self, content, status):
    """Initialize the error object.

    Args:
      content: A dict representing the error message response to display.
      status: An integer representing the HTTP status code of the error.
    """
    Exception.__init__(self)
    self.status = status
    self.content = content

  def __str__(self):
    """Returns the string representation of the error message content."""
    return repr(self.content)
