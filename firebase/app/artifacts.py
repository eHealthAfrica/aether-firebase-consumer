#!/usr/bin/env python

# Copyright (C) 2019 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
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

import fnmatch
from time import sleep
from typing import (
    Any,
    Callable,
    List,
    Mapping
)

from confluent_kafka import KafkaException

# Firebase
import firebase_admin
from firebase_admin import credentials as firebase_credentials
# from firebase_admin import firestore as CFS  # TODO on CFS implementation
# from firebase_admin import db as RTDB


# Consumer SDK
from aet.exceptions import ConsumerHttpException
from aet.job import BaseJob, JobStatus
from aet.kafka import KafkaConsumer, FilterConfig, MaskConfig
from aet.logger import callback_logger, get_logger
from aet.resource import BaseResource, lock

# Aether python lib
# from aether.python.avro.schema import Node

from app.config import get_consumer_config, get_kafka_config
from app.fixtures import schemas

from app import utils
from app.helpers import MessageHandlingException

LOG = get_logger('artifacts')
CONSUMER_CONFIG = get_consumer_config()
KAFKA_CONFIG = get_kafka_config()


class FirebaseInstance(BaseResource):
    schema = schemas.FB_INSTANCE
    jobs_path = '$.firebase'
    name = 'firebase'
    public_actions = BaseResource.public_actions + [
        'test_connection'
    ]

    session: firebase_admin.App = None

    @lock
    def get_session(self):
        if self.session:
            return self.session
        name = self.self.definition['name']
        credentials = firebase_credentials(self.self.definition['credential'])
        self.session = firebase_admin.App(
            name,
            credentials,
        )
        self.get_rtdb()
        self.get_cloud_firestore()
        return self.session

    def get_rtdb(self):
        if self.rtdb:
            return self.rtdb
        # get RTDB
        self.rtdb = firebase_admin.db.reference(app=self.session)
        return self.rtdb
        pass

    def get_cloud_firestore(self):
        if self.cloud_firestore:
            return self.cloud_firestore
        self.cloud_firestore = firebase_admin.firestore.client(app=self.session)
        return self.cloud_firestore

    def test_connection(self, *args, **kwargs):
        try:
            pass
        except Exception as err:
            raise ConsumerHttpException(err, 500)

    # def check_remote_msg_needs_update(self, _id, msg):
    #     new_hash = utils.hash(msg)
    #     old_hash = self.get_remote_hash(_id)
    #     if not old_hash:
    #         return
    #     if new_hash == old_hash:
    #         raise MessageHandlingException(
    #             f'Msg in {self.name} with id :'
    #             f' {_id} is already consistent with copy in Firebase')

    def write_rtdb(self, msg):
        try:
            rtdb = self.get_rtdb()
            _id = self.get_message_id(msg)
            self.check_remote_msg_needs_update(_id, msg)  # Throws MHE if already consistent
            msg_hash = utils.hash(msg)
            # Set new hash
            self.set_remote_hash(_id, msg_hash)
            # Set new message
            ref = rtdb.reference(f'{self.target_path}/{_id}')
            ref.set(msg)

        except MessageHandlingException as nominal_misbehavior:
            LOG.debug(nominal_misbehavior)
        except Exception as bad_err:
            LOG.error(bad_err)

    # def get_remote_hash(self, _id):
    #     rtdb = self.get_rtdb()
    #     ref = rtdb.reference(f'{self.hash_path}/{_id}')
    #     return ref.get()

    # def set_remote_hash(self, _id, hash):
    #     rtdb = self.get_rtdb()
    #     ref = rtdb.reference(f'{self.hash_path}/{_id}')
    #     ref.set(hash)


class Subscription(BaseResource):
    schema = schemas.SUBSCRIPTION
    jobs_path = '$.subscription'
    name = 'subscription'

    def _handles_topic(self, topic, tenant):
        topic_str = self.definition.topic_pattern
        # remove tenant information
        no_tenant = topic.lstrip(f'{tenant}.')
        return fnmatch.fnmatch(no_tenant, topic_str)


