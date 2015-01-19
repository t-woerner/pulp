"""
Contains the definitions for all classes related to the importer's API for
interacting with the Pulp server during a repo sync.

Plugin implementations for repository sync will obviously vary wildly. For help
in understanding the APIs, below is a short outline of a common sync process and
its calls into this conduit:

1. Call get_units to understand what units are already associated with the
   repository being synchronized.
2. For each new unit to add to the Pulp server and associate with the repository,
   the plugin takes the following steps.:
   a. Calls init_unit which takes unit specific metadata and allows Pulp to
      populate any calculated/derived values for the unit. The result of this
      call is an object representation of the unit.
   b. Uses the storage_path field in the returned unit to save the bits for the
      unit to disk.
   c. Calls save_unit which creates/updates Pulp's knowledge of the content unit
      and creates an association between the unit and the repository
   d. If necessary, calls link_unit to establish any relationships between units.
3. For units previously associated with the repository (known from get_units)
   that should no longer be, calls remove_unit to remove that association.

Throughout the sync process, the set_progress call can be used to update the
Pulp server on the status of the sync. Pulp will make this information available
to users.
"""

from gettext import gettext as _
import logging
import sys

from pulp.plugins.conduits.mixins import (
    ImporterConduitException, AddUnitMixin, RepoScratchPadMixin,
    ImporterScratchPadMixin, SingleRepoUnitsMixin, StatusMixin,
    SearchUnitsMixin)
from pulp.plugins.model import SyncReport
from pulp.server.managers.repo.unit_association import OWNER_TYPE_IMPORTER
import pulp.server.managers.factory as manager_factory


_logger = logging.getLogger(__name__)


class RepoSyncConduit(RepoScratchPadMixin, ImporterScratchPadMixin, AddUnitMixin,
                      SingleRepoUnitsMixin, StatusMixin, SearchUnitsMixin):
    """
    Used to communicate back into the Pulp server while an importer performs
    a repo sync. Instances of this class should *not* be cached between repo
    sync runs. Each sync will be issued its own conduit instance that is scoped
    to that run of the sync alone.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize its sync process.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, repo_id, importer_id, association_owner_type, association_owner_id):
        RepoScratchPadMixin.__init__(self, repo_id, ImporterConduitException)
        ImporterScratchPadMixin.__init__(self, repo_id, importer_id)
        AddUnitMixin.__init__(self, repo_id, importer_id, association_owner_type,
                              association_owner_id)
        SingleRepoUnitsMixin.__init__(self, repo_id, ImporterConduitException)
        StatusMixin.__init__(self, importer_id, ImporterConduitException)
        SearchUnitsMixin.__init__(self, ImporterConduitException)

        self._association_manager = manager_factory.repo_unit_association_manager()
        self._content_query_manager = manager_factory.content_query_manager()

        self._removed_count = 0

    def __str__(self):
        return _('RepoSyncConduit for repository [%(r)s]') % {'r': self.repo_id}

    def remove_unit(self, unit):
        """
        Removes the association between the given content unit and the repository
        being synchronized.

        This call will only remove the association owned by this importer
        between the repository and unit. If the unit was manually associated by
        a user, the repository will retain that instance of the association.

        This call does not delete Pulp's representation of the unit in its
        database. If this call removes the final association of the unit to a
        repository, the unit will become "orphaned" and will be deleted from
        Pulp outside of this plugin.

        Units passed to this call must have their id fields set by the Pulp server.

        This call is idempotent. If no association, owned by this importer, exists
        between the unit and repository, this call has no effect.

        @param unit: unit object (must have its id value set)
        @type  unit: L{Unit}
        """

        try:
            self._association_manager.unassociate_unit_by_id(
                self.repo_id, unit.type_id, unit.id, OWNER_TYPE_IMPORTER, self.association_owner_id)
            self._removed_count += 1
        except Exception, e:
            _logger.exception(_('Content unit unassociation failed'))
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def associate_existing(self, unit_type_id, search_dicts):
        """
        Associates existing units with a repo

        :param unit_type_id: unit type id
        :type  unit_type_id: str
        :param search_dicts: search dicts for units to associate with repo
                             (example: list of unit key dicts)
        :type  search_dicts: list of dicts
        """
        unit_ids = self._content_query_manager.get_content_unit_ids(unit_type_id, search_dicts)
        self._association_manager.associate_all_by_ids(self.repo_id, unit_type_id, unit_ids,
                                                       self.association_owner_type,
                                                       self.association_owner_id)

    def build_success_report(self, summary, details):
        """
        Creates the SyncReport instance that needs to be returned to the Pulp
        server at the end of a successful sync_repo call.

        The added, updated, and removed unit count fields will be populated with
        the tracking counters maintained by the conduit based on calls into it.
        If these are inaccurate for a given plugin's implementation, the counts
        can be changed in the returned report before returning it to Pulp.

        @param summary: short log of the sync; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the sync; may be None
        @type  details: any serializable
        """
        r = SyncReport(True, self._added_count, self._updated_count,
                       self._removed_count, summary, details)
        return r

    def build_failure_report(self, summary, details):
        """
        Creates the SyncReport instance that needs to be returned to the Pulp
        server at the end of a sync_repo call. The report built in this fashion
        will indicate the sync has gracefully failed (as compared to an
        unexpected exception bubbling up).

        The added, updated, and removed unit count fields will be populated with
        the tracking counters maintained by the conduit based on calls into it.
        If these are inaccurate for a given plugin's implementation, the counts
        can be changed in the returned report before returning it to Pulp. This
        data will capture how far it got before building the report and should
        be overridden if the plugin attempts to do some form of rollback due to
        the encountered error.

        @param summary: short log of the sync; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the sync; may be None
        @type  details: any serializable
        """
        r = SyncReport(False, self._added_count, self._updated_count,
                       self._removed_count, summary, details)
        return r

    def build_cancel_report(self, summary, details):
        """
        Creates the SyncReport instance that needs to be returned to the Pulp
        server at the end of a sync_repo call. The report built in this fashion
        will indicate the sync has been cancelled.

        The added, updated, and removed unit count fields will be populated with
        the tracking counters maintained by the conduit based on calls into it.
        If these are inaccurate for a given plugin's implementation, the counts
        can be changed in the returned report before returning it to Pulp. This
        data will capture how far it got before building the report and should
        be overridden if the plugin attempts to do some form of rollback due to
        the cancellation.

        @param summary: short log of the sync; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the sync; may be None
        @type  details: any serializable
        """
        r = SyncReport(False, self._added_count, self._updated_count,
                       self._removed_count, summary, details)
        r.canceled_flag = True
        return r
