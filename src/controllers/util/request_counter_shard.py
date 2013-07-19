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

"""Handles the request counter for API Queries.

  Sharding is used to keep track of the number of requests for an API Query.

  Based on code from:
  https://developers.google.com/appengine/articles/sharding_counters
"""

__author__ = 'pete.frisella@gmail.com (Pete Frisella)'

import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

SHARD_KEY_TEMPLATE = 'shard-{}-{:d}'


class GeneralCounterShardConfig(ndb.Model):
  """Tracks the number of shards for each named counter."""
  num_shards = ndb.IntegerProperty(default=20)

  @classmethod
  def AllKeys(cls, name):
    """Returns all possible keys for the counter name given the config.

    Args:
      name: The name of the counter.

    Returns:
      The full list of ndb.Key values corresponding to all the possible
      counter shards that could exist.
    """
    config = cls.get_or_insert(name)
    shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index)
                         for index in range(config.num_shards)]
    return [ndb.Key(GeneralCounterShard, shard_key_string)
            for shard_key_string in shard_key_strings]


class GeneralCounterShard(ndb.Model):
  """Shards for each named counter."""
  count = ndb.IntegerProperty(default=0)


def GetCount(name):
  """Retrieve the value for a given sharded counter.

  Args:
    name: The name of the counter.

  Returns:
    Integer; the cumulative count of all sharded counters for the given
    counter name.
  """
  total = memcache.get(name)
  if total is None:
    total = 0
    all_keys = GeneralCounterShardConfig.AllKeys(name)
    for counter in ndb.get_multi(all_keys):
      if counter is not None:
        total += counter.count
    memcache.add(name, total, 60)
  return total


def Increment(name):
  """Increment the value for a given sharded counter.

  Args:
    name: The name of the counter.
  """
  config = GeneralCounterShardConfig.get_or_insert(name)
  _Increment(name, config.num_shards)


@ndb.transactional
def _Increment(name, num_shards):
  """Transactional helper to increment the value for a given sharded counter.

  Also takes a number of shards to determine which shard will be used.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  index = random.randint(0, num_shards - 1)
  shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
  counter = GeneralCounterShard.get_by_id(shard_key_string)
  if counter is None:
    counter = GeneralCounterShard(id=shard_key_string)
  counter.count += 1
  counter.put()
  # Memcache increment does nothing if the name is not a key in memcache
  memcache.incr(name)


@ndb.transactional
def IncreaseShards(name, num_shards):
  """Increase the number of shards for a given sharded counter.

  Will never decrease the number of shards.

  Args:
    name: The name of the counter.
    num_shards: How many shards to use.
  """
  config = GeneralCounterShardConfig.get_or_insert(name)
  if config.num_shards < num_shards:
    config.num_shards = num_shards
    config.put()


def DeleteCounter(name):
  """Delete a sharded counter.

  Args:
    name: The name of the counter to delete.
  """
  all_keys = GeneralCounterShardConfig.AllKeys(name)
  ndb.delete_multi(all_keys)
  memcache.delete(name)
  config_key = ndb.Key('GeneralCounterShardConfig', name)
  config_key.delete()
