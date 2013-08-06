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

"""Utility module to Transform GA API responses to different formats.

  Transforms a JSON response from the Google Analytics Core Reporting API V3.
  Responses can be anonymized, transformed, and returned in a new format.
  For example: CSV, TSV, Data Table, etc.

  GetTransform: Returns a transform for the requested format.
  TransformJson: Transform and render a Core Reporting API response as JSON.
  TransformCsv: Transform and render a Core Reporting API response as CSV.
  TransformDataTableString: Transform and render a Core Reporting API response
      as a Data Table string.
  TransformDataTableResponse: Transform and render a Core Reporting API response
      as a Data Table response.
  TransformTsv: Transform and render a Core Reporting API response as TSV.
  RemoveKeys: Removes key/value pairs from a JSON response.
  GetDataTableSchema: Get a Data Table schema from Core Reporting API Response.
  GetDataTableRows: Get Data Table rows from Core Reporting API Response.
  GetDataTable: Returns a Data Table using the Gviz library
  GetColumnOrder: Converts API Response column headers to columns for Gviz.
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import cStringIO
import urllib

from libs.csv_writer import csv_writer
from libs.gviz_api import gviz_api

# The label to use for unknown data types.
UNKNOWN_LABEL = 'UNKNOWN'

# Maps the types used in a Core Reporting API response to Python types.
BUILTIN_DATA_TYPES = {
    'STRING': str,
    'INTEGER': int,
    'FLOAT': float,
    'CURRENCY': float,
    UNKNOWN_LABEL: str
}

# Maps the types used in a Core Reporting API response to JavaScript types.
JS_DATA_TYPES = {
    'STRING': 'string',
    'INTEGER': 'number',
    'FLOAT': 'number',
    'CURRENCY': 'number',
    UNKNOWN_LABEL: 'string'
}


# List of properties to remove from the response when Anonymized.
# Paths to sub-properties in a nested dict can be separated with a
# colon. e.g. 'query:ids' will remove ids property from parent property query.
PRIVATE_PROPERTIES = ('id', 'query:ids', 'selfLink', 'nextLink', 'profileInfo')


def GetTransform(response_format='json', tqx=None):
  """Returns a transform based on the requested format.

  Args:
    response_format: A string indicating the type of transform to get.
    tqx: string tqx is a standard parameter for the Chart Tools Datasource
      Protocol V0.6. If it exists then we must handle it. In this case it will
      get passed to the Data Table Response transform.

  Returns:
    A transform instance for the requested format type or a default transform
    instance if an invalid response format is requested.
  """
  if response_format == 'json':
    transform = TransformJson()
  elif response_format == 'csv':
    output = cStringIO.StringIO()
    writer = csv_writer.GetCsvStringPrinter(output)
    transform = TransformCsv(writer, output)
  elif response_format == 'data-table':
    transform = TransformDataTableString()
  elif response_format == 'data-table-response':
    transform = TransformDataTableResponse(tqx)
  elif response_format == 'tsv':
    output = cStringIO.StringIO()
    writer = csv_writer.GetTsvStringPrinter(output)
    transform = TransformTsv(writer, output)
  else:
    transform = TransformJson()

  return transform


class TransformJson(object):
  """A transform to render a Core Reporting API response as JSON."""

  def Transform(self, content):
    """Transforms a Core Reporting API Response to JSON.

    Although this method simply returns the original argument it is needed to
    maintain a consistent interface for all transforms.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A dict, the original Core Reporting API Response.
    """
    return content

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response in JSON.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderJson(content, status)


class TransformCsv(object):
  """A transform to render a Core Reporting API response as CSV."""

  def __init__(self, writer, output):
    """Initialize the CSV Transform.

    Args:
      writer: The CSV Writer object to use for the transform.
      output: The CStringIO object to write the transformed content to.
    """
    self.writer = writer
    self.output = output

  def Transform(self, content):
    """Transforms the columns and rows from the API JSON response to CSV.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A string of either a CSV formatted response with a header or empty if no
      rows existed in the content to transform.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    csv_output = ''
    if content:
      column_headers = content.get('columnHeaders', [])
      rows = content.get('rows', [])

      if column_headers:
        self.writer.OutputHeaders(content)

      if rows:
        self.writer.OutputRows(content)

      csv_output = self.output.getvalue()
      self.output.close()

    return csv_output

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as CSV.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderCsv(content, status)


