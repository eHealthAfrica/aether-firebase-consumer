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
    'url': 'url-to-firebase',               # URL of FB instance
    'credential': {'json': 'doc'},          # credentials document
    'firebase_config_path': '/path',        # path of config in Firebase
    'aether_server_alias': 'server-name',   # alias of the Aether instance in FB config
    'hash_path': '/hashes'                  # path of Hashes
}


SUBSCRIPTION = {
    'id': 'sub-test',
    'name': 'Test Subscription',
    'topic_pattern': '*',
    'topic_options': {
        'masking_annotation': '@aether_masking',  # schema key for mask level of a field
        'masking_levels': ['public', 'private'],  # classifications
        'masking_emit_level': 'public',           # emit from this level ->
        'filter_required': True,                 # filter on a message value?
        'filter_field_path': 'operational_status',    # which field?
        'filter_pass_values': ['operational'],             # what are the passing values?
    },
    'fb_options': {
        'alias_name': 'test'
    }
}

JOB = {
    'id': 'default',
    'name': 'Default ES Consumer Job',
    'firebase': 'default',
    'subscription': ['sub-test']
}
