from dateutil.relativedelta import relativedelta

from odoo import fields, models


class HrLeaveAccrualLevel(models.Model):
    _inherit = 'hr.leave.accrual.level'

    frequency = fields.Selection(
        selection_add=[('quarterly', 'Quarterly')],
        ondelete={'quarterly': 'set default'},
    )

    def _get_next_date(self, last_call):
        """Return the next quarterly call relative to the allocation cycle.

        Odoo initializes ``last_call`` from the allocation Start Date (plus the
        optional Start Accruing delay). Therefore adding three calendar months
        keeps every employee's quarterly cycle anchored to their own allocation
        Start Date, for example 15 April -> 15 July -> 15 October.
        """
        self.ensure_one()
        if self.frequency == 'quarterly':
            return last_call + relativedelta(months=3)
        return super()._get_next_date(last_call)

    def _get_previous_date(self, last_call):
        """Treat a quarterly ``last_call`` as the start of its own period.

        During accrual processing Odoo passes the stored call date, which is
        already an allocation-relative quarterly boundary. Returning the same
        date prevents prorating a complete three-month period.
        """
        self.ensure_one()
        if self.frequency == 'quarterly':
            return last_call
        return super()._get_previous_date(last_call)
