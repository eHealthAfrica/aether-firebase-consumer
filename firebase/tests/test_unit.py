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

from copy import copy

from . import *  # get all test assets from test/__init__.py
from app.fixtures import examples
from app.artifacts import Subscription

# Test Suite contains both unit and integration tests
# Unit tests can be run on their own from the root directory
# enter the bash environment for the version of python you want to test
# for example for python 3
# `docker-compose run consumer-sdk-test bash`
# then start the unit tests with
# `pytest -m unit`
# to run integration tests / all tests run the test_all.sh script from the /tests directory.


@pytest.mark.unit
def test__subscription_extended_validation():
    _doc = examples.SUBSCRIPTION
    assert(Subscription._validate(_doc) is True)
    assert(Subscription._validate_pretty(_doc)['valid'] is True)
    bad_paths = [
        '{illegal}/sub/stitution',
        'too/short'
    ]
    for path in bad_paths:
        t_doc = copy(_doc)
        t_doc['fb_options']['target_path'] = path
        assert(Subscription._validate(t_doc) is False), t_doc['fb_options']['target_path']
        assert(len(Subscription._validate_pretty(_doc)['validation_errors']) > 0)


@pytest.mark.unit
def test__get_rtdb_core_client_io(rtdb):
    ref = rtdb.reference('/some/path')
    assert(ref.get() is None)
    test_values = [1, 1.0, "a", [1, 2, 3], {'a': 'b'}]
    for test_value in test_values:
        ref.set(test_value)
        assert(ref.get() == test_value)


@pytest.mark.unit
def test__get_cfs_core_client_io(cfs):
    ref = cfs.collection(u'test').document(u'adoc')
    test_value = {u'key': u't_val'}
    ref.set(test_value)
    assert(ref.get().to_dict() == test_value)
    ref.delete()
    assert(ref.get().to_dict() != test_value)


@pytest.mark.unit
def test__read_write_path_cfs(cfs):
    # must alternate between doc/collection
    #        c/       d/     c
    path = '_aether/entity/type-of-entity'
    #      ID of doc
    _id = 'some-id'
    #      the doc
    msg = {'hello': 'cfs!'}
    res = helpers.write_cfs(cfs, path, msg, _id)
    assert(res is not None), res
    cfs_msg = helpers.read_cfs(cfs, path, _id)
    assert(cfs_msg == msg)
