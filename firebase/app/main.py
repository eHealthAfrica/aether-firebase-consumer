#!/usr/bin/env python

# Copyright (C) 2018 by eHealth Africa : http://www.eHealthAfrica.org
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

import contextlib
import errno
import os
import json
import logging
import signal
import sys
from time import sleep

from aet.consumer import KafkaConsumer
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as CFS
from firebase_admin import db as RTDB

EXCLUDED_TOPICS = ['__confluent.support.metrics']

# where in FB-RTDB is the head of config?
AETHER_CONFIG_FIREBASE_PATH = os.env['AETHER_CONFIG_FIREBASE_PATH']
# credentials to the db
AETHER_FB_CREDENTIAL_PATH = os.env['AETHER_FB_CREDENTIAL_PATH']
# instance url
AETHER_FB_URL = os.env['AETHER_FB_URL']

class FirebaseConsumer(object):

    def __init__(self):
        pass

    def subscribe_to_config(self):
        pass

    def handle_config_update(self, config):
        pass

if __name__ == "__main__":
    viewer = FirebaseConsumer()
