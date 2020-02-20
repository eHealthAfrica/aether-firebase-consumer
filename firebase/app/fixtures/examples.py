#!/usr/bin/env python

# Copyright (C) 2020 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


FB_INSTANCE = {
    'id': 'default',
    'name': 'the default instance',
    'rtdb_project': 'test-project',
    'cfs_project': 'cfsproject',
    'url': 'local-test',                   # URL of FB instance
    'credential': {'json': 'doc'},              # credentials document
    'aether_server_alias': 'test-server',       # alias of the Aether instance in FB config
    'firebase_config_path': '_aether/rules',    # path of config in RTDB
    'hash_path': '_aether/hashes'               # path of Hashes in RTDB
}


SUBSCRIPTION = {
    'id': 'sub-test',
    'name': 'Test Subscription',
    'topic_pattern': '*',
    'topic_options': {
        'masking_annotation': '@aether_masking',  # schema key for mask level of a field
        'masking_levels': ['public', 'private'],  # classifications
        'masking_emit_level': 'public',           # emit from this level ->
        'filter_required': False,                 # filter on a message value?
        'filter_field_path': 'operational_status',    # which field?
        'filter_pass_values': ['operational'],             # what are the passing values?
    },
    'fb_options': {
        'sync_mode': 'forward',                    # enum(forward / sync/ consume)
        'target_path': '_aether/entities/{topic}'  # can use {topic} to set via topic name,
    }                                              # or hard-code like a/b/c
}

JOB = {
    'id': 'default',
    'name': 'Default Firebase Consumer Job',
    'firebase': 'default',
    'subscription': ['sub-test']
}
