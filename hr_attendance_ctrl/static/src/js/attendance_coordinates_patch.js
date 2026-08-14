/** @odoo-module **/

import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";


patch(ActivityMenu.prototype, {
    async checking(latitude = false, longitude = false) {
        // Odoo calls checking(false, false) when company device tracking is
        // disabled.  The location label has already obtained a browser fix;
        // reuse that recent fix so hr.attendance can store GPS and office IDs.
        const cache = window.__att_ctrl_geo_cache;
        const age = cache ? Date.now() - (cache.ts || 0) : Infinity;
        if (
            (latitude === false || latitude == null) &&
            (longitude === false || longitude == null) &&
            cache?.coords &&
            age >= 0 &&
            age <= 60000
        ) {
            latitude = cache.coords.latitude;
            longitude = cache.coords.longitude;
        }
        return super.checking(latitude, longitude);
    },
});
