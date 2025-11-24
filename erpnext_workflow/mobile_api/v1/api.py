import frappe
from frappe.auth import LoginManager
from frappe import _
from erpnext_workflow.mobile_api.v1.api_utils import * 
from frappe.model.workflow import get_transitions, get_workflow, apply_workflow
import re
from frappe.utils.user import get_users_with_role

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        login_manager.post_login()

        if frappe.response.get("message") == "Logged In":
            user = login_manager.user

            try:
                settings = frappe.get_single("Smart Workflow Settings")
            except frappe.DoesNotExistError:
                return gen_response(500, "User has no permission for mobile app, please contact Admin")

            if not settings.enabled:
                return gen_response(500, "User has no permission for mobile app, please contact Admin")

            return gen_response(200, "Logged In", {"user": user})

        return gen_response(500, "Login failed")

    except frappe.AuthenticationError:
        return gen_response(500, "Invalid username or password")

    except Exception as e:
        clean_msg = BeautifulSoup(str(e), "lxml").get_text()
        return gen_response(500, clean_msg)


@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_type_list(user=None):
    try:
        doc = frappe.get_list('Workflow Action', filters={'status': 'Open'}, fields=['name', 'reference_name', 'reference_doctype'])
        gen_response(200 ,"Data Fetch Succesfully", doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)
	
@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_list(reference_doctype, user=None):
    try:
        lst = []
 
        settings = frappe.get_single("Smart Workflow Settings")
 
        title_map = {}
        for row in settings.title_fields:
            title_map[row.reference_doctype] = row.title_field_name
 
        workflow_state_filter = frappe.form_dict.get("workflow_state")
 
        document_list = frappe.get_list(
            "Workflow Action",
            filters={"status": "Open", "reference_doctype": reference_doctype},
            fields=["name", "reference_name", "reference_doctype"]
        )
 
        for row in document_list:
            if frappe.db.exists(row.reference_doctype, row.reference_name):
 
                doc = frappe.get_doc(row.reference_doctype, row.reference_name)
                current_state = getattr(doc, "workflow_state", "")
 
                if workflow_state_filter and current_state != workflow_state_filter:
                    continue
 
                info = {}
                info["reference_doctype"] = row.reference_doctype
                info["reference_name"] = row.reference_name
                info["workflow_state"] = current_state
 
                title_field = title_map.get(row.reference_doctype)
                if title_field and hasattr(doc, title_field):
                    info["title"] = getattr(doc, title_field)
                else:
                    info["title"] = ""
 
                lst.append(info)
 
        return gen_response(200, "Data Fetched Successfully", lst)
 
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
 
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_document_list Error")
        return gen_response(500, str(e))

def get_status(status):
	if status == 0:
		return 'Draft'

	if status == 1:
		return 'Submitted'
	
	if status == 2:
		return 'Cancelled'
    
