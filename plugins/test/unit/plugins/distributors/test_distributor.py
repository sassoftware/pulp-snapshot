import shutil
import sys

import mock
from pulp.server.managers import factory
# from pulp.server.exceptions import PulpCodedException
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
        shutil.rmtree(self.work_dir, ignore_errors=True)
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
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.time.time")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.repo_controller")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoGroup")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoContentUnit")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoDistributor")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoImporter")
    def test_publish(self, _imp, _distr, _units, _repogroup, _repoctrl, _time):
        _time.return_value = 1234567890.1234

        repo_id = "repo-1-sasmd-level0"
        exp_repo_name = 'repo-1-sasmd-level0__20090213233130.1233Z'
        repo_notes = {'_repo-type': 'rpm',
                      '_repository_timestamp': 1234567890.1234}
        repo = mock.MagicMock(id=repo_id, notes=repo_notes)
        conduit = self._config_conduit()
        config = dict()

        _distr.objects.filter.return_value = [
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

        _repogroup.get_collection.return_value.find.return_value = [
            dict(id='group-0', repo_ids=['a', 'b', 'c']),
            dict(id='group-1', repo_ids=['a', 'b', 'c']),
        ]

        publ = self.Module.Publisher(repo, conduit, config)
        publ.working_dir = self.work_dir
        publ.uuid = 'f0000000-0000-0000-0000-000000000001'

        publ.process_lifecycle()

        _distr.objects.filter.assert_called_once_with(
            repo_id="repo-1-sasmd-level0")

        _units.get_collection.return_value.find.assert_called_once_with(
            dict(repo_id="repo-1-sasmd-level0"))

        _imp.objects.filter.assert_called_once_with(
            repo_id="repo-1-sasmd-level0")
        _imp.objects.filter.return_value.first.assert_called_once_with()

        _repogroup.get_collection.return_value.update.assert_called_once_with(
            {'repo_ids': 'repo-1-sasmd-level0'},
            {'$addToSet': {
                'repo_ids': 'repo-1-sasmd-level0__20090213233130.1233Z'}
             }
        )

        notes = dict(repo.notes)
        notes.update({
            '_repository_snapshot':
            'repo-1-sasmd-level0__20090213233130.1233Z',
            '_repository_timestamp': 1234567890.1234})

        imp_type_id = _imp.objects.filter.return_value.first.return_value['import_type_id']  # noqa
        _repoctrl.create_repo.assert_called_once_with(
            exp_repo_name, distributor_list=[
                {
                    'distributor_type_id': 'yum_distributor',
                    'auto_publish': True,
                    'distributor_config': {
                        'relative_url': 'aaa__20090213233130.1233Z'},
                }],
            importer_type_id=imp_type_id,
            importer_repo_plugin_config={},
            notes=notes)

        _units.assert_has_calls([
            mock.call(repo_id=exp_repo_name, unit_type_id="rpm",
                      unit_id="aaa"),
            mock.call(repo_id=exp_repo_name, unit_type_id="srpm",
                      unit_id="bbb"),
        ])

        _units.get_collection.return_value.insert.assert_called_once_with(
            [_units.return_value, _units.return_value])
        _repoctrl.rebuild_content_unit_counts.assert_called_once_with(
            _repoctrl.create_repo.return_value)

        conduit.build_success_report.assert_called_once_with(
            {'repository_snapshot':
             'repo-1-sasmd-level0__20090213233130.1233Z'},
            [{'num_processed': 1,
              'items_total': 1,
              'state': 'FINISHED',
              'num_success': 1,
              'error_details': [],
              'description': 'Snapshotting repository',
              'num_failures': 0,
              'step_id': 'f0000000-0000-0000-0000-000000000001',
              'step_type': 'publish_snapshot',
              'details': ''}])

        self.assertEquals(exp_repo_name, publ.repo_snapshot)

    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoContentUnit")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._get_units")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._build_report")  # noqa
    def test_publish_no_change(self, _build_report, _get_units, _units):
        repo_id = "repo-1-sasmd-level0"
        repo_snapshot_other = "repo-1-timestamped"
        notes = {'_repo-type': 'rpm',
                 '_repository_snapshot': repo_snapshot_other}
        repo = mock.MagicMock(id=repo_id, notes=notes)
        conduit = self._config_conduit()
        config = dict()

        _get_units.return_value = [{'unit_id': 1, 'unit_type_id': 'rpm'}]

        publ = self.Module.Publisher(repo, conduit, config)
        publ.working_dir = self.work_dir

        publ.process_lifecycle()
        _build_report.assert_called_once_with(repo_snapshot_other)

    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoContentUnit")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._get_units")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._build_report")  # noqa
    def test_publish_empty_repo(self, _build_report, _get_units, _units):
        repo_id = "repo-1-sasmd-level0"
        notes = {'_repo-type': 'rpm'}
        repo = mock.MagicMock(id=repo_id, notes=notes)
        conduit = self._config_conduit()
        config = dict()

        _get_units.return_value = []

        publ = self.Module.Publisher(repo, conduit, config)
        publ.working_dir = self.work_dir

        publ.process_lifecycle()
        # Expect call with no snapshot, since one was not created
        _build_report.assert_called_once_with(None)

    @mock.patch("pulp_snapshot.plugins.distributors.distributor.time.time")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.repo_controller")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoGroup")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoContentUnit")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._get_units")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoDistributor")  # noqa
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.RepoImporter")
    @mock.patch("pulp_snapshot.plugins.distributors.distributor.Publisher._build_report")  # noqa
    def test_publish_empty_repo_nonempty_snapshot(self, _build_report, _imp,
                                                  _distr, _get_units, _units,
                                                  _repogroup, _repoctrl,
                                                  _time):
        _time.return_value = 1234567890.1234
        repo_id = "repo-1-sasmd-level0"
        repo_snapshot_other = "repo-1-timestamped"
        exp_repo_name = 'repo-1-sasmd-level0__20090213233130.1233Z'
        notes = {'_repo-type': 'rpm',
                 '_repository_snapshot': repo_snapshot_other}
        exp_notes = dict(notes)
        exp_notes.update(_repository_timestamp=1234567890.1234,
                         _repository_snapshot=exp_repo_name)
        repo = mock.MagicMock(id=repo_id, notes=notes)
        conduit = self._config_conduit()
        config = dict()

        _get_units.side_effect = [[],
                                  [{'unit_id': 1, 'unit_type_id': 'rpm'}]]

        _distr.objects.filter.return_value = [
            dict(distributor_type_id="yum_distributor",
                 config=dict(relative_url="aaa"),
                 auto_publish=True),
            dict(distributor_type_id=ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT,
                 config=dict(a=1),
                 auto_publish=False),
        ]

        publ = self.Module.Publisher(repo, conduit, config)
        publ.working_dir = self.work_dir

        publ.process_lifecycle()
        _build_report.assert_called_once_with(exp_repo_name)

        _distr.objects.filter.assert_called_once_with(
            repo_id=repo_id)

        _get_units.assert_has_calls([
            mock.call(_units.get_collection.return_value, repo_id),
            mock.call(_units.get_collection.return_value,
                      repo_snapshot_other),
        ])

        _imp.objects.filter.assert_called_once_with(
            repo_id=repo_id)
        _imp.objects.filter.return_value.first.assert_called_once_with()

        # Nothing to insert
        _units.get_collection.return_value.insert.assert_not_called()

        imp_type_id = _imp.objects.filter.return_value.first.return_value['import_type_id']  # noqa
        _repoctrl.create_repo.assert_called_once_with(
            exp_repo_name, distributor_list=[
                {
                    'distributor_type_id': 'yum_distributor',
                    'auto_publish': True,
                    'distributor_config': {
                        'relative_url': 'aaa__20090213233130.1233Z'},
                }],
            importer_type_id=imp_type_id,
            importer_repo_plugin_config={},
            notes=exp_notes)
