#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pulp_snapshot_plugins',
    version='0.1',
    license='MIT',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Mihai Ibanescu',
    author_email='mihai.ibanescu@sas.com',
    entry_points={
        'pulp.distributors': [
            'distributor = pulp_snapshot.plugins.distributors.distributor:entry_point',  # noqa
        ]
    },
    include_package_data=True,
    data_files=[
        ('/usr/lib/pulp/plugins/types', ['types/snapshot.json']),
    ],
    install_requires=['blinker', 'celery', 'django', 'kombu', 'mongoengine',
                      'oauth2', 'semantic_version'],
    tests_require=['mock', 'pytest'],
)
