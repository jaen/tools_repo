#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from pyversion import is_python3
if is_python3():
  import http.cookiejar as cookielib
  import urllib.error
  import urllib.parse
  import urllib.request
  import xmlrpc.client
else:
  import imp
  import urllib2
  import urlparse
  import xmlrpclib
  urllib = imp.new_module('urllib')
  urllib.error = urllib2
  urllib.parse = urlparse
  urllib.request = urllib2
  xmlrpc = imp.new_module('xmlrpc')
  xmlrpc.client = xmlrpclib

try:
  import threading as _threading
except ImportError:
  import dummy_threading as _threading

try:
  import resource
  def _rlimit_nofile():
    return resource.getrlimit(resource.RLIMIT_NOFILE)
except ImportError:
  def _rlimit_nofile():
    return (256, 256)

try:
  import multiprocessing
except ImportError:
  multiprocessing = None

import sys
import json
import re

from command import Command, MirrorSafeCommand

class Dumpjson(Command, MirrorSafeCommand):
  common = True
  helpSummary = "Export json file with sources"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
"""

  def _Options(self, p):
    pass

  def Execute(self, opt, args):
    all_projects = self.GetProjects(args, missing_ok=True, submodules_ok=False)

    data = {}
    for p in all_projects:
        data[p.relpath] = {
            "url": p.remote.url,
            "revisionExpr": p.revisionExpr,
        }
        filtered_groups = filter(lambda g: not (g == "all" or g.startswith("name:") or g.startswith("path:")), p.groups)
        if filtered_groups:
            data[p.relpath]["groups"] = sorted(filtered_groups)
        if p.linkfiles:
            data[p.relpath]["linkfiles"] = [ { "src": l.src, "dest": l.dest } for l in p.linkfiles ]
        if p.copyfiles:
            data[p.relpath]["copyfiles"] = [ { "src": c.src, "dest": c.dest } for c in p.copyfiles ]

    print(json.dumps(data, sort_keys=True))
