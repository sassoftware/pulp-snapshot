import sys
import tempfile
import unittest
from types import ModuleType


class ImporterWrapper(ModuleType):
    def __init__(self, name):
        self.__path__ = '/fake-path/' + name.replace('.', '/') + ".py"

    def __getattr__(self, name):
        if name != 'config':
            raise AttributeError(name)
        return self

    def get(self, name, default=None):
        if name != 'config':
            return default
        return self

    def getint(self, name, default=None):
        return 0

    def getfloat(self, name, default=None):
        return 0.0

    def getboolean(self, name, default=None):
        return default

sys.modules['pulp.server.config'] = ImporterWrapper('pulp.server.config')
import pulp.server  # noqa
pulp.server.config = sys.modules['pulp.server.config']


class TestCase(unittest.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.work_dir = tempfile.mkdtemp()
