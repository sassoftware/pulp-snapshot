from collections import namedtuple
import logging
import time

from gettext import gettext as _
from pulp.plugins.util import publish_step as platform_steps
from pulp.plugins.distributor import Distributor
from pulp.server.db.model import Importer as RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.repo_group import RepoGroup
from pulp.server.controllers import repository as repo_controller
from pulp_snapshot.common import ids, constants
from . import configuration

_LOG = logging.getLogger(__name__)
REPO_SNAPSHOT_NAME = '_repository_snapshot'
REPO_SNAPSHOT_TIMESTAMP = '_repository_timestamp'

REPO_UNIT = namedtuple("REPO_UNIT", "unit_type_id unit_id")


def entry_point():
    return Snapshot_Distributor, {}


class Snapshot_Distributor(Distributor):
    @classmethod
    def metadata(cls):
        return {
            'id': ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT,
            'display_name': _('Snapshot Distributor'),
            'types': sorted(ids.SUPPORTED_TYPES),
        }

    def validate_config(self, repo, config, config_conduit):
        return configuration.validate_config(repo, config, config_conduit)

    def publish_repo(self, repo, conduit, config):
        publisher = Publisher(repo=repo, conduit=conduit, config=config)
        return publisher.process_lifecycle()

    def distributor_removed(self, repo, config):
        pass


class Publisher(platform_steps.PluginStep):
    description = _("Snapshotting repository")

    def __init__(self, repo, conduit, config, **kwargs):
        super(Publisher, self).__init__(
            step_type=constants.PUBLISH_SNAPSHOT,
            repo=repo,
            conduit=conduit,
            config=config,
            plugin_type=ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT,
            **kwargs)
        self.description = self.__class__.description
        self.repo_snapshot = None

    def process_main(self, item=None):
        repo = self.get_repo()

        units_coll = RepoContentUnit.get_collection()
        units = self._get_units(units_coll, repo.id)

        snapshot_name = repo.notes.get(REPO_SNAPSHOT_NAME)
        if snapshot_name:
            old_units = self._get_units(units_coll, snapshot_name)
        else:
            old_units = []
        units = self._units_to_set(units)
        old_units = self._units_to_set(old_units)
        # Create a snapshot if one did not exist before (snapshot_name is
        # None) and the repo is not empty, or if the unit contents are
        # different
        if units == old_units and (snapshot_name or not units):
            return self._build_report(snapshot_name)

        now = time.time()
        suffix = time.strftime("%Y%m%d%H%M%S", time.gmtime(now))
        suffix = "__%s.%04dZ" % (suffix, 10000 * (now - int(now)))
        new_name = "%s%s" % (repo.id, suffix)
        notes = {}
        notes[REPO_SNAPSHOT_TIMESTAMP] = now
        if '_repo-type' in repo.notes:
            notes['_repo-type'] = repo.notes['_repo-type']
        notes[REPO_SNAPSHOT_NAME] = new_name
        notes[REPO_SNAPSHOT_TIMESTAMP] = now
        distributors = []
        # Fetch the repo's existing importers

        repo_importer = RepoImporter.objects.filter(repo_id=repo.id).first()
        if repo_importer is not None:
            importer_type_id = repo_importer['importer_type_id']
        else:
            importer_type_id = None

        repo_obj = repo_controller.create_repo(
            new_name, notes=notes,
            importer_type_id=importer_type_id,
            importer_repo_plugin_config={},
            distributor_list=distributors)
        copied = []
        for unit in sorted(units):
            copied.append(RepoContentUnit(
                repo_id=new_name,
                unit_id=unit.unit_id,
                unit_type_id=unit.unit_type_id,
            ))
        if copied:
            units_coll.insert(copied)
        repo_controller.rebuild_content_unit_counts(repo_obj)

        group_coll = RepoGroup.get_collection()
        group_coll.update(dict(repo_ids=repo.id),
                          {'$addToSet': dict(repo_ids=new_name)})
        return self._build_report(new_name)

    def _get_units(self, collection, repo_id):
        return list(collection.find(dict(repo_id=repo_id)))

    @classmethod
    def _units_to_set(cls, units):
        return set(REPO_UNIT(x['unit_type_id'], x['unit_id'])
                   for x in units)

    def _build_report(self, repo_id):
        self.repo_snapshot = repo_id

    def get_progress_report_summary(self):
        ret = super(Publisher, self).get_progress_report_summary()
        if self.repo_snapshot:
            ret.update(repository_snapshot=self.repo_snapshot)
        return ret
