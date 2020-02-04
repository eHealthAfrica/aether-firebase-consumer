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


import json
import pytest
from time import sleep
from uuid import uuid4

import birdisle
import birdisle.redis

import firebase_admin
import firebase_admin.credentials
from firebase_admin.credentials import ApplicationDefault
from firebase_admin.db import reference as RTDB
from firebase_admin.exceptions import UnavailableError
from google.api_core.exceptions import Unknown as UnknownError
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore_v1.client import Client as CFS
from spavro.schema import parse

from aet.kafka_utils import (
    create_topic,
    delete_topic,
    get_producer,
    get_admin_client,
    # get_broker_info,
    # is_kafka_available,
    produce
)
from aet.helpers import chunk_iterable
from aet.logger import get_logger
# from aet.jsonpath import CachedParser

from aether.python.avro import generation


from app import config, consumer
from app.helpers import RTDB, Firestore

CONSUMER_CONFIG = config.consumer_config
KAFKA_CONFIG = config.kafka_config


LOG = get_logger('FIXTURE')


kafka_server = "kafka-test:29099"


project_name_rtdb = 'rtdb_test_app'
project_name_cfs = 'cfstestapp'  # NO UNDERSCORES ALLOWED!
rtdb_local = CONSUMER_CONFIG.get('FIREBASE_DATABASE_EMULATOR_HOST')
rtdb_name = 'testdb'
rtdb_url = f'http://{rtdb_local}/'
rtdb_ns = f'?ns={rtdb_name}'
rtdb_fq = rtdb_url + rtdb_ns
LOG.info(rtdb_fq)


# pick a random tenant for each run so we don't need to wipe ES.
TS = str(uuid4()).replace('-', '')[:8]
TENANT = f'TEN{TS}'
TEST_TOPIC = 'es_test_topic'

GENERATED_SAMPLES = {}


@pytest.fixture(scope='session')
def rtdb_options():
    yield {
        'databaseURL': rtdb_fq,
        'projectID': project_name_rtdb
    }


@pytest.fixture(scope='session')
def rtdb(rtdb_options):
    app = firebase_admin.initialize_app(
        name=project_name_rtdb,
        credential=ApplicationDefault(),
        options=rtdb_options
    )
    yield RTDB(app)


@pytest.fixture(scope='session')
def cfs():
    return CFS(project_name_cfs, credentials=AnonymousCredentials())


@pytest.mark.unit
@pytest.fixture(scope='session')
def birdisle_server():
    password = config.get_consumer_config().get('REDIS_PASSWORD')
    server = birdisle.Server(f'requirepass {password}')
    yield server
    server.close()


@pytest.mark.unit
@pytest.fixture(scope='session')
def Birdisle(birdisle_server):
    birdisle.redis.LocalSocketConnection.health_check_interval = 0
    password = config.get_consumer_config().get('REDIS_PASSWORD')
    r = birdisle.redis.StrictRedis(server=birdisle_server, password=password)
    r.config_set('notify-keyspace-events', 'KEA')
    return r


# @pytest.mark.integration
@pytest.fixture(scope='session', autouse=True)
def create_remote_kafka_assets(request, sample_generator, *args):
    # @mark annotation does not work with autouse=True.
    if 'integration' not in request.config.invocation_params.args:
        LOG.debug(f'NOT creating Kafka Assets')
        yield None
    else:
        LOG.debug(f'Creating Kafka Assets')
        kafka_security = config.get_kafka_admin_config()
        kadmin = get_admin_client(kafka_security)
        new_topic = f'{TENANT}.{TEST_TOPIC}'
        create_topic(kadmin, new_topic)
        GENERATED_SAMPLES[new_topic] = []
        producer = get_producer(kafka_security)
        schema = parse(json.dumps(ANNOTATED_SCHEMA))
        for subset in sample_generator(max=100, chunk=10):
            GENERATED_SAMPLES[new_topic].extend(subset)
            produce(subset, schema, new_topic, producer)
        yield None  # end of work before clean-up
        LOG.debug(f'deleting topic: {new_topic}')
        delete_topic(kadmin, new_topic)


# raises UnavailableError
def check_app_alive(rtdb, cfs):
    ref = rtdb.path('some/path')
    cref = cfs.collection(u'test2').document(u'adoc')
    return (ref and cref)