@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_list_5_record(user=None):
    try:
        lst = []
	
        document_list = frappe.get_list('Workflow Action', filters={'status': 'Open'}, fields=['name', 'reference_name', 'reference_doctype'], limit_page_length=5)
        for row in document_list:
            docc = {}
            if frappe.db.exists(row.reference_doctype, row.reference_name):
                doc = frappe.get_doc(row.reference_doctype, row.reference_name)
                docc['reference_doctype'] = row.reference_doctype
                docc['reference_name'] = row.reference_name
                docc['workflow_state'] = doc.workflow_state
                docc['title'] = doc.title
                docc['status'] = get_status(doc.docstatus)
                lst.append(docc)
        gen_response(200 ,"Data Fetch Succesfully", lst)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_workflow_action(reference_doctype, reference_name):
    try:
        doc = frappe.get_doc(reference_doctype, reference_name)
        workflow = get_workflow(doc.doctype)
        data = get_transitions(doc, workflow)
        gen_response(200 ,"Data Fetch Succesfully", data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_print_format(reference_doctype, reference_name, print_format_name=None):
    try:
        if not print_format_name:
            print_format_name = "Standard"
        
        res = frappe.get_print(
            doctype=reference_doctype,
            name=reference_name,
            print_format=print_format_name
        )
        
        # Replace grey background
        res = res.replace('background-color: #d1d8dd;', 'background-color: white;')
        res = res.replace('padding: 30px 0px;', 'padding: 0px;')
        
        # Remove unwanted patterns
        unwanted_patterns = [
            r'<div class="action-banner print-hide">.*?</div>',  
        ]
        for pattern in unwanted_patterns:
            res = re.sub(pattern, '', res, flags=re.DOTALL)
        
        res = re.sub(r'<link[^>]*print\.bundle[^>]*>', '', res)
        
        alignment_css = """
        <style>
        .text-right { text-align: right !important; }
        .text-center { text-align: center !important; }
        .text-left { text-align: left !important; }
        
        .print-format { max-width: 8.3in; margin: 0 auto; padding: 15px; }
        table { width: 100%; border-collapse: collapse; }
        table.table-bordered { border: 1px solid #d1d8dd; }
        table.table-bordered td, table.table-bordered th { 
            border: 1px solid #d1d8dd; 
            padding: 8px;
        }
        .col-xs-1 { width: 8.33%; }
        .col-xs-2 { width: 16.66%; }
        .col-xs-3 { width: 25%; }
        .col-xs-4 { width: 33.33%; }
        .col-xs-5 { width: 41.66%; }
        .col-xs-6 { width: 50%; }
        .col-xs-7 { width: 58.33%; }
        .col-xs-8 { width: 66.66%; }
        .col-xs-9 { width: 75%; }
        .col-xs-10 { width: 83.33%; }
        .col-xs-11 { width: 91.66%; }
        .col-xs-12 { width: 100%; }
        .row { display: flex; flex-wrap: wrap; }
        .row > div { float: left; }
        </style>
        """
        
        res = res.replace('</head>', alignment_css + '</head>')
            
        return gen_response(200, "Data Fetched Successfully", res)
        
    except frappe.PermissionError:
        return gen_response(403, "Not permitted")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Print Format Error")
        return exception_handler(e)


@frappe.whitelist()
@mtpl_validate(methods=["POST"])
def update_workflow(reference_doctype, reference_name, action):
    try:
        # doc = get_doc_details(reference_doctype, reference_name)
        doc = frappe.get_doc(reference_doctype, reference_name)
        apply_workflow(doc, action)
        gen_response(200 ,"Workflow Updated")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
def store_fcm_token(user, token):
    try:
        doc = frappe.get_doc('User', user)
        doc.db_set('user_fcm_token', token)
        frappe.db.commit()
        return doc
    except Exception as e:
        raise e

@frappe.whitelist()
@mtpl_validate(methods=["POST"])
def trigger_workflow_notification(doc, method):

    if not hasattr(doc, 'workflow_state') or not doc.workflow_state:
        return

    previous = doc.get_doc_before_save()
    old_state = previous.workflow_state if previous else None
    new_state = doc.workflow_state
    
    if old_state == new_state:
        return
    
    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": doc.doctype, "is_active": 1},
        "name"
    )
    
    if not workflow_name:
        return
    
    current_role = frappe.db.get_value(
        "Workflow Document State",
        {"parent": workflow_name, "state": new_state},
        "allow_edit"
    )
    
    if not current_role:
        return
    
    users = frappe.db.get_all(
        "Has Role",
        filters={"role": current_role},
        fields=["parent as user"]
    )
    
    enabled_users = [
        u.user for u in users
        if frappe.db.get_value("User", u.user, "enabled")
    ]
    
    if not enabled_users:
        return
    
    transitions = frappe.get_all(
        "Workflow Transition",
        filters={"parent": workflow_name, "state": new_state},
        fields=["action"]
    )
    
    actions_list = [{"action": t["action"]} for t in transitions]
    
    message = {
        "doctype": doc.doctype,
        "docname": doc.name,
        "msg": new_state,
        "actions": actions_list,
        "user": enabled_users
    }
    
    frappe.log_error("Workflow Notification", message)

    for user in enabled_users:
        frappe.publish_realtime("erp_notification", message, user=user)

    workflow_state_filter = frappe.form_dict.get("workflow_state")

    if workflow_state_filter:
        if doc.workflow_state != workflow_state_filter:
            frappe.throw(_("The workflow state does not match the filter."))

