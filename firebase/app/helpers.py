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


class RTDB(object):

    def __init__(self, app):
        self.app = app

    def reference(self, path):
        return realtime(path, app=self.app)


class CFSPathType(enum.Enum):
    DOC = 0
    COLLECTION = 1


def _even_len(obj):
    return (len(obj) % 2 == 0)


class CloudFirestorePath(object):

    def __init__(self, pathString: str, _type: CFSPathType):
        self.parts = [i for i in pathString.split('/') if i]
        LOG.debug(f'new path: {self.parts}')
        self._type = _type

    def _first_type(self) -> CFSPathType:
        DOC = CFSPathType.DOC
        COLLECTION = CFSPathType.COLLECTION
        _type = self._type
        return DOC if (
            (_type is DOC and not _even_len(self.parts)) or
            (_type is COLLECTION and _even_len(self.parts))) \
            else COLLECTION

    def _next_type(self, _type: CFSPathType) -> CFSPathType:
        return CFSPathType.DOC if _type is CFSPathType.COLLECTION else CFSPathType.COLLECTION

    def _next_ref(self, ref, _type, _id):
        if _type is CFSPathType.COLLECTION:
            return ref.collection(_id)
        else:
            return ref.document(_id)

    def _build_ref(self, cfs):
        _type = self._first_type()
        _ref = cfs
        for _id in self.parts:
            LOG.debug([_id, _type])
            _ref = self._next_ref(_ref, _type, _id)
            _type = self._next_type(_type)
        return _ref

    def reference(self, cfs):
        return self._build_ref(cfs)


class CFSCollection(CloudFirestorePath):
    def __init__(self, pathString):
        super().__init__(pathString, CFSPathType.COLLECTION)


class CFSDocument(CloudFirestorePath):
    def __init__(self, pathString):
        super().__init__(pathString, CFSPathType.DOC)


def Firestore(app) -> firestore.Client:
    # we use firebase_admin.firestore which takes the app info and returns firestore.Client
    return cfs(app)


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


def read_rtdb(rtdb, path):
    pass


def write_rtdb(rtdb, path):
    pass


# CFS Document io

def read_cfs(cfs, path, doc_id=None):
    if doc_id:
        path = f'{path}/{doc_id}'
        _path = CFSDocument(path)
    else:
        _path = CFSCollection(path)
    _ref = _path.reference(cfs)
    return _ref.get().to_dict()


def write_cfs(cfs, path, value, doc_id=None):
    if doc_id:
        path = f'{path}/{doc_id}'
        _path = CFSDocument(path)
    else:
        _path = CFSCollection(path)
    _ref = _path.reference(cfs)
    return _ref.set(value)
