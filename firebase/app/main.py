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

import utils

EXCLUDED_TOPICS = ['__confluent.support.metrics']

# where in FB-RTDB is the head of config?
AETHER_CONFIG_FIREBASE_PATH = os.environ['AETHER_CONFIG_FIREBASE_PATH']
# credentials to the db
AETHER_FB_CREDENTIAL_PATH = os.environ['AETHER_FB_CREDENTIAL_PATH']
AETHER_FB_HASH_PATH = os.environ['AETHER_FB_HASH_PATH']
# instance url
AETHER_FB_URL = os.environ['AETHER_FB_URL']
# this Aether server is called in firebase
AETHER_SERVER_ALIAS= os.environ['AETHER_SERVER_ALIAS']

LOG = logging.getLogger('FirebaseConsumer')
LOG.setLevel(logging.DEBUG)

class FirebaseConsumer(object):

    def __init__(self):
        self.cfs_workers = {}
        self.rtdb_workers = {}

        self.authenticate()
        self.handle_config_update(
            data=self.get_config(),
            path='/')
        self.subscribe_to_config()


    def authenticate(self):
        cred = credentials.Certificate(AETHER_FB_CREDENTIAL_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': AETHER_FB_URL
        })

    def get_config(self):
        ref = RTDB.reference(AETHER_CONFIG_FIREBASE_PATH)
        config = ref.get()
        logging.debug(f'Initial configuration: {config}')
        return config

    def subscribe_to_config(self):
        RTDB.reference(AETHER_CONFIG_FIREBASE_PATH).listen(self.handle_config_update)

    def handle_config_update(self, event=None, data=None, path=None):
        path = path or event.path
        data = data or event.data


class FirebaseWorker(object):

    def __init__(self, config):
        self.name = name
        self.config = config
        self.configure(self.config)

    def check_config_update(self, config):
        new_hash = utils.hash(config)
        if new_hash is self.config_hash:
            return
        else:
            self.configure(config)

    def configure(self, config):
        self.config_hash = utils.hash(config)

    def stop(self):
        pass

    def start(self):
        pass

class RTDBWorker(FirebaseWorker):
    pass

class CFSWorker(FirebaseWorker):
    pass

if __name__ == "__main__":
    viewer = FirebaseConsumer()
