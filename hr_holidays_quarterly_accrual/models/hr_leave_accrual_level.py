from dateutil.relativedelta import relativedelta

from odoo import fields, models


class HrLeaveAccrualLevel(models.Model):
    _inherit = 'hr.leave.accrual.level'

    frequency = fields.Selection(
        selection_add=[('quarterly', 'Quarterly')],
        ondelete={'quarterly': 'set default'},
    )

    _sql_constraints = [
        ('check_dates',
         "CHECK( (frequency IN ('daily', 'hourly', 'quarterly')) or "
         "(week_day IS NOT NULL AND frequency = 'weekly') or "
         "(first_day > 0 AND second_day > first_day AND first_day <= 31 AND second_day <= 31 AND frequency = 'bimonthly') or "
         "(first_day > 0 AND first_day <= 31 AND frequency = 'monthly') or "
         "(first_month_day > 0 AND first_month_day <= 31 AND second_month_day > 0 AND second_month_day <= 31 AND frequency = 'biyearly') or "
         "(yearly_day > 0 AND yearly_day <= 31 AND frequency = 'yearly'))",
         "The dates you've set up aren't correct. Please check them."),
        ('start_count_check', "CHECK( start_count >= 0 )", "You can not start an accrual in the past."),
        ('added_value_greater_than_zero', 'CHECK(added_value > 0)', "You must give a rate greater than 0 in accrual plan levels."),
        (
            'valid_yearly_cap_value',
            'CHECK(cap_accrued_time_yearly IS NOT TRUE OR COALESCE(maximum_leave_yearly, 0) > 0)',
            "You cannot have a cap on yearly accrued time without setting a maximum amount."
        ),
    ]

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