@pytest.fixture(scope='session', autouse=True)
def check_local_firebase_readyness(request, rtdb, cfs, *args):
    # @mark annotation does not work with autouse=True
    # if 'integration' not in request.config.invocation_params.args:
    #     LOG.debug(f'NOT Checking for LocalFirebase')
    #     return
    LOG.debug('Waiting for Firebase')
    for x in range(30):
        try:
            check_app_alive(rtdb, cfs)
            LOG.debug(f'Firebase ready after {x} seconds')
            return
        except (UnavailableError, UnknownError):
            sleep(1)

    raise TimeoutError('Could not connect to Firebase for integration test')


@pytest.mark.unit
@pytest.mark.integration
@pytest.fixture(scope='session')
def sample_generator():
    t = generation.SampleGenerator(ANNOTATED_SCHEMA)
    t.set_overrides('geometry.latitude', {'min': 44.754512, 'max': 53.048971})
    t.set_overrides('geometry.longitude', {'min': 8.013135, 'max': 28.456375})
    t.set_overrides('url', {'constant': 'http://ehealthafrica.org'})
    for field in ['beds', 'staff_doctors', 'staff_nurses']:
        t.set_overrides(field, {'min': 0, 'max': 50})

    def _gen(max=None, chunk=None):

        def _single(max):
            if not max:
                while True:
                    yield t.make_sample()
            for x in range(max):
                yield t.make_sample()

        def _chunked(max, chunk):
            return chunk_iterable(_single(max), chunk)

        if chunk:
            yield from _chunked(max, chunk)
        else:
            yield from _single(max)
    yield _gen


