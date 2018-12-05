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
import json
import logging
import os
import signal
import sys

from aet.consumer import KafkaConsumer
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as CFS
from firebase_admin import db as RTDB

from healthcheck import HealthcheckServer
import settings
import utils

CSET = settings.get_consumer_config()
KSET = settings.get_kafka_config()

# credentials to the db
AETHER_FB_CREDENTIAL_PATH = '/opt/firebase/cert.json'  # mounted into volume
# AETHER_FB_HASH_PATH = CSET['AETHER_FB_HASH_PATH'] # TODO

LOG = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        '%(asctime)s [FIREBASE] %(levelname)-8s %(message)s'))
LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)


class FirebaseConsumer(object):

    def __init__(self):
        self.killed = False
        self.workers = {'cfs': {}, 'rtdb': {}}
        self.config = None
        LOG.debug('Initializing Firebase Connection')
        self.authenticate()
        self.subscribe_to_config()
        signal.signal(signal.SIGTERM, self.kill)
        signal.signal(signal.SIGINT, self.kill)
        self.serve_healthcheck(CSET['AETHER_FB_EXPOSE_PORT'])
        self.worker = threading.Thread(target=self.run, args=())

    def authenticate(self):
        cred = credentials.Certificate(AETHER_FB_CREDENTIAL_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': CSET['AETHER_FB_URL']
        })
        LOG.debug('Authenticated.')

    def update_config(self, keys, value):
        self.config = utils.replace_nested(self.config, keys, value)
        LOG.debug('Configuration updated.')

    def subscribe_to_config(self):
        LOG.debug('Subscribing to changes.')
        RTDB.reference(CSET['AETHER_CONFIG_FIREBASE_PATH']).listen(self.handle_config_update)

    def kill(self, *args, **kwargs):
        self.killed = True
        LOG.debug('Firebase Consumer caught kill signal.')
        self.healthcheck.stop()
        self.kill_workers()
        
    def kill_workers(self):
        for db, workers in self.workers.items():
            for controller in workers:
                LOG.debug(f'Signaling shutdown to {controller.name}.')
                controller.kill()

    def safe_sleep(self, dur):
        # keeps shutdown time low by yielding during sleep and checking if killed.
        for x in range(dur):
            if not self.killed:
                sleep(1)        

    def serve_healthcheck(self, port):
        self.healthcheck = HealthcheckServer(port)
        self.healthcheck.start()

    def handle_config_update(self, event=None):
        path = event.path
        data = event.data
        LOG.debug(f'Change in config event; {event}, {data}, {path}')
        if not self.config:
            self.config = data
            LOG.debug('First config set.')
            self.initialize_workers()
            return 
        path_parts = [i for i in path.split('/') if i]  # filter blank path elements
        self.update_config(path_parts, data)
        if path_parts[0] is not '_tracked':
            LOG.debug('Changes do not effect tracked entities')
            return
        else:
            conf_type, db_type, name = path_parts[0:3]
            LOG.debug(f'Propogating change to {db_type} -> {name}')
            config = self.config \
                                .get('_tracked') \
                                .get(db_type) \
                                .get(name)
            if not name in self.workers[db_type].keys():
                LOG.info(f'Config for NEW worker {name} in db {db_type}')
                if db_type == 'rtdb':
                    self.workers['rtdb'][name] = FirebaseWorker(name, config, self)  # RTDBWorker(name, config, self)
                # TODO when CFS is implemented
                # else:
                #     self.workers['cfs'][name] = CFSWorker(name, config, self)
            else:
                LOG.info(f'Updating config for worker {name} in db {db_type}')
                workers[db_type][name].update(config)


    def initialize_workers(self):
        cfs = self.config.get('_tracked', {}).get('cfs', {})
        rtdb = self.config.get('_tracked', {}).get('rtdb', {})
        # TODO when CFS is implemented
        # for name, config in cfs.items():
        #     self.workers['cfs'][name] = CFSWorker(name, config, self)
        for name, config in rtdb.items():
            self.workers['rtdb'][name] = FirebaseWorker(name, config, self)  # TODO RTDBWorker(name, config, self)

    def run(self):
        while not self.killed:
            LOG.debug('FirebaseConsumer checking worker status')
            has_workers = False
            for db, workers in self.workers.items():
                for name, worker in workers:
                    LOG.debug(f'child {name} status : {worker.status}')
                    has_workers = True
            if not has_workers:
                LOG.debug('FirebaseConsumer has no registered workers.')
            self.safe_sleep(10)


class WorkerStatus(enum.Enum):

    RUNNING = 0
    STARTING = 1
    PAUSED = 2
    LOCKED = 3
    RECONFIGURE = 4
    DEAD = 5


