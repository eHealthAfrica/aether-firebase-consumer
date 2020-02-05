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


import enum

from firebase_admin.db import reference as realtime
from firebase_admin.firestore import client as cfs

from google.cloud import firestore
from aet.logger import get_logger

from app import config, utils


LOG = get_logger('HELPERS')


class MessageHandlingException(Exception):
    # A simple way to handle the variety of expected misbehaviors in message sync
    # Between Aether and Firebase
    pass


class SyncMode(enum.Enum):
    SYNC = 1        # Firebase  <->  Aether
    FORWARD = 2     # Firebase   ->  Aether
    CONSUME = 3     # Firebase  <-   Aether
    NONE = 4        # Firebase   |   Aether


# Hash functions

def get_remote_hash(rtdb, _id):
    ref = rtdb.reference(f'{config.HASH_PATH}/{_id}')
    return ref.get()


def set_remote_hash(rtdb, _id, hash):
    ref = rtdb.reference(f'{config.HASH_PATH}/{_id}')
    ref.set(hash)


def remote_msg_needs_update(rtdb, _id, msg) -> bool:
    new_hash = utils.hash(msg)
    old_hash = get_remote_hash(rtdb, _id)
    if not old_hash:
        return True
    if new_hash == old_hash:
        return False


# RTDB io

class RTDB(object):

    def __init__(self, app):
        self.app = app

    def reference(self, path):
        return realtime(path, app=self.app)


def read_rtdb(rtdb, path):
    _ref = rtdb.reference(path)
    return _ref.get()


def write_rtdb(rtdb, path, value):
    _ref = rtdb.reference(path)
    return _ref.set(value)


# CFS io

def Firestore(app) -> firestore.Client:
    # we use firebase_admin.firestore which takes the app info and returns firestore.Client
    return cfs(app)


def ref_path(cfs, path, doc_id=None):
    if doc_id:
        path = f'{path}/{doc_id}'
        return cfs.document(path)
    else:
        return cfs.collection(path)


def read_cfs(cfs, path, doc_id=None):
    return ref_path(cfs, path, doc_id).get().to_dict()


def write_cfs(cfs, path, value, doc_id=None):
    return ref_path(cfs, path, doc_id).set(value)
