#!/usr/bin/env python

# Copyright (C) 2018 by eHealth Africa : http://www.eHealthAfrica.org
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


import http.server
import logging
from socketserver import TCPServer
import threading
import sys

LOG = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s [FIREBASE] %(levelname)-8s %(message)s'))
LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)


class HealthcheckHandler(http.server.BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super(HealthcheckHandler, self).__init__(*args, **kwargs)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def LOG_message(self, format, *args):
        LOG.debug(args)


class HealthcheckServer(threading.Thread):

    def __init__(self, port):
        self._port = port
        super(HealthcheckServer, self).__init__()

    def run(self):
        host, port = '0.0.0.0', int(self._port)
        handler = HealthcheckHandler
        TCPServer.allow_reuse_address = True
        try:
            self.httpd = TCPServer((host, port), handler)
            self.httpd.serve_forever()
        except OSError as ose:
            LOG.critical('Could not serve healthcheck endpoint: %s' % ose)
            sys.exit(1)

    def stop(self):
        try:
            LOG.debug('stopping healthcheck endpoint')
            self.httpd.shutdown()
            self.httpd.server_close()
            LOG.debug('healthcheck stopped.')
        except AttributeError:
            LOG.debug('Healthcheck was already down.')
