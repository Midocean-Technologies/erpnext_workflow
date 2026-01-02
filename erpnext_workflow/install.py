import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.permissions import add_permission

@frappe.whitelist()
def after_install():
    create_custom_fields()
    create_role_if_not_exists()
    role_for_socket_and_comment_notification_list()

@frappe.whitelist()
def after_migrate():
    create_role_if_not_exists()
    role_for_socket_and_comment_notification_list()

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
            "fieldtype": "Small Text",
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

    create_custom_field(
        "Workflow",
        {
            "label": _("Print Format"),
            "fieldname": "print_format",
            "fieldtype": "Link",
            "options": "Print Format",
            "insert_after": "workflow_state_field",
        },
    )

def create_role_if_not_exists():
    ROLE_NAME = "Workflow Mobile App"
    if not frappe.db.exists("Role", ROLE_NAME):
        print(f"Creating role: {ROLE_NAME}")
        role_doc = frappe.get_doc({
            "doctype": "Role",
            "role_name": ROLE_NAME,
            "desk_access": 1,
            "disabled": 0
        })
        role_doc.insert(ignore_permissions=True)
        frappe.db.commit()
    else:
        print(f"Role '{ROLE_NAME}' already exists")

def add_role_permission(doctype, role):

    existing_perms = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": doctype, "role": role},
        pluck="name"
    )

    for perm in existing_perms:
        frappe.delete_doc("Custom DocPerm", perm, ignore_permissions=True)

    add_permission(doctype, role)

    frappe.db.sql("""
        UPDATE `tabCustom DocPerm`
        SET 
            `read` = 1,
            `write` = 1,
            `create` = 1,
            `delete` = 0,
            `submit` = 0,
            `cancel` = 0,
            `export` = 0,
            `amend` = 0,
            `select` = 1
        WHERE parent = %s AND role = %s
    """, (doctype, role))

    frappe.clear_cache(doctype=doctype)

@frappe.whitelist()
def role_for_socket_and_comment_notification_list():
    ROLE_NAME = "Workflow Mobile App"
    DOCTYPES = [
        "Socket Notification List",
        "Comment"
    ]
    try:
        if not frappe.db.exists("Role", ROLE_NAME):
            print(f"Role '{ROLE_NAME}' does not exist. Creating it now...")
            create_role_if_not_exists()

        for doctype in DOCTYPES:
            if not frappe.db.exists("DocType", doctype):
                print(f"Error: DocType '{doctype}' does not exist")
                continue

            add_role_permission(doctype, ROLE_NAME)

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Error adding permissions for {ROLE_NAME}"
        )
        raise