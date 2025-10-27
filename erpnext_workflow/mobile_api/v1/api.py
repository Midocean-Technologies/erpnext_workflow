import frappe
from frappe.auth import LoginManager
from frappe import _
from erpnext_workflow.mobile_api.v1.api_utils import * 
from frappe.model.workflow import get_transitions, get_workflow, apply_workflow
# from frappe.workflow.doctype.workflow_action.workflow_action import confirm_action, apply_action


@frappe.whitelist(allow_guest=True)
def login(usr, pwd, firebase_token=None):
    try:
        # Authenticate user
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        login_manager.post_login()

        if frappe.response.get("message") == "Logged In":
            user = login_manager.user

            # installed_apps = frappe.get_installed_apps()
            # if "erpnext_workflow" not in installed_apps:
            #     return gen_response(500, "The ERPNext Workflow app is not installed on this site. Please contact the Administrator.")

            settings = frappe.get_single("Smart Workflow Settings")

            if not settings.enabled:
                return gen_response(500, "User has no permission for mobile app, please contact Admin")

            if firebase_token:
                if not settings.firebase_token:
                    return gen_response(500, "Firebase token not found, please contact Admin")
                if firebase_token != settings.firebase_token:
                    return gen_response(500, "Invalid Firebase token")

            frappe.response["user"] = user
            frappe.response["key_details"] = generate_key(user)

            return gen_response(200, frappe.response["message"])

        return gen_response(500, "Login failed")

    except frappe.AuthenticationError:
        return gen_response(500, frappe.response.get("message", "Invalid username or password"))
    except Exception as e:
        return exception_handler(e)

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
	
        document_list = frappe.get_list('Workflow Action', filters={'status': 'Open', 'reference_doctype': reference_doctype}, fields=['name', 'reference_name', 'reference_doctype'])
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
def get_print_format(reference_doctype, reference_name):
    try:
        print_format = "Standard"
        smart_setting = frappe.get_single("Smart Connect Setting")
        if smart_setting.print_format:
            for i in smart_setting.print_format:
                if i.doctype_name == reference_doctype:
                    print_format = i.print_format

        data = frappe.get_print(doctype=reference_doctype, name=reference_name, print_format=print_format)
        gen_response(200 ,"Data Fetch Succesfully", data)
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