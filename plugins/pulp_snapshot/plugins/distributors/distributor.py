import logging
import time

from gettext import gettext as _
from pulp.plugins.util.publish_step import PublishStep
from pulp.plugins.distributor import Distributor
from pulp.server.db.model.repository import (
    Repo, RepoDistributor, RepoContentUnit)
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.exceptions import PulpCodedException
from pulp_snapshot.common import ids, constants
from pulp_snapshot.plugins import error_codes
from . import configuration

_LOG = logging.getLogger(__name__)


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
        return publisher.publish()

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

    def process_main(self, item=None):
        repo = self.get_repo()
        suffix = "__%.4f" % time.time()
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
        _LOG.info("Distributors: %r", distributors)

        units_coll = RepoContentUnit.get_collection()
        units = list(units_coll.find(dict(repo_id=repo.id)))

        RepoManager.create_and_configure_repo(new_name, notes=notes,
                                              distributor_list=distributors)
        _LOG.info("Units: %r", units)
        copied = []
        for unit in units:
            copied.append(RepoContentUnit(
                repo_id=new_name,
                unit_id=unit['unit_id'],
                unit_type_id=unit['unit_type_id'],
            ))
        units_coll.insert(copied)
        RepoManager.rebuild_content_unit_counts(repo_ids=[new_name])
