from collections import namedtuple
import logging
import time

from gettext import gettext as _
from pulp.plugins.util.publish_step import PublishStep
from pulp.plugins.distributor import Distributor
from pulp.server.db.model.repository import RepoDistributor, RepoContentUnit
from pulp.server.db.model.repo_group import RepoGroup
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.exceptions import PulpCodedException
from pulp_snapshot.common import ids, constants
from pulp_snapshot.plugins import error_codes
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

    def publish_repo(self, repo, publish_conduit, config):
        publisher = Publisher(repo=repo, publish_conduit=publish_conduit,
                              config=config)
        return publisher.process_lifecycle()

    def distributor_removed(self, repo, config):
        pass


class Publisher(PublishStep):
    description = _("Snapshotting repository")

    def __init__(self, repo, publish_conduit, config):
        super(Publisher, self).__init__(
            step_type=constants.PUBLISH_SNAPSHOT,
            repo=repo,
            publish_conduit=publish_conduit,
            config=config,
            distributor_type=ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT)
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
        if units == old_units and snapshot_name:
            return self._build_report(snapshot_name)

        now = time.time()
        suffix = time.strftime("%Y%m%d%H%M%S", time.gmtime(now))
        suffix = "__%s.%04dZ" % (suffix, 10000 * (now - int(now)))
        new_name = "%s%s" % (repo.id, suffix)
        notes = {}
        if '_repo-type' in repo.notes:
            notes['_repo-type'] = repo.notes['_repo-type']
        # Fetch the repo's existing distributors and importers
        distributor_coll = RepoDistributor.get_collection()
        repo_distributors = list(distributor_coll.find({'repo_id': repo.id}))
        distributors = []
        for x in repo_distributors:
            if x['distributor_type_id'] == ids.TYPE_ID_DISTRIBUTOR_SNAPSHOT:
                continue
            distrib = dict(
                distributor_type_id=x['distributor_type_id'],
                distributor_config=x['config'].copy(),
                auto_publish=x['auto_publish'])
            cfg = distrib['distributor_config']
            if 'relative_url' in cfg:
                cfg['relative_url'] = "%s%s" % (cfg['relative_url'], suffix)
            distributors.append(distrib)

        RepoManager.create_and_configure_repo(new_name, notes=notes,
                                              distributor_list=distributors)
        copied = []
        for unit in sorted(units):
            copied.append(RepoContentUnit(
                repo_id=new_name,
                unit_id=unit.unit_id,
                unit_type_id=unit.unit_type_id,
            ))
        units_coll.insert(copied)
        RepoManager.rebuild_content_unit_counts(repo_ids=[new_name])
        delta = dict(notes={
            REPO_SNAPSHOT_NAME: new_name,
            REPO_SNAPSHOT_TIMESTAMP: now,
        })
        RepoManager.update_repo(repo.id, delta)

        group_coll = RepoGroup.get_collection()
        groups = [RepoGroup(x, repo_ids=[new_name])
                  for x in self._get_repo_groups(repo.id)]
        group_coll.insert(groups)
        return self._build_report(new_name)

    def _get_units(self, collection, repo_id):
        return list(collection.find(dict(repo_id=repo_id)))

    def _get_repo_groups(self, repo_id):
        group_coll = RepoGroup.get_collection()
        # mongo lets you specify a single element in an array match
        return set(x['id'] for x in group_coll.find(dict(repo_ids=repo_id)))

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
