# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Events affected by the former split-run check-out issue were already
    # marked as synchronized. Re-queue them so the corrected aggregation can
    # rebuild the first/last punch for each day.
    cr.execute("UPDATE dahua_attendance_log SET synced = FALSE WHERE synced = TRUE")
