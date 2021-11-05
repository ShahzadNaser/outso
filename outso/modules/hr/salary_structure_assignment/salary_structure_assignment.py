# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def before_save(self, method):
    if self.base:
        self.hourlyrate = round(self.base/(30*8), 2)