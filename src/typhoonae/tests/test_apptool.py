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
"""Unit tests for the apptool console script."""

import os
import re
import sys
import typhoonae
import typhoonae.apptool
import unittest


class ApptoolTestCase(unittest.TestCase):
    """Tests apptoll functions."""

    def setUp(self):
        """Loads the sample application."""

        self.app_root = os.path.join(os.path.dirname(__file__), 'sample')
        os.chdir(self.app_root)
        sys.path.insert(0, os.getcwd())
        self.conf = typhoonae.getAppConfig()
        assert self.conf.application == 'sample'

    def testScheduledTasksConfig(self):
        """Tests the configuration for scheduled tasks."""

        class OptionsMock:
            server_name = 'localhost'
            set_crontab = False

        options = OptionsMock()

        typhoonae.apptool.read_crontab(options)
        tab = typhoonae.apptool.write_crontab(options, self.app_root)
        assert ('*/1', '*', '*', '*', '*', os.path.join(os.getcwd(), 'bin',
                'runtask') + ' http://localhost:8080/a',
                ' # Test A (every 1 minutes)', 'Test A (every 1 minutes)') \
                in tab
