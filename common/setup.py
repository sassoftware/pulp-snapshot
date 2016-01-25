from setuptools import setup, find_packages

setup(
    name='pulp_snapshot_common',
    version='0.1',
    license='GPLv2+',
    packages=find_packages(exclude=['test', 'test.*']),
    author='Mihai Ibanescu',
    author_email='mihai.ibanescu@sas.com'
)
