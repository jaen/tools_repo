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

from command import Command, MirrorSafeCommand

class Nix(Command, MirrorSafeCommand):
  common = True
  helpSummary = "Export nix file with sources"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
"""

  def Execute(self, opt, args):
    all_projects = self.GetProjects(args, missing_ok=True, submodules_ok=False)

    oS = '{\n'
    oS += "unpackPhase = ''\n" \
    'echo "reassembling source tree from git source store paths"\n' \
    'mkdir src; cd src\n' \
    'for src in $srcs; do\n' \
    " dest_folder=$(stripHash $src); dest_folder=''${dest_folder//=//}\n" \
    ' echo "$src -> $dest_folder"\n' \
    ' mkdir -p "$dest_folder"\n' \
    ' cp --reflink=auto --no-preserve=ownership --no-dereference --preserve=links --recursive "$src/." "$dest_folder/"\n' \
    ' chmod -R u+w "$dest_folder"\n' \
    'done\n' \
    'echo "creating symlinks and copies as specified in repo manifest(s)"\n'
    for p in all_projects:
      for f in p.linkfiles:
        oS += 'ln -s ' + f.src_rel_to_dest + ' ' + f.dest + '\n'
      for c in p.copyfiles:
        oS += 'cp --reflink=auto ' + p.relpath + '/' + c.src + ' ' + c.dest + '\n'
    oS += "'';\n"

    oS += 'sources = [\n'
    for p in all_projects:
      oS += '  (builtins.fetchGit {\n'
      oS += '    url = "' + p.remote.url + '";\n'
      if 'refs/heads' in p.revisionExpr:
        oS += '    ref = "' + p.revisionExpr.split('/')[-1] + '";\n'
      else:
        oS += '    ref = "' + p.revisionExpr + '";\n'
      oS += '    rev = "' + p._LsRemote(p.revisionExpr).split('\t')[0] + '";\n'
      oS += '    name = "' + p.relpath.replace('/', '=') + '";\n'
      oS += '  })\n'
    oS += '];\n}'
    print(oS)