class TransformDataTableString(object):
  """A transform to render a Core Reporting API response as a Data Table."""

  def Transform(self, content):
    """Transforms a Core Reporting API response to a DataTable JSON String.

    DataTable
    https://developers.google.com/chart/interactive/docs/reference#DataTable

    JSON string -- If you are hosting the page that hosts the visualization that
    uses your data, you can generate a JSON string to pass into a DataTable
    constructor to populate it.
    From: https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      None if no content is provided, an empty string if a Data Table isn't
      supported for the given content, or a Data Table as a JSON String.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    if not content:
      return None

    column_headers = content.get('columnHeaders')
    rows = content.get('rows')
    if column_headers and rows:
      data_table_schema = GetDataTableSchema(content)
      data_table_rows = GetDataTableRows(content)

      data_table_output = GetDataTable(data_table_schema, data_table_rows)

      if data_table_output:
        return data_table_output.ToJSon()
    return ''

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as a Data Table String.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderText(content, status)


class TransformDataTableResponse(object):
  """A transform to render a Core Reporting API response as a Data Table."""

  def __init__(self, tqx=None):
    """Initialize the Data Table Response Transform.

    Args:
      tqx: string A set of colon-delimited key/value pairs for standard or
        custom parameters. Pairs are separated by semicolons.
        (https://developers.google.com/chart/interactive/docs/dev/
          implementing_data_source#requestformat)
    """
    if tqx:
      tqx = urllib.unquote(tqx)
    self.tqx = tqx

  def Transform(self, content):
    """Transforms a Core Reporting API response to a DataTable JSON Response.

    DataTable
    https://developers.google.com/chart/interactive/docs/reference#DataTable

    JSON response -- If you do not host the page that hosts the visualization,
    and just want to act as a data source for external visualizations, you can
    create a complete JSON response string that can be returned in response to a
    data request.
    From: https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      None if no content is provided, an empty string if a Data Table isn't
      supported for the given content, or a Data Table Response as JSON.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    if not content:
      return None

    column_headers = content.get('columnHeaders')
    rows = content.get('rows')
    if column_headers and rows:
      data_table_schema = GetDataTableSchema(content)
      data_table_rows = GetDataTableRows(content)
      data_table_output = GetDataTable(data_table_schema, data_table_rows)

      column_order = GetColumnOrder(column_headers)

      if data_table_output:
        req_id = 0
        # If tqx exists then handle at a minimum the reqId parameter
        if self.tqx:
          tqx_pairs = {}
          try:
            tqx_pairs = dict(pair.split(':') for pair in self.tqx.split(';'))
          except ValueError:
            # if the parse fails then just continue and use the empty dict
            pass
          req_id = tqx_pairs.get('reqId', 0)

        return data_table_output.ToJSonResponse(
            columns_order=column_order, req_id=req_id)
    return ''

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as a Data Table Response.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderText(content, status)


class TransformTsv(object):
  """A transform to render a Core Reporting API response as TSV."""

  def __init__(self, writer, output):
    """Initialize the TSV Transform.

    Args:
      writer: The CSV Writer object to use for the transform.
      output: The CStringIO object to write the transformed content to.
    """
    self.writer = writer
    self.output = output

  def Transform(self, content):
    """Transforms the columns and rows from the API JSON response to TSV.

    An Excel TSV is UTF-16 encoded.

    Args:
      content: A dict representing the Core Reporting API JSON response to
               transform.

    Returns:
      A UTF-16 encoded string representing an Excel TSV formatted response with
      a header or an empty string if no rows exist in the content.

    Raises:
      AttributeError: Invalid JSON response content was provided.
    """
    tsv_output = ''
    if content:
      column_headers = content.get('columnHeaders', [])
      rows = content.get('rows', [])

      if column_headers:
        self.writer.OutputHeaders(content)

      if rows:
        self.writer.OutputRows(content)

      out = self.output.getvalue()
      # Get UTF-8 output
      decoding = out.decode('UTF-8')
      # and re-encode to UTF-16 for Excel TSV
      tsv_output = decoding.encode('UTF-16')
      self.output.close()

    return tsv_output

  def Render(self, webapp, content, status):
    """Renders a Core Reporting API response as Excel TSV.

    Args:
      webapp: The webapp2 object to use to render the response.
      content: A dict representing the JSON content to render.
      status: An integer representing the HTTP status code to send.
    """
    webapp.RenderTsv(content, status)


def RemoveKeys(content, keys_to_remove=PRIVATE_PROPERTIES):
  """Removes key/value pairs from a JSON response.

  By default this will remove key/value pairs related to account information
  for a Google Analytics Core Reporting API JSON response.

  To remove keys, a path for each key to delete is created and stored in a list.
  Using this list of paths, the content is then traversed until each key is
  found and deleted from the content. For example, to traverse the content to
  find a single key, the key path is reversed and then each "node" in the path
  is popped off and fetched from the content. The traversal continues until
  all "nodes" have been fetched. Then a deletion is attempted.

  The reversal of the path is required because key paths are defined in order
  from ancestor to descendant and a pop operation returns the last item in a
  list. Since content traversal needs to go from ancestor to descendants,
  reversing the path before traversal will place the parent/ancestor at the
  end of the list, making it the first node/key to find in the content.

  Args:
    content: A dict representing the Core Reporting API JSON response to
             remove keys from.
    keys_to_remove: A tuple representing the keys to remove from the content.
                    The hiearchy/paths to child keys should be separated with a
                    colon. e.g. 'query:ids' will remove the child key, ids, from
                    parent key query.

  Returns:
    The given dict with the specified keys removed.
  """
  if content and keys_to_remove:
    for key_to_remove in keys_to_remove:

      # This gives a list that defines the hierarchy/path of the key to remove.
      key_hierarchy = key_to_remove.split(':')

      # Reverse the path to get the correct traversal order.
      key_hierarchy.reverse()
      key = key_hierarchy.pop()
      child_content = content

      # Traverse through hierarchy to find the key to delete.
      while key_hierarchy and child_content:
        child_content = child_content.get(key)
        key = key_hierarchy.pop()

      try:
        del child_content[key]
      except (KeyError, NameError, TypeError):
        # If the key doesn't exist then it's already "removed" so just continue
        # and move on to the next key for removal.
        pass
  return content


def GetDataTableSchema(content, data_types=None):
  """Builds and returns a Data Table schema from a Core Reporting API Response.

  Args:
    content: A dict representing the Core Reporting API JSON response to build
             a schmea from.
    data_types: A dict that maps the expected data types in the content to
                the equivalent JavaScript types. e.g.:
                {
                    'STRING': 'string',
                    'INTEGER': 'number'
                }
  Returns:
    A dict that contains column header and data type information that can be
    used for a Data Table schema/description. Returns None if there are no
    column headers in the Core Reporting API Response.

  Raises:
    AttributeError: Invalid JSON response content was provided.
  """
  if not content:
    return None

  if data_types is None:
    data_types = JS_DATA_TYPES

  column_headers = content.get('columnHeaders')
  schema = None

  if column_headers:
    schema = {}
    for header in column_headers:
      name = header.get('name', UNKNOWN_LABEL).encode('UTF-8')
      data_type = header.get('dataType', UNKNOWN_LABEL)
      data_type = data_types.get(data_type, data_types.get(UNKNOWN_LABEL))
      schema.update({
          name: (data_type, name),
      })
  return schema


def GetDataTableRows(content, data_types=None):
  """Builds and returns Data Table rows from a Core Reporting API Response.

  Args:
    content: A dict representing the Core Reporting API JSON response to build
             the rows from.

    data_types: A dict that maps the expected data types in the content to
                the equivalent Python types. e.g.:
                {
                    'STRING': str,
                    'INTEGER': int,
                    'FLOAT': float
                }

  Returns:
    A list where each item is a dict representing one row of data in a Data
    Table. Returns None if there are no column headers in the Core Reporting
    API response.
  """
  if not content:
    return None

  if data_types is None:
    data_types = BUILTIN_DATA_TYPES

  column_headers = content.get('columnHeaders')
  data_table = None

  if column_headers:
    data_table = []
    for data in content.get('rows', []):
      data_row = {}
      for index, data in enumerate(data):
        data_type = column_headers[index].get('dataType')
        convert_to = data_types.get(data_type, data_types.get(UNKNOWN_LABEL))
        if convert_to:
          data_row_value = convert_to(data)
        else:
          data_row_value = data.encode('UTF-8')
        data_row.update({
            column_headers[index].get('name', UNKNOWN_LABEL): data_row_value
        })
      data_table.append(data_row)
  return data_table


def GetDataTable(table_schema, table_rows):
  """Returns a Data Table using the Gviz library.

  DataTable:
  https://developers.google.com/chart/interactive/docs/reference#DataTable

  Data Source Python Library:
  https://developers.google.com/chart/interactive/docs/dev/gviz_api_lib

  Args:
    table_schema: A dict that contains column header and data type information
                  for a Data Table.
    table_rows: A list where each item in the list is a dict representing one
                row of data in a Data Table. It should match the schema defined
                by the provided table_schema argument.

  Returns:
    A gviz_api.DataTable object or None if Data Table isn't supported for
    the arguments provided.
  """
  if not table_schema or not table_rows:
    return None

  data_table_output = gviz_api.DataTable(table_schema)
  data_table_output.LoadData(table_rows)

  return data_table_output


def GetColumnOrder(column_headers):
  """Converts GA API columns headers into a column order tuple used by Gviz.

  Args:
    column_headers: A list of dicts that represent Column Headers. Equivalent
                    to the response from the GA API.
                    e.g.
                       [
                          {
                              "name": string,
                              "columnType": string,
                              "dataType": string
                          }
                       ]

  Returns:
    A tuple with column order that matches column headers in the original
    GA API response or None if there are no column headers.

  Raises:
    TypeError: An invalid list was provided.
  """
  column_order = None
  if column_headers:
    column_order = []
    for column in column_headers:
      column_order.append(column.get('name'))
    column_order = tuple(column_order)
  return column_order
