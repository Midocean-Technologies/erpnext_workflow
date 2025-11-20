import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

@frappe.whitelist()
def after_install():
    create_custom_fields()
    execute()

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

    create_custom_field(
        "Workflow",
        {
            "label": _("Send Mobile App Notification"),
            "fieldname": "send_mobile_app_notification",
            "fieldtype": "Check",
            "insert_after": "send_email_alert",
        },
    )


def execute():
    TITLE_FIELD_MAP = {
        # Sales Module
        "Sales Order": "customer",
        "Sales Invoice": "customer",
        "Delivery Note": "customer",

        # Purchase Module
        "Purchase Order": "supplier",
        "Purchase Invoice": "supplier",
        "Purchase Receipt": "supplier",

        # CRM / Core
        "Customer": "customer_name",
        "Supplier": "supplier_name",
        "Quotation": "party_name",
        "Lead": "lead_name",

        # Accounting
        "Payment Entry": "party",

        # Stock / Quality
        "Material Request": "material_request_type",
        "Stock Entry": "stock_entry_type",
        "Quality Inspection": "item_code",

        # HR
        "Employee": "employee_name",
    }

    doc = frappe.get_single("Smart Workflow Settings")
    existing = [d.reference_doctype for d in doc.title_fields]

    for doctype, fieldname in TITLE_FIELD_MAP.items():
        if doctype not in existing:
            row = doc.append("title_fields", {})
            row.reference_doctype = doctype
            row.title_field_name = fieldname

    doc.save(ignore_permissions=True)