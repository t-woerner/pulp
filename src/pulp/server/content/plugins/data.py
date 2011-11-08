# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module contains transfer objects for encapsulating data passed into a
plugin method call. Objects defined in this module will have extra information
bundled in that is relevant to the plugin's state for the given entity.
"""

class Repository:
    """
    Contains repository data and any additional data relevant for the plugin to
    function.

    @ivar id: programmatic ID for the repository
    @type id: str

    @ivar display_name: user-friendly name describing the repository
    @type display_name: str or None

    @ivar description: user-friendly description of the repository
    @type description: str or None

    @ivar notes: arbitrary key-value pairs set and used by users to
                 programmatically describe the repository
    @type notes: str or None

    @ivar working_dir: local (to the Pulp server) directory the importer may use
          to store any temporary data required by the importer; this directory
          is unique for each repository
    @type working_dir: str
    """

    @classmethod
    def from_repo(cls, repo):
        """
        Creates a new instance of this class from a Pulp internal repository
        representation (in its database dict representation).
        """
        r = Repository()

        r.id = repo['id']
        r.display_name = repo['display_name']
        r.description = repo['description']
        r.notes = repo['notes']

    def init(self):
        self.id = None
        self.display_name = None
        self.description = None
        self.notes = None

        self.working_dir = None

class Unit:
    """
    Contains information related to a single content unit. The unit may or
    may not exist in Pulp; this is meant simply as a way of linking together
    a number of pieces of data.

    @ivar id: Pulp internal ID that refers to this unit; if the unit does not
              yet exist in Pulp, this will be None
    @type id: str

    @ivar type: ID of the unit's type
    @type type: str

    @ivar metadata: mapping of key/value pairs describing the unit
    @type metadata: dict

    @ivar location: full path to where on disk the unit is currently stored;
                    the unit may have been placed here either by an importer or
                    this may refer to a temporary location Pulp has saved the
                    unit to if it was uploaded by a user
    @type location: str
    """

    def init(self, type, metadata):
        self.type = type
        self.metadata = metadata

        self.id = None
        self.location = None
