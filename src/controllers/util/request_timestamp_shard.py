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

"""Handles the request timestamp for API Query requests.

  Sharding timestamps is used to handle when the last request was made for
  and API Query.

  Based on code from:
  https://developers.google.com/appengine/articles/sharding_counters
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

from datetime import datetime
import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

SHARD_KEY_TEMPLATE = 'shard-{}-{:d}'


class GeneralTimestampShardConfig(ndb.Model):
  """Tracks the number of shards for each named timestamp."""
  num_shards = ndb.IntegerProperty(default=20)

  @classmethod
  def AllKeys(cls, name):
    """Returns all possible keys for the timestamp name given the config.

    Args:
      name: The name of the timestamp.

    Returns:
      The full list of ndb.Key values corresponding to all the possible
      timestamp shards that could exist.
    """
    config = cls.get_or_insert(name)
    shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index)
                         for index in range(config.num_shards)]
    return [ndb.Key(GeneralTimestampShard, shard_key_string)
            for shard_key_string in shard_key_strings]


class GeneralTimestampShard(ndb.Model):
  """Shards for each named Timestamp."""
  timestamp = ndb.DateTimeProperty()


def GetTimestamp(name):
  """Retrieve the value for a given sharded timestamp.

  Args:
    name: The name of the timestamp.

  Returns:
    Integer; the cumulative count of all sharded Timestamps for the given
    Timestamp name.
  """
  latest_timestamp = memcache.get(name)
  if latest_timestamp is None:
    all_keys = GeneralTimestampShardConfig.AllKeys(name)
    for timestamp in ndb.get_multi(all_keys):
      if timestamp is not None and latest_timestamp is None:
        latest_timestamp = timestamp.timestamp
      elif timestamp is not None and timestamp.timestamp > latest_timestamp:
        latest_timestamp = timestamp.timestamp
    memcache.add(name, latest_timestamp, 60)
  return latest_timestamp


def Refresh(name):
  """Refresh the value for a given sharded timestamp.

  Args:
    name: The name of the timestamp.
  """
  config = GeneralTimestampShardConfig.get_or_insert(name)
  _Refresh(name, config.num_shards)


@ndb.transactional
def _Refresh(name, num_shards):
  """Transactional helper to refresh the value for a given sharded timestamp.

  Also takes a number of shards to determine which shard will be used.

  Args:
      name: The name of the timestamp.
      num_shards: How many shards to use.
  """
  index = random.randint(0, num_shards - 1)
  shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
  timestamp = GeneralTimestampShard.get_by_id(shard_key_string)
  if timestamp is None:
    timestamp = GeneralTimestampShard(id=shard_key_string)
  timestamp.timestamp = datetime.utcnow()
  timestamp.put()
  # Memcache replace does nothing if the name is not a key in memcache
  memcache.replace(name, timestamp.timestamp)


@ndb.transactional
def IncreaseShards(name, num_shards):
  """Increase the number of shards for a given sharded counter.

  Will never decrease the number of shards.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  config = GeneralTimestampShardConfig.get_or_insert(name)
  if config.num_shards < num_shards:
    config.num_shards = num_shards
    config.put()


def DeleteTimestamp(name):
  """Delete a sharded timestamp.

  Args:
    name: The name of the timestamp to delete.
  """
  all_keys = GeneralTimestampShardConfig.AllKeys(name)
  ndb.delete_multi(all_keys)
  memcache.delete(name)
  config_key = ndb.Key('GeneralTimestampShardConfig', name)
  config_key.delete()
