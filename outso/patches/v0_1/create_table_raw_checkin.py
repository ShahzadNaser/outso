# Copyright (c) 2021, Thenexperts and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():

    frappe.db.sql("""
        CREATE TABLE IF NOT EXISTS `tabRaw Checkins` (
            `id` int(11) NOT NULL auto_increment,     
            `employee` varchar(250)  NOT NULL default '',     
            `check_time` datetime(6) DEFAULT NULL,     
            `sync` TINYINT(1) NOT NULL default 0,     
            `attendance_it` int(11)  default NULL,     
            `creation`     DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY  (`id`)
            );
    """)
    frappe.db.commit()