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

"""Handles timezone conversions for the Google Analytics superProxy.

Based on example from:
https://developers.google.com/appengine/docs/python/datastore/typesandpropertyclasses#datetime
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import datetime


def GetNATzinfo(tz='utc'):
  """Returns a timezone info object for the requested North American timezone.

  Args:
    tz: The requested timezone in North America.

  Returns:
    tzinfo object The tzinfo object for the requested timezone. If the timezone
    info is not available then None is returned.

  Raises:
    AttributeError: An invalid string was provided as an argument.
  """
  tzinfo = None
  tz = tz.lower()

  if tz == 'pst' or tz == 'pdt' or tz == 'pacific':
    tzinfo = NorthAmericanTzinfo(-8, 'PST', 'PDT')
  elif tz == 'mst' or tz == 'mdt' or tz == 'mountain':
    tzinfo = NorthAmericanTzinfo(-7, 'MST', 'MDT')
  elif tz == 'cst' or tz == 'cdt' or tz == 'central':
    tzinfo = NorthAmericanTzinfo(-6, 'CST', 'CDT')
  elif tz == 'est' or tz == 'edt' or tz == 'eastern':
    tzinfo = NorthAmericanTzinfo(-5, 'EST', 'EDT')
  elif tz == 'ast' or tz == 'adt' or tz == 'atlantic':
    tzinfo = NorthAmericanTzinfo(-4, 'AST', 'ADT')
  elif tz == 'utc':
    tzinfo = UtcTzinfo()

  return tzinfo


def ConvertDatetimeTimezone(date_to_convert, to_timezone):
  """Converts a datetime object's timzeone.

  Args:
    date_to_convert: The datetime object to convert the timezone.
    to_timezone: The timezone to convert the datetimt to.

  Returns:
    A datetime object set to the timezone requested. If the timezone isn't
    supported then None is returned.

  Raises:
    AttributeError: An invalid datetime object was provided.
  """
  tzinfo = GetNATzinfo(to_timezone)

  if tzinfo:
    new_date = date_to_convert.replace(tzinfo=UtcTzinfo())
    return new_date.astimezone(tzinfo)

  return None


class NorthAmericanTzinfo(datetime.tzinfo):
  """Implementation of North American timezones."""

  def __init__(self, hours, std_name, dst_name):
    """Initialize value for the North American timezone.

    Args:
      hours: integer Offset of local time from UTC in hours. E.g. -8 is Pacific.
      std_name: string Name of the timezone for standard time. E.g. PST.
      dst_name: string Name of the timezone for daylight savings time. E.g. PDT.
    """
    self.std_offset = datetime.timedelta(hours=hours)
    self.std_name = std_name
    self.dst_name = dst_name

  def utcoffset(self, dt):
    return self.std_offset + self.dst(dt)

  def _FirstSunday(self, dt):
    """First Sunday on or after dt."""
    return dt + datetime.timedelta(days=(6-dt.weekday()))

  def dst(self, dt):
    # 2 am on the second Sunday in March
    dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
    # 1 am on the first Sunday in November
    dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

    if dst_start <= dt.replace(tzinfo=None) < dst_end:
      return datetime.timedelta(hours=1)
    else:
      return datetime.timedelta(hours=0)

  def tzname(self, dt):
    if self.dst(dt) == datetime.timedelta(hours=0):
      return self.dst_name
    else:
      return self.std_name


class UtcTzinfo(datetime.tzinfo):
  """Implementation of UTC time."""

  def utcoffset(self, dt):
    return datetime.timedelta(0)

  def dst(self, dt):
    return datetime.timedelta(0)

  def tzname(self, dt):
    return 'UTC'
