import shutil
import sys

import mock
from pulp.server.managers import factory
from pulp.server.exceptions import PulpCodedException
from .... import testbase
from pulp_snapshot.common import ids


class Attributer(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get(self, *args, **kwargs):
        return self.__dict__.get(*args, **kwargs)


class ModuleFinder(object):
    _known = dict(
        nectar=dict(
            config=dict(DownloaderConfig=mock.MagicMock()),
            downloaders=dict(
                local=dict(LocalFileDownloader=mock.MagicMock()),
                threaded=dict(HTTPThreadedDownloader=mock.MagicMock()),
            ),
            listener=Attributer(DownloadEventListener=object),
            report=dict(DownloadReport=mock.MagicMock()),
            request=dict(DownloadRequest=mock.MagicMock()),
        ),
        ldap=dict(
            modlist=dict(),
        ),
        M2Crypto=dict(
            BIO=mock.MagicMock(),
            EVP=mock.MagicMock(),
            RSA=mock.MagicMock(),
            X509=mock.MagicMock(),
            util=mock.MagicMock(),
        ),
        gofer=dict(
            messaging=dict(
                Connector=mock.MagicMock(),
                NotFound=mock.MagicMock(),
                Queue=mock.MagicMock(),
                auth=dict(ValidationFailed=mock.MagicMock()),
            ),
            proxy=dict(Agent=mock.MagicMock()),
            rmi=dict(
                async=dict(ReplyConsumer=mock.MagicMock(),
                           Listener=mock.MagicMock()),
            ),
        ),
        qpid=dict(
            messaging=dict(
                Connection=mock.MagicMock(),
                exceptions=dict(ConnectionError=mock.MagicMock(),
                                MessagingError=mock.MagicMock()),
            ),
        ),
    )

    def __init__(self, name=None):
        self.name = name

    def find_module(self, fullname, path=None):
        comps = fullname.split('.')
        fmod = self._known
        for comp in comps:
            fmod = fmod.get(comp)
            if fmod is None:
                return None
        return self

    def load_module(self, fullname):
        fn = []
        if self.name is not None:
            fn.append(self.name)
        fn.append(fullname)
        return self.__class__('.'.join(fn))

    def __getattr__(self, name):
        if name == '__path__':
            return "FAKE"
        if self.name:
            comps = self.name.split('.')
        else:
            comps = []
        comps.append(name)
        fmod = self._known
        for comp in comps:
            fmod = fmod.get(comp)
            if fmod is None:
                raise AttributeError(comp)
        return fmod


class BaseTest(testbase.TestCase):
    def setUp(self):
        super(BaseTest, self).setUp()
        self._meta_path = sys.meta_path
        sys.meta_path = [ModuleFinder()] + sys.meta_path
        from pulp_snapshot.plugins.distributors import distributor
        self.Module = distributor
        self.Configuration = distributor.configuration
        self._confmock = mock.patch.dict(
            distributor.configuration.__dict__,
        )
        self._confmock.start()
        factory.reset()

    def tearDown(self):
        self._confmock.stop()
        sys.meta_path = self._meta_path
        shutil.rmtree(self.work_dir)
        super(BaseTest, self).tearDown()

    def _config_conduit(self):
        ret = mock.MagicMock()
        ret.get_repo_distributors_by_relative_url.return_value = []
        return ret


class TestEntryPoint(BaseTest):
    """
    Tests for the entry_point() function.
    """
    def test_entry_point(self):
        """
        Assert the correct return value for the entry_point() function.
        """
        return_value = self.Module.entry_point()

        expected_value = (self.Module.Snapshot_Distributor, {})
        self.assertEqual(return_value, expected_value)


class TestConfiguration(BaseTest):
    def test_validate_config(self):
        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = dict()
        distributor = self.Module.Snapshot_Distributor()
        self.assertEquals(
            distributor.validate_config(repo, config, conduit),
            (True, None))


class TestPublish(BaseTest):
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.time")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoManager")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoContentUnit")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoDistributor")
    def test_publish(self, _distr, _units, _repomgr, _time):
        _time.time.return_value = 1234567890.1234

        repo_id = "repo-1-sasmd-level0"
        repo = mock.MagicMock(id=repo_id, notes={'_repo-type': 'rpm'})
        conduit = self._config_conduit()
        config = dict()

        _distr.get_collection.return_value.find.return_value = [
            dict(distributor_type_id="yum_distributor",
                 config=dict(relative_url="aaa"),
                 auto_publish=True),
            dict(distributor_type_id=ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT,
                 config=dict(a=1),
                 auto_publish=False),
        ]
        _units.get_collection.return_value.find.return_value = [
            dict(unit_type_id="rpm", unit_id="aaa"),
            dict(unit_type_id="srpm", unit_id="bbb"),
        ]

        publ = self.Module.Publisher(repo, conduit, config)
        publ.working_dir = self.work_dir

        publ.process()

        _distr.get_collection.return_value.find.assert_called_once_with(
            dict(repo_id="repo-1-sasmd-level0"))

        _units.get_collection.return_value.find.assert_called_once_with(
            dict(repo_id="repo-1-sasmd-level0"))

        exp_repo_name = 'repo-1-sasmd-level0__1234567890.1234'
        _repomgr.create_and_configure_repo.assert_called_once_with(
            exp_repo_name, distributor_list=[
                {
                    'distributor_type_id': 'yum_distributor',
                    'auto_publish': True,
                    'distributor_config': {
                        'relative_url': 'aaa__1234567890.1234'},
                }],
            notes=repo.notes)

        _units.assert_has_calls([
            mock.call(repo_id=exp_repo_name, unit_type_id="rpm",
                      unit_id="aaa"),
            mock.call(repo_id=exp_repo_name, unit_type_id="srpm",
                      unit_id="bbb"),
        ])

        _units.get_collection.return_value.insert.assert_called_once_with(
            [_units.return_value, _units.return_value])
        _repomgr.rebuild_content_unit_counts.assert_called_once_with(
            repo_ids=[exp_repo_name])
