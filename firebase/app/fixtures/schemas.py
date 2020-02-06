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

FB_INSTANCE = '''
{
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "The Root Schema",
  "required": [
    "id",
    "name",
    "url",
    "credential",
    "aether_server_alias",
    "firebase_config_path",
    "hash_path"
  ],
  "properties": {
    "id": {
      "$id": "#/properties/id",
      "type": "string",
      "title": "The Id Schema",
      "default": "",
      "examples": [
        "default"
      ],
      "pattern": "^(.*)$"
    },
    "name": {
      "$id": "#/properties/name",
      "type": "string",
      "title": "The Name Schema",
      "default": "",
      "examples": [
        "the default instance"
      ],
      "pattern": "^(.*)$"
    },
    "url": {
      "$id": "#/properties/url",
      "type": "string",
      "title": "The Url Schema",
      "default": "",
      "examples": [
        "local-test"
      ],
      "pattern": "^(.*)$"
    },
    "rtdb_project": {
      "$id": "#/properties/rtdb_project",
      "type": "string",
      "title": "The Url Schema",
      "default": "",
      "examples": [
        "test_rtdb"
      ],
      "pattern": "^(.*)$"
    },
    "cfs_project": {
      "$id": "#/properties/cfs_project",
      "type": "string",
      "title": "The Url Schema",
      "default": "",
      "examples": [
        "testcfs"
      ],
      "pattern": "^(.*)$"
    },
    "credential": {
      "$id": "#/properties/credential",
      "type": "object",
      "title": "The Credential Schema",
      "properties": {}
    },
    "aether_server_alias": {
      "$id": "#/properties/aether_server_alias",
      "type": "string",
      "title": "The Aether_server_alias Schema",
      "default": "",
      "examples": [
        "test-server"
      ],
      "pattern": "^(.*)$"
    },
    "firebase_config_path": {
      "$id": "#/properties/firebase_config_path",
      "type": "string",
      "title": "The Firebase_config_path Schema",
      "default": "",
      "examples": [
        "_aether/rules"
      ],
      "pattern": "^(.*)$"
    },
    "hash_path": {
      "$id": "#/properties/hash_path",
      "type": "string",
      "title": "The Hash_path Schema",
      "default": "",
      "examples": [
        "_aether/hashes"
      ],
      "pattern": "^(.*)$"
    }
  }
}
'''

SUBSCRIPTION = '''
{
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "The Root Schema",
  "required": [
    "id",
    "name",
    "topic_pattern"
  ],
  "properties": {
    "id": {
      "$id": "#/properties/id",
      "type": "string",
      "title": "The Id Schema",
      "default": "",
      "examples": [
        "the id for this resource"
      ],
      "pattern": "^(.*)$"
    },
    "name": {
      "$id": "#/properties/name",
      "type": "string",
      "title": "The Name Schema",
      "default": "",
      "examples": [
        "a nice name for this resource"
      ],
      "pattern": "^(.*)$"
    },
    "topic_pattern": {
      "$id": "#/properties/topic_pattern",
      "type": "string",
      "title": "The Topic_pattern Schema",
      "default": "",
      "examples": [
        "source topic for data i.e. gather*"
      ],
      "pattern": "^(.*)$"
    },
    "topic_options": {
      "$id": "#/properties/topic_options",
      "type": "object",
      "title": "The Topic_options Schema",
      "anyOf": [
        {
          "required": [
            "masking_annotation"
          ]
        },
        {
          "required": [
            "filter_required"
          ]
        }
      ],
      "dependencies": {
        "filter_required": [
          "filter_field_path",
          "filter_pass_values"
        ],
        "masking_annotation": [
          "masking_levels",
          "masking_emit_level"
        ]
      },
      "properties": {
        "masking_annotation": {
          "$id": "#/properties/topic_options/properties/masking_annotation",
          "type": "string",
          "title": "The Masking_annotation Schema",
          "default": "",
          "examples": [
            "@aether_masking"
          ],
          "pattern": "^(.*)$"
        },
        "masking_levels": {
          "$id": "#/properties/topic_options/properties/masking_levels",
          "type": "array",
          "title": "The Masking_levels Schema",
          "items": {
            "$id": "#/properties/topic_options/properties/masking_levels/items",
            "title": "The Items Schema",
            "examples": [
              "private",
              "public"
            ],
            "pattern": "^(.*)$"
          }
        },
        "masking_emit_level": {
          "$id": "#/properties/topic_options/properties/masking_emit_level",
          "type": "string",
          "title": "The Masking_emit_level Schema",
          "default": "",
          "examples": [
            "public"
          ],
          "pattern": "^(.*)$"
        },
        "filter_required": {
          "$id": "#/properties/topic_options/properties/filter_required",
          "type": "boolean",
          "title": "The Filter_required Schema",
          "default": false,
          "examples": [
            false
          ]
        },
        "filter_field_path": {
          "$id": "#/properties/topic_options/properties/filter_field_path",
          "type": "string",
          "title": "The Filter_field_path Schema",
          "default": "",
          "examples": [
            "some.json.path"
          ],
          "pattern": "^(.*)$"
        },
        "filter_pass_values": {
          "$id": "#/properties/topic_options/properties/filter_pass_values",
          "type": "array",
          "title": "The Filter_pass_values Schema",
          "items": {
            "$id": "#/properties/topic_options/properties/filter_pass_values/items",
            "title": "The Items Schema",
            "examples": [
              false
            ]
          }
        }
      }
    },
    "fb_options": {
      "$id": "#/properties/es_options",
      "type": "object",
      "title": "The Firebase Options Schema",
      "required": [],
      "properties": {
        "target_path": {
          "$id": "#/properties/es_options/properties/target_path",
          "type": "string",
          "title": "Target path in Firebase",
          "default": "",
          "examples": [
            "test"
          ],
          "pattern": "^(.*)$"
        },
        "sync_mode": {
          "$id": "#/properties/es_options/properties/sync_mode",
          "type": "string",
          "enum": ["forward"],
          "title": "Mode of transport from Aether -> Firebase",
          "default": "forward",
          "examples": [
            "forward"
          ],
          "pattern": "^(.*)$"
        }
      }
    }
  }
}
'''

FB_JOB = '''
{
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "The Root Schema",
  "required": [
    "id",
    "name",
    "firebase"
  ],
  "properties": {
    "id": {
      "$id": "#/properties/id",
      "type": "string",
      "title": "The Id Schema",
      "default": "",
      "examples": [
        "the id for this resource"
      ],
      "pattern": "^(.*)$"
    },
    "name": {
      "$id": "#/properties/name",
      "type": "string",
      "title": "The Name Schema",
      "default": "",
      "examples": [
        "a nice name for this resource"
      ],
      "pattern": "^(.*)$"
    },
    "firebase": {
      "$id": "#/properties/firebase",
      "type": "string",
      "title": "The Firebase Schema",
      "default": "",
      "examples": [
        "id of the Firebase Instance to use"
      ],
      "pattern": "^(.*)$"
    },
    "subscription": {
      "$id": "#/properties/subscription",
      "type": "array",
      "title": "The Subscriptions Schema",
      "items": {
        "$id": "#/properties/subscription/items",
        "type": "string",
        "title": "The Items Schema",
        "default": "",
        "examples": [
          "id-of-sub"
        ],
        "pattern": "^(.*)$"
      }
    }
  }
}
'''
