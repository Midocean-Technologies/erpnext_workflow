import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.permissions import add_permission

@frappe.whitelist()
def after_install():
    create_custom_fields()
    # execute()
    create_role_if_not_exists()
    role_for_socket_notification_list()

@frappe.whitelist()
def after_migrate():
    # execute()
    create_role_if_not_exists()
    role_for_socket_notification_list()

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

@frappe.whitelist()
def role_for_socket_notification_list():
    ROLE_NAME = "Workflow Mobile App"
    DOCTYPE = "Socket Notification List"
    
    try:
        if not frappe.db.exists("Role", ROLE_NAME):
            print(f"Role '{ROLE_NAME}' does not exist. Creating it now...")
            create_role_if_not_exists()
        
        if not frappe.db.exists("DocType", DOCTYPE):
            print(f"Error: DocType '{DOCTYPE}' does not exist")
            return
        
        existing_perms = frappe.get_all(
            "Custom DocPerm",
            filters={"parent": DOCTYPE, "role": ROLE_NAME},
            pluck="name"
        )
        
        for perm in existing_perms:
            frappe.delete_doc("Custom DocPerm", perm, ignore_permissions=True)
        
        add_permission(DOCTYPE, ROLE_NAME)
        
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
        """, (DOCTYPE, ROLE_NAME))
        
        frappe.db.commit()
        
        frappe.clear_cache(doctype=DOCTYPE)
                
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Error adding permissions for {ROLE_NAME}"
        )
        print(f"Error: {str(e)}")
        raise