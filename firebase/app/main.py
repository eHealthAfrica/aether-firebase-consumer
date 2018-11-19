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
AETHER_FB_CREDENTIAL_PATH = '/opt/firebase/cert.json'  # TODO Add path?
AETHER_FB_HASH_PATH = os.environ['AETHER_FB_HASH_PATH']
# instance url
AETHER_FB_URL = os.environ['AETHER_FB_URL']
# this Aether server is called in firebase
AETHER_SERVER_ALIAS= os.environ['AETHER_SERVER_ALIAS']

LOG = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        '%(asctime)s [FIREBASE] %(levelname)-8s %(message)s'))
LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)


class FirebaseConsumer(object):

    def __init__(self):
        self.cfs_workers = {}
        self.rtdb_workers = {}
        self.config = None
        LOG.debug('Initializing Firebase Connection')
        self.authenticate()
        self.subscribe_to_config()

    def authenticate(self):
        cred = credentials.Certificate(AETHER_FB_CREDENTIAL_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': AETHER_FB_URL
        })
        LOG.debug('Authenticated.')

    def update_config(self, keys, value):
        self.config = utils.replace_nested(self.config, keys, value)

    def subscribe_to_config(self):
        LOG.debug('Subscribing to changes.')
        RTDB.reference(AETHER_CONFIG_FIREBASE_PATH).listen(self.handle_config_update)

    def handle_config_update(self, event=None):
        path = event.path
        data = event.data
        LOG.debug(f'Change in config event; {event}, {data}, {path}')
        if not self.config:
            self.config = data
            LOG.debug('First config set.')
            return
        for k, v in event.__dict__.items():
            LOG.debug(f'{k} : {v}')
        path_parts = path.split('/')
        if len(path_parts) < 3:
            LOG.debug('Changes do not effect data tracked entities')
            return


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