class FirebaseJob(BaseJob):
    name = 'job'
    # Any type here needs to be registered in the API as APIServer._allowed_types
    _resources = [FirebaseInstance, Subscription]
    schema = schemas.FB_JOB

    public_actions = BaseJob.public_actions + [
        'get_logs',
        'list_topics',
        'list_subscribed_topics'
    ]
    # publicly available list of topics
    subscribed_topics: dict
    log_stack: list
    log: Callable  # each job instance has it's own log object to keep log_stacks -> user reportable

    consumer: KafkaConsumer = None
    # processing artifacts
    _indices: dict
    _schemas: dict
    _previous_topics: list
    _subscriptions: List[Subscription]

    def _setup(self):
        self.subscribed_topics = {}
        self._schemas = {}
        self._subscriptions = []
        self._previous_topics = []
        self.log_stack = []
        self.log = callback_logger('JOB', self.log_stack, 100)
        self.group_name = f'{self.tenant}.firebaseconsumer.{self._id}'
        self.sleep_delay: float = 0.5
        self.report_interval: int = 100
        args = {k.lower(): v for k, v in KAFKA_CONFIG.copy().items()}
        args['group.id'] = self.group_name
        LOG.debug(args)
        self.consumer = KafkaConsumer(**args)

    def _job_firebase(self, config=None) -> FirebaseInstance:
        if config:
            fb = self.get_resources('firebase', config)
            if not fb:
                raise ConsumerHttpException('No Firebase associated with Job', 400)
            self._firebase = fb
        return self._firebase

    def _job_subscriptions(self, config=None) -> List[Subscription]:
        if config:
            subs = self.get_resources('subscription', config)
            if not subs:
                raise ConsumerHttpException('No Subscriptions associated with Job', 400)
            self._subscriptions = subs
        return self._subscriptions

    def _job_subscription_for_topic(self, topic):
        return next(iter(
            sorted([
                i for i in self._job_subscriptions()
                if i._handles_topic(topic, self.tenant)
            ])),
            None)

    def _test_connections(self, config):
        self._job_subscriptions(config)
        self._job_firebase(config).test_connection()  # raises CHE
        return True

    def _get_messages(self, config):
        try:
            self.log.debug(f'{self._id} checking configurations...')
            self._test_connections(config)
            subs = self._job_subscriptions()
            self._handle_new_subscriptions(subs)
            self.log.debug(f'Job {self._id} getting messages')
            return self.consumer.poll_and_deserialize(
                timeout=5,
                num_messages=1)  # max
        except ConsumerHttpException as cer:
            # don't fetch messages if we can't post them
            self.log.debug(f'Job not ready: {cer}')
            self.status = JobStatus.RECONFIGURE
            sleep(self.sleep_delay * 10)
            return []
        except Exception as err:
            import traceback
            traceback_str = ''.join(traceback.format_tb(err.__traceback__))
            self.log.critical(f'unhandled error: {str(err)} | {traceback_str}')
            raise err
            sleep(self.sleep_delay)
            return []

    def _handle_new_subscriptions(self, subs):
        old_subs = list(sorted(set(self.subscribed_topics.values())))
        for sub in subs:
            pattern = sub.definition.topic_pattern
            # only allow regex on the end of patterns
            if pattern.endswith('*'):
                self.subscribed_topics[sub.id] = f'^{self.tenant}.{pattern}'
            else:
                self.subscribed_topics[sub.id] = f'{self.tenant}.{pattern}'
        new_subs = list(sorted(set(self.subscribed_topics.values())))
        _diff = list(set(old_subs).symmetric_difference(set(new_subs)))
        if _diff:
            self.log.info(f'{self.tenant} added subs to topics: {_diff}')
            self.consumer.subscribe(new_subs, on_assign=self._on_assign)

    def _handle_messages(self, config, messages):
        self.log.debug(f'{self.group_name} | reading {len(messages)} messages')
        count = 0
        for msg in messages:
            topic = msg.topic
            schema = msg.schema
            if schema != self._schemas.get(topic):
                self.log.info(f'{self._id} Schema change on {topic}')
                self._update_topic(topic, schema)
                self._schemas[topic] = schema
            else:
                self.log.debug('Schema unchanged.')
            self.submit(msg.value, topic)
            count += 1
        self.log.info(f'processed {count} {topic} docs in tenant {self.tenant}')

    # called when a subscription causes a new assignment to be given to the consumer
    def _on_assign(self, *args, **kwargs):
        assignment = args[1]
        for _part in assignment:
            if _part.topic not in self._previous_topics:
                self.log.info(f'New topic to configure: {_part.topic}')
                self._apply_consumer_filters(_part.topic)
                self._previous_topics.append(_part.topic)

    def _apply_consumer_filters(self, topic):
        self.log.debug(f'{self._id} applying filter for new topic {topic}')
        subscription = self._job_subscription_for_topic(topic)
        if not subscription:
            self.log.error(f'Could not find subscription for topic {topic}')
            return
        try:
            opts = subscription.definition.topic_options
            _flt = opts.get('filter_required', False)
            if _flt:
                _filter_options = {
                    'check_condition_path': opts.get('filter_field_path', ''),
                    'pass_conditions': opts.get('filter_pass_values', []),
                    'requires_approval': _flt
                }
                self.log.info(_filter_options)
                self.consumer.set_topic_filter_config(
                    topic,
                    FilterConfig(**_filter_options)
                )
            mask_annotation = opts.get('masking_annotation', None)
            if mask_annotation:
                _mask_options = {
                    'mask_query': mask_annotation,
                    'mask_levels': opts.get('masking_levels', []),
                    'emit_level': opts.get('masking_emit_level')
                }
                self.log.info(_mask_options)
                self.consumer.set_topic_mask_config(
                    topic,
                    MaskConfig(**_mask_options)
                )
            self.log.info(f'Filters applied for topic {topic}')
        except AttributeError as aer:
            self.log.error(f'No topic options for {subscription.id}| {aer}')

    def _name_from_topic(self, topic):
        return topic.lstrip(f'{self.tenant}.')

    def _update_topic(self, topic, schema: Mapping[Any, Any]):
        self.log.debug(f'{self.tenant} is updating topic: {topic}')
        # subscription = self._job_subscription_for_topic(topic)
        # node: Node = Node(schema)
        self.log.debug('getting index')
        # es_index = index_handler.get_es_index_from_subscription(
        #     subscription.definition.get('es_options'),
        #     name=self._name_from_topic(topic),
        #     tenant=self.tenant.lower(),
        #     schema=node
        # )
        # self.log.debug(f'index {es_index}')
        # TODO Alias topic -> Firebase Type name
        # alias_request = subscription.definition.get('fb_options', {}).get('alias_name')
        # if alias_request:
        #     alias = f'{alias_request}'.lower()
        # else:
        #     alias = index_handler.get_alias_from_namespace(node.namespace)
        # Try to add the indices / ES alias
        # TODO handle any updates to Firebase Required... ? Any?
        # updated_firebase = self._topic_update
        # if updated_firebase:
        #     self.log.info(
        #         f'Registered firebase topic change for {self.tenant}'
        #     )
        # else:
        #     self.log.info(
        #         f'Registered firebase topic did not need update.'
        #     )

    def submit(self, doc, topic_name):
        pass

    # public
    def list_topics(self, *args, **kwargs):
        '''
        Get a list of topics to which the job can subscribe.
        You can also use a wildcard at the end of names like:
        Name* which would capture both Name1 && Name2, etc
        '''
        timeout = 5
        try:
            md = self.consumer.list_topics(timeout=timeout)
        except (KafkaException) as ker:
            raise ConsumerHttpException(str(ker) + f'@timeout: {timeout}', 500)
        topics = [
            str(t).split(f'{self.tenant}.')[1] for t in iter(md.topics.values())
            if str(t).startswith(self.tenant)
        ]
        return topics

    # public
    def list_subscribed_topics(self, *arg, **kwargs):
        '''
        A List of topics currently subscribed to by this job
        '''
        return list(self.subscribed_topics.values())

    # public
    def get_logs(self, *arg, **kwargs):
        '''
        A list of the last 100 log entries from this job in format
        [
            (timestamp, log_level, message),
            (timestamp, log_level, message),
            ...
        ]
        '''
        return self.log_stack[:]