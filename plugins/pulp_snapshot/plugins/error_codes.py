from gettext import gettext as _

from pulp.common.error_codes import Error

SNAP0100 = Error("SNAP0100", _("Error snapshotting repository %(repo)s"),
                 ['repo'])
