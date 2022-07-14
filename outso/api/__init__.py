import frappe

__version__ = '0.0.1'

@frappe.whitelist(allow_guest=True)
def get():
    error = False