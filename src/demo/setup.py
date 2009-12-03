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
"""Setup script."""

import os
from setuptools import setup, find_packages


setup(
    name='demo',
    version='0.1.0',
    author="Tobias Rodaebel",
    author_email="tobias dot rodaebel at googlemail dot com",
    description="Typhoon App Engine demo application.",
    long_description=(),
    license="Apache License 2.0",
    keywords="appengine gae typhoonae wsgi",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        ],
    url='',
    packages=find_packages(os.sep.join(['src', 'demo'])),
    include_package_data=True,
    package_dir={'': os.sep.join(['src', 'demo'])},
    install_requires=[
        'setuptools',
        ],
    zip_safe=False,
    )
