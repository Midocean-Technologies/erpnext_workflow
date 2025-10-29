import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

@frappe.whitelist()
def after_install():
    create_custom_fields()

def create_custom_fields():
    create_custom_field(
        "User",
        {
            "label": _("Active Mobile App"),
            "fieldname": "active_mobile_app",
            "fieldtype": "Check",
            "insert_after": "user_fcm_token",
        },
    )

    create_custom_field(
        "User",
        {
            "label": _("User FCM Token"),
            "fieldname": "user_fcm_token",
            "fieldtype": "Small Text ",
            "insert_after": "time_zone",
        },
    )