ANNOTATED_SCHEMA = {
    'doc': 'MySurvey (title: HS OSM Gather Test id: gth_hs_test, version: 2)',
    'name': 'MySurvey',
    'type': 'record',
    'fields': [
        {
            'doc': 'xForm ID',
            'name': '_id',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey'
        },
        {
            'doc': 'xForm version',
            'name': '_version',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_default_visualization': 'undefined'
        },
        {
            'doc': 'Surveyor',
            'name': '_surveyor',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey'
        },
        {
            'doc': 'Submitted at',
            'name': '_submitted_at',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'dateTime'
        },
        {
            'name': '_start',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'dateTime'
        },
        {
            'name': 'timestamp',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'dateTime'
        },
        {
            'name': 'username',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'name': 'source',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'name': 'osm_id',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Name of Facility',
            'name': 'name',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Address',
            'name': 'addr_full',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Phone Number',
            'name': 'contact_number',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Facility Operator Name',
            'name': 'operator',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Operator Type',
            'name': 'operator_type',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_default_visualization': 'pie',
            '@aether_lookup': [
                {
                    'label': 'Public',
                    'value': 'public'
                },
                {
                    'label': 'Private',
                    'value': 'private'
                },
                {
                    'label': 'Community',
                    'value': 'community'
                },
                {
                    'label': 'Religious',
                    'value': 'religious'
                },
                {
                    'label': 'Government',
                    'value': 'government'
                },
                {
                    'label': 'NGO',
                    'value': 'ngo'
                },
                {
                    'label': 'Combination',
                    'value': 'combination'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'Facility Location',
            'name': 'geometry',
            'type': [
                'null',
                {
                    'doc': 'Facility Location',
                    'name': 'geometry',
                    'type': 'record',
                    'fields': [
                        {
                            'doc': 'latitude',
                            'name': 'latitude',
                            'type': [
                                'null',
                                'float'
                            ],
                            'namespace': 'MySurvey.geometry'
                        },
                        {
                            'doc': 'longitude',
                            'name': 'longitude',
                            'type': [
                                'null',
                                'float'
                            ],
                            'namespace': 'MySurvey.geometry'
                        },
                        {
                            'doc': 'altitude',
                            'name': 'altitude',
                            'type': [
                                'null',
                                'float'
                            ],
                            'namespace': 'MySurvey.geometry'
                        },
                        {
                            'doc': 'accuracy',
                            'name': 'accuracy',
                            'type': [
                                'null',
                                'float'
                            ],
                            'namespace': 'MySurvey.geometry'
                        }
                    ],
                    'namespace': 'MySurvey',
                    '@aether_extended_type': 'geopoint'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'geopoint'
        },
        {
            'doc': 'Operational Status',
            'name': 'operational_status',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_default_visualization': 'pie',
            '@aether_lookup': [
                {
                    'label': 'Operational',
                    'value': 'operational'
                },
                {
                    'label': 'Non Operational',
                    'value': 'non_operational'
                },
                {
                    'label': 'Unknown',
                    'value': 'unknown'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'When is the facility open?',
            'name': '_opening_hours_type',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Pick the days of the week open and enter hours for each day',
                    'value': 'oh_select'
                },
                {
                    'label': 'Only open on weekdays with the same hours every day.',
                    'value': 'oh_weekday'
                },
                {
                    'label': '24/7 - All day, every day',
                    'value': 'oh_24_7'
                },
                {
                    'label': 'Type in OSM String by hand (Advanced Option)',
                    'value': 'oh_advanced'
                },
                {
                    'label': 'I do not know the operating hours',
                    'value': 'oh_unknown'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'Which days is this facility open?',
            'name': '_open_days',
            'type': [
                'null',
                {
                    'type': 'array',
                    'items': 'string'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Monday',
                    'value': 'Mo'
                },
                {
                    'label': 'Tuesday',
                    'value': 'Tu'
                },
                {
                    'label': 'Wednesday',
                    'value': 'We'
                },
                {
                    'label': 'Thursday',
                    'value': 'Th'
                },
                {
                    'label': 'Friday',
                    'value': 'Fr'
                },
                {
                    'label': 'Saturday',
                    'value': 'Sa'
                },
                {
                    'label': 'Sunday',
                    'value': 'Su'
                },
                {
                    'label': 'Public Holidays',
                    'value': 'PH'
                }
            ],
            '@aether_extended_type': 'select'
        },
        {
            'doc': 'Open hours by day of the week',
            'name': '_dow_group',
            'type': [
                'null',
                {
                    'doc': 'Open hours by day of the week',
                    'name': '_dow_group',
                    'type': 'record',
                    'fields': [
                        {
                            'doc': 'Enter open hours for each day:',
                            'name': '_hours_note',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Monday open hours',
                            'name': '_mon_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Tuesday open hours',
                            'name': '_tue_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Wednesday open hours',
                            'name': '_wed_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Thursday open hours',
                            'name': '_thu_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Friday open hours',
                            'name': '_fri_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Saturday open hours',
                            'name': '_sat_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Sunday open hours',
                            'name': '_sun_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'doc': 'Public Holiday open hours',
                            'name': '_ph_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        },
                        {
                            'name': '_select_hours',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey._dow_group',
                            '@aether_extended_type': 'string'
                        }
                    ],
                    'namespace': 'MySurvey',
                    '@aether_extended_type': 'group'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'group'
        },
        {
            'doc': 'Enter weekday hours',
            'name': '_weekday_hours',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'OSM:opening_hours',
            'name': '_advanced_hours',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'name': 'opening_hours',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Verify the open hours are correct or go back and fix:',
            'name': '_disp_hours',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'Facility Category',
            'name': 'amenity',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Clinic',
                    'value': 'clinic'
                },
                {
                    'label': 'Doctors',
                    'value': 'doctors'
                },
                {
                    'label': 'Hospital',
                    'value': 'hospital'
                },
                {
                    'label': 'Dentist',
                    'value': 'dentist'
                },
                {
                    'label': 'Pharmacy',
                    'value': 'pharmacy'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'Available Services',
            'name': 'healthcare',
            'type': [
                'null',
                {
                    'type': 'array',
                    'items': 'string'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Doctor',
                    'value': 'doctor'
                },
                {
                    'label': 'Pharmacy',
                    'value': 'pharmacy'
                },
                {
                    'label': 'Hospital',
                    'value': 'hospital'
                },
                {
                    'label': 'Clinic',
                    'value': 'clinic'
                },
                {
                    'label': 'Dentist',
                    'value': 'dentist'
                },
                {
                    'label': 'Physiotherapist',
                    'value': 'physiotherapist'
                },
                {
                    'label': 'Alternative',
                    'value': 'alternative'
                },
                {
                    'label': 'Laboratory',
                    'value': 'laboratory'
                },
                {
                    'label': 'Optometrist',
                    'value': 'optometrist'
                },
                {
                    'label': 'Rehabilitation',
                    'value': 'rehabilitation'
                },
                {
                    'label': 'Blood donation',
                    'value': 'blood_donation'
                },
                {
                    'label': 'Birthing center',
                    'value': 'birthing_center'
                }
            ],
            '@aether_extended_type': 'select'
        },
        {
            'doc': 'Specialities',
            'name': 'speciality',
            'type': [
                'null',
                {
                    'type': 'array',
                    'items': 'string'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'xx',
                    'value': 'xx'
                }
            ],
            '@aether_extended_type': 'select'
        },
        {
            'doc': 'Speciality medical equipment available',
            'name': 'health_amenity_type',
            'type': [
                'null',
                {
                    'type': 'array',
                    'items': 'string'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Ultrasound',
                    'value': 'ultrasound'
                },
                {
                    'label': 'MRI',
                    'value': 'mri'
                },
                {
                    'label': 'X-Ray',
                    'value': 'x_ray'
                },
                {
                    'label': 'Dialysis',
                    'value': 'dialysis'
                },
                {
                    'label': 'Operating Theater',
                    'value': 'operating_theater'
                },
                {
                    'label': 'Laboratory',
                    'value': 'laboratory'
                },
                {
                    'label': 'Imaging Equipment',
                    'value': 'imaging_equipment'
                },
                {
                    'label': 'Intensive Care Unit',
                    'value': 'intensive_care_unit'
                },
                {
                    'label': 'Emergency Department',
                    'value': 'emergency_department'
                }
            ],
            '@aether_extended_type': 'select'
        },
        {
            'doc': 'Does this facility provide Emergency Services?',
            'name': 'emergency',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Yes',
                    'value': 'yes'
                },
                {
                    'label': 'No',
                    'value': 'no'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'Does the pharmacy dispense prescription medication?',
            'name': 'dispensing',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Yes',
                    'value': 'yes'
                },
                {
                    'label': 'No',
                    'value': 'no'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'Number of Beds',
            'name': 'beds',
            'type': [
                'null',
                'int'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'int',
            '@aether_masking': 'private'
        },
        {
            'doc': 'Number of Doctors',
            'name': 'staff_doctors',
            'type': [
                'null',
                'int'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'int',
            '@aether_masking': 'private'
        },
        {
            'doc': 'Number of Nurses',
            'name': 'staff_nurses',
            'type': [
                'null',
                'int'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'int',
            '@aether_masking': 'private'
        },
        {
            'doc': 'Types of insurance accepted?',
            'name': 'insurance',
            'type': [
                'null',
                {
                    'type': 'array',
                    'items': 'string'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Public',
                    'value': 'public'
                },
                {
                    'label': 'Private',
                    'value': 'private'
                },
                {
                    'label': 'None',
                    'value': 'no'
                },
                {
                    'label': 'Unknown',
                    'value': 'unknown'
                }
            ],
            '@aether_extended_type': 'select',
            '@aether_masking': 'public'
        },
        {
            'doc': 'Is this facility wheelchair accessible?',
            'name': 'wheelchair',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Yes',
                    'value': 'yes'
                },
                {
                    'label': 'No',
                    'value': 'no'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'What is the source of water for this facility?',
            'name': 'water_source',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Well',
                    'value': 'well'
                },
                {
                    'label': 'Water works',
                    'value': 'water_works'
                },
                {
                    'label': 'Manual pump',
                    'value': 'manual_pump'
                },
                {
                    'label': 'Powered pump',
                    'value': 'powered_pump'
                },
                {
                    'label': 'Groundwater',
                    'value': 'groundwater'
                },
                {
                    'label': 'Rain',
                    'value': 'rain'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'What is the source of power for this facility?',
            'name': 'electricity',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_lookup': [
                {
                    'label': 'Power grid',
                    'value': 'grid'
                },
                {
                    'label': 'Generator',
                    'value': 'generator'
                },
                {
                    'label': 'Solar',
                    'value': 'solar'
                },
                {
                    'label': 'Other Power',
                    'value': 'other'
                },
                {
                    'label': 'No Power',
                    'value': 'none'
                }
            ],
            '@aether_extended_type': 'select1'
        },
        {
            'doc': 'URL for this location (if available)',
            'name': 'url',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'In which health are is the facility located?',
            'name': 'is_in_health_area',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'doc': 'In which health zone is the facility located?',
            'name': 'is_in_health_zone',
            'type': [
                'null',
                'string'
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'string'
        },
        {
            'name': 'meta',
            'type': [
                'null',
                {
                    'name': 'meta',
                    'type': 'record',
                    'fields': [
                        {
                            'name': 'instanceID',
                            'type': [
                                'null',
                                'string'
                            ],
                            'namespace': 'MySurvey.meta',
                            '@aether_extended_type': 'string'
                        }
                    ],
                    'namespace': 'MySurvey',
                    '@aether_extended_type': 'group'
                }
            ],
            'namespace': 'MySurvey',
            '@aether_extended_type': 'group'
        },
        {
            'doc': 'UUID',
            'name': 'id',
            'type': 'string'
        }
    ],
    'namespace': 'org.ehealthafrica.aether.odk.xforms.Mysurvey'
}
