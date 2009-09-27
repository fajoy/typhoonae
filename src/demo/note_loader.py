# -*- coding: utf-8 -*-
#
# Copyright 2009 Tobias Rodäbel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Simple notes loader."""

import google.appengine.ext.db
import google.appengine.tools.bulkloader


class Note(google.appengine.ext.db.Model):
    """Very simple note model."""

    body = google.appengine.ext.db.StringProperty()
    date = google.appengine.ext.db.DateTimeProperty(auto_now=True)


class NoteLoader(google.appengine.tools.bulkloader.Loader):
    """Simple loader class."""

    def __init__(self):
        google.appengine.tools.bulkloader.Loader.__init__(
            self, 'Note', [('body', str),])

loaders = [NoteLoader]