class FirebaseWorker(object):

    def __init__(self, name, config, parent):
        LOG.debug(f'New worker: {name}')
        self.consumer_max_records = 10
        self.consumer_timeout = 1000  # MS
        self.topic = None
        self.worker = None
        self.status = WorkerStatus.STARTING
        self.name = name
        self.config = config
        self.parent = parent
        self.start()

    # Main loop control

    def start(self):
        self.status = WorkerStatus.RECONFIGURE
        self.worker = threading.Thread(target=self.run, args=())

    def run(self):
        LOG.debug(f'Worker thread spawned for {self.name}')
        while self.status is not WorkerStatus.DEAD:
            try:
                if self.status is WorkerStatus.RECONFIGURE:
                    LOG.debug(f'Thread for {self.name} is reconfiguring.')
                    self.configure()
                    continue
                elif self.status is not WorkerStatus.RUNNING:
                    LOG.debug(f'Thread for {self.name} paused with status {self.status}')
                    self.sleep(10)
                    continue
                else:
                    LOG.debug(f'{self.name} polling for messages on topic {self.topic}')
                    package = self.get_messages()
                    if package:
                        self.handle_messages(messages)
                    else:
                        LOG.debug(f'{self.name} has no new messages')
                        self.sleep(3)
            except Exception err:
                LOG.error(f'Worker thread for {self.name} died!')
                self.status = WorkerStatus.DEAD
                raise err
        LOG.debug(f'{self.name} exiting.')

    def sleep(self, dur):
        for i in range(dur):
            try:
                if self.status is not in [
                                         WorkerStatus.DEAD,
                                         WorkerStatus.RECONFIGURE
                                         ] and not self.parent.killed:
                    sleep(1)
                else:
                    return
            except AttributeError:  # Parent is likely dead
                LOG(f'Parent of {self.name} died while child was sleeping. Exiting.')
                self.status = WorkerStatus.DEAD

    #
    # Configuration management
    #

    #Handle Updates from parent
    def update(self, config):
        LOG.debug(f'Update to config in {self.name}')
        self.config = config
        self.status = WorkerStatus.RECONFIGURE
        LOG.debug(f'{self.name} will configure on next cycle')

    # Configuration details may vary for each DB type. Subclasses should override this.
    def configure(self, config):
        try:
            LOG.debug(f'{self.name} replacing old config hash {self.config_hash}')
        except AttributeError:
            LOG.debug(f'{self.name} does not have a previous config hash')
        self.config_hash = utils.hash(config)
        LOG.debug(f'{self.name} has new config hash: {self.config_hash}')
        self.consumer = self.get_consumer()

    # Get a consumer instance based on the current configuration
    def get_consumer(self):
        try:
            self.consumer.close()  # close existing consumer if it exists
        except AttributeError:
            pass
        args = kafka_config.copy()
        args['group_id'] = self.group_name
        try:
            self.consumer = KafkaConsumer(**args)
            self.consumer.subscribe([self.topic])
            log.debug('Consumer %s subscribed on topic: %s @ group %s' %
                      (self.index, self.topic, self.group_name))

    #
    # Control status mechanisms
    #

    def pause(self):
        self.status = WorkerStatus.PAUSED

    def resume(self):
        self.status = WorkerStatus.RUNNING

    def lock(self):
        self.status = WorkerStatus.LOCKED

    

    def kill(self):
        LOG.debug(f'Thread for {self.name} killed.')
        self.status = WorkerStatus.DEAD

    #
    # Message Handling
    #

    def get_messages(self):
        try:
            return self.consumer.poll_and_deserialize(
                    timeout_ms=self.consumer_timeout,
                    max_records=self.consumer_max_records)
        except TypeError as ter:  # consumer is likely None
            LOG.error(f'{self.name} died with error {ter}')
            self.status = WorkerStatus.DEAD

    # Base implementation of handle messages is only for testing / debugging purposes. 
    # Should be overridden in subclasses.
    def handle_messages(self, messages):
        for parition_key, packages in new_messages.items():
            for package in packages:
                schema = package.get('schema')
                LOG.debug(f'{self.name} schema: {schema}')
                messages = package.get('messages')
                LOG.debug(f'{self.name} messages #{len(messages)}')
                # for x, msg in enumerate(messages):
                #     pass                       


class RTDBWorker(FirebaseWorker):
    
    def configure(self):
        pass

    def handle_messages(self, messages):
        pass

    def submit(self, msg):
        pass


class CFSWorker(FirebaseWorker):
    
    def configure(self):
        pass

    def handle_messages(self, messages):
        pass

    def submit(self, msg):
        pass

if __name__ == "__main__":
    viewer = FirebaseConsumer()
