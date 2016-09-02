#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Stores probe data in a sqlite database

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
:status: Alpha

..

    Copyright 2014 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Probe constants
from herald import PROBE_CHANNEL_MSG_SEND, PROBE_CHANNEL_MSG_CONTENT, \
    PROBE_CHANNEL_MSG_RECV
from herald.probe import SERVICE_STORE

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Property, \
    Validate

# Standard library
import logging
import sqlite3

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

CHANNEL_FIELDS = {
    PROBE_CHANNEL_MSG_SEND: ("uid", "timestamp", "transport", "subject",
                             "target", "transportTarget", "repliesTo"),
    PROBE_CHANNEL_MSG_RECV: ("uid", "timestamp", "transport", "subject",
                             "source", "transportSource", "repliesTo"),
    PROBE_CHANNEL_MSG_CONTENT: ("uid", "content"),
    'http_multicast': ("timestamp", "uid", "event"),
}
"""
For each channel, the list of fields for which a value is given
"""

CHANNEL_VALUES = dict((key, tuple(":{0}".format(field) for field in fields))
                      for key, fields in CHANNEL_FIELDS.items())
"""
For each channel, the list of ':field' parameters to give to execute, in the
values() SQL statement
"""

FAILSAFE_CHANNELS = (PROBE_CHANNEL_MSG_CONTENT,)
""" List of channels which integrity error can be ignored """

# ------------------------------------------------------------------------------


@ComponentFactory('herald-probe-sqlite-factory')
@Provides(SERVICE_STORE)
@Property("_db_name", "db.file", "herald_probe.db")
class SqliteStore(object):
    """
    Traces data into a logger
    """
    def __init__(self):
        """
        Sets up members
        """
        # DB file name
        self._db_name = ":memory:"

    @Validate
    def validate(self, _):
        """
        Component validated
        """
        # Open the database
        sql_con = sqlite3.connect(self._db_name)
        try:
            with sql_con:
                # Create tables
                sql_con.execute('''CREATE TABLE IF NOT EXISTS {0}
                    (id integer PRIMARY KEY AUTOINCREMENT,
                     uid text,
                     timestamp integer,
                     transport text,
                     subject text,
                     target text,
                     transportTarget text,
                     repliesTo text
                    )'''.format(PROBE_CHANNEL_MSG_SEND))

                sql_con.execute('''CREATE TABLE IF NOT EXISTS {0}
                    (id integer PRIMARY KEY AUTOINCREMENT,
                     uid text,
                     timestamp integer,
                     transport text,
                     subject text,
                     source text,
                     transportSource text,
                     repliesTo text
                    )'''.format(PROBE_CHANNEL_MSG_RECV))

                sql_con.execute('''CREATE TABLE IF NOT EXISTS {0}
                    (uid text PRIMARY KEY,
                     content BLOB
                    )'''.format(PROBE_CHANNEL_MSG_CONTENT))

                sql_con.execute('''CREATE TABLE IF NOT EXISTS http_multicast
                    (id integer PRIMARY KEY AUTOINCREMENT,
                     timestamp integer,
                     uid text,
                     event text
                    )''')
        finally:
            sql_con.close()

    def __convert_timestamp(self, data):
        """
        Converts in-place the timestamp in the given dictionary (if any) from
        float (second-based) to integer (millisecond-based)

        :param data: Data to be stored in a channel
        """
        try:
            timestamp = data['timestamp']
        except KeyError:
            # No timestamp in data: do nothing
            return data
        else:
            # Copy dictionary and set the new time stamp
            new_data = data.copy()
            new_data['timestamp'] = int(timestamp * 1000)
            return new_data

    def store(self, channel, data):
        """
        Stores data to the given channel

        :param channel: Channel where to store data
        :param data: A dictionary of data to be stored
        """
        sql_con = sqlite3.connect(self._db_name)
        try:
            if channel in CHANNEL_FIELDS:
                # Convert timestamp
                filtered_data = self.__convert_timestamp(data)

                # Prepare the request
                # Channel names are well defined => no need to escape (for now)
                sql = '''INSERT INTO {0}({1}) values ({2})''' \
                    .format(channel, ",".join(CHANNEL_FIELDS[channel]),
                            ",".join(CHANNEL_VALUES[channel]))

                try:
                    with sql_con:
                        # Run it
                        sql_con.execute(sql, filtered_data)
                except sqlite3.IntegrityError as ex:
                    # Error inserting data
                    if channel == PROBE_CHANNEL_MSG_CONTENT:
                        # Not a harmful error
                        _logger.debug("Error inserting data in table %s: %s",
                                      channel, ex)
        except:
            _logger.exception("Error inserting data in table %s", channel)
            raise
        finally:
            sql_con.close()
