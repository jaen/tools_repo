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

def _fetch_revs(p, sem):
  with sem:
      p.rev = p._LsRemote(p.revisionExpr).split('\t')[0]
      assert p.rev != ""

class Dumpjson(Command, MirrorSafeCommand):
  common = True
  helpSummary = "Export json file with sources"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
"""

  def _Options(self, p):
    p.add_option('-j', '--jobs',
                 dest='jobs', action='store', type='int', default=8,
                 help="number of projects to check simultaneously")
    p.add_option('-l', '--local-only',
                 dest='local_only', action='store_true',
                 help="don't fetch project revisions even if they are missing")

  def Execute(self, opt, args):
    all_projects = self.GetProjects(args, missing_ok=True, submodules_ok=False)

    # Fill out rev if we already have the information available
    to_fetch = []
    for p in all_projects:
      if re.match("[0-9a-f]{40}", p.revisionExpr):
          # Use revisionExpr if it is already a SHA1 hash
          p.rev = p.revisionExpr
      else:
        p.rev = None
        to_fetch.append(p)

    if not opt.local_only:
      # Fetch rev for projects we don't know yet
      sem = _threading.Semaphore(opt.jobs)
      threads = [ _threading.Thread(target=_fetch_revs, args=(p, sem)) for p in to_fetch ]
      for t in threads:
          t.start()
      for t in threads:
          t.join()

    data = {}
    for p in all_projects:
        data[p.relpath] = {
            "url": p.remote.url,
            "revisionExpr": p.revisionExpr,
            "rev": p.rev,
        }
        filtered_groups = filter(lambda g: not (g == "all" or g.startswith("name:") or g.startswith("path:")), p.groups)
        if filtered_groups:
            data[p.relpath]["groups"] = sorted(filtered_groups)
        if p.linkfiles:
            data[p.relpath]["linkfiles"] = [ { "src": l.src, "dest": l.dest } for l in p.linkfiles ]
        if p.copyfiles:
            data[p.relpath]["copyfiles"] = [ { "src": c.src, "dest": c.dest } for c in p.copyfiles ]

    print(json.dumps(data, sort_keys=True))
