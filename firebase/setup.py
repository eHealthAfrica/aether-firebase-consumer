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

from setuptools import setup
setup(
    name='aether_firebase_consumer',
    author='Shawn Sarwar',
    author_email="shawn.sarwar@ehealthafrica.org",
    decription='''An Aether Consumer for Firebase CFS and RTDB''',
    version='1.0.0',
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'sqlalchemy', 'alembic', 'aet.consumer', 'mock', 'aether_sdk_example', 'firebase-admin'],
    url='https://github.com/eHealthAfrica/aether-firebase-consumer',
    keywords=['aet', 'aether', 'kafka', 'consumer', 'firebase'],
    classifiers=[]
)
