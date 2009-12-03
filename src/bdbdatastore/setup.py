"""Setup script."""

import os
from setuptools import setup, find_packages


setup(
    name='bdbdatastore',
    version='0.2.2',
    author="Nick Johnson",
    author_email="arachnid at notdot dot net",
    description="An alternate datastore backend for App Engine, implemented "
                "using BDB JE.",
    long_description="bdbdatastore is an alternate datastore backend for App "
        "Engine apps. It's far more robust and scalable than the one the "
        "development server uses, but not as big and hard to install as "
        "HBase and HyperTable based backends. bdbdatastore is intended "
        "primarially for use by people who want to host their own App Engine "
        "apps, and don't expect datastore load for a single app to exceed "
        "what a single server can handle. In the event your app gets too big "
        "for bdbdatastore, the migration path to an alternate backend is "
        "smooth.",
    license="Apache License 2.0",
    keywords=["appengine", "gae", "bdb"],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Java',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        ],
    url='http://arachnid.github.com/bdbdatastore/',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    install_requires=[
        'setuptools',
        ],
    zip_safe=False,
    )
