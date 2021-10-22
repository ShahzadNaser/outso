# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt
from outso.constants.globals import SHIFT_HOURS
from outso.utils import get_time_diff


def before_save(doc, method):
    calculate_overtime(doc)

def calculate_overtime(doc):
    '''Customization calculate overtime according to requirements'''
    if doc.working_hours and doc.working_hours > SHIFT_HOURS:
        temp_hours = get_time_diff(doc.out_time,doc.in_time, "hours") - SHIFT_HOURS
        overtime_hours , rem = divmod(temp_hours,1)
        if(rem >= .50):
            if(rem >= .75):
                overtime_hours += 1
            else:
                overtime_hours += .5
        doc.overtime_hours = flt(overtime_hours